"""Unit tests for the ship pipeline.

Two behaviours matter and are tested directly: a failing step must stop the run,
and its error must name the exact command to re-run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from core.shared.pipeline import GATES, Step, StepError, banner, run_step

_OK = Step("always succeeds", (sys.executable, "-c", "print('hello from the step')"))
_FAIL = Step("always fails", (sys.executable, "-c", "import sys; sys.exit(3)"))


def test_run_step_returns_elapsed_time(tmp_path: Path) -> None:
    """A successful step reports how long it took."""
    assert run_step(_OK, 1, 1, tmp_path) >= 0.0


def test_run_step_streams_rather_than_captures(tmp_path: Path, capfd) -> None:
    """Child output reaches the terminal, which is what makes debugging easy."""
    run_step(_OK, 1, 1, tmp_path)
    assert "hello from the step" in capfd.readouterr().out


def test_run_step_raises_on_non_zero_exit(tmp_path: Path) -> None:
    """A failing command stops the pipeline instead of being ignored."""
    with pytest.raises(StepError):
        run_step(_FAIL, 2, 4, tmp_path)


def test_failure_reports_position_command_and_exit_code(tmp_path: Path) -> None:
    """The report is self-contained enough to act on without scrolling."""
    with pytest.raises(StepError) as excinfo:
        run_step(_FAIL, 2, 4, tmp_path)
    text = str(excinfo.value)
    assert "step 2/4" in text
    assert "always fails" in text
    assert "Exit code: 3" in text
    assert "Nothing was committed or pushed" in text
    assert _FAIL.display in text


def test_failure_carries_structured_fields(tmp_path: Path) -> None:
    """Callers can inspect the failure, not only print it."""
    with pytest.raises(StepError) as excinfo:
        run_step(_FAIL, 2, 4, tmp_path)
    failure = excinfo.value
    assert failure.code == 3
    assert failure.position == 2
    assert failure.cwd == tmp_path


def test_dry_run_executes_nothing(tmp_path: Path, capfd) -> None:
    """Dry run describes the step without running it, even a failing one."""
    assert run_step(_FAIL, 1, 1, tmp_path, dry_run=True) == 0.0
    assert "not executed" in capfd.readouterr().out


def test_banner_prints_the_text(capfd) -> None:
    """The section header is visible in the stream."""
    banner("Lint")
    assert "Lint" in capfd.readouterr().out


def test_every_gate_is_present() -> None:
    """Lint, file size, secret scan, tests and the league benchmark — none may
    be quietly dropped."""
    labels = " ".join(gate.name for gate in GATES).lower()
    for expected in ("ruff", "file size", "secret", "tests", "benchmark"):
        assert expected in labels


def test_gates_run_the_cheapest_check_first() -> None:
    """Ruff first, so a typo fails in a second rather than a minute.

    The three slowest run last and in dependency order: the ordinary suite, then
    the league benchmark, then the split-repository suite. Neither of the last
    two is worth starting before the ordinary suite passes.
    """
    names = [gate.name for gate in GATES]
    assert names[0].startswith("Lint")
    assert names[-3].startswith("Tests")
    assert names[-2].startswith("League benchmark")
    assert names[-1].startswith("Split-repository")


def test_the_benchmark_gate_re_selects_what_the_default_run_deselects() -> None:
    """**The whole point of the split.** `pyproject.toml` deselects `slow` from
    the default run because coverage tracing costs 6x on 192 sub-games — 2:00
    becomes 12:14. That is only acceptable because this gate runs it anyway, and
    without the tracing that made it expensive. A `-m slow` that stopped being a
    gate would leave the headline numbers unchecked, which is exactly how the
    16-vs-48 opening-count discrepancy survived a whole phase."""
    benchmark = next(gate for gate in GATES if "benchmark" in gate.name.lower())
    assert "-m" in benchmark.command and "slow" in benchmark.command
    assert "--no-cov" in benchmark.command


def test_no_gate_uses_a_shell() -> None:
    """Commands are argument lists, so no quoting or injection surprises."""
    assert all(isinstance(gate.command, tuple) for gate in GATES)


def test_step_display_is_copy_pasteable() -> None:
    """The displayed command can be pasted straight back into the terminal."""
    assert Step("x", ("uv", "run", "pytest")).display == "uv run pytest"


def test_a_stale_lock_is_reported_in_the_failure(tmp_path) -> None:
    """**Reported twice by Diana before anyone noticed why the hint never fired.**

    `git_ops.hint_for` matches on git's output text — but the pipeline streams
    every step straight to the terminal and captures nothing, which is what
    makes a failing test readable in place. There was no output for the hint
    table to match, so it could never fire from this code path.

    Checking the filesystem instead cannot be defeated by a reworded git message
    or a non-English locale.
    """
    from core.shared.pipeline import Step, StepError, environment_advice

    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "index.lock").write_text("", encoding="utf-8")

    advice = environment_advice(tmp_path)
    assert "index.lock" in advice
    assert "Get-Process git" in advice

    reported = str(StepError(Step("Stage", ("git", "add", "-A")), 1, 7, tmp_path, 128))
    assert "stale .git/index.lock" in reported


def test_no_advice_when_the_environment_is_clean(tmp_path) -> None:
    """It must stay quiet, or every unrelated failure grows a red herring."""
    from core.shared.pipeline import environment_advice

    assert environment_advice(tmp_path) == ""
    (tmp_path / ".git").mkdir()
    assert environment_advice(tmp_path) == ""

