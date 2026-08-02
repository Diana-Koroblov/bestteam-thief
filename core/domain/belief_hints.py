"""Folding the opponent's words into the posterior (TODO 4.2.1.d).

Split from ``belief.py`` to keep both under the 150-line rule, and because the
two update sources are not equal and should not read as though they were.

**The scent is a fact; the hint is an argument.** Every other input we have is
something the opponent could not choose — the board, the barrier list, the trail
they leave by existing. The hint is the one channel where the opponent gets a
vote on what we believe, so it is the one input scaled by a learned coefficient
before it touches anything.

The scaling is what makes a lie useful instead of dangerous. Against an opponent
with a coefficient of 0.2, "I am going north" moves mass **south** — a reliably
inverted signal is still a signal. Against a stranger the coefficient sits at
0.5, trust is 0, and the update is a deliberate no-op: on turn one against
someone we have never played, their words are worth exactly nothing.
"""

from __future__ import annotations

from core.domain.actions import Direction
from core.domain.belief import normalise
from core.domain.board import Board, Position
from core.domain.hint_parser import ParsedHint

__all__ = ["update_from_hint", "DELTAS"]

DELTAS: dict[Direction, tuple[int, int]] = {
    Direction.N: (-1, 0),
    Direction.S: (1, 0),
    Direction.E: (0, 1),
    Direction.W: (0, -1),
}

# How far a fully trusted, fully understood claim may tilt the posterior. Well
# under 1.0 on purpose: the hint may be a lie even from a mostly-honest
# opponent, and the scent field must stay the dominant evidence.
MAX_TILT = 0.35


def update_from_hint(
    belief: dict[Position, float],
    hint: ParsedHint,
    trust: float,
    board: Board,
) -> dict[Position, float]:
    """Tilt *belief* along the claimed bearing, scaled by *trust*.

    Args:
        belief: The current posterior.
        hint: What the opponent's sentence claimed, with the parser's
            confidence in having read it correctly.
        trust: Signed, in [-1, 1], from ``Reliability.trust``. Zero means no
            record yet and produces no change at all.
        board: Geometry.

    Two independent gates must both open before anything moves: the parser must
    be confident it understood the words (``hint.usable``), and the opponent's
    record must say the words are worth something (``trust`` away from zero).
    Confusing those two would let a clearly-worded lie count as strong evidence.
    """
    if not hint.usable or hint.direction is None or trust == 0.0:
        return dict(belief)

    # A negative coefficient inverts the claim rather than discarding it.
    bearing = hint.direction if trust > 0 else _opposite(hint.direction)
    strength = MAX_TILT * abs(trust) * hint.confidence
    d_row, d_col = DELTAS[bearing]

    tilted: dict[Position, float] = {}
    for cell, mass in belief.items():
        ahead = (cell[0] + d_row, cell[1] + d_col)
        # Off-board mass cannot move, so the cell keeps all of it. Letting it
        # drain would quietly bias the posterior away from the edges — an
        # opinion about geometry that no hint actually expressed.
        moving = strength if ahead in belief else 0.0

        # **Both writes accumulate; neither assigns.** They used to assign, and
        # the bug was invisible in one direction: a cell would receive mass from
        # its neighbour, then the loop would reach that cell and overwrite the
        # contribution. Tilting north happened to visit donors before
        # recipients and worked; tilting south visited them in the other order
        # and silently did nothing at all. The result was a filter that could
        # read a truthful opponent but not a liar — which is exactly the case
        # this module exists for.
        tilted[cell] = tilted.get(cell, 0.0) + mass * (1.0 - moving)
        if moving:
            tilted[ahead] = tilted.get(ahead, 0.0) + mass * moving
    return normalise({c: v for c, v in tilted.items() if c in belief})


def _opposite(direction: Direction) -> Direction:
    """Return the reverse bearing, for reading a known liar."""
    return {
        Direction.N: Direction.S,
        Direction.S: Direction.N,
        Direction.E: Direction.W,
        Direction.W: Direction.E,
    }[direction]
