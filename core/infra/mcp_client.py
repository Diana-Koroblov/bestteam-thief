"""The client that talks to our opponent — and to nobody else.

M#4 requires each peer to address exactly one other peer. That is enforced here
structurally: the URL is set once at construction and there is **no method that
takes a URL**. A second opponent is not something this class can be persuaded
to do; it would require a second client, which the runtime never builds.

Every call carries a deadline (Ch. 8.4.1). A request without one is the direct
route to a frozen game loop: the process waits, the watchdog fires, and the
match is a technical loss worth 0 to *both* teams. So the deadline is a
constructor argument, not an optional parameter someone can forget.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from core.infra.errors import AuthError, DeadlineError, RemoteToolError, TransportError

__all__ = ["OpponentClient"]


@dataclass(frozen=True)
class OpponentClient:
    """A one-way channel to the single opponent of this match.

    Attributes:
        base_url: The opponent's public MCP endpoint, from the handshake.
        timeout_sec: The agreed response window (``response_timeout_sec``, 30 s
            by default). Applies to every call without exception.
        team: Our team name, sent so the opponent can recognise us.
    """

    base_url: str
    timeout_sec: float
    team: str = ""

    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Invoke *tool* on the opponent and return its reply.

        Args:
            tool: The remote tool name, e.g. ``receive_commit``.
            payload: The message body, already canonical.

        Returns:
            The decoded reply.

        Raises:
            DeadlineError: No answer inside ``timeout_sec``. Not retryable —
                the window is spent, and another attempt walks into the watchdog.
            AuthError: 401 or 403. Not retryable; retrying an unauthenticated
                peer just gives a stranger a second attempt.
            TransportError: The request never completed, or the reply was not
                JSON. Retryable within the gatekeeper's backoff budget.
            RemoteToolError: The opponent answered with a structured error. The
                network worked; our payload did not.
        """
        url = f"{self.base_url.rstrip('/')}/tools/{tool}"
        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=self.timeout_sec,
                headers={"X-Team": self.team} if self.team else None,
            )
        except httpx.TimeoutException as error:
            raise DeadlineError(tool, self.timeout_sec) from error
        except httpx.HTTPError as error:
            raise TransportError(f"{tool!r} could not reach {url}: {error}") from error

        return self._decode(tool, response)

    @staticmethod
    def _decode(tool: str, response: httpx.Response) -> dict[str, Any]:
        """Turn an HTTP response into a reply or the right typed failure."""
        if response.status_code in (401, 403):
            raise AuthError(f"{tool!r} was refused: HTTP {response.status_code}")
        if response.status_code >= 400:
            raise TransportError(f"{tool!r} returned HTTP {response.status_code}")

        try:
            body = response.json()
        except ValueError as error:
            raise TransportError(f"{tool!r} returned a non-JSON body") from error

        if isinstance(body, dict) and body.get("error") == "protocol":
            raise RemoteToolError(tool, body.get("detail", "no detail given"))
        if not isinstance(body, dict):
            raise TransportError(f"{tool!r} returned {type(body).__name__}, expected an object")
        return body
