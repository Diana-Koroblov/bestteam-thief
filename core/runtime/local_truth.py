"""What this peer knows and what it says (TODO 4.1.6, 4.2.1, 4.5.1).

Split out of `peer_runtime.py`, which had grown two jobs. That file is the
**inbound state machine** — is this message allowed right now? This one is the
peer's *local truth*: the scent it emits, the posterior it maintains, the
observation a brain is handed, and the reveal that carries a decision back out.

The two are genuinely separate concerns and the split is not only about line
count. The state machine is about what an opponent is permitted to do to us; this
is about what we are permitted to know. They share exactly one thing — the record
of revealed turns — which is owned here, because reading it is what this file is
for and recording it is a single line over there.

**This is the file whose absence made Phase 8 inert on the wire.** Until it
existed, `PeerRuntime.belief()` returned a uniform posterior and no scent field
ever crossed the wire, so a live Cop measured entropy at 5.61 bits against a
`confident_bits` threshold of 3.5, stayed in HERD for all 35 turns, and never
placed a barrier — which PRD §2.1 identifies as the only way the Cop can win. The
strategy was fine. It simply had nothing to run on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.crypto.canonical import digest
from core.domain.board import Position
from core.domain.brain_base import Decision, Observation
from core.domain.filter import BeliefFilter
from core.domain.scent import decode, encode
from core.infra.llm.factory import build_writer
from core.infra.llm.meter import TokenMeter
from core.infra.llm.writer import HintWriter, compass_word
from core.protocol.schemas import Reveal, Role
from core.runtime.orchestrator import Orchestrator

__all__ = ["LocalTruth"]


@dataclass
class LocalTruth:
    """The scent we emit, the belief we hold, and the words we send.

    Attributes:
        orchestrator: Owns the game state; the only thing allowed to change it.
        reveals: Opponent move per step, and the scent field that came with it.
        meter: What the verbal channel has cost in model tokens (M#54). Owned
            here because this is the file that builds the writer, and it
            **survives `reset`**: the report wants the series, and the providers
            are built once and reused across all six sub-games.
    """

    orchestrator: Orchestrator
    reveals: dict[int, Reveal] = field(default_factory=dict)
    meter: TokenMeter = field(default_factory=TokenMeter)
    _filter: BeliefFilter | None = field(default=None, repr=False)
    _filtered_step: int = field(default=-1, repr=False)
    _writer: HintWriter | None = field(default=None, repr=False)

    @property
    def filter(self) -> BeliefFilter:
        """The belief filter, built from the **negotiated** pheromone section.

        Lazy because the config is only trustworthy after the handshake, and
        read from `[pheromones]` rather than from our own preferences: the field
        we emit has to be the one the opponent's filter expects, and C-007 means
        either decay model may have been signed.
        """
        if self._filter is None:
            config = self.orchestrator.config
            self._filter = BeliefFilter(
                board=self.orchestrator.board,
                rate=float(config.get("pheromones.pheromone_decay", 0.10)),
                model=str(config.get("pheromones.decay_model", "multiplicative")),
            )
        return self._filter

    def observe(self) -> Observation:
        """Build what the brain is allowed to see.

        Deliberately **excludes the opponent's position**. In a real match
        nobody has it; handing it over here would produce a strategy that works
        in self-play and collapses against a real peer.

        **Advancing the filter happens here, once per step, and that is
        deliberate.** A separate `advance()` the caller had to remember would be
        forgotten exactly once, and the symptom is silent: a uniform posterior
        does not raise, it just leaves the Cop permanently unconfident and
        therefore permanently unable to wall. The step number guards it instead,
        so calling this twice in one turn is safe and calling it never is the
        only remaining mistake.
        """
        state = self.orchestrator.state
        self._advance(state.step)
        quota = self.orchestrator.config.require("movement_and_barriers.max_barriers")
        return Observation(
            board=self.orchestrator.board,
            own_position=self.orchestrator.own_position,
            barriers=state.barriers,
            step=state.step,
            barriers_remaining=quota - state.barriers_placed,
            belief=self.belief(),
            hints=tuple(reveal.hint for reveal in self.reveals.values() if reveal.hint),
        )

    def _advance(self, step: int) -> None:
        """Emit this turn's mark and fold in the opponent's latest field.

        The field used is the newest they have revealed, which is **a turn old
        and can be nothing else**: our move for this turn is committed before
        their reveal for this turn can arrive. `BeliefFilter.observe` runs
        `predict` first for exactly that reason.

        A step that goes *backwards* is a new sub-game, and it resets rather
        than being ignored. `reset()` exists for a caller that knows the
        boundary has arrived, but a guard that has to be remembered is the exact
        shape of the defect this whole file was written to fix — and the symptom
        would be the same one: a filter that silently stops filtering, a Cop
        that never gains confidence, and no error anywhere.
        """
        if step < self._filtered_step:
            self.reset()
        elif step == self._filtered_step:
            return
        self._filtered_step = step
        state = self.orchestrator.state
        # 🐛 **Step 0 observed AND emitted, so the first frame carried two
        # emission cycles.** This runs twice on the opening turn and only the
        # opening turn — once from `belief()` at the pre-move step 0, once from
        # `reveal_for` at the post-move step 1 — because `_filtered_step` starts
        # at -1 and every later turn finds its pre-move step already claimed.
        # Two deposits one decay apart put a *second-generation* value on the
        # wire: at rho=0.1 subtractive, 0.9 -> 0.8 -> 0.7, and a peer replaying
        # our field from an empty board cannot explain a 0.7 in a game one step
        # old. imreeyal's checker withheld our cop's step-1 frame in all three
        # police sub-games of both series on 16/08 and 17/08, and diagnosed it
        # exactly: a spawn deposit laid before the first move.
        #
        # Ch. 4.3 ties emission to an action — *"every time an agent moves or
        # stays in place"* — and at step 0 no action has been taken, so the book
        # asks for no emission here either. Nothing is concealed by removing it:
        # both start cells are public signed terms (`cop_start`, `thief_start`).
        #
        # The guard is on the deposit alone, deliberately. `observe` must still
        # run at step 0 — our Cop has already read the Thief's opening field by
        # then, and skipping it would drop that evidence from the first
        # decision. It is `reset`'s -1 that guarantees this, which is why the
        # fix could not simply be to start the counter at 0.
        if step > 0:
            self.filter.deposit(self.orchestrator.own_position)
        self.filter.observe(
            self.latest_opponent_scent(), state.barriers, self.orchestrator.own_position
        )

    def latest_opponent_scent(self) -> dict[Position, float]:
        """Return the most recent field the opponent transmitted, or ``{}``.

        Empty means **silence, not absence** (Ch. 4): before their first reveal
        there is no reading, and a filter that sharpened on nothing would be
        manufacturing confidence it has not earned.
        """
        return decode(self.reveals[max(self.reveals)].scent) if self.reveals else {}

    def belief(self) -> dict[Position, float]:
        """Return the posterior over where the opponent is (4.2.1).

        Advances the filter under the same per-step guard `observe` uses, so a
        caller that wants only the posterior gets a *masked* one — barriers and
        our own cell at exactly zero (4.2.1.e). Without that this returns the
        raw uniform prior, which still sums to 1.0 and looks entirely correct
        while claiming the opponent might be standing inside a wall.
        """
        self._advance(self.orchestrator.state.step)
        return dict(self.filter.belief)

    def scent_digest(self) -> str | None:
        """Return the digest of the field we are transmitting, or None (C-008).

        `None` when `seal_scent_digest` was not agreed, and the caller must then
        **omit the key** rather than send null: the opponent recomputes our
        digests with their own payload builder, so one extra key fails every
        digest we ever sent and makes an honest peer look like a forger.
        """
        if not self.orchestrator.config.get("pheromones.seal_scent_digest", False):
            return None
        return digest(encode(self.filter.trail))

    def sealed_barrier(self, decision: Decision) -> Position | None:
        """Return the cell to seal into this turn's commitment, or None (C-018).

        Two conditions, both of which have to hold, and neither of which a
        caller should be trusted to remember: a barrier was actually placed, and
        the opponent agreed to the payload shape that carries it. Sealing
        unilaterally is worse than not sealing — every digest we sent would fail
        their audit and an honest peer would look like a forger.

        The declaration is unaffected either way. `reveal_for` announces the
        cell on every placement, agreement or not, because M#15 is a duty owed
        to the opponent and not a term of the negotiation.
        """
        if decision.barrier is None:
            return None
        if not self.orchestrator.config.get("movement_and_barriers.seal_barrier_cell", False):
            return None
        return decision.barrier

    def reveal_for(self, decision: Decision, role: Role, step: int | None = None) -> Reveal:
        """Turn a brain's decision into the message that carries it (4.5.1).

        The brain chose the bearing and the truth flag; the language layer is
        *told* the result and only writes the sentence (A3.11, Ch. 5). The scent
        field rides along because there is nowhere else for it to go — see
        `Reveal` for why that also fixes the timing of the whole game.
        """
        if self._writer is None:
            self._writer = build_writer(self.orchestrator.config, self.meter)
        turn = self.orchestrator.state.step if step is None else step
        # Idempotent, so the field we transmit is this turn's even if nobody
        # called `observe` first. Sending a stale trail would be a lie about the
        # one channel that cannot lie, and under C-008 it would be a sealed one.
        self._advance(self.orchestrator.state.step)
        written = self._writer.write(
            compass_word(decision.claim),
            decision.intent,
            turn,
            str(self.orchestrator.config.get("world.map_area", "")),
        )
        return Reveal(
            step=turn,
            role=role,
            move=decision.move.value,
            hint=written.text,
            intent=decision.intent,
            barrier_cell=decision.barrier,
            scent=encode(self.filter.trail),
        )

    def reset(self) -> None:
        """Clear everything belonging to the sub-game just finished.

        The filter and the per-step guard reset together: a posterior carried
        across the boundary would describe a board the rules have just rebuilt,
        and a stale `_filtered_step` would silently skip the first turn's
        filtering of the next one.
        """
        self.filter.reset()
        self._filtered_step = -1
        self.reveals.clear()
