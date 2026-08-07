"""Run the whole pre-match protocol against ourselves (TODO 9.1, 9.2.1).

    uv run python scripts/rehearse_handshake.py [--out results/rehearsal]

M#52 permits warm-ups and recommends them, for the reason this script exists:
protocol bugs should be found on a Tuesday and not thirty seconds before a
counted match. This is that warm-up reduced to its cheapest useful part — the
handshake only, no moves — driven through the **real** FastMCP transport, our own
`create_server`, our own client and our own tool registration. Only the socket is
absent.

**What a green run does and does not prove.** It proves the exchange serialises,
registers, decodes and settles end to end: 4.1.6 and the echoing `on_negotiate`
were both bugs of exactly that shape, invisible to unit tests and fatal on the
wire. It proves **nothing** about agreement, because both sides are this code and
identical peers always agree. A real opponent is the only thing that tests the
refusals, which is why every one of them is unit-tested against hand-built
messages instead.

The artefact is filed under a `bestteam-vs-bestteam` game id, which says what it
is at a glance. A rehearsal that could be mistaken for a counted match would be
worse than no rehearsal at all.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.infra.mcp_client import OpponentClient  # noqa: E402
from core.infra.mcp_server import build_server_spec, create_server  # noqa: E402
from core.protocol.schemas import Role  # noqa: E402
from core.protocol.tools import build_guarded_tools, decode_negotiation  # noqa: E402
from core.report.artefacts import write  # noqa: E402
from core.report.identifiers import game_id  # noqa: E402
from core.runtime.orchestrator import Orchestrator  # noqa: E402
from core.runtime.peer_runtime import PeerRuntime  # noqa: E402
from core.shared.config_manager import load_config  # noqa: E402

__all__ = ["main", "rehearse"]


def _config():
    """Load whichever role this repository ships (ADR-001).

    Either one works: the *shared* half is byte-identical across both by
    construction, and the shared half is the entire subject of a handshake.
    """
    role = "police" if (ROOT / "config" / "police" / "game.json").is_file() else "thief"
    return load_config(ROOT / "config" / role)


async def rehearse(out: Path | None) -> int:
    """Exchange handshakes between two local peers and report the outcome."""
    config = _config()
    ours = PeerRuntime(orchestrator=Orchestrator.from_config(config, Role.COP))
    theirs = PeerRuntime(orchestrator=Orchestrator.from_config(config, Role.THIEF))

    server = create_server(build_server_spec(build_guarded_tools(theirs), "rehearsal", 8099))
    client = OpponentClient(base_url="in-process", timeout_sec=10, transport=server)

    proposal = ours.prematch.proposal()
    print(f"  cop   -> config {proposal.config_digest[:16]}... scent "
          f"{proposal.scent_model_digest[:16]}...")
    reply = decode_negotiation(await client.call("negotiate", proposal.payload()))
    print(f"  thief -> config {reply.config_digest[:16]}... scent "
          f"{reply.scent_model_digest[:16]}...")

    locked = ours.prematch.settle(reply)
    print(f"\n  result: {locked.result}")
    for reason in locked.reasons:
        print(f"    REFUSED: {reason}")
    for warning in ours.prematch.warnings():
        print(f"    ! {warning}")

    _check(proposal, reply)
    if out is not None:
        identifier = game_id(proposal.step_zero["team_name"], reply.step_zero["team_name"], locked.agreed_at[:10])
        print(f"\n  filed: {write(locked.payload(), out, f'rehearsal_{identifier}.json')}")
    return 0 if locked.agreed else 1


def _check(proposal, reply) -> None:
    """Report which parts of 9.1 actually crossed the wire.

    Named individually rather than summarised. Every one of these was a field
    that existed, travelled and was compared by nothing until 9.1 — so "the
    handshake worked" is precisely the sentence that was true while four of the
    eight DoDs had no enforcement behind them.
    """
    print()
    for label, mine, yours in (
        ("9.1.1 config digest", proposal.config_digest, reply.config_digest),
        ("9.1.2 scent model  ", proposal.scent_model_digest, reply.scent_model_digest),
        ("9.1.5 readings     ", proposal.readings, reply.readings),
        ("9.1.8 role split   ", proposal.role_split, reply.role_split),
        (
            "9.1.4 commit      ",
            proposal.step_zero.get("github_commit"),
            reply.step_zero.get("github_commit"),
        ),
    ):
        state = "crossed intact" if mine == yours and yours else "*** DID NOT ARRIVE ***"
        print(f"  {label}: {state}")


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the rehearsal."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "rehearsal",
        help="Where to file the agreement. Pass --no-file to skip.",
    )
    parser.add_argument("--no-file", action="store_true", help="Run without writing anything.")
    args = parser.parse_args(argv)

    print("Rehearsing the pre-match handshake over the real transport.\n")
    return asyncio.run(rehearse(None if args.no_file else args.out))


if __name__ == "__main__":
    raise SystemExit(main())
