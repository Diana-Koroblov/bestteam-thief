"""Diagnosing and clearing a stale `.git/index.lock` (added 02/08).

Promoted from nuisance to tooling after it stopped three runs in one session.
Telling somebody to delete a lock file is advice with a sharp edge on it: if a
git process really is mid-write, removing the lock lets a second one corrupt the
index. So the rule these tests defend is **refuse on a maybe** — the cost of
being wrong is a broken repository, the cost of refusing is a thirty-second wait.
"""

from __future__ import annotations

import time
from pathlib import Path

from core.shared.git_lock import (
    STALE_AFTER_SEC,
    age_seconds,
    diagnose,
    lock_path,
    release,
)


def _locked(tmp_path: Path, age: float = 0.0) -> Path:
    """Create a lock file, optionally backdated."""
    (tmp_path / ".git").mkdir(exist_ok=True)
    lock = lock_path(tmp_path)
    lock.write_text("", encoding="utf-8")
    if age:
        stamp = time.time() - age
        import os

        os.utime(lock, (stamp, stamp))
    return lock


def test_no_lock_reports_nothing_to_do(tmp_path: Path) -> None:
    assert age_seconds(tmp_path) is None
    assert "nothing is blocking git" in diagnose(tmp_path)
    removed, why = release(tmp_path)
    assert not removed
    assert "No .git/index.lock" in why


def test_a_fresh_lock_is_refused(tmp_path: Path, monkeypatch) -> None:
    """**Refuse on a maybe.** A slow operation can still be alive."""
    monkeypatch.setattr("core.shared.git_lock.git_is_running", lambda: False)
    _locked(tmp_path, age=1.0)
    removed, why = release(tmp_path)
    assert not removed
    assert "REFUSED" in why
    assert lock_path(tmp_path).is_file()


def test_a_lock_is_refused_while_git_is_running(tmp_path: Path, monkeypatch) -> None:
    """Age alone is not enough — a sync agent can make a live lock look old."""
    monkeypatch.setattr("core.shared.git_lock.git_is_running", lambda: True)
    _locked(tmp_path, age=STALE_AFTER_SEC * 10)
    removed, why = release(tmp_path)
    assert not removed
    assert "git process is running" in why
    assert lock_path(tmp_path).is_file()


def test_a_provably_stale_lock_is_removed(tmp_path: Path, monkeypatch) -> None:
    """Both conditions met: no process, and old enough to be certain."""
    monkeypatch.setattr("core.shared.git_lock.git_is_running", lambda: False)
    _locked(tmp_path, age=STALE_AFTER_SEC + 10)
    removed, why = release(tmp_path)
    assert removed
    assert "Removed a stale" in why
    assert not lock_path(tmp_path).is_file()


def test_a_failed_removal_is_reported_not_raised(tmp_path: Path, monkeypatch) -> None:
    """**Never raises.** Observed for real: the file existed but could not be
    unlinked, and reporting it beat a traceback."""
    monkeypatch.setattr("core.shared.git_lock.git_is_running", lambda: False)
    _locked(tmp_path, age=STALE_AFTER_SEC + 10)

    def refuse(self):
        raise OSError("Operation not permitted")

    monkeypatch.setattr(Path, "unlink", refuse)
    removed, why = release(tmp_path)
    assert not removed
    assert "Could not remove" in why


def test_the_process_check_fails_closed(monkeypatch) -> None:
    """**An unknown state must never become permission to delete.**

    If the check itself errors we report True, so a broken `tasklist` makes us
    cautious rather than reckless.
    """
    import subprocess

    from core.shared import git_lock

    def explode(*_args, **_kwargs):
        raise OSError("tasklist missing")

    monkeypatch.setattr(subprocess, "run", explode)
    assert git_lock.git_is_running() is True


def test_diagnose_explains_each_situation(tmp_path: Path, monkeypatch) -> None:
    """"It is locked" is not actionable; *why* it is locked is."""
    monkeypatch.setattr("core.shared.git_lock.git_is_running", lambda: True)
    _locked(tmp_path, age=100)
    assert "RIGHT NOW" in diagnose(tmp_path)

    monkeypatch.setattr("core.shared.git_lock.git_is_running", lambda: False)
    assert "Safe to clear" in diagnose(tmp_path)

    _locked(tmp_path, age=1)
    assert "Too fresh" in diagnose(tmp_path)
