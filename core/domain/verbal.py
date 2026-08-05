"""The verbal half of a turn, for whichever role is playing (TODO 8.3.2-8.3.5).

Everything the words are worth, assembled in one place: read what they said,
score them for it, and decide what to say back. Both advanced brains own one of
these, because none of it is role-specific — a Cop and a Thief profile an
opponent the same way and lie for the same reasons.

**Why the hint update lives in the brain and not in the belief filter.**
Folding a hint into the posterior is a filter step (4.2.1.d), and the obvious
home for it is beside `predict` and `update_from_scent`. It is here instead
because the tilt is scaled by the opponent's *reliability*, which is one of the
four profiled traits (8.3.2) and is confidence-gated with the other three. A
filter that owned the coefficient would need its own copy of the profile, and
then two objects would hold an opinion about the same opponent. The filter
supplies the fact; the brain applies the argument.

**Order matters, and it is the same order the protocol delivers in.** Their
hint for turn *k* arrives with their reveal, which we read at turn *k+1* — so
the peak we held when they spoke and the peak we hold now bracket exactly the
move their claim described. Checking a claim against the wrong pair of peaks
would score honest opponents as liars at random, and the coefficient that comes
out of it is README material.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.domain.actions import Direction
from core.domain.belief_hints import update_from_hint
from core.domain.bluff import BluffPolicy
from core.domain.board import Position
from core.domain.brain_base import Observation
from core.domain.hint_parser import parse
from core.domain.intent import Intent
from core.domain.opponent_profile import OpponentProfile
from core.domain.trail import TrailTracker

__all__ = ["VerbalLayer"]


@dataclass
class VerbalLayer:
    """One opponent's reputation, our own trail, and the bluff policy.

    Attributes:
        profile: The four gated traits (8.3.2), banked across the series.
        bluff: What to say and whether it is true (8.3.4).
        trail: Our own reconstructed emission — the Thief evaluates moves
            against it and the bluff prices its claims against it.
        heard: How many hints we have already folded in, so a growing tuple is
            read exactly once.
        claimed: The bearing we asserted last turn, awaiting their reaction.
        peak: Where we believed they were when we said it.
    """

    profile: OpponentProfile = field(default_factory=OpponentProfile)
    bluff: BluffPolicy = field(default_factory=BluffPolicy)
    trail: TrailTracker = field(default_factory=TrailTracker)
    heard: int = 0
    claimed: Direction | None = None
    peak: Position | None = None

    def restart(self, sub_game: int) -> None:
        """Cross a sub-game boundary: keep the reputation, drop the board state.

        The profile banks its counters and clears its trajectory, the bluff
        re-seeds so this sub-game replays on its own, and the trail resets
        outright — carrying scent across a boundary would have us fleeing the
        ghost of a game that is over.
        """
        self.profile.end_sub_game()
        self.bluff.restart(sub_game)
        self.trail.reset()
        self.claimed = None
        self.peak = None

    def observe(self, observation: Observation) -> dict[Position, float]:
        """Fold this turn's evidence in and return the belief to search on.

        Returns the posterior with the opponent's claim applied, scaled by what
        their record says it is worth. With no record the trust is 0 and the
        tilt is a deliberate no-op: on turn one against a stranger, words are
        worth exactly nothing.
        """
        peak = observation.most_likely_opponent()
        self.profile.observe_peak(peak, observation.own_position)
        self.profile.observe_quota(observation.barriers_remaining)
        self.profile.observe_response(self.claimed, self.peak, peak)

        belief = observation.belief
        unread = observation.hints[self.heard:]
        self.heard = len(observation.hints)
        if unread:
            # **Only the newest one is used, and any backlog is discarded.**
            # A hint describes the move that has just happened, and the two
            # peaks above bracket exactly that move — they bracket nothing at
            # all for a hint from three turns ago. Normally there is no backlog;
            # one appears when a turn produced no observation, and scoring those
            # claims against the wrong pair of peaks would file honest opponents
            # as liars at random. Discarding evidence we cannot place is the
            # cheaper error, and `checked` still reports what we really used.
            hint = parse(unread[-1])
            self.profile.observe_hint(
                hint.direction, self.peak, peak, hint.confidence, observation.step
            )
            belief = update_from_hint(
                belief, hint, self.profile.reliability.trust, observation.board
            )

        self.peak = peak
        self.trail.observe(observation.own_position, observation.board)
        return belief

    def speak(
        self, heading: Direction, observation: Observation, herding: bool = False
    ) -> tuple[Intent, Direction | None]:
        """Decide what to claim about *heading*, and remember it for next turn."""
        intent, claim = self.bluff.decide(
            heading,
            observation.own_position,
            self.trail,
            observation.board,
            self.profile,
            herding,
        )
        self.claimed = claim
        return intent, claim
