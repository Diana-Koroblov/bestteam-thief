"""Unit tests for GameState (PRD 1 §4).

Immutability is the whole point: a search that mutated the position it was
evaluating would corrupt the board it is reasoning about, and a state that
cannot be hashed cannot be committed to.
"""

from __future__ import annotations

import dataclasses

import pytest

from core.crypto.canonical import digest
from core.domain.game_state import GameState

START = GameState(cop=(0, 0), thief=(3, 3))


def test_defaults_describe_a_fresh_sub_game() -> None:
    assert START.barriers == frozenset()
    assert START.step == 0
    assert START.barriers_placed == 0
    assert START.sub_game == 1


def test_the_state_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        START.cop = (1, 1)  # type: ignore[misc]


def test_the_state_is_hashable() -> None:
    """Commit-reveal hashes the state a move was made against (Ch. 5.3.1)."""
    assert {START, GameState(cop=(0, 0), thief=(3, 3))} == {START}


def test_equal_states_produce_equal_digests() -> None:
    """Two peers must serialise the same position to the same bytes."""
    left = GameState(cop=(1, 2), thief=(3, 4), barriers=frozenset({(0, 0)}), step=7)
    right = GameState(cop=(1, 2), thief=(3, 4), barriers=frozenset({(0, 0)}), step=7)
    payload = lambda s: {  # noqa: E731 - a test-local shorthand
        "cop": list(s.cop),
        "thief": list(s.thief),
        "barriers": sorted(list(b) for b in s.barriers),
        "step": s.step,
    }
    assert digest(payload(left)) == digest(payload(right))


def test_agents_share_a_cell() -> None:
    assert not START.agents_share_a_cell
    assert GameState(cop=(3, 3), thief=(3, 3)).agents_share_a_cell


def test_advancing_returns_a_new_state_and_leaves_the_old_one_alone() -> None:
    moved = START.advanced(cop=(0, 1))
    assert moved.cop == (0, 1)
    assert moved.step == 1
    assert START.cop == (0, 0)
    assert START.step == 0


def test_advancing_always_increments_the_step() -> None:
    """A turn that forgets to count is a step the Thief survived for free."""
    state = START
    for expected in range(1, 6):
        state = state.advanced()
        assert state.step == expected


def test_advancing_can_set_the_step_explicitly_and_still_increments() -> None:
    assert START.advanced(step=10).step == 11


def test_placing_a_barrier_blocks_the_cell_and_spends_quota() -> None:
    blocked = START.with_barrier((1, 1))
    assert blocked.barriers == frozenset({(1, 1)})
    assert blocked.barriers_placed == 1
    assert START.barriers == frozenset()


def test_placing_a_barrier_does_not_advance_the_step() -> None:
    """Whether placement ends the turn is the turn loop's business, not the state's."""
    assert START.with_barrier((1, 1)).step == 0


def test_barriers_accumulate() -> None:
    state = START.with_barrier((1, 1)).with_barrier((2, 2)).with_barrier((3, 4))
    assert state.barriers == frozenset({(1, 1), (2, 2), (3, 4)})
    assert state.barriers_placed == 3


def test_barriers_placed_is_tracked_separately_from_the_barrier_set() -> None:
    """Derived would be silently wrong if a rule ever blocks without spending quota."""
    assert "barriers_placed" in {f.name for f in dataclasses.fields(GameState)}
