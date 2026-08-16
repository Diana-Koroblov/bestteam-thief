"""One peer's private knowledge: what we emit, and what we believe (TODO 4.1.6, 4.2.1).

The recursive filter of `belief.py` and the trail of `scent.py`, joined and given
the one thing neither has on its own — **a turn**. Held per peer, because in a
real match neither side can see the other's filter, and sharing one object
between two agents would silently make the harness measure a game nobody plays.

This lives in `domain` and is used by **both** `core/runtime/selfplay.py` and
`core/runtime/peer_runtime.py`, which is the entire point of extracting it. It
was previously a private `Side` class inside the harness while the live runtime
had no filter at all, and that arrangement is what let the two drift: everything
Phase 8 measured was measured on a filter the wire did not have.

The timing, which is the subtle part
------------------------------------
Commit-reveal fixes when evidence can arrive. A peer commits its move for turn
*k* **before** the opponent reveals anything about turn *k* — that is what the
protocol is for. The opponent's field for turn *k* therefore travels with their
turn-*k* reveal and is first usable when deciding turn *k+1*.

So the freshest field any peer can hold at decision time is **one turn old**, and
`observe` is written to be called with exactly that. `predict` runs first and
widens the prior by one move, which is what carries a belief about where they
were into a belief about where they are.

**The harness used to hand brains the opponent's current-turn deposit**, one turn
fresher than the wire can deliver, because with both trails in one process there
was nothing to stop it. Every Phase 8 number was measured against that. See
`selfplay.play_sub_game`, where the field is now held back a turn on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.domain.belief import mask, predict, uniform, update_from_scent
from core.domain.board import Board, Position
from core.domain.scent import decay, emit, merge

__all__ = ["BeliefFilter"]


@dataclass
class BeliefFilter:
    """What one peer emits and what it believes about the other.

    Attributes:
        board: Geometry.
        rate: `pheromones.pheromone_decay`, 0.10 by Appendix F.
        model: `multiplicative` (the book) or `subtractive` (the reference).
            Both ship because either may be signed at the handshake (C-007).
        belief: Posterior over the opponent's cell. Uniform until evidence.
        trail: What we have emitted, and what we transmit.
    """

    board: Board
    rate: float = 0.10
    model: str = "multiplicative"
    belief: dict[Position, float] = field(default_factory=dict)
    trail: dict[Position, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Start uniform over every cell, which is honest ignorance (4.2.1.a)."""
        if not self.belief:
            self.belief = uniform(self.board)

    def deposit(self, at: Position) -> dict[Position, float]:
        """Lay this turn's mark over the decayed remains and return what to send.

        Decay first, then merge the fresh 5x5. Emitting before decaying would
        fade the deposit we just laid and make every reading one turn old.

        The returned field **includes this turn's deposit** (C-005, N13): it
        matches the reference implementation, so it is what most opponents will
        send, and uncertainty survives regardless because both peers move again
        afterwards.
        """
        self.trail = merge(decay(self.trail, self.rate, self.model), emit(at, self.board, self.model))
        return self.trail

    def observe(
        self,
        opponent_field: dict[Position, float],
        barriers: frozenset[Position],
        own: Position,
    ) -> dict[Position, float]:
        """Predict, then update on the opponent's transmitted field (4.2.1.b-e).

        Args:
            opponent_field: What they last transmitted — see the module
                docstring on why that is a turn old and must be.
            barriers: Every wall in force.
            own: Where we stand, which the opponent cannot be.

        **Prediction comes first, always.** The opponent moved since we last
        looked, so the prior must be widened *before* new evidence narrows it.
        Updating against a stale prior is how a filter becomes confidently wrong.

        An empty field leaves the belief where prediction put it, which is Ch. 4's
        *silence is not absence*: no reading is no evidence, and a filter that
        sharpened on nothing would be manufacturing confidence.
        """
        self.belief = predict(self.belief, self.board, barriers)
        self.belief = update_from_scent(self.belief, opponent_field, self.board, self.model)
        self.belief = mask(self.belief, barriers, own)
        return self.belief

    def reset(self) -> None:
        """Clear everything for a new sub-game.

        A trail carried across the boundary would have us chasing a game that is
        over, and a belief carried across would be a posterior about a position
        the rules have just rebuilt.
        """
        self.belief = uniform(self.board)
        self.trail = {}
