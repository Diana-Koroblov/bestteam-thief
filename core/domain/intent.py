"""Whether the hint accompanying a move is truthful (Ch. 5, TODO 4.5.1).

**This lives in `domain`, not `protocol`, because it is a strategic decision
rather than a wire format.** The brain chooses it; the protocol only carries it
and the language layer is merely told the result. Putting it here is what lets
`core.infra.llm` read it without reaching sideways into `core.protocol`, which
the M#3 separation rule forbids — and the architecture test enforces.

Declared **inside** the commitment, so a peer must decide before seeing the
opponent's move and cannot claim afterwards that a lie was "meant" as truth
(Ch. 5.3.1). Lying is legal; misdeclaring the flag is forgery.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["Intent"]


class Intent(str, Enum):
    """Truthful or deceptive, decided by the brain and never by the model.

    Inherits `str` so it serialises as `"lie"` rather than `"Intent.LIE"` — the
    value is hashed into the commit, so its text form is part of the protocol.
    """

    TRUTH = "truth"
    LIE = "lie"
