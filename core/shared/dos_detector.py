"""The third gate, and the only one aimed at us (TODO 7.1.2.c, M#29).

The quota and the bucket protect the *provider* from our volume. This protects
our **account** from our own bugs, and the difference decides how it behaves
when it fires.

A rate limiter throttles and lets the caller continue. This does not: it locks
the pipe entirely and stays locked. The scenario it exists for is a loop firing
thousands of messages a minute, where the provider's answer is HTTP 429 and,
if we keep going, suspension — which would cost every remaining match in the
league, not one report.

So the trade is deliberate and one-sided: **sacrifice one report to save the
account.** Losing a report scores 0 for that match under M#35. Losing the
account scores 0 for all of them.

The lock does not time out, and there is no automatic recovery. Whatever
triggered it is a bug in our code, and a detector that unlocked itself after a
minute would let the same loop resume at exactly the rate that tripped it.
Clearing it is a human decision taken after reading the log.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

__all__ = ["DosDetector"]


@dataclass
class DosDetector:
    """Locks the outbound pipe when the call pattern stops looking like a match.

    Attributes:
        window_sec: Width of the sliding window.
        max_calls: Calls inside the window that constitute an anomaly.
        recent: Clock readings of the calls still inside the window.
        locked: Whether the pipe is shut. Terminal until `reset()`.
        reason: What tripped it, kept for the log and the post-match report.
    """

    window_sec: float
    max_calls: int
    recent: deque[float] = field(default_factory=deque)
    locked: bool = False
    reason: str = ""

    def observe(self, now: float) -> bool:
        """Record one attempt and return whether the pipe is still open.

        Called **before** the request goes out, not after. A detector that only
        saw completed calls would be blind to precisely the failure it is for:
        a loop whose calls are all failing fast is the fastest loop there is.
        """
        if self.locked:
            return False

        self.recent.append(now)
        while self.recent and now - self.recent[0] > self.window_sec:
            self.recent.popleft()

        if len(self.recent) > self.max_calls:
            self.locked = True
            self.reason = (
                f"{len(self.recent)} calls in {self.window_sec:g}s exceeds the "
                f"{self.max_calls} allowed - this is a loop, not a match. Pipe locked "
                "to protect the account (M#29); clear it with reset() after reading "
                "the call log."
            )
            return False
        return True

    def rate_per_minute(self, now: float) -> float:
        """Observed rate over the window, for `status()` and the report."""
        if self.window_sec <= 0:  # pragma: no cover - refused by config validation
            return 0.0
        inside = [at for at in self.recent if now - at <= self.window_sec]
        return len(inside) * 60.0 / self.window_sec

    def reset(self) -> None:
        """Clear the lock. A human decision, taken after reading the log."""
        self.locked = False
        self.reason = ""
        self.recent.clear()
