"""Asking an opponent's host whether a match could actually start (Ch. 2.3).

Three questions, in the order they will bite: is their Agent Card there, does
their A2A endpoint answer, and — the only one that decides anything — does their
MCP server expose the six tools we are going to call. A peer missing
`declare_barrier` passes any "is it up?" check and fails at the first placement.

**Every failure is reported, never raised.** The point is to learn *which* of the
three is broken; an exception at the first hides the state of the other two, and
that is how a peer ends up fixing their card twice while their MCP server is the
thing that is down.
"""

from __future__ import annotations

import json
from typing import Any

from core.a2a import CARD_PATHS, MESSAGE_PATHS

__all__ = ["READINESS_QUESTION", "REQUIRED_TOOLS", "probe", "declared_url", "texts"]

# The one question the endpoint exists to answer.
READINESS_QUESTION = (
    "Confirm your MCP endpoint, Agent Card, commit/reveal protocol, and timeout "
    "settings. Do not start a game yet."
)

# What we will call during a match.
REQUIRED_TOOLS = (
    "negotiate",
    "receive_commit",
    "receive_reveal",
    "declare_barrier",
    "capture_claim",
    "final_reveal",
)

HTTP_TIMEOUT_SEC = 15.0

# Every probe request opens its own connection, and says so.
#
# 🐛 Found against nis-yar1 on 13/08: their A2A endpoint answered 200 to a fresh
# connection and 400 "Bad request syntax" to the *second* request on a reused
# one — the signature of a `http.server` handler that does not drain the request
# body, leaving the next request on that socket parsed from the middle of the
# previous one. Any pooling client hits it. A probe that reported their bug as
# "your endpoint is down" would send them hunting in the wrong place, so we take
# the connection variable off the table and test one thing at a time.
NO_KEEPALIVE = {"Connection": "close"}


async def probe(base: str) -> int:
    """Check card, message endpoint and MCP tools. Returns 1 if any is unusable."""
    print(f"probing {base}\n")
    card_ok = await _card(base)
    message_ok = await _message(base)
    mcp_ok = await _mcp(f"{base}/mcp")
    ready = card_ok and message_ok and mcp_ok
    print(
        f"\nverdict: {'READY' if ready else 'NOT READY'} "
        f"(card {_mark(card_ok)}, a2a {_mark(message_ok)}, mcp {_mark(mcp_ok)})"
    )
    if not mcp_ok:
        print("  the match runs on MCP. A missing card is untidy; a missing tool is fatal.")
    return 0 if ready else 1


async def _request(method: str, url: str, body: dict | None = None) -> Any:
    """Make one request on a connection of its own. None means it failed."""
    import httpx

    headers = dict(NO_KEEPALIVE)
    if body is not None:
        headers["Content-Type"] = "application/a2a+json"
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SEC, follow_redirects=True) as http:
        try:
            return await http.request(method, url, json=body, headers=headers)
        except httpx.HTTPError as error:
            print(f"        unreachable: {type(error).__name__}")
            return None


async def _card(base: str) -> bool:
    """Fetch the Agent Card, trying both spellings the revisions have used."""
    for path in CARD_PATHS:
        response = await _request("GET", f"{base}{path}")
        if response is None or response.status_code != 200:
            print(f"card    {path}: {'no answer' if response is None else response.status_code}")
            continue
        try:
            card = response.json()
        except ValueError:
            print(f"card    {path}: HTTP 200 but the body is not JSON")
            continue
        print(f"card    {path}: OK")
        print(f"        name : {card.get('name', '(unnamed)')}")
        print(f"        url  : {declared_url(card)}")
        return True
    return False


async def _message(base: str) -> bool:
    """Send the readiness question to whichever path and envelope answers.

    Both envelopes are tried on each path — the REST form first, then JSON-RPC —
    because a peer whose card says `JSONRPC` may well refuse the other, and
    "your endpoint is broken" is the wrong thing to tell someone whose endpoint
    simply wanted the envelope their own card advertised.
    """
    message = {"messageId": "probe", "role": "ROLE_USER", "parts": [{"text": READINESS_QUESTION}]}
    envelopes = {
        "rest": {"message": message},
        "jsonrpc": {
            "jsonrpc": "2.0",
            "id": "probe",
            "method": "message/send",
            "params": {"message": message},
        },
    }
    for path in MESSAGE_PATHS:
        for name, body in envelopes.items():
            response = await _request("POST", f"{base}{path}", body)
            if response is None or response.status_code != 200:
                code = "no answer" if response is None else f"HTTP {response.status_code}"
                print(f"a2a     {path} [{name}]: {code}")
                continue
            print(f"a2a     {path} [{name}]: OK")
            for line in texts(response.json()):
                print(f"        | {line}")
            return True
    return False


async def _mcp(url: str) -> bool:
    """List their MCP tools and say which of ours are missing.

    Uses `fastmcp.Client` directly rather than `OpponentClient`: this is not a
    match message, it is a question about the server, and routing it through the
    gatekeeper would spend match quota on a diagnostic.
    """
    from fastmcp import Client

    try:
        async with Client(url) as client:
            names = sorted(tool.name for tool in await client.list_tools())
    except Exception as error:  # noqa: BLE001 - a probe reports failures, never raises
        print(f"mcp     {url}: unreachable ({type(error).__name__}: {error})")
        return False
    print(f"mcp     {url}: OK")
    print(f"        tools: {', '.join(names) or '(none)'}")
    missing = [tool for tool in REQUIRED_TOOLS if tool not in names]
    if missing:
        print(f"        MISSING: {', '.join(missing)}")
    return not missing


def declared_url(card: dict) -> str:
    """Return the message endpoint a card advertises, however it spells it.

    A2A puts it in `url`; nis-yar1's card puts it in `supportedInterfaces`,
    which no revision of the schema defines. Reading both is three lines here
    and saves telling a peer their card is empty when it is merely unusual.
    """
    if isinstance(card.get("url"), str):
        return card["url"]
    for key in ("supportedInterfaces", "additionalInterfaces"):
        for entry in card.get(key) or []:
            if isinstance(entry, dict) and isinstance(entry.get("url"), str):
                return f"{entry['url']}  (in {key}, not in the standard `url` field)"
    return "(none declared - a strict A2A client cannot find their endpoint)"


def texts(payload: Any) -> list[str]:
    """Return the text lines of an A2A reply, whichever shape it came back in.

    Three are in circulation and we have met all three: a bare Message, a
    JSON-RPC `result`, and a Task carrying artifacts — what nis-yar1 returns.
    Printing raw JSON when a reply is perfectly readable is a small thing that
    makes a readiness check feel unusable.
    """
    if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
        payload = payload["result"]
    if isinstance(payload, dict) and isinstance(payload.get("task"), dict):
        payload = payload["task"]
    containers: list[Any] = [payload]
    if isinstance(payload, dict) and isinstance(payload.get("artifacts"), list):
        containers = payload["artifacts"]
    lines: list[str] = []
    for container in containers:
        parts = container.get("parts") if isinstance(container, dict) else None
        for part in parts if isinstance(parts, list) else []:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                lines.extend(part["text"].splitlines())
    return lines or [json.dumps(payload)[:400]]


def _mark(ok: bool) -> str:
    """Return the one-word verdict used in the summary line."""
    return "ok" if ok else "FAILED"
