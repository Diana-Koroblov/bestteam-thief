"""Four traits, and the gate in front of each (TODO 8.3.2, 8.3.3; A3.4-A3.6).

The rule these tests exist to hold is A3.4: **below its gate a trait answers
None, never a default.** "Unknown" and "measured as zero" lead to opposite
behaviour — one says keep playing the unexploitable default, the other says the
opponent is deaf and the verbal layer is waste — so a trait that returned 0.0
before it had evidence would trigger the exploitation it was meant to gate.

The second rule is A3.5's two scopes, which is the easiest thing here to get
wrong: traits **bank** across the six sub-games of a series and **clear** for a
new opponent, while the trajectory they are measured from does neither.
"""

from __future__ import annotations

from core.domain.actions import Direction
from core.domain.opponent_profile import (
    MIN_MOVEMENT_SAMPLES,
    MIN_VERBAL_SAMPLES,
    TRAITS,
    MovementStyle,
    OpponentProfile,
)

FLEEING = [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (6, 1)]
CIRCLING = [(0, 1), (0, 2), (1, 2), (1, 1), (0, 1), (0, 2), (1, 2)]

FLEE_RATE, ORBIT_RATE = 0.65, 0.35


def walked(peaks, ours=(0, 0)) -> OpponentProfile:
    """Feed a trajectory of belief peaks through the profiler."""
    profile = OpponentProfile()
    for peak in peaks:
        profile.observe_peak(peak, ours)
    return profile


# --- trait 1: movement style ------------------------------------------------


def test_a_receding_peak_reads_as_a_fleer() -> None:
    """We never see the opponent (M#8), so the trajectory of our own belief peak
    is all there is to profile from."""
    profile = walked(FLEEING)
    assert profile.flee_fraction == 1.0
    assert profile.style(FLEE_RATE, ORBIT_RATE) is MovementStyle.FLEE_GREEDY


def test_a_repeating_peak_reads_as_an_orbiter() -> None:
    """Circling is what a revisited cell looks like from here."""
    profile = walked(CIRCLING, ours=(5, 5))
    assert profile.orbit_fraction >= ORBIT_RATE
    assert profile.style(FLEE_RATE, ORBIT_RATE) is MovementStyle.ORBITER


def test_the_fleer_reading_wins_when_both_thresholds_fire() -> None:
    """A greedy fleer on a finite board eventually revisits cells too, so
    revisiting is the weaker evidence and must not outvote the stronger."""
    profile = walked(FLEEING + FLEEING)
    assert profile.orbit_fraction >= ORBIT_RATE
    assert profile.style(FLEE_RATE, ORBIT_RATE) is MovementStyle.FLEE_GREEDY


def test_too_few_samples_declines_to_classify() -> None:
    """Adapting to a phantom read from three noisy peaks is worse than not
    adapting at all."""
    profile = walked(FLEEING[: MIN_MOVEMENT_SAMPLES - 1])
    assert profile.transitions < MIN_MOVEMENT_SAMPLES
    assert profile.style(FLEE_RATE, ORBIT_RATE) is MovementStyle.UNKNOWN


def test_a_missing_peak_is_skipped_rather_than_recorded_as_stationary() -> None:
    """Otherwise the turns we know least about would drag the flee rate toward
    zero and misclassify a fleer as a circler."""
    profile = OpponentProfile()
    profile.observe_peak(None, (0, 0))
    assert profile.visits == 0 and profile.transitions == 0


# --- trait 2: barrier rate --------------------------------------------------


def test_the_barrier_rate_is_walls_per_watched_turn() -> None:
    """**Not** walls per quota. A Cop that has spent 2 of 14 in three turns and
    one that spent 2 in thirty are opposite opponents, and only the denominator
    says so."""
    profile = OpponentProfile()
    for remaining in (14, 13, 13, 12, 12, 12, 12):
        profile.observe_quota(remaining)
    assert profile.barrier_rate == 2 / 6


def test_a_cop_that_never_walls_reads_as_zero_not_unknown() -> None:
    """The trait that pays for the Thief: a Cop that cannot spend barriers
    cannot catch us, and it must be distinguishable from one we have not
    watched long enough to judge."""
    profile = OpponentProfile()
    for _ in range(9):
        profile.observe_quota(14)
    assert profile.barrier_rate == 0.0


def test_the_barrier_rate_declines_to_speak_too_early() -> None:
    """A3.4 applies to the public trait as much as the inferred ones."""
    profile = OpponentProfile()
    for remaining in (14, 13):
        profile.observe_quota(remaining)
    assert profile.barrier_rate is None


def test_a_rising_quota_is_ignored_rather_than_counted_backwards() -> None:
    """A quota can only fall. A rise is a new sub-game or a corrupt reading, and
    subtracting it would credit the opponent with negative walls."""
    profile = OpponentProfile()
    for remaining in (10, 14, 13, 12, 11, 10, 9):
        profile.observe_quota(remaining)
    assert profile.barriers_seen == 5


# --- trait 3: hint responsiveness -------------------------------------------


def responded(pairs, claim=Direction.N) -> OpponentProfile:
    """Feed (before, after) peak pairs against a fixed claim of ours."""
    profile = OpponentProfile()
    for before, after in pairs:
        profile.observe_response(claim, before, after)
    return profile


def test_an_opponent_who_always_runs_the_claimed_way_reads_as_responsive() -> None:
    """Direction of the reaction is deliberately not assumed — a listening
    Thief runs from what we claim and a listening Cop runs toward it, so what is
    measured is the imbalance, not the sign."""
    north = [((3, 3), (2, 3)), ((2, 3), (1, 3)), ((4, 4), (3, 4)), ((5, 5), (4, 5))]
    assert responded(north).hint_responsiveness == 1.0


def test_an_opponent_who_always_runs_the_other_way_reads_as_responsive_too() -> None:
    """A consistently inverted reaction is still a reaction, and still worth
    spending tokens on."""
    south = [((3, 3), (4, 3)), ((2, 3), (3, 3)), ((4, 4), (5, 4)), ((5, 5), (6, 5))]
    assert responded(south).hint_responsiveness == 1.0


def test_a_deaf_opponent_reads_as_zero() -> None:
    """8.3.5's trigger. Equal along and against, so the imbalance cancels."""
    mixed = [((3, 3), (2, 3)), ((3, 3), (4, 3)), ((1, 1), (0, 1)), ((1, 1), (2, 1))]
    assert responded(mixed).hint_responsiveness == 0.0


def test_a_perpendicular_step_is_counted_and_not_discarded() -> None:
    """**Two of the four bearings are always perpendicular**, so an opponent
    moving at random lands there half the time. Dropping those samples would
    leave a one-in-four along against a three-in-four not-along, and report a
    coin-flipping opponent as strongly responsive."""
    across = [((3, 3), (3, 4)), ((3, 4), (3, 5)), ((3, 5), (3, 6)), ((3, 6), (3, 5))]
    profile = responded(across)
    assert profile.neutral == 4
    assert profile.hint_responsiveness == 0.0


def test_saying_nothing_records_nothing() -> None:
    """There is no correlation to measure against a claim we never made."""
    assert responded([((3, 3), (2, 3))] * 6, claim=None).hint_responsiveness is None


def test_responsiveness_declines_to_speak_below_its_gate() -> None:
    """Silence is the honest answer, and it is what keeps 8.3.5 from firing on
    three coincidences."""
    profile = responded([((3, 3), (2, 3))] * (MIN_VERBAL_SAMPLES - 1))
    assert profile.hint_responsiveness is None


# --- trait 4: reliability ---------------------------------------------------


def test_a_truthful_claim_raises_the_coefficient_and_a_lie_lowers_it() -> None:
    """The Beta posterior of 4.2.2, fed from the peaks rather than by hand."""
    honest, liar = OpponentProfile(), OpponentProfile()
    for _ in range(6):
        honest.observe_hint(Direction.N, (3, 3), (2, 3), 1.0, 0)
        liar.observe_hint(Direction.N, (3, 3), (4, 3), 1.0, 0)
    assert honest.reliability.coefficient > 0.5 > liar.reliability.coefficient


def test_an_uncheckable_claim_is_excluded_rather_than_scored_as_a_lie() -> None:
    """Otherwise a stationary opponent accumulates a reputation never earned."""
    profile = OpponentProfile()
    profile.observe_hint(Direction.N, (3, 3), (3, 3), 1.0, 0)
    profile.observe_hint(Direction.N, None, (2, 3), 1.0, 0)
    assert profile.reliability.checked == 0


def test_a_hint_naming_no_direction_is_not_evidence_of_anything() -> None:
    """Half the template bank says nothing directional on purpose."""
    profile = OpponentProfile()
    profile.observe_hint(None, (3, 3), (2, 3), 1.0, 0)
    assert profile.reliability.checked == 0


# --- A3.5: the two scopes ---------------------------------------------------


def test_traits_bank_across_a_sub_game_boundary() -> None:
    """Six sub-games against one team is the sample the traits are estimated
    from; clearing them each game would throw five sixths of it away."""
    profile = walked(FLEEING)
    profile.end_sub_game()
    profile.observe_peak((0, 0), (0, 0))
    assert profile.transitions == len(FLEEING) - 1
    assert profile.visits == len(FLEEING) + 1


def test_the_trajectory_does_not_survive_a_sub_game_boundary() -> None:
    """A cell 'revisited' across two different sub-games says nothing about
    whether this opponent circles, and a transition across the boundary is a
    move nobody made."""
    profile = walked([(0, 0), (0, 1)])
    profile.end_sub_game()
    profile.observe_peak((0, 0), (0, 0))
    assert profile.revisits == 0
    assert profile.transitions == 1


def test_a_new_opponent_clears_everything() -> None:
    """Teams may change code between matches, so a reputation earned by one is
    evidence about nobody else."""
    profile = walked(FLEEING)
    profile.for_opponent("someone else")
    assert profile.team == "someone else"
    assert profile.transitions == 0
    assert profile.style(FLEE_RATE, ORBIT_RATE) is MovementStyle.UNKNOWN


def test_the_same_opponent_keeps_their_record() -> None:
    """Called every turn, so it has to be a no-op when nothing has changed."""
    profile = walked(FLEEING)
    profile.for_opponent("")
    profile.for_opponent("")
    assert profile.transitions == len(FLEEING) - 1


# --- A3.6: at most four -----------------------------------------------------


def test_we_profile_exactly_the_number_of_traits_the_config_permits(minimal_config) -> None:
    """**A3.6.** 200 observed steps per series cannot support a fifth without
    fitting noise, and `max_profiled_traits` was a limit nothing enforced — a
    fifth trait could have been added without one test noticing. Asserted
    against the **shipped** config rather than a literal, so the number in the
    file and the number in the code cannot drift apart."""
    assert len(TRAITS) == minimal_config.get("strategy.max_profiled_traits")


def test_every_named_trait_is_actually_readable() -> None:
    """Otherwise the cap could be satisfied by naming traits that do not exist,
    which would make the check above a decoration."""
    profile = OpponentProfile()
    assert profile.style(FLEE_RATE, ORBIT_RATE) is MovementStyle.UNKNOWN
    assert profile.barrier_rate is None
    assert profile.hint_responsiveness is None
    assert profile.reliability.coefficient == 0.5


def test_it_describes_itself_without_inventing_a_number() -> None:
    """An ungated trait prints as '-'. A report that filled it with 0.00 would
    be asserting a measurement nobody made."""
    line = OpponentProfile(team="bestteam").describe()
    assert "bestteam" in line and "walls/turn -" in line and "listens -" in line
