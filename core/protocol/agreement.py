"""The verdict of a handshake, and the record it leaves (TODO 9.1, N10).

Split from `negotiation.py` when that file reached its 150 lines. The seam is the
same one `schemas.py` and `tools.py` sit either side of: this is the **value** —
the vocabulary of outcomes and the artefact a match is filed under — and
`negotiation.py` is the comparison that produces it.

Worth keeping apart for a second reason. The record outlives the exchange: it is
committed beside the match log and read months later by a grader, or by an
opponent disputing a result. Its shape is a contract with those readers, not an
implementation detail of the comparison that happened to fill it in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "AGREED",
    "REFUSED_CONFIG_MISMATCH",
    "REFUSED_SCENT_MISMATCH",
    "REFUSED_READING_MISMATCH",
    "REFUSED_ROLE_SPLIT",
    "REFUSED_BY_OPPONENT",
    "LockedAgreement",
    "utc_now",
]

AGREED = "AGREED"
REFUSED_CONFIG_MISMATCH = "REFUSED_CONFIG_MISMATCH"
REFUSED_SCENT_MISMATCH = "REFUSED_SCENT_MISMATCH"
REFUSED_READING_MISMATCH = "REFUSED_READING_MISMATCH"
REFUSED_ROLE_SPLIT = "REFUSED_ROLE_SPLIT"

# **The handshake is not symmetric, and this is the far side of it.** Whoever
# sends first gets a structured verdict; whoever *answers* raises a
# ProtocolError, which reaches the initiator as a remote error string and not as
# a comparison it can inspect. Without a result for that case the initiating peer
# would learn of a refusal as a traceback and file no record of it — and a
# refusal is exactly the outcome most worth having on disk, because it is the one
# that gets argued about afterwards.
REFUSED_BY_OPPONENT = "REFUSED_BY_OPPONENT"


def utc_now() -> str:
    """UTC to the second. Both peers file a time; a local one would disagree."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class LockedAgreement:
    """What the two peers settled, and what a human still has to.

    Attributes:
        result: ``AGREED`` or one of the refusals. Play may start only on the
            first, and the state machine is what enforces that.
        reasons: Why it was refused, quotably. With no referee, "your step 0
            reveal used subtractive decay" is the entire remedy available to us.
        warnings: Everything neither peer signed. **Not** a softer refusal —
            these are the items that must be settled in the human channel before
            the first move, because a mechanism discovered mid-match is
            unresolvable and voids the result for both teams (M#35).
        scent_model: The M#23 payload itself, not only its hash. Attached by the
            caller that owns a configuration; `settle` deliberately cannot read
            one.
        clause: The paragraph both sides agreed in writing (9.1.6).
    """

    result: str
    config_sha256: str = ""
    scent_model_sha256: str = ""
    our_games_played: int = 0
    their_games_played: int = 0
    our_commit: str = ""
    their_commit: str = ""
    role_split: str = ""
    readings: dict[str, str] = field(default_factory=dict)
    scent_model: dict[str, Any] = field(default_factory=dict)
    clause: str = ""
    reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    agreed_at: str = field(default_factory=utc_now)

    @property
    def agreed(self) -> bool:
        """Whether play may start."""
        return self.result == AGREED

    def payload(self) -> dict[str, Any]:
        """Return the record written beside the match log (N10, 9.3.5).

        **The scent model travels as its payload, not only as its hash.** A
        digest proves two peers agreed; it does not say *what* they agreed, and
        the file a grader or a disputing opponent reads afterwards needs the
        second. It is also where `sampling_mode` is recorded (9.1.7).

        The clause is kept for the same reason. 9.1.6's requirement is that the
        capture rules were settled *in writing*, and the writing belongs in the
        artefact rather than in whichever chat window it was pasted into.

        Warnings are kept rather than printed and forgotten. A match played with
        three unsigned readings is a match whose result can be disputed, and the
        file that says so should be the one committed with it.
        """
        return {
            "result": self.result,
            "agreed_at": self.agreed_at,
            "config_sha256": self.config_sha256,
            "scent_model_sha256": self.scent_model_sha256,
            "scent_model": dict(self.scent_model),
            "role_split": self.role_split,
            "games_played": {"ours": self.our_games_played, "theirs": self.their_games_played},
            "github_commit": {"ours": self.our_commit, "theirs": self.their_commit},
            "readings": dict(self.readings),
            "agreed_clause": self.clause,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
        }
