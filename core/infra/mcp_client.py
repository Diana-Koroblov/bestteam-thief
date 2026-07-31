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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from core.infra.errors import (
    AuthError,
    DeadlineError,
    PeerError,
    RemoteToolError,
    TransportError,
)

__all__ = ["OpponentClient"]


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

    @property
    def target(self) -> Any:
        """Return whatever ``fastmcp.Client`` should connect to."""
        return self.transport if self.transport is not None else self.base_url

    async def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Invoke *tool* on the opponent and return its reply.

        Args:
            tool: The remote tool name, e.g. ``receive_commit``.
            payload: The message body, already canonical.

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
        from fastmcp import Client

        try:
            async with Client(self.target) as session:
                result = await session.call_tool(
                    tool, {"payload": payload}, timeout=self.timeout_sec
                )
        except Exception as error:  # noqa: BLE001 - every path re-raises as a typed failure
            raise self.classify(tool, error, self.timeout_sec) from error

        return self._decode(tool, result.data)

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
        # FastMCP raises its own ToolError when the tool failed on the opponent's
        # side. That is a remote refusal, not a network fault, and the difference
        # decides whether retrying makes any sense at all.
        if type(error).__name__ in ("ToolError", "McpError"):
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
