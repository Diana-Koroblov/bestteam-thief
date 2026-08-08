"""Building and writing the four match artefacts (TODO 7.2.1-7.2.4).

These are the files a grader reads. Two rules shape all of them:

* **Nothing is invented.** Every value is either measured, negotiated, or read
  from git. A plausible-looking placeholder in a submitted report is worse than
  an absent field, because a missing field prompts a question and a wrong one
  does not.
* **Written as UTF-8 bytes, explicitly.** Team names may be Hebrew and Windows
  consoles are cp1252. See the package docstring.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.crypto.canonical import digest
from core.shared.system_info import describe
from core.shared.version import VERSION

__all__ = [
    "ArtefactError",
    "build_declaration",
    "build_config_snapshot",
    "build_result",
    "write",
    "payload_digest",
    "utc_now",
    "REPO_LINKS",
]


class ArtefactError(ValueError):
    """An artefact would contradict itself, so it is refused rather than written."""


# **Four** links, not two: the rulebook wants both teams' repositories for both
# roles, so a grader can read every agent that played (7.2.1 DoD).
REPO_LINKS = ("ours_cop", "ours_thief", "theirs_cop", "theirs_thief")


def utc_now() -> str:
    """UTC, ISO-8601. Both peers are in one timezone today and may not be
    tomorrow; a local timestamp would make two reports disagree about when a
    match happened.

    ``timezone.utc`` rather than ``datetime.UTC``: the latter is Python 3.11+
    and this project targets 3.10. Diana runs 3.12 and would never have seen it
    — the same shape as the ``tomllib`` problem in Phase 1.
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_declaration(
    game_identifier: str,
    teams: dict[str, list[str]],
    repos: dict[str, str],
    mcp_urls: dict[str, str],
    llm_model: str,
    token_cap: int,
) -> dict[str, Any]:
    """Assemble ``declaration_<game_id>.json`` (7.2.1).

    Args:
        teams: ``{team_name: [member, ...]}`` for both sides.
        repos: The four repository links; missing ones are recorded as ``""``
            rather than omitted, so a reader sees *which* one is absent.
        mcp_urls: Each peer's public endpoint.
        llm_model: Our model name — never the provider (Appendix F Table 21).
        token_cap: The agreed ceiling, for the meter to be checked against.
    """
    return {
        "game_id": game_identifier,
        "created_utc": utc_now(),
        "code_version": VERSION,
        "teams": teams,
        "repositories": {key: repos.get(key, "") for key in REPO_LINKS},
        "mcp_urls": mcp_urls,
        "llm_model": llm_model,
        "token_cap": token_cap,
        "hardware": describe(),
    }


def build_config_snapshot(
    game_identifier: str,
    sub_game: int,
    shared_config: dict[str, Any],
    role: str,
    agreed_digest: str = "",
    role_split: str = "",
    scent_model_digest: str = "",
    readings: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Assemble ``config_<game_id>_g<NN>.json`` (7.2.2, Appendix F §2, M#11).

    This is the sub-game's rulebook, frozen. It is committed to both
    repositories after the match so that anyone re-reading the log can see the
    physics it was played under — a log without its config is a list of moves
    nobody can score.

    Args:
        shared_config: The negotiated contract verbatim, exactly as both peers
            hashed it. The **shared** file only: private settings are not part
            of the agreement and including them would make two correctly-agreed
            peers file contradicting snapshots.
        agreed_digest: The `config_sha256` actually exchanged at the handshake.
            Optional, and checked when given — see below.
        readings: The C-006/C-010 mechanism choices, which Appendix F does not
            cover at all and which two honest peers will otherwise assume
            differently (C-011).

    Raises:
        ArtefactError: *agreed_digest* does not match the config in this file.
            **The digest is recomputed here rather than copied.** A snapshot
            asserting agreement on a config it does not actually contain is not
            merely wrong, it is evidence for the wrong thing: it would be quoted
            in a dispute to prove a match was played under parameters that were
            never agreed. Refusing to write it is the only safe outcome.
    """
    computed = payload_digest(shared_config)
    if agreed_digest and agreed_digest != computed:
        raise ArtefactError(
            f"config digest mismatch for sub-game {sub_game}: the handshake agreed "
            f"{agreed_digest[:16]}... but this config hashes to {computed[:16]}.... "
            "Refusing to write a snapshot that claims agreement on parameters it "
            "does not contain (M#11)."
        )
    return {
        "game_id": game_identifier,
        "sub_game": sub_game,
        "created_utc": utc_now(),
        "code_version": VERSION,
        "role": role,
        "config_sha256": computed,
        "role_split": role_split,
        "scent_model_digest": scent_model_digest,
        "readings": dict(readings or {}),
        "shared_config": shared_config,
    }


def build_result(
    game_identifier: str,
    sub_games: list[dict[str, Any]],
    github_commit: str,
    total_llm_tokens: int,
    repos: dict[str, str],
    series: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble ``result_<game_id>.json`` (7.2.4, M#49, M#53, M#54).

    Args:
        sub_games: One entry per sub-game, each carrying at least ``role``,
            ``verdict``, ``cop_points`` and ``thief_points``.
        github_commit: From Step-0, so the result names the code that produced
            it (M#53).
        total_llm_tokens: Cumulative model tokens (M#54). Named for which kind
            of token it counts, per the 7.1.4 discipline: rate-limiter tokens
            and OAuth tokens are different things and a bare `total_tokens`
            does not say which one a reader is looking at.
        series: What the meeting is worth once the tie rule has been applied.
            Filed **beside** `totals` rather than replacing it, because the two
            answer different questions: `totals` is the arithmetic of the
            sub-games and this is the league credit. A series level at 45-45
            pays 2-2 (Ch. 9.2 tie rule), and a report showing only one of those
            numbers reads like the other was a mistake.

    Cumulative scores are **summed here, not passed in**. A caller supplying its
    own total could disagree with the per-sub-game rows in the same file, and a
    report that contradicts itself is worse than one that is merely wrong.
    """
    ours = sum(int(game.get("our_points", 0)) for game in sub_games)
    theirs = sum(int(game.get("their_points", 0)) for game in sub_games)
    return {
        "game_id": game_identifier,
        "created_utc": utc_now(),
        "github_commit": github_commit,
        "code_version": VERSION,
        "sub_games": sub_games,
        "totals": {"ours": ours, "theirs": theirs, "sub_games_played": len(sub_games)},
        "series": dict(series or {}),
        "total_llm_tokens": total_llm_tokens,
        "repositories": {key: repos.get(key, "") for key in REPO_LINKS},
    }


def write(payload: dict[str, Any], directory: Path, filename: str) -> Path:
    """Write *payload* as UTF-8 JSON and return the path.

    Unlike ``runtime.snapshot.save`` this **does** raise on failure. A snapshot
    is written while something is already going wrong and must never make it
    worse; a report is written deliberately, and silently failing to produce a
    submission artefact would be discovered only by its absence in the grader's
    inbox — which is to say, too late.
    """
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    body = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    target.write_bytes(body.encode("utf-8"))
    return target


def payload_digest(payload: dict[str, Any]) -> str:
    """Canonical digest of an artefact, for the log and for cross-checking."""
    return digest(payload)
