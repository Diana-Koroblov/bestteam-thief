"""Round-trip latency, measured rather than assumed (TODO 5.3.2, PRD 5 §3.4).

Appendix F negotiates `response_timeout_sec = 30`. Whether that is generous or
marginal is not a matter of opinion: it depends on the actual round trip between
two home connections through a tunnel, and nobody knows that number until the
two-machine rehearsal produces it.

This is the instrument that produces it. It exists so the rehearsal is a
recording rather than an argument afterwards, and so the decision it feeds is a
decision about data.

**The margin, not the mean, is what matters.** A p50 of 200 ms says nothing
useful about a 30-second timeout; the question is whether the slow tail leaves
room for a request *and* the one retry the deadline tracker is allowed. So the
verdict is computed against p95 with a factor for that retry, and the
recommendation is always to *raise* the timeout — M#12 permits raising by mutual
agreement and forbids lowering under any circumstances, so a thin margin has
exactly one legal remedy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

__all__ = ["LatencyRecorder", "SAFE_MARGIN", "AMPLE", "THIN"]

# The response window should cover a slow request and the retry that follows it,
# with room left over: 2 for the retry the deadline tracker allows, plus a third
# attempt's worth of headroom so a single bad sample does not sit on the line.
SAFE_MARGIN = 3.0

AMPLE = "ample"
THIN = "thin"


@dataclass
class LatencyRecorder:
    """Collects round-trip times and answers whether the timeout is safe.

    Attributes:
        samples: Every recorded round trip, in seconds, in arrival order.
    """

    samples: list[float] = field(default_factory=list)

    def record(self, seconds: float) -> None:
        """Add one round-trip measurement.

        Raises:
            ValueError: A negative duration. Clocks do go backwards — a system
                clock adjustment mid-match will do it — and a negative sample
                would quietly drag a percentile down rather than being noticed.
        """
        if seconds < 0:
            raise ValueError(f"round-trip time cannot be negative: {seconds!r}")
        self.samples.append(float(seconds))

    def percentile(self, fraction: float) -> float:
        """Return the nearest-rank percentile of the samples.

        Nearest-rank rather than interpolated: with the ~200 samples a series
        produces, the difference is negligible, and an interpolated p95 reports
        a latency that was never actually observed. For a number that will be
        quoted to the opposing team, a real observation is easier to defend.

        Returns:
            0.0 when nothing has been recorded, so a report can always be
            written — an empty rehearsal is a finding, not a crash.
        """
        if not self.samples:
            return 0.0
        ordered = sorted(self.samples)
        rank = max(1, math.ceil(fraction * len(ordered)))
        return ordered[min(rank, len(ordered)) - 1]

    @property
    def p50(self) -> float:
        """Median round trip."""
        return self.percentile(0.50)

    @property
    def p95(self) -> float:
        """The slow tail, which is what the timeout has to survive."""
        return self.percentile(0.95)

    def recommended_timeout(self) -> float:
        """Return the smallest response timeout the measured tail justifies.

        Rounded up to a whole second: the value goes into a config both teams
        sign, and `27.4` invites a negotiation about the decimal instead of
        about the margin.
        """
        return float(math.ceil(self.p95 * SAFE_MARGIN))

    def verdict(self, timeout_sec: float) -> str:
        """Return :data:`AMPLE` or :data:`THIN` for *timeout_sec*.

        THIN is not a failure. It is the trigger for PRD 5 requirement 5.13:
        propose raising the timeout, by mutual agreement, before the series.
        """
        return AMPLE if self.recommended_timeout() <= timeout_sec else THIN

    def describe(self, timeout_sec: float) -> str:
        """One line for the rehearsal record and the post-match report."""
        if not self.samples:
            return "no latency samples recorded"
        verdict = self.verdict(timeout_sec)
        line = (
            f"{len(self.samples)} samples: p50 {self.p50:.3f}s, p95 {self.p95:.3f}s "
            f"against a {timeout_sec:g}s timeout - margin {verdict}"
        )
        if verdict == THIN:
            line += (
                f". Propose raising response_timeout_sec to "
                f"{self.recommended_timeout():g}s by mutual agreement (M#12)"
            )
        return line
