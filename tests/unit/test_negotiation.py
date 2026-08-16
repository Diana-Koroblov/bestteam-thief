"""Settling a match before the first move (TODO 9.1, PRD_negotiation §7).

The scenarios TN.1-TN.11 in `docs/PRD_negotiation.md`, plus the distinction the
PRD leaves implicit and which decides how many fixtures we get to play: **an
opponent's silence is not their disagreement.**

Half of what travels in this handshake — the scent digest, the readings, the role
split — is our own extension of Appendix F. A peer that never built those fields
is not contradicting us. Refusing them would cost a match over a rule the book
does not state; accepting them silently would let a contradiction reach the board,
where M#35 voids the result for *both* teams. So silence warns and contradiction
refuses, and each of those two paths is tested here separately.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from core.crypto.canonical import digest
from core.crypto.scent_model import scent_model_of, scent_model_payload
from core.protocol.agreement import (
    AGREED,
    REFUSED_BY_OPPONENT,
    REFUSED_CONFIG_MISMATCH,
    REFUSED_READING_MISMATCH,
    REFUSED_ROLE_SPLIT,
    REFUSED_SCENT_MISMATCH,
)
from core.protocol.negotiation import proposal, refused_by_opponent, settle
from core.protocol.schemas import Role

CLEAN = {"team_name": "bestteam", "github_commit": "a" * 40}
THEIRS = {"team_name": "redteam", "github_commit": "b" * 40}


@pytest.fixture
def ours(minimal_config):
    """Our handshake, with a clean tree and one counted match declared."""
    return proposal(
        config=minimal_config,
        role=Role.COP,
        games_played=1,
        scent_digest=digest(scent_model_of(minimal_config)),
        step_zero=CLEAN,
    )


@pytest.fixture
def mirror(ours):
    """An opponent running this same code, so everything matches."""
    return replace(ours, role=Role.THIEF, step_zero=THEIRS, game_count=3)


# --- TN.1: the happy path ----------------------------------------------------


def test_two_peers_running_this_code_agree(ours, mirror) -> None:
    locked = settle(ours, mirror)
    assert locked.agreed and locked.result == AGREED
    assert locked.warnings == (), "a clean handshake must leave nothing outstanding"


def test_the_agreement_records_both_declarations(ours, mirror) -> None:
    """M#37 and M#53 are per-match facts, and the file that records them is the
    one committed beside the log (9.3.5)."""
    locked = settle(ours, mirror)
    assert (locked.our_games_played, locked.their_games_played) == (1, 3)
    assert (locked.our_commit, locked.their_commit) == ("a" * 40, "b" * 40)


def test_the_payload_carries_the_warnings_and_not_only_the_verdict(ours) -> None:
    """A match played with three unsigned readings is a match whose result can
    be disputed, and the artefact committed with it should say so. Printing them
    to a terminal nobody kept is not a record."""
    theirs = replace(ours, role=Role.THIEF, readings={}, step_zero=THEIRS)
    payload = settle(ours, theirs).payload()
    assert payload["result"] == AGREED
    assert any("stated no reading" in item for item in payload["warnings"])


# --- TN.2: the config, which is checked first and alone ----------------------


def test_a_config_mismatch_refuses_the_match(ours, mirror) -> None:
    """M#11, N2. Not "warn and reconcile later": two rule sets produce two
    results and an unresolvable dispute."""
    locked = settle(ours, replace(mirror, config_digest="wrong"))
    assert locked.result == REFUSED_CONFIG_MISMATCH and not locked.agreed


def test_a_config_mismatch_is_reported_alone(ours) -> None:
    """**Ordering, and it is not cosmetic.** Peers holding different configs
    disagree about everything downstream too. Reporting four contradictions when
    there is really one sends an opponent hunting in the wrong place, and with
    no referee that hunt is the entire remedy available to either of us.
    """
    theirs = replace(
        ours,
        config_digest="wrong",
        scent_model_digest="also-wrong",
        readings={"capture.resolution": "on_placement"},
        role_split="4-2",
        step_zero=THEIRS,
    )
    assert len(settle(ours, theirs).reasons) == 1


# --- TN.5: the scent model ---------------------------------------------------


def test_a_stated_scent_mismatch_refuses(ours, mirror) -> None:
    """M#23, C-007. Identical configs and a different digest means their *code*
    disagrees with the config they just signed — which is exactly the failure
    that would otherwise surface as forgery in the end-of-match audit, against
    two honest teams."""
    locked = settle(ours, replace(mirror, scent_model_digest="different"))
    assert locked.result == REFUSED_SCENT_MISMATCH
    assert "0.810 is the book" in locked.reasons[0], "the remedy has to be sayable"


def test_an_unstated_scent_model_warns_and_plays(ours, mirror) -> None:
    """PRD_negotiation §3.6b. Sealing the model is our proposal, not the book's
    rule; forfeiting a fixture over it would be paying for our own extension."""
    locked = settle(ours, replace(mirror, scent_model_digest=""))
    assert locked.agreed
    assert any("scent model digest" in item for item in locked.warnings)


def test_the_sampling_mode_is_inside_the_sealed_model(minimal_config) -> None:
    """9.1.7. "What the field contains" and "when it may be read" are different
    agreements, and only the first is obvious. A peer acting on the current
    turn's field is revealing before committing — the one attack commit-reveal
    exists to prevent — and this is the field in which they say so.
    """
    payload = scent_model_of(minimal_config)
    assert payload["sampling_mode"] == "end_of_previous_full_turn"
    assert payload["field_includes_current_turn"] is True


def test_flipping_the_transmission_rule_changes_the_digest() -> None:
    """C-005 has to be *sealed*, not merely written down. Two peers disagreeing
    about whether the field carries this turn's deposit read each other's trails
    one turn out of step, and every belief either of them forms is wrong."""
    included = scent_model_payload(0.10, "multiplicative", 5, includes_current_turn=True)
    excluded = scent_model_payload(0.10, "multiplicative", 5, includes_current_turn=False)
    assert digest(included) != digest(excluded)


# --- the readings ------------------------------------------------------------


def test_a_stated_reading_mismatch_refuses(ours, mirror) -> None:
    # The opposite of whatever we signed, not a literal. Pinning "false" made
    # this test pass by *agreeing* with us the day we signed C-006c off (16/08),
    # which is the one outcome it exists to rule out.
    mine = mirror.readings["capture.swap_is_capture"]
    flipped = "false" if mine == "true" else "true"
    theirs = replace(mirror, readings=dict(mirror.readings, **{"capture.swap_is_capture": flipped}))
    locked = settle(ours, theirs)
    assert locked.result == REFUSED_READING_MISMATCH
    assert "C-006c" in locked.reasons[0]


def test_unstated_readings_warn_and_play(ours, mirror) -> None:
    locked = settle(ours, replace(mirror, readings={}))
    assert locked.agreed
    assert any("stated no reading" in item for item in locked.warnings)


# --- N17: the role split -----------------------------------------------------


def test_a_stated_role_split_mismatch_refuses(ours, mirror) -> None:
    """C-011. Our scoring analysis assumes 3-3, and the cop role carries a
    15-point spread against the thief's 5 — so a series that turned out to be
    4-2 was a different game from the one we prepared for."""
    locked = settle(ours, replace(mirror, role_split="4-2"))
    assert locked.result == REFUSED_ROLE_SPLIT


def test_an_unstated_role_split_warns_and_plays(ours, mirror) -> None:
    """It is in no Appendix at all, so most opponents will not send it. The
    warning is what gets it asked in the human channel."""
    locked = settle(ours, replace(mirror, role_split=""))
    assert locked.agreed
    assert any("no role split" in item for item in locked.warnings)


def test_our_own_split_is_what_the_agreement_records(ours, mirror) -> None:
    """Recording theirs would make the artefact agree with whatever arrived,
    which is the shape of bug that made the old handshake unable to fail."""
    assert settle(ours, replace(mirror, role_split="")).role_split == "3-3"


def test_two_peers_claiming_the_same_role_are_refused(ours, mirror) -> None:
    """**A matching split is not a settled plan** (C-011).

    `"3-3"` is symmetric: both peers send the identical string and agree, and it
    says nothing about who starts as Cop. Each builds its plan from the role it
    holds, so two peers holding the same one build mirror images and play a
    sub-game with two Cops in it.

    Caught here rather than on the wire. Without this the disagreement first
    surfaced as `PeerRuntime._require_opponent` rejecting their opening commit —
    a technical loss for both teams, worth 0 each, over something the handshake
    settles for free.
    """
    locked = settle(ours, replace(mirror, role=ours.role))
    assert locked.result == REFUSED_ROLE_SPLIT and not locked.agreed
    assert any("we both propose to play cop" in reason for reason in locked.reasons)


# --- TN.10: Step-0 and the commit ---------------------------------------------


def test_a_dirty_tree_is_reported_on_either_side(ours, mirror) -> None:
    """M#53 pins the code for the whole series. A commit that does not describe
    the running code makes the match unreproducible — and it is *our* side that
    matters most here, since it is the side we can still fix."""
    dirty = settle(replace(ours, step_zero={"github_commit": "c" * 40 + "-dirty"}), mirror)
    assert any("we declared commit" in item for item in dirty.warnings)
    theirs = settle(ours, replace(mirror, step_zero={"github_commit": "unknown"}))
    assert any("the opponent declared commit" in item for item in theirs.warnings)


def test_an_absent_declaration_is_reported(ours, mirror) -> None:
    """M#24. Without it a peer can swap agents between sub-games and there is no
    moment left at which anyone would notice."""
    locked = settle(ours, replace(mirror, step_zero={}))
    assert any("no Step-0 declaration" in item for item in locked.warnings)


# --- the declaration itself ---------------------------------------------------


def test_a_negative_counted_total_is_refused(minimal_config) -> None:
    """`games_played` has no default anywhere in this module. The most dangerous
    value in the protocol must not be the one you get by forgetting it."""
    with pytest.raises(ValueError, match="cannot be negative"):
        proposal(minimal_config, Role.COP, -1, "d", CLEAN)


def test_the_proposal_states_everything_the_dod_requires(ours) -> None:
    """9.1.1-9.1.4 and 9.1.8, in one message."""
    assert ours.config_digest and ours.scent_model_digest
    assert ours.step_zero["github_commit"] and ours.role_split
    assert ours.readings["coordinates.component_order"] == "row,col"


# --- the far side of an asymmetric handshake ---------------------------------


def test_a_refusal_by_the_opponent_is_still_a_record(ours) -> None:
    """**Only one side of this exchange gets a verdict.** The peer that answers
    raises; the peer that asked receives a remote error string. Without a record
    for that case the initiator would learn of a refusal as a traceback and file
    nothing — losing exactly the outcome most likely to be argued about later.
    """
    locked = refused_by_opponent(ours, "'negotiate' was rejected: they run subtractive decay")
    assert locked.result == REFUSED_BY_OPPONENT and not locked.agreed
    assert "subtractive decay" in locked.reasons[0], "their wording is the only account we get"
    assert locked.config_sha256 == ours.config_digest
    assert locked.their_commit == "", "we never heard from them; inventing one would be a lie"
