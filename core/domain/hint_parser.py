"""Free text in, direction and confidence out (TODO 4.4.1).

The inbound half of the verbal game. Adapted from HW6's parser, with the
lesson that mattered kept intact: **report confidence, never just a direction.**

A parser that always returns its best guess is worse than one that admits
defeat. "I might drift north" and "I am going north" are different evidence, and
collapsing them lets a vague opponent steer our belief for free. Low confidence
defers to the scent field, which cannot lie.

The one asymmetry worth remembering: the opponent chooses these words to be
read. Every other input we have — the board, our own scent, the barrier list —
is a fact. This one is an argument, and it is the only channel where the
opponent gets a vote on what we believe.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from core.domain.actions import Direction

__all__ = ["ParsedHint", "parse"]

# Stems, so "northern", "northward" and "northbound" all count.
BEARINGS: dict[str, Direction] = {
    "north": Direction.N,
    "south": Direction.S,
    "east": Direction.E,
    "west": Direction.W,
}

# Words that weaken a claim without reversing it.
HEDGES = ("might", "maybe", "perhaps", "possibly", "could", "somewhere", "probably")

# Words that reverse it. "Not going north" is a claim about south-ish, but a
# weak one — so it lowers confidence rather than flipping the direction, which
# would let a one-word negation drive our belief harder than a plain statement.
NEGATIONS = ("not", "never", "n't", "away from", "opposite", "anywhere but")


@dataclass(frozen=True)
class ParsedHint:
    """What the opponent's sentence claims, and how much of it to believe.

    Attributes:
        direction: The bearing claimed, or None when the text names none.
        confidence: 0.0 to 1.0. **This is the important field.** It is the
            parser's own certainty about *what was said*, not about whether it
            is true — truthfulness is the reliability coefficient's job (4.2.2),
            and keeping the two apart is what stops one bad turn poisoning both.
        raw: The original text, kept for the log and the bluff audit.
    """

    direction: Direction | None
    confidence: float
    raw: str

    @property
    def usable(self) -> bool:
        """Whether this is worth acting on at all."""
        return self.direction is not None and self.confidence >= 0.4


def parse(text: str) -> ParsedHint:
    """Read *text* into a claimed bearing and a confidence.

    Args:
        text: The opponent's hint, as received. Never trusted, never executed,
            only read.

    Confidence starts high for a single plain bearing and is reduced by
    hedging, negation and self-contradiction. Two different bearings in one
    sentence is the interesting case: it is either a confused model or a
    deliberate smokescreen, and either way the honest answer is "unclear".
    """
    if not text or not text.strip():
        return ParsedHint(None, 0.0, text)

    lowered = text.lower()
    found = [
        bearing for stem, bearing in BEARINGS.items() if re.search(rf"\b{stem}\w*", lowered)
    ]

    if not found:
        return ParsedHint(None, 0.0, text)
    if len(set(found)) > 1:
        # Two bearings at once. Confused model or deliberate smokescreen —
        # either way we learned nothing, and pretending otherwise is how a
        # parser becomes an attack surface.
        return ParsedHint(None, 0.1, text)

    confidence = 0.9
    if any(hedge in lowered for hedge in HEDGES):
        confidence *= 0.5
    if any(negation in lowered for negation in NEGATIONS):
        # Deliberately weakens rather than flips. Flipping would let a single
        # "not" push our belief harder than a plain statement ever could,
        # which is a lever we should not hand the opponent.
        confidence *= 0.35
    return ParsedHint(found[0], round(confidence, 3), text)
