"""Unit tests for barrier placement (PRD 1 §3.3, T1.6-T1.12).

The five rules under test: placement costs the turn, the target must be the
Cop's own cell or an orthogonal neighbour, the quota is hard, barriers are
permanent, and a placement can win the sub-game outright.
"""

from __future__ import annotations

import pytest

from core.domain.barriers import (
    BarrierManager,
    PlacementOutcome,
    RejectionReason,
)
from core.domain.board import Board

BOARD = Board(grid_size=7)
COP = (3, 3)


@pytest.fixture
def manager() -> BarrierManager:
    """A manager at the Appendix F default quota."""
    return BarrierManager(max_barriers=14, board=BOARD)


# --- construction -----------------------------------------------------------


def test_quota_comes_from_config(manager: BarrierManager) -> None:
    assert manager.remaining == 14
    assert manager.placed_count == 0


def test_a_negative_quota_is_refused() -> None:
    """1.3.1.a: no negotiation can produce this, so it is a programming error."""
    with pytest.raises(ValueError, match="must not be negative"):
        BarrierManager(max_barriers=-1, board=BOARD)


def test_a_raised_quota_is_accepted() -> None:
    """M#12 permits raising a minimum by mutual agreement."""
    assert BarrierManager(max_barriers=20, board=BOARD).remaining == 20


# --- where a barrier may go -------------------------------------------------


@pytest.mark.parametrize("target", [(3, 3), (2, 3), (4, 3), (3, 2), (3, 4)])
def test_own_cell_and_four_orthogonal_neighbours_are_legal(
    manager: BarrierManager, target: tuple[int, int]
) -> None:
    assert manager.can_place(target, COP, True)


@pytest.mark.parametrize("target", [(2, 2), (2, 4), (4, 2), (4, 4)])
def test_diagonally_adjacent_is_rejected(
    manager: BarrierManager, target: tuple[int, int]
) -> None:
    """T1.8: one step means orthogonal, exactly as movement does."""
    result = manager.place(target, COP)
    assert result.outcome is PlacementOutcome.REJECTED
    assert result.reason is RejectionReason.OUT_OF_RANGE


@pytest.mark.parametrize("target", [(1, 3), (3, 1), (5, 5), (0, 0)])
def test_anything_further_than_one_step_is_rejected(
    manager: BarrierManager, target: tuple[int, int]
) -> None:
    assert not manager.can_place(target, COP, True)


def test_a_target_off_the_board_is_rejected(manager: BarrierManager) -> None:
    result = manager.place((-1, 0), (0, 0))
    assert result.reason is RejectionReason.OFF_BOARD


def test_placing_while_moving_is_rejected(manager: BarrierManager) -> None:
    """T1.9: the barrier costs the Cop its move for that turn."""
    result = manager.place((2, 3), COP, is_forgoing_move=False)
    assert result.outcome is PlacementOutcome.REJECTED
    assert result.reason is RejectionReason.NOT_FORGOING_MOVE
    assert manager.remaining == 14


def test_the_same_cell_cannot_be_blocked_twice(manager: BarrierManager) -> None:
    assert manager.place((2, 3), COP).succeeded
    result = manager.place((2, 3), COP)
    assert result.reason is RejectionReason.ALREADY_BLOCKED
    assert manager.placed_count == 1


# --- the quota --------------------------------------------------------------


def test_fourteen_placements_are_accepted_and_the_fifteenth_is_not() -> None:
    """T1.6 and T1.7. The Cop walks the top rows, spending the whole quota."""
    manager = BarrierManager(max_barriers=14, board=BOARD)
    cells = [(row, col) for row in range(2) for col in range(7)]
    for index, cell in enumerate(cells):
        assert manager.place(cell, cell).succeeded, index
    assert manager.placed_count == 14
    assert manager.remaining == 0

    fifteenth = manager.place((3, 0), (3, 0))
    assert fifteenth.outcome is PlacementOutcome.REJECTED
    assert fifteenth.reason is RejectionReason.QUOTA_EXHAUSTED
    assert manager.placed_count == 14


def test_a_rejected_placement_never_costs_quota(manager: BarrierManager) -> None:
    manager.place((0, 0), COP)  # out of range
    manager.place((2, 3), COP, is_forgoing_move=False)  # not forgoing
    assert manager.remaining == 14


# --- permanence -------------------------------------------------------------


def test_there_is_no_way_to_remove_a_barrier(manager: BarrierManager) -> None:
    """1.3.1.d: permanence is enforced by the absence of an API, not a flag."""
    for name in ("remove", "clear", "reset", "undo", "delete", "pop"):
        assert not hasattr(manager, name), name


def test_the_exposed_barrier_set_is_frozen(manager: BarrierManager) -> None:
    manager.place((2, 3), COP)
    assert isinstance(manager.barriers, frozenset)


def test_a_placed_barrier_stays_for_the_rest_of_the_sub_game(
    manager: BarrierManager,
) -> None:
    manager.place((2, 3), COP)
    for _ in range(5):
        manager.place((3, 4), COP)
    assert (2, 3) in manager.barriers


# --- captures ---------------------------------------------------------------


def test_placing_on_the_thief_captures(manager: BarrierManager) -> None:
    """T1.10, M#46."""
    result = manager.place((2, 3), COP, thief_pos=(2, 3))
    assert result.outcome is PlacementOutcome.CAPTURE
    assert result.cell == (2, 3)


def test_sealing_the_last_exit_captures(manager: BarrierManager) -> None:
    """M#47: the Thief loses without anyone moving onto it."""
    manager = BarrierManager(max_barriers=14, board=BOARD)
    thief = (0, 0)
    assert manager.place((1, 0), (1, 0), thief_pos=thief).outcome is PlacementOutcome.PLACED
    final = manager.place((0, 1), (0, 1), thief_pos=thief)
    assert final.outcome is PlacementOutcome.CAPTURE


def test_a_placement_that_leaves_an_exit_does_not_capture(
    manager: BarrierManager,
) -> None:
    assert manager.place((2, 3), COP, thief_pos=(3, 3)).outcome is PlacementOutcome.PLACED


def test_capture_is_not_reported_when_the_thief_is_unobserved(
    manager: BarrierManager,
) -> None:
    """The Cop often places against a belief, not a sighting."""
    assert manager.place((2, 3), COP).outcome is PlacementOutcome.PLACED


def test_a_rejected_placement_reports_the_cell_it_was_asked_about(
    manager: BarrierManager,
) -> None:
    """M#15: every attempt is declarable, including the refused ones."""
    result = manager.place((0, 0), COP)
    assert result.cell == (0, 0)
    assert not result.succeeded
