"""Everything one turn commits to, computed exactly once (TODO 9.4).

Split from `match_driver.py`, which drives a turn; this decides what the turn
*is*. The seam is real rather than a line-count convenience: the driver deals in
ordering and deadlines, and this file deals in the values that must be identical
across the wire, the hash and the log.

🐛 **The bug this module exists to prevent, found by the first real match.** The
seal and the log line each asked the runtime for the scent digest and the reveal
independently. Both derive from a filter that advances as the game does, so by
the time the log line was built — after the state had moved on — they answered
differently, and all 35 steps failed their own audit. An honest peer looked
exactly like a forger.

So a turn is planned once, and the plan is the only thing anyone reads
afterwards. Three recomputations that agree only while nothing moves is not a
property; it is a coincidence waiting for a graded match.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.crypto.commitment import seal
from core.domain.brain_base import Decision
from core.protocol.schemas import Reveal
from core.report.match_log import build_step
from core.runtime.turn_decode import sealed_state

__all__ = ["Planned", "plan_turn", "log_entry"]


@dataclass(frozen=True)
class Planned:
    """One turn's decision and every value derived from it.

    Attributes:
        decision: What the brain chose — move, barrier, claim and truth flag.
        reveal: The message that will carry it, hint and scent field included.
        sealed: The commitment, with the nonce to withhold until the audit.
        state: The snapshot the commitment was sealed against.
        scent_digest: The field's digest when C-008 was agreed, else None.
        barrier: The cell sealed into the commitment when C-018 was agreed and
            a placement was made — distinct from `decision.barrier`, which is
            declared either way.
    """

    decision: Decision
    reveal: Reveal
    sealed: Any
    state: dict[str, Any]
    scent_digest: str | None
    barrier: Any


def plan_turn(runtime: Any, step: int) -> Planned:
    """Decide, phrase, and seal — once, and in that order.

    `reveal_for` runs **before** `scent_digest`, deliberately: it advances the
    filter and lays this turn's deposit, so asking for the digest first would
    seal the field as it stood *last* turn while transmitting this turn's.
    Sealing one field and sending another is the exact hole C-008 closes,
    reintroduced from the other end.
    """
    state = runtime.orchestrator.state
    decision = runtime.decide()
    reveal = runtime.reveal_for(decision, step)
    scent_digest = runtime.scent_digest()
    barrier = runtime.sealed_barrier(decision)
    return Planned(
        decision=decision,
        reveal=reveal,
        state=sealed_state(state),
        scent_digest=scent_digest,
        barrier=barrier,
        sealed=seal(
            sealed_state(state),
            decision.move.value,
            decision.intent.value,
            scent_digest=scent_digest,
            barrier_cell=barrier,
        ),
    )


def log_entry(plan: Planned, step: int) -> dict[str, Any]:
    """Return this turn's log line, read entirely off the plan."""
    return build_step(
        step=step,
        claimed_digest=plan.sealed.digest,
        state=plan.state,
        move=plan.decision.move.value,
        intent=plan.decision.intent.value,
        hint=plan.reveal.hint,
        barrier_cell=plan.decision.barrier,
        scent_digest=plan.scent_digest,
        sealed_barrier=plan.barrier is not None,
    )
