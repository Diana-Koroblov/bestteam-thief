"""Expectimax over the belief (TODO 8.1.1, 8.1.11; PRD advanced §3.1).

The two properties worth asserting are that the search **takes a capture** when
one is on offer, and that it **plays the distribution rather than its peak**.
The second is what separates this from the baseline: an argmax chase commits to
one mode and pays the whole board width when it guessed wrong.
"""

from __future__ import annotations

import time

from core.domain.actions import Direction
from core.domain.board import Board
from core.domain.brain_base import Observation
from police.brain import PoliceBrain
from police.evaluation import CAPTURE_VALUE, CopWeights, evaluate
from police.search import DEFAULT_DEPTH, best_move, expectimax, options

BOARD = Board(grid_size=7)
WEIGHTS = CopWeights()


def observe(own, belief, barriers=frozenset(), step=0, remaining=14) -> Observation:
    """Build one Cop's view."""
    return Observation(
        board=BOARD,
        own_position=own,
        barriers=barriers,
        step=step,
        barriers_remaining=remaining,
        belief=belief,
    )


# --- the option set ---------------------------------------------------------


def test_stay_is_always_available_and_always_first() -> None:
    """A Cop with no legal step must still have a decision to return, and a
    stable ordering is what makes an unbroken tie resolve the same way on both
    machines replaying one log."""
    boxed = options((0, 0), frozenset({(0, 1), (1, 0)}), BOARD)
    assert boxed == [(Direction.STAY, (0, 0))]
    assert options((3, 3), frozenset(), BOARD)[0][0] is Direction.STAY


def test_walls_and_edges_remove_options() -> None:
    """Off-board and barriered are indistinguishable to a mover, deliberately."""
    assert len(options((0, 0), frozenset(), BOARD)) == 3
    assert len(options((3, 3), frozenset({(2, 3)}), BOARD)) == 4


# --- 8.1.1 the search -------------------------------------------------------


def test_depth_zero_is_the_evaluation() -> None:
    """The base case, asserted rather than assumed — every value in the tree is
    ultimately this number."""
    belief = {(0, 6): 1.0}
    assert expectimax((3, 3), belief, frozenset(), BOARD, 0, WEIGHTS) == evaluate(
        (3, 3), belief, frozenset(), BOARD, WEIGHTS
    )


def test_a_capture_on_offer_is_taken() -> None:
    """Nothing positional is worth declining a capture: 20 points against a
    survival's 5, and the sub-game ends."""
    direction, value = best_move(observe((3, 3), {(3, 4): 1.0}), WEIGHTS, 2)
    assert direction is Direction.E
    assert value >= CAPTURE_VALUE * 0.9


def test_the_last_survivor_cell_is_a_certain_capture() -> None:
    """When masking leaves no mass anywhere, the Thief was on the cell we
    stepped onto — there is nowhere else it could have been."""
    value = expectimax((0, 0), {(0, 1): 1.0}, frozenset({(1, 0), (1, 1)}), BOARD, 2, WEIGHTS)
    assert value == CAPTURE_VALUE


def test_searching_deeper_finds_a_capture_a_shallow_search_cannot_see() -> None:
    """The point of depth. A Thief two steps away is invisible to one ply."""
    belief = {(3, 5): 1.0}
    shallow = expectimax((3, 3), belief, frozenset(), BOARD, 1, WEIGHTS)
    deep = expectimax((3, 3), belief, frozenset(), BOARD, 3, WEIGHTS)
    assert deep > shallow


def test_the_search_is_deterministic() -> None:
    """Two peers replay one log and must reach the same move; a search that
    wobbled would make the match unverifiable."""
    view = observe((3, 3), {(0, 0): 0.5, (6, 6): 0.5})
    assert len({best_move(view, WEIGHTS, 2)[0] for _ in range(5)}) == 1


# --- 8.1.11 playing the distribution, not its peak --------------------------


def test_a_distant_peak_does_not_pull_the_cop_away_from_the_mass() -> None:
    """**A1.13.** Four cells at 0.25 each; the peak is only the peak because
    ties break on coordinates, and it is six steps away while the other three
    quarters of the probability sit two steps away.

    The baseline walks the whole board to the argmax. The belief-weighted search
    goes to the mass — which is the entire practical difference between playing
    a distribution and playing its peak.

    Note what this is *not* testing. There is no information to gather by
    moving: the scent field arrives whole and reads identically wherever we
    stand, so a move cannot buy an observation. The benefit of the posterior is
    that it changes which move is cheapest, and that is what is measured here.
    """
    view = observe((3, 3), {(0, 0): 0.25, (2, 5): 0.25, (3, 5): 0.25, (4, 5): 0.25})
    assert view.most_likely_opponent() == (0, 0)
    assert PoliceBrain()._pick_move(view).move is not Direction.E
    assert best_move(view, WEIGHTS, DEFAULT_DEPTH)[0] is Direction.E


def test_a_confident_posterior_reverts_to_direct_pursuit() -> None:
    """**A1.14.** With the mass in one place the weighted objective and the
    argmax objective are the same objective, so the two brains agree."""
    view = observe((3, 3), {(3, 0): 0.94, (6, 6): 0.06})
    assert PoliceBrain()._pick_move(view).move is Direction.W
    assert best_move(view, WEIGHTS, DEFAULT_DEPTH)[0] is Direction.W


def test_an_empty_belief_does_not_crash_the_search() -> None:
    """Turn one, before any scent has been transmitted."""
    direction, _ = best_move(observe((3, 3), {}), WEIGHTS, DEFAULT_DEPTH)
    assert direction in {d for d, _ in options((3, 3), frozenset(), BOARD)}


# --- A1.3 the deadline ------------------------------------------------------


def test_the_default_depth_finishes_far_inside_the_step_deadline() -> None:
    """30 s per step, and a peer that overruns takes a technical loss. The
    worst case for branching is an open board with a uniform belief — every move
    legal, every cell live."""
    belief = dict.fromkeys(BOARD.cells(), 1.0 / 49)
    started = time.perf_counter()
    best_move(observe((3, 3), belief), WEIGHTS, DEFAULT_DEPTH)
    assert time.perf_counter() - started < 5.0
