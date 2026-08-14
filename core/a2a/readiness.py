"""What we are willing to say about ourselves, and where we say it from.

Split from the card and the reply because both need it and neither owns it: the
card publishes these facts to anyone who asks, the reply quotes them back at
whoever asked a question, and they must never be able to disagree. One
dictionary, built once, used by both.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["CARD_PATHS", "MESSAGE_PATHS", "EXTENSION_URI", "Readiness", "match_facts"]

# Both spellings the A2A revisions have used for the card.
CARD_PATHS: tuple[str, ...] = ("/.well-known/agent-card.json", "/.well-known/agent.json")

# What nis-yar1 asked us for, and what their own server actually serves. Serving
# both costs one route each; guessing which they meant costs a match.
MESSAGE_PATHS: tuple[str, ...] = ("/message:send", "/a2a/message:send")

# A2A lets an agent declare a private extension by URI (`capabilities.extensions`).
# The match facts live there rather than at the top level of the card, so a
# standards-conformant reader can skip them and ours can find them.
EXTENSION_URI = "https://github.com/Diana-Koroblov/bestteam-cop/a2a/cops-and-robbers/v1"


@dataclass(frozen=True)
class Readiness:
    """Everything a peer may know about us before a match, and nothing else.

    Built from the merged configuration by the gateway, because that is the one
    layer allowed to read config and to know what a transport is. Frozen so a
    request handler cannot edit what the next request will be told.

    Every field here is **already public**: it is the Step-0 declaration and the
    negotiated contract, both of which the opponent receives anyway. The LLM
    provider is private per peer under Appendix F Table 21 and is deliberately
    absent, as is everything in `game.toml`.

    Attributes:
        team_name: Our declared team id, as it appears in `agreed_between`.
        contact_label: The public, boring name for this process.
        role: Which side this process plays — a peer runs two, on two URLs.
        members: Both group members, as declared at Step-0 (Ch. 9.3.3).
        repos: Our two published repositories, cop and thief.
        mcp_tools: The tool names our server actually registers. Read off the
            server spec rather than typed here, so this can never drift into
            advertising a tool we do not serve.
        num_games: Sub-games in the series, from the agreed contract.
        role_split: The block plan we propose (N17).
        response_timeout_sec: The agreed per-message window.
        timeout_attempts: How many times we wait that window before calling it a
            technical loss. Two — one try, one retry (M#6).
        watchdog_timeout_sec: The longer supervisor window.
        config_sha256: Digest of the shared contract. Published so a mismatch is
            found now, by a script, rather than at the handshake on the day.
    """

    team_name: str
    contact_label: str
    role: str
    members: tuple[str, ...] = ()
    repos: dict[str, str] = field(default_factory=dict)
    mcp_tools: tuple[str, ...] = ()
    num_games: int = 6
    role_split: str = "3-3"
    response_timeout_sec: float = 30.0
    timeout_attempts: int = 2
    watchdog_timeout_sec: float = 60.0
    config_sha256: str = ""

    @property
    def patience_sec(self) -> float:
        """Seconds we actually wait before declaring a technical loss.

        The agreed window times the attempts we are allowed. Quoted separately
        from `response_timeout_sec` because the two answer different questions —
        one is what we ask of them, the other is when they have lost the
        sub-game — and confusing them is how a slow opponent gets written off
        thirty seconds early.
        """
        return self.response_timeout_sec * self.timeout_attempts


def match_facts(ready: Readiness, base_url: str) -> dict[str, Any]:
    """Return the machine-readable half of everything we publish.

    The same dictionary goes into the card's extension and into the data part of
    a reply, so a peer that scrapes one and a peer that parses the other are
    told exactly the same thing.

    The base URL is a **parameter**, not configuration. We answer on localhost
    during a rehearsal and on an ngrok domain during a match; the transport
    reads it off the incoming request, so what we advertise is always the URL
    that actually reached us.
    """
    return {
        "team": ready.team_name,
        "role": ready.role,
        "members": list(ready.members),
        "repos": dict(ready.repos),
        "agentCardUrl": f"{base_url}{CARD_PATHS[0]}",
        "a2aMessageUrl": f"{base_url}{MESSAGE_PATHS[0]}",
        "mcpUrl": f"{base_url}/mcp",
        "mcpTools": list(ready.mcp_tools),
        "transport": "MCP over HTTP (FastMCP), JSON tool calls",
        "sendsFirstCommitAfterNegotiation": True,
        "commitFlow": (
            "Every step is symmetric: we push receive_commit for step 0 as soon as "
            "negotiation is settled, without waiting for yours, then wait for yours, "
            "then push receive_reveal. Neither side is the initiator."
        ),
        "numGames": ready.num_games,
        "roleSplit": ready.role_split,
        "timeouts": {
            "responseTimeoutSec": ready.response_timeout_sec,
            "attempts": ready.timeout_attempts,
            "patienceBeforeTechnicalLossSec": ready.patience_sec,
            "watchdogTimeoutSec": ready.watchdog_timeout_sec,
            "sameAtEveryStep": True,
            "note": (
                "One window for every step, step 0 included — we do not implement a "
                "60s-then-10s scheme. These values are network_and_league in the "
                "game.json we both hashed; changing them changes config_sha256 and "
                "must be re-agreed and re-packed before the match."
            ),
        },
        "configSha256": ready.config_sha256,
        "gameChannel": "MCP only",
        "a2aScope": "readiness and debugging only - no commits, reveals or moves",
    }
