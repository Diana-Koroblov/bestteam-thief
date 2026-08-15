"""The league's own four-artefact shape — not ours (docs/PAIRING-PLAYBOOK.md Stage 1/4c).

`core/report/artefacts.py` builds the native path's schema: `totals.ours/theirs`,
no `game_uid`, no league fields. Teams built on the reference protocol (the
majority of this league, per the copthief-league-protocol conformance kit) file
and email a differently-shaped `result_<game_id>.json` — keyed by group name
rather than "ours/theirs", carrying `game_uid`, `mutual_agreement.sha256` and
three league fields. A shared "flexible" builder would be one edit away from
producing a file neither grader's tooling recognises, so this is a second,
independent implementation rather than a parametrised first one.
"""

from __future__ import annotations

import json
import uuid
from hashlib import sha256
from typing import Any

from core.crypto.canonical import canonical_json

__all__ = ["game_id", "game_uid", "build_sub_game_row", "build_result", "consensus_sha256"]

# The symmetric hash scope (imreeyal §6; vectors/report_consensus.json in the
# kit pins the same spaced-form construction). Anything outside these keys is
# per-side and must never enter the hash, or two honest teams' bytes can never
# match by construction.
_AGGREGATE_KEYS = (
    "total_score", "sub_games_won", "ties", "winner_group", "series_tie",
    "first_meeting_between_groups", "diversity_reward_applied",
)
_ROW_KEYS = ("sub_game_number", "roles", "result", "winner_group", "score")


def game_id(group_a: str, group_b: str) -> str:
    """Return the sorted-pair match id both sides derive with nothing to negotiate."""
    return "-vs-".join(sorted([group_a, group_b]))


def game_uid(terms: dict[str, Any], group_a: str, group_b: str) -> str:
    """Return the id both peers reproduce without a round-trip.

    ``uuid(sha256(canonical(terms) + "|" + "|".join(sorted([a, b])))[:16])`` —
    the kit's own formula (`vectors/game_uid.json`), reproduced against
    `verify_vectors.py` on this tree before this function was written. Derived
    from the FLAT terms only, never the whole `game.json` (WARNINGS §2).
    """
    pair = sorted([group_a, group_b])
    seed = f"{canonical_json(terms)}|{'|'.join(pair)}"
    return str(uuid.UUID(bytes=sha256(seed.encode()).digest()[:16]))


def build_sub_game_row(
    *,
    number: int,
    our_group: str,
    their_group: str,
    our_role: str,
    result: str,
    winner_group: str,
    steps: int,
    our_commit: str,
    their_commit: str,
    our_tokens: int,
    their_tokens: int,
    our_points: int,
    their_points: int,
    log_filename: str,
    log_verified: bool,
    tampered: bool,
    started_at: str,
    ended_at: str,
) -> dict[str, Any]:
    """Return one row of ``sub_games`` in the league's own field names.

    ``log_verified``/``tampered`` are independent, not two readings of one
    bool: a clean audit is ``(True, False)``, a genuinely mismatched record is
    ``(False, True)``, and "no audit ever arrived" — a technical loss, nobody's
    forgery — is ``(False, False)``. Collapsing the last two into "not verified
    means tampered" would print a forgery accusation over a plain timeout
    (imreeyal's own pairing playbook Stage 7 pins the technical-loss row at
    exactly `{log_verified: false, tampered: false}`).
    """
    their_role = "thief" if our_role == "police" else "police"
    return {
        "sub_game_number": number,
        "roles": {our_group: our_role, their_group: their_role},
        "started_at": started_at,
        "ended_at": ended_at,
        "result": result,
        "winner_group": winner_group,
        "tie": False,
        "steps": steps,
        "github_commit": {our_group: our_commit, their_group: their_commit},
        "tokens": {our_group: our_tokens, their_group: their_tokens},
        "score": {our_group: our_points, their_group: their_points},
        "log_files": {our_group: log_filename, their_group: log_filename},
        "audit": {"log_verified": log_verified, "tampered": tampered},
    }


def build_result(
    *,
    counted: bool,
    our_group: str,
    their_group: str,
    sub_games: list[dict[str, Any]],
    game_uid_value: str,
    timezone: str,
    repos: dict[str, dict[str, str]],
    games_played: dict[str, int | None],
    first_meeting: bool,
) -> dict[str, Any]:
    """Assemble ``result_<game_id>.json`` in the league's schema, hash included."""
    gid = game_id(our_group, their_group)
    total_score: dict[str, int] = {}
    tokens_total: dict[str, int] = {}
    wins = {our_group: 0, their_group: 0}
    for row in sub_games:
        for group, points in row["score"].items():
            total_score[group] = total_score.get(group, 0) + int(points)
        for group, tokens in row["tokens"].items():
            tokens_total[group] = tokens_total.get(group, 0) + int(tokens)
        if row["winner_group"] in wins:
            wins[row["winner_group"]] += 1
    series_tie = total_score.get(our_group, 0) == total_score.get(their_group, 0)
    winner = None if series_tie else max(total_score, key=lambda g: total_score[g])
    diversity = {
        our_group: bool(counted and first_meeting and winner == our_group),
        their_group: bool(counted and first_meeting and winner == their_group),
    }
    result: dict[str, Any] = {
        "_schema": "Final series result (book section 9.3.3). Email the compact "
        "canonical bytes, not this pretty-print.",
        "schema_version": "1.2",
        "report_type": "final_game_result",
        "league": {
            "authority": "book App. E rule 52 - one counted series per pairing",
            "counted": counted,
            "reason": "counted" if counted else "friendly",
        },
        "game_id": gid,
        "game_uid": game_uid_value,
        "links": {
            "declaration": f"declaration_{gid}.json",
            "config": f"config_{gid}_g<NN>.json",
            "log": f"log_{gid}_g<NN>.json",
            "result": f"result_{gid}.json",
            "github": repos,
        },
        "timezone": timezone,
        "groups": sorted([our_group, their_group]),
        "num_sub_games": len(sub_games),
        "sub_games": sub_games,
        "final_result": {
            "total_score": total_score,
            "sub_games_won": wins,
            "ties": sum(1 for row in sub_games if row["tie"]),
            "winner_group": winner,
            "series_tie": series_tie,
            "tokens_total_series": tokens_total,
            "games_played_including_this": games_played,
            "first_meeting_between_groups": first_meeting,
            "diversity_reward_applied": diversity,
        },
    }
    result["mutual_agreement"] = {"sha256": consensus_sha256(result), "confirmed": True}
    return result


def consensus_sha256(result: dict[str, Any]) -> str:
    """Return the settlement consensus signature both teams must reproduce.

    Scope is ``{game_id, aggregate, sub_games[]}``, each row trimmed to
    ``_ROW_KEYS`` — the symmetric outcome only (imreeyal §6). Spaced-form JSON
    (``json.dumps`` defaults, not the compact form every other hash in this
    project uses), computed **before** this key is inserted into the document —
    sign-then-insert, so the field is excluded from its own preimage. Matches
    ``vectors/report_consensus.json`` in the league conformance kit.
    """
    doc = {
        "game_id": result["game_id"],
        "aggregate": {key: result["final_result"][key] for key in _AGGREGATE_KEYS},
        "sub_games": [{key: row[key] for key in _ROW_KEYS} for row in result["sub_games"]],
    }
    spaced = json.dumps(doc, sort_keys=True, ensure_ascii=False)
    return sha256(spaced.encode("utf-8")).hexdigest()
