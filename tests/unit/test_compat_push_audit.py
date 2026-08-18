"""Unit tests for `core.compat.turn_wait.push_audit`.

Split from `test_turn_wait.py` under the 150-line ceiling (ADR-005): that file
covers the negotiate/agreement wait, this covers the closing audit push — two
different functions in one module, sharing only the `_Client` test double.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Client:
    """Counts pushes so a test can prove we re-sent."""

    pushes: list = field(default_factory=list)

    async def call(self, tool: str, message: dict, argument: str = "") -> dict:
        self.pushes.append((tool, message.get("sub_game_number")))
        return {"ok": True}


async def test_push_audit_lands_on_the_first_try() -> None:
    """The ordinary case: their door is still the one we last talked to."""
    from core.compat.turn_wait import push_audit

    client = _Client()
    landed, notes = await push_audit(client, {"sub_game_number": 1}, redial=None)

    assert landed
    assert notes == []
    assert client.pushes == [("submit_audit", 1)]


async def test_push_audit_redials_a_dead_socket_instead_of_giving_up() -> None:
    """🐛 **What najamjad actually hit, 17/08.** The peer that just won can exit
    the moment it has read its inbox, killing its server mid-response — so the
    client the last turn left us with is routinely a corpse by the time we
    reach the audit push. Silently swallowing that failure (the old code) reads
    on their side as "AUDIT SKIPPED" while our own log shows nothing wrong."""
    from core.compat.turn_wait import push_audit
    from core.infra.errors import PeerError

    class _Dead:
        async def call(self, *_args: Any, **_kwargs: Any) -> dict:
            raise PeerError("session terminated")

    live = _Client()

    async def redial() -> Any:
        return live

    landed, notes = await push_audit(_Dead(), {"sub_game_number": 1}, redial=redial)

    assert landed
    assert "attempt 1 failed" in notes[0]
    assert live.pushes == [("submit_audit", 1)]


async def test_push_audit_reports_when_it_never_lands() -> None:
    """Both attempts fail: the caller must be told, not left to assume silence
    means success — that assumption is the whole bug this function replaces."""
    from core.compat.turn_wait import push_audit
    from core.infra.errors import PeerError

    class _AlwaysDead:
        async def call(self, *_args: Any, **_kwargs: Any) -> dict:
            raise PeerError("session terminated")

    async def redial() -> Any:
        return _AlwaysDead()

    landed, notes = await push_audit(_AlwaysDead(), {"sub_game_number": 1}, redial=redial)

    assert not landed
    assert "never landed" in notes[-1]
