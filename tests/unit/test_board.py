"""Unit tests for the board geometry (PRD 1 §3.1, T1.18).

The guarantees: the grid size genuinely comes from config, an edge and a wall
are indistinguishable to callers, and the coordinate convention is pinned.
"""

from __future__ import annotations

import pytest

from core.domain.actions import Direction
from core.domain.board import Board

EMPTY: frozenset[tuple[int, int]] = frozenset()


def test_default_board_is_seven_by_seven() -> None:
    board = Board(grid_size=7)
    assert board.last_index == 6
    assert len(list(board.cells())) == 49


@pytest.mark.parametrize("size", [7, 9, 10, 15])
def test_the_engine_works_at_any_legal_size(size: int) -> None:
    """T1.18: no hardcoded 7 anywhere. grid_size is an Appendix F minimum."""
    board = Board(grid_size=size)
    assert board.in_bounds((size - 1, size - 1))
    assert not board.in_bounds((size, size - 1))
    assert len(list(board.cells())) == size * size


@pytest.mark.parametrize("size", [0, 1, 5, 6])
def test_a_board_below_the_minimum_is_refused(size: int) -> None:
    """M#12: minimums may be raised by agreement, never lowered."""
    with pytest.raises(ValueError, match="below the Appendix F minimum"):
        Board(grid_size=size)


@pytest.mark.parametrize(
    "pos,expected",
    [((0, 0), True), ((6, 6), True), ((3, 3), True), ((-1, 0), False), ((0, 7), False)],
)
def test_in_bounds(pos: tuple[int, int], expected: bool) -> None:
    assert Board(grid_size=7).in_bounds(pos) is expected


def test_a_non_zero_origin_index_shifts_the_whole_board() -> None:
    """axis_start_index is negotiable, so 1-based counting must work."""
    board = Board(grid_size=7, origin_index=1)
    assert not board.in_bounds((0, 0))
    assert board.in_bounds((1, 1))
    assert board.in_bounds((7, 7))
    assert not board.in_bounds((8, 8))


def test_an_edge_and_a_wall_are_both_impassable() -> None:
    """Treating them alike is what makes the corner case of M#47 disappear."""
    board = Board(grid_size=7)
    barriers = frozenset({(3, 3)})
    assert not board.is_passable((3, 3), barriers)  # wall
    assert not board.is_passable((-1, 3), barriers)  # edge
    assert board.is_passable((3, 4), barriers)


def test_neighbours_are_the_four_orthogonal_cells() -> None:
    board = Board(grid_size=7)
    found = dict(board.neighbours((3, 3)))
    assert found == {
        Direction.N: (2, 3),
        Direction.S: (4, 3),
        Direction.E: (3, 4),
        Direction.W: (3, 2),
    }


def test_neighbours_are_yielded_even_when_off_board() -> None:
    """"Which neighbours exist" and "which are reachable" are different questions."""
    found = dict(Board(grid_size=7).neighbours((0, 0)))
    assert found[Direction.N] == (-1, 0)
    assert found[Direction.W] == (0, -1)
    assert len(found) == 4


def test_north_decreases_the_row_index() -> None:
    """C-010: origin top-left, positions are (row, col), so N goes up."""
    board = Board(grid_size=7)
    assert dict(board.neighbours((3, 3)))[Direction.N] == (2, 3)
    assert dict(board.neighbours((3, 3)))[Direction.E] == (3, 4)


def test_cells_covers_the_grid_exactly_once() -> None:
    cells = list(Board(grid_size=7).cells())
    assert len(cells) == len(set(cells)) == 49
    assert cells[0] == (0, 0)
    assert cells[-1] == (6, 6)
