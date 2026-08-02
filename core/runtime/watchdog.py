"""The last line of defence against a silent process (TODO 6.4.3, M#7).

The deadline tracker watches **one request**. The watchdog watches **the whole
process**, and catches what the tracker cannot: a peer that is not waiting on
anything because it never got as far as sending. A deadlocked thread, a brain
stuck in a loop, an exception swallowed somewhere with no deadline outstanding
— all of these look identical from outside, which is silence.

Appendix F negotiates `watchdog_timeout_sec = 60`, deliberately longer than the
30-second response timeout so the two do not race: the tracker gets a full
timeout and a retry before the watchdog concludes the process itself is gone.

**It persists state before shutting down.** A killed process that left nothing
behind cannot be audited, and the end-of-match audit is what proves we played
honestly. Losing a sub-game is survivable; losing the evidence is not.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

__all__ = ["Watchdog", "DEFAULT_WATCHDOG_SEC"]

# Appendix F `network_and_league.watchdog_timeout_sec`, negotiable.
DEFAULT_WATCHDOG_SEC = 60.0


@dataclass
class Watchdog:
    """Fires once when the heartbeat goes stale.

    Attributes:
        timeout: Seconds of silence tolerated.
        last_beat: Clock reading of the most recent heartbeat.
        on_shutdown: Called with a reason **before** the caller acts on the
            verdict — this is where state is persisted. Injected rather than
            imported so the watchdog has no opinion about where a snapshot
            goes, and so tests can assert it ran.
        fired: Whether it has already triggered.
    """

    timeout: float = DEFAULT_WATCHDOG_SEC
    last_beat: float = 0.0
    on_shutdown: Callable[[str], None] | None = None
    fired: bool = field(default=False)

    def beat(self, now: float) -> None:
        """Record a sign of life.

        A beat after firing is ignored. Once we have concluded the process is
        gone and persisted state, a late heartbeat must not resurrect a
        sub-game whose result was already recorded.
        """
        if not self.fired:
            self.last_beat = now

    def stale(self, now: float) -> bool:
        """Whether the silence has exceeded the timeout."""
        return now - self.last_beat >= self.timeout

    def check(self, now: float) -> str | None:
        """Return ``"technical_loss"`` on the first stale check, else None.

        **Fires exactly once.** A watchdog polled every second on a dead process
        would otherwise persist state and shut down sixty times, and the last
        write — made while the process was already tearing down — is the one
        most likely to leave a truncated file.
        """
        if self.fired or not self.stale(now):
            return None

        self.fired = True
        reason = f"no heartbeat for {now - self.last_beat:.0f}s (limit {self.timeout:.0f}s)"
        if self.on_shutdown is not None:
            self.on_shutdown(reason)
        return "technical_loss"

    def silence(self, now: float) -> float:
        """How long we have been quiet, for the log and the GUI."""
        return max(0.0, now - self.last_beat)
