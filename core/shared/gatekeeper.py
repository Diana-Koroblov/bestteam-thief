"""The single door every outbound call leaves by (TODO 7.1.2, 7.1.3, M#28, M#29).

```
outgoing ──► DOS Detector ──► Quota Manager ──► Token Bucket ──► provider
  report      │ anomaly        │ full            │ empty
              ▼                ▼                 ▼
           LOCKED           Rejected           Blocked
```

**Cumulative, not alternative.** A call must clear all three. They fail in
different ways on purpose: the detector *locks* (something is wrong with us and
waiting will not help), the quota *rejects* (today is over), the bucket *blocks*
(wait and you will be served).

**The detector runs first, which reverses PRD 7 §3.1's diagram.** The order
there is quota → bucket → detector, and taken literally it makes the detector
blind to the one case it exists for: once the quota is exhausted every call is
rejected before reaching it, so a runaway loop hammering a spent quota is
invisible. Nothing goes out either way — the account is safe under both orders —
but only this one *names* the fault. "Locked: 400 calls in 10s, this is a loop"
is a diagnosis; "quota exhausted" repeated ten thousand times is not.

Automated reporting is what makes this necessary. It removes the human delay
between a bug and its consequences, and hands a live account to code that may
contain a loop. The book's question — what happens when that loop starts firing
thousands of messages a minute? — has a bad answer without these gates:
HTTP 429, then suspension, then every remaining match lost.

**HTTP 429 is honoured, never blind-retried (req. 7.4).** The provider has told
us the rate is too high; repeating the request immediately is how a rate limit
becomes a ban. Detection is duck-typed rather than importing `httpx`, so this
module stays free of a transport dependency and works for any client whose
error carries a status code.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.shared.call_logger import FAILED, OK, REFUSED, CallLogger, CallRecord
from core.shared.dos_detector import DosDetector
from core.shared.queue_manager import QueueManager
from core.shared.rate_limiter import DailyQuota, TokenBucket
from core.shared.rate_limits import RateLimits

__all__ = [
    "Gatekeeper",
    "GatekeeperError",
    "QuotaExhaustedError",
    "GatekeeperLockedError",
    "QueueStatus",
    "is_rate_limited",
]

TOO_MANY_REQUESTS = 429


class GatekeeperError(RuntimeError):
    """A gate refused the call. It never reached the provider."""


class QuotaExhaustedError(GatekeeperError):
    """Today's ceiling is spent. Nothing further goes out until UTC midnight."""


class GatekeeperLockedError(GatekeeperError):
    """The DOS detector shut the pipe. Terminal until a human clears it."""


def is_rate_limited(error: Exception) -> bool:
    """Whether *error* is the provider saying "too fast".

    Duck-typed across the two shapes clients use — a `status_code` on the error
    or on an attached `response` — so this module needs no HTTP library and no
    knowledge of which one the caller chose.
    """
    for holder in (error, getattr(error, "response", None)):
        if getattr(holder, "status_code", None) == TOO_MANY_REQUESTS:
            return True
    return False


@dataclass(frozen=True)
class QueueStatus:
    """A snapshot of every gate, for the GUI and the post-match report."""

    in_flight: int
    waiting: int
    high_water: int
    rate_tokens: float
    quota_remaining: int
    locked: bool
    lock_reason: str


@dataclass
class Gatekeeper:
    """Runs outbound calls, or explains which gate refused them.

    Attributes:
        limits: The budget table. Every number comes from it (req. 7.6).
        logger: Where every attempt is recorded, refusals included.
        clock: Epoch seconds. Epoch rather than monotonic because the quota
            rolls on the UTC calendar day, which a monotonic clock cannot name.
        sleep: Injected, so backoff and queueing cost nothing in tests.
    """

    limits: RateLimits
    logger: CallLogger = field(default_factory=CallLogger)
    clock: Callable[[], float] = time.time
    sleep: Callable[[float], None] = time.sleep
    bucket: TokenBucket = field(init=False)
    quota: DailyQuota = field(init=False)
    detector: DosDetector = field(init=False)
    queue: QueueManager = field(init=False)

    def __post_init__(self) -> None:
        """Build the three gates and the queue from the budget table."""
        self.bucket = TokenBucket(
            capacity=float(self.limits.burst_capacity),
            refill_per_second=self.limits.refill_per_second,
            updated_at=self.clock(),
        )
        self.quota = DailyQuota(ceiling=self.limits.daily_send_quota)
        self.detector = DosDetector(
            window_sec=self.limits.dos_window_sec,
            max_calls=self.limits.dos_max_calls_in_window,
        )
        self.queue = QueueManager(
            concurrent_requests=self.limits.concurrent_requests,
            queue_depth=self.limits.queue_depth,
            sleep=self.sleep,
        )

    def execute(self, call: Callable[..., Any], *args: Any, target: str = "", **kwargs: Any) -> Any:
        """Run *call* through all three gates and return its result.

        Args:
            call: The provider call. Invoked with the remaining arguments.
            *args: Positional arguments for *call*.
            target: Name for the log, e.g. ``gmail.send``. Defaults to the
                callable's own name.
            **kwargs: Keyword arguments for *call*.

        Raises:
            GatekeeperLockedError: The pipe is shut. Do not retry.
            QuotaExhaustedError: Today's ceiling is spent. Do not retry today.
        """
        name = target or getattr(call, "__name__", "unknown")
        started = self.clock()

        if not self.detector.observe(started):
            self._refuse(name, started, self.detector.reason)
            raise GatekeeperLockedError(self.detector.reason)
        if not self.quota.allow(started):
            reason = f"daily quota of {self.limits.daily_send_quota} calls is spent"
            self._refuse(name, started, reason)
            raise QuotaExhaustedError(reason)

        with self.queue.slot():
            self._await_rate_token()
            self.quota.record(self.clock())
            return self._run_with_backoff(call, name, started, args, kwargs)

    def _await_rate_token(self) -> None:
        """Block until the bucket yields a rate token.

        Blocks rather than raising: erroring here is indistinguishable from a
        forfeit, and under M#35 an unsent report scores 0 for both teams.
        """
        while not self.bucket.take(self.clock()):
            self.sleep(max(self.bucket.wait_time(self.clock()), 0.0))

    def _run_with_backoff(
        self, call: Callable[..., Any], name: str, started: float, args: tuple, kwargs: dict
    ) -> Any:
        """Invoke *call*, honouring HTTP 429 with a fixed backoff (req. 7.4)."""
        last: Exception | None = None
        for attempt in range(1, self.limits.max_retries + 2):
            try:
                result = call(*args, **kwargs)
            except Exception as error:  # noqa: BLE001 - re-raised below, always
                last = error
                if not is_rate_limited(error) or attempt > self.limits.max_retries:
                    self._finish(name, started, FAILED, f"{type(error).__name__}: {error}", attempt)
                    raise
                self.sleep(self.limits.retry_backoff_sec)
                continue
            self._finish(name, started, OK, "", attempt)
            return result
        raise AssertionError(f"unreachable: {last!r}")  # pragma: no cover

    def _refuse(self, target: str, started: float, detail: str) -> None:
        """Log a call a gate stopped before it ran."""
        self.logger.record(
            CallRecord(target=target, started_at=started, outcome=REFUSED, detail=detail)
        )

    def _finish(self, target: str, started: float, outcome: str, detail: str, attempts: int) -> None:
        """Log a call that reached the provider."""
        self.logger.record(
            CallRecord(
                target=target,
                started_at=started,
                duration_sec=self.clock() - started,
                outcome=outcome,
                detail=detail,
                attempts=attempts,
            )
        )

    def status(self) -> QueueStatus:
        """Return a snapshot of every gate."""
        now = self.clock()
        return QueueStatus(
            in_flight=self.queue.in_flight,
            waiting=self.queue.waiting,
            high_water=self.queue.high_water,
            rate_tokens=self.bucket.level(now),
            quota_remaining=self.quota.remaining(now),
            locked=self.detector.locked,
            lock_reason=self.detector.reason,
        )
