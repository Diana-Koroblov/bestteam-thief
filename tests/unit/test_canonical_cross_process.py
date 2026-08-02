"""Two processes must agree, byte for byte (TODO 6.5.2, 6.1.2).

**This is the worst-case failure in the entire project.** If two peers serialise
the same payload differently, every commitment digest mismatches at the audit,
neither side can prove it played honestly, and *both teams score 0*. Not a lost
match — a lost series, for four people.

Every other test in the suite runs inside one interpreter, where agreement is
almost guaranteed by accident: the same dict ordering, the same float repr, the
same locale. A real match has two processes on two machines, so agreement has to
be demonstrated **across a process boundary** or it has not been demonstrated.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from core.crypto.canonical import canonical_json, digest

ROOT = Path(__file__).resolve().parents[2]

# Deliberately awkward: key order that differs from insertion, unicode, floats
# that print differently under naive formatting, and nesting.
PAYLOAD = {
    "zeta": [3, 1, 2],
    "alpha": {"nested": True, "b": None},
    "float": 0.1 + 0.2,
    "unicode": "גנב ושוטר — ✓",
    "int": 10**18,
}

# **The child writes UTF-8 bytes, never `print`.**
#
# The first version used `print`, and it failed on Windows and only on Windows:
# the console there defaults to cp1252, so printing the Hebrew payload raised
# `UnicodeEncodeError` and the child exited 1. The canonical form was correct
# all along — it was the *reporting* that could not survive the platform.
#
# That is worth more than a test fix. Anything in the peer that logs or prints
# canonical JSON containing a non-ASCII team name will die the same way on a
# Windows console, mid-match. `sys.stdout.buffer` bypasses the console codec
# entirely, which is the only reliable answer.
CHILD = """
import json, sys
sys.path.insert(0, {root!r})
from core.crypto.canonical import canonical_json, digest
payload = json.loads(sys.stdin.read())
out = digest(payload) + chr(10) + canonical_json(payload)
sys.stdout.buffer.write(out.encode("utf-8"))
"""


def _in_child(payload: dict) -> tuple[str, str]:
    """Serialise *payload* in a **separate interpreter** and return its output."""
    import json

    # `check=True` is deliberately NOT used: it raises `CalledProcessError`
    # carrying only the exit code, which hid the child's real traceback and made
    # the first Windows failure unreadable. We surface stderr instead.
    result = subprocess.run(
        [sys.executable, "-c", CHILD.format(root=str(ROOT))],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, (
        f"child process failed:\n{result.stderr.decode('utf-8', errors='replace')}"
    )
    child_digest, child_json = result.stdout.decode("utf-8").split("\n", 1)
    return child_digest, child_json


def test_a_second_process_produces_the_identical_digest() -> None:
    """**6.5.2. The one that stops both teams scoring 0.**

    This test earned its keep on the first Windows run: the child died with
    `UnicodeEncodeError` before it could report anything, because a cp1252
    console cannot print Hebrew. The canonical bytes were right; the platform
    could not carry them.

    Run in a real subprocess rather than a thread or a fixture, because the
    things that break canonical form — hash seed, dict ordering, locale, float
    repr — are per-*interpreter*, and a thread would share all of them and prove
    nothing.
    """
    child_digest, child_json = _in_child(PAYLOAD)
    assert child_digest == digest(PAYLOAD)
    assert child_json == canonical_json(PAYLOAD)


def test_key_insertion_order_cannot_change_the_digest() -> None:
    """Two peers build the same payload in different orders. They must agree."""
    forward = {"a": 1, "b": 2, "c": 3}
    backward = {"c": 3, "b": 2, "a": 1}
    assert digest(forward) == digest(backward)
    assert _in_child(backward)[0] == digest(forward)


def test_non_ascii_survives_the_boundary() -> None:
    """Team names and hints may be Hebrew; an escaping difference is a mismatch."""
    payload = {"team": "הטובים", "hint": "צפונה"}
    assert _in_child(payload)[0] == digest(payload)


def test_a_single_changed_bit_changes_the_digest() -> None:
    """Otherwise the audit would not detect tampering at all."""
    assert digest({"move": "N"}) != digest({"move": "S"})


# --- 6.1.2: the nonce must never come from `random` -------------------------


def test_nonces_are_generated_with_secrets_not_random() -> None:
    """**M#18, asserted against the source rather than trusted.**

    ``random`` is seeded predictably. An opponent who guessed the seed could
    reproduce every nonce in the match, and the commitment scheme — whose entire
    strength against a five-move dictionary attack *is* the nonce — would
    collapse silently while still appearing to work.
    """
    source = (ROOT / "core" / "crypto" / "commitment.py").read_text(encoding="utf-8")
    assert "import secrets" in source
    assert "import random" not in source
    assert "random." not in source


def test_two_nonces_are_never_the_same() -> None:
    """Reusing a nonce across two steps lets an opponent link them."""
    from core.crypto.commitment import new_nonce

    assert len({new_nonce() for _ in range(500)}) == 500


@pytest.mark.parametrize("field", ["state", "move", "intent", "nonce"])
def test_every_sealed_field_is_covered_by_the_digest(field: str) -> None:
    """6.5.1. Mutating any one of them must be caught, or the seal is partial."""
    from core.crypto.commitment import commitment_payload

    base = {"state": "s", "move": "N", "intent": "truth", "nonce": "abc"}
    tampered = {**base, field: "TAMPERED"}
    assert digest(commitment_payload(**base)) != digest(commitment_payload(**tampered))


def test_canonical_output_is_encodable_on_a_windows_console_codec() -> None:
    """**Found on Windows, invisible on Linux — and it is not only a test bug.**

    The cross-process child originally used `print`, and died with
    `UnicodeEncodeError` on a cp1252 console while the canonical bytes were
    perfectly correct. Any code path in the peer that logs or prints a canonical
    payload containing a Hebrew team name will fail the same way, mid-match, on
    Diana's machine but never on a CI runner.

    The rule this pins down: canonical output is **bytes**, and anything that
    turns it back into console text must say UTF-8 explicitly.
    """
    payload = {"team": "הטובים", "hint": "צפונה — ✓"}
    encoded = canonical_json(payload).encode("utf-8")
    assert encoded.decode("utf-8") == canonical_json(payload)

    with pytest.raises(UnicodeEncodeError):
        canonical_json(payload).encode("cp1252")
