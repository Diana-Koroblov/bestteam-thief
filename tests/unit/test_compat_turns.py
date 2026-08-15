"""Unit tests for the role guard, live-commit tracking, and per-sender step
counter added to core/compat/turns.py (imreeyal §3.4, §3.6, §3.10).
"""

from __future__ import annotations

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
