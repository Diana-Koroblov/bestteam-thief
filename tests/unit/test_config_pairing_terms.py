"""Our C-00x choices are pairing terms, not contract keys (imreeyal item 9).

Split out of `test_config_spec.py` and `test_config_manager.py` when both crossed
the 150-line limit. The grouping is not arbitrary: every test here exists because
the agreed contract became the **9-key Appendix F shape**, and each one guards a
different half of that move.

The change in one line: our six mechanism choices — the `capture` block, the
barrier seal flag and three pheromone flags — used to live in the shared
`game.json`. imreeyal's file never carried them, which was the whole of the
canonical digest mismatch (our `17606f14` against their `cca1243e`) over content
that differed in no rule at all. They now live in private config and bind as
terms settled in the thread.

Two failure modes that would each produce a green suite and a lost match:

* **Demanding them in a contract.** A peer sending the plain shape — including
  us, now — would be refused over rows the book does not state.
* **Forgetting we still need the values.** They are not decoration: three are
  read through `require()`, and the rest default to values we did **not** agree.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.shared.config_manager import ConfigVersionError, load_config
from core.shared.config_spec import dotted_get
from tests.paths import PRESENT_ROLES, role_dir, shared_config

SHIPPED = shared_config()

# The six that moved. Named once, because two tests assert opposite things about
# them and a drifting pair of literals would let both pass while disagreeing.
MOVED = (
    "capture.resolution",
    "capture.stay_counts_as_move",
    "capture.swap_is_capture",
    "movement_and_barriers.seal_barrier_cell",
    "pheromones.decay_model",
    "pheromones.field_includes_current_turn",
    "pheromones.seal_scent_digest",
)

AGREED = {
    "capture.resolution": "after_moves",
    "capture.stay_counts_as_move": False,
    "capture.swap_is_capture": False,
    "movement_and_barriers.seal_barrier_cell": True,
    "pheromones.decay_model": "subtractive",
    "pheromones.field_includes_current_turn": True,
    "pheromones.seal_scent_digest": True,
}


def _write(directory: Path, shared: dict) -> Path:
    """Write a throwaway role directory holding only a shared contract."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "game.json").write_text(json.dumps(shared), encoding="utf-8")
    return directory


def test_our_extensions_are_absent_from_the_agreed_contract() -> None:
    """The filed artefact is the 9-key shape, and this is what makes it one."""
    contract = shared_config()
    for path in MOVED:
        assert dotted_get(contract, path, None) is None, f"{path} is not a contract key"


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_the_merged_configuration_still_holds_every_extension(role: str) -> None:
    """**The safety `classify` gave up, asserted where it belongs.**

    `classify` no longer reports an absent `ours` row, because a contract is not
    supposed to carry one. That would be a hole if nothing checked that *we*
    still hold the values, and holding them is not optional:

    * the three `capture` keys are read through `require()` in the rules engine,
      so absent means a peer that cannot build its rules — a technical loss
      worth 0 to **both** teams;
    * `pheromones.decay_model` defaults to `"multiplicative"`, the model we did
      **not** agree, silently reblurring the belief filter;
    * the two seal flags default to `False`, silently changing our commitment
      shape under an opponent auditing against the old one.

    Merged is what we play. The contract is only what we agreed.
    """
    config = load_config(role_dir(role))
    for path, expected in AGREED.items():
        assert config.get(path) == expected, path


def test_an_absent_version_is_accepted(tmp_path: Path) -> None:
    """**Absent is silence; a stated incompatible version is a claim.**

    This gate used to require `version` in the shared file. The agreed 9-key
    contract carries none — theirs never did — so refusing absence would refuse
    every kit-conformant peer's contract, including the one we agreed to. Same
    treatment `schema_version` has always had, for the reason stated there.
    """
    shared = {key: value for key, value in SHIPPED.items() if key != "version"}
    assert load_config(_write(tmp_path / "role", shared)).get("scoring.tie_score") == 2


def test_a_stated_incompatible_version_is_still_refused(tmp_path: Path) -> None:
    """The half of the gate that still bites: a claim we cannot honour."""
    role = _write(tmp_path / "role", dict(SHIPPED, version="99.00"))
    with pytest.raises(ConfigVersionError, match="99.00"):
        load_config(role)


def test_incompatible_version_raises(tmp_path: Path) -> None:
    shared = dict(SHIPPED, version="2.00")
    role = _write(tmp_path / "role", shared)
    with pytest.raises(ConfigVersionError, match="cannot read"):
        load_config(role)


def test_same_major_version_is_accepted(tmp_path: Path) -> None:
    role = _write(tmp_path / "role", dict(SHIPPED, version="1.07"))
    assert load_config(role).get("scoring.tie_score") == 2
