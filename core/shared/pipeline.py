"""Sequential command pipeline: live output, fail fast, actionable errors.

Every step streams straight to the terminal — nothing is captured — so a failing
test or a lint violation is readable in place rather than buried in a summary.
The first non-zero exit stops the run and reports the exact command to re-run.

Kept apart from ``scripts/ship.py`` so the step table is data that can be
unit-tested without executing anything.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

__all__ = ["Step", "StepError", "GATES", "banner", "run_step", "environment_advice"]

_RULE = "=" * 68


@dataclass(frozen=True)
class Step:
    """One command in the pipeline.

    Attributes:
        name: Human-readable label shown in the banner.
        command: Argument list, executed without a shell.
    """

    name: str
    command: tuple[str, ...]

    @property
    def display(self) -> str:
        """Return the command as a copy-pasteable string."""
        return " ".join(self.command)


class StepError(RuntimeError):
    """A pipeline step exited non-zero. Nothing after it ran."""

    def __init__(self, step: Step, position: int, total: int, cwd: Path, code: int) -> None:
        self.step = step
        self.position = position
        self.total = total
        self.cwd = cwd
        self.code = code
        super().__init__(str(self))

    def __str__(self) -> str:
        """Render the failure as a self-contained report."""
        return (
            f"\n{_RULE}\n"
            f" FAILED at step {self.position}/{self.total}: {self.step.name}\n"
            f"{_RULE}\n"
            f"  Command  : {self.step.display}\n"
            f"  Exit code: {self.code}\n"
            f"  Directory: {self.cwd}\n\n"
            f"  Nothing was committed or pushed.\n"
            f"  The failure output is above, in full.\n\n"
            f"  Re-run just this step while you debug:\n"
            f"    {self.step.display}\n"
            f"{environment_advice(self.cwd)}"
        )


def environment_advice(cwd: Path) -> str:
    """Return advice about the *environment*, checked by state not by output.

    **Deliberately not string-matching on git's message.** The pipeline streams
    every step straight to the terminal and captures nothing — which is what
    makes a failing test readable in place — so there is no output here to
    match against. A stale lock was reported twice before anyone noticed the
    hint table could never fire from this code path.

    Inspecting the filesystem is better anyway: it cannot be defeated by a
    reworded git message or a non-English locale.
    """
    lock = cwd / ".git" / "index.lock"
    if not lock.is_file():
        return ""
    return (
        "\n  *** A stale .git/index.lock is present. ***\n"
        "  Usually VS Code's git integration, or an interrupted ship.py run.\n"
        "  1. Check nothing is running:  Get-Process git -ErrorAction SilentlyContinue\n"
        "  2. Only if that prints nothing:  Remove-Item .git\\index.lock\n"
        "  Deleting the lock while git IS running can corrupt the index,\n"
        "  so step 1 is not optional.\n"
    )


# The four quality gates, in the order that fails cheapest first: lint and file
# size are near-instant, the test suite is the slowest.
GATES: tuple[Step, ...] = (
    Step("Lint (ruff, zero violations)", ("uv", "run", "ruff", "check", ".")),
    Step(
        "File size (max 150 code lines)",
        ("uv", "run", "python", "scripts/check_file_size.py"),
    ),
    Step(
        "Secret scan",
        ("uv", "run", "python", "scripts/scan_secrets.py", "--tracked"),
    ),
    Step("Tests and coverage (>= 85%)", ("uv", "run", "pytest")),
    # The 8.3.6 league benchmark: 192 sub-games, both roles, at the shipped
    # configuration. Its own step and **without coverage**, because tracing
    # costs 6x on this workload — 2:00 becomes 12:14, and it turned the gate
    # above from 4:47 into 15:48. It contributes no coverage the unit suite does
    # not already have (police/ and thief/ report 98-100% there), so the trace
    # buys nothing and the evidence buys everything. Deselected from the default
    # run by `-m 'not slow'` in pyproject.toml and re-selected here, so it still
    # blocks every commit rather than becoming a number nobody re-checks.
    Step(
        "League benchmark (192 sub-games, both roles)",
        ("uv", "run", "pytest", "-m", "slow", "--no-cov"),
    ),
    # Last, because it is the slowest and because it only makes sense once the
    # suite passes here. It is also the only gate that can catch a failure which
    # exists solely after the role split. See scripts/check_split_repos.py.
    Step(
        "Split-repository suite (cop and thief)",
        ("uv", "run", "python", "scripts/check_split_repos.py"),
    ),
)


def banner(text: str) -> None:
    """Print a section header."""
    print(f"\n{_RULE}\n {text}\n{_RULE}", flush=True)


def run_step(step: Step, position: int, total: int, cwd: Path, dry_run: bool = False) -> float:
    """Run one step, streaming its output live.

    Args:
        step: The step to execute.
        position: 1-based index, for the banner.
        total: Total number of steps.
        cwd: Working directory.
        dry_run: Print the command instead of running it.

    Returns:
        Elapsed seconds.

    Raises:
        StepError: The command exited non-zero.
    """
    banner(f"[{position}/{total}] {step.name}")
    print(f"$ {step.display}\n", flush=True)

    if dry_run:
        print("  (dry run - not executed)", flush=True)
        return 0.0

    started = time.monotonic()
    # No capture_output: stdout and stderr are inherited, so output streams
    # to the terminal in real time instead of appearing all at once at the end.
    result = subprocess.run(step.command, cwd=cwd, check=False)
    elapsed = time.monotonic() - started

    if result.returncode != 0:
        raise StepError(step, position, total, cwd, result.returncode)

    print(f"\n  OK ({elapsed:.1f}s)", flush=True)
    return elapsed
