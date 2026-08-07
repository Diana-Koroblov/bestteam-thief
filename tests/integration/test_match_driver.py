"""Two peers play a real sub-game against each other (TODO 9.4).

**This is the test the project was missing.** Every layer below it was covered —
sealing, the tools, the belief filter, the rules — and none of them proved that
a turn can actually be *played*, because nothing drove one. Self-play proves the
strategy works against a god-view harness; this proves the protocol works
against an opponent.

Both peers run the **real** FastMCP server, the real client, the real tool
registration and the real commit-reveal ordering. Only the socket is absent, via
the in-process transport — the same seam `test_localhost_roundtrip.py` uses, and
the reason a full series can be exercised in a test instead of only in a match.

The two drivers run under `asyncio.gather`, which is what makes the ordering
real: each blocks waiting for the other's message, and a driver that sent its
reveal before the opponent's commit arrived would still pass a single-peer test
while being exactly the flaw commit-reveal exists to prevent.
"""

from __future__ import annotations

import asyncio

import pytest

from core.domain.barriers import BarrierManager
from core.infra.mcp_client import OpponentClient
from core.infra.mcp_server import build_server_spec, create_server
from core.protocol.schemas import Role
from core.protocol.tools import build_guarded_tools
from core.report.match_log import build_log, verify_log
from core.runtime.brain_loader import load_brain
from core.runtime.match_driver import MatchDriver
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from tests.paths import brain_class

# A match needs **both** brains in one process, and a published repository ships
# exactly one (ADR-001, M#2). That is not a gap in the test — it is the same
# separation the league relies on, where the two sides run on two machines. So
# these skip where only one role is present, and run in the working tree, which
# is the only place both exist. The split-repository gate exists to catch tests
# that forget this and take the whole suite down at import.
BOTH_ROLES = pytest.mark.skipif(
    brain_class("police") is None or brain_class("thief") is None,
    reason="a match needs both roles; this repository publishes one (ADR-001)",
)


def _peer(config, role: Role) -> PeerRuntime:
    """Build one peer, agreed and ready to play, with its shipped brain."""
    runtime = PeerRuntime(orchestrator=Orchestrator.from_config(config, role))
    runtime.brain = load_brain(config.get(f"strategy.{role.value}_class"), role.value, config)
    runtime.agreed = True
    return runtime


def _drivers(config, port_base: int = 8300):
    """Return two drivers wired to each other's servers, in process."""
    cop, thief = _peer(config, Role.COP), _peer(config, Role.THIEF)
    quota = config.require("movement_and_barriers.max_barriers")
    board = cop.orchestrator.board
    servers = {
        Role.COP: create_server(build_server_spec(build_guarded_tools(cop), "cop", port_base)),
        Role.THIEF: create_server(
            build_server_spec(build_guarded_tools(thief), "thief", port_base + 1)
        ),
    }
    return (
        MatchDriver(
            runtime=cop,
            # Each peer's client points at the *other* peer's server.
            client=OpponentClient("in-process", 10, transport=servers[Role.THIEF]),
            barriers=BarrierManager(max_barriers=quota, board=board),
        ),
        MatchDriver(
            runtime=thief,
            client=OpponentClient("in-process", 10, transport=servers[Role.COP]),
            barriers=BarrierManager(max_barriers=quota, board=board),
        ),
    )


async def _play(config):
    """Run one sub-game to its verdict and return both drivers."""
    cop, thief = _drivers(config)
    await asyncio.gather(cop.play_sub_game(), thief.play_sub_game())
    return cop, thief


@BOTH_ROLES
def test_two_peers_play_a_sub_game_to_a_verdict(minimal_config) -> None:
    """The whole point: a match that actually runs, over the real protocol."""
    cop, thief = asyncio.run(_play(minimal_config))
    assert cop.records, "the cop played no turns at all"
    assert cop.reason and thief.reason
    assert not cop.phases.lost and not thief.phases.lost


@BOTH_ROLES
def test_both_peers_agree_on_the_final_position(minimal_config) -> None:
    """Two independently enforced copies of the physics must not diverge.

    Each peer applies `resolve_turn` to its own state from its own decision and
    the opponent's reveal. If those two computations ever disagreed, the audit
    would blame two honest teams — so this is the check that the rules really
    are being enforced identically on both sides, not merely written once.
    """
    cop, thief = asyncio.run(_play(minimal_config))
    assert cop.state.cop == thief.state.cop
    assert cop.state.thief == thief.state.thief
    assert cop.state.barriers == thief.state.barriers
    assert cop.state.step == thief.state.step


@BOTH_ROLES
def test_the_log_this_produces_verifies(minimal_config) -> None:
    """**The artefact the project cannot be submitted without.**

    A real log, from real seals, re-hashed end to end. Until a driver existed,
    the Replay Viewer had nothing genuine to verify and the mandatory
    `Verified OK` screenshot could not be taken (M#20, Ch. 7.4).
    """
    cop, _ = asyncio.run(_play(minimal_config))
    log = build_log(
        "gid", 1, "cop", [record.entry for record in cop.records], cop.nonces, outcome=cop.reason
    )
    assert log["unverifiable_steps"] == []
    assert verify_log(log).passed


@BOTH_ROLES
def test_every_turn_passed_through_the_state_machine(minimal_config) -> None:
    """**M#4, M#5.** The machine has to govern the flow, not merely exist.

    It was dead code with respect to the game until this driver: defined,
    unit-tested, and referenced by nothing that played.
    """
    from core.runtime.phase_machine import Phase

    cop, _ = asyncio.run(_play(minimal_config))
    assert Phase.COMMITTING in cop.phases.history
    assert Phase.AWAITING_REVEAL in cop.phases.history
    assert cop.phases.history.count(Phase.VERIFYING) == len(cop.records)
    assert cop.phases.phase is Phase.COMPLETE


@BOTH_ROLES
def test_a_peer_that_never_answers_ends_in_a_technical_loss(minimal_config) -> None:
    """A hang is worse than a loss: the opponent must not take us down with them.

    The deadline is squeezed to milliseconds rather than waiting out the
    negotiated 30 seconds, so the failure path is exercised in a test suite
    people will actually run.
    """
    cop, _ = _drivers(minimal_config)
    cop.deadlines.timeout = 0.01
    reason = asyncio.run(cop.play_sub_game())
    assert cop.phases.lost
    assert "never arrived" in reason
