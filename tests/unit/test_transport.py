"""Unit tests for the transport edge (TODO 2.2).

Two invariants carry the weight: a peer can address **exactly one** opponent
(M#4), and every failure arrives as a *named* type, because the right recovery
differs for each and "something went wrong" admits none of them.

The client's *decoding* is unit-tested here against its classification helpers.
The full request path is covered by ``tests/integration/test_localhost_roundtrip.py``,
which drives a real FastMCP server over the real MCP protocol — because the
transport bug this layer once had was invisible to any mocked HTTP test.
"""

from __future__ import annotations

import dataclasses
import inspect
from pathlib import Path

import httpx
import pytest

from core.infra.errors import (
    AuthError,
    DeadlineError,
    PeerError,
    RemoteToolError,
    TransportError,
)
from core.infra.mcp_client import OpponentClient
from core.infra.mcp_server import LISTEN_HOST, build_server_spec, create_server
from core.protocol.tools import TOOL_BUILDERS, build_guarded_tools, guard
from tests.unit.test_protocol import Recorder


def _tools() -> dict:
    """Guarded tools for a recorder handler, as the gateway would build them."""
    return build_guarded_tools(Recorder())


# --- the server spec --------------------------------------------------------


def test_the_server_binds_every_interface_not_loopback() -> None:
    """A tunnel forwards to the host interface; loopback is reachable from nowhere."""
    assert LISTEN_HOST == "0.0.0.0"  # noqa: S104 - the point of the test
    assert build_server_spec(_tools(), "cop", 8081).host == "0.0.0.0"  # noqa: S104


def test_the_server_registers_exactly_the_protocol_tools() -> None:
    """Registration is all this layer decides; the rules live in core.protocol."""
    spec = build_server_spec(_tools(), "bestteam-cop", 8081)
    assert spec.tool_names == tuple(sorted(TOOL_BUILDERS))


def test_the_spec_is_inspectable_without_starting_anything() -> None:
    spec = build_server_spec(_tools(), "bestteam-thief", 8082)
    assert (spec.name, spec.port) == ("bestteam-thief", 8082)
    assert all(callable(tool) for tool in spec.tools.values())


def test_creating_a_server_is_the_only_thing_that_needs_fastmcp() -> None:
    """The import is lazy, so every test above runs without it."""
    source = inspect.getsource(create_server)
    assert "from fastmcp import FastMCP" in source


def test_the_transport_imports_nothing_from_the_protocol_layer() -> None:
    """M#3: a transport that knew the rules would be a sideways dependency.

    This is the edge the import-graph test caught; the guard moved into
    ``core.protocol`` so the server can take plain callables.
    """
    import core.infra.mcp_server as module

    assert "core.protocol" not in Path(module.__file__).read_text(encoding="utf-8")


# --- what a malformed request from the opponent gets back ------------------


def test_a_protocol_error_comes_back_as_data_not_a_traceback() -> None:
    """Their bad payload is not our crash.

    Letting it escape would hand the opponent a stack trace and leave our own
    log with nothing but an exception. As data, both sides can see what was
    actually received — which is the whole remedy available without a referee.
    """
    guarded = _tools()["receive_reveal"]
    reply = guarded({"step": 1, "role": "cop", "move": "N", "nonce": "leak"})
    assert reply["error"] == "protocol"
    assert reply["tool"] == "receive_reveal"
    assert "must not carry a nonce" in reply["detail"]


def test_a_valid_request_passes_straight_through_the_guard() -> None:
    assert _tools()["receive_commit"]({"step": 1, "role": "thief", "digest": "abc"})["kind"] == "ack"


def test_the_guard_keeps_the_tool_name_so_registration_is_correct() -> None:
    """FastMCP registers by name; a wrapper that renamed the tool would break it."""
    assert _tools()["negotiate"].__name__ == "negotiate"


def test_the_guard_does_not_swallow_unexpected_failures() -> None:
    """Only ProtocolError becomes data. A real bug must still surface as one."""

    def broken(payload: dict) -> dict:
        raise RuntimeError("a genuine bug")

    with pytest.raises(RuntimeError, match="a genuine bug"):
        guard("boom", broken)({})


# --- exactly one opponent (M#4) --------------------------------------------


def test_no_client_method_accepts_a_url() -> None:
    """The single-opponent rule is structural, not a convention to remember."""
    for name, member in inspect.getmembers(OpponentClient, inspect.isfunction):
        if name.startswith("_"):
            continue
        parameters = set(inspect.signature(member).parameters)
        assert not parameters & {"url", "base_url", "host", "peer", "target"}, name


def test_the_opponent_target_is_fixed_at_construction() -> None:
    client = OpponentClient(base_url="https://a.test", timeout_sec=30)
    with pytest.raises(dataclasses.FrozenInstanceError):
        client.base_url = "https://b.test"  # type: ignore[misc]


def test_a_deadline_is_a_constructor_field_not_an_optional_argument() -> None:
    """Ch. 8.4.1: a request without a deadline is a frozen loop waiting to happen."""
    assert "timeout_sec" in {f.name for f in dataclasses.fields(OpponentClient)}
    assert "timeout" not in inspect.signature(OpponentClient.call).parameters


def test_a_trailing_slash_is_stripped_from_the_opponent_url() -> None:
    """FastMCP serves at /mcp, so /mcp/ costs a 307 redirect on every request.

    Seen in the M2 server log: a 307 before every 200. Locally that is noise;
    against a real opponent it doubles the round trips for every message of
    every turn, inside a 30-second budget.
    """
    assert OpponentClient("http://127.0.0.1:8082/mcp/", 30).target == "http://127.0.0.1:8082/mcp"
    assert OpponentClient("http://127.0.0.1:8082/mcp", 30).target == "http://127.0.0.1:8082/mcp"


def test_the_in_process_transport_wins_over_the_url_when_set() -> None:
    """Used for self-play and for the round-trip test; the URL stays for real matches."""
    sentinel = object()
    assert OpponentClient("https://a.test", 30, transport=sentinel).target is sentinel
    assert OpponentClient("https://a.test", 30).target == "https://a.test"


# --- every failure is named ------------------------------------------------


def test_a_structured_protocol_error_becomes_a_remote_tool_error() -> None:
    """The network worked; our payload did not. The detail is preserved verbatim."""
    body = {"error": "protocol", "tool": "receive_reveal", "detail": "must not carry a nonce"}
    with pytest.raises(RemoteToolError, match="must not carry a nonce") as caught:
        OpponentClient._decode("receive_reveal", body)
    assert caught.value.detail == "must not carry a nonce"


def test_a_non_object_reply_is_a_transport_error() -> None:
    """The protocol is objects; a list means we are talking to the wrong thing."""
    with pytest.raises(TransportError, match="expected an object"):
        OpponentClient._decode("x", [1, 2])


def test_a_plain_reply_passes_through() -> None:
    assert OpponentClient._decode("x", {"kind": "ack"}) == {"kind": "ack"}


def _classify(error: Exception, timeout: float = 30.0):
    return OpponentClient.classify("receive_commit", error, timeout)


@pytest.mark.parametrize("status", [401, 403])
def test_an_auth_failure_is_not_a_transport_failure(status: int) -> None:
    """Retrying an unauthenticated peer gives a stranger a second attempt."""
    response = httpx.Response(status, request=httpx.Request("POST", "https://x.test"))
    error = httpx.HTTPStatusError("refused", request=response.request, response=response)
    assert isinstance(_classify(error), AuthError)


@pytest.mark.parametrize("status", [400, 404, 500, 503])
def test_other_http_failures_are_transport_errors(status: int) -> None:
    response = httpx.Response(status, request=httpx.Request("POST", "https://x.test"))
    error = httpx.HTTPStatusError("bad", request=response.request, response=response)
    assert isinstance(_classify(error), TransportError)


@pytest.mark.parametrize(
    "error", [TimeoutError("slow"), httpx.ReadTimeout("slow", request=None)]
)
def test_a_timeout_becomes_a_deadline_and_reports_the_budget(error: Exception) -> None:
    """Not retryable: the window is spent and the watchdog is next."""
    failure = _classify(error, timeout=12.5)
    assert isinstance(failure, DeadlineError)
    assert failure.seconds == 12.5
    assert failure.tool == "receive_commit"


def test_a_remote_tool_failure_is_distinguished_from_a_network_fault() -> None:
    """FastMCP raises ToolError when the opponent's own tool failed."""

    class ToolError(Exception):
        pass

    assert isinstance(_classify(ToolError("boom")), RemoteToolError)
    assert isinstance(_classify(OSError("down")), TransportError)


def test_every_failure_shares_one_base_so_the_runtime_can_catch_narrowly() -> None:
    for error in (AuthError, TransportError, DeadlineError, RemoteToolError):
        assert issubclass(error, PeerError)
    assert not issubclass(PeerError, ValueError)
