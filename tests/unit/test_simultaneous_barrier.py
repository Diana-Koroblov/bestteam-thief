"""🐛 A Thief can walk **into** the wall the Cop is building this turn.

Found by the Phase 8.2 self-play, not by inspection: the advanced Thief reaches
positions the baseline never did, and four sub-games came back with a
`cop_separations` count that TODO 3.5.4 says must be 0. The separations were real
but the cause was not the Cop — it was the engine.

The sequence, from `AdvancedCop` vs `AdvancedThief`, cop start (1,3)::

    turn 6   cop (5,5)  thief (6,6)  barriers []
             cop commits "wall (5,6)"      thief commits "move N to (5,6)"
    turn 7   cop (5,5)  thief (5,6)  barriers [(5,6)]     <- thief inside a wall
    turn 8   cop (5,5)  thief (4,6)  barriers [(5,6),(6,5)]  <- and out again

Both actions are legal against the pre-move board, which is correct under
commit-reveal — neither side sees the other's choice. What is wrong is the
*resolution*. Three things follow from it, and all three are bad:

* **A capture is silently dropped.** `capture.resolution = "after_moves"` (C-006b)
  says positions are evaluated once both actions apply. After they apply the
  Thief is standing on a barriered cell, which is M#46's capture condition.
* **`are_connected` reports nonsense.** `reachable` will not expand into an
  impassable cell, so a Thief inside a wall looks unreachable from everywhere —
  which is what produced the bogus self-separation counts.
* **The seal leaks.** A barrier blocks entry, not exit, so the Thief steps out
  next turn having passed straight through the wall that was meant to cut it off.

`BarrierManager.place()` compares against whatever `thief_pos` the caller hands
it, and `selfplay.play_sub_game` hands it the **pre-move** position — exactly the
integration note CONTRADICTIONS C-006b left for the turn loop, unactioned.

**Resolved 05/08: it captures.** The turn loop now resolves the Thief's move
first and hands the **post-move** cell to `BarrierManager.place`, so M#46 is
judged on where the Thief actually ends up. Both halves of C-006b fall out of
that one value: a wall on a vacated cell misses, a wall on the cell the Thief
steps onto captures. The reading was chosen deliberately rather than patched in
— `capture.resolution` sits in the shared `game.json` and therefore in the M#11
digest, so it has to match what the opponent signs (negotiation item N15).
"""

from __future__ import annotations

from core.domain.actions import Direction
from core.domain.board import Board
from core.domain.brain_base import BrainBase, Decision
from core.domain.game_state import GameState
from core.domain.rules import Rules, Verdict
from core.runtime.selfplay import play_sub_game

BOARD = Board(grid_size=7)
RULES = Rules(board=BOARD, survival_threshold=35)


class WallsTheCellBelow(BrainBase):
    """A Cop that walls the cell one south of it, once, then holds."""

    def __init__(self, name: str = "") -> None:
        super().__init__(name)
        self.placed = False

    def _pick_move(self, observation) -> Decision:
        if self.placed:
            return Decision(Direction.STAY, reason="done")
        self.placed = True
        row, column = observation.own_position
        return Decision(Direction.STAY, barrier=(row + 1, column), reason="wall below")


class StepsOnce(BrainBase):
    """A Thief that takes one step in a fixed direction, then holds.

    It holds rather than continuing because a Thief that kept walking would step
    onto the Cop a turn or two later and end the sub-game for a completely
    unrelated reason — which is exactly how the first version of this test
    passed while proving nothing.
    """

    def __init__(self, name: str = "", heading: Direction = Direction.N) -> None:
        super().__init__(name)
        self.heading = heading
        self.moved = False

    def _pick_move(self, observation) -> Decision:
        if self.moved:
            return Decision(Direction.STAY, reason="hold")
        self.moved = True
        return Decision(self.heading, reason=self.heading.value)


def test_a_barrier_on_the_cell_the_thief_moves_onto_captures() -> None:
    """**M#46 under `after_moves` resolution.** Once both actions apply the Thief
    stands on a barriered cell, and that is the capture condition.

    Before the fix this returned SURVIVAL: the Thief stood in the wall, stepped
    out the next turn, and outlasted the clock.
    """
    result = play_sub_game(
        WallsTheCellBelow(), StepsOnce(heading=Direction.N), RULES, 14,
        GameState(cop=(3, 3), thief=(5, 3)),
    )
    assert result.outcome.verdict is Verdict.CAPTURE
    assert result.steps == 1, "and it ends immediately, not eventually"
    assert "(4, 3)" in result.outcome.reason


def test_a_barrier_on_a_vacated_cell_still_misses() -> None:
    """The other half of C-006b, from the same argument.

    The original reading has to survive the fix: a Thief *leaving* the cell the
    Cop walls is not captured. Both behaviours now come out of one value, so
    neither can be changed without the other being reconsidered.

    The Thief heads **south**, away from the Cop — walking north would put it on
    the Cop's own cell and end the sub-game for an unrelated reason.
    """
    result = play_sub_game(
        WallsTheCellBelow(), StepsOnce(heading=Direction.S), RULES, 14,
        GameState(cop=(3, 3), thief=(4, 3)),
    )
    assert result.history[1].thief == (5, 3)
    assert (4, 3) in result.history[1].barriers
    assert result.steps > 1, "the vacated cell must not capture"


def test_the_thief_only_ever_sits_on_a_barrier_in_the_frame_that_ends_the_game() -> None:
    """The impossible state the old resolution produced, asserted gone.

    `are_connected` cannot expand into an impassable cell, so a Thief inside a
    barrier reads as unreachable from everywhere — which is what produced four
    bogus `cop_separations` in the 8.2 self-play and blocked 8.QG.4.

    The **final** frame legitimately shows the Thief on the walled cell: that is
    the capture, and the log should record it truthfully. What must never happen
    is play continuing from there.
    """
    result = play_sub_game(
        WallsTheCellBelow(), StepsOnce(heading=Direction.N), RULES, 14,
        GameState(cop=(3, 3), thief=(5, 3)),
    )
    assert all(state.thief not in state.barriers for state in result.history[:-1])
    assert result.outcome.verdict is Verdict.CAPTURE
