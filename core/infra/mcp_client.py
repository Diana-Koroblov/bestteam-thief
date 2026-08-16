"""The MCP client that talks to our opponent — and to nobody else.

**Corrected 31/07.** The first version posted plain JSON to ``/tools/<name>``.
That is not MCP, and no opponent's server would have answered it: FastMCP speaks
JSON-RPC over streamable HTTP, so the two peers would have failed to connect at
all. The project is specified over MCP; the client now uses ``fastmcp.Client``.

M#4 is enforced structurally: the target is set once at construction and there
is **no method that takes a URL**. A second opponent is not something this class
can be persuaded to do.

Every call carries a deadline (Ch. 8.4.1). A request without one is the direct
route to a frozen game loop: the process waits, the watchdog fires, and the
match is a technical loss worth 0 to *both* teams. So the deadline is a
constructor field, not an optional argument someone can forget.

**The session is opened once and held for the whole match.** Until 08/08 every
call ran `async with Client(...)`, which is one MCP session per message: an
initialize POST, a notification POST, a GET for the event stream, the tool POST
and a DELETE — six connections to send one move, and the stream occupies one of
them so the rest cannot reuse it. Both halves of a turn are then ~12 connections,
and a free ngrok tunnel allows about 120 a minute: measured, the edge stops
completing the TLS handshake at connection 123. Two full self-matches over the
real tunnel died at step 9 of sub-game 1 with `ConnectError` and nothing in the
agent's request log, because the connection never got far enough to become a
request. Both peers scored 0 for a network budget, not for anything either
strategy did. One held session sends one POST per message instead, which is the
protocol used as designed and roughly a tenfold cut in connections.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

import httpx

from core.infra.errors import (
    AuthError,
    DeadlineError,
    PeerError,
    RemoteToolError,
    TransportError,
)

# What the MCP client says when the peer restarted underneath us — the normal
# state at every sub-game boundary against a runner that starts a fresh process
# per sub-game, not a fault. `Session termination failed` is our own `aclose`
# posting a DELETE to a session that is already gone; `Error in post_writer` is
# the SDK's background writer noticing a 502 mid-flight while the opponent
# rebinds, catching it, logging a full traceback and closing the streams.
#
# Both are already handled: the failure reaches us as a `TransportError` on the
# next call and the retry loop redials. Neither log line changes what we do.
_EXPECTED_DISCONNECTS = ("Error in post_writer", "Session termination failed")


class _QuietExpectedDisconnects(logging.Filter):
    """Drop only the two known-benign records, never the rest of the logger.

    A blanket `setLevel` here would be the wrong tool twice over: the first
    attempt set ERROR, which did not suppress `logger.exception` at all, and
    raising it to CRITICAL would have hidden every genuine client error along
    with the noise. A filter matched on the message is narrow enough to keep
    real failures visible.

    Why bother silencing at all: these tracebacks print at exactly the moment a
    sub-game changes hands, so they land next to whatever else is happening and
    get blamed for it. That cost four separate misdiagnoses on 16/08, including
    two during live windows.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Return False — drop it — for the expected boundary chatter."""
        return not record.getMessage().startswith(_EXPECTED_DISCONNECTS)


def quieten_expected_disconnects() -> None:
    """Install the filter once. Safe to call repeatedly."""
    logger = logging.getLogger("mcp.client.streamable_http")
    if not any(isinstance(item, _QuietExpectedDisconnects) for item in logger.filters):
        logger.addFilter(_QuietExpectedDisconnects())


__all__ = ["quieten_expected_disconnects", "OpponentClient", "DEFAULT_CALLS_PER_MINUTE"]

# Outbound messages per minute, when the config names no figure. A free ngrok
# endpoint stops completing the TLS handshake at about 120 requests a minute —
# measured twice, at connection 123 both times, and the client sees a bare
# `ConnectError` with nothing in the agent's request log because the connection
# never became a request. Two peers on one LAN play about 1.4 steps a second at
# two messages a step, which is 168 a minute: over budget, and the sub-game dies
# around step 20 with a technical loss for both sides. 100 leaves headroom and
# costs 0.6 s a message against a 30 s response window.
DEFAULT_CALLS_PER_MINUTE = 100.0


@dataclass
class _Session:
    """The open MCP session, mutable so a frozen client can still hold one.

    `OpponentClient` is frozen because M#4 makes the target un-rebindable, not
    because a match should reconnect on every message. The connection is state,
    it belongs to the client that owns the target, and it lives here so that
    freezing the one keeps meaning what it says while the other can change.
    """

    client: Any = None
    session: Any = None
    last_call: float = 0.0


@dataclass(frozen=True)
class OpponentClient:
    """A one-way channel to the single opponent of this match.

    Attributes:
        base_url: The opponent's public MCP endpoint, from the handshake.
        timeout_sec: The agreed response window (``response_timeout_sec``).
            Applies to every call without exception.
        team: Our team name, sent as metadata so the opponent can recognise us.
        transport: An in-process FastMCP server, used instead of *base_url* when
            set. Exists so the round-trip can be exercised over the **real** MCP
            protocol with no socket — and so both our own roles can play each
            other locally during self-play.
    """

    base_url: str
    timeout_sec: float
    team: str = ""
    transport: Any = None
    calls_per_minute: float = DEFAULT_CALLS_PER_MINUTE
    # Not part of the client's identity: two clients aimed at the same opponent
    # are the same client whether or not either has connected yet.
    live: _Session = field(default_factory=_Session, compare=False, repr=False)

    @property
    def target(self) -> Any:
        """Return whatever ``fastmcp.Client`` should connect to.

        The trailing slash is stripped. FastMCP serves at ``/mcp``, so a URL
        ending ``/mcp/`` makes every single request a **307 redirect followed by
        the real request** — visible in the M2 server log as a 307 before each
        200. Harmless on localhost, but it doubles the round trips against a
        real opponent across the internet, on every message of every turn.
        """
        if self.transport is not None:
            return self.transport
        return self.base_url.rstrip("/") if self.base_url.endswith("/") else self.base_url

    async def call(
        self, tool: str, payload: dict[str, Any], argument: str = "payload"
    ) -> dict[str, Any]:
        """Invoke *tool* on the opponent and return its reply.

        Args:
            tool: The remote tool name, e.g. ``receive_commit``.
            payload: The message body, already canonical.
            argument: The **parameter name** the remote tool declares. Ours all
                take ``payload``; the reference implementation's take ``message``
                for everything except ``submit_audit`` (`core/compat/`). MCP
                binds arguments by name, so a tool invoked with the wrong one
                fails as an unrecognised call rather than a rejected message.

        Raises:
            DeadlineError: No answer inside ``timeout_sec``. Not retryable —
                the window is spent, and another attempt walks into the watchdog.
            AuthError: The peer refused our credentials. Not retryable; retrying
                an unauthenticated peer just gives a stranger a second attempt.
            TransportError: The call never completed. Retryable within the
                gatekeeper's backoff budget.
            RemoteToolError: The opponent answered with a structured error. The
                network worked; our payload did not.
        """
        await self._pace()
        session = await self._connect()
        try:
            result = await session.call_tool(
                tool, {argument: payload}, timeout=self.timeout_sec
            )
        except Exception as error:  # noqa: BLE001 - every path re-raises as a typed failure
            # A session that failed is not a session to send the next move on,
            # so it is dropped and the next call opens a fresh one.
            #
            # **Dropped, never retried.** A held session that fails at the
            # connection looks like "the socket was dead before we wrote", and
            # a retry looks free. It is not: the connection can equally break
            # after the opponent accepted the message and before its answer got
            # back, and then the retry sends a commit they already hold. Tried
            # on 08/08 and it cost a sub-game inside two minutes — the opponent
            # correctly refused with `step 0 was already committed; no second
            # attempt`, and a sub-game neither side played wrong was a technical
            # loss. Ch. 5.3 makes a commitment single-shot on purpose; nothing
            # at this layer may send one twice.
            await self.aclose()
            raise self.classify(tool, error, self.timeout_sec) from error

        return self._decode(tool, result.data)

    async def _pace(self) -> None:
        """Hold the message back until the tunnel can afford it.

        The budget belongs to the *endpoint*, not to either peer's opinion of a
        reasonable pace, and it is spent by whoever is fastest. Two of our own
        peers on one machine answer instantly and empty a free ngrok minute in
        forty seconds; against a real opponent the same loop runs at whatever
        the slower side allows, which may be just as fast.

        Deliberately paced *here* and not in the turn loop. The limit is a fact
        about the transport, so a driver, a rehearsal script or the closing
        exchange should not each have to remember it. The wait is bounded by
        one interval — 0.6 s at the default — against an agreed 30 s response
        window, so nothing here can talk us into a deadline (M#5). The
        in-process transport is exempt: it opens no connections and a test suite
        should not spend real seconds pretending it does.
        """
        if self.transport is not None or self.calls_per_minute <= 0:
            return
        interval = 60.0 / self.calls_per_minute
        waiting = interval - (time.monotonic() - self.live.last_call)
        if waiting > 0:
            await asyncio.sleep(waiting)
        self.live.last_call = time.monotonic()

    async def _connect(self) -> Any:
        """Return the open session, opening one if this is the first call."""
        from fastmcp import Client

        if self.live.session is None:
            client = Client(self.target)
            try:
                self.live.session = await client.__aenter__()
            except Exception as error:  # noqa: BLE001 - classified like any call failure
                raise self.classify("connect", error, self.timeout_sec) from error
            self.live.client = client
        return self.live.session

    async def aclose(self) -> None:
        """Close the session, if one is open. Safe to call more than once.

        Failures are swallowed: this runs on the error path and at the end of a
        match, and a peer that has already gone away must not turn tidying up
        into the exception that loses the sub-game it is tidying up after.
        """
        client, self.live.client, self.live.session = self.live.client, None, None
        if client is not None:
            with suppress(Exception):
                await client.__aexit__(None, None, None)

    @staticmethod
    def classify(tool: str, error: Exception, timeout_sec: float) -> PeerError:
        """Map any failure onto the type that says what to do next.

        One function so the mapping is testable without a network, and so a new
        failure mode has exactly one place to be classified rather than being
        absorbed by whichever ``except`` happened to be nearest.
        """
        if isinstance(error, (TimeoutError, httpx.TimeoutException)):
            return DeadlineError(tool, timeout_sec)
        if isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
            if status in (401, 403):
                return AuthError(f"{tool!r} was refused: HTTP {status}")
            return TransportError(f"{tool!r} returned HTTP {status}")
        # The streamable-http transport manufactures error code 32600 itself,
        # client-side, whenever a POST comes back HTTP 404 (mcp/client/
        # streamable_http.py `_handle_post_request`) — the spec's signal for
        # "this session id is no longer valid". The very first call has no
        # session yet, so a 404 there cannot be a real opponent rejecting us;
        # it is an offline tunnel, a wrong domain, or a peer who has not
        # started — connectivity facts, not a verdict, and exactly what
        # `greet()`'s retry loop (docs/MATCHDAY.md `--wait`) exists to wait
        # out. Misclassified as a refusal, it used to end the handshake on
        # the first attempt instead of retrying for the full `--wait` budget.
        if type(error).__name__ == "McpError":
            code = getattr(getattr(error, "error", None), "code", None)
            if code == 32600:
                return TransportError(f"{tool!r}: no MCP session at the opponent's URL yet")
            return RemoteToolError(tool, str(error))
        # FastMCP raises its own ToolError when the tool failed on the opponent's
        # side. That is a remote refusal, not a network fault, and the difference
        # decides whether retrying makes any sense at all.
        if type(error).__name__ == "ToolError":
            return RemoteToolError(tool, str(error))
        return TransportError(f"{tool!r} failed: {type(error).__name__}: {error}")

    @staticmethod
    def _decode(tool: str, data: Any) -> dict[str, Any]:
        """Turn a tool result into a reply, or the right typed failure."""
        if isinstance(data, dict) and data.get("error") == "protocol":
            raise RemoteToolError(tool, data.get("detail", "no detail given"))
        if not isinstance(data, dict):
            raise TransportError(
                f"{tool!r} returned {type(data).__name__}, expected an object"
            )
        return data
