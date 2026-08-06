"""The adoption benchmark: 192 sub-games, both roles, seeded (TODO 8.3.6; A4.1, A4.2).

This is the run that decides what ships. A4.1 asks for **≥100 sub-games across
both roles** and A4.2 says adopt only on ≥70 % against the control, so the whole
2x2 matrix is played over the full mirrored opening set and the gates are
asserted rather than reported.

**Why the opening set and not a repeat count.** Both brains are deterministic
given a seed, so a hundred sub-games from one opening would be one sub-game
reported a hundred times — a batch size that looks like evidence and is not.
Varying the opening produces genuinely different games. Every mirrored pair on a
7x7 board is 49 minus the one where both agents start on the same cell: **48
openings, 192 sub-games.**

🐛 **Why this file exists at all.** `test_advanced_thief_selfplay.py` reported
every 8.2 figure as *n*/48 while running `range(0, 7, 2)` — four values per axis,
sixteen openings. What was missing was that **no committed test performed the run
those numbers came from**, so the eight sub-games between 40/48 and the
tripwire's threshold were unguarded. The discrepancy was invisible because 16 and
48 both read as plausible sample sizes in prose, which is why the sizes are
asserted here rather than described.

The sequel makes the point better than the original did. With this file in place,
the 8.2 numbers reproduced *exactly* — which is precisely why they looked
trustworthy, and they were not: the harness was reading a turn of scent the wire
cannot deliver, so the run was faithfully reproducing a game neither peer can
play (TODO 4.1.6). **A reproducible measurement is not necessarily a valid one.**
Hence the assertions below are comparisons between arms, not fixed counts.

Measured 06/08 at the **shipped configuration** — the real `config/*/game.toml`,
loaded per role — with `survival_threshold = 35` and seed 20260812, and with the
transmitted scent field held back one turn as commit-reveal requires. Thief
survivals, mean steps, and the Cop's walls spent::

                          baseline thief              advanced thief
    baseline cop     21/48 · 19.62 steps ·  0w    42/48 · 32.25 steps ·  0w
    advanced cop      0/48 ·  8.96 steps · 27w    40/48 · 31.50 steps · 47w

**Self-separation is 0 in all four cells**, which is the gate no other number
matters until it passes.

⚠️ **Every figure here moved on 06/08 and none of it was a strategy change.**
The harness had been feeding both filters the opponent's *current-turn* scent
deposit, which no peer can have: a field revealed at turn *k* is first readable
at turn *k+1*, because turn *k*'s own move was sealed before it arrived. The
brains are untouched; they are simply being measured on the game they will play.

What that cost, and what it did not: the **baseline** Cop's capture rate fell
from 48/48 to 27/48, so its old figure was largely borrowed from information it
could not have had. The **advanced** Cop still captures 48/48. Both A4.2 gates
therefore still clear, and the gap between the two Cops is wider than it was.
"""

from __future__ import annotations

import pytest

from core.domain.board import Board
from core.domain.game_state import GameState
from core.domain.rules import Rules, Verdict
from core.runtime.selfplay import play_sub_game
from core.shared.config_manager import load_config
from tests.paths import PRESENT_ROLES, role_dir

pytestmark = [
    pytest.mark.skipif(
        "police" not in PRESENT_ROLES or "thief" not in PRESENT_ROLES,
        reason="a published repository ships one role; self-play needs both (ADR-001)",
    ),
    # Deselected from the default run and re-selected as its own gate, without
    # coverage: 192 sub-games take 2:00 untraced and 12:14 under `--cov`. It is
    # not skipped — `pipeline.GATES` runs it on every commit, because a number
    # nobody re-checks is how the 16-vs-48 discrepancy survived a whole phase.
    pytest.mark.slow,
]

BOARD = Board(grid_size=7)
RULES = Rules(board=BOARD, survival_threshold=35)
QUOTA = 14

# Every mirrored opening on the board, less the centre where the mirror puts
# both agents on one cell — a position the rules have no opening for.
OPENINGS = [
    ((row, col), (6 - row, 6 - col))
    for row in range(7)
    for col in range(7)
    if (row, col) != (3, 3)
]

# A4.1's floor, as arithmetic rather than as a comment.
CELLS = 4
MIN_SUB_GAMES = 100

# A4.2. Below this a change is not adopted, whatever else it improved.
ADOPTION_RATE = 0.7


def configured(brain_class, role: str):
    """Build a brain and apply the **shipped** configuration for its role.

    ⚠️ **The 8.1 and 8.2 suites never did this, and it was luck that it did not
    matter.** They built brains from code defaults, so every config-only setting
    — search depth, evaluation weights, `false_anchor` — was measured at
    whatever the dataclass happened to say rather than at what a graded match
    would load. The two agreed by coincidence until 8.3, when the verbal layer
    shipped **on for the cop and off for the thief** (`bluff_enabled`), a split
    only the config files can express. A benchmark that ignores them measures a
    configuration nobody plays.
    """
    brain = brain_class()
    brain.configure(load_config(role_dir(role)))
    return brain


def play(cop_class, thief_class) -> list:
    """Play every opening once. Brains are rebuilt per game, so the batch
    measures 48 independent sub-games rather than one long series."""
    return [
        play_sub_game(
            configured(cop_class, "police"),
            configured(thief_class, "thief"),
            RULES,
            QUOTA,
            GameState(cop=start, thief=flee),
        )
        for start, flee in OPENINGS
    ]


def survivals(games: list) -> int:
    """How many sub-games the Thief lasted out."""
    return sum(1 for game in games if game.outcome.verdict is Verdict.SURVIVAL)


@pytest.fixture(scope="module")
def matrix() -> dict:
    """The full 2x2, played once and shared by every assertion below."""
    from police.advanced import AdvancedCop
    from police.brain import PoliceBrain
    from thief.advanced import AdvancedThief
    from thief.brain import ThiefBrain

    return {
        (cop, thief): play(cop_class, thief_class)
        for cop, cop_class in (("baseline", PoliceBrain), ("advanced", AdvancedCop))
        for thief, thief_class in (("baseline", ThiefBrain), ("advanced", AdvancedThief))
    }


# --- A4.1: the sample is the size it claims to be ---------------------------


def test_the_benchmark_plays_at_least_a_hundred_sub_games(matrix: dict) -> None:
    """**The assertion the 16-vs-48 bug should have had.** A sample size stated
    in prose drifted from the one in the code for a whole phase and nothing
    noticed; a sample size stated as a test cannot."""
    assert len(OPENINGS) == 48
    assert sum(len(games) for games in matrix.values()) == len(OPENINGS) * CELLS
    assert len(OPENINGS) * CELLS >= MIN_SUB_GAMES


def test_both_roles_are_measured(matrix: dict) -> None:
    """A4.1 asks for both, and a benchmark covering one role would let the other
    regress silently."""
    assert {cop for cop, _ in matrix} == {"baseline", "advanced"}
    assert {thief for _, thief in matrix} == {"baseline", "advanced"}


# --- 8.QG.4: the gate no other number outranks ------------------------------


def test_the_cop_never_walls_itself_away_from_the_thief(matrix: dict) -> None:
    """**Must be 0, in every cell.** A separation is a sub-game lost to geometry
    rather than to the opponent, and no win rate on this page means anything
    until this is zero (A4.4)."""
    separations = {key: sum(g.cop_separations for g in games) for key, games in matrix.items()}
    assert separations == dict.fromkeys(matrix, 0)


# --- A4.2: the adoption gate, per role --------------------------------------


def test_the_advanced_cop_clears_the_adoption_rate(matrix: dict) -> None:
    """Captures against the baseline Thief. Saturated at 48/48, which is why the
    next test measures the thing that still has room to move."""
    captured = len(OPENINGS) - survivals(matrix[("advanced", "baseline")])
    assert captured >= len(OPENINGS) * ADOPTION_RATE


def test_the_advanced_cop_captures_faster_than_the_baseline_one(matrix: dict) -> None:
    """The metric that has signal once the win rate saturates: both Cops catch
    the baseline Thief every time, and only the clock separates them."""
    advanced = sum(g.steps for g in matrix[("advanced", "baseline")])
    baseline = sum(g.steps for g in matrix[("baseline", "baseline")])
    assert advanced < baseline


def test_the_advanced_thief_clears_the_adoption_rate(matrix: dict) -> None:
    """Survival against the baseline Cop, which is the Thief's half of A4.2."""
    assert survivals(matrix[("baseline", "advanced")]) >= len(OPENINGS) * ADOPTION_RATE


def test_the_competitive_cell_is_reported_and_not_gated(matrix: dict) -> None:
    """**Advanced against advanced is zero-sum, so A4.2 does not apply to it.**
    Every sub-game the Thief survives here is one the Cop did not win, so a 70 %
    floor on one side is a 30 % ceiling on the other — and it would fire on the
    *other* role improving, which is the opposite of what a gate is for. The 8.2
    suite had exactly that test and 8.3 broke it by making the Cop better.

    So the check is that both brains are still playing a real game: neither is
    shut out, and the Thief still beats the baseline it replaced."""
    survived = survivals(matrix[("advanced", "advanced")])
    assert 0 < survived < len(OPENINGS)
    assert survived > survivals(matrix[("advanced", "baseline")])


# --- the floors stay floors -------------------------------------------------


def test_the_baselines_are_unchanged_and_still_a_floor(matrix: dict) -> None:
    """Every claim above is relative to them, and a floor edited to flatter the
    thing measured against it is not a floor.

    ⚠️ **This used to assert the baseline Thief survives nothing, and that was
    an artefact.** It held only while the harness handed the Cop's filter the
    Thief's current-turn scent deposit — evidence commit-reveal cannot deliver.
    With the field held back one turn the baseline Thief survives a fair share
    of openings against the baseline Cop, which is what a floor with headroom
    should look like.

    The floor property was never "the baseline loses every game" anyway. It is
    that **each advanced brain beats its own baseline against a common
    opponent**, which is what makes the A/B above a measurement rather than a
    comparison of two unrelated numbers.
    """
    baseline = survivals(matrix[("baseline", "baseline")])
    assert survivals(matrix[("baseline", "advanced")]) > baseline, "the thief improved"
    assert survivals(matrix[("advanced", "baseline")]) < baseline, "the cop improved"


def test_a_better_cop_is_still_a_harder_cop(matrix: dict) -> None:
    """A cross-check on both brains at once. If the advanced Cop were not harder
    to escape than the baseline, one of the two A/Bs above would be measuring
    something other than what it claims."""
    assert survivals(matrix[("advanced", "advanced")]) <= survivals(
        matrix[("baseline", "advanced")]
    )


# --- TA.3: advanced against advanced completes ------------------------------


def test_every_sub_game_reaches_a_verdict(matrix: dict) -> None:
    """No timeouts, no illegal moves, no game that simply stops. An illegal move
    is resolved as holding position by the harness, so a brain proposing them
    would show up as a game that ran to the step limit doing nothing."""
    for games in matrix.values():
        assert all(game.steps > 0 and game.outcome.reason for game in games)


# --- 8.3.3: a series, not six unrelated games -------------------------------


def series(cop, thief, games: int = 6) -> None:
    """Play *games* sub-games with **one pair of brains**, as a real series does."""
    for index in range(games):
        start, flee = OPENINGS[index]
        play_sub_game(cop, thief, RULES, QUOTA, GameState(cop=start, thief=flee))


def test_traits_accumulate_across_the_six_sub_games_of_a_series() -> None:
    """**8.3.3, end to end.** Every other test here rebuilds the brains per game,
    which is right for measuring a batch and wrong for measuring memory. A series
    reuses one brain, and the profile has to survive the boundary — otherwise the
    six games we get against one opponent are six samples of one game."""
    from police.advanced import AdvancedCop
    from thief.advanced import AdvancedThief

    cop, thief = AdvancedCop(), AdvancedThief()
    series(cop, thief)
    assert cop.verbal.profile.transitions > 35
    assert thief.verbal.profile.transitions > 35
    assert cop.verbal.profile.reliability.checked > 0


def test_a_new_opponent_clears_what_the_series_learned() -> None:
    """A3.5. Teams may change code between matches, so a reputation earned by
    one of them is evidence about nobody else."""
    from police.advanced import AdvancedCop
    from thief.advanced import AdvancedThief

    cop = AdvancedCop()
    series(cop, AdvancedThief(), games=3)
    assert cop.verbal.profile.transitions > 0
    cop.meets("a different team")
    assert cop.verbal.profile.transitions == 0
    assert cop.verbal.profile.reliability.checked == 0


def test_the_trail_and_the_draw_stream_restart_at_every_boundary() -> None:
    """The other half of A3.5's two scopes. A trail carried across a boundary
    would have us fleeing a scored game, and a draw stream that never restarted
    would make sub-game 4 replayable only by replaying 1 to 3 first."""
    from police.advanced import AdvancedCop
    from thief.advanced import AdvancedThief

    thief = AdvancedThief()
    series(AdvancedCop(), thief, games=3)
    assert len(thief.verbal.trail.visits) <= RULES.survival_threshold + 1
