"""The role plan and the arithmetic of a series (TODO 9.5, C-011).

The driver is tested against a live opponent in `tests/integration/`; this
covers the parts that decide *which* sub-games are played and *what they are
worth*, both of which are pure functions of things already agreed.
"""

from __future__ import annotations

import pytest

from core.domain.rules import Outcome, Rules, Verdict
from core.protocol.schemas import Role
from core.runtime.series import SeriesRunner, SubGameReport, roles_for

CAPTURE = Outcome(Verdict.CAPTURE, "cop and thief share cell (3, 3)")
SURVIVAL = Outcome(Verdict.SURVIVAL, "thief survived 35 of 35 steps")
LOST = Rules.technical_loss("their commit for step 4 never arrived")


def _report(sub_game: int, role: Role, outcome: Outcome, audit=None) -> SubGameReport:
    """One finished sub-game, with no driver behind it."""
    return SubGameReport(sub_game=sub_game, role=role, outcome=outcome, steps=10, audit=audit)


def _runner(reports, table) -> SeriesRunner:
    """A runner that has already played, for testing `finish` on its own."""
    return SeriesRunner(build=None, plan=[], table=table, reports=list(reports))


def test_the_negotiated_split_gives_three_sub_games_of_each() -> None:
    """3-3 is what we propose and refuse to play without (C-011, N17)."""
    assert roles_for("3-3", Role.COP, 6) == [Role.COP] * 3 + [Role.THIEF] * 3


def test_the_plan_starts_from_our_own_role_not_from_the_split() -> None:
    """**The string is symmetric and settles nothing about who starts.**

    Both peers send the identical `"3-3"` and agree. What makes the two plans
    opposite is each peer building its own from the role it holds — which is
    exactly why `settle` refuses two peers claiming the same one.
    """
    ours = roles_for("3-3", Role.COP, 6)
    theirs = roles_for("3-3", Role.THIEF, 6)
    assert all(mine is not yours for mine, yours in zip(ours, theirs, strict=True))


def test_a_split_that_alternates_every_sub_game_is_expressible() -> None:
    """Nothing in the rulebook fixes the shape, only the total of 6."""
    assert roles_for("1-1-1-1-1-1", Role.THIEF, 6)[:3] == [Role.THIEF, Role.COP, Role.THIEF]


@pytest.mark.parametrize("split", ["3-4", "6", "", "three-three", "2-2"])
def test_a_split_that_does_not_cover_the_series_is_refused(split: str) -> None:
    """Loud, because the alternative is discovering it after the match.

    A plan covering five sub-games of six plays a whole series before anyone
    notices, and by then the opponent has filed a report that disagrees with
    ours about a sub-game we never played.
    """
    with pytest.raises(ValueError):
        roles_for(split, Role.COP, 6)


def test_our_points_follow_the_role_we_played(score_table) -> None:
    """A capture pays 20 to the Cop — which is us in one of these and not the other."""
    assert _report(1, Role.COP, CAPTURE).points(score_table) == (20, 5)
    assert _report(4, Role.THIEF, CAPTURE).points(score_table) == (5, 20)


def test_a_swapped_series_is_scored_by_team_and_not_by_role(score_table) -> None:
    """**The bug `level_series` was split out to prevent.**

    Three captures as Cop and three survivals as Thief is 60+30 = 90 for us and
    15+15 = 30 for them. Summing by role instead would total the Cop column
    across all six — crediting us with the opponent's three sub-games and
    reporting a 75-45 series that nobody played.
    """
    reports = [_report(n, Role.COP, CAPTURE) for n in (1, 2, 3)]
    reports += [_report(n, Role.THIEF, SURVIVAL) for n in (4, 5, 6)]
    series = _runner(reports, score_table).finish()
    assert (series.our_points, series.their_points) == (90, 30)
    assert series.verdict is None and series.league_points is None


def test_a_level_series_pays_the_tie_score_to_both(score_table) -> None:
    """Ch. 9.2: no meeting is left without a scoring decision."""
    reports = [_report(1, Role.COP, CAPTURE), _report(2, Role.THIEF, CAPTURE)]
    series = _runner(reports, score_table).finish()
    assert (series.our_points, series.their_points) == (25, 25)
    assert series.verdict is Verdict.TIE
    assert series.summary()["our_league_points"] == score_table.tie_score


def test_a_series_of_technical_losses_pays_nobody(score_table) -> None:
    """C-013. Two teams that crashed six times each must not outscore one that played."""
    series = _runner([_report(n, Role.COP, LOST) for n in (1, 2, 3)], score_table).finish()
    assert series.verdict is Verdict.TECHNICAL_LOSS
    assert series.summary()["our_league_points"] == 0


def test_the_summary_reports_the_points_when_they_decide_it(score_table) -> None:
    """A decided series has no tie bonus, so the league credit is the total."""
    series = _runner([_report(1, Role.COP, CAPTURE)], score_table).finish()
    assert series.summary() == {
        "verdict": "decided_on_points",
        "our_points": 20,
        "their_points": 5,
        "our_league_points": 20,
        "their_league_points": 5,
    }


def test_a_failed_audit_is_reported_and_never_self_scored(score_table) -> None:
    """**M#19, Ch. 5.4.** A forgery is evidence we file, not a verdict we award.

    The sanction is a total technical loss for the forger, awarded by a league
    holding both reports — not by the accusing peer, scoring its own match from
    its own re-hash. So the sub-game keeps the points it was played for and the
    finding is filed beside them.
    """
    forged = type("Audit", (), {"passed": False})()
    series = _runner([_report(1, Role.COP, CAPTURE, audit=forged)], score_table).finish()
    assert series.forged == [1]
    assert series.our_points == 20
    assert series.rows(score_table)[0]["opponent_log_audit"] == "FAILED"


def test_an_unfinished_closing_exchange_is_not_an_accusation(score_table) -> None:
    """No audit and a failed audit are different findings and must read differently."""
    series = _runner([_report(1, Role.COP, CAPTURE, audit=None)], score_table).finish()
    assert series.forged == []
    assert series.rows(score_table)[0]["opponent_log_audit"] == "not_run"
