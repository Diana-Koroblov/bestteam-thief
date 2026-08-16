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
from core.domain.scent import decay, intensity

__all__ = [
    "scent_model_payload",
    "scent_model_digest",
    "scent_model_of",
    "WORKED_EXAMPLE_INPUT",
    "SAMPLING_MODE",
]

# The value the worked example decays, chosen because it is the centre
# intensity Appendix F fixes — so both peers already agree on the input.
WORKED_EXAMPLE_INPUT = 0.90

# **When a received field may be acted on** (TODO 9.1.7, C-005). Not a setting:
# a field revealed at turn *k* is first usable when deciding turn *k+1*, because
# turn *k*'s own move was committed before that reveal could arrive. It is inside
# the digest anyway, because "what the field contains" and "when it may be read"
# are different agreements and only the first one is obvious. An opponent who
# acts on the current turn's field is revealing before committing, which is the
# single attack commit-reveal exists to prevent — and this is where they say so.
SAMPLING_MODE = "end_of_previous_full_turn"


def _emission_table(model: str) -> dict[str, float]:
    """Return ``{"d²": intensity}`` for the kernel *model* actually emits.

    Keyed by squared distance for both models, because that is the shape this
    document has always published and an opponent's parser expects. It stays
    unambiguous under the subtractive rings too: every offset with the same d²
    sits on the same Chebyshev ring, so no key is ever assigned two values.
    """
    from core.domain.scent import RADIUS

    table: dict[str, float] = {}
    for d_row in range(-RADIUS, RADIUS + 1):
        for d_col in range(-RADIUS, RADIUS + 1):
            table[str(d_row * d_row + d_col * d_col)] = intensity(d_row, d_col, model)
    return dict(sorted(table.items(), key=lambda item: int(item[0])))


def scent_model_payload(
    rate: float, model: str, grid_size: int, includes_current_turn: bool = True
) -> dict:
    """Return the scent agreement, ready to hash and to send.

    Args:
        rate: ``pheromone_decay`` — 0.10, fixed by Appendix F.
        model: ``multiplicative`` (book) or ``subtractive`` (reference).
        grid_size: ``pheromone_grid_size`` — 5, fixed by Appendix F.
        includes_current_turn: Whether the field we transmit at turn *k* carries
            turn *k*'s own deposit (C-005). Inside the digest because it changes
            what the opponent's filter should expect to see, and two peers
            disagreeing about it read each other's trails one turn out of step.

    The emission table travels as ``distance² → intensity`` rather than as a
    25-cell grid: it is the same information, half the payload, and it makes a
    disagreement about *one* radius obvious instead of hiding it among 25
    numbers that differ in one place.

    🐛 **The table used to be `EMISSION` whatever the model said**, so this
    document declared the book's Euclidean kernel even for a match negotiated
    onto the reference's subtractive rings — the digest asserted physics we
    were not playing, which is worse than a disagreement because it is a
    disagreement that verifies. Derived from `intensity` now, so the document
    and the field are read from one definition.
    """
    after = decay({(0, 0): WORKED_EXAMPLE_INPUT}, rate, model).get((0, 0), 0.0)
    return {
        "emission_by_squared_distance": _emission_table(model),
        "grid_size": grid_size,
        "decay_rate": rate,
        "decay_model": model,
        "field_includes_current_turn": bool(includes_current_turn),
        "sampling_mode": SAMPLING_MODE,
        "worked_example": {
            "input": WORKED_EXAMPLE_INPUT,
            "after_one_turn": round(after, 10),
        },
    }


def scent_model_digest(
    rate: float, model: str, grid_size: int, includes_current_turn: bool = True
) -> str:
    """Return the digest both peers compare during negotiation (M#23)."""
    return digest(scent_model_payload(rate, model, grid_size, includes_current_turn))


def scent_model_of(config) -> dict:
    """Return the scent agreement for a loaded configuration.

    The one place the four values are pulled out of config, so the payload we
    hash and the field we actually emit can never be read from different keys.
    """
    return scent_model_payload(
        rate=float(config.get("pheromones.pheromone_decay", 0.10)),
        model=str(config.get("pheromones.decay_model", "multiplicative")),
        grid_size=int(config.get("pheromones.pheromone_grid_size", 5)),
        includes_current_turn=bool(config.get("pheromones.field_includes_current_turn", True)),
    )
