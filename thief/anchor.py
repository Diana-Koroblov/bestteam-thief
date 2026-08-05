"""The false anchor: feed the trail, then leave (TODO 8.2.5; PRD advanced §4.4).

**Built, measured, and shipped disabled.** 8.2.6 required its value to be settled
by ablation rather than by argument, and the ablation rejected it. The code stays
because the measurement is the deliverable and because a tactic deleted is a
tactic that gets re-proposed; `[strategy] false_anchor` turns it back on.

What the measurement found, over 48 openings against our own advanced Cop::

    anchor OFF   40/48 survived   mean 30.42 steps
    anchor ON    37/48 survived   mean 29.17 steps

It loses three sub-games net. ⚠️ A narrower 16-opening sweep showed 12/16 → 16/16
and would have had us **adopt** it — the smaller set happened to contain exactly
the games it fixes and none it breaks.

**Why it cannot work as §4.4 describes it.** The section assumes a trail can be
*fed*: "build a strong trail in one region, then break away". But `scent.merge`
keeps the **maximum**, so re-emitting on a cell we already occupy restores the
values already there and adds nothing. Five turns of standing still produces a
field byte-for-byte identical to one turn — 25 cells, total intensity 7.14 —
while five turns of *moving* leaves 34 cells and 12.51. Movement accumulates
scent; repetition does not. So the turns bought no extra ambiguity, and "those
turns can be bought cheaply" is the part that turned out to be false: against a
Cop that is closing, every one of them is distance not gained.

A2.10 is enforced literally rather than as a vibe: `payoff` is the head start the
break can actually convert, bounded by how far the Cop has to come, and `cost` is
the turns spent. Below break-even the tactic does not fire — which, given the
above, is most of the time even when it is switched on.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.domain.board import Position
from core.domain.brain_base import Observation

__all__ = ["AnchorPhase", "FalseAnchor"]


class AnchorPhase(str, Enum):
    """What the tactic is doing this turn."""

    OFF = "OFF"
    ANCHORING = "ANCHORING"
    BREAKING = "BREAKING"


@dataclass
class FalseAnchor:
    """The two-stage bluff, and the arithmetic that decides whether to run it.

    Attributes:
        enabled: Off unless config says otherwise (8.2.6).
        anchor_turns: Turns spent building the plateau. The cost side of A2.10.
        break_turns: Turns spent running afterwards. Caps the payoff — beyond
            this the trail we laid on the way out dominates anyway.
        min_exits: Refuse to start anywhere that could be closed while we stand
            still. Standing in a pocket to run a bluff is how a Thief loses a
            game it had already won.
        max_risk: The most believed capture probability we will stand still
            under. **A policy threshold, not an epsilon** — but it started life
            as `risk <= 0.0`, which never once fired: `belief.normalise` leaves
            unreachable cells holding denormals around 1e-18, so an exact-zero
            comparison is false on a board where nothing can reach us. 2% is
            about one turn in fifty, measured against a whole game where the
            observed risk never exceeded 0.6%.
        phase: Current stage.
        remaining: Turns left in this stage.
        cell: Where the plateau is being built. What BREAKING runs away from.
    """

    enabled: bool = False
    anchor_turns: int = 3
    break_turns: int = 5
    min_exits: int = 3
    max_risk: float = 0.02
    phase: AnchorPhase = AnchorPhase.OFF
    remaining: int = 0
    cell: Position | None = None

    def reset(self) -> None:
        """Clear the state machine at a sub-game boundary."""
        self.phase = AnchorPhase.OFF
        self.remaining = 0
        self.cell = None

    def payoff(self, observation: Observation) -> int:
        """Return the head start a break could actually convert, in turns.

        Bounded by the distance the Cop must travel: against a Cop three steps
        away there is no ten-turn head start to win, however confused it is. An
        unbounded estimate is what turns a tactic into wishful thinking.
        """
        cop = observation.most_likely_opponent()
        if cop is None:
            return 0
        here = observation.own_position
        distance = abs(cop[0] - here[0]) + abs(cop[1] - here[1])
        return min(distance, self.break_turns)

    def worth_running(self, observation: Observation, risk: float, exits: int) -> bool:
        """Whether A2.10's payoff-over-cost test passes right now.

        Three conditions, and all three are refusals rather than preferences:

        * the tactic is switched on at all;
        * **nothing can capture us next turn.** Standing still is the loudest
          thing a Thief can do, and doing it under threat is indefensible;
        * we have room to stand in, and the head start beats the turns it costs.
        """
        return (
            self.enabled
            and risk <= self.max_risk
            and exits >= self.min_exits
            and self.payoff(observation) > self.anchor_turns
        )

    def update(self, observation: Observation, risk: float, exits: int) -> AnchorPhase:
        """Advance the state machine one turn and return the stage now in force.

        **Danger cancels the bluff immediately, in either stage.** A tactic that
        ran to completion while the Cop closed in would be a scripted sequence,
        and A3.2's rule against fixed schedules exists precisely because a
        scripted Thief is a readable one.
        """
        if self.phase is not AnchorPhase.OFF and (risk > self.max_risk or not self.enabled):
            self.reset()
            return self.phase

        if self.phase is AnchorPhase.OFF:
            if self.worth_running(observation, risk, exits):
                self.phase = AnchorPhase.ANCHORING
                self.remaining = self.anchor_turns
                self.cell = observation.own_position
            return self.phase

        self.remaining -= 1
        if self.remaining <= 0:
            if self.phase is AnchorPhase.ANCHORING:
                self.phase = AnchorPhase.BREAKING
                self.remaining = self.break_turns
            else:
                self.reset()
        return self.phase

    def bias(self, destination: Position, weight: float) -> float:
        """Return the score adjustment this tactic applies to a candidate move.

        Sign flips between the stages, which is the tactic in one line: while
        ANCHORING we *want* to be near the plateau and loud, and while BREAKING
        we want every step to open distance from it. OFF contributes nothing, so
        a disabled tactic cannot perturb an otherwise identical decision.
        """
        if self.cell is None or self.phase is AnchorPhase.OFF:
            return 0.0
        away = abs(destination[0] - self.cell[0]) + abs(destination[1] - self.cell[1])
        return weight * (-away if self.phase is AnchorPhase.ANCHORING else away)
