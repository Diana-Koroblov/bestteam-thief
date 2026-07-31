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


def test_sealed_carries_the_secrets_the_peer_must_withhold() -> None:
    """Move and intent are released at reveal; the nonce only at final reveal."""
    sealed = seal(STATE, "W", "lie")
    assert (sealed.move, sealed.intent) == ("W", "lie")
    assert sealed.nonce
