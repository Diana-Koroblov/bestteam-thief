"""The Agent Card, served at `/.well-known/agent-card.json`.

Discovery only: a peer that has never spoken to us fetches this to learn where
our endpoints are and what we claim to do. It is a `GET` with no body, which is
why it cannot be an MCP tool and has to be a plain HTTP route.

Everything in it comes from `Readiness`, so the card and the reply to a message
cannot drift apart — the two most obvious ways to tell an opponent two different
stories about the same match.
"""

from __future__ import annotations

from typing import Any

from core.a2a.readiness import EXTENSION_URI, MESSAGE_PATHS, Readiness, match_facts

__all__ = ["agent_card"]


def agent_card(ready: Readiness, base_url: str) -> dict[str, Any]:
    """Return the Agent Card as JSON, addressed for whoever is asking.

    Args:
        ready: What we publish about ourselves.
        base_url: The origin this request arrived on, no trailing slash. Never
            our own config — see `match_facts`.
    """
    return {
        "protocolVersion": "0.3.0",
        "name": ready.contact_label or ready.team_name,
        "description": (
            f"Cops-and-Robbers league peer for team {ready.team_name}, playing "
            f"{ready.role}. A2A is coordination and debugging only; the match "
            "itself runs over MCP commit/reveal."
        ),
        "version": "1.0.0",
        "url": f"{base_url}/a2a/message:send",
        "preferredTransport": "HTTP+JSON",
        "additionalInterfaces": [
            {"url": f"{base_url}{path}", "transport": "HTTP+JSON"} for path in MESSAGE_PATHS
        ],
        "provider": {
            "organization": ready.team_name,
            "url": ready.repos.get("cop", "") or ready.repos.get("thief", ""),
        },
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
            # The match facts, declared as a private extension rather than
            # invented as top-level fields. A reader that does not know this URI
            # is meant to skip the block, which is exactly the right outcome.
            "extensions": [
                {
                    "uri": EXTENSION_URI,
                    "description": "Where the actual game runs, and under what terms.",
                    "required": False,
                    "params": match_facts(ready, base_url),
                }
            ],
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {
                "id": "match-readiness",
                "name": "Match readiness",
                "description": (
                    "Confirms our MCP endpoint, the tools it exposes, the agreed "
                    "timeouts and the digest of the shared contract."
                ),
                "tags": ["coordination", "readiness", "mcp"],
                "examples": [
                    "Confirm your MCP endpoint, commit/reveal protocol and timeout settings.",
                ],
            }
        ],
    }
