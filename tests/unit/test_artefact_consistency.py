"""What the four artefacts must agree about (TODO 7.2, T7.5).

The individual builders are tested in `test_report_artefacts.py` and
`test_match_log.py`. This file tests the *set*: four files land in one grader's
inbox describing one match, and the failure mode nobody notices while writing
them one at a time is drift between them.

**This caught a real one.** The log was built without `created_utc` or
`code_version`, which the other three had carried since 7.2.1. Every per-file
test passed; nothing compared them. So the comparison is now a test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.crypto.commitment import seal
from core.report import (
    artefact_name,
    build_config_snapshot,
    build_declaration,
    build_log,
    build_result,
    build_step,
    game_id,
    write,
)

GAME_ID = game_id("bestteam", "otherteam", "2026-08-12")
SHARED = {"version": "1.00", "board_and_agents": {"grid_size": 7}}
REPOS = {"ours_cop": "https://github.com/x/bestteam-cop"}
KINDS = ("declaration", "config", "log", "result")


def all_four() -> dict[str, dict]:
    """Return one of each artefact, for the same match."""
    locked = seal({"cop": [0, 0], "thief": [3, 3], "step": 0}, "N", "truth")
    step = build_step(0, locked.digest, {"cop": [0, 0], "thief": [3, 3], "step": 0}, "N", "truth")
    return {
        "declaration": build_declaration(
            GAME_ID, {"bestteam": ["Diana", "Itay"]}, REPOS, {}, "llama3.1:8b", 200_000
        ),
        "config": build_config_snapshot(GAME_ID, 1, SHARED, "cop"),
        "log": build_log(GAME_ID, 1, "cop", [step], {"0": locked.nonce}),
        "result": build_result(GAME_ID, [], "abc123", 0, REPOS),
    }


@pytest.mark.parametrize("kind", KINDS)
def test_every_artefact_names_the_match_the_same_way(kind: str) -> None:
    """**The whole point of 7.2.5.** One shared id, or the four files read as
    fragments of different matches."""
    assert all_four()[kind]["game_id"] == GAME_ID


@pytest.mark.parametrize("field", ["created_utc", "code_version"])
@pytest.mark.parametrize("kind", KINDS)
def test_every_artefact_carries_the_common_fields(kind: str, field: str) -> None:
    """The drift this file exists to catch. A submitted artefact that cannot say
    when it was written or which code wrote it is one a grader has to ask about."""
    assert all_four()[kind][field], f"{kind} is missing {field}"


def test_every_timestamp_is_utc() -> None:
    """Two peers share a timezone today and may not tomorrow; four files
    disagreeing about when one match happened is a needless question."""
    for kind, payload in all_four().items():
        assert payload["created_utc"].endswith("+00:00"), kind


def test_the_per_sub_game_artefacts_agree_on_which_sub_game() -> None:
    """Config and log are written per sub-game and must be the same one.

    A config from `g01` beside a log from `g03` would look like a complete pair
    to anyone reading the directory rather than the contents.
    """
    payloads = all_four()
    assert payloads["config"]["sub_game"] == payloads["log"]["sub_game"]


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_has_a_filename(kind: str) -> None:
    sub_game = 1 if kind in ("config", "log") else None
    name = artefact_name(kind, GAME_ID, sub_game)
    assert name.startswith(kind) and name.endswith(".json")


def test_the_four_filenames_are_distinct() -> None:
    """They land in one inbox beside nine other teams' files."""
    names = {artefact_name(kind, GAME_ID, 1 if kind in ("config", "log") else None) for kind in KINDS}
    assert len(names) == 4


def test_the_whole_set_survives_being_written_and_reread(tmp_path: Path) -> None:
    """Every one of them is a submission artefact, not an internal structure."""
    for kind, payload in all_four().items():
        sub_game = 1 if kind in ("config", "log") else None
        target = write(payload, tmp_path, artefact_name(kind, GAME_ID, sub_game))
        assert json.loads(target.read_text(encoding="utf-8"))["game_id"] == GAME_ID


def test_no_artefact_leaks_the_private_provider() -> None:
    """Appendix F Table 21 keeps the provider private to each peer; the model is
    declared, the provider never is."""
    for kind, payload in all_four().items():
        body = json.dumps(payload)
        for private in ("groq", "ollama", "P2P_LLM_PROVIDER"):
            assert private not in body, f"{kind} leaks {private}"
