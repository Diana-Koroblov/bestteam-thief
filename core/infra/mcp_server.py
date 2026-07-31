"""The FastMCP server this peer exposes to exactly one opponent.

Thin on purpose. Everything it serves comes from ``core.protocol.tools``, which
knows nothing about FastMCP — so the rules are testable without a socket, and
this file only has to be right about *registration*, not about the game.

**Binds 0.0.0.0, not 127.0.0.1.** A tunnel forwards to the host interface, so a
server bound to loopback is reachable from the same machine and from nowhere
else. That failure appears only when a real opponent connects, which is the
worst moment to find it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core.protocol.tools import PeerHandler, ProtocolError, build_tools

__all__ = ["ServerSpec", "build_server_spec", "create_server"]

# Every interface, so an ngrok tunnel can reach us. See the module docstring.
LISTEN_HOST = "0.0.0.0"  # noqa: S104 - deliberate, and explained above


@dataclass(frozen=True)
class ServerSpec:
    """Everything needed to stand a server up, decided before one exists.

    Separated from the server itself so the wiring can be unit-tested: the tool
    set, the bind address and the names are all assertable without importing
    FastMCP or opening a port.

    Attributes:
        name: Identifies this peer in MCP metadata.
        host: Bind address. Always ``0.0.0.0`` in play.
        port: Local port; the tunnel maps a public name onto it.
        tools: Tool name to callable, already bound to the handler.
    """

    name: str
    host: str
    port: int
    tools: dict[str, Callable[..., Any]]

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Return the registered tool names, sorted for stable comparison."""
        return tuple(sorted(self.tools))


def build_server_spec(handler: PeerHandler, name: str, port: int) -> ServerSpec:
    """Return the full server definition for *handler*, without starting one."""
    return ServerSpec(name=name, host=LISTEN_HOST, port=port, tools=build_tools(handler))


def _wrap(name: str, tool: Callable[..., Any]) -> Callable[..., Any]:
    """Return *tool* with protocol errors turned into a structured reply.

    A ``ProtocolError`` is the opponent's malformed payload, not our crash. It
    comes back as data naming the problem, so they can fix it and so our log
    records what we actually received. Letting it escape as a traceback would
    give them a stack trace and us nothing.
    """

    def guarded(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return tool(payload)
        except ProtocolError as error:
            return {"error": "protocol", "tool": name, "detail": str(error)}

    guarded.__name__ = name
    guarded.__doc__ = tool.__doc__
    return guarded


def create_server(spec: ServerSpec):  # pragma: no cover - needs a live FastMCP
    """Register every tool on a FastMCP instance and return it.

    Imported lazily so the protocol layer, and every test above, stays free of a
    FastMCP dependency. Excluded from coverage because exercising it means
    standing up a real server; ``build_server_spec`` carries the logic that can
    be tested, and the localhost round-trip test (2.4.2) covers the rest.
    """
    from fastmcp import FastMCP

    server = FastMCP(spec.name)
    for name, tool in spec.tools.items():
        server.add_tool(_wrap(name, tool), name=name)
    return server
