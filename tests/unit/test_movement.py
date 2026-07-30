"""Unit tests for actions and move resolution (PRD 1 §3.2, T1.1-T1.5, T1.17).

The two guarantees worth the most here: a diagonal cannot be constructed at all,
and the same (state, action) produces the same result on two independent
instances — which is what lets two peers verify each other without a referee.
"""

from __future__ import annotations

import pytest

from core.domain.actions import DELTAS, MOVE_SET, Direction, parse_direction
from core.domain.board import Board
from core.domain.movement import (
    IllegalMoveError,
    get_legal_moves,
    is_immobilised,
    resolve_move,
)

BOARD = Board(grid_size=7)
EMPTY: frozenset[tuple[int, int]] = frozenset()
CENTRE = (3, 3)


# --- the move set is fixed (Appendix F Table 15, M#14) ----------------------


def test_exactly_five_actions_exist() -> None:
    assert len(Direction) == 5
    assert {d.value for d in Direction} == set(MOVE_SET)


def test_no_diagonal_exists_anywhere() -> None:
    """T1.3: deleted from the enum, not filtered at validation.

    C-009: the reference Board defaults to 8-direction king movement, so this
    guards against a careless port re-introducing them.
    """
    names = {d.name for d in Direction}
    assert names.isdisjoint({"NE", "NW", "SE", "SW", "NORTHEAST", "NORTH_EAST"})
    assert all(abs(dr) + abs(dc) <= 1 for dr, dc in DELTAS.values())


def test_a_direction_serialises_as_its_bare_name() -> None:
    """Otherwise a commitment hashes differently on each peer."""
    import json

    assert json.dumps({"move": Direction.N}) == '{"move": "N"}'


@pytest.mark.parametrize("value", MOVE_SET)
def test_parse_accepts_every_legal_move(value: str) -> None:
    assert parse_direction(value).value == value


@pytest.mark.parametrize("value", ["NE", "SW", "UP", "n", "", "STAY "])
def test_parse_rejects_anything_else(value: str) -> None:
    """The message quotes what arrived, so an opponent's error can be cited."""
    with pytest.raises(ValueError, match="is not a legal move"):
        parse_direction(value)


# --- resolution -------------------------------------------------------------


@pytest.mark.parametrize(
    "direction,expected",
    [
        (Direction.N, (2, 3)),
        (Direction.S, (4, 3)),
        (Direction.E, (3, 4)),
        (Direction.W, (3, 2)),
    ],
)
def test_each_direction_moves_one_cell(direction: Direction, expected: tuple[int, int]) -> None:
    """T1.1."""
    assert resolve_move(CENTRE, direction, EMPTY, BOARD) == expected


def test_stay_leaves_the_position_unchanged() -> None:
    """T1.2."""
    assert resolve_move(CENTRE, Direction.STAY, EMPTY, BOARD) == CENTRE


@pytest.mark.parametrize(
    "pos,direction",
    [((0, 3), Direction.N), ((6, 3), Direction.S), ((3, 6), Direction.E), ((3, 0), Direction.W)],
)
def test_moving_off_any_edge_raises(pos: tuple[int, int], direction: Direction) -> None:
    """T1.4."""
    with pytest.raises(IllegalMoveError, match="leaves the 7x7 board"):
        resolve_move(pos, direction, EMPTY, BOARD)


def test_moving_into_a_barrier_raises() -> None:
    """T1.5."""
    with pytest.raises(IllegalMoveError, match="barrier at"):
        resolve_move(CENTRE, Direction.N, frozenset({(2, 3)}), BOARD)


def test_stay_is_legal_even_when_fully_enclosed() -> None:
    """An agent is never literally without an action. See is_immobilised."""
    walls = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    assert resolve_move(CENTRE, Direction.STAY, walls, BOARD) == CENTRE


def _outcome(pos, direction, barriers, board):
    """Return the result of a move as a comparable value, error included."""
    try:
        return resolve_move(pos, direction, barriers, board)
    except IllegalMoveError as error:
        return ("IllegalMoveError", str(error))


def test_the_same_state_and_action_resolve_identically_on_two_instances() -> None:
    """T1.17: no referee, so both peers must compute the same result.

    Errors are compared too — a disagreement about *whether* a move is legal is
    the expensive kind, because it surfaces as an opponent rejecting a move we
    believe is fine.
    """
    first, second = Board(grid_size=7), Board(grid_size=7)
    barriers = frozenset({(2, 3), (3, 2)})
    for pos in [CENTRE, (0, 0), (6, 6), (0, 3)]:
        left = [_outcome(pos, d, barriers, first) for d in Direction]
        right = [_outcome(pos, d, barriers, second) for d in Direction]
        assert left == right, pos


# --- legal move enumeration -------------------------------------------------


def test_an_open_centre_has_five_legal_moves() -> None:
    assert len(get_legal_moves(CENTRE, EMPTY, BOARD)) == 5


def test_a_corner_has_stay_plus_two() -> None:
    moves = dict(get_legal_moves((0, 0), EMPTY, BOARD))
    assert set(moves) == {Direction.STAY, Direction.S, Direction.E}


def test_barriers_and_edges_both_remove_options() -> None:
    moves = dict(get_legal_moves((0, 3), frozenset({(0, 4)}), BOARD))
    assert set(moves) == {Direction.STAY, Direction.S, Direction.W}


def test_a_fully_enclosed_cell_leaves_only_stay() -> None:
    walls = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    assert get_legal_moves(CENTRE, walls, BOARD) == [(Direction.STAY, CENTRE)]


def test_stay_is_always_first_so_ties_break_identically() -> None:
    """Iteration order feeds search tie-breaks, which must match across peers."""
    assert get_legal_moves(CENTRE, EMPTY, BOARD)[0][0] is Direction.STAY


def test_every_returned_destination_is_actually_passable() -> None:
    barriers = frozenset({(2, 3)})
    for _, destination in get_legal_moves(CENTRE, barriers, BOARD):
        assert BOARD.is_passable(destination, barriers)


# --- immobilisation, the M#47 test -----------------------------------------


def test_an_open_agent_is_not_immobilised() -> None:
    assert not is_immobilised(CENTRE, EMPTY, BOARD)


def test_four_walls_immobilise() -> None:
    """T1.11."""
    walls = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    assert is_immobilised(CENTRE, walls, BOARD)


def test_a_corner_needs_only_two_barriers() -> None:
    """T1.12: board edges count as blocking, so corners are cheap to seal."""
    assert is_immobilised((0, 0), frozenset({(1, 0), (0, 1)}), BOARD)
    assert not is_immobilised((0, 0), frozenset({(1, 0)}), BOARD)


def test_an_edge_cell_needs_three_barriers() -> None:
    assert is_immobilised((0, 3), frozenset({(0, 2), (0, 4), (1, 3)}), BOARD)
    assert not is_immobilised((0, 3), frozenset({(0, 2), (0, 4)}), BOARD)


def test_immobilised_does_not_depend_on_stay_being_available() -> None:
    """C-006b: M#47 is adjacency, not "has no legal move". STAY always exists."""
    walls = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    assert get_legal_moves(CENTRE, walls, BOARD) != []
    assert is_immobilised(CENTRE, walls, BOARD)
