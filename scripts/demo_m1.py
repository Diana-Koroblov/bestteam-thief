"""Milestone M1, observable (TODO 1.QG.4).

    uv run python scripts/demo_m1.py

Plays three scripted scenarios against the real engine — no mocks, no test
doubles, the same `core.domain` modules a match will use — and prints the board
after every turn:

    1. both agents moving legally on a 7x7 grid;
    2. the barrier quota running out, and the 15th placement being refused;
    3. the Cop stepping onto the Thief, and the capture firing.

The DoD for M1 is *"behaviour seen, not merely coded"*. The unit suite already
asserts all of this; the point here is that a human can watch it happen, which
is a different kind of evidence and catches a different kind of mistake — a
coordinate convention that is self-consistently wrong passes every test and
looks obviously broken on screen.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.domain.actions import Direction  # noqa: E402
from core.domain.barriers import BarrierManager  # noqa: E402
from core.domain.board import Board  # noqa: E402
from core.domain.game_state import GameState  # noqa: E402
from core.domain.movement import resolve_move  # noqa: E402
from core.domain.rules import Rules  # noqa: E402
from core.domain.scoring import ScoreTable, score  # noqa: E402
from core.shared.config_manager import load_config  # noqa: E402
from core.ui.render import legend, render  # noqa: E402

__all__ = ["main"]


def _banner(text: str) -> None:
    print(f"\n{'=' * 62}\n {text}\n{'=' * 62}")


def _show(state: GameState, board: Board, note: str) -> None:
    print(f"\nstep {state.step:2d}  {note}")
    print(render(board, state.cop, state.thief, state.barriers))


def _scenario_movement(board: Board, rules: Rules) -> None:
    """Both agents take legal orthogonal steps; nothing terminal happens."""
    _banner("1. Legal movement on a 7x7 grid")
    state = GameState(cop=(0, 0), thief=(3, 3))
    _show(state, board, "start: cop in the corner, thief in the centre")

    script = [(Direction.S, Direction.E), (Direction.S, Direction.S), (Direction.E, Direction.STAY)]
    for cop_move, thief_move in script:
        state = state.advanced(
            cop=resolve_move(state.cop, cop_move, state.barriers, board),
            thief=resolve_move(state.thief, thief_move, state.barriers, board),
        )
        _show(state, board, f"cop {cop_move.value}, thief {thief_move.value}")
        print(f"   verdict: {rules.verdict(state) or 'game continues'}")


def _scenario_quota(board: Board, quota: int) -> None:
    """Spend the whole barrier quota, then watch the next placement bounce."""
    _banner(f"2. The barrier quota is hard ({quota} allowed)")
    manager = BarrierManager(max_barriers=quota, board=board)
    for index in range(quota):
        cell = (index // board.grid_size, index % board.grid_size)
        manager.place(cell, cell)
    state = GameState(cop=(1, 6), thief=(5, 5), barriers=manager.barriers)
    _show(state, board, f"{manager.placed_count} placed, {manager.remaining} remaining")

    refused = manager.place((2, 6), (1, 6))
    print(f"\n   placement {quota + 1}: {refused.outcome.value} - {refused.reason.value}")
    print(f"   barriers on the board: {manager.placed_count} (unchanged)")


def _scenario_capture(board: Board, rules: Rules, table: ScoreTable) -> None:
    """The Cop steps onto the Thief and the capture fires."""
    _banner("3. Coordinate overlap triggers capture")
    state = GameState(cop=(3, 2), thief=(3, 3), step=11)
    _show(state, board, "cop is one step west of the thief")

    after = state.advanced(cop=resolve_move(state.cop, Direction.E, state.barriers, board))
    _show(after, board, "cop moves E onto the thief")

    outcome = rules.turn_verdict(state, after)
    print(f"\n   verdict: {outcome.verdict.value} - {outcome.reason}")
    print(f"   score (cop, thief): {score(outcome, table)}")


def main() -> int:
    """Run all three scenarios against the real engine."""
    config = load_config(ROOT / "config" / _role())
    board = Board(
        grid_size=config.require("board_and_agents.grid_size"),
        origin_index=config.require("board_and_agents.axis_start_index"),
    )
    rules = Rules.from_config(config, board)

    print(f"config: {config.shared_digest()[:16]}...  {legend()}")
    _scenario_movement(board, rules)
    _scenario_quota(board, config.require("movement_and_barriers.max_barriers"))
    _scenario_capture(board, rules, ScoreTable.from_config(config))
    _banner("M1 observed")
    return 0


def _role() -> str:
    """Return whichever role directory this repository actually ships."""
    for role in ("police", "thief"):
        if (ROOT / "config" / role / "game.json").is_file():
            return role
    raise SystemExit("no config/<role>/game.json found in this repository")


if __name__ == "__main__":
    raise SystemExit(main())
