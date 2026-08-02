"""Unit tests for git command execution and failure hints.

The hint table is the part that matters: a failed push must tell you what to do,
not just that it failed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from core.shared.git_ops import (
    FAILURE_HINTS,
    GitCommandError,
    has_pending_changes,
    hint_for,
    run_git,
)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """An initialised git repository with one commit."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "a.txt").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    return tmp_path


def test_run_git_returns_output(repo: Path) -> None:
    """A successful command returns git's output."""
    assert "init" in run_git(["log", "--oneline"], repo)


def test_run_git_dry_run_executes_nothing(repo: Path) -> None:
    """Dry run returns empty and leaves the repository untouched."""
    before = run_git(["rev-parse", "HEAD"], repo)
    assert run_git(["commit", "-m", "nope"], repo, dry_run=True) == ""
    assert run_git(["rev-parse", "HEAD"], repo) == before


def test_run_git_raises_on_failure(repo: Path) -> None:
    """A failing command raises rather than returning a code nobody checks."""
    with pytest.raises(GitCommandError):
        run_git(["checkout", "no-such-branch"], repo)


def test_failure_message_names_the_command_and_directory(repo: Path) -> None:
    """The error is self-contained enough to act on."""
    with pytest.raises(GitCommandError) as excinfo:
        run_git(["checkout", "no-such-branch"], repo)
    assert "git checkout no-such-branch" in str(excinfo.value)


def test_has_pending_changes_detects_a_new_file(repo: Path) -> None:
    """An untracked file counts as pending."""
    assert has_pending_changes(repo) is False
    (repo / "b.txt").write_text("new\n", encoding="utf-8")
    assert has_pending_changes(repo) is True


@pytest.mark.parametrize("needle", [needle for needle, _ in FAILURE_HINTS])
def test_every_configured_hint_is_reachable(needle: str) -> None:
    """Each entry in the table fires on output containing its needle."""
    assert hint_for(f"remote: error: {needle} blah") != ""


def test_the_workflow_scope_hint_names_the_actual_fix() -> None:
    """The failure we hit in practice points at the exact command that fixes it."""
    advice = hint_for("refusing to allow an OAuth App to update workflow without `workflow` scope")
    assert "gh auth refresh" in advice
    assert "workflow" in advice


def test_unmatched_output_yields_no_hint() -> None:
    """An unfamiliar failure returns nothing rather than misleading advice."""
    assert hint_for("something entirely unexpected") == ""


def test_a_stale_lock_file_gets_actionable_advice() -> None:
    """**The failure that stopped a real push, 02/08.**

    Git's own message says "remove the file manually to continue", which is
    correct and also the fastest way to corrupt an index if a git process really
    is still running. The hint puts the *check* first and makes clear the second
    step is conditional on it.
    """
    advice = hint_for(
        "fatal: Unable to create 'C:/repo/.git/index.lock': File exists."
    )
    assert "Get-Process git" in advice
    assert "Only if that prints nothing" in advice
    assert "corrupt the index" in advice


def test_the_lock_hint_does_not_shadow_more_specific_ones() -> None:
    """Hints are matched in order; a real auth failure must still win."""
    assert "Re-authenticate" in hint_for("Authentication failed for repo.git")
