"""The end-of-match audit (TODO 6.1.4, 6.5.1).

**This is what makes lying safe to allow.** The rulebook lets an agent bluff
freely in words, and that only works because *moves* cannot be bluffed: each was
sealed before the opponent chose theirs, and at the end every seal is reopened.
A hint is an opinion; a commitment is a fact with a receipt.

So these tests are adversarial by construction. Each one forges a log the way a
losing opponent actually would, and checks that we catch it.
"""

from __future__ import annotations

import pytest

from core.crypto.audit import AuditResult, StepRecord, audit_log
from core.crypto.commitment import seal


def _honest(step: int, move: str = "N", intent: str = "truth") -> StepRecord:
    """One correctly sealed turn."""
    sealed = seal({"step": step}, move, intent)
    return StepRecord(
        step=step,
        claimed_digest=sealed.digest,
        state={"step": step},
        move=sealed.move,
        intent=sealed.intent,
        nonce=sealed.nonce,
    )


def _log(length: int = 5) -> list[StepRecord]:
    return [_honest(step) for step in range(1, length + 1)]


def test_an_honest_log_passes() -> None:
    result = audit_log(_log())
    assert result.passed
    assert result.checked == 5
    assert "Verified OK" in result.describe()


# --- the forgeries ----------------------------------------------------------


def test_a_changed_move_is_caught() -> None:
    """The core claim: you cannot revise a move after seeing the opponent's."""
    log = _log()
    log[2] = StepRecord(**{**log[2].__dict__, "move": "S"})
    result = audit_log(log)
    assert not result.passed
    assert result.failures[0][0] == 3


def test_a_changed_intent_is_caught() -> None:
    """Lying is legal; **misdeclaring the flag afterwards is forgery** (Ch. 5.3.1).

    Without this, a peer caught in a costly lie could claim it had been flagged
    as a lie all along — and the Intent flag would be worthless.
    """
    log = _log()
    log[1] = StepRecord(**{**log[1].__dict__, "intent": "lie"})
    assert not audit_log(log).passed


def test_a_changed_state_is_caught() -> None:
    log = _log()
    log[0] = StepRecord(**{**log[0].__dict__, "state": {"step": 99}})
    assert not audit_log(log).passed


def test_a_swapped_nonce_is_caught() -> None:
    """Nonces are withheld until the final reveal, then all of them must fit."""
    log = _log()
    log[3] = StepRecord(**{**log[3].__dict__, "nonce": log[0].nonce})
    assert not audit_log(log).passed


def test_replaying_a_step_at_a_different_turn_is_caught() -> None:
    """**No time travel — and this test found a real hole in the audit.**

    The first version of `audit_log` verified every seal and checked that step
    numbers increase. Both passed here, and the forgery still went through: a
    genuine step-1 commitment relabelled as step 4 still matches *its own*
    sealed state, and the outer numbers still ascend.

    Nothing compared the **declared** step against the one sealed inside the
    state. The commitment docstring promises "no time travel", but that promise
    only holds if the audit actually checks it.
    """
    log = _log()
    stolen = log[0]
    log[3] = StepRecord(**{**stolen.__dict__, "step": 4})
    result = audit_log(log)
    assert not result.passed
    assert "replays the commitment sealed for step 1" in result.failures[0][1]


def test_a_state_without_a_step_key_is_not_rejected() -> None:
    """The replay check must not become a schema preference.

    A peer may seal a state shaped differently from ours. Failing their whole
    log over that would be an accusation we could not support.
    """
    sealed = seal("opaque-state-string", "N", "truth")
    record = StepRecord(1, sealed.digest, "opaque-state-string", "N", "truth", sealed.nonce)
    assert audit_log([record]).passed


def test_reordered_steps_are_caught_even_though_each_seal_verifies() -> None:
    """**Re-hashing alone is not enough, and this is the subtle case.**

    Every individual seal in a reordered log still verifies — the forger did not
    touch any single record. Only the *sequence* is a lie, so the audit has to
    check ordering explicitly or a replayed history passes cleanly.
    """
    log = _log()
    log[1], log[3] = log[3], log[1]
    assert not audit_log(log).passed
    assert "increasing" in audit_log(log).failures[0][1]


def test_a_duplicated_step_is_caught() -> None:
    log = _log()
    log.append(log[2])
    assert not audit_log(log).passed
    assert any("duplicate" in reason for _, reason in audit_log(log).failures)


# --- how it reports ---------------------------------------------------------


def test_an_empty_log_does_not_pass() -> None:
    """**A missing log is not a clean one.**

    Treating them alike would let a peer escape the audit entirely by sending
    nothing at all — the cheapest possible forgery.
    """
    result = audit_log([])
    assert not result.passed
    assert "empty log" in result.describe()


def test_every_failure_is_reported_not_just_the_first() -> None:
    """A forged log is an expected input, so the audit never raises.

    Raising would stop at the first fault; we want the whole picture, because
    the pattern of failures is what distinguishes a bug from a forgery.
    """
    log = _log()
    log[0] = StepRecord(**{**log[0].__dict__, "move": "S"})
    log[2] = StepRecord(**{**log[2].__dict__, "move": "E"})
    result = audit_log(log)
    assert len(result.failures) == 2


def test_failures_name_the_step_and_the_reason() -> None:
    """"The audit failed" is not something a grader — or we — can act on."""
    log = _log()
    log[1] = StepRecord(**{**log[1].__dict__, "move": "W"})
    step, reason = audit_log(log).failures[0]
    assert step == 2
    assert "digest" in reason


def test_the_sealed_scent_field_is_audited_when_present() -> None:
    """C-008: a fabricated field must fail once both peers agreed to seal it."""
    sealed = seal({"step": 1}, "N", "truth", scent_digest="real")
    honest = StepRecord(1, sealed.digest, {"step": 1}, "N", "truth", sealed.nonce, "real")
    forged = StepRecord(1, sealed.digest, {"step": 1}, "N", "truth", sealed.nonce, "fabricated")
    assert audit_log([honest]).passed
    assert not audit_log([forged]).passed


@pytest.mark.parametrize("length", [1, 2, 35])
def test_it_scales_from_one_step_to_a_full_sub_game(length: int) -> None:
    assert audit_log(_log(length)).checked == length


def test_the_result_reports_nothing_about_who_wins() -> None:
    """**Evidence and sanctions stay separate** (M#19).

    If this module decided outcomes, a change to the scoring table could alter
    what counts as proof. It reports mismatches; the rules layer decides.
    """
    fields = set(AuditResult().__dict__)
    assert fields == {"checked", "failures"}
