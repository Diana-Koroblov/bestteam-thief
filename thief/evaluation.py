"""What a Thief position is worth (TODO 8.2.1-8.2.4; PRD advanced §4).

Higher is better for the Thief. The role economics say what to optimise: survival
pays us 10 and the Cop 5, capture pays the Cop 20 and us 5. **We are ahead by
default and only have to not lose**, so every term here is about denying the Cop
its win condition rather than about doing anything clever.

Distance is a poor proxy for safety, and this file exists because of that
A far cell with one exit is worse than a near cell with four — the Cop's entire
plan is to drive our exit count to 1 while standing next to that exit (§2.2), and
distance says nothing about how close we are to that state. So `capture_risk`
is the mirror image of the Cop's `endgame_mass`, weighted hardest of anything
here, and raw distance is the *smallest* term rather than the largest.

The second correction is about walls. A region is not safe because it is big; it
is safe because the Cop cannot close it with the barriers it has left. Fourteen
walls seal a lot of board, and `seal_pressure` prices that in using the count the
Cop must declare truthfully (M#15) — public arithmetic, not an exploit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.domain.board import Board, Position
from core.domain.connectivity import exit_count
from core.domain.cuts import k_step_reach, last_exit_of, region_has_cycle
from core.domain.pathfinding import distance_map

__all__ = ["ThiefWeights", "evaluate", "capture_risk", "seal_pressure", "CAPTURED"]

# Being caught is not a poor position, it is the sub-game lost. Mirrors the
# Cop's CAPTURE_VALUE and for the same reason: no arrangement of room, cycles or
# distance may be traded for it.
CAPTURED = -1000.0

# How far ahead escape room is counted. Five steps is roughly how long a seal
# takes to matter; cells we could only reach in twelve turns are not part of
# this fight.
REACH_HORIZON = 5


@dataclass(frozen=True)
class ThiefWeights:
    """Relative worth of each term. Ours alone — never negotiated, never sent.

    Attributes:
        capture_risk: Penalty per unit of believed Cop mass that could end the
            sub-game next turn (A2.4). The largest weight here by an order of
            magnitude: this is the losing state, not a bad one.
        seal_pressure: Penalty for sitting where the Cop's remaining quota is
            enough to close us in (A2.3, A2.8).
        room: Reward per cell of five-step escape room (A2.1).
        cycle: Reward for a region that still contains a cycle (A2.7). A cycle
            is what lets one evader outlast one pursuer indefinitely.
        scent: Penalty per unit of our own trail already within earshot (A2.5).
        distance: Reward per expected step between us and the believed Cop.
            Deliberately the smallest term — see the module docstring.
    """

    capture_risk: float = 400.0
    seal_pressure: float = 25.0
    room: float = 2.0
    cycle: float = 30.0
    scent: float = 4.0
    distance: float = 1.0

    @classmethod
    def from_config(cls, config: Any) -> ThiefWeights:
        """Read `[strategy] weight_*` keys, falling back to the defaults above.

        Defaults live in the dataclass so a fresh clone plays a real game with
        no tuning file, and so a weight silently defaulting to 0 in config
        cannot disable a whole term without an error to notice.
        """
        if config is None:
            return cls()
        defaults = cls()
        read = {
            name: float(config.get(f"strategy.weight_{name}", getattr(defaults, name)))
            for name in ("capture_risk", "seal_pressure", "room", "cycle", "scent", "distance")
        }
        return cls(**read)


def _placeable(cop: Position, cell: Position) -> bool:
    """Whether a Cop on *cop* could wall *cell* next turn.

    Ch. 3.4 allows its own cell or an orthogonal neighbour — so a Cop standing
    **on** our last exit is as lethal as one beside it, and an adjacency-only
    test would miss the most dangerous square on the board.
    """
    return cop == cell or abs(cop[0] - cell[0]) + abs(cop[1] - cell[1]) == 1


def capture_risk(
    cell: Position, belief: dict[Position, float], barriers: frozenset[Position], board: Board
) -> float:
    """Return the believed Cop mass that could capture us on *cell* next turn.

    **A2.4, the single most valuable line in this evaluation.** Three ways the
    sub-game ends, and all three are checked because the Cop chooses whichever
    is available:

    * we have no exits at all — already captured under M#47;
    * we have exactly one exit and the Cop can wall it (§2.2's win condition);
    * the Cop is adjacent and simply steps onto us.

    Returned as mass rather than a boolean because the Cop's position is a
    belief. A 30% chance of being caught next turn is not a veto, it is a price.
    """
    free = [n for _, n in board.neighbours(cell) if board.is_passable(n, barriers)]
    if not free:
        return sum(belief.values())

    exit_cell = last_exit_of(cell, barriers, board)
    return sum(
        mass
        for cop, mass in belief.items()
        if _placeable(cop, cell) or (exit_cell is not None and _placeable(cop, exit_cell))
    )


def seal_pressure(
    cell: Position, barriers: frozenset[Position], board: Board, walls_left: int
) -> float:
    """Return how much of the Cop's quota it would take to seal us in, inverted.

    **A2.3 and A2.8.** Closing a cell means blocking every exit it has, so
    `exit_count - 1` is what stands between us and the one-exit losing state.
    Measured against `walls_left` — the Cop's remaining barriers, which it must
    declare truthfully (M#15) — because fourteen walls and two walls are
    completely different games and a fixed threshold would play both the same.

    Returns:
        0.0 when the Cop cannot close us with what it has; rising toward 1.0 as
        its quota covers the gap. Never negative: a huge quota against a wide
        open cell is safe, not *extra* safe.
    """
    needed = max(exit_count(cell, barriers, board) - 1, 0)
    if walls_left <= 0 or needed > walls_left:
        return 0.0
    return 1.0 - (needed / (walls_left + 1))


def evaluate(
    cell: Position,
    belief: dict[Position, float],
    barriers: frozenset[Position],
    board: Board,
    walls_left: int,
    weights: ThiefWeights,
) -> float:
    """Score a Thief position against a belief about the Cop. Higher is better.

    Args:
        cell: Where the Thief stands in the position being scored.
        belief: Posterior over the Cop's cell. Need not be normalised — every
            term is linear in mass, so an unnormalised belief scales the score
            rather than reordering it.
        barriers: The walls in force.
        board: Geometry.
        walls_left: What the Cop may still place.
        weights: Relative worth of each term.

    Returns:
        A float with no absolute meaning; only comparisons are used.

    The scent term is **absent here on purpose.** It belongs to the move, not to
    the position, and it is applied at the root of the search — see
    `thief/search.py` for why a trail cost inside a deep search would be false
    precision.
    """
    distances = distance_map(cell, barriers, board)
    far = float(board.grid_size * 2)
    return (
        -weights.capture_risk * capture_risk(cell, belief, barriers, board)
        - weights.seal_pressure * seal_pressure(cell, barriers, board, walls_left)
        + weights.room * len(k_step_reach(cell, barriers, board, REACH_HORIZON))
        + weights.cycle * region_has_cycle(cell, barriers, board)
        + weights.distance * sum(
            mass * distances.get(cop, far) for cop, mass in belief.items()
        )
    )
