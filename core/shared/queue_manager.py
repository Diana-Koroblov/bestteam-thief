"""Waiting for a slot, rather than failing for want of one (TODO 7.1.1, 7.1.5).

**A saturated limiter blocks; it never raises.** The reference implementation's
measured demand is 0.5 RPM against a 30 RPM budget, so this path should never
run in a real match — but when it does, the choice between delaying a report and
failing one is not close. A failed report is indistinguishable from a forfeit,
and under M#35 an unsent report scores 0 for *both* teams.

Two limits, doing different jobs:

* ``concurrent_requests`` caps how many calls are in flight. Waiting on it is
  normal and cheap.
* ``queue_depth`` caps how many callers may be waiting. Reaching it is not a
  busy system — at 0.5 RPM of real demand, a hundred queued callers means
  something upstream is looping — so that one *is* refused, loudly, rather than
  quietly growing an unbounded backlog of reports nobody will read.

The sleep is injected, so the tests exercise the waiting without spending it.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

__all__ = [
    "QueueManager",
    "QueueOverflowError",
    "QueueDeadlockError",
    "WAIT_SLICE_SEC",
    "MAX_WAIT_SEC",
]

# How long a blocked caller sleeps before re-checking. Short enough that a freed
# slot is taken promptly, long enough not to spin a core while waiting.
WAIT_SLICE_SEC = 0.05

# The longest anyone may wait for a slot, matching Appendix F's response timeout.
# **A hang is worse than a loss** (M#4, and the phase machine's whole shape): a
# caller still waiting after a full response window is not queued behind traffic,
# because this process is single-threaded and nothing else can free the slot. It
# is deadlocked — re-entrant use of the Gatekeeper, most likely — and waiting
# longer cannot fix it. Better a named error than a peer that never speaks again.
MAX_WAIT_SEC = 30.0
MAX_WAIT_SLICES = int(MAX_WAIT_SEC / WAIT_SLICE_SEC)


class QueueOverflowError(RuntimeError):
    """More callers are waiting than the configured depth allows."""


class QueueDeadlockError(RuntimeError):
    """A caller waited a full response window for a slot that never freed."""


@dataclass
class QueueManager:
    """Admission control for outbound calls.

    Attributes:
        concurrent_requests: Calls allowed in flight at once.
        queue_depth: Callers allowed to wait.
        sleep: Injected, so waiting is testable without spending real seconds.
        in_flight: Calls currently running.
        waiting: Callers currently blocked.
        high_water: The largest `in_flight + waiting` ever seen, for the report.
            Worth keeping precisely because it should stay at 1 all match: the
            first value above that is evidence, not noise.
    """

    concurrent_requests: int
    queue_depth: int
    sleep: Callable[[float], None] = time.sleep
    in_flight: int = 0
    waiting: int = 0
    high_water: int = 0

    @property
    def saturated(self) -> bool:
        """Whether every concurrency slot is taken."""
        return self.in_flight >= self.concurrent_requests

    @contextmanager
    def slot(self) -> Iterator[None]:
        """Hold one concurrency slot for the duration of the block.

        Raises:
            QueueOverflowError: The queue is already `queue_depth` deep. See the
                module docstring for why this one case refuses instead of
                waiting.
            QueueDeadlockError: The wait outlived a full response window. See
                `MAX_WAIT_SEC`.
        """
        if self.waiting >= self.queue_depth:
            raise QueueOverflowError(
                f"{self.waiting} callers already waiting (queue_depth={self.queue_depth}). "
                "Real demand is ~0.5 RPM, so a queue this deep is a loop upstream, "
                "not a busy match."
            )

        self.waiting += 1
        self._mark()
        try:
            for _ in range(MAX_WAIT_SLICES):
                if not self.saturated:
                    break
                self.sleep(WAIT_SLICE_SEC)
            else:
                raise QueueDeadlockError(
                    f"waited {MAX_WAIT_SEC:g}s for one of {self.concurrent_requests} "
                    "slots. This process is single-threaded, so nothing else could "
                    "have freed it: the Gatekeeper has been re-entered from inside "
                    "a call it was already running."
                )
        finally:
            self.waiting -= 1

        self.in_flight += 1
        self._mark()
        try:
            yield
        finally:
            self.in_flight -= 1

    def _mark(self) -> None:
        """Record the deepest the queue has ever been."""
        self.high_water = max(self.high_water, self.in_flight + self.waiting)
