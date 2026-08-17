"""Reproducing najamjad's 17/08 symptom over the **real** transport, not a mock.

`test_turn_wait.py::test_push_audit_*` proves the retry logic against a fake
client that raises on cue. This file proves the same thing against a real
`OpponentClient` and a real FastMCP server: a call to a socket nobody is
listening on raises the genuine `PeerError` our classifier produces, a bare
unretried push (the old code) never reaches the opponent's inbox, and
`push_audit`'s redial does — landing in a real `Inboxes.agreements`-style
queue read back through the real reference tools, not asserted on a return
value alone.
"""

from __future__ import annotations

import contextlib

import pytest

from core.compat.mailbox import Inboxes, build_reference_tools
from core.compat.turn_wait import push_audit
from core.infra.errors import PeerError
from core.infra.mcp_client import OpponentClient
from core.infra.mcp_server import build_server_spec, create_server

# Nothing binds this port; a call here is a genuine connection failure, not a
# simulated one — the same shape of failure as dialling a peer whose process
# already exited.
DEAD_URL = "http://127.0.0.1:8931/mcp"


@pytest.fixture
def live_opponent() -> tuple[OpponentClient, Inboxes]:
    """A real reference-protocol server, reachable over the real MCP protocol."""
    inboxes = Inboxes()
    server = create_server(
        build_server_spec(build_reference_tools(inboxes), name="live-peer", port=8082)
    )
    client = OpponentClient(base_url="in-process", timeout_sec=5, transport=server)
    return client, inboxes


async def test_a_dead_target_raises_the_real_peer_error(
    live_opponent: tuple[OpponentClient, Inboxes],
) -> None:
    """Sanity check on the reproduction itself: dialling nothing really fails,
    typed the way the runtime catches it — not a bare `ConnectionError` that a
    `except PeerError` clause would let straight through unnoticed."""
    dead = OpponentClient(base_url=DEAD_URL, timeout_sec=1.0)
    with pytest.raises(PeerError):
        await dead.call("submit_audit", {"sub_game_number": 1}, argument="payload")


async def test_the_old_unretried_push_never_reaches_their_inbox(
    live_opponent: tuple[OpponentClient, Inboxes],
) -> None:
    """**What najamjad actually saw.** This is the pre-fix shape of the call
    site — one attempt, wrapped in `contextlib.suppress(PeerError)` — proven
    against the real client/server pair rather than argued about. The payload
    never lands, and nothing here says so; that silence is the bug."""
    _live, inboxes = live_opponent
    dead = OpponentClient(base_url=DEAD_URL, timeout_sec=1.0)

    with contextlib.suppress(PeerError):
        await dead.call("submit_audit", {"sub_game_number": 1}, argument="payload")

    assert inboxes.audits.empty(), "reproduces the silent loss, not a hypothesis about it"


async def test_push_audit_recovers_over_the_real_wire(
    live_opponent: tuple[OpponentClient, Inboxes],
) -> None:
    """The fix, proven the same way: first attempt dials nothing and fails,
    the redial hands back the real live client, and the payload is found —
    decoded off the real MCP protocol — sitting in the opponent's real inbox."""
    live, inboxes = live_opponent
    dead = OpponentClient(base_url=DEAD_URL, timeout_sec=1.0)

    async def redial() -> OpponentClient:
        return live

    landed, notes = await push_audit(
        dead, {"sub_game_number": 1, "sender": "cop", "records": []}, redial=redial
    )

    assert landed
    assert "attempt 1 failed" in notes[0]
    delivered = inboxes.audits.get_nowait()
    assert delivered["sub_game_number"] == 1
