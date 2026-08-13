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
from core.domain.rules import Rules
from core.protocol.schemas import Role
from core.runtime.filing import MatchFiling
from core.runtime.match_driver import MatchDriver
from core.runtime.peer_runtime import PeerRuntime
from core.runtime.series import SeriesRunner, SubGameReport

__all__ = ["driver_factory", "filing_for", "declare", "forfeit", "refuse"]


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
    # Set on the filing, not passed to this call, because `result()` needs the
    # same four links (M#49) and is written by a different method at a different
    # time. One assignment covers both artefacts.
    filing.repos = _repos(ours.payload, away)
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


def forfeit(filing: MatchFiling, plan: list, table: Any, reason: str) -> None:
    """File the sub-games we planned but never played, as technical losses.

    🐛 **A refused handshake used to file nothing at all, and that is an M#35
    hazard rather than a tidy exit.** Observed in a real localhost match: our
    peer's outbound handshake failed while its *inbound* server had already
    agreed, so the opponent played its half against a peer that had given up. It
    correctly scored three technical losses and filed a six-row report. We filed
    three rows — because the process exited before `_series` ever built a filing.

    Two teams, one match, two reports disagreeing about how many sub-games
    happened. A contradictory pair voids the match and scores **0 for both**,
    which is the rule that punishes the honest side for the paperwork.

    A technical loss is already 0-0, so filing them costs nothing in points and
    buys the one thing that matters: a report that says the same as theirs. It
    is also the honest record — those sub-games really did not happen, and
    saying so beats silence, which a grader cannot distinguish from a team that
    never turned up.
    """
    reports = [
        SubGameReport(
            sub_game=number, role=role, outcome=Rules.technical_loss(reason), steps=0
        )
        for number, role in plan
    ]
    SeriesRunner(build=None, plan=[], table=table, filing=filing, reports=reports).finish()


def refuse(sdk: Any, args: Any, theirs: Any, locked: Any, plan: list) -> str:
    """File a match the handshake never settled, and describe what was written.

    Lives here rather than in the CLI for the reason `filing_for` does: every
    value comes from the handshake that just failed, and the CLI's job is to
    print the sentence this returns.

    With no ``--out`` there is nowhere to file and nothing to reconcile, which is
    the rehearsal case; the refusal is then just a non-zero exit.
    """
    from core.report.identifiers import game_id

    if not args.out:
        return "  no --out, so nothing was filed"
    declared = getattr(theirs, "step_zero", None) or {}
    identifier = game_id(
        sdk.team_name, str(declared.get("team_name", "")) or "opponent", locked.agreed_at[:10]
    )
    filing = filing_for(sdk.runtime, identifier, Path(args.out), locked)
    declare(filing, sdk.runtime, (getattr(args, "our_url", ""), args.opponent), theirs)
    forfeit(filing, plan, sdk.scoring, f"handshake not agreed: {locked.result}")
    return (
        f"artefacts       : {len(filing.written)} files in {filing.directory}\n"
        "  filed as technical losses so our report matches theirs (M#35)"
    )


def _repos(ours: dict[str, Any], theirs: dict[str, Any]) -> dict[str, str]:
    """Return the four repository links Ch. 9.4 requires in the closing JSON.

    🐛 **These were four empty strings in every artefact we filed.**
    `MatchFiling.repos` was never populated by anything outside the test suite,
    so a real match reported `{"ours_cop": "", ...}` against a rule that asks for
    *"group A's two links and group B's two links"* (M#49).

    They could not even have been filled in: the URLs lived only in README prose
    and the handshake never exchanged them. Ours now come from `[identity]` and
    the opponent's ride in their Step-0 payload, read with `.get` so a peer that
    sends none is recorded as blank rather than refused.
    """
    mine = ours.get("repos") or {}
    yours = theirs.get("repos") or {}
    return {
        "ours_cop": str(mine.get("cop", "")),
        "ours_thief": str(mine.get("thief", "")),
        "theirs_cop": str(yours.get("cop", "")),
        "theirs_thief": str(yours.get("thief", "")),
    }


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
