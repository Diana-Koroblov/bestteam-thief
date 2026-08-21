"""Unit tests for core/compat/league_merge.py (core/report/merge.py's twin)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.compat.league_merge import load_rows, merge_rows
from core.report.artefacts import ArtefactError


def test_load_rows_is_empty_for_an_absent_file(tmp_path: Path) -> None:
    assert load_rows(tmp_path / "missing.json") == []


def test_load_rows_reads_sub_games_back(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    path.write_text(json.dumps({"sub_games": [{"sub_game_number": 1}]}), encoding="utf-8")
    assert load_rows(path) == [{"sub_game_number": 1}]


def test_load_rows_refuses_an_unreadable_file_rather_than_treating_it_as_absent(
    tmp_path: Path,
) -> None:
    """M#35: silently treating the other role process's half as absent files a
    report covering only our sub-games while claiming to be the series."""
    path = tmp_path / "result.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(ArtefactError):
        load_rows(path)


def _filed(uid: str, began: str) -> str:
    """A filed result whose one row began at *began* (ISO-8601, or bare date)."""
    stamp = f"{began}T17:13:42+00:00" if len(began) == 10 else began
    return json.dumps(
        {"game_uid": uid, "sub_games": [{"sub_game_number": 1, "started_at": stamp}]}
    )


def test_load_rows_refuses_a_second_series_played_under_the_same_terms(
    tmp_path: Path,
) -> None:
    """The real case. `result_<game_id>.json` is only the team pair, so a
    later series against the same opponent claims an earlier one's filename —
    and because the config never changed between them, both carry the same
    `game_uid` too. Only when they began separates them, which is why that is
    checked, and a plain calendar date could not tell two runs on one
    afternoon apart."""
    path = tmp_path / "result_bestteam-vs-imreeyal.json"
    same_uid = "ffad01a2-4965-be0b-c708-3cdbedd7373a"
    path.write_text(_filed(same_uid, "2026-08-16"), encoding="utf-8")
    with pytest.raises(ArtefactError, match="2026-08-16"):
        load_rows(path, same_uid, "2026-08-17T09:00:00+00:00")


def test_load_rows_refuses_two_runs_on_one_afternoon(tmp_path: Path) -> None:
    """🐛 The bug a date-only check missed: same day, same unchanged terms, a
    re-match hours apart — the date matches and so does the uid."""
    path = tmp_path / "result.json"
    same_uid = "ffad01a2-4965-be0b-c708-3cdbedd7373a"
    path.write_text(_filed(same_uid, "2026-08-17T09:00:00+00:00"), encoding="utf-8")
    with pytest.raises(ArtefactError, match="apart"):
        load_rows(path, same_uid, "2026-08-17T17:13:42+00:00")


def test_load_rows_refuses_a_series_played_under_renegotiated_terms(
    tmp_path: Path,
) -> None:
    """The second net: different terms move the uid even on the same day."""
    path = tmp_path / "result.json"
    path.write_text(_filed("old-terms-uid", "2026-08-17"), encoding="utf-8")
    with pytest.raises(ArtefactError, match="other terms"):
        load_rows(path, "new-terms-uid", "2026-08-17T17:13:42+00:00")


def test_load_rows_merges_the_other_role_process_half_of_the_same_series(
    tmp_path: Path,
) -> None:
    """The case that must still merge (M#35): one series, two role processes,
    same terms and close together in time."""
    path = tmp_path / "result.json"
    path.write_text(_filed("same-uid", "2026-08-17T17:00:00+00:00"), encoding="utf-8")
    rows = load_rows(path, "same-uid", "2026-08-17T17:13:42+00:00")
    assert rows[0]["sub_game_number"] == 1


def test_load_rows_still_merges_a_file_that_recorded_neither_uid_nor_timestamp(
    tmp_path: Path,
) -> None:
    """Unknown is not a mismatch — refusing on a file an older build wrote
    would strand the other half of a legitimate series."""
    path = tmp_path / "result.json"
    path.write_text(json.dumps({"sub_games": [{"sub_game_number": 2}]}), encoding="utf-8")
    assert load_rows(path, "new-uid", "2026-08-17T17:13:42+00:00") == [{"sub_game_number": 2}]


def test_merge_rows_keeps_ours_on_a_clash_and_orders_by_number() -> None:
    existing = [{"sub_game_number": 4, "result": "old"}, {"sub_game_number": 1, "result": "a"}]
    ours = [{"sub_game_number": 4, "result": "new"}]
    merged = merge_rows(existing, ours)
    assert [row["sub_game_number"] for row in merged] == [1, 4]
    assert merged[1]["result"] == "new"


def test_merge_rows_is_idempotent_for_a_rerun_of_our_own_half() -> None:
    existing = [{"sub_game_number": 1}, {"sub_game_number": 2}]
    assert merge_rows(existing, existing) == existing
