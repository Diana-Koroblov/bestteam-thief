"""Barrier placement: the Cop's only resource, and its rules.

The rule, from Chapter 3.4: *"on a turn where the Cop forgoes movement, it may
place a barrier on any cell one step away from it"* — on a turn where the Cop **forgoes
movement**, it may place a barrier on its own cell or one of the four
orthogonally adjacent cells. The cell becomes impassable to **both** players for
the rest of the sub-game, and there is no way to remove it.

Two consequences shape the whole design:

* **A barrier costs a turn.** With 35 moves and a quota of 14, spending the full
  quota consumes 40% of the Cop's game. The scarce resource is turns, not
  barriers, which is why raising ``max_barriers`` in negotiation buys almost
  nothing (see ``docs/PARAMETERS.md`` §4.1).
* **A barrier can capture.** Placing on the Thief's current cell wins outright
  (M#46), and so does sealing the Thief's last orthogonal exit (M#47). Placement
  therefore returns an outcome rather than a boolean — the capture is too easy
  to forget if it lives in a separate call.

The Cop must declare every placement truthfully with its exact cell (M#15) and
may not lie about the location (M#16). There is deliberately **no** placement
path that does not produce a declarable record.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.domain.board import Board, Position
from core.domain.movement import is_immobilised

__all__ = ["PlacementOutcome", "RejectionReason", "Placement", "BarrierManager"]


class PlacementOutcome(str, Enum):
    """What a placement attempt achieved."""

    PLACED = "PLACED"
    CAPTURE = "CAPTURE"
    REJECTED = "REJECTED"


class RejectionReason(str, Enum):
    """Why a placement was refused. Empty when it succeeded."""

    NONE = ""
    NOT_FORGOING_MOVE = "a barrier may only be placed on a turn the cop forgoes movement"
    OUT_OF_RANGE = "target must be the cop's own cell or an orthogonal neighbour"
    OFF_BOARD = "target is outside the board"
    ALREADY_BLOCKED = "that cell already holds a barrier"
    QUOTA_EXHAUSTED = "the barrier quota is spent"


@dataclass(frozen=True)
class Placement:
    """The result of one placement attempt, and the record that gets declared.

    Attributes:
        outcome: PLACED, CAPTURE or REJECTED.
        cell: The exact cell, carried into the signed move record (M#15).
        reason: Why it was rejected; ``NONE`` on success.
    """

    outcome: PlacementOutcome
    cell: Position
    reason: RejectionReason = RejectionReason.NONE

    @property
    def succeeded(self) -> bool:
        """Return True when a barrier was actually added to the board."""
        return self.outcome is not PlacementOutcome.REJECTED


class BarrierManager:
    """Tracks placed barriers and enforces the quota and adjacency rules."""

    def __init__(self, max_barriers: int, board: Board) -> None:
        """Store the quota and the board the placements are validated against.

        Args:
            max_barriers: Appendix F quota, default 14 (a minimum, so it may be
                raised by agreement but never lowered).
            board: Supplies the bounds.

        Raises:
            ValueError: The quota is negative, which no negotiation can produce.
        """
        if max_barriers < 0:
            raise ValueError(f"max_barriers must not be negative, got {max_barriers}")
        self._max = max_barriers
        self._board = board
        self._placed: set[Position] = set()

    @property
    def barriers(self) -> frozenset[Position]:
        """Return the current barriers. Frozen, because they are permanent."""
        return frozenset(self._placed)

    @property
    def placed_count(self) -> int:
        """Return how many barriers have been placed."""
        return len(self._placed)

    @property
    def remaining(self) -> int:
        """Return how many barriers the Cop may still place."""
        return self._max - len(self._placed)

    def rejection_for(
        self, target: Position, cop_pos: Position, *, is_forgoing_move: bool
    ) -> RejectionReason:
        """Return why *target* is not placeable, or ``NONE`` if it is.

        Checked in the order a reviewer would ask them, so the message names the
        first thing actually wrong rather than an incidental consequence.
        """
        if not is_forgoing_move:
            return RejectionReason.NOT_FORGOING_MOVE
        if self.remaining <= 0:
            return RejectionReason.QUOTA_EXHAUSTED
        if not self._board.in_bounds(target):
            return RejectionReason.OFF_BOARD
        if target != cop_pos and target not in {cell for _, cell in self._board.neighbours(cop_pos)}:
            return RejectionReason.OUT_OF_RANGE
        if target in self._placed:
            return RejectionReason.ALREADY_BLOCKED
        return RejectionReason.NONE

    def can_place(self, target: Position, cop_pos: Position, is_forgoing_move: bool) -> bool:
        """Return True when placing on *target* is legal this turn."""
        return self.rejection_for(target, cop_pos, is_forgoing_move=is_forgoing_move) is (
            RejectionReason.NONE
        )

    def place(
        self,
        target: Position,
        cop_pos: Position,
        *,
        is_forgoing_move: bool = True,
        thief_pos: Position | None = None,
    ) -> Placement:
        """Place a barrier on *target* and report what it achieved.

        Args:
            target: The cell to block.
            cop_pos: Where the Cop stands this turn.
            is_forgoing_move: Whether the Cop gave up its move for this.
            thief_pos: The Thief's cell, when known, so the two capture
                conditions can be evaluated. Omitted when the Cop is placing
                against a belief rather than an observation.

        Returns:
            A ``Placement``. ``CAPTURE`` when the barrier lands on the Thief
            (M#46) or seals its last orthogonal exit (M#47).
        """
        reason = self.rejection_for(target, cop_pos, is_forgoing_move=is_forgoing_move)
        if reason is not RejectionReason.NONE:
            return Placement(PlacementOutcome.REJECTED, target, reason)

        self._placed.add(target)
        if thief_pos is not None and self._captures(target, thief_pos):
            return Placement(PlacementOutcome.CAPTURE, target)
        return Placement(PlacementOutcome.PLACED, target)

    def _captures(self, target: Position, thief_pos: Position) -> bool:
        """Return True when the barrier just placed ends the sub-game."""
        return target == thief_pos or is_immobilised(thief_pos, self.barriers, self._board)
