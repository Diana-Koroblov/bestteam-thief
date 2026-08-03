"""The one public surface. Everything outside `core/` goes through here.

Excellence guide §4.1: the UI, the scripts and the notebooks import **this** and
nothing deeper. The check is literal — ``grep -r "from core.domain" core/ui/``
must return nothing — and it is enforced by a test rather than remembered.

The reason is replaceability. `core.domain.GameState` is a value the engine is
free to reshape between phases; a Tkinter callback reaching into it turns an
internal detail into a public contract by accident. A facade means the engine
can change and only this file has to keep up.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.domain.connectivity import exit_count, region_size
from core.domain.movement import get_legal_moves
from core.infra.mcp_server import ServerSpec, build_server_spec
from core.infra.tunnel import TunnelManager
from core.protocol.schemas import Role
from core.protocol.tools import build_guarded_tools
from core.runtime.brain_loader import load_brain
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from core.shared import env
from core.shared.config_manager import load_config

__all__ = ["PeerSDK", "BoardView"]


@dataclass(frozen=True)
class BoardView:
    """A flat, read-only snapshot for display. No engine objects escape.

    Deliberately plain types: a UI holding a live ``GameState`` would keep a
    reference to a position the engine has already replaced, and would render
    the previous turn while claiming to show this one.
    """

    grid_size: int
    cop: tuple[int, int]
    thief: tuple[int, int]
    barriers: tuple[tuple[int, int], ...]
    step: int
    barriers_placed: int
    barriers_remaining: int


class PeerSDK:
    """Everything a caller outside ``core`` is allowed to do."""

    def __init__(self, config_dir: Path, role: Role) -> None:
        """Load a role's configuration and build a runnable peer.

        Args:
            config_dir: ``config/police`` or ``config/thief``.
            role: The side this process plays. One process, one role (M#1).
        """
        self._config = load_config(config_dir)
        self._orchestrator = Orchestrator.from_config(self._config, role)
        # Loaded eagerly: a bad strategy path must fail here, where the only
        # cost is an error message, not on turn one of a real match.
        brain = load_brain(self._config.get(f"strategy.{role.value}_class"), role.value)
        self._runtime = PeerRuntime(orchestrator=self._orchestrator, brain=brain)

    @property
    def role(self) -> Role:
        """Return the role this peer plays."""
        return self._orchestrator.role

    @property
    def config_digest(self) -> str:
        """Return the digest both peers compare during the handshake (M#11)."""
        return self._config.shared_digest()

    @property
    def runtime(self) -> PeerRuntime:
        """Return the handler an MCP server registers its tools against."""
        return self._runtime

    def server_spec(self, port: int | None = None) -> ServerSpec:
        """Return this peer's server definition, tools already built and guarded.

        This is the join M#3 puts in the gateway: the protocol builds the tools,
        the transport registers them, and neither imports the other. The wiring
        happens here because here is the one place allowed to know both.
        """
        return build_server_spec(
            tools=build_guarded_tools(self._runtime),
            name=self._config.get("identity.contact_label", "peer"),
            port=port or self._config.require("network.listen_port"),
        )

    def tunnel(self, **overrides: Any) -> TunnelManager:
        """Return the tunnel manager for this peer's configured provider (TODO 5.1.1).

        The authtoken is resolved here rather than by the caller, because which
        variable holds it depends on which provider the config selected — and a
        caller that hardcoded ``NGROK_AUTHTOKEN`` would silently start an
        unauthenticated fallback the day the config switched.

        Missing is not an error yet: ``start()`` raises with the SETUP step that
        fixes it, so building the manager to inspect it stays free.
        """
        manager = TunnelManager.from_config(self._config, "", **overrides)
        manager.authtoken = env.optional(manager.spec.token_env) or ""
        return manager

    @property
    def brain_name(self) -> str:
        """Return the strategy this peer will play with."""
        return self._runtime.brain.name if self._runtime.brain else "none"

    def connect(self, base_url: str) -> None:
        """Attach the single opponent for this match."""
        self._orchestrator.connect(base_url)

    def board_view(self) -> BoardView:
        """Return a display snapshot of the current position."""
        state = self._orchestrator.state
        quota = self._config.require("movement_and_barriers.max_barriers")
        return BoardView(
            grid_size=self._orchestrator.board.grid_size,
            cop=state.cop,
            thief=state.thief,
            barriers=tuple(sorted(state.barriers)),
            step=state.step,
            barriers_placed=state.barriers_placed,
            barriers_remaining=quota - state.barriers_placed,
        )

    def legal_moves(self) -> tuple[str, ...]:
        """Return the move names legal for *us* from where we stand."""
        state = self._orchestrator.state
        moves = get_legal_moves(
            self._orchestrator.own_position, state.barriers, self._orchestrator.board
        )
        return tuple(direction.value for direction, _ in moves)

    def own_room(self) -> int:
        """Return how many cells we can still reach.

        Exposed because it is the number that decides whether a barrier is a
        good idea: a Cop whose region no longer contains the Thief has already
        lost, whatever the board looks like.
        """
        state = self._orchestrator.state
        return region_size(
            self._orchestrator.own_position, state.barriers, self._orchestrator.board
        )

    def own_exits(self) -> int:
        """Return how many orthogonal exits we currently have."""
        state = self._orchestrator.state
        return exit_count(
            self._orchestrator.own_position, state.barriers, self._orchestrator.board
        )
