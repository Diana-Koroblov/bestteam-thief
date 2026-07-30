"""Canonical JSON serialisation — the one place bytes are produced for hashing.

**Every** hash in this project goes through here: the shared-config digest
exchanged during negotiation (M#11), the per-step commitment (M#17), and the
scent-model lock (M#23). There is exactly one implementation on purpose.

Two peers that serialise differently produce different digests from identical
data. The handshake then refuses a perfectly valid match, or — worse — the
end-of-game audit reports forgery against an honest opponent and **both teams
score 0**. That failure is silent until the moment it is expensive, so the
serialiser is deliberately boring and deliberately singular.

The rules: keys sorted, no whitespace between tokens, UTF-8 without ASCII
escaping, and floats left exactly as Python renders them.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

__all__ = ["canonical_json", "canonical_bytes", "digest"]


def canonical_json(payload: Any) -> str:
    """Return *payload* as canonical JSON text.

    Sorted keys make the output independent of insertion order; fixed separators
    remove the whitespace that ``json.dumps`` would otherwise vary; and
    ``ensure_ascii=False`` keeps non-ASCII characters as themselves rather than
    as escapes, so the bytes depend on the text and not on the encoder's mood.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_bytes(payload: Any) -> bytes:
    """Return the UTF-8 bytes that any peer must hash for *payload*."""
    return canonical_json(payload).encode("utf-8")


def digest(payload: Any) -> str:
    """Return the SHA-256 hex digest of *payload* in canonical form."""
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()
