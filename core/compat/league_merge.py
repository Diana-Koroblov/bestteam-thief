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


def load_rows(path: Path) -> list[dict[str, Any]]:
    """Return the sub-game rows already filed at *path*, or none if it is absent.

    Raises:
        ArtefactError: The file exists and cannot be read as a league result.
            Not skipped — silently treating the other role process's half as
            absent is exactly how a report ends up covering three sub-games
            while claiming to be the series (M#35).
    """
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload["sub_games"]
        return [dict(row) for row in rows]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ArtefactError(
            f"{path} exists but is not a readable league result ({error}). It holds "
            "the other role process's half; merging into it blind would file a "
            "report covering our sub-games only (M#35). Move it aside deliberately."
        ) from error


def merge_rows(
    existing: list[dict[str, Any]], ours: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return one row per sub-game, ours winning on a clash, in sub-game order."""
    by_number = {int(row["sub_game_number"]): row for row in existing}
    by_number.update({int(row["sub_game_number"]): row for row in ours})
    return [by_number[number] for number in sorted(by_number)]
