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
from core.infra.gmail_sender import GmailSender, build_transport
from core.infra.mcp_server import ServerSpec, build_server_spec
from core.infra.tunnel import TunnelManager
from core.protocol.schemas import Role
from core.protocol.tools import build_guarded_tools
from core.runtime.brain_loader import brain_for
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from core.runtime.prematch import PreMatch
from core.sdk.view_state import GuiState
from core.shared import env
from core.shared.config_manager import load_config
from core.shared.gatekeeper import Gatekeeper
from core.shared.provider_budget import verify_budget
from core.shared.rate_limits import load_rate_limits

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
        self._config_dir = Path(config_dir)
        self._config = load_config(config_dir)
        self._gatekeeper: Gatekeeper | None = None
        self._orchestrator = Orchestrator.from_config(self._config, role)
        # Loaded eagerly: a bad strategy path must fail here, where the only
        # cost is an error message, not on turn one of a real match.
        #
        # Through `brain_for`, never by spelling the key here. The role is `cop`
        # and the config key is `police_class` (Appendix B.4), so the derived
        # `strategy.cop_class` this line used to ask for is a path no file
        # contains: `Config.get` returned None, `load_brain` read None as "use
        # the default", and the live CLI fielded the baseline PoliceBrain while
        # `config/police/game.toml` named AdvancedCop. Silent, and only on the
        # cop — `thief_class` happens to match the derived spelling, so the
        # thief looked right and the asymmetry hid the fault. Caught by a real
        # match: the test harness already went through `brain_for`, so no test
        # ever exercised the path a match actually takes (M#1).
        brain = brain_for(role.value, self._config)
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

    @property
    def scoring(self):
        """Return the Appendix F score table this match is priced with."""
        return self._orchestrator.scoring

    @property
    def num_games(self) -> int:
        """Return `[number of sub-games]` in a series — 6 under Appendix F Table 18."""
        return int(self._config.require("network_and_league.num_games"))

    @property
    def shared_config(self) -> dict:
        """Return the negotiated contract, verbatim — the file we send them.

        The **shared** half only. Private settings are not part of the agreement
        and including them would put our ngrok domain and provider choice in an
        opponent's hands, which Appendix F Table 21 keeps private on purpose.
        Copied, so a caller writing it out cannot edit the config we are hashing.
        """
        return dict(self._config.shared)

    @property
    def team_name(self) -> str:
        """Return our team name as declared at Step-0."""
        return str(self._config.get("identity.team_name", ""))

    @property
    def opponent(self):
        """Return the attached peer, or None before `connect`."""
        return self._orchestrator.opponent

    @property
    def prematch(self) -> PreMatch:
        """Return what this peer declares before the first move (TODO 9.1).

        The **same object** the runtime settles inbound handshakes against, not
        a second copy. Two views of one agreement that could disagree is the
        failure the whole handshake exists to prevent, and it would be
        embarrassing to introduce it in the facade.
        """
        return self._runtime.prematch

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
        # The reserved domain belongs to one account, so the committed value can
        # only ever be one team-mate's — and on the other machine `--tunnel`
        # fails binding a domain that account does not own. `P2P_PUBLIC_DOMAIN`
        # overrides it per machine, exactly as `P2P_LLM_PROVIDER` overrides the
        # provider, and for the same reason: it is a fact about this computer,
        # not about the match.
        manager.domain = env.optional("P2P_PUBLIC_DOMAIN") or manager.domain
        return manager

    @property
    def gatekeeper(self) -> Gatekeeper:
        """Return the single door every outbound call leaves by (TODO 7.1.2).

        **One instance per process, built once and reused.** The quota and the
        DOS detector are stateful by definition — a fresh Gatekeeper per call
        would start with a full bucket and an empty window, which is precisely
        the loop the detector exists to catch, made undetectable.
        """
        if self._gatekeeper is None:
            self._gatekeeper = Gatekeeper(limits=load_rate_limits(self._config_dir))
        return self._gatekeeper

    def mailer(self, transport: Any = None) -> GmailSender:
        """Return the league reporter, wired through the Gatekeeper (TODO 7.3).

        Args:
            transport: Injected in tests. Left unset in play, where the OAuth
                client is built on first use — so importing the SDK never needs
                a token and a peer with no credentials still starts.

        The **caller** decides when a report goes out. `[email]
        send_on_series_end` says it should be at the end of a series, and the
        turn loop that reaches that point does not exist yet (Phase 9).
        """
        return GmailSender.from_config(
            self._config, self.gatekeeper, transport or build_transport()
        )

    def verify_budget(self) -> None:
        """Refuse a metered provider paired with too short an interval (TODO 7.1.6).

        Raises:
            BudgetError: Naming both keys. Called at CLI startup rather than
                here in ``__init__``, so it stops a human about to play a match
                instead of failing the suite on a machine whose ``.env`` picks
                a metered provider.
        """
        verify_budget(self._config)

    @property
    def brain_name(self) -> str:
        """Return the strategy this peer will play with."""
        return self._runtime.brain.name if self._runtime.brain else "none"

    def connect(self, base_url: str) -> None:
        """Attach the single opponent for this match."""
        self._orchestrator.connect(base_url)

    @property
    def ui_cell_pixels(self) -> int:
        """Square size for both windows, from `[ui] cell_pixels`."""
        return int(self._config.get("ui.cell_pixels", 64))

    def gui_state(self, locked: bool = False) -> GuiState:
        """Return one frame for the Live GUI — local truth only (M#8, M#9).

        **Not `board_view()`.** That one carries both true positions and exists
        for self-play debugging and the CLI; handing it to a display would put
        the objective board state on screen, which is project disqualification.
        The two are separate methods so that the dangerous one has to be asked
        for by name.
        """
        return GuiState.from_observation(self._runtime.observe(), locked)

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
