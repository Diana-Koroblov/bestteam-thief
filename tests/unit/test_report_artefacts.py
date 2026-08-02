"""The four match artefacts (TODO 7.2.1-7.2.4).

These are the files a grader reads, which changes what "correct" means. Two
rules run through every test: **nothing is invented**, and **everything is
written as UTF-8 bytes**. A plausible-looking placeholder in a submitted report
is worse than an absent field — a missing field prompts a question, a wrong one
does not.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.report.artefacts import REPO_LINKS, build_declaration, build_result, write

NON_ASCII_TEAM = "Ωμέγα-Ünïcode"
TEAMS = {"bestteam": ["Diana", "Itay"], NON_ASCII_TEAM: ["A", "B"]}
REPOS = {"ours_cop": "https://github.com/x/bestteam-cop"}
SUB_GAMES = [
    {"role": "cop", "verdict": "capture", "our_points": 20, "their_points": 5},
    {"role": "thief", "verdict": "survival", "our_points": 10, "their_points": 5},
]


def _declaration() -> dict:
    return build_declaration(
        "2026-08-12_a-vs-b_abc", TEAMS, REPOS, {"ours": "https://x.ngrok.dev"}, "llama3.1:8b", 50_000
    )


# --- 7.2.1 declaration ------------------------------------------------------


def test_all_four_repository_links_are_present() -> None:
    """**Four, not two.** Both teams' repos for both roles, so a grader can
    read every agent that played."""
    assert set(_declaration()["repositories"]) == set(REPO_LINKS)
    assert len(REPO_LINKS) == 4


def test_a_missing_repository_is_recorded_as_empty_not_omitted() -> None:
    """A reader must be able to see *which* link is absent.

    Omitting the key would make an incomplete report look complete.
    """
    repositories = _declaration()["repositories"]
    assert repositories["ours_cop"].endswith("bestteam-cop")
    assert repositories["theirs_thief"] == ""


def test_it_declares_the_model_never_the_provider() -> None:
    """Appendix F Table 21 keeps the provider private to each peer."""
    declared = _declaration()
    assert declared["llm_model"] == "llama3.1:8b"
    assert "provider" not in json.dumps(declared)


def test_the_timestamp_is_utc() -> None:
    """Both peers are in one timezone today and may not be tomorrow; a local
    timestamp would make two reports disagree about when a match happened."""
    assert _declaration()["created_utc"].endswith("+00:00")


# --- 7.2.4 result -----------------------------------------------------------


def test_totals_are_summed_here_rather_than_trusted() -> None:
    """**A report that contradicts itself is worse than one merely wrong.**

    A caller supplying its own total could disagree with the per-sub-game rows
    printed in the same file.
    """
    result = build_result("gid", SUB_GAMES, "abc123", 1234, REPOS)
    assert result["totals"] == {"ours": 30, "theirs": 10, "sub_games_played": 2}


def test_the_result_names_the_code_that_produced_it() -> None:
    """M#53 — a result without a commit cannot be reproduced."""
    result = build_result("gid", SUB_GAMES, "abc123", 1234, REPOS)
    assert result["github_commit"] == "abc123"
    assert result["total_llm_tokens"] == 1234


def test_an_empty_series_totals_zero_rather_than_failing() -> None:
    """A match abandoned before sub-game 1 still has to file a report."""
    assert build_result("gid", [], "abc", 0, REPOS)["totals"]["sub_games_played"] == 0


# --- writing ----------------------------------------------------------------


def test_non_ascii_survives_the_write(tmp_path: Path) -> None:
    """The rule from 6.5.2, applied where it will actually be exercised.

    Team names are student-chosen and need not be ASCII. A cp1252 console would
    raise on this, which is why the file is written as explicit UTF-8 bytes.
    """
    target = write(_declaration(), tmp_path, "declaration.json")
    assert NON_ASCII_TEAM in target.read_text(encoding="utf-8")
    assert json.loads(target.read_text(encoding="utf-8"))["teams"][NON_ASCII_TEAM] == ["A", "B"]


def test_the_file_is_written_as_bytes_not_console_text(tmp_path: Path) -> None:
    """Explicit UTF-8 bytes cannot be defeated by a cp1252 console default."""
    target = write({"team": NON_ASCII_TEAM}, tmp_path, "x.json")
    assert target.read_bytes().decode("utf-8")


def test_keys_are_sorted_so_two_reports_diff_cleanly(tmp_path: Path) -> None:
    body = write({"zeta": 1, "alpha": 2}, tmp_path, "x.json").read_text(encoding="utf-8")
    assert body.index('"alpha"') < body.index('"zeta"')


def test_it_creates_the_directory(tmp_path: Path) -> None:
    assert write({"a": 1}, tmp_path / "runs" / "match", "x.json").is_file()


def test_writing_a_report_raises_on_failure_unlike_a_snapshot(tmp_path: Path) -> None:
    """**The deliberate asymmetry with `runtime.snapshot.save`.**

    A snapshot is written while something is already going wrong and must never
    make it worse. A report is written on purpose, and silently failing to
    produce a submission artefact would be discovered only by its absence in the
    grader's inbox — which is to say, too late.
    """
    import pytest

    blocked = tmp_path / "file"
    blocked.write_text("not a directory", encoding="utf-8")
    with pytest.raises(OSError):
        write({"a": 1}, blocked / "nested", "x.json")


def test_a_grader_can_open_it(tmp_path: Path) -> None:
    """It is a submission artefact, not only an internal format."""
    target = write(build_result("gid", SUB_GAMES, "abc", 10, REPOS), tmp_path, "r.json")
    assert json.loads(target.read_text(encoding="utf-8"))["totals"]["ours"] == 30
