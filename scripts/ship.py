"""One command: gates, commit, publish to both repositories.

    uv run python scripts/ship.py -m "feat: barriers and capture rules"

Order of operations::

    1. git add -A          stage everything first, so the secret scan sees
                           brand-new files too, not just already-tracked ones
    2. ruff                zero violations
    3. file size           no file over 150 code lines
    4. secret scan         no API keys or private keys
    5. pytest              all pass, coverage >= 85%
    6. git commit          only if something changed
    7. publish.py          split-publish to bestteam-cop and bestteam-thief

The first failure stops everything. Nothing is committed and nothing is pushed
unless every gate is green, which is the point: it should not be possible to
publish a red tree by forgetting a step.

There is deliberately no --skip-gates flag. If you genuinely need to bypass
them, run scripts/publish.py directly and know that you are doing it.

--skip-league is a narrow, explicit exception: it drops only the league
benchmark step (192 sub-games, ~2 minutes), leaving lint, file size, secret
scan, the unit suite and coverage, and the split-repository check all in
place. It exists for fast iteration; it must be typed on purpose every time,
never defaulted on, so a red benchmark can't slip through unnoticed the way
the 16-vs-48 opening-count discrepancy once did.

--simple is a second, wider exception for the same reason: it drops the
league benchmark AND the unit/integration test gate (the self-play batches
in tests/integration/ are the slow part of that gate), leaving lint, file
size, the secret scan, and the split-repository check. Same rule as
--skip-league - typed on purpose every time, never defaulted on, and it does
not replace a real `ship.py` run before anything that actually matters ships.

Two lock helpers, because a stale .git/index.lock stopped three runs in one
session::

    ship.py --why-locked       explain the situation, change nothing
    ship.py --unlock -m "..."  clear it first, but only if provably stale

`--unlock` refuses unless no git process is running AND the lock is older than
30 s. The cost of being wrong is a corrupted index; the cost of refusing is that
somebody waits half a minute.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.shared.git_lock import diagnose, release  # noqa: E402
from core.shared.git_ops import GitCommandError, has_pending_changes, run_git  # noqa: E402
from core.shared.pipeline import GATES, Step, StepError, banner, run_step  # noqa: E402

__all__ = ["main", "build_steps"]


def build_steps(
    message: str, role: str, dry_run: bool, skip_league: bool = False, simple: bool = False
) -> tuple[Step, ...]:
    """Return the full pipeline: stage, gates, then publish.

    skip_league drops only the league benchmark gate; simple additionally drops
    the unit/integration test gate (see module docstring). Every other gate
    still runs.
    """
    stage = Step("Stage all changes", ("git", "add", "-A"))
    drop_league = skip_league or simple
    gates = tuple(
        gate
        for gate in GATES
        if not (drop_league and "League benchmark" in gate.name)
        and not (simple and "Tests and coverage" in gate.name)
    )
    publish_command = ["uv", "run", "python", "scripts/publish.py", "--role", role, "-m", message]
    if dry_run:
        publish_command.append("--dry-run")
    publish = Step("Publish to both repositories", tuple(publish_command))
    return (stage, *gates, publish)


def _commit(message: str, dry_run: bool) -> None:
    """Commit the staged changes, or report that there is nothing to commit."""
    banner("Commit to the working tree")
    if dry_run:
        print(f"  (dry run) git commit -m {message!r}", flush=True)
        return
    if not has_pending_changes(ROOT):
        print("  Nothing new to commit - republishing the current tree.", flush=True)
        return
    print(run_git(["commit", "-m", message], ROOT), flush=True)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run the quality gates, commit, and publish to both repositories."
    )
    parser.add_argument("--message", "-m", required=True, help="Commit message.")
    parser.add_argument(
        "--unlock",
        action="store_true",
        help="Clear a stale .git/index.lock first, but only if it is provably "
        "stale: no git process running AND old enough that any live operation "
        "would have finished. Refuses on a maybe.",
    )
    parser.add_argument(
        "--why-locked",
        action="store_true",
        help="Explain the current lock situation and exit, changing nothing.",
    )
    parser.add_argument("--role", choices=["cop", "thief", "both"], default="both")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen.")
    parser.add_argument(
        "--skip-league",
        action="store_true",
        help="Skip only the league benchmark gate (~2 min, 192 sub-games). "
        "Every other gate - lint, file size, secret scan, unit tests and "
        "coverage, split-repository check - still runs. Must be passed "
        "explicitly each time; there is no default-on equivalent.",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Skip the league benchmark AND the unit/integration test gate "
        "(the slow self-play batches live there), leaving lint, file size, "
        "the secret scan, and the split-repository check. For fast "
        "iteration only; must be passed explicitly each time.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Return 0 when everything succeeded, 1 on the first failure."""
    args = _parse_args(argv)

    if args.why_locked:
        print(diagnose(ROOT))
        return 0
    if args.unlock:
        removed, explanation = release(ROOT)
        print(f"  {explanation}", flush=True)
        if not removed and "No .git" not in explanation:
            return 1
    steps = build_steps(args.message, args.role, args.dry_run, args.skip_league, args.simple)
    total = len(steps)
    stage, *rest = steps
    gates, publish = rest[:-1], rest[-1]

    try:
        run_step(stage, 1, total, ROOT, args.dry_run)
        for offset, gate in enumerate(gates, start=2):
            run_step(gate, offset, total, ROOT, args.dry_run)
        _commit(args.message, args.dry_run)
        run_step(publish, total, total, ROOT, dry_run=False)
    except StepError as failure:
        print(failure, file=sys.stderr)
        return 1
    except GitCommandError as error:
        print(f"\nFAILED during commit:\n{error}", file=sys.stderr)
        return 1

    banner("Shipped" if not args.dry_run else "Dry run complete - nothing was changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
