"""Four traits, confidence-gated, banked across a series (TODO 8.3.2, 8.3.3).

Six sub-games against one team is roughly **200 observed steps**. That is enough
to estimate three or four coarse traits and nowhere near enough to fit anything
subtle, so A3.6 caps the count at four and A3.4 puts a sample gate in front of
every one. Below its gate a trait answers ``None`` — never a default value.
"Unknown" and "measured as zero" lead to opposite behaviour, and a model that
always answers is worse than one that abstains.

The four, and where each comes from
-----------------------------------
* **Movement style** — from the trajectory of our own belief peak. We never see
  the opponent (M#8), so this is an estimate built on estimates, which is
  precisely why it is a three-way category rather than a number anything
  multiplies by.
* **Barrier rate** — from `barriers_remaining`, which every peer must declare
  truthfully with its exact cell (M#15). Public arithmetic, free intelligence,
  and the only trait here that cannot be wrong.
* **Hint responsiveness** — how much their next move correlates with what *we*
  just claimed. Drives 8.3.5: an opponent who ignores hints makes the verbal
  layer pure waste.
* **Reliability `r`** — their claims against the scent field, held as the Beta
  posterior in `core/domain/reliability.py`.

Why flee and orbit are one trait and not two
--------------------------------------------
`police/phases.py` already measured two things — how often the peak opened the
distance, and how often it returned to a cell it had been on. Counting them
separately alongside the four above makes five and breaches A3.6. They are read
here as **two thresholds on one measured quantity**: the peak trajectory, which
is a single observation stream with a single confidence gate. Recorded in
`docs/CONTRADICTIONS.md` C-016.

Resetting (A3.5, TODO 8.3.3)
----------------------------
Traits **accumulate across the six sub-games** of one series and are **cleared
for a new opponent**, because teams may change code between matches. The two
scopes are different, so the state is split: banked counters survive a sub-game
boundary, while the per-sub-game trajectory — the last peak, and the set of
cells already visited — does not. Carrying those across would score a cell
"revisited" because a *previous game* passed through it, which says nothing at
all about whether this opponent circles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from core.domain.actions import DELTAS, Direction
from core.domain.board import Position
from core.domain.reliability import Reliability, claim_matches_scent

__all__ = [
    "MovementStyle",
    "OpponentProfile",
    "TRAITS",
    "MIN_MOVEMENT_SAMPLES",
    "MIN_VERBAL_SAMPLES",
]

# **The four, by name, so A3.6's cap is checkable rather than asserted.**
# `[strategy] max_profiled_traits` shipped in both configs from Phase 0 and was
# read by nothing, which is the weakest possible form of a limit: a fifth trait
# could have been added without a single test noticing. Listing them here lets
# `test_opponent_profile.py` compare this tuple against the shipped config, so
# the number in the file and the number in the code cannot drift apart.
TRAITS: tuple[str, ...] = ("movement_style", "barrier_rate", "hint_responsiveness", "reliability")

# One sub-game's worth of peaks. Enough to separate a fleer from a circler,
# nowhere near enough to fit anything subtle — which is the point.
MIN_MOVEMENT_SAMPLES = 6

# The verbal channel produces at most one usable sample per turn and often none,
# so its gate is lower. Four checked claims is still two more than the number at
# which a running average would read 1.00 and call itself certain.
MIN_VERBAL_SAMPLES = 4


class MovementStyle(str, Enum):
    """The coarse movement trait the phasing is gated on (A1.12)."""

    UNKNOWN = "UNKNOWN"
    FLEE_GREEDY = "FLEE_GREEDY"
    ORBITER = "ORBITER"


@dataclass
class OpponentProfile:
    """What we have learned about one opponent, over one series.

    Attributes:
        team: Whose profile this is. Compared on every observation so a new
            opponent cannot inherit the last one's reputation (A3.5).
        transitions: Peak-to-peak steps observed, banked across sub-games.
        away: How many of those opened the distance between us.
        visits: Peaks recorded, banked.
        revisits: Peaks that landed on a cell this sub-game had already used.
        barrier_turns: Turns on which we could see the opponent's quota.
        barriers_seen: Walls they actually spent over those turns.
        aligned: Turns where their next step ran *with* the bearing we claimed.
        opposed: Turns where it ran against it.
        neutral: Turns where it ran across it, which is the null result.
        reliability: Their honesty, as a Beta posterior.
    """

    team: str = ""
    transitions: int = 0
    away: int = 0
    visits: int = 0
    revisits: int = 0
    barrier_turns: int = 0
    barriers_seen: int = 0
    aligned: int = 0
    opposed: int = 0
    neutral: int = 0
    reliability: Reliability = field(default_factory=Reliability)
    _seen: set[Position] = field(default_factory=set, repr=False)
    _last_peak: Position | None = field(default=None, repr=False)
    _last_quota: int | None = field(default=None, repr=False)

    # --- lifecycle ---------------------------------------------------------

    def for_opponent(self, team: str) -> None:
        """Clear everything if *team* is not who we have been profiling (A3.5).

        A no-op when the name is unchanged, so this is safe to call every turn —
        which is what makes it impossible to forget on the one path that matters.
        """
        if team == self.team:
            return
        self.__dict__.update(OpponentProfile(team=team).__dict__)

    def end_sub_game(self) -> None:
        """Bank the traits and drop the trajectory. See the module docstring."""
        self._seen = set()
        self._last_peak = None
        self._last_quota = None

    # --- observation -------------------------------------------------------

    def observe_peak(self, peak: Position | None, ours: Position) -> None:
        """Record this turn's believed opponent cell. Free, so it happens always.

        A ``None`` peak — no belief at all — is skipped rather than recorded as a
        stationary opponent, which would drag the flee rate toward zero and
        misclassify a fleer as a circler on exactly the turns we know least.
        """
        if peak is None:
            return
        if self._last_peak is not None:
            self.transitions += 1
            self.away += _distance(peak, ours) > _distance(self._last_peak, ours)
        self.visits += 1
        self.revisits += peak in self._seen
        self._seen.add(peak)
        self._last_peak = peak

    def observe_quota(self, remaining: int) -> None:
        """Record the opponent's declared barrier count (M#15).

        Counted as a **rate over turns we watched**, not as a fraction of the
        quota: a Cop that has spent 2 of 14 in three turns and one that spent 2
        in thirty are opposite opponents, and only the denominator says so.
        """
        if self._last_quota is not None and remaining <= self._last_quota:
            self.barrier_turns += 1
            self.barriers_seen += self._last_quota - remaining
        self._last_quota = remaining

    def observe_response(self, claimed: Direction | None, before: Position | None,
                         after: Position | None) -> None:
        """Record whether their next step ran with or against what we claimed.

        Args:
            claimed: The bearing *we* asserted last turn, or None if we said
                nothing directional — in which case there is nothing to correlate.
            before: Where the peak sat when we spoke.
            after: Where it sits now.

        **Direction of the reaction is deliberately not assumed.** A listening
        Thief runs from what we claim and a listening Cop runs toward it, so
        scoring "did they do the expected thing" would need a model of their
        role *and* their policy. Counting both ways and reporting the *imbalance*
        measures the only thing 8.3.5 needs: whether our words move them at all.

        A step perpendicular to the claim is recorded as neither, and it has to
        be counted rather than discarded. Two of the four bearings are always
        perpendicular, so an opponent moving at random lands there half the
        time; dropping those samples would leave a one-in-four along against a
        three-in-four not-along and report a coin-flipping opponent as strongly
        responsive.
        """
        if claimed is None or before is None or after is None or before == after:
            return
        d_row, d_col = after[0] - before[0], after[1] - before[1]
        claim_row, claim_col = DELTAS[claimed]
        projection = d_row * claim_row + d_col * claim_col
        self.aligned += projection > 0
        self.opposed += projection < 0
        self.neutral += projection == 0

    def observe_hint(self, claimed: Direction | None, before: Position | None,
                     after: Position | None, confidence: float, step: int) -> None:
        """Check one of *their* claims against the scent and bank the verdict."""
        if claimed is None:
            return
        truthful = claim_matches_scent(claimed, before, after)
        if truthful is not None:
            self.reliability.record(truthful, weight=confidence, step=step)

    # --- gated traits ------------------------------------------------------

    def style(self, flee_rate: float, orbit_rate: float) -> MovementStyle:
        """Classify the movement trait, or decline to (A3.4).

        The fleer reading wins when both fire: a greedy fleer on a finite board
        eventually revisits cells too, so revisiting is the weaker evidence.
        """
        if self.transitions < MIN_MOVEMENT_SAMPLES:
            return MovementStyle.UNKNOWN
        if self.flee_fraction >= flee_rate:
            return MovementStyle.FLEE_GREEDY
        if self.orbit_fraction >= orbit_rate:
            return MovementStyle.ORBITER
        return MovementStyle.UNKNOWN

    @property
    def flee_fraction(self) -> float:
        """Fraction of observed steps that opened the distance."""
        return self.away / self.transitions if self.transitions else 0.0

    @property
    def orbit_fraction(self) -> float:
        """Fraction of observed peaks that landed on an already-used cell."""
        return self.revisits / self.visits if self.visits else 0.0

    @property
    def barrier_rate(self) -> float | None:
        """Walls per watched turn, or None below the gate.

        Near zero says a Cop that cannot catch us, which A3.2's table turns into
        a Thief that stops taking risks and runs the clock.
        """
        if self.barrier_turns < MIN_MOVEMENT_SAMPLES:
            return None
        return self.barriers_seen / self.barrier_turns

    @property
    def hint_responsiveness(self) -> float | None:
        """How much our words move them, in [0, 1], or None below the gate.

        The imbalance between aligned and opposed responses, over every observed
        response including the perpendicular ones. An opponent who never reads
        our hints answers our claims with moves that are uncorrelated with them,
        so the two counts converge and this goes to zero — which is 8.3.5's
        trigger and the reason it is an absolute value rather than a signed one.
        """
        total = self.aligned + self.opposed + self.neutral
        if total < MIN_VERBAL_SAMPLES:
            return None
        return abs(self.aligned - self.opposed) / total

    def describe(self) -> str:
        """One line for the match log and the post-match report."""
        rate = self.barrier_rate
        listens = self.hint_responsiveness
        return (
            f"{self.team or 'opponent'}: flee {self.flee_fraction:.2f}, "
            f"orbit {self.orbit_fraction:.2f}, "
            f"walls/turn {'-' if rate is None else f'{rate:.2f}'}, "
            f"listens {'-' if listens is None else f'{listens:.2f}'}, "
            f"reliability {self.reliability.describe()}"
        )


def _distance(first: Position, second: Position) -> int:
    """Manhattan distance. Walls are irrelevant to *which way they went*."""
    return abs(first[0] - second[0]) + abs(first[1] - second[1])
