"""Unit tests for the transport edge (TODO 2.2).

Two invariants carry the weight: a peer can address **exactly one** opponent
(M#4), and every failure arrives as a *named* type, because the right recovery
differs for each and "something went wrong" admits none of them.

The client is exercised through ``httpx.MockTransport`` rather than a live
socket — real ports make tests slow and flaky, and what needs testing here is
the decoding, not TCP.
"""

from __future__ import annotations

import dataclasses
import inspect

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
from core.infra.mcp_server import (
    LISTEN_HOST,
    _wrap,
    build_server_spec,
    create_server,
)
from core.protocol.tools import TOOL_BUILDERS
from tests.unit.test_protocol import Recorder


@pytest.fixture(autouse=True)
def _restore_httpx():
    """Put ``httpx.post`` back however the test ended, including on failure."""
    original = httpx.post
    yield
    httpx.post = original


def _client_over(handler, timeout: float = 30.0) -> OpponentClient:
    """Return a client whose requests are answered by *handler* in-process.

    ``httpx.MockTransport`` runs the whole request path — headers, timeouts,
    status codes, JSON decoding — with no socket. Real ports would make these
    tests slow and flaky, and what needs testing here is the decoding, not TCP.
    """
    transport = httpx.MockTransport(handler)

    def patched(url, **kwargs):
        with httpx.Client(transport=transport) as session:
            return session.post(url, **kwargs)

    httpx.post = patched
    return OpponentClient(base_url="https://opponent.test", timeout_sec=timeout, team="bestteam")


# --- the server spec --------------------------------------------------------


def test_the_server_binds_every_interface_not_loopback() -> None:
    """A tunnel forwards to the host interface; loopback is reachable from nowhere."""
    assert LISTEN_HOST == "0.0.0.0"  # noqa: S104 - the point of the test
    assert build_server_spec(Recorder(), "cop", 8081).host == "0.0.0.0"  # noqa: S104


def test_the_server_registers_exactly_the_protocol_tools() -> None:
    """Registration is all this layer decides; the rules live in core.protocol."""
    spec = build_server_spec(Recorder(), "bestteam-cop", 8081)
    assert spec.tool_names == tuple(sorted(TOOL_BUILDERS))


def test_the_spec_is_inspectable_without_starting_anything() -> None:
    spec = build_server_spec(Recorder(), "bestteam-thief", 8082)
    assert (spec.name, spec.port) == ("bestteam-thief", 8082)
    assert all(callable(tool) for tool in spec.tools.values())


def test_creating_a_server_is_the_only_thing_that_needs_fastmcp() -> None:
    """The import is lazy, so every test above runs without it."""
    source = inspect.getsource(create_server)
    assert "from fastmcp import FastMCP" in source


# --- what a malformed request from the opponent gets back ------------------


def test_a_protocol_error_comes_back_as_data_not_a_traceback() -> None:
    """Their bad payload is not our crash.

    Letting it escape would hand the opponent a stack trace and leave our own
    log with nothing but an exception. As data, both sides can see what was
    actually received — which is the whole remedy available without a referee.
    """
    spec = build_server_spec(Recorder(), "cop", 8081)
    guarded = _wrap("receive_reveal", spec.tools["receive_reveal"])
    reply = guarded({"step": 1, "role": "cop", "move": "N", "nonce": "leak"})
    assert reply["error"] == "protocol"
    assert reply["tool"] == "receive_reveal"
    assert "must not carry a nonce" in reply["detail"]


def test_a_valid_request_passes_straight_through_the_guard() -> None:
    spec = build_server_spec(Recorder(), "cop", 8081)
    guarded = _wrap("receive_commit", spec.tools["receive_commit"])
    assert guarded({"step": 1, "role": "thief", "digest": "abc"})["kind"] == "ack"


def test_the_guard_keeps_the_tool_name_so_registration_is_correct() -> None:
    """FastMCP registers by name; a wrapper that renamed the tool would break it."""
    spec = build_server_spec(Recorder(), "cop", 8081)
    assert _wrap("negotiate", spec.tools["negotiate"]).__name__ == "negotiate"


def test_the_guard_does_not_swallow_unexpected_failures() -> None:
    """Only ProtocolError becomes data. A real bug must still surface as one."""

    def broken(payload: dict) -> dict:
        raise RuntimeError("a genuine bug")

    with pytest.raises(RuntimeError, match="a genuine bug"):
        _wrap("boom", broken)({})


# --- exactly one opponent (M#4) --------------------------------------------


def test_no_client_method_accepts_a_url() -> None:
    """The single-opponent rule is structural, not a convention to remember."""
    for name, member in inspect.getmembers(OpponentClient, inspect.isfunction):
        if name.startswith("_"):
            continue
        parameters = set(inspect.signature(member).parameters)
        assert not parameters & {"url", "base_url", "host", "peer", "target"}, name


def test_the_opponent_url_is_fixed_at_construction() -> None:
    client = OpponentClient(base_url="https://a.test", timeout_sec=30)
    with pytest.raises(dataclasses.FrozenInstanceError):
        client.base_url = "https://b.test"  # type: ignore[misc]


def test_every_call_carries_the_agreed_deadline() -> None:
    """Ch. 8.4.1: a request without a deadline is a frozen loop waiting to happen."""
    seen: dict[str, object] = {}

    def record(request: httpx.Request) -> httpx.Response:
        seen["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, json={"ok": True})

    _client_over(record, timeout=12.5).call("negotiate", {"step": 0})
    assert seen["timeout"]["connect"] == 12.5


def test_the_team_name_is_sent_so_the_opponent_can_recognise_us() -> None:
    seen: dict[str, object] = {}

    def record(request: httpx.Request) -> httpx.Response:
        seen["team"] = request.headers.get("X-Team")
        return httpx.Response(200, json={"ok": True})

    _client_over(record).call("negotiate", {"step": 0})
    assert seen["team"] == "bestteam"


def test_the_tool_name_becomes_the_path() -> None:
    seen: dict[str, object] = {}

    def record(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        return httpx.Response(200, json={"ok": True})

    _client_over(record).call("receive_commit", {"step": 1})
    assert seen["path"] == "/tools/receive_commit"


# --- every failure is named ------------------------------------------------


def test_a_successful_reply_is_returned_as_a_dict() -> None:
    reply = _client_over(lambda _: httpx.Response(200, json={"kind": "ack"})).call("x", {})
    assert reply == {"kind": "ack"}


def test_a_timeout_raises_deadline_and_reports_the_budget() -> None:
    """Not retryable: the window is spent and the watchdog is next."""

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(DeadlineError, match="exceeded the 30s response deadline") as caught:
        _client_over(timeout).call("receive_commit", {})
    assert caught.value.seconds == 30
    assert caught.value.tool == "receive_commit"


@pytest.mark.parametrize("status", [401, 403])
def test_an_auth_failure_is_not_a_transport_failure(status: int) -> None:
    """Retrying an unauthenticated peer gives a stranger a second attempt."""
    with pytest.raises(AuthError, match="was refused"):
        _client_over(lambda _: httpx.Response(status)).call("negotiate", {})


@pytest.mark.parametrize("status", [400, 404, 500, 503])
def test_other_http_failures_are_transport_errors(status: int) -> None:
    with pytest.raises(TransportError, match=f"HTTP {status}"):
        _client_over(lambda _: httpx.Response(status)).call("negotiate", {})


def test_an_unreachable_opponent_is_a_transport_error() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(TransportError, match="could not reach"):
        _client_over(refuse).call("negotiate", {})


def test_a_non_json_reply_is_a_transport_error() -> None:
    with pytest.raises(TransportError, match="non-JSON body"):
        _client_over(lambda _: httpx.Response(200, text="<html>oops</html>")).call("x", {})


def test_a_json_array_is_refused() -> None:
    """The protocol is objects; a list means we are talking to the wrong thing."""
    with pytest.raises(TransportError, match="expected an object"):
        _client_over(lambda _: httpx.Response(200, json=[1, 2])).call("x", {})


def test_a_structured_protocol_error_comes_back_as_remote_tool_error() -> None:
    """The network worked; our payload did not. The detail is preserved verbatim."""
    body = {"error": "protocol", "tool": "receive_reveal", "detail": "must not carry a nonce"}
    with pytest.raises(RemoteToolError, match="must not carry a nonce") as caught:
        _client_over(lambda _: httpx.Response(200, json=body)).call("receive_reveal", {})
    assert caught.value.detail == "must not carry a nonce"


def test_every_failure_shares_one_base_so_the_runtime_can_catch_narrowly() -> None:
    for error in (AuthError, TransportError, DeadlineError, RemoteToolError):
        assert issubclass(error, PeerError)
    assert not issubclass(PeerError, ValueError)
