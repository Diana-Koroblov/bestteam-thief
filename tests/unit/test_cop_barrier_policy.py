"""Whether to build a wall, and which (TODO 8.1.2, 8.1.4-8.1.7, 8.1.12).

A barrier is the only irreversible act in the game, so the refusals get more
tests than the preferences. Every board here is drawn by hand: a placement rule
that "looked fine in a self-play batch" is not evidence, because the batch never
reached the position where it loses the sub-game.
"""

from __future__ import annotations

from dataclasses import replace

from core.domain.board import Board
from core.domain.brain_base import Observation
from core.domain.cuts import region_has_cycle
from police.barrier_policy import (
    best_barrier,
    candidates,
    cut_bonus,
    placement_value,
    rejection_for,
)
from police.evaluation import CAPTURE_VALUE, CopWeights
from police.phases import PhaseSettings

BOARD = Board(grid_size=7)
WEIGHTS = CopWeights()
SETTINGS = PhaseSettings()

# A corridor down column 0, walled off along column 1. The only way from the
# bottom of the board to (0,0) runs through (2,0).
CORRIDOR = frozenset({(0, 1), (1, 1), (2, 1)})

# The 3x3 block minus its centre: the smallest region with a cycle in it.
RING = frozenset(
    cell for cell in BOARD.cells() if cell not in {(r, c) for r in range(3) for c in range(3)}
) | {(1, 1)}


def observe(own, belief, barriers=frozenset(), remaining=14) -> Observation:
    """Build one Cop's view."""
    return Observation(
        board=BOARD, own_position=own, barriers=barriers, step=5,
        barriers_remaining=remaining, belief=belief,
    )


# --- what may be walled at all ---------------------------------------------


def test_only_our_own_cell_and_its_neighbours_are_candidates() -> None:
    """Ch. 3.4. The Cop cannot cut at a distance — it must walk to every wall,
    which is what makes the three-phase plan necessary rather than decorative."""
    assert set(candidates(observe((3, 3), {}))) == {(3, 3), (2, 3), (4, 3), (3, 2), (3, 4)}


def test_the_board_edge_and_existing_walls_remove_candidates() -> None:
    """Off-board is not placeable and neither is a cell already walled."""
    assert set(candidates(observe((0, 0), {}, frozenset({(0, 1)})))) == {(0, 0), (1, 0)}


# --- 8.1.12 no wall while the belief is diffuse -----------------------------


def test_a_diffuse_belief_refuses_every_placement() -> None:
    """**A1.15.** The phase machine already holds us in HERD here; this is a
    second, independent guard, and permanence earns the redundancy."""
    uniform = dict.fromkeys(BOARD.cells(), 1.0 / 49)
    view = observe((3, 3), uniform)
    assert "diffuse" in rejection_for((3, 4), view, SETTINGS)
    assert best_barrier(view, WEIGHTS, SETTINGS, 2) is None


def test_a_spent_quota_refuses_every_placement() -> None:
    """Said plainly rather than discovered as a rejected placement mid-turn."""
    view = observe((1, 0), {(0, 0): 1.0}, CORRIDOR, remaining=0)
    assert "quota" in rejection_for((1, 0), view, SETTINGS)


# --- 8.1.2 and 8.1.4 the wall goes behind you, never between ----------------


def test_a_wall_that_strands_the_thief_is_refused() -> None:
    """**A1.5, and the whole reason this module filters before it scores.**
    Walling (2,0) closes the corridor with the believed Thief on the far side.
    The board would look tidier and the sub-game would be lost — barriers are
    permanent, and no play afterwards recovers it."""
    view = observe((3, 0), {(0, 0): 1.0}, CORRIDOR)
    assert "strand" in rejection_for((2, 0), view, SETTINGS)


def test_the_same_wall_behind_us_is_allowed() -> None:
    """The rule is separation, not confinement (§3.2). One cell the other side
    of the Cop, everything else identical, and it is fine."""
    view = observe((3, 0), {(0, 0): 1.0}, CORRIDOR)
    assert rejection_for((4, 0), view, SETTINGS) == ""


def test_a_wall_that_captures_is_not_a_wall_that_strands() -> None:
    """🐛 **The separation guard used to refuse the winning move.**

    Sealing the Thief's last exit puts it outside our component by construction,
    so a guard reading the belief as it stood *before* the placement saw the
    worst thing on the board and vetoed a capture. Stranding is now judged on the
    mass that survives: mass this wall captures is not mass we failed to reach.
    """
    view = observe((1, 1), {(0, 0): 1.0}, frozenset({(0, 1)}))
    assert rejection_for((1, 0), view, SETTINGS) == ""
    assert placement_value((1, 0), view, WEIGHTS, 2) == CAPTURE_VALUE


def test_a_wall_that_captures_nothing_and_strands_everything_is_still_refused() -> None:
    """The fix must not have turned the guard off. One cell further along the
    corridor captures nobody and walls the whole posterior away."""
    view = observe((3, 0), {(0, 0): 1.0}, CORRIDOR)
    assert "strand" in rejection_for((2, 0), view, SETTINGS)


def test_sealing_ourselves_in_with_the_thief_is_allowed() -> None:
    """Co-confinement is a **win**: we sweep the pocket and it has nowhere to
    go. A mobility guard would have refused the winning move."""
    view = observe((1, 1), {(0, 0): 1.0}, frozenset({(0, 2), (2, 0), (2, 2)}))
    assert rejection_for((1, 2), view, SETTINGS) == ""


def test_isolation_discounts_a_wall_that_would_leave_a_tiny_pocket() -> None:
    """🐛 18/08, live against the advanced Thief: this exact shape — three
    walls along a column, the Cop standing at the one remaining door to a
    2-cell pocket the belief says the Thief is almost certainly through —
    is what the Cop built while chasing it into (0,6)/(1,6). `rejection_for`
    does not refuse the fourth wall: almost all believed mass sits inside the
    pocket it seals, so nothing reads as *stranded* by A1.5's own test. Only
    the placement's VALUE should reflect that the Cop is one wall from a dead
    end if that 97% turns out to be wrong — which is exactly what it was."""
    neck = frozenset({(0, 5), (1, 5), (2, 5)})
    view = observe((2, 6), {(1, 6): 0.97, (6, 6): 0.03}, neck)
    assert rejection_for((2, 6), view, SETTINGS) == ""
    isolation_aware = placement_value((2, 6), view, WEIGHTS, 2)
    blind = placement_value((2, 6), view, replace(WEIGHTS, isolation=0.0), 2)
    assert isolation_aware < blind


# --- futile and unfinishable walls ------------------------------------------


def test_a_wall_that_changes_nothing_is_refused() -> None:
    """It cost a turn and bought neither an exit nor a cell of the Thief's
    reach. The Thief got a free step for it."""
    view = observe((6, 6), {(0, 0): 1.0})
    assert "neither" in rejection_for((6, 5), view, SETTINGS)


def test_a_cut_we_cannot_finish_is_refused() -> None:
    """**A1.10, TODO 8.1.7.** Sealing a cell means blocking every exit it has,
    so its exit count after this wall is a lower bound on the walls still
    needed. A seal that leaks is worse than no seal: we paid the turns and the
    Thief walked out through the gap."""
    view = observe((3, 5), {(3, 3): 1.0}, remaining=2)
    assert "more walls" in rejection_for((3, 4), view, SETTINGS)


def test_the_same_cut_is_allowed_with_the_quota_to_finish_it() -> None:
    """Confirms the refusal above is about the quota and not the geometry."""
    assert rejection_for((3, 4), observe((3, 5), {(3, 3): 1.0}, remaining=9), SETTINGS) == ""


# --- 8.1.5 and 8.1.6 what makes one wall better than another ----------------


def test_a_corner_placement_outscores_open_ground() -> None:
    """**A1.8.** Board edges are wall we did not pay for, so a placement tucked
    against one continues a cut already anchored."""
    view = observe((0, 1), {})
    assert cut_bonus((0, 0), view, WEIGHTS) > cut_bonus((3, 3), observe((3, 3), {}), WEIGHTS)


def test_breaking_a_cycle_is_worth_more_than_the_cell_it_removes() -> None:
    """**8.1.6.** A region the Thief can circle is a region it survives in for
    all 35 steps, however small. Cycle elimination is the objective; cell count
    is only a proxy for it."""
    view = observe((0, 2), {(0, 0): 1.0}, RING)
    assert region_has_cycle((0, 0), RING, BOARD) is True
    assert region_has_cycle((0, 0), RING | {(0, 1)}, BOARD) is False
    assert cut_bonus((0, 1), view, WEIGHTS) > WEIGHTS.cycle


# --- the endgame ------------------------------------------------------------


def test_walling_our_own_cell_can_capture() -> None:
    """**M#47.** A barrier blocks entry, not exit, so the Cop may wall the cell
    it stands on — and when that cell is the Thief's last exit, it wins."""
    view = observe((1, 0), {(0, 0): 1.0}, frozenset({(0, 1)}))
    assert placement_value((1, 0), view, WEIGHTS, 2) == CAPTURE_VALUE
    assert best_barrier(view, WEIGHTS, SETTINGS, 2)[0] == (1, 0)


def test_walling_the_thiefs_own_cell_captures() -> None:
    """**M#46.** The other capture rule, and the Cop placing against a belief
    cannot tell which of the two fired."""
    view = observe((0, 1), {(0, 0): 1.0}, frozenset({(1, 0)}))
    assert placement_value((0, 0), view, WEIGHTS, 2) == CAPTURE_VALUE


def test_partial_belief_gives_a_partial_capture_value() -> None:
    """The Cop plays a distribution. Half the mass on the sealed cell is worth
    half the capture, and the rest is worth the position it leaves."""
    view = observe((1, 0), {(0, 0): 0.5, (5, 5): 0.5}, frozenset({(0, 1)}))
    value = placement_value((1, 0), view, WEIGHTS, 2)
    assert 0.0 < value < CAPTURE_VALUE
    assert value > CAPTURE_VALUE * 0.4


def test_best_barrier_returns_none_when_everything_is_refused() -> None:
    """The common case and the safe one: on a turn where every available wall is
    a bad wall, not building beats building the least bad."""
    assert best_barrier(observe((6, 6), {(0, 0): 1.0}), WEIGHTS, SETTINGS, 2) is None


def test_the_reason_names_the_cell_and_what_it_achieves() -> None:
    """Carried into the match log, so a replay explains the turn (TODO 7.5.1)."""
    view = observe((1, 0), {(0, 0): 1.0}, frozenset({(0, 1)}))
    _, _, reason = best_barrier(view, WEIGHTS, SETTINGS, 2)
    assert "(1, 0)" in reason and "0 exits" in reason
