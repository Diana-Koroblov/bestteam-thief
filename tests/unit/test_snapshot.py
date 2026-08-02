"""Crash-time state persistence (TODO 6.4.4).

**Losing a sub-game is survivable; losing the evidence is not.** The audit is
what proves we played honestly, and it can only run over a log that reached the
disk. So every test here is about writing correctly *while something is already
going wrong* — the one situation where ordinary error handling is unavailable.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.runtime.snapshot import SNAPSHOT_NAME, load, save
from core.runtime.watchdog import Watchdog

STATE = {"step": 7, "phase": "awaiting_reveal", "team": "הטובים", "reason": "watchdog"}


def test_a_snapshot_round_trips(tmp_path: Path) -> None:
    assert save(STATE, tmp_path) == tmp_path / SNAPSHOT_NAME
    assert load(tmp_path) == STATE


def test_hebrew_survives_the_write(tmp_path: Path) -> None:
    """Explicit UTF-8. We already lost an afternoon to cp1252 in 6.5.2."""
    save(STATE, tmp_path)
    assert "הטובים" in (tmp_path / SNAPSHOT_NAME).read_text(encoding="utf-8")
    assert load(tmp_path)["team"] == "הטובים"


def test_the_write_leaves_no_temporary_file_behind(tmp_path: Path) -> None:
    """**Atomic: write to a temp file, then `os.replace`.**

    A process dying mid-write would otherwise leave half-written JSON — and a
    truncated snapshot is worse than none, because it looks recoverable right up
    until it is parsed.
    """
    save(STATE, tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == [SNAPSHOT_NAME]


def test_it_creates_the_directory(tmp_path: Path) -> None:
    """A crash must not fail because nobody made the folder first."""
    nested = tmp_path / "runs" / "match-3"
    assert save(STATE, nested) is not None
    assert load(nested) == STATE


def test_saving_never_raises_on_unserialisable_state(tmp_path: Path) -> None:
    """**This runs during a failure.**

    An exception here would replace a recorded technical loss with an unhandled
    traceback, and lose the original reason along with it.
    """
    assert save({"bad": object()}, tmp_path) is None


def test_saving_never_raises_on_an_unwritable_path(tmp_path: Path) -> None:
    blocked = tmp_path / "file"
    blocked.write_text("not a directory", encoding="utf-8")
    assert save(STATE, blocked / "nested") is None


def test_a_missing_snapshot_reads_as_none(tmp_path: Path) -> None:
    assert load(tmp_path) is None


def test_a_corrupt_snapshot_reads_as_none(tmp_path: Path) -> None:
    """Exactly what a crash during an older, non-atomic write would leave.

    A missing file and a corrupt one return the same thing on purpose: the
    caller's response to both is identical — start fresh.
    """
    (tmp_path / SNAPSHOT_NAME).write_text('{"step": 7,', encoding="utf-8")
    assert load(tmp_path) is None


def test_a_snapshot_that_is_not_an_object_reads_as_none(tmp_path: Path) -> None:
    (tmp_path / SNAPSHOT_NAME).write_text("[1, 2, 3]", encoding="utf-8")
    assert load(tmp_path) is None


def test_saving_twice_overwrites_rather_than_appending(tmp_path: Path) -> None:
    save({"step": 1}, tmp_path)
    save({"step": 2}, tmp_path)
    assert load(tmp_path) == {"step": 2}


def test_keys_are_sorted_so_two_snapshots_diff_cleanly(tmp_path: Path) -> None:
    """A replay is compared by eye; reordered keys make a diff unreadable."""
    save({"zeta": 1, "alpha": 2}, tmp_path)
    written = (tmp_path / SNAPSHOT_NAME).read_text(encoding="utf-8")
    assert written.index('"alpha"') < written.index('"zeta"')


def test_the_watchdog_persists_before_it_shuts_down(tmp_path: Path) -> None:
    """**The wiring that makes 6.4.3's promise real.**

    The watchdog's `on_shutdown` runs before the verdict is returned, so state
    reaches the disk while the process is still healthy enough to write it.
    """
    dog = Watchdog(
        timeout=60.0,
        last_beat=0.0,
        on_shutdown=lambda reason: save({"reason": reason, "step": 7}, tmp_path),
    )
    assert dog.check(now=90.0) == "technical_loss"

    recovered = load(tmp_path)
    assert recovered["step"] == 7
    assert "no heartbeat" in recovered["reason"]


def test_the_file_is_valid_json_a_grader_can_open(tmp_path: Path) -> None:
    """It is a submission artefact, not only an internal format."""
    save(STATE, tmp_path)
    assert json.loads((tmp_path / SNAPSHOT_NAME).read_text(encoding="utf-8")) == STATE
