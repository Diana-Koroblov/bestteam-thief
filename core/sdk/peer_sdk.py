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

from core.domain.connectivity import exit_count, region_size
from core.domain.movement import get_legal_moves
from core.protocol.schemas import Role
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
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
        self._runtime = PeerRuntime(orchestrator=self._orchestrator)

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
