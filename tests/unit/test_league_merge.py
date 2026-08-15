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


def test_merge_rows_keeps_ours_on_a_clash_and_orders_by_number() -> None:
    existing = [{"sub_game_number": 4, "result": "old"}, {"sub_game_number": 1, "result": "a"}]
    ours = [{"sub_game_number": 4, "result": "new"}]
    merged = merge_rows(existing, ours)
    assert [row["sub_game_number"] for row in merged] == [1, 4]
    assert merged[1]["result"] == "new"


def test_merge_rows_is_idempotent_for_a_rerun_of_our_own_half() -> None:
    existing = [{"sub_game_number": 1}, {"sub_game_number": 2}]
    assert merge_rows(existing, existing) == existing
