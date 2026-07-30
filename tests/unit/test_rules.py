"""Unit tests for the terminal conditions (PRD 1 §3.4, T1.10-T1.15).

Every one of the four endings is exercised, plus all three capture-resolution
flags in **both** settings — an opponent may sign the reading we did not choose,
and the code has to play under whichever was agreed (C-006).
"""

from __future__ import annotations

import pytest

from core.domain.board import Board
from core.domain.game_state import GameState
from core.domain.rules import Outcome, Rules, Verdict

BOARD = Board(grid_size=7)


@pytest.fixture
def rules() -> Rules:
    """The rules under our negotiated defaults."""
    return Rules(board=BOARD, survival_threshold=35)


# --- capture by co-location (T1.13) ----------------------------------------


def test_sharing_a_cell_is_a_capture(rules: Rules) -> None:
    outcome = rules.verdict(GameState(cop=(3, 3), thief=(3, 3)))
    assert outcome is not None
    assert outcome.verdict is Verdict.CAPTURE
    assert "share cell" in outcome.reason


def test_an_ordinary_position_is_not_terminal(rules: Rules) -> None:
    assert rules.verdict(GameState(cop=(0, 0), thief=(3, 3), step=10)) is None


# --- capture by sealing in, M#47 (T1.11, T1.12) ----------------------------


def test_a_sealed_thief_is_captured(rules: Rules) -> None:
    walls = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    outcome = rules.verdict(GameState(cop=(0, 0), thief=(3, 3), barriers=walls))
    assert outcome is not None
    assert outcome.verdict is Verdict.CAPTURE
    assert "M#47" in outcome.reason


def test_a_cornered_thief_needs_only_two_barriers(rules: Rules) -> None:
    """T1.12: board edges block just as barriers do."""
    walls = frozenset({(1, 0), (0, 1)})
    state = GameState(cop=(5, 5), thief=(0, 0), barriers=walls)
    assert rules.verdict(state).verdict is Verdict.CAPTURE


def test_one_open_exit_is_not_a_capture(rules: Rules) -> None:
    walls = frozenset({(2, 3), (4, 3), (3, 2)})
    assert rules.verdict(GameState(cop=(0, 0), thief=(3, 3), barriers=walls)) is None


# --- survival (T1.14, T1.15) ------------------------------------------------


def test_the_thief_wins_at_exactly_the_threshold(rules: Rules) -> None:
    """T1.14."""
    outcome = rules.verdict(GameState(cop=(0, 0), thief=(3, 3), step=35))
    assert outcome.verdict is Verdict.SURVIVAL
    assert "35 of 35" in outcome.reason


def test_one_step_short_is_not_yet_survival(rules: Rules) -> None:
    """T1.15."""
    assert rules.verdict(GameState(cop=(0, 0), thief=(3, 3), step=34)) is None


def test_capture_beats_survival_on_the_final_step(rules: Rules) -> None:
    """A thief caught on step 35 was caught, not saved by the clock."""
    state = GameState(cop=(3, 3), thief=(3, 3), step=35)
    assert rules.verdict(state).verdict is Verdict.CAPTURE


def test_a_raised_threshold_is_honoured() -> None:
    """survival_threshold is an Appendix F minimum and may be raised."""
    raised = Rules(board=BOARD, survival_threshold=45)
    assert raised.verdict(GameState(cop=(0, 0), thief=(3, 3), step=35)) is None
    assert raised.verdict(GameState(cop=(0, 0), thief=(3, 3), step=45)) is not None


# --- C-006c, the swap -------------------------------------------------------


def test_swapping_cells_is_a_capture_by_default(rules: Rules) -> None:
    before = GameState(cop=(3, 3), thief=(3, 4))
    after = GameState(cop=(3, 4), thief=(3, 3), step=1)
    outcome = rules.turn_verdict(before, after)
    assert outcome.verdict is Verdict.CAPTURE
    assert "swapped" in outcome.reason


def test_the_swap_can_be_negotiated_off() -> None:
    """An opponent may sign the opposite reading; we must play under it."""
    lenient = Rules(board=BOARD, survival_threshold=35, swap_is_capture=False)
    before = GameState(cop=(3, 3), thief=(3, 4))
    after = GameState(cop=(3, 4), thief=(3, 3), step=1)
    assert lenient.turn_verdict(before, after) is None


def test_moving_in_the_same_direction_is_not_a_swap(rules: Rules) -> None:
    before = GameState(cop=(3, 3), thief=(3, 5))
    after = GameState(cop=(3, 4), thief=(3, 6), step=1)
    assert rules.turn_verdict(before, after) is None


# --- C-006a, when capture is evaluated --------------------------------------


def test_after_moves_ignores_a_cell_the_thief_has_vacated(rules: Rules) -> None:
    """The default: a barrier on a cell just left does not capture."""
    before = GameState(cop=(2, 3), thief=(3, 3))
    after = GameState(cop=(2, 3), thief=(4, 3), barriers=frozenset({(3, 3)}), step=1)
    assert rules.turn_verdict(before, after) is None


def test_before_moves_judges_the_pre_move_snapshot(rules: Rules) -> None:
    """The opposite reading, also implemented, also negotiable.

    The same transition gives opposite verdicts under the two settings, which is
    exactly why the flag has to be signed rather than assumed.
    """
    early = Rules(board=BOARD, survival_threshold=35, resolution="before_moves")
    before = GameState(cop=(3, 3), thief=(3, 3))
    after = GameState(cop=(3, 3), thief=(4, 3), step=1)
    assert early.turn_verdict(before, after).verdict is Verdict.CAPTURE
    assert rules.turn_verdict(before, after) is None


# --- C-006b, whether STAY defeats M#47 --------------------------------------


def test_stay_counting_as_a_move_makes_sealing_in_unreachable() -> None:
    """STAY is legal from every cell, so this reading disables M#47 entirely."""
    lenient = Rules(board=BOARD, survival_threshold=35, stay_counts_as_move=True)
    walls = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    state = GameState(cop=(0, 0), thief=(3, 3), barriers=walls)
    assert lenient.sealed_in(state) is False
    assert lenient.verdict(state) is None


def test_the_default_reading_decides_by_adjacency(rules: Rules) -> None:
    walls = frozenset({(2, 3), (4, 3), (3, 2), (3, 4)})
    assert rules.sealed_in(GameState(cop=(0, 0), thief=(3, 3), barriers=walls))


# --- technical loss ---------------------------------------------------------


def test_a_technical_loss_records_its_reason() -> None:
    outcome = Rules.technical_loss("watchdog fired after 60s")
    assert outcome.verdict is Verdict.TECHNICAL_LOSS
    assert "watchdog" in outcome.reason


def test_outcome_is_immutable() -> None:
    """The reason is evidence in a log audit; it must not be editable after."""
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        Outcome(Verdict.CAPTURE, "x").reason = "y"  # type: ignore[misc]


# --- construction from config ----------------------------------------------


def test_rules_are_built_from_the_negotiated_config() -> None:
    """Every terminal condition traces to a signed value, not to a literal."""
    from core.shared.config_manager import load_config
    from tests.paths import PRESENT_ROLES, role_dir

    config = load_config(role_dir(PRESENT_ROLES[0]))
    rules = Rules.from_config(config, Board(grid_size=config.require("board_and_agents.grid_size")))
    assert rules.survival_threshold == 35
    assert rules.resolution == "after_moves"
    assert rules.stay_counts_as_move is False
    assert rules.swap_is_capture is True
    assert rules.board.grid_size == 7
