"""Playing a real series against a real opponent (TODO 9.2, 9.4, 9.5).

    python -m core play --role cop --opponent https://them.ngrok-free.dev/mcp \
        --tunnel --out results/ --first cop

Everything under ``core/runtime/`` could already play a series; nothing outside
the test suite could reach it. `MatchDriver` takes a runtime and a client, and
`SeriesRunner` takes a ``build`` callable, exactly so the live deployment could
be assembled somewhere else — this is that somewhere. Until it existed the
project could play a match only against itself.

**One process serves and drives.** Their calls land in *our* `PeerRuntime`, and
that same object is what our driver reads to resolve a turn. Splitting the two
across processes would hand the driver a runtime nobody fills: it would wait out
every deadline against an opponent that had already answered, and lose six
sub-games to a timeout with the messages sitting in the other process. So the
server runs as a background task inside the driver's own event loop.

**Our share of the six, not all six.** A published repository ships one brain
(ADR-001, M#1), so a 3-3 split is two processes in sequence: this one plays the
sub-games the plan assigns to the role it holds, the other repository plays the
rest — into the same directory, under the same `game_id`, which is what makes
six logs from two processes one match rather than two halves nobody can join
up (7.2.5).

**The process that files the sixth sub-game sends the report.** Both of ours
merge into one `result_<game_id>.json` (`core/report/merge.py`), and the one
that completes it mails it without anyone typing a command — because a match
won on the board and never reported scores 0 for both teams (M#35). See
`core/runtime/reporting.py`.

**Nothing is played before the handshake settles.** The negotiation runs first
and a refusal exits non-zero with no move sent. A match played under configs
differing by one byte is a match whose audit reports forgery against two honest
teams, and it scores 0 for both (M#11, M#35).
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Any

from core.cli_handshake import greet
from core.protocol.schemas import Role
from core.report.scoreboard import print_series
from core.runtime.live import reopen
from core.sdk.peer_sdk import PeerSDK

__all__ = ["play", "plan_for"]

# How long to let the server bind before we invite anyone to call it. The
# opponent may answer our handshake by calling straight back, and a refusal
# because our port was not up yet reads exactly like a refusal on the merits.
BIND_SECONDS = 1.0

# How long to keep serving after our last sub-game. Their closing exchange
# calls *our* tools, so a peer that exits the moment its own series ends leaves
# the opponent unable to re-hash our log — recorded as `not_run`, on the one
# artefact that proves neither side forged anything (M#19, M#36).
LINGER_SECONDS = 20.0

# How long to pause between sub-games. Both peers close at their own pace, and
# an opening commit that lands while the opponent is still exchanging nonces is
# a commit nobody will answer. Cheap next to the sub-game it protects: three
# seconds against 35 steps, and it cost two sub-games on 13/08 to learn.
SETTLE_SECONDS = 3.0


def plan_for(split: str, first: Role, count: int, ours: Role) -> list[tuple[int, Role]]:
    """Return the ``(sub_game, role)`` pairs *this* process plays.

    Args:
        split: The negotiated block plan, ``"3-3"``.
        first: The role **our team** holds in the first block. A negotiated
            term rather than a derived one: both peers send the identical
            string ``"3-3"`` and it settles nothing about who opens as Cop, so
            two teams deriving it locally build mirror-image plans and meet
            Cop-on-Cop in sub-game one (C-011, N17).
        count: ``num_games`` — 6 under Appendix F Table 18.
        ours: The role this process holds.

    The filter is what carries a 3-3 split across two single-role
    repositories. Both of our processes are handed the same *first*, so the Cop
    repository keeps sub-games 1-3 and the Thief repository keeps 4-6, rather
    than both trying to open the series.
    """
    from core.runtime.series import roles_for

    return [
        (number, role)
        for number, role in enumerate(roles_for(split, first, count), start=1)
        if role is ours
    ]


def play(sdk: PeerSDK, args: argparse.Namespace) -> int:
    """Serve, negotiate, play, file. Returns a process exit code.

    The tunnel is started before the server and stopped in a ``finally`` for
    the reason `cli_commands.serve` gives: an orphaned agent holds the reserved
    domain and the next run cannot bind it — which on match day is the run that
    matters.
    """
    if not args.opponent:
        raise SystemExit("--opponent <url> is required to play a match (M#4)")

    # A different wire protocol is a different everything: a different handshake,
    # turns that carry no move, one audit at the end. It gets its own entry point
    # rather than a flag threaded through this one (C-019).
    if getattr(args, "protocol", "native") == "reference":
        from core import cli_compat

        return cli_compat.play_reference(sdk, args)

    plan = plan_for(args.role_split, Role(args.first), sdk.num_games, sdk.role)
    if not plan:
        raise SystemExit(
            f"a {args.role_split} split with our team opening as {args.first} leaves "
            f"the {sdk.role.value} repository no sub-games to play (C-011)"
        )

    # Before the server exists, not after. Our **inbound** `on_negotiate` agrees
    # the moment the opponent calls it, and from that instant they may commit —
    # while this process is still somewhere in its own handshake. A reset
    # sequenced any later deletes the commit they have already sent, their
    # reveal is refused as unsealed, and a sub-game nobody played wrong is
    # scored a technical loss.
    prepared: set[int] = set()
    reopen(sdk.runtime, prepared)(plan[0][0])

    spec = sdk.server_spec(args.port)
    manager = sdk.tunnel(port=spec.port) if args.tunnel else None
    our_url = f"http://127.0.0.1:{spec.port}/mcp"
    if manager is not None:
        our_url = f"{manager.start()}/mcp"

    # Stashed on `args` because the declaration has to record the address this
    # match was really reachable on, and only this scope knows it: with --tunnel
    # it is read back from the agent, not computed from config.
    args.our_url = our_url
    print(f"role            : {sdk.role.value}  ({sdk.brain_name})")
    print(f"our url         : {our_url}")
    print(f"give them       : --opponent {our_url}")
    print(f"their url       : {args.opponent}\n")
    try:
        if getattr(args, "gui", False):
            # Tk must own the main thread, so the match moves off it. See
            # `core/cli_gui.py` — and note this is the only way to obtain the
            # belief-map capture Ch. 9.4 calls an absolute requirement.
            from core.cli_gui import play_with_window

            return play_with_window(sdk, spec, args, plan, prepared)
        return asyncio.run(_run(sdk, spec, args, plan, prepared))
    finally:
        if manager is not None:
            manager.stop()


async def _run(
    sdk: PeerSDK,
    spec: Any,
    args: argparse.Namespace,
    plan: list[tuple[int, Role]],
    prepared: set[int],
) -> int:
    """Hold the server up for as long as the match needs it."""
    from core.infra.mcp_server import create_server

    server = create_server(spec)
    serving = asyncio.create_task(
        server.run_async(transport="http", host=spec.host, port=spec.port,
                          uvicorn_config={"access_log": False})
    )
    try:
        await asyncio.sleep(BIND_SECONDS)
        return await _handshake_then_play(sdk, args, plan, prepared)
    finally:
        # The session outlives every sub-game now — one connection carries the
        # whole match — so it is this process's to close, and closing it while
        # the loop is still running is the only moment that can. `aclose`
        # swallows its own failures: an opponent who has already gone is the
        # normal end of a match, not an error to raise out of a finally.
        if sdk.opponent is not None:
            await sdk.opponent.aclose()
        serving.cancel()


async def _handshake_then_play(
    sdk: PeerSDK,
    args: argparse.Namespace,
    plan: list[tuple[int, Role]],
    prepared: set[int],
) -> int:
    """Settle the agreement, then play it. Exits 1 rather than playing a refusal."""
    from core.infra.errors import PeerError

    prematch = sdk.prematch
    prematch.role_split = args.role_split
    ours = prematch.proposal()
    if sdk.opponent is None:
        sdk.connect(args.opponent)

    theirs = None
    try:
        theirs = await greet(sdk, ours, float(args.wait))
    except PeerError as error:
        locked = prematch.refused(str(error))
    else:
        locked = prematch.settle(theirs)

    # The inbound tool sets this when *they* initiate; the initiating side has
    # to record its own verdict or the driver refuses its own first commit.
    sdk.runtime.agreed = locked.agreed
    print(f"handshake       : {locked.result}")
    for reason in locked.reasons:
        print(f"  REFUSED: {reason}")
    for warning in prematch.warnings():
        print(f"  ! {warning}")
    if not locked.agreed:
        # File the sub-games we will not play, rather than exiting silently: our
        # inbound server may already have agreed with them, in which case they
        # are playing a match we are not. See `live.forfeit` (M#35).
        from core.runtime.live import refuse

        print(refuse(sdk, args, theirs, locked, plan))
        return 1
    return await _series(sdk, args, theirs, locked, plan, prepared)


async def _series(
    sdk: PeerSDK,
    args: argparse.Namespace,
    theirs: Any,
    locked: Any,
    plan: list[tuple[int, Role]],
    prepared: set[int],
) -> int:
    """Play this process's sub-games and report what they were worth."""
    from core.report.identifiers import game_id
    from core.runtime.live import declare, driver_factory, filing_for, reopen
    from core.runtime.reporting import send_series_report
    from core.runtime.series import SeriesRunner

    declared = theirs.step_zero if theirs is not None else {}
    their_team = str(declared.get("team_name", "")) or "opponent"
    identifier = game_id(sdk.team_name, their_team, locked.agreed_at[:10])
    filing = (
        filing_for(sdk.runtime, identifier, Path(args.out), locked) if args.out else None
    )
    # Before the first move, not after the last: an interrupted series must
    # still leave the declaration it was played under (7.2.1, M#24).
    if filing is not None:
        declare(filing, sdk.runtime, (getattr(args, "our_url", ""), args.opponent), theirs)

    print(f"game id         : {identifier}")
    print(f"our sub-games   : {', '.join(str(number) for number, _ in plan)}\n")
    runner = SeriesRunner(
        build=driver_factory(sdk.runtime, sdk.opponent, prepared),
        plan=plan,
        table=sdk.scoring,
        filing=filing,
        reopen=reopen(sdk.runtime, prepared),
        settle=SETTLE_SECONDS,
    )
    report = await runner.run()
    print_series(report, sdk.scoring, filing)
    # Before the linger, not after: the mail is the one remaining thing that can
    # still lose a match already won, and a human who reads the scoreboard and
    # closes the window must not be the reason it never left (M#35).
    if filing is not None:
        # A self-match can never be counted, whatever the flag says: both sides
        # are us, so the "opponent" would never file the second report M#35
        # requires and the pair could only ever contradict a real one.
        counted = bool(getattr(args, "counted", False)) and their_team != sdk.team_name
        print(send_series_report(sdk.mailer, filing.result_path, sdk.num_games,
                                 sdk.role.value, counted))
    linger = float(getattr(args, "linger", LINGER_SECONDS))
    if linger > 0:
        print(f"\nstaying up {linger:.0f}s so they can finish auditing our log (M#36) ...")
        await asyncio.sleep(linger)
    return 0
