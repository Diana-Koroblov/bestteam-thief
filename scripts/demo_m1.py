"""Milestone M1, observable (TODO 1.QG.4).

    uv run python scripts/demo_m1.py

Plays three scripted scenarios against the real engine — no mocks, no test
doubles, the same `core.domain` modules a match will use — and prints the board
after every turn:

    1. both agents moving legally on a 7x7 grid;
    2. the barrier quota running out - and a wall that seals the cop away;
    3. the Cop stepping onto the Thief, and the capture firing;
    4. the five legal barrier targets, and the cheap diagonal cut they allow.

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
from core.domain.connectivity import are_connected, region_size  # noqa: E402
from core.domain.game_state import GameState  # noqa: E402
from core.domain.movement import get_legal_moves, resolve_move  # noqa: E402
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


def _wall_route(board: Board) -> list[tuple[str, tuple[int, int]]]:
    """Return a legal turn-by-turn plan for walling the rows above and below row 1.

    The Cop patrols row 1. On a placement turn it walls the cell directly north
    or south of itself — a legal orthogonal neighbour — and on a movement turn it
    steps one cell east or west. It never stands on a barrier and never
    teleports: every entry here is something one real turn could do.
    """
    span = list(range(board.grid_size))
    plan: list[tuple[str, tuple[int, int]]] = []
    for row, columns in ((0, span), (2, span[::-1])):
        for index, col in enumerate(columns):
            if index:
                plan.append(("move", (1, col)))
            plan.append(("place", (row, col)))
    return plan


def _scenario_quota(board: Board, quota: int, max_moves: int) -> None:
    """Spend the whole barrier quota by legal play, then watch the next one bounce."""
    _banner(f"2. The barrier quota is hard ({quota} allowed)")
    manager = BarrierManager(max_barriers=quota, board=board)
    state = GameState(cop=(1, 0), thief=(5, 5))
    _show(state, board, "cop starts on row 1 and will wall the rows above and below")

    turns = 0
    for action, cell in _wall_route(board):
        if manager.remaining == 0:
            break
        turns += 1
        if action == "move":
            state = state.advanced(cop=cell)
            continue
        # A placement costs the Cop its move for the turn (Ch. 3.4).
        if manager.place(cell, state.cop, thief_pos=state.thief).succeeded:
            state = state.advanced(barriers=manager.barriers)

    placed = manager.placed_count
    _show(state, board, f"{placed} placed over {turns} turns")
    print("\n   Ch. 3.4: a barrier is placed only on a turn the cop forgoes movement,")
    print(f"   and only on its own cell or an orthogonal neighbour. So {placed} walls cost")
    print(f"   {placed} turns minimum, plus {turns - placed} turns of walking between them")
    print(f"   for this shape = {turns} of {max_moves}, leaving {max_moves - turns} to chase.")

    walls = manager.barriers
    cop_room = region_size(state.cop, walls, board)
    thief_room = region_size(state.thief, walls, board)
    print("\n   *** BUT LOOK AT WHAT THIS WALL DID. ***")
    print(f"   cop can reach {cop_room} cells; thief can reach {thief_room}.")
    print(f"   connected: {are_connected(state.cop, state.thief, walls, board)}")
    print(f"   The cop sealed ITSELF into a {cop_room}-cell corridor. It can never")
    print("   reach the thief again, so the thief waits out the clock and wins on")
    print("   survival. Barriers are permanent, so nothing recovers this.")
    print("   This is the book's warning made concrete: 'without accidentally")
    print("   blocking its own access routes'. The real lesson is not that walls")
    print("   cost turns - it is")
    print("   that separation loses. Every placement must first ask: can I still")
    print("   reach the thief afterwards? See core/domain/connectivity.py.")

    # An empty cell next to the Cop, so the refusal can only be about the quota.
    refused = manager.place((state.cop[0], state.cop[1] + 1), state.cop)
    print(f"\n   placement {quota + 1} on a free adjacent cell: {refused.outcome.value}")
    print(f"   reason: {refused.reason.value}")
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


def _scenario_diagonal(board: Board) -> None:
    """Five legal targets per turn, so a diagonal cut needs no walking at all."""
    _banner("4. Five targets, and why that makes diagonals cheap")
    cop = (3, 3)
    manager = BarrierManager(max_barriers=14, board=board)

    print("\n   Ch. 3.4 allows the cop's own cell OR any of the 4 orthogonal")
    print("   neighbours - five targets, all reachable without moving.")
    print("   So consecutive placements from one spot can be DIAGONAL to each")
    print("   other, at 1 turn per barrier instead of the 1.9 of scenario 2.")

    for cell in ((3, 3), (2, 3), (3, 4), (4, 3)):
        manager.place(cell, cop)
    state = GameState(cop=cop, thief=(5, 5), barriers=manager.barriers, step=4)
    _show(state, board, f"{manager.placed_count} barriers in {manager.placed_count} turns, no movement")

    escapes = [d.value for d, _ in get_legal_moves(cop, manager.barriers, board)]
    print("\n   (2,3)-(3,4) and (3,4)-(4,3) touch only at corners: a diagonal chain,")
    print("   which is the minimum vertex cut on a 4-connected grid.")
    print(f"   cop escape routes: {escapes} - one exit deliberately left open.")

    trapped = BarrierManager(max_barriers=14, board=board)
    for cell in ((3, 3), (2, 3), (3, 4), (4, 3), (3, 2)):
        trapped.place(cell, cop)
    print(f"\n   Taking the 5th target traps the cop: escapes = "
          f"{[d.value for d, _ in get_legal_moves(cop, trapped.barriers, board)]}")
    print("   That is the book's warning - 'without accidentally blocking its own")
    print("   access routes' (Ch. 3.4).")


def main() -> int:
    """Run all four scenarios against the real engine."""
    config = load_config(ROOT / "config" / _role())
    board = Board(
        grid_size=config.require("board_and_agents.grid_size"),
        origin_index=config.require("board_and_agents.axis_start_index"),
    )
    rules = Rules.from_config(config, board)

    print(f"config: {config.shared_digest()[:16]}...  {legend()}")
    _scenario_movement(board, rules)
    _scenario_quota(
        board,
        config.require("movement_and_barriers.max_barriers"),
        config.require("movement_and_barriers.max_moves"),
    )
    _scenario_capture(board, rules, ScoreTable.from_config(config))
    _scenario_diagonal(board)
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
