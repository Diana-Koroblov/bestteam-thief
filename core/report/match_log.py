"""The per-sub-game log, and the proof it is replayable (TODO 7.2.3, M#20).

`log_<game_id>_g<NN>.json` is the one artefact that has to survive being
disbelieved. The others describe a match; this one *proves* it. Its DoD —
"sufficient for full replay verification" — is not a claim that can be settled
by inspection, so this module also supplies the inverse:

    build_log(...) ─► write ─► read ─► records(...) ─► audit_log(...)

If that round trip does not end in `Verified OK`, the log is not sufficient,
whatever it contains. The Replay Viewer (7.5.2) calls exactly this path, so the
viewer and the test are checking the same thing rather than two similar things.

**Nonces arrive last, and the shape here says so.** A step is recorded when it
happens, carrying its digest, state, move, intent and hint; the nonces are held
back until `FinalReveal` (M#18) and merged in at the end. Building the log in
one call from two sources mirrors the protocol instead of pretending the nonce
was available all along.

A step whose nonce never arrived is written with an empty one rather than
dropped. Dropping it would produce a shorter log that audits clean — which is
precisely the forgery the audit exists to catch. Present and unverifiable is the
honest record.
"""

from __future__ import annotations

from typing import Any

from core.crypto.audit import AuditResult, StepRecord, audit_log
from core.report.artefacts import utc_now
from core.shared.version import VERSION

__all__ = ["build_step", "build_log", "records", "verify_log", "STEP_FIELDS"]

# Everything a step needs to be re-hashed. `scent_digest` is deliberately absent:
# it is optional and omitted when unused, for the reason given in `build_step`.
STEP_FIELDS = ("step", "claimed_digest", "state", "move", "intent", "nonce")


def build_step(
    step: int,
    claimed_digest: str,
    state: Any,
    move: str,
    intent: str,
    hint: str = "",
    barrier_cell: tuple[int, int] | None = None,
    scent_digest: str | None = None,
) -> dict[str, Any]:
    """Record one turn, without its nonce.

    Args:
        claimed_digest: What we put on the wire during the commit phase.
        state: The board snapshot the move was sealed against. Stored verbatim,
            because the audit re-hashes *this* value — a normalised or prettied
            copy would hash differently and fail every step.
        intent: ``truth`` or ``lie``, the flag the commit covers.
        barrier_cell: The exact cell, when this turn placed one (M#15, M#16).
        scent_digest: Only when both peers agreed to seal the field (C-008).

    **When *scent_digest* is None the key is omitted, not set to null.** This
    mirrors `commitment_payload` exactly, and for the same reason: the replay
    rebuilds the hashed payload from this file, so a key that the sealing peer
    left out must be left out here too. A `null` that survived into the payload
    would change every digest in the log and make an honest match look forged.
    """
    record: dict[str, Any] = {
        "step": step,
        "claimed_digest": claimed_digest,
        "state": state,
        "move": move,
        "intent": intent,
        "hint": hint,
        "barrier_cell": list(barrier_cell) if barrier_cell is not None else None,
    }
    if scent_digest is not None:
        record["scent_digest"] = scent_digest
    return record


def build_log(
    game_identifier: str,
    sub_game: int,
    role: str,
    steps: list[dict[str, Any]],
    nonces: dict[str, str] | None = None,
    outcome: str = "",
    config_sha256: str = "",
) -> dict[str, Any]:
    """Assemble ``log_<game_id>_g<NN>.json`` (7.2.3).

    Args:
        steps: Entries from :func:`build_step`, in the order they were played.
        nonces: The `FinalReveal` mapping, keyed by step number as a string —
            the shape the wire uses, so no caller has to convert it.
        outcome: How the sub-game ended, for the reader who is not auditing.
        config_sha256: Ties this log to the config snapshot beside it. Without
            it the two files are only related by filename, and a filename is
            not evidence.

    The nonce merge is the whole point of this function: everything else is
    copied through unchanged, deliberately, so that what is hashed on replay is
    what was hashed at the time.
    """
    supplied = dict(nonces or {})
    # `step["step"]` rather than `.get`: a step dict without a step number is a
    # caller bug, and the two lines below must agree about what a step is. A
    # defensive `.get` here would quietly file it as unverifiable instead, which
    # is the one artefact where a silent gap is indistinguishable from forgery.
    merged = [{**step, "nonce": supplied.get(str(step["step"]), "")} for step in steps]
    return {
        "game_id": game_identifier,
        "sub_game": sub_game,
        "created_utc": utc_now(),
        "code_version": VERSION,
        "role": role,
        "outcome": outcome,
        "config_sha256": config_sha256,
        "steps": merged,
        "step_count": len(merged),
        "unverifiable_steps": [
            step["step"] for step in merged if not step["nonce"]
        ],
    }


def records(payload: dict[str, Any]) -> list[StepRecord]:
    """Turn a loaded log back into what the audit consumes.

    The inverse of :func:`build_log`, and the reason the DoD can be demonstrated
    rather than asserted. Unknown keys — `hint`, `barrier_cell`, anything a
    later phase adds — are dropped rather than passed on: they are for the
    reader, they were never inside the hash, and forwarding one would change
    every digest.

    Raises:
        KeyError: A step is missing a field the re-hash needs. Loud on purpose.
            A log that cannot be replayed must not be reported as one that
            replayed with a few gaps.
    """
    return [
        StepRecord(
            **{name: step[name] for name in STEP_FIELDS},
            scent_digest=step.get("scent_digest"),
        )
        for step in payload.get("steps", [])
    ]


def verify_log(payload: dict[str, Any]) -> AuditResult:
    """Re-hash a loaded log end to end (7.5.2).

    One call, so the Replay Viewer and the test that proves the log format is
    sufficient exercise the same path instead of two similar ones.
    """
    return audit_log(records(payload))
