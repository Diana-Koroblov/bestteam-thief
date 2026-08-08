"""Playing an actual turn against an actual opponent (TODO 9.4, M#4-M#6).

Everything else in this project was built for this file and then waited for it.
`PeerRuntime` is the **receiving** half — what an opponent is allowed to do to
us; this is the **acting** half: decide, seal, send, wait, resolve, record.

**The ordering is the protocol, not an implementation detail.** One turn goes:

    commit ─► await theirs ─► reveal ─► await theirs ─► resolve

We send our reveal only after their commit has arrived. Reversing those two
would let an opponent read our move and *then* choose theirs, which is the one
failure commit-reveal exists to prevent (Ch. 5.3.1) — and it would be invisible
in a green test run, because a cooperative opponent never exploits it.

**Who knows what.** The runtime tracks the full board, because it must: M#13
makes each peer the enforcer of the other's physics, and a move cannot be
checked for legality against a position you do not hold. The *brain* is shown
strictly less — `LocalTruth.observe` hides the opponent's position and hands
over a belief map instead — and the GUI shows less again (M#8, M#9). Three
layers, narrowing; the Dec-POMDP fog is enforced where the decisions are made,
not by keeping the referee ignorant, because there is no referee.

**Every wait is bounded.** A peer that blocks forever on a message that will
never arrive takes the opponent down with it and the match ends with no result
for either side — the one outcome nobody can appeal (Ch. 8.4). So each wait
carries a deadline, and expiry ends the sub-game through the phase machine
rather than by hanging.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from core.domain.barriers import BarrierManager
from core.domain.game_state import GameState
from core.domain.rules import Outcome, Rules
from core.domain.turn import IllegalMoveError, resolve_turn
from core.infra.errors import PeerError
from core.protocol.schemas import BarrierDeclaration, CaptureClaim, Commit, Reveal, Role
from core.runtime.deadline_tracker import DeadlineTracker
from core.runtime.phase_machine import Phase, PhaseMachine
from core.runtime.turn_decode import decision_of
from core.runtime.turn_plan import Planned, log_entry, plan_turn

__all__ = ["MatchDriver", "TurnRecord"]

# How long to yield between polls of what the server has received. Zero would
# spin the event loop hot; a long sleep would add its own latency to every turn
# inside the 30 s response budget.
POLL_SECONDS = 0.005


@dataclass
class TurnRecord:
    """One completed turn, from our side.

    Attributes:
        step: The turn number, matching the sealed state.
        entry: The log line, ready for `build_log` once nonces are released.
        nonce: Held back until the final reveal (M#18).
    """

    step: int
    entry: dict[str, Any]
    nonce: str


@dataclass
class MatchDriver:
    """Drives one peer through one sub-game against one opponent.

    Attributes:
        runtime: Our receiving half. Owns the orchestrator and the brain.
        client: The single opponent (M#4).
        barriers: The quota, spent through `resolve_turn`.
        phases: The state machine every turn passes through (M#4, M#5).
        deadlines: Bounds every wait (M#6).
        records: One `TurnRecord` per completed turn.
        reason: Why the sub-game ended, in words, for the log and the report.
        outcome: The same ending as a verdict the scoring table can price.
            ``None`` until the sub-game ends. Kept beside `reason` rather than
            parsed back out of it: a series is scored from these, and deriving a
            verdict by matching words in a sentence is how a capture becomes a
            survival the day someone rewords a message.
    """

    runtime: Any
    client: Any
    barriers: BarrierManager
    phases: PhaseMachine = field(default_factory=PhaseMachine)
    deadlines: DeadlineTracker = field(default_factory=DeadlineTracker)
    records: list[TurnRecord] = field(default_factory=list)
    reason: str = ""
    outcome: Outcome | None = None
    clock: Any = time.monotonic

    @property
    def role(self) -> Role:
        """Which side we play this sub-game."""
        return self.runtime.own_role

    @property
    def state(self) -> GameState:
        """The board as we hold it."""
        return self.runtime.orchestrator.state

    @property
    def nonces(self) -> dict[str, str]:
        """Step to nonce, for the final reveal (M#18)."""
        return {str(record.step): record.nonce for record in self.records}

    async def play_sub_game(self, max_turns: int = 1000) -> str:
        """Play to a terminal verdict and return the reason it ended.

        Args:
            max_turns: A backstop only. The negotiated `max_moves` ends a
                sub-game long before this; a loop with no bound at all is how a
                rules bug becomes a hang instead of a failed test.

        Never raises on an opponent's failure. A dropped peer, an illegal move
        or a refused message is a **result** — a technical loss, recorded — and
        a traceback here would lose the log that proves whose fault it was.
        """
        for _ in range(max_turns):
            try:
                if await self._turn():
                    return self.reason
            except PeerError as error:
                return self._fail(f"opponent unreachable: {error}")
            except IllegalMoveError as error:
                return self._fail(str(error))
        return self._fail(f"no verdict after {max_turns} turns")

    async def _turn(self) -> bool:
        """Play one full turn. Returns True when the sub-game ended."""
        step = self.state.step
        self.phases.to(Phase.COMPUTING_MOVE)
        plan = plan_turn(self.runtime, step)

        self.phases.to(Phase.COMMITTING)
        await self.client.call(
            "receive_commit", Commit(step, self.role, plan.sealed.digest).payload()
        )
        if not await self._await(lambda: step in self.runtime.commits, "their commit", step):
            return True

        self.phases.to(Phase.AWAITING_REVEAL)
        await self._reveal(plan, step)
        if not await self._await(lambda: step in self.runtime.reveals, "their reveal", step):
            return True

        self.phases.to(Phase.VERIFYING)
        return await self._resolve(plan, step)

    async def _reveal(self, plan: Planned, step: int) -> None:
        """Send the move, the hint and the field — and declare any placement.

        The barrier is declared as its own message as well as riding on the
        reveal. M#15 makes the declaration a duty in its own right, and a peer
        that only implemented `receive_reveal` would still be owed one.
        """
        await self.client.call("receive_reveal", plan.reveal.payload())
        if plan.decision.barrier is not None:
            await self.client.call(
                "declare_barrier",
                BarrierDeclaration(
                    step=step,
                    role=self.role,
                    cell=plan.decision.barrier,
                    remaining=self.barriers.remaining,
                ).payload(),
            )

    async def _resolve(self, plan: Planned, step: int) -> bool:
        """Apply both decisions, record the turn, and report whether it ended."""
        theirs: Reveal = self.runtime.reveals[step]
        ours = plan.decision
        cop, thief = (
            (ours, decision_of(theirs)) if self.role is Role.COP else (decision_of(theirs), ours)
        )
        turn = resolve_turn(
            self.state, cop, thief, self.barriers, self.runtime.orchestrator.rules, strict=True
        )
        self.runtime.orchestrator.advance(turn.state)
        self.records.append(
            TurnRecord(step=step, entry=log_entry(plan, step), nonce=plan.sealed.nonce)
        )

        if turn.outcome is None:
            self.phases.to(Phase.WAITING_FOR_OPPONENT)
            return False
        await self._claim_capture(turn, step)
        self.outcome = turn.outcome
        self.reason = turn.outcome.reason
        self.phases.to(Phase.COMPLETE)
        return True

    async def _claim_capture(self, turn: Any, step: int) -> None:
        """Assert a capture and record their answer (M#21, M#22).

        Only the Cop claims, and it claims even though both peers computed the
        same verdict from the same rules. The claim is not how a capture is
        *discovered* — it is the signed, obliged answer that makes the verdict
        evidence rather than an assertion, and the thief's reply is what the
        audit reads if the result is later disputed.
        """
        if self.role is not Role.COP or "capture" not in turn.outcome.reason.lower():
            return
        await self.client.call(
            "capture_claim",
            CaptureClaim(
                step=step, role=self.role, cell=turn.state.thief, rule=turn.outcome.reason
            ).payload(),
        )

    async def _await(self, arrived, label: str, step: int) -> bool:
        """Wait for *arrived* to become true, bounded. False means we gave up.

        The one retry the tracker allows is deliberately **not** a re-send here:
        what we are waiting on is a message the opponent must push to our
        server, so there is nothing of ours to send again. The second expiry
        ends the sub-game, which is exactly what M#6 asks for.
        """
        self.deadlines.start(f"{label} for step {step}", self.clock())
        while not arrived():
            verdict = self.deadlines.check(self.clock())
            if verdict == "technical_loss":
                self._fail(f"{label} for step {step} never arrived")
                return False
            if verdict == "retry":
                self.deadlines.retry(self.clock())
            await asyncio.sleep(POLL_SECONDS)
        self.deadlines.resolve()
        return True

    def _fail(self, reason: str) -> str:
        """End the sub-game in a recorded technical loss (M#4).

        The **first** failure is the one kept. A sub-game that timed out and
        then failed its closing exchange failed once, for the first reason;
        overwriting it would leave the report naming the consequence instead of
        the cause. `PhaseMachine.fail` is already a no-op once terminal, for the
        same reason.
        """
        if self.outcome is None:
            self.reason = reason
            self.outcome = Rules.technical_loss(reason)
        self.phases.fail(reason)
        return self.reason
