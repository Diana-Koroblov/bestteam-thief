"""Cheap truth, expensive lies (TODO 8.3.4, 8.3.5; PRD advanced §5.3).

Honesty is not free — the hint describes our own movement, so a truthful one
genuinely helps the opponent. But **the cost varies, and the variation is the
lever**. A3.7 names the quantity exactly: how much the claim would shift their
belief *beyond what our scent trail already reveals*.

Measuring that without modelling their filter
---------------------------------------------
We cannot see the opponent's posterior, and inventing one would be scoring our
bluff against a filter nobody is running. What we *can* compute exactly is the
input to their filter, because we reconstruct our own emission every turn
(`core/domain/trail.py`). So the reading is `1 - bearing_leak`: how plainly our
own field already announces the direction we are about to move in.

* **Trail already pointing that way → low information value.** Three turns north
  leaves the field loud behind us and silent ahead, and anyone reading the
  gradient knows our heading. Saying it out loud costs nothing they did not
  have, and it banks credibility for free (A3.8).
* **Trail saying nothing about our bearing → high information value.** A turn, a
  reversal, a circled cell: naming the bearing hands them something the field
  does not contain. This is the turn where a lie is worth telling (A3.9).

Which is the useful shape: we are honest exactly when honesty is cheap, and the
credibility that buys is spent on the turns where our words are worth something.

**The first version of this measured the wrong thing and would have shipped a
tactic that never fired.** It read the trail's strength at our own cell — but the
trail is updated before the claim is chosen, so that cell always carries a
full-strength deposit we laid this turn. Every turn priced as "they already
know", no lie was ever eligible, and the result would have looked exactly like a
policy that does nothing rather than one that never ran. A single deposit reveals
a *position*; only the asymmetry between deposits reveals a *bearing*.

Credibility, and why our own record is the right one to use
------------------------------------------------------------
A3.9 weights the lie by "the credibility banked so far". The strictly correct
quantity is *their* estimate of *our* reliability, which we cannot see. We use
our own declared record instead — a `Reliability` over what we said, updated as
we say it — which assumes they caught every lie. That is the conservative
direction: it makes us lie less often than a perfectly-informed policy would,
and the failure mode of being too honest is bounded while the failure mode of
being caught out repeatedly is a channel that never works again.

**The weight is `trust`, not the coefficient, and the difference is the whole
policy.** Drawing against the raw coefficient looks right and settles in the
worst possible place: lie with probability *p* and the record converges to
*p = 0.5*, which is precisely the "mixed" reading `reliability.py` calls
worthless. An opponent facing a coin-flipping liar ignores every word we say,
so both our lies *and* our truths stop working, and the bank we spent turns
filling buys nothing.

`trust` is `2·coefficient − 1`: zero at a mixed record, rising toward 1 as the
record turns honest. Drawing against it means we **cannot lie until credibility
has actually been banked** — on turn one against a stranger the probability is
exactly 0 — and the loop settles near two truths to one lie, a reputation
comfortably on the believable side of 0.5. Which is the state A3.9 wants: words
they act on, and the option to spend that once.

The loop needs no schedule (A3.2): a lie lowers the weight and makes the next
lie less likely; truths raise it back. Nothing here reads the turn number.

What we claim when we lie
-------------------------
The reverse bearing. It is derived from the move we actually chose, so it is
board-state-driven rather than scripted, and against a distance-maximising
opponent it is exactly A3.10's herding lie: a Thief told the Cop is going north
opens the distance southward, into the half of the board we picked.

A3.11 is structural, not a rule this file follows: the flag and the bearing are
returned to the **brain**, which seals them into the commitment. The language
layer is handed the result and never consulted about it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Any

from core.domain.actions import DELTAS, Direction, opposite
from core.domain.board import Board, Position
from core.domain.intent import Intent
from core.domain.opponent_profile import OpponentProfile
from core.domain.reliability import Reliability
from core.domain.trail import TrailTracker

__all__ = ["BluffSettings", "BluffPolicy", "information_value"]


@dataclass(frozen=True)
class BluffSettings:
    """Thresholds for the verbal layer. Ours alone, never negotiated.

    Attributes:
        enabled: False pins every turn to the plain truth, which is the control
            arm the ablation in 8.3.6 measures against.
        cheap_truth: Information value at or below which the truth is free.
            **Set from the measured distribution, not from taste.** Claiming the
            direction we have actually been walking reads 1.00 after two steps,
            0.69 after three, 0.54 after four and 0.31 after six, while a turn
            reads 0.74, a reversal 1.00 and standing still 1.00. A threshold of
            0.6 therefore separates "we are in a straight line and the field has
            already said so" from "we are about to do something the field does
            not predict", which is exactly the line A3.8 and A3.9 draw.
        responsiveness_floor: Measured hint-responsiveness at or below which we
            stop claiming anything at all (A3.12, TODO 8.3.5).
        seed: Recorded, so a lie is reproducible from the log like everything
            else. Seeded separately from the movement tie-break so that turning
            the verbal layer on cannot perturb which moves get chosen — the two
            ablations have to be independent to mean anything.
    """

    enabled: bool = True
    cheap_truth: float = 0.60
    responsiveness_floor: float = 0.10
    seed: int = 0

    @classmethod
    def from_config(cls, config: Any) -> BluffSettings:
        """Read the `[strategy]` and `[game]` keys, defaulting to the above."""
        if config is None:
            return cls()
        return cls(
            enabled=bool(config.get("strategy.bluff_enabled", cls.enabled)),
            cheap_truth=float(config.get("strategy.cheap_truth", cls.cheap_truth)),
            responsiveness_floor=float(
                config.get("strategy.responsiveness_floor", cls.responsiveness_floor)
            ),
            seed=int(config.get("game.seed", cls.seed)),
        )


def information_value(
    trail: TrailTracker, position: Position, heading: Direction, board: Board
) -> float:
    """Return how much naming *heading* would add, in [0, 1] (A3.7).

    1.0 means our trail says nothing about which way we are going and the claim
    is pure new information; 0.0 means the field already announces it and the
    words are free. See the module docstring for why this is the right proxy.

    A bearing with no direction — STAY — is the maximum by definition: standing
    still leaves a trail that predicts nothing about a move we are not making.
    """
    step = DELTAS[heading]
    if step == (0, 0):
        return 1.0
    return 1.0 - trail.bearing_leak(position, step)


@dataclass
class BluffPolicy:
    """Decides truth or lie, and what bearing to claim.

    Attributes:
        settings: Thresholds and the recorded seed.
        honesty: Our own declared record — the credibility bank.
        lies: How many lies we have actually told, for the log. Reported
            because "the policy is on" and "the policy ever lied" are different
            claims and only the second is evidence.
    """

    settings: BluffSettings = field(default_factory=BluffSettings)
    honesty: Reliability = field(default_factory=Reliability)
    lies: int = 0
    _rng: Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Build the generator from the recorded seed."""
        self._rng = Random(self.settings.seed)

    def restart(self, sub_game: int) -> None:
        """Re-seed for a new sub-game so each one replays on its own.

        The credibility bank is deliberately **not** cleared: it accumulates
        across the six sub-games of a series exactly as the opponent's own
        memory of us does. It is `OpponentProfile.for_opponent` that draws the
        line at a new team (A3.5).
        """
        self._rng = Random(self.settings.seed + sub_game)

    def decide(
        self,
        heading: Direction,
        position: Position,
        trail: TrailTracker,
        board: Board,
        profile: OpponentProfile,
        herding: bool = False,
    ) -> tuple[Intent, Direction | None]:
        """Return the flag to seal and the bearing to claim, or no claim at all.

        Args:
            heading: The move the search actually chose. STAY yields no claim —
                it has no bearing, and inventing one would be a lie we did not
                decide to tell.
            position: Where we stand, for reading our own trail.
            trail: Our reconstructed emission.
            board: Geometry.
            profile: What we have measured about this opponent.
            herding: True when a lie has a *job* this turn — the Cop in its HERD
                phase, where A3.10 spends credibility to steer a fleeing Thief
                into the region we chose. It bypasses the cheap-truth gate and
                nothing else; the credibility draw still governs how often.

        Returns:
            ``(intent, claim)``. A ``None`` claim means we say nothing
            directional, which is legal, always truthful, and — when the
            opponent has been measured deaf — the correct use of the channel.
        """
        listens = profile.hint_responsiveness
        if not self.settings.enabled or heading is Direction.STAY:
            return Intent.TRUTH, None
        if listens is not None and listens <= self.settings.responsiveness_floor:
            # 8.3.5. Measured deaf, so the tokens and the exposure are both
            # waste. Gated on a *confident* reading: `None` here means we have
            # not looked yet, which is not the same as looking and finding zero.
            return Intent.TRUTH, None

        value = information_value(trail, position, heading, board)
        if value <= self.settings.cheap_truth and not herding:
            return self._truth(heading)
        if self._rng.random() < max(self.honesty.trust, 0.0):
            return self._lie(heading)
        return self._truth(heading)

    def _truth(self, heading: Direction) -> tuple[Intent, Direction | None]:
        """Bank one truthful claim and return it."""
        self.honesty.record(True)
        return Intent.TRUTH, heading

    def _lie(self, heading: Direction) -> tuple[Intent, Direction | None]:
        """Spend credibility on the reverse bearing.

        Falls back to the truth if the heading has no reverse. That cannot
        happen today — STAY is refused above — but a policy whose lie path could
        return ``None`` while declaring `LIE` would seal a deception flag over a
        hint that claims nothing, and the flag is what the audit reads.
        """
        claim = opposite(heading)
        if claim is None:
            return self._truth(heading)
        self.honesty.record(False)
        self.lies += 1
        return Intent.LIE, claim
