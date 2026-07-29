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
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.shared.git_ops import GitCommandError, has_pending_changes, run_git  # noqa: E402
from core.shared.pipeline import GATES, Step, StepError, banner, run_step  # noqa: E402

__all__ = ["main", "build_steps"]


def build_steps(message: str, role: str, dry_run: bool) -> tuple[Step, ...]:
    """Return the full pipeline: stage, gates, then publish."""
    stage = Step("Stage all changes", ("git", "add", "-A"))
    publish_command = ["uv", "run", "python", "scripts/publish.py", "--role", role, "-m", message]
    if dry_run:
        publish_command.append("--dry-run")
    publish = Step("Publish to both repositories", tuple(publish_command))
    return (stage, *GATES, publish)


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
    parser.add_argument("--role", choices=["cop", "thief", "both"], default="both")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Return 0 when everything succeeded, 1 on the first failure."""
    args = _parse_args(argv)
    steps = build_steps(args.message, args.role, args.dry_run)
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
