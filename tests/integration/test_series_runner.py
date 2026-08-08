"""Two teams play a whole six-sub-game series and file it (TODO 9.5).

`test_match_driver.py` proves one sub-game can be played. This proves a **match**
can: six sub-games under the negotiated 3-3 split, the roles swapping halfway,
each sub-game closed by a mutual audit, and the four artefacts written to disk.

The four peers this runs on are built in `series_harness.py`; everything here is
a property the series must have once they play.
"""

from __future__ import annotations

import json

import pytest

from core.domain.rules import Verdict
from core.protocol.schemas import Role
from core.report.identifiers import artefact_name
from core.report.match_log import verify_log
from core.runtime.filing import MatchFiling
from tests.integration.series_harness import GAME_ID, play
from tests.paths import brain_class

BOTH_ROLES = pytest.mark.skipif(
    brain_class("police") is None or brain_class("thief") is None,
    reason="a match needs both roles; this repository publishes one (ADR-001)",
)


@BOTH_ROLES
def test_a_full_series_of_six_sub_games_is_played(minimal_config) -> None:
    """**Appendix F Table 18.** A league match is six sub-games, not one."""
    mine, _ = play(minimal_config)
    assert len(mine.sub_games) == 6
    assert [report.sub_game for report in mine.sub_games] == [1, 2, 3, 4, 5, 6]
    # Six real results. A series of technical losses would also be six reports,
    # and would mean the peers never managed to play each other at all.
    assert all(report.outcome.verdict is not Verdict.TECHNICAL_LOSS for report in mine.sub_games)


@BOTH_ROLES
def test_the_roles_swap_halfway_and_the_two_teams_stay_opposite(minimal_config) -> None:
    """The 3-3 split, actually played (C-011, N17).

    Both plans are built from `roles_for` on opposite starting roles, so this
    also checks the thing `settle` now refuses at the handshake: the two teams
    never hold the same role in the same sub-game.
    """
    mine, theirs = play(minimal_config)
    assert [report.role for report in mine.sub_games] == [Role.COP] * 3 + [Role.THIEF] * 3
    assert all(
        ours.role is not opponent.role
        for ours, opponent in zip(mine.sub_games, theirs.sub_games, strict=True)
    )


@BOTH_ROLES
def test_the_two_teams_agree_on_every_sub_game_result(minimal_config) -> None:
    """No referee, so the only check is that both independent scorers match.

    Our points must be their opponent's points in every sub-game. A disagreement
    here means two honest teams would file two contradicting reports, which is
    the failure the whole commit-reveal apparatus exists downstream of.
    """
    mine, theirs = play(minimal_config)
    assert mine.our_points == theirs.their_points
    assert mine.their_points == theirs.our_points
    for ours, opponent in zip(mine.sub_games, theirs.sub_games, strict=True):
        assert ours.outcome.verdict is opponent.outcome.verdict


@BOTH_ROLES
def test_every_sub_game_closes_with_an_audit_that_passes(minimal_config) -> None:
    """M#36. Six mutual audits, none of them accusing an honest opponent."""
    mine, theirs = play(minimal_config)
    assert mine.forged == [] and theirs.forged == []
    assert all(report.audit is not None and report.audit.passed for report in mine.sub_games)


@BOTH_ROLES
def test_a_sub_game_boundary_does_not_leak_into_the_next(minimal_config) -> None:
    """**The bug `start_sub_game` exists to prevent.**

    Everything keyed by step survives a boundary unless it is cleared, and the
    next sub-game reaches step 0 again — so a surviving commit would make
    `on_commit` refuse the opening move as already committed, and a surviving
    history would audit their step 0 against a board from a game that ended.

    `steps > 1` is the assertion that bites. Without the reset each later
    sub-game opens on the previous one's terminal position, plays a single turn
    and ends — which passes every other check in this file, because an empty log
    audits clean and one step is still a step.
    """
    mine, _ = play(minimal_config)
    assert all(report.audit.checked == report.steps for report in mine.sub_games)
    assert all(report.steps > 1 for report in mine.sub_games)


@BOTH_ROLES
def test_the_series_files_all_four_artefacts(tmp_path, minimal_config) -> None:
    """**Ch. 9.2.** The files a grader reads — which nothing wrote until now.

    Two per sub-game plus the result, and the declaration filed alongside. Every
    one under the same `game_id`, which is what makes six logs one match.
    """
    play(minimal_config, tmp_path)
    MatchFiling(game_id=GAME_ID, directory=tmp_path, config=minimal_config).declaration(
        teams={"bestteam": ["id-1"], "opponents": ["id-2"]},
        mcp_urls={"cop": "https://example.invalid/mcp"},
        llm_model="template",
        token_cap=200000,
    )
    for sub_game in range(1, 7):
        assert (tmp_path / artefact_name("log", GAME_ID, sub_game)).is_file()
        assert (tmp_path / artefact_name("config", GAME_ID, sub_game)).is_file()
    assert (tmp_path / artefact_name("result", GAME_ID)).is_file()
    assert (tmp_path / artefact_name("declaration", GAME_ID)).is_file()


@BOTH_ROLES
def test_every_filed_log_verifies_from_disk(tmp_path, minimal_config) -> None:
    """**The mandatory `Verified OK` artefact** (M#20, Ch. 7.4).

    Read back off disk after a JSON round trip, which is where the tuple-vs-list
    class of bug lives, and re-hashed end to end. This is the path the Replay
    Viewer takes, so a green run here is the screenshot.
    """
    play(minimal_config, tmp_path)
    for sub_game in range(1, 7):
        log = json.loads((tmp_path / artefact_name("log", GAME_ID, sub_game)).read_text("utf-8"))
        assert log["unverifiable_steps"] == [], f"sub-game {sub_game} has unsealed steps"
        assert verify_log(log).passed, f"sub-game {sub_game} did not verify"
        assert log["config_sha256"] == minimal_config.shared_digest()


@BOTH_ROLES
def test_the_result_file_does_not_contradict_its_own_sub_games(tmp_path, minimal_config) -> None:
    """A report that disagrees with itself is worse than one that is wrong.

    `totals` is the arithmetic of the rows; `series` is what the tie rule makes
    of it. Both are filed, so neither reads as a mistake.
    """
    mine, _ = play(minimal_config, tmp_path)
    result = json.loads((tmp_path / artefact_name("result", GAME_ID)).read_text("utf-8"))
    assert result["totals"]["sub_games_played"] == 6
    assert result["totals"]["ours"] == sum(row["our_points"] for row in result["sub_games"])
    assert result["totals"]["ours"] == mine.our_points
    assert [row["role"] for row in result["sub_games"]] == ["cop"] * 3 + ["thief"] * 3
    assert all(row["opponent_log_audit"] == "passed" for row in result["sub_games"])


@BOTH_ROLES
def test_each_config_snapshot_pins_the_physics_its_log_was_played_under(
    tmp_path, minimal_config
) -> None:
    """7.2.2. A log without its config is a list of moves nobody can score."""
    play(minimal_config, tmp_path)
    for sub_game in range(1, 7):
        path = tmp_path / artefact_name("config", GAME_ID, sub_game)
        snapshot = json.loads(path.read_text("utf-8"))
        assert snapshot["config_sha256"] == minimal_config.shared_digest()
        assert snapshot["shared_config"] == minimal_config.shared
        assert snapshot["role_split"] == "3-3"
