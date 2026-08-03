"""The first two gates: a daily ceiling and a token bucket (TODO 7.1.2.a/b, M#28).

They answer different questions and neither substitutes for the other. The
quota asks *have we sent too much today?* — a slow, absolute ceiling. The bucket
asks *are we sending too fast right now?* — and separates sustained rate `r`
from burst size `C`, so a legitimate flurry of retries is allowed while a loop
running at the same average rate is not.

**Naming discipline (PRD 7 §3.1).** "Token" means three unrelated things in this
project: rate-limiter tokens, LLM tokens and OAuth tokens. The bucket's currency
is `rate_tokens` everywhere below, never `tokens`. The book calls this out
explicitly, which suggests it has caused confusion before.

**The clock is injected**, as everywhere else in this codebase that involves
time. A bucket that called `time.monotonic()` itself could only be tested by
waiting out a real minute, and a suite nobody runs is a suite that does not
exist.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

__all__ = ["TokenBucket", "DailyQuota", "utc_day"]


def utc_day(epoch_sec: float) -> str:
    """Return the UTC calendar day of *epoch_sec* as ``YYYY-MM-DD``.

    UTC, not local time, for the same reason the artefacts use it: the two peers
    share a timezone today and may not tomorrow, and a quota that rolls over at
    a different moment on each machine is a quota neither side can reason about.
    """
    return datetime.fromtimestamp(epoch_sec, tz=timezone.utc).date().isoformat()


@dataclass
class TokenBucket:
    """`rate_tokens ← min(C, rate_tokens + r·Δt)`; a call needs one (M#28).

    Attributes:
        capacity: `C`, the largest burst allowed.
        refill_per_second: `r`.
        rate_tokens: What is in the bucket now. Starts full, so the first call
            of a match is never made to wait for a budget nothing has spent.
        updated_at: Clock reading the level was last computed at.
    """

    capacity: float
    refill_per_second: float
    rate_tokens: float = -1.0
    updated_at: float = 0.0

    def __post_init__(self) -> None:
        """Start the bucket full unless a level was given explicitly."""
        if self.rate_tokens < 0:
            self.rate_tokens = self.capacity

    def level(self, now: float) -> float:
        """Return what the bucket would hold at *now*, without consuming."""
        elapsed = max(0.0, now - self.updated_at)
        return min(self.capacity, self.rate_tokens + elapsed * self.refill_per_second)

    def take(self, now: float) -> bool:
        """Consume one rate token if one is available. True when the call may go.

        Refills before deciding, so a caller that waited out the shortfall is
        served on its next attempt rather than being told to wait again by a
        level that was computed before it slept.
        """
        self.rate_tokens = self.level(now)
        self.updated_at = now
        if self.rate_tokens < 1.0:
            return False
        self.rate_tokens -= 1.0
        return True

    def wait_time(self, now: float) -> float:
        """Seconds until one rate token exists. Zero when a call may go now.

        This is what makes blocking possible instead of erroring: the caller is
        told exactly how long to sleep, so a saturated limiter delays a report
        rather than failing it — and a failed report is indistinguishable from
        a forfeit (M#35).
        """
        shortfall = 1.0 - self.level(now)
        if shortfall <= 0:
            return 0.0
        if self.refill_per_second <= 0:  # pragma: no cover - refused by violations()
            return float("inf")
        return shortfall / self.refill_per_second


@dataclass
class DailyQuota:
    """A hard ceiling per UTC day. Once exhausted, nothing further goes out.

    Attributes:
        ceiling: Calls allowed per day.
        used: Calls made on `day` so far.
        day: The UTC day `used` refers to, or empty before the first call.
    """

    ceiling: int
    used: int = 0
    day: str = ""

    def _roll(self, now: float) -> None:
        """Reset the counter when the UTC day has changed."""
        today = utc_day(now)
        if today != self.day:
            self.day, self.used = today, 0

    def remaining(self, now: float) -> int:
        """How many calls are left today."""
        self._roll(now)
        return max(0, self.ceiling - self.used)

    def allow(self, now: float) -> bool:
        """Whether another call is within today's ceiling. Does not consume."""
        return self.remaining(now) > 0

    def record(self, now: float) -> None:
        """Count one call against today's ceiling.

        Counted **on the attempt, not on success**. A call that failed still
        reached the provider and still counts against what they saw, and a
        quota that only counted successes would let a failing loop run free —
        which is the exact scenario the ceiling exists to survive.
        """
        self._roll(now)
        self.used += 1
