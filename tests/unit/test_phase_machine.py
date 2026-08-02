"""The turn state machine (TODO 6.4.1, 6.5.3, M#4, M#5).

**A hang is worse than a loss.** A peer that stalls waiting for a message that
never arrives takes the opponent down with it, and the match ends with no result
for either side — the one outcome nobody can appeal.

So the property under test is not "the happy path works". It is that **every**
live phase has a legal way to fail, and that terminal really means terminal.
"""

from __future__ import annotations

import itertools

import pytest

from core.runtime.phase_machine import (
    TERMINAL,
    TRANSITIONS,
    IllegalTransitionError,
    Phase,
    PhaseMachine,
)

LIVE = [phase for phase in Phase if phase not in TERMINAL]


def test_the_happy_path_runs_end_to_end() -> None:
    machine = PhaseMachine()
    for target in (
        Phase.COMPUTING_MOVE,
        Phase.COMMITTING,
        Phase.AWAITING_REVEAL,
        Phase.VERIFYING,
        Phase.COMPLETE,
    ):
        machine.to(target)
    assert machine.terminal
    assert not machine.lost
    assert len(machine.history) == 6


def test_a_verified_turn_can_start_the_next_one() -> None:
    """A sub-game is many turns; verifying must loop, not only finish."""
    machine = PhaseMachine(Phase.VERIFYING)
    assert machine.can(Phase.WAITING_FOR_OPPONENT)
    assert machine.can(Phase.COMPLETE)


# --- the property that matters ---------------------------------------------


@pytest.mark.parametrize("phase", LIVE)
def test_every_live_phase_can_fail(phase: Phase) -> None:
    """**M#5. A failure with no legal exit becomes a hang.**

    Any phase can fail — network, model, opponent, or our own code — so every
    one of them needs somewhere legal to go. Parametrised over the enum rather
    than a written list, so adding a phase later without a failure edge breaks
    this test instead of shipping silently.
    """
    assert PhaseMachine(phase).can(Phase.TECHNICAL_LOSS)


@pytest.mark.parametrize("phase", LIVE)
def test_failing_is_always_available_and_records_a_reason(phase: Phase) -> None:
    machine = PhaseMachine(phase)
    machine.fail("watchdog expired")
    assert machine.lost
    assert machine.reason == "watchdog expired"


@pytest.mark.parametrize("phase", sorted(TERMINAL, key=lambda p: p.value))
def test_a_terminal_phase_has_no_way_out(phase: Phase) -> None:
    """**A lost sub-game must not quietly resume and start sending moves.**"""
    machine = PhaseMachine(phase)
    assert TRANSITIONS[phase] == frozenset()
    for target in Phase:
        assert not machine.can(target)


def test_failing_twice_does_not_raise() -> None:
    """The watchdog and the deadline tracker can both fire on one stalled turn.

    The second must not raise while the first is being handled, or a clean
    technical loss turns into an unhandled exception in the shutdown path.
    """
    machine = PhaseMachine(Phase.AWAITING_REVEAL)
    machine.fail("deadline expired")
    assert machine.fail("watchdog expired") is Phase.TECHNICAL_LOSS
    assert machine.reason == "deadline expired"


def test_completing_cannot_be_downgraded_to_a_loss() -> None:
    """A recorded result is final; re-opening it would rewrite the score."""
    machine = PhaseMachine(Phase.COMPLETE)
    assert machine.fail("too late") is Phase.COMPLETE
    assert not machine.lost


# --- 6.5.3: every illegal pair asserted to raise ----------------------------


def test_every_illegal_transition_raises() -> None:
    """**The full matrix**, not a sample.

    49 ordered pairs, each either in the table or asserted to raise. A machine
    tested only on the paths someone thought of is a machine with untested
    paths, and the untested one is what fires during a graded match.
    """
    checked = 0
    for origin, target in itertools.product(Phase, Phase):
        machine = PhaseMachine(origin)
        checked += 1
        if target in TRANSITIONS[origin]:
            assert machine.to(target) is target
        else:
            with pytest.raises(IllegalTransitionError):
                machine.to(target)
    assert checked == len(Phase) ** 2


def test_no_phase_can_transition_to_itself() -> None:
    """Self-loops would let a stalled turn "progress" forever without moving."""
    for phase in Phase:
        assert phase not in TRANSITIONS[phase]


def test_the_error_names_both_phases_and_the_legal_options() -> None:
    """"Illegal transition" alone cannot be debugged from a log after a match."""
    with pytest.raises(IllegalTransitionError) as caught:
        PhaseMachine(Phase.WAITING_FOR_OPPONENT).to(Phase.VERIFYING)
    message = str(caught.value)
    assert "waiting_for_opponent" in message
    assert "verifying" in message
    assert "computing_move" in message


def test_phases_serialise_as_plain_strings() -> None:
    """These names go into the log a grader reads, not into a Python repr."""
    assert Phase.COMMITTING == "committing"
    assert f"{Phase.TECHNICAL_LOSS.value}" == "technical_loss"


def test_the_table_covers_every_phase() -> None:
    """A phase missing from the table would raise `KeyError` mid-match."""
    assert set(TRANSITIONS) == set(Phase)


def test_history_records_the_route_not_just_the_destination() -> None:
    """A surprising loss must explain how it got there."""
    machine = PhaseMachine()
    machine.to(Phase.COMPUTING_MOVE)
    machine.fail("model timeout")
    assert machine.history == [
        Phase.WAITING_FOR_OPPONENT,
        Phase.COMPUTING_MOVE,
        Phase.TECHNICAL_LOSS,
    ]
