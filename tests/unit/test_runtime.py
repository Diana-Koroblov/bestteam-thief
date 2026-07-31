"""Unit tests for the runtime skeleton (TODO 2.3).

The theme: **an out-of-order message is refused, loudly.** Under commit-reveal a
peer that accepted a reveal with no commit behind it would let the opponent see
our move and then choose theirs, which is the one failure the whole protocol
exists to prevent.
"""

from __future__ import annotations

import pytest

from core.domain.game_state import GameState
from core.protocol.schemas import (
    BarrierDeclaration,
    CaptureClaim,
    Commit,
    FinalReveal,
    Negotiation,
    Reveal,
    Role,
)
from core.protocol.tools import ProtocolError
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime


@pytest.fixture
def orchestrator(minimal_config) -> Orchestrator:
    return Orchestrator.from_config(minimal_config, Role.COP)


@pytest.fixture
def runtime(orchestrator: Orchestrator) -> PeerRuntime:
    peer = PeerRuntime(orchestrator=orchestrator)
    peer.agreed = True
    return peer


# --- orchestrator -----------------------------------------------------------


def test_everything_comes_from_the_signed_config(orchestrator: Orchestrator) -> None:
    """No literals: what we play is provably what was agreed."""
    assert orchestrator.board.grid_size == 7
    assert orchestrator.state.cop == (0, 0)
    assert orchestrator.state.thief == (3, 3)
    assert orchestrator.rules.survival_threshold == 35
    assert orchestrator.scoring.capture_cop == 20


def test_own_position_depends_on_the_role(minimal_config) -> None:
    """The only position a peer knows for certain is its own."""
    cop = Orchestrator.from_config(minimal_config, Role.COP)
    thief = Orchestrator.from_config(minimal_config, Role.THIEF)
    assert cop.own_position == (0, 0)
    assert thief.own_position == (3, 3)
    assert cop.is_cop and not thief.is_cop


def test_connecting_uses_the_negotiated_timeout(orchestrator: Orchestrator) -> None:
    orchestrator.connect("https://opponent.test")
    assert orchestrator.opponent.timeout_sec == 30
    assert orchestrator.opponent.base_url == "https://opponent.test"


def test_a_second_opponent_is_refused(orchestrator: Orchestrator) -> None:
    """M#4: exactly one peer. Replacing it silently would let a stranger take over."""
    orchestrator.connect("https://first.test")
    with pytest.raises(RuntimeError, match="exactly one other peer"):
        orchestrator.connect("https://second.test")


def test_advancing_keeps_the_previous_state_for_the_audit(orchestrator: Orchestrator) -> None:
    first = orchestrator.state
    orchestrator.advance(first.advanced(cop=(0, 1)))
    assert orchestrator.history == [first]
    assert orchestrator.state.cop == (0, 1)


# --- the handshake gate -----------------------------------------------------


def test_a_matching_digest_agrees_and_answers(orchestrator: Orchestrator) -> None:
    peer = PeerRuntime(orchestrator=orchestrator)
    ours = orchestrator.config.shared_digest()
    reply = peer.on_negotiate(Negotiation(step=0, role=Role.THIEF, config_digest=ours))
    assert peer.agreed
    assert reply.config_digest == ours


def test_a_digest_mismatch_refuses_the_match(orchestrator: Orchestrator) -> None:
    """M#11: two peers enforcing different physics produce an unauditable game."""
    peer = PeerRuntime(orchestrator=orchestrator)
    with pytest.raises(ProtocolError, match="config digest mismatch"):
        peer.on_negotiate(Negotiation(step=0, role=Role.THIEF, config_digest="wrong"))
    assert not peer.agreed


@pytest.mark.parametrize(
    "call",
    [
        lambda p: p.on_commit(Commit(step=0, role=Role.THIEF, digest="d")),
        lambda p: p.on_reveal(Reveal(step=0, role=Role.THIEF, move="N")),
        lambda p: p.on_barrier(BarrierDeclaration(step=0, role=Role.THIEF, cell=(1, 1))),
        lambda p: p.on_capture_claim(CaptureClaim(step=0, role=Role.THIEF, cell=(1, 1))),
        lambda p: p.on_final_reveal(FinalReveal(step=0, role=Role.THIEF, nonces={"0": "a"})),
    ],
)
def test_nothing_is_accepted_before_the_handshake(orchestrator: Orchestrator, call) -> None:
    peer = PeerRuntime(orchestrator=orchestrator)
    with pytest.raises(ProtocolError, match="before the configuration was agreed"):
        call(peer)


# --- ordering ---------------------------------------------------------------


def test_a_commit_is_stored_and_acknowledged(runtime: PeerRuntime) -> None:
    ack = runtime.on_commit(Commit(step=0, role=Role.THIEF, digest="abc"))
    assert runtime.commits == {0: "abc"}
    assert ack.acknowledged_digest == "abc"
    assert ack.role is Role.COP


def test_a_step_cannot_be_committed_twice(runtime: PeerRuntime) -> None:
    """A second attempt is a second chance to choose, after seeing something."""
    runtime.on_commit(Commit(step=0, role=Role.THIEF, digest="abc"))
    with pytest.raises(ProtocolError, match="already committed"):
        runtime.on_commit(Commit(step=0, role=Role.THIEF, digest="def"))


def test_a_reveal_without_a_commit_is_refused(runtime: PeerRuntime) -> None:
    """The attack the protocol exists to stop: see our move, then pick yours."""
    with pytest.raises(ProtocolError, match="has no matching commit"):
        runtime.on_reveal(Reveal(step=0, role=Role.THIEF, move="N"))


def test_a_reveal_after_its_commit_is_recorded(runtime: PeerRuntime) -> None:
    runtime.on_commit(Commit(step=0, role=Role.THIEF, digest="abc"))
    runtime.on_reveal(Reveal(step=0, role=Role.THIEF, move="N", hint="near the park"))
    assert runtime.reveals[0].move == "N"


def test_a_step_cannot_be_revealed_twice(runtime: PeerRuntime) -> None:
    runtime.on_commit(Commit(step=0, role=Role.THIEF, digest="abc"))
    runtime.on_reveal(Reveal(step=0, role=Role.THIEF, move="N"))
    with pytest.raises(ProtocolError, match="already revealed"):
        runtime.on_reveal(Reveal(step=0, role=Role.THIEF, move="S"))


@pytest.mark.parametrize(
    "call",
    [
        lambda p: p.on_commit(Commit(step=0, role=Role.COP, digest="d")),
        lambda p: p.on_reveal(Reveal(step=0, role=Role.COP, move="N")),
        lambda p: p.on_barrier(BarrierDeclaration(step=0, role=Role.COP, cell=(1, 1))),
    ],
)
def test_a_message_claiming_our_own_role_is_refused(runtime: PeerRuntime, call) -> None:
    """Otherwise we can be fed our own commitments and record them as theirs."""
    with pytest.raises(ProtocolError, match="which is our own"):
        call(runtime)


def test_only_the_cop_may_declare_a_barrier(minimal_config) -> None:
    """Ch. 3.4. A thief-side declaration is either a bug or an attempt."""
    peer = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.COP))
    peer.agreed = True
    with pytest.raises(ProtocolError, match="only the cop may place barriers"):
        peer.on_barrier(BarrierDeclaration(step=1, role=Role.THIEF, cell=(1, 1)))


def test_a_cop_barrier_declaration_is_recorded(minimal_config) -> None:
    peer = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.THIEF))
    peer.agreed = True
    peer.on_barrier(BarrierDeclaration(step=1, role=Role.COP, cell=(2, 3), remaining=13))
    assert peer.barriers[0].cell == (2, 3)


# --- capture claims and the final reveal -----------------------------------


def test_a_capture_claim_is_answered_from_the_rules_not_from_convenience(
    runtime: PeerRuntime,
) -> None:
    """M#21: a false denial is caught by the audit, so this is never a choice."""
    reply = runtime.on_capture_claim(CaptureClaim(step=5, role=Role.THIEF, cell=(3, 3)))
    assert reply.accepted is False
    assert "no terminal condition" in reply.reason


def test_a_genuine_capture_is_admitted(runtime: PeerRuntime) -> None:
    runtime.orchestrator.state = GameState(cop=(3, 3), thief=(3, 3), step=5)
    reply = runtime.on_capture_claim(CaptureClaim(step=5, role=Role.THIEF, cell=(3, 3)))
    assert reply.accepted is True
    assert "share cell" in reply.reason


def test_the_final_reveal_must_cover_every_committed_step(runtime: PeerRuntime) -> None:
    """An unverifiable step is treated as forgery, so a gap is refused now."""
    runtime.on_commit(Commit(step=0, role=Role.THIEF, digest="a"))
    runtime.on_commit(Commit(step=1, role=Role.THIEF, digest="b"))
    with pytest.raises(ProtocolError, match="missing nonces for step\\(s\\) 1"):
        runtime.on_final_reveal(FinalReveal(step=2, role=Role.THIEF, nonces={"0": "n0"}))


def test_a_complete_final_reveal_is_stored(runtime: PeerRuntime) -> None:
    runtime.on_commit(Commit(step=0, role=Role.THIEF, digest="a"))
    runtime.on_final_reveal(FinalReveal(step=1, role=Role.THIEF, nonces={"0": "n0"}))
    assert runtime.opponent_nonces == {"0": "n0"}


def test_the_final_reveal_happens_once(runtime: PeerRuntime) -> None:
    runtime.on_commit(Commit(step=0, role=Role.THIEF, digest="a"))
    runtime.on_final_reveal(FinalReveal(step=1, role=Role.THIEF, nonces={"0": "n0"}))
    with pytest.raises(ProtocolError, match="already received"):
        runtime.on_final_reveal(FinalReveal(step=1, role=Role.THIEF, nonces={"0": "other"}))
