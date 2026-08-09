"""Filing our own report the moment a series ends (TODO 7.3.4, 9.3.3, M#35).

`[email] send_on_series_end = true` has been in both `game.toml` files since
Phase 1 and described a hook nothing called: `GmailSender` was built, tested and
wired to the Gatekeeper, and its only caller was the setup self-test. The report
therefore went out when a human remembered to send it — against the harshest
rule in the book, which voids the match and scores **0 for both teams** when
either side fails to report.

Three decisions shape this module:

**It sends only a complete series.** A 3-3 split is two processes in sequence,
and the first to finish holds a report covering three sub-games. Mailing that
would put two messages with the same `game_id` in the grader's inbox, the
earlier one disagreeing with the later — which is the *contradictory pair* M#35
voids matches over, produced by the code meant to satisfy it. So the decision is
made from the merged file on disk: whoever files the sixth row sends.

**A failure here is loud and never fatal.** The match is over and its artefacts
are on disk. Raising would lose nothing but would bury the one line the human
still has to act on, so every failure returns the same thing: what went wrong,
and the exact command that files the match by hand.

**It reports rather than prints.** The caller owns the terminal. This returns
the text, which is also what lets every branch be tested without a mailbox.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.report.merge import load_rows

__all__ = ["send_series_report"]

# Printed after every outcome except a successful send, because every one of
# them leaves a report unsent — and an unsent report is 0 for both teams.
MANUAL = "  file it by hand:  uv run python scripts/send_report.py --role {role} {path}"

# Left-hand column, matching the scoreboard printed immediately above it.
LABEL = "report          : "


def send_series_report(
    make_mailer: Callable[[], Any], path: Path, expected: int, role: str = "cop"
) -> str:
    """Send our report if the series is complete, and describe what happened.

    Args:
        make_mailer: Builds the `GmailSender`. A callable rather than a sender,
            so the OAuth client is never constructed for a series that is not
            going to be reported — and so `core.runtime` needs no import of the
            SDK that owns it.
        path: `result_<game_id>.json`, already merged across both of our role
            processes by `MatchFiling.result`.
        expected: `[number of sub-games]` — 6 under Appendix F Table 18. The
            report goes out when the file holds that many rows and not before.
        role: Ours, for the hand-filing command in the message.

    Returns:
        Text for the caller to print. Never raises: see the module docstring.
    """
    played = len(load_rows(path))
    if played < expected:
        return (
            f"{LABEL}held back - {path.name} covers {played} of {expected} sub-games\n"
            "  the other role process files the rest and sends then (M#35)\n"
            + MANUAL.format(role=role, path=path)
        )
    try:
        mailer = make_mailer()
        if not mailer.enabled or not mailer.on_series_end:
            return _unsent("[email] enabled/send_on_series_end is off in game.toml", role, path)
        mailer.send_result(path)
    except Exception as error:  # the match is over; nothing here may crash it
        return _unsent(f"{type(error).__name__}: {error}", role, path)
    return (
        f"{LABEL}sent to {mailer.recipient}  ({path.name}, {played} sub-games)\n"
        "  now confirm THEY sent theirs - a missing report is 0 for BOTH (M#35)"
    )


def _unsent(reason: str, role: str, path: Path) -> str:
    """Say plainly that no report left this machine, and how to fix it.

    Deliberately not softened. Every other line the match prints is a result;
    this one is a task, and the cost of it reading like a warning is a series
    that was won on the board and scored zero on the paperwork.
    """
    return (
        f"{LABEL}NOT SENT - {reason}\n"
        + MANUAL.format(role=role, path=path)
    )
