"""One sub-game against a peer that speaks the reference protocol.

The shape of a turn here is the opposite of ours. Nothing is answered: we push
a message, and the reply — whenever it comes — arrives as a fresh inbound call
into an inbox. So every wait in this file is a bounded poll against a mailbox. A
peer that blocks forever on a message that will never come takes the opponent
down with it, and a match with no result scores 0 for both sides (M#35).

**The thief opens.** There is no separate "your move" signal: receiving a turn
message *is* the turn token, so somebody must send the first one unprompted, and
the reference makes that the thief. Two peers that both wait, or both open, is a
sub-game nobody plays.
"""

from __future__ import annotations

import asyncio
import queue
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.compat import league_report, sealing
from core.compat.mailbox import Inboxes
from core.compat.pairing import HandshakeError
from core.compat.turn_wait import collect_our_agreement
from core.compat.turns import read_turn, send_turn
from core.compat.wire import (
    INFO_MODE_SHA256,
    SCENT_MODEL_SHA256,
    WIRE_SHAPE_SHA256,
    AuditPayload,
    TurnMessage,
    terms_from_config,
    wire_role,
)
from core.protocol.schemas import Role

__all__ = ["ReferenceSession", "HandshakeError", "reconnect"]

# How long to yield between mailbox polls. Long enough not to spin a core, short
# enough to be invisible inside a 30 s response budget.
POLL_SECONDS = 0.05

# Strictly under the signed `response_timeout_sec` (30s), not equal to it: the
# MCP SDK's own per-call default is 30s, so one delivered-but-unanswered push
# plus a 0.5s retry sleep can breach a 30s deadline while every individual call
# still looks fine on its own (imreeyal §3.5 — our scar too, not just theirs).
CALL_TIMEOUT_SEC = 10.0


async def reconnect(sdk: Any, url: str) -> None:
    """Drop the outbound session and dial again, fresh, for the next sub-game.

    Not a formality: their runner starts a new process per sub-game, so a
    client holding last sub-game's socket dials a corpse in this one — every
    call times out while a fresh connection to the same URL reads healthy
    (imreeyal §3.4). Six reconnects a match is nothing next to the
    per-*message* reconnection `OpponentClient` was rewritten to stop doing
    (`core/infra/mcp_client.py`) — six sockets, not six hundred.

    `OpponentClient` is frozen, so the capped timeout has to be set at
    construction — `disconnect()` first, since `connect()` refuses a second
    opponent even when the slot holds a stale one of our own making (M#4).
    """
    if sdk.opponent is not None:
        await sdk.opponent.aclose()
        sdk.disconnect()
    signed = float(sdk.runtime.orchestrator.config.require("network_and_league.response_timeout_sec"))
    sdk.connect(url, timeout_sec=min(signed, CALL_TIMEOUT_SEC))


@dataclass
class ReferenceSession:
    """Drives this peer through one sub-game of the reference protocol.

    Attributes:
        runtime: Our own `PeerRuntime`. The brain, the belief filter and the
            board all come from it unchanged — only the wire is different.
        client: The single opponent (M#4).
        inboxes: Where their pushes land.
        records: Our sealed steps, revealed together in the closing audit.
    """

    runtime: Any
    client: Any
    inboxes: Inboxes
    identity: dict = field(default_factory=dict)
    sub_game_number: int = 0
    result: str = ""
    winner: str = ""
    records: list[dict] = field(default_factory=list)
    # What actually arrived, keyed by their step number — for binding a
    # closing audit record to the commit that was really sent (imreeyal §3.10).
    received: dict[int, str] = field(default_factory=dict)
    # Our own per-sender step counter (imreeyal §3.6): incremented once per
    # outbound turn, independent of the shared game-progress counter.
    sent: int = 0
    # Handshake findings that log rather than refuse — a declared scent-model
    # divergence is the pairing working as agreed, not a fault (3.12 fallback).
    warnings: list = field(default_factory=list)

    @property
    def role(self) -> Role:
        """Which side we play this sub-game."""
        return self.runtime.own_role

    @property
    def orchestrator(self) -> Any:
        """The only thing permitted to change the board."""
        return self.runtime.orchestrator

    @property
    def state(self) -> Any:
        """The board as we hold it — our own half of it, at least."""
        return self.orchestrator.state

    @property
    def config(self) -> Any:
        """The negotiated configuration."""
        return self.orchestrator.config

    def agreement_message(self) -> tuple[dict, dict]:
        """Return what we send, and the terms we are signing.

        Sending it is the gateway's job. A peer that has not started yet is a
        transport failure to retry, not a disagreement about the game, and
        deciding which is which means knowing the transport's exception types —
        which this layer must not import (M#3).

        ``game_uid`` is derived here rather than trusted from anywhere on the
        wire — it never crosses it (WARNINGS §2) — from the flat terms and the
        two group ids. Ours is read from ``identity``; theirs from
        ``agreed_between`` in the shared config, which already has to name
        them for the constitution to be byte-identical. Empty when the second
        name is not yet known, rather than raising: a peer mid-rehearsal with
        only its own team in ``agreed_between`` should still be able to print
        what it would send.
        """
        terms = terms_from_config(self.config)
        nonce = secrets.token_hex(16)
        ours_id = str(self.identity.get("group_id", ""))
        theirs_id = next((name for name in self.config.agreed_between if name != ours_id), "")
        uid = league_report.game_uid(terms, ours_id, theirs_id) if theirs_id else ""
        model = str(self.config.get("pheromones.decay_model", "multiplicative"))
        return {
            "terms": terms,
            "nonce": nonce,
            "signature": sealing.commit_of(terms, nonce),
            "identity": dict(self.identity),
            "sub_game_number": self.sub_game_number,
            "role": wire_role(self.role.value),
            "wire_shape_sha256": WIRE_SHAPE_SHA256,
            "info_mode_sha256": INFO_MODE_SHA256,
            "scent_model_sha256": SCENT_MODEL_SHA256.get(model, ""),
            "game_uid": uid,
        }, terms

    async def collect_agreement(self, wait: float, ours: dict) -> dict:
        """Wait for their signed agreement and verify it against *ours*.

        Args:
            wait: Seconds to poll the inbox before giving up.
            ours: The full agreement MESSAGE we sent, not the bare terms — the
                pairing guard reads `sub_game_number`, `role` and the model
                hashes off it, and handing it only the terms leaves our side of
                every one of those checks permanently silent (see
                `core/compat/pairing.py` for the live bug that was).

        Both peers push and both then read their own inbox, so the exchange is
        symmetric and neither side is the server. A refusal is the correct
        outcome: two peers enforcing different physics produce an audit that
        reports forgery against two honest teams (M#11).

        The skipping of agreements stamped for a **different** sub-game lives in
        `core/compat/turn_wait.py`, with the waiting it exists to serve; see
        that module for why an alternating split makes it necessary.
        """
        return await collect_our_agreement(self, wait, ours)

    async def play_sub_game(self, on_turn: Callable[[str], None] | None = None) -> str:
        """Play to a verdict and return it. Never raises on their failure.

        ``on_turn`` fires once per message received. This protocol has no
        synchronous "your move" to display — without a hook, a sub-game is
        silent from handshake to verdict, and all a caller's terminal shows
        is the transport underneath it. A hook rather than a `print` here:
        this module is the mechanics, the CLI decides what a human sees (M#3).
        """
        if self.role is Role.THIEF:
            await send_turn(self, None)
            if self._survived():
                return self._end("survival", Role.THIEF.value)
        # Private, and it has to be. How long WE are willing to wait for their
        # first turn is a fact about our patience, not a term either side
        # agreed: raising the signed `watchdog_timeout_sec` to buy it edited the
        # negotiated constitution and moved `config_sha256` out from under an
        # opponent who had pinned it — caught by imreeyal on 16/08, and rightly.
        # Waiting longer than the signed watchdog only ever costs us time, so
        # the local key may exceed it; it may never shorten it below what the
        # agreement allows, which is why the signed value is the floor here.
        signed = float(self.config.get("network_and_league.watchdog_timeout_sec", 60))
        patience = max(signed, float(self.config.get("network.sub_game_patience_sec", 0) or 0))
        while not self.result:
            arrived = await self._collect(self.inboxes.turns, patience)
            if arrived is None:
                return self._end("timeout", self.role.value)
            try:
                message = TurnMessage.from_dict(arrived)
                outcome = read_turn(self, message)
            except (ValueError, TypeError, KeyError) as error:
                return self._end("timeout", self.role.value, str(error))
            if on_turn is not None:
                on_turn(f"{self.state.step:>3}  {message.sender:<5} {message.hint or '-'}")
            if outcome.we_won:
                return self._end("capture", Role.COP.value)
            if outcome.they_won:
                return self._end(outcome.win_type or "survival", Role.THIEF.value)
            # The answer we owe rides out on our own next turn, even when it is
            # the admission that they caught us: M#21 makes it a duty, and a
            # peer that fell silent on being caught would look like one that
            # dropped rather than one that lost.
            await send_turn(self, outcome.claim_response)
            if outcome.we_are_caught:
                return self._end("capture", Role.COP.value)
            if self._survived():
                # Our own claim just rode out on that turn (`turns._win`). A
                # claimant that kept waiting for an answer watchdogs into
                # "timeout" while the opponent files "survival" — the same
                # sub-game reported two ways, which is the exact contradiction
                # M#35 scores 0-0. Found live in the 14/08 boundary drill: our
                # thief had never actually reached survival on this path.
                return self._end("survival", Role.THIEF.value)
        return self.result

    def _survived(self) -> bool:
        """Whether the survival threshold is reached and we are the thief."""
        threshold = int(self.config.require("movement_and_barriers.survival_threshold"))
        return self.role is Role.THIEF and int(self.state.step) >= threshold

    def audit_payload(self) -> dict:
        """Return our own records, for the gateway to push at end of match.

        Carries ``sub_game_number`` beside the reference's own keys — additive,
        and every conformant peer drops unknown keys. It is what lets a
        receiver tell a late audit from the right one; see `collect_audit`.
        """
        payload = AuditPayload(
            sender=self.role.value,
            records=self.records,
            result_claim=self.result or "timeout",
        ).to_dict()
        payload["sub_game_number"] = self.sub_game_number
        return payload

    async def collect_audit(self, wait: float) -> dict:
        """Wait for their reveal and re-verify every record in it.

        An audit stamped with an EARLIER sub-game's number is skipped, not
        judged: a slow peer's closing push can land after our boundary drain,
        and verifying it against this sub-game's live commits reports forgery
        against an honest opponent (14/08 drill, sub-games 3 and 5). An
        unstamped audit — any unmodified reference peer — is consumed as-is.

        Separate from sending ours because *sending* is best-effort against a
        peer that may already have exited, and deciding what counts as a
        tolerable transport failure is the gateway's business, not this file's
        (M#3). Ours may have landed even when the call raised, and theirs may
        already be sitting in our inbox either way — so this runs regardless.
        """
        deadline = time.monotonic() + wait
        while True:
            theirs = await self._collect(self.inboxes.audits, deadline - time.monotonic())
            if theirs is None:
                return {"passed": False, "verified_steps": 0, "failed_steps": [],
                        "received": False}
            stamped = theirs.get("sub_game_number")
            if isinstance(stamped, int) and self.sub_game_number and stamped != self.sub_game_number:
                continue
            verdict = sealing.audit_records(
                AuditPayload.from_dict(theirs).records, live=self.received
            )
            return {**verdict, "received": True}

    async def _collect(self, inbox: queue.Queue, seconds: float) -> dict | None:
        """Wait up to *seconds* for one message. ``None`` means it never came."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                return inbox.get_nowait()
            except queue.Empty:
                await asyncio.sleep(POLL_SECONDS)
        return None

    def _end(self, result: str, winner: str, detail: str = "") -> str:
        """Record the verdict, keeping the first one that arrived."""
        if not self.result:
            self.result = f"{result} ({detail})" if detail else result
            self.winner = winner
        return self.result
