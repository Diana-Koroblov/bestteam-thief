"""The complete state of one sub-game, as an immutable value.

Frozen on purpose. A transition returns a **new** state rather than mutating a
shared one, which removes a whole class of aliasing bug: the GUI thread, the
search tree and the turn loop all hold references to states, and an expectimax
search that mutated the position it was evaluating would corrupt the very board
it is reasoning about.

Immutability also buys the property this project actually needs — a state is a
value that can be hashed. Two peers commit to `SHA256(State ‖ Move ‖ Intent ‖
Nonce)` (Ch. 5.3.1), so "the state this move was made against" has to be a
thing that can be serialised identically on both machines. A mutable object with
an identity is not that.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from core.domain.board import Position

__all__ = ["GameState"]


@dataclass(frozen=True)
class GameState:
    """A snapshot of one sub-game between two turns.

    Attributes:
        cop: The Cop's cell.
        thief: The Thief's cell.
        barriers: Permanently blocked cells, impassable to both players.
        step: How many completed turns have elapsed.
        barriers_placed: How many of the quota the Cop has spent. Derivable
            from ``len(barriers)`` today, but kept separate because a future
            negotiated rule could block a cell without spending quota, and a
            derived value would silently be wrong rather than loudly stale.
        sub_game: Which of the six sub-games this is, 1-based.
    """

    cop: Position
    thief: Position
    barriers: frozenset[Position] = field(default_factory=frozenset)
    step: int = 0
    barriers_placed: int = 0
    sub_game: int = 1

    @property
    def agents_share_a_cell(self) -> bool:
        """Return True when both agents occupy the same cell."""
        return self.cop == self.thief

    def advanced(self, **changes: object) -> GameState:
        """Return a copy with *changes* applied and the step counter advanced.

        The step counter is advanced here rather than by each caller because a
        turn that fails to increment it is a turn the Thief survived for free —
        and the survival threshold is what the Thief wins on.
        """
        step = int(changes.pop("step", self.step)) + 1
        return replace(self, step=step, **changes)  # type: ignore[arg-type]

    def with_barrier(self, cell: Position) -> GameState:
        """Return a copy with *cell* blocked and the quota counter incremented.

        Does not advance the step; the caller decides whether placing a barrier
        also ends the turn. It does, under the rules — placement costs the Cop
        its move — but that is the turn loop's business, not the state's.
        """
        return replace(
            self,
            barriers=self.barriers | {cell},
            barriers_placed=self.barriers_placed + 1,
        )
