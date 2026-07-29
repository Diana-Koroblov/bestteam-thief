"""Publish the working tree to the two role repositories (ADR-001).

The rulebook requires two separate GitHub repositories (M#49) and forbids any
shared runtime state between the Cop and the Thief (M#2). We develop in one tree
and publish role-specific subsets, so neither repository ever contains the other
role's brain or configuration.

    core/ + police/ + config/police/   ->  bestteam-cop
    core/ + thief/  + config/thief/    ->  bestteam-thief

Usage::

    uv run python scripts/publish.py --message "feat: base logic"
    uv run python scripts/publish.py --role cop --message "..." --dry-run
    uv run python scripts/publish.py --scan-only

Each target must already be a clone of the corresponding GitHub repository,
sitting beside this working tree. The secret scan runs before anything is
staged; a hit aborts the publish for every role.

The push is attempted on every run, including when there is nothing new to
commit, so that a run which committed but failed to push can simply be repeated.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.shared.git_ops import GitCommandError, has_pending_changes, run_git  # noqa: E402
from core.shared.publish_spec import ROLES, RoleSpec  # noqa: E402
from core.shared.secret_scanner import scan_tracked  # noqa: E402

__all__ = ["main"]


def _scan_secrets() -> None:
    """Abort the publish if anything key-shaped is tracked. (M#39, M#40)"""
    findings = scan_tracked(ROOT)
    if not findings:
        print("Secret scan OK - none found in tracked files.")
        return
    print(f"FAIL - {len(findings)} suspected secret(s):")
    for finding in findings:
        print(finding)
    raise SystemExit("Publish aborted: secret found. Nothing was pushed.")


def _sync_tree(spec: RoleSpec, target: Path, dry_run: bool) -> None:
    """Mirror this role's file set into *target*, removing anything stale."""
    for relative in spec.all_paths():
        source = ROOT / relative
        if not source.exists():
            continue
        print(f"    {relative}")
        if dry_run:
            continue
        destination = target / relative
        if source.is_dir():
            shutil.rmtree(destination, ignore_errors=True)
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns(*spec.ignore))
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    readme = ROOT / spec.readme
    if readme.exists():
        print(f"    {spec.readme} -> README.md")
        if not dry_run:
            shutil.copy2(readme, target / "README.md")

    for relative in spec.forbidden:
        stale = target / relative
        if stale.exists():
            print(f"    removing stale {relative}")
            if not dry_run:
                shutil.rmtree(stale, ignore_errors=True)


def _publish_role(spec: RoleSpec, target: Path, message: str, dry_run: bool) -> None:
    """Sync, commit and push a single role repository."""
    print(f"\n== {spec.name} -> {target}")
    if not (target / ".git").is_dir():
        raise SystemExit(f"{target} is not a git clone. Clone the repository there first.")

    _sync_tree(spec, target, dry_run)
    run_git(["add", "-A"], target, dry_run)

    if dry_run or has_pending_changes(target):
        run_git(["commit", "-m", message], target, dry_run)
    else:
        print("    nothing new to commit")

    # Always attempt the push, even with nothing new to commit: an earlier run
    # may have committed and then failed to push (expired token, no network).
    print(f"    pushing to {spec.repo_dir}")
    run_git(["push", "origin", "HEAD"], target, dry_run)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Publish to the two role repositories.")
    parser.add_argument("--role", choices=["cop", "thief", "both"], default="both")
    parser.add_argument("--message", "-m", help="Commit message.")
    parser.add_argument("--parent", type=Path, default=ROOT.parent, help="Where the clones live.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen.")
    parser.add_argument("--scan-only", action="store_true", help="Run the secret scan and exit.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Publish the selected roles. Returns 0 on success, 1 on a git failure."""
    args = _parse_args(argv)
    _scan_secrets()
    if args.scan_only:
        return 0
    if not args.message:
        raise SystemExit("--message is required (except with --scan-only).")

    selected = [spec for spec in ROLES if args.role in (spec.name, "both")]
    for spec in selected:
        try:
            _publish_role(spec, args.parent / spec.repo_dir, args.message, args.dry_run)
        except GitCommandError as error:
            print(f"\nFAILED: {error}")
            print("\nFix the above, then re-run this command. Work already committed is kept.")
            return 1

    print("\nDry run complete - nothing was changed." if args.dry_run else "\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
