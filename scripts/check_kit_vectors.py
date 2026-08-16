"""Check our scent physics against the league kit's CORE pheromone fixture.

    uv run python scripts/check_kit_vectors.py --kit path/to/copthief-league-protocol

The kit is public (github.com/Imreec/copthief-league-protocol) and is not
vendored here: it is another team's artefact, it moves, and a stale copy in our
tree would be a vector run that proves nothing. Point this at a fresh clone.

**Why a separate checker rather than the kit's own `verify_vectors.py`.** That
script verifies the kit's reference implementation against its own fixtures.
What we need is the other direction — OUR `core.domain.scent` against those same
fixtures — because the fixture is the agreed statement of the physics and our
port of it is the thing that was wrong (imreeyal, 16/08: 105 of 105 frames
refused).

Exit code 0 means every CORE case matched.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.domain.board import Board  # noqa: E402
from core.domain.scent import decay, emit  # noqa: E402

__all__ = ["main"]

# The kit's `decay` fixture keeps a faded cell as an explicit 0.0; ours drops
# the key. Same physics, different representation of "nothing here" — and the
# kit's own description settles which one reaches an opponent: *"Only value>0
# crosses the wire"*. So the comparison is over positive cells.
POSITIVE_ONLY = True


def _grid(field: dict) -> dict[str, float]:
    """Our field as the fixture writes one: ``{"r,c": value}``, positives only."""
    return {
        f"{row},{col}": round(value, 3)
        for (row, col), value in sorted(field.items())
        if not POSITIVE_ONLY or value > 0.0
    }


def _expected(field: dict) -> dict[str, float]:
    """The fixture's field, reduced to the same positives-only comparison."""
    return {key: value for key, value in field.items() if not POSITIVE_ONLY or value > 0.0}


def _check_emit(case: dict) -> tuple[bool, str]:
    """One `emit` fixture: our subtractive kernel against the pinned field."""
    centre = tuple(case["center"])
    board = Board(grid_size=int(case["board_size"]))
    ours = _grid(emit(centre, board, "subtractive"))
    theirs = _expected(case["field"])
    if ours == theirs:
        return True, f"emit centre={list(centre)} board={case['board_size']}  {len(ours)} cells"
    differing = sorted(set(ours) | set(theirs), key=lambda k: (ours.get(k), theirs.get(k)))
    detail = ", ".join(
        f"{key}: ours={ours.get(key)} theirs={theirs.get(key)}"
        for key in differing
        if ours.get(key) != theirs.get(key)
    )
    return False, f"emit centre={list(centre)}  MISMATCH  {detail}"


def _check_decay(case: dict) -> tuple[bool, str]:
    """One `decay` fixture: one subtractive step at the pinned rate."""
    before = {
        tuple(int(part) for part in key.split(",")): value
        for key, value in case["before"].items()
    }
    ours = _grid(decay(before, float(case["decay"]), "subtractive"))
    theirs = _expected(case["after"])
    ok = ours == theirs
    return ok, f"decay rate={case['decay']}  {'ok' if ok else f'MISMATCH ours={ours} theirs={theirs}'}"


def main(argv: list[str] | None = None) -> int:
    """Return 0 when every CORE pheromone case matches."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kit", required=True, type=Path, help="A clone of the kit.")
    args = parser.parse_args(argv)

    fixture = json.loads((args.kit / "vectors" / "pheromone.json").read_text(encoding="utf-8"))
    print(f"fixture : vectors/pheromone.json   status={fixture.get('status')}")
    print(f"kit     : {args.kit}\n")

    results = [_check_emit(case) for case in fixture.get("emit", [])]
    results += [_check_decay(case) for case in fixture.get("decay", [])]
    for ok, line in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {line}")

    failed = [line for ok, line in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} CORE pheromone cases pass.")
    if failed:
        print("FAILED - our emission does not match the registered subtractive model.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
