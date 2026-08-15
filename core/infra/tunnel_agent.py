"""Per-agent ngrok wiring: which account decides, and where the local API answers.

Split from `tunnel.py` under the 150-line ceiling, holding two facts measured
live on 14/08 with two real accounts — both of which broke the two-door setup
(one reserved domain per role, both up for a whole match) before they were
understood:

* **The default config file's authtoken beats the environment variable.** Our
  spawn has always passed the token in the child's environment (M#39, argv is
  public) and it never actually decided anything: the cop's account matched the
  default config's token by coincidence, and the thief's agent authenticated as
  the wrong account and died with `ERR_NGROK_320` on a domain its own account
  legitimately owns. A minimal ``--config`` displaces the default file, and with
  no token inside it the environment token finally decides the account. The
  file this module writes contains no secret, so where it lives is not
  sensitive.

* **Two agents cannot share one inspection API.** ``web_addr`` defaults to
  4040 for every agent; the second either loses the bind or, worse, the probe
  reads whichever agent owns 4040 and hands the thief the cop's public URL —
  which it would then announce as its own door. One ``web_addr`` per agent,
  one probe port per manager.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

__all__ = ["AGENT_API_PORT", "agent_api_url", "write_agent_config", "probe_agent_api"]

# ngrok's default inspection port; the cop keeps it, every further agent on the
# machine takes the next one up (see `PeerSDK.tunnel`).
AGENT_API_PORT = 4040


def agent_api_url(api_port: int) -> str:
    """Return the local inspection endpoint for the agent on *api_port*."""
    return f"http://127.0.0.1:{api_port}/api/tunnels"


def write_agent_config(api_port: int, directory: Path | None = None) -> str:
    """Write the minimal per-agent config and return its path.

    Deliberately token-free — the token stays in the child's environment
    (M#39), and an empty config is exactly what lets it decide. Rewritten on
    every start: the file is two lines, and a stale ``web_addr`` from a
    previous run is precisely the failure this module exists to end.
    """
    base = Path(directory) if directory else Path(tempfile.gettempdir())
    path = base / f"ngrok-agent-{api_port}.yml"
    path.write_text(f'version: "2"\nweb_addr: "127.0.0.1:{api_port}"\n', encoding="utf-8")
    return str(path)


def probe_agent_api(api_port: int) -> str | None:  # pragma: no cover - needs a running agent
    """Return the agent's public HTTPS URL, or None when it has not published one."""
    import httpx

    try:
        payload = httpx.get(agent_api_url(api_port), timeout=2.0).json()
    except Exception:  # noqa: BLE001 - any failure means "no tunnel yet"
        return None
    urls = [tunnel.get("public_url", "") for tunnel in payload.get("tunnels", [])]
    return next((url for url in urls if url.startswith("https://")), None)
