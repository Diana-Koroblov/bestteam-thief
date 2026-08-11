"""The deployment a real series is played on (TODO 9.2, 9.4, 9.5).

`tests/integration/series_harness.py` is this module's twin. That one wires four
peers into one process over an in-process transport, because a test must be able
to play both sides. This is the same wiring against a real opponent: one peer,
the one role this repository ships, and a client that speaks HTTP over a tunnel.

Kept beside `series.py` rather than in the CLI because it is not a command — it
is the answer to *"what does a `MatchDriver` look like when the opponent is real"*,
and the CLI, a future rehearsal script and any harness that wants a live peer all
need the same answer. `SeriesRunner.build` exists precisely so this could be
supplied from outside; supplying it from a command-line module would have made
the CLI the only place that knows how to deploy a match.

**The runtime is reused across sub-games, never rebuilt.** The server stays up,
our URL does not change, and the brain keeps what it has learned about this
opponent over six sub-games (TODO 8.3.3). What restarts between sub-games is the
board, through `start_sub_game`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.crypto.canonical import digest
from core.domain.barriers import BarrierManager
from core.protocol.schemas import Role
from core.runtime.filing import MatchFiling
from core.runtime.match_driver import MatchDriver
from core.runtime.peer_runtime import PeerRuntime

__all__ = ["driver_factory", "filing_for", "declare"]


def reopen(runtime: PeerRuntime, prepared: set[int]) -> Callable[[int], None]:
    """Return a reset that runs **at most once** per sub-game.

    `start_sub_game` clears every inbox keyed by step number, which is right at
    a boundary and catastrophic a moment later: from the instant we are ready to
    play, the opponent may legitimately commit, and a second reset would delete
    a commit that had already arrived. Their reveal is then refused as unsealed
    and an untouched sub-game is scored a technical loss.

    So the reset is idempotent per sub-game and both callers go through here —
    the one that prepares the opening board before the handshake, and the one
    `SeriesRunner` fires the moment a sub-game closes.
    """

    def prepare(sub_game: int) -> None:
        if sub_game in prepared:
            return
        prepared.add(sub_game)
        runtime.start_sub_game(sub_game)

    return prepare


def driver_factory(
    runtime: PeerRuntime, client: Any, prepared: set[int] | None = None
) -> Callable[[int, Role], MatchDriver]:
    """Return the ``build`` callable `SeriesRunner` asks for.

    Args:
        runtime: Our receiving half — the same object the MCP server fills, and
            the reason serving and driving must share a process.
        client: The single opponent (M#4).
        prepared: Sub-games already reopened, shared with `reopen`. Omitted by a
            caller that resets nowhere else, which is the in-process case where
            no message can arrive before the build.

    The barrier quota is rebuilt per sub-game, deliberately. It is spent state:
    carrying one `BarrierManager` across the series would let a Cop who used all
    fourteen in sub-game one open sub-game two with none, which is neither what
    Appendix F says nor what the opponent's own copy would compute.
    """
    ready = reopen(runtime, prepared if prepared is not None else set())

    def build(sub_game: int, role: Role) -> MatchDriver:
        # The role is fixed by the repository (ADR-001); the plan only ever asks
        # for the one this process holds, and disagreeing means the plan was
        # built for the other side.
        if role is not runtime.orchestrator.role:
            raise ValueError(
                f"sub-game {sub_game} is planned for {role.value} but this process "
                f"plays {runtime.orchestrator.role.value}; a published repository "
                "ships one brain (ADR-001, M#1)"
            )
        ready(sub_game)
        return MatchDriver(
            runtime=runtime,
            client=client,
            barriers=BarrierManager(
                max_barriers=runtime.orchestrator.config.require(
                    "movement_and_barriers.max_barriers"
                ),
                board=runtime.orchestrator.board,
            ),
        )

    return build


def filing_for(
    runtime: PeerRuntime, game_identifier: str, directory: Path, locked: Any
) -> MatchFiling:
    """Return the artefact writer for one match (7.2.1-7.2.4).

    Every field comes from the **settled agreement** rather than from the
    command line. The config snapshot filed afterwards is what lets a reader
    reconstruct the physics a log was played under, and a digest typed by a
    human is one that can disagree with the handshake it claims to record.
    """
    return MatchFiling(
        game_id=game_identifier,
        directory=Path(directory),
        config=runtime.orchestrator.config,
        role_split=locked.role_split,
        agreed_digest=locked.config_sha256,
        scent_model_digest=locked.scent_model_sha256,
        readings=dict(locked.readings),
        github_commit=locked.our_commit,
    )


def declare(
    filing: MatchFiling, runtime: PeerRuntime, urls: tuple[str, str], theirs: Any
) -> None:
    """File the pre-game declaration before the first move (7.2.1, M#24).

    `declaration_<game_id>.json` is one of the four artefacts Ch. 9.3.3 names,
    and until this function existed nothing outside the test suite called the
    builder: a real match filed a config snapshot, six logs and a result, and no
    declaration at all.

    Assembled here rather than in the CLI because every value comes from the
    handshake that just settled. **Both peers' Step-0 payloads go in whole**,
    each beside the digest that seals it, which is what makes the hardware
    specification a signed declaration rather than a line in a report (M#24) —
    a machine restated later contradicts a digest the opponent already holds.

    Args:
        urls: ``(ours, theirs)`` — the public MCP endpoints this match ran over.
        theirs: The opponent's settled `Negotiation`, or None if the handshake
            never produced one. Their half is then recorded as empty rather than
            guessed; an absent opponent declaration is a visible finding and an
            invented one is a false statement in a signed artefact.
    """
    ours = runtime.prematch.step_zero()
    away = dict(getattr(theirs, "step_zero", None) or {})
    config = runtime.orchestrator.config
    filing.declaration(
        teams=_teams(ours.payload, away),
        mcp_urls={"ours": urls[0], "theirs": urls[1]},
        llm_model=str(ours.payload.get("llm_model", "")),
        token_cap=int(config.get("network_and_league.token_budget_per_series", 0)),
        step_zero={
            "ours": {"payload": ours.payload, "sha256": ours.digest},
            # **Recomputed over what they actually sent, not quoted from them.**
            # The handshake carries their payload and no digest of it, and a
            # digest a peer supplies for its own declaration proves nothing. This
            # one is ours to stand behind: it is the value their bytes hash to.
            "theirs": {"payload": away, "sha256": digest(away) if away else ""},
        },
    )


def _teams(ours: dict[str, Any], theirs: dict[str, Any]) -> dict[str, list[str]]:
    """Return ``{team: [member, ...]}`` for both sides, ours first.

    An opponent running an older peer sends no `members` key, and that is read
    as an empty list rather than refused: the roster is a reporting field, and
    losing a graded match over one would be the wrong trade entirely.
    """
    named: dict[str, list[str]] = {
        str(ours.get("team_name", "")) or "ours": list(ours.get("members", []))
    }
    label = str(theirs.get("team_name", "")) or "opponent"
    named[label] = list(theirs.get("members", []))
    return named
