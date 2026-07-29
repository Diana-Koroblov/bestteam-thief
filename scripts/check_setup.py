"""Verify the external-service setup (TODO 0.2). See docs/SETUP.md.

    uv run python scripts/check_setup.py

Exits 1 if any check FAILs. WARNs are reported but do not fail: a machine that
only ever runs the template provider legitimately has no Ollama.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.shared.env import load_env  # noqa: E402
from core.shared.setup_checks import FAIL, OK, WARN, run_all  # noqa: E402

_MARK = {OK: "[ OK ]", WARN: "[WARN]", FAIL: "[FAIL]"}


def main() -> int:
    """Print the setup report. Returns 1 if anything failed."""
    load_env(ROOT)
    results = run_all(ROOT)
    width = max(len(result.name) for result in results)

    print("\nExternal setup check (docs/SETUP.md)\n" + "-" * 60)
    for result in results:
        print(f"{_MARK[result.status]}  {result.name:<{width}}  {result.detail}")
        if result.fix:
            print(f"{'':8}{'':<{width}}  -> {result.fix}")

    failed = [r for r in results if r.status == FAIL]
    warned = [r for r in results if r.status == WARN]
    print("-" * 60)
    print(f"{len(results) - len(failed) - len(warned)} OK, {len(warned)} warning(s), "
          f"{len(failed)} failure(s)")

    if failed:
        print("\nFix the failures above, then re-run. See docs/SETUP.md.")
        return 1
    print("\nSetup looks good.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
