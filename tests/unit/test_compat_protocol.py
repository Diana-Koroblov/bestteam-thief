"""Unit tests for the reference-protocol compatibility layer (C-019).

The point of every test here is interoperability with code we did not write and
cannot change. So the assertions are deliberately about *their* rules, not ours:
the hash formula is recomputed independently rather than compared to our own
helper, and the tool signatures are asserted by name because MCP binds
arguments by name.
"""

from __future__ import annotations

import hashlib
import inspect
import json

import pytest

from core.compat import sealing
from core.compat.exchange import field_of, grid_of, sealed_payload, synthetic_reveal
from core.compat.mailbox import REFERENCE_TOOLS, Inboxes, build_reference_tools
from core.compat.wire import TurnMessage, terms_diff, terms_from_config
from core.crypto import canonical as native
from core.protocol.schemas import Role
from core.shared.config_manager import load_config
from tests.paths import PRESENT_ROLES, role_dir

PAYLOAD = {"step": 3, "move": "N", "position": [1, 2]}
NONCE = "deadbeefdeadbeefdeadbeefdeadbeef"


def _reference_commit(payload: dict, nonce: str) -> str:
    """Recompute their digest from their published formula, independently."""
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(f"{text}|{nonce}".encode()).hexdigest()


def test_our_commit_matches_the_reference_formula_exactly() -> None:
    """The whole layer is worthless if this one line disagrees."""
    assert sealing.commit_of(PAYLOAD, NONCE) == _reference_commit(PAYLOAD, NONCE)


def test_the_reference_formula_is_not_our_native_one() -> None:
    """Guards the drift `sealing`'s docstring warns about.

    If these ever coincide, one of the two protocols is hashing under the
    other's rule and an audit will report forgery against an honest peer.
    """
    ours = native.digest({**PAYLOAD, "nonce": NONCE})
    assert sealing.commit_of(PAYLOAD, NONCE) != ours


def test_a_sealed_record_verifies_and_a_tampered_one_does_not() -> None:
    sealed = sealing.seal(PAYLOAD)
    assert sealing.verify(PAYLOAD, sealed["nonce"], sealed["commit"])
    assert not sealing.verify({**PAYLOAD, "move": "S"}, sealed["nonce"], sealed["commit"])


def test_audit_passes_a_clean_log_and_names_the_forged_step() -> None:
    clean = {"payload": PAYLOAD, **sealing.seal(PAYLOAD)}
    forged = {"payload": {"step": 9, "move": "W"}, **sealing.seal(PAYLOAD)}
    assert sealing.audit_records([clean])["passed"]
    verdict = sealing.audit_records([clean, forged])
    assert not verdict["passed"]
    assert verdict["failed_steps"] == [9]
    assert verdict["verified_steps"] == 1


def test_a_record_missing_its_nonce_counts_as_forged_not_skipped() -> None:
    """An unverifiable step is treated as forgery (M#19)."""
    verdict = sealing.audit_records([{"payload": PAYLOAD, "commit": "abc"}])
    assert not verdict["passed"]
    assert verdict["failed_steps"] == [3]


def test_a_turn_message_survives_the_wire_unchanged() -> None:
    message = TurnMessage(
        step=2, sender="cop", hint="north", smell_grid={"1,1": 0.9},
        commit="x" * 64, timestamp="2026-08-13T00:00:00+00:00",
        barrier_placed=[3, 4],
    )
    assert TurnMessage.from_dict(message.to_dict()) == message


def test_an_unknown_field_is_dropped_rather_than_refused() -> None:
    """Their format has grown a field before; it will again."""
    data = {"step": 1, "sender": "thief", "hint": "", "smell_grid": {},
            "commit": "c", "timestamp": "t", "invented_later": True}
    assert TurnMessage.from_dict(data).step == 1


def test_a_turn_message_without_a_commit_is_refused() -> None:
    with pytest.raises(ValueError, match="commit"):
        TurnMessage.from_dict({"step": 1, "sender": "thief"})


def test_a_scent_field_round_trips_through_their_grid_format() -> None:
    field = {(0, 1): 0.62, (2, 3): 0.9}
    assert field_of(grid_of(field)) == field
    assert grid_of(field) == {"0,1": 0.62, "2,3": 0.9}


def test_a_malformed_scent_cell_is_dropped_not_raised_on() -> None:
    """Unsealed, from a stranger, mid-match: a typo must not cost the game."""
    assert field_of({"nonsense": 0.5, "1,1": 0.9}) == {(1, 1): 0.9}


def test_their_turn_becomes_a_reveal_our_own_filter_can_read() -> None:
    message = TurnMessage(
        step=4, sender="thief", hint="I am east", smell_grid={"2,2": 0.9},
        commit="c", timestamp="t",
    )
    reveal = synthetic_reveal(message, Role.THIEF)
    assert reveal.hint == "I am east"
    assert reveal.scent == ((2, 2, 0.9),)
    # Never disclosed under this protocol, and nothing may pretend otherwise.
    assert reveal.move == ""


def test_the_four_tools_are_named_and_shaped_the_way_their_client_calls_them() -> None:
    """MCP binds by name: `message` for three, `payload` for the audit."""
    tools = build_reference_tools(Inboxes())
    assert tuple(sorted(tools)) == tuple(sorted(REFERENCE_TOOLS))
    for name, expected in (
        ("negotiate", "message"), ("receive_turn", "message"),
        ("receive_control", "message"), ("submit_audit", "payload"),
    ):
        assert list(inspect.signature(tools[name]).parameters) == [expected]


def test_each_tool_stores_its_message_and_answers_ok() -> None:
    inboxes = Inboxes()
    tools = build_reference_tools(inboxes)
    assert tools["receive_turn"]({"step": 1}) == {"ok": True}
    assert inboxes.turns.get_nowait() == {"step": 1}
    tools["negotiate"]({"terms": {}})
    assert inboxes.agreements.get_nowait() == {"terms": {}}


def test_submit_audit_routes_a_real_reveal_to_the_audit_inbox() -> None:
    inboxes = Inboxes()
    build_reference_tools(inboxes)["submit_audit"]({"records": [{"step": 1}]})
    assert inboxes.audits.get_nowait() == {"records": [{"step": 1}]}
    assert inboxes.consensus.empty()


def test_submit_audit_routes_a_consensus_envelope_apart_from_reveals() -> None:
    """🐛 The two must never share a queue: a consensus envelope carries no
    records at all, and reading it as that sub-game's own reveal would corrupt
    whichever one happened to be read first (yanell11, 22/08)."""
    inboxes = Inboxes()
    envelope = {"sender": "thief", "records": [], "result_claim": "series_consensus",
                "consensus_sha": "a" * 64}
    build_reference_tools(inboxes)["submit_audit"](envelope)
    assert inboxes.consensus.get_nowait() == envelope
    assert inboxes.audits.empty()


def test_draining_clears_turns_but_leaves_agreements() -> None:
    inboxes = Inboxes()
    inboxes.turns.put({"step": 1})
    inboxes.agreements.put({"terms": {}})
    inboxes.drain()
    assert inboxes.turns.empty()
    assert not inboxes.agreements.empty()


def test_draining_between_sub_games_does_not_clear_the_held_agreements() -> None:
    """`drain` runs at every sub-game boundary, which is exactly when a held
    agreement is one boundary away from being needed. Clearing it there would
    undo the fix in `turn_wait` without touching that file."""
    inboxes = Inboxes()
    inboxes.held[2] = {"terms": {}}
    inboxes.drain()
    assert inboxes.held == {2: {"terms": {}}}


def test_our_terms_carry_the_values_we_actually_signed() -> None:
    config = load_config(role_dir(PRESENT_ROLES[0]))
    terms = terms_from_config(config)
    assert terms["board_size"] == config.require("board_and_agents.grid_size")
    assert terms["max_steps"] == config.require("movement_and_barriers.max_moves")
    assert terms["thief_start"] == list(config.require("board_and_agents.thief_start"))
    # Absent from our game.json, so it must still resolve or their peer refuses.
    assert terms["min_center_intensity"] is not None


def test_a_terms_mismatch_names_the_key_instead_of_dumping_both_dicts() -> None:
    ours = {"board_size": 7, "max_steps": 35}
    theirs = {"board_size": 10, "max_steps": 35}
    assert terms_diff(ours, ours) == []
    assert terms_diff(ours, theirs) == ["board_size: ours=7 theirs=10"]


def test_the_sealed_payload_describes_itself() -> None:
    """Self-describing is what lets a stranger audit us with no shared schema."""

    class _State:
        barriers = frozenset({(1, 1)})
        step = 5

    payload = sealed_payload(_State(), (2, 3), 7, "N", "truth", "hello")
    assert payload["position"] == [2, 3]
    assert payload["step"] == 5
    assert payload["move"] == "MOVE:N"
    assert payload["verdict"] == "moved"
    assert "grid=7x7" in payload["state"]
    # Everything needed to re-verify travels together, so an opponent that has
    # never seen our schema can still check it.
    sealed = sealing.seal(payload)
    assert sealing.verify(payload, sealed["nonce"], sealed["commit"])
