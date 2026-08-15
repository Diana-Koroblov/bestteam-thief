"""Playing a series against a peer that speaks the reference protocol.

    python -m core play --role cop --protocol reference \
        --opponent https://them.trycloudflare.com/mcp --tunnel --out results/ \
        --report-to friendly@them.example,us@ourteam.example

The mirror of `cli_play.py`, and deliberately a separate entry point rather than
a branch inside it. That file is the audited native path — it negotiates with
`PreMatch`, files four artefacts and mails a report — and none of that survives
contact with a protocol whose handshake is a different message, whose turns
carry no move, and whose audit is one payload at the end.

**Files and reports in the league's own schema, not ours.** `core/compat/
league_report.py` builds the four-artefact shape most of this league already
files (`docs/PAIRING-PLAYBOOK.md`), keyed by group name rather than "ours" and
"theirs". Pass `--out` to file it; pass `--report-to` for an uncounted
(friendly) send, or `--counted` for a league one — exactly the native path's
gating, applied to a different schema.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
from typing import Any

from core.compat import reporting
from core.compat.league_row import row_from_session
from core.compat.mailbox import Inboxes, build_reference_tools
from core.compat.session import HandshakeError, ReferenceSession, reconnect
from core.compat.turn_wait import TURN_WAIT_SECONDS, await_agreement
from core.infra.errors import PeerError
from core.infra.llm.factory import model_name
from core.protocol.schemas import Role
from core.report.artefacts import utc_now
from core.sdk.peer_sdk import PeerSDK
from core.shared.league_log import counted_matches

__all__ = ["play_reference"]

# Matches `cli_play`: let the server bind before anyone is invited to call it.
BIND_SECONDS = 1.0


def play_reference(sdk: PeerSDK, args: argparse.Namespace) -> int:
    """Serve the four mailbox tools, then play our share of the series."""
    from core.cli_play import plan_for

    plan = plan_for(args.role_split, Role(args.first), sdk.num_games, sdk.role)
    if not plan:
        raise SystemExit(
            f"a {args.role_split} split with our team opening as {args.first} leaves "
            f"the {sdk.role.value} repository no sub-games to play (C-011)"
        )

    inboxes = Inboxes()
    spec = sdk.server_spec(args.port, tools=build_reference_tools(inboxes))
    manager = sdk.tunnel(port=spec.port) if args.tunnel else None
    our_url = f"http://127.0.0.1:{spec.port}/mcp"
    if manager is not None:
        our_url = f"{manager.start()}/mcp"

    if getattr(args, "gui", False):
        # Said out loud rather than ignored. The window is driven by the native
        # turn loop in `core/cli_gui.py`, and a flag that quietly does nothing
        # is worse than one that is refused: Ch. 9.4 wants a belief-map capture,
        # and discovering afterwards that no window ever opened is too late.
        print("note            : --gui is not available on the reference protocol; "
              "run without --protocol reference to watch a match.")
    print(f"role            : {sdk.role.value}  ({sdk.brain_name})")
    print("protocol        : reference (negotiate / receive_turn / submit_audit)")
    print(f"our url         : {our_url}")
    print(f"give them       : --opponent {our_url}")
    print(f"their url       : {args.opponent}")
    print(f"our sub-games   : {', '.join(str(number) for number, _ in plan)}\n")
    try:
        return asyncio.run(_run(sdk, spec, args, plan, inboxes))
    finally:
        if manager is not None:
            manager.stop()


async def _run(
    sdk: PeerSDK,
    spec: Any,
    args: argparse.Namespace,
    plan: list[tuple[int, Role]],
    inboxes: Inboxes,
) -> int:
    """Hold the server up for as long as the series needs it."""
    from core.infra.mcp_server import create_server

    server = create_server(spec)
    serving = asyncio.create_task(
        server.run_async(transport="http", host=spec.host, port=spec.port,
                          uvicorn_config={"access_log": False})
    )
    try:
        await asyncio.sleep(BIND_SECONDS)
        return await _series(sdk, args, plan, inboxes)
    finally:
        if sdk.opponent is not None:
            await sdk.opponent.aclose()
        # The same deliberate-shutdown noise `cli_play._run` silences, and for
        # the same reason: uvicorn.Server._serve() has no try/finally around its
        # main loop, so cancelling it never reaches uvicorn's own shutdown and
        # asyncio.run()'s teardown force-cancels the ASGI lifespan task and any
        # open SSE stream instead. Uvicorn logs both at ERROR with a full
        # traceback on every clean exit — here, twice, after a series that
        # passed every audit. The process ends immediately after, so the logger
        # is never restored.
        logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)
        serving.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await serving


async def _series(
    sdk: PeerSDK,
    args: argparse.Namespace,
    plan: list[tuple[int, Role]],
    inboxes: Inboxes,
) -> int:
    """Play each sub-game the plan gives us, file, and report what happened.

    The handshake runs **per sub-game**, because the reference rebuilds a whole
    runtime for each one and negotiates again from it. A peer that agreed once
    and then stayed silent would leave every later agreement sitting unread in
    their inbox while they waited for ours.
    """
    identity = _identity(sdk)
    failures = 0
    rows: list[dict[str, Any]] = []
    their_group = ""
    their_identity: dict[str, Any] = {}
    for number, _role in plan:
        sdk.runtime.start_sub_game(number)
        inboxes.drain()
        await reconnect(sdk, args.opponent)
        session = ReferenceSession(
            runtime=sdk.runtime, client=sdk.opponent, inboxes=inboxes,
            identity=identity, sub_game_number=number,
        )
        message, _ = session.agreement_message()
        started = utc_now()
        try:
            # Waits for an agreement stamped for THIS sub-game, re-sending ours
            # meanwhile: under an alternating split our plan has gaps and the
            # opponent is two sub-games away. See core/compat/turn_wait.py.
            theirs = await await_agreement(
                session, sdk.opponent, message,
                total_wait=float(getattr(args, "turn_wait", TURN_WAIT_SECONDS)),
                push_wait=float(args.wait),
            )
        except (HandshakeError, PeerError) as error:
            print(f"  sub-game {number}  HANDSHAKE REFUSED\n    {error}")
            failures += 1
            continue
        declared = dict(theirs.get("identity") or {})
        their_group = str(declared.get("group_id", "")) or their_group
        their_identity = declared or their_identity
        print("".join(f"    ! {note}\n" for note in session.warnings), end="")
        result = await session.play_sub_game(on_turn=lambda line, n=number: print(f"  [{n}] {line}"))
        # Best effort: the peer that just won may exit the moment it has read
        # its inbox, killing its server mid-response — while our payload landed
        # anyway and theirs may already be waiting for us.
        with contextlib.suppress(PeerError):
            await sdk.opponent.call(
                "submit_audit", session.audit_payload(), argument="payload"
            )
        verdict = await session.collect_audit(float(args.linger) or 20.0)
        print(
            f"  sub-game {number}  {sdk.role.value:5} {result:24} "
            f"{'audit passed' if verdict['passed'] else 'audit FAILED'}"
            f"{'' if verdict.get('received') else ' (no audit received)'}"
        )
        if not verdict["passed"]:
            print(f"    their failed steps: {verdict['failed_steps']}")
        if args.out:
            their_commit = str(getattr(args, "their_commit", "") or "")
            rows.append(row_from_session(
                sdk=sdk, session=session, number=number, raw_result=result, verdict=verdict,
                started=started, ended=utc_now(), their_group=their_group,
                their_commit=their_commit,
            ))
    print()
    if args.out:
        print(reporting.send_league_report(sdk, args, rows, identity, their_identity, their_group))
    else:
        print("not filed - pass --out to write the four artefacts (M#35 needs a real report)")
    return 1 if failures else 0


def _identity(sdk: PeerSDK) -> dict:
    """Return who we are, for the declaration both sides must publish.

    Built here rather than in the session because `model_name` reads the
    provider registry, and `core/compat/` must not reach into `core.infra` —
    joining two subsystems is the gateway's job and nobody else's (M#3).
    """
    config = sdk.runtime.orchestrator.config
    return {
        "group_id": sdk.team_name,
        "group_name": sdk.team_name,
        "members": list(config.get("identity.members", ()) or ()),
        "repos": {
            "cop": str(config.get("identity.repo_cop", "")),
            "thief": str(config.get("identity.repo_thief", "")),
        },
        "llm_model": model_name(config),
        # Read from the log, never typed: M#38 disqualifies the whole project
        # for a wrong declared count, and the only caller that may read this
        # key is the one thing that cannot lie about it (core/shared/league_log.py).
        "counted_games_played": counted_matches(),
    }
