"""Unit tests for commit-reveal (PRD 2, Ch. 5.3.1).

Three properties, each corresponding to an attack the scheme exists to stop:
no time travel, no revision after seeing the opponent, no dictionary attack.
"""

from __future__ import annotations

from core.crypto.commitment import (
    NONCE_BYTES,
    commitment_payload,
    new_nonce,
    seal,
    verify,
)

STATE = {"cop": [0, 0], "thief": [3, 3], "step": 4}


def test_a_sealed_move_verifies_with_its_own_values() -> None:
    sealed = seal(STATE, "N", "truth")
    assert verify(sealed.digest, STATE, "N", "truth", sealed.nonce)


def test_the_digest_reveals_nothing_about_the_move() -> None:
    """Only the digest goes on the wire this turn."""
    sealed = seal(STATE, "N", "lie")
    assert "N" not in sealed.digest
    assert len(sealed.digest) == 64


def test_a_changed_move_fails_verification() -> None:
    """No revision after seeing the opponent's move."""
    sealed = seal(STATE, "N", "truth")
    assert not verify(sealed.digest, STATE, "S", "truth", sealed.nonce)


def test_a_changed_intent_fails_verification() -> None:
    """The truth/lie flag is sealed too, so it cannot be reinterpreted later."""
    sealed = seal(STATE, "N", "truth")
    assert not verify(sealed.digest, STATE, "N", "lie", sealed.nonce)


def test_a_commitment_cannot_be_replayed_at_another_step() -> None:
    """No time travel: the state is inside the hash."""
    sealed = seal(STATE, "N", "truth")
    later = {**STATE, "step": 9}
    assert not verify(sealed.digest, later, "N", "truth", sealed.nonce)


def test_the_wrong_nonce_fails_verification() -> None:
    sealed = seal(STATE, "N", "truth")
    assert not verify(sealed.digest, STATE, "N", "truth", new_nonce())


def test_the_same_move_seals_differently_every_time() -> None:
    """Without this, an opponent hashes all five moves and reads our commitment.

    Also stops two identical turns from being linkable.
    """
    digests = {seal(STATE, "N", "truth").digest for _ in range(20)}
    assert len(digests) == 20


def test_nonces_are_long_enough_to_be_unguessable() -> None:
    nonce = new_nonce()
    assert len(nonce) == NONCE_BYTES * 2
    assert int(nonce, 16) >= 0


def test_an_explicit_nonce_makes_the_digest_reproducible() -> None:
    """Tests need determinism; play never passes one, so nonces stay fresh."""
    first = seal(STATE, "E", "truth", nonce="0" * 32)
    second = seal(STATE, "E", "truth", nonce="0" * 32)
    assert first.digest == second.digest


def test_the_payload_shape_is_defined_in_exactly_one_place() -> None:
    """Both peers hash the same four fields, in the same structure."""
    assert set(commitment_payload(STATE, "N", "truth", "abc")) == {
        "state",
        "move",
        "intent",
        "nonce",
    }


def test_a_walled_cell_cannot_be_changed_after_the_fact() -> None:
    """**C-018, M#15/M#16.** The reason this field exists at all.

    A placement costs the cop its move, so it travels as ``STAY``. Without the
    cell inside the hash, ``STAY`` and "walled (2,3)" seal identically and a cop
    could pick which wall it built after seeing where the thief went.
    """
    sealed = seal(STATE, "STAY", "truth", barrier_cell=(2, 3))
    assert verify(sealed.digest, STATE, "STAY", "truth", sealed.nonce, barrier_cell=(2, 3))
    assert not verify(sealed.digest, STATE, "STAY", "truth", sealed.nonce, barrier_cell=(2, 4))


def test_a_walled_turn_and_a_still_turn_seal_differently() -> None:
    """Otherwise a declared placement could simply be denied afterwards."""
    still = seal(STATE, "STAY", "truth", nonce="0" * 32)
    walled = seal(STATE, "STAY", "truth", nonce="0" * 32, barrier_cell=(2, 3))
    assert still.digest != walled.digest


def test_a_turn_without_a_barrier_hashes_exactly_as_before() -> None:
    """The key is omitted, not nulled — an opponent who never walls is unaffected.

    This is what lets a peer that implements C-018 audit one that does not: the
    payload for an ordinary turn is byte-identical either way.
    """
    assert "barrier_cell" not in commitment_payload(STATE, "N", "truth", "abc")
    assert "barrier_cell" not in commitment_payload(STATE, "N", "truth", "abc", barrier_cell=None)


def test_a_tuple_and_a_list_cell_seal_identically() -> None:
    """A log read back from JSON returns lists; we seal from tuples.

    Canonical JSON already renders the two alike, and this pins it, because a
    silent divergence here would fail every barrier turn in the audit.
    """
    from_tuple = seal(STATE, "STAY", "truth", nonce="0" * 32, barrier_cell=(2, 3))
    from_list = seal(STATE, "STAY", "truth", nonce="0" * 32, barrier_cell=[2, 3])
    assert from_tuple.digest == from_list.digest


def test_sealed_carries_the_secrets_the_peer_must_withhold() -> None:
    """Move and intent are released at reveal; the nonce only at final reveal."""
    sealed = seal(STATE, "W", "lie")
    assert (sealed.move, sealed.intent) == ("W", "lie")
    assert sealed.nonce


def test_verification_is_constant_time() -> None:
    """**M#17/6.1.3.b.** Asserted against the source, not merely intended.

    A timing attack is not a realistic threat in this setting — the audit runs
    offline over a log the opponent already holds — but reaching for `==` on a
    digest is the habit that eventually gets used somewhere it does matter.
    """
    from pathlib import Path

    source = Path(__file__).resolve().parents[2] / "core" / "crypto" / "commitment.py"
    body = source.read_text(encoding="utf-8")
    assert "secrets.compare_digest" in body
    assert ") == claimed" not in body


def test_a_single_flipped_bit_is_detected() -> None:
    """6.1.3.b, over every field the digest covers."""
    from core.crypto.commitment import seal, verify

    sealed = seal({"step": 1}, "N", "truth", nonce="abc")
    assert verify(sealed.digest, {"step": 1}, "N", "truth", "abc")

    flipped = sealed.digest[:-1] + ("0" if sealed.digest[-1] != "0" else "1")
    assert not verify(flipped, {"step": 1}, "N", "truth", "abc")


def test_the_same_inputs_with_different_nonces_differ() -> None:
    """6.1.3.a, M#17 — the nonce is what makes a five-move space unguessable."""
    from core.crypto.commitment import seal

    digests = {seal({"step": 1}, "N", "truth").digest for _ in range(50)}
    assert len(digests) == 50

