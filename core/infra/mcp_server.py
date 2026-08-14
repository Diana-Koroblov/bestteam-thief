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

__all__ = [
    "LISTEN_HOST",
    "Route",
    "ServerSpec",
    "base_url",
    "build_server_spec",
    "create_server",
]

# Every interface, so an ngrok tunnel can reach us. See the module docstring.
LISTEN_HOST = "0.0.0.0"  # noqa: S104 - deliberate, and explained above


@dataclass(frozen=True)
class Route:
    """One plain HTTP endpoint served beside `/mcp`, for things MCP does not do.

    A2A discovery is the reason this exists: an Agent Card is fetched with a
    bare `GET` by a peer that has not spoken MCP to us yet, so it cannot be a
    tool. It rides the **same** server and therefore the same tunnel — a second
    process would need a second public URL, and we have one reserved domain.

    ``respond`` is deliberately not an ASGI handler. It takes the base URL the
    request arrived on and the decoded JSON body (``None`` for a `GET`), and
    returns ``(status, body)``. Framework types stop at this module, which is
    what keeps the A2A content testable without a socket (M#3).

    Attributes:
        path: Absolute path, e.g. ``/.well-known/agent-card.json``.
        methods: HTTP methods this path answers.
        respond: ``(base_url, body) -> (status, json_body)``.
    """

    path: str
    methods: tuple[str, ...]
    respond: Callable[[str, dict[str, Any] | None], tuple[int, dict[str, Any]]]


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
        routes: Plain HTTP endpoints served beside `/mcp`. Empty is normal —
            a match needs none of them.
    """

    name: str
    host: str
    port: int
    tools: dict[str, Callable[..., Any]]
    routes: tuple[Route, ...] = ()

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Return the registered tool names, sorted for stable comparison."""
        return tuple(sorted(self.tools))

    @property
    def route_paths(self) -> tuple[str, ...]:
        """Return the extra HTTP paths, sorted, for the same reason."""
        return tuple(sorted(route.path for route in self.routes))


def build_server_spec(
    tools: dict[str, Callable[..., Any]],
    name: str,
    port: int,
    routes: tuple[Route, ...] = (),
) -> ServerSpec:
    """Return the full server definition, without starting anything.

    Args:
        tools: Ready-made callables. This layer neither builds nor validates
            them — it does not know what a commit is, and must not.
        name: Peer name for MCP metadata.
        port: Local bind port.
        routes: Ready-made HTTP responders, on the same terms as the tools:
            this layer serves them and does not know what they say.
    """
    return ServerSpec(
        name=name, host=LISTEN_HOST, port=port, tools=dict(tools), routes=tuple(routes)
    )


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
    for route in spec.routes:
        _register(server, route)
    return server


def _register(server: Any, route: Route) -> None:  # pragma: no cover - needs a live app
    """Mount one `Route` as a Starlette endpoint on *server*.

    All the framework contact in this file is here: decode the body, hand the
    responder two plain values, encode what comes back. A malformed body is a
    400 rather than a traceback, because the peer sending it is on another
    machine and a stack trace in our terminal tells them nothing.
    """
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    async def endpoint(request: Request) -> JSONResponse:
        body: dict[str, Any] | None = None
        if request.method != "GET":
            try:
                body = await request.json()
            except ValueError:
                return JSONResponse(
                    {"error": {"code": "invalid_request", "message": "body is not valid JSON"}},
                    status_code=400,
                )
        status, payload = route.respond(base_url(request), body)
        return JSONResponse(payload, status_code=status)

    server.custom_route(route.path, methods=list(route.methods), name=route.path)(endpoint)


def base_url(request: Any) -> str:
    """Return the public origin this request arrived on, no trailing slash.

    **Read off the request, never off our own config.** The server itself only
    ever sees `http://0.0.0.0:8081`; the URL a peer must be given is whatever
    the tunnel puts in front of that, and it changes between a localhost
    rehearsal and a match. Uvicorn does not trust proxy headers by default, so
    the forwarded pair is consulted first — without them an ngrok-fronted card
    would advertise `http://` and every fetch of it would break on mixed
    content.
    """
    headers = request.headers
    scheme = headers.get("x-forwarded-proto", "").split(",")[0].strip() or request.url.scheme
    host = (
        headers.get("x-forwarded-host", "").split(",")[0].strip()
        or headers.get("host", "").strip()
        or request.url.netloc
    )
    return f"{scheme}://{host}".rstrip("/")
