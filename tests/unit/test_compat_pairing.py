"""Unit tests for core/compat/pairing.py — the locked-model hash policy and
the collect-agreement bug its extraction fixed (imreeyal 3.12 fallback).
"""

from __future__ import annotations

import pytest

from core.compat.mailbox import Inboxes
from core.compat.pairing import HandshakeError, pairing_warnings
from core.compat.session import ReferenceSession
from core.protocol.schemas import Role
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from core.shared.config_manager import Config

WIRE = "2" * 64
OTHER = "f" * 64


def test_a_wire_shape_differ_refuses() -> None:
    with pytest.raises(HandshakeError, match="wire_shape"):
        pairing_warnings({"wire_shape_sha256": WIRE}, {"wire_shape_sha256": OTHER})


def test_an_info_mode_differ_refuses() -> None:
    with pytest.raises(HandshakeError, match="info_mode"):
        pairing_warnings({"info_mode_sha256": WIRE}, {"info_mode_sha256": OTHER})


def test_a_scent_model_differ_logs_instead_of_refusing() -> None:
    """The 3.12 fallback: one declared form per side is the agreement WORKING.
    imreeyal's own scent check logs rather than refuses, and so must ours."""
    warnings = pairing_warnings(
        {"scent_model_sha256": WIRE}, {"scent_model_sha256": OTHER}
    )
    assert len(warnings) == 1
    assert "scent_model" in warnings[0]
    assert "logged" in warnings[0]


def test_matching_hashes_neither_refuse_nor_warn() -> None:
    declared = {"wire_shape_sha256": WIRE, "scent_model_sha256": WIRE}
    assert pairing_warnings(declared, dict(declared)) == []


def test_a_hash_omitted_by_either_side_never_refuses() -> None:
    assert pairing_warnings({"wire_shape_sha256": WIRE}, {}) == []
    assert pairing_warnings({}, {"scent_model_sha256": OTHER}) == []


async def test_collect_agreement_runs_the_pairing_guard_on_our_real_message(
    minimal_config: Config,
) -> None:
    """The guard used to receive the bare terms as ``ours``, so every check on
    our own declared fields read as omission and never fired — a live bug: our
    role-collision guard passed everything and only the opponent's ever caught
    one. This drives the real path with the real message and expects OUR side
    to refuse."""
    runtime = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.COP))
    runtime.agreed = True
    session = ReferenceSession(
        runtime=runtime, client=None, inboxes=Inboxes(),
        identity={"group_id": "bestteam"}, sub_game_number=1,
    )
    message, _ = session.agreement_message()
    echoed = dict(message)  # same role, same sub-game: a collision on both
    session.inboxes.agreements.put(echoed)
    with pytest.raises(HandshakeError, match="role collision"):
        await session.collect_agreement(1.0, message)
