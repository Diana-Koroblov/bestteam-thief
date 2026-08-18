"""Waiting for our turn to come round, instead of racing ahead into theirs.

Split from `cli_compat.py` and `session.py` under the 150-line ceiling
(ADR-005), along the seam `pairing.py` already sits on: those two own *what a
sub-game does*, this owns *when we are allowed to start one*.

**The problem this exists for.** A role-split that is not contiguous — the
alternating `1-1-1-1-1-1` some opponents' playbooks assume — gives each of our
two processes a plan with gaps in it: the cop holds `[1, 3, 5]`. The series
loop advanced to the next entry the moment the previous one ended, so the cop
pushed an agreement stamped sub-game 3 while the opponent was still playing
sub-game 2 against our *thief*. Their pairing guard reads 3 against its own 2,
refuses it as a sub-game mismatch and drops it. When they finally reach 3 and
send theirs, we accept it happily — and they are still waiting for ours, which
they discarded. Both sides then sit until the watchdog, and a sub-game nobody
played wrong is a technical loss worth 0 to both teams (M#35).

Two rules follow, and both are here:

* **An agreement stamped for a sub-game that is not ours is held, never refused
  and never discarded.** It is the opponent being somewhere else in the series,
  which is normal in an alternating split, not a disagreement about the game.
  Refusing it is how the deadlock above starts.

  🐛 *Skipping* it was only half a fix, and the drill on 16/08 caught the other
  half: the message was taken off the queue and dropped on the floor. A peer
  ahead of us pushes its sub-game 2 agreement while we are still playing
  sub-game 1 — that push is not noise, it is precisely the message we will need
  forty seconds later — and we threw it away, then waited for a repeat. Our own
  peers survive it because `await_agreement` re-sends every 30 s; an opponent
  that pushes **once**, which the reference runner does, is deadlocked by it.
  So it goes into `Inboxes.held`, keyed by the sub-game it names, and is the
  first thing looked at when we reach that sub-game.
* **Our own agreement is re-sent while we wait.** One push is not enough when
  the peer may legitimately drop it for being early: the message that mattered
  is the one they were ready to receive, and only a repeat gets it there.

**Waiting is measured in sub-games, not seconds.** A process whose turn is two
sub-games away is idle for however long the opponent takes to play them —
thirty-five steps each, plus, for a peer that starts a fresh process per
sub-game, its own rebind window. That is minutes, not the 120 s the handshake
courtesy in `cli_handshake.greet` was sized for, so it gets its own budget.
"""

from __future__ import annotations

import asyncio
import queue
import time
from contextlib import suppress
from typing import Any

from core.compat.pairing import HandshakeError, verify_agreement

__all__ = [
    "AgreementTimeoutError",
    "POLL_SECONDS",
    "PUSH_RETRY_SECONDS",
    "REPUSH_SECONDS",
    "TURN_WAIT_SECONDS",
    "await_agreement",
    "collect_our_agreement",
    "push_agreement",
    "push_audit",
]

# How long to yield between inbox polls. Long enough not to spin a core, short
# enough to be invisible inside a step deadline.
POLL_SECONDS = 0.05

# Gap between attempts while the opponent's server is simply not up yet.
PUSH_RETRY_SECONDS = 3.0

# How often to re-send our agreement while waiting for our turn. Far enough
# apart to be negligible against the tunnel's request budget — a whole sub-game
# of waiting costs a handful of messages, against the ~70 a sub-game itself
# spends — and close enough that we are never the reason a turn starts late.
REPUSH_SECONDS = 30.0

# Total time to wait for the opponent to reach *our* sub-game. Sized for the
# worst honest case rather than the typical one: two of their sub-games back to
# back at 35 steps each, plus a process rebind between each, is several minutes
# and nothing has gone wrong. A peer that has genuinely died costs us this long
# to notice, which is the right trade — declaring a technical loss on a slow
# opponent who was about to answer forfeits a sub-game we had not lost.
TURN_WAIT_SECONDS = 900.0


class AgreementTimeoutError(HandshakeError):
    """Nothing arrived in the window — as distinct from something unacceptable.

    A `HandshakeError` subclass so every existing caller still catches it, but
    its own type because the two demand opposite responses: a verification
    failure must not be retried (their terms really do differ, and repeating the
    exchange cannot change that), while silence *should* be, because the peer
    may simply not have got here yet.
    """


async def push_agreement(
    client: Any, message: dict, seconds: float, redial: Any = None
) -> Any:
    """Send our agreement, retrying while the opponent is still starting up.

    Returns the client the push finally succeeded on — which is **not** always
    the one passed in, and callers must keep it.

    A **transport** failure is retried, and so is a **structured refusal that
    names itself transient** — a peer answering synchronously rather than
    holding us silently still means "not yet," not "no." A refusal that is
    actually about the merits (wrong terms, unauthorised sender) keeps
    refusing on every retry and still surfaces once the budget runs out; the
    cost of trying is a few extra seconds, not a wrong verdict.

    🐛 **A single-process peer that answers negotiate synchronously was
    indistinguishable from one that refuses on the merits.** Two of our own
    processes hold an out-of-turn agreement and never answer it at all
    (`Inboxes.held`); yanell11's one peer instead replies at once with
    `'negotiate' was rejected by the opponent: sub-game 2 has not started on
    this peer yet ... retry when it does` — and the OLD code treated every
    `RemoteToolError` as final, so our thief abandoned sub-games 2, 4 and 6 in
    the same second it opened them, never once retrying, while their own peer
    was still finishing sub-game 1 exactly as its message said (18/08).

    🐛 **Every retry used to reuse the dead socket.** Against a peer that starts
    a fresh process per sub-game — the reference runner does — the session dies
    the instant they rebind, so every retry failed for the one reason retrying
    could never fix, and the loop ran its whole budget out before raising. Live
    against imreeyal on 16/08: sub-game 1 settled clean, then our thief printed
    `no answer yet; retrying` until the window died. *Their door was healthy the
    whole time.* So `redial` is called between attempts, and a redial that fails
    is itself just another thing to retry — the peer may still be down.
    """
    from core.infra.errors import RemoteToolError, TransportError

    deadline = time.monotonic() + seconds
    while True:
        try:
            await client.call("negotiate", message, argument="message")
            return client
        except (TransportError, RemoteToolError):
            if time.monotonic() >= deadline:
                raise
            print(f"  no answer yet; retrying for {deadline - time.monotonic():.0f}s more ...")
            await asyncio.sleep(PUSH_RETRY_SECONDS)
            if redial is not None:
                with suppress(Exception):
                    client = await redial()


async def push_audit(opponent: Any, payload: dict, redial: Any) -> tuple[bool, list[str]]:
    """Push our audit payload, retrying once after a redial. Returns (landed, notes).

    The peer that just won may exit the moment it has read its inbox, killing
    its server mid-response, so the client this sub-game's last turn left us
    with can easily be a corpse by the time we reach this call — same as
    `push_agreement` above, and for the same reason. A silently swallowed
    failure here reads on their side as "AUDIT SKIPPED" while our own log
    shows nothing wrong at all (najamjad, 17/08) — this is the fix and the
    visibility both.
    """
    from core.infra.errors import PeerError

    notes: list[str] = []
    for attempt in range(2):
        try:
            if attempt:
                opponent = await redial()
            await opponent.call("submit_audit", payload, argument="payload")
            return True, notes
        except PeerError as error:
            notes.append(f"outbound submit_audit attempt {attempt + 1} failed: {error}")
    notes.append("outbound submit_audit never landed - their audit of us will read as skipped")
    return False, notes


async def collect_our_agreement(session: Any, wait: float, ours: dict) -> dict:
    """Return the opponent's agreement **for this sub-game**, holding others.

    Looks in `Inboxes.held` before the queue: under an alternating split their
    agreement for our sub-game routinely arrives while we are still playing the
    previous one, so by the time we ask for it the queue is the wrong place to
    look — see the module docstring for the deadlock that caused.

    Args:
        session: The `ReferenceSession` whose `sub_game_number` decides which
            agreement is ours and whose `warnings` collects the declared
            divergences the pairing guard logs rather than refuses.
        wait: Seconds to poll before giving up.
        ours: The full agreement MESSAGE we sent, not the bare terms — the
            pairing guard reads `sub_game_number`, `role` and the model hashes
            off it, and handing it only the terms leaves our side of every one
            of those checks permanently silent (`core/compat/pairing.py`).

    Raises:
        AgreementTimeoutError: Nothing for us arrived inside *wait*.
        HandshakeError: Something arrived for this sub-game and was not
            acceptable. Deliberately still fatal — two peers enforcing
            different physics produce an audit that reports forgery against two
            honest teams (M#11).
    """
    held = session.inboxes.held.pop(session.sub_game_number, None)
    if held is not None:
        session.warnings.extend(verify_agreement(ours, held))
        return held
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        try:
            theirs = session.inboxes.agreements.get_nowait()
        except queue.Empty:
            await asyncio.sleep(POLL_SECONDS)
            continue
        stamped = theirs.get("sub_game_number")
        if isinstance(stamped, int) and session.sub_game_number and (
            stamped != session.sub_game_number
        ):
            # Them, elsewhere in the series. Normal under an alternating split.
            session.inboxes.held[stamped] = theirs
            continue
        session.warnings.extend(verify_agreement(ours, theirs))
        return theirs
    raise AgreementTimeoutError("the opponent never sent its agreement")


async def await_agreement(
    session: Any,
    client: Any,
    message: dict,
    total_wait: float = TURN_WAIT_SECONDS,
    push_wait: float = 120.0,
    repush_every: float = REPUSH_SECONDS,
    announce: Any = print,
    redial: Any = None,
) -> dict:
    """Push our agreement and wait for theirs, re-sending until our turn comes.

    Args:
        redial: Awaited to get a fresh client when the current one stops
            answering, and passed on to every retry inside `push_agreement`.
            **Required in practice against a peer that restarts per sub-game**:
            this loop legitimately runs for minutes, and the socket it started
            with does not survive that. Optional only so the unit tests can
            drive the loop without a transport (M#3 — this module must not
            import one).

    Returns their agreement. Raises `AgreementTimeoutError` if *total_wait*
    passes with nothing for this sub-game, or `HandshakeError` the moment
    something arrives for this sub-game that does not verify — the second is
    fatal at once rather than retried, because repeating an exchange cannot
    make two different contracts agree.
    """
    deadline = time.monotonic() + total_wait
    waited = False
    while True:
        client = await push_agreement(client, message, push_wait, redial=redial)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AgreementTimeoutError("the opponent never sent its agreement")
        try:
            theirs = await collect_our_agreement(session, min(repush_every, remaining), message)
            # 🐛 **A push that succeeded is not a push that arrived anywhere
            # useful.** Against a peer that runs one process per sub-game, ours
            # routinely lands in the PREDECESSOR — the process still finishing
            # the previous sub-game against our other role — moments before it
            # exits, taking our agreement with it. Nothing looks wrong from
            # here: the call returned, so we stop re-sending, and their next
            # process starts with an empty inbox and waits for a message it
            # will never get. Their agreement is the first hard evidence that
            # the process which will actually PLAY our sub-game is alive, so
            # that is the moment to send ours — once more, on a fresh socket.
            #
            # Best-effort: they may already hold ours, and a duplicate is
            # harmless (their mailbox queues it and the handshake takes one).
            # A failure here must not lose a sub-game we have just agreed.
            if redial is not None:
                with suppress(Exception):
                    client = await redial()
            with suppress(Exception):
                await push_agreement(client, message, 0.0)
            return theirs
        except AgreementTimeoutError:
            if time.monotonic() >= deadline:
                raise
            if not waited:
                announce(
                    f"  sub-game {session.sub_game_number}  waiting for the opponent to "
                    f"reach it (up to {total_wait:.0f}s), re-sending our agreement ..."
                )
                waited = True
