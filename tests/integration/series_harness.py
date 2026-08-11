"""Two teams, four peers, wired to play a series in one process (TODO 9.5).

Split from `test_series_runner.py` on a real seam: this is the *deployment* a
series is played on, and that file is what the series must then be true of.

**Four peers, not two.** Each team fields a Cop process and a Thief process, and
they stay separate objects for the whole series because M#1 and M#2 require it —
one process, one role, no shared memory. For sub-games 1-3 our Cop faces their
Thief; for 4-6 our Thief faces their Cop. The two processes on a side never
meet, which is the arrangement a published repository forces (ADR-001) and the
reason the split is two repositories rather than a flag.

The transport is in-process, as everywhere else in this suite: the real server,
the real client, the real tools, no socket.
"""

from __future__ import annotations

import asyncio
from typing import Any

from core.domain.barriers import BarrierManager
from core.infra.mcp_client import OpponentClient
from core.infra.mcp_server import build_server_spec, create_server
from core.protocol.schemas import Role
from core.protocol.tools import build_guarded_tools
from core.report.identifiers import game_id
from core.runtime.brain_loader import brain_for
from core.runtime.filing import MatchFiling
from core.runtime.live import declare
from core.runtime.match_driver import MatchDriver
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from core.runtime.series import OTHER, SeriesRunner, roles_for

__all__ = ["GAME_ID", "Team", "play"]

GAME_ID = game_id("bestteam", "opponents", "2026-08-08")


class Team:
    """One team's two role processes, alive for the whole series.

    The runtimes persist across sub-games rather than being rebuilt, because
    that is what a real peer does: the server stays up, the URL does not change,
    and the brain banks what it has learned about this opponent over six
    sub-games (TODO 8.3.3). What restarts is the board, via `start_sub_game`.
    """

    def __init__(self, config: Any, port_base: int) -> None:
        self.config = config
        self.peers = {role: self._peer(role) for role in Role}
        self.servers = {
            role: create_server(
                build_server_spec(
                    build_guarded_tools(self.peers[role]), role.value, port_base + index
                )
            )
            for index, role in enumerate(Role)
        }

    def _peer(self, role: Role) -> PeerRuntime:
        """Build one role process, agreed and ready, with its shipped brain."""
        runtime = PeerRuntime(orchestrator=Orchestrator.from_config(self.config, role))
        runtime.brain = brain_for(role.value, self.config)
        runtime.agreed = True
        return runtime

    def driver(self, sub_game: int, role: Role, opponent: Team) -> MatchDriver:
        """Return this team's driver for one sub-game, board freshly reopened."""
        runtime = self.peers[role]
        runtime.start_sub_game(sub_game)
        return MatchDriver(
            runtime=runtime,
            # Their process for the role we are *not* playing.
            client=OpponentClient("in-process", 10, transport=opponent.servers[OTHER[role]]),
            barriers=BarrierManager(
                max_barriers=self.config.require("movement_and_barriers.max_barriers"),
                board=runtime.orchestrator.board,
            ),
        )


def runners(config: Any, directory: Any = None) -> tuple[SeriesRunner, SeriesRunner]:
    """Return both teams' runners under the negotiated 3-3 split.

    Only our side files artefacts. Both would write the same filenames into one
    directory and the second would overwrite the first — which is a real hazard
    worth keeping out of a fixture, since the two teams genuinely do produce
    files with identical names and each keeps its own (M#35: each side files its
    own report).
    """
    us, them = Team(config, 8400), Team(config, 8410)
    ours = roles_for("3-3", Role.COP, 6)
    filing = (
        MatchFiling(game_id=GAME_ID, directory=directory, config=config, role_split="3-3")
        if directory
        else None
    )
    if filing is not None:
        # Before the first move, exactly as `cli_play` does it. Filed **here**
        # rather than by the test, so `test_the_series_files_all_four_artefacts`
        # proves the declaration is produced by playing a series — which is the
        # claim it was making while the test wrote the file itself.
        declare(filing, us.peers[Role.COP], ("in-process://ours", "in-process://theirs"), None)
    return (
        SeriesRunner(
            build=lambda n, role: us.driver(n, role, them),
            plan=list(enumerate(ours, start=1)),
            table=us.peers[Role.COP].orchestrator.scoring,
            filing=filing,
        ),
        SeriesRunner(
            build=lambda n, role: them.driver(n, role, us),
            plan=[(n, OTHER[role]) for n, role in enumerate(ours, start=1)],
            table=them.peers[Role.COP].orchestrator.scoring,
        ),
    )


def play(config: Any, directory: Any = None):
    """Play both sides of a full series and return ``(ours, theirs)``.

    Gathered rather than run in turn: each runner blocks waiting for the other's
    messages, so running them sequentially would deadlock on the first commit —
    which is the property that makes this an integration test and not a harness.
    """

    async def both():
        ours, theirs = runners(config, directory)
        return await asyncio.gather(ours.run(), theirs.run())

    return asyncio.run(both())
