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
from core.compat.wire import TurnMessage, wire_role
from core.domain.actions import Direction
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
    _answer_capture(session, message, outcome)
    return outcome


async def send_turn(session: Any, owed: dict | None, stand: bool = False) -> None:
    """Decide, move, seal and push one turn — carrying any answer we owe.

    The move is applied **before** the hint and the scent are produced, so the
    field we transmit is deposited at the cell we actually ended on. Sealing one
    position and advertising a trail from another is the C-008 hole reintroduced
    from the other end, and here it would also make our own claim inconsistent.

    Args:
        stand: Send without deciding or moving — a concession. Set only when
            they have just caught us.

            🐛 **We must not move.** Their verifier re-checks a capture
            structurally rather than trusting either peer: the cell they claim
            it on must equal the LAST position our own reveal carries. Taking
            one more ordinary turn walks that trail one cell past the capture,
            and they read it as "a capture the thief's own reveal says never
            happened" — `tamper_forfeit`, 0 to BOTH teams (App. E rule 35),
            while our own side keeps reporting "audit passed" throughout,
            because nothing on our side ever re-checks the claim we already
            know is true. Lost once already (16/08) and rediscovered live
            against the kit's own sparring peer (18/08) — see
            `docs/KNOWN_ISSUES.md`.

            **We must still answer.** M#21 makes it a duty, and the wire has no
            channel for it but a turn message. So this is a real turn that goes
            nowhere: STAY, at the cell where we were caught, carrying the
            concession and nothing else.
    """
    if stand:
        decision = replace(session.runtime.decide(), move=Direction.STAY, barrier=None)
        position = session.orchestrator.own_position
    else:
        decision = session.runtime.decide()
        position = apply_move(session, decision)
    reveal = session.runtime.reveal_for(decision, session.state.step)
    # Incremented before the seal, not after: the record must carry the same
    # step number the turn actually travels under (imreeyal §3.6 — per-sender,
    # starting at 1, not the shared game-progress counter `state.step`, which a
    # standing concession leaves unchanged and would duplicate).
    session.sent += 1
    payload = sealed_payload(
        session.state,
        position,
        int(session.config.require("board_and_agents.grid_size")),
        decision.move.value,
        decision.intent.value,
        reveal.hint,
        # Our first record of this sub-game only — the step-0 record their
        # artefact reads the commit column from (M#53). Repeating it on all 35
        # turns would seal the same string 35 times to say one thing once.
        github_commit=str(session.identity.get("github_commit", "")) if session.sent == 1 else "",
        role=wire_role(session.role.value),
        sub_game=session.sub_game_number,
        step=session.sent,
    )
    record = {"payload": payload, **sealing.seal(payload)}
    session.records.append(record)
    trail = session.runtime.truth.filter
    wire_field = decay(decode(reveal.scent), trail.rate, trail.model)
    await session.client.call(
        "receive_turn",
        TurnMessage(
            step=session.sent,
            # `wire_role`, not the raw value. Our vocabulary says "cop"; the
            # reference's says "police", and the greeting already translates
            # (session.py). This did not, so every turn went out labelled from a
            # role the receiver does not know. Harmless until the first barrier,
            # which is checked against the sender's role — the reference then
            # refused with "a barrier arrived from sender 'cop' — only the cop
            # places barriers", a sentence that only parses once you see that
            # 'cop' and "the cop" are two different strings to it. Cost a whole
            # sub-game as a technical loss, eight turns in, against imreeyal's
            # sparring peer.
            sender=wire_role(session.role.value),
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


def _trapped(session: Any) -> Any:
    """Return the barrier capture our own half of the board shows, or None.

    Only the Thief can be trapped, and only the Thief's half of `state` is real
    on this wire — but that is exactly the half this reads. `state.thief` is our
    own cell, and `state.barriers` holds every wall either side has declared,
    because `read_turn` folds theirs in before this runs. The Cop's position,
    which is a fiction in a compat session, is never consulted.
    """
    if session.role is not Role.THIEF:
        return None
    return session.orchestrator.rules.thief_is_trapped(session.state)


def _answer_capture(session: Any, message: Any, outcome: Incoming) -> None:
    """Answer their claim, and concede a barrier capture whether or not they ask.

    🐛 **This asked only `claim == own_position`** and never consulted the rules,
    so the compat path conceded neither M#46 (a wall on our own cell) nor M#47
    (every orthogonal exit blocked). The native path at least asked — it answers
    `on_capture_claim` from `rules.verdict` — but that entry point did not know
    M#46 either until `thief_is_trapped` existed, so wiring this one to it
    unchanged would have fixed the rarer of the two. imreeyal's cop caged our thief in
    the corner (6,0) on 16/08: walls at (5,0) and (6,1) by step 20, the other two
    sides being board edge. We sat there for the final 15 turns and filed a
    survival. Their settlement layer derived the capture from our own revealed
    trail, and the series was 60-40 to them rather than the 47-47 both files say.

    The concession rides on ``claim_response.caught`` because that is the only
    channel this wire has for it — a reference peer reads that field as *"they
    admit I won"*. So it is sent even when no claim arrived, which is the normal
    case: placing a barrier costs the Cop its move, and `_claim` correctly stays
    silent on a STAY, so nobody ever asks the turn the cage closes.
    """
    trapped = _trapped(session)
    if not message.capture_claim and trapped is None:
        return
    claim = (
        (int(message.capture_claim[0]), int(message.capture_claim[1]))
        if message.capture_claim
        else session.orchestrator.own_position
    )
    caught = claim == session.orchestrator.own_position or trapped is not None
    outcome.claim_response = {"claim": list(claim), "caught": caught}
    if caught:
        # Which rule ended it. Additive, and a conformant peer drops what it
        # does not know — but a capture we conceded without being asked is
        # otherwise indistinguishable from one we mis-answered.
        outcome.claim_response["rule"] = trapped.reason if trapped else "cop occupies our cell"
    outcome.we_are_caught = caught


def _win(session: Any) -> dict | None:
    """Return the Thief's survival claim once the threshold is reached."""
    if session.role is not Role.THIEF:
        return None
    threshold = int(session.config.require("movement_and_barriers.survival_threshold"))
    return {"type": "survival"} if int(session.state.step) >= threshold else None
