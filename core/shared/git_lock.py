"""Diagnosing and safely clearing a stale ``.git/index.lock`` (added 02/08).

Reported three times in one session, which is what promoted it from a nuisance
to a piece of tooling. Repeating the manual dance was not working, and telling
someone to delete a lock file is advice with a sharp edge on it.

**Why it keeps coming back.** Git creates ``index.lock`` at the start of any
index-modifying command and removes it at the end. It survives only when the
process that made it never finished — a killed ``ship.py``, an editor's
background ``git status``, or an antivirus or cloud-sync agent holding the file
open long enough that git gives up. On Windows all three are common, and the
last one is invisible: the git process is gone, so the usual check finds nothing
and the file still sits there.

**Why deleting it blind is dangerous.** If a git process really is mid-write,
removing the lock lets a second one corrupt the index. So this module refuses
unless two independent conditions hold: no git process is running, **and** the
lock is old enough that any live operation would have finished. Either alone is
too weak — a sync agent can hide a process, and a slow operation can look old.
"""

from __future__ import annotations

import platform
import subprocess
import time
from pathlib import Path

__all__ = ["lock_path", "age_seconds", "git_is_running", "diagnose", "release", "STALE_AFTER_SEC"]

# A live `git add` on this repository finishes in well under a second. Thirty
# gives enormous headroom for a slow disk while still meaning "nothing is
# plausibly using this".
STALE_AFTER_SEC = 30.0


def lock_path(repo: Path) -> Path:
    """Return where the lock lives for *repo*."""
    return repo / ".git" / "index.lock"


def age_seconds(repo: Path, now: float | None = None) -> float | None:
    """Seconds since the lock was created, or None if there is no lock."""
    lock = lock_path(repo)
    if not lock.is_file():
        return None
    return max(0.0, (now if now is not None else time.time()) - lock.stat().st_mtime)


def git_is_running() -> bool:
    """Whether any git process is currently alive.

    Best effort, and deliberately **fails closed**: if the check itself errors we
    report True, so an unknown state never becomes permission to delete.
    """
    windows = platform.system() == "Windows"
    command = (
        ["tasklist", "/FI", "IMAGENAME eq git.exe", "/NH"] if windows else ["pgrep", "-x", "git"]
    )
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return True

    if windows:
        return "git.exe" in result.stdout.lower()
    return result.returncode == 0 and bool(result.stdout.strip())


def diagnose(repo: Path, now: float | None = None) -> str:
    """Explain the current lock situation in words, without changing anything."""
    age = age_seconds(repo, now)
    if age is None:
        return "No .git/index.lock - nothing is blocking git."

    running = git_is_running()
    lines = [
        f"A .git/index.lock exists, created {age:.0f}s ago.",
        f"Git process currently running: {'YES' if running else 'no'}.",
    ]
    if running:
        lines.append(
            "  -> Something is using git RIGHT NOW. Wait for it, or close your"
            " editor. Do not delete the lock while this says YES."
        )
    elif age < STALE_AFTER_SEC:
        lines.append(
            f"  -> Too fresh to call stale (under {STALE_AFTER_SEC:.0f}s)."
            " Wait a moment and check again."
        )
    else:
        lines.append(
            "  -> Stale: no git process, and old enough that any live operation"
            " would have finished. Safe to clear with:  ship.py --unlock"
        )
    return "\n".join(lines)


def release(repo: Path, now: float | None = None) -> tuple[bool, str]:
    """Remove the lock if and only if it is provably stale.

    Returns:
        ``(removed, explanation)``. Never raises, and never removes on a
        maybe — the cost of being wrong is a corrupted index, while the cost of
        refusing is that somebody waits thirty seconds.
    """
    age = age_seconds(repo, now)
    if age is None:
        return False, "No .git/index.lock to remove."
    if git_is_running():
        return False, "REFUSED: a git process is running. Wait, or close your editor."
    if age < STALE_AFTER_SEC:
        return False, (
            f"REFUSED: the lock is only {age:.0f}s old (stale after "
            f"{STALE_AFTER_SEC:.0f}s). Wait and retry."
        )
    try:
        lock_path(repo).unlink()
    except OSError as error:
        return False, f"Could not remove the lock: {error}"
    return True, f"Removed a stale .git/index.lock ({age:.0f}s old)."
