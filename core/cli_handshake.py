"""Getting the two peers to agree before either of them moves (TODO 9.1, 9.2).

One function, split out of `core/cli_play.py` because it answers a question the
rest of that module does not: **has the opponent started yet?**

Two humans on two machines never start their peers in the same second. Without
the wait here, whoever runs first hits a closed port, records a refusal and
exits — before the other one is listening. That is a booked fixture lost to
nothing at all.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from core.sdk.peer_sdk import PeerSDK

__all__ = ["greet", "RETRY_SECONDS"]

# Gap between handshake attempts while the opponent is still starting up.
RETRY_SECONDS = 2.0


async def greet(sdk: PeerSDK, ours: Any, seconds: float) -> Any:
    """Send our handshake, waiting out an opponent who has not started yet.

    Two humans on two machines never start their peers in the same second, and
    without this the earlier one hits a closed port, records a refusal and exits
    before the later one is listening.

    **Only `TransportError` is retried.** It is the one failure the client's own
    taxonomy marks retryable — the call never completed, so nothing was decided.
    A `RemoteToolError` is the opponent refusing on the merits and retrying it
    would bury a verdict we already hold; a `DeadlineError` means the agreed
    window is spent and another attempt walks into the watchdog (M#5).
    """
    from core.infra.errors import TransportError
    from core.protocol.tools import decode_negotiation

    deadline = time.monotonic() + seconds
    while True:
        try:
            return decode_negotiation(await sdk.opponent.call("negotiate", ours.payload()))
        except TransportError:
            if time.monotonic() >= deadline:
                raise
            print(f"  no answer yet; retrying for {deadline - time.monotonic():.0f}s more ...")
            await asyncio.sleep(RETRY_SECONDS)
