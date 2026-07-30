"""Legal move resolution — a pure function of (position, direction, barriers).

There is no referee in this game. Physics is enforced by each peer independently
against a config both loaded byte-identically (M#11), so this module must be
deterministic: same inputs, same output, on both machines, every time. No
randomness, no clock, no I/O.

``resolve_move`` raises rather than returning a fallback. A rejected move is a
technical loss for whoever sent it (M#13), which is information we need loudly
and immediately — silently substituting STAY would hide an opponent's illegal
move and cost us the point we were owed.
"""

from __future__ import annotations

from core.domain.actions import DELTAS, Direction
from core.domain.board import Board, Position

__all__ = ["IllegalMoveError", "resolve_move", "get_legal_moves", "is_immobilised"]


class IllegalMoveError(ValueError):
    """A move was rejected by the physics rules.

    Raised for a move off the board or into a barrier. Diagonals cannot reach
    this point: they do not exist in ``Direction`` at all, so they fail earlier
    at ``parse_direction``.
    """


def resolve_move(
    pos: Position,
    direction: Direction,
    barriers: frozenset[Position],
    board: Board,
) -> Position:
    """Return the position reached by applying *direction* to *pos*.

    Args:
        pos: The agent's current cell.
        direction: One of the five legal actions.
        barriers: Cells permanently blocked for both players.
        board: Supplies the bounds.

    Returns:
        The resulting position. ``STAY`` returns *pos* unchanged.

    Raises:
        IllegalMoveError: The destination is off the board or barriered.
    """
    d_row, d_col = DELTAS[direction]
    destination = (pos[0] + d_row, pos[1] + d_col)

    if not board.in_bounds(destination):
        raise IllegalMoveError(
            f"{direction.value} from {pos} leaves the {board.grid_size}x{board.grid_size} board"
        )
    if destination in barriers:
        raise IllegalMoveError(f"{direction.value} from {pos} runs into the barrier at {destination}")
    return destination


def get_legal_moves(
    pos: Position,
    barriers: frozenset[Position],
    board: Board,
) -> list[tuple[Direction, Position]]:
    """Return every legal action from *pos*, paired with where it leads.

    ``STAY`` is always present and always first. It is legal from every cell —
    an agent boxed in on all four sides can still stand still, which is exactly
    why "has no legal move" is *not* the test for the immobilised-thief rule.
    See ``is_immobilised`` and CONTRADICTIONS C-006b.

    The list is deterministic in order (STAY, then N, S, E, W as they appear in
    ``DELTAS``) so that a search tie-broken by iteration order resolves the same
    way on both peers.
    """
    moves: list[tuple[Direction, Position]] = [(Direction.STAY, pos)]
    moves.extend(
        (direction, destination)
        for direction, destination in board.neighbours(pos)
        if board.is_passable(destination, barriers)
    )
    return moves


def is_immobilised(
    pos: Position,
    barriers: frozenset[Position],
    board: Board,
) -> bool:
    """Return True when all four orthogonal neighbours of *pos* are blocked.

    This is the M#47 capture test, and it is defined by **adjacency**, not by
    the absence of a legal move. STAY is always available, so an agent is never
    literally without an action; reading M#47 that way would make it
    unreachable. Our ``capture.stay_counts_as_move = false`` default encodes the
    adjacency reading, negotiated per match (CONTRADICTIONS C-006b).

    Board edges count as blocking, so a thief in a corner needs only two
    barriers rather than four. ``Board.is_passable`` already treats an edge and
    a wall identically, so that case needs no special handling here.
    """
    return not any(
        board.is_passable(destination, barriers) for _, destination in board.neighbours(pos)
    )
