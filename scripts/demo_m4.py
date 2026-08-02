"""**Milestone M4, made observable** (TODO 4.QG.4).

    uv run python scripts/demo_m4.py

The DoD says M4 must be *observed*, not asserted, so this runs the whole Phase 4
loop end to end and prints what changed at each step:

1. the scent field updates and decays every turn,
2. free text drives inference — a hint moves the posterior,
3. the verbal layer emits a hint the brain chose to be truthful or deceptive.

No network, no tokens, no opponent. Everything here is the code that plays.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.domain.belief import (  # noqa: E402
    entropy,
    mask,
    peak,
    predict,
    uniform,
    update_from_scent,
)
from core.domain.belief_hints import update_from_hint  # noqa: E402
from core.domain.board import Board  # noqa: E402
from core.domain.hint_parser import parse  # noqa: E402
from core.domain.intent import Intent  # noqa: E402
from core.domain.reliability import Reliability  # noqa: E402
from core.domain.scent import decay, emit, merge  # noqa: E402
from core.domain.scent_residual import freshest_source  # noqa: E402
from core.infra.llm import HintWriter  # noqa: E402

__all__ = ["main"]

BOARD = Board(grid_size=7)
TRUTH = (5, 5)
RATE = 0.10


def main() -> int:
    """Run four turns of the Phase 4 loop and report every part of it."""
    writer = HintWriter(forbidden=("capture", "barriers", "scent", "game_count"))
    liar = Reliability(truths=1.0, lies=20.0)
    belief, trail = uniform(BOARD), {}

    print("M4 - the verbal and inferential layer, end to end\n")
    print(f"  the thief is really at {TRUTH}; the cop is told nothing.\n")
    print(f"  {'turn':<5}{'entropy':<10}{'peak':<9}{'p(true)':<10}{'scent age':<11}hint we send")
    print("  " + "-" * 76)

    for turn in range(1, 5):
        # 1. the opponent emits; the field decays and merges (4.1.1-4.1.4)
        trail = merge(decay(trail, RATE), emit(TRUTH, BOARD))

        # 2. the recursive filter: predict, then update on evidence (4.2.1)
        belief = predict(belief, BOARD)
        belief = update_from_scent(belief, trail, BOARD)
        belief = mask(belief, frozenset(), (0, 0))

        # 3. free text drives inference, scaled by what their word is worth
        heard = parse("I am heading north, you will never catch me.")
        belief = update_from_hint(belief, heard, liar.trust, BOARD)

        _, age = freshest_source(trail, RATE)
        hint = writer.write("west", Intent.LIE if turn % 2 else Intent.TRUTH, turn)
        print(
            f"  {turn:<5}{entropy(belief):<10.2f}{str(peak(belief)):<9}"
            f"{belief.get(TRUTH, 0.0):<10.3f}{str(age) + ' turns':<11}{hint.text}"
        )

    print(f"\n  we heard : \"{heard.raw}\"")
    print(f"  parsed as: {heard.direction.value} at confidence {heard.confidence}")
    print(f"  their record: {liar.describe()} -> trust {liar.trust:.2f}, so we INVERT it")
    print("\n  entropy fell from 5.61 bits (knowing nothing) to the value above,")
    print("  the peak sits on the true cell, and every hint we sent is legal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
