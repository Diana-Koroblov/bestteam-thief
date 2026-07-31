"""CLI entry point: ``uv run python -m core peer --role police|thief``.

Two separate OS processes, two separate config directories, one role each
(M#1, M#4). The role is a **required** flag with no default, so a peer cannot be
started ambiguously — a process that guessed its own role could be started twice
as the same side, and the resulting match would be unauditable.

The two roles read `config/police/` and `config/thief/` respectively, which is
also the boundary the published repositories split on: each ships only its own.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.protocol.schemas import Role
from core.sdk.peer_sdk import PeerSDK

__all__ = ["main"]

ROOT = Path(__file__).resolve().parent.parent

# The role name on the command line, and the config directory it reads.
CONFIG_DIRS: dict[str, str] = {"police": "police", "cop": "police", "thief": "thief"}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        prog="python -m core",
        description="Run one peer of a Cops-and-Robbers match.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    peer = sub.add_parser("peer", help="Start this peer.")
    peer.add_argument(
        "--role",
        required=True,
        choices=sorted(CONFIG_DIRS),
        help="Which side this process plays. No default, on purpose.",
    )
    peer.add_argument("--opponent", help="The opponent's public MCP URL.")
    peer.add_argument("--dry-run", action="store_true", help="Load and report, then exit.")
    peer.add_argument("--serve", action="store_true", help="Run the MCP server and wait.")
    peer.add_argument("--port", type=int, help="Override the port from config.")
    peer.add_argument(
        "--handshake",
        action="store_true",
        help="Negotiate with --opponent, send one sealed move, print the replies.",
    )
    return parser.parse_args(argv)


def _config_dir(role: str) -> Path:
    """Return the config directory for *role*, or exit with a clear reason.

    A published repository ships one role only, so asking a Cop repository to
    run a Thief must say so plainly rather than failing later on a missing file.
    """
    directory = ROOT / "config" / CONFIG_DIRS[role]
    if not (directory / "game.json").is_file():
        raise SystemExit(
            f"no configuration for role {role!r} in this repository "
            f"({directory} has no game.json). Each published repository ships "
            "one role only; use the other repository for the other side."
        )
    return directory


def main(argv: list[str] | None = None) -> int:
    """Return 0 when the peer started cleanly."""
    args = _parse_args(argv)
    role = Role.COP if CONFIG_DIRS[args.role] == "police" else Role.THIEF
    sdk = PeerSDK(_config_dir(args.role), role)

    view = sdk.board_view()
    print(f"role            : {sdk.role.value}")
    print(f"config digest   : {sdk.config_digest[:16]}...")
    print(f"board           : {view.grid_size}x{view.grid_size}")
    print(f"cop / thief     : {view.cop} / {view.thief}")
    print(f"barriers        : {view.barriers_remaining} remaining")
    print(f"our legal moves : {', '.join(sdk.legal_moves())}")

    if args.opponent:
        sdk.connect(args.opponent)
        print(f"opponent        : {args.opponent}")

    if args.dry_run:
        print("\ndry run - configuration loaded, nothing started.")
        return 0
    if args.serve:
        return _serve(sdk, args.port)
    if args.handshake:
        return _handshake(sdk, args.opponent)

    print("\nthe turn loop arrives in Phase 3; this peer is wired but not yet playing.")
    print("try --serve in one terminal and --handshake --opponent <url> in another.")
    return 0


def _serve(sdk: PeerSDK, port: int | None) -> int:
    """Run this peer's MCP server until interrupted.

    Ctrl-C is the normal way to stop a server, so it exits quietly. Letting the
    KeyboardInterrupt escape prints a ten-frame traceback through asyncio and
    anyio, which teaches whoever is watching to ignore tracebacks — exactly the
    habit that hides a real one during a match.
    """
    from core.infra.mcp_server import create_server

    spec = sdk.server_spec(port)
    # No trailing slash: FastMCP serves at /mcp, and /mcp/ costs a 307 redirect
    # before every single request. The client strips it defensively too.
    url = f"http://127.0.0.1:{spec.port}/mcp"
    print(f"\nserving {len(spec.tools)} tools on http://{spec.host}:{spec.port}/mcp")
    print(f"give the other terminal:  --opponent {url}")
    print("ctrl-c to stop.\n")
    try:
        create_server(spec).run(transport="http", host=spec.host, port=spec.port)
    except KeyboardInterrupt:
        print("\nserver stopped.")
    return 0


def _handshake(sdk: PeerSDK, opponent: str | None) -> int:
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


if __name__ == "__main__":
    sys.exit(main())
