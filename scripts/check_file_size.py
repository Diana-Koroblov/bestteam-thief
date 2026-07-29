"""CLI guard for the 150-line rule (excellence guide §3.2).

Run before every commit::

    uv run python scripts/check_file_size.py

Exits 1 and lists offenders, worst first, when any file breaches the limit.
A file over the limit is **split**, never compressed — see docs/TODO.md for the
approved split strategies.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running as a plain script from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.shared.constants import MAX_FILE_LOC  # noqa: E402
from core.shared.loc_counter import find_oversized  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Fail if any source file exceeds the LOC limit.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Project root to scan (default: the repository root).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=MAX_FILE_LOC,
        help=f"Maximum code lines per file (default: {MAX_FILE_LOC}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Return 0 when every file is within the limit, 1 otherwise."""
    args = _parse_args(argv)
    offenders = find_oversized(args.root, limit=args.limit)

    if not offenders:
        print(f"File size OK - no file exceeds {args.limit} code lines.")
        return 0

    print(f"FAIL - {len(offenders)} file(s) exceed {args.limit} code lines:\n")
    for report in offenders:
        relative = report.path.relative_to(args.root)
        over = report.code_lines - args.limit
        print(f"  {report.code_lines:>4} lines (+{over:<3})  {relative}")
    print("\nSplit these files. Do not compress them to fit.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
