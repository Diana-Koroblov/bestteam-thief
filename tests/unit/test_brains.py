"""Unit tests for the two baseline strategies (TODO 3.1, 3.2).

The two properties that matter most: a brain is **deterministic** — two peers
replay the same log and must agree — and the Thief **never walks into a dead
end**, which is the DoD's own requirement and the cheapest way to lose.
"""

from __future__ import annotations

import pytest

from core.domain.actions import Direction
from core.domain.board import Board
from core.domain.brain_base import BrainBase, Decision, Observation
from core.domain.connectivity import exit_count
from tests.paths import brain_class, needs_brain

PoliceBrain = brain_class("police")
ThiefBrain = brain_class("thief")
cop_only = needs_brain("police")
thief_only = needs_brain("thief")

BOARD = Board(grid_size=7)


def observe(position, belief=None, barriers=frozenset(), **fields) -> Observation:
    """Build an observation with a single believed opponent cell."""
    return Observation(
        board=BOARD,
        own_position=position,
        barriers=barriers,
        belief={belief: 1.0} if belief else {},
        **fields,
    )


# --- the contract -----------------------------------------------------------


def test_a_decision_cannot_move_and_place_at_once() -> None:
    """Ch. 3.4: a barrier costs the turn, so the two are mutually exclusive."""
    with pytest.raises(ValueError, match="requires forgoing movement"):
        Decision(Direction.N, barrier=(1, 1))


def test_a_barrier_with_stay_is_allowed() -> None:
    assert Decision(Direction.STAY, barrier=(1, 1)).barrier == (1, 1)


def test_the_belief_peak_breaks_ties_on_coordinates() -> None:
    """Two peers with the same belief must pick the same cell, always."""
    tied = Observation(board=BOARD, own_position=(0, 0), belief={(3, 3): 0.5, (1, 1): 0.5})
    assert tied.most_likely_opponent() == (1, 1)


def test_no_belief_means_no_target() -> None:
    assert Observation(board=BOARD, own_position=(0, 0)).most_likely_opponent() is None


def test_a_brain_must_implement_pick_move() -> None:
    with pytest.raises(TypeError):
        BrainBase()  # type: ignore[abstract]


# --- the cop baseline -------------------------------------------------------


@cop_only
def test_the_cop_steps_toward_the_believed_thief() -> None:
    decision = PoliceBrain().decide(observe((0, 0), belief=(0, 3)))
    assert decision.move is Direction.E
    assert "shortest path" in decision.reason


@cop_only
def test_the_cop_walks_a_full_shortest_path() -> None:
    """Six moves from a corner to the centre, with no wasted step."""
    brain, position = PoliceBrain(), (0, 0)
    for _ in range(6):
        move = brain.decide(observe(position, belief=(3, 3))).move
        delta = {Direction.N: (-1, 0), Direction.S: (1, 0), Direction.E: (0, 1), Direction.W: (0, -1)}
        position = (position[0] + delta[move][0], position[1] + delta[move][1])
    assert position == (3, 3)


@cop_only
def test_the_cop_routes_around_a_barrier() -> None:
    decision = PoliceBrain().decide(observe((0, 0), belief=(0, 2), barriers=frozenset({(0, 1)})))
    assert decision.move is Direction.S


@cop_only
def test_the_cop_holds_when_it_believes_nothing() -> None:
    """Wandering would spread our own scent over cells carrying no information."""
    decision = PoliceBrain().decide(observe((3, 3)))
    assert decision.move is Direction.STAY
    assert "no belief" in decision.reason


@cop_only
def test_the_cop_says_so_when_the_thief_is_unreachable() -> None:
    """Barriers are permanent, so this is a lost sub-game — the log must show it."""
    walls = frozenset({(0, 2), (1, 1), (2, 0)})
    decision = PoliceBrain().decide(observe((0, 0), belief=(6, 6), barriers=walls))
    assert decision.move is Direction.STAY
    assert "not reachable" in decision.reason


@cop_only
def test_the_cop_places_no_barriers_at_baseline() -> None:
    """A self-trapping baseline would make every later A/B meaningless."""
    for target in [(0, 3), (3, 3), (6, 6)]:
        assert PoliceBrain().decide(observe((0, 0), belief=target)).barrier is None


# --- the thief baseline -----------------------------------------------------


@thief_only
def test_the_thief_moves_away_from_the_believed_cop() -> None:
    decision = ThiefBrain().decide(observe((3, 3), belief=(3, 0)))
    assert decision.move in (Direction.E, Direction.N, Direction.S)


@thief_only
def test_the_thief_refuses_a_dead_end() -> None:
    """The DoD's own requirement, and the cheapest way to lose a sub-game.

    From (1,0) the cell (0,0) is a pocket: walling (0,1) leaves it with one
    exit, the way in. Fleeing there hands the cop a capture for one barrier.
    """
    walls = frozenset({(0, 1)})
    decision = ThiefBrain().decide(observe((1, 0), belief=(6, 6), barriers=walls))
    assert exit_count((0, 0), walls, BOARD) == 1
    assert decision.move is not Direction.N


@thief_only
def test_the_thief_does_not_flee_into_a_corner() -> None:
    """**Regression, found by Diana watching a game.**

    The first version scored on raw distance, so from the centre it ran to
    (6,6) — the farthest cell from a believed cop at (0,0), and also the cell a
    cop seals with **two** barriers under M#47. It then sat there 29 turns.

    Two things had failed silently: `region_size` is 49 for *every* cell on an
    open board, so that key discriminated nothing; and the dead-end veto only
    fires at one exit, so a two-exit corner passed. `EXIT_WEIGHT` is the fix.
    """
    from core.domain.actions import DELTAS

    position = (3, 3)
    brain = ThiefBrain()
    for _ in range(12):
        move = brain.decide(observe(position, belief=(0, 0))).move
        delta = DELTAS[move]
        position = (position[0] + delta[0], position[1] + delta[1])
        assert exit_count(position, frozenset(), BOARD) > 2, f"entered {position}"


@thief_only
def test_the_thief_trades_distance_for_exits() -> None:
    """From (5,4) with the cop believed at (0,0): (5,5) is nearer than (6,4).

    Distance alone would pick the corner-ward move. The exit penalty makes the
    open cell win, which is the whole point of the constant.
    """
    decision = ThiefBrain().decide(observe((5, 4), belief=(0, 0)))
    landed = {Direction.E: (5, 5), Direction.S: (6, 4)}.get(decision.move)
    assert landed is None or exit_count(landed, frozenset(), BOARD) == 4


@thief_only
def test_the_thief_still_refuses_a_pocket_when_barriers_exist() -> None:
    """Region size decides nothing on an open board, and everything once walled."""
    walls = frozenset({(0, 2), (1, 1), (2, 0)})
    decision = ThiefBrain().decide(observe((3, 3), belief=(6, 6), barriers=walls))
    assert decision.move is not Direction.STAY


@thief_only
def test_the_thief_still_moves_when_it_believes_nothing() -> None:
    decision = ThiefBrain().decide(observe((3, 3)))
    assert "keeping room" in decision.reason


@thief_only
def test_the_thief_never_places_a_barrier() -> None:
    """Only the cop may (Ch. 3.4). A thief-side placement would be refused anyway."""
    assert ThiefBrain().decide(observe((3, 3), belief=(0, 0))).barrier is None


# --- determinism ------------------------------------------------------------


@pytest.mark.parametrize("role", ["police", "thief"])
def test_the_same_observation_always_yields_the_same_decision(role: str) -> None:
    """Without this, a replay diverges and the log cannot be verified."""
    made = brain_class(role)
    if made is None:
        pytest.skip(f"the {role!r} package is not published to this repository")
    view = observe((3, 3), belief=(1, 1), barriers=frozenset({(2, 2), (4, 4)}))
    decisions = {made().decide(view).move for _ in range(25)}
    assert len(decisions) == 1
