"""Dating a scent reading (TODO 4.1.9) and sealing our own field (4.1.8, C-008).

A reading is not only *"they were near here"* — it is *"they were near here,
this many turns ago"*. Recovering the age turns one number into a timestamp,
which is what separates a stale trail from a fresh one.
"""

from __future__ import annotations

import pytest

from core.crypto.canonical import canonical_json
from core.crypto.commitment import commitment_payload, seal, verify
from core.domain.board import Board
from core.domain.scent import decay, emit
from core.domain.scent_residual import MAX_AGE, age_of, freshest_source

BOARD = Board(grid_size=7)


# --- 4.1.9 residual recovery ------------------------------------------------


@pytest.mark.parametrize("turns", list(range(0, 8)))
def test_a_decayed_deposit_reports_its_own_age(turns: int) -> None:
    """Round-trip against the real decay function, not against arithmetic."""
    field = emit((3, 3), BOARD)
    for _ in range(turns):
        field = decay(field, 0.10)
    assert age_of(field[(3, 3)], 0.10) == turns


def test_it_works_under_the_reference_decay_model_too() -> None:
    """**C-007: we may end up playing either model, so both must invert.**

    Which one is in force is settled at the handshake by the M#23 digest
    (0.90 → 0.81 for the book, 0.90 → 0.80 for the reference). Implementing
    only one would leave us unable to read half the league.
    """
    assert age_of(0.80, 0.10, "subtractive") == 1
    assert age_of(0.70, 0.10, "subtractive") == 2


def test_the_two_models_agree_early_and_diverge_later() -> None:
    """**They agree at one turn, which is exactly why C-007 is dangerous.**

    At 0.81 both models return 1, so a single early reading cannot tell them
    apart — the divergence only shows up further down the curve, by which point
    a match is already being played on a mistaken assumption. That is the case
    for settling the model at the **handshake** via the M#23 digest rather than
    inferring it from readings.
    """
    assert age_of(0.81, 0.10, "multiplicative") == age_of(0.81, 0.10, "subtractive") == 1
    assert age_of(0.5905, 0.10, "multiplicative") == 4
    assert age_of(0.5905, 0.10, "subtractive") == 3


@pytest.mark.parametrize("reading", [0.0, -0.1, 1.5])
def test_an_impossible_reading_is_not_dated(reading: float) -> None:
    """Stronger than a fresh deposit, or absent. Neither can be aged."""
    assert age_of(reading, 0.10) is None


def test_a_trace_older_than_the_horizon_is_refused() -> None:
    """**None, not a large number.**

    A confident timestamp on a trace that faded twenty turns ago is worse than
    no timestamp: it would send the Cop chasing where the Thief used to be.
    """
    ancient = 0.9 * (0.9 ** (MAX_AGE + 5))
    assert age_of(ancient, 0.10) is None


def test_the_freshest_source_is_the_strongest_reading() -> None:
    """Distance and age both weaken a deposit; only the peak is unambiguous."""
    cell, age = freshest_source(emit((5, 5), BOARD), 0.10)
    assert cell == (5, 5)
    assert age == 0


def test_an_empty_field_yields_no_source() -> None:
    assert freshest_source({}, 0.10) == (None, None)


# --- 4.1.8 sealing our own scent field (C-008) ------------------------------


def test_the_payload_is_byte_identical_when_sealing_is_off() -> None:
    """**The trap, and the reason this is opt-in.**

    The opponent recomputes our digests during the audit using *their* payload
    builder. If we added a ``"scent_digest": null`` key that they do not, every
    digest we ever sent would fail their verification and we would look like
    forgers — a total technical loss.

    So "off" must mean the key is *absent*, not null. Asserted on the canonical
    bytes, because that is what is actually hashed.
    """
    without = commitment_payload("state", "N", "truth", "abc")
    explicit_none = commitment_payload("state", "N", "truth", "abc", None)
    assert canonical_json(without) == canonical_json(explicit_none)
    assert "scent_digest" not in canonical_json(without)


def test_sealing_changes_the_digest() -> None:
    """Otherwise the seal would be decorative — C-008 would still be open."""
    plain = seal("state", "N", "truth", nonce="abc")
    sealed = seal("state", "N", "truth", nonce="abc", scent_digest="f9d248c2")
    assert plain.digest != sealed.digest


def test_a_sealed_field_verifies_only_against_the_same_field() -> None:
    """A fabricated field now fails the audit, which is the whole point."""
    sealed = seal("state", "N", "truth", nonce="abc", scent_digest="real")
    assert verify(sealed.digest, "state", "N", "truth", "abc", "real")
    assert not verify(sealed.digest, "state", "N", "truth", "abc", "fabricated")
    assert not verify(sealed.digest, "state", "N", "truth", "abc")


def test_an_unsealed_commitment_still_verifies_the_old_way() -> None:
    """Backwards compatible, because most opponents will not agree to N13c."""
    sealed = seal("state", "N", "truth", nonce="abc")
    assert verify(sealed.digest, "state", "N", "truth", "abc")
