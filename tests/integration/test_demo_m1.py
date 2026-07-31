"""The M1 demo must keep running (TODO 1.QG.4).

A demonstration nobody executes rots within a week, and this one is the evidence
for a milestone. Running it here means a change to the domain layer that breaks
the demo fails the suite rather than being discovered when someone tries to show
it working.

This also exercises the whole layer end to end through its real entry points —
config load, board, movement, barriers, rules, scoring — which no unit test does.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_DEMO = Path(__file__).resolve().parents[2] / "scripts" / "demo_m1.py"


def _load_demo():
    """Import scripts/demo_m1.py, which is not on the package path."""
    spec = importlib.util.spec_from_file_location("demo_m1", _DEMO)
    module = importlib.util.module_from_spec(spec)
    sys.modules["demo_m1"] = module
    spec.loader.exec_module(module)
    return module


demo = _load_demo()


def test_the_demo_runs_and_shows_all_three_scenarios(capsys) -> None:
    assert demo.main() == 0
    printed = capsys.readouterr().out
    assert "Legal movement on a 7x7 grid" in printed
    assert "The barrier quota is hard" in printed
    assert "Coordinate overlap triggers capture" in printed
    assert "Five targets, and why that makes diagonals cheap" in printed
    assert "M1 observed" in printed


def test_the_demo_shows_the_cheap_diagonal_and_the_self_trap(capsys) -> None:
    """Diana's observation, verified against the engine.

    Five legal targets per turn means consecutive placements from one cell can
    be diagonal to each other — 1 turn per barrier, against 1.9 for a walked
    row. Taking the fifth target walls the cop in, which is the book's own
    warning made concrete.
    """
    demo.main()
    printed = capsys.readouterr().out.split("4. Five targets")[1]
    assert "4 barriers in 4 turns, no movement" in printed
    assert "cop escape routes: ['STAY', 'W']" in printed
    assert "Taking the 5th target traps the cop: escapes = ['STAY']" in printed


def test_the_demo_shows_the_fifteenth_barrier_refused(capsys) -> None:
    demo.main()
    printed = capsys.readouterr().out
    assert "placement 15 on a free adjacent cell: REJECTED" in printed
    assert "quota is spent" in printed
    assert "barriers on the board: 14 (unchanged)" in printed


def test_the_wall_route_is_legal_play_not_teleportation(capsys) -> None:
    """The Cop must never be drawn standing on a barrier.

    An earlier version placed all 14 barriers by teleporting the Cop to each
    cell. Legal per the letter of the rule — a Cop may wall its own cell — but
    unreachable by real play, and it rendered as `C` sitting inside a wall. A
    demo whose whole job is to make behaviour trustworthy must not show a board
    that no game could produce.
    """
    demo.main()
    quota_section = capsys.readouterr().out.split("2. The barrier quota")[1]
    for line in quota_section.splitlines():
        if "|" in line and "C" in line:
            assert "#" not in line.split("C")[0][-2:], line


def test_the_demo_spends_the_quota_over_real_turns(capsys) -> None:
    """The point of the scenario: a barrier costs a turn, so 14 walls cost 26."""
    demo.main()
    printed = capsys.readouterr().out
    assert "14 placed over 26 turns" in printed
    assert "leaving 9 to chase" in printed
    assert "12 turns of walking between them" in printed


def test_the_demo_names_the_self_trap_rather_than_hiding_it(capsys) -> None:
    """Scenario 2's wall is a losing move, and the demo must say so.

    Rows 0 and 2 fully walled leaves the cop in a 7-cell corridor with the thief
    outside it. Presenting that as a plan would teach the wrong lesson; the
    point is that separation loses.
    """
    demo.main()
    printed = capsys.readouterr().out
    assert "cop can reach 7 cells; thief can reach 28" in printed
    assert "connected: False" in printed
    assert "separation loses" in printed


def test_the_demo_shows_a_capture_and_its_score(capsys) -> None:
    demo.main()
    printed = capsys.readouterr().out
    assert "CAPTURE" in printed
    assert "score (cop, thief): (20, 5)" in printed


def test_the_demo_draws_the_axes_the_way_we_negotiated(capsys) -> None:
    """C-010 made visible: the cop starts at (0,0), drawn top-left.

    A coordinate convention that is self-consistently wrong passes every unit
    test and looks obviously broken on screen. That is the point of the demo.
    """
    demo.main()
    printed = capsys.readouterr().out
    first_board = printed.split("step  0")[1].splitlines()
    assert first_board[3].startswith(" 0 |C"), first_board[3]


def test_the_demo_uses_the_shipped_config_not_literals(capsys) -> None:
    """It prints the config digest, so what you watched is what was signed."""
    from core.shared.config_manager import load_config
    from tests.paths import PRESENT_ROLES, role_dir

    demo.main()
    printed = capsys.readouterr().out
    assert load_config(role_dir(PRESENT_ROLES[0])).shared_digest()[:16] in printed
