"""Replaying a saved match and proving it was not rewritten (TODO 7.5, M#20).

The Live GUI answers *what is happening now?* This answers the harder question:
*did what is claimed to have happened actually happen?*

In a system with no referee, the match history is not held by a trusted
authority — it is a file on each player's disk, which invites rewriting the past
to win retroactively. Cryptography is what turns that file from a forgeable
document into evidence, and this is where it is spent.

**One `TAMPERED` voids the match** (7.24). No appeal, no retrospective
correction. So the verdict has to be specific: which step, and why. "The replay
failed" is not something a grader can act on, and not something we could defend
ourselves against if the fault were on our side.

The stepping and the verifying are deliberately separate. Verification runs
**once, over the whole log, up front** — not lazily as the cursor moves. A
viewer that only checked the steps somebody happened to click through would
report `Verified OK` on a log whose forgery sits at step 30.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.crypto.audit import AuditResult
from core.crypto.commitment import verify
from core.report.match_log import records

__all__ = ["ReplaySession", "load_replay", "ReplayError", "VERIFIED_OK", "TAMPERED"]

VERIFIED_OK = ("Verified OK", "#1a7f37")
TAMPERED = ("TAMPERED", "#b00000")


class ReplayError(ValueError):
    """The file is not a match log this viewer can replay."""


@dataclass
class ReplaySession:
    """A loaded log, a cursor over it, and its verdict.

    Attributes:
        payload: The log as written by `core.report.match_log.build_log`.
        cursor: Which step is on screen, 0-based.
        result: The whole-log audit, computed once at construction.
    """

    payload: dict[str, Any]
    cursor: int = 0
    result: AuditResult = field(init=False)

    def __post_init__(self) -> None:
        """Audit the entire log before a single frame is drawn."""
        self.result = self.verify_all()

    def verify_all(self) -> AuditResult:
        """Re-hash every entry from its revealed nonce and move (7.5.2).

        Raises:
            ReplayError: The file is missing fields the re-hash needs. A log
                that cannot be verified must not be displayed as one that
                verified — a viewer showing a green banner over an unverifiable
                file is worse than one that refuses to open it.
        """
        from core.report.match_log import verify_log

        try:
            return verify_log(self.payload)
        except (KeyError, TypeError, AttributeError) as error:
            raise ReplayError(
                f"this file is not a replayable match log: missing or malformed {error}"
            ) from error

    @property
    def steps(self) -> list[dict[str, Any]]:
        """Every recorded step, in play order."""
        return list(self.payload.get("steps", []))

    @property
    def total(self) -> int:
        """How many steps the log holds."""
        return len(self.steps)

    @property
    def verdict(self) -> tuple[str, str]:
        """Return ``(text, colour)`` — green `Verified OK` or red `TAMPERED` (7.5.3)."""
        return VERIFIED_OK if self.result.passed else TAMPERED

    def current(self) -> dict[str, Any] | None:
        """The step under the cursor, or None for an empty log."""
        return self.steps[self.cursor] if self.total else None

    def step_ok(self, index: int) -> bool:
        """Whether one step re-hashes, for marking it in the step list.

        Recomputed per step rather than read from `result.failures`, because a
        failure recorded for ordering or duplication is about the log's *shape*
        and says nothing about whether that individual seal is genuine. A viewer
        that conflated them would point at the wrong row.

        🐛 **Both sealed fields, or this contradicts the banner above it.** This
        read `scent_digest` and not `sealed_barrier_cell`, so it rebuilt a
        payload the sealing peer never hashed and reported `MISMATCH` on every
        turn that walled a cell (C-018) — while `verify_all`, which goes through
        `records()` and does read both, passed the same log. The viewer
        therefore showed a green `Verified OK` over a red `MISMATCH` on an
        honest log, and a placement moves as `STAY`, so the affected steps are
        exactly the Cop's most consequential ones.

        The field set has to be read the way `match_log.records` reads it, which
        is why both use `.get` on the same two keys: presence is the signal, and
        an opponent who sealed neither has neither key.
        """
        if not 0 <= index < self.total:
            return False
        step = self.steps[index]
        return verify(
            step["claimed_digest"],
            step["state"],
            step["move"],
            step["intent"],
            step["nonce"],
            step.get("scent_digest"),
            step.get("sealed_barrier_cell"),
        )

    def forward(self) -> int:
        """Advance one step, stopping at the last. Returns the new cursor."""
        self.cursor = min(self.cursor + 1, max(0, self.total - 1))
        return self.cursor

    def back(self) -> int:
        """Go back one step, stopping at the first. Returns the new cursor."""
        self.cursor = max(0, self.cursor - 1)
        return self.cursor

    def describe(self) -> str:
        """One line for the window title and the report.

        The audit's own sentence, unprefixed. It already opens with the verdict
        — `Verified OK - 35 steps re-hashed` — so pasting `self.verdict` in
        front of it printed *"Verified OK - Verified OK - 35 steps re-hashed"*,
        which is what `--headless` put on screen for the M#20 deliverable. The
        `verdict` tuple stays where it belongs: the viewer's coloured badge.
        """
        return self.result.describe()

    def audit_records(self) -> list:
        """The parsed step records, for anything that wants them directly."""
        return records(self.payload)


def load_replay(path: Path) -> ReplaySession:
    """Load a log from disk and audit it.

    Read as **UTF-8 bytes explicitly**: hints and team names may be Hebrew, and
    a Windows console defaults to cp1252 — which would raise on a file that is
    perfectly valid (the rule from 6.5.2).

    Raises:
        ReplayError: The file is absent or not JSON.
    """
    path = Path(path)
    try:
        payload = json.loads(path.read_bytes().decode("utf-8"))
    except FileNotFoundError as error:
        raise ReplayError(f"no log at {path}") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ReplayError(f"{path} is not a readable JSON log: {error}") from error
    if not isinstance(payload, dict):
        raise ReplayError(f"{path} holds {type(payload).__name__}, not a match log")
    return ReplaySession(payload=payload)
