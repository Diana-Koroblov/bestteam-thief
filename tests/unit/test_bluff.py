"""Cheap truth, expensive lies (TODO 8.3.4, 8.3.5; A3.7-A3.12).

The policy's claim is a specific one and these tests are written to be able to
falsify it: **we are honest exactly when honesty is cheap**, and the credibility
that buys is spent on the turns where our words are actually worth something.

Two things are asserted about the *shape* rather than the outcome, because they
are what makes the rest safe. A3.2 — nothing here reads the turn number, so a
lie is never on a schedule an opponent can learn. And Ch. 5.3.1 — a `LIE` flag
always names a bearing, because the flag is what the audit reads and a
confession over a hint that claims nothing is a record of a lie never told.
"""

from __future__ import annotations

import pytest

from core.domain.actions import Direction
from core.domain.bluff import BluffPolicy, BluffSettings, information_value
from core.domain.board import Board
from core.domain.intent import Intent
from core.domain.opponent_profile import MIN_VERBAL_SAMPLES, OpponentProfile
from core.domain.trail import TrailTracker

BOARD = Board(grid_size=7)
CENTRE = (3, 3)


def trail_over(cells) -> TrailTracker:
    """A trail laid by standing on each of *cells* in turn."""
    trail = TrailTracker()
    for cell in cells:
        trail.observe(cell, BOARD)
    return trail


def deaf(turns: int = MIN_VERBAL_SAMPLES + 2) -> OpponentProfile:
    """A profile with enough evidence to say the opponent ignores us."""
    profile = OpponentProfile()
    for index in range(turns):
        # Alternating along and against, which cancels to an imbalance of zero.
        after = (2, 3) if index % 2 else (4, 3)
        profile.observe_response(Direction.N, (3, 3), after)
    return profile


# --- A3.7: the information value -------------------------------------------

# Four turns walking north up column 3, ending on the centre. The field is loud
# to the south of us and silent to the north.
WALKED_NORTH = [(6, 3), (5, 3), (4, 3), (3, 3)]


def test_a_trail_with_no_history_makes_every_claim_expensive() -> None:
    """Nothing of ours on the board, so naming our bearing hands them something
    the field does not contain."""
    assert information_value(TrailTracker(), CENTRE, Direction.N, BOARD) == 1.0


def test_a_straight_run_gives_the_bearing_away_for_free() -> None:
    """Loud behind, silent ahead. Anyone reading the gradient already knows the
    heading, so saying it out loud costs nothing — and banks credibility (A3.8)."""
    assert information_value(trail_over(WALKED_NORTH), CENTRE, Direction.N, BOARD) < 0.6


def test_doubling_back_is_expensive_however_loud_the_trail() -> None:
    """**The sign matters.** The field records where we have been, so a reversal
    is exactly the move it does *not* predict. A reading that took absolute
    loudness would call this cheap and be wrong in the most useful case."""
    assert information_value(trail_over(WALKED_NORTH), CENTRE, Direction.S, BOARD) == 1.0


def test_turning_across_our_own_trail_is_expensive() -> None:
    """Nothing in a north-south smear says whether we are about to go east."""
    assert information_value(trail_over(WALKED_NORTH), CENTRE, Direction.E, BOARD) > 0.9


def test_the_reading_is_taken_ahead_and_behind_and_not_underfoot() -> None:
    """**The bug this replaced.** The trail is updated before the claim is
    chosen, so our own cell always carries a full-strength deposit we laid this
    turn. A reading taken there is saturated on every turn of every game: the lie
    would never once be eligible, and the null result would look exactly like a
    tactic that does nothing rather than one that never ran."""
    standing = trail_over([CENTRE] * 5)
    # `approx`, because summing the two halves of a symmetric window in float
    # leaves the halves differing in the last bit. The claim is that the reading
    # is saturated, not that two float sums are bit-identical.
    assert information_value(standing, CENTRE, Direction.N, BOARD) == pytest.approx(1.0)


def test_holding_position_is_always_maximum_value() -> None:
    """STAY has no bearing, so no trail can have leaked it."""
    assert information_value(trail_over(WALKED_NORTH), CENTRE, Direction.STAY, BOARD) == 1.0


# --- A3.8: low value buys credibility ---------------------------------------


def test_a_cheap_claim_is_told_truthfully_and_names_our_real_bearing() -> None:
    """A3.8. It costs nothing they did not already have, and it still builds r."""
    policy = BluffPolicy(settings=BluffSettings(seed=1))
    running = trail_over(WALKED_NORTH)
    intent, claim = policy.decide(Direction.N, CENTRE, running, BOARD, OpponentProfile())
    assert (intent, claim) == (Intent.TRUTH, Direction.N)


def test_cheap_truths_raise_the_credibility_bank_and_never_spend_it() -> None:
    """The bank is what A3.9 spends, so it has to actually fill — and a turn
    that is cheap must never be the one it is spent on."""
    policy = BluffPolicy(settings=BluffSettings(seed=1))
    running = trail_over(WALKED_NORTH)
    before = policy.honesty.coefficient
    for _ in range(5):
        policy.decide(Direction.N, CENTRE, running, BOARD, OpponentProfile())
    assert policy.honesty.coefficient > before
    assert policy.lies == 0


# --- A3.9: high value spends it ---------------------------------------------


def test_an_expensive_claim_is_sometimes_a_lie_and_the_lie_is_reversed() -> None:
    """A3.9 and the herding lie in one: the reverse bearing is derived from the
    move we actually chose, so it is board-driven rather than scripted."""
    policy = BluffPolicy(settings=BluffSettings(seed=20260812))
    told = [
        policy.decide(Direction.N, CENTRE, TrailTracker(), BOARD, OpponentProfile())
        for _ in range(30)
    ]
    lies = [claim for intent, claim in told if intent is Intent.LIE]
    assert lies, "a quiet trail is the case the lie exists for"
    assert set(lies) == {Direction.S}


def test_credibility_must_be_banked_before_it_can_be_spent() -> None:
    """**A3.9, literally.** `trust` is 0 at a mixed record, so the first claim
    against a stranger cannot be a lie — which is correct: a lie is only worth
    telling to someone who has reason to believe us."""
    policy = BluffPolicy(settings=BluffSettings(seed=20260812))
    assert policy.honesty.trust == 0.0
    intent, _ = policy.decide(Direction.N, CENTRE, TrailTracker(), BOARD, OpponentProfile())
    assert intent is Intent.TRUTH


def test_the_record_settles_on_the_believable_side_of_mixed() -> None:
    """**The reason the draw weights on `trust` and not on the coefficient.**
    Drawing against the coefficient converges to 0.5 — the "mixed" reading that
    `reliability.py` calls worthless, where an opponent ignores our lies *and*
    our truths. Weighting on trust settles near two truths to one lie, so the
    words stay worth acting on and the bluff keeps its bite."""
    policy = BluffPolicy(settings=BluffSettings(seed=20260812))
    for _ in range(60):
        policy.decide(Direction.N, CENTRE, TrailTracker(), BOARD, OpponentProfile())
    assert policy.lies > 0
    assert 0.55 < policy.honesty.coefficient < 0.8


def test_nothing_in_the_policy_reads_the_turn_number() -> None:
    """**A3.2.** Deception is triggered by board state, never by a schedule, so
    the same state must produce the same decision whenever it occurs."""
    first = BluffPolicy(settings=BluffSettings(seed=4))
    second = BluffPolicy(settings=BluffSettings(seed=4))
    for _ in range(7):
        first.decide(Direction.N, CENTRE, TrailTracker(), BOARD, OpponentProfile())
    assert first.decide(
        Direction.N, CENTRE, TrailTracker(), BOARD, OpponentProfile()
    ) == _nth(second, 8)


def _nth(policy: BluffPolicy, count: int):
    """Return the *count*-th decision from a fresh policy, all state identical."""
    result = None
    for _ in range(count):
        result = policy.decide(Direction.N, CENTRE, TrailTracker(), BOARD, OpponentProfile())
    return result


# --- A3.10: the Cop spends credibility to herd ------------------------------


def test_herding_makes_a_cheap_turn_eligible_to_lie() -> None:
    """A3.10. In Phase A the lie has a *job* — steering a fleeing Thief into the
    region we picked — so it is worth telling even when concealment is not."""
    running = trail_over(WALKED_NORTH)
    plain = BluffPolicy(settings=BluffSettings(seed=20260812))
    herd = BluffPolicy(settings=BluffSettings(seed=20260812))
    honest = [
        plain.decide(Direction.N, CENTRE, running, BOARD, OpponentProfile())[0] for _ in range(20)
    ]
    herding = [
        herd.decide(Direction.N, CENTRE, running, BOARD, OpponentProfile(), herding=True)[0]
        for _ in range(20)
    ]
    assert set(honest) == {Intent.TRUTH}
    assert Intent.LIE in herding


# --- A3.12 / 8.3.5: stop talking to someone who is not listening ------------


def test_a_measured_deaf_opponent_silences_the_verbal_layer() -> None:
    """The tokens and the exposure are both waste against someone who ignores
    every word."""
    policy = BluffPolicy(settings=BluffSettings(seed=1))
    intent, claim = policy.decide(Direction.N, CENTRE, TrailTracker(), BOARD, deaf())
    assert (intent, claim) == (Intent.TRUTH, None)


def test_an_unmeasured_opponent_is_not_treated_as_deaf() -> None:
    """`None` means we have not looked, which is not the same as looking and
    finding zero — and gating on the difference is the whole of A3.4."""
    quiet = deaf(turns=MIN_VERBAL_SAMPLES - 1)
    assert quiet.hint_responsiveness is None
    _, claim = BluffPolicy(settings=BluffSettings(seed=1)).decide(
        Direction.N, CENTRE, TrailTracker(), BOARD, quiet
    )
    assert claim is not None


# --- structural guarantees --------------------------------------------------


def test_holding_position_claims_nothing() -> None:
    """STAY has no bearing, and inventing one would be a lie we did not decide
    to tell."""
    policy = BluffPolicy(settings=BluffSettings(seed=1))
    assert policy.decide(
        Direction.STAY, CENTRE, TrailTracker(), BOARD, OpponentProfile()
    ) == (Intent.TRUTH, None)


def test_a_lie_always_names_a_bearing() -> None:
    """**Ch. 5.3.1.** The flag is what the audit reads; a `LIE` over a hint that
    claims nothing would put a confession in the record for a lie never told."""
    policy = BluffPolicy(settings=BluffSettings(seed=20260812))
    for _ in range(40):
        intent, claim = policy.decide(
            Direction.W, CENTRE, TrailTracker(), BOARD, OpponentProfile()
        )
        assert claim is not None or intent is Intent.TRUTH


def test_disabled_pins_every_turn_to_silence() -> None:
    """The control arm 8.3.6 measures against. It has to be *exact*: a control
    that still occasionally spoke would be measuring two verbal layers."""
    policy = BluffPolicy(settings=BluffSettings(enabled=False, seed=1))
    for _ in range(10):
        assert policy.decide(
            Direction.N, CENTRE, TrailTracker(), BOARD, OpponentProfile()
        ) == (Intent.TRUTH, None)
    assert policy.lies == 0


# --- replayability ----------------------------------------------------------


def test_the_same_seed_produces_the_same_lies() -> None:
    """A lie has to be reproducible from the log like everything else."""
    def told(seed: int):
        policy = BluffPolicy(settings=BluffSettings(seed=seed))
        return [
            policy.decide(Direction.N, CENTRE, TrailTracker(), BOARD, OpponentProfile())
            for _ in range(15)
        ]

    assert told(11) == told(11)
    assert told(11) != told(12)


def test_a_restart_re_seeds_but_keeps_the_credibility_bank() -> None:
    """The opponent's memory of us does not reset between sub-games, so neither
    does ours. Only `for_opponent` draws that line (A3.5)."""
    policy = BluffPolicy(settings=BluffSettings(seed=3))
    for _ in range(8):
        policy.decide(Direction.N, CENTRE, TrailTracker(), BOARD, OpponentProfile())
    banked = policy.honesty.coefficient
    policy.restart(2)
    assert policy.honesty.coefficient == banked


def test_settings_come_from_config_when_it_offers_them() -> None:
    """Tuning must not need a code change; the defaults must not need a config."""

    class Stub:
        def get(self, path: str, default: object = None) -> object:
            return {"strategy.bluff_enabled": False, "game.seed": 42}.get(path, default)

    settings = BluffSettings.from_config(Stub())
    assert settings.enabled is False and settings.seed == 42
    assert BluffSettings.from_config(None) == BluffSettings()
