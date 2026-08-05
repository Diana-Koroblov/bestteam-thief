"""Cut geometry: what a wall actually does to a region (PRD advanced §3.3).

`connectivity.py` answers *"can A still reach B?"*. This answers the harder
question the Cop needs before spending a barrier: **what does this placement buy,
and can the cut be finished?**

Three facts about a 4-connected grid drive everything here.

* **A diagonal chain of barriers cannot be crossed.** Movement is orthogonal
  only (`actions.py` has no diagonal to construct), so barriers touching corner
  to corner form a wall with no gap in it. That makes the diagonal the cheapest
  possible cut — four barriers seal a six-cell corner, where an orthogonal line
  would need six.
* **A region with a cycle is a region the Thief survives in.** One pursuer
  cannot corner an evader on a cyclic graph; the evader simply goes round.
  Removing the last cycle is worth more than removing several cells, and the two
  are not the same measurement.
* **The board edge is free wall.** A cut anchored on an edge needs no barrier
  there, which is why `diagonal_support` counts off-board corners alongside
  placed ones.

Everything here is a pure function of `(cells, barriers, board)` — no role, no
belief, no config. Both brains use it: the Cop to find cuts, the Thief to avoid
regions where one is close to complete (PRD advanced §4.3).
"""

from __future__ import annotations

from collections import deque

from core.domain.board import Board, Position
from core.domain.connectivity import reachable

__all__ = [
    "k_step_reach",
    "region_has_cycle",
    "diagonal_support",
    "separates",
    "last_exit_of",
]

# The four corner offsets. Not in `actions.py` on purpose: these are not moves
# and must never become moves (M#14). A diagonal is something a *wall* can be,
# never something an agent can do.
_CORNERS = ((-1, -1), (-1, 1), (1, -1), (1, 1))


def k_step_reach(start: Position, barriers: frozenset[Position], board: Board, k: int) -> frozenset[Position]:
    """Return every cell within *k* legal steps of *start*.

    The honest measure of what a placement costs the Thief (A1.7). Scoring a
    barrier by whether it sits *between* the two agents rewards walls that look
    obstructive and do nothing — the Thief simply walks around one cell. Scoring
    it by how much of the Thief's near-term reachable set disappears rewards
    walls that actually remove options.

    *k* is bounded rather than unbounded because the sub-game is: with a 35-step
    limit and a pursuer already close, cells the Thief could only reach in
    twelve turns are not part of this fight.

    Args:
        start: The cell to expand from.
        barriers: Permanently blocked cells.
        board: Supplies bounds and neighbours.
        k: Step budget. 0 returns just *start*.

    Returns:
        The reachable set, *start* included.
    """
    seen: set[Position] = {start}
    frontier: deque[tuple[Position, int]] = deque([(start, 0)])
    while frontier:
        cell, depth = frontier.popleft()
        if depth >= k:
            continue
        for _, neighbour in board.neighbours(cell):
            if neighbour not in seen and board.is_passable(neighbour, barriers):
                seen.add(neighbour)
                frontier.append((neighbour, depth + 1))
    return frozenset(seen)


def region_has_cycle(start: Position, barriers: frozenset[Position], board: Board) -> bool:
    """Return True when *start*'s region still contains a cycle.

    Counted rather than searched. For a connected graph, a cycle exists exactly
    when the edge count reaches the vertex count — a tree has ``V - 1`` edges and
    every extra edge closes a loop. On a 49-cell board that is cheaper and far
    less error-prone than a depth-first back-edge hunt, and it cannot miss a
    cycle the way a traversal with a subtle visited-set bug can.

    **This is the Cop's real objective** (§2.1). A region the Thief can circle
    is a region it survives in for all 35 steps, however small the region is; a
    cycle-free region can be swept from one end.
    """
    region = {cell for cell in reachable(start, barriers, board) if board.is_passable(cell, barriers)}
    if not region:
        return False
    # Each edge is seen from both ends, so the sum double-counts.
    edges = sum(1 for cell in region for _, other in board.neighbours(cell) if other in region) // 2
    return edges >= len(region)


def diagonal_support(cell: Position, barriers: frozenset[Position], board: Board) -> int:
    """Return how many of *cell*'s four corners already anchor a cut (A1.8).

    A corner counts when it holds a barrier **or lies off the board**. The board
    edge is wall we did not have to pay for, so a placement tucked into a corner
    continues a cut just as surely as one beside an existing barrier — and the
    scoring must see that, or the Cop will spend barriers rebuilding the edge.

    Returns:
        0..4. Higher means this placement extends work already done rather than
        starting a second, half-finished wall somewhere else.
    """
    row, column = cell
    corners = ((row + d_row, column + d_col) for d_row, d_col in _CORNERS)
    return sum(1 for corner in corners if not board.is_passable(corner, barriers))


def separates(
    first: Position,
    second: Position,
    cell: Position,
    barriers: frozenset[Position],
    board: Board,
) -> bool:
    """Return True when walling *cell* would cut *first* off from *second*.

    The single most expensive mistake the Cop can make, so it gets its own name
    rather than living inline as a negated `are_connected`. A Cop that walls
    itself away from the Thief has forfeited the sub-game — barriers are
    permanent, and no play afterwards recovers it (`connectivity.py`).

    Note that this is *separation*, not confinement. Sealing yourself in **with**
    the Thief is the winning move and must not be rejected (§3.2).
    """
    return second not in reachable(first, barriers | {cell}, board)


def last_exit_of(cell: Position, barriers: frozenset[Position], board: Board) -> Position | None:
    """Return *cell*'s only free neighbour, or None when it has none or several.

    The endgame in one call. M#47 captures a Thief with no free neighbour, so a
    Thief down to exactly one exit is a single barrier from losing — and this
    returns the cell that barrier goes on.

    None is deliberately ambiguous between "already sealed" and "still has
    options", because both mean *there is no one placement to make here*. The
    caller that needs to tell them apart asks `exit_count` instead.
    """
    free = [n for _, n in board.neighbours(cell) if board.is_passable(n, barriers)]
    return free[0] if len(free) == 1 else None
