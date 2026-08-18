"""The tunnel lifecycle (TODO 5.1.1, 5.1.2, PRD 5 §7 T5.1, T5.2, T5.6).

**No test here opens a real tunnel** — PRD 5 §5 forbids it, and a suite that
needed an ngrok account could not run in CI or on a machine without one. The
process, the agent's API and the clock are all constructor fields, so every
path including the failures is exercised against fakes in microseconds.

The failure paths are the reason this file is long. They fire only when
something has already gone wrong at the worst moment — during a graded match —
which makes them the least likely to be hit by accident in development and the
most expensive to get wrong.
"""

from __future__ import annotations

import shutil

import pytest

from core.infra import tunnel as tunnel_module
from core.infra.tunnel import (
    PROVIDERS,
    STARTUP_POLLS,
    TunnelError,
    TunnelManager,
    build_command,
)

DOMAIN = "denotatively-sciuroid-florine.ngrok-free.dev"
PUBLISHED = f"https://{DOMAIN}"


class FakeProcess:
    """Stands in for a running agent. Implements only what the manager touches."""

    def __init__(self, exit_code: int | None = None) -> None:
        self.returncode = exit_code
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = -15

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode or 0

    def kill(self) -> None:  # pragma: no cover - only a hung agent reaches this
        self.killed = True


class Spawner:
    """Records every spawn and hands back the next prepared process."""

    def __init__(self, *processes: FakeProcess) -> None:
        self.queue = list(processes) or [FakeProcess()]
        self.commands: list[tuple[str, ...]] = []
        self.envs: list[dict[str, str]] = []

    def __call__(self, command, env) -> FakeProcess:
        self.commands.append(tuple(command))
        self.envs.append(env)
        return self.queue[min(len(self.commands), len(self.queue)) - 1]


@pytest.fixture
def binary_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend the agent is installed, so the suite runs on a bare machine."""
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")


def build(spawner: Spawner, **fields) -> tuple[TunnelManager, list[float]]:
    """Return a manager wired to fakes, plus the list its sleeps land in."""
    slept: list[float] = []
    defaults = {
        "authtoken": "tok_secret_value",
        "port": 8081,
        "domain": DOMAIN,
        "probe": lambda api_port: PUBLISHED,
    }
    manager = TunnelManager(
        spawn=spawner, sleep=slept.append, **{**defaults, **fields}
    )
    return manager, slept


# --- starting ---------------------------------------------------------------


def test_start_returns_the_url_the_agent_published(binary_present) -> None:
    """**T5.1.** Read back from the agent, never computed from config.

    The manager is given one domain and the agent reports another. Returning
    the agent's answer is what makes a tunnel that failed to start look
    different from one that worked — a distinction that otherwise only surfaces
    when the opponent cannot reach us, mid-match.
    """
    manager, _ = build(Spawner(), domain="stale.ngrok-free.dev", probe=lambda api_port: PUBLISHED)
    assert manager.start() == PUBLISHED


def test_the_static_domain_is_pinned_on_the_command_line(binary_present) -> None:
    spawner = Spawner()
    manager, _ = build(spawner)
    manager.start()
    assert spawner.commands[0][:5] == ("ngrok", "http", "127.0.0.1:8081", "--url", DOMAIN)


def test_without_a_domain_the_url_flag_is_dropped_entirely(binary_present) -> None:
    """Not passed empty. `--url ''` is an argument error, not a random URL."""
    spawner = Spawner()
    manager, _ = build(spawner, domain=None)
    manager.start()
    assert spawner.commands[0][:3] == ("ngrok", "http", "127.0.0.1:8081")
    assert "--url" not in spawner.commands[0]




def test_the_authtoken_never_reaches_the_command_line(binary_present) -> None:
    """**M#39.** Every process on the machine can read another's argv.

    A token passed as an argument is a token in the process table, readable by
    anything running as this user. It goes in the child's environment instead.
    """
    spawner = Spawner()
    manager, _ = build(spawner)
    manager.start()
    assert not any("tok_secret_value" in arg for arg in spawner.commands[0])
    assert spawner.envs[0]["NGROK_AUTHTOKEN"] == "tok_secret_value"


def test_starting_twice_does_not_spawn_a_second_agent(binary_present) -> None:
    """Two agents on one port leaves the opponent talking to whichever won."""
    spawner = Spawner()
    manager, _ = build(spawner)
    assert manager.start() == manager.start()
    assert len(spawner.commands) == 1


# --- refusing to start ------------------------------------------------------


def test_a_missing_authtoken_is_a_readable_error(binary_present) -> None:
    """**T5.6.** A stack trace at match time tells nobody what to do."""
    manager, _ = build(Spawner(), authtoken="  ")
    with pytest.raises(TunnelError, match="NGROK_AUTHTOKEN"):
        manager.start()


def test_a_missing_binary_says_how_to_install_it(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    manager, _ = build(Spawner())
    with pytest.raises(TunnelError, match="winget install ngrok.ngrok"):
        manager.start()


def test_an_unknown_provider_lists_the_ones_that_exist() -> None:
    manager, _ = build(Spawner(), provider="ngroc")
    with pytest.raises(TunnelError, match="localtonet, ngrok"):
        manager.start()


def test_an_agent_that_dies_during_startup_is_reported_at_once(binary_present) -> None:
    """The ten-second budget spent on an already-dead process learns nothing."""
    manager, slept = build(Spawner(FakeProcess(exit_code=1)), probe=lambda api_port: None)
    with pytest.raises(TunnelError, match="exited before publishing"):
        manager.start()
    assert slept == []


def test_an_agent_that_never_publishes_gives_up_and_cleans_up(binary_present) -> None:
    """A tunnel we cannot confirm is not a tunnel; the agent is not left behind."""
    process = FakeProcess()
    manager, slept = build(Spawner(process), probe=lambda api_port: None)
    with pytest.raises(TunnelError, match="no public URL within"):
        manager.start()
    assert len(slept) == STARTUP_POLLS
    assert process.terminated


def test_a_failed_start_never_leaves_a_live_agent_behind(binary_present) -> None:
    """Otherwise the *next* start finds one and returns an empty URL.

    `start()` short-circuits when the agent is already running. If a crashing
    probe left the process up, that short circuit would hand the caller `""` —
    a peer that believes it is exposed at nothing, and an opponent who cannot
    reach it. Any failure therefore tears the process down.
    """

    def explode(api_port: int) -> str:
        raise OSError("the agent API refused the connection")

    process = FakeProcess()
    manager, _ = build(Spawner(process), probe=explode)
    with pytest.raises(OSError, match="refused the connection"):
        manager.start()
    assert process.terminated
    assert not manager.is_alive()


# --- restarting and stopping ------------------------------------------------


def test_restart_returns_the_same_static_domain(binary_present) -> None:
    """**T5.2.** The whole reason for reserving one.

    A restart mid-series leaves the address the opponent already stored still
    valid; a rotating URL would strand them at a dead endpoint.
    """
    spawner = Spawner(FakeProcess(), FakeProcess())
    manager, _ = build(spawner)
    first = manager.start()
    assert manager.restart() == first
    assert len(spawner.commands) == 2


def test_liveness_tracks_the_process(binary_present) -> None:
    manager, _ = build(Spawner())
    assert not manager.is_alive()
    manager.start()
    assert manager.is_alive()
    manager.stop()
    assert not manager.is_alive()


def test_stopping_nothing_is_safe() -> None:
    """`stop()` runs in a `finally` on a peer that may never have started one."""
    manager, _ = build(Spawner())
    manager.stop()
    manager.stop()


def test_the_url_survives_being_stopped(binary_present) -> None:
    """It names the domain we reserved, not the process; the report runs after."""
    manager, _ = build(Spawner())
    manager.start()
    manager.stop()
    assert manager.url == PUBLISHED


# --- configuration ----------------------------------------------------------


def test_the_fallback_provider_is_selected_by_config_alone(binary_present) -> None:
    """**5.1.2.** Switching providers must never be a code change."""
    spawner = Spawner()
    manager, _ = build(spawner, provider="localtonet")
    manager.start()
    assert spawner.commands[0][0] == "localtonet"
    assert spawner.envs[0]["LOCALTONET_AUTHTOKEN"] == "tok_secret_value"


def test_from_config_reads_the_private_network_section(minimal_config) -> None:
    """Local settings only: the opponent never sees or agrees to any of these."""
    manager = TunnelManager.from_config(minimal_config, "tok")
    assert manager.port == minimal_config.require("network.listen_port")
    assert manager.provider in PROVIDERS


def test_an_overridden_port_moves_the_tunnel_with_the_server(minimal_config) -> None:
    """Otherwise `--port` publishes a domain that forwards nowhere."""
    manager = TunnelManager.from_config(minimal_config, "tok", port=9999)
    assert build_command(manager.spec, manager.port, manager.domain)[2] == "127.0.0.1:9999"


def test_every_provider_reads_its_token_from_its_own_variable() -> None:
    """A shared name would silently start an unauthenticated fallback."""
    assert len({provider.token_env for provider in PROVIDERS.values()}) == len(PROVIDERS)
    assert tunnel_module.PROVIDERS["ngrok"].token_env == "NGROK_AUTHTOKEN"
