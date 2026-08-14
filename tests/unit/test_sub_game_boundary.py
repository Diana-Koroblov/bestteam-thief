"""The sub-game boundary, which lost two sub-games against `nis-yar1` on 13/08.

Both peers close a sub-game at their own pace, so there is a window in which one
is already opening the next while the other is still exchanging nonces. Every
test here is about a message that arrives inside that window.

The failure it reproduces is the expensive kind: a technical loss on a sub-game
*neither side played wrong*, scored 0 for both under M#35, with nothing in
either log to explain it.
"""

from __future__ import annotations

import pytest

from core.protocol.schemas import Commit, Reveal, Role
from core.protocol.tools import ProtocolError
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from core.shared.config_manager import Config


@pytest.fixture
def runtime(minimal_config: Config) -> PeerRuntime:
    """A cop peer that has agreed and is mid-series."""
    peer = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, Role.COP))
    peer.agreed = True
    return peer


def _commit(step: int = 0) -> Commit:
    return Commit(step=step, role=Role.THIEF, digest="d" * 64)


def _reveal(step: int = 0) -> Reveal:
    return Reveal(step=step, role=Role.THIEF, move="N", hint="hi")


def test_a_commit_arriving_before_the_reset_survives_it(runtime: PeerRuntime) -> None:
    """The exact loss: their opening commit landed, then our reset wiped it."""
    runtime.commits[0] = "previous sub-game"
    runtime.begin_closing()

    runtime.on_commit(_commit())          # their sub-game 2 opener, early
    runtime.start_sub_game(2)             # our reset

    assert runtime.commits[0] == "d" * 64, "their commit must survive the boundary"


def test_a_reveal_arriving_before_the_reset_survives_it(runtime: PeerRuntime) -> None:
    """Sub-game 2's actual symptom: 'their reveal for step 0 never arrived'."""
    runtime.begin_closing()
    runtime.on_commit(_commit())
    runtime.on_reveal(_reveal())
    runtime.start_sub_game(2)

    assert 0 in runtime.reveals
    assert runtime.reveals[0].move == "N"


def test_the_seal_is_still_enforced_across_the_boundary(runtime: PeerRuntime) -> None:
    """Holding a message must not become a way to skip commit-reveal."""
    runtime.begin_closing()
    with pytest.raises(ProtocolError, match="sealed before it is shown"):
        runtime.on_reveal(_reveal())


def test_a_held_commit_is_acknowledged_like_any_other(runtime: PeerRuntime) -> None:
    """Silence would read as a dead peer and cost the sub-game anyway."""
    runtime.begin_closing()
    ack = runtime.on_commit(_commit())
    assert ack.acknowledged_digest == "d" * 64
    assert ack.step == 0


def test_the_finished_sub_game_is_untouched_while_closing(runtime: PeerRuntime) -> None:
    """The audit reads the sub-game just played; holding must not disturb it."""
    runtime.commits[7] = "played"
    runtime.begin_closing()
    runtime.on_commit(_commit(0))

    assert runtime.commits[7] == "played", "the closing audit still needs these"
    assert 0 not in runtime.commits, "next sub-game's opener is held, not merged early"


def test_the_reset_clears_the_previous_sub_game(runtime: PeerRuntime) -> None:
    """Promotion must not resurrect the sub-game that just ended."""
    runtime.commits[7] = "played"
    runtime.begin_closing()
    runtime.on_commit(_commit(0))
    runtime.start_sub_game(2)

    assert 7 not in runtime.commits
    assert runtime.commits == {0: "d" * 64}


def test_closing_ends_when_the_next_sub_game_opens(runtime: PeerRuntime) -> None:
    """Otherwise every later message of the new sub-game would be held too."""
    runtime.begin_closing()
    runtime.start_sub_game(2)
    assert runtime.closing is False

    runtime.on_commit(_commit(1))
    assert runtime.commits[1] == "d" * 64
    assert runtime.pending_commits == {}


def test_a_duplicate_commit_is_still_refused_in_normal_play(runtime: PeerRuntime) -> None:
    """The boundary relaxes ordering; it must not relax the rules."""
    runtime.on_commit(_commit(0))
    with pytest.raises(ProtocolError, match="already committed"):
        runtime.on_commit(_commit(0))
