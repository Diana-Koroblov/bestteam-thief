"""Unit tests for the SDK facade and the CLI (TODO 2.3.3, 2.3.4).

The facade exists so the engine stays replaceable. A UI holding a live
``GameState`` turns an internal detail into a public contract by accident, and
would render last turn's board while claiming to show this one.
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from core import __main__ as cli
from core.protocol.schemas import Role
from core.sdk.peer_sdk import BoardView, PeerSDK
from tests.paths import PRESENT_ROLES, role_dir

_ROLE = {"police": Role.COP, "thief": Role.THIEF}


@pytest.fixture(params=PRESENT_ROLES)
def sdk(request) -> PeerSDK:
    """One SDK per role this repository actually ships."""
    return PeerSDK(role_dir(request.param), _ROLE[request.param])


# --- the facade -------------------------------------------------------------


def test_the_board_view_carries_only_plain_types(sdk: PeerSDK) -> None:
    """No engine object escapes, so the engine stays free to change shape."""
    view = sdk.board_view()
    assert isinstance(view, BoardView)
    for member in fields(BoardView):
        value = getattr(view, member.name)
        assert isinstance(value, (int, tuple)), member.name


def test_the_view_reports_the_negotiated_board_and_quota(sdk: PeerSDK) -> None:
    view = sdk.board_view()
    assert view.grid_size == 7
    assert view.barriers_remaining == 14
    assert view.step == 0


def test_the_digest_is_the_one_the_handshake_compares(sdk: PeerSDK) -> None:
    assert len(sdk.config_digest) == 64


def test_legal_moves_are_from_our_own_position(sdk: PeerSDK) -> None:
    """The cop starts cornered with three options; the thief has all five."""
    moves = sdk.legal_moves()
    assert moves[0] == "STAY"
    assert len(moves) == (3 if sdk.role is Role.COP else 5)


def test_room_and_exits_are_exposed_because_they_decide_barrier_safety(
    sdk: PeerSDK,
) -> None:
    """A cop whose region no longer holds the thief has already lost."""
    assert sdk.own_room() == 49
    assert sdk.own_exits() == (2 if sdk.role is Role.COP else 4)


def test_connecting_goes_through_the_facade(sdk: PeerSDK) -> None:
    sdk.connect("https://opponent.test")
    with pytest.raises(RuntimeError, match="exactly one other peer"):
        sdk.connect("https://second.test")


def test_the_runtime_is_reachable_for_tool_registration(sdk: PeerSDK) -> None:
    assert hasattr(sdk.runtime, "on_commit")


def test_the_tunnel_reads_the_token_its_provider_actually_uses(
    sdk: PeerSDK, monkeypatch
) -> None:
    """**TODO 5.1.1.** Which variable holds the token depends on the provider.

    A caller that hardcoded ``NGROK_AUTHTOKEN`` would silently start an
    unauthenticated fallback the day `[network] tunnel_provider` changed, so
    the facade resolves it from the provider rather than from a constant.
    """
    monkeypatch.setenv("NGROK_AUTHTOKEN", "tok_from_the_environment")
    manager = sdk.tunnel()
    assert manager.spec.token_env == "NGROK_AUTHTOKEN"
    assert manager.authtoken == "tok_from_the_environment"


def test_an_absent_token_is_not_an_error_until_the_tunnel_starts(
    sdk: PeerSDK, monkeypatch
) -> None:
    """Building the manager to inspect it stays free; `start()` is what refuses."""
    monkeypatch.delenv("NGROK_AUTHTOKEN", raising=False)
    monkeypatch.setattr("core.shared.env.load_env", lambda *a, **k: False)
    assert sdk.tunnel().authtoken == ""


def test_the_tunnel_follows_an_overridden_port(sdk: PeerSDK) -> None:
    """Otherwise `--port` publishes a domain that forwards nowhere."""
    assert sdk.tunnel(port=9999).port == 9999


def test_the_ui_layer_never_reaches_past_the_facade() -> None:
    """Excellence guide §4.1, checked literally rather than remembered."""
    ui = Path(__file__).resolve().parents[2] / "core" / "ui"
    for module in ui.rglob("*.py"):
        text = module.read_text(encoding="utf-8")
        assert "from core.runtime" not in text, module.name
        assert "from core.protocol" not in text, module.name
        assert "from core.infra" not in text, module.name


# --- the CLI ----------------------------------------------------------------


def test_the_role_flag_is_required() -> None:
    """A peer that guessed its own role could be started twice as one side."""
    with pytest.raises(SystemExit):
        cli.main(["peer"])


def test_an_unknown_role_is_refused() -> None:
    with pytest.raises(SystemExit):
        cli.main(["peer", "--role", "referee"])


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_each_shipped_role_starts_and_reports(role: str, capsys) -> None:
    name = "police" if role == "police" else "thief"
    assert cli.main(["peer", "--role", name, "--dry-run"]) == 0
    printed = capsys.readouterr().out
    assert "config digest" in printed
    assert "board           : 7x7" in printed


def test_cop_is_accepted_as_an_alias_for_police() -> None:
    assert "cop" in cli.CONFIG_DIRS
    assert cli.CONFIG_DIRS["cop"] == "police"


def test_a_role_this_repository_does_not_ship_fails_clearly(monkeypatch, tmp_path) -> None:
    """Each published repository holds one role; asking for the other must say so."""
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    with pytest.raises(SystemExit, match="one role only"):
        cli.main(["peer", "--role", "thief", "--dry-run"])


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_an_opponent_url_is_attached_when_given(role: str, capsys) -> None:
    name = "police" if role == "police" else "thief"
    assert cli.main(["peer", "--role", name, "--opponent", "https://x.test", "--dry-run"]) == 0
    assert "opponent        : https://x.test" in capsys.readouterr().out


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_without_dry_run_the_peer_says_it_is_wired_but_not_playing(role: str, capsys) -> None:
    """The turn loop is Phase 3. Saying so beats appearing to hang."""
    name = "police" if role == "police" else "thief"
    assert cli.main(["peer", "--role", name]) == 0
    assert "not yet playing" in capsys.readouterr().out
