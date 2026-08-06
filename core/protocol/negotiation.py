"""Settling a match before the first move (PRD_negotiation §4, TODO 9.1).

Two teams who have never met, do not trust each other and have no arbiter must
agree the physics of a match and be able to *prove* they agreed it. This module
is that comparison, and nothing else: it takes two `Negotiation` messages and
returns a `LockedAgreement` saying whether play may start and why.

**Deliberately free of the environment.** The commit hash, the counted-match
total and the model name are facts about a machine, not about the protocol, and
they are gathered next door in `core/runtime/prematch.py`. Keeping them out means
every refusal in this file can be provoked by a test with two plain dataclasses.

**Missing is not mismatched, and the distinction decides fixtures.** Half of what
travels here — the scent digest, the readings, the role split — is our own
extension of Appendix F. A peer that never built those fields is not
contradicting us; refusing them would forfeit a match over a rule the book does
not state (PRD_negotiation §3.6b). A peer that *did* send one and disagrees is a
different matter entirely, and refuses. Silence warns, contradiction refuses.
"""

from __future__ import annotations

from typing import Any

from core.protocol import readings as readings_module
from core.protocol.agreement import (
    AGREED,
    REFUSED_BY_OPPONENT,
    REFUSED_CONFIG_MISMATCH,
    REFUSED_READING_MISMATCH,
    REFUSED_ROLE_SPLIT,
    REFUSED_SCENT_MISMATCH,
    LockedAgreement,
    utc_now,
)
from core.protocol.schemas import Negotiation, Role

__all__ = ["proposal", "settle", "refused_by_opponent", "DIRTY_MARKERS"]

# A commit that ends in either of these does not describe the running code, so
# the reproducibility M#53 exists for is not there to be had.
DIRTY_MARKERS = ("-dirty", "unknown")


def proposal(
    config,
    role: Role,
    games_played: int,
    scent_digest: str,
    step_zero: dict[str, Any],
    role_split: str = "3-3",
) -> Negotiation:
    """Return the handshake this peer sends.

    Args:
        games_played: Counted matches already played, declared honestly (M#37).
            **No default.** A parameter that defaulted to zero would make the
            single most dangerous value in the protocol the one you get by
            forgetting it, and M#38 disqualifies the whole project for it.
        scent_digest: From `crypto.scent_model`, sealing the decay formula and
            the sampling mode rather than just naming them (M#23).
        step_zero: The signed declaration, carrying `github_commit` (M#53).
        role_split: How the sub-games divide. Stated rather than assumed — it is
            in no Appendix, so silence means two teams assuming different
            things (C-011, N17).
    """
    if games_played < 0:
        raise ValueError(f"a counted-match total cannot be negative, got {games_played}")
    return Negotiation(
        step=0,
        role=role,
        config_digest=config.shared_digest(),
        scent_model_digest=scent_digest,
        game_count=games_played,
        role_split=role_split,
        readings=readings_module.readings_of(config),
        step_zero=dict(step_zero),
    )


def refused_by_opponent(ours: Negotiation, detail: str) -> LockedAgreement:
    """Return the record for a handshake **they** refused (M#11, M#35).

    Their reason is preserved verbatim rather than re-worded. It is the only
    account we will ever have of why they said no, and with no referee it is
    also the only thing either of us can quote while working out which side is
    actually wrong.
    """
    return LockedAgreement(
        result=REFUSED_BY_OPPONENT,
        config_sha256=ours.config_digest,
        scent_model_sha256=ours.scent_model_digest,
        our_games_played=ours.game_count,
        our_commit=str(ours.step_zero.get("github_commit", "")),
        role_split=ours.role_split,
        readings=dict(ours.readings),
        reasons=(detail,),
        agreed_at=utc_now(),
    )


def _commit_warnings(label: str, declaration: dict[str, Any]) -> list[str]:
    """Return what is wrong with one peer's Step-0 declaration (9.1.4, M#53)."""
    if not declaration:
        return [f"{label} sent no Step-0 declaration, so no commit is pinned for the series (M#24)"]
    commit = str(declaration.get("github_commit", ""))
    if not commit:
        return [f"{label} declared no github_commit, so the code played cannot be named (M#53)"]
    if any(commit.endswith(marker) or commit == marker for marker in DIRTY_MARKERS):
        return [
            f"{label} declared commit {commit!r}: the declared commit does not describe "
            "the running code, so the match is not reproducible"
        ]
    return []


def settle(ours: Negotiation, theirs: Negotiation) -> LockedAgreement:
    """Compare two proposals and return whether the match may start.

    The order is not cosmetic. The config digest is checked first because a
    mismatch there means every later comparison is between peers reading
    different rulebooks, and reporting four disagreements when there is really
    one would send an opponent hunting in the wrong place.
    """
    reasons: list[str] = []
    warnings: list[str] = []
    result = AGREED

    if ours.config_digest != theirs.config_digest:
        result = REFUSED_CONFIG_MISMATCH
        reasons.append(
            f"config digest mismatch: ours {ours.config_digest[:16]}..., theirs "
            f"{theirs.config_digest[:16]}... - refusing rather than playing two "
            "different rulebooks (M#11)"
        )
    elif not theirs.scent_model_digest:
        warnings.append(
            "the opponent stated no scent model digest; the decay formula and the "
            "sampling mode are unsealed and must be agreed in writing (M#23, C-007)"
        )
    elif ours.scent_model_digest != theirs.scent_model_digest:
        result = REFUSED_SCENT_MISMATCH
        reasons.append(
            "scent model mismatch: identical configs but different emission, decay or "
            "sampling. Compare the worked example - 0.810 is the book, 0.800 is the "
            "reference simulator (M#23, C-007)"
        )

    if result == AGREED:
        conflicts = readings_module.disagreements(ours.readings, theirs.readings)
        if conflicts:
            result = REFUSED_READING_MISMATCH
            reasons.extend(conflicts)
        elif missing := readings_module.unsigned(ours.readings, theirs.readings):
            warnings.append(f"the opponent stated no reading for: {', '.join(missing)}")

    if result == AGREED:
        if not theirs.role_split:
            warnings.append(
                f"the opponent stated no role split; we assume {ours.role_split} and the "
                "scoring analysis depends on it (N17, C-011)"
            )
        elif ours.role_split != theirs.role_split:
            result = REFUSED_ROLE_SPLIT
            reasons.append(
                f"role split mismatch: we propose {ours.role_split}, they propose "
                f"{theirs.role_split} - not in any Appendix, so it must be stated (N17)"
            )

    warnings.extend(_commit_warnings("we", ours.step_zero))
    warnings.extend(_commit_warnings("the opponent", theirs.step_zero))
    return LockedAgreement(
        result=result,
        config_sha256=ours.config_digest,
        scent_model_sha256=ours.scent_model_digest,
        our_games_played=ours.game_count,
        their_games_played=theirs.game_count,
        our_commit=str(ours.step_zero.get("github_commit", "")),
        their_commit=str(theirs.step_zero.get("github_commit", "")),
        role_split=ours.role_split,
        readings=dict(ours.readings),
        reasons=tuple(reasons),
        warnings=tuple(warnings),
        agreed_at=utc_now(),
    )
