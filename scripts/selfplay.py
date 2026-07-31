"""Run self-play batches and print the A/B table (TODO 3.5.1-3.5.4).

    uv run python scripts/selfplay.py --games 100
    uv run python scripts/selfplay.py --games 1 --show

No network, no LLM, no tokens — so this can run on every change, which is the
only way an A/B habit survives contact with a deadline.

**Read the separation counter first.** It reports how often the Cop could not
reach the Thief at all. Anything above 0 means the Cop walled itself off and
lost the sub-game to geometry rather than to the opponent, and no other number
on the table matters until it is 0.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.domain.board import Board  # noqa: E402
from core.domain.game_state import GameState  # noqa: E402
from core.domain.rules import Rules, Verdict  # noqa: E402
from core.domain.scoring import ScoreTable, score  # noqa: E402
from core.runtime.brain_loader import load_brain  # noqa: E402
from core.runtime.selfplay import SubGameResult, play_sub_game  # noqa: E402
from core.shared.config_manager import load_config  # noqa: E402
from core.ui.render import legend, render  # noqa: E402

__all__ = ["main", "run_batch", "report"]


def run_batch(games: int, cop_spec: str = "", thief_spec: str = "") -> list[SubGameResult]:
    """Play *games* sub-games from the negotiated opening and return the results."""
    config = load_config(ROOT / "config" / _role())
    board = Board(
        grid_size=config.require("board_and_agents.grid_size"),
        origin_index=config.require("board_and_agents.axis_start_index"),
    )
    rules = Rules.from_config(config, board)
    start = GameState(
        cop=tuple(config.require("board_and_agents.cop_start")),
        thief=tuple(config.require("board_and_agents.thief_start")),
    )
    quota = config.require("movement_and_barriers.max_barriers")

    # Brains are rebuilt per game so no state leaks between sub-games — a brain
    # that remembered the last game would make the batch measure one long game.
    return [
        play_sub_game(
            load_brain(cop_spec, "cop"), load_brain(thief_spec, "thief"), rules, quota, start
        )
        for _ in range(games)
    ]


def report(results: list[SubGameResult]) -> dict[str, float]:
    """Return the summary numbers, and print them as a table."""
    table = ScoreTable.from_config(load_config(ROOT / "config" / _role()))
    captures = sum(1 for r in results if r.outcome.verdict is Verdict.CAPTURE)
    separations = sum(r.cop_separations for r in results)
    barriers = sum(r.barriers_placed for r in results)
    points = [score(r.outcome, table) for r in results]

    summary = {
        "games": len(results),
        "cop_win_rate": captures / len(results),
        "mean_steps": sum(r.steps for r in results) / len(results),
        "barriers_spent": barriers,
        "captures_per_barrier": captures / barriers if barriers else 0.0,
        "cop_separations": separations,
        "cop_points": sum(p[0] for p in points),
        "thief_points": sum(p[1] for p in points),
    }

    print(f"\n{'metric':<24} value")
    print("-" * 40)
    for key, value in summary.items():
        shown = f"{value:.3f}" if isinstance(value, float) else str(value)
        print(f"{key:<24} {shown}")

    print("\nwhich rule ended each game:")
    for verdict in sorted({r.outcome.verdict.value for r in results}):
        count = sum(1 for r in results if r.outcome.verdict.value == verdict)
        print(f"  {verdict:<16} {count}")

    if separations:
        print(
            f"\n*** {separations} turn(s) with the cop unable to reach the thief. "
            "\n    The cop walled itself off; nothing else on this table matters "
            "until that is 0. ***"
        )
    return summary


def _show_game(result: SubGameResult, board: Board) -> None:
    """Print every turn of one game. Free, and better than the GUI for debugging."""
    print(legend())
    for step, state in enumerate(result.history):
        print(f"\nstep {step}")
        print(render(board, state.cop, state.thief, state.barriers))
        if step < len(result.reasons):
            cop_why, thief_why = result.reasons[step]
            print(f"   cop  : {cop_why}\n   thief: {thief_why}")
    print(f"\n{result.outcome.verdict.value}: {result.outcome.reason}")


def _role() -> str:
    """Return whichever role directory this repository ships."""
    for role in ("police", "thief"):
        if (ROOT / "config" / role / "game.json").is_file():
            return role
    raise SystemExit("no config/<role>/game.json in this repository")


def main(argv: list[str] | None = None) -> int:
    """Run a batch and print the report."""
    parser = argparse.ArgumentParser(description="Self-play A/B harness.")
    parser.add_argument("--games", type=int, default=20, help="Sub-games to play.")
    parser.add_argument("--cop", default="", help="Cop strategy, package.module:Class.")
    parser.add_argument("--thief", default="", help="Thief strategy.")
    parser.add_argument("--show", action="store_true", help="Print every turn of game 1.")
    args = parser.parse_args(argv)

    results = run_batch(args.games, args.cop, args.thief)
    if args.show:
        config = load_config(ROOT / "config" / _role())
        _show_game(results[0], Board(grid_size=config.require("board_and_agents.grid_size")))
    report(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
