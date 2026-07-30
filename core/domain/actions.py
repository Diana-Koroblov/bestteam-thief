"""The complete set of legal actions. There is nothing else an agent may do.

Appendix F Table 15 row 1 fixes the move set at four single orthogonal steps
plus STAY, and marks it **קבוע** — fixed. Deviating disqualifies the team, and
M#14 makes the sanction concrete: a diagonal move is rejected by the opponent
and forfeits the game.

So diagonals are not filtered here, they are **absent**. There is no `NE`, no
delta of `(-1, 1)`, nothing to accidentally construct and nothing for a future
refactor to re-enable. An illegal move is unrepresentable rather than merely
caught, which is a stronger guarantee than any validation check.

That distinction is not academic. The reference implementation's `Board` falls
back to eight-direction king movement when no move set is passed to it
(CONTRADICTIONS C-009), so a team porting that class carelessly plays an illegal
game and only finds out when an opponent rejects a move mid-match.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["Direction", "DELTAS", "MOVE_SET", "parse_direction"]


class Direction(str, Enum):
    """One legal action.

    Inherits from ``str`` so a Direction serialises as its own name in the
    canonical JSON that gets hashed. A move that hashed as ``"Direction.N"`` on
    one peer and ``"N"`` on the other would fail every commitment check.
    """

    N = "N"
    S = "S"
    E = "E"
    W = "W"
    STAY = "STAY"


# Row-major deltas: (row, col), origin top-left, row increasing downwards.
# North therefore *decreases* the row index. See CONTRADICTIONS C-010 for why
# the component order is pinned and confirmed with the opponent by example.
DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.N: (-1, 0),
    Direction.S: (1, 0),
    Direction.E: (0, 1),
    Direction.W: (0, -1),
    Direction.STAY: (0, 0),
}

# The exact list Appendix F fixes, in its published order. `config_spec` checks
# the negotiated config against this; a mismatch means someone edited a fixed
# value and the match must not start.
MOVE_SET: tuple[str, ...] = ("N", "S", "E", "W", "STAY")


def parse_direction(value: str) -> Direction:
    """Return the Direction named by *value*, raising on anything else.

    Args:
        value: A move name received from the opponent or read from a log.

    Returns:
        The matching Direction.

    Raises:
        ValueError: *value* is not one of the five legal actions. The message
            names what was received, because this is the error that fires when
            an opponent sends a diagonal and we need to quote it back at them.
    """
    try:
        return Direction(value)
    except ValueError:
        legal = ", ".join(MOVE_SET)
        raise ValueError(f"{value!r} is not a legal move. Legal moves are: {legal}") from None
