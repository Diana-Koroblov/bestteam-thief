"""The four tools a reference peer expects, and the inboxes behind them.

Every tool here is a **mailbox**: it stores what arrived and returns
``{"ok": true}``. Nothing is answered, because under this protocol nothing can
be — the opponent's reply to our negotiation is a separate inbound call to this
same server, not the return value of ours.

**The parameter names are load-bearing.** The reference client sends
``{"message": ...}`` to three tools and ``{"payload": ...}`` to ``submit_audit``,
by name. A parameter called anything else is a tool their client cannot invoke,
and the failure surfaces as a bare MCP error mid-handshake.

**These replace our native six rather than joining them.** Both protocols spell
one tool ``negotiate`` and mean different things by it — different parameter
name, different return contract — so a server exposing both would answer that
call wrongly for one of the two. `--protocol reference` picks a side.
"""

from __future__ import annotations

import queue
from collections.abc import Callable
from typing import Any

__all__ = ["Inboxes", "build_reference_tools", "REFERENCE_TOOLS"]


class Inboxes:
    """What the opponent has pushed to us and we have not yet consumed.

    ``queue.Queue`` rather than a list: FastMCP may run a synchronous tool in a
    worker thread, so the producer is not reliably on the event loop that
    consumes. A thread-safe queue costs nothing here and removes a class of bug
    that would only ever appear against a real opponent under load.

    Attributes:
        agreements: Signed terms from the opponent's handshake.
        turns: Their ``TurnMessage``s. Receiving one passes us the turn token.
        audits: Their end-of-game ``AuditPayload``.
        controls: Advisory signals. Accepted and drained so a peer that sends
            them is not met with an error, and never acted on — our series is
            driven by our own plan, not by an opponent's restart request.
        held: Agreements that arrived stamped for a sub-game we had not reached
            yet, kept by that number until we do. **This object outlives the
            individual `ReferenceSession`s** — one is built per sub-game — which
            is exactly why the holding lives here and not on the session.
    """

    def __init__(self) -> None:
        """Start with four empty inboxes and nothing held."""
        self.agreements: queue.Queue = queue.Queue()
        self.turns: queue.Queue = queue.Queue()
        self.audits: queue.Queue = queue.Queue()
        self.controls: queue.Queue = queue.Queue()
        self.held: dict[int, dict] = {}

    def drain(self) -> None:
        """Discard everything pending except agreements — held or queued.

        Called between sub-games. A turn left over from the sub-game just
        finished would be consumed as the opening move of the next one, and the
        board it describes no longer exists. Agreements are left alone because
        the opponent may legitimately have re-negotiated already, and `held` is
        left alone because its whole purpose is to survive this call.
        """
        for inbox in (self.turns, self.audits, self.controls):
            while True:
                try:
                    inbox.get_nowait()
                except queue.Empty:
                    break


def build_reference_tools(inboxes: Inboxes) -> dict[str, Callable[..., Any]]:
    """Return the four reference tools, bound to *inboxes*.

    Deliberately unguarded by `protocol.tools.guard`: that helper turns a
    ``ProtocolError`` into a structured reply, and there is no validation here
    to fail. A mailbox that inspected its mail would be re-implementing the
    turn loop in the transport, which is the one thing M#3 forbids.
    """

    def negotiate(message: dict) -> dict:
        """Receive the opponent's signed game agreement."""
        inboxes.agreements.put(message)
        return {"ok": True}

    def receive_turn(message: dict) -> dict:
        """Receive the opponent's turn — and with it, the turn token."""
        inboxes.turns.put(message)
        return {"ok": True}

    def submit_audit(payload: dict) -> dict:
        """Receive the opponent's end-of-game reveal: records and nonces."""
        inboxes.audits.put(payload)
        return {"ok": True}

    def receive_control(message: dict) -> dict:
        """Receive an advisory control signal. Recorded, never obeyed."""
        inboxes.controls.put(message)
        return {"ok": True}

    return {
        "negotiate": negotiate,
        "receive_turn": receive_turn,
        "submit_audit": submit_audit,
        "receive_control": receive_control,
    }


# Named so a test can assert the surface without standing a server up, the way
# `TOOL_BUILDERS` does for the native protocol.
REFERENCE_TOOLS: tuple[str, ...] = (
    "negotiate", "receive_turn", "submit_audit", "receive_control",
)
