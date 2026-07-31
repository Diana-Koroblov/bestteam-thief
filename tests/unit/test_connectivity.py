"""Unit tests for connectivity — the cop's self-trap guard.

The distinction these tests exist to protect: **separation is the failure,
confinement is the win.** A small region shared with the thief is a winning
position; a large region the cop cannot enter is a lost one.
"""

from __future__ import annotations

import pytest

from core.domain.board import Board
from core.domain.connectivity import are_connected, exit_count, reachable, region_size

BOARD = Board(grid_size=7)
EMPTY: frozenset[tuple[int, int]] = frozenset()

# Rows 0 and 2 fully walled: the cop on row 1 is sealed into a 7-cell corridor
# and the thief has the other 28 cells. This is the demo's scenario 2, and it is
# a guaranteed loss for the cop.
CORRIDOR = frozenset({(0, c) for c in range(7)} | {(2, c) for c in range(7)})


def test_an_empty_board_is_one_region() -> None:
    assert len(reachable((0, 0), EMPTY, BOARD)) == 49


def test_barriers_are_excluded_from_the_region() -> None:
    barriers = frozenset({(0, 1), (1, 0)})
    region = reachable((3, 3), barriers, BOARD)
    assert len(region) == 46
    assert barriers.isdisjoint(region)


def test_an_agent_can_always_leave_a_cell_it_stands_on() -> None:
    """A barrier blocks entry, not exit — the cop may wall its own cell."""
    region = reachable((3, 3), frozenset({(3, 3)}), BOARD)
    assert (3, 3) in region
    assert len(region) == 49


def test_a_diagonal_chain_severs_a_corner() -> None:
    """Diagonal chains are the minimum vertex cut on a 4-connected grid."""
    chain = frozenset({(0, 2), (1, 1), (2, 0)})
    assert region_size((0, 0), chain, BOARD) == 3
    assert not are_connected((0, 0), (6, 6), chain, BOARD)


def test_three_barriers_cut_off_a_corner_that_four_neighbours_would_not() -> None:
    """A cut needs fewer walls than enclosing a cell. This is why shape beats quota."""
    chain = frozenset({(0, 2), (1, 1), (2, 0)})
    assert len(chain) == 3
    assert region_size((6, 6), chain, BOARD) == 49 - 3 - 3


# --- the self-trap, which is what scenario 2 of the demo actually built -----


def test_the_corridor_wall_seals_the_cop_away_from_the_thief() -> None:
    """The losing move: 14 barriers, and the cop can never reach the thief again."""
    cop, thief = (1, 0), (5, 5)
    assert region_size(cop, CORRIDOR, BOARD) == 7
    assert region_size(thief, CORRIDOR, BOARD) == 28
    assert not are_connected(cop, thief, CORRIDOR, BOARD)


def test_confinement_together_is_the_opposite_of_separation() -> None:
    """A small shared region is a win, not a trap. Same size, opposite value."""
    pocket = frozenset({(0, 2), (1, 2), (2, 0), (2, 1), (2, 2)})
    cop, thief = (0, 0), (1, 1)
    assert region_size(cop, pocket, BOARD) == 4
    assert are_connected(cop, thief, pocket, BOARD)


def test_connectivity_is_symmetric() -> None:
    assert are_connected((0, 0), (6, 6), EMPTY, BOARD)
    assert are_connected((6, 6), (0, 0), EMPTY, BOARD)
    assert not are_connected((1, 0), (5, 5), CORRIDOR, BOARD)
    assert not are_connected((5, 5), (1, 0), CORRIDOR, BOARD)


def test_a_cell_is_connected_to_itself() -> None:
    assert are_connected((3, 3), (3, 3), CORRIDOR, BOARD)


# --- exit counting, the endgame -------------------------------------------


@pytest.mark.parametrize(
    "pos,expected",
    [((3, 3), 4), ((0, 3), 3), ((0, 0), 2), ((6, 6), 2)],
)
def test_exit_count_on_an_open_board(pos: tuple[int, int], expected: int) -> None:
    assert exit_count(pos, EMPTY, BOARD) == expected


def test_exit_count_reaches_one_before_a_capture_is_possible() -> None:
    """At 1, a single barrier on that exit captures the thief (M#47)."""
    walls = frozenset({(2, 3), (4, 3), (3, 2)})
    assert exit_count((3, 3), walls, BOARD) == 1


def test_exit_count_zero_means_already_captured() -> None:
    walls = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    assert exit_count((3, 3), walls, BOARD) == 0


def test_a_cornered_thief_starts_at_two_exits() -> None:
    """Which is why corners are cheap to seal — two barriers, not four."""
    assert exit_count((0, 0), EMPTY, BOARD) == 2
    assert exit_count((0, 0), frozenset({(0, 1)}), BOARD) == 1


def test_exit_count_does_not_measure_freedom_on_its_own() -> None:
    """Four exits inside a tiny pocket is not freedom.

    A 3x3 room sealed off with 7 barriers. The centre still reports the maximum
    four exits, yet the whole region is nine cells. ``region_size`` is the
    honest measure of how much room the thief actually has, and this is why the
    cop's evaluation uses both.
    """
    room = frozenset({(3, 0), (3, 1), (3, 2), (3, 3), (0, 3), (1, 3), (2, 3)})
    assert exit_count((1, 1), room, BOARD) == 4
    assert region_size((1, 1), room, BOARD) == 9
