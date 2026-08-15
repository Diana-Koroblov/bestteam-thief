"""Unit tests for the negotiate-payload and pairing-refusal additions to
core/compat/session.py (imreeyal §3.6, §3.8, §3.11).
"""

from __future__ import annotations

from dataclasses import replace

from core.compat.mailbox import Inboxes
from core.compat.session import ReferenceSession
from core.compat.wire import TurnMessage, terms_from_config
from core.protocol.schemas import Role
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from core.shared.config_manager import Config, load_config
from tests.paths import PRESENT_ROLES, role_dir


class _StubOrchestrator:
    def __init__(self, config):
        self.config = config


class _StubRuntime:
    def __init__(self, config, role=Role.COP):
        self.orchestrator = _StubOrchestrator(config)
        self.own_role = role


def _session(role: Role = Role.COP, sub_game: int = 1) -> ReferenceSession:
    config = load_config(role_dir(PRESENT_ROLES[0]))
    return ReferenceSession(
        runtime=_StubRuntime(config, role),
        client=None,
        inboxes=Inboxes(),
        identity={"group_id": "bestteam"},
        sub_game_number=sub_game,
    )


def test_agreement_message_carries_the_new_pairing_fields() -> None:
    from core.compat.wire import SCENT_MODEL_SHA256

    session = _session(Role.COP, sub_game=3)
    message, terms = session.agreement_message()
    assert message["sub_game_number"] == 3
    assert message["role"] == "police"  # our "cop" in the reference's vocabulary
    assert message["wire_shape_sha256"]
    assert message["info_mode_sha256"]
    # Declared from the signed decay_model, never hardcoded: the hash asserts
    # the whole bundle (kernel + decay + merge), so it must follow the config.
    model = str(session.config.get("pheromones.decay_model", "multiplicative"))
    assert message["scent_model_sha256"] == SCENT_MODEL_SHA256[model]
    assert terms == terms_from_config(session.config)


def test_agreement_message_derives_game_uid_from_agreed_between() -> None:
    """On the real on-disk config, agreed_between already names imreeyal — the
    uid must be non-empty and independent of which name comes first."""
    from core.compat.league_report import game_uid

    session = _session()
    message, terms = session.agreement_message()
    theirs = next(name for name in session.config.agreed_between if name != "bestteam")
    assert message["game_uid"] == game_uid(terms, "bestteam", theirs)
    assert message["game_uid"] == game_uid(terms, theirs, "bestteam")


def test_game_uid_is_empty_when_the_opponent_is_not_yet_named() -> None:
    """A one-name agreed_between (a proposal, not yet a signed contract) must
    not crash the message it would otherwise be able to send."""
    config = load_config(role_dir(PRESENT_ROLES[0]))
    solo = replace(config, shared={**config.shared, "agreed_between": ["bestteam"]})
    session = ReferenceSession(
        runtime=_StubRuntime(solo), client=None, inboxes=Inboxes(),
        identity={"group_id": "bestteam"},
    )
    message, _ = session.agreement_message()
    assert message["game_uid"] == ""


def test_verify_pairing_refuses_a_sub_game_mismatch() -> None:
    from core.compat.pairing import pairing_warnings

    pairing_warnings({"sub_game_number": 1}, {"sub_game_number": 1})  # no raise
    try:
        pairing_warnings({"sub_game_number": 1}, {"sub_game_number": 2})
        raised = False
    except Exception:
        raised = True
    assert raised


def test_verify_pairing_refuses_a_role_collision() -> None:
    from core.compat.pairing import HandshakeError, pairing_warnings

    pairing_warnings({"role": "police"}, {"role": "thief"})  # no raise
    try:
        pairing_warnings({"role": "police"}, {"role": "police"})
    except HandshakeError as error:
        assert "role" in str(error)
    else:
        raise AssertionError("expected a role-collision refusal")


def test_verify_pairing_never_refuses_on_omission() -> None:
    """The unmodified reference peer declares neither field; a guard that
    fail-fasts on silence would forfeit that game to itself."""
    from core.compat.pairing import pairing_warnings

    assert pairing_warnings({}, {}) == []
    assert pairing_warnings({"sub_game_number": 1}, {}) == []
    assert pairing_warnings({}, {"role": "police"}) == []


async def test_play_sub_game_reports_progress_through_on_turn(minimal_config: Config) -> None:
    """Silent otherwise (Itay, 14/08): a peer watching a live sub-game saw
    nothing but transport noise until it ended. ``on_turn`` fires once per
    message received so a caller can print real progress instead."""
    runtime = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.COP))
    runtime.agreed = True
    session = ReferenceSession(runtime=runtime, client=None, inboxes=Inboxes(), identity={})
    turn = TurnMessage(
        step=1, sender="thief", hint="going quiet", smell_grid={}, commit="c" * 64,
        timestamp="2026-01-01", win_claim={"type": "survival"},
    )
    session.inboxes.turns.put(turn.to_dict())

    lines: list[str] = []
    result = await session.play_sub_game(on_turn=lines.append)

    assert result == "survival"
    assert len(lines) == 1
    assert "thief" in lines[0]
    assert "going quiet" in lines[0]
