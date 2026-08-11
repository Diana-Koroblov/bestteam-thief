"""Joining two processes' halves of one series into one report (7.2.4, 7.2.5).

A 3-3 split is **two processes in sequence**, because a published repository
ships one brain (ADR-001, M#1): the Cop repository plays sub-games 1-3 and the
Thief repository plays 4-6, both filing into one directory under one `game_id`.

Every other artefact is named per sub-game and so survives that. `result_<game
_id>.json` is the one file named for the whole match, and the second process to
finish **overwrote** it — leaving a report that covered three sub-games and
called itself the series.

That is not a cosmetic defect. `build_result` sums `totals` from the rows it is
given, so the overwritten file was internally consistent and wrong: it reported
our thief's half as the whole match, while the opponent's report of the same
match showed six sub-games against our three. A contradictory pair of reports
voids the match and scores **0 for both teams** (M#35) — the one rule that
punishes the honest team for the paperwork rather than for the play.

So the result is **merged**. Rows are keyed by sub-game number and the
freshly-played ones win, which makes it idempotent in the two ways that matter:
the second process adds its half without disturbing the first, and a process
re-run after a crash replaces its own rows and leaves the other half alone.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.domain.rules import Outcome, Verdict
from core.domain.scoring import ScoreTable, level_series
from core.report.artefacts import ArtefactError

__all__ = ["load_rows", "merge_rows", "series_block", "first_start"]


def first_start(path: Path) -> str:
    """Return the `started_utc` already filed at *path*, or ``""``.

    The declaration is the second artefact named for the whole match rather than
    for a sub-game, so it meets the same two-process problem as the result: both
    of our role processes write it, and the later one must not move the match's
    start time forward past three sub-games that had already been played.

    Unreadable is treated as absent here, unlike `load_rows`. The cost of being
    wrong is a start time stamped a few minutes late in one field; the cost of
    refusing is no declaration at all for a match that was really played.
    """
    if not path.is_file():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return str(payload.get("started_utc", ""))
    except (OSError, ValueError, TypeError):
        return ""


def load_rows(path: Path) -> list[dict[str, Any]]:
    """Return the sub-game rows already filed at *path*, or none if it is absent.

    Raises:
        ArtefactError: The file exists and could not be read as a result. It is
            **not** skipped. Treating an unreadable half as an absent one is
            precisely the bug this module exists to fix — it would file a
            three-sub-game report claiming to be the series, and do it silently.
            Failing here costs an error message at a point where every log and
            config snapshot is already on disk, and `scripts/send_report.py`
            can still file the match by hand.
    """
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload["sub_games"]
        return [dict(row) for row in rows]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ArtefactError(
            f"{path} exists but is not a readable result file ({error}). It holds the "
            "other half of this series; merging into it blind would file a report "
            "covering our sub-games only, which is how a match becomes 0 for both "
            "teams (M#35). Move it aside deliberately, or file by hand with "
            "scripts/send_report.py."
        ) from error


def merge_rows(
    existing: list[dict[str, Any]], ours: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return one row per sub-game, ours winning, in sub-game order.

    Args:
        existing: What is already on disk — the other role process's half, or
            our own from a run that crashed and is being repeated.
        ours: The sub-games this process has just played.

    Ours win on a clash because we hold the driver that played them. The two
    processes never plan the same sub-game (`cli_play.plan_for` filters by
    role), so a clash means a re-run, and a re-run's rows are the later truth.
    """
    by_number = {int(row.get("sub_game", 0)): row for row in existing}
    by_number.update({int(row.get("sub_game", 0)): row for row in ours})
    return [by_number[number] for number in sorted(by_number)]


def series_block(rows: list[dict[str, Any]], table: ScoreTable) -> dict[str, Any]:
    """Return what the merged series is worth, tie rule applied (Ch. 9.2).

    `SeriesReport.summary` answers this for the sub-games one process played.
    Once the halves are merged that answer is wrong twice over: the totals are
    short, and a series level across all six looks decisive across three. So the
    block is recomputed from the merged rows.

    The tie rule itself is **not** re-implemented here — the outcomes are
    reconstructed from the rows and handed to `level_series`, so C-013 (a series
    of nothing but technical losses pays nobody) has one definition and cannot
    drift between the file and the scoreboard printed beside it.
    """
    ours = sum(int(row.get("our_points", 0)) for row in rows)
    theirs = sum(int(row.get("their_points", 0)) for row in rows)
    if ours != theirs:
        return _block("decided_on_points", ours, theirs, ours, theirs)
    outcomes = [
        Outcome(Verdict(str(row.get("verdict", Verdict.TECHNICAL_LOSS.value))), "")
        for row in rows
    ]
    points, verdict = level_series(outcomes, table)
    return _block(verdict.value, ours, theirs, points, points)


def _block(
    verdict: str, ours: int, theirs: int, our_league: int, their_league: int
) -> dict[str, Any]:
    """Shape the block exactly as `SeriesReport.summary` does.

    One shape, whichever way the series was decided: a reader comparing two
    teams' reports should not have to notice that a tie file has different keys.
    """
    return {
        "verdict": verdict,
        "our_points": ours,
        "their_points": theirs,
        "our_league_points": our_league,
        "their_league_points": their_league,
    }
