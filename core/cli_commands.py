"""What each CLI command actually does (TODO 2.3.4, 5.1.1, 7.5, 9.1).

Split from ``core/__main__.py`` when that file reached 149 of its 150 permitted
lines. Argument parsing and dispatch stayed there; the work moved here. The
split is along a real seam rather than an arbitrary one: ``__main__`` decides
*which* command runs, this module decides *what* it does, and only the latter
needs to know what a tunnel or a replay session is.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from core.sdk.peer_sdk import PeerSDK

__all__ = ["serve", "handshake", "replay", "negotiate"]


def negotiate(sdk: PeerSDK, args: argparse.Namespace) -> int:
    """Run the pre-match protocol and record what it settled (TODO 9.1).

    Without ``--opponent`` this prints only our side: the digests to compare,
    the counted-match total read from `docs/LEAGUE_LOG.md`, and the clause to
    paste. That is the useful half before a fixture exists, and it is also how
    the numbers get into an email without a peer being live.

    With one, it exchanges handshakes and **exits non-zero on a refusal**, so a
    match cannot be started from a script that ignored the verdict. A refused
    match costs nothing; a disputed one scores 0 for both teams (M#35).
    """
    import asyncio

    from core.infra.errors import PeerError
    from core.protocol.tools import decode_negotiation

    prematch = sdk.prematch
    prematch.role_split = args.role_split
    ours = prematch.proposal()
    print(f"config_sha256     : {ours.config_digest}")
    print(f"scent_model_sha256: {ours.scent_model_digest}")
    print(f"github_commit     : {ours.step_zero.get('github_commit', '')}")
    print(f"counted matches   : {ours.game_count}  (from docs/LEAGUE_LOG.md, M#37)")
    print(f"role split        : {ours.role_split}")
    print(f"\n--- paste this to the opponent (9.1.6) ---\n{prematch.clause()}\n")

    if not args.opponent:
        _print_warnings(prematch.warnings())
        return 0

    # Same guard as `handshake`: a caller that already attached a peer keeps it.
    # In play that is a no-op; it is what lets the whole exchange be driven over
    # the in-process transport in a test rather than only over a socket.
    if sdk._orchestrator.opponent is None:  # noqa: SLF001 - the CLI is the gateway's caller
        sdk.connect(args.opponent)

    async def run() -> int:
        # Only one side of this exchange receives a verdict. Whoever answers
        # raises; whoever asked gets a remote error string. Without this catch
        # the initiator would learn of a refusal as a traceback and file nothing
        # — losing the record of the outcome most likely to be argued about.
        client = sdk._orchestrator.opponent  # noqa: SLF001 - the CLI is the gateway's caller
        try:
            theirs = decode_negotiation(await client.call("negotiate", ours.payload()))
        except PeerError as error:
            locked, theirs = prematch.refused(str(error)), None
        else:
            locked = prematch.settle(theirs)
        print(f"result            : {locked.result}")
        # Only printed when they actually answered. A refusal leaves these at
        # their zero values, and "they declare 0 counted matches" is a sentence
        # about a peer we never heard from — a plausible wrong figure, which the
        # artefact rules rank below an absent one because it prompts no question.
        if theirs is not None:
            print(f"their commit      : {locked.their_commit or '(none declared)'}")
            print(f"they declare      : {locked.their_games_played} counted match(es)")
        for reason in locked.reasons:
            print(f"  REFUSED: {reason}")
        _print_warnings(prematch.warnings())
        if args.out:
            print(f"\nagreement written : {_record(locked, ours, theirs, args.out)}")
        return 0 if locked.agreed else 1

    return asyncio.run(run())


def _print_warnings(found: list[str]) -> None:
    """Print what a human still has to settle, or say that nothing is open."""
    if not found:
        print("nothing outstanding.")
        return
    print("SETTLE BEFORE THE FIRST MOVE (M#35):")
    for warning in found:
        print(f"  ! {warning}")


def _record(locked, ours, theirs, directory) -> Path:
    """Write the agreement beside the match artefacts (N10, 9.3.5).

    Named from the shared ``game_id`` so both teams' files carry the same
    identifier, and from the opponent's **declared** team name rather than one
    we typed — an agreement filed under a name they never claimed is evidence
    for the wrong match. ``theirs`` is None when they refused before declaring
    anything, and ``unknown`` says exactly that rather than inventing a name.
    """
    from core.report.artefacts import write
    from core.report.identifiers import game_id

    declared = theirs.step_zero if theirs is not None else {}
    ours_team = str(ours.step_zero.get("team_name", "")) or "unknown"
    identifier = game_id(ours_team, str(declared.get("team_name", "")) or "unknown", locked.agreed_at[:10])
    return write(locked.payload(), Path(directory), f"agreement_{identifier}.json")


def replay(args: argparse.Namespace) -> int:
    """Verify a saved log, then show it (TODO 7.5).

    The verdict is printed either way and the **exit code carries it** — 0 for
    `Verified OK`, 1 for `TAMPERED` — so a log can be checked from a script or
    a CI job without a display. One `TAMPERED` voids the match (7.24), which is
    not a verdict that should require a human to be looking at a window.
    """
    from core.sdk.replay_sdk import load_replay

    session = load_replay(args.log)
    print(session.describe())
    if not args.headless:  # pragma: no cover - opens a window
        from core.ui.replay import ReplayViewer

        ReplayViewer(args.log, args.grid).run()
    return 0 if session.result.passed else 1


def serve(sdk: PeerSDK, port: int | None, tunnel: bool = False) -> int:
    """Run this peer's MCP server until interrupted, optionally exposed publicly.

    Ctrl-C is the normal way to stop a server, so it exits quietly. Letting the
    KeyboardInterrupt escape prints a ten-frame traceback through asyncio and
    anyio, which teaches whoever is watching to ignore tracebacks — exactly the
    habit that hides a real one during a match.

    The tunnel is started **before** the server and torn down in a `finally`.
    Before, because a tunnel that cannot start should cost nothing but an error
    message; in a `finally`, because an agent orphaned by a crashed peer holds
    the reserved domain and the next run cannot bind it (TODO 5.1.1).
    """
    from core.infra.mcp_server import create_server

    spec = sdk.server_spec(port)
    # No trailing slash: FastMCP serves at /mcp, and /mcp/ costs a 307 redirect
    # before every single request. The client strips it defensively too.
    url = f"http://127.0.0.1:{spec.port}/mcp"
    manager = sdk.tunnel(port=spec.port) if tunnel else None
    if manager is not None:
        url = f"{manager.start()}/mcp"

    print(f"\nserving {len(spec.tools)} tools on http://{spec.host}:{spec.port}/mcp")
    print(f"give the other terminal:  --opponent {url}")
    print("ctrl-c to stop.\n")
    try:
        create_server(spec).run(transport="http", host=spec.host, port=spec.port)
    except KeyboardInterrupt:
        print("\nserver stopped.")
    finally:
        if manager is not None:
            manager.stop()
    return 0


def handshake(sdk: PeerSDK, opponent: str | None) -> int:
    """Negotiate with the opponent and send one sealed move (milestone M2).

    Deliberately does the *whole* exchange rather than a bare ping: a handshake
    that succeeds proves the digests match, the tools are registered and the
    encoding survives — which is what M2 actually claims.
    """
    import asyncio

    from core.crypto.commitment import seal

    if not opponent:
        raise SystemExit("--handshake needs --opponent <url>")
    if sdk._orchestrator.opponent is None:  # noqa: SLF001 - the CLI is the gateway's caller
        sdk.connect(opponent)

    async def run() -> int:
        client = sdk._orchestrator.opponent  # noqa: SLF001
        agreed = await client.call(
            "negotiate",
            {"step": 0, "role": sdk.role.value, "config_digest": sdk.config_digest},
        )
        print(f"negotiate  -> agreed on {agreed['config_digest'][:16]}...")

        view = sdk.board_view()
        sealed = seal({"cop": list(view.cop), "thief": list(view.thief), "step": 0}, "S", "truth")
        ack = await client.call(
            "receive_commit", {"step": 0, "role": sdk.role.value, "digest": sealed.digest}
        )
        print(f"commit     -> {ack['kind']} for {ack['acknowledged_digest'][:16]}...")

        reply = await client.call(
            "receive_reveal",
            {"step": 0, "role": sdk.role.value, "move": "S", "hint": "heading south"},
        )
        print(f"reveal     -> {reply}")
        print("\nM2 observed: a message left this peer and decoded correctly at the other.")
        return 0

    return asyncio.run(run())
