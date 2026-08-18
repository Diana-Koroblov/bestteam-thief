"""What a finished sub-game and a finished series leave behind.

Split from `core/compat/filing.py` under the 150-line ceiling (ADR-005), and the
seam is the same one `turns.py`/`session.py` and `league_row.py`/
`league_report.py` already draw: *filing* knows how to build and write one
artefact, this knows **which** artefacts a finished thing owes and in what
order. The CLI calls only this, and prints the lines it hands back — it owns
what a human sees, not what a sub-game is worth (M#3).

Nothing here raises. The sub-games are already played and the result is the
artefact that has to survive; losing a log to a full disk must not also cost the
report that names it, so every failure comes back as a line to print.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from core.compat import reporting
from core.compat.filing import file_declaration, file_sub_game
from core.compat.league_report import game_id
from core.compat.league_row import row_from_session
from core.report.artefacts import ArtefactError, utc_now

__all__ = ["close_series", "close_sub_game", "linger_for_audit"]


async def linger_for_audit(args: Any) -> None:
    """Stay up after our own plan is spent, so a late audit push still lands.

    🐛 The reference path's door used to close the instant `_series` returned —
    no cushion, unlike the native path's own `--linger` (`cli_play.py`). Our
    LAST sub-game's audit push races their own settlement on their side; if
    their reveal (or a redial of ours) arrives a beat late, it hits a door we
    already tore down — a 502/406 that reads as their bug and is ours
    (imreeyal correspondence, 17/08, point 3).
    """
    linger = float(getattr(args, "linger", 20.0))
    if linger > 0:
        print(f"\nstaying up {linger:.0f}s so they can finish auditing our log (M#36) ...")
        await asyncio.sleep(linger)


def close_sub_game(
    *,
    sdk: Any,
    args: Any,
    session: Any,
    number: int,
    result: str,
    verdict: dict[str, Any],
    started: str,
    ended: str,
    their_group: str,
    their_identity: dict[str, Any],
    our_identity: dict[str, Any],
    rows: list[dict[str, Any]],
    written: list[Path],
) -> str:
    """Record what one finished sub-game leaves behind; return any note to print.

    *rows* and *written* are appended to, matching :func:`close_series`: the
    caller keeps one list of each for the whole series and this decides what
    goes in them.

    Both commits come from the blocks the two peers actually exchanged, so a
    filed row can never name code a declaration did not. ``--their-commit``
    still wins when given: it is the operator correcting a peer whose own block
    was wrong or absent.
    """
    group = their_group or "opponent"
    rows.append(row_from_session(
        sdk=sdk, session=session, number=number, raw_result=result, verdict=verdict,
        started=started, ended=ended, their_group=group,
        their_commit=str(
            getattr(args, "their_commit", "") or their_identity.get("github_commit", "") or ""
        ),
        our_commit=str(our_identity.get("github_commit", "") or ""),
    ))
    try:
        written.extend(file_sub_game(
            out=Path(args.out), game_identifier=game_id(sdk.team_name, group),
            session=session, sdk=sdk, number=number, outcome=result,
            our_group=sdk.team_name, their_group=group,
        ))
    except (OSError, ArtefactError) as error:
        return f"sub-game {number} artefacts NOT filed: {type(error).__name__}: {error}"
    return ""


def close_series(
    *,
    sdk: Any,
    args: Any,
    rows: list[dict[str, Any]],
    written: list[Path],
    our_identity: dict[str, Any],
    their_identity: dict[str, Any],
    their_group: str,
    opened: str,
) -> list[str]:
    """File the declaration, send the report, and return the lines to print."""
    lines: list[str] = []
    if their_group:
        try:
            written.append(file_declaration(
                out=Path(args.out),
                game_identifier=game_id(sdk.team_name, their_group),
                sdk=sdk, our_identity=our_identity, their_identity=their_identity,
                their_group=their_group, their_url=str(getattr(args, "opponent", "") or ""),
                started_utc=opened, ended_utc=utc_now(),
            ))
        except (OSError, ArtefactError) as error:
            lines.append(f"declaration     : NOT FILED - {type(error).__name__}: {error}")
    lines.append(f"artefacts       : {len(written)} file(s) in {args.out}")
    lines.append(
        reporting.send_league_report(sdk, args, rows, our_identity, their_identity, their_group)
    )
    return lines
