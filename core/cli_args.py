"""Defining the command line, away from the code that acts on it.

Split out of ``core/__main__.py`` when the parser outgrew it: four subcommands
with their flags is most of that file, and every new flag pushed the entry point
further past the 150-line ceiling ADR-005 sets.

The seam is a real one rather than a way to satisfy a gate. This module states
**what may be asked for**; `__main__` decides **what to do about it**. Nothing
here imports the runtime, so the whole surface can be parsed and asserted on
without building a peer — which is what the CLI tests do.
"""

from __future__ import annotations

import argparse
from pathlib import Path

__all__ = ["parse_args", "CONFIG_DIRS"]

# The role name on the command line, and the config directory it reads.
CONFIG_DIRS: dict[str, str] = {"police": "police", "cop": "police", "thief": "thief"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
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
        "--tunnel",
        action="store_true",
        help="Expose the server publicly through the configured tunnel provider. "
        "Required for league play (M#10); local development does not need it.",
    )
    peer.add_argument(
        "--handshake",
        action="store_true",
        help="Negotiate with --opponent, send one sealed move, print the replies.",
    )
    peer.add_argument(
        "--gui", action="store_true", help="Open the Live GUI. Shows local truth only (M#8)."
    )

    match = sub.add_parser("play", help="Play a full series against a live opponent (TODO 9.2).")
    match.add_argument("--role", required=True, choices=sorted(CONFIG_DIRS))
    match.add_argument("--opponent", required=True, help="Their public MCP URL.")
    match.add_argument("--port", type=int, help="Override the listen port from config.")
    match.add_argument("--tunnel", action="store_true", help="Expose us publicly (M#10).")
    match.add_argument("--out", type=Path, help="Where the four artefacts go. Omit to file none.")
    match.add_argument("--role-split", default="3-3", help="The negotiated block plan (N17).")
    match.add_argument(
        "--wait", type=float, default=120.0, help="Seconds to keep retrying the handshake."
    )
    match.add_argument(
        "--linger", type=float, default=20.0, help="Seconds to serve on, so they can audit us."
    )
    match.add_argument(
        "--first",
        default="cop",
        choices=["cop", "thief"],
        help="The role OUR TEAM holds in the first block. Negotiated with the "
        "opponent, never assumed, and identical for both of our processes (C-011).",
    )
    match.add_argument("--counted", action="store_true", help="A LEAGUE match: mail the "
                       "closing report (M#32). Omit for rehearsals - the report is filed, "
                       "not sent, and the command to send it by hand is printed.")
    match.add_argument("--gui", action="store_true", help="Watch the match in the Live "
                       "GUI: own position, own barriers, the belief heat map and the hints "
                       "received. Local truth only (M#8, M#9). Closing it does not forfeit.")

    settle = sub.add_parser("negotiate", help="Run the pre-match protocol (TODO 9.1).")
    settle.add_argument("--role", required=True, choices=sorted(CONFIG_DIRS))
    settle.add_argument("--opponent", help="Their public MCP URL. Omit to print our side only.")
    settle.add_argument(
        "--role-split",
        default="3-3",
        help="How the sub-games divide. Stated, never assumed - it is in no Appendix (N17).",
    )
    settle.add_argument(
        "--pack",
        type=Path,
        help="Write everything an opponent needs into this directory: the config "
        "to load byte-identically, the handshake we send, and the clauses to agree.",
    )
    settle.add_argument(
        "--review",
        type=Path,
        help="Review a game.json THEY proposed against Appendix F and ours. Exits "
        "non-zero on a breach: agreeing to one disqualifies BOTH teams (M#12).",
    )
    settle.add_argument(
        "--out",
        type=Path,
        help="Directory for agreement_<game_id>.json. Omit to settle without filing.",
    )

    replay = sub.add_parser("replay", help="Open a saved match log and verify it (M#20).")
    replay.add_argument("log", type=Path, help="Path to log_<game_id>_gNN.json.")
    replay.add_argument("--grid", type=int, default=7, help="Board edge; a log records positions.")
    replay.add_argument(
        "--headless",
        action="store_true",
        help="Print the verdict and exit without opening a window. Exits non-zero on TAMPERED.",
    )
    return parser.parse_args(argv)
