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
    """Just the one queue the waiter reads."""

    agreements: queue.Queue = field(default_factory=queue.Queue)


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

    async def counting_push(cl: Any, msg: dict, seconds: float) -> None:
        await original(cl, msg, seconds)
        await arrive_late()

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
