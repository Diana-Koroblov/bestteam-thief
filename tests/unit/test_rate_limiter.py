"""The individual gates (TODO 7.1.2.a-c, M#28, M#29, PRD 7 T7.1-T7.3).

**No test here sleeps.** The clock is a number the test passes in, so a daily
quota rolling over at UTC midnight is checked in microseconds, and so is a
sliding window that would otherwise take ten real seconds to fill.

Tested apart from the Gatekeeper on purpose. These three are the parts that
must be right *individually* — the composition can only be as correct as the
pieces, and a bug in the bucket looks exactly like a bug in the composition
when they are only ever exercised together.
"""

from __future__ import annotations

from core.shared.dos_detector import DosDetector
from core.shared.rate_limiter import DailyQuota, TokenBucket, utc_day

# 2026-08-03T00:00:00Z, and the same instant one second before.
MIDNIGHT = 1785715200.0
DAY = 86_400.0


# --- token bucket (7.1.2.b) --------------------------------------------------


def test_the_bucket_starts_full() -> None:
    """The first call of a match must not wait for a budget nothing has spent."""
    bucket = TokenBucket(capacity=5, refill_per_second=0.5)
    assert bucket.level(now=0.0) == 5
    assert bucket.take(now=0.0)


def test_a_burst_empties_it_and_the_next_call_is_blocked() -> None:
    """**T7.1.** Blocked, not crashed."""
    bucket = TokenBucket(capacity=3, refill_per_second=0.5, updated_at=0.0)
    assert [bucket.take(now=0.0) for _ in range(3)] == [True, True, True]
    assert not bucket.take(now=0.0)


def test_it_refills_at_r_and_never_past_c() -> None:
    """`rate_tokens ← min(C, rate_tokens + r·Δt)` — the second half matters.

    Without the cap, an idle hour would bank 1800 tokens and the next burst
    would be unlimited, which is the opposite of what a bucket is for.
    """
    bucket = TokenBucket(capacity=3, refill_per_second=0.5, rate_tokens=0.0, updated_at=0.0)
    assert bucket.level(now=2.0) == 1.0
    assert bucket.level(now=10_000.0) == 3.0


def test_it_says_exactly_how_long_to_wait() -> None:
    """What makes blocking possible instead of erroring.

    A failed report is indistinguishable from a forfeit, and under M#35 an
    unsent report scores 0 for *both* teams — so the caller is told how long to
    sleep rather than being handed an exception.
    """
    bucket = TokenBucket(capacity=3, refill_per_second=0.5, rate_tokens=0.0, updated_at=0.0)
    assert bucket.wait_time(now=0.0) == 2.0
    assert bucket.wait_time(now=2.0) == 0.0


def test_waiting_out_the_shortfall_actually_serves_the_caller() -> None:
    """A level computed before the sleep must not refuse the call after it."""
    bucket = TokenBucket(capacity=1, refill_per_second=1.0, rate_tokens=0.0, updated_at=0.0)
    assert not bucket.take(now=0.0)
    assert bucket.take(now=bucket.wait_time(now=0.0))


# --- daily quota (7.1.2.a) ---------------------------------------------------


def test_an_exhausted_quota_rejects_everything_after_it() -> None:
    """**T7.2.** Once the ceiling is reached, nothing further goes out."""
    quota = DailyQuota(ceiling=2)
    for _ in range(2):
        assert quota.allow(MIDNIGHT)
        quota.record(MIDNIGHT)
    assert not quota.allow(MIDNIGHT)
    assert quota.remaining(MIDNIGHT) == 0


def test_the_ceiling_rolls_over_at_utc_midnight() -> None:
    """UTC, not local: a quota that rolled at a different moment on each machine
    is a quota neither side can reason about."""
    quota = DailyQuota(ceiling=1)
    quota.record(MIDNIGHT)
    assert not quota.allow(MIDNIGHT + DAY - 1)
    assert quota.allow(MIDNIGHT + DAY)


def test_attempts_count_even_when_they_fail() -> None:
    """A failing loop still reached the provider, and still counts to them.

    A quota that only counted successes would let exactly that loop run free —
    the scenario the ceiling exists to survive.
    """
    quota = DailyQuota(ceiling=3)
    for _ in range(3):
        quota.record(MIDNIGHT)
    assert not quota.allow(MIDNIGHT)


def test_the_day_key_is_a_utc_calendar_date() -> None:
    assert utc_day(MIDNIGHT) == "2026-08-03"
    assert utc_day(MIDNIGHT - 1) == "2026-08-02"


# --- DOS detector (7.1.2.c) --------------------------------------------------


def test_a_normal_match_never_trips_it() -> None:
    """Measured demand is ~0.5 RPM against a ceiling of 120."""
    detector = DosDetector(window_sec=10.0, max_calls=20)
    assert all(detector.observe(float(step) * 120.0) for step in range(50))
    assert not detector.locked


def test_a_loop_locks_the_pipe() -> None:
    """**T7.3.** Sacrifice one report to save the account (M#29).

    Losing a report scores 0 for that match. Losing the account scores 0 for
    every remaining one.
    """
    detector = DosDetector(window_sec=10.0, max_calls=20)
    verdicts = [detector.observe(now=step * 0.01) for step in range(100)]
    assert verdicts.count(False) > 0
    assert detector.locked
    assert "this is a loop, not a match" in detector.reason


def test_the_lock_does_not_time_out_on_its_own() -> None:
    """A detector that unlocked itself would let the same loop resume."""
    detector = DosDetector(window_sec=10.0, max_calls=2)
    for step in range(5):
        detector.observe(now=float(step) * 0.1)
    assert not detector.observe(now=1_000_000.0)

    detector.reset()
    assert detector.observe(now=1_000_001.0)


def test_the_window_slides(  ) -> None:
    """Calls older than the window are forgotten, or every long match would trip."""
    detector = DosDetector(window_sec=10.0, max_calls=3)
    for step in range(3):
        assert detector.observe(now=float(step))
    assert detector.observe(now=100.0)
    assert detector.rate_per_minute(now=100.0) == 6.0
