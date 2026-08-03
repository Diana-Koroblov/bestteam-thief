"""Latency measurement for the two-machine rehearsal (TODO 5.3.2, T5.8).

The instrument, not the reading. The reading needs both machines on the public
internet and lands in the rehearsal record; what is testable here is that the
arithmetic behind it is right, because the number it produces is one we may
have to quote to the opposing team when proposing a longer timeout.
"""

from __future__ import annotations

import pytest

from core.infra.latency import AMPLE, THIN, LatencyRecorder


def recorder(*samples: float) -> LatencyRecorder:
    """Return a recorder holding *samples*."""
    made = LatencyRecorder()
    for sample in samples:
        made.record(sample)
    return made


def test_percentiles_are_real_observations() -> None:
    """Nearest-rank, so a quoted p95 is a latency that actually happened.

    An interpolated percentile reports a number nobody measured, which is
    harder to defend in a negotiation than one that is simply in the data.
    """
    made = recorder(*[float(n) for n in range(1, 101)])
    assert made.p50 == 50.0
    assert made.p95 == 95.0
    assert made.percentile(0.0) == 1.0


def test_order_of_arrival_does_not_matter() -> None:
    assert recorder(9.0, 1.0, 5.0).p50 == recorder(1.0, 5.0, 9.0).p50


def test_an_empty_rehearsal_is_a_finding_not_a_crash() -> None:
    """A report can always be written; zero samples is itself worth reporting."""
    empty = LatencyRecorder()
    assert empty.p50 == 0.0
    assert empty.p95 == 0.0
    assert "no latency samples" in empty.describe(30.0)


def test_a_negative_sample_is_refused() -> None:
    """Clocks do go backwards, and a negative would quietly drag p95 down."""
    with pytest.raises(ValueError, match="cannot be negative"):
        LatencyRecorder().record(-0.5)


def test_a_fast_link_leaves_the_agreed_timeout_alone() -> None:
    """Appendix F's 30 s is generous for anything a home connection produces."""
    assert recorder(*[0.4] * 50).verdict(30.0) == AMPLE


def test_a_slow_tail_asks_for_a_longer_timeout() -> None:
    """**M#12.** Raising is legal by mutual agreement; lowering never is.

    So a thin margin has exactly one remedy, and the recommendation only ever
    points upward.
    """
    made = recorder(*([1.0] * 18 + [14.0] * 2))
    assert made.verdict(30.0) == THIN
    assert made.recommended_timeout() == 42.0
    assert "raising response_timeout_sec to 42s" in made.describe(30.0)


def test_the_recommendation_is_a_whole_number_of_seconds() -> None:
    """`27.4` invites an argument about the decimal instead of about the margin."""
    made = recorder(9.13)
    assert made.recommended_timeout() == 28.0


def test_the_margin_covers_the_retry_the_tracker_is_allowed() -> None:
    """A timeout that only fits one attempt is a timeout with no room to recover.

    The deadline tracker gets one try and one retry, so the window has to hold
    both with something left over.
    """
    from core.infra.latency import SAFE_MARGIN
    from core.runtime.deadline_tracker import MAX_ATTEMPTS

    assert SAFE_MARGIN > MAX_ATTEMPTS


def test_the_report_line_carries_both_percentiles() -> None:
    line = recorder(0.2, 0.4, 0.6).describe(30.0)
    assert "p50" in line and "p95" in line and "ample" in line
