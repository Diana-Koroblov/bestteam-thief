"""One factory per MCP tool. Adding a tool is one factory plus one registration.

The pattern exists so the transport never learns the rules. Each factory takes
a handler — an object that knows what a message *means* — and returns a plain
callable that FastMCP can register. Nothing here imports FastMCP, so the whole
protocol layer is testable without a server, a socket or an event loop.

Every tool validates before it delegates. A malformed payload from an opponent
must produce a named, quotable error rather than a stack trace: with no referee,
"your step 7 commit arrived with no digest" is the entire remedy available to
us, and it has to be sayable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from core.protocol.schemas import (
    Ack,
    BarrierDeclaration,
    CaptureClaim,
    CaptureResponse,
    Commit,
    FinalReveal,
    MessageKind,
    Negotiation,
    Reveal,
    Role,
)

__all__ = ["ProtocolError", "PeerHandler", "TOOL_BUILDERS", "build_tools"]


class ProtocolError(ValueError):
    """A message was malformed, out of order, or from the wrong role.

    Deliberately distinct from a transport failure. A dropped connection is bad
    luck; a malformed payload is the opponent's bug or the opponent's attempt,
    and the two call for different responses.
    """


class PeerHandler(Protocol):
    """What the runtime must provide for these tools to mean anything.

    A Protocol rather than a base class: the tools depend on the shape, not the
    identity, so tests can pass a recorder and the runtime can pass itself.
    """

    def on_commit(self, message: Commit) -> Ack: ...
    def on_reveal(self, message: Reveal) -> None: ...
    def on_final_reveal(self, message: FinalReveal) -> None: ...
    def on_capture_claim(self, message: CaptureClaim) -> CaptureResponse: ...
    def on_barrier(self, message: BarrierDeclaration) -> None: ...
    def on_negotiate(self, message: Negotiation) -> Negotiation: ...


def _require(payload: dict[str, Any], *names: str) -> None:
    """Raise ``ProtocolError`` naming every field that is missing or empty."""
    missing = [name for name in names if payload.get(name) in (None, "")]
    if missing:
        raise ProtocolError(f"missing required field(s): {', '.join(missing)}")


def _common(payload: dict[str, Any], kind: MessageKind) -> tuple[int, Role]:
    """Validate and return the ``step`` and ``role`` every message carries."""
    if payload.get("kind") not in (None, kind.value):
        raise ProtocolError(f"expected a {kind.value} payload, got {payload.get('kind')!r}")
    step = payload.get("step")
    if not isinstance(step, int) or step < 0:
        raise ProtocolError(f"step must be a non-negative integer, got {step!r}")
    try:
        return step, Role(payload.get("role"))
    except ValueError:
        raise ProtocolError(f"unknown role {payload.get('role')!r}") from None


def _commit_tool(handler: PeerHandler) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Receive a sealed move. Stores the digest and locks us in too."""

    def receive_commit(payload: dict[str, Any]) -> dict[str, Any]:
        step, role = _common(payload, MessageKind.COMMIT)
        _require(payload, "digest")
        return handler.on_commit(Commit(step=step, role=role, digest=payload["digest"])).payload()

    return receive_commit


def _reveal_tool(handler: PeerHandler) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Receive move, hint and intent. The nonce is **refused** here (M#18)."""

    def receive_reveal(payload: dict[str, Any]) -> dict[str, Any]:
        step, role = _common(payload, MessageKind.REVEAL)
        if "nonce" in payload:
            raise ProtocolError(
                "a reveal must not carry a nonce; nonces are released only in "
                "the final reveal at end of match (M#18)"
            )
        _require(payload, "move")
        cell = payload.get("barrier_cell")
        handler.on_reveal(
            Reveal(
                step=step,
                role=role,
                move=payload["move"],
                hint=payload.get("hint", ""),
                intent=payload.get("intent", "truth"),
                barrier_cell=tuple(cell) if cell else None,
            )
        )
        return {"received": True, "step": step}

    return receive_reveal


def _final_reveal_tool(handler: PeerHandler) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Receive every nonce, once, at end of match."""

    def final_reveal(payload: dict[str, Any]) -> dict[str, Any]:
        step, role = _common(payload, MessageKind.FINAL_REVEAL)
        nonces = payload.get("nonces")
        if not isinstance(nonces, dict) or not nonces:
            raise ProtocolError("final_reveal requires a non-empty mapping of step to nonce")
        handler.on_final_reveal(FinalReveal(step=step, role=role, nonces=nonces))
        return {"received": True, "count": len(nonces)}

    return final_reveal


def _capture_tool(handler: PeerHandler) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Answer a capture claim. M#21 obliges the answer to be truthful."""

    def capture_claim(payload: dict[str, Any]) -> dict[str, Any]:
        step, role = _common(payload, MessageKind.CAPTURE_CLAIM)
        cell = payload.get("cell")
        if not (isinstance(cell, (list, tuple)) and len(cell) == 2):
            raise ProtocolError(f"capture_claim needs a [row, col] cell, got {cell!r}")
        claim = CaptureClaim(step=step, role=role, cell=tuple(cell), rule=payload.get("rule", ""))
        return handler.on_capture_claim(claim).payload()

    return capture_claim


def _barrier_tool(handler: PeerHandler) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Receive an open barrier declaration with its exact cell (M#15)."""

    def declare_barrier(payload: dict[str, Any]) -> dict[str, Any]:
        step, role = _common(payload, MessageKind.BARRIER_DECLARATION)
        cell = payload.get("cell")
        if not (isinstance(cell, (list, tuple)) and len(cell) == 2):
            raise ProtocolError(f"declare_barrier needs a [row, col] cell, got {cell!r}")
        handler.on_barrier(
            BarrierDeclaration(
                step=step, role=role, cell=tuple(cell), remaining=payload.get("remaining", 0)
            )
        )
        return {"received": True, "cell": list(cell)}

    return declare_barrier


def _negotiate_tool(handler: PeerHandler) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Exchange the pre-match handshake (M#37)."""

    def negotiate(payload: dict[str, Any]) -> dict[str, Any]:
        step, role = _common(payload, MessageKind.NEGOTIATION)
        _require(payload, "config_digest")
        proposal = Negotiation(
            step=step,
            role=role,
            config_digest=payload["config_digest"],
            scent_model_digest=payload.get("scent_model_digest", ""),
            game_count=payload.get("game_count", 0),
            role_split=payload.get("role_split", "3-3"),
            readings=payload.get("readings", {}),
        )
        return handler.on_negotiate(proposal).payload()

    return negotiate


TOOL_BUILDERS: dict[str, Callable[[PeerHandler], Callable[..., Any]]] = {
    "receive_commit": _commit_tool,
    "receive_reveal": _reveal_tool,
    "final_reveal": _final_reveal_tool,
    "capture_claim": _capture_tool,
    "declare_barrier": _barrier_tool,
    "negotiate": _negotiate_tool,
}


def build_tools(handler: PeerHandler) -> dict[str, Callable[..., Any]]:
    """Return every tool bound to *handler*, raw — errors still propagate."""
    return {name: builder(handler) for name, builder in TOOL_BUILDERS.items()}


def guard(name: str, tool: Callable[..., Any]) -> Callable[..., Any]:
    """Return *tool* with protocol errors turned into a structured reply.

    A ``ProtocolError`` is the opponent's malformed payload, not our crash. It
    comes back as data naming the problem, so they can fix it and our log
    records what we actually received. Letting it escape would give them a
    stack trace and us nothing.

    Lives here rather than in the transport so that the server can take plain
    callables and import nothing from this layer — the transport must never
    learn the rules (M#3).
    """

    def guarded(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return tool(payload)
        except ProtocolError as error:
            return {"error": "protocol", "tool": name, "detail": str(error)}

    guarded.__name__ = name
    guarded.__doc__ = tool.__doc__
    return guarded


def build_guarded_tools(handler: PeerHandler) -> dict[str, Callable[..., Any]]:
    """Return every tool bound to *handler* and safe to expose on a server."""
    return {name: guard(name, tool) for name, tool in build_tools(handler).items()}
