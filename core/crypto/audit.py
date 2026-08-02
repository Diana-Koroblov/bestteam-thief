"""The end-of-match audit: re-hash both logs and find the forger (TODO 6.1.4).

**This is the only reason lying is safe to allow in this game.** The rulebook
lets an agent bluff freely in words, and that works precisely because *moves*
cannot be bluffed: each was sealed before the opponent chose theirs, and at the
end every seal is opened and recomputed. A hint is an opinion; a commitment is
a fact with a receipt.

Three properties this must have, and each is a way it could quietly fail:

* **Symmetric.** We audit their log and they audit ours, with the same code
  path. An audit that only ran one way would be an accusation, not a check.
* **Specific.** A failure names the step and the field, because "the audit
  failed" is not something a grader can act on and not something we could
  defend ourselves against if the fault were on our side.
* **Silent about who wins.** This module reports mismatches. It does not
  decide sanctions — that belongs to the rules layer, and mixing the two would
  make a scoring change able to alter what counts as evidence (M#19).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.crypto.commitment import verify

__all__ = ["StepRecord", "AuditResult", "audit_log"]


@dataclass(frozen=True)
class StepRecord:
    """One turn as it must appear in a log to be auditable.

    Attributes:
        step: Turn number. Included in the hashed state, so a commitment made
            for step 4 cannot be replayed at step 9.
        claimed_digest: What they sent during the commit phase.
        state: The board snapshot they committed against.
        move: The move revealed later.
        intent: ``truth`` or ``lie`` — the flag covering the hint.
        nonce: Released only at the final reveal (M#18).
        scent_digest: Present only when both peers agreed to seal it (C-008).
    """

    step: int
    claimed_digest: str
    state: Any
    move: str
    intent: str
    nonce: str
    scent_digest: str | None = None


@dataclass
class AuditResult:
    """What the audit found, in enough detail to act on.

    Attributes:
        checked: How many steps were verified.
        failures: ``(step, reason)`` for each mismatch, in step order.
    """

    checked: int = 0
    failures: list[tuple[int, str]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True only if every step verified. An empty log does **not** pass.

        A log with no steps is a missing log, not a clean one, and treating the
        two alike would let a peer escape the audit by sending nothing.
        """
        return self.checked > 0 and not self.failures

    def describe(self) -> str:
        """One line for the report, naming the first failure if there is one."""
        if self.passed:
            return f"Verified OK - {self.checked} steps re-hashed, no mismatch"
        if not self.checked:
            return "FAILED - empty log, nothing to verify"
        step, reason = self.failures[0]
        return (
            f"FAILED - {len(self.failures)} of {self.checked} steps mismatch; "
            f"first at step {step}: {reason}"
        )


def audit_log(records: list[StepRecord]) -> AuditResult:
    """Re-hash every step and report every mismatch.

    Args:
        records: The opponent's log, or our own — the same code both ways.

    Returns:
        An ``AuditResult``. **Never raises on a bad log.** A forged log is an
        expected input here, not an exceptional one, and an exception would end
        the audit at the first fault instead of reporting all of them.

    Steps are also checked for **ordering and duplication**. Re-hashing alone
    would accept a log whose steps were reordered or repeated, because each
    individual seal would still verify.
    """
    result = AuditResult()
    seen: set[int] = set()

    for position, record in enumerate(records):
        result.checked += 1

        if record.step in seen:
            result.failures.append((record.step, "duplicate step number"))
            continue
        seen.add(record.step)

        if position > 0 and record.step <= records[position - 1].step:
            result.failures.append((record.step, "step numbers are not increasing"))
            continue

        sealed_step = _step_inside(record.state)
        if sealed_step is not None and sealed_step != record.step:
            # **The replay hole, found by the test that was written to find it.**
            #
            # Verifying each seal and checking that step numbers increase is not
            # enough. A forger can take a genuine step-1 commitment, relabel it
            # as step 4 and leave the sealed state untouched: the digest still
            # matches its own state, and the outer numbers still ascend. The
            # commitment's "no time travel" guarantee only holds if somebody
            # actually compares the declared step against the sealed one.
            result.failures.append(
                (record.step, f"replays the commitment sealed for step {sealed_step}")
            )
            continue

        if not verify(
            record.claimed_digest,
            record.state,
            record.move,
            record.intent,
            record.nonce,
            record.scent_digest,
        ):
            result.failures.append(
                (record.step, "digest does not match the revealed move, intent and nonce")
            )

    return result


def _step_inside(state: Any) -> int | None:
    """Return the step number sealed inside *state*, if it carries one.

    Returns None when the state has no ``step`` key, rather than treating its
    absence as a failure: a peer may legitimately seal a state shaped
    differently from ours, and rejecting their whole log over a schema
    preference would be an accusation we cannot support.
    """
    if isinstance(state, dict):
        value = state.get("step")
        if isinstance(value, int):
            return value
    return None
