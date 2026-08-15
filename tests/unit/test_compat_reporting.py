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
    })


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
