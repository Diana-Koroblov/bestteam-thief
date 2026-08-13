"""What happens when both role processes write one artefact at once.

Two processes file `declaration_<game_id>.json` and `result_<game_id>.json`
under a single `game_id` — that is the design, and it is what makes six logs
from two processes one match. The writes therefore collide, and this file pins
what the collision may and may not cost.

Every case here comes from a real match rather than from imagination. The
corruption came from the first self-match, the sharing conflict from the
rehearsal over the tunnel, and both had the same consequence: one team's report
missing or unreadable while the other's was filed, which M#35 scores 0 for both.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.domain.rules import Outcome, Verdict
from core.protocol.schemas import Role
from core.report import artefacts
from core.report.artefacts import ArtefactError, write
from core.runtime.filing import MatchFiling
from core.runtime.series import SeriesRunner, SubGameReport


class StubConfig:
    """A config whose shared half is a constant, for filing artefacts."""

    shared: dict = {"grid_size": 7}

    def shared_digest(self) -> str:
        from core.crypto.canonical import digest

        return digest(self.shared)


def test_a_written_artefact_is_always_one_whole_document(tmp_path: Path) -> None:
    """The staging file must never be left where a reader could find it."""
    path = write({"a": 1}, tmp_path, "thing.json")
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1}
    assert list(tmp_path.iterdir()) == [path], "a .tmp file survived the write"


def test_a_blocked_replace_is_waited_out_rather_than_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """🐛 **`os.replace` is atomic on Windows but not always permitted.**

    `MoveFileEx` raises `ERROR_ACCESS_DENIED` while anything else holds the
    destination open, which for a peer reading an artefact lasts milliseconds.
    The rehearsal hit it on the last write of the match and the exception took
    the entire report with it. The condition is transient by nature, so waiting
    is the whole fix.
    """
    real = artefacts.os.replace
    attempts: list[int] = []

    def blocked_twice(src: str, dst: str) -> None:
        attempts.append(1)
        if len(attempts) < 3:
            raise PermissionError(5, "Access is denied")
        real(src, dst)

    monkeypatch.setattr(artefacts.os, "replace", blocked_twice)
    monkeypatch.setattr(artefacts.time, "sleep", lambda _: None)

    path = write({"ok": True}, tmp_path, "thing.json")
    assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True}
    assert len(attempts) == 3, "it must retry, not give up on the first refusal"


def test_a_permanently_blocked_replace_raises_and_leaves_no_litter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When it truly will not clear, say which file and clean up after ourselves.

    A staged `.tmp` left beside the real artefacts is what a grader would find
    in the submission directory, and it looks exactly like a half-written
    report.
    """
    def always_blocked(src: str, dst: str) -> None:
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(artefacts.os, "replace", always_blocked)
    monkeypatch.setattr(artefacts.time, "sleep", lambda _: None)

    with pytest.raises(ArtefactError, match="thing.json"):
        write({"ok": True}, tmp_path, "thing.json")
    assert list(tmp_path.iterdir()) == [], "the staged file was left behind"


def test_the_retry_budget_stays_far_inside_a_step_deadline() -> None:
    """It runs during a match. A minute of patience here is a watchdog loss."""
    budget = artefacts.REPLACE_ATTEMPTS * artefacts.REPLACE_PAUSE_SEC
    assert 0 < budget <= 5.0


# --- the layer underneath: the result must outlive the declaration ----------


def test_the_result_is_filed_even_when_the_declaration_cannot_be_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, score_table
) -> None:
    """🐛 **The one that actually happened, and what it cost.**

    `result` closed the declaration first, so a failure on that write left
    `MatchFiling.result` through `SeriesRunner.run`: a peer that had played
    three clean sub-games printed no scoreboard, filed no `result_<game_id>`
    and sent nothing, while its opponent filed normally. One side reporting and
    the other silent is the contradictory pair M#35 voids matches over.

    The declaration is already on disk — written before the first move — so all
    that is lost is `ended_utc`. The result is what the report is built from.
    """
    filing = MatchFiling(
        game_id="2026-08-13_bestteam-vs-them_deadbeef", directory=tmp_path, config=StubConfig()
    )
    filing.declaration(teams={}, mcp_urls={}, llm_model="llama3.1:8b", token_cap=0)
    assert filing.declaration_path.exists(), "the pre-match declaration is the premise here"

    survived = Outcome(Verdict.SURVIVAL, "thief survived 35 of 35 steps")
    runner = SeriesRunner(
        build=None, plan=[], table=score_table, filing=filing,
        reports=[
            SubGameReport(sub_game=n, role=Role.THIEF, outcome=survived, steps=35)
            for n in (1, 2, 3)
        ],
    )

    def blocked(*args: object, **kwargs: object) -> None:
        raise PermissionError(5, "Access is denied")

    monkeypatch.setattr(MatchFiling, "declaration", blocked)
    runner.finish()

    assert filing.result_path.exists(), "the result was lost to a failure in another artefact"
    assert filing.close_failure, "a silent loss is worse than a loud one"
    assert "PermissionError" in filing.close_failure
