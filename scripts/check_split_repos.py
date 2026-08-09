"""Run CI's role-sensitive steps as each published repository would see them.

    uv run python scripts/check_split_repos.py

Why this gate exists. The working tree holds **both** roles, so `uv run pytest`
here can never fail for a reason that only exists after the split. Each
published repository ships one role and forbids the other (ADR-001, M#2), so a
test — or any module — that names `config/police` or imports `thief` passes
locally and takes the whole suite down in CI on at least one repository.

That is not hypothetical: it is exactly how CI run #8 broke both repositories at
import time while every local gate was green.

So we build a throwaway copy of each role's published file set and run CI's
checks inside it, before anything is pushed. It is the same code path CI will
run, which is the only kind of check worth having.

**Lint runs here too, and did not until it had to.** This gate was written for
the import failure above and covered `pytest` alone — which left the CI job's
*first* step, `ruff check .`, protected by nothing. Ruff infers first-party
packages from what is on disk, so in `bestteam-cop` the absent `thief` package
made every `from thief... import` third-party and nine test files failed I001 in
one repository while being clean in the other and invisible in the working tree.
`known-first-party` in `pyproject.toml` is the fix; running the linter in the
split tree is what would have caught it. A gate that covers one of CI's two
role-sensitive steps is a gate that says "OK" to a red build.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.shared.publish_spec import ROLES, RoleSpec  # noqa: E402

__all__ = ["main", "build_role_tree", "run_suite"]

# The two CI steps whose answer depends on which role is present, in CI's own
# order. The file-size and secret gates are deliberately absent: one is a
# property of a file's text and the other needs a git repository, and neither
# can change because a package is missing.
#
# --no-cov because coverage is already measured once, in the working tree, where
# both role packages exist. Measuring it again against a half tree would report
# a false shortfall and fail the gate for the wrong reason.
CI_STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ruff", ("-m", "ruff", "check", ".")),
    ("pytest", ("-m", "pytest", "-q", "--no-cov", "-p", "no:cacheprovider")),
)


def build_role_tree(spec: RoleSpec, target: Path) -> None:
    """Copy *spec*'s published file set into *target*.

    Mirrors ``scripts/publish.py`` deliberately: if the two ever disagree, this
    gate stops testing what is actually shipped.
    """
    for relative in spec.all_paths():
        source = ROOT / relative
        if not source.exists():
            continue
        destination = target / relative
        if source.is_dir():
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns(*spec.ignore))
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    for relative in spec.forbidden:
        shutil.rmtree(target / relative, ignore_errors=True)


def run_suite(spec: RoleSpec, target: Path) -> bool:
    """Return True when every CI step passes inside *target*.

    Uses the interpreter already running this script rather than a fresh ``uv
    run``, so the throwaway tree needs no environment of its own.

    **Every step runs, even after one fails.** A lint error and an import error
    have different causes and a human fixing both wants to see both — stopping
    at the first would turn one push into two.
    """
    print(f"\n  {spec.repo_dir}: CI steps with only {', '.join(spec.role_paths)}")
    passed = True
    for name, arguments in CI_STEPS:
        print(f"    -- {name}")
        completed = subprocess.run(  # noqa: S603 - fixed argument list, no shell
            [sys.executable, *arguments],
            cwd=target,
            check=False,
        )
        passed = passed and completed.returncode == 0
    return passed


def main() -> int:
    """Return 0 when every published repository would pass, 1 otherwise.

    Only meaningful in the working tree. Inside a published repository the other
    role is absent by design, so there is nothing to simulate and the gate
    reports success rather than a confusing failure.
    """
    buildable = [spec for spec in ROLES if all((ROOT / p).exists() for p in spec.role_paths)]
    if len(buildable) < len(ROLES):
        print("Only one role is present - this is a published repository, nothing to split.")
        return 0

    failed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="p2p-split-") as workspace:
        for spec in buildable:
            target = Path(workspace) / spec.repo_dir
            build_role_tree(spec, target)
            if not run_suite(spec, target):
                failed.append(spec.repo_dir)

    if failed:
        print(
            "\nSplit-repository check FAILED for: "
            + ", ".join(failed)
            + "\nThe working tree has both roles, so this cannot reproduce locally without"
            "\nthe split. Look for a literal 'config/police', 'config/thief', or an import"
            "\nof the other role package. See tests/paths.py for the supported pattern."
            "\nIf it is ruff and only ruff, suspect a rule that reads the filesystem:"
            "\n'[tool.ruff.lint.isort] known-first-party' exists because I001 classified"
            "\nthe absent role package as third-party.",
            file=sys.stderr,
        )
        return 1

    print("\nSplit-repository check OK - both published repositories pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
