"""Tunnel health, as a heartbeat (TODO 5.2.1, 5.2.2, PRD 5 §3.2, M#7).

**Tunnel resilience is game resilience.** A dropped tunnel is not a networking
inconvenience: the opponent cannot deliver a reveal, turn synchronisation
deadlocks, and under M#35 a match with no result scores 0 for *both* teams. So
the tunnel gets the same treatment as every other failure here — bounded
recovery, then a controlled ending, never an open-ended wait.

Two mechanisms, and the difference between them is the point:

* **Active.** Each check that finds the agent gone spends one reconnect
  attempt. Restarting a local process is cheap and usually works.
* **Passive.** The watchdog is beaten only while the tunnel is up. If
  reconnection keeps failing, silence accumulates and the sub-game ends within
  `watchdog_timeout_sec` without anyone having to decide that it should (5.7).

The passive half is what makes the active half safe to get wrong. Even if the
reconnect logic looped forever, the heartbeat it is *not* sending is what stops
the match — a bug here costs a sub-game, not a hang.

Reconnection is not complete until the handshake has been re-run. A tunnel that
is technically up while the opponent still holds a stale session is worse than
one that is plainly down, because it looks healthy from here (5.6).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.runtime.watchdog import Watchdog

__all__ = ["TunnelSupervisor", "MAX_RECONNECT_ATTEMPTS"]

# Bounded, because an unbounded retry is the deadlock the deadline tracker
# exists to prevent (PRD 5 §6). Three, because the failure a restart actually
# fixes — a transient agent crash — is fixed on the first attempt, and the ones
# it does not fix (binary gone, token rejected, port taken) are not fixed by a
# fourth. Three attempts at a ten-second startup budget also still fit inside
# the 60 s watchdog window, so every attempt can influence the outcome.
MAX_RECONNECT_ATTEMPTS = 3


@dataclass
class TunnelSupervisor:
    """Keeps the tunnel up, or ends the sub-game trying.

    Attributes:
        tunnel: Anything with the :class:`~core.infra.tunnel.TunnelManager`
            interface. Typed loosely on purpose — the runtime does not need to
            know which CLI is publishing the URL.
        watchdog: Beaten on every healthy check, starved otherwise.
        on_reconnect: Called with the new public URL after a restart, to re-run
            the handshake. Injected, because this layer must not know what a
            handshake is (M#3).
        max_attempts: Reconnects allowed for the whole session.
        attempts: How many have been spent.
        down_since: Clock reading when the outage began, or None while healthy.
        reconnects: `(clock, url)` per recovery, for the post-match report.
        failures: Why each failed attempt failed, in order.
    """

    tunnel: Any
    watchdog: Watchdog
    on_reconnect: Callable[[str], None] | None = None
    max_attempts: int = MAX_RECONNECT_ATTEMPTS
    attempts: int = 0
    down_since: float | None = None
    reconnects: list[tuple[float, str]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def check(self, now: float) -> str | None:
        """Return ``"technical_loss"`` when the tunnel is unrecoverable, else None.

        Returns a decision and never acts on one. Only the phase machine may end
        a sub-game (M#4); merging the two would put that power inside a health
        probe, and "which module changed the state" would stop having one answer.
        """
        if self.tunnel.is_alive():
            self.down_since = None
            self.watchdog.beat(now)
            return None

        if self.down_since is None:
            self.down_since = now
        if self.attempts < self.max_attempts and self._reconnect(now):
            return None

        # Two clocks, deliberately independent. Starving the watchdog is the
        # right *shared* signal (5.7), but starving only works if the tunnel is
        # the sole heartbeat source — and a peer whose tunnel is down may still
        # be beating the same watchdog from elsewhere in the turn loop, which
        # would leave this outage running forever. The outage clock below does
        # not depend on anyone else's behaviour, so the bound holds either way.
        if now - self.down_since >= self.watchdog.timeout:
            return "technical_loss"
        return self.watchdog.check(now)

    def _reconnect(self, now: float) -> bool:
        """Spend one attempt on a restart. True once the tunnel *and* the session are back.

        Any failure is swallowed and recorded rather than raised. A missing
        binary, a taken port and a refused token are all "still down" from here,
        none of them is worth a traceback while the watchdog is already
        counting, and the reason reaches the log either way.
        """
        self.attempts += 1
        try:
            url = self.tunnel.restart()
            if self.on_reconnect is not None:
                self.on_reconnect(url)
        except Exception as error:  # noqa: BLE001 - every failure means "still down"
            self.failures.append(f"attempt {self.attempts}: {type(error).__name__}: {error}")
            return False

        self.reconnects.append((now, url))
        self.down_since = None
        self.watchdog.beat(now)
        return True

    @property
    def exhausted(self) -> bool:
        """Whether every reconnect attempt has been spent."""
        return self.attempts >= self.max_attempts

    def describe(self) -> str:
        """One line for the post-match report."""
        if not self.reconnects and not self.failures:
            return "tunnel stable; no reconnects"
        parts = [f"{len(self.reconnects)} reconnect(s), {len(self.failures)} failed attempt(s)"]
        parts.extend(self.failures)
        return "; ".join(parts)
