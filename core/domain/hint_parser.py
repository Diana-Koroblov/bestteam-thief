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

# Words that reverse a claim. "Not going north" is a claim about south-ish, but
# a weak one — so it lowers confidence rather than flipping the direction, which
# would let a one-word negation drive our belief harder than a plain statement.
# Matched as **whole words**, never as prefixes. An earlier version used
# ``startswith`` and included "no" — and ``"north".startswith("no")`` is True,
# so every northward hint negated itself. Every hint claiming north was scored
# 0.315 and silently discarded.
NEGATIONS = frozenset(
    {"not", "never", "n't", "away", "opposite", "avoid", "anywhere", "isn't", "won't"}
)

# **A negation counts only if it PRECEDES the bearing and sits close to it.**
#
# Negation scopes forward in English: "not going north" negates, "north — you
# will never catch me" does not. The first version scanned the whole sentence
# and silently broke the entire verbal channel, because hints are *taunts* and
# "you will never catch me" is the house style. Almost every hint an opponent
# could send scored 0.315, landed under the usable threshold, and was discarded.
#
# That failure is invisible from the outside: an ignored hint looks exactly like
# an opponent who said nothing useful, so we would have played the whole league
# with a dead verbal channel and no symptom.
NEGATION_WINDOW = 3


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
    if _negated_near_bearing(lowered, found[0]):
        # Deliberately weakens rather than flips. Flipping would let a single
        # "not" push our belief harder than a plain statement ever could,
        # which is a lever we should not hand the opponent.
        confidence *= 0.35
    return ParsedHint(found[0], round(confidence, 3), text)


def _negated_near_bearing(lowered: str, bearing: Direction) -> bool:
    """Whether a negation sits within ``NEGATION_WINDOW`` words of the bearing.

    Position is what separates "I am **not** going north" from "I am heading
    north, you will **never** catch me". The first negates the claim; the second
    is trash talk that happens to contain a negative word, and treating it as a
    negation would silently discard almost every hint in the league.
    """
    stem = {v: k for k, v in BEARINGS.items()}[bearing]
    words = re.findall(r"[a-z']+", lowered)
    positions = [i for i, w in enumerate(words) if w.startswith(stem)]
    return any(
        word in NEGATIONS and any(0 < p - index <= NEGATION_WINDOW for p in positions)
        for index, word in enumerate(words)
    )
