"""The three gates composed (TODO 7.1.2-7.1.6, PRD 7 T7.1-T7.4).

The Gatekeeper exists because automated reporting removes the human delay
between a bug and its consequences. These tests are the only place that
scenario is ever exercised — by the time it runs for real, a live account is
already attached to it.

No test contacts a provider, and none sleeps: the call is a local function and
the clock and sleep are injected.
"""

from __future__ import annotations

import pytest

from core.shared.call_logger import FAILED, OK, REFUSED
from core.shared.gatekeeper import (
    Gatekeeper,
    GatekeeperLockedError,
    QuotaExhaustedError,
    is_rate_limited,
)
from core.shared.rate_limits import RateLimits, load_rate_limits
from tests.paths import PRESENT_ROLES, role_dir

MIDNIGHT = 1785715200.0


class FakeClock:
    """A clock the test advances by hand, and a sleep that advances it."""

    def __init__(self, start: float = MIDNIGHT) -> None:
        self.now = start
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += max(seconds, 0.001)


class Rejecting:
    """A provider that answers HTTP 429 a fixed number of times, then succeeds."""

    def __init__(self, refusals: int) -> None:
        self.refusals = refusals
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self.calls <= self.refusals:
            raise TooManyRequestsError()
        return "sent"


class TooManyRequestsError(Exception):
    """Shaped like an httpx status error, without importing httpx."""

    status_code = 429


def build(clock: FakeClock, **overrides) -> Gatekeeper:
    """Return a Gatekeeper on a generous budget unless the test narrows it."""
    defaults = {
        "requests_per_minute": 30,
        "burst_capacity": 5,
        "concurrent_requests": 2,
        "retry_backoff_sec": 5,
        "max_retries": 3,
        "queue_depth": 100,
        "daily_send_quota": 50,
        "dos_window_sec": 10,
        "dos_max_calls_in_window": 20,
    }
    limits = RateLimits(**{**defaults, **overrides})
    return Gatekeeper(limits=limits, clock=clock, sleep=clock.sleep)


def test_a_call_that_clears_every_gate_goes_through() -> None:
    clock = FakeClock()
    keeper = build(clock)
    assert keeper.execute(lambda: "sent", target="gmail.send") == "sent"
    assert keeper.logger.count(OK) == 1


def test_the_gates_are_cumulative_not_alternative() -> None:
    """A call must clear all three; clearing one is not clearing the door."""
    clock = FakeClock()
    keeper = build(clock, daily_send_quota=1)
    keeper.execute(lambda: "first")
    assert keeper.status().rate_tokens > 0  # the bucket would still allow it
    with pytest.raises(QuotaExhaustedError):
        keeper.execute(lambda: "second")


def test_an_exhausted_quota_refuses_and_says_so() -> None:
    """**T7.2.**"""
    clock = FakeClock()
    keeper = build(clock, daily_send_quota=0)
    with pytest.raises(QuotaExhaustedError, match="daily quota"):
        keeper.execute(lambda: "never", target="gmail.send")
    assert keeper.logger.count(REFUSED) == 1


def test_a_saturated_bucket_delays_rather_than_fails() -> None:
    """**T7.1.** Erroring here is indistinguishable from a forfeit (M#35)."""
    clock = FakeClock()
    keeper = build(clock, burst_capacity=2, requests_per_minute=60)
    for _ in range(4):
        assert keeper.execute(lambda: "ok") == "ok"
    assert clock.slept, "the third call should have waited, not raised"
    assert keeper.logger.count(FAILED) == 0


def test_a_loop_locks_the_pipe_and_it_stays_locked() -> None:
    """**T7.3.** One report is cheaper than the account (M#29)."""
    clock = FakeClock()
    keeper = build(clock, dos_max_calls_in_window=3, dos_window_sec=10)
    with pytest.raises(GatekeeperLockedError, match="loop, not a match"):
        for _ in range(20):
            keeper.execute(lambda: "ok")

    assert keeper.status().locked
    with pytest.raises(GatekeeperLockedError):
        keeper.execute(lambda: "ok")


def test_a_429_is_backed_off_never_blind_retried() -> None:
    """**T7.4.** Repeating immediately is how a rate limit becomes a ban."""
    clock = FakeClock()
    keeper = build(clock)
    provider = Rejecting(refusals=2)

    assert keeper.execute(provider, target="gmail.send") == "sent"
    assert clock.slept == [5, 5]
    assert keeper.logger.records[-1].attempts == 3
    assert keeper.logger.retried == 1


def test_retries_are_bounded_by_max_retries() -> None:
    """The whole sequence has to finish inside one response window."""
    clock = FakeClock()
    keeper = build(clock, max_retries=2)
    with pytest.raises(TooManyRequestsError):
        keeper.execute(Rejecting(refusals=99))
    assert clock.slept == [5, 5]


def test_a_non_429_failure_is_not_retried_at_all() -> None:
    """The provider did not ask us to slow down; repeating just repeats the bug."""
    clock = FakeClock()
    keeper = build(clock)

    def broken() -> str:
        raise ValueError("malformed attachment")

    with pytest.raises(ValueError, match="malformed"):
        keeper.execute(broken, target="gmail.send")
    assert clock.slept == []
    assert keeper.logger.count(FAILED) == 1


def test_refusals_are_logged_as_carefully_as_successes() -> None:
    """A locked pipe with no record explains nothing at 2 a.m."""
    clock = FakeClock()
    keeper = build(clock, daily_send_quota=0)
    with pytest.raises(QuotaExhaustedError):
        keeper.execute(lambda: "never", target="gmail.send")
    entry = keeper.logger.records[0]
    assert entry.target == "gmail.send"
    assert entry.outcome == REFUSED
    assert "daily quota" in entry.detail


def test_arguments_reach_the_call_unchanged() -> None:
    clock = FakeClock()
    keeper = build(clock)
    assert keeper.execute(lambda a, b=0: a + b, 40, b=2) == 42


def test_status_reports_every_gate() -> None:
    clock = FakeClock()
    keeper = build(clock, daily_send_quota=10)
    keeper.execute(lambda: "ok")
    status = keeper.status()
    assert status.quota_remaining == 9
    assert status.in_flight == 0
    assert status.high_water == 1
    assert not status.locked


def test_rate_limited_detection_handles_both_client_shapes() -> None:
    """Duck-typed, so core.shared needs no HTTP dependency."""

    class Attached:
        response = TooManyRequestsError()

    assert is_rate_limited(TooManyRequestsError())
    assert is_rate_limited(Attached())  # type: ignore[arg-type]
    assert not is_rate_limited(ValueError("nothing to do with rate"))


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_the_shipped_budget_loads_and_is_playable(role: str) -> None:
    """**Req. 7.6.** Every limit comes from the file; none has a default in code."""
    limits = load_rate_limits(role_dir(role))
    assert limits.violations() == []
    assert limits.refill_per_second == 0.5
