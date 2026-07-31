"""Shortest legal paths on the barriered grid. Pure geometry, no strategy.

Breadth-first, because every move costs exactly one turn — so the first time BFS
reaches a cell it has reached it by a shortest route, and no weighting is needed.

Determinism matters more than speed here. Two peers replay the same log and must
compute the same path, so neighbours are visited in a fixed order (N, S, E, W as
they appear in ``DELTAS``) and ties break the same way on both machines. A path
that depended on set iteration order would make the log unverifiable.
"""

from __future__ import annotations

from collections import deque

from core.domain.actions import Direction
from core.domain.board import Board, Position

__all__ = ["shortest_path", "first_step_towards", "distance_map"]


def distance_map(
    start: Position, barriers: frozenset[Position], board: Board
) -> dict[Position, int]:
    """Return the number of moves from *start* to every reachable cell.

    One sweep answers "how far is everything", which is what a pursuit or an
    evasion heuristic actually needs — far cheaper than a separate search per
    candidate cell.
    """
    distances: dict[Position, int] = {start: 0}
    queue: deque[Position] = deque([start])
    while queue:
        current = queue.popleft()
        for _, neighbour in board.neighbours(current):
            if neighbour not in distances and board.is_passable(neighbour, barriers):
                distances[neighbour] = distances[current] + 1
                queue.append(neighbour)
    return distances


def shortest_path(
    start: Position,
    goal: Position,
    barriers: frozenset[Position],
    board: Board,
) -> list[Position]:
    """Return the cells from *start* to *goal* inclusive, or ``[]`` if unreachable.

    An empty list is a real answer, not a failure: barriers are permanent, so a
    goal can become genuinely unreachable, and the Cop must be able to notice
    that rather than walk into a wall forever.
    """
    if start == goal:
        return [start]
    came_from: dict[Position, Position] = {start: start}
    queue: deque[Position] = deque([start])

    while queue:
        current = queue.popleft()
        for _, neighbour in board.neighbours(current):
            if neighbour in came_from or not board.is_passable(neighbour, barriers):
                continue
            came_from[neighbour] = current
            if neighbour == goal:
                return _trace(came_from, start, goal)
            queue.append(neighbour)
    return []


def _trace(came_from: dict[Position, Position], start: Position, goal: Position) -> list[Position]:
    """Walk the parent chain back from *goal* and return it forwards."""
    path = [goal]
    while path[-1] != start:
        path.append(came_from[path[-1]])
    return list(reversed(path))


def first_step_towards(
    start: Position,
    goal: Position,
    barriers: frozenset[Position],
    board: Board,
) -> Direction:
    """Return the first move along a shortest path, or ``STAY`` if there is none.

    ``STAY`` rather than an exception: an unreachable goal is a legitimate
    board state, and a brain that raised would turn a lost position into a
    crash — which scores 0 for *both* teams instead of just losing.
    """
    path = shortest_path(start, goal, barriers, board)
    if len(path) < 2:
        return Direction.STAY
    for direction, neighbour in board.neighbours(start):
        if neighbour == path[1]:
            return direction
    return Direction.STAY  # pragma: no cover - unreachable given a valid path
