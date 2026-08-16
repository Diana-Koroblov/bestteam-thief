"""The answering-path drill against a driver that RESTARTS between sub-games.

    uv run python scripts/drill_restart.py

`drill_answering_path.py` holds its door up for the whole plan. A real opponent
does not: imreeyal start a fresh process per sub-game, and their door reads 502
for up to two minutes while the next one binds. That difference is not cosmetic
— it is the difference between a socket our peers can keep and one that dies
underneath them — so this supervisor runs the drill **once per sub-game, each in
its own process**, and leaves a gap between them.

🐛 **What it exists to catch**, live on 16/08. Our waiting loop re-sent our
agreement every 30 s while waiting for the opponent to reach our sub-game, and
every one of those re-sends reused the socket their restart had already killed.
It could never succeed. Our cop survived it — a new sub-game redials at the top
of the series loop — but our **thief** must send the opening turn of every
sub-game it holds, so being late is fatal: sub-games 2, 4 and 6 all timed out
while imreeyal's door was healthy throughout.

**Why a process and not a rebind.** Cancelling the serving task inside one
process leaves the listener bound: uvicorn's `_serve()` has no try/finally
around its main loop, so it never reaches its own shutdown. An in-process
"restart" rebinds onto its own corpse and fails with EADDRINUSE. Only the
process exiting really frees the port and really kills the sessions — which is
exactly what the opponent's runner does, and therefore what has to be modelled.

Run it with both peers already up, exactly as they would be at T::

    uv run python -m core play --role cop   --protocol reference --first cop \\
        --role-split 1-1-1-1-1-1 --port 8081 --opponent http://127.0.0.1:8090/mcp
    uv run python -m core play --role thief --protocol reference --first cop \\
        --role-split 1-1-1-1-1-1 --port 8082 --opponent http://127.0.0.1:8090/mcp

Exit code 0 means every sub-game engaged across a real restart.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.drill_answering_path import PLAN  # noqa: E402

__all__ = ["main"]

DRIVER = Path(__file__).resolve().parent / "drill_answering_path.py"


async def _one(number: int, args: argparse.Namespace) -> str:
    """Run one sub-game in a child process and return its verdict line."""
    child = await asyncio.create_subprocess_exec(
        sys.executable, str(DRIVER),
        "--only", str(number), "--port", str(args.port), "--wait", str(args.wait),
        "--cop-url", args.cop_url, "--thief-url", args.thief_url,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await child.communicate()
    # The driver prints two lines per sub-game: the "-> their X door ..."
    # announcement and the verdict. Only the second one is a result.
    for row in out.decode(errors="replace").splitlines():
        text = row.strip()
        if text.startswith(f"sub-game {number}") and "->" not in text:
            return text.split("  ", 1)[1].strip()
    return "NO VERDICT - the driver process produced no result line"


async def _run(args: argparse.Namespace) -> int:
    """Walk the plan, one process per sub-game, and report."""
    print(f"driver      : {DRIVER.name}, a fresh process per sub-game")
    print(f"their cop   : {args.cop_url}")
    print(f"their thief : {args.thief_url}")
    print(f"gap between : {args.gap:.0f}s with the door completely gone\n")
    verdicts: list[tuple[int, str, str]] = []
    for index, (number, _role, door) in enumerate(PLAN):
        print(f"  sub-game {number}  driver process starting -> their {door} door ...")
        verdict = await _one(number, args)
        print(f"  sub-game {number}  {verdict}\n")
        verdicts.append((number, door, verdict))
        if index != len(PLAN) - 1:
            print(f"  --- driver process gone for {args.gap:.0f}s ---\n")
            await asyncio.sleep(args.gap)

    print("=" * 62)
    for number, door, verdict in verdicts:
        print(f"  sub-game {number}  their {door:5}  {verdict}")
    failed = [item for item in verdicts if not item[2].startswith("engaged")]
    if failed:
        print(f"\nDRILL FAILED - {len(failed)} sub-game(s) never engaged across a restart.")
        print("A peer that only re-sends on the socket it already holds cannot")
        print("recover from the opponent's restart, and the role that opens dies.")
    else:
        print("\nDRILL PASSED - every sub-game engaged across a real driver restart.")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """Return 0 when every sub-game engaged despite the driver restarting."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cop-url", default="http://127.0.0.1:8081/mcp")
    parser.add_argument("--thief-url", default="http://127.0.0.1:8082/mcp")
    parser.add_argument("--port", type=int, default=8090, help="The driver's door.")
    parser.add_argument("--wait", type=float, default=120.0)
    parser.add_argument(
        "--gap", type=float, default=8.0,
        help="Seconds with no door at all between sub-games. imreeyal's rebind "
        "is ~120s; the default is short enough to run often.",
    )
    return asyncio.run(_run(parser.parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
