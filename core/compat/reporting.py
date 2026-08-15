"""Filing and sending a reference-protocol series' own report (the twin of
``core/runtime/reporting.py`` over the league schema — see ``league_report.py``).

Friendly reports go to the two teams' own inboxes and never the lecturer;
counted reports go to the league alias, exactly as the native path already
does, gated the same way: ``--counted`` **and** the opponent must be a real
team, not ourselves (a self-match has no second reporter to agree with).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from core.compat import league_merge, league_report
from core.compat.wire import terms_from_config
from core.infra.gmail_sender import GmailSender, build_transport
from core.report.artefacts import write
from core.sdk.peer_sdk import PeerSDK
from core.shared.league_log import LeagueLogError, counted_matches
from core.shared.league_log import read as read_league_log

__all__ = ["send_league_report"]

MANUAL = "  file it by hand once complete: both role processes must have run."
LABEL = "league report  : "


def send_league_report(
    sdk: PeerSDK,
    args: argparse.Namespace,
    rows: list[dict[str, Any]],
    our_identity: dict[str, Any],
    their_identity: dict[str, Any],
    their_group: str,
) -> str:
    """Merge, file, and — if the series is complete — send our own report.

    Never raises: the series is over and its logs are on disk regardless of
    whether the report can be built or mailed, so every failure is described
    rather than propagated (matching ``core.runtime.reporting``).
    """
    if not their_group:
        return f"{LABEL}NOT FILED - no opponent group_id was ever learned (no sub-game agreed)"
    try:
        return _send(sdk, args, rows, our_identity, their_identity, their_group)
    except Exception as error:  # the match is over; nothing here may crash it
        return f"{LABEL}NOT FILED - {type(error).__name__}: {error}"


def _send(
    sdk: PeerSDK,
    args: argparse.Namespace,
    rows: list[dict[str, Any]],
    our_identity: dict[str, Any],
    their_identity: dict[str, Any],
    their_group: str,
) -> str:
    our_group = sdk.team_name
    out = Path(args.out)
    gid = league_report.game_id(our_group, their_group)
    path = out / f"result_{gid}.json"
    merged = league_merge.merge_rows(league_merge.load_rows(path), rows)
    counted = bool(getattr(args, "counted", False)) and their_group != our_group
    terms = terms_from_config(sdk.runtime.orchestrator.config)
    uid = league_report.game_uid(terms, our_group, their_group)
    result = league_report.build_result(
        counted=counted,
        our_group=our_group,
        their_group=their_group,
        sub_games=merged,
        game_uid_value=uid,
        timezone=str(sdk.runtime.orchestrator.config.get("network.timezone", "Asia/Jerusalem")),
        repos={our_group: our_identity.get("repos", {}), their_group: their_identity.get("repos", {})},
        games_played=_games_played(our_group, their_group),
        first_meeting=_first_meeting(their_group),
    )
    write(result, out, f"result_{gid}.json")

    expected = sdk.num_games
    if len(merged) < expected:
        return (
            f"{LABEL}held back - {path.name} covers {len(merged)} of {expected} sub-games\n"
            "  the other role process files the rest (M#35)\n" + MANUAL
        )
    if not counted:
        return _send_friendly(sdk, args, path)
    return _send_counted(sdk, path)


def _games_played(our_group: str, their_group: str) -> dict[str, int | None]:
    """Ours is always known; theirs is null unless they declared it (SPEC §6.2:
    a count is each team's own unverifiable claim, so null is *unclaimed*, not 0)."""
    return {our_group: counted_matches(), their_group: None}


def _first_meeting(their_group: str) -> bool:
    try:
        played = {name.lower() for name in read_league_log().opponents}
    except LeagueLogError:
        return True
    return their_group.lower() not in played


def _send_friendly(sdk: PeerSDK, args: argparse.Namespace, path: Path) -> str:
    raw = str(getattr(args, "report_to", "") or "")
    recipients = [addr.strip() for addr in raw.split(",") if addr.strip()]
    if not recipients:
        return f"{LABEL}NOT SENT - friendly, but no --report-to given\n" + MANUAL
    config = sdk.runtime.orchestrator.config
    enabled = bool(config.get("email.enabled", True))
    if not enabled:
        return f"{LABEL}NOT SENT - [email] enabled is off in game.toml\n" + MANUAL
    mailer = GmailSender(
        sender=str(config.get("email.sender", "")).strip(),
        recipient=", ".join(recipients),
        gatekeeper=sdk.gatekeeper,
        transport=lambda body: build_transport()(body),
        enabled=enabled,
    )
    mailer.send_result(path, subject=f"{path.stem} (friendly)")
    return f"{LABEL}sent to {mailer.recipient}  ({path.name}, friendly, never the lecturer)"


def _send_counted(sdk: PeerSDK, path: Path) -> str:
    mailer = sdk.mailer()
    if not mailer.enabled or not mailer.on_series_end:
        return f"{LABEL}NOT SENT - [email] enabled/send_on_series_end is off\n" + MANUAL
    mailer.send_result(path)
    return (
        f"{LABEL}sent to {mailer.recipient}  ({path.name}, counted)\n"
        "  now confirm THEY sent theirs - a missing report is 0 for BOTH (M#35)"
    )
