"""The four-phase exchange (TODO 6.2, M#17-M#22).

This is what makes simultaneous movement possible over a network where somebody
has to send first. The tests are written from the attacker's side: for each
phase, what would a peer gain by skipping or repeating it?
"""

from __future__ import annotations

import pytest

from core.protocol.four_phase import ProtocolError, Stage, TurnExchange

MOVE = {"move": "N", "hint": "Heading north, catch me.", "intent": "truth"}


def _both_committed(step: int = 1) -> TurnExchange:
    exchange = TurnExchange(step=step)
    exchange.commit("us", "aaa")
    exchange.commit("them", "bbb")
    return exchange


def _both_acked(step: int = 1) -> TurnExchange:
    exchange = _both_committed(step)
    exchange.acknowledge("us")
    exchange.acknowledge("them")
    return exchange


def test_a_clean_turn_runs_through_all_four_stages() -> None:
    exchange = TurnExchange(step=1)
    assert exchange.commit("us", "aaa") is Stage.AWAITING_COMMITS
    assert exchange.commit("them", "bbb") is Stage.AWAITING_ACKS
    assert exchange.acknowledge("us") is Stage.AWAITING_ACKS
    assert exchange.acknowledge("them") is Stage.AWAITING_REVEALS
    assert exchange.reveal("us", MOVE) is Stage.AWAITING_REVEALS
    assert exchange.reveal("them", MOVE) is Stage.SETTLED
    assert exchange.settled


# --- phase 1: the commit protects whoever sends first -----------------------


def test_committing_twice_is_refused() -> None:
    """**The exact behaviour the hash exists to prevent.**

    A second commit is an attempt to change a move after seeing something.
    """
    exchange = TurnExchange(step=1)
    exchange.commit("us", "aaa")
    with pytest.raises(ProtocolError, match="already committed"):
        exchange.commit("us", "ccc")


def test_going_first_reveals_nothing() -> None:
    """Only a digest travels in phase 1 — no move, no hint, no intent.

    This is what makes it safe to be the peer who sends first, which somebody
    always has to be.
    """
    exchange = TurnExchange(step=1)
    exchange.commit("us", "aaa")
    assert exchange.reveals == {}
    assert set(exchange.commits) == {"us"}


# --- phase 2: the ack is what makes revealing safe --------------------------


def test_acking_before_both_commits_is_refused() -> None:
    """Acking early would claim to hold a commitment that has not arrived."""
    exchange = TurnExchange(step=1)
    exchange.commit("us", "aaa")
    with pytest.raises(ProtocolError, match="before both commits"):
        exchange.acknowledge("us")


def test_revealing_before_both_acks_is_refused() -> None:
    """**The attack the ack phase exists to stop.**

    Revealing to an opponent who has not confirmed they are locked in hands
    them our move while they are still free to choose theirs.
    """
    exchange = _both_committed()
    exchange.acknowledge("us")
    with pytest.raises(ProtocolError, match="revealed during"):
        exchange.reveal("us", MOVE)


def test_a_repeated_ack_does_not_advance_the_stage() -> None:
    """One peer acking twice must not stand in for the other peer acking once."""
    exchange = _both_committed()
    exchange.acknowledge("us")
    exchange.acknowledge("us")
    assert exchange.stage is Stage.AWAITING_ACKS


# --- phase 3: the nonce is withheld -----------------------------------------


def test_a_reveal_carrying_a_nonce_is_refused() -> None:
    """**M#18, and this guards our own code more than the opponent's.**

    Leaking the nonce per turn would quietly dismantle the end-of-match audit
    while every other test still passed — the moves would all verify, just a
    turn too early to be worth anything.
    """
    exchange = _both_acked()
    with pytest.raises(ProtocolError, match="nonce"):
        exchange.reveal("us", {**MOVE, "nonce": "deadbeef"})


def test_the_move_is_usable_before_it_is_verifiable() -> None:
    """Deliberate: act on the move now, verify the whole log at the end.

    Per-turn verification sounds better and is worse — a peer that verified
    turn 4 and disliked the result could abandon the match before turn 5.
    """
    exchange = _both_acked()
    exchange.reveal("them", MOVE)
    assert exchange.reveals["them"]["move"] == "N"
    assert "nonce" not in exchange.reveals["them"]


def test_committing_after_the_reveal_stage_is_refused() -> None:
    """No going back to an earlier phase to try a different move.

    Note which guard fires: **"already committed", not "wrong stage"**. Both
    would refuse, and the first is the more useful message — it names what the
    caller actually did wrong rather than merely where they were. The stage
    guard is the backstop, exercised below with a side that has not committed.
    """
    exchange = _both_acked()
    with pytest.raises(ProtocolError, match="already committed"):
        exchange.commit("us", "ccc")


def test_a_late_first_commit_is_refused_by_the_stage_guard() -> None:
    """The backstop: an unknown side trying to join a turn already in progress.

    Not reachable in a two-peer match, which is exactly why it is tested — a
    guard that only ever fires in situations we imagined is a guard we cannot
    trust when something unimagined happens.
    """
    exchange = _both_acked()
    with pytest.raises(ProtocolError, match="during"):
        exchange.commit("third_party", "ccc")


def test_acking_after_settling_is_refused() -> None:
    exchange = _both_acked()
    exchange.reveal("us", MOVE)
    exchange.reveal("them", MOVE)
    with pytest.raises(ProtocolError, match="during"):
        exchange.acknowledge("us")


# --- reporting --------------------------------------------------------------


def test_it_names_who_it_is_waiting_for() -> None:
    """The watchdog needs to log *what* stalled, not merely that something did."""
    exchange = TurnExchange(step=1)
    exchange.commit("us", "aaa")
    assert "them" in exchange.waiting_for()

    settled = _both_acked()
    settled.reveal("us", MOVE)
    assert "them" in settled.waiting_for()
    assert "awaiting_reveals" in settled.waiting_for()


def test_a_settled_turn_waits_for_nobody() -> None:
    exchange = _both_acked()
    exchange.reveal("us", MOVE)
    exchange.reveal("them", MOVE)
    assert "nobody" in exchange.waiting_for()


def test_each_step_gets_its_own_exchange() -> None:
    """State must not leak between turns; the step is carried explicitly."""
    assert TurnExchange(step=4).step == 4
    assert TurnExchange(step=4).commits == {}
