"""Herd, seal, squeeze — and what moves between them (TODO 8.1.9, 8.1.10).

The rule under test is A1.11: **transitions are driven by measured state, never
by turn number.** So every case here changes something on the board — entropy,
exit count, region size — and asserts the phase followed, and the one test that
does move the clock asserts that the clock can only ever make us *more*
cautious.

The traits themselves moved to `core/domain/opponent_profile.py` in 8.3 and are
tested in `test_opponent_profile.py`. What is left here is what this file was
always about: whether the *phasing* follows the measurement.
"""

from __future__ import annotations

from core.domain.board import Board
from core.domain.brain_base import Observation
from core.domain.opponent_profile import OpponentProfile
from police.phases import Phase, PhaseSettings, classify

BOARD = Board(grid_size=7)
SETTINGS = PhaseSettings()

# Seals the 2x2 corner off from the rest of the board: a 4-cell region.
POCKET = frozenset({(0, 2), (1, 2), (2, 0), (2, 1), (2, 2)})


def observe(belief, barriers=frozenset(), step=5, own=(3, 3)) -> Observation:
    """Build one Cop's view."""
    return Observation(
        board=BOARD, own_position=own, barriers=barriers, step=step,
        barriers_remaining=14, belief=belief,
    )


def profile_of(peaks, cop=(0, 0)) -> OpponentProfile:
    """Feed a trajectory of belief peaks through the profiler."""
    profile = OpponentProfile()
    for peak in peaks:
        profile.observe_peak(peak, cop)
    return profile


FLEEING = [(1, 0), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (6, 1)]
CIRCLING = [(0, 1), (0, 2), (1, 2), (1, 1), (0, 1), (0, 2), (1, 2)]


# --- 8.1.12 no wall while we do not know where they are ---------------------


def test_a_diffuse_belief_holds_us_in_herd() -> None:
    """**A1.15.** A barrier placed where the Thief probably is not can open a
    route *for* it, and unlike a bad move it is permanent. Uniform over 49 cells
    is 5.6 bits against a 3.5 threshold."""
    uniform = dict.fromkeys(BOARD.cells(), 1.0 / 49)
    assert classify(observe(uniform), OpponentProfile(), SETTINGS) is Phase.HERD


def test_no_belief_at_all_holds_us_in_herd() -> None:
    """Turn one, before any scent has been transmitted."""
    assert classify(observe({}), OpponentProfile(), SETTINGS) is Phase.HERD


# --- 8.1.9 the three phases, on measured state ------------------------------


def test_a_thief_on_open_ground_is_herded_not_sealed() -> None:
    """Four exits and the whole board to run in. A wall here removes 1/49 of
    its room and gifts it a free step — a trade that loses (§3.4 Phase A)."""
    assert classify(observe({(3, 3): 1.0}), OpponentProfile(), SETTINGS) is Phase.HERD


def test_an_edge_committed_thief_triggers_sealing() -> None:
    """Exit count is what makes a barrier lethal, and it only falls when the
    Thief is edge-bound. The corner has two exits against the open board's four."""
    assert classify(observe({(0, 0): 1.0}), OpponentProfile(), SETTINGS) is Phase.SEAL


def test_a_small_region_triggers_the_squeeze() -> None:
    """Nothing left to cut — advance and close (§3.4 Phase C)."""
    assert classify(observe({(0, 0): 1.0}, POCKET), OpponentProfile(), SETTINGS) is Phase.SQUEEZE


def test_the_squeeze_threshold_is_the_region_and_not_the_walls() -> None:
    """Barriers on the far side of the board do not shrink *this* region, and a
    phase machine counting walls rather than cells would think they did."""
    distant = frozenset({(6, 6), (6, 5), (5, 6)})
    assert classify(observe({(0, 0): 1.0}, distant), OpponentProfile(), SETTINGS) is Phase.SEAL


# --- 8.1.10 the opponent gate -----------------------------------------------


def test_a_greedy_fleer_earns_a_stricter_sealing_threshold() -> None:
    """**A1.12.** The board's own edges corner a fleer for free, so we decline
    to pay for a wall it was going to walk into anyway. Three exits seals against
    an unclassified thief and does not against a known fleer."""
    edge = observe({(0, 3): 1.0})
    assert classify(edge, OpponentProfile(), SETTINGS) is Phase.SEAL
    assert classify(edge, profile_of(FLEEING), SETTINGS) is Phase.HERD


def test_an_orbiter_gets_barriers_early_wherever_it_stands() -> None:
    """An orbiter never corners itself and the chase never converges, so the
    quota has to come out while there is still a cycle to cut."""
    open_ground = observe({(3, 3): 1.0})
    assert classify(open_ground, OpponentProfile(), SETTINGS) is Phase.HERD
    assert classify(open_ground, profile_of(CIRCLING, cop=(5, 5)), SETTINGS) is Phase.SEAL


# --- the one turn number in the file ----------------------------------------


def test_the_turn_floor_can_only_delay_a_placement() -> None:
    """`barrier_hold_until_turn` ships in both configs while A1.11 forbids
    turn-driven transitions. Reconciled by making it **suppressive only** — it
    holds us in HERD and can never by itself cause a wall (C-015)."""
    settings = PhaseSettings(hold_until_turn=8)
    early = observe({(0, 0): 1.0}, step=3)
    assert classify(early, OpponentProfile(), settings) is Phase.HERD
    assert classify(observe({(0, 0): 1.0}, step=9), OpponentProfile(), settings) is Phase.SEAL


def test_a_measured_orbiter_lifts_the_turn_floor() -> None:
    """A1.12 requires spending barriers *earlier* against an orbiter, so a
    floor that could veto that would put the two requirements in conflict."""
    settings = PhaseSettings(hold_until_turn=8)
    early = observe({(3, 3): 1.0}, step=3)
    assert classify(early, profile_of(CIRCLING, cop=(5, 5)), settings) is Phase.SEAL


def test_the_floor_is_off_by_default_so_measurement_drives_everything() -> None:
    """Nothing is suppressed unless a config asks for it."""
    assert PhaseSettings().hold_until_turn == 0


def test_settings_come_from_config_when_it_offers_them() -> None:
    """Tuning must not need a code change; the defaults must not need a config."""

    class Stub:
        def get(self, path: str, default: object = None) -> object:
            return 5 if path == "strategy.barrier_hold_until_turn" else default

    assert PhaseSettings.from_config(Stub()).hold_until_turn == 5
    assert PhaseSettings.from_config(None) == PhaseSettings()
