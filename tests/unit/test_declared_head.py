"""Unit tests for the pre-flight that refuses an unfetchable declared head.

Real clones in `tmp_path` rather than a mocked `run_git`: the thing under test
is what git actually reports about remotes and remote-tracking branches, and a
stub would only assert that we wrote the strings we expected to write. Three
windows of ours declared a hash from a remote-less tree while every unit test
passed, which is the failure a stub reproduces perfectly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.protocol.step_zero import DIRTY_SUFFIX
from core.shared.declared_head import UnpublishedHeadError, describe_declared_head
from core.shared.git_ops import run_git


def _clone(path: Path) -> str:
    """Return the HEAD of a fresh one-commit repository at *path*."""
    path.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-q", "-b", "main"], cwd=path)
    run_git(["config", "user.email", "t@example.com"], cwd=path)
    run_git(["config", "user.name", "t"], cwd=path)
    (path / "a.txt").write_text("one", encoding="utf-8")
    run_git(["add", "-A"], cwd=path)
    run_git(["commit", "-qm", "one"], cwd=path)
    return run_git(["rev-parse", "HEAD"], cwd=path).strip()


def test_a_tree_with_no_remote_is_refused(tmp_path: Path) -> None:
    """🐛 **`p2p-chase` has no origin and never will.** Its commits are local by
    construction, so `55ddff06…` resolved for nobody across three windows while
    the code that should have played sat published under two other heads."""
    repo = tmp_path / "devtree"
    head = _clone(repo)
    with pytest.raises(UnpublishedHeadError, match="no git remote"):
        describe_declared_head(repo, head)


def test_a_committed_but_unpushed_head_is_refused(tmp_path: Path) -> None:
    """A remote exists, so the repo looks publishable — but this commit is not
    on it, and the artefact would name code the opponent cannot fetch."""
    origin, repo = tmp_path / "origin", tmp_path / "clone"
    _clone(origin)
    run_git(["clone", "-q", str(origin), str(repo)], cwd=tmp_path)
    run_git(["config", "user.email", "t@example.com"], cwd=repo)
    run_git(["config", "user.name", "t"], cwd=repo)
    (repo / "b.txt").write_text("two", encoding="utf-8")
    run_git(["add", "-A"], cwd=repo)
    run_git(["commit", "-qm", "two"], cwd=repo)
    head = run_git(["rev-parse", "HEAD"], cwd=repo).strip()
    with pytest.raises(UnpublishedHeadError, match="no remote branch"):
        describe_declared_head(repo, head)


def test_a_pushed_head_is_accepted_and_names_where_it_lives(tmp_path: Path) -> None:
    """The gate is load-bearing only if a properly published head still arms."""
    origin, repo = tmp_path / "origin", tmp_path / "clone"
    _clone(origin)
    run_git(["clone", "-q", str(origin), str(repo)], cwd=tmp_path)
    head = run_git(["rev-parse", "HEAD"], cwd=repo).strip()
    described = describe_declared_head(repo, head)
    assert head in described
    assert "origin/main" in described


def test_a_dirty_tree_is_refused_before_git_is_consulted(tmp_path: Path) -> None:
    """The suffix already says the hash does not describe the running code, so
    whether it is pushed is beside the point — imreeyal saw this on 16/08."""
    with pytest.raises(UnpublishedHeadError, match="uncommitted changes"):
        describe_declared_head(tmp_path, "abc123" + DIRTY_SUFFIX)


def test_a_non_clone_is_refused_rather_than_declared_unknown(tmp_path: Path) -> None:
    """`commit_hash` returns "unknown" from an archive rather than raising. That
    is right for playing; it is not a value to file into a league artefact."""
    with pytest.raises(UnpublishedHeadError, match="not a git clone"):
        describe_declared_head(tmp_path, "unknown")
