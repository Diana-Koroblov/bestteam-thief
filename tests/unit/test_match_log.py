"""The log artefact, and whether it is actually replayable (TODO 7.2.3, T7.11-T7.12).

**The DoD here cannot be checked by reading the file.** "Sufficient for full
replay verification" is a claim about a round trip, so these tests do the round
trip: seal real commitments with the real `commitment` module, build the log,
write it, read it back off disk, and re-hash. Anything less would be asserting
that the fields *look* like enough.

The seals are genuine rather than hand-written digests. A test that invented its
own hash would pass against a log format that no real commitment could ever
survive.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.crypto.commitment import seal
from core.report.artefacts import write
from core.report.match_log import build_log, build_step, records, verify_log

ROLE = "cop"
MOVES = ("N", "E", "STAY", "S")


def sealed_steps(count: int = 4, scent: bool = False):
    """Return `(steps, nonces)` for *count* genuinely sealed turns."""
    steps, nonces = [], {}
    for index in range(count):
        state = {"cop": [0, index], "thief": [3, 3], "step": index}
        scent_digest = f"scent{index}" if scent else None
        locked = seal(state, MOVES[index % len(MOVES)], "truth", scent_digest=scent_digest)
        steps.append(
            build_step(
                step=index,
                claimed_digest=locked.digest,
                state=state,
                move=locked.move,
                intent=locked.intent,
                hint=f"heading somewhere {index}",
                scent_digest=scent_digest,
            )
        )
        nonces[str(index)] = locked.nonce
    return steps, nonces


def test_a_sealed_barrier_survives_the_round_trip(tmp_path: Path) -> None:
    """**C-018.** A walled turn must re-hash off disk, where the cell is a list.

    The barrier is the one field that is both declared for the reader and folded
    into the digest, so it is the one most able to pass in memory and fail on
    disk.
    """
    state = {"cop": [1, 1], "thief": [3, 3], "step": 0}
    locked = seal(state, "STAY", "truth", barrier_cell=(1, 2))
    step = build_step(
        step=0,
        claimed_digest=locked.digest,
        state=state,
        move="STAY",
        intent="truth",
        barrier_cell=(1, 2),
        sealed_barrier=True,
    )
    payload = build_log("gid", 1, ROLE, [step], {"0": locked.nonce})
    target = write(payload, tmp_path, "log.json")

    reloaded = json.loads(target.read_text(encoding="utf-8"))
    assert reloaded["steps"][0]["barrier_cell"] == [1, 2]
    assert verify_log(reloaded).passed


def test_a_declared_but_unsealed_barrier_still_audits_clean() -> None:
    """The case that would accuse an honest peer of forgery.

    A peer that declares placements without sealing them — legal, and what an
    opponent running the plain book does — must not fail its own audit. So the
    re-hash reads `sealed_barrier_cell`, which such a log does not have, and
    never the declaration.
    """
    state = {"cop": [1, 1], "thief": [3, 3], "step": 0}
    locked = seal(state, "STAY", "truth")
    step = build_step(
        step=0,
        claimed_digest=locked.digest,
        state=state,
        move="STAY",
        intent="truth",
        barrier_cell=(1, 2),
        sealed_barrier=False,
    )
    assert "sealed_barrier_cell" not in step
    payload = build_log("gid", 1, ROLE, [step], {"0": locked.nonce})
    assert verify_log(payload).passed


def test_a_forged_barrier_cell_is_caught() -> None:
    """Changing which cell was walled, after the fact, is what C-018 stops."""
    state = {"cop": [1, 1], "thief": [3, 3], "step": 0}
    locked = seal(state, "STAY", "truth", barrier_cell=(1, 2))
    step = build_step(
        step=0,
        claimed_digest=locked.digest,
        state=state,
        move="STAY",
        intent="truth",
        barrier_cell=(1, 2),
        sealed_barrier=True,
    )
    step["sealed_barrier_cell"] = [2, 2]
    payload = build_log("gid", 1, ROLE, [step], {"0": locked.nonce})
    assert not verify_log(payload).passed


def test_a_clean_log_verifies_off_disk(tmp_path: Path) -> None:
    """**T7.11.** The whole claim, end to end: seal, write, read, re-hash.

    Off disk rather than in memory on purpose — JSON turns tuples into lists
    and this is where that would bite, not in a dict that never left the
    process.
    """
    steps, nonces = sealed_steps()
    payload = build_log("gid", 3, ROLE, steps, nonces, outcome="capture")
    target = write(payload, tmp_path, "log.json")

    reloaded = json.loads(target.read_text(encoding="utf-8"))
    result = verify_log(reloaded)
    assert result.passed
    assert result.checked == 4
    assert "Verified OK" in result.describe()


def test_one_altered_move_is_caught_and_named(tmp_path: Path) -> None:
    """**T7.12.** A tampered log names the step. `TAMPERED` voids the match, so
    a verdict nobody can locate is a verdict nobody can defend against."""
    steps, nonces = sealed_steps()
    payload = build_log("gid", 3, ROLE, steps, nonces)
    payload["steps"][2]["move"] = "W"

    result = verify_log(payload)
    assert not result.passed
    assert result.failures[0][0] == 2
    assert "FAILED" in result.describe()


def test_a_sealed_scent_digest_survives_the_round_trip() -> None:
    """C-008: sealing the field is opt-in, and the log has to carry it or every
    digest fails on replay."""
    steps, nonces = sealed_steps(scent=True)
    assert verify_log(build_log("gid", 1, ROLE, steps, nonces)).passed


def test_an_unsealed_scent_digest_is_omitted_never_null() -> None:
    """**Mirrors `commitment_payload` exactly, and must.**

    The replay rebuilds the hashed payload from this file. A key the sealing
    peer left out has to be left out here too — a `null` surviving into the
    payload would change every digest and make an honest match look forged.
    """
    steps, _ = sealed_steps()
    assert "scent_digest" not in steps[0]


def test_nonces_are_merged_from_the_final_reveal() -> None:
    """They arrive last (M#18), and the shape says so rather than pretending."""
    steps, nonces = sealed_steps(2)
    payload = build_log("gid", 1, ROLE, steps, nonces)
    assert payload["steps"][0]["nonce"] == nonces["0"]
    assert payload["unverifiable_steps"] == []


def test_a_step_with_no_nonce_is_kept_and_flagged() -> None:
    """**Dropping it would produce a shorter log that audits clean** — which is
    exactly the forgery the audit exists to catch. Present and unverifiable is
    the honest record."""
    steps, nonces = sealed_steps(3)
    del nonces["1"]
    payload = build_log("gid", 1, ROLE, steps, nonces)

    assert payload["step_count"] == 3
    assert payload["unverifiable_steps"] == [1]
    assert not verify_log(payload).passed


def test_reader_only_fields_never_reach_the_hash() -> None:
    """`hint` and `barrier_cell` are for the reader; neither was inside the
    seal, and forwarding one would change every digest."""
    steps, nonces = sealed_steps(1)
    payload = build_log("gid", 1, ROLE, steps, nonces)
    assert payload["steps"][0]["hint"]
    assert verify_log(payload).passed


def test_the_barrier_cell_is_recorded_exactly(tmp_path: Path) -> None:
    """M#15/M#16 — the declaration must be exact, and JSON has no tuple."""
    steps, nonces = sealed_steps(1)
    steps[0] = build_step(**{**_without(steps[0], "nonce"), "barrier_cell": (2, 5)})
    target = write(build_log("gid", 1, ROLE, steps, nonces), tmp_path, "log.json")
    reloaded = json.loads(target.read_text(encoding="utf-8"))
    assert reloaded["steps"][0]["barrier_cell"] == [2, 5]


def _without(step: dict, *drop: str) -> dict:
    """Return *step* without *drop*, for rebuilding one in a test."""
    return {key: value for key, value in step.items() if key not in drop}


def test_a_log_missing_a_hashed_field_fails_loudly() -> None:
    """**Loud on purpose.** A log that cannot be replayed must not be reported
    as one that replayed with a few gaps."""
    steps, nonces = sealed_steps(1)
    payload = build_log("gid", 1, ROLE, steps, nonces)
    del payload["steps"][0]["claimed_digest"]
    with pytest.raises(KeyError, match="claimed_digest"):
        records(payload)


def test_an_empty_log_does_not_pass() -> None:
    """A log with no steps is a missing log, not a clean one — otherwise a peer
    escapes the audit by sending nothing."""
    assert not verify_log(build_log("gid", 1, ROLE, [], {})).passed


def test_the_log_names_the_config_it_was_played_under() -> None:
    """Filename proximity is not evidence; the digest is."""
    steps, nonces = sealed_steps(1)
    payload = build_log("gid", 1, ROLE, steps, nonces, config_sha256="deadbeef")
    assert payload["config_sha256"] == "deadbeef"


def test_a_step_with_no_step_number_fails_at_build_time() -> None:
    """**A silent gap in this artefact is indistinguishable from forgery.**

    A defensive `.get` would have filed the step as merely unverifiable, which
    reads as an honest missing nonce rather than as the caller bug it is.
    """
    with pytest.raises(KeyError, match="step"):
        build_log("gid", 1, ROLE, [{"claimed_digest": "x"}], {})
