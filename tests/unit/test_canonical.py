"""Unit tests for canonical serialisation.

These are the cheapest tests in the project and they guard the most expensive
failure: a digest mismatch that makes an honest opponent look like a forger.
"""

from __future__ import annotations

import hashlib

from core.crypto.canonical import canonical_bytes, canonical_json, digest


def test_key_order_does_not_change_the_bytes() -> None:
    """Two dicts built in different orders must serialise identically."""
    first = {"b": 1, "a": 2}
    second = {"a": 2, "b": 1}
    assert canonical_json(first) == canonical_json(second)
    assert digest(first) == digest(second)


def test_nested_key_order_does_not_change_the_bytes() -> None:
    """Sorting must reach into nested structures, not just the top level."""
    first = {"outer": {"z": [1, 2], "y": {"n": 1, "m": 2}}}
    second = {"outer": {"y": {"m": 2, "n": 1}, "z": [1, 2]}}
    assert digest(first) == digest(second)


def test_no_incidental_whitespace() -> None:
    """Separators are pinned, so no space creeps in after ``:`` or ``,``."""
    assert canonical_json({"a": 1, "b": [1, 2]}) == '{"a":1,"b":[1,2]}'


def test_list_order_is_preserved() -> None:
    """Sorting applies to keys only. Move order is meaningful and must survive."""
    assert canonical_json(["S", "N"]) == '["S","N"]'


def test_non_ascii_is_not_escaped() -> None:
    """Text is encoded as itself, so the bytes depend on the text alone."""
    assert canonical_json({"team": "משטרה"}) == '{"team":"משטרה"}'


def test_digest_matches_sha256_of_the_bytes() -> None:
    """The digest is exactly SHA-256 over the canonical bytes, nothing more."""
    payload = {"move": "N", "nonce": "abc"}
    expected = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    assert digest(payload) == expected
    assert len(expected) == 64


def test_digest_changes_when_any_value_changes() -> None:
    """A commitment that ignored part of its payload would be worthless."""
    base = {"state": 1, "move": "N", "intent": "chase", "nonce": "x"}
    for key in base:
        altered = dict(base)
        altered[key] = "changed"
        assert digest(altered) != digest(base), key


def test_float_rendering_is_stable() -> None:
    """The pheromone constants must round-trip to the same text every run."""
    assert canonical_json({"decay": 0.1, "centre": 0.9}) == '{"centre":0.9,"decay":0.1}'
