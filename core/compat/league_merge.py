"""Joining two role-processes' halves of one league-schema result (core/report/merge.py's twin).

Same two-process problem as the native path (a 3-3 split is two processes in
sequence, ADR-001) over the league schema's own field names — `sub_game_number`
rather than `sub_game`, rows keyed by group name rather than "ours"/"theirs".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.report.artefacts import ArtefactError

__all__ = ["load_rows", "merge_rows"]


def load_rows(path: Path, expect_uid: str = "", expect_date: str = "") -> list[dict[str, Any]]:
    """Return the sub-game rows already filed at *path*, or none if it is absent.

    Args:
        expect_uid: The ``game_uid`` of the series now being filed.
        expect_date: The calendar date its sub-games started, ``YYYY-MM-DD``.

    Raises:
        ArtefactError: The file exists and cannot be read as a league result,
            or it holds a **different series**. Neither is skipped — silently
            treating the other role process's half as absent is how a report
            ends up covering three sub-games while claiming to be the series
            (M#35).

    🐛 **The filename is derived from `game_id` alone**, which is only the
    sorted team pair — so every series against one opponent claims the same
    path, and `merge_rows` keys on `sub_game_number`. A second series against a
    team we had already played therefore merges *into the first*, row by row,
    producing one document that describes two different afternoons and a
    `mutual_agreement.sha256` matching neither. Ours against imreeyal (16/08 at
    47-47, 17/08 at 40-60) escaped this only because the two runs happened to be
    given different `--out` directories.

    The filename cannot be the fix: the league schema pins match-level artefacts
    to `<role>_<game_id>.json` and that is the name that gets emailed.

    **`game_uid` alone is not the discriminator either**, which is worth stating
    because it looks like one. It is `sha256(canonical(terms) | pair)` — derived
    from the negotiated terms, not from the occasion — so two series played
    under one unchanged config share it exactly. Our two imreeyal results both
    carry `ffad01a2-4965-be0b-c708-3cdbedd7373a`. It is kept as the cheap
    second net that catches a renegotiated series; the **date** is what
    separates two runs of the same contract, and both role processes of one
    series agree on it because they play it together.
    """
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = [dict(row) for row in payload["sub_games"]]
        found_uid = str(payload.get("game_uid", "") or "")
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ArtefactError(
            f"{path} exists but is not a readable league result ({error}). It holds "
            "the other role process's half; merging into it blind would file a "
            "report covering our sub-games only (M#35). Move it aside deliberately."
        ) from error

    if expect_uid and found_uid and found_uid != expect_uid:
        raise _different(path, f"it was played under other terms (game_uid {found_uid})")
    found_date = _started_date(rows)
    if expect_date and found_date and found_date != expect_date:
        raise _different(path, f"its sub-games were played on {found_date}, ours on {expect_date}")
    return rows


def _started_date(rows: list[dict[str, Any]]) -> str:
    """Return the calendar date the filed sub-games began, or ``""``.

    Read from the first row that carries a parseable `started_at`. Rows filed
    by an older build, or one that never stamped a start, yield no opinion —
    unknown is not a mismatch, and refusing on it would strand the other half
    of a legitimate series.
    """
    for row in rows:
        stamp = str(row.get("started_at", "") or "")
        if len(stamp) >= 10 and stamp[4] == "-" and stamp[7] == "-":
            return stamp[:10]
    return ""


def _different(path: Path, because: str) -> ArtefactError:
    """Return the refusal, naming what to do about it.

    The operator is looking at two results that want one filename, and the
    thing they need told is which one is which and that neither is lost.
    """
    return ArtefactError(
        f"{path} holds a DIFFERENT series: {because}. Merging would fuse two series "
        "into one report describing neither, under a consensus hash matching neither. "
        "File this series under its own --out directory, or move the earlier result "
        "aside deliberately."
    )


def merge_rows(
    existing: list[dict[str, Any]], ours: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return one row per sub-game, ours winning on a clash, in sub-game order."""
    by_number = {int(row["sub_game_number"]): row for row in existing}
    by_number.update({int(row["sub_game_number"]): row for row in ours})
    return [by_number[number] for number in sorted(by_number)]
