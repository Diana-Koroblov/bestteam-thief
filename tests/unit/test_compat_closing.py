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

from core.compat import sealing
from core.compat.closing import close_sub_game
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

    def __init__(self, their_sealed_commit: str = "s" * 40) -> None:
        self.records = [self._sealed(1)]
        self.their_records = [self._sealed(1, their_sealed_commit)]
        self.received = {1: self.their_records[0]["commit"]}

    @staticmethod
    def _sealed(step: int, github_commit: str = "") -> dict:
        payload = {"step": step, "state": "grid=7x7;self=[1,0];barriers=[]",
                   "move": "S", "intent": "truth", "hint": "moving", "verdict": "truth"}
        if github_commit:
            payload["github_commit"] = github_commit
        return {"payload": payload, **sealing.seal(payload)}


def _close(tmp_path: Path, session=None, their_commit="", their_identity=None, **overrides):
    rows: list[dict] = []
    written: list[Path] = []
    note = close_sub_game(
        sdk=_SDK(), args=argparse.Namespace(out=str(tmp_path), their_commit=their_commit),
        session=session or _Session(), number=1, result="capture",
        verdict={"passed": True, "received": True}, started="2026-08-17T12:00:00+00:00",
        ended="2026-08-17T12:05:00+00:00", their_group="yanell11",
        their_identity=their_identity if their_identity is not None
        else {"github_commit": "s" * 40},
        our_identity={"github_commit": "a" * 40},
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
        assert rows[0]["github_commit"] == {"bestteam": "a" * 40, "yanell11": "s" * 40}
        # We played cop and captured, so Appendix F pays us 20 and them 5.
        assert rows[0]["score"] == {"bestteam": 20, "yanell11": 5}
        assert rows[0]["audit"] == {"log_verified": True, "tampered": False}

    def test_their_commit_is_read_from_what_they_sealed(self, tmp_path: Path) -> None:
        """The sealed record outranks the handshake block (imreeyal, 17/08).

        Their plaintext block says one thing and their commitment says another;
        the commitment is the one that cannot be revised after the fact, so it
        is the one filed.
        """
        rows, _written, note = _close(
            tmp_path, session=_Session(their_sealed_commit="c" * 40),
            their_identity={"github_commit": "d" * 40},
        )
        assert rows[0]["github_commit"]["yanell11"] == "c" * 40
        assert "sealed step-0" in note and "handshake" in note

    def test_agreeing_channels_produce_no_finding(self, tmp_path: Path) -> None:
        """A conformant peer sources its plaintext from its seal, so they match."""
        _rows, _written, note = _close(tmp_path)
        assert note == ""

    def test_the_handshake_block_is_used_when_nothing_was_sealed(self, tmp_path: Path) -> None:
        """A peer that seals no commit is not a peer that declared none."""
        rows, _written, note = _close(
            tmp_path, session=_Session(their_sealed_commit=""),
            their_identity={"github_commit": "d" * 40},
        )
        assert rows[0]["github_commit"]["yanell11"] == "d" * 40
        assert note == ""

    def test_the_seal_outranks_the_operator_flag(self, tmp_path: Path) -> None:
        """🐛 The override used to win, and it cost the 17/08 verification window.

        The reader was correct — imreeyal sealed one head in all six sub-games
        and our logs prove it — but both terminals still carried the old
        `--their-commit` flags, which outranked the evidence and filed the
        pre-fix per-role guess. A value somebody types must never beat one that
        was signed, so the flag now loses and the disagreement is reported.
        """
        rows, _written, note = _close(
            tmp_path, session=_Session(their_sealed_commit="c" * 40), their_commit="e" * 40
        )
        assert rows[0]["github_commit"]["yanell11"] == "c" * 40
        assert "--their-commit" in note

    def test_the_flag_is_used_when_nothing_was_sealed(self, tmp_path: Path) -> None:
        """It stays a fallback: a peer that sealed nothing leaves nothing to outrank."""
        rows, _written, _note = _close(
            tmp_path, session=_Session(their_sealed_commit=""),
            their_identity={}, their_commit="e" * 40,
        )
        assert rows[0]["github_commit"]["yanell11"] == "e" * 40

    def test_an_unwritable_directory_costs_the_files_and_not_the_row(self, tmp_path: Path) -> None:
        """The result is what must survive; a lost log is reported, never raised."""
        blocker = tmp_path / "taken"
        blocker.write_text("not a directory", encoding="utf-8")
        rows, written, note = _close(blocker)
        assert len(rows) == 1
        assert written == []
        assert "artefacts NOT filed" in note
