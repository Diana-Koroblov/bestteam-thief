"""The interface every strategy implements. Movement is decided here, never by a model.

Chapter 6 is unambiguous: *"הכרעת המהלך היא תמיד אלגוריתמית ובקוד פייתון"*. A
language model hallucinates in Cartesian space — it will happily propose a move
into a wall — and an illegal move is a technical loss (M#13). The model's whole
job is the verbal layer. So no brain may import an LLM provider, and an
architecture test enforces it (M#25).

A brain sees an ``Observation``, not the game. It is given what a peer can
legitimately know: its own position, the barriers that were openly declared, the
scent field the opponent transmitted, and the hints received. **It is not given
the opponent's position**, because in a real match nobody has it — passing the
true position here would silently produce a strategy that cannot work.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from core.domain.actions import Direction
from core.domain.board import Board, Position

__all__ = ["Observation", "Decision", "BrainBase"]


@dataclass(frozen=True)
class Observation:
    """Everything this peer may legitimately know when choosing a move.

    Attributes:
        board: Geometry, sized from the negotiated config.
        own_position: Where we are. The only position known for certain.
        barriers: Openly declared placements (M#15).
        step: Turns elapsed.
        barriers_remaining: How many walls the Cop may still place.
        belief: Probability per cell that the opponent is there. Uniform until
            Phase 4 supplies a real posterior — deliberately, so a baseline
            written now cannot come to depend on information it will not have.
        hints: Verbal messages received so far, any of which may be lies.
    """

    board: Board
    own_position: Position
    barriers: frozenset[Position] = field(default_factory=frozenset)
    step: int = 0
    barriers_remaining: int = 0
    belief: dict[Position, float] = field(default_factory=dict)
    hints: tuple[str, ...] = ()

    def most_likely_opponent(self) -> Position | None:
        """Return the highest-probability cell, or None when we know nothing.

        Ties break on the cell's own coordinates, so two peers replaying the
        same belief reach the same answer. A search tie-broken by dict order
        would diverge between machines and make the log unverifiable.
        """
        if not self.belief:
            return None
        return max(sorted(self.belief), key=lambda cell: self.belief[cell])


@dataclass(frozen=True)
class Decision:
    """What a brain chose this turn.

    Attributes:
        move: The action to take. ``STAY`` when placing a barrier, since a
            placement costs the Cop its move (Ch. 3.4).
        barrier: The cell to wall, or None. Only ever set by a Cop.
        reason: Why, in one line. Written to the log so a replay explains
            itself rather than showing an unmotivated sequence of moves.
    """

    move: Direction
    barrier: Position | None = None
    reason: str = ""

    def __post_init__(self) -> None:
        """Reject a decision that moves *and* places, which no rule allows."""
        if self.barrier is not None and self.move is not Direction.STAY:
            raise ValueError(
                f"a barrier at {self.barrier} requires forgoing movement, "
                f"but the move is {self.move.value} (Ch. 3.4)"
            )


class BrainBase(ABC):
    """Base for every strategy. Subclasses implement ``_pick_move`` only.

    The split between ``decide`` and ``_pick_move`` is what lets the Cop add
    barrier reasoning without every strategy re-implementing movement, and what
    keeps the turn loop from knowing which role it is running.
    """

    def __init__(self, name: str = "") -> None:
        """Store a display name used in logs and the A/B report."""
        self.name = name or type(self).__name__

    def decide(self, observation: Observation) -> Decision:
        """Return this turn's decision.

        Overridable, but the default is deliberately thin: pick a move. The Cop
        overrides it to consider a barrier first, because that choice replaces
        the move rather than accompanying it.
        """
        return self._pick_move(observation)

    @abstractmethod
    def _pick_move(self, observation: Observation) -> Decision:
        """Choose a move from *observation*. Must be deterministic.

        Two peers replay the same log and must reach the same result, so a
        brain that consulted a clock or an unseeded random source would make
        the match unverifiable.
        """
