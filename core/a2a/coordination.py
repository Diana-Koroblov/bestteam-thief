"""Answering one inbound A2A message: are you up, and under what terms.

Deliberately dull. There is one question worth asking before a match and this
answers it in both envelopes anyone has sent us — the REST form nis-yar1's note
documents (`{"message": ...}`) and the JSON-RPC form the specification uses
(`{"method": "message/send", "params": {...}}`) — replying in whichever arrived.
Insisting on our reading of an ambiguous spec would be technically defensible
and would still leave us unable to talk to them.

**A game message is refused here, not absorbed.** A commit that never went
through the MCP tool was never sealed and has no line in the log, so no replay
could verify the sub-game it belonged to (M#18, M#20). Being told "send that
through MCP" costs seconds; discovering after a series that half of it happened
off the record costs the series.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from core.a2a.card import agent_card
from core.a2a.readiness import Readiness, match_facts

__all__ = ["Coordination", "GAME_WORDS"]

# Words that mean a game message. A peer sending one of these over A2A is out of
# contract, and saying so beats accepting it.
GAME_WORDS = (
    "receive_commit",
    "receive_reveal",
    "final_reveal",
    "declare_barrier",
    "capture_claim",
    "digest",
    "nonce",
)


@dataclass(frozen=True)
class Coordination:
    """Answers the two A2A requests as plain dictionaries.

    No Starlette, no FastMCP, no clock beyond a UUID: every method is a pure
    function of *readiness* and the request, so the whole surface is assertable
    in a unit test without opening a port.
    """

    readiness: Readiness

    def card(self, base_url: str) -> dict[str, Any]:
        """Return the Agent Card for a `GET` that arrived on *base_url*."""
        return agent_card(self.readiness, base_url)

    def match_facts(self, base_url: str) -> dict[str, Any]:
        """Return the machine-readable facts, as published in the card."""
        return match_facts(self.readiness, base_url)

    def answer(self, base_url: str, payload: dict[str, Any] | None) -> tuple[int, dict[str, Any]]:
        """Return `(status, body)` for one inbound A2A message."""
        if not isinstance(payload, dict):
            return 400, _error("a2a message body must be a JSON object")
        inbound = _message_of(payload)
        if inbound is None:
            return 400, _error("no message found: expected message.parts[].text")

        text = _text_of(inbound)
        message = self._reply(base_url, text, _game_words(text))
        if payload.get("jsonrpc"):
            return 200, {"jsonrpc": "2.0", "id": payload.get("id"), "result": message}
        return 200, message

    def _reply(self, base_url: str, text: str, smuggled: tuple[str, ...]) -> dict[str, Any]:
        """Build the A2A message we send back, refusal included if earned."""
        facts = self.match_facts(base_url)
        facts["accepted"] = not smuggled
        if smuggled:
            facts["refused"] = (
                f"message mentions {', '.join(smuggled)} - send that through MCP, not A2A"
            )
        return {
            "kind": "message",
            "messageId": uuid.uuid4().hex,
            "role": "ROLE_AGENT",
            "parts": [{"text": self._text(facts, smuggled)}, {"data": facts}],
            "metadata": {"echo": text[:200]} if text else {},
        }

    def _text(self, facts: dict[str, Any], smuggled: tuple[str, ...]) -> str:
        """Render the human half of the reply — what a person reads in a terminal.

        Both halves of every answer, always. A structured `data` part is what
        their probe parses; this is what a human pastes into the chat where the
        match is being arranged, and an endpoint that returned only one of the
        two would be useless to one of the two readers.
        """
        ready = self.readiness
        clock = facts["timeouts"]
        lines = [
            f"{ready.team_name} / {ready.contact_label} ({ready.role}) is up.",
            f"1. Agent Card : {facts['agentCardUrl']}",
            f"2. A2A message: {facts['a2aMessageUrl']}",
            f"3. MCP game   : {facts['mcpUrl']}",
            f"   MCP tools  : {', '.join(facts['mcpTools'])}",
            "4. Yes - our runner sends receive_commit for step 0 immediately after "
            "negotiation, without waiting for yours. Both sides push every step.",
            f"5. Timeouts: {clock['responseTimeoutSec']:.0f}s per message at EVERY step, "
            f"{clock['attempts']} attempts, so {clock['patienceBeforeTechnicalLossSec']:.0f}s "
            f"before a technical loss; watchdog {clock['watchdogTimeoutSec']:.0f}s. "
            "We do NOT implement 60s at step 0 and 10s later - 10s is not in the "
            "game.json we both hashed, and a value that tight would fail honest turns.",
            f"config_sha256: {facts['configSha256'] or '(unset)'} - compare with yours.",
            "A2A here is readiness and debugging only. Commits, reveals, barriers and "
            "capture claims go through MCP.",
        ]
        if smuggled:
            lines.append(f"REFUSED: {facts['refused']}")
        return "\n".join(lines)


def _message_of(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Dig the message out of either envelope, or None if there is none."""
    params = payload.get("params")
    if isinstance(params, dict) and isinstance(params.get("message"), dict):
        return params["message"]
    if isinstance(payload.get("message"), dict):
        return payload["message"]
    # A bare message, sent with no envelope at all. Liberal on purpose.
    return payload if isinstance(payload.get("parts"), list) else None


def _text_of(message: dict[str, Any]) -> str:
    """Concatenate every text part. Unknown part shapes are skipped, not fatal."""
    parts = message.get("parts")
    if not isinstance(parts, list):
        return ""
    return "\n".join(
        part["text"]
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    )


def _game_words(text: str) -> tuple[str, ...]:
    """Return the game-protocol words this message contains, if any."""
    lowered = text.lower()
    return tuple(word for word in GAME_WORDS if word in lowered)


def _error(reason: str) -> dict[str, Any]:
    """Return a body that says what was wrong with the request, quotably."""
    return {"error": {"code": "invalid_request", "message": reason}}
