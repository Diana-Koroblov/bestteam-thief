"""The settlement consensus signature — the one field graders byte-compare.

Split from `test_league_report.py` at the 150-line ceiling (ADR-005), along a
real seam: that module tests what the artefact SAYS, this one tests the single
digest two independent implementations must agree on. Everything here is about
the preimage — its scope, its separators, and what must stay out of it.

**The recipe is restated by hand in these tests rather than imported from
`_AGGREGATE_KEYS`.** Importing it would make every assertion agree with the
implementation by construction and check nothing; the point is an independent
statement of the construction the reference implementation defines.
"""

from __future__ import annotations

import hashlib
import json

from core.compat.league_report import build_result, build_sub_game_row, consensus_sha256


def _row(number: int, result: str, winner: str, our_points: int, their_points: int) -> dict:
    """One clean, mutually-audited sub-game row."""
    return build_sub_game_row(
        number=number, our_group="bestteam", their_group="imreeyal",
        our_role="police", result=result, winner_group=winner, steps=20,
        our_commit="a" * 40, their_commit="b" * 40, our_tokens=0, their_tokens=0,
        our_points=our_points, their_points=their_points, log_filename="log.json",
        log_verified=True, tampered=False, started_at="t0", ended_at="t1",
    )


def test_mutual_agreement_hash_is_the_spaced_form_sign_then_insert() -> None:
    """Matches vectors/report_consensus.json's construction: sort_keys, spaced
    separators, and computed BEFORE the hash key is inserted into the document.

    The five aggregate keys are written out here rather than imported from
    `_AGGREGATE_KEYS`, on purpose: importing them would make this test agree
    with the implementation by construction and assert nothing. This is the
    recipe restated independently, and it is the whole recipe — there are no
    free variables left in it (imreeyal, 16/08).
    """
    rows = [_row(1, "capture", "bestteam", 20, 5)]
    result = build_result(
        counted=True, our_group="bestteam", their_group="imreeyal", sub_games=rows,
        game_uid_value="uid-1", timezone="Asia/Jerusalem",
        repos={}, games_played={"bestteam": 1, "imreeyal": None}, first_meeting=True,
    )
    doc = {
        "game_id": result["game_id"],
        "aggregate": {
            key: result["final_result"][key]
            for key in ("total_score", "sub_games_won", "ties", "winner_group", "series_tie")
        },
        "sub_games": [
            {key: row[key] for key in ("sub_game_number", "roles", "result", "winner_group", "score")}
            for row in result["sub_games"]
        ],
    }
    expected = hashlib.sha256(
        json.dumps(doc, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert result["mutual_agreement"]["sha256"] == expected == consensus_sha256(result)
    # The compact (no-space) form must NOT reproduce it - spaced is load-bearing.
    compact = hashlib.sha256(
        json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert compact != expected


def test_the_aggregate_excludes_the_filing_facts() -> None:
    """🐛 **We carried seven keys and the reference has five.**

    `first_meeting_between_groups` and `diversity_reward_applied` are claims
    this artefact makes about the LEAGUE around the series, not the symmetric
    outcome two engines compute independently from the same six sub-games —
    which is the only thing a mutual signature can mean. Our hash was
    self-consistent and reproduced from our own document every time; it simply
    could never equal an opponent's, and that is the one thing it is for.

    Asserted by changing only a filing fact: the signature must not move.
    """
    rows = [_row(1, "capture", "bestteam", 20, 5)]
    common = {
        "counted": True, "our_group": "bestteam", "their_group": "imreeyal",
        "sub_games": rows, "game_uid_value": "uid-1", "timezone": "Asia/Jerusalem",
        "repos": {}, "games_played": {"bestteam": 1, "imreeyal": None},
    }
    first = build_result(**common, first_meeting=True)
    again = build_result(**common, first_meeting=False)

    assert first["final_result"]["first_meeting_between_groups"] is True
    assert again["final_result"]["first_meeting_between_groups"] is False
    assert first["mutual_agreement"]["sha256"] == again["mutual_agreement"]["sha256"]


def test_mutual_agreement_ignores_per_side_fields() -> None:
    """Timestamps, tokens and commit hashes must never enter the hash, or two
    honest teams' bytes could never match by construction."""
    base = build_result(
        counted=True, our_group="bestteam", their_group="imreeyal",
        sub_games=[_row(1, "capture", "bestteam", 20, 5)],
        game_uid_value="uid-1", timezone="Asia/Jerusalem", repos={},
        games_played={"bestteam": 1, "imreeyal": None}, first_meeting=True,
    )
    changed_row = _row(1, "capture", "bestteam", 20, 5)
    changed_row["started_at"] = "some other time"
    changed_row["tokens"] = {"bestteam": 999, "imreeyal": 0}
    changed_row["github_commit"] = {"bestteam": "c" * 40, "imreeyal": "d" * 40}
    other = build_result(
        counted=True, our_group="bestteam", their_group="imreeyal", sub_games=[changed_row],
        game_uid_value="uid-1", timezone="Europe/London", repos={},
        games_played={"bestteam": 7, "imreeyal": 3}, first_meeting=True,
    )
    assert base["mutual_agreement"]["sha256"] == other["mutual_agreement"]["sha256"]
