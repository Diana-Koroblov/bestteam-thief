"""The pre-match protocol as it is actually run (TODO 9.1).

Everything under 9.1 happens once per match, from a terminal, minutes before the
first move — so the command is the artefact, not the library behind it. These
tests drive `python -m core negotiate` end to end against a live in-process peer.

**The exit code is the part that matters most.** A refused match costs nothing; a
*disputed* one scores 0 for both teams (M#35). If the command printed
`REFUSED_CONFIG_MISMATCH` and still exited 0, a script would start the match
anyway and the whole comparison would have been decoration.
"""

from __future__ import annotations

import json

import pytest

from core.__main__ import main
from core.infra.mcp_client import OpponentClient
from core.infra.mcp_server import build_server_spec, create_server
from core.protocol.schemas import Role
from core.protocol.tools import build_guarded_tools
from core.runtime.orchestrator import Orchestrator
from core.runtime.peer_runtime import PeerRuntime
from core.sdk.peer_sdk import PeerSDK
from tests.paths import PRESENT_ROLES

ROLE = PRESENT_ROLES[0]


@pytest.fixture
def opponent(minimal_config) -> OpponentClient:
    """A live peer of the other role, reachable over the in-process transport."""
    other = Role.THIEF if ROLE == "police" else Role.COP
    peer = PeerRuntime(orchestrator=Orchestrator.from_config(minimal_config, other))
    server = create_server(build_server_spec(build_guarded_tools(peer), "opponent", 8083))
    return OpponentClient(base_url="in-process", timeout_sec=5, transport=server)


@pytest.fixture
def attached(monkeypatch, opponent: OpponentClient):
    """Make the CLI's `PeerSDK` come up with that peer already connected."""
    built: list[PeerSDK] = []
    original = PeerSDK.__init__

    def patched(self, config_dir, role):
        original(self, config_dir, role)
        self._orchestrator.opponent = opponent
        built.append(self)

    monkeypatch.setattr(PeerSDK, "__init__", patched)
    return built


def test_it_prints_our_side_without_an_opponent(capsys) -> None:
    """The useful half before a fixture exists: the digests to compare, the
    honest counted total, and the clause to paste (9.1.6)."""
    assert main(["negotiate", "--role", ROLE]) == 0
    printed = capsys.readouterr().out
    assert "config_sha256" in printed and "scent_model_sha256" in printed
    assert "from docs/LEAGUE_LOG.md" in printed
    assert "0.810 after one turn" in printed, "the worked example is the point of M#23"


def test_a_full_exchange_agrees_and_exits_zero(attached, capsys) -> None:
    """9.1.1-9.1.8 against a peer running this same code."""
    assert main(["negotiate", "--role", ROLE, "--opponent", "in-process"]) == 0
    printed = capsys.readouterr().out
    assert "result            : AGREED" in printed
    assert "counted match(es)" in printed


def test_a_refusal_exits_non_zero(monkeypatch, opponent, capsys) -> None:
    """**The assertion the whole command exists for.** Printing a refusal and
    exiting 0 would let a script start a match that cannot be audited, and M#35
    voids a disputed result for both teams.

    Patched on the **instance** the CLI builds, not on the class: `PreMatch` is
    what the opponent peer runs too, so a class-level patch would change both
    sides identically and they would agree — a green test proving nothing. This
    is the same trap as an ablation that flips the flag for both arms.
    """
    original = PeerSDK.__init__

    def patched(self, config_dir, role):
        original(self, config_dir, role)
        self._orchestrator.opponent = opponent
        self._runtime.prematch.scent_model = lambda: {"decay_model": "reference-simulator"}

    monkeypatch.setattr(PeerSDK, "__init__", patched)
    assert main(["negotiate", "--role", ROLE, "--opponent", "in-process"]) == 1
    printed = capsys.readouterr().out
    assert "REFUSED_BY_OPPONENT" in printed and "REFUSED: " in printed


def test_a_refusal_is_still_filed(monkeypatch, opponent, tmp_path) -> None:
    """A refusal is the outcome most likely to be argued about, so it is the one
    that most needs a timestamped record carrying the opponent's own wording."""
    original = PeerSDK.__init__

    def patched(self, config_dir, role):
        original(self, config_dir, role)
        self._orchestrator.opponent = opponent
        self._runtime.prematch.scent_model = lambda: {"decay_model": "reference-simulator"}

    monkeypatch.setattr(PeerSDK, "__init__", patched)
    main(["negotiate", "--role", ROLE, "--opponent", "in-process", "--out", str(tmp_path)])
    payload = json.loads(next(tmp_path.glob("agreement_*.json")).read_text(encoding="utf-8"))
    assert payload["result"] == "REFUSED_BY_OPPONENT"
    assert "0.810 is the book" in payload["reasons"][0]
    assert payload["github_commit"]["theirs"] == "", "they never declared; inventing one is a lie"


def test_the_agreement_is_filed_where_it_was_asked_for(attached, tmp_path, capsys) -> None:
    """N10, 9.3.5: the file committed beside the match log. Named from the
    **declared** team names, so an agreement is never filed under a name the
    opponent did not claim."""
    assert main(["negotiate", "--role", ROLE, "--opponent", "in-process", "--out", str(tmp_path)]) == 0
    written = list(tmp_path.glob("agreement_*.json"))
    assert len(written) == 1
    payload = json.loads(written[0].read_text(encoding="utf-8"))
    assert payload["result"] == "AGREED"
    assert payload["scent_model"]["sampling_mode"] == "end_of_previous_full_turn"
    assert payload["readings"]["coordinates.component_order"] == "row,col"
    assert "bestteam" in written[0].name


def test_the_role_split_reaches_the_wire(attached, capsys) -> None:
    """N17 is negotiated per match, so it has to be settable per invocation —
    and 4-2 against a peer proposing 3-3 must refuse rather than quietly
    proceed, because the cop role carries a 15-point spread against the thief's
    5 and an unnoticed split is a different series from the one we prepared for.
    """
    assert main(["negotiate", "--role", ROLE, "--opponent", "in-process", "--role-split", "4-2"]) == 1
    printed = capsys.readouterr().out
    assert "role split        : 4-2" in printed, "the flag has to reach the proposal"
    assert "REFUSED_ROLE_SPLIT" in printed, "and the proposal has to reach the opponent"


def test_a_peer_we_never_heard_from_is_not_reported_as_declaring_zero(
    monkeypatch, opponent, capsys
) -> None:
    """`artefacts.py`'s rule, applied to the terminal: a plausible wrong figure
    ranks below an absent one, because a missing line prompts a question and a
    wrong one does not. `their_games_played` sits at 0 after a refusal, and
    printing it would say a peer that never answered had declared zero matches.
    """
    original = PeerSDK.__init__

    def patched(self, config_dir, role):
        original(self, config_dir, role)
        self._orchestrator.opponent = opponent
        self._runtime.prematch.scent_model = lambda: {"decay_model": "reference-simulator"}

    monkeypatch.setattr(PeerSDK, "__init__", patched)
    main(["negotiate", "--role", ROLE, "--opponent", "in-process"])
    assert "they declare" not in capsys.readouterr().out
