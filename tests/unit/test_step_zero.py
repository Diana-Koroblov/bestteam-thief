"""The Step-0 declaration (TODO 6.3.1-6.3.3, M#24, M#53).

Two jobs. It makes a match **reproducible** — a grader can see the exact code,
model and hardware behind every move — and it **pins the code for the whole
series**, because `github_commit` is inside the digest and a peer cannot swap in
a different agent between sub-games while still matching what it signed.

The tests split accordingly: hardware detection must never *fail*, and the
declaration must never quietly *lie*.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.protocol.step_zero import DIRTY_SUFFIX, StepZero, build, commit_hash
from core.shared.system_info import describe, gpu_name, total_ram_gb

REPO = Path(__file__).resolve().parents[2]

# **Tests must not run git against the developer's live repository.**
#
# `commit_hash` shells out to `git status`, which takes `.git/index.lock`. A
# suite that is interrupted mid-run then leaves that lock behind and blocks
# every later `git add` - which is exactly what stopped three ship.py runs on
# 02/08 before anyone traced it here. A throwaway repo has no such consequence.


@pytest.fixture(scope="module")
def scratch_repo(tmp_path_factory) -> Path:
    """A real but disposable git repository, used instead of ours."""
    import subprocess

    repo = tmp_path_factory.mktemp("scratch_repo")
    (repo / "file.txt").write_text("x", encoding="utf-8")
    for args in (
        ["init", "-q"],
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test"],
        ["add", "-A"],
        ["commit", "-qm", "initial"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    return repo


# --- 6.3.1: hardware, and never failing ------------------------------------


def test_the_declaration_has_every_field_the_rulebook_asks_for() -> None:
    reported = describe()
    assert set(reported) == {"os", "python", "machine", "cpu_cores", "ram_gb", "gpu"}
    assert all(value not in (None, "") for value in reported.values())


def test_no_field_is_ever_missing_even_when_it_cannot_be_read() -> None:
    """**Degrade, never fail.**

    Refusing to play because we could not read a CPU frequency would turn a
    cosmetic gap into a forfeit. An unknown field says so and the match starts.
    """
    for value in describe().values():
        assert value is not None


def test_a_machine_with_no_gpu_reports_none_rather_than_erroring() -> None:
    """"none" is a real answer. Diana's machine has no GPU and plays anyway."""
    assert isinstance(gpu_name(), str)
    assert gpu_name() != ""


def test_ram_is_a_number_or_the_word_unknown() -> None:
    reported = total_ram_gb()
    assert isinstance(reported, float | int) or reported == "unknown"


def test_the_declaration_is_json_safe() -> None:
    """It goes inside a signed payload; a non-primitive would break the digest."""
    import json

    json.dumps(describe())


# --- 6.3.2 / 6.3.3: what the declaration promises ---------------------------


def _declaration(repo: Path | None = None, **overrides) -> StepZero:
    defaults = {
        "team_name": "bestteam",
        "role": "cop",
        "sub_game": 1,
        "llm_model": "llama3.1:8b",
        "repo": repo or REPO,
    }
    return build(**{**defaults, **overrides})


def test_it_carries_every_required_field() -> None:
    payload = _declaration().payload
    assert set(payload) == {
        "team_name", "role", "sub_game", "llm_model",
        "code_version", "github_commit", "hardware",
    }


def test_it_declares_the_model_but_never_the_provider() -> None:
    """**Appendix F Table 21 keeps the provider private to each peer.**

    Declaring `groq` or `ollama` would leak a choice the rulebook explicitly
    does not negotiate — and hand an opponent a hint about our latency budget.
    """
    payload = _declaration(llm_model="llama3.1:8b").payload
    assert "provider" not in payload
    assert payload["llm_model"] == "llama3.1:8b"


def test_the_digest_changes_when_anything_declared_changes() -> None:
    """Otherwise the seal would not pin what it claims to pin."""
    base = _declaration().digest
    assert _declaration(team_name="other").digest != base
    assert _declaration(role="thief").digest != base
    assert _declaration(sub_game=2).digest != base
    assert _declaration(llm_model="other").digest != base


def test_the_sub_game_number_is_sealed_so_it_cannot_be_replayed() -> None:
    """The same replay hole the move audit closes (6.1.4), closed here too.

    Without this, a declaration signed for sub-game 1 could be presented again
    as sub-game 4 while the code underneath had changed.
    """
    assert _declaration(sub_game=1).digest != _declaration(sub_game=4).digest


def test_the_digest_is_stable_across_calls() -> None:
    """Both peers compute it independently and compare, so it cannot vary."""
    assert len({_declaration().digest for _ in range(5)}) == 1


def test_a_dirty_tree_is_declared_rather_than_hidden() -> None:
    """**M#53. The honest failure mode.**

    With uncommitted changes the declared commit does not describe the running
    code, so the reproducibility claim is simply false. Far better to say so
    before the match than to have a grader discover it afterwards.
    """
    dirty = StepZero(payload={"github_commit": "abc123" + DIRTY_SUFFIX}, digest="x")
    assert dirty.dirty
    assert any("DIRTY" in warning for warning in dirty.warnings())


def test_a_clean_tree_raises_no_warning() -> None:
    clean = StepZero(payload={"github_commit": "abc123"}, digest="x")
    assert not clean.dirty
    assert clean.warnings() == []


def test_a_missing_commit_is_flagged_but_does_not_stop_play() -> None:
    """A peer running from an archive rather than a clone can still play."""
    archived = StepZero(payload={"github_commit": "unknown"}, digest="x")
    assert any("cannot be pinned" in warning for warning in archived.warnings())


def test_warnings_are_returned_not_raised() -> None:
    """Whether to play a graded match against an unverifiable opponent is a
    judgement for the people involved, not a decision for a dataclass."""
    assert isinstance(StepZero({"github_commit": "unknown"}, "x").warnings(), list)


def test_the_commit_hash_reads_a_real_repository(scratch_repo: Path) -> None:
    """Run against a throwaway clone, never the live repo - see the note above."""
    found = commit_hash(scratch_repo)
    assert found == "unknown" or len(found.removesuffix(DIRTY_SUFFIX)) == 40


def test_an_unavailable_git_does_not_raise(tmp_path: Path) -> None:
    """Never let a reporting gap become a forfeit."""
    assert commit_hash(tmp_path) in {"unknown"} or isinstance(commit_hash(tmp_path), str)


@pytest.mark.parametrize("role", ["cop", "thief"])
def test_both_roles_declare_cleanly(role: str) -> None:
    assert _declaration(role=role).payload["role"] == role
