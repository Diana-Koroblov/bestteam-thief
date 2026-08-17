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

from pathlib import Path
from typing import Any

from core.compat import reporting
from core.compat.filing import file_declaration, file_sub_game
from core.compat.league_report import game_id
from core.compat.league_row import row_from_session
from core.compat.match_log import sealed_commit
from core.report.artefacts import ArtefactError, utc_now

__all__ = ["close_series", "close_sub_game"]


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

    Their commit comes from what they **sealed**, not from what they typed —
    see :func:`_their_commit` for the precedence and why a disagreement between
    their two channels is reported rather than resolved silently.
    """
    group = their_group or "opponent"
    their_commit, finding = _their_commit(args, session, their_identity)
    rows.append(row_from_session(
        sdk=sdk, session=session, number=number, raw_result=result, verdict=verdict,
        started=started, ended=ended, their_group=group,
        their_commit=their_commit,
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
    return finding


def _their_commit(args: Any, session: Any, their_identity: dict[str, Any]) -> tuple[str, str]:
    """Return the opponent's head to file, and any note about how they declared it.

    Precedence is strongest-source-first: the operator's ``--their-commit``
    override, then the head they **sealed** into their step-0 record, then the
    plaintext handshake identity block. Settled with imreeyal on 17/08 — a
    sealed commit is inside the commitment and unrevisable, a handshake block
    is neither.

    **A peer's two channels disagreeing is a finding, not a tie to break
    quietly.** A conformant peer sources its plaintext declaration *from* the
    sealed record, so the two agree by construction and a divergence means one
    of them is wrong. We file the sealed one either way and say so, because a
    silent pick would destroy the only evidence that the disagreement existed.
    """
    override = str(getattr(args, "their_commit", "") or "")
    if override:
        return override, ""
    sealed = sealed_commit(getattr(session, "their_records", []) or [])
    declared = str(their_identity.get("github_commit", "") or "")
    if sealed and declared and sealed != declared:
        return sealed, (
            f"their two channels disagree: sealed step-0 {sealed[:12]}... but handshake "
            f"declared {declared[:12]}... - filing the sealed one"
        )
    return sealed or declared, ""


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
