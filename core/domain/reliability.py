"""How much this opponent's words have been worth (TODO 4.2.2, 4.4.2).

*Original extension — README material.*

The rulebook lets an agent lie, and says nothing about noticing. So we track it:
one coefficient per opponent, carried across the whole 6-sub-game series,
updated every time a claim can be checked against the scent field — the one
channel that cannot lie.

**A Beta posterior, not a running average.** The difference matters in the only
situation where this is decisive. After a single checked claim a mean would read
1.0 or 0.0 — total certainty from one observation, at exactly the moment an
opponent's first hint is least representative. The Beta counts start at 1/1, so
one truthful hint gives 0.67 rather than 1.0, and confidence is earned over the
series instead of asserted on turn one.

Reading the coefficient:

* **> 0.5** — believe the claim; shift belief the way it points.
* **~ 0.5** — no evidence either way, or a mixed record. Ignore the words.
* **< 0.5** — a systematic liar, which is *more* useful than a truthful
  opponent: a reliably inverted signal is still a signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.domain.actions import Direction
from core.domain.board import Position

__all__ = ["Reliability", "claim_matches_scent"]


@dataclass
class Reliability:
    """Beta(truths, lies) over one opponent's honesty.

    Attributes:
        truths: Checked claims that matched the scent. Starts at 1 — a uniform
            prior, meaning "no opinion", not "one truth observed".
        lies: Checked claims that contradicted it. Starts at 1 for the same
            reason.
        checked: How many claims we could actually verify. Reported so the
            README can say "0.31 over 24 checked hints" rather than a bare
            number that might rest on one lucky reading.
        timeline: ``(step, truthful)`` for every checked claim, in order.

    **The timeline is recorded but deliberately not acted on.** A Beta posterior
    is *exchangeable*: ten truths then two lies scores exactly the same as two
    lies then ten truths. That blindness is real, and it is exactly what a
    "build trust, then spend it at the decisive turn" opponent exploits.

    We record the ordering now so the ablation in Phase 7 can test recency
    weighting against **real opponents** rather than against sequences we
    invented. Tuning a second-order refinement on a first-order model that has
    never met an adversary would be fitting noise. See ``decayed_coefficient``.
    """

    truths: float = 1.0
    lies: float = 1.0
    checked: int = field(default=0)
    timeline: list[tuple[int, bool]] = field(default_factory=list)

    @property
    def coefficient(self) -> float:
        """Posterior mean: 0.5 with no evidence, toward 0 or 1 with it."""
        return self.truths / (self.truths + self.lies)

    @property
    def trust(self) -> float:
        """Signed trust in [-1, 1]. Negative means *invert what they say*.

        Zero is the honest answer at the start, and it makes the hint update a
        no-op until the opponent has actually told us something about
        themselves — which is the correct behaviour on turn one against a
        stranger.
        """
        return 2.0 * self.coefficient - 1.0

    def record(self, truthful: bool, weight: float = 1.0, step: int = 0) -> None:
        """Fold in one checked claim.

        Args:
            truthful: Whether the claim matched the scent field.
            weight: The parser's confidence. A claim we barely understood must
                not move the coefficient as far as an unambiguous one, or a
                vague opponent could dilute their own record on purpose.
            step: The turn, recorded for the timeline. Not used in the score.
        """
        if truthful:
            self.truths += weight
        else:
            self.lies += weight
        self.checked += 1
        self.timeline.append((step, truthful))

    def decayed_coefficient(self, gamma: float = 0.85) -> float:
        """Recency-weighted score. **Measurement only — nothing reads this yet.**

        Replays the timeline with each prior observation discounted by *gamma*
        before the new one lands, so a betrayal after a long honest run drops
        the score faster than the exchangeable Beta does.

        Kept as a pure function of recorded history rather than wired into
        ``coefficient``, so Phase 7 can A/B the two against real opponents. The
        cost of being wrong here is asymmetric: over-reacting to one late lie
        would have us invert a mostly-honest opponent's hints for the rest of a
        sub-game, which is worse than the blindness it fixes.
        """
        truths = lies = 1.0
        for _, truthful in self.timeline:
            truths, lies = gamma * truths, gamma * lies
            if truthful:
                truths += 1.0
            else:
                lies += 1.0
        return truths / (truths + lies)

    def turns_since_last_lie(self, now: int) -> int | None:
        """Turns since the last caught lie, or None if they have never lied."""
        lied = [step for step, truthful in self.timeline if not truthful]
        return now - lied[-1] if lied else None

    def describe(self) -> str:
        """One line for the log and the post-match report."""
        verdict = "truthful" if self.coefficient > 0.6 else (
            "deceptive" if self.coefficient < 0.4 else "mixed"
        )
        return f"{self.coefficient:.2f} ({verdict}, {self.checked} checked)"


def claim_matches_scent(
    claim: Direction, before: Position | None, after: Position | None
) -> bool | None:
    """Did the opponent move the way they said they would?

    Args:
        claim: The bearing their hint asserted.
        before: Where the scent peak put them last turn.
        after: Where it puts them now.

    Returns:
        True, False, or **None when the claim cannot be checked** — no peak
        either turn, or they did not move at all. None is not a soft "False":
        scoring an unverifiable claim as a lie would let a stationary opponent
        accumulate a false reputation, so it must be excluded from the record
        rather than folded in as evidence.
    """
    if before is None or after is None or before == after:
        return None

    d_row, d_col = after[0] - before[0], after[1] - before[1]
    moved = {
        Direction.N: d_row < 0,
        Direction.S: d_row > 0,
        Direction.W: d_col < 0,
        Direction.E: d_col > 0,
    }
    return moved.get(claim, False)
