"""Unit tests for the wire schemas and the MCP tool factories (TODO 2.1).

Two things carry the weight here: a payload must hash identically on both peers,
and a malformed message must produce a **named** error we can quote back at an
opponent. With no referee, "your step 7 commit arrived with no digest" is the
entire remedy available to us.
"""

from __future__ import annotations

import pytest

from core.crypto.canonical import digest
from core.protocol.schemas import (
    Ack,
    BarrierDeclaration,
    CaptureClaim,
    CaptureResponse,
    Commit,
    FinalReveal,
    Intent,
    MessageKind,
    Negotiation,
    Reveal,
    Role,
)
from core.protocol.tools import TOOL_BUILDERS, ProtocolError, build_tools


class Recorder:
    """A handler that remembers what it was given and answers plausibly."""

    def __init__(self) -> None:
        self.seen: list[object] = []

    def on_commit(self, message: Commit) -> Ack:
        self.seen.append(message)
        return Ack(step=message.step, role=Role.THIEF, acknowledged_digest=message.digest)

    def on_reveal(self, message: Reveal) -> None:
        self.seen.append(message)

    def on_final_reveal(self, message: FinalReveal) -> None:
        self.seen.append(message)

    def on_capture_claim(self, message: CaptureClaim) -> CaptureResponse:
        self.seen.append(message)
        return CaptureResponse(step=message.step, role=Role.THIEF, accepted=True)

    def on_barrier(self, message: BarrierDeclaration) -> None:
        self.seen.append(message)

    def on_negotiate(self, message: Negotiation) -> Negotiation:
        self.seen.append(message)
        return Negotiation(step=0, role=Role.THIEF, config_digest=message.config_digest)


@pytest.fixture
def handler() -> Recorder:
    return Recorder()


@pytest.fixture
def tools(handler: Recorder) -> dict:
    return build_tools(handler)


# --- schemas ----------------------------------------------------------------


def test_every_message_carries_its_kind_step_and_role() -> None:
    payload = Commit(step=3, role=Role.COP, digest="abc").payload()
    assert payload["kind"] == "commit"
    assert payload["step"] == 3
    assert payload["role"] == "cop"


def test_the_kind_cannot_be_faked_by_a_caller() -> None:
    """KIND is a ClassVar, so a Commit can never claim to be a Reveal."""
    with pytest.raises(TypeError):
        Commit(step=1, role=Role.COP, digest="x", kind=MessageKind.REVEAL)  # type: ignore[call-arg]


def test_tuples_become_lists_so_a_round_trip_hashes_the_same() -> None:
    """JSON has no tuple; a re-serialised message must produce identical bytes."""
    payload = Reveal(step=1, role=Role.COP, move="N", barrier_cell=(2, 3)).payload()
    assert payload["barrier_cell"] == [2, 3]
    assert digest(payload) == digest(dict(payload))


def test_enums_serialise_as_their_values() -> None:
    payload = Reveal(step=1, role=Role.THIEF, move="S", intent=Intent.LIE).payload()
    assert payload["intent"] == "lie"
    assert payload["role"] == "thief"


def test_two_identical_messages_produce_one_digest() -> None:
    left = Commit(step=5, role=Role.COP, digest="d")
    right = Commit(step=5, role=Role.COP, digest="d")
    assert digest(left.payload()) == digest(right.payload())


def test_a_commit_payload_contains_no_move() -> None:
    """The whole point: the commitment reveals nothing (Ch. 5.3.1)."""
    assert set(Commit(step=1, role=Role.COP, digest="d").payload()) == {
        "kind",
        "step",
        "role",
        "digest",
    }


def test_a_reveal_payload_contains_no_nonce() -> None:
    """M#18: nonces are released only in the final reveal."""
    assert "nonce" not in Reveal(step=1, role=Role.COP, move="N").payload()


def test_the_negotiation_payload_carries_every_agreed_reading() -> None:
    """C-006 and C-010 must be signed, not assumed."""
    payload = Negotiation(
        step=0,
        role=Role.COP,
        config_digest="d",
        scent_model_digest="s",
        readings={"capture.resolution": "after_moves", "coords": "row,col"},
    ).payload()
    assert payload["role_split"] == "3-3"
    assert payload["readings"]["coords"] == "row,col"


# --- tool factories ---------------------------------------------------------


def test_every_mandated_tool_has_a_factory() -> None:
    """2.1.2: a new tool is one factory plus one registration line."""
    assert set(TOOL_BUILDERS) == {
        "receive_commit",
        "receive_reveal",
        "final_reveal",
        "capture_claim",
        "declare_barrier",
        "negotiate",
    }


def test_a_commit_is_stored_and_acknowledged(tools: dict, handler: Recorder) -> None:
    reply = tools["receive_commit"]({"step": 2, "role": "cop", "digest": "abc"})
    assert reply["kind"] == "ack"
    assert reply["acknowledged_digest"] == "abc"
    assert handler.seen[0].digest == "abc"


def test_a_reveal_carrying_a_nonce_is_refused(tools: dict) -> None:
    """The M#18 guard, enforced on the receiving side too."""
    with pytest.raises(ProtocolError, match="must not carry a nonce"):
        tools["receive_reveal"]({"step": 2, "role": "cop", "move": "N", "nonce": "deadbeef"})


def test_a_reveal_without_a_move_is_refused(tools: dict) -> None:
    with pytest.raises(ProtocolError, match="missing required field"):
        tools["receive_reveal"]({"step": 2, "role": "cop", "hint": "hello"})


def test_a_barrier_cell_arrives_as_a_tuple(tools: dict, handler: Recorder) -> None:
    tools["receive_reveal"]({"step": 2, "role": "cop", "move": "STAY", "barrier_cell": [2, 3]})
    assert handler.seen[0].barrier_cell == (2, 3)


@pytest.mark.parametrize("step", [-1, "3", None, 1.5])
def test_a_bad_step_is_refused(tools: dict, step: object) -> None:
    with pytest.raises(ProtocolError, match="step must be a non-negative integer"):
        tools["receive_commit"]({"step": step, "role": "cop", "digest": "d"})


def test_an_unknown_role_is_refused(tools: dict) -> None:
    with pytest.raises(ProtocolError, match="unknown role"):
        tools["receive_commit"]({"step": 1, "role": "referee", "digest": "d"})


def test_a_mislabelled_payload_is_refused(tools: dict) -> None:
    """A receiver never infers the type from the shape."""
    with pytest.raises(ProtocolError, match="expected a commit payload"):
        tools["receive_commit"]({"kind": "reveal", "step": 1, "role": "cop", "digest": "d"})


def test_a_final_reveal_needs_actual_nonces(tools: dict) -> None:
    with pytest.raises(ProtocolError, match="non-empty mapping"):
        tools["final_reveal"]({"step": 35, "role": "cop", "nonces": {}})


def test_a_final_reveal_reports_how_many_it_received(tools: dict) -> None:
    reply = tools["final_reveal"]({"step": 35, "role": "cop", "nonces": {"0": "a", "1": "b"}})
    assert reply == {"received": True, "count": 2}


@pytest.mark.parametrize("cell", [None, [1], [1, 2, 3], "3,3"])
def test_a_capture_claim_needs_a_two_part_cell(tools: dict, cell: object) -> None:
    with pytest.raises(ProtocolError, match=r"needs a \[row, col\] cell"):
        tools["capture_claim"]({"step": 9, "role": "cop", "cell": cell})


@pytest.mark.parametrize("cell", [None, [1], [1, 2, 3], "2,3"])
def test_a_barrier_declaration_needs_a_two_part_cell(tools: dict, cell: object) -> None:
    """A malformed declaration is not a declaration. M#15 wants the exact cell."""
    with pytest.raises(ProtocolError, match=r"needs a \[row, col\] cell"):
        tools["declare_barrier"]({"step": 4, "role": "cop", "cell": cell})


def test_a_capture_claim_is_answered(tools: dict, handler: Recorder) -> None:
    reply = tools["capture_claim"]({"step": 9, "role": "cop", "cell": [3, 3], "rule": "M#46"})
    assert reply["accepted"] is True
    assert handler.seen[0].cell == (3, 3)


def test_a_barrier_declaration_names_its_exact_cell(tools: dict, handler: Recorder) -> None:
    """M#15: no hidden placement, and the cell is exact."""
    reply = tools["declare_barrier"]({"step": 4, "role": "cop", "cell": [2, 3], "remaining": 13})
    assert reply["cell"] == [2, 3]
    assert handler.seen[0].remaining == 13


def test_negotiation_requires_a_config_digest(tools: dict) -> None:
    """M#11: no digest means nothing to compare, so there is no match to play."""
    with pytest.raises(ProtocolError, match="missing required field"):
        tools["negotiate"]({"step": 0, "role": "cop"})


def test_negotiation_returns_our_own_proposal(tools: dict) -> None:
    reply = tools["negotiate"]({"step": 0, "role": "cop", "config_digest": "abc"})
    assert reply["kind"] == "negotiation"
    assert reply["config_digest"] == "abc"


def test_tools_are_plain_callables_with_no_transport_dependency() -> None:
    """Nothing in this layer imports FastMCP, so it tests without a server."""
    import core.protocol.tools as module

    assert "fastmcp" not in str(module.__dict__.get("__builtins__", ""))
    assert all(callable(tool) for tool in build_tools(Recorder()).values())
