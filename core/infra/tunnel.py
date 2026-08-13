"""The public face of this peer: a tunnel, managed programmatically (TODO 5.1.1).

Most machines sit behind NAT and a firewall, so the opponent cannot reach our
FastMCP server directly. A tunnelling agent solves that by publishing a public
URL that forwards to our local port. Public exposure is mandatory for league
play (M#10), which makes this module a hard dependency of every graded match and
of nothing else: Layers 1-4 continue to run on `127.0.0.1` with no agent
installed at all.

Three decisions are worth stating, because each of them is load-bearing:

**The URL is read back, not assumed.** We could compute `https://{domain}` from
config and never check it. Then a tunnel that failed to start would look
identical to one that worked, right up to the moment the opponent could not
reach us — during the match. So `start()` polls the agent's own local API until
it reports a live tunnel, and returns what the agent says rather than what we
hoped (PRD 5 §3.1 requirement 5.2).

**The authtoken never appears in argv.** Every process on the machine can read
another process's command line, so a token passed as `--authtoken <value>` is a
token in the process table. It goes in the child's environment instead (M#39).

**Every side effect is injected.** Spawning, probing and sleeping are
constructor fields, so the whole lifecycle is exercised against fakes and no
test opens a real tunnel (PRD 5 §5). The alternative — patching `subprocess` —
tests the patch as much as the code.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from core.shared.config_manager import Config

__all__ = ["TunnelError", "Provider", "PROVIDERS", "TunnelManager", "build_command",
           "AGENT_API", "reserved_domain", "DOMAIN_VAR", "LEGACY_DOMAIN_VAR"]

# Where the reserved domain really lives. See `reserved_domain`.
DOMAIN_VAR = "NGROK_DOMAIN"

# The name it used to live under, still honoured so an existing .env keeps
# working — but deliberately *lower* precedence than DOMAIN_VAR. See below.
LEGACY_DOMAIN_VAR = "P2P_PUBLIC_DOMAIN"


def reserved_domain(config: Config) -> str | None:
    """Return the static domain to publish on, or None for an ephemeral URL.

    🐛 **The committed default used to be a domain reserved on another
    account.** `--tunnel` therefore could not start at all::

        ERR_NGROK_320: This domain is reserved for another account.

    which meant public exposure (M#10) was unavailable and no league match could
    be played over the internet — a failure invisible to every localhost test we
    had, because localhost needs no tunnel.

    So the domain is read from the **environment** first. A reserved domain is
    an account credential in everything but name: it is tied to one ngrok login,
    it is useless to anyone else, and committing it to two public repositories
    guarantees it goes stale the moment the account changes. `.env` is where the
    authtoken beside it already lives.

    The config key is kept as a fallback so an existing setup is not broken by
    this, and **empty is a legitimate answer**: with no domain the agent assigns
    a random URL, which `TunnelManager` reads back rather than computes. A match
    can be played that way; the URL simply has to be re-sent after a restart.

    🐛 **One resolver, and the placeholder must never win.** For a while there
    were two variables for one value: this one, and `P2P_PUBLIC_DOMAIN`, applied
    *afterwards* by `PeerSDK.tunnel` and therefore overriding it. `.env-example`
    shipped the second holding the literal text `your-domain.ngrok-free.dev`, so
    copying the example and filling in the domain the file tells you to fill in
    left the placeholder in charge — and a placeholder domain fails exactly like
    a domain owned by someone else, which is the ERR_NGROK_320 failure this
    function was written to end. The legacy name is still read so an old `.env`
    plays, but it is last, because the value someone set on purpose beats one
    they inherited from a template.
    """
    for name in (DOMAIN_VAR, LEGACY_DOMAIN_VAR):
        if found := os.environ.get(name, "").strip():
            return found
    return str(config.get("network.public_domain") or "").strip() or None

# ngrok's agent exposes a local inspection API on a fixed port. Not the public
# tunnel: this is loopback-only and is how we ask the agent what it published.
AGENT_API = "http://127.0.0.1:4040/api/tunnels"

# The agent needs a moment to register the tunnel before its API admits to one.
# Twenty polls at half a second is a ten-second budget: generous for a local
# process, and a third of the 30 s response window if this ever runs mid-match.
STARTUP_POLLS = 20
POLL_INTERVAL_SEC = 0.5
STARTUP_BUDGET_SEC = STARTUP_POLLS * POLL_INTERVAL_SEC

# Seconds a terminating agent gets to close its connections before we kill it.
STOP_GRACE_SEC = 5.0


class TunnelError(RuntimeError):
    """The tunnel could not be started, or died and could not be revived.

    Deliberately **not** a :class:`~core.infra.errors.PeerError`. Those describe
    an opponent who failed us and carry a decision about retrying them; this is
    our own infrastructure failing, and the recovery is completely different.
    """


@dataclass(frozen=True)
class Provider:
    """One tunnelling CLI and how to invoke it.

    Attributes:
        name: The value that selects it in `[network] tunnel_provider`.
        binary: Executable that must be on PATH.
        args: Argument template. `{port}` and `{domain}` are substituted.
        domain_args: Appended only when a static domain is configured; without
            one, the agent assigns a random URL that changes on every restart.
        token_env: Environment variable the CLI reads its authtoken from.
        install_hint: What to tell a user who does not have the binary.
    """

    name: str
    binary: str
    args: tuple[str, ...]
    domain_args: tuple[str, ...]
    token_env: str
    install_hint: str


PROVIDERS: dict[str, Provider] = {
    # The primary, and the only one either machine has been set up with.
    "ngrok": Provider(
        name="ngrok",
        binary="ngrok",
        args=("http", "{port}"),
        domain_args=("--url", "{domain}"),
        token_env="NGROK_AUTHTOKEN",
        install_hint="winget install ngrok.ngrok",
    ),
    # The documented P2 fallback (PRD 5 §3.1 requirement 5.4). Kept here so the
    # switch is a config value rather than a code change, but note that these
    # arguments have never been run against a live Localtonet account: confirm
    # them against localtonet.com/docs before relying on this in a graded match.
    "localtonet": Provider(
        name="localtonet",
        binary="localtonet",
        args=("http", "--port", "{port}"),
        domain_args=("--domain", "{domain}"),
        token_env="LOCALTONET_AUTHTOKEN",
        install_hint="download from localtonet.com/download",
    ),
}


def build_command(provider: Provider, port: int, domain: str | None) -> tuple[str, ...]:
    """Return the argument vector for *provider*, with no secret anywhere in it."""
    template = (*provider.args, *(provider.domain_args if domain else ()))
    return (provider.binary, *(arg.format(port=port, domain=domain or "") for arg in template))


def _spawn(command: Sequence[str], env: dict[str, str]) -> Any:  # pragma: no cover - real process
    """Start the agent as a child process, with its console output discarded."""
    return subprocess.Popen(
        list(command), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def _probe_agent_api() -> str | None:  # pragma: no cover - needs a running agent
    """Return the agent's public HTTPS URL, or None when it has not published one."""
    import httpx

    try:
        payload = httpx.get(AGENT_API, timeout=2.0).json()
    except Exception:  # noqa: BLE001 - any failure means "no tunnel yet"
        return None
    urls = [tunnel.get("public_url", "") for tunnel in payload.get("tunnels", [])]
    return next((url for url in urls if url.startswith("https://")), None)


@dataclass
class TunnelManager:
    """Owns the tunnel agent for this peer's whole session.

    Attributes:
        authtoken: Read from the environment by the caller, never from config.
        port: The local port our FastMCP server listens on.
        domain: Our reserved static domain. Optional, but a match played
            without one strands the opponent at a dead address after any
            restart, which is why we reserved one.
        provider: Key into :data:`PROVIDERS`.
        spawn: Starts the child process. Injected; see the module docstring.
        probe: Returns the published public URL, or None.
        sleep: Waits between polls. Injected so no test spends real seconds.
        process: The running child, or None.
        url: The public URL from the most recent successful start.
    """

    authtoken: str
    port: int
    domain: str | None = None
    provider: str = "ngrok"
    spawn: Callable[[Sequence[str], dict[str, str]], Any] = _spawn
    probe: Callable[[], str | None] = _probe_agent_api
    sleep: Callable[[float], None] = time.sleep
    process: Any = field(default=None)
    url: str = ""

    @classmethod
    def from_config(cls, config: Config, authtoken: str, **overrides: Any) -> TunnelManager:
        """Build from the private `[network]` section of a loaded config.

        The port, domain and provider are all local settings the opponent never
        sees or agrees to, which is why they live in `game.toml` and not in the
        negotiated `game.json` (PRD 5 §3.3 requirement 5.10).

        Args:
            config: A loaded configuration.
            authtoken: The provider's token, read from the environment.
            **overrides: Replace any derived field. `port` in particular, so
                that `--port` on the command line moves the tunnel with the
                server instead of publishing a domain that forwards nowhere.
        """
        derived: dict[str, Any] = {
            "port": config.require("network.listen_port"),
            "domain": reserved_domain(config),
            "provider": config.get("network.tunnel_provider", "ngrok"),
        }
        return cls(authtoken=authtoken, **{**derived, **overrides})

    @property
    def spec(self) -> Provider:
        """Return the selected provider, or say which ones exist."""
        try:
            return PROVIDERS[self.provider]
        except KeyError:
            known = ", ".join(sorted(PROVIDERS))
            raise TunnelError(
                f"unknown tunnel provider {self.provider!r}; "
                f"set [network] tunnel_provider to one of: {known}"
            ) from None

    def start(self) -> str:
        """Start the agent and return the public URL it published.

        Idempotent: starting an already-running tunnel returns the existing URL
        rather than spawning a second agent, because two agents on one port
        leaves the opponent talking to whichever won the race.

        Raises:
            TunnelError: No authtoken, no binary, or no URL inside the startup
                budget. Always with the step of docs/SETUP.md that fixes it —
                a stack trace at match time tells nobody what to do (T5.6).
        """
        if self.is_alive():
            return self.url

        spec = self.spec
        if not self.authtoken.strip():
            raise TunnelError(
                f"{spec.token_env} is not set, so no tunnel can start and no opponent "
                "can reach us. Copy .env-example to .env and fill it in. "
                "See docs/SETUP.md 0.2.4."
            )
        if shutil.which(spec.binary) is None:
            raise TunnelError(
                f"{spec.binary!r} is not on PATH. See docs/SETUP.md 0.2.4 "
                f"({spec.install_hint})."
            )

        self.process = self.spawn(build_command(spec, self.port, self.domain), self._environment())
        try:
            self.url = self._await_url(spec)
        except Exception:
            # A failed start must leave nothing running. Otherwise the next
            # attempt finds a live agent, short-circuits on the check above as
            # already-started, and hands the caller an empty URL — a peer that
            # believes it is exposed at "" and an opponent who cannot reach it.
            self.stop()
            raise
        return self.url

    def _environment(self) -> dict[str, str]:
        """Return the child's environment, carrying the token out of argv (M#39)."""
        return {**os.environ, self.spec.token_env: self.authtoken}

    def _await_url(self, spec: Provider) -> str:
        """Poll the agent's local API until it publishes a URL, or give up.

        An agent that exits during startup is reported immediately rather than
        waited out: the whole ten-second budget spent on a process that is
        already dead is ten seconds of the match spent learning nothing.

        Cleanup belongs to the caller, which tears the process down on any
        failure — so there is exactly one place that has to get it right.
        """
        command = " ".join(build_command(spec, self.port, self.domain))
        for _ in range(STARTUP_POLLS):
            url = self.probe()
            if url:
                return url
            if not self.is_alive():
                raise TunnelError(
                    f"{spec.binary} exited before publishing a URL. "
                    f"Run it by hand to see why: {command}"
                )
            self.sleep(POLL_INTERVAL_SEC)

        raise TunnelError(
            f"{spec.binary} published no public URL within {STARTUP_BUDGET_SEC:g}s. "
            f"Check the agent's own log, or run: {command}"
        )

    def is_alive(self) -> bool:
        """Whether the agent process is still running.

        Deliberately a process check with no network call. The supervisor asks
        this every turn, and an HTTP request per turn would add latency to the
        very move loop this exists to protect.
        """
        return self.process is not None and self.process.poll() is None

    def restart(self) -> str:
        """Stop and start again, returning the public URL.

        With a reserved static domain this is the *same* URL as before, which is
        the entire reason for reserving one: a restart mid-series leaves the
        address the opponent already stored still valid (T5.2).
        """
        self.stop()
        return self.start()

    def stop(self) -> None:
        """Terminate the agent. Safe to call when nothing is running.

        The URL is kept. It describes the domain we reserved, not the process
        that happened to serve it, and the report is written after the tunnel
        is already down.
        """
        process, self.process = self.process, None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=STOP_GRACE_SEC)
        except subprocess.TimeoutExpired:  # pragma: no cover - needs a real process
            process.kill()
