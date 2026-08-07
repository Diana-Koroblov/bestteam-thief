"""One turn's physics, shared by self-play and a live match (TODO 9.4.1).

These used to be private helpers inside `runtime/selfplay.py`, exercised only
through a whole sub-game. They are tested directly now because a second caller
exists: the live driver applies the same function, and the reason for extracting
it was that two copies would be two sets of rules.

The cases that matter are the ones where the two callers must behave
*differently* (`strict`) and the ones where they must not (everything else).
"""

from __future__ import annotations

import pytest

from core.domain.actions import Direction
from core.domain.barriers import BarrierManager
from core.domain.board import Board
from core.domain.brain_base import Decision
from core.domain.game_state import GameState
from core.domain.rules import Rules, Verdict
from core.domain.turn import IllegalMoveError, resolve_turn

BOARD = Board(grid_size=7, origin_index=0)


def rules_for(config) -> Rules:
    return Rules.from_config(config, BOARD)


def move(direction: str, barrier=None) -> Decision:
    return Decision(move=Direction(direction), barrier=barrier)


def test_both_decisions_apply_simultaneously(minimal_config) -> None:
    """Neither side sees the other's move, so neither can react to it."""
    state = GameState(cop=(0, 0), thief=(3, 3))
    barriers = BarrierManager(max_barriers=14, board=BOARD)
    turn = resolve_turn(state, move("S"), move("N"), barriers, rules_for(minimal_config))
    assert (turn.state.cop, turn.state.thief) == ((1, 0), (2, 3))
    assert turn.state.step == state.step + 1


def test_a_placement_costs_the_move(minimal_config) -> None:
    """Ch. 3.4: the cop forgoes movement to wall a cell, so it does not travel.

    Half of this is enforced one layer down — `Decision` refuses to exist with a
    barrier and a travelling move — and the assertion here is that the resolver
    agrees: the cop is where it started and the wall is on the board.
    """
    state = GameState(cop=(2, 2), thief=(5, 5))
    barriers = BarrierManager(max_barriers=14, board=BOARD)
    turn = resolve_turn(
        state, move("STAY", barrier=(2, 3)), move("STAY"), barriers, rules_for(minimal_config)
    )
    assert turn.state.cop == (2, 2)
    assert (2, 3) in turn.state.barriers
    assert turn.state.barriers_placed == 1


def test_a_barrier_cannot_ride_along_with_a_move() -> None:
    """The combination is refused at construction, so no resolver can see it."""
    with pytest.raises(ValueError, match="forgoing movement"):
        Decision(move=Direction("S"), barrier=(2, 3))


def test_a_wall_on_the_cell_the_thief_steps_onto_captures(minimal_config) -> None:
    """**C-006b.** The thief's destination is resolved first, then the placement.

    The other order let a thief walk into the wall being built and stand inside
    it — which is both a capture missed and a board no legal play can produce.
    """
    state = GameState(cop=(3, 2), thief=(3, 4))
    barriers = BarrierManager(max_barriers=14, board=BOARD)
    turn = resolve_turn(
        state, move("STAY", barrier=(3, 3)), move("W"), barriers, rules_for(minimal_config)
    )
    assert turn.outcome is not None and turn.outcome.verdict is Verdict.CAPTURE


def test_a_wall_on_a_vacated_cell_does_not_capture(minimal_config) -> None:
    """The same rule read the other way: the thief left before the wall landed."""
    state = GameState(cop=(3, 2), thief=(3, 3))
    barriers = BarrierManager(max_barriers=14, board=BOARD)
    turn = resolve_turn(
        state, move("STAY", barrier=(3, 3)), move("E"), barriers, rules_for(minimal_config)
    )
    assert turn.outcome is None
    assert turn.state.thief == (3, 4)


def test_an_illegal_move_holds_position_for_the_harness(minimal_config) -> None:
    """Self-play must survive a bad proposal: a batch of a hundred cannot abort."""
    state = GameState(cop=(0, 0), thief=(3, 3))
    barriers = BarrierManager(max_barriers=14, board=BOARD)
    turn = resolve_turn(state, move("N"), move("STAY"), barriers, rules_for(minimal_config))
    assert turn.state.cop == (0, 0)


def test_an_illegal_move_is_raised_for_a_live_match(minimal_config) -> None:
    """**M#13/M#14.** An opponent's illegal move is a technical loss in our favour.

    Converting it to STAY, as the harness does, would hand back a point the
    rules had already awarded us — which is why the two callers differ here and
    nowhere else.
    """
    state = GameState(cop=(0, 0), thief=(3, 3))
    barriers = BarrierManager(max_barriers=14, board=BOARD)
    with pytest.raises(IllegalMoveError, match="cop"):
        resolve_turn(state, move("N"), move("STAY"), barriers, rules_for(minimal_config), strict=True)


def test_the_offending_side_is_named(minimal_config) -> None:
    """Ours is a bug to fix and theirs is a claim to make; the message must say."""
    state = GameState(cop=(3, 3), thief=(0, 0))
    barriers = BarrierManager(max_barriers=14, board=BOARD)
    with pytest.raises(IllegalMoveError, match="thief"):
        resolve_turn(state, move("STAY"), move("N"), barriers, rules_for(minimal_config), strict=True)


def test_a_refused_placement_still_reports_the_cell(minimal_config) -> None:
    """A rejection is declarable too — it is what we quote when refusing theirs."""
    state = GameState(cop=(2, 2), thief=(5, 5))
    barriers = BarrierManager(max_barriers=0, board=BOARD)
    turn = resolve_turn(
        state, move("STAY", barrier=(2, 3)), move("STAY"), barriers, rules_for(minimal_config)
    )
    assert turn.placed is not None and turn.placed.cell == (2, 3)
    assert not turn.placed.succeeded
    assert turn.state.barriers == state.barriers


def test_the_quota_is_spent_from_the_manager_it_was_given(minimal_config) -> None:
    """The manager is mutated on purpose: a copy would let one wall be spent twice."""
    state = GameState(cop=(2, 2), thief=(5, 5))
    barriers = BarrierManager(max_barriers=14, board=BOARD)
    resolve_turn(
        state, move("STAY", barrier=(2, 3)), move("STAY"), barriers, rules_for(minimal_config)
    )
    assert barriers.remaining == 13
