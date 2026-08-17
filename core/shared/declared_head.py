"""Is the commit we are about to declare one an opponent can actually fetch?

M#53 makes ``github_commit`` a promise, not a label: *the code that played is
the code at this hash*. A hash that resolves nowhere is not a weaker promise, it
is a false one — and because both peers file each other's declaration, one bad
value lands in two teams' artefacts and a grader reads it in both.

Three ways to declare a hash nobody can fetch. We have now shipped all three:

* the working tree is **dirty**, so the hash does not describe the running code
  (imreeyal saw this in our first window on 16/08);
* the repository has **no remote at all** — the development tree, whose commits
  are local by construction. Three windows of ours declared ``55ddff06…`` from
  `p2p-chase`, which has no origin and never will, while the code that should
  have played sat published under two other heads;
* the head is committed and the remote exists, but was **never pushed**.

Read-only and offline. ``git ls-remote`` would be authoritative, but it needs
the network at the exact moment a match is arming, and a pre-flight that can
hang is worse than one that is slightly conservative: the remote-tracking refs
this reads are updated by our own ``git push``, which is the event that matters.
"""

from __future__ import annotations

from pathlib import Path

from core.protocol.step_zero import DIRTY_SUFFIX
from core.shared.git_ops import GitCommandError, run_git

__all__ = ["UnpublishedHeadError", "describe_declared_head"]


class UnpublishedHeadError(RuntimeError):
    """The head we would declare cannot be resolved by anyone but us."""


def describe_declared_head(repo: Path, commit: str) -> str:
    """Return where *commit* is published, or raise saying why it is not.

    Args:
        repo: The clone whose HEAD produced *commit* — the directory holding
            ``core/``, which is the published repository for this role when the
            process was launched correctly and the dev tree when it was not.
        commit: What `commit_hash` returned, ``-dirty`` suffix and all.

    Raises:
        UnpublishedHeadError: The value would be filed into two teams' artefacts and
            resolve for neither.
    """
    if commit.endswith(DIRTY_SUFFIX):
        raise UnpublishedHeadError(
            f"the working tree in {repo} has uncommitted changes, so the head it would "
            f"declare ({commit}) does not describe the code that is about to play"
        )
    if commit == "unknown":
        raise UnpublishedHeadError(f"{repo} is not a git clone, so no head can be declared (M#53)")
    try:
        remotes = [line for line in run_git(["remote"], cwd=repo).splitlines() if line.strip()]
        contains = run_git(["branch", "-r", "--contains", commit], cwd=repo)
    except (GitCommandError, OSError) as error:
        raise UnpublishedHeadError(f"cannot tell whether {commit[:8]} is published: {error}") from error
    if not remotes:
        raise UnpublishedHeadError(
            f"{repo} has no git remote, so its commits are local by construction and "
            f"{commit[:8]} can never resolve for an opponent (M#53).\n"
            "  Launch each role from ITS OWN published repository, not the development tree."
        )
    # `->` drops git's symbolic `origin/HEAD -> origin/main` row, which names no
    # branch of its own and reads as noise in a value we paste into a thread.
    branches = sorted(
        line.strip() for line in contains.splitlines() if line.strip() and "->" not in line
    )
    if not branches:
        raise UnpublishedHeadError(
            f"{commit[:8]} is committed in {repo} but sits on no remote branch — push it "
            "before the match, or the artefact names code the opponent cannot fetch (M#53)"
        )
    return f"{commit}  (published on {', '.join(branches[:3])})"
