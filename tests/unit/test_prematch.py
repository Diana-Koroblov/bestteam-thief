"""The facts this machine declares about itself (TODO 9.1.2-9.1.4).

`negotiation.py` compares two messages and knows nothing about the world.
Everything the world contributes — the commit, the counted-match total, the
model that will actually speak — is gathered here, and each one of those is a
value M#38 disqualifies the project for getting wrong.

So the tests below are about **provenance** rather than arithmetic: that the
number came from the log and not from a default, that the model name came from
the provider that will really be called, and that the reply we send an opponent
is what we independently believe rather than an echo of what they sent us.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from core.protocol.schemas import Negotiation, Role
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from core.runtime.prematch import PreMatch
from core.shared.league_log import LeagueLogError

LOG = """# League Log

## Counted matches

| # | Date | Opponent team | Our role |
|---|---|---|---|
| 1 | 2026-08-09 | redteam | cop |
| 2 | 2026-08-10 | blueteam | thief |

**Counted matches so far: 2**
"""


@pytest.fixture
def league(tmp_path):
    """A log declaring two counted matches, so 0 cannot pass by accident."""
    path = tmp_path / "LEAGUE_LOG.md"
    path.write_text(LOG, encoding="utf-8")
    return path


@pytest.fixture
def prematch(minimal_config, league) -> PreMatch:
    return PreMatch(
        orchestrator=Orchestrator.from_config(minimal_config, Role.COP), league_log_path=league
    )


# --- 9.1.3: the number is read, never typed ----------------------------------


def test_the_declared_total_comes_from_the_log(prematch: PreMatch) -> None:
    """M#37, N8. The handshake and the document a grader reads are the same
    source, so a false declaration takes editing the evidence rather than
    mistyping a digit — and mistyping a digit is how honest teams get
    disqualified."""
    assert prematch.proposal().game_count == 2


def test_an_unreadable_log_refuses_rather_than_declaring_zero(minimal_config, tmp_path) -> None:
    """**Zero is a legitimate declaration today**, so a fallback would be
    indistinguishable from a working parser right up until the match where it
    mattered. M#38 disqualifies the entire project for that one value."""
    peer = PreMatch(
        orchestrator=Orchestrator.from_config(minimal_config, Role.COP),
        league_log_path=tmp_path / "absent.md",
    )
    with pytest.raises(LeagueLogError):
        peer.proposal()


# --- 9.1.4: the declaration ---------------------------------------------------


def test_the_declaration_names_the_model_that_will_actually_speak(
    prematch: PreMatch, monkeypatch
) -> None:
    """**A real defect this closes.** The only previous caller read
    `llm.ollama_model` directly, so a machine whose `.env` selected template or
    groq declared Ollama regardless. Appendix F Table 21 makes the *model* the
    declared thing and the *provider* private, so naming a model we never called
    is a false declaration, not a cosmetic one.
    """
    monkeypatch.setenv("P2P_LLM_PROVIDER", "ollama")
    assert prematch.step_zero().payload["llm_model"] == "llama3.1:8b"
    monkeypatch.setenv("P2P_LLM_PROVIDER", "template")
    assert PreMatch(
        orchestrator=prematch.orchestrator, league_log_path=prematch.league_log_path
    ).step_zero().payload["llm_model"] == "template"


def test_the_declaration_carries_the_commit_and_the_role(prematch: PreMatch) -> None:
    """M#53 pins the code for the whole series."""
    payload = prematch.step_zero().payload
    assert payload["role"] == "cop" and payload["github_commit"]
    assert payload["team_name"] == "bestteam"


def test_the_declaration_rides_inside_the_handshake(prematch: PreMatch) -> None:
    """9.1.4's DoD is that they are *exchanged*. A declaration built and never
    sent is the same failure as a strategy wired to nothing."""
    assert prematch.proposal().step_zero["github_commit"]


# --- what must not change mid-series ------------------------------------------


def test_the_proposal_is_built_once(prematch: PreMatch) -> None:
    """What we declare must be one value all series. Rebuilding it could answer
    differently from the message the opponent already holds, and the agreement
    would stop describing the peer that signed it — the same reason
    `step_zero.commit_hash` is cached."""
    assert prematch.proposal() is prematch.proposal()


def test_settling_records_the_agreement(prematch: PreMatch) -> None:
    """Nothing may be computed against an unagreed configuration
    (PRD_negotiation §5), so "have we agreed" has to be answerable."""
    assert prematch.agreement is None
    locked = prematch.settle(replace(prematch.proposal(), role=Role.THIEF))
    assert prematch.agreement is locked and locked.agreed


def test_warnings_gather_from_every_source(minimal_config, tmp_path) -> None:
    """A human reads **one** list before agreeing to play, not three.

    Three independent sources are made to complain at once: the log (the same
    opponent twice, M#52), the handshake (they sent no Step-0, M#24) and the
    role split nobody stated (C-011). A `warnings()` that surfaced only the
    source it happened to check first would leave two of them for the opponent
    to discover mid-match, where M#35 makes them unresolvable.
    """
    path = tmp_path / "duplicate.md"
    path.write_text(LOG.replace("blueteam", "redteam"), encoding="utf-8")
    peer = PreMatch(
        orchestrator=Orchestrator.from_config(minimal_config, Role.COP), league_log_path=path
    )
    peer.settle(replace(peer.proposal(), role=Role.THIEF, step_zero={}, role_split=""))
    found = " | ".join(peer.warnings())
    assert "M#52" in found and "no Step-0 declaration" in found and "no role split" in found


# --- the reply the opponent receives ------------------------------------------


def test_the_reply_is_our_proposal_and_not_an_echo(minimal_config, league) -> None:
    """**The defect this phase fixed.** `on_negotiate` used to return the
    opponent's own `game_count`, `role_split` and `readings` straight back at
    them, so the exchange could not detect any of the disagreements it exists to
    detect: agreement was guaranteed, because we repeated whatever arrived.
    """
    peer = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.COP))
    peer.prematch = PreMatch(orchestrator=peer.orchestrator, league_log_path=league)
    # Everything an opponent may legitimately send that differs from ours: a
    # count of their own, and silence on the two fields Appendix F never
    # mentions. None of these refuses — which is what makes the echo visible.
    theirs = Negotiation(
        step=0,
        role=Role.THIEF,
        config_digest=minimal_config.shared_digest(),
        game_count=99,
        role_split="",
        readings={},
    )
    reply = peer.on_negotiate(theirs)
    assert peer.agreed
    assert reply.game_count == 2, "we declare what our log says, not what theirs does"
    assert reply.role_split == "3-3", "silence from them is not agreement to nothing"
    assert reply.readings["capture.resolution"] == "after_moves"


def test_a_refusal_still_stops_the_match(minimal_config, league) -> None:
    """M#11 through the runtime, not just the comparison function."""
    from core.protocol.tools import ProtocolError

    peer = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.COP))
    peer.prematch = PreMatch(orchestrator=peer.orchestrator, league_log_path=league)
    with pytest.raises(ProtocolError, match="REFUSED_CONFIG_MISMATCH"):
        peer.on_negotiate(Negotiation(step=0, role=Role.THIEF, config_digest="wrong"))
    assert not peer.agreed


def test_changing_the_role_split_after_sending_is_refused(prematch: PreMatch) -> None:
    """**A seam that would only ever have been noticed at the worst moment.**
    The CLI sets `role_split` on this object before building the proposal; a
    caller that set it afterwards would get the cached message back unchanged
    and believe a split the opponent never received. That is C-011 exactly,
    reintroduced by the object written to prevent it — so it raises instead.
    """
    prematch.role_split = "4-2"
    assert prematch.proposal().role_split == "4-2"
    prematch.role_split = "2-4"
    with pytest.raises(ValueError, match="changed from '4-2' to '2-4'"):
        prematch.proposal()


def test_the_agreement_records_what_was_agreed_not_only_that_it_was(
    prematch: PreMatch,
) -> None:
    """**A digest proves agreement and says nothing about its content.**

    The artefact is committed beside the match log (9.3.5) and read later by
    someone who was not in the conversation — a grader, or an opponent
    disputing a result. So it carries the scent model itself (including
    `sampling_mode`, 9.1.7) and the clause both sides settled in writing
    (9.1.6), not just the hashes that pin them.
    """
    payload = prematch.settle(replace(prematch.proposal(), role=Role.THIEF)).payload()
    assert payload["scent_model"]["sampling_mode"] == "end_of_previous_full_turn"
    assert payload["scent_model"]["worked_example"]["after_one_turn"] == 0.81
    assert "vacated does not capture" in payload["agreed_clause"]
    assert payload["scent_model_sha256"], "the hash still pins the payload beside it"
