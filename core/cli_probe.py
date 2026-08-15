"""`python -m core probe` — which protocol does this opponent actually speak?

    python -m core probe https://them.ngrok-free.dev/mcp

The one machine-answerable question worth asking before a slot is booked. Our
native surface is six synchronous tools; the Appendix D example repository
exposes four fire-and-forget mailboxes, and most of the league built on it
(C-019). The two cannot talk to each other, and the failure looks like a network
fault rather than a mismatch — an unrecognised tool, a reply of the wrong shape,
or a peer that never answers. Two friendly slots were lost that way on 13/08.

**It replaces the A2A readiness probe, retired on 15/08.** That command asked
three questions — Agent Card, A2A message endpoint, MCP tools — and failed the
whole verdict unless all three passed, so a healthy opponent who never built A2A
read as NOT READY. It also checked their tools against our six *only*, which
reported the reference implementation's perfectly playable four as five missing
tools. Both are the same mistake: judging an opponent against our own shape
rather than asking what theirs is.

**Nothing here plays.** No runtime, no negotiation, no artefact. A readiness
check that could open a sub-game is one nobody dares run twice.
"""

from __future__ import annotations

import argparse
import asyncio

__all__ = ["probe_command", "probe", "classify", "NATIVE_TOOLS", "REFERENCE_TOOLS"]

# Our own six. `core/protocol/tools.py` is the authority; repeated here because
# this module must be able to name them without building a runtime.
NATIVE_TOOLS = (
    "negotiate",
    "receive_commit",
    "receive_reveal",
    "declare_barrier",
    "capture_claim",
    "final_reveal",
)

# The example repository's four (`core/compat/mailbox.py`).
REFERENCE_TOOLS = ("negotiate", "receive_turn", "submit_audit", "receive_control")

HTTP_TIMEOUT_SEC = 15.0


def classify(names: tuple[str, ...]) -> tuple[str, str]:
    """Return ``(flag, explanation)`` for the tool list *names*.

    Both surfaces spell one tool ``negotiate`` and mean different things by it,
    so the decision rests on the tools either side of that: a peer serving
    ``receive_commit`` speaks ours, one serving ``receive_turn`` speaks the
    reference's. A peer serving both is answered on ours, because that is the
    path our four artefacts and the audit were built around.
    """
    found = set(names)
    native = [tool for tool in NATIVE_TOOLS if tool in found]
    reference = [tool for tool in REFERENCE_TOOLS if tool in found]
    missing_native = [tool for tool in NATIVE_TOOLS if tool not in found]

    if not missing_native:
        return "", "they speak OUR protocol - play them with no --protocol flag"
    if len(reference) >= 3:
        return (
            "--protocol reference",
            "they speak the example repository's protocol - "
            "play them with --protocol reference",
        )
    if native:
        return "", (
            "PARTIAL native surface: missing " + ", ".join(missing_native) + ". "
            "A missing declare_barrier is a sub-game that dies at the first "
            "placement - ask them before booking a slot."
        )
    return "", (
        "unrecognised surface - neither ours nor the example repository's. "
        "Ask them which implementation they built on."
    )


async def probe(url: str) -> int:
    """List their MCP tools and say what to do about them. 0 means playable.

    Uses `fastmcp.Client` directly rather than `OpponentClient`: this is a
    question about their server, not a match message, and routing it through
    the gatekeeper would spend match quota on a diagnostic.
    """
    from fastmcp import Client

    print(f"probing {url}\n")
    try:
        async with Client(url) as client:
            names = tuple(sorted(tool.name for tool in await client.list_tools()))
    except Exception as error:  # noqa: BLE001 - a probe reports failures, never raises
        print(f"  unreachable: {type(error).__name__}: {error}")
        print("\n  Their peer is not running, or the URL is wrong. An ngrok URL is")
        print("  live only while their process is up - ask them to start it.")
        return 1

    print(f"  tools ({len(names)}): {', '.join(names) or '(none)'}\n")
    flag, explanation = classify(names)
    print(f"  {explanation}")
    if flag:
        print(f"\n  add to your play command: {flag}")
    return 0


def probe_command(args: argparse.Namespace) -> int:
    """Run the probe against ``args.url``, tolerating a missing ``/mcp``."""
    url = args.url.rstrip("/")
    if not url.endswith("/mcp"):
        url = f"{url}/mcp"
    return asyncio.run(probe(url))
