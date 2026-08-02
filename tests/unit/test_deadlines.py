"""Deadlines and the watchdog (TODO 6.4.2, 6.4.3, 6.5.4, M#6, M#7).

**No test here sleeps at all.** The clock is a number the test passes in, so a
sixty-second timeout is checked in microseconds. Code calling `time.monotonic()`
directly could only be tested by actually waiting, and a suite nobody runs
because it takes two minutes is a suite that does not exist.

That is not merely convenient. These are the paths that fire *only* when
something has already gone wrong, so they are the least likely to be exercised
by accident and the most expensive to get wrong.
"""

from __future__ import annotations

import pytest

from core.runtime.deadline_tracker import MAX_ATTEMPTS, DeadlineTracker
from core.runtime.phase_machine import Phase, PhaseMachine
from core.runtime.watchdog import Watchdog

# --- deadlines --------------------------------------------------------------


def test_a_request_inside_its_window_is_not_disturbed() -> None:
    tracker = DeadlineTracker(timeout=30.0)
    tracker.start("reveal", now=100.0)
    assert tracker.check(now=129.9) is None
    assert tracker.pending.remaining(now=110.0) == 20.0


def test_the_first_expiry_asks_for_a_retry_not_a_loss() -> None:
    """A single dropped packet on a home connection is common and survivable."""
    tracker = DeadlineTracker(timeout=30.0)
    tracker.start("reveal", now=100.0)
    assert tracker.check(now=130.0) == "retry"


def test_the_second_expiry_gives_up() -> None:
    """**Not many retries.** `max_retries` attempts at 30 s each would blow past
    the watchdog and turn a recoverable blip into the hang the timeout exists to
    prevent."""
    tracker = DeadlineTracker(timeout=30.0)
    tracker.start("reveal", now=100.0)
    assert tracker.check(now=130.0) == "retry"
    tracker.retry(now=130.0)
    assert tracker.check(now=160.0) == "technical_loss"
    assert tracker.pending.attempts == MAX_ATTEMPTS


def test_expiry_is_inclusive_at_the_boundary() -> None:
    """Exactly at the limit is expired. The opponent had their full window."""
    tracker = DeadlineTracker(timeout=30.0)
    tracker.start("reveal", now=0.0)
    assert tracker.check(now=30.0) == "retry"


def test_a_resolved_request_stops_being_watched() -> None:
    tracker = DeadlineTracker(timeout=30.0)
    tracker.start("reveal", now=0.0)
    tracker.resolve()
    assert tracker.check(now=99_999.0) is None


def test_remaining_never_goes_negative() -> None:
    """Callers pass this to a socket timeout; a negative would raise there."""
    tracker = DeadlineTracker(timeout=30.0)
    deadline = tracker.start("reveal", now=0.0)
    assert deadline.remaining(now=100.0) == 0.0


def test_retrying_nothing_raises() -> None:
    """Retrying a request we never made means we lost track of the protocol.

    Guessing would put an unexpected message on the wire, which the opponent is
    entitled to treat as a violation.
    """
    with pytest.raises(RuntimeError):
        DeadlineTracker().retry(now=1.0)


def test_expiries_are_recorded_for_the_report() -> None:
    """An opponent who timed out twice is worth knowing about before the next
    sub-game, and worth reporting after the series."""
    tracker = DeadlineTracker(timeout=10.0)
    tracker.start("commit", now=0.0)
    tracker.check(now=10.0)
    assert tracker.expiries == [("commit", 1)]
    assert "commit (attempt 1)" in tracker.describe()


def test_the_tracker_decides_when_but_never_what() -> None:
    """**M#4: only the phase machine may end a sub-game.**

    The tracker returns a string. Merging the two would put the ability to end
    a match inside a timer, and "which module changed the state" would stop
    having one answer.
    """
    tracker = DeadlineTracker(timeout=1.0)
    tracker.start("reveal", now=0.0)
    tracker.retry(now=0.0)
    verdict = tracker.check(now=5.0)

    machine = PhaseMachine(Phase.AWAITING_REVEAL)
    assert verdict == "technical_loss"
    machine.fail(verdict)
    assert machine.lost


# --- the watchdog -----------------------------------------------------------


def test_a_beating_process_is_left_alone() -> None:
    dog = Watchdog(timeout=60.0, last_beat=0.0)
    for now in range(0, 300, 30):
        dog.beat(float(now))
        assert dog.check(float(now)) is None


def test_silence_past_the_limit_fires() -> None:
    """What the deadline tracker cannot catch: a peer not waiting on anything.

    A deadlocked thread, a brain stuck in a loop, an exception swallowed with no
    deadline outstanding — from outside, all three look like silence.
    """
    dog = Watchdog(timeout=60.0, last_beat=0.0)
    assert dog.check(now=60.0) == "technical_loss"


def test_it_persists_state_before_shutting_down() -> None:
    """**Losing a sub-game is survivable; losing the evidence is not.**

    A killed process that left nothing behind cannot be audited, and the audit
    is what proves we played honestly.
    """
    persisted: list[str] = []
    dog = Watchdog(timeout=60.0, last_beat=0.0, on_shutdown=persisted.append)
    dog.check(now=90.0)
    assert len(persisted) == 1
    assert "no heartbeat" in persisted[0]


def test_it_fires_exactly_once() -> None:
    """Polled every second on a dead process it would otherwise persist and shut
    down sixty times — and the last write, made while already tearing down, is
    the one most likely to leave a truncated file."""
    persisted: list[str] = []
    dog = Watchdog(timeout=60.0, last_beat=0.0, on_shutdown=persisted.append)
    verdicts = [dog.check(now=float(t)) for t in range(60, 120)]
    assert verdicts.count("technical_loss") == 1
    assert len(persisted) == 1


def test_a_late_heartbeat_cannot_resurrect_a_recorded_loss() -> None:
    """Once the result is written, a straggler thread must not undo it."""
    dog = Watchdog(timeout=60.0, last_beat=0.0)
    dog.check(now=60.0)
    dog.beat(now=61.0)
    assert dog.fired
    assert dog.check(now=200.0) is None


def test_the_watchdog_window_is_longer_than_the_response_timeout() -> None:
    """**They must not race.**

    The tracker needs a full timeout *and* a retry — 60 s — before the watchdog
    is entitled to conclude the process itself is gone. Appendix F's defaults
    (30 s and 60 s) are exactly on that boundary, so this is asserted rather
    than assumed.
    """
    from core.runtime.deadline_tracker import DEFAULT_TIMEOUT_SEC
    from core.runtime.watchdog import DEFAULT_WATCHDOG_SEC

    assert DEFAULT_WATCHDOG_SEC >= DEFAULT_TIMEOUT_SEC * MAX_ATTEMPTS
