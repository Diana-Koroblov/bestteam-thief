"""Writing the reference path's artefacts to disk (`core/runtime/filing.py`'s twin).

`core/compat/reporting.py` files the *result*; this builds and writes the three
artefacts that prove it. They were missing entirely until 17/08 — see
`core/compat/match_log.py` for what that cost — so the seam is drawn where the
native path already draws it: the report is one job, the evidence beside it is
another.

**One artefact per call, and no opinion about when.** Which files a finished
sub-game owes, in what order, and what to do when one cannot be written all
live in `core/compat/closing.py`; these two functions only know how to produce
the file they are named for.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.compat.match_log import build_sub_game_log
from core.compat.wire import SCENT_MODEL_SHA256, wire_role
from core.report.artefacts import build_config_snapshot, build_declaration, write

__all__ = ["file_sub_game", "file_declaration"]


def file_sub_game(
    *,
    out: Path,
    game_identifier: str,
    session: Any,
    sdk: Any,
    number: int,
    outcome: str,
    our_group: str,
    their_group: str,
    role_split: str = "",
) -> list[Path]:
    """File the config snapshot and the log for one finished sub-game.

    Both, together, and in that order — the native path's rule, for its reason:
    *"a log without its config is a list of moves nobody can score"*.

    The snapshot is written with **no** ``agreed_digest``. This protocol signs
    the fourteen flat terms, not the whole `game.json`, so the two peers never
    exchange a config digest at all; passing ours as the agreed one would put a
    number in an artefact that nobody ever agreed to, which is exactly the
    invented value `core/report/artefacts.py` refuses to write.

    ``role_split`` and ``scent_model_digest`` used to file as empty strings:
    this call passed neither, while the native path has always passed both.
    The scent digest is the one we declare on the wire — a lookup keyed on the
    negotiated ``pheromones.decay_model``, resolved the same way
    ``core/compat/session.py`` resolves it — not the internal formula digest
    in ``core/crypto/scent_model.py``, which is a different object.
    """
    config = sdk.runtime.orchestrator.config
    role = wire_role(session.role.value)
    model = str(config.get("pheromones.decay_model", "multiplicative"))
    snapshot = build_config_snapshot(
        game_identifier=game_identifier,
        sub_game=number,
        shared_config=config.shared,
        role=role,
        role_split=role_split,
        scent_model_digest=SCENT_MODEL_SHA256.get(model, ""),
    )
    log = build_sub_game_log(
        game_identifier=game_identifier,
        sub_game=number,
        our_group=our_group,
        their_group=their_group,
        our_role=role,
        our_records=session.records,
        their_records=session.their_records,
        live_commits=session.received,
        outcome=outcome,
        config_sha256=snapshot["config_sha256"],
    )
    return [
        write(snapshot, out, f"config_{game_identifier}_g{number:02d}.json"),
        write(log, out, f"log_{game_identifier}_g{number:02d}.json"),
    ]


def file_declaration(
    *,
    out: Path,
    game_identifier: str,
    sdk: Any,
    our_identity: dict[str, Any],
    their_identity: dict[str, Any],
    their_group: str,
    their_url: str,
    started_utc: str = "",
    ended_utc: str = "",
) -> Path:
    """File ``declaration_<game_id>.json`` — what was fixed about the whole match.

    ``step_zero`` carries the two **identity blocks**, because on this wire that
    is what the peers actually exchanged and what our own first record seals
    (`core/compat/exchange.sealed_payload`). The native path's sealed hardware
    payload has no counterpart here, and filling the field with a plausible
    substitute would be worse than leaving it as what it really is.
    """
    config = sdk.runtime.orchestrator.config
    our_group = sdk.team_name
    ours = dict(our_identity.get("repos") or {})
    theirs = dict(their_identity.get("repos") or {})
    return write(
        build_declaration(
            game_identifier=game_identifier,
            teams={
                our_group: list(our_identity.get("members") or ()),
                their_group: list(their_identity.get("members") or ()),
            },
            repos={
                "ours_cop": str(ours.get("cop", "")),
                "ours_thief": str(ours.get("thief", "")),
                "theirs_cop": str(theirs.get("cop", "")),
                "theirs_thief": str(theirs.get("thief", "")),
            },
            mcp_urls={our_group: str(config.get("network.public_url", "")), their_group: their_url},
            llm_model=str(our_identity.get("llm_model", "")),
            token_cap=int(config.get("network_and_league.token_budget_per_series", 0) or 0),
            step_zero={"ours": dict(our_identity), "theirs": dict(their_identity)},
            started_utc=started_utc,
            ended_utc=ended_utc,
        ),
        out,
        f"declaration_{game_identifier}.json",
    )
