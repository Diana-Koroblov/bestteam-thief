"""Cut geometry on hand-built boards (TODO 8.1.5, 8.1.6; PRD advanced §3.3).

Every board here is drawn by hand and small enough to verify by counting, which
is the point: these functions decide whether a permanent, irreversible barrier
gets placed, so "it looked right in a self-play game" is not evidence.
"""

from __future__ import annotations

from core.domain.board import Board
from core.domain.cuts import (
    diagonal_support,
    k_step_reach,
    last_exit_of,
    region_has_cycle,
    separates,
)

BOARD = Board(grid_size=7)


# --- k-step reach: what a wall actually costs the thief ---------------------


def test_reach_grows_as_a_diamond_on_open_ground() -> None:
    """Orthogonal movement, so the k-step set is a Manhattan ball."""
    assert k_step_reach((3, 3), frozenset(), BOARD, 0) == {(3, 3)}
    assert len(k_step_reach((3, 3), frozenset(), BOARD, 1)) == 5
    assert len(k_step_reach((3, 3), frozenset(), BOARD, 2)) == 13


def test_the_board_edge_clips_the_reach() -> None:
    """A cornered thief has fewer options, and that is the whole endgame."""
    assert len(k_step_reach((0, 0), frozenset(), BOARD, 1)) == 3


def test_a_wall_removes_cells_from_the_reach() -> None:
    """**A1.7.** Placements are scored by this, not by whether they sit between
    the two agents — a wall the thief simply walks around scores zero here and
    should."""
    open_reach = k_step_reach((0, 0), frozenset(), BOARD, 3)
    walled = k_step_reach((0, 0), frozenset({(0, 1), (1, 0)}), BOARD, 3)
    assert walled == {(0, 0)}
    assert len(open_reach) > len(walled)


# --- cycles: the reason a small region can still be survivable --------------


def test_an_open_board_is_full_of_cycles() -> None:
    """One pursuer cannot corner an evader on a cyclic graph (§2.1)."""
    assert region_has_cycle((3, 3), frozenset(), BOARD) is True


def test_a_corridor_has_no_cycle() -> None:
    """A 1-wide dead end can be swept from one end; the thief cannot loop."""
    walls = frozenset({(0, 2), (1, 0), (1, 1), (1, 2)})
    assert region_has_cycle((0, 0), walls, BOARD) is False


def test_a_ring_of_cells_is_a_cycle() -> None:
    """The 3x3 block minus its centre — the smallest region worth fearing."""
    keep = {(r, c) for r in range(3) for c in range(3)} - {(1, 1)}
    walls = frozenset(cell for cell in BOARD.cells() if cell not in keep)
    assert region_has_cycle((0, 0), walls, BOARD) is True


def test_breaking_the_ring_removes_the_cycle() -> None:
    """**8.1.6.** One wall converts a region the thief circles forever into one
    it can be swept out of. That is what a barrier is *for*."""
    keep = {(r, c) for r in range(3) for c in range(3)} - {(1, 1)}
    walls = frozenset(cell for cell in BOARD.cells() if cell not in keep)
    assert region_has_cycle((0, 0), walls, BOARD) is True
    assert region_has_cycle((0, 0), walls | {(0, 1)}, BOARD) is False


def test_a_sealed_cell_has_no_cycle() -> None:
    """Degenerate but reachable: a region of one cell."""
    walls = frozenset({(0, 1), (1, 0)})
    assert region_has_cycle((0, 0), walls, BOARD) is False


# --- diagonal support: the cheapest cut on a 4-connected grid ---------------


def test_open_ground_offers_no_support() -> None:
    """Nothing to extend, so nothing to prefer."""
    assert diagonal_support((3, 3), frozenset(), BOARD) == 0


def test_the_board_edge_counts_as_support() -> None:
    """**A1.8.** The edge is wall we did not pay for. A scoring that ignored it
    would send the cop off to rebuild the border it already had."""
    assert diagonal_support((0, 0), frozenset(), BOARD) == 3


def test_an_existing_barrier_supports_its_diagonal_neighbour() -> None:
    """Corner-to-corner barriers cannot be crossed — there is no diagonal move
    to cross them with (M#14)."""
    assert diagonal_support((3, 3), frozenset({(2, 2)}), BOARD) == 1
    assert diagonal_support((3, 3), frozenset({(2, 2), (4, 4)}), BOARD) == 2


def test_an_orthogonal_neighbour_is_not_diagonal_support() -> None:
    """It blocks a step; it does not continue a cut."""
    assert diagonal_support((3, 3), frozenset({(2, 3)}), BOARD) == 0


# --- separation: the one mistake that cannot be undone ----------------------


def test_a_wall_that_cuts_the_last_link_separates() -> None:
    """Barriers are permanent, so this is a forfeited sub-game (M#8 aside — it
    is simply lost)."""
    walls = frozenset({(0, 2), (1, 1), (1, 2)})
    assert separates((0, 0), (3, 3), (1, 0), walls, BOARD) is True


def test_sealing_yourself_in_with_the_thief_is_not_separation() -> None:
    """**§3.2, the corrected guard.** Co-confinement is a *win*: the cop sweeps
    the pocket and the thief has nowhere to go. A guard that rejected small
    regions would refuse the winning move."""
    walls = frozenset({(0, 2), (1, 2), (2, 2), (2, 0), (2, 1)})
    assert separates((0, 0), (0, 1), (1, 1), walls, BOARD) is False


def test_a_wall_on_our_own_cell_never_separates_us_from_anything() -> None:
    """A barrier blocks entry, not exit, so the cop can still step off it."""
    assert separates((3, 3), (0, 0), (3, 3), frozenset(), BOARD) is False


# --- the endgame, in one call ----------------------------------------------


def test_the_last_exit_is_named() -> None:
    """**M#47.** One free neighbour means one barrier from capture, and this
    returns the cell that barrier goes on."""
    assert last_exit_of((0, 0), frozenset({(0, 1)}), BOARD) == (1, 0)


def test_several_exits_means_no_single_placement() -> None:
    """Ambiguous on purpose — both answers mean "not one wall away"."""
    assert last_exit_of((0, 0), frozenset(), BOARD) is None


def test_a_sealed_cell_has_no_last_exit() -> None:
    """Already captured; there is no placement left to make."""
    assert last_exit_of((0, 0), frozenset({(0, 1), (1, 0)}), BOARD) is None
