"""A2A coordination, alongside the MCP game protocol and never instead of it.

The Rulebook makes MCP the project requirement and A2A a *strongly recommended*
complement (Ch. 2.3, [9]). This package is that complement and nothing more: an
Agent Card and one message endpoint, both read-only, so a peer can ask "are you
up, what do you expose, what did you agree to" without opening a game.

**No move ever leaves through here.** Commits, reveals, barriers and captures go
through the six MCP tools, are sealed, and are replayable from the log. A move
arriving over an unaudited side channel is unauditable by construction, which is
why `answer` refuses one rather than politely ignoring it.

Nothing in this package imports Starlette, FastMCP or a socket — the same rule
`core/protocol` follows, and for the same reason: the content of a card and the
content of a reply are decidable at a desk, and a test for them should not need
a port. The transport adapts these responders in `core/infra/mcp_server.py`;
the gateway joins the two in `core/sdk/peer_sdk.py` (M#3).
"""

from __future__ import annotations

from core.a2a.card import agent_card
from core.a2a.coordination import Coordination
from core.a2a.readiness import CARD_PATHS, MESSAGE_PATHS, Readiness, match_facts

__all__ = [
    "CARD_PATHS",
    "MESSAGE_PATHS",
    "Coordination",
    "Readiness",
    "agent_card",
    "match_facts",
]
