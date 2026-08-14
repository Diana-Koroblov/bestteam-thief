"""Where A2A meets the transport — the join M#3 puts in the gateway.

`core/a2a` decides what a card says and knows nothing about HTTP. `core/infra`
serves HTTP and knows nothing about cards. Neither may import the other, so the
two meet here, in the layer that is allowed to know both — and that also holds
the third thing this needs and neither of them may read: the configuration.

Split out of `peer_sdk.py` for the 150-line limit (ADR-005), along a seam that
was already there: the facade delegates, and everything that has to know what an
`X-Forwarded-Proto` header or an Appendix F key is lives in one file.
"""

from __future__ import annotations

from typing import Any

from core.a2a import CARD_PATHS, MESSAGE_PATHS, Coordination, Readiness
from core.infra.mcp_server import Route
from core.runtime.deadline_tracker import MAX_ATTEMPTS

__all__ = ["readiness_of", "routes_for"]


def readiness_of(
    config: Any,
    role: str,
    digest: str,
    role_split: str,
    mcp_tools: tuple[str, ...] = (),
) -> Readiness:
    """Return what we tell a peer about ourselves before a match (Ch. 2.3).

    Args:
        config: The merged configuration. Only the shared half is read from —
            `identity` is declared at Step-0 anyway and `network_and_league` is
            the negotiated contract. Nothing from `game.toml` is published, and
            the LLM provider is private per peer under Appendix F Table 21.
        role: Which side this process plays.
        digest: `config_sha256`, so a peer can compare contracts before the day
            rather than discover a mismatch at the handshake.
        role_split: The block plan we propose (N17).
        mcp_tools: The names the server is about to register — read off the
            spec, never typed, so we cannot advertise a tool we do not serve.
    """
    return Readiness(
        team_name=str(config.get("identity.team_name", "")),
        contact_label=str(config.get("identity.contact_label", "peer")),
        role=role,
        members=tuple(config.get("identity.members", ()) or ()),
        repos={
            "cop": str(config.get("identity.repo_cop", "")),
            "thief": str(config.get("identity.repo_thief", "")),
        },
        mcp_tools=mcp_tools,
        num_games=int(config.require("network_and_league.num_games")),
        role_split=role_split,
        response_timeout_sec=float(config.require("network_and_league.response_timeout_sec")),
        timeout_attempts=MAX_ATTEMPTS,
        watchdog_timeout_sec=float(config.require("network_and_league.watchdog_timeout_sec")),
        config_sha256=digest,
    )


def routes_for(readiness: Readiness) -> tuple[Route, ...]:
    """Return the A2A endpoints, ready for a transport to mount.

    Four routes for two endpoints, because A2A has spelled the card two ways
    and their note asks for a message path their own server does not serve. The
    duplication is one line each and removes a whole class of match-morning 404.
    """
    desk = Coordination(readiness)
    cards = tuple(
        Route(path, ("GET",), lambda base, _body, desk=desk: (200, desk.card(base)))
        for path in CARD_PATHS
    )
    return cards + tuple(Route(path, ("POST",), desk.answer) for path in MESSAGE_PATHS)
