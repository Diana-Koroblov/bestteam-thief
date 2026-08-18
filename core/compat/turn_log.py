"""A plain-text trail of every turn sent or received, to a file console output can lose.

Requested directly (yanell11, 18/08) after a cop went silent mid-game with no
trace anywhere: console output redirected to a file is still one process's
stdout, and a hang or a silent exception leaves nothing after the last line
that happened to flush. This writes one line per turn, opened in append mode
and flushed immediately, so the last line on disk names the exact step a
process died on even if the process never got to exit cleanly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

__all__ = ["log_turn"]


def log_turn(role: str, sub_game: int, step: int, direction: str, note: str = "") -> None:
    """Append one line: who we are, which sub-game and step, sent or received."""
    line = (
        f"{datetime.now(UTC).isoformat()}  role={role}  sub_game={sub_game}  "
        f"step={step}  {direction}"
    )
    if note:
        line += f"  {note}"
    path = Path(f"turn_log_{role}.log")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
