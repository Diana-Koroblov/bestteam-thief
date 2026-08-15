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
from core.infra.mcp_client import DEFAULT_CALLS_PER_MINUTE, OpponentClient
from core.protocol.schemas import Role
from core.shared.config_manager import Config

__all__ = ["Orchestrator"]


def _opening(config: Config, sub_game: int) -> GameState:
    """Return the agreed starting position for a sub-game.

    One definition, used by both the first sub-game and every restart after it.
    Two would let a series open its second sub-game from a position neither peer
    agreed to — and both peers would still be enforcing the physics correctly,
    from different boards.
    """
    return GameState(
        cop=tuple(config.require("board_and_agents.cop_start")),
        thief=tuple(config.require("board_and_agents.thief_start")),
        sub_game=sub_game,
    )


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
            state=_opening(config, sub_game=1),
        )

    @property
    def is_cop(self) -> bool:
        """Return True when this process plays the Cop."""
        return self.role is Role.COP

    @property
    def own_position(self) -> tuple[int, int]:
        """Return where *we* are — the only position we know for certain."""
        return self.state.cop if self.is_cop else self.state.thief

    def connect(self, base_url: str, timeout_sec: float | None = None) -> None:
        """Attach the single opponent, using the timeout we negotiated.

        Args:
            timeout_sec: Overrides the signed `response_timeout_sec` when
                given. The reference-protocol path uses this to cap every
                outbound call strictly *under* the signed deadline rather than
                equal to it — the MCP SDK's own per-call default is exactly
                that deadline, so one delivered-but-unanswered push plus a
                retry sleep can breach it while every individual call still
                looks fine (imreeyal §3.5). The native path never passes it.

        Raises:
            RuntimeError: An opponent is already attached. M#4 permits exactly
                one **at a time**, and silently replacing it would let a second
                peer take over a match already in progress — `disconnect()`
                first if this is a deliberate reconnect, not a second peer.
        """
        if self.opponent is not None:
            raise RuntimeError(
                f"an opponent is already attached at {self.opponent.base_url}; "
                "a peer addresses exactly one other peer (M#4)"
            )
        self.opponent = OpponentClient(
            base_url=base_url,
            timeout_sec=timeout_sec or self.config.require("network_and_league.response_timeout_sec"),
            team=self.config.get("identity.team_name", ""),
            # Private and per-machine, like the port and the domain beside it:
            # it describes what our tunnel plan can carry, and the opponent
            # neither sees it nor agrees to it (PRD 5 §3.3 requirement 5.10).
            calls_per_minute=float(
                self.config.get("network.max_calls_per_minute", DEFAULT_CALLS_PER_MINUTE)
            ),
        )

    def disconnect(self) -> None:
        """Detach the current opponent so `connect` may attach a fresh one.

        Not a loophole in M#4 — that rule forbids **two opponents at once**,
        which this cannot produce: the slot is empty until the next `connect`.
        It exists for the reference protocol, which drops and re-dials its
        outbound session at every sub-game boundary because the opponent's own
        runner restarts a process per sub-game too (imreeyal §3.4). The native
        path never calls this; one match, one opponent, for its whole length.
        """
        self.opponent = None

    def restart(self, sub_game: int) -> None:
        """Reopen the board for the next sub-game of the series (TODO 9.5).

        The history goes with it. It is the log's record of *one* sub-game, and
        `match_closing.their_records` indexes into it by step to re-hash the
        opponent's commitments — so a history carrying the previous sub-game's
        states would audit their step 0 against a board from a game that ended,
        and report forgery against an honest opponent.
        """
        self.history.clear()
        self.state = _opening(self.config, sub_game)

    def advance(self, state: GameState) -> None:
        """Replace the current state, keeping the previous one for the log.

        The history is what the replay simulator reads, so a transition that
        skipped this method would be invisible to the audit — which is why this
        is the only way state changes.
        """
        self.history.append(self.state)
        self.state = state
