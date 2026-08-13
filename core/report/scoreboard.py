"""The series, printed for the two humans who have to agree on it (TODO 9.3.2).

Split from `cli_play.py` on a real seam. That module drives a match; this one
renders the result, and the two change for different reasons — a new transport
does not alter a scoreboard, and a clearer column does not alter the protocol.

**Written to be read aloud.** Before either side reports anything, both teams
have to agree the figures (9.3.2), and that conversation happens over a chat
window with two terminals open. So every sub-game prints the verdict, the reason
it ended, the step count and the audit word on one line — the four things an
opponent's copy either matches or does not.
"""

from __future__ import annotations

from typing import Any

__all__ = ["print_series"]


def print_series(report: Any, table: Any, filing: Any = None) -> None:
    """Print every sub-game, then what the meeting is worth.

    Args:
        report: The finished `SeriesReport`.
        table: The negotiated `ScoreTable` the rows are priced with.
        filing: The `MatchFiling`, or None when the series was played without
            writing artefacts — a warm-up, which must not leave files that
            look like a league match.
    """
    for row in report.rows(table):
        print(
            f"  sub-game {row['sub_game']}  {row['role']:<5}  {row['verdict']:<16}"
            f"  {row['our_points']:>3} - {row['their_points']:<3}"
            f"  {row['steps']:>2} steps  audit {row['opponent_log_audit']}"
        )
        print(f"      {row['reason']}")

    summary = report.summary()
    print(f"\ntotals          : us {summary['our_points']} - them {summary['their_points']}")
    print(
        f"league points   : us {summary['our_league_points']} - "
        f"them {summary['their_league_points']}  ({summary['verdict']})"
    )
    # Reported, never acted on. A failed re-hash is a total technical loss for
    # the forger, but that verdict belongs to a league holding both reports —
    # not to the accusing peer scoring its own match (Ch. 5.4, M#19).
    if report.forged:
        print(f"AUDIT FAILED on sub-game(s) {report.forged} - file it, do not score it (M#19)")
    if filing is not None:
        print(f"\nartefacts       : {len(filing.written)} files in {filing.directory}")
        print("send yours, and confirm they sent theirs - a missing report is 0 for BOTH (M#35)")
