"""Releasing the nonces and auditing the opponent's log (M#18, M#19, M#36).

The end of a sub-game is where commit-reveal finally pays out. Until now every
digest the opponent sent was unverifiable on purpose: releasing nonces turn by
turn would let each side confirm its guesses about the other's strategy while
the game was still running. At the end, both sides open everything.

**We reconstruct their log rather than asking for it**, and that is the point
Ch. 5.4 makes: *"Each side takes the opponent's State, Move, Intent and the
exposed Nonce, reconstructs the data, hashes it afresh, and compares against the
signature declared at the commitment stage."* Every input is something we
already hold and they cannot retract — the digest they committed, the move they
revealed, the field they transmitted, the state both peers computed
independently. A log they hand us at the end is a document; this is evidence.

That is also why the state comes from **our** history and never from them: it is
the one field a forger would most want to choose after the fact, and we have our
own copy of it.
"""

from __future__ import annotations

from typing import Any

from core.crypto.audit import AuditResult, StepRecord, audit_log
from core.crypto.canonical import digest
from core.protocol.schemas import FinalReveal
from core.runtime.turn_decode import sealed_state

__all__ = ["their_records", "exchange_and_audit"]


def their_records(driver: Any) -> list[StepRecord]:
    """Rebuild the opponent's log from what we independently hold.

    Only steps they both committed *and* revealed are included. A step with a
    commitment and no reveal is not evidence of forgery — it is a turn that
    never finished, which the phase machine has already recorded as a technical
    loss — and treating it as a hash mismatch would accuse them of the wrong
    thing.
    """
    runtime = driver.runtime
    config = runtime.orchestrator.config
    seals_scent = bool(config.get("pheromones.seal_scent_digest", False))
    seals_barrier = bool(config.get("movement_and_barriers.seal_barrier_cell", False))
    history = runtime.orchestrator.history

    records = []
    for step in sorted(runtime.commits):
        reveal = runtime.reveals.get(step)
        if reveal is None or step >= len(history):
            continue
        cell = reveal.barrier_cell
        records.append(
            StepRecord(
                step=step,
                claimed_digest=runtime.commits[step],
                # Ours, not theirs: both peers computed this state from the same
                # rules, and it is the field a forger would most want to pick.
                state=sealed_state(history[step]),
                move=reveal.move,
                intent=str(getattr(reveal.intent, "value", reveal.intent)),
                nonce=runtime.opponent_nonces.get(str(step), ""),
                scent_digest=digest(reveal.scent) if seals_scent else None,
                barrier_cell=list(cell) if (seals_barrier and cell) else None,
            )
        )
    return records


async def exchange_and_audit(driver: Any) -> AuditResult:
    """Send every nonce, wait for theirs, and re-hash their whole log.

    Returns:
        The audit of **their** log. `passed` false is a forgery finding, which
        Ch. 5.4 makes a total technical loss for them — but this module reports
        and never sanctions, because deciding what a mismatch costs belongs to
        the rules layer (M#19).

    A peer that never sends its final reveal leaves every step unverifiable,
    which the audit already treats as failure. We do not retry it: the sub-game
    is over, there is nothing left to protect by waiting, and a peer that has
    gone quiet at the audit is exactly the peer a deadline exists for.
    """
    step = driver.state.step
    await driver.client.call(
        "final_reveal", FinalReveal(step=step, role=driver.role, nonces=driver.nonces).payload()
    )
    await driver._await(  # noqa: SLF001 - the driver owns the clock and the tracker
        lambda: bool(driver.runtime.opponent_nonces), "their final reveal", step
    )
    return audit_log(their_records(driver))
