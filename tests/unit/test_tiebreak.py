"""The seeded near-tie draw (TODO 8.3.1; A3.1).

Two properties have to hold at once and they pull against each other, which is
why they get a file rather than a line: the choice must **vary across seeds**,
or it is a signature an opponent learns for free, and it must be **fixed within
a seed**, or the log stops being replayable. A test for either one alone would
pass on an implementation that fails the project.
"""

from __future__ import annotations

from core.domain.actions import Direction
from core.domain.tiebreak import DEFAULT_EPSILON, Tiebreaker

# Four actions inside a tenth of a point of each other, and one that is not.
NEAR_TIE = [
    (10.0, Direction.STAY),
    (9.95, Direction.N),
    (9.92, Direction.S),
    (2.0, Direction.E),
]


def draws(seed: int, rounds: int = 40) -> list[Direction]:
    """Take *rounds* draws from one seeded chooser."""
    chooser = Tiebreaker(seed=seed, epsilon=DEFAULT_EPSILON)
    return [chooser.choose(NEAR_TIE) for _ in range(rounds)]


# --- A3.1: unreadable ------------------------------------------------------


def test_a_near_tie_does_not_always_pick_the_same_action() -> None:
    """The whole point. A deterministic tie-break is a signature: an opponent
    who noticed would know our move on every balanced turn without modelling
    anything at all."""
    assert len(set(draws(20260812))) > 1


def test_two_seeds_disagree() -> None:
    """T12. If every seed produced the same sequence the generator would be
    decoration, and 'seeded' would be a claim rather than a mechanism."""
    assert draws(1) != draws(2)


# --- §6: replayable --------------------------------------------------------


def test_the_same_seed_replays_exactly() -> None:
    """T15. Randomness that cannot be replayed would break the property the
    whole project rests on — two peers re-reading one log must agree."""
    assert draws(20260812) == draws(20260812)


def test_a_restart_is_reproducible_from_the_seed_alone() -> None:
    """Each sub-game replays **on its own**. A single stream carried across six
    games would make game 4 reproducible only by replaying 1 to 3 first, and the
    artefact we publish is one log per sub-game."""
    first, second = Tiebreaker(seed=7), Tiebreaker(seed=7)
    [first.choose(NEAR_TIE) for _ in range(5)]
    first.restart(3)
    second.restart(3)
    assert [first.choose(NEAR_TIE) for _ in range(6)] == [
        second.choose(NEAR_TIE) for _ in range(6)
    ]


# --- the ε threshold -------------------------------------------------------


def test_a_clear_winner_is_never_gambled_away() -> None:
    """Unexploitability is the floor, not a licence to throw away advantage."""
    clear = [(10.0, Direction.STAY), (1.0, Direction.N), (0.5, Direction.S)]
    chooser = Tiebreaker(seed=3, epsilon=DEFAULT_EPSILON)
    assert {chooser.choose(clear) for _ in range(30)} == {Direction.STAY}


def test_only_candidates_within_epsilon_are_eligible() -> None:
    """The 2.0 option is eight points behind and must never be drawn."""
    assert Direction.E not in set(draws(20260812, rounds=60))


def test_zero_epsilon_restores_the_fixed_ordering() -> None:
    """The ablation arm has to be **exact**, not merely similar: 8.3.6 compares
    the draw against a control, and a control that still wobbled would be
    measuring the difference between two randomisers."""
    chooser = Tiebreaker(seed=99, epsilon=0.0)
    assert {chooser.choose(NEAR_TIE) for _ in range(30)} == {Direction.STAY}
    assert chooser.draws == 0


def test_an_exact_tie_at_zero_epsilon_takes_the_first_in_search_order() -> None:
    """`options` puts STAY first and then N, S, E, W, and two peers replaying
    one log have to land on the same one."""
    tied = [(5.0, Direction.STAY), (5.0, Direction.N)]
    assert Tiebreaker(seed=1, epsilon=0.0).choose(tied) is Direction.STAY


# --- reporting -------------------------------------------------------------


def test_it_counts_the_draws_it_actually_took() -> None:
    """'The randomiser is on' and 'the randomiser ever fired' are different
    claims, and only the second one is evidence."""
    chooser = Tiebreaker(seed=5, epsilon=DEFAULT_EPSILON)
    clear = [(10.0, Direction.STAY), (0.0, Direction.N)]
    chooser.choose(clear)
    assert chooser.draws == 0
    chooser.choose(NEAR_TIE)
    assert chooser.draws == 1


def test_a_restart_clears_the_draw_count() -> None:
    """It is a per-sub-game statistic; carrying it would report game 3's draws
    against game 4's log."""
    chooser = Tiebreaker(seed=5, epsilon=DEFAULT_EPSILON)
    chooser.choose(NEAR_TIE)
    chooser.restart(1)
    assert chooser.draws == 0


def test_a_single_candidate_is_returned_without_a_draw() -> None:
    """A boxed-in agent still has exactly one legal action, and spending a draw
    on it would shift the stream for every turn after it."""
    chooser = Tiebreaker(seed=5, epsilon=DEFAULT_EPSILON)
    assert chooser.choose([(1.0, Direction.STAY)]) is Direction.STAY
    assert chooser.draws == 0
