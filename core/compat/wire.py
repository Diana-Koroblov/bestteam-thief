"""The reference implementation's wire format, field for field.

Three messages cross the wire under this protocol, and only one of them carries
a turn. The names, the defaults and the ``None``s are copied deliberately: the
opponent compares terms with ``!=`` on a whole dict and re-hashes records with
their own payload inside, so a field we spell differently is a refused match or
a false forgery verdict rather than a warning.

**The turn token travels with `TurnMessage`.** Receiving one is what makes it
our turn; there is no separate "your move" signal, and the thief opens.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = ["TurnMessage", "AuditPayload", "terms_from_config", "terms_diff", "REFERENCE_TERMS"]

# The reference ships this in `pheromones` and our `game.json` has never had it,
# because nothing in our own physics reads a floor on the centre intensity. It
# is still a **signed term** there, so a value we cannot supply is a handshake
# we cannot pass — 0.5 is the reference's own shipped value.
DEFAULT_MIN_CENTER_INTENSITY = 0.5

# Every key the reference signs, in the order its own `terms_from_config` builds
# them. Order does not affect the signature (the JSON is key-sorted) but it does
# decide how a mismatch reads to a human, and this is a message sent mid-match.
REFERENCE_TERMS: tuple[str, ...] = (
    "board_size", "smell_grid_size", "decay_per_step", "emit_intensity",
    "min_center_intensity", "max_steps", "barriers_max", "setting",
    "hint_max_words", "axis_origin_corner", "axis_start_index",
    "thief_start", "cop_start", "num_games",
)


@dataclass
class TurnMessage:
    """Everything one peer tells the other about its turn — and nothing more.

    The true position and move are **not** here. They are sealed inside
    ``commit`` and proven only at the end-of-game audit, which is the whole
    reason this protocol needs a belief map: an opponent's cell is inferred from
    ``smell_grid`` and ``hint``, never read off the wire.

    Attributes:
        capture_claim: Police only — ``[row, col]`` it asserts the thief is on.
        claim_response: The thief's honest answer to the *previous* claim. It
            rides on the next outbound turn rather than returning immediately,
            because these tools cannot answer anything.
        win_claim: The thief's ``{"type": "survival"}`` when it has run out the
            clock.
    """

    step: int
    sender: str
    hint: str
    smell_grid: dict
    commit: str
    timestamp: str
    barrier_placed: list | None = None
    capture_claim: list | None = None
    claim_response: dict | None = None
    win_claim: dict | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-ready form that goes on the wire."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TurnMessage:
        """Return the message *data* describes.

        Unknown keys are dropped rather than raising. The reference has already
        grown ``win_claim`` once, and a peer that refused a message carrying one
        extra field would take a technical loss over an opponent's new feature.
        """
        allowed = {"step", "sender", "hint", "smell_grid", "commit", "timestamp",
                   "barrier_placed", "capture_claim", "claim_response", "win_claim"}
        missing = {"step", "sender", "commit"} - data.keys()
        if missing:
            raise ValueError(f"turn message is missing {sorted(missing)}")
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass
class AuditPayload:
    """End-of-game reveal: the sealed records, so the opponent can re-verify.

    Attributes:
        records: ``[{"payload": {...}, "nonce": str, "commit": str}]``. Each
            record carries its own payload, which is what lets two peers audit
            each other without ever agreeing a payload schema.
        result_claim: ``capture`` | ``survival`` | ``timeout``.
    """

    sender: str
    records: list = field(default_factory=list)
    result_claim: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-ready form that goes on the wire."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AuditPayload:
        """Return the payload *data* describes, ignoring unknown keys."""
        return cls(
            sender=str(data.get("sender", "")),
            records=list(data.get("records") or []),
            result_claim=str(data.get("result_claim", "")),
        )


def terms_from_config(config: Any) -> dict[str, Any]:
    """Return our shared contract expressed in the reference's vocabulary.

    Every value is read from the same `game.json` our native path signs, so the
    two protocols cannot end up playing different physics — only describing the
    same physics with different key names.
    """
    return {
        "board_size": config.get("board_and_agents.grid_size"),
        "smell_grid_size": config.get("pheromones.pheromone_grid_size"),
        "decay_per_step": config.get("pheromones.pheromone_decay"),
        "emit_intensity": config.get("pheromones.pheromone_center_intensity"),
        "min_center_intensity": config.get(
            "pheromones.pheromone_min_center_intensity", DEFAULT_MIN_CENTER_INTENSITY
        ),
        "max_steps": config.get("movement_and_barriers.max_moves"),
        "barriers_max": config.get("movement_and_barriers.max_barriers"),
        "setting": config.get("world.map_area"),
        "hint_max_words": config.get("world.hint_max_words", 15),
        "axis_origin_corner": config.get("board_and_agents.axis_origin_corner", "top-left"),
        "axis_start_index": config.get("board_and_agents.axis_start_index", 0),
        "thief_start": list(config.get("board_and_agents.thief_start") or []),
        "cop_start": list(config.get("board_and_agents.cop_start") or []),
        "num_games": config.get("network_and_league.num_games", 1),
    }


def terms_diff(ours: dict[str, Any], theirs: dict[str, Any]) -> list[str]:
    """Return one readable line per disagreeing term, ours first.

    The reference refuses on ``ours != theirs`` and prints both whole dicts,
    which at fourteen keys is a wall of text hiding one wrong number. This is
    the same refusal with the difference actually located — the message is sent
    to a human mid-match who has minutes, not hours.
    """
    lines = []
    for key in sorted(set(ours) | set(theirs)):
        mine, yours = ours.get(key, "<absent>"), theirs.get(key, "<absent>")
        if mine != yours:
            lines.append(f"{key}: ours={mine!r} theirs={yours!r}")
    return lines
