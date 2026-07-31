"""The FastMCP server this peer exposes to exactly one opponent.

Thin on purpose, and **it imports nothing from the protocol layer**. It takes a
dictionary of ready-made callables and registers them. That is not a stylistic
choice: M#3 forbids peripheral subsystems from reaching sideways into one
another, and a transport that imported the protocol would be a transport that
knows the rules. Whoever builds the tools — the gateway — hands them over
already guarded.

**Binds 0.0.0.0, not 127.0.0.1.** A tunnel forwards to the host interface, so a
server bound to loopback is reachable from the same machine and from nowhere
else. That failure appears only when a real opponent connects, which is the
worst possible moment to find it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = ["LISTEN_HOST", "ServerSpec", "build_server_spec", "create_server"]

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
        tools: Tool name to callable, already bound and already guarded.
    """

    name: str
    host: str
    port: int
    tools: dict[str, Callable[..., Any]]

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Return the registered tool names, sorted for stable comparison."""
        return tuple(sorted(self.tools))


def build_server_spec(
    tools: dict[str, Callable[..., Any]],
    name: str,
    port: int,
) -> ServerSpec:
    """Return the full server definition, without starting anything.

    Args:
        tools: Ready-made callables. This layer neither builds nor validates
            them — it does not know what a commit is, and must not.
        name: Peer name for MCP metadata.
        port: Local bind port.
    """
    return ServerSpec(name=name, host=LISTEN_HOST, port=port, tools=dict(tools))


def create_server(spec: ServerSpec):
    """Register every tool on a FastMCP instance and return it.

    Imported lazily so this module, and every test above it, stays free of a
    FastMCP dependency. Excluded from coverage because exercising it means
    standing up a real server; ``build_server_spec`` carries the logic that can
    be tested, and the localhost round-trip test (2.4.2) covers the rest.
    """
    from fastmcp import FastMCP
    from fastmcp.tools import Tool

    server = FastMCP(spec.name)
    for name, tool in spec.tools.items():
        server.add_tool(Tool.from_function(tool, name=name))
    return server
