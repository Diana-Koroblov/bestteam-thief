"""The scent model as a signed artefact (M#23, TODO 4.1.5).

Both peers must agree how scent is emitted and decayed **before** the first
move, and prove it by digest. The reason is C-007: the book's multiplicative
decay gives 0.9 → 0.81 while the reference implementation's subtractive decay
gives 0.9 → 0.80. Two peers running different models produce different beliefs
from identical observations, and the end-of-match audit reports that as forgery
against two honest teams.

The payload carries a **worked example**, not just a formula name. A label can
be agreed while the arithmetic still differs; a number cannot. If their example
says 0.80, they built on the reference — which tells us both that we must
settle the model and which implementation we are facing.
"""

from __future__ import annotations

from core.crypto.canonical import digest
from core.domain.scent import EMISSION, decay

__all__ = ["scent_model_payload", "scent_model_digest", "WORKED_EXAMPLE_INPUT"]

# The value the worked example decays, chosen because it is the centre
# intensity Appendix F fixes — so both peers already agree on the input.
WORKED_EXAMPLE_INPUT = 0.90


def scent_model_payload(rate: float, model: str, grid_size: int) -> dict:
    """Return the scent agreement, ready to hash and to send.

    Args:
        rate: ``pheromone_decay`` — 0.10, fixed by Appendix F.
        model: ``multiplicative`` (book) or ``subtractive`` (reference).
        grid_size: ``pheromone_grid_size`` — 5, fixed by Appendix F.

    The emission table travels as ``distance² → intensity`` rather than as a
    25-cell grid: it is the same information, half the payload, and it makes a
    disagreement about *one* radius obvious instead of hiding it among 25
    numbers that differ in one place.
    """
    after = decay({(0, 0): WORKED_EXAMPLE_INPUT}, rate, model).get((0, 0), 0.0)
    return {
        "emission_by_squared_distance": {str(d): v for d, v in sorted(EMISSION.items())},
        "grid_size": grid_size,
        "decay_rate": rate,
        "decay_model": model,
        "worked_example": {
            "input": WORKED_EXAMPLE_INPUT,
            "after_one_turn": round(after, 10),
        },
    }


def scent_model_digest(rate: float, model: str, grid_size: int) -> str:
    """Return the digest both peers compare during negotiation (M#23)."""
    return digest(scent_model_payload(rate, model, grid_size))
