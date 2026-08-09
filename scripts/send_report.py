"""File our league report by hand (TODO 9.3.3, M#35).

    uv run python scripts/send_report.py --role cop results/result_<game_id>.json
    uv run python scripts/send_report.py --role cop results/          # newest result
    uv run python scripts/send_report.py --role cop results/ --dry-run

A finished series mails its own report — `core/runtime/reporting.py` does it the
moment the sixth sub-game is filed. This is the path for when that did not
happen, and there are three real ways it does not:

* **The series never completed.** The opponent dropped after sub-game four, so
  no process ever filed a sixth row. The match still has to be reported: a
  series that ended badly is not a series that goes unreported, and M#35 costs
  *both* teams 0 when either side stays silent.
* **The send failed.** No token, a revoked grant, a network that was down for
  the eleven seconds it mattered. The match printed `NOT SENT` and this command.
* **The result changed.** The two teams reconciled their scoreboards afterwards
  and the file was corrected (9.3.2).

It reads the same `[email]` block as the match does, so the sender, the
recipient and the Gatekeeper are the ones a real report goes through — this is
not a second, simpler send path that could behave differently on the day.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.infra.gmail_sender import GmailError, GmailSender, build_transport  # noqa: E402
from core.report.artefacts import ArtefactError  # noqa: E402
from core.report.merge import load_rows  # noqa: E402
from core.shared.config_manager import load_config  # noqa: E402
from core.shared.env import load_env  # noqa: E402
from core.shared.gatekeeper import Gatekeeper  # noqa: E402
from core.shared.rate_limits import load_rate_limits  # noqa: E402

# The command line says `cop`; the directory is `police` (Appendix B.4).
CONFIG_DIRS = {"police": "police", "cop": "police", "thief": "thief"}


def resolve(target: Path) -> Path:
    """Return the result file to send, accepting a directory as a shorthand.

    A directory resolves to its **newest** `result_*.json`. Convenient, and
    narrow on purpose: it will not guess between two matches' reports, because
    mailing the wrong match's result is indistinguishable to the grader from
    reporting a game that never happened.
    """
    if target.is_file():
        return target
    if not target.is_dir():
        raise GmailError(f"no such file or directory: {target}")
    found = sorted(target.glob("result_*.json"), key=lambda path: path.stat().st_mtime)
    if not found:
        raise GmailError(
            f"{target} holds no result_*.json. A match played without --out files "
            "nothing, which is correct for a rehearsal and fatal for a counted match."
        )
    return found[-1]


def describe(path: Path) -> str:
    """Return one line saying what is about to be mailed, read from the file.

    Read from the artefact rather than taken on trust: the whole point of the
    manual path is that it is used when something has already gone differently
    from the plan, and a human about to mail the lecturer should see how many
    sub-games are actually in the file.
    """
    rows = load_rows(path)
    ours = sum(int(row.get("our_points", 0)) for row in rows)
    theirs = sum(int(row.get("their_points", 0)) for row in rows)
    return f"{path.name}: {len(rows)} sub-game(s), us {ours} - them {theirs}"


def send(path: Path, role: str, dry_run: bool) -> int:
    """Mail *path* through the configured sender. Returns a process exit code."""
    role_dir = ROOT / "config" / CONFIG_DIRS[role]
    if not (role_dir / "game.json").is_file():
        raise GmailError(
            f"no configuration for role {role!r} ({role_dir} has no game.json). Each "
            "published repository ships one role; use the other repository."
        )
    config = load_config(role_dir)
    mailer = GmailSender.from_config(
        config,
        gatekeeper=Gatekeeper(limits=load_rate_limits(role_dir)),
        # Built here rather than lazily: this command exists to send, so a
        # missing token must fail now and name the SETUP step, not after the
        # user has been told the report went out.
        transport=(lambda body: None) if dry_run else build_transport(),
    )
    print(f"[ .. ]  {describe(path)}")
    print(f"        from {mailer.sender} to {mailer.recipient}")
    if dry_run:
        print("[ OK ]  dry run - nothing was sent")
        return 0
    if not mailer.enabled:
        print("[FAIL]  [email] enabled = false in game.toml; nothing was sent", file=sys.stderr)
        return 1
    mailer.send_result(path)
    print("[ OK ]  sent. Now confirm THEY sent theirs - a missing report is 0 for BOTH (M#35)")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and send. Returns a process exit code."""
    parser = argparse.ArgumentParser(description="Send a filed league report by hand.")
    parser.add_argument("target", type=Path, help="result_<game_id>.json, or a directory.")
    parser.add_argument(
        "--role", required=True, choices=sorted(CONFIG_DIRS), help="Whose [email] block to use."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be sent and stop."
    )
    args = parser.parse_args(argv)

    load_env(ROOT)
    try:
        return send(resolve(args.target), args.role, args.dry_run)
    except (GmailError, ArtefactError) as error:
        print(f"[FAIL]  {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
