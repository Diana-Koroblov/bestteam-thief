"""Every request carries an expiry (TODO 6.4.2, M#6).

**The rule: we never wait indefinitely for anything.** Appendix F negotiates
``response_timeout_sec = 30``; past it the opponent is not slow, they are gone,
and a peer that keeps waiting converts their failure into a match with no result
for either side.

So expiry triggers **one** controlled retry and then a technical loss. Not zero,
because a single dropped packet on a home connection is common and cheap to
survive. Not many, because ``max_retries`` attempts at 30 seconds each would
blow past the watchdog and turn a recoverable blip into the very hang the
timeout exists to prevent.

**The clock is injected.** Every deadline here is arithmetic on a number the
caller supplies, so the tests run in microseconds and the DoD's "no test sleeps
longer than 2 s" is satisfied by construction rather than by patience. Code that
called ``time.monotonic()`` directly could only be tested by actually waiting,
and a test suite nobody runs is a test suite that does not exist.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["Deadline", "DeadlineTracker", "DEFAULT_TIMEOUT_SEC", "MAX_ATTEMPTS"]

# Appendix F `network_and_league.response_timeout_sec`, negotiable.
DEFAULT_TIMEOUT_SEC = 30.0

# One try, then one retry. See the module docstring for why not more.
MAX_ATTEMPTS = 2


@dataclass
class Deadline:
    """One outstanding request and when it stops being worth waiting for.

    Attributes:
        label: What we are waiting for, named for the log. "Deadline expired"
            is not something anyone can act on after a match.
        started: Clock reading when the request went out.
        timeout: Seconds allowed.
        attempts: How many times this has been sent, including the first.
    """

    label: str
    started: float
    timeout: float = DEFAULT_TIMEOUT_SEC
    attempts: int = 1

    def expired(self, now: float) -> bool:
        """Whether *now* is past the limit. Exactly at the limit is expired."""
        return now - self.started >= self.timeout

    def remaining(self, now: float) -> float:
        """Seconds left, floored at zero so callers never see a negative wait."""
        return max(0.0, self.timeout - (now - self.started))

    @property
    def exhausted(self) -> bool:
        """Whether the retry has already been spent."""
        return self.attempts >= MAX_ATTEMPTS


@dataclass
class DeadlineTracker:
    """Holds the outstanding request, if any, and decides what expiry means.

    Attributes:
        timeout: Default seconds per request, from the negotiated config.
        pending: The request in flight, or None.
        expiries: ``(label, attempt)`` for every expiry, kept for the report —
            an opponent who timed out twice is worth knowing about before the
            next sub-game, and worth reporting after the series.
    """

    timeout: float = DEFAULT_TIMEOUT_SEC
    pending: Deadline | None = None
    expiries: list[tuple[str, int]] = field(default_factory=list)

    def start(self, label: str, now: float, timeout: float | None = None) -> Deadline:
        """Begin waiting for *label*.

        Starting a new request while one is pending **replaces** it rather than
        raising: the protocol is strictly one request at a time, so this can
        only happen after the previous one resolved, and losing the old
        deadline is safer than refusing to send the new one mid-match.
        """
        self.pending = Deadline(label, now, timeout if timeout is not None else self.timeout)
        return self.pending

    def resolve(self) -> None:
        """The reply arrived. Clear the deadline."""
        self.pending = None

    def check(self, now: float) -> str | None:
        """Return what to do about the pending request, if anything.

        Returns:
            None while there is time left or nothing is pending, ``"retry"``
            on the first expiry, and ``"technical_loss"`` on the second.

        Deliberately returns a decision instead of acting on one. The tracker
        knows *when* to give up; only the phase machine may decide what that
        does to the sub-game (M#4), and merging the two would put the ability to
        end a match inside a timer.
        """
        if self.pending is None or not self.pending.expired(now):
            return None

        self.expiries.append((self.pending.label, self.pending.attempts))
        if self.pending.exhausted:
            return "technical_loss"
        return "retry"

    def retry(self, now: float) -> Deadline:
        """Re-send the pending request against a fresh clock reading.

        Raises:
            RuntimeError: If nothing is pending. Retrying a request we never
                made means the caller has lost track of the protocol, and
                guessing would put an unexpected message on the wire.
        """
        if self.pending is None:
            raise RuntimeError("retry() called with no request in flight")
        self.pending = Deadline(
            self.pending.label, now, self.pending.timeout, self.pending.attempts + 1
        )
        return self.pending

    def describe(self) -> str:
        """One line for the post-match report."""
        if not self.expiries:
            return "no deadline expiries"
        return f"{len(self.expiries)} expiries: " + ", ".join(
            f"{label} (attempt {attempt})" for label, attempt in self.expiries
        )
