"""`python -m core a2a` — publish our card, and check theirs (Ch. 2.3).

Two jobs, one command. With no flags it prints what a peer would be told, so the
answer can be read and pasted into the chat where the match is being arranged.
With `--probe` it asks *their* host the same questions, which otherwise get asked
by hand and answered from memory.

**Nothing here plays.** No runtime is started, no negotiation is sent, no
artefact is filed. A readiness check that could accidentally open a sub-game
would be a readiness check nobody dares run twice.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from core.a2a import CARD_PATHS, MESSAGE_PATHS
from core.infra.a2a_probe import READINESS_QUESTION, REQUIRED_TOOLS, probe
from core.sdk.peer_sdk import PeerSDK

__all__ = ["a2a"]


def a2a(sdk: PeerSDK, args: argparse.Namespace) -> int:
    """Show our own coordination surface, or probe an opponent's. 0 means ready."""
    if not args.probe:
        return _show(sdk, args.base or f"http://127.0.0.1:{sdk.listen_port}")
    return asyncio.run(probe(args.probe.rstrip("/")))


def _show(sdk: PeerSDK, base: str) -> int:
    """Print the card and the readiness answer exactly as a peer would get them.

    Through the **same** responders the server mounts, not a re-description of
    them. A preview that built its own copy could print an answer no opponent
    will ever receive, which is worse than having no preview at all.
    """
    routes = {route.path: route for route in sdk.a2a_routes(REQUIRED_TOOLS)}
    _, card = routes[CARD_PATHS[0]].respond(base, None)
    _, reply = routes[MESSAGE_PATHS[0]].respond(
        base, {"message": {"role": "ROLE_USER", "parts": [{"text": READINESS_QUESTION}]}}
    )
    print(json.dumps(card, indent=2))
    print(f"\n--- what we answer on POST {MESSAGE_PATHS[0]} ---\n")
    print(reply["parts"][0]["text"])
    return 0
