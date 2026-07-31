"""The single gateway between subsystems. Nothing peripheral imports anything else.

M#3 requires one path between modules, and the reason is not tidiness. Five
subsystems — domain, protocol, transport, strategy, reporting — that each import
each other become a graph nobody can reason about, and in a project where the
*only* defence against a dispute is a readable log, "which module changed the
state" has to have one answer.

So the rule is a shape: **peripheral modules import `core.domain` and nothing
else horizontal.** The strategy layer never calls the transport. The transport
never touches the board. Anything that needs two subsystems goes through here.

The rule is enforced, not merely stated: ``tests/integration/test_process_separation.py``
walks the real import graph and fails on a violation. A convention nobody checks
is a convention that lasts about a week.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.domain.board import Board
from core.domain.game_state import GameState
from core.domain.rules import Rules
from core.domain.scoring import ScoreTable
from core.infra.mcp_client import OpponentClient
from core.protocol.schemas import Role
from core.shared.config_manager import Config

__all__ = ["Orchestrator"]


@dataclass
class Orchestrator:
    """Owns the game state and is the only thing permitted to change it.

    Attributes:
        config: The negotiated configuration, already validated.
        role: Which side this process plays. One process, one role (M#1).
        board: Geometry, sized from config.
        rules: Terminal conditions, resolved once from config.
        scoring: The Appendix F values.
        state: The current position. Replaced, never mutated.
        opponent: The one peer we talk to. ``None`` until the handshake supplies
            a URL, which is why it is not a constructor argument.
    """

    config: Config
    role: Role
    board: Board
    rules: Rules
    scoring: ScoreTable
    state: GameState
    opponent: OpponentClient | None = None
    history: list[GameState] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: Config, role: Role) -> Orchestrator:
        """Build a runnable orchestrator from a loaded configuration.

        Every value comes from the signed config — board size, start positions,
        terminal conditions, scoring. Nothing is a literal here, so what we play
        is provably what was agreed.
        """
        board = Board(
            grid_size=config.require("board_and_agents.grid_size"),
            origin_index=config.require("board_and_agents.axis_start_index"),
        )
        return cls(
            config=config,
            role=role,
            board=board,
            rules=Rules.from_config(config, board),
            scoring=ScoreTable.from_config(config),
            state=GameState(
                cop=tuple(config.require("board_and_agents.cop_start")),
                thief=tuple(config.require("board_and_agents.thief_start")),
            ),
        )

    @property
    def is_cop(self) -> bool:
        """Return True when this process plays the Cop."""
        return self.role is Role.COP

    @property
    def own_position(self) -> tuple[int, int]:
        """Return where *we* are — the only position we know for certain."""
        return self.state.cop if self.is_cop else self.state.thief

    def connect(self, base_url: str) -> None:
        """Attach the single opponent, using the timeout we negotiated.

        Raises:
            RuntimeError: An opponent is already attached. M#4 permits exactly
                one, and silently replacing it would let a second peer take over
                a match already in progress.
        """
        if self.opponent is not None:
            raise RuntimeError(
                f"an opponent is already attached at {self.opponent.base_url}; "
                "a peer addresses exactly one other peer (M#4)"
            )
        self.opponent = OpponentClient(
            base_url=base_url,
            timeout_sec=self.config.require("network_and_league.response_timeout_sec"),
            team=self.config.get("identity.team_name", ""),
        )

    def advance(self, state: GameState) -> None:
        """Replace the current state, keeping the previous one for the log.

        The history is what the replay simulator reads, so a transition that
        skipped this method would be invisible to the audit — which is why this
        is the only way state changes.
        """
        self.history.append(self.state)
        self.state = state
