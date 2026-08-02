"""Reading the age of a scent deposit from its strength (TODO 4.1.9).

A reading is not just "they were near here" — it is **"they were near here, this
many turns ago"**. Recovering that turns one number into a timestamp, and a
timestamp is what separates a stale trail from a fresh one.

Both decay models are inverted here because C-007 means we may end up playing
either. The book's model is multiplicative, the reference's is subtractive, and
which one is in force is settled at the handshake by comparing the M#23 digest
(`0.90 -> 0.81` against `0.90 -> 0.80`). Implementing only one would leave us
unable to read half the opponents in the league.

**Both sides can compute this from public values**, so it is inference rather
than an exploit: the emission table and the decay rate are both negotiated.
"""

from __future__ import annotations

from math import log

from core.domain.scent import EMISSION

__all__ = ["age_of", "freshest_source", "MAX_AGE"]

# Past this the reading is indistinguishable from noise and we decline to date
# it. A confident timestamp on a trace that faded twenty turns ago is worse than
# no timestamp: it would have the Cop chase where the Thief used to be.
MAX_AGE = 25

PEAK = EMISSION[0]


def age_of(reading: float, rate: float, model: str = "multiplicative") -> int | None:
    """Return how many turns ago a *reading* was laid at full strength.

    Args:
        reading: The sampled intensity.
        rate: The negotiated decay rate.
        model: ``multiplicative`` (the book) or ``subtractive`` (the reference).

    Returns:
        Turns elapsed, or None when the reading cannot be dated — zero or
        negative, stronger than a fresh deposit, or older than ``MAX_AGE``.

    Assumes the deposit began at the emission **centre** value. A reading taken
    two cells from the source is weaker for reasons of distance, not age, so
    dating it as old would be wrong. The caller must therefore only date a cell
    it has reason to treat as a source — which is why ``freshest_source``
    exists and takes the strongest reading rather than any reading.
    """
    if reading <= 0.0 or reading > PEAK or rate <= 0.0:
        return None

    if model == "subtractive":
        turns = round((PEAK - reading) / rate)
    else:
        if rate >= 1.0:
            return None
        turns = round(log(reading / PEAK) / log(1.0 - rate))

    return turns if 0 <= turns <= MAX_AGE else None


def freshest_source(field: dict, rate: float, model: str = "multiplicative"):
    """Return the strongest cell in *field* and its age, or ``(None, None)``.

    The strongest reading is the best candidate for a source because distance
    and age both weaken a deposit, and only the peak is unambiguous about which
    of the two is responsible.
    """
    if not field:
        return None, None
    cell = max(sorted(field), key=lambda c: field[c])
    return cell, age_of(field[cell], rate, model)
