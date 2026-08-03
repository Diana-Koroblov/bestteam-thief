"""Tunnel drop, reconnect and technical loss (TODO 5.2.1, 5.2.2, T5.3-T5.5, T5.9).

These are the paths that only ever run when the match is already going wrong,
so none of them can be trusted to have been exercised by hand. The clock is a
number the test passes in, exactly as in `test_deadlines.py`: a sixty-second
watchdog window is checked in microseconds.

The property under test throughout is that **there is no way to hang.** Every
sequence below ends in either a working tunnel or a recorded technical loss.
"""

from __future__ import annotations

from core.runtime.phase_machine import Phase, PhaseMachine
from core.runtime.tunnel_supervisor import MAX_RECONNECT_ATTEMPTS, TunnelSupervisor
from core.runtime.watchdog import DEFAULT_WATCHDOG_SEC, Watchdog

URL = "https://denotatively-sciuroid-florine.ngrok-free.dev"


class FakeTunnel:
    """A tunnel that can be killed and that may or may not come back."""

    def __init__(self, alive: bool = True, revives: bool = True) -> None:
        self.alive = alive
        self.revives = revives
        self.restarts = 0

    def is_alive(self) -> bool:
        return self.alive

    def restart(self) -> str:
        self.restarts += 1
        if not self.revives:
            raise RuntimeError("ngrok exited before publishing a URL")
        self.alive = True
        return URL


def build(tunnel: FakeTunnel, **fields) -> tuple[TunnelSupervisor, Watchdog]:
    """Return a supervisor over *tunnel* and the watchdog it feeds."""
    dog = Watchdog(timeout=DEFAULT_WATCHDOG_SEC, last_beat=0.0)
    return TunnelSupervisor(tunnel=tunnel, watchdog=dog, **fields), dog


def test_a_healthy_tunnel_feeds_the_watchdog() -> None:
    supervisor, dog = build(FakeTunnel())
    for now in range(0, 300, 30):
        assert supervisor.check(float(now)) is None
    assert dog.silence(now=300.0) == 30.0


def test_a_dropped_tunnel_is_restarted() -> None:
    """**T5.3, T5.4.** Restarting a local process is cheap and usually works."""
    tunnel = FakeTunnel(alive=False)
    supervisor, _ = build(tunnel)
    assert supervisor.check(now=10.0) is None
    assert tunnel.restarts == 1
    assert supervisor.reconnects == [(10.0, URL)]


def test_reconnecting_re_runs_the_handshake() -> None:
    """**PRD 5 requirement 5.6.** The opponent must not hold a stale session.

    A tunnel that is technically up while the opponent still believes in the
    old session is worse than one that is plainly down, because from here it
    looks healthy.
    """
    handshakes: list[str] = []
    supervisor, _ = build(FakeTunnel(alive=False), on_reconnect=handshakes.append)
    supervisor.check(now=10.0)
    assert handshakes == [URL]


def test_a_failed_re_handshake_is_a_failed_reconnect() -> None:
    """Recovery is not the process coming back, it is the session coming back."""

    def refuse(url: str) -> None:
        raise RuntimeError("config digest mismatch")

    tunnel = FakeTunnel(alive=False)
    supervisor, _ = build(tunnel, on_reconnect=refuse)
    supervisor.check(now=10.0)
    assert supervisor.reconnects == []
    assert "config digest mismatch" in supervisor.failures[0]


def test_an_unrevivable_tunnel_ends_in_a_technical_loss_not_a_hang() -> None:
    """**T5.5.** Bounded recovery, then a controlled ending.

    Losing on a technical fault is bad. Hanging is worse: it wastes the
    opponent's time, produces no log, and leaves the match unresolvable — which
    under M#35 costs *both* teams their points.
    """
    tunnel = FakeTunnel(alive=False, revives=False)
    supervisor, _ = build(tunnel)
    verdicts = [supervisor.check(float(now)) for now in range(0, 200, 10)]
    assert "technical_loss" in verdicts
    assert tunnel.restarts == MAX_RECONNECT_ATTEMPTS


def test_attempts_are_bounded_however_long_the_match_runs() -> None:
    """An unbounded retry is the deadlock the deadline tracker exists to prevent."""
    tunnel = FakeTunnel(alive=False, revives=False)
    supervisor, _ = build(tunnel)
    for now in range(0, 10_000, 10):
        supervisor.check(float(now))
    assert tunnel.restarts == MAX_RECONNECT_ATTEMPTS
    assert supervisor.exhausted


def test_a_dead_tunnel_is_never_beaten_through() -> None:
    """The passive half, and the reason a bug in the active half is survivable.

    Even if reconnection looped forever, the heartbeat it is *not* sending is
    what closes the match out.
    """
    supervisor, dog = build(FakeTunnel(alive=False, revives=False))
    supervisor.check(now=1.0)
    assert dog.silence(now=1.0) == 1.0


def test_the_loss_lands_inside_the_watchdog_window() -> None:
    """**5.2.2 DoD.** A dead tunnel triggers a controlled action within the limit."""
    supervisor, _ = build(FakeTunnel(alive=False, revives=False))
    assert supervisor.check(now=DEFAULT_WATCHDOG_SEC) == "technical_loss"


def test_the_outage_ends_even_while_something_else_beats_the_watchdog() -> None:
    """Starving the watchdog only works if the tunnel is its *only* heartbeat.

    It is not: the turn loop beats the same watchdog. A peer that kept beating
    it from elsewhere would leave this outage running forever, so the outage
    is bounded by its own clock rather than by anyone else's behaviour.
    """
    supervisor, dog = build(FakeTunnel(alive=False, revives=False))
    verdicts = []
    for now in range(0, 200, 10):
        dog.beat(float(now))  # something else in the runtime is still alive
        verdicts.append(supervisor.check(float(now)))
    assert "technical_loss" in verdicts


def test_a_recovered_tunnel_starts_the_outage_clock_over() -> None:
    """A blip an hour ago must not shorten the budget for an unrelated one now."""
    tunnel = FakeTunnel(alive=False)
    supervisor, dog = build(tunnel)
    supervisor.check(now=10.0)
    assert supervisor.down_since is None

    tunnel.alive, tunnel.revives = False, False
    dog.beat(now=1000.0)
    assert supervisor.check(now=1000.0) is None
    assert supervisor.down_since == 1000.0
    # A full window from *this* drop, not from the one 990 seconds ago.
    assert supervisor.check(now=1000.0 + DEFAULT_WATCHDOG_SEC) == "technical_loss"


def test_the_supervisor_decides_when_but_never_what() -> None:
    """**M#4: only the phase machine may end a sub-game.**

    **T5.9** in the concrete: the opponent vanishes while we are waiting on a
    reveal. Merging the verdict into the health probe would put the power to
    end a match inside a timer.
    """
    supervisor, _ = build(FakeTunnel(alive=False, revives=False))
    machine = PhaseMachine(Phase.AWAITING_REVEAL)
    verdict = supervisor.check(now=DEFAULT_WATCHDOG_SEC)

    assert not machine.terminal
    machine.fail(verdict or "")
    assert machine.lost


def test_the_reconnect_budget_fits_inside_the_watchdog_window() -> None:
    """**They must not race.** An attempt that could never finish in time is not
    an attempt, it is a number that makes the retry policy look more generous
    than it is. Asserted rather than assumed, because both constants move."""
    from core.infra.tunnel import STARTUP_BUDGET_SEC

    assert MAX_RECONNECT_ATTEMPTS * STARTUP_BUDGET_SEC <= DEFAULT_WATCHDOG_SEC


def test_the_report_says_what_happened() -> None:
    stable, _ = build(FakeTunnel())
    stable.check(now=1.0)
    assert "no reconnects" in stable.describe()

    troubled, _ = build(FakeTunnel(alive=False, revives=False))
    troubled.check(now=1.0)
    assert "1 failed attempt" in troubled.describe()
