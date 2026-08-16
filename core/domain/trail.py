"""Our own scent, reconstructed (TODO 8.2.3, 8.3.4; PRD advanced §4.2).

**Both agents emit** (Ch. 4.1.3), so this is shared domain code and not a Thief
tactic. It arrived in `thief/` because the Thief needed it first — A2.5 charges
its own trail as a cost — and moved here when the bluff policy showed the Cop
needs the same quantity: the information value of a hint is measured against
what our trail has already given away, and the Cop's trail gives away just as
much as the Thief's (TODO 8.3.4). A module in a role package is invisible to the
other role's repository, so a Cop reaching for it would simply not have it.

Ch. 4 gives each side the opponent's transmitted field and nothing else, so
`Observation` carries a belief about where the opponent is and no record of what
we ourselves have been emitting — which is exactly the quantity A2.5 says to
treat as a cost.

**So we rebuild it rather than ask for it.** Emission is a pure function of where
we have stood: `merge(decay(previous), emit(here))`, evaluated once per turn with
the negotiated rate and decay model. The brain is told `own_position` every turn,
so replaying that is exact, not an estimate — the same arithmetic the engine runs,
on the same inputs.

`bearing_leak` asks the other question the same field answers — *"can they
already tell which way I am going?"* — and it is what the bluff policy prices a
claim against (`core/domain/bluff.py`).

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
That fact is measured in `tests/unit/test_trail.py`, and it is why the
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
        self.emitted = merge(decay(self.emitted, self.rate, self.model), emit(position, board, self.model))
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

    def bearing_leak(self, position: Position, heading: Position) -> float:
        """Return how much our field already betrays that we are going *heading*.

        Args:
            position: Where we stand.
            heading: The unit step we are about to take, as ``(d_row, d_col)``.

        Returns:
            0.0 when the trail says nothing about our bearing, rising toward 1.0
            when it says it plainly.

        **A single deposit reveals a position, not a bearing.** It is radially
        symmetric — it says *here* and nothing about which way we came from or
        are going. What encodes a bearing is the **asymmetry** left by movement:
        three turns north leaves a tail of decaying deposits to the south and
        nothing to the north, and an opponent reading that smear knows our
        heading without being told.

        So the reading splits the whole field about us, along the heading axis,
        and compares the two halves — normalised by the total so it does not
        drift with how long the game has run:

            (behind - ahead) / (behind + ahead)

        **Split by projection, not by the two adjacent cells.** The tail that
        carries the signal sits two and three cells back, and the neighbouring
        pair is dominated by the symmetric window we deposited this very turn: a
        four-step run north reads 0.13 that way and 0.81 this way, for the same
        board and the same trail. `cost_at`'s 5x5 windows do not work here either
        — two cells apart they overlap in three rows of five, which averages away
        the difference being measured.

        Negative values — about to double back into our own trail — clamp to 0,
        and correctly: the field records where we have *been*, so a reversal is
        precisely the move it does not predict, and saying it out loud is real
        information.
        """
        d_row, d_col = heading
        ahead = behind = 0.0
        for (row, column), value in self.emitted.items():
            projection = (row - position[0]) * d_row + (column - position[1]) * d_col
            if projection > 0:
                ahead += value
            elif projection < 0:
                behind += value
        total = ahead + behind
        return max((behind - ahead) / total, 0.0) if total else 0.0

    def loudest(self) -> Position | None:
        """Return the cell carrying our strongest mark, or None if silent.

        This is our best guess at where the Cop's posterior is currently
        centred, and it is what the false anchor breaks away *from*. Ties break
        on coordinates so a replay reaches the same answer.
        """
        if not self.emitted:
            return None
        return max(sorted(self.emitted), key=lambda cell: self.emitted[cell])
