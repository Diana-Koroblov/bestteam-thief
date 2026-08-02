"""Which cells can still reach which. The cop's most important self-check.

A barrier blocks both players, so every wall the Cop builds is also a wall
around itself. The rulebook states the danger plainly (Ch. 3.4): the Cop must
squeeze the Thief into a corner *"without accidentally blocking its own access
routes"* (Ch. 3.4) —
without accidentally blocking its own access routes.

The failure it warns about is not subtle, it is terminal. A Cop that partitions
the board and ends up on the wrong side of its own wall cannot reach the Thief
at all, so the Thief simply waits out the clock and wins on survival. No amount
of good play afterwards recovers it, because barriers are permanent.

So the guard is **separation, not confinement**. A small shared region is a
*winning* position for the Cop — the Thief has nowhere to run. A large region
the Cop cannot enter is a lost one. The two look similar on a board and are
opposite in value, which is exactly why this is computed rather than eyeballed.
"""

from __future__ import annotations

from collections import deque

from core.domain.board import Board, Position

__all__ = ["reachable", "are_connected", "region_size", "exit_count"]


def reachable(start: Position, barriers: frozenset[Position], board: Board) -> frozenset[Position]:
    """Return every cell reachable from *start* by legal orthogonal movement.

    Breadth-first over the 4-connected grid. *start* itself is included even if
    it is barriered, because an agent standing on a cell can always leave it —
    a barrier blocks entry, not exit.

    Args:
        start: The cell to search from.
        barriers: Permanently blocked cells.
        board: Supplies bounds and neighbours.

    Returns:
        The connected region containing *start*.
    """
    seen: set[Position] = {start}
    queue: deque[Position] = deque([start])
    while queue:
        for _, neighbour in board.neighbours(queue.popleft()):
            if neighbour not in seen and board.is_passable(neighbour, barriers):
                seen.add(neighbour)
                queue.append(neighbour)
    return frozenset(seen)


def are_connected(
    first: Position,
    second: Position,
    barriers: frozenset[Position],
    board: Board,
) -> bool:
    """Return True when a legal path exists between *first* and *second*.

    This is the question the Cop must ask before **every** barrier placement:
    *"after this wall, can I still reach the Thief?"* If the answer is no, the
    placement forfeits the sub-game however good it looks locally.
    """
    return second in reachable(first, barriers, board)


def region_size(start: Position, barriers: frozenset[Position], board: Board) -> int:
    """Return how many cells share a region with *start*.

    For the Thief this is the honest measure of freedom — far better than
    counting immediate neighbours. A Thief with four open neighbours inside a
    six-cell pocket is nearly caught; one with two neighbours in an open board
    is not.
    """
    return len(reachable(start, barriers, board))


def exit_count(pos: Position, barriers: frozenset[Position], board: Board) -> int:
    """Return how many orthogonal neighbours of *pos* are passable.

    The endgame counter. At 1, a single barrier on that last exit captures the
    Thief (M#47), so this is what the Cop drives down before spending its final
    walls. At 0 the Thief is already captured.
    """
    return sum(
        1 for _, neighbour in board.neighbours(pos) if board.is_passable(neighbour, barriers)
    )
