"""Near-ties, resolved by a seeded draw (TODO 8.3.1; PRD advanced §5.1 A3.1).

**Unexploitability is the floor; exploitation is upside.** If we profile the
opponent and they profile us, the recursion has no bottom — so the first thing
to get right is not being readable, and a deterministic tie-break is exactly the
signature a competent opponent learns for free. Our searches break ties on the
fixed ordering from `options`, which puts STAY first and then N, S, E, W: an
opponent who noticed would know our next move on every turn where the position
is genuinely balanced, without modelling anything at all.

**Why this is not inside the search.** `best_move` and `expectimax` stay
strictly deterministic. A search that wobbled internally would return different
values for the same position and make our own log unverifiable — a much worse
problem than being readable. So the search reports every candidate with its
value, and the *choice among near-equals* happens once, here, at the point where
the brain commits to an action.

**Seeded, and the seed is recorded** (§6). Randomness that cannot be replayed
would break the one property the whole project rests on: two peers re-reading a
log must reach the same conclusions about what happened. `Random(seed)` is a
Mersenne Twister with a stated integer seed, which produces the same stream on
both machines, and `core/report/match_log.py` writes the seed beside the steps
it produced.

**ε is a real threshold, not a formality.** Set it too wide and the brain throws
away genuine advantage to look unpredictable; set it to zero and only exact
float equality qualifies, which almost never happens. It is therefore config-
driven and settled by the benchmark (8.3.6) rather than by argument, and
``epsilon <= 0`` disables the draw entirely so the ablation arm is exact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import TypeVar

__all__ = ["Tiebreaker", "DEFAULT_EPSILON"]

Candidate = TypeVar("Candidate")

# In evaluation units. The Cop charges 2.0 per expected step of distance and the
# Thief 1.0, so half a unit is well under one step of real progress — a tie in
# anything but the arithmetic.
DEFAULT_EPSILON = 0.5


@dataclass
class Tiebreaker:
    """A seeded chooser over actions that score within ε of the best.

    Attributes:
        seed: The recorded seed. Ours alone and never negotiated — it is not
            part of the physics, only of how we settle a coin toss.
        epsilon: How close two scores must be to count as tied. ``<= 0``
            disables the draw and restores the fixed ordering.
        draws: How many times a draw was actually taken, for the log. Reported
            because "the randomiser is on" and "the randomiser ever fired" are
            different claims, and only the second one is evidence.
    """

    seed: int = 0
    epsilon: float = DEFAULT_EPSILON
    draws: int = 0
    _rng: Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Build the generator from the recorded seed."""
        self._rng = Random(self.seed)

    def restart(self, sub_game: int) -> None:
        """Re-seed for a new sub-game, deterministically.

        ``seed + sub_game`` rather than a continuing stream, so **one sub-game
        replays on its own**. A single stream carried across six games would
        make game 4 reproducible only by replaying games 1 to 3 first, and the
        artefact we publish is one log per sub-game.
        """
        self._rng = Random(self.seed + sub_game)
        self.draws = 0

    def choose(self, scored: list[tuple[float, Candidate]]) -> Candidate:
        """Return the winner, drawing at random among near-equals.

        Args:
            scored: ``(value, candidate)`` in the search's fixed order. Higher
                is better. Must be non-empty.

        The fixed order is what makes the disabled path identical to the old
        behaviour: with ``epsilon <= 0`` the first candidate holding the best
        value wins, which is exactly what ``max`` with an index tie-break did.
        """
        best = max(value for value, _ in scored)
        near = [candidate for value, candidate in scored if best - value <= self.epsilon]
        if self.epsilon <= 0.0 or len(near) <= 1:
            return near[0]
        self.draws += 1
        return near[self._rng.randrange(len(near))]
