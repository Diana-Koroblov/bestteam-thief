"""Typed failures for the network edge. Never a bare ``Exception`` (2.2.3).

The distinction is not tidiness, it decides what the runtime does next:

* ``AuthError`` — the opponent is not who the handshake said. Do **not** retry;
  retrying an unauthenticated peer is how a stranger gets a second attempt.
* ``TransportError`` — the network failed. Retrying is correct, within the
  gatekeeper's backoff budget.
* ``DeadlineError`` — we ran out of time. Retrying is *not* correct: the
  30-second response limit is already spent, and another attempt walks us into
  the watchdog and a technical loss worth 0 to both sides.

Catching a bare ``Exception`` at this boundary would collapse all three into
"something went wrong", and the only recovery that fits all three is to give up.
"""

from __future__ import annotations

__all__ = ["PeerError", "AuthError", "TransportError", "DeadlineError", "RemoteToolError"]


class PeerError(Exception):
    """Base for everything that can go wrong talking to the opponent."""


class AuthError(PeerError):
    """The peer could not be authenticated, or rejected our credentials."""


class TransportError(PeerError):
    """The message did not get there: connection refused, reset, DNS, TLS."""


class DeadlineError(PeerError):
    """No reply inside the agreed response window.

    Carries the budget so the log records what we actually waited for, rather
    than leaving a dispute about whether the opponent was slow or we were
    impatient.
    """

    def __init__(self, tool: str, seconds: float) -> None:
        super().__init__(f"{tool!r} exceeded the {seconds:g}s response deadline")
        self.tool = tool
        self.seconds = seconds


class RemoteToolError(PeerError):
    """The opponent's server accepted the call and answered with an error.

    Distinct from a transport failure: the network worked. Usually this is their
    ``ProtocolError`` coming back to us, which means our payload was wrong — so
    the message is preserved verbatim for the log.
    """

    def __init__(self, tool: str, detail: str) -> None:
        super().__init__(f"{tool!r} was rejected by the opponent: {detail}")
        self.tool = tool
        self.detail = detail
