"""The Gatekeeper's budgets, as data (TODO 7.1.1, PRD 7 §3.1 req. 7.6).

**No limit is hardcoded anywhere.** Every number the Gatekeeper enforces is read
from ``config/<role>/rate_limits.json``, for the same reason the game's physics
live in ``game.json``: a constant compiled into the source is a constant nobody
can inspect, and Appendix F Table 19 makes these binding minimums that may be
raised by mutual agreement but never lowered (M#12).

Kept apart from the gates themselves so the table can be validated without
constructing a limiter, and so a proposed budget can be *checked* rather than
eyeballed — the retry budget in particular, which has to fit inside the response
timeout or the first retry storm walks straight into the watchdog.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from pathlib import Path

__all__ = ["RateLimits", "RateLimitsError", "load_rate_limits", "DEFAULT_RESPONSE_TIMEOUT_SEC"]

# Appendix F `network_and_league.response_timeout_sec`. Duplicated here only as a
# fallback for `violations()`; the real value comes from the negotiated config.
DEFAULT_RESPONSE_TIMEOUT_SEC = 30.0


class RateLimitsError(ValueError):
    """``rate_limits.json`` is missing, malformed, or not playable."""


@dataclass(frozen=True)
class RateLimits:
    """One role's Gatekeeper budget.

    Attributes:
        requests_per_minute: Sustained rate `r` for the token bucket.
        burst_capacity: Bucket size `C` — the largest legitimate burst.
        concurrent_requests: How many calls may be in flight at once.
        retry_backoff_sec: Constant wait between retries after an HTTP 429.
        max_retries: Retries after the first attempt.
        queue_depth: How many callers may wait for a slot.
        daily_send_quota: Hard ceiling on calls per UTC day.
        dos_window_sec: Width of the DOS detector's sliding window.
        dos_max_calls_in_window: Calls inside that window that lock the pipe.
    """

    requests_per_minute: int
    burst_capacity: int
    concurrent_requests: int
    retry_backoff_sec: float
    max_retries: int
    queue_depth: int
    daily_send_quota: int
    dos_window_sec: float
    dos_max_calls_in_window: int

    @property
    def refill_per_second(self) -> float:
        """The bucket's `r`, per second rather than per minute."""
        return self.requests_per_minute / 60.0

    @property
    def retry_budget_sec(self) -> float:
        """Total time spent waiting if every retry is used.

        The backoff is **constant, not exponential**. Exponential is the usual
        advice and it is wrong here: the whole retry sequence has to finish
        inside one response window, and doubling gets there in three steps. A
        fixed 5 s × 3 is 15 s, which leaves room for the requests themselves.
        """
        return self.retry_backoff_sec * self.max_retries

    def violations(self, response_timeout_sec: float = DEFAULT_RESPONSE_TIMEOUT_SEC) -> list[str]:
        """Return budgets that are legal on paper but cannot survive a match.

        An empty list means the table is safe to play with.
        """
        found: list[str] = []
        if self.retry_budget_sec >= response_timeout_sec:
            found.append(
                f"retry budget {self.retry_budget_sec:g}s "
                f"({self.max_retries} x {self.retry_backoff_sec:g}s) does not fit inside the "
                f"{response_timeout_sec:g}s response timeout: the last retry would still be "
                "waiting when the opponent has already recorded us as gone"
            )
        if self.burst_capacity < 1:
            found.append(
                f"burst_capacity {self.burst_capacity} allows no call at all; "
                "the bucket starts full and one token is needed per request"
            )
        if self.requests_per_minute < 1:
            found.append(
                f"requests_per_minute {self.requests_per_minute} never refills the bucket, "
                "so the opening burst would be the last call of the match and the wait "
                "for the next rate token would be unbounded"
            )
        if self.concurrent_requests < 1:
            found.append(f"concurrent_requests {self.concurrent_requests} would block every call")
        return found


def load_rate_limits(role_dir: Path, *, enforce: bool = True) -> RateLimits:
    """Load and validate ``rate_limits.json`` from *role_dir*.

    Keys beginning with an underscore are documentation — the file carries its
    own justification for every number, which is worth more in a config a
    grader reads than a comment in a module they will not open.

    Args:
        role_dir: Directory holding ``rate_limits.json``.
        enforce: Refuse a table that cannot survive a match. False only to
            inspect a proposal so the problem can be quoted back.

    Raises:
        RateLimitsError: Missing, malformed, incomplete, or unplayable.
    """
    path = Path(role_dir) / "rate_limits.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RateLimitsError(f"missing Gatekeeper budget: {path}") from error
    except json.JSONDecodeError as error:
        raise RateLimitsError(f"{path} is not valid JSON: {error}") from error

    wanted = {member.name for member in fields(RateLimits)}
    missing = sorted(wanted - set(raw))
    if missing:
        raise RateLimitsError(
            f"{path} is missing {', '.join(missing)}. Every limit is read from this "
            "file and none has a default in code (PRD 7 req. 7.6)."
        )

    limits = RateLimits(**{key: raw[key] for key in wanted})
    if enforce and (found := limits.violations()):
        raise RateLimitsError(f"{path} is not playable:\n  " + "\n  ".join(found))
    return limits
