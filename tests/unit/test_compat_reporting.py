"""Unit tests for core/compat/reporting.py's filing decisions.

The Gmail send path itself is exercised live against the league conformance
kit's sparring peer, not mocked here — see docs/MATCHDAY.md's own posture on
not contacting the live API from a test (PRD 7 §5). What is unit-tested is
what does not need a network: completeness gating, and who gets named winner.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.compat.reporting import _first_meeting, _games_played, send_league_report


def test_games_played_is_ours_and_null_for_an_unclaimed_opponent() -> None:
    """SPEC §6.2: a count is each team's own unverifiable claim, so an emitter
    that cannot know the other side's declares nothing rather than inventing it."""
    result = _games_played("bestteam", "imreeyal")
    assert result["imreeyal"] is None
    assert isinstance(result["bestteam"], int)


def test_a_counted_series_counts_itself_on_both_sides() -> None:
    """The field is `games_played_including_this`, and both inputs are *before*
    counts — so a counted series owes each side its declaration plus one.

    🐛 Filed `{bestteam: 0, imreeyal: 6}` on 17/08 where the truth at T was 1 and
    7. Nothing pinned it, and two honest peers would have printed different
    totals for the same series in front of the grader.
    """
    before = _games_played("bestteam", "imreeyal", {"counted_games_played": 6})
    after = _games_played("bestteam", "imreeyal", {"counted_games_played": 6}, counted=True)

    assert after["imreeyal"] == before["imreeyal"] + 1
    assert after["bestteam"] == before["bestteam"] + 1


def test_a_friendly_counts_for_nobody() -> None:
    """A friendly changes no counted total. Including one would over-declare,
    and over-declaring is the direction M#38 disqualifies for."""
    friendly = _games_played("bestteam", "imreeyal", {"counted_games_played": 6}, counted=False)
    assert friendly["imreeyal"] == 6


def test_an_unclaimed_opponent_stays_null_even_on_a_counted_series() -> None:
    """`null` means *unclaimed*. Incrementing a claim nobody made would turn
    silence into a declaration of 1 that we invented on their behalf."""
    assert _games_played("bestteam", "imreeyal", {}, counted=True)["imreeyal"] is None


def test_a_boolean_is_not_a_declared_count() -> None:
    """`True` is an `int` in Python, so a peer sending `true` would otherwise be
    read as having declared 1 — a claim they never made."""
    assert _games_played("bestteam", "imreeyal", {"counted_games_played": True})["imreeyal"] is None


def test_first_meeting_is_true_for_an_opponent_never_counted_before() -> None:
    assert _first_meeting("a-brand-new-opponent-nobody-has-played") is True


def test_send_league_report_refuses_to_file_with_no_opponent_learned() -> None:
    """No sub-game ever agreed, so nothing is safe to attribute to a name."""
    message = send_league_report(
        sdk=None, args=argparse.Namespace(), rows=[], our_identity={}, their_identity={},
        their_group="",
    )
    assert "NOT FILED" in message
    assert "no opponent" in message


class _StubConfig:
    def __init__(self, data: dict) -> None:
        self._data = data

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def require(self, key: str):
        """Raise on a missing key, exactly as the real Config does.

        A stub whose `require` silently returned None would let a typo'd path
        through here and fail only against a real config file — which is the
        failure mode the real `require` exists to prevent.
        """
        if key not in self._data:
            raise KeyError(key)
        return self._data[key]


class _StubOrchestrator:
    def __init__(self, config: _StubConfig) -> None:
        self.config = config


class _StubRuntime:
    def __init__(self, config: _StubConfig) -> None:
        self.orchestrator = _StubOrchestrator(config)


class _StubSDK:
    """Just enough of PeerSDK for the pre-send (held-back) path — no mailer,
    no gatekeeper: an incomplete series must never reach either."""

    team_name = "bestteam"
    num_games = 6

    def __init__(self, config: _StubConfig) -> None:
        self.runtime = _StubRuntime(config)


def _config() -> _StubConfig:
    return _StubConfig({
        "board_and_agents.grid_size": 7,
        "pheromones.pheromone_grid_size": 5,
        "pheromones.pheromone_decay": 0.1,
        "pheromones.pheromone_center_intensity": 0.9,
        "movement_and_barriers.max_moves": 35,
        "movement_and_barriers.max_barriers": 14,
        "world.map_area": "New York",
        "network_and_league.num_games": 6,
        "scoring.tie_score": 2,
    })


def _row(number: int, *, verified: bool) -> dict:
    """One merged row, either mutually revealed or never engaged."""
    result = "capture" if verified else "technical_loss"
    return {
        "sub_game_number": number, "roles": {"bestteam": "police", "imreeyal": "thief"},
        "started_at": "t0", "ended_at": "t1", "result": result,
        "winner_group": "bestteam" if verified else "",
        "tie": False, "steps": 10 if verified else 0,
        "github_commit": {"bestteam": "a", "imreeyal": "b"},
        "tokens": {"bestteam": 0, "imreeyal": 0},
        "score": {"bestteam": 20 if verified else 0, "imreeyal": 5 if verified else 0},
        "log_files": {"bestteam": "log.json", "imreeyal": "log.json"},
        "audit": {"log_verified": verified, "tampered": False},
    }


def test_a_series_with_an_unplayed_sub_game_is_filed_but_never_mailed(tmp_path: Path) -> None:
    """🐛 **Six rows is not six sub-games.**

    A window nobody played still produces a row — a `technical_loss` — so the
    row-count gate passed on 16/08 and mailed a lecturer-shaped artefact for a
    series in which three of six sub-games never exchanged a turn. Filing it is
    right, because the file is the evidence. Sending it is not: a series
    containing such windows is not a measurement, and no report should be filed
    by either side (imreeyal Stage 7).
    """
    args = argparse.Namespace(
        out=tmp_path, counted=False, report_to="them@example.com,us@example.com"
    )
    rows = [_row(n, verified=n % 2 == 1) for n in range(1, 7)]
    sdk = _StubSDK(_config())

    message = send_league_report(sdk, args, rows, {}, {}, "imreeyal")

    assert "NOT SENT" in message
    assert "[2, 4, 6]" in message, "the unplayed sub-games must be named, not counted"
    written = json.loads((tmp_path / "result_bestteam-vs-imreeyal.json").read_text())
    assert written["num_sub_games"] == 6, "filed in full - it is the evidence"
    assert written["mutual_agreement"]["confirmed"] is False


def test_a_complete_series_is_mailed(tmp_path: Path) -> None:
    """The gate above is load-bearing only if a clean series still goes out."""
    args = argparse.Namespace(out=tmp_path, counted=False, report_to="")
    rows = [_row(n, verified=True) for n in range(1, 7)]

    message = send_league_report(_StubSDK(_config()), args, rows, {}, {}, "imreeyal")

    assert "NOT SENT - friendly, but no --report-to given" in message, message
    written = json.loads((tmp_path / "result_bestteam-vs-imreeyal.json").read_text())
    assert written["mutual_agreement"]["confirmed"] is True


def test_send_league_report_holds_back_an_incomplete_series(tmp_path: Path) -> None:
    args = argparse.Namespace(out=tmp_path, counted=False, report_to="")
    row = {
        "sub_game_number": 1, "roles": {"bestteam": "police", "imreeyal": "thief"},
        "started_at": "t0", "ended_at": "t1", "result": "capture", "winner_group": "bestteam",
        "tie": False, "steps": 10, "github_commit": {"bestteam": "a", "imreeyal": "b"},
        "tokens": {"bestteam": 0, "imreeyal": 0}, "score": {"bestteam": 20, "imreeyal": 5},
        "log_files": {"bestteam": "log.json", "imreeyal": "log.json"},
        "audit": {"log_verified": True, "tampered": False},
    }
    sdk = _StubSDK(_config())
    message = send_league_report(sdk, args, [row], {}, {}, "imreeyal")
    assert "held back" in message
    assert "covers 1 of 6" in message
    # Filed even though incomplete — a partial file is what the other role
    # process's later run merges into (core/compat/league_merge.py).
    written = json.loads((tmp_path / "result_bestteam-vs-imreeyal.json").read_text())
    assert written["num_sub_games"] == 1
