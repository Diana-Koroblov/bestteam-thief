"""The two-directional audit at the end of one sub-game (ADR-005 split).

Lifted out of `core/cli_compat.py` when that file reached its 150 lines, and the
seam is a real one rather than a convenience: **the audit is two independent
claims and this module is the only place that knows they are two.** We push our
reveal to the opponent, and separately we collect theirs. Neither is a reply to
the other, neither implies the other, and conflating them is exactly the defect
this module was extracted to fix.

🐛 **`audit passed` used to be printed on the strength of the inbound direction
alone**, while the outbound call sat inside `contextlib.suppress(PeerError)`
with its result discarded. So a sub-game in which our records never reached the
opponent printed identically to one in which they did. nis-yar1 recorded
`opponent_received=false` on five rows of a series our own terminal called
clean, and nothing on this side could have contradicted them — we had no
evidence either way, and were reporting as though we did.

The suppression itself was never wrong: a peer that has just won may exit the
moment it reads its inbox, killing its server mid-response, while our payload
landed anyway. That is a good reason not to raise. It is not a reason to say
nothing, and the two had been conflated.
"""

from __future__ import annotations

from typing import Any

from core.infra.errors import PeerError

__all__ = ["DELIVERED", "exchange"]

DELIVERED = "delivered"


async def exchange(sdk: Any, session: Any, linger: float) -> tuple[dict[str, Any], str]:
    """Push our audit, collect theirs, and report on both directions.

    Args:
        sdk: The peer, whose ``opponent`` is the outbound client.
        session: The finished sub-game, holding the records to reveal.
        linger: Seconds to keep serving while their audit arrives.

    Returns:
        ``(verdict, outbound)``. The verdict describes **their** records
        arriving in our inbox — ``passed``, ``received`` and ``failed_steps``.
        The outbound string describes **ours** leaving for theirs, and is
        ``"delivered"`` or a note naming the failure. A caller that prints only
        the first is making a claim it cannot support.
    """
    try:
        await sdk.opponent.call("submit_audit", session.audit_payload(), argument="payload")
        outbound = DELIVERED
    except PeerError as error:
        # Named, not swallowed. The opponent's own record of this sub-game will
        # say `opponent_received=false`, and the two teams should be able to
        # agree about which of them saw what without reading each other's code.
        outbound = f"NOT DELIVERED ({type(error).__name__}: {error})"
    return await session.collect_audit(linger), outbound
