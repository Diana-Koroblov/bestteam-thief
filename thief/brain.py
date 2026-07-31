"""The Thief's baseline: maximise distance, and never walk into a dead end.

The Thief wins by surviving `survival_threshold` steps, so the clock is on its
side and it does not have to do anything clever — only avoid being cornered.

The DoD names the trap directly: *never voluntarily enter a cell with no exit
other than the one it came from*. That is the difference between a baseline that
survives and one that walks into a pocket on turn 6 and is caught at leisure.
So the tie-break is **room to move**, not raw distance: a cell three steps away
inside a four-cell pocket is worse than a cell two steps away on the open board.

Like the Cop's baseline this is a floor to measure against, not the real
strategy. Cycle-seeking and false anchors arrive with the belief filter.
"""

from __future__ import annotations

from core.domain.actions import Direction
from core.domain.board import Position
from core.domain.brain_base import BrainBase, Decision, Observation
from core.domain.connectivity import exit_count, region_size
from core.domain.movement import get_legal_moves
from core.domain.pathfinding import distance_map

__all__ = ["ThiefBrain"]

# A cell whose only way out is the way in. Entering one hands the Cop a capture
# for the price of a single barrier, so it is refused unless nothing else exists.
DEAD_END_EXITS = 1


class ThiefBrain(BrainBase):
    """Moves away from the believed Cop position while keeping room to run."""

    def _pick_move(self, observation: Observation) -> Decision:
        """Pick the safest legal move, preferring distance and space.

        Candidates are scored on three keys, in order:

        1. **not a dead end** — the DoD's requirement, and the cheapest way to
           lose a sub-game if ignored;
        2. **distance from the believed Cop** — the obvious pressure;
        3. **region size** — how much board remains reachable afterwards. This
           is what stops the Thief fleeing into a large-looking corner that a
           single wall will seal.

        Ties break on the destination cell so that a replay is reproducible.
        """
        moves = get_legal_moves(
            observation.own_position, observation.barriers, observation.board
        )
        threat = observation.most_likely_opponent()
        distances = (
            distance_map(threat, observation.barriers, observation.board) if threat else {}
        )

        def score(entry: tuple[Direction, Position]) -> tuple[int, int, int, Position]:
            _, cell = entry
            exits = exit_count(cell, observation.barriers, observation.board)
            safe = 0 if exits <= DEAD_END_EXITS else 1
            away = distances.get(cell, 0)
            room = region_size(cell, observation.barriers, observation.board)
            return (safe, away, room, cell)

        best = max(sorted(moves, key=lambda entry: entry[1]), key=score)
        direction, cell = best

        if threat is None:
            return Decision(direction, reason=f"no belief yet - keeping room at {cell}")
        return Decision(
            direction,
            reason=f"{distances.get(cell, 0)} from believed cop at {threat}, "
            f"{exit_count(cell, observation.barriers, observation.board)} exits",
        )
