"""Sending and reading one reference-protocol turn.

Module-level functions taking the session rather than methods on it, for the
same reason `core/runtime/turn_plan.py` is a separate file: the coordination
(what we wait for, when we stop) and the mechanics (what a turn *is*) are two
jobs, and together they put one class past the 150-line ceiling ADR-005 sets.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from core.compat import sealing
from core.compat.exchange import Incoming, grid_of, now_iso, sealed_payload, synthetic_reveal
from core.compat.wire import TurnMessage
from core.domain.movement import IllegalMoveError, resolve_move
from core.domain.scent import decay, decode
from core.protocol.schemas import Role
from core.protocol.tools import ProtocolError

# imreeyal §3.13: they read the trail one decay step older than we deposit it,
# rounded to 3 decimals to kill IEEE-754 last-bit noise on the wire. Applied
# here, to the outgoing copy only — `LocalTruth`'s own stored trail must stay
# undecayed-at-centre, or next turn's `deposit()` would age it twice.
_WIRE_DECIMALS = 3

__all__ = ["send_turn", "read_turn", "apply_move"]


def read_turn(session: Any, message: TurnMessage) -> Incoming:
    """Fold their turn into what we know, and answer any claim honestly.

    Raises:
        ProtocolError: *message* claims to be from our own role, or from
            neither role this sub-game holds. Bound from role parity at the
            top, before anything else about the message is trusted — a guard
            re-bound one beat later has rejected a real opener as "unauthorised
            sender" on every even sub-game (imreeyal §3.4).
    """
    theirs = Role.THIEF if session.role is Role.COP else Role.COP
    accepted = {theirs.value, "police"} if theirs is Role.COP else {theirs.value}
    if message.sender not in accepted:
        raise ProtocolError(f"turn message sender {message.sender!r} is not {theirs.value}")
    # What actually arrived, independent of anything the closing audit later
    # claims — this is what a rewritten-and-resealed record is checked against.
    session.received[int(message.step)] = message.commit

    if message.barrier_placed:
        # Their quota, not ours. The cell is blocked for both of us, but
        # `barriers_placed` counts what *we* have spent and inflating it would
        # quietly retire barriers we still hold.
        cell = (int(message.barrier_placed[0]), int(message.barrier_placed[1]))
        state = session.state
        session.orchestrator.advance(replace(state, barriers=state.barriers | {cell}))

    session.runtime.truth.reveals[int(message.step)] = synthetic_reveal(message, theirs)

    outcome = Incoming()
    if message.claim_response and message.claim_response.get("caught"):
        outcome.we_won = True
    if message.win_claim:
        outcome.they_won = True
        outcome.win_type = str(message.win_claim.get("type") or "survival")
    if message.capture_claim:
        claim = (int(message.capture_claim[0]), int(message.capture_claim[1]))
        caught = claim == session.orchestrator.own_position
        outcome.claim_response = {"claim": list(claim), "caught": caught}
        outcome.we_are_caught = caught
    return outcome


async def send_turn(session: Any, owed: dict | None) -> None:
    """Decide, move, seal and push one turn — carrying any answer we owe.

    The move is applied **before** the hint and the scent are produced, so the
    field we transmit is deposited at the cell we actually ended on. Sealing one
    position and advertising a trail from another is the C-008 hole reintroduced
    from the other end, and here it would also make our own claim inconsistent.
    """
    decision = session.runtime.decide()
    position = apply_move(session, decision)
    reveal = session.runtime.reveal_for(decision, session.state.step)
    payload = sealed_payload(
        session.state,
        position,
        int(session.config.require("board_and_agents.grid_size")),
        decision.move.value,
        decision.intent.value,
        reveal.hint,
    )
    record = {"payload": payload, **sealing.seal(payload)}
    session.records.append(record)
    # Per-sender, starting at 1 — not the shared game-progress counter
    # `state.step` advances on either side's move. A single interleaved
    # sequence (ours: 0,2,4...) looks like a reordered stream to a receiver
    # expecting its own counterpart's steps to run 1,2,3... (imreeyal §3.6).
    session.sent += 1
    trail = session.runtime.truth.filter
    wire_field = decay(decode(reveal.scent), trail.rate, trail.model)
    await session.client.call(
        "receive_turn",
        TurnMessage(
            step=session.sent,
            sender=session.role.value,
            hint=reveal.hint,
            smell_grid=grid_of({
                cell: round(value, _WIRE_DECIMALS) for cell, value in wire_field.items()
            }),
            commit=record["commit"],
            timestamp=now_iso(),
            barrier_placed=list(decision.barrier) if decision.barrier else None,
            capture_claim=_claim(session, decision, position),
            claim_response=owed,
            win_claim=_win(session),
        ).to_dict(),
        argument="message",
    )


def apply_move(session: Any, decision: Any) -> tuple[int, int]:
    """Apply our own move to our own half of the board, and return where we are.

    An illegal choice becomes a stand rather than an exception, which is what
    the reference does too: the alternative is losing a sub-game because our own
    brain proposed a step into a wall.
    """
    state = session.state
    if decision.barrier is not None:
        state = state.with_barrier(tuple(decision.barrier))
    try:
        moved = resolve_move(
            session.orchestrator.own_position,
            decision.move,
            state.barriers,
            session.orchestrator.board,
        )
    except IllegalMoveError:
        moved = session.orchestrator.own_position
    changes = {"cop": moved} if session.role is Role.COP else {"thief": moved}
    session.orchestrator.advance(state.advanced(**changes))
    return moved


def _claim(session: Any, decision: Any, position: tuple[int, int]) -> list | None:
    """Return the cell we assert we are on, when we are the Cop.

    The Cop claims **its own** position rather than a guess about theirs: a
    capture is the Cop standing where the Thief stands, so naming our own cell
    asks exactly the right question and the Thief can answer it honestly (M#21).
    """
    if session.role is not Role.COP or decision.move.value == "STAY":
        return None
    return list(position)


def _win(session: Any) -> dict | None:
    """Return the Thief's survival claim once the threshold is reached."""
    if session.role is not Role.THIEF:
        return None
    threshold = int(session.config.require("movement_and_barriers.survival_threshold"))
    return {"type": "survival"} if int(session.state.step) >= threshold else None
