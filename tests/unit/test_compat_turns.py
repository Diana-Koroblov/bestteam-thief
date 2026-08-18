"""Unit tests for the role guard, live-commit tracking, and per-sender step
counter added to core/compat/turns.py (imreeyal §3.4, §3.6, §3.10).
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from core.compat.mailbox import Inboxes
from core.compat.session import ReferenceSession
from core.compat.turns import read_turn, send_turn
from core.compat.wire import TurnMessage
from core.protocol.schemas import Role
from core.protocol.tools import ProtocolError
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from core.shared.config_manager import Config
from tests.paths import brain_class, needs_brain

thief_only = needs_brain("thief")


def _session(role: Role, minimal_config: Config, client=None) -> ReferenceSession:
    runtime = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, role))
    runtime.agreed = True
    return ReferenceSession(runtime=runtime, client=client, inboxes=Inboxes(), identity={})


def _turn(step: int, sender: str, commit: str = "c" * 64) -> TurnMessage:
    return TurnMessage(
        step=step, sender=sender, hint="", smell_grid={}, commit=commit, timestamp="2026-01-01"
    )


def test_read_turn_accepts_the_opposite_role_and_records_the_live_commit(
    minimal_config: Config,
) -> None:
    session = _session(Role.COP, minimal_config)  # we are cop; thief must open
    read_turn(session, _turn(1, "thief", "a" * 64))
    assert session.received[1] == "a" * 64


def test_read_turn_rejects_our_own_role_as_a_claimed_sender(minimal_config: Config) -> None:
    """Bound from role parity before anything else is trusted (imreeyal §3.4) —
    a stray or replayed message claiming to be us must never be folded in."""
    session = _session(Role.COP, minimal_config)
    with pytest.raises(ProtocolError, match="thief"):
        read_turn(session, _turn(1, "cop"))


def test_read_turn_accepts_police_as_the_reference_spelling_of_cop(
    minimal_config: Config,
) -> None:
    session = _session(Role.THIEF, minimal_config)  # we are thief; cop/police must open
    read_turn(session, _turn(1, "police", "b" * 64))
    assert session.received[1] == "b" * 64


def _barrier_turn(step: int, sender: str, cell: list[int]) -> TurnMessage:
    """Their turn, carrying the wall they just placed."""
    return TurnMessage(
        step=step, sender=sender, hint="", smell_grid={}, commit="c" * 64,
        timestamp="2026-01-01", barrier_placed=cell,
    )


def test_a_barrier_sealing_our_last_exit_concedes_the_capture(minimal_config: Config) -> None:
    """🐛 **The sub-game we filed as a survival (imreeyal g02, 16/08).**

    Their cop caged our thief at the corner (6,0): (5,0) walled at step 19,
    (6,1) at step 20, the other two sides being board edge. This path judged
    capture by bare positional equality, so we conceded nothing — nobody asked,
    because placing the wall costs the cop its move and `_claim` stays silent on
    a STAY — and played out the final 15 turns into a survival their settlement
    layer derived, correctly, as a capture.
    """
    session = _session(Role.THIEF, minimal_config)
    session.orchestrator.advance(
        replace(session.state, thief=(6, 0), barriers=frozenset({(5, 0)}))
    )
    outcome = read_turn(session, _barrier_turn(1, "police", [6, 1]))
    assert outcome.we_are_caught is True
    assert outcome.claim_response == {
        "claim": [6, 0], "caught": True, "rule": "thief sealed in at (6, 0) (M#47)"
    }


def test_a_barrier_on_our_own_cell_concedes_the_capture(minimal_config: Config) -> None:
    """**M#46**, the more common wall form — and one no state-judging path
    implemented at all until `Rules.thief_is_trapped` existed."""
    session = _session(Role.THIEF, minimal_config)
    session.orchestrator.advance(replace(session.state, thief=(3, 3)))
    outcome = read_turn(session, _barrier_turn(1, "police", [3, 3]))
    assert outcome.we_are_caught is True
    assert "M#46" in outcome.claim_response["rule"]


def test_a_wall_that_leaves_an_exit_open_concedes_nothing(minimal_config: Config) -> None:
    """The concession is load-bearing only if ordinary pressure still plays on:
    g04 and g06 of that same series were 8 and 9 walls and no cage."""
    session = _session(Role.THIEF, minimal_config)
    session.orchestrator.advance(replace(session.state, thief=(6, 0)))
    outcome = read_turn(session, _barrier_turn(1, "police", [5, 0]))
    assert outcome.we_are_caught is False
    assert outcome.claim_response is None


def test_the_cop_never_reads_a_cage_off_its_own_state(minimal_config: Config) -> None:
    """Only the Thief can be trapped, and only the Thief's half of a compat
    `state` is real — `state.thief` is a fiction in a cop session, so conceding
    from it would hand away a sub-game nobody had won."""
    session = _session(Role.COP, minimal_config)
    session.orchestrator.advance(
        replace(session.state, thief=(6, 0), barriers=frozenset({(5, 0), (6, 1)}))
    )
    outcome = read_turn(session, _turn(1, "thief"))
    assert outcome.we_are_caught is False
    assert outcome.claim_response is None


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def call(self, name: str, payload: dict, argument: str = "payload") -> dict:
        self.calls.append(payload)
        return {"ok": True}


@thief_only
async def test_send_turn_numbers_our_own_turns_from_one_independent_of_state_step(
    minimal_config: Config,
) -> None:
    """Per-sender, starting at 1 (imreeyal §3.6) — not the shared game-progress
    counter, which advances on either side's move and would send 0, 2, 4..."""
    client = _RecordingClient()
    session = _session(Role.THIEF, minimal_config, client=client)
    session.runtime.brain = brain_class("thief")()
    await send_turn(session, None)
    await send_turn(session, None)
    assert [call["step"] for call in client.calls] == [1, 2]


@thief_only
async def test_send_turn_reads_the_trail_one_decay_step_older_and_rounded(
    minimal_config: Config,
) -> None:
    """imreeyal §3.13: `LocalTruth` deposits at peak 0.9, but the wire must
    carry the already-decayed reading rounded to 3 decimals — not the raw
    deposit.

    The expected figure is **computed from the model the config names**, not
    written down: 0.81 under the book's multiplicative decay, 0.80 under the
    reference's subtractive one, and a literal here silently asserts which
    match we last negotiated rather than that the wire carries a decayed value.
    """
    from tests.conftest import decayed_peak

    client = _RecordingClient()
    session = _session(Role.THIEF, minimal_config, client=client)
    session.runtime.brain = brain_class("thief")()
    await send_turn(session, None)
    peak = max(client.calls[0]["smell_grid"].values())
    assert peak == pytest.approx(round(decayed_peak(minimal_config), 3))


class _FlakyClient(_RecordingClient):
    """Fails its first *fail_times* calls, clearing the cached session each
    time `aclose` runs — same shape as `OpponentClient` (`core/infra/
    mcp_client.py`), where a retry against an uncleared session fails
    identically to the call that broke it.
    """

    def __init__(self, fail_times: int) -> None:
        super().__init__()
        self.fail_times = fail_times
        self.attempts = 0
        self.acloses = 0

    async def call(self, name: str, payload: dict, argument: str = "payload") -> dict:
        self.attempts += 1
        if self.attempts <= self.fail_times:
            from core.infra.errors import TransportError

            raise TransportError("dropped")
        return await super().call(name, payload, argument)

    async def aclose(self) -> None:
        self.acloses += 1


@thief_only
async def test_a_transient_send_failure_is_retried_not_left_fatal(
    minimal_config: Config,
) -> None:
    """🐛 Live against yanell11, 18/08: one `ConnectError` on `receive_turn`
    ended a sub-game 26 turns in — a dropped packet, not a dead peer.
    `negotiate` and `submit_audit` both retry; a turn during active play did
    not, for no reason tied to the protocol.
    """
    client = _FlakyClient(fail_times=1)
    session = _session(Role.THIEF, minimal_config, client=client)
    session.runtime.brain = brain_class("thief")()
    await send_turn(session, None)
    assert client.attempts == 2
    assert client.acloses == 1, "the cached session must be cleared before retrying"
    assert len(client.calls) == 1


@thief_only
async def test_a_second_failure_is_also_retried_not_just_the_first(
    minimal_config: Config,
) -> None:
    """🐛 The fix above still lost the *next* sub-game: one retry on the same
    client hit the identical broken session, because nothing had cleared it.
    A peer can take longer than one retry to recover from."""
    client = _FlakyClient(fail_times=2)
    session = _session(Role.THIEF, minimal_config, client=client)
    session.runtime.brain = brain_class("thief")()
    await send_turn(session, None)
    assert client.attempts == 3
    assert client.acloses == 2
    assert len(client.calls) == 1
