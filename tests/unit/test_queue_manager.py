"""Admission control for outbound calls (TODO 7.1.1, 7.1.5).

**A saturated limiter blocks; it never raises.** Measured demand is 0.5 RPM
against a 30 RPM budget, so nothing here should run during a real match — which
is exactly why it is tested. The one path that does refuse is the one that
cannot be a busy match at that rate, and the difference between the two is the
whole design.

The sleep is injected, so waiting is exercised without being spent.
"""

from __future__ import annotations

import pytest

from core.shared.queue_manager import (
    MAX_WAIT_SEC,
    QueueDeadlockError,
    QueueManager,
    QueueOverflowError,
)


def test_an_uncontended_call_takes_a_slot_and_gives_it_back() -> None:
    queue = QueueManager(concurrent_requests=2, queue_depth=10, sleep=lambda _: None)
    with queue.slot():
        assert queue.in_flight == 1
    assert queue.in_flight == 0
    assert queue.high_water == 1


def test_a_taken_slot_is_waited_for_rather_than_refused() -> None:
    """Erroring is indistinguishable from a forfeit; under M#35 that scores 0
    for *both* teams. So the caller waits.

    Freed from inside the sleep, because that is how it frees in production
    too: the holder finishes on another turn of the loop while this one waits.
    """
    queue = QueueManager(concurrent_requests=1, queue_depth=5)
    queue.in_flight = 1
    waits: list[float] = []

    def release(seconds: float) -> None:
        waits.append(seconds)
        queue.in_flight = 0

    queue.sleep = release
    with queue.slot():
        assert queue.in_flight == 1
    assert len(waits) == 1
    assert queue.high_water == 2


def test_a_queue_deeper_than_configured_is_a_loop_not_a_busy_match() -> None:
    """The one case that refuses, and the reason it is not inconsistent.

    At 0.5 RPM of real demand a hundred queued callers cannot be traffic. Left
    to wait, they would grow an unbounded backlog of reports nobody will read.
    """
    queue = QueueManager(concurrent_requests=1, queue_depth=0, sleep=lambda _: None)
    with pytest.raises(QueueOverflowError, match="not a busy match"), queue.slot():
        pass


def test_the_waiting_count_unwinds_even_when_admission_is_refused() -> None:
    """A leaked waiter would drift the queue toward a false overflow."""
    queue = QueueManager(concurrent_requests=1, queue_depth=1, sleep=lambda _: None)
    with queue.slot():
        pass
    assert queue.waiting == 0


def test_a_slot_that_never_frees_ends_the_wait_instead_of_hanging() -> None:
    """**A hang is worse than a loss**, and this is the only unbounded wait here.

    The process is single-threaded, so a slot nobody else can free is a slot
    that never frees — re-entrant use of the Gatekeeper. Waiting longer cannot
    fix it, and a peer that never speaks again takes the opponent's match down
    with it (M#35).
    """
    queue = QueueManager(concurrent_requests=1, queue_depth=5, sleep=lambda _: None)
    queue.in_flight = 1
    with pytest.raises(QueueDeadlockError, match="re-entered"), queue.slot():
        pass  # pragma: no cover - the wait never admits us
    assert queue.waiting == 0, "a leaked waiter would drift toward a false overflow"


def test_the_deadlock_bound_matches_the_response_window() -> None:
    """Longer would outlive the turn it was protecting; shorter would refuse a
    legitimate queue that Appendix F still considers inside the deadline."""
    from core.runtime.deadline_tracker import DEFAULT_TIMEOUT_SEC

    assert MAX_WAIT_SEC == DEFAULT_TIMEOUT_SEC


def test_the_high_water_mark_is_kept_because_it_should_never_move() -> None:
    """It should read 1 all match. The first value above that is evidence."""
    queue = QueueManager(concurrent_requests=4, queue_depth=10, sleep=lambda _: None)
    for _ in range(20):
        with queue.slot():
            pass
    assert queue.high_water == 1
