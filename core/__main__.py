"""CLI entry point: ``uv run python -m core peer --role police|thief``.

Two separate OS processes, two separate config directories, one role each
(M#1, M#4). The role is a **required** flag with no default, so a peer cannot be
started ambiguously — a process that guessed its own role could be started twice
as the same side, and the resulting match would be unauditable.

The two roles read `config/police/` and `config/thief/` respectively, which is
also the boundary the published repositories split on: each ships only its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

from core import cli_commands
from core.cli_args import CONFIG_DIRS, parse_args
from core.protocol.schemas import Role
from core.sdk.peer_sdk import PeerSDK
from core.shared.provider_budget import BudgetError

__all__ = ["main"]

ROOT = Path(__file__).resolve().parent.parent


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
    args = parse_args(argv)
    if args.command == "replay":
        return cli_commands.replay(args)
    if args.command == "probe":
        # Before the SDK, like `replay`: asking a stranger's server what it
        # exposes needs no role, no config and no runtime of ours, and
        # requiring one would make the check unrunnable from a clone that has
        # not been set up yet — which is exactly when it is most useful.
        from core import cli_probe

        return cli_probe.probe_command(args)

    role = Role.COP if CONFIG_DIRS[args.role] == "police" else Role.THIEF
    sdk = PeerSDK(_config_dir(args.role), role)

    # Before anything else, and before any model is contacted: a metered
    # provider paired with every_n_steps = 1 burns ~52k tokens over a series,
    # and the two halves live on different machines (TODO 7.1.6).
    try:
        sdk.verify_budget()
    except BudgetError as error:
        raise SystemExit(str(error)) from error

    if args.command == "negotiate":
        from core import cli_negotiate

        return cli_negotiate.negotiate(sdk, args)
    if args.command == "play":
        from core import cli_play

        return cli_play.play(sdk, args)

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
    if args.gui:  # pragma: no cover - opens a window
        from core.ui.live_gui import LiveGui

        # `sdk.gui_state`, never `sdk.board_view`: the latter carries both true
        # positions and putting it on a screen is disqualification (M#8, M#9).
        LiveGui(sdk.gui_state, int(sdk.ui_cell_pixels)).run()
        return 0
    if args.serve:
        return cli_commands.serve(sdk, args.port, args.tunnel)
    if args.handshake:
        return cli_commands.handshake(sdk, args.opponent)

    print("\nthe turn loop arrives in Phase 3; this peer is wired but not yet playing.")
    print("try --serve in one terminal and --handshake --opponent <url> in another.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
