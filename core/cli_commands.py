"""What each CLI command actually does (TODO 2.3.4, 5.1.1, 7.5).

Split from ``core/__main__.py`` when that file reached 149 of its 150 permitted
lines. Argument parsing and dispatch stayed there; the work moved here. The
split is along a real seam rather than an arbitrary one: ``__main__`` decides
*which* command runs, this module decides *what* it does, and only the latter
needs to know what a tunnel or a replay session is.
"""

from __future__ import annotations

import argparse

from core.sdk.peer_sdk import PeerSDK

__all__ = ["serve", "handshake", "replay"]


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
