"""The mechanism choices Appendix F never settles, as data and as prose (9.1.5-9.1.7).

Appendix F's status column already settles every *value*: fixed cannot change,
minimum may only be raised, negotiable is decided at the handshake. So two honest
peers can never disagree about a number — only about a **mechanism**, and that is
what this file enumerates (PRD_negotiation §3.6).

Two outputs from one source. `readings_of` produces the machine-comparable dict
that rides on the handshake and lands in the config snapshot; `clause` produces
the paragraph a human pastes into the agreement (9.1.6's *"in writing"*). Both
are generated from the live configuration, so the sentence we send an opponent
cannot drift from the flags we actually play under — which is the whole failure
mode a hand-written clause has.

**What a readings mismatch actually catches, precisely.** Every key below except
the component order is inside the shared config, so a disagreement there would
already have refused the match at the `config_sha256` comparison. What survives
that check and lands here is the case worth having: a peer that signed our config
and whose *code* does something else. The readings are their implementation's own
account of itself, and it is the only one we ever get.
"""

from __future__ import annotations

from typing import Any

from core.domain.scent import decay

__all__ = ["READINGS", "COMPONENT_ORDER", "readings_of", "disagreements", "unsigned", "clause"]

# The tuple order is the order they are presented in; the reference is quoted
# back at an opponent when one of them fails to match.
READINGS: tuple[tuple[str, str], ...] = (
    ("capture.resolution", "N15 / C-006b"),
    ("capture.stay_counts_as_move", "N14 / C-006a"),
    ("capture.swap_is_capture", "N16 / C-006c"),
    ("pheromones.decay_model", "N13b / C-007"),
    ("pheromones.field_includes_current_turn", "N13 / C-005"),
    ("pheromones.seal_scent_digest", "N13c / C-008"),
    ("board_and_agents.axis_origin_corner", "N18 / C-010"),
    ("board_and_agents.axis_start_index", "N18 / C-010"),
)

# **Not a config key, and deliberately so.** Every coordinate in this engine is
# `(row, col)` by construction; a flag offering `(x, y)` would be read by nothing
# and would be a lie in the one place C-010 says a lie is invisible until the
# first asymmetric coordinate. It is declared because it must be agreed, and
# hard-coded because it is structural.
COMPONENT_ORDER = "coordinates.component_order"


def _render(value: Any) -> str:
    """Return *value* as the string both peers can compare.

    JSON's spelling of the booleans, not Python's: an opponent writing in any
    other language sends ``true``, and a comparison that only ever matched
    ``True`` would report every one of them as a disagreement.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def readings_of(config) -> dict[str, str]:
    """Return the mechanism choices this peer will actually play under.

    Read from the merged configuration rather than from a literal table, so a
    negotiated deviation is declared by the same edit that makes us play it.
    """
    found = {path: _render(config.get(path)) for path, _ in READINGS}
    found[COMPONENT_ORDER] = "row,col"
    return found


def disagreements(ours: dict[str, str], theirs: dict[str, str]) -> list[str]:
    """Return the readings both peers stated and stated differently.

    Keys the opponent omitted are **not** disagreements — see `unsigned`. A peer
    that never implemented our extension is not contradicting us, and refusing
    the match over a field of our own invention would forfeit a fixture rather
    than prevent a dispute (PRD_negotiation §3.6b).
    """
    references = dict(READINGS)
    found = []
    for path, value in sorted(ours.items()):
        other = theirs.get(path)
        if other is not None and other != value:
            reference = references.get(path, "C-010")
            found.append(f"{path}: we play {value!r}, they play {other!r} ({reference})")
    return found


def unsigned(ours: dict[str, str], theirs: dict[str, str]) -> list[str]:
    """Return the readings the opponent did not state at all.

    Every one of these has to be settled in the human channel before the first
    move, because with no referee a mechanism discovered mid-match is
    unresolvable and voids the result for **both** teams (M#35).
    """
    return sorted(path for path in ours if path not in theirs)


def clause(config) -> str:
    """Return the agreement paragraph to paste to the opponent (9.1.6).

    The scent example is **computed**, never quoted. A worked number is the whole
    point of M#23 — it is what distinguishes the book's multiplicative decay from
    the reference's subtractive one — and a number typed into a docstring would
    be the first thing to go stale when the flag changed.
    """
    read = readings_of(config)
    rate = float(config.get("pheromones.pheromone_decay", 0.10))
    centre = float(config.get("pheromones.pheromone_center_intensity", 0.90))
    after = decay({(0, 0): centre}, rate, read["pheromones.decay_model"]).get((0, 0), 0.0)
    vacated = "does not capture" if read["capture.resolution"] == "after_moves" else "captures"
    swap = "counts as a capture" if read["capture.swap_is_capture"] == "true" else "does not capture"
    sealed = "seals" if read["pheromones.seal_scent_digest"] == "true" else "does not seal"
    includes = "including" if read["pheromones.field_includes_current_turn"] == "true" else "excluding"
    return "\n".join(
        (
            "Capture resolution. Actions resolve simultaneously; positions are evaluated "
            f"after both moves are applied. A barrier placed on a cell the thief has vacated {vacated}. "
            "A thief whose four orthogonal neighbours are all blocked by barriers and/or board "
            "edges is captured, regardless of the availability of STAY. Two agents exchanging "
            f"cells in the same turn {swap}.",
            f"Scent. Each peer transmits its own scent field with every turn message, {includes} "
            f"that turn's deposit. Decay is {read['pheromones.decay_model']}: at rho = {rate:g} a "
            f"centre cell at {centre:.3f} becomes {after:.3f} after one turn. A field revealed at "
            "turn k is first acted on when deciding turn k+1 (sampling mode: "
            "end_of_previous_full_turn), because turn k's own move was committed before that "
            f"reveal could arrive. Each peer {sealed} a digest of its emitted field inside that "
            "step's commitment.",
            f"Coordinates. A position is (row, col), origin {read['board_and_agents.axis_origin_corner']}, "
            f"indexed from {read['board_and_agents.axis_start_index']}. Worked example: we read [0,1] "
            "as row 0, column 1 - one cell East of the cop's start.",
        )
    )
