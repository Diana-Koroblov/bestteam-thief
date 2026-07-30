"""Run the test suite as each published repository would see it.

    uv run python scripts/check_split_repos.py

Why this gate exists. The working tree holds **both** roles, so `uv run pytest`
here can never fail for a reason that only exists after the split. Each
published repository ships one role and forbids the other (ADR-001, M#2), so a
test — or any module — that names `config/police` or imports `thief` passes
locally and takes the whole suite down in CI on at least one repository.

That is not hypothetical: it is exactly how CI run #8 broke both repositories at
import time while every local gate was green.

So we build a throwaway copy of each role's published file set and run the suite
inside it, before anything is pushed. It is the same code path CI will run,
which is the only kind of check worth having.
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

# --no-cov because coverage is already measured once, in the working tree, where
# both role packages exist. Measuring it again against a half tree would report
# a false shortfall and fail the gate for the wrong reason.
PYTEST_ARGS = ("-m", "pytest", "-q", "--no-cov", "-p", "no:cacheprovider")


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
    """Return True when the suite passes inside *target*.

    Uses the interpreter already running this script rather than a fresh ``uv
    run``, so the throwaway tree needs no environment of its own.
    """
    print(f"\n  {spec.repo_dir}: running the suite with only {', '.join(spec.role_paths)}")
    completed = subprocess.run(  # noqa: S603 - fixed argument list, no shell
        [sys.executable, *PYTEST_ARGS],
        cwd=target,
        check=False,
    )
    return completed.returncode == 0


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
            "\nof the other role package. See tests/paths.py for the supported pattern.",
            file=sys.stderr,
        )
        return 1

    print("\nSplit-repository check OK - both published repositories pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
