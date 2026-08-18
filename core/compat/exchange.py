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
    github_commit: str = "",
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

    🐛 **Self-describing is not shape-free, and this was lost once already**
    (16/08, `docs/KNOWN_ISSUES.md`) **and rediscovered live, 18/08**, against
    the kit's own sparring peer this time: `verified_steps: 25, failed_steps:
    [26]`, our own side reporting "audit passed" throughout. Four things this
    shape gets that a plain re-implementation would not, each read off a real
    opponent's artefact rather than guessed:

    * ``step`` is the **wire** step (the counter the turn actually travelled
      under), not `state.step`. They bind each revealed record to the commit
      that arrived under its step number; `state.step` is a different counter
      that a standing concession leaves unchanged, so two records can claim the
      same step and their verifier reads it as a withheld or re-sealed turn.
    * ``move`` is ``MOVE:<direction>`` for a real move, and a bare ``STAY`` with
      no prefix for standing still — not our raw direction value.
    * ``verdict`` is always ``"moved"``. ``intent`` already answers whether the
      hint was truthful; putting it in `verdict` too answers a question nobody
      asked with a value that looks like a different one.
    * ``role`` and ``sub_game`` are present on every turn record, so a reader
      can place which side and which sub-game a record belongs to without
      cross-referencing anything else.

    Args:
        github_commit: Included only when non-empty, which the caller does for
            our FIRST record of a sub-game. 🐛 It was in the handshake identity
            block but never here, and imreeyal populate their artefact's commit
            column from the sealed step-0 record — so their file recorded an
            empty commit for us across all six sub-games of a clean series.
            Sealing it also makes it *evidence* rather than a claim: it is
            inside the commitment, so it cannot be revised after the fact.

            Absent rather than empty when unknown. A key present with a blank
            value is a declaration that we have no commit; an absent key hashes
            exactly as it did before this argument existed, which keeps every
            turn that does not carry one byte-identical to the old shape.
        step: The wire step this record travels under. Falls back to
            `state.step` when omitted, which keeps any caller that has not been
            updated working exactly as before.
    """
    barriers = sorted([list(cell) for cell in state.barriers])
    payload = {
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
    if github_commit:
        payload["github_commit"] = github_commit
    return payload


def system_spec_record(identity: dict[str, Any], sub_game_number: int) -> dict[str, Any]:
    """Return the sealed step-0 record the reference expects first in an audit.

    **A record that never rides a live turn**, which is exactly why its absence
    is invisible during play: every turn we send verifies, and the opponent
    still fails the whole sub-game — for the one record we never sent. Their
    verdict names it once any other orphan is out of the way: a count of
    revealed records one short of what they expected (step 0 through N).

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
