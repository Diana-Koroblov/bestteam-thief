"""The signed declaration exchanged before the first move (TODO 6.3.2, M#24, M#53).

Both peers publish who they are, what they are running on, and **which commit
they are running** — then hash the whole thing. Two purposes, and the second is
the one that actually protects us:

* It makes the match reproducible. A grader reading the report can see the exact
  code, model and hardware that produced every move.
* It **pins the code for the whole series**. `github_commit` is inside the
  digest, so a peer cannot quietly swap in a different agent between sub-games
  and still match the declaration it signed at Step-0 (M#53).

**A dirty working tree is reported, not hidden** (6.3.3). If uncommitted changes
exist, the declared commit does not describe the code that is actually running,
and the whole reproducibility claim is false. Better to say so before the match
than to have a grader discover it afterwards.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from core.crypto.canonical import digest
from core.shared.git_ops import GitCommandError, has_pending_changes, run_git
from core.shared.system_info import describe
from core.shared.version import VERSION

__all__ = ["StepZero", "build", "commit_hash", "DIRTY_SUFFIX"]

# Appended to the commit when the tree has uncommitted changes, so the value is
# still a usable identifier while being unmistakably not a clean commit.
DIRTY_SUFFIX = "-dirty"


@lru_cache(maxsize=8)
def commit_hash(repo: Path) -> str:
    """Return the current commit, suffixed when the tree is dirty.

    Returns ``"unknown"`` if git is unavailable — a peer running from a
    downloaded archive rather than a clone can still play, and refusing would
    turn a reporting gap into a forfeit.

    **Cached, and that is a correctness choice as much as a speed one.** This
    shells out to git twice, and Step-0 runs six times per series; the test
    suite exposed the cost by calling it repeatedly and slowing to a crawl. More
    importantly, the commit we declare must be *the same value all series* —
    re-reading it mid-match could produce a different answer than the one we
    signed, and the digest would stop describing the running code.
    """
    try:
        head = run_git(["rev-parse", "HEAD"], cwd=repo).strip()
    except (GitCommandError, OSError):
        return "unknown"
    try:
        return head + DIRTY_SUFFIX if has_pending_changes(repo) else head
    except (GitCommandError, OSError):
        return head


@dataclass(frozen=True)
class StepZero:
    """One peer's declaration, and the digest that seals it.

    Attributes:
        payload: Everything declared, as plain JSON-safe values.
        digest: SHA-256 over the canonical form. Exchanged and compared; a peer
            whose later behaviour contradicts it can be shown to have changed.
    """

    payload: dict
    digest: str

    @property
    def dirty(self) -> bool:
        """Whether this peer declared uncommitted changes."""
        return str(self.payload.get("github_commit", "")).endswith(DIRTY_SUFFIX)

    def warnings(self) -> list[str]:
        """Everything a human should see before agreeing to start.

        Returned rather than raised. Whether to play a graded match against an
        unverifiable opponent is a judgement for the people involved, not a
        decision for a dataclass.
        """
        found = []
        if self.dirty:
            found.append(
                "working tree is DIRTY - the declared commit does not describe "
                "the running code, so the match is not reproducible"
            )
        if self.payload.get("github_commit") == "unknown":
            found.append("no git commit available - code version cannot be pinned")
        return found


def build(
    team_name: str,
    role: str,
    sub_game: int,
    llm_model: str,
    repo: Path,
    members: tuple[str, ...] = (),
) -> StepZero:
    """Assemble and seal this peer's Step-0 declaration.

    Args:
        team_name: Ours, as agreed with the league.
        members: Who is on this team. Declared because the pre-game declaration
            artefact must name *"the identity of both groups and their members"*
            (Ch. 9.3.3), and this exchange is the only channel that carries the
            opponent's. Additive: a peer that sends none is read as an empty
            list, not refused.
        role: ``cop`` or ``thief`` for this sub-game.
        sub_game: 1-6. Inside the digest, so a declaration signed for sub-game 1
            cannot be replayed as sub-game 4 — the same replay hole the audit
            closes for moves (6.1.4).
        llm_model: The provider's model name. **Not the provider**, which
            Appendix F keeps private to each peer.
        repo: Repository root, for the commit hash.
    """
    payload = {
        "team_name": team_name,
        "members": list(members),
        "role": role,
        "sub_game": sub_game,
        "llm_model": llm_model,
        "code_version": VERSION,
        "github_commit": commit_hash(repo),
        "hardware": describe(),
    }
    return StepZero(payload=payload, digest=digest(payload))
