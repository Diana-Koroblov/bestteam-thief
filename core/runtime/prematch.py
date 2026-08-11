"""The facts this machine declares before the first move (TODO 9.1).

Split from `peer_runtime.py` on the same seam `local_truth.py` was: that file is
the **inbound state machine**, this one is what we *declare* about ourselves —
which commit we run, how many counted matches we have played, which model speaks
for us, and which readings of the ambiguous rules our code actually implements.

`core/protocol/negotiation.py` deliberately knows none of this. It compares two
messages and nothing else, so every refusal in it can be provoked by a test
holding two dataclasses. Reading git, the league log and the provider registry is
a different job, and it is this one.

**Nothing here is a parameter a human types.** The counted-match total comes from
`docs/LEAGUE_LOG.md`, the commit from `git rev-parse`, the model from the
provider that will actually be called. M#38 disqualifies the entire project for
one wrong declaration, and the way that happens to an honest team is a stale
number in a config file, not fraud.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from core.crypto.canonical import digest
from core.crypto.scent_model import scent_model_of
from core.infra.llm.factory import model_name
from core.protocol import readings as readings_module
from core.protocol.agreement import LockedAgreement
from core.protocol.negotiation import proposal, refused_by_opponent, settle
from core.protocol.schemas import Negotiation
from core.protocol.step_zero import StepZero, build
from core.runtime.orchestrator import Orchestrator
from core.shared import league_log

__all__ = ["PreMatch", "REPO_ROOT"]

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class PreMatch:
    """This peer's side of the handshake, and the agreement it produced.

    Attributes:
        orchestrator: Owns the configuration everything below is derived from.
        role_split: How the sub-games divide. Configurable because it is
            negotiated per match and 3-3 is our proposal, not a rule (N17).
        sub_game: Which sub-game the Step-0 declaration is signed for. Inside
            the digest, so a declaration signed for one cannot be replayed as
            another (M#24).
        agreement: Set once `settle` has run. ``None`` means no handshake has
            completed and no move may be computed (PRD_negotiation §5).
    """

    orchestrator: Orchestrator
    repo: Path = REPO_ROOT
    league_log_path: Path = league_log.DEFAULT_PATH
    role_split: str = "3-3"
    sub_game: int = 1
    agreement: LockedAgreement | None = None
    _proposal: Negotiation | None = field(default=None, repr=False)
    _step_zero: StepZero | None = field(default=None, repr=False)

    @property
    def config(self):
        """The merged configuration this peer plays under."""
        return self.orchestrator.config

    def counted_matches(self) -> int:
        """Return the honest counted-match total to declare (M#37, N8).

        Raises:
            LeagueLogError: The log is unreadable or contradicts itself.
                **Propagated, never defaulted.** A handshake that quietly
                declared 0 because it could not find the table would be making
                precisely the claim M#38 disqualifies the project for.
        """
        return league_log.counted_matches(self.league_log_path)

    def step_zero(self) -> StepZero:
        """Return this peer's signed declaration (M#24, M#53, TODO 9.1.4).

        Built once. `system_info.describe` shells out to `wmic` and `nvidia-smi`
        with a five-second timeout each, and this is called by both `proposal`
        and `warnings` — but speed is the lesser reason. The declaration we warn
        a human about has to be the *same bytes* we signed and sent, and a
        function that rebuilds it is a function that can answer differently.
        """
        if self._step_zero is None:
            self._step_zero = build(
                team_name=str(self.config.get("identity.team_name", "")),
                members=tuple(self.config.get("identity.members", ())),
                role=self.orchestrator.role.value,
                sub_game=self.sub_game,
                llm_model=model_name(self.config),
                repo=self.repo,
            )
        return self._step_zero

    def scent_model(self) -> dict[str, Any]:
        """Return the scent agreement, worked example included (M#23, 9.1.2)."""
        return scent_model_of(self.config)

    def proposal(self) -> Negotiation:
        """Return what we send, building it once.

        **Cached for the same reason `step_zero.commit_hash` is.** What we
        declare must be one value all series; rebuilding it mid-match could
        answer differently from the message the opponent already holds, and the
        agreement would stop describing the peer that signed it.

        Raises:
            ValueError: `role_split` was changed after the proposal was built.
                Silently returning the cached message would leave the opponent
                holding one split while we believed another — the exact C-011
                failure the field exists to prevent, reintroduced by the object
                that was supposed to prevent it. Set it before the first call.
        """
        if self._proposal is not None and self._proposal.role_split != self.role_split:
            raise ValueError(
                f"the role split changed from {self._proposal.role_split!r} to "
                f"{self.role_split!r} after the handshake was built and possibly sent"
            )
        if self._proposal is None:
            self._proposal = proposal(
                config=self.config,
                role=self.orchestrator.role,
                games_played=self.counted_matches(),
                scent_digest=digest(self.scent_model()),
                step_zero=self.step_zero().payload,
                role_split=self.role_split,
            )
        return self._proposal

    def settle(self, theirs: Negotiation) -> LockedAgreement:
        """Compare the opponent's handshake with ours and record the outcome.

        The scent model and the clause are attached **here** rather than inside
        `negotiation.settle`, which is deliberately unable to read a config. They
        belong in the record because a digest proves that two peers agreed and
        says nothing about what they agreed to — and the artefact is what gets
        read months later by someone who was not in the conversation.
        """
        return self._record(settle(self.proposal(), theirs))

    def refused(self, detail: str) -> LockedAgreement:
        """Record a handshake the **opponent** refused (TODO 9.1.1).

        Only one side of this exchange gets a verdict: the answering peer raises
        and the initiating one receives a remote error string. That side still
        has to file a record, because a refusal is the outcome most likely to be
        argued about later — and "we tried and they said no" with a timestamp
        and their own wording is a very different position from silence.
        """
        return self._record(refused_by_opponent(self.proposal(), detail))

    def _record(self, locked: LockedAgreement) -> LockedAgreement:
        """Attach what was agreed to the verdict, and keep it."""
        self.agreement = replace(
            locked, scent_model=self.scent_model(), clause=self.clause()
        )
        return self.agreement

    def clause(self) -> str:
        """Return the agreement paragraph to send the opponent (9.1.6).

        Generated from the live configuration rather than quoted from the PRD,
        so the sentence an opponent agrees to and the flags we play under cannot
        say different things.
        """
        return readings_module.clause(self.config)

    def warnings(self) -> list[str]:
        """Everything a human must resolve before agreeing to play.

        The league log's own warnings are folded in here rather than raised: an
        eleventh counted match is a rule breach, but a peer mid-handshake is the
        wrong place to discover it and the wrong thing to crash over.
        """
        found = list(league_log.read(self.league_log_path).warnings())
        found.extend(self.step_zero().warnings())
        found.extend(self._contract_warnings())
        if self.agreement is not None:
            found.extend(self.agreement.warnings)
        return found

    def _contract_warnings(self) -> list[str]:
        """Warn when the shared contract does not yet name both parties.

        Appendix B.3 opens the file with `agreed_between`, and ours ships naming
        only us because a committed default cannot know who we will play. That
        is correct for a proposal and wrong for a signed contract — and the
        difference is invisible at match time, since nothing in the code reads
        the field. It is read here instead, once, by a human, before agreeing.
        """
        named = self.config.agreed_between
        if len(named) >= 2:
            return []
        ours = ", ".join(named) or "nobody"
        return [
            f"agreed_between names {ours}; add the opponent's team id before signing, "
            "so the config snapshot filed after the match records who agreed to it "
            "(Appendix B.3)"
        ]
