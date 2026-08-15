"""Pull both role repositories back into the working tree — the inverse of publish.

    uv run python scripts/sync_from_repos.py
    uv run python scripts/sync_from_repos.py --dry-run

``publish.py`` copies this tree *out* to ``bestteam-cop`` and ``bestteam-thief``.
That was correct for one developer and wrong for two: work pushed to GitHub by
one person had no way back into the other's tree, and a stale ``ship.py`` would
mirror over it. This closes the loop.

    p2p-chase  --publish.py-->  bestteam-cop    <--> GitHub
         ^                      bestteam-thief  <--> GitHub
         |                             |
         +------ sync_from_repos.py ---+

**It reads the same ``publish_spec`` that publish.py writes**, so the two can
never disagree about which files belong where. Shared paths come from the cop
clone; each role's own files come from its own repository.

Three refusals, each protecting against a way this could silently destroy work:

* **Uncommitted changes here.** Copying over them loses them with no undo.
* **Divergent shared code.** ``core/`` exists in *both* repositories. If they
  differ, one of them is stale and picking either would discard real work — so
  we stop and name the mismatch rather than guessing.
* **A missing clone.** Better to say which directory is absent than to
  half-sync and leave a tree that imports but is subtly wrong.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.shared.publish_spec import ROLES, SHARED_PATHS  # noqa: E402

__all__ = ["main", "shared_tree_hashes", "sync"]

# Compared between the two clones before anything is copied. These are the
# directories both repositories carry, so they are the only place a divergence
# can hide.
GUARDED = ("core", "docs", "tests", "scripts")


def _git(args: list[str], cwd: Path) -> str:
    """Run git and return stdout, or raise with git's own message."""
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=120, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd.name}:\n{result.stderr.strip()}")
    return result.stdout.strip()


def shared_tree_hashes(repo: Path) -> dict[str, str]:
    """Return git's content hash for each guarded directory.

    Git hashes directory *contents*, so equal hashes mean byte-identical trees.
    Far more reliable than comparing timestamps, which differ merely because two
    clones were checked out at different moments.
    """
    output = _git(["rev-parse", *[f"HEAD:{path}" for path in GUARDED]], repo)
    return dict(zip(GUARDED, output.splitlines(), strict=True))


def _copy(source: Path, destination: Path, ignore: tuple[str, ...], dry_run: bool) -> int:
    """Mirror one path, returning how many files were copied."""
    if not source.exists():
        return 0
    if dry_run:
        return sum(1 for item in source.rglob("*") if item.is_file()) if source.is_dir() else 1

    if source.is_dir():
        shutil.rmtree(destination, ignore_errors=True)
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns(*ignore))
        return sum(1 for item in destination.rglob("*") if item.is_file())
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return 1


def sync(pull: bool, dry_run: bool) -> int:
    """Pull both clones, verify they agree, then copy into this tree."""
    clones = {role.name: ROOT.parent / role.repo_dir for role in ROLES}
    for path in clones.values():
        if not (path / ".git").is_dir():
            print(f"  MISSING: {path} is not a clone. Nothing copied.")
            return 1

    if _git(["status", "--porcelain"], ROOT):
        print("  REFUSED: this tree has uncommitted changes.\n"
              "  Commit or stash them first - syncing would overwrite them with no undo.")
        return 1

    if pull:
        for path in clones.values():
            print(f"  pulling {path.name}...", flush=True)
            print(f"    {_git(['pull', '--ff-only'], path) or 'already current'}")

    hashes = {name: shared_tree_hashes(path) for name, path in clones.items()}
    cop, thief = hashes["cop"], hashes["thief"]
    drifted = [path for path in GUARDED if cop[path] != thief[path]]
    if drifted:
        print(f"\n  REFUSED: shared paths differ between the two repositories: {drifted}\n"
              "  One clone is stale. Push from whichever is newer, pull both, and retry.\n"
              "  Copying either version would silently discard the other's work.")
        return 1
    print(f"\n  shared trees agree across both repositories ({', '.join(GUARDED)})")

    copied = 0
    for role in ROLES:
        source_repo = clones[role.name]
        paths = SHARED_PATHS if role.name == "cop" else ()
        for relative in (*paths, *role.role_paths):
            count = _copy(source_repo / relative, ROOT / relative, role.ignore, dry_run)
            if count:
                copied += count
                print(f"    {relative:<28} {count:>4} files  <- {source_repo.name}")

    verb = "would copy" if dry_run else "copied"
    print(f"\n  {verb} {copied} files. Run `uv run pytest` before shipping.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the sync."""
    parser = argparse.ArgumentParser(description="Pull both role repos into this tree.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen.")
    parser.add_argument("--no-pull", action="store_true", help="Skip git pull; copy what is there.")
    args = parser.parse_args(argv)

    print("=" * 68 + "\n Sync from the role repositories\n" + "=" * 68)
    try:
        return sync(pull=not args.no_pull, dry_run=args.dry_run)
    except RuntimeError as failure:
        print(f"\n  {failure}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
