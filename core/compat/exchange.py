"""Translating between our turn and the reference implementation's.

Pure functions only — no waiting, no sockets, no runtime. What lives here is the
set of conversions that have to be exactly right and are worth testing without
standing a match up: the scent grid, the sealed payload, and the synthetic
`Reveal` that lets our existing belief filter consume an opponent's turn without
knowing this protocol exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from core.compat import sealing
from core.domain.board import Position
from core.domain.scent import encode
from core.protocol.schemas import Reveal, Role

__all__ = [
    "Incoming", "now_iso", "grid_of", "field_of", "synthetic_reveal",
    "sealed_payload", "system_spec_record",
]


def now_iso() -> str:
    """Return the timestamp every turn message carries (book: mandatory)."""
    return datetime.now(UTC).isoformat()


def grid_of(field: dict[Position, float]) -> dict[str, float]:
    """Return our field as the reference's ``{"r,c": intensity}`` object.

    Sorted, so two peers hashing the same field produce the same bytes. JSON
    objects are key-sorted by the canonical serialiser anyway, but the ordering
    is settled here so the value does not depend on that being true.
    """
    return {f"{row},{col}": value for (row, col), value in sorted(field.items())}


def field_of(grid: Any) -> dict[Position, float]:
    """Return the field a ``{"r,c": intensity}`` object describes.

    Malformed cells are **dropped rather than raised on**. Our native `decode`
    raises, and it is right to: there the field is sealed and a missing cell is
    evidence of tampering. Here it is an unsealed object from a peer we did not
    write, arriving mid-match, and taking a technical loss over one unparsable
    key would lose a game to a typo in someone else's serialiser.
    """
    field: dict[Position, float] = {}
    for key, value in (grid or {}).items():
        row, _, column = str(key).partition(",")
        try:
            field[(int(row), int(column))] = float(value)
        except (TypeError, ValueError):
            continue
    return field


@dataclass
class Incoming:
    """What an opponent's turn message means for us.

    Attributes:
        we_won: They confirmed our capture claim hit them.
        we_are_caught: Their claim hit our true cell. We must answer honestly
            (M#21) and the answer rides on our next message.
        they_won: They raised a win claim, e.g. survival.
        claim_response: The honest answer we owe them next turn.
    """

    we_won: bool = False
    we_are_caught: bool = False
    they_won: bool = False
    win_type: str = ""
    claim_response: dict | None = None


def synthetic_reveal(message: Any, theirs: Role) -> Reveal:
    """Return the opponent's turn as the `Reveal` our own machinery expects.

    `LocalTruth` reads two things off a stored reveal — the hint and the scent —
    and this protocol supplies both. Presenting them in the native shape means
    the belief filter, the observation a brain is handed and the hint history
    all keep working unchanged, rather than being reimplemented here.

    **``move`` is deliberately empty**, because under this protocol the opponent
    never discloses it. Nothing in the compatibility path decodes it; the native
    `decision_of` would raise on it, which is the correct outcome if this object
    ever reached code that assumed a move it cannot have.
    """
    barrier = getattr(message, "barrier_placed", None)
    return Reveal(
        step=int(getattr(message, "step", 0) or 0),
        role=theirs,
        move="",
        hint=str(getattr(message, "hint", "") or ""),
        barrier_cell=tuple(barrier) if barrier else None,
        scent=encode(field_of(getattr(message, "smell_grid", None))),
    )


def sealed_payload(
    state: Any,
    position: Position,
    grid_size: int,
    move: str,
    intent: str,
    hint: str,
    role: str = "",
    sub_game: int = 0,
    step: int | None = None,
) -> dict[str, Any]:
    """Return the record we seal for this turn, in the reference's own shape.

    Self-describing on purpose, following the reference: the whole payload
    travels with its nonce in the closing audit, so the opponent re-hashes
    exactly what we supply and neither side has to have agreed its shape. That
    is what makes this protocol auditable against a stranger — and it is the
    one place where the reference's design is plainly better than our own.

    **Self-describing is not shape-free, and we learned that the hard way.** A
    record still has to say the things a conformance reader looks for. Ours were
    missing two keys and spelled two values our own way, and the opponent's
    audit failed us across four match attempts — `tamper_forfeit`, 0 to BOTH
    teams under App. E rule 35, while our own side reported "audit passed" every
    time. Every difference below was read off imreeyal's own artefact rather
    than guessed:

    * ``move`` is ``MOVE:<direction>`` for a real move, and a bare ``STAY``
      with no prefix for standing still. Not our raw ``"E"``.
    * ``verdict`` is always ``"moved"``. We had been putting the *intent* there,
      which is a different question — ``intent`` already answers it.
    * ``role`` and ``sub_game`` are present on every turn record. We omitted
      both; a record that cannot say which side or which sub-game it belongs to
      is one a reader cannot place.
    """
    barriers = sorted([list(cell) for cell in state.barriers])
    return {
        # **The wire step, not `state.step`.** They bind the reveal to the wire:
        # every record is looked up by the step number the turn carried, and the
        # commit must match what arrived under it. `state.step` is a different
        # counter and it does not always agree — a STAY concession leaves it
        # unchanged, so two records claim the same step, one looks re-sealed and
        # the next looks withheld. Their verifier says exactly that:
        # "revealed under commit X but PLAYED under Y — the revealed log is a
        # different game than the one on the wire", and "received in play but
        # missing from the reveal — a withheld turn". Both are tamper_forfeit,
        # 0 to BOTH teams (App. E rule 35).
        "step": int(state.step) if step is None else int(step),
        "state": f"grid={grid_size}x{grid_size};self={list(position)};barriers={barriers}",
        "position": list(position),
        "move": move if move == "STAY" else f"MOVE:{move}",
        "intent": intent,
        "verdict": "moved",
        "hint": hint,
        "role": role,
        "sub_game": sub_game,
    }


def system_spec_record(identity: dict[str, Any], sub_game_number: int) -> dict[str, Any]:
    """Return the sealed step-0 record the reference expects first in an audit.

    **A record that never rides a live turn**, which is exactly why its absence
    was invisible across two match attempts: every turn we sent verified, and
    the opponent still failed us — for the one record we never sent. Their
    verdict named it once an unrelated orphan turn was out of the way:
    ``verified_steps: 21, failed_steps: [23]``, 23 being the count they expected
    (step 0 through 22) against the 22 we supplied. A `tamper_forfeit` is 0 to
    BOTH teams (App. E rule 35), and our own side reported "audit passed"
    throughout, so nothing here would ever have caught it.

    Their field names and their fallbacks (``unspecified`` / ``none`` / ``0``),
    because the reader re-hashes exactly what we supply and a spelling of our
    own would not reproduce. Values come off the identity block assembled in
    `core.reference_identity`, so `core/compat/` never reaches into
    `core.shared` to build it (M#3).
    """
    payload = {
        "code_version": str(identity.get("github_commit") or "unknown"),
        "group_name": str(identity.get("group_name") or ""),
        "model": str(identity.get("llm_model") or "template"),
        "num_games_declared": int(identity.get("counted_games_played") or 0),
        "spec": dict(identity.get("spec") or {}),
        "step": 0,
        "sub_game_number": sub_game_number,
        "type": "system_spec",
    }
    return {"payload": payload, **sealing.seal(payload)}
