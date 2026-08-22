"""Unit tests for the two endgame bugs the 14/08 boundary drill caught live:
a thief that never ended its own survival, and a late audit judged as the
current sub-game's (imreeyal §0 — the answering path nobody had exercised).
"""

from __future__ import annotations

from dataclasses import replace

from core.compat import sealing
from core.compat.mailbox import Inboxes
from core.compat.session import ReferenceSession
from core.protocol.schemas import Role
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from core.shared.config_manager import Config
from tests.paths import brain_class, needs_brain

thief_only = needs_brain("thief")


def _session(role: Role, minimal_config: Config, client=None, number: int = 1) -> ReferenceSession:
    runtime = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, role))
    runtime.agreed = True
    return ReferenceSession(
        runtime=runtime, client=client, inboxes=Inboxes(), identity={}, sub_game_number=number
    )


class _SilentOpponent:
    """Accepts every push and never answers — the far side has already settled."""

    async def call(self, name: str, payload: dict, argument: str = "payload") -> dict:
        return {"ok": True}


@thief_only
async def test_the_thief_ends_its_own_survival_instead_of_waiting_out_the_watchdog(
    minimal_config: Config,
) -> None:
    """The claim rides out on our own turn; a claimant that then waits for an
    answer watchdogs into "timeout" while the opponent files "survival" — the
    same sub-game reported two contradictory ways (M#35 scores that 0-0)."""
    session = _session(Role.THIEF, minimal_config, client=_SilentOpponent())
    session.runtime.brain = brain_class("thief")()
    threshold = int(minimal_config.require("movement_and_barriers.survival_threshold"))
    state = session.orchestrator.state
    session.orchestrator.advance(replace(state, step=threshold))
    result = await session.play_sub_game()
    assert result == "survival"
    assert session.winner == "thief"


def test_collect_audit_skips_an_earlier_sub_games_late_audit(minimal_config: Config) -> None:
    """A slow peer's closing push lands after our boundary drain; judged
    against THIS sub-game's live commits it reads as forgery against an honest
    opponent (drill sub-games 3 and 5). Stamped stale audits are skipped and
    the genuine one behind them is judged instead."""
    session = _session(Role.COP, minimal_config, number=3)
    record = {"payload": {"step": 1}, **sealing.seal({"step": 1})}
    stale = {"sender": "thief", "records": [], "result_claim": "survival", "sub_game_number": 1}
    genuine = {"sender": "thief", "records": [record], "result_claim": "survival",
               "sub_game_number": 3}
    session.received[1] = record["commit"]
    session.inboxes.audits.put(stale)
    session.inboxes.audits.put(genuine)

    import asyncio

    verdict = asyncio.run(session.collect_audit(2.0))
    assert verdict["received"]
    assert verdict["passed"]
    assert verdict["verified_steps"] == 1


def test_collect_audit_still_consumes_an_unstamped_reference_audit(
    minimal_config: Config,
) -> None:
    """Any unmodified reference peer sends no sub_game_number; that is silence,
    not staleness, and must be judged normally."""
    session = _session(Role.COP, minimal_config, number=3)
    record = {"payload": {"step": 1}, **sealing.seal({"step": 1})}
    session.received[1] = record["commit"]
    session.inboxes.audits.put({"sender": "thief", "records": [record], "result_claim": "capture"})

    import asyncio

    verdict = asyncio.run(session.collect_audit(2.0))
    assert verdict["received"]
    assert verdict["passed"]


def test_our_own_audit_payload_is_stamped_with_the_sub_game(minimal_config: Config) -> None:
    session = _session(Role.COP, minimal_config, number=5)
    assert session.audit_payload()["sub_game_number"] == 5


def test_our_own_audit_payload_names_its_sender_in_the_wire_vocabulary(
    minimal_config: Config,
) -> None:
    """🐛 This sent our raw `Role.value` ("cop"), not `wire_role`'s ("police") —
    the same fix `TurnMessage.sender` already needed. A peer whose `submit_audit`
    validates the sender rejects "cop" outright, which reads as the audit never
    landing at all (yanell11, 22/08, sub-games 1 and 3)."""
    cop = _session(Role.COP, minimal_config, number=1)
    assert cop.audit_payload()["sender"] == "police"
    thief = _session(Role.THIEF, minimal_config, number=2)
    assert thief.audit_payload()["sender"] == "thief"
