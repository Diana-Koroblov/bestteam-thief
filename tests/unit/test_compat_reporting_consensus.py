"""Unit tests for the end-of-series consensus exchange in `core/compat/reporting.py`.

Split from `test_compat_reporting.py` under the 150-line ceiling (ADR-005):
that file covers filing/gating decisions with no opponent client at all, this
covers the one path that pushes and reads something over the wire.
"""

from __future__ import annotations

import argparse
import queue
from pathlib import Path

import pytest

from core.compat.reporting import send_league_report
from core.protocol.schemas import Role
from tests.unit.test_compat_reporting import _config, _row, _StubSDK


class _FakeOpponent:
    """Records what we pushed, so a test can inspect the envelope itself."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def call(self, tool: str, message: dict, argument: str = "") -> dict:
        self.calls.append((tool, message))
        return {"ok": True}


class _StubSDKWithOpponent(_StubSDK):
    def __init__(self, config, role: Role) -> None:
        super().__init__(config)
        self.opponent = _FakeOpponent()
        self.role = role


def _inboxes(peer_sha: str = "") -> object:
    inboxes = argparse.Namespace(consensus=queue.Queue())
    if peer_sha:
        inboxes.consensus.put({"consensus_sha": peer_sha})
    return inboxes


async def test_a_complete_series_pushes_its_consensus_and_matches_an_identical_reply(
    tmp_path: Path,
) -> None:
    """yanell11, 22/08: the envelope must actually go out over `submit_audit`,
    shaped exactly as their spec reads it, and a later identical reply from
    the peer must read back as a match rather than silence."""
    args = argparse.Namespace(out=tmp_path, counted=False, report_to="", opponent="")
    rows = [_row(n, verified=True) for n in range(1, 7)]
    sdk = _StubSDKWithOpponent(_config(), Role.THIEF)

    mismatched = await send_league_report(
        sdk, args, rows, {}, {}, "imreeyal", _inboxes(peer_sha="0" * 64)
    )
    assert "MISMATCH" in mismatched
    tool, pushed = sdk.opponent.calls[0]
    assert tool == "submit_audit"
    assert pushed == {
        "sender": "thief", "records": [], "result_claim": "series_consensus",
        "consensus_sha": pushed["consensus_sha"],
    }

    matching = await send_league_report(
        _StubSDKWithOpponent(_config(), Role.THIEF), args, rows, {}, {}, "imreeyal",
        _inboxes(peer_sha=pushed["consensus_sha"]),
    )
    assert "MATCH" in matching and "MISMATCH" not in matching


async def test_a_complete_series_reports_no_peer_consensus_received(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A peer that never implemented this must read as absence, not a fault."""
    monkeypatch.setattr("core.compat.reporting.CONSENSUS_WAIT_SECONDS", 0.05)
    args = argparse.Namespace(out=tmp_path, counted=False, report_to="", opponent="")
    rows = [_row(n, verified=True) for n in range(1, 7)]
    sdk = _StubSDKWithOpponent(_config(), Role.COP)

    message = await send_league_report(sdk, args, rows, {}, {}, "imreeyal", _inboxes())

    assert "peer consensus  : not received" in message
