"""The reference implementation's commit-reveal, which is **not** ours.

Two differences, and either one alone makes every digest disagree:

* Ours hashes a single JSON object with the nonce *inside* it. The reference
  hashes ``canonical_json(payload) + "|" + nonce`` — the nonce is appended as
  text, outside the document.
* Ours requires both peers to build byte-identical payloads, which is why the
  optional keys are omitted rather than set to null (C-008, C-018). The
  reference ships each payload *with* its record, so a verifier re-hashes
  exactly what the sender supplied and no shared payload schema is needed.

The second is the better design for interoperating with strangers, and it is
why this module can verify an opponent's log without agreeing anything about
its shape beforehand.

**This deliberately duplicates `core/crypto/canonical.py` rather than reusing
it.** They are two different formulas that must never drift into each other: a
single "shared" serialiser with a flag would be one edit away from silently
re-hashing native matches under the reference rule, and the failure mode is an
audit reporting forgery against an honest opponent (M#19).
"""

from __future__ import annotations

import hashlib
import json
import secrets
from typing import Any

__all__ = ["NONCE_BYTES", "canonical", "commit_of", "seal", "verify", "audit_records"]

# Matches the reference's own constant. The nonce carries the whole search cost
# here exactly as it does natively, so this is not a value to economise on.
NONCE_BYTES = 16


def canonical(payload: dict[str, Any]) -> str:
    """Return *payload* as the reference's canonical JSON text.

    Sorted keys, no whitespace, non-ASCII left as itself. Identical rules to
    ours — it is only what happens *around* this string that differs.
    """
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def commit_of(payload: dict[str, Any], nonce: str) -> str:
    """Return ``SHA256(canonical(payload) | nonce)`` as hex.

    The pipe is a literal character in the hashed text, not a bitwise operation
    and not a structural separator the JSON knows about. A payload whose last
    value ends in ``|`` is therefore theoretically ambiguous; that is the
    reference's choice and we reproduce it exactly, because reproducing it
    imperfectly is indistinguishable from forgery.
    """
    return hashlib.sha256(f"{canonical(payload)}|{nonce}".encode()).hexdigest()


def seal(payload: dict[str, Any]) -> dict[str, str]:
    """Return a fresh ``{"nonce", "commit"}`` pair for *payload*.

    ``secrets`` rather than ``random``, for the reason `core.crypto.commitment`
    gives: a predictable nonce is no nonce at all.
    """
    nonce = secrets.token_hex(NONCE_BYTES)
    return {"nonce": nonce, "commit": commit_of(payload, nonce)}


def verify(payload: dict[str, Any], nonce: str, commit: str) -> bool:
    """Return True when *payload* and *nonce* really produce *commit*."""
    return secrets.compare_digest(commit_of(payload, nonce), commit)


def audit_records(
    records: list[dict[str, Any]], live: dict[int, str] | None = None
) -> dict[str, Any]:
    """Re-verify every ``{payload, nonce, commit}`` the opponent revealed.

    Args:
        live: ``{step: commit}`` as it actually arrived during play (the
            ``TurnMessage.commit`` field), if the caller tracked it. When a
            record's step **was** seen live, it is failed unless its commit
            equals the one that arrived then — binding the reveal to what was
            really sent, not only to itself. Without this a record rewritten
            and re-sealed after the fact is self-consistent and would pass:
            ``commit_of(payload, nonce) == commit`` proves nothing about
            whether *that* commit ever crossed the wire.

            A step **absent** from ``live`` is not a mismatch: a step-0
            system-spec/declaration record legitimately exists only inside the
            closing audit and never rides a live turn (the reference's own
            log shape — PAIRING-PLAYBOOK §4f, "readers must accept both" step-0
            spellings). Treating "never seen live" the same as "seen and
            different" would fail every clean sub-game on that one record.

    Returns the reference's own result shape, so a peer on either side of the
    wire reads the same verdict: ``passed``, ``verified_steps``, ``failed_steps``.

    A record missing any of the three keys counts as **failed**, not skipped. An
    unverifiable step is treated as forgery (M#19), and quietly passing over one
    would turn the one artefact that proves integrity into a formality.
    """
    failed: list[int] = []
    for record in records:
        payload = record.get("payload")
        nonce = record.get("nonce")
        commit = record.get("commit")
        step = payload.get("step", -1) if isinstance(payload, dict) else -1
        if not isinstance(payload, dict) or not isinstance(nonce, str) or not isinstance(
            commit, str
        ):
            failed.append(step)
            continue
        if not verify(payload, nonce, commit):
            failed.append(step)
            continue
        if live is not None and step in live and live[step] != commit:
            failed.append(step)
    return {
        "passed": not failed,
        "verified_steps": len(records) - len(failed),
        "failed_steps": failed,
    }
