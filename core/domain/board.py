"""The board: dimensions, bounds and passability. No game rules live here.

Two spatial predicates are all the rest of the engine is allowed to ask —
``in_bounds`` and ``is_passable``. Keeping the geometry behind exactly two
questions means a change to the coordinate convention or the barrier
representation touches one file.

The grid size is read from config, never hardcoded. Appendix F marks it a
**minimum** of 7, so two teams may agree to play on 9 or 10; an engine with a
literal 7 in it would quietly play a different game from the one that was
signed.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from core.domain.actions import DELTAS, Direction

__all__ = ["Board", "Position"]

Position = tuple[int, int]


@dataclass(frozen=True)
class Board:
    """A square grid with an origin convention.

    Attributes:
        grid_size: Side length. Appendix F minimum 7.
        origin_index: The first index of each axis (``axis_start_index``).
            Almost always 0, but negotiable, so it is not assumed.

    Positions are ``(row, col)``. Row increases downwards from the top-left
    origin, so North decreases the row. The book negotiates *where* (0,0) sits
    but never states the component order, which is why it is pinned here and
    confirmed with the opponent using a worked example (CONTRADICTIONS C-010).
    """

    grid_size: int
    origin_index: int = 0

    def __post_init__(self) -> None:
        """Reject a board that cannot host a game.

        Raises:
            ValueError: The grid is smaller than the Appendix F minimum of 7.
                Catching it here rather than at move time means an illegal
                config fails at startup, not three turns into a match.
        """
        if self.grid_size < 7:
            raise ValueError(
                f"grid_size {self.grid_size} is below the Appendix F minimum of 7; "
                "raising it by agreement is legal, lowering it is not (M#12)"
            )

    @property
    def last_index(self) -> int:
        """Return the highest valid index on either axis."""
        return self.origin_index + self.grid_size - 1

    def in_bounds(self, pos: Position) -> bool:
        """Return True when *pos* lies on the board."""
        row, col = pos
        return (
            self.origin_index <= row <= self.last_index
            and self.origin_index <= col <= self.last_index
        )

    def is_passable(self, pos: Position, barriers: frozenset[Position]) -> bool:
        """Return True when *pos* is on the board and not blocked.

        Off-board and barriered cells are deliberately indistinguishable to
        callers: both are simply somewhere an agent cannot be. The edge of the
        board and a wall have identical consequences for mobility, and treating
        them alike is what makes the immobilised-thief rule (M#47) fall out
        naturally instead of needing a special case for corners.
        """
        return self.in_bounds(pos) and pos not in barriers

    def neighbours(self, pos: Position) -> Iterable[tuple[Direction, Position]]:
        """Yield each orthogonal neighbour of *pos* with the direction to it.

        Yields all four regardless of bounds or barriers — filtering is the
        caller's job, because "which neighbours exist" and "which are reachable"
        are different questions and conflating them hides the corner cases.
        """
        row, col = pos
        for direction, (d_row, d_col) in DELTAS.items():
            if direction is not Direction.STAY:
                yield direction, (row + d_row, col + d_col)

    def cells(self) -> Iterable[Position]:
        """Yield every cell on the board, row by row."""
        span = range(self.origin_index, self.last_index + 1)
        for row in span:
            for col in span:
                yield (row, col)
