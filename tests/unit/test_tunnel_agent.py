"""Unit tests for core/infra/tunnel_agent.py — the per-agent config file and
probe port that make two concurrent ngrok agents (one reserved domain per
role, both up for a whole match) actually work. Both facts measured live on
14/08 with two real accounts; see the module docstring for the full story.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from core.infra.tunnel import TunnelManager
from core.infra.tunnel_agent import agent_api_url, write_agent_config
from tests.unit.test_tunnel import FakeProcess, Spawner


@pytest.fixture
def binary_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pretend the agent is installed, so the suite runs on a bare machine."""
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")


def test_the_agent_config_moves_the_api_and_carries_no_token(tmp_path: Path) -> None:
    """The file displaces ngrok's default config, whose token BEATS the
    environment variable (measured: a second account's own reserved domain
    died with ERR_NGROK_320 under the default file). It must therefore hold
    the web_addr and nothing secret."""
    path = Path(write_agent_config(4041, tmp_path))
    text = path.read_text(encoding="utf-8")
    assert "127.0.0.1:4041" in text
    assert "authtoken" not in text


def test_the_manager_passes_the_config_and_keeps_the_token_in_the_env(
    binary_present,
) -> None:
    spawner = Spawner()
    manager = TunnelManager(
        authtoken="tok_secret_value", port=8082, domain="second.ngrok-free.dev",
        api_port=4041, spawn=spawner, probe=lambda api_port: "https://second.ngrok-free.dev",
        sleep=lambda seconds: None,
    )
    manager.start()
    command = spawner.commands[0]
    assert "--config" in command
    config_text = Path(command[command.index("--config") + 1]).read_text(encoding="utf-8")
    assert "4041" in config_text
    assert "tok_secret_value" not in config_text  # the token stays in the env (M#39)
    assert "tok_secret_value" in spawner.envs[0].values()


def test_the_probe_is_asked_at_this_agents_own_port(binary_present) -> None:
    """Reading a fixed 4040 with two agents up hands one role the other's URL,
    which it would then announce as its own door."""
    asked: list[int] = []

    def probe(api_port: int) -> str:
        asked.append(api_port)
        return "https://second.ngrok-free.dev"

    manager = TunnelManager(
        authtoken="tok", port=8082, domain="second.ngrok-free.dev", api_port=4041,
        spawn=Spawner(FakeProcess()), probe=probe, sleep=lambda seconds: None,
    )
    manager.start()
    assert asked == [4041]


def test_the_api_url_names_the_port_it_was_given() -> None:
    assert agent_api_url(4041) == "http://127.0.0.1:4041/api/tunnels"
