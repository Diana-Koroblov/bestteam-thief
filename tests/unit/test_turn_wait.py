"""Waiting for our turn instead of racing into the opponent's (C-011).

The deadlock these guard against, concretely: under an alternating split our
cop holds sub-games `[1, 3, 5]`, so the instant sub-game 1 ends it opened 3
while the opponent was still playing 2 against our thief. They dropped our
early agreement as a sub-game mismatch, we accepted theirs when it finally
came, and they went on waiting for a message they had already discarded.
"""

from __future__ import annotations

import queue
from dataclasses import dataclass, field
from typing import Any

import pytest

from core.compat.turn_wait import (
    AgreementTimeoutError,
    await_agreement,
    collect_our_agreement,
)


@dataclass
class _Inboxes:
    """The one queue the waiter reads, and the shelf it puts the rest on."""

    agreements: queue.Queue = field(default_factory=queue.Queue)
    held: dict = field(default_factory=dict)


@dataclass
class _Session:
    """The two attributes `turn_wait` touches, and nothing else."""

    sub_game_number: int
    inboxes: _Inboxes = field(default_factory=_Inboxes)
    warnings: list = field(default_factory=list)


@dataclass
class _Client:
    """Counts pushes so a test can prove we re-sent."""

    pushes: list = field(default_factory=list)

    async def call(self, tool: str, message: dict, argument: str = "") -> dict:
        self.pushes.append((tool, message.get("sub_game_number")))
        return {"ok": True}


def _agreement(number: int | None) -> dict:
    """An inbound agreement stamped for sub-game *number*."""
    return {"sub_game_number": number, "terms": {}, "nonce": "n", "signature": "s"}


@pytest.fixture(autouse=True)
def _no_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    """Accept whatever arrives — signature checking is `test_compat_pairing`'s job."""
    monkeypatch.setattr("core.compat.turn_wait.verify_agreement", lambda ours, theirs: [])


async def test_an_agreement_for_our_sub_game_is_returned() -> None:
    """The ordinary case: they are where we are."""
    session = _Session(sub_game_number=3)
    session.inboxes.agreements.put(_agreement(3))

    assert await collect_our_agreement(session, 1.0, {}) == _agreement(3)


async def test_an_agreement_for_another_sub_game_is_skipped_not_refused() -> None:
    """**The deadlock, in one assertion.**

    Their sub-game 2 agreement arriving while we hold 3 is the opponent being
    elsewhere in the series, not a disagreement about the game. Refusing it is
    what used to strand both peers.
    """
    session = _Session(sub_game_number=3)
    session.inboxes.agreements.put(_agreement(2))
    session.inboxes.agreements.put(_agreement(3))

    assert (await collect_our_agreement(session, 1.0, {}))["sub_game_number"] == 3


async def test_an_agreement_we_are_not_ready_for_is_kept_not_thrown_away() -> None:
    """🐛 **Skipping it was only half the fix**, and the half that was missing is
    the one that cost two match windows.

    The message was taken off the queue and dropped. Against our own peers that
    is survivable, because `await_agreement` re-sends every 30 s — so every test
    above passed and the drill passed too, as long as both sides were ours. An
    opponent that pushes its agreement **once**, which the reference runner
    does, is deadlocked outright: it sends the sub-game 2 agreement while we are
    still playing 1, we bin it, and then both sides wait forever for a message
    that was already delivered.

    Caught by `scripts/drill_answering_path.py` on 16/08, not by this file —
    which is the argument for the drill existing.
    """
    inboxes = _Inboxes()
    early = _Session(sub_game_number=1, inboxes=inboxes)
    early.inboxes.agreements.put(_agreement(2))
    with pytest.raises(AgreementTimeoutError):
        await collect_our_agreement(early, 0.15, {})

    assert inboxes.held == {2: _agreement(2)}, "an early agreement must survive the wait"

    # ...and is found when we get there, with nothing further arriving.
    later = _Session(sub_game_number=2, inboxes=inboxes)
    assert (await collect_our_agreement(later, 0.0, {}))["sub_game_number"] == 2
    assert inboxes.held == {}, "taken off the shelf, not left to be re-read"


async def test_silence_raises_the_timeout_type_not_a_bare_refusal() -> None:
    """The caller retries silence and never retries a refusal, so they differ."""
    with pytest.raises(AgreementTimeoutError):
        await collect_our_agreement(_Session(sub_game_number=1), 0.15, {})


async def test_an_unstamped_agreement_is_accepted() -> None:
    """A peer that never stamps sub-games is not thereby unplayable.

    Omission is silence, not disagreement — the same rule `pairing_warnings`
    applies to every other declared field.
    """
    session = _Session(sub_game_number=4)
    session.inboxes.agreements.put(_agreement(None))

    assert await collect_our_agreement(session, 1.0, {}) is not None


async def test_our_agreement_is_re_sent_while_we_wait() -> None:
    """One push is not enough when the peer legitimately drops an early one.

    The opponent arrives at our sub-game only after our first push has already
    been discarded, so the exchange completes solely because we sent it again.
    """
    session = _Session(sub_game_number=5)
    client = _Client()

    async def arrive_late(*_args: Any, **_kwargs: Any) -> None:
        """Drop it in only once we have pushed twice."""
        if len(client.pushes) >= 2:
            session.inboxes.agreements.put(_agreement(5))

    import core.compat.turn_wait as module

    original = module.push_agreement

    async def counting_push(cl: Any, msg: dict, seconds: float, **kwargs: Any) -> Any:
        live = await original(cl, msg, seconds, **kwargs)
        await arrive_late()
        return live

    module.push_agreement = counting_push
    try:
        theirs = await await_agreement(
            session, client, {"sub_game_number": 5}, total_wait=5.0,
            repush_every=0.1, announce=lambda _line: None,
        )
    finally:
        module.push_agreement = original

    assert theirs["sub_game_number"] == 5
    assert len(client.pushes) >= 2, "we must re-send, not push once and hope"


async def test_a_dead_socket_is_redialled_rather_than_retried_forever() -> None:
    """🐛 **The retry that could never work**, live against imreeyal on 16/08.

    Their runner starts a fresh process per sub-game, so the session we hold
    dies the moment they rebind — and every retry reused that same dead client.
    The loop printed `no answer yet; retrying` for its entire budget and then
    raised, while their door was healthy throughout. Sub-game 1 settled clean
    and sub-game 2 never engaged, twice over.

    Here the first client refuses everything, as a dead session does, and the
    exchange can only complete if the waiter asks for a new one.
    """
    from core.infra.errors import TransportError

    class _Dead:
        async def call(self, *_args: Any, **_kwargs: Any) -> dict:
            raise TransportError("session terminated")

    session = _Session(sub_game_number=2)
    live = _Client()

    async def redial() -> Any:
        session.inboxes.agreements.put(_agreement(2))
        return live

    theirs = await await_agreement(
        session, _Dead(), {"sub_game_number": 2}, total_wait=5.0, push_wait=2.0,
        repush_every=0.1, announce=lambda _line: None, redial=redial,
    )

    assert theirs["sub_game_number"] == 2
    assert live.pushes, "the fresh client must be the one we go on to push with"


async def test_the_total_budget_is_honoured_when_nobody_answers() -> None:
    """A peer that never arrives costs us the budget and then reports it."""
    session = _Session(sub_game_number=2)

    with pytest.raises(AgreementTimeoutError):
        await await_agreement(
            session, _Client(), {}, total_wait=0.3, repush_every=0.1,
            announce=lambda _line: None,
        )


def test_the_default_budget_spans_more_than_one_sub_game() -> None:
    """Sized in sub-games, not in handshake seconds.

    A waiting process idles through whole opponent sub-games plus, for a peer
    that restarts per sub-game, its rebind window. The 120 s handshake courtesy
    would call that a dead opponent.
    """
    from core.compat.turn_wait import TURN_WAIT_SECONDS

    assert TURN_WAIT_SECONDS >= 600.0
