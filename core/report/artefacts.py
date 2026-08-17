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
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

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
    step_zero: dict[str, Any] | None = None,
    started_utc: str = "",
    ended_utc: str = "",
) -> dict[str, Any]:
    """Assemble ``declaration_<game_id>.json`` (7.2.1, M#24).

    Ch. 9.3.3 defines this file as everything **fixed** about the whole match:
    both groups and their members, the repository links, the MCP addresses, the
    hardware, the model, the agreed token ceiling, and the start and end times.

    Args:
        teams: ``{team_name: [member, ...]}`` for both sides.
        repos: The four repository links; missing ones are recorded as ``""``
            rather than omitted, so a reader sees *which* one is absent.
        mcp_urls: Each peer's public endpoint.
        llm_model: Our model name — never the provider (Appendix F Table 21).
        token_cap: The agreed ceiling, for the meter to be checked against.
        step_zero: ``{"ours": {...}, "theirs": {...}}`` — both sealed Step-0
            payloads with their digests. **This is what makes the hardware
            declaration a signed one** rather than a claim typed into a report:
            each half hashes to a digest the other peer already holds, so a
            machine specification cannot be rewritten after the match without
            contradicting a value the opponent can produce (M#24).
        started_utc: When the first sub-game of this match began. Passed rather
            than stamped here, because the file is rewritten at the end of the
            series and the start time must survive that.
        ended_utc: When the last one finished; ``""`` while the match is running,
            which is exactly what an interrupted series should leave on disk.
    """
    return {
        "game_id": game_identifier,
        "created_utc": utc_now(),
        "started_utc": started_utc or utc_now(),
        "ended_utc": ended_utc,
        "code_version": VERSION,
        "teams": teams,
        "repositories": {key: repos.get(key, "") for key in REPO_LINKS},
        "mcp_urls": mcp_urls,
        "llm_model": llm_model,
        "token_cap": token_cap,
        "hardware": describe(),
        "step_zero": dict(step_zero or {}),
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


def write(
    payload: dict[str, Any], directory: Path, filename: str, sort_keys: bool = True
) -> Path:
    """Write *payload* as UTF-8 JSON, atomically, and return the path.

    Args:
        sort_keys: Sorted by default, which is what makes two runs of our own
            artefacts byte-comparable. The league *result* file passes ``False``
            and relies on insertion order instead: the league's shape is an
            ordered one (`_schema, schema_version, report_type, …`), six
            pairings file it that way, and it is the one artefact the two teams
            diff against each other rather than against a previous run. Nothing
            hashed depends on this either way — `consensus_sha256` sorts its own
            derived document before signing it.

    Unlike ``runtime.snapshot.save`` this **does** raise on failure. A snapshot
    is written while something is already going wrong and must never make it
    worse; a report is written deliberately, and silently failing to produce a
    submission artefact would be discovered only by its absence in the grader's
    inbox — which is to say, too late.

    🐛 **Written through a temporary file and `os.replace`, because a plain
    truncate-and-write corrupted a real match.** Both of our role processes file
    `result_<game_id>.json` under one identifier — that is the whole point of the
    merge — and when their writes overlapped, the shorter one truncated the
    longer and left its tail behind::

        ArtefactError: ... is not a readable result file (Extra data: line 67)

    `load_rows` then refuses the file, correctly, and reporting stops dead. The
    replace is atomic on both Windows and POSIX, so a concurrent writer now
    yields one whole document rather than two spliced halves. It does not make
    the last writer merge — `merge_rows` does that — but a lost update is
    recoverable by re-running a half, and a corrupt artefact is not.

    The staged name carries the pid *and* a random token. The pid alone is not
    enough: it identifies the process for anyone debugging a stray file, but two
    threads in one process share it, and they would then splice the temporary
    file instead of the target — the same bug moved one filename along.
    """
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    # Terminating newline, deliberately. A MIME text part must end with one, so
    # the mailer would otherwise append a byte the file on disk does not have —
    # and the league's convention is artefact bytes == body bytes == attachment
    # bytes, compared with strict equality (imreeyal have failed a pairing's
    # mail over ten bytes). Emitting it here makes the three identical at the
    # source rather than asking every reader to tolerate a difference.
    body = json.dumps(payload, indent=2, sort_keys=sort_keys, ensure_ascii=False) + "\n"
    staged = target.with_name(f"{target.name}.{os.getpid()}.{uuid4().hex[:8]}.tmp")
    staged.write_bytes(body.encode("utf-8"))
    _replace_when_windows_lets_go(staged, target)
    return target


# One second, in twenty parts. The conflict below lasts as long as another
# process holds a handle open, which for a peer reading an artefact is
# milliseconds — and a second is still far inside the 30 s response window.
REPLACE_ATTEMPTS = 20
REPLACE_PAUSE_SEC = 0.05


def _replace_when_windows_lets_go(staged: Path, target: Path) -> None:
    """Replace *target* with *staged*, waiting out a concurrent reader.

    🐛 **`os.replace` is atomic on Windows but it is not always permitted.**
    `MoveFileEx` fails with `ERROR_ACCESS_DENIED` when anything else has the
    destination open, and both of our role processes write one declaration and
    one result under a single `game_id`. A live rehearsal over the tunnel hit it
    exactly once, on the last write of the match::

        PermissionError: [WinError 5] Access is denied:
            'declaration_....json.4432.5a424743.tmp' -> 'declaration_....json'

    and the cost was the whole report: the exception left `MatchFiling.result`
    through `SeriesRunner.run`, so a peer that had played three clean sub-games
    printed no scoreboard, filed no `result_<game_id>.json` and sent nothing —
    while the opponent filed normally. One side reporting and the other silent
    is the contradictory pair M#35 scores **0 for both teams** over, produced by
    the code that made writing atomic in the first place.

    A retry is the whole fix, because the condition is transient by nature: the
    other process is reading, not holding. When it genuinely will not clear, the
    staged file is removed rather than left as litter beside the real artefacts,
    and the caller is told which write failed.

    Raises:
        ArtefactError: The replace never became possible.
    """
    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(staged, target)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS - 1:
                break
            time.sleep(REPLACE_PAUSE_SEC)

    staged.unlink(missing_ok=True)
    raise ArtefactError(
        f"could not replace {target.name} after "
        f"{REPLACE_ATTEMPTS * REPLACE_PAUSE_SEC:g}s - another process is holding it open"
    )


def payload_digest(payload: dict[str, Any]) -> str:
    """Canonical digest of an artefact, for the log and for cross-checking."""
    return digest(payload)
