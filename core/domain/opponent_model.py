"""What we learn about one opponent across the 6-sub-game series (TODO 4.4.3).

*Original extension — README material.*

We meet the same opponent six times: three sub-games as Cop, three as Thief. So
every move they make is a sample from a policy we will face again, and the
league's own scoring says which samples are worth most — **a capture pays the
Cop 20 and the Thief 5, while survival pays the Thief 10 and the Cop 5.** Our
Cop games are worth double, and it is in the Cop games that we observe *their*
Thief. Modelling their Thief is therefore the highest-value inference available.

**Three things this deliberately does not do.**

*It never sacrifices a sub-game to probe.* Recording is free; a deliberately
weak move to test their response risks 15 points to buy information worth less.
We play to win every game and learn from what happens anyway.

*It does not try to predict from board state.* Their move depends on their
belief about us, which we cannot see — so the same board can legitimately
produce different moves, and a state→move lookup would be confidently wrong.
What we model instead is the **conditional response**: given roughly where we
are relative to them, which way do they tend to go? That marginalises over the
hidden belief rather than pretending to reconstruct it.

*It does not claim significance it has not earned.* Three sub-games is about a
hundred observations. That is far too few to learn a policy, and quite enough to
**test a hypothesis** — which is why ``flee_rate`` exists. If their Thief simply
maximises distance, as the book's baseline does and as most teams will build,
that single fact is worth more than any model we could fit.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from core.domain.actions import Direction
from core.domain.board import Position

__all__ = ["OpponentModel", "Sighting"]

# Below this many samples in a bucket we decline to predict at all. Guessing
# from two observations is how a model becomes a liability rather than an edge.
MIN_SAMPLES = 4


@dataclass(frozen=True)
class Sighting:
    """One observed move: where they were, where we were, what they did."""

    theirs: Position
    ours: Position
    move: Direction


def _quadrant(theirs: Position, ours: Position) -> tuple[int, int]:
    """Bucket by the *sign* of the offset from us to them, not the distance.

    Nine buckets, so a hundred observations give roughly a dozen each. Bucketing
    by exact offset would give 49 buckets and one sample apiece — a table that
    memorises the sample instead of describing the policy.
    """
    d_row, d_col = theirs[0] - ours[0], theirs[1] - ours[1]
    return ((d_row > 0) - (d_row < 0), (d_col > 0) - (d_col < 0))


@dataclass
class OpponentModel:
    """A frequency model of one opponent, in one role, across the series.

    Attributes:
        role: Which role we watched them play — their Cop and their Thief are
            different programs and must never share a model.
        sightings: Every observed move, in order.
    """

    role: str
    sightings: list[Sighting] = field(default_factory=list)

    def record(self, theirs: Position, ours: Position, move: Direction) -> None:
        """Note one move. Free, so it happens in every sub-game."""
        self.sightings.append(Sighting(theirs, ours, move))

    @property
    def flee_rate(self) -> float | None:
        """Fraction of moves that increased the distance between us.

        **The cheapest high-value hypothesis, and the one to check first.** The
        book's baseline Thief maximises distance, and most teams will build
        something close to it. A flee rate near 1.0 says their Thief is greedy,
        which makes it herdable: a greedy fleer can be walked into a corner,
        because it will always take the bait of the furthest cell.

        None until there is anything to report — never 0.0, which would read as
        "they never flee" rather than "we have not looked".
        """
        if not self.sightings:
            return None
        fled = sum(1 for s in self.sightings if _increased(s))
        return fled / len(self.sightings)

    @property
    def stay_rate(self) -> float | None:
        """How often they hold position. A high rate suggests a cornered or
        cycle-seeking policy rather than a fleeing one."""
        if not self.sightings:
            return None
        return sum(1 for s in self.sightings if s.move is Direction.STAY) / len(self.sightings)

    def predict(self, theirs: Position, ours: Position) -> tuple[Direction | None, float]:
        """Return their most likely move and how concentrated that guess is.

        Returns ``(None, 0.0)`` when the bucket is too thin to speak. A model
        that always answers is worse than one that abstains: the belief filter
        already has the scent field, which cannot lie, and a confident wrong
        prediction actively degrades it.
        """
        bucket = [s for s in self.sightings if _quadrant(s.theirs, s.ours) == _quadrant(theirs, ours)]
        if len(bucket) < MIN_SAMPLES:
            return None, 0.0
        counts = Counter(s.move for s in bucket)
        move, hits = counts.most_common(1)[0]
        return move, hits / len(bucket)

    @property
    def predictability(self) -> float:
        """Mean confidence across buckets — 0.25 is a coin toss, 1.0 is a robot.

        Reported in the match log so the README can say *how modellable* an
        opponent was, rather than asserting that modelling worked.
        """
        buckets: dict[tuple[int, int], Counter] = {}
        for sighting in self.sightings:
            key = _quadrant(sighting.theirs, sighting.ours)
            buckets.setdefault(key, Counter())[sighting.move] += 1
        usable = [c for c in buckets.values() if sum(c.values()) >= MIN_SAMPLES]
        if not usable:
            return 0.0
        return sum(c.most_common(1)[0][1] / sum(c.values()) for c in usable) / len(usable)

    def describe(self) -> str:
        """One line for the log and the post-match report."""
        if not self.sightings:
            return f"{self.role}: no sightings yet"
        return (
            f"{self.role}: {len(self.sightings)} moves, "
            f"flee {self.flee_rate:.2f}, stay {self.stay_rate:.2f}, "
            f"predictability {self.predictability:.2f}"
        )


def _increased(sighting: Sighting) -> bool:
    """Whether this move took them further from us in Manhattan distance."""
    deltas = {
        Direction.N: (-1, 0),
        Direction.S: (1, 0),
        Direction.E: (0, 1),
        Direction.W: (0, -1),
        Direction.STAY: (0, 0),
    }
    d_row, d_col = deltas[sighting.move]
    landed = (sighting.theirs[0] + d_row, sighting.theirs[1] + d_col)
    before = abs(sighting.theirs[0] - sighting.ours[0]) + abs(sighting.theirs[1] - sighting.ours[1])
    after = abs(landed[0] - sighting.ours[0]) + abs(landed[1] - sighting.ours[1])
    return after > before
