"""Our own scent, reconstructed (TODO 8.2.3; PRD advanced §4.2).

The Thief is the only agent that can be *heard*. Ch. 4 gives each side the
opponent's transmitted field and nothing else, so `Observation` carries a belief
about where the Cop is and no record of what we ourselves have been emitting —
which is exactly the quantity A2.5 says to treat as a cost.

**So we rebuild it rather than ask for it.** Emission is a pure function of where
we have stood: `merge(decay(previous), emit(here))`, evaluated once per turn with
the negotiated rate and decay model. The brain is told `own_position` every turn,
so replaying that is exact, not an estimate — the same arithmetic the engine runs,
on the same inputs.

Rebuilding beats threading a field through `Observation` for a concrete reason:
`PeerRuntime.belief()` is still the Phase 4 placeholder, so a trail plumbed
through the runtime would exist in self-play and be empty in a real match. A
brain that owns its own history behaves identically in both.

**What a trail costs us.** Not the cell's own intensity — the *neighbourhood's*.
The Cop does not read one cell, it reads the whole field and runs a filter over
it, and what a filter needs is a mark that identifies where we are *now*. So the
cost of stepping somewhere is how much of our own history already sits within
earshot: a cell we have circled keeps the field concentrated on us, while a quiet
one spreads it and buys ambiguity.

**Standing still does not make a trail louder, and that surprised us.** `merge`
keeps the *maximum*, so re-emitting on a cell we already occupy restores exactly
the values that were there — five turns of standing produces a field byte-for-byte
identical to one turn of it (25 cells, total 7.14). Moving five turns instead
leaves 34 cells and total 12.51, because each step lays a fresh window beside the
decaying old one. **Movement is what accumulates scent; repetition does not.**
That fact is measured in `tests/unit/test_thief_trail.py`, and it is why the
false anchor of §4.4 does not work the way the PRD assumed — see `thief/anchor.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.domain.board import Board, Position
from core.domain.scent import RADIUS, decay, emit, merge

__all__ = ["TrailTracker"]


@dataclass
class TrailTracker:
    """The field we have emitted, kept in step with the engine's copy.

    Attributes:
        rate: `pheromones.pheromone_decay`, 0.10 by Appendix F.
        model: `multiplicative` (the book) or `subtractive` (the reference).
            Both ship because either may be signed at the handshake (C-007), and
            reconstructing with the wrong one would drift a little every turn.
        emitted: Intensity per cell, exactly as the engine holds it.
        visits: Every cell we have stood on, in order.
    """

    rate: float = 0.10
    model: str = "multiplicative"
    emitted: dict[Position, float] = field(default_factory=dict)
    visits: list[Position] = field(default_factory=list)

    def observe(self, position: Position, board: Board) -> None:
        """Age the trail and lay this turn's deposit.

        Order matters and matches `selfplay.Side.emit_and_age`: decay first,
        then merge the fresh 5x5. Emitting before decaying would fade the
        deposit we just laid and make every reconstructed reading one turn old.
        """
        self.emitted = merge(decay(self.emitted, self.rate, self.model), emit(position, board))
        self.visits.append(position)

    def reset(self) -> None:
        """Clear everything at a sub-game boundary.

        A trail is per sub-game: the board is rebuilt, and carrying intensity
        across the boundary would have us fleeing our own ghost.
        """
        self.emitted = {}
        self.visits = []

    def cost_at(self, cell: Position, board: Board) -> float:
        """Return how loud standing on *cell* would be.

        The sum of our existing intensity across the 5x5 window we would emit
        into. High means we have been here recently and repeatedly, so the Cop's
        filter already has a sharp, current fix — moving somewhere quiet is worth
        real distance.

        Uses the emission window rather than the single cell because that is the
        footprint our next deposit actually covers; a single-cell reading would
        rate "one step off a cell I have circled ten times" as silent.
        """
        row, column = cell
        return sum(
            self.emitted.get((row + d_row, column + d_col), 0.0)
            for d_row in range(-RADIUS, RADIUS + 1)
            for d_col in range(-RADIUS, RADIUS + 1)
            if board.in_bounds((row + d_row, column + d_col))
        )

    def loudest(self) -> Position | None:
        """Return the cell carrying our strongest mark, or None if silent.

        This is our best guess at where the Cop's posterior is currently
        centred, and it is what the false anchor breaks away *from*. Ties break
        on coordinates so a replay reaches the same answer.
        """
        if not self.emitted:
            return None
        return max(sorted(self.emitted), key=lambda cell: self.emitted[cell])
