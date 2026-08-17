"""Turning one finished sub-game into a league-schema row (core/compat/league_report.py's
row builder, split out because it needs the scoring/step-zero seam and that
file otherwise stays a leaf `core/compat/session.py` can import without a
cycle — the same reason `core/compat/turns.py` types its session `Any`).
"""

from __future__ import annotations

from typing import Any

from core.compat.league_report import build_sub_game_row, game_id
from core.compat.wire import wire_role
from core.domain.rules import Outcome, Verdict
from core.domain.scoring import score
from core.protocol.schemas import Role

__all__ = ["row_from_session"]


def row_from_session(
    *,
    sdk: Any,
    session: Any,
    number: int,
    raw_result: str,
    verdict: dict[str, Any],
    started: str,
    ended: str,
    their_group: str,
    their_commit: str,
    our_commit: str,
) -> dict[str, Any]:
    """Return one finished sub-game's row, scored and dated, from a live session.

    Args:
        our_commit: The head we **declared**, passed in rather than read here.

    🐛 **This file used to call `commit_hash(Path.cwd())`.** The declaration
    reads `REPO_ROOT` (`core/reference_identity.py`), so the same series could
    declare one commit to the opponent and file another against itself — and it
    did: launched from `p2p-chase`, the identity block named the published head
    while every row named `55ddff06…`, a tree with no remote that resolves for
    nobody (M#53). Two sources for one value is the bug; taking the declared one
    as a parameter is the fix, because there is then only one.

    The value is filed **verbatim**, `-dirty` suffix included. Stripping it made
    a row claim a clean commit over a tree the declaration had just told the
    opponent was dirty — our own two artefacts contradicting each other about
    the one field that says which code ran.
    """
    our_group = sdk.team_name
    gid = game_id(our_group, their_group or "opponent")
    log_name = f"log_{gid}_g{number:02d}.json"
    keyword = raw_result.split(" (", 1)[0].strip().lower()
    # Three states, not two: a clean audit, a genuinely mismatched record, and
    # "nothing ever arrived" (a technical loss — nobody's forgery). Collapsing
    # the last two would print a forgery accusation over a plain timeout.
    received = bool(verdict.get("received"))
    log_verified = received and bool(verdict.get("passed"))
    tampered = received and not verdict.get("passed")
    if keyword not in ("capture", "survival"):
        # A technical loss pays 0-0 and crowns nobody (Ch. 3.5) — the row shape
        # imreeyal's own pairing playbook Stage 7 pins for exactly this case.
        return build_sub_game_row(
            number=number, our_group=our_group, their_group=their_group or "opponent",
            our_role=wire_role(session.role.value), result="technical_loss", winner_group="",
            steps=int(session.state.step), our_commit=our_commit, their_commit=their_commit,
            our_tokens=0, their_tokens=0, our_points=0, their_points=0,
            log_filename=log_name, log_verified=False, tampered=tampered,
            started_at=started, ended_at=ended,
        )
    outcome = Verdict.CAPTURE if keyword == "capture" else Verdict.SURVIVAL
    cop_points, thief_points = score(Outcome(outcome, ""), sdk.scoring)
    our_points, their_points = (
        (cop_points, thief_points) if session.role is Role.COP else (thief_points, cop_points)
    )
    winner_group = our_group if session.winner == session.role.value else (their_group or "opponent")
    return build_sub_game_row(
        number=number, our_group=our_group, their_group=their_group or "opponent",
        our_role=wire_role(session.role.value), result=keyword, winner_group=winner_group,
        steps=int(session.state.step), our_commit=our_commit, their_commit=their_commit,
        our_tokens=0, their_tokens=0, our_points=our_points, their_points=their_points,
        log_filename=log_name, log_verified=log_verified, tampered=tampered,
        started_at=started, ended_at=ended,
    )
