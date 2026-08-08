"""The advanced Thief (TODO 8.2, 8.3). Survival is already ours to lose.

The role economics set the whole posture. Survival pays us 10 and the Cop 5;
capture pays the Cop 20 and us 5. Between two competent teams the expected
outcome of every sub-game is that we survive — so this brain is built to **not
lose**, and every tactic that costs turns has to justify itself against a
default that is already winning.

Six things happen each turn:

1. **Listen.** Fold the Cop's hint into the posterior, scaled by what its record
   says the words are worth, and fold this turn into the four profiled traits
   (`core/domain/verbal.py`).
2. **Emit.** Lay this position into our own reconstructed trail, because the
   engine does not hand it back to us and A2.5 needs it.
3. **Price the danger.** `capture_risk` at our current cell — the mirror of the
   Cop's win condition, and the input the bluff is gated on.
4. **Bluff?** Advance the false anchor's state machine, which mostly answers
   "no" and always answers "no" while anything can capture us (`thief/anchor.py`).
5. **Move.** Expectimax over the posterior about the Cop, with the trail cost
   charged at the root and the anchor's bias added on top, and near-ties settled
   by a seeded draw so a balanced position does not make us readable (8.3.1).
6. **Speak.** Decide truth or lie and which bearing to claim, priced against
   what our own trail has already given away (8.3.4).

`_pick_move` is overridden rather than `decide` — unlike the Cop we never place
a barrier, so there is no second kind of action to choose between.

The one trait we measure and deliberately do not act on
-------------------------------------------------------
§5.2's table says the Cop's **barrier rate** should drive us: a Cop that never
walls cannot catch us, so the right play against one is to stop taking risks and
run the clock. We measure it — it is public under M#15, so it costs nothing —
and nothing reads it, for a reason that only shows up when you try to test the
change: **the only opponent in this repository that exhibits the trait is one we
already beat 48 out of 48.** The baseline Cop places no barriers at all, and the
advanced Cop spends its quota, so self-play contains no game where acting on a
low barrier rate could change an outcome. Adopting behaviour we cannot measure
would be exactly the mistake 8.2.6 caught with the false anchor, where an
untested tactic looked good and cost three sub-games.

So it is reported in `OpponentProfile.describe()` and left there, in the same
posture as `Reliability.decayed_coefficient`: prepared, measured against real
opponents in Phase 9, adopted only if a league match shows it is worth
something.

This does not replace `thief/brain.py`. The baseline stays exactly as it is,
because every claim made here is an A/B result against it and a floor you have
edited is not a floor.
"""

from __future__ import annotations

from typing import Any

from core.domain.bluff import BluffPolicy, BluffSettings
from core.domain.brain_base import BrainBase, Decision, Observation
from core.domain.connectivity import exit_count
from core.domain.tiebreak import DEFAULT_EPSILON, Tiebreaker
from core.domain.trail import TrailTracker
from core.domain.verbal import VerbalLayer
from thief.anchor import AnchorPhase, FalseAnchor
from thief.evaluation import ThiefWeights, capture_risk
from thief.search import DEFAULT_DEPTH, options, scored_moves

__all__ = ["AdvancedThief"]

# How hard the false anchor pulls, per step of distance from the plateau. Small
# next to the evaluation's own terms on purpose: the bluff biases a choice
# between otherwise comparable moves, it never overrides a safety verdict.
ANCHOR_WEIGHT = 3.0


class AdvancedThief(BrainBase):
    """Evades on escape room and exit count, not on raw distance."""

    def __init__(self, name: str = "", depth: int = DEFAULT_DEPTH) -> None:
        """Build a Thief that plays competently with no configuration at all.

        Args:
            name: Display name for logs and the A/B table.
            depth: Search plies, overridden by `configure` when a config is
                available — but a default lives here so a fresh clone plays.
        """
        super().__init__(name)
        self.depth = depth
        self.weights = ThiefWeights()
        self.verbal = VerbalLayer()
        self.anchor = FalseAnchor()
        self.ties = Tiebreaker(epsilon=DEFAULT_EPSILON)
        self.phase = AnchorPhase.OFF
        self._last_step = -1
        self._sub_game = 0

    def configure(self, config: Any) -> None:
        """Adopt the `[strategy]`, `[game]` and `[pheromones]` sections.

        The decay rate and model come from the **negotiated** pheromone section
        rather than from our own preferences: the trail we reconstruct has to
        match the one the engine is actually emitting, and C-007 means either
        decay model may have been signed at the handshake.
        """
        self.depth = int(config.get("strategy.search_depth", self.depth))
        self.weights = ThiefWeights.from_config(config)
        self.ties = Tiebreaker(
            seed=int(config.get("game.seed", 0)),
            epsilon=float(config.get("strategy.tie_epsilon", DEFAULT_EPSILON)),
        )
        self.verbal = VerbalLayer(
            bluff=BluffPolicy(settings=BluffSettings.from_config(config)),
            trail=TrailTracker(
                rate=float(config.get("pheromones.pheromone_decay", 0.10)),
                model=str(config.get("pheromones.decay_model", "multiplicative")),
            ),
        )
        self.anchor = FalseAnchor(
            enabled=bool(config.get("strategy.false_anchor", False)),
            anchor_turns=int(config.get("strategy.anchor_turns", 3)),
            break_turns=int(config.get("strategy.break_turns", 5)),
        )

    def meets(self, team: str) -> None:
        """Clear the profile for a new opponent (A3.5, TODO 8.3.3).

        See `police/advanced.py` for why the ordinary boundary is the process
        and this is the guard for the case where a brain outlives it.
        """
        self.verbal.profile.for_opponent(team)

    def restart_sub_game(self, sub_game: int) -> None:
        """Bank the profile, drop the board state, and un-anchor (TODO 9.5).

        The false anchor is reset here as well as in `VerbalLayer.restart`: it
        is a multi-turn commitment to a direction, and a Thief that began a new
        sub-game still holding the previous one's anchor would spend its opening
        turns honouring a deception the opponent never heard.
        """
        self.verbal.restart(sub_game)
        self.anchor.reset()

    def _pick_move(self, observation: Observation) -> Decision:
        """Choose this turn's step and this turn's claim, and say why."""
        self._track(observation)
        belief = self.verbal.observe(observation)
        risk = capture_risk(
            observation.own_position, belief, observation.barriers, observation.board
        )
        exits = exit_count(observation.own_position, observation.barriers, observation.board)
        self.phase = self.anchor.update(observation, risk, exits)

        direction = self._choose(observation, belief)
        intent, claim = self.verbal.speak(direction, observation)
        landing = dict(options(observation.own_position, observation.barriers, observation.board))
        return Decision(
            direction,
            claim=claim,
            intent=intent,
            reason=(
                f"{self.phase.value}: {direction.value} to {landing[direction]}, "
                f"{exit_count(landing[direction], observation.barriers, observation.board)} exits, "
                f"risk {risk:.2f}, says {claim.value if claim else '-'} ({intent.value})"
            ),
        )

    def _choose(self, observation: Observation, belief):
        """Return the direction, with the anchor's bias applied to the search.

        When the tactic is OFF this is exactly the search plus the near-tie
        draw — `bias` returns 0.0 for every candidate, so a disabled bluff
        cannot perturb a decision. That matters for 8.2.6: the ablation has to
        compare two brains that differ in one thing only.
        """
        scored = scored_moves(observation, self.weights, self.verbal.trail, self.depth, belief)
        if self.phase is not AnchorPhase.OFF:
            landing = dict(options(observation.own_position, observation.barriers, observation.board))
            scored = [
                (value + self.anchor.bias(landing[direction], ANCHOR_WEIGHT), direction)
                for value, direction in scored
            ]
        return self.ties.choose(scored)

    def _track(self, observation: Observation) -> None:
        """Cross a sub-game boundary, which shows up as the step counter resetting.

        The trail, the anchor and the tie-break stream all restart; the profiled
        traits are **banked** across the six sub-games of a series and cleared
        only for a new opponent (A3.5, TODO 8.3.3). Carrying a trail across the
        boundary would have us fleeing the ghost of a previous game, and
        carrying the anchor's state would resume a bluff on a board that no
        longer exists.
        """
        if observation.step <= self._last_step:
            self._sub_game += 1
            self.verbal.restart(self._sub_game)
            self.anchor.reset()
            self.ties.restart(self._sub_game)
        self._last_step = observation.step
