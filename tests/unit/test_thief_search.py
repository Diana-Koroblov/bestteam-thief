"""Expectimax for the evader (TODO 8.2.1).

The mirror of `test_cop_search.py`, with the sign flipped. Two properties carry
the file: the search must **never walk into the Cop**, and it must prefer room
over raw distance — the trade the baseline got wrong when it ran to (6,6) and sat
in the one square a Cop seals with two barriers.
"""

from __future__ import annotations

import time

from core.domain.actions import Direction
from core.domain.board import Board
from core.domain.brain_base import Observation
from thief.evaluation import CAPTURED, ThiefWeights
from thief.search import DEFAULT_DEPTH, best_move, expectimax, options, value_of
from thief.trail import TrailTracker

BOARD = Board(grid_size=7)
WEIGHTS = ThiefWeights()
QUIET = TrailTracker()


def observe(own, belief, barriers=frozenset(), walls_left=14) -> Observation:
    """Build one Thief's view."""
    return Observation(
        board=BOARD, own_position=own, barriers=barriers, step=5,
        barriers_remaining=walls_left, belief=belief,
    )


# --- the option set ---------------------------------------------------------


def test_stay_is_always_available_and_always_first() -> None:
    """A boxed-in Thief still has a decision to return, and a stable ordering is
    what makes an unbroken tie resolve identically on both machines."""
    assert options((0, 0), frozenset({(0, 1), (1, 0)}), BOARD) == [(Direction.STAY, (0, 0))]
    assert options((3, 3), frozenset(), BOARD)[0][0] is Direction.STAY


# --- never walk into the cop ------------------------------------------------


def test_stepping_onto_the_cop_is_the_sub_game_lost() -> None:
    """Certainty of capture is valued at the terminal, not merely penalised."""
    assert value_of((3, 4), {(3, 4): 1.0}, frozenset(), BOARD, 1, WEIGHTS, 14) < CAPTURED / 2


def test_the_search_walks_away_from_a_known_cop() -> None:
    """The one thing an evader must never get wrong."""
    direction, _ = best_move(observe((3, 3), {(3, 4): 1.0}), WEIGHTS, QUIET, 2)
    assert direction is not Direction.E


def test_a_boxed_in_thief_returns_a_decision_rather_than_raising() -> None:
    """A hang is worse than a loss: a peer that crashed mid-turn scores 0 for
    both teams."""
    walls = frozenset({(0, 1), (1, 0)})
    assert best_move(observe((0, 0), {(6, 6): 1.0}, walls), WEIGHTS, QUIET, 2)[0] is Direction.STAY


# --- room beats distance ----------------------------------------------------


def test_it_declines_the_corner_that_maximises_distance() -> None:
    """🐛 **The baseline's recorded failure, asserted against.** Raw distance
    sends the Thief to (6,6) — the furthest cell, and the one a Cop seals with
    two barriers under M#47. From (5,5) the search must not step into it."""
    direction, _ = best_move(observe((5, 5), {(0, 0): 1.0}), WEIGHTS, QUIET, DEFAULT_DEPTH)
    assert options((5, 5), frozenset(), BOARD)
    assert dict(options((5, 5), frozenset(), BOARD))[direction] != (6, 6)


def test_it_refuses_a_dead_end() -> None:
    """Entering a cell whose only way out is the way in hands the Cop a capture
    for the price of one barrier."""
    walls = frozenset({(2, 6), (4, 6), (3, 5)})
    direction, _ = best_move(observe((3, 4), {(0, 0): 1.0}, walls), WEIGHTS, QUIET, 2)
    assert direction is not Direction.E


def test_a_bigger_remaining_quota_makes_a_tight_cell_less_attractive() -> None:
    """**A2.8.** Fourteen walls and one wall are different games; the same board
    must be read differently under each."""
    view = observe((0, 1), {(6, 6): 1.0})
    rich = expectimax((0, 0), view.belief, view.barriers, BOARD, 1, WEIGHTS, 14)
    poor = expectimax((0, 0), view.belief, view.barriers, BOARD, 1, WEIGHTS, 0)
    assert poor > rich


# --- the trail cost sits at the root ---------------------------------------


def test_a_loud_cell_is_avoided_when_the_alternatives_are_close() -> None:
    """**A2.5.** Applied to the cell we actually step onto — see the module
    docstring for why charging it deeper would be false precision."""
    trail = TrailTracker()
    for _ in range(3):
        trail.observe((3, 3), BOARD)
    view = observe((3, 3), {})
    quiet_value = value_of((3, 3), {}, frozenset(), BOARD, 1, WEIGHTS, 14)
    loud, _ = best_move(view, WEIGHTS, trail, 1)
    assert loud is not Direction.STAY
    assert quiet_value == value_of((3, 3), {}, frozenset(), BOARD, 1, WEIGHTS, 14)


def test_a_silent_trail_changes_nothing() -> None:
    """So the trail term cannot perturb a decision before anything is emitted."""
    view = observe((3, 3), {(0, 0): 1.0})
    assert best_move(view, WEIGHTS, TrailTracker(), 2) == best_move(view, WEIGHTS, QUIET, 2)


# --- determinism and the deadline -------------------------------------------


def test_the_search_is_deterministic() -> None:
    """Two peers replay one log and must reach the same move."""
    view = observe((3, 3), {(0, 0): 0.5, (6, 6): 0.5})
    assert len({best_move(view, WEIGHTS, QUIET, 2)[0] for _ in range(5)}) == 1


def test_an_empty_belief_does_not_crash_the_search() -> None:
    """Turn one, before any scent has been transmitted."""
    direction, _ = best_move(observe((3, 3), {}), WEIGHTS, QUIET, DEFAULT_DEPTH)
    assert direction in {d for d, _ in options((3, 3), frozenset(), BOARD)}


def test_the_default_depth_finishes_far_inside_the_step_deadline() -> None:
    """30 s per step, and a peer that overruns takes a technical loss."""
    belief = dict.fromkeys(BOARD.cells(), 1.0 / 49)
    started = time.perf_counter()
    best_move(observe((3, 3), belief), WEIGHTS, QUIET, DEFAULT_DEPTH)
    assert time.perf_counter() - started < 5.0
