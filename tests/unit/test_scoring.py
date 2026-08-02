"""Unit tests for scoring and series aggregation (PRD 1 §3.5, T1.16).

M#48 requires every value to come from config. The test that matters most is
that the shipped table matches Appendix F exactly — a scoring bug is invisible
during play and only surfaces when the lecturer totals the league.
"""

from __future__ import annotations

import pytest

from core.domain.rules import Outcome, Verdict
from core.domain.scoring import ScoreTable, aggregate, score

TABLE = ScoreTable(
    capture_cop=20,
    capture_thief=5,
    survival_cop=5,
    survival_thief=10,
    tie_score=2,
    technical_loss=0,
)

CAPTURE = Outcome(Verdict.CAPTURE, "co-located")
SURVIVAL = Outcome(Verdict.SURVIVAL, "35 steps")
TECHNICAL = Outcome(Verdict.TECHNICAL_LOSS, "timeout")


def test_the_shipped_config_matches_appendix_f(score_table: ScoreTable) -> None:
    """The values we will actually play with, not the ones in this test file.

    Everything below uses the local ``TABLE``; this one test ties it back to the
    config, so a drift in the shipped file fails here rather than in the league.
    """
    assert score_table == TABLE


# --- one sub-game (T1.16) ---------------------------------------------------


def test_capture_pays_twenty_five() -> None:
    assert score(CAPTURE, TABLE) == (20, 5)


def test_survival_pays_five_ten() -> None:
    assert score(SURVIVAL, TABLE) == (5, 10)


def test_a_technical_loss_zeroes_both_sides() -> None:
    """Ch. 3.5: "a technical loss zeroes both sides alike".

    Neither side profits from the other's crash or timeout, which is why no
    strategy should ever be built around stressing an opponent's clock.
    """
    assert score(TECHNICAL, TABLE) == (0, 0)


def test_a_tie_has_no_sub_game_score() -> None:
    """It is decided across a series; returning something here would hide a bug."""
    with pytest.raises(ValueError, match="not a sub-game verdict"):
        score(Outcome(Verdict.TIE, "equal"), TABLE)


def test_capture_is_worth_more_in_total_than_survival() -> None:
    """25 against 15. The pot is bigger when the Cop forces a result."""
    assert sum(score(CAPTURE, TABLE)) > sum(score(SURVIVAL, TABLE))


def test_neither_role_mirrors_the_other() -> None:
    """The asymmetry is the engine: each side's best outcome is different."""
    assert TABLE.capture_cop > TABLE.survival_cop
    assert TABLE.survival_thief > TABLE.capture_thief


# --- a series ---------------------------------------------------------------


def test_a_clean_sweep_for_the_cop() -> None:
    result = aggregate([CAPTURE] * 6, TABLE)
    assert (result.cop_points, result.thief_points) == (120, 30)
    assert result.verdict is Verdict.CAPTURE
    assert result.sub_games == 6


def test_a_clean_sweep_for_the_thief() -> None:
    result = aggregate([SURVIVAL] * 6, TABLE)
    assert (result.cop_points, result.thief_points) == (30, 60)
    assert result.verdict is Verdict.SURVIVAL


def test_equal_totals_award_the_tie_score_to_both() -> None:
    """Appendix F: a tie pays both sides, not neither."""
    result = aggregate([CAPTURE, SURVIVAL], TABLE)  # 25 vs 15... not equal
    assert result.verdict is Verdict.CAPTURE

    balanced = aggregate([CAPTURE, SURVIVAL, SURVIVAL, SURVIVAL], TABLE)
    assert (balanced.cop_points, balanced.thief_points) == (2, 2)
    assert balanced.verdict is Verdict.TIE


def test_the_tie_is_decided_on_cumulative_points_not_sub_games_won() -> None:
    """Three wins each is not a tie: 3 captures and 3 survivals is 75 to 45."""
    result = aggregate([CAPTURE] * 3 + [SURVIVAL] * 3, TABLE)
    assert (result.cop_points, result.thief_points) == (75, 45)
    assert result.verdict is not Verdict.TIE


def test_a_technical_loss_drags_the_whole_series_down() -> None:
    with_loss = aggregate([CAPTURE, CAPTURE, TECHNICAL], TABLE)
    without = aggregate([CAPTURE, CAPTURE], TABLE)
    assert with_loss.cop_points == without.cop_points
    assert with_loss.sub_games == 3


def test_a_series_that_never_actually_played_pays_nothing() -> None:
    """C-013: 0 == 0 is arithmetically a tie, but paying the bonus for it would
    reward two teams for crashing every sub-game."""
    result = aggregate([TECHNICAL] * 6, TABLE)
    assert result.verdict is Verdict.TECHNICAL_LOSS
    assert (result.cop_points, result.thief_points) == (0, 0)


def test_an_empty_series_pays_nothing() -> None:
    """Two teams that never played are level at zero, not level at the bonus."""
    assert aggregate([], TABLE).verdict is Verdict.TECHNICAL_LOSS
    assert aggregate([], TABLE).cop_points == 0


def test_one_real_sub_game_is_enough_to_earn_a_genuine_tie() -> None:
    """A series is not void just because some sub-games failed."""
    result = aggregate([TECHNICAL, CAPTURE, SURVIVAL, SURVIVAL, SURVIVAL], TABLE)
    assert (result.cop_points, result.thief_points) == (2, 2)
    assert result.verdict is Verdict.TIE


# --- no literals ------------------------------------------------------------


def test_scoring_reads_a_raised_table_without_a_code_change() -> None:
    """M#12 permits raising values by agreement; nothing here is hardcoded."""
    raised = ScoreTable(
        capture_cop=30, capture_thief=5, survival_cop=5, survival_thief=15,
        tie_score=3, technical_loss=0,
    )
    assert score(CAPTURE, raised) == (30, 5)
    assert aggregate([CAPTURE, SURVIVAL, SURVIVAL], raised).cop_points == 40
