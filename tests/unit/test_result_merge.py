"""One report from two processes (TODO 9.5.4, 7.2.5, M#35).

A 3-3 split is two processes in sequence, and `result_<game_id>.json` is the one
artefact named for the match rather than for a sub-game. The second process to
finish used to overwrite it, filing a three-sub-game report that called itself
the series — self-consistent, contradicting the opponent's report of the same
match, and worth 0 to both teams under M#35.

The tests below are written against that failure: every one of them plays the
two halves in sequence, the way match day does, rather than checking the merge
function on rows it was handed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.domain.rules import Outcome, Rules, Verdict
from core.domain.scoring import ScoreTable
from core.protocol.schemas import Role
from core.report.artefacts import ArtefactError
from core.report.merge import load_rows, merge_rows, series_block
from core.runtime.filing import MatchFiling
from core.runtime.series import SeriesRunner, SubGameReport

GAME_ID = "2026-08-12_bestteam-vs-them_abc12345"

CAPTURE = Outcome(Verdict.CAPTURE, "cop and thief share cell (3, 3)")
SURVIVAL = Outcome(Verdict.SURVIVAL, "thief survived 35 of 35 steps")
LOST = Rules.technical_loss("their commit for step 4 never arrived")


class StubConfig:
    """A config whose shared half is a constant, for filing artefacts."""

    shared: dict = {"grid_size": 7}

    def shared_digest(self) -> str:
        from core.crypto.canonical import digest

        return digest(self.shared)


def half(directory: Path, sub_games, table: ScoreTable, tokens: int = 0) -> Path:
    """File one role process's half of a series and return the result path.

    Goes through `SeriesRunner.finish` and `MatchFiling.result` rather than
    calling the merge directly: the defect was in how those two met, so a test
    that skipped them would have passed against the broken code.
    """
    reports = [
        SubGameReport(
            sub_game=number, role=role, outcome=outcome, steps=35, llm_tokens=tokens
        )
        for number, role, outcome in sub_games
    ]
    filing = MatchFiling(game_id=GAME_ID, directory=directory, config=StubConfig())
    SeriesRunner(build=None, plan=[], table=table, filing=filing, reports=reports).finish()
    return filing.result_path


def read(path: Path) -> dict:
    """Return the filed report."""
    return json.loads(path.read_text(encoding="utf-8"))


COP_HALF = [(1, Role.COP, CAPTURE), (2, Role.COP, CAPTURE), (3, Role.COP, CAPTURE)]
THIEF_HALF = [(4, Role.THIEF, SURVIVAL), (5, Role.THIEF, SURVIVAL), (6, Role.THIEF, SURVIVAL)]


# --- the defect ------------------------------------------------------------


def test_the_second_process_does_not_erase_the_first(tmp_path: Path, score_table) -> None:
    """**The bug.** Six sub-games were played; three used to be reported.

    Our thief repository finishes last, so before the merge the filed result
    described sub-games 4-6 and totalled 30 — while the opponent's report of the
    same match showed six sub-games. A contradictory pair voids the match and
    scores 0 for *both* teams.
    """
    half(tmp_path, COP_HALF, score_table)
    path = half(tmp_path, THIEF_HALF, score_table)

    payload = read(path)
    assert [row["sub_game"] for row in payload["sub_games"]] == [1, 2, 3, 4, 5, 6]
    assert payload["totals"]["sub_games_played"] == 6


def test_the_totals_are_the_whole_series(tmp_path: Path, score_table) -> None:
    """Three captures as Cop and three survivals as Thief is 90-30 by team.

    The arithmetic is `build_result`'s and was never wrong; what was wrong was
    the rows it was given. Asserted on the merged file because that is the
    number a grader compares against the opponent's copy.
    """
    half(tmp_path, COP_HALF, score_table)
    payload = read(half(tmp_path, THIEF_HALF, score_table))

    assert payload["totals"] == {"ours": 90, "theirs": 30, "sub_games_played": 6}


def test_the_league_credit_is_recomputed_over_both_halves(
    tmp_path: Path, score_table
) -> None:
    """**`SeriesReport.summary` knows only its own half, so it cannot be copied.**

    Each half here is the same outcome played from both sides, so each is level
    on its own and so is the series: 25-25, then 15-15, for 40-40. Carrying the
    last process's summary through would file `15` as what the series was worth
    and let the tie rule speak for three sub-games it never saw.
    """
    first = [(1, Role.COP, CAPTURE), (2, Role.THIEF, CAPTURE)]
    second = [(3, Role.COP, SURVIVAL), (4, Role.THIEF, SURVIVAL)]
    half(tmp_path, first, score_table)
    payload = read(half(tmp_path, second, score_table))

    assert payload["series"]["our_points"] == payload["series"]["their_points"] == 40
    assert payload["series"]["verdict"] == Verdict.TIE.value
    assert payload["series"]["our_league_points"] == score_table.tie_score


def test_a_series_decided_on_points_files_the_points(tmp_path: Path, score_table) -> None:
    """The other branch, so the tie case above is not the only one exercised."""
    payload = read(half(tmp_path, COP_HALF, score_table))
    assert payload["series"]["verdict"] == "decided_on_points"
    assert payload["series"]["our_league_points"] == payload["series"]["our_points"] == 60


def test_the_token_total_covers_both_halves(tmp_path: Path, score_table) -> None:
    """**M#54, and the same two-process trap as the points.**

    The reported figure used to be the literal `0`. Summing this process's meter
    instead would be a second version of the bug this module exists to fix: each
    process meters only the three sub-games it played, so the Cop repository
    would file its own consumption as the series'. The sum is taken over the
    merged rows for exactly the reason the totals are.
    """
    half(tmp_path, COP_HALF, score_table, tokens=100)
    payload = read(half(tmp_path, THIEF_HALF, score_table, tokens=50))

    assert [row["llm_tokens"] for row in payload["sub_games"]] == [100, 100, 100, 50, 50, 50]
    assert payload["total_llm_tokens"] == 450


def test_a_zero_token_series_is_still_reported(tmp_path: Path, score_table) -> None:
    """`template` spends nothing, and zero is then the honest answer — which is
    precisely why the old hardcoded zero was so hard to notice."""
    assert read(half(tmp_path, COP_HALF, score_table))["total_llm_tokens"] == 0


# --- re-running a half ------------------------------------------------------


def test_re_running_a_half_replaces_its_own_rows_and_no_others(
    tmp_path: Path, score_table
) -> None:
    """A crashed process is re-run, which must not double-count its sub-games.

    Ours win on a clash because we hold the driver that just played them; the
    other half is untouched because the two processes never plan the same
    sub-game.
    """
    half(tmp_path, COP_HALF, score_table)
    half(tmp_path, THIEF_HALF, score_table)
    payload = read(half(tmp_path, [(4, Role.THIEF, LOST), *THIEF_HALF[1:]], score_table))

    rows = {row["sub_game"]: row for row in payload["sub_games"]}
    assert len(payload["sub_games"]) == 6
    assert rows[4]["verdict"] == Verdict.TECHNICAL_LOSS.value
    assert rows[1]["verdict"] == Verdict.CAPTURE.value


def test_filing_the_same_half_twice_is_idempotent(tmp_path: Path, score_table) -> None:
    """Otherwise a retry inflates the score, which is worse than losing."""
    first = read(half(tmp_path, COP_HALF, score_table))
    second = read(half(tmp_path, COP_HALF, score_table))
    assert first["totals"] == second["totals"]


# --- the pieces -------------------------------------------------------------


def test_rows_are_ordered_by_sub_game_whichever_half_lands_first(
    tmp_path: Path, score_table
) -> None:
    """The thief repository may finish first if the split runs 3-3 the other way."""
    half(tmp_path, THIEF_HALF, score_table)
    payload = read(half(tmp_path, COP_HALF, score_table))
    assert [row["sub_game"] for row in payload["sub_games"]] == [1, 2, 3, 4, 5, 6]


def test_an_absent_file_merges_to_our_rows_alone(tmp_path: Path) -> None:
    """The first process of the two, and every rehearsal, take this path."""
    assert load_rows(tmp_path / "nothing.json") == []
    assert merge_rows([], [{"sub_game": 1}]) == [{"sub_game": 1}]


def test_an_unreadable_result_refuses_rather_than_being_ignored(tmp_path: Path) -> None:
    """**Skipping it would rebuild the exact bug, silently.**

    A file we cannot read still holds the other half of the series. Treating it
    as absent files a report covering our sub-games only — which is how an
    honest match becomes 0 for both teams.
    """
    path = tmp_path / "result_x.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(ArtefactError, match="readable result"):
        load_rows(path)


def test_a_result_without_sub_games_is_not_silently_empty(tmp_path: Path) -> None:
    """A truncated or half-written artefact is a fault, not an empty series."""
    path = tmp_path / "result_x.json"
    path.write_text(json.dumps({"game_id": GAME_ID}), encoding="utf-8")
    with pytest.raises(ArtefactError):
        load_rows(path)


def test_a_series_of_technical_losses_pays_nobody(score_table) -> None:
    """**C-013.** Level at 0-0 is not a tie worth `tie_score` to both sides.

    Checked here as well as in `test_scoring.py` because the merged block is
    computed from filed rows rather than from `Outcome` objects, and a second
    implementation of the tie rule is exactly how the file and the scoreboard
    printed beside it come to disagree.
    """
    rows = [
        {"sub_game": n, "verdict": Verdict.TECHNICAL_LOSS.value, "our_points": 0, "their_points": 0}
        for n in (1, 2)
    ]
    block = series_block(rows, score_table)
    assert block["verdict"] == Verdict.TECHNICAL_LOSS.value
    assert block["our_league_points"] == score_table.technical_loss


def test_the_merged_block_has_the_same_shape_as_a_single_half(
    tmp_path: Path, score_table
) -> None:
    """A reader comparing two teams' reports must not have to notice which
    branch produced the file."""
    reports = [SubGameReport(sub_game=1, role=Role.COP, outcome=CAPTURE, steps=35)]
    runner = SeriesRunner(build=None, plan=[], table=score_table, reports=reports)
    summary = runner.finish().summary()
    assert set(series_block([], score_table)) == set(summary)
