"""Unit tests for core/compat/closing.py — that the artefacts actually get written.

`test_compat_match_log.py` proves a log re-verifies once built. This proves one
ever *is*: the gap that cost both imreeyal series was never in the builder, it
was that nothing on this path called one. So these assert against the directory
after a finished sub-game, not against a return value.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from core.compat import sealing
from core.compat.closing import close_sub_game, linger_for_audit
from core.compat.match_log import verify_sub_game_log
from core.domain.scoring import ScoreTable
from core.protocol.schemas import Role

SHARED = {
    "schema_version": "1.2",
    "agreed_between": ["bestteam", "yanell11"],
    "board_and_agents": {"grid_size": 7},
    "pheromones": {"pheromone_decay": 0.1, "decay_model": "multiplicative"},
}


class _Config:
    shared = SHARED

    def get(self, key, default=None):
        return default

    def require(self, key):
        raise KeyError(key)


class _Orchestrator:
    config = _Config()


class _Runtime:
    orchestrator = _Orchestrator()


class _SDK:
    team_name = "bestteam"
    num_games = 6
    runtime = _Runtime()
    # Appendix F's five, so the row carries the real 20/5 rather than a stub's
    # arithmetic — this test asserts on the filed points.
    scoring = ScoreTable(
        capture_cop=20, capture_thief=5, survival_cop=5, survival_thief=10,
        tie_score=2, technical_loss=0,
    )


class _State:
    step = 12


class _Session:
    """A finished sub-game, with the records a real one would be holding."""

    role = Role.COP
    state = _State()
    winner = "cop"

    def __init__(self) -> None:
        self.records = [self._sealed(1)]
        self.their_records = [self._sealed(1)]
        self.received = {1: self.their_records[0]["commit"]}

    @staticmethod
    def _sealed(step: int) -> dict:
        payload = {"step": step, "state": "grid=7x7;self=[1,0];barriers=[]",
                   "move": "S", "intent": "truth", "hint": "moving", "verdict": "truth"}
        return {"payload": payload, **sealing.seal(payload)}


def _close(tmp_path: Path, **overrides):
    rows: list[dict] = []
    written: list[Path] = []
    note = close_sub_game(
        sdk=_SDK(), args=argparse.Namespace(out=str(tmp_path), their_commit=""),
        session=_Session(), number=1, result="capture",
        verdict={"passed": True, "received": True}, started="2026-08-17T12:00:00+00:00",
        ended="2026-08-17T12:05:00+00:00", their_group="yanell11",
        their_identity={"github_commit": "b" * 40}, our_identity={"github_commit": "a" * 40},
        rows=rows, written=written, **overrides,
    )
    return rows, written, note


class TestTheArtefactsExist:
    def test_a_finished_sub_game_writes_its_log_and_its_config(self, tmp_path: Path) -> None:
        """The regression that cost two series: a row was filed and nothing else."""
        _rows, written, note = _close(tmp_path)
        assert note == ""
        names = sorted(path.name for path in written)
        assert names == [
            "config_bestteam-vs-yanell11_g01.json",
            "log_bestteam-vs-yanell11_g01.json",
        ]
        assert all(path.is_file() for path in written)

    def test_the_written_log_re_verifies(self, tmp_path: Path) -> None:
        """Filed evidence has to survive being re-read, or it is not evidence."""
        _rows, written, _note = _close(tmp_path)
        log = json.loads(next(p for p in written if p.name.startswith("log_")).read_text("utf-8"))
        assert verify_sub_game_log(log)["passed"]

    def test_the_log_names_the_config_filed_beside_it(self, tmp_path: Path) -> None:
        """A log naming a digest no neighbouring file explains is unscoreable."""
        _rows, written, _note = _close(tmp_path)
        by_kind = {path.name.split("_")[0]: json.loads(path.read_text("utf-8")) for path in written}
        assert by_kind["log"]["config_sha256"] == by_kind["config"]["config_sha256"]


class TestTheRowStillGoes:
    def test_the_row_is_recorded_alongside(self, tmp_path: Path) -> None:
        rows, _written, _note = _close(tmp_path)
        assert len(rows) == 1
        assert rows[0]["github_commit"] == {"bestteam": "a" * 40, "yanell11": "b" * 40}
        # We played cop and captured, so Appendix F pays us 20 and them 5.
        assert rows[0]["score"] == {"bestteam": 20, "yanell11": 5}
        assert rows[0]["audit"] == {"log_verified": True, "tampered": False}

    def test_an_unwritable_directory_costs_the_files_and_not_the_row(self, tmp_path: Path) -> None:
        """The result is what must survive; a lost log is reported, never raised."""
        blocker = tmp_path / "taken"
        blocker.write_text("not a directory", encoding="utf-8")
        rows, written, note = _close(blocker)
        assert len(rows) == 1
        assert written == []
        assert "artefacts NOT filed" in note


class TestTheDoorStaysOpen:
    """The reference path's own `--linger`, see `linger_for_audit`'s docstring."""

    async def test_it_sleeps_for_the_configured_linger(self, monkeypatch: pytest.MonkeyPatch) -> None:
        slept: list[float] = []
        monkeypatch.setattr("asyncio.sleep", lambda seconds: slept.append(seconds) or _noop())
        await linger_for_audit(argparse.Namespace(linger=7.0))
        assert slept == [7.0]

    async def test_a_zero_linger_does_not_sleep_at_all(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "asyncio.sleep", lambda seconds: (_ for _ in ()).throw(AssertionError("should not sleep"))
        )
        await linger_for_audit(argparse.Namespace(linger=0.0))


async def _noop() -> None:
    return None
