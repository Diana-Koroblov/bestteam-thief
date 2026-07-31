"""Unit tests for the brain seam in the runtime (TODO 3.3).

Ch. 6 places the strategy **between decoding the incoming hint and packing the
outgoing commit**. Keeping it on that seam is what stops a brain from ever
seeing the opponent's sealed move — and what makes the observation the honest
one a real match provides.
"""

from __future__ import annotations

from dataclasses import fields

import pytest

from core.protocol.schemas import Commit, Reveal, Role
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from tests.paths import brain_class, needs_brain

cop_only = needs_brain("police")


@pytest.fixture
def runtime(minimal_config) -> PeerRuntime:
    peer = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.COP))
    peer.agreed = True
    return peer



def test_the_observation_never_contains_the_opponent_position(runtime: PeerRuntime) -> None:
    """The single most important property of this seam.

    In a real match nobody knows where the opponent is. Handing the true
    position to a brain here would produce a strategy that wins in self-play
    and collapses against a real peer — and we would not find out until a
    graded match.
    """

    view = runtime.observe()
    assert "opponent" not in {f.name for f in fields(view)}
    assert view.own_position == runtime.orchestrator.own_position
    assert runtime.orchestrator.state.thief not in (view.own_position,)


def test_the_belief_covers_every_cell_we_could_be_wrong_about(runtime: PeerRuntime) -> None:
    """Uniform for now; Phase 4 replaces the contents, not the shape."""
    belief = runtime.belief()
    assert len(belief) == 48  # 49 cells minus our own
    assert abs(sum(belief.values()) - 1.0) < 1e-9


def test_the_belief_excludes_barriers(runtime: PeerRuntime) -> None:
    runtime.orchestrator.state = runtime.orchestrator.state.with_barrier((5, 5))
    assert (5, 5) not in runtime.belief()


def test_the_observation_carries_the_hints_received(runtime: PeerRuntime) -> None:
    runtime.on_commit(Commit(step=0, role=Role.THIEF, digest="d"))
    runtime.on_reveal(Reveal(step=0, role=Role.THIEF, move="N", hint="near the bridge"))
    assert runtime.observe().hints == ("near the bridge",)


def test_deciding_without_a_brain_fails_loudly(runtime: PeerRuntime) -> None:
    """Better than standing still for 35 turns and losing on the clock."""
    with pytest.raises(RuntimeError, match="no brain loaded"):
        runtime.decide()


@cop_only
def test_the_runtime_asks_the_brain_and_returns_its_decision(runtime: PeerRuntime) -> None:
    """The seam end to end: observation in, decision out."""
    runtime.brain = brain_class("police")()
    decision = runtime.decide()
    assert decision.move.value in {"N", "S", "E", "W", "STAY"}
    assert decision.reason
