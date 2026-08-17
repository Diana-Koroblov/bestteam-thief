"""The 1 -> 2 -> 3 answering-path drill (imreeyal, 16/08).

    uv run python scripts/drill_answering_path.py

Stands in for an opponent's runner and plays **consecutive** sub-games against
our two standing processes, alternating roles the way a peer with one process
does::

    sub-game 1   driver plays thief   ->  our COP door    (:8081)
    sub-game 2   driver plays cop     ->  our THIEF door  (:8082)
    sub-game 3   driver plays thief   ->  our COP door    (:8081)

**Why this shape and not the unit tests.** `tests/unit/test_turn_wait.py`
exercises the waiting, and the waiting works. It cannot see the *advance
trigger*, which only fires when a real neighbouring sub-game settles: the
question is whether our thief is **still holding sub-game 2** after sub-game 1
has completed elsewhere. Two match windows were lost to that on 15/08 and no
test could have caught it, because both halves of the failure live in different
processes. Our own earlier two-process drill missed it too — it ran both sides
on ``[1,3,5]``, so they advanced together and never left one process waiting
while the other played.

Run it with both peers already up, exactly as they would be at T::

    uv run python -m core play --role cop   --protocol reference --first cop \\
        --role-split 1-1-1-1-1-1 --opponent http://127.0.0.1:8090/mcp --allow-local-head
    uv run python -m core play --role thief --protocol reference --first cop \\
        --role-split 1-1-1-1-1-1 --opponent http://127.0.0.1:8090/mcp --allow-local-head

`--allow-local-head` because this tree has no remote: against ourselves the
declared hash is nobody's evidence, and against a real opponent it is refused.

Exit code 0 means every sub-game engaged. Non-zero names the one that did not.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.compat.mailbox import Inboxes, build_reference_tools  # noqa: E402
from core.compat.session import ReferenceSession  # noqa: E402
from core.compat.turn_wait import (  # noqa: E402
    AgreementTimeoutError,
    collect_our_agreement,
    push_agreement,
)
from core.protocol.schemas import Role  # noqa: E402
from core.sdk.peer_sdk import PeerSDK  # noqa: E402

__all__ = ["main", "PLAN"]

# (sub-game, role the DRIVER plays, which of our doors it belongs to).
# The driver takes the opposite role to ours, so sub-game 1 is our cop's.
PLAN: tuple[tuple[int, Role, str], ...] = (
    (1, Role.THIEF, "cop"),
    (2, Role.COP, "thief"),
    (3, Role.THIEF, "cop"),
)

BIND_SECONDS = 1.0


def _config_dir(role: Role) -> Path:
    """Return the config directory the driver borrows for *role*."""
    return ROOT / "config" / ("police" if role is Role.COP else "thief")


async def _one(number: int, role: Role, url: str, inboxes: Inboxes, wait: float) -> str:
    """Play one sub-game as *role* against *url*. Returns a verdict string."""
    sdk = PeerSDK(_config_dir(role), role)
    sdk.runtime.start_sub_game(number)
    inboxes.drain()
    sdk.connect(url, timeout_sec=10.0)
    session = ReferenceSession(
        runtime=sdk.runtime, client=sdk.opponent, inboxes=inboxes,
        identity={"group_id": "drill", "group_name": "drill"}, sub_game_number=number,
    )
    message, _ = session.agreement_message()
    try:
        await push_agreement(sdk.opponent, message, wait)
        await collect_our_agreement(session, wait, message)
    except AgreementTimeoutError:
        return "NO AGREEMENT - nobody on the other side was holding this sub-game"
    except Exception as error:  # noqa: BLE001 - a drill reports, never raises
        return f"HANDSHAKE FAILED - {type(error).__name__}: {error}"
    try:
        result = await session.play_sub_game()
        # Their side audits ours at the end of every sub-game, so a drill that
        # never revealed would leave a truthful `audit FAILED (no audit
        # received)` on their transcript and make clean evidence look dirty.
        with suppress(Exception):
            await sdk.opponent.call(
                "submit_audit", session.audit_payload(), argument="payload"
            )
    except Exception as error:  # noqa: BLE001 - same
        return f"PLAY FAILED - {type(error).__name__}: {error}"
    finally:
        await sdk.opponent.aclose()
    return f"engaged, result {result!r}"


@asynccontextmanager
async def _door(port: int, inboxes: Inboxes) -> Any:
    """Stand the drill's mailbox up, and take it down again on the way out."""
    from core.infra.mcp_server import create_server

    sdk = PeerSDK(_config_dir(Role.COP), Role.COP)
    spec = sdk.server_spec(port, tools=build_reference_tools(inboxes))
    server = create_server(spec)
    serving = asyncio.create_task(
        server.run_async(transport="http", host=spec.host, port=spec.port,
                         uvicorn_config={"access_log": False})
    )
    await asyncio.sleep(BIND_SECONDS)
    try:
        yield
    finally:
        serving.cancel()
        with suppress(asyncio.CancelledError):
            await serving


async def _walk(args: argparse.Namespace, inboxes: Inboxes) -> list[tuple[int, str, str]]:
    """Play the plan, standing the door up once or once per sub-game."""
    doors = {"cop": args.cop_url, "thief": args.thief_url}
    verdicts: list[tuple[int, str, str]] = []

    async def one(number: int, role: Role, door: str) -> None:
        print(f"  sub-game {number}  driver plays {role.value:5} -> their {door} door ...")
        verdict = await _one(number, role, doors[door], inboxes, float(args.wait))
        print(f"  sub-game {number}  {verdict}\n")
        verdicts.append((number, door, verdict))

    plan = [entry for entry in PLAN if args.only in (None, entry[0])]
    async with _door(args.port, inboxes):
        for number, role, door in plan:
            await one(number, role, door)
    return verdicts




async def _run(args: argparse.Namespace) -> int:
    """Serve our mailbox, walk the plan, and report."""
    inboxes = Inboxes()
    # Silenced before the first bind rather than in a `finally`: uvicorn's
    # `_serve()` has no try/finally around its main loop, so cancelling it never
    # reaches uvicorn's own shutdown and asyncio force-cancels the ASGI lifespan
    # task and any open SSE stream instead — logged at ERROR with a full
    # traceback on every clean exit. With --restart that repeats once per
    # sub-game, and this output is pasted to an opponent as evidence.
    logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)
    if args.only is None:
        print(f"drill door      : http://127.0.0.1:{args.port}/mcp")
        print(f"their cop       : {args.cop_url}")
        print(f"their thief     : {args.thief_url}\n")
    verdicts = await _walk(args, inboxes)
    if args.only is not None:
        # A child of `drill_restart.py`: it parses our one verdict line out of
        # stdout and prints the summary itself.
        return 1 if any(not v.startswith("engaged") for _n, _d, v in verdicts) else 0

    print("=" * 62)
    failed = [(n, d, v) for n, d, v in verdicts if not v.startswith("engaged")]
    for number, door, verdict in verdicts:
        print(f"  sub-game {number}  their {door:5}  {verdict}")
    if failed:
        print(f"\nDRILL FAILED - {len(failed)} sub-game(s) never engaged.")
        print("A sub-game their side does not hold means its plan pointer moved on")
        print("without that entry ever being played (C-011).")
    else:
        print("\nDRILL PASSED - every sub-game engaged, in order, across the boundary.")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """Return 0 when every sub-game in the plan engaged."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cop-url", default="http://127.0.0.1:8081/mcp")
    parser.add_argument("--thief-url", default="http://127.0.0.1:8082/mcp")
    parser.add_argument("--port", type=int, default=8090, help="The drill's own door.")
    parser.add_argument("--wait", type=float, default=120.0)
    parser.add_argument(
        "--only", type=int, default=None,
        help="Play just this one sub-game and exit. This is how "
        "scripts/drill_restart.py gives each sub-game its own process; run that "
        "instead of passing this by hand.",
    )
    return asyncio.run(_run(parser.parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
