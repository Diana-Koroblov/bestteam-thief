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

__all__ = ["Step", "StepError", "GATES", "banner", "run_step"]

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
