"""Playing a series against a peer that speaks the reference protocol.

    python -m core play --role cop --protocol reference \
        --opponent https://them.trycloudflare.com/mcp --tunnel

The mirror of `cli_play.py`, and deliberately a separate entry point rather than
a branch inside it. That file is the audited native path — it negotiates with
`PreMatch`, files four artefacts and mails a report — and none of that survives
contact with a protocol whose handshake is a different message, whose turns
carry no move, and whose audit is one payload at the end.

**Uncounted by design, for now.** Nothing here files a league artefact or sends
a report: the native path owns those, and a result produced under a different
protocol should not quietly enter the league record until its scoring has been
agreed with the lecturer. It plays, it audits, it prints. That is enough to stop
being unable to play anyone.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import time
from typing import Any

from core.compat.mailbox import Inboxes, build_reference_tools
from core.compat.session import HandshakeError, ReferenceSession
from core.infra.errors import PeerError
from core.infra.llm.factory import model_name
from core.protocol.schemas import Role
from core.sdk.peer_sdk import PeerSDK

__all__ = ["play_reference"]

# Matches `cli_play`: let the server bind before anyone is invited to call it.
BIND_SECONDS = 1.0

# How long to wait between handshake attempts while an opponent starts up.
RETRY_SECONDS = 3.0


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
        server.run_async(transport="http", host=spec.host, port=spec.port)
    )
    try:
        await asyncio.sleep(BIND_SECONDS)
        if sdk.opponent is None:
            sdk.connect(args.opponent)
        return await _series(sdk, args, plan, inboxes)
    finally:
        if sdk.opponent is not None:
            await sdk.opponent.aclose()
        serving.cancel()


async def _series(
    sdk: PeerSDK,
    args: argparse.Namespace,
    plan: list[tuple[int, Role]],
    inboxes: Inboxes,
) -> int:
    """Play each sub-game the plan gives us, and report what happened.

    The handshake runs **per sub-game**, because the reference rebuilds a whole
    runtime for each one and negotiates again from it. A peer that agreed once
    and then stayed silent would leave every later agreement sitting unread in
    their inbox while they waited for ours.
    """
    failures = 0
    for number, _role in plan:
        sdk.runtime.start_sub_game(number)
        inboxes.drain()
        session = ReferenceSession(
            runtime=sdk.runtime,
            client=sdk.opponent,
            inboxes=inboxes,
            identity=_identity(sdk),
        )
        message, terms = session.agreement_message()
        try:
            await _push(sdk.opponent, message, float(args.wait))
            await session.collect_agreement(float(args.wait), terms)
        except (HandshakeError, PeerError) as error:
            print(f"  sub-game {number}  HANDSHAKE REFUSED\n    {error}")
            failures += 1
            continue
        result = await session.play_sub_game()
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
    print(
        "\nplayed under the reference protocol - not filed, not reported.\n"
        "  agree the scoreboard with them by hand (M#36)."
    )
    return 1 if failures else 0


async def _push(client: Any, message: dict, seconds: float) -> None:
    """Send our agreement, retrying while the opponent is still starting up.

    Only a **transport** failure is retried. Peers legitimately start seconds
    apart, and the native path gives the same courtesy in `cli_handshake.greet`.
    A refusal on the merits is not retryable and is not raised here at all — it
    comes back later, as their agreement failing to verify.
    """
    from core.infra.errors import TransportError

    deadline = time.monotonic() + seconds
    while True:
        try:
            await client.call("negotiate", message, argument="message")
            return
        except TransportError:
            if time.monotonic() >= deadline:
                raise
            print(f"  no answer yet; retrying for {deadline - time.monotonic():.0f}s more ...")
            await asyncio.sleep(RETRY_SECONDS)


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
    }
