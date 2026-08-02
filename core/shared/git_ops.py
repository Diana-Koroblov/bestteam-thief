"""Git command execution with actionable failure messages.

Kept apart from ``scripts/publish.py`` so the publish script stays small and so
the failure-hint table can be unit-tested without running git.

The hints exist because a raw ``CalledProcessError`` traceback tells you a
command failed but not what to do about it, and the common failures here have
specific, non-obvious fixes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

__all__ = ["GitCommandError", "FAILURE_HINTS", "hint_for", "run_git", "has_pending_changes"]


class GitCommandError(RuntimeError):
    """A git command failed. Carries git's own output plus a suggested fix."""


# (substring found in git's output, what to do about it)
FAILURE_HINTS: tuple[tuple[str, str], ...] = (
    (
        "without `workflow` scope",
        "Your GitHub token cannot write .github/workflows/.\n"
        "    Fix (easiest):  gh auth refresh -h github.com -s workflow\n"
        "    Or switch the remote to SSH, or use a token with the 'workflow' scope.",
    ),
    (
        "Authentication failed",
        "GitHub rejected your credentials. Re-authenticate, or use SSH:\n"
        "    git remote set-url origin git@github.com:<user>/<repo>.git",
    ),
    (
        "Repository not found",
        "Check the remote URL and that you have push access:  git remote -v",
    ),
    (
        "non-fast-forward",
        "The remote has commits you do not. Pull first:  git pull --rebase origin main",
    ),
    (
        "rejected",
        "The remote refused the push. Read git's message above for the reason.",
    ),
    (
        "index.lock",
        "A stale lock file from a git process that died or is still running.\n"
        "    This is almost always VS Code's git integration, or an interrupted\n"
        "    ship.py run - not a problem with your repository.\n"
        "    1. CHECK NOTHING IS RUNNING FIRST:   Get-Process git -ErrorAction SilentlyContinue\n"
        "    2. Only if that prints nothing:      Remove-Item .git\\index.lock\n"
        "    Deleting the lock while git really is running can corrupt the index,\n"
        "    so step 1 is not optional.",
    ),
    (
        "does not have a commit checked out",
        "The target directory is not a working clone. Clone the repository there first.",
    ),
)


def hint_for(output: str) -> str:
    """Return advice for *output*, or an empty string when nothing matches."""
    for needle, advice in FAILURE_HINTS:
        if needle in output:
            return advice
    return ""


def run_git(args: list[str], cwd: Path, dry_run: bool = False) -> str:
    """Run a git command in *cwd* and return its combined output.

    Args:
        args: Git arguments, without the leading ``git``.
        cwd: Directory to run in.
        dry_run: Print the command instead of running it.

    Raises:
        GitCommandError: The command exited non-zero.
    """
    if dry_run:
        print(f"    [dry-run] git {' '.join(args)}")
        return ""

    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    output = (result.stdout + result.stderr).strip()

    if result.returncode != 0:
        advice = hint_for(output)
        message = f"git {' '.join(args)} failed in {cwd}\n{output}"
        raise GitCommandError(f"{message}\n\n  How to fix:\n    {advice}" if advice else message)

    return output


def has_pending_changes(cwd: Path) -> bool:
    """Return True when the working tree has staged or unstaged changes."""
    return bool(run_git(["status", "--porcelain"], cwd).strip())
