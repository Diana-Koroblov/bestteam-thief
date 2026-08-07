"""Reading a configuration the opponent proposed (TODO 9.1.1, TN.6-TN.8).

M#12 disqualifies **both** teams for an illegal value, so "the opponent proposed
it" is not a defence and this is the check that stops us signing one.

Two failure modes shape these tests, and both would produce a green suite while
losing a match:

* **Refusing a legal proposal.** Six of the rows in our `PARAMETERS` table are
  our own inventions. A peer sending a plain Appendix F config is missing all
  six, and refusing them would forfeit a fixture over a rule the book does not
  state.
* **A review that contradicts itself.** A lowered minimum offered as a judgement
  call two lines below being refused is worse than a wrong answer, because this
  document's whole job is to settle an argument with someone who does not trust
  us.
"""

from __future__ import annotations

import copy
import json

import pytest

from core.crypto.canonical import digest
from core.shared.config_review import Review, review, review_file
from tests.paths import shared_config


@pytest.fixture
def ours() -> dict:
    """The shipped shared contract — the real file, not an invented one."""
    return shared_config()


@pytest.fixture
def theirs(ours: dict) -> dict:
    """A proposal identical to ours, for a test to spoil one key at a time."""
    return copy.deepcopy(ours)


# --- the proposal we must not refuse -----------------------------------------


def test_a_plain_appendix_f_config_is_playable(ours: dict, theirs: dict) -> None:
    """**The fixture-saving case.** An opponent who read only the book sends no
    `decay_model`, no `capture` section and no scent-sealing flag, because none
    of those are in it. Every one is ours. Refusing would cost a match over
    rules we invented (PRD_negotiation §3.6b)."""
    for key in ("decay_model", "field_includes_current_turn", "seal_scent_digest"):
        theirs["pheromones"].pop(key)
    theirs.pop("capture")
    found = review(theirs, ours)
    assert found.playable, "a config that breaches no Appendix F rule is legal to sign"
    assert len(found.absent) == 6
    assert all("in no Appendix" in item for item in found.absent)


def test_an_absent_appendix_f_key_says_so(ours: dict, theirs: dict) -> None:
    """Also not illegal — but it *is* a value neither peer has agreed, and the
    two must be distinguishable because only one of them is our own doing."""
    theirs["world"].pop("hint_max_words")
    absent = review(theirs, ours).absent
    assert any("hint_max_words" in item and "(Appendix F)" in item for item in absent)


# --- what must be refused ----------------------------------------------------


def test_a_lowered_minimum_is_refused(ours: dict, theirs: dict) -> None:
    """M#12: raising is legal, lowering is not, and agreement is not a defence."""
    theirs["movement_and_barriers"]["max_barriers"] = 10
    found = review(theirs, ours)
    assert not found.playable
    assert "M#12" in found.illegal[0]


def test_a_changed_fixed_value_is_refused(ours: dict, theirs: dict) -> None:
    """Appendix F's scoring table is fixed. A team proposing 25 for a capture is
    proposing a different game."""
    theirs["scoring"]["capture_cop"] = 25
    assert not review(theirs, ours).playable


def test_a_degenerate_but_legal_pair_is_refused(ours: dict, theirs: dict) -> None:
    """Both are minimums and Appendix F permits raising either alone, which
    produces a game with no defined outcome. See PARAMETERS.md 4.2."""
    theirs["movement_and_barriers"]["max_moves"] = 40
    found = review(theirs, ours)
    assert not found.playable
    assert any("survival_threshold" in item for item in found.illegal)


def test_a_config_we_cannot_read_is_refused(ours: dict, theirs: dict) -> None:
    """A proposal our code cannot load is one we could not audit afterwards,
    and the audit is the only thing standing between us and an unprovable
    dispute."""
    theirs["version"] = "99.00"
    assert not review(theirs, ours).playable


# --- the review must not argue with itself -----------------------------------


def test_an_illegal_value_is_never_offered_as_a_judgement_call(ours: dict, theirs: dict) -> None:
    """**It appeared in both lists on the first run.** `max_barriers: 10` was
    refused under Appendix F and listed as a legal change four lines below it.
    A document that contradicts itself in front of the opponent it is meant to
    convince is worse than one that is simply wrong.
    """
    theirs["movement_and_barriers"]["max_barriers"] = 10
    found = review(theirs, ours)
    assert any("max_barriers" in item for item in found.illegal)
    assert not [item for item in found.changes if "max_barriers" in item]


def test_a_raised_minimum_is_a_change_and_not_a_breach(ours: dict, theirs: dict) -> None:
    """The mirror image, and the reason the two lists cannot simply be 'differs
    from ours': raising a minimum is always legal, and sometimes against our
    interest — a bigger board is strongly thief-favouring (PARAMETERS §4.3)."""
    theirs["board_and_agents"]["grid_size"] = 9
    found = review(theirs, ours)
    assert found.playable
    assert any("grid_size" in item and "always legal" in item for item in found.changes)


def test_a_negotiable_difference_is_reported_without_alarm(ours: dict, theirs: dict) -> None:
    theirs["world"]["map_area"] = "Tel Aviv"
    found = review(theirs, ours)
    assert found.playable
    assert any("Tel Aviv" in item and "negotiable" in item for item in found.changes)


# --- keys nothing reads ------------------------------------------------------


def test_a_key_we_do_not_recognise_is_surfaced(ours: dict, theirs: dict) -> None:
    """Not an error — another team may have extensions exactly as we do. But a
    key nothing on our side reads is one we would silently ignore, and silent
    disagreement about a shared file is the whole failure this protocol exists
    to prevent."""
    theirs["their_own_section"] = {"turbo_mode": True}
    assert review(theirs, ours).unknown == ("their_own_section.turbo_mode",)


def test_our_own_shipped_config_has_no_unknown_keys(ours: dict) -> None:
    """The table and the file must not drift apart. A key in `game.json` that no
    `Parameter` describes is one an opponent's reviewer would flag at us."""
    assert review(ours, ours).unknown == ()


# --- the digest --------------------------------------------------------------


def test_it_predicts_the_digest_we_would_be_comparing(ours: dict, theirs: dict) -> None:
    """M#11 is decided by a hash, so a review that did not compute one would
    leave the only question that actually refuses a match unanswered."""
    theirs["world"]["map_area"] = "Tel Aviv"
    assert review(theirs, ours).sha256 == digest(theirs)


def test_reviewing_our_own_proposal_is_a_clean_bill(ours: dict) -> None:
    """If the shipped config failed its own reviewer, we would be sending
    opponents a file we would refuse ourselves."""
    found = review(ours, ours)
    assert found.playable and found.absent == () and found.changes == ()
    assert "legal to sign" in found.report()


# --- reading it off disk -----------------------------------------------------


def test_it_reads_a_proposal_from_a_file(tmp_path, ours: dict) -> None:
    path = tmp_path / "their_game.json"
    path.write_text(json.dumps(ours), encoding="utf-8")
    assert review_file(path, ours).playable


def test_an_unreadable_proposal_is_refused_with_its_path(tmp_path, ours: dict) -> None:
    """Named, because "it did not work" is not something you can send someone."""
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="broken.json"):
        review_file(broken, ours)
    with pytest.raises(ValueError, match="absent.json"):
        review_file(tmp_path / "absent.json", ours)


def test_the_report_names_the_rule_for_every_refusal(ours: dict, theirs: dict) -> None:
    """With no referee, the citation is the entire remedy: the conversation has
    to be about a rule, not about whose code said no."""
    theirs["movement_and_barriers"]["max_barriers"] = 10
    report = review(theirs, ours).report()
    assert "M#12" in report and "REFUSE" in report
    assert isinstance(review(theirs, ours), Review)
