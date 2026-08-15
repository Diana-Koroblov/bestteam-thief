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

* **An agreement stamped for a sub-game that is not ours is skipped, never
  refused.** It is the opponent being somewhere else in the series, which is
  normal in an alternating split, not a disagreement about the game. Refusing
  it is how the deadlock above starts. This mirrors `session.collect_audit`,
  which already skips an audit stamped with an earlier sub-game for exactly the
  same reason.
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


async def push_agreement(client: Any, message: dict, seconds: float) -> None:
    """Send our agreement, retrying while the opponent is still starting up.

    Only a **transport** failure is retried. Peers legitimately start seconds
    apart, and the native path gives the same courtesy in `cli_handshake.greet`.
    A refusal on the merits is not retryable and is not raised here at all — it
    comes back later, as their agreement failing to verify.
    """
    from core.infra.errors import TransportError

    deadline = time.monotonic() + seconds
    while True:
        try:
            await client.call("negotiate", message, argument="message")
            return
        except TransportError:
            if time.monotonic() >= deadline:
                raise
            print(f"  no answer yet; retrying for {deadline - time.monotonic():.0f}s more ...")
            await asyncio.sleep(PUSH_RETRY_SECONDS)


async def collect_our_agreement(session: Any, wait: float, ours: dict) -> dict:
    """Return the opponent's agreement **for this sub-game**, skipping others.

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
) -> dict:
    """Push our agreement and wait for theirs, re-sending until our turn comes.

    Returns their agreement. Raises `AgreementTimeoutError` if *total_wait* passes
    with nothing for this sub-game, or `HandshakeError` the moment something
    arrives for this sub-game that does not verify — the second is fatal at
    once rather than retried, because repeating an exchange cannot make two
    different contracts agree.
    """
    deadline = time.monotonic() + total_wait
    waited = False
    while True:
        await push_agreement(client, message, push_wait)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AgreementTimeoutError("the opponent never sent its agreement")
        try:
            return await collect_our_agreement(session, min(repush_every, remaining), message)
        except AgreementTimeoutError:
            if time.monotonic() >= deadline:
                raise
            if not waited:
                announce(
                    f"  sub-game {session.sub_game_number}  waiting for the opponent to "
                    f"reach it (up to {total_wait:.0f}s), re-sending our agreement ..."
                )
                waited = True
