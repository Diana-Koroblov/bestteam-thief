"""The advanced Thief (TODO 8.2). Survival is already ours to lose.

The role economics set the whole posture. Survival pays us 10 and the Cop 5;
capture pays the Cop 20 and us 5. Between two competent teams the expected
outcome of every sub-game is that we survive — so this brain is built to **not
lose**, and every tactic that costs turns has to justify itself against a
default that is already winning.

Four things happen each turn:

1. **Emit.** Fold this position into our own reconstructed trail, because the
   engine does not hand it back to us and A2.5 needs it (`thief/trail.py`).
2. **Price the danger.** `capture_risk` at our current cell — the mirror of the
   Cop's win condition, and the input the bluff is gated on.
3. **Bluff?** Advance the false anchor's state machine, which mostly answers
   "no" and always answers "no" while anything can capture us (`thief/anchor.py`).
4. **Move.** Expectimax over the posterior about the Cop, with the trail cost
   charged at the root and the anchor's bias added on top.

`_pick_move` is overridden rather than `decide` — unlike the Cop we never place
a barrier, so there is no second kind of action to choose between.

This does not replace `thief/brain.py`. The baseline stays exactly as it is,
because every claim made here is an A/B result against it and a floor you have
edited is not a floor.
"""

from __future__ import annotations

from typing import Any

from core.domain.brain_base import BrainBase, Decision, Observation
from core.domain.connectivity import exit_count
from thief.anchor import AnchorPhase, FalseAnchor
from thief.evaluation import ThiefWeights, capture_risk
from thief.search import DEFAULT_DEPTH, best_move, options, value_of
from thief.trail import TrailTracker

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
        self.trail = TrailTracker()
        self.anchor = FalseAnchor()
        self.phase = AnchorPhase.OFF
        self._last_step = -1

    def configure(self, config: Any) -> None:
        """Adopt the `[strategy]` and `[pheromones]` sections.

        The decay rate and model come from the **negotiated** pheromone section
        rather than from our own preferences: the trail we reconstruct has to
        match the one the engine is actually emitting, and C-007 means either
        decay model may have been signed at the handshake.
        """
        self.depth = int(config.get("strategy.search_depth", self.depth))
        self.weights = ThiefWeights.from_config(config)
        self.trail = TrailTracker(
            rate=float(config.get("pheromones.pheromone_decay", 0.10)),
            model=str(config.get("pheromones.decay_model", "multiplicative")),
        )
        self.anchor = FalseAnchor(
            enabled=bool(config.get("strategy.false_anchor", False)),
            anchor_turns=int(config.get("strategy.anchor_turns", 3)),
            break_turns=int(config.get("strategy.break_turns", 5)),
        )

    def _pick_move(self, observation: Observation) -> Decision:
        """Choose this turn's step, and say why in one line for the log."""
        self._track(observation)
        risk = capture_risk(
            observation.own_position, observation.belief, observation.barriers, observation.board
        )
        exits = exit_count(observation.own_position, observation.barriers, observation.board)
        self.phase = self.anchor.update(observation, risk, exits)

        direction = self._choose(observation)
        landing = dict(options(observation.own_position, observation.barriers, observation.board))
        return Decision(
            direction,
            reason=(
                f"{self.phase.value}: {direction.value} to {landing[direction]}, "
                f"{exit_count(landing[direction], observation.barriers, observation.board)} exits, "
                f"risk {risk:.2f}"
            ),
        )

    def _choose(self, observation: Observation):
        """Return the direction, with the anchor's bias applied to the search.

        When the tactic is OFF this is exactly `best_move` — `bias` returns 0.0
        for every candidate, so a disabled bluff cannot perturb a decision. That
        matters for 8.2.6: the ablation has to compare two brains that differ in
        one thing only.
        """
        direction, _ = best_move(observation, self.weights, self.trail, self.depth)
        if self.phase is AnchorPhase.OFF:
            return direction

        legal = options(observation.own_position, observation.barriers, observation.board)
        scored = [
            (
                self._value(observation, cell) + self.anchor.bias(cell, ANCHOR_WEIGHT),
                -index,
                heading,
            )
            for index, (heading, cell) in enumerate(legal)
        ]
        return max(scored, key=lambda entry: (entry[0], entry[1]))[2]

    def _value(self, observation: Observation, cell) -> float:
        """Return a candidate's search value, trail cost included.

        Shares `best_move`'s arithmetic by construction rather than by copy: a
        second scoring path that drifted from the first would make the anchor
        look better or worse than it is, and 8.2.6 exists to measure exactly
        that difference.
        """
        value = value_of(
            cell,
            observation.belief,
            observation.barriers,
            observation.board,
            self.depth,
            self.weights,
            observation.barriers_remaining,
        )
        return value - self.weights.scent * self.trail.cost_at(cell, observation.board)

    def _track(self, observation: Observation) -> None:
        """Emit into our own trail, restarting it at a sub-game boundary.

        The boundary shows up as the step counter failing to advance. Carrying a
        trail across it would have us fleeing the ghost of a previous game, and
        carrying the anchor's state would resume a bluff on a board that no
        longer exists.
        """
        if observation.step <= self._last_step:
            self.trail.reset()
            self.anchor.reset()
        self._last_step = observation.step
        self.trail.observe(observation.own_position, observation.board)
