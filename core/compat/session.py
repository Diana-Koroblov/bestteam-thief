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
from dataclasses import dataclass, field
from typing import Any

from core.compat import sealing
from core.compat.mailbox import Inboxes
from core.compat.turns import read_turn, send_turn
from core.compat.wire import AuditPayload, TurnMessage, terms_diff, terms_from_config
from core.protocol.schemas import Role

__all__ = ["ReferenceSession", "HandshakeError"]

# How long to yield between mailbox polls. Long enough not to spin a core, short
# enough to be invisible inside a 30 s response budget.
POLL_SECONDS = 0.05


class HandshakeError(RuntimeError):
    """The agreement did not settle, so no move may be sent."""


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
    result: str = ""
    winner: str = ""
    records: list[dict] = field(default_factory=list)

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
        """
        terms = terms_from_config(self.config)
        nonce = secrets.token_hex(16)
        return {
            "terms": terms,
            "nonce": nonce,
            "signature": sealing.commit_of(terms, nonce),
            "identity": dict(self.identity),
        }, terms

    async def collect_agreement(self, wait: float, ours: dict) -> dict:
        """Wait for their signed terms and verify them against *ours*.

        Both peers push and both then read their own inbox, so the exchange is
        symmetric and neither side is the server. A refusal is the correct
        outcome: two peers enforcing different physics produce an audit that
        reports forgery against two honest teams (M#11).
        """
        theirs = await self._collect(self.inboxes.agreements, wait)
        if theirs is None:
            raise HandshakeError("the opponent never sent its agreement")
        self._verify(ours, theirs)
        return theirs

    def _verify(self, ours: dict, theirs: dict) -> None:
        """Refuse unless they signed the very same terms we did."""
        differences = terms_diff(ours, dict(theirs.get("terms") or {}))
        if differences:
            raise HandshakeError("the agreed terms differ:\n  " + "\n  ".join(differences))
        if not sealing.verify(
            theirs["terms"], str(theirs.get("nonce", "")), str(theirs.get("signature", ""))
        ):
            raise HandshakeError("their signature does not cover the terms they sent")

    async def play_sub_game(self) -> str:
        """Play to a verdict and return it. Never raises on their failure."""
        if self.role is Role.THIEF:
            await send_turn(self, None)
        patience = float(self.config.get("network_and_league.watchdog_timeout_sec", 60))
        while not self.result:
            arrived = await self._collect(self.inboxes.turns, patience)
            if arrived is None:
                return self._end("timeout", self.role.value)
            try:
                outcome = read_turn(self, TurnMessage.from_dict(arrived))
            except (ValueError, TypeError, KeyError) as error:
                return self._end("timeout", self.role.value, str(error))
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
        return self.result

    def audit_payload(self) -> dict:
        """Return our own records, for the gateway to push at end of match."""
        return AuditPayload(
            sender=self.role.value,
            records=self.records,
            result_claim=self.result or "timeout",
        ).to_dict()

    async def collect_audit(self, wait: float) -> dict:
        """Wait for their reveal and re-verify every record in it.

        Separate from sending ours because *sending* is best-effort against a
        peer that may already have exited, and deciding what counts as a
        tolerable transport failure is the gateway's business, not this file's
        (M#3). Ours may have landed even when the call raised, and theirs may
        already be sitting in our inbox either way — so this runs regardless.
        """
        theirs = await self._collect(self.inboxes.audits, wait)
        if theirs is None:
            return {"passed": False, "verified_steps": 0, "failed_steps": [], "received": False}
        verdict = sealing.audit_records(AuditPayload.from_dict(theirs).records)
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
