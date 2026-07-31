"""A real MCP round trip between two peers (TODO 2.4.2).

**Why this test exists at all.** The first transport posted plain JSON to
``/tools/<name>``. Every unit test passed, because they mocked HTTP. No opponent
would ever have answered: FastMCP speaks JSON-RPC over streamable HTTP, and the
two peers would simply have failed to connect on match day. Nothing short of an
end-to-end exchange over the genuine protocol would have caught it.

So this drives a **real** ``FastMCP`` server, built by our own ``create_server``,
through a **real** ``fastmcp.Client``, using the in-process transport. The
protocol, the encoding, the tool registration and the error mapping are all the
production path; only the socket is absent.
"""

from __future__ import annotations

import pytest

from core.crypto.commitment import seal
from core.infra.errors import PeerError, RemoteToolError
from core.infra.mcp_client import OpponentClient
from core.infra.mcp_server import build_server_spec, create_server
from core.protocol.schemas import Role
from core.protocol.tools import build_guarded_tools
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime


@pytest.fixture
def thief_peer(minimal_config) -> PeerRuntime:
    """A thief peer that has already agreed the configuration."""
    peer = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.THIEF))
    peer.agreed = True
    return peer


@pytest.fixture
def cop_to_thief(thief_peer: PeerRuntime) -> OpponentClient:
    """A cop-side client wired to a live thief-side MCP server."""
    server = create_server(
        build_server_spec(build_guarded_tools(thief_peer), name="bestteam-thief", port=8082)
    )
    return OpponentClient(base_url="in-process", timeout_sec=5, team="bestteam", transport=server)


async def test_a_commit_crosses_the_wire_and_is_acknowledged(
    cop_to_thief: OpponentClient, thief_peer: PeerRuntime
) -> None:
    """The DoD: a message leaving A is received and decoded correctly at B."""
    sealed = seal({"cop": [0, 0], "thief": [3, 3], "step": 0}, "S", "truth")
    reply = await cop_to_thief.call(
        "receive_commit", {"step": 0, "role": "cop", "digest": sealed.digest}
    )
    assert reply["kind"] == "ack"
    assert reply["acknowledged_digest"] == sealed.digest
    assert thief_peer.commits[0] == sealed.digest


async def test_a_full_commit_then_reveal_exchange(
    cop_to_thief: OpponentClient, thief_peer: PeerRuntime
) -> None:
    """Two turns of the real sequence, in order."""
    for step in (0, 1):
        sealed = seal({"step": step}, "E", "truth")
        await cop_to_thief.call(
            "receive_commit", {"step": step, "role": "cop", "digest": sealed.digest}
        )
        reply = await cop_to_thief.call(
            "receive_reveal",
            {"step": step, "role": "cop", "move": "E", "hint": "past the bridge"},
        )
        assert reply == {"received": True, "step": step}

    assert sorted(thief_peer.reveals) == [0, 1]
    assert thief_peer.reveals[1].hint == "past the bridge"


async def test_geometry_survives_the_encoding(cop_to_thief: OpponentClient, thief_peer) -> None:
    """A cell must arrive as the same cell. JSON has no tuple (C-010)."""
    await cop_to_thief.call("receive_commit", {"step": 0, "role": "cop", "digest": "d"})
    await cop_to_thief.call(
        "receive_reveal",
        {"step": 0, "role": "cop", "move": "STAY", "barrier_cell": [2, 3]},
    )
    assert thief_peer.reveals[0].barrier_cell == (2, 3)


async def test_a_barrier_declaration_arrives_with_its_exact_cell(
    cop_to_thief: OpponentClient, thief_peer: PeerRuntime
) -> None:
    """M#15, end to end."""
    reply = await cop_to_thief.call(
        "declare_barrier", {"step": 4, "role": "cop", "cell": [2, 3], "remaining": 13}
    )
    assert reply["cell"] == [2, 3]
    assert thief_peer.barriers[0].cell == (2, 3)


async def test_an_out_of_order_reveal_is_refused_across_the_wire(
    cop_to_thief: OpponentClient,
) -> None:
    """The ordering gate has to survive the transport, not just the unit test."""
    with pytest.raises(RemoteToolError, match="no matching commit"):
        await cop_to_thief.call("receive_reveal", {"step": 7, "role": "cop", "move": "N"})


async def test_a_reveal_carrying_a_nonce_is_refused_across_the_wire(
    cop_to_thief: OpponentClient,
) -> None:
    """M#18, proven at the boundary an opponent actually touches."""
    with pytest.raises(RemoteToolError, match="must not carry a nonce"):
        await cop_to_thief.call(
            "receive_reveal", {"step": 0, "role": "cop", "move": "N", "nonce": "leak"}
        )


async def test_a_handshake_mismatch_refuses_the_match_over_the_wire(minimal_config) -> None:
    """M#11: a digest mismatch must stop the match before the first move."""
    fresh = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.THIEF))
    server = create_server(build_server_spec(build_guarded_tools(fresh), "thief", 8082))
    client = OpponentClient(base_url="in-process", timeout_sec=5, transport=server)

    with pytest.raises(RemoteToolError, match="config digest mismatch"):
        await client.call("negotiate", {"step": 0, "role": "cop", "config_digest": "wrong"})
    assert not fresh.agreed


async def test_a_matching_handshake_opens_the_match(minimal_config) -> None:
    fresh = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.THIEF))
    server = create_server(build_server_spec(build_guarded_tools(fresh), "thief", 8082))
    client = OpponentClient(base_url="in-process", timeout_sec=5, transport=server)

    reply = await client.call(
        "negotiate",
        {"step": 0, "role": "cop", "config_digest": minimal_config.shared_digest()},
    )
    assert reply["kind"] == "negotiation"
    assert fresh.agreed


async def test_a_failure_from_the_real_transport_arrives_typed(
    cop_to_thief: OpponentClient,
) -> None:
    """The classification path, exercised through the genuine client.

    Calling a tool the opponent does not expose is the cheapest real failure to
    produce, and it must arrive as a ``PeerError`` rather than whatever FastMCP
    happened to raise — the runtime catches our types, not theirs.
    """
    with pytest.raises(PeerError):
        await cop_to_thief.call("no_such_tool", {"step": 0, "role": "cop"})


async def test_every_registered_tool_is_reachable(cop_to_thief: OpponentClient) -> None:
    """Registration is the thing this layer decides; confirm it actually took."""
    from fastmcp import Client

    async with Client(cop_to_thief.target) as session:
        names = {tool.name for tool in await session.list_tools()}
    assert names == {
        "receive_commit",
        "receive_reveal",
        "final_reveal",
        "capture_claim",
        "declare_barrier",
        "negotiate",
    }
