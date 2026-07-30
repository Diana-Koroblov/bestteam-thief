"""CLI secret scan (Appendix E rules #39, #40).

    uv run python scripts/scan_secrets.py             # staged changes (pre-commit)
    uv run python scripts/scan_secrets.py --tracked   # every tracked file (CI)
    uv run python scripts/scan_secrets.py --history   # every line ever committed
    uv run python scripts/scan_secrets.py --history --root ../bestteam-cop

Exits 1 on any hit. A secret committed once is permanently exposed — remove it
and use an environment variable instead. Never "commit now, fix later".

``--history`` exists because ``--tracked`` only sees the current checkout: a key
that was committed and later deleted passes the tracked scan while staying
readable forever in the log. Quality gate 0.QG.3 requires the history check on
**both** published repositories, not just the working tree.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.shared.secret_scanner import scan_history, scan_staged, scan_tracked  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Return 0 when no secret is found, 1 otherwise."""
    parser = argparse.ArgumentParser(description="Block credentials from being committed.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--tracked", action="store_true", help="Scan all tracked files, not staged.")
    mode.add_argument("--history", action="store_true", help="Scan every line ever committed.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root.")
    args = parser.parse_args(argv)

    if args.history:
        subject, findings = "the full git history", scan_history(args.root)
    elif args.tracked:
        subject, findings = "tracked files", scan_tracked(args.root)
    else:
        subject, findings = "staged changes", scan_staged(args.root)

    if not findings:
        print(f"Secret scan OK - none found in {subject} of {args.root}.")
        return 0

    print(f"FAIL - {len(findings)} suspected secret(s) in {subject}:\n")
    for finding in findings:
        print(finding)
    if args.history:
        print("\nA secret in the history is already public. Rotate the key, then rewrite")
        print("the history. Editing the file is not enough. (M#39, M#40)")
    else:
        print("\nRemove it and use an environment variable instead.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
