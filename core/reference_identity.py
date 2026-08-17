"""What we declare about ourselves on the reference wire.

Split from `cli_compat.py` under the 150-line ceiling (ADR-005) when the missing
commit field below pushed it over. The seam is a real one: that module decides
*how a series is played*, this one states *who is playing it* — the block both
peers publish at every handshake and file into their artefacts.

**A gateway module, and it has to be.** `model_name` reads the provider registry
in `core.infra` and `counted_matches` reads the league log in `core.shared`;
`core/compat/` may reach into neither, because joining two subsystems is the
gateway's job and nobody else's (M#3). So this sits beside `cli_compat` at the
`core/` level rather than inside `core/compat/`.

**Every field here is read, never typed.** The commit comes from git, the counted
total from `docs/LEAGUE_LOG.md`, the model from the provider that will actually
be called. A declaration is a claim an opponent files against us and a grader
reads afterwards, and the way an honest team gets one wrong is a stale literal,
not fraud — M#38 disqualifies the whole project for a wrong counted total.
"""

from __future__ import annotations

import argparse

from core.infra.llm.factory import model_name
from core.protocol.step_zero import commit_hash
from core.runtime.prematch import REPO_ROOT
from core.sdk.peer_sdk import PeerSDK
from core.shared.declared_head import UnpublishedHeadError, describe_declared_head
from core.shared.league_log import counted_matches

__all__ = ["identity_of", "declared_head"]


def declared_head(args: argparse.Namespace) -> str:
    """Return the head this process will declare, refusing one nobody can fetch.

    Printed by the caller rather than merely checked. imreeyal's counted bar is
    that the head which plays is pushed before the T *and declared in the
    thread*, and a value you have to go and derive after the fact is one that
    gets typed from memory.

    🐛 **Three windows of ours declared `55ddff06…`**, which is `p2p-chase`'s
    HEAD — a tree with no remote at all, so the hash resolved for nobody and
    could not be made to. The published code sat under two other heads the whole
    time; the only fault was the directory each process was launched from, which
    is the kind of mistake a pre-flight catches and a written procedure does not.
    """
    commit = commit_hash(REPO_ROOT)
    try:
        return describe_declared_head(REPO_ROOT, commit)
    except UnpublishedHeadError as error:
        if getattr(args, "allow_local_head", False):
            return f"{commit}\n  ! LOCAL ONLY - {error}"
        raise SystemExit(
            f"refusing to arm: {error}\n\n"
            "  Pass --allow-local-head for a drill against ourselves, where the artefact\n"
            "  never leaves this machine and the hash is nobody's evidence."
        ) from error


def identity_of(sdk: PeerSDK) -> dict:
    """Return the identity block both sides publish at every handshake.

    🐛 **`github_commit` was absent entirely until 16/08** — not blank, not
    stale: the key was never sent. The native path pins the commit through
    `step_zero` (M#53), and this path simply had no field for it, so imreeyal's
    artefacts recorded ``unknown`` against us across two match attempts and
    neither side could have named the code that ran. A declaration that omits
    the one value making a result reproducible is worse than one that admits it
    does not know, because nobody notices the omission.
    """
    config = sdk.runtime.orchestrator.config
    return {
        "group_id": sdk.team_name,
        "group_name": sdk.team_name,
        "members": list(config.get("identity.members", ()) or ()),
        "repos": {
            "cop": str(config.get("identity.repo_cop", "")),
            "thief": str(config.get("identity.repo_thief", "")),
        },
        "llm_model": model_name(config),
        "github_commit": commit_hash(REPO_ROOT),
        "counted_games_played": counted_matches(),
    }
