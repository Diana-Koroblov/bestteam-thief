"""Modelling one opponent across the 6-sub-game series (TODO 4.4.3).

*Original extension — README material.*

The discipline these tests enforce is **abstention**. A model that always
answers is worse than one that stays quiet: the belief filter already has the
scent field, which cannot lie, and a confident wrong prediction actively
degrades it. So most of what follows checks that the model refuses to speak
when it has not earned the right to.
"""

from __future__ import annotations

from core.domain.actions import Direction
from core.domain.opponent_model import MIN_SAMPLES, OpponentModel


def _greedy_fleer(model: OpponentModel, samples: int = 12) -> OpponentModel:
    """An opponent south-east of us who always runs further away."""
    for _ in range(samples):
        model.record(theirs=(5, 5), ours=(2, 2), move=Direction.S)
    return model


def test_an_unobserved_opponent_reports_nothing_rather_than_zero() -> None:
    """**None, not 0.0.** "We have not looked" and "they never flee" are
    different claims, and only one of them is true on turn one."""
    fresh = OpponentModel(role="thief")
    assert fresh.flee_rate is None
    assert fresh.stay_rate is None
    assert fresh.predictability == 0.0
    assert "no sightings" in fresh.describe()


def test_it_refuses_to_predict_from_too_few_samples() -> None:
    """Three sub-games is ~100 moves; one bucket may still hold two.

    Guessing from two observations is how a model becomes a liability instead of
    an edge.
    """
    model = OpponentModel(role="thief")
    for _ in range(MIN_SAMPLES - 1):
        model.record(theirs=(5, 5), ours=(2, 2), move=Direction.S)
    move, confidence = model.predict(theirs=(5, 5), ours=(2, 2))
    assert move is None
    assert confidence == 0.0


def test_a_greedy_fleer_is_detected_and_predicted() -> None:
    """**The cheapest high-value hypothesis, and the one to test first.**

    The book's baseline Thief maximises distance and most teams will build
    something close. A flee rate near 1.0 says theirs is greedy — which makes it
    *herdable*, because a greedy fleer always takes the bait of the furthest
    cell and can be walked into a corner.
    """
    model = _greedy_fleer(OpponentModel(role="thief"))
    assert model.flee_rate == 1.0
    move, confidence = model.predict(theirs=(5, 5), ours=(2, 2))
    assert move is Direction.S
    assert confidence == 1.0


def test_an_unpredictable_opponent_reports_low_confidence() -> None:
    """It must be able to say "I do not know", or the number means nothing."""
    model = OpponentModel(role="thief")
    for move in [Direction.N, Direction.S, Direction.E, Direction.W] * 3:
        model.record(theirs=(5, 5), ours=(2, 2), move=move)
    _, confidence = model.predict(theirs=(5, 5), ours=(2, 2))
    assert confidence <= 0.3
    assert model.predictability <= 0.3


def test_the_two_roles_are_modelled_separately() -> None:
    """**Their Cop and their Thief are different programs.**

    Merging them would average two unrelated policies into one that describes
    neither — and the whole point is that we face each of them three times.
    """
    cop_model = OpponentModel(role="cop")
    thief_model = OpponentModel(role="thief")
    _greedy_fleer(thief_model)
    for _ in range(12):
        cop_model.record(theirs=(5, 5), ours=(2, 2), move=Direction.N)
    assert thief_model.flee_rate == 1.0
    assert cop_model.flee_rate == 0.0


def test_buckets_are_by_direction_not_by_exact_cell() -> None:
    """Nine buckets, not 49.

    Bucketing by exact offset would give one sample per bucket — a table that
    memorises the series instead of describing the policy.
    """
    model = OpponentModel(role="thief")
    for offset in range(MIN_SAMPLES):
        model.record(theirs=(5, 5 + offset % 2), ours=(2, 2), move=Direction.S)
    move, _ = model.predict(theirs=(6, 6), ours=(1, 1))  # same quadrant, different cells
    assert move is Direction.S


def test_staying_still_is_not_counted_as_fleeing() -> None:
    """A cornered opponent holds position; that is the opposite of fleeing."""
    model = OpponentModel(role="thief")
    for _ in range(8):
        model.record(theirs=(5, 5), ours=(2, 2), move=Direction.STAY)
    assert model.flee_rate == 0.0
    assert model.stay_rate == 1.0


def test_the_description_carries_the_sample_size() -> None:
    """"predictability 0.9 over 12 moves" is a claim; "0.9" alone is not."""
    described = _greedy_fleer(OpponentModel(role="thief")).describe()
    assert "12 moves" in described
    assert "flee 1.00" in described
