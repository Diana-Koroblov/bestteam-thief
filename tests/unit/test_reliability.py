"""Learning who lies, and what to do about it (TODO 4.2.2, 4.4.2).

*Original extension — README material.*

The rulebook permits lying and says nothing about noticing. The claim these
tests defend is that a **systematic liar is more useful than an honest
opponent**: a reliably inverted signal is still a signal, and only a mixed
record is genuinely worthless.
"""

from __future__ import annotations

from core.domain.actions import Direction
from core.domain.reliability import Reliability, claim_matches_scent

# --- the coefficient --------------------------------------------------------


def test_a_stranger_is_worth_exactly_nothing() -> None:
    """**0.5, and trust of 0, so their words are a no-op on turn one.**

    The honest starting position against an opponent we have never played. A
    prior of anything else would be us inventing a reputation.
    """
    fresh = Reliability()
    assert fresh.coefficient == 0.5
    assert fresh.trust == 0.0
    assert fresh.checked == 0


def test_one_observation_does_not_produce_certainty() -> None:
    """**Why a Beta posterior and not a running average.**

    A mean would read 1.0 after a single truthful hint — total certainty at
    exactly the moment an opponent's first claim is least representative, and
    the moment a clever one would spend a cheap truth to buy it.
    """
    record = Reliability()
    record.record(truthful=True)
    assert 0.6 < record.coefficient < 0.7


def test_it_converges_toward_zero_against_a_consistent_liar() -> None:
    record = Reliability()
    for _ in range(20):
        record.record(truthful=False)
    assert record.coefficient < 0.1
    assert record.trust < -0.8


def test_it_converges_toward_one_against_a_truthful_opponent() -> None:
    record = Reliability()
    for _ in range(20):
        record.record(truthful=True)
    assert record.coefficient > 0.9
    assert record.trust > 0.8


def test_a_mixed_record_stays_near_the_middle() -> None:
    """The genuinely useless case — unlike a liar, who is readable."""
    record = Reliability()
    for turn in range(20):
        record.record(truthful=turn % 2 == 0)
    assert 0.4 < record.coefficient < 0.6


def test_a_barely_understood_claim_moves_the_record_less() -> None:
    """Weighted by parser confidence, so a vague opponent cannot dilute on purpose."""
    firm, vague = Reliability(), Reliability()
    for _ in range(10):
        firm.record(truthful=False, weight=0.9)
        vague.record(truthful=False, weight=0.2)
    assert firm.coefficient < vague.coefficient


# --- what counts as checkable ----------------------------------------------


def test_a_matching_move_is_truthful() -> None:
    assert claim_matches_scent(Direction.N, (4, 3), (3, 3)) is True


def test_a_contradicted_move_is_a_lie() -> None:
    assert claim_matches_scent(Direction.N, (3, 3), (4, 3)) is False


def test_an_unverifiable_claim_is_excluded_rather_than_scored() -> None:
    """**None is not a soft False, and the difference is exploitable.**

    With no scent peak, or an opponent who did not move, the claim cannot be
    checked. Scoring that as a lie would let a stationary opponent accumulate a
    reputation they never earned — and would let *us* act on it.
    """
    assert claim_matches_scent(Direction.N, None, (3, 3)) is None
    assert claim_matches_scent(Direction.N, (3, 3), None) is None
    assert claim_matches_scent(Direction.N, (3, 3), (3, 3)) is None


# --- recorded, but deliberately not acted on (Phase 7 ablation) -------------


def test_the_beta_score_is_blind_to_ordering() -> None:
    """**The real weakness, stated as a test rather than left implicit.**

    A Beta posterior is *exchangeable*. Twelve truths then two lies scores the
    same as two lies then twelve truths — and "build trust, then spend it at the
    decisive turn" is exactly the strategy that exploits it.

    Asserting the blindness keeps it honest: if someone later wires recency
    weighting into `coefficient`, this test fails and forces the change to be
    deliberate rather than accidental.
    """
    late = Reliability()
    for step in range(12):
        late.record(True, step=step)
    late.record(False, step=12)
    late.record(False, step=13)

    early = Reliability()
    early.record(False, step=0)
    early.record(False, step=1)
    for step in range(2, 14):
        early.record(True, step=step)

    assert abs(late.coefficient - early.coefficient) < 1e-9


def test_the_decayed_score_is_not_blind_to_ordering() -> None:
    """The prepared alternative, measured but unused (see the module docstring)."""
    late = Reliability()
    for step in range(12):
        late.record(True, step=step)
    late.record(False, step=12)

    early = Reliability()
    early.record(False, step=0)
    for step in range(1, 13):
        early.record(True, step=step)

    assert late.decayed_coefficient() < early.decayed_coefficient()


def test_the_timeline_records_when_not_just_how_often() -> None:
    record = Reliability()
    record.record(True, step=3)
    record.record(False, step=7)
    assert record.timeline == [(3, True), (7, False)]
    assert record.turns_since_last_lie(now=12) == 5


def test_an_opponent_who_never_lied_has_no_last_lie() -> None:
    """None, not 0 — "never" and "just now" must not read the same."""
    record = Reliability()
    record.record(True, step=1)
    assert record.turns_since_last_lie(now=9) is None
