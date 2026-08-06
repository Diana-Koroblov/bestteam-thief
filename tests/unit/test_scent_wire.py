"""The scent field on the wire, and the peer that reads it (TODO 4.1.6, 4.1.8).

4.1.6 was marked complete for a whole phase with **nothing implementing it**.
`Reveal` had no scent field, no codec read one, and `PeerRuntime.belief()`
returned a uniform posterior — so a live Cop measured entropy at 5.61 bits
against a `confident_bits` threshold of 3.5, stayed in HERD for all 35 turns and
never placed a barrier, which PRD §2.1 calls the only way the Cop can win.

The DoD said *"our field is sent inside each turn message and the opponent's is
merged on receipt"*. These tests are that sentence, split into its two halves and
made falsifiable.
"""

from __future__ import annotations

import pytest

from core.crypto.canonical import canonical_json
from core.domain.board import Board
from core.domain.scent import decode, emit, encode
from core.protocol.schemas import Reveal, Role
from core.protocol.tools import ProtocolError, build_tools
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime

BOARD = Board(grid_size=7)


@pytest.fixture
def runtime(minimal_config) -> PeerRuntime:
    """A peer that has already agreed the configuration."""
    peer = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.COP))
    peer.agreed = True
    return peer


def their_reveal(step: int, at: tuple[int, int], role: Role = Role.THIEF) -> dict:
    """The payload an opponent standing on *at* would send."""
    return {
        "kind": "reveal",
        "step": step,
        "role": role.value,
        "move": "N",
        "hint": "I drift north while you guess at shadows.",
        "scent": [list(cell) for cell in encode(emit(at, BOARD))],
    }


# --- the codec --------------------------------------------------------------


def test_a_field_survives_the_round_trip_exactly() -> None:
    """Under C-008 the field may be hashed, so *exactly* is the requirement:
    a value that changed in its last bit would fail the opponent's audit of a
    digest we honestly produced."""
    field = emit((3, 3), BOARD)
    assert decode(encode(field)) == field


def test_it_survives_canonical_json_too() -> None:
    """That is the form it actually travels in, and floats are the risk."""
    import json

    field = emit((2, 5), BOARD)
    revived = json.loads(canonical_json(encode(field)))
    assert decode(revived) == field


def test_the_encoding_is_ordered_so_two_peers_agree() -> None:
    """`canonical_json` sorts object keys; a list has to settle its own order or
    two peers hash identical data into different digests."""
    field = emit((3, 3), BOARD)
    assert list(encode(field)) == sorted(encode(field))


def test_a_malformed_cell_is_refused_at_the_boundary() -> None:
    """Loud on purpose. A silently dropped cell is a hole in the one channel
    that cannot lie, and it would surface as a filter that mysteriously
    underperforms rather than as an error anyone could find."""
    with pytest.raises(ValueError):
        decode([[1, 2]])


def test_an_absent_field_decodes_to_silence_not_an_error() -> None:
    """A peer whose trail has genuinely decayed to nothing is not making a
    claim, and Ch. 4 says silence is not absence."""
    assert decode(None) == {}
    assert decode([]) == {}


# --- half one: the field is sent --------------------------------------------


def test_our_reveal_carries_the_field_we_emitted(runtime: PeerRuntime) -> None:
    """The outbound half of 4.1.6's DoD."""
    from core.domain.actions import Direction
    from core.domain.brain_base import Decision

    runtime.observe()  # emits this turn's deposit
    reveal = runtime.reveal_for(Decision(Direction.N))
    assert decode(reveal.scent) == runtime.truth.filter.trail
    assert reveal.scent, "a peer that transmits nothing tells the opponent nothing"


def test_the_reveal_states_the_move_and_the_flag_the_brain_chose(
    runtime: PeerRuntime,
) -> None:
    """A3.11: the brain sets the truth flag, the model only writes the words."""
    from core.domain.actions import Direction
    from core.domain.brain_base import Decision
    from core.domain.intent import Intent

    reveal = runtime.reveal_for(Decision(Direction.E, claim=Direction.W, intent=Intent.LIE))
    assert reveal.move == "E"
    assert reveal.intent is Intent.LIE
    assert "west" in reveal.hint.lower(), "the claim the brain chose must be conveyed"


# --- half two: the opponent's is merged on receipt --------------------------


def test_an_incoming_field_reaches_the_belief(runtime: PeerRuntime) -> None:
    """The inbound half, and the one whose absence made Phase 8 inert."""
    from core.domain.belief import peak

    tools = build_tools(runtime)
    runtime.commits[0] = "digest"
    tools["receive_reveal"](their_reveal(0, (5, 5)))

    runtime.orchestrator.advance(runtime.orchestrator.state.advanced(step=1))
    assert peak(runtime.observe().belief) == (5, 5)


def test_a_reveal_without_a_field_is_still_accepted(runtime: PeerRuntime) -> None:
    """An opponent may legitimately send nothing — a peer that refused would
    forfeit a match over a rule Appendix F does not state."""
    tools = build_tools(runtime)
    runtime.commits[0] = "digest"
    payload = their_reveal(0, (5, 5))
    del payload["scent"]
    tools["receive_reveal"](payload)
    assert runtime.latest_opponent_scent() == {}


def test_a_malformed_field_is_refused_rather_than_half_read(
    runtime: PeerRuntime,
) -> None:
    """With no referee, "your step 0 reveal carried a two-value scent cell" is
    the entire remedy available to us, so it has to be sayable."""
    tools = build_tools(runtime)
    runtime.commits[0] = "digest"
    payload = their_reveal(0, (5, 5))
    payload["scent"] = [[1, 2]]
    with pytest.raises((ProtocolError, ValueError)):
        tools["receive_reveal"](payload)


# --- the timing commit-reveal forces ----------------------------------------


def test_the_field_we_act_on_is_the_newest_one_revealed(runtime: PeerRuntime) -> None:
    """A field revealed at turn k is first usable at turn k+1: our move for turn
    k is sealed before their reveal for turn k can arrive. Reading a fresher one
    is not a nicety we are declining, it is impossible."""
    tools = build_tools(runtime)
    for step, cell in enumerate([(1, 1), (2, 2), (3, 3)]):
        runtime.commits[step] = "digest"
        tools["receive_reveal"](their_reveal(step, cell))
    assert runtime.latest_opponent_scent() == emit((3, 3), BOARD)


def test_the_filter_runs_once_per_turn_however_often_we_look(
    runtime: PeerRuntime,
) -> None:
    """`observe` advances the filter, so it has to be idempotent within a turn —
    a brain, the GUI and the logger may all ask, and three deposits in one turn
    would be a trail we never laid."""
    runtime.observe()
    first = dict(runtime.truth.filter.trail)
    runtime.observe()
    runtime.belief()
    runtime.reveal_for(_north())
    assert runtime.truth.filter.trail == first


def test_a_reveal_transmits_this_turns_field_even_if_nobody_observed(
    runtime: PeerRuntime,
) -> None:
    """Sending a stale trail would be a lie about the one channel that cannot
    lie — and under C-008 a *sealed* one. So the reveal advances the filter
    itself rather than trusting a caller to have done it."""
    reveal = runtime.reveal_for(_north())
    assert decode(reveal.scent) == emit(runtime.orchestrator.own_position, BOARD)


def test_a_step_that_goes_backwards_is_a_new_sub_game(runtime: PeerRuntime) -> None:
    """**The last must-remember seam, closed.** A per-step guard that only ever
    counted upward would silently stop filtering the moment a sub-game restarted
    at step 0 — and the symptom is the same silent one as the original defect: a
    Cop that never gains confidence and never places a wall, with no error
    anywhere to find."""
    from core.domain.belief import entropy

    tools = build_tools(runtime)
    runtime.commits[0] = "digest"
    tools["receive_reveal"](their_reveal(0, (5, 5)))
    state = runtime.orchestrator.state
    runtime.orchestrator.advance(state.advanced(step=3))
    assert entropy(runtime.observe().belief) < 3.0, "a sighting must sharpen the belief"

    runtime.orchestrator.advance(runtime.orchestrator.state.advanced(step=0))
    fresh = runtime.observe()
    assert entropy(fresh.belief) > 5.0, "a new sub-game starts from honest ignorance"
    assert runtime.latest_opponent_scent() == {}


def _north():
    """A decision to step north, claiming nothing."""
    from core.domain.actions import Direction
    from core.domain.brain_base import Decision

    return Decision(Direction.N)


# --- C-008 ------------------------------------------------------------------


def test_the_scent_digest_is_omitted_unless_it_was_agreed(
    runtime: PeerRuntime, minimal_config
) -> None:
    """Sealing unilaterally is **worse than not sealing**: the opponent
    recomputes our digests with their own payload builder, so one extra key
    fails every digest we ever sent and an honest peer looks like a forger.

    The "off" peer gets a **deep-copied** config. `minimal_config` is
    session-scoped, so flipping the key on it in place would leak into every
    test that ran afterwards — which is how a suite acquires failures that
    depend on the order it happened to run in.
    """
    import copy
    from dataclasses import replace

    runtime.observe()
    assert runtime.scent_digest() is not None  # the shipped config agrees to it

    unsealed = copy.deepcopy(minimal_config.merged)
    unsealed["pheromones"]["seal_scent_digest"] = False
    peer = PeerRuntime(
        orchestrator=Orchestrator.from_config(replace(minimal_config, merged=unsealed), Role.COP)
    )
    peer.observe()
    assert peer.scent_digest() is None


def test_the_digest_covers_the_field_we_actually_send(runtime: PeerRuntime) -> None:
    """C-008's whole point: the reference leaves the field outside the hash, so
    a peer can transmit one field and seal another."""
    from core.crypto.canonical import digest

    runtime.observe()
    from core.domain.actions import Direction
    from core.domain.brain_base import Decision

    reveal: Reveal = runtime.reveal_for(Decision(Direction.N))
    assert runtime.scent_digest() == digest(reveal.scent)
