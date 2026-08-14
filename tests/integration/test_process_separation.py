"""Separation, enforced against the real import graph (TODO 2.4.1).

Two mandatory rules meet here:

* **M#2** — the Cop's code and the Thief's code must not share live state. The
  book is blunt that this is not a style question: a shared module holding live
  state is a back door through which one agent can read the other's local truth,
  and it *"disqualifies the solution - even if the game works technically"*.
* **M#3** — one gateway between subsystems, so "which module changed the state"
  has exactly one answer.

Both are checked by parsing every file and resolving its imports, not by reading
the code and believing it. A convention nobody checks lasts about a week.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.shared.import_graph import build_graph

ROOT = Path(__file__).resolve().parents[2]

# Peripheral subsystems. Each may depend on `core.domain` and `core.shared`,
# and on nothing else at its own level: the strategy never calls the transport,
# the transport never touches the board.
PERIPHERAL = ("core.protocol", "core.infra", "core.ui")

# What a peripheral subsystem is allowed to reach.
FOUNDATIONS = ("core.domain", "core.shared", "core.crypto")

# The gateway. Only these may join subsystems together.
# `core.cli_commands` is `__main__`'s body, moved out when that file reached 149
# of its 150 permitted lines; `core.cli_negotiate` is the pre-match protocol moved
# out of *that* one at 110; `core.cli_play` is the match itself, which needs the
# transport and the protocol in one place because playing is precisely the act of
# joining them; `core.cli_compat` is that same act against a peer speaking the
# Appendix D protocol (C-019), and joins the same two for the same reason;
# `core.cli_handshake` is the retry that waits for an opponent to
# start, split out of `cli_play` at 151; and `core.cli_gui` hosts the Live GUI
# beside a running match, which no module below the gateway may do because it
# joins the window to the turn loop. They are one gateway with one permission —
# listing them here records where the CLI now lives, it does not widen the rule.
#
# This test is what noticed the third file, and every one since, on the run that
# added it. That is the point of writing the layering down rather than
# remembering it: a new module quietly acquiring gateway privileges is not
# something anyone spots in review.
GATEWAY = (
    "core.runtime",
    "core.sdk",
    "core.__main__",
    "core.cli_args",
    "core.cli_commands",
    "core.cli_negotiate",
    "core.cli_play",
    "core.cli_compat",
    "core.cli_handshake",
    "core.cli_gui",
)


# The shipped packages. Tests and scripts legitimately reach across subsystems —
# that is what a test is for — so they are not part of the architecture.
SOURCE_PACKAGES = ("core", "police", "thief")


@pytest.fixture(scope="module")
def graph() -> dict:
    """The import graph of shipped code only."""
    return build_graph(ROOT, packages=SOURCE_PACKAGES)


def _subsystem(name: str) -> str | None:
    """Return the subsystem a module belongs to, or None."""
    for prefix in (*PERIPHERAL, *FOUNDATIONS, *GATEWAY):
        if name == prefix or name.startswith(f"{prefix}."):
            return prefix
    return None


# --- M#2: the two roles never meet -----------------------------------------


def test_no_module_reachable_from_one_role_imports_the_other(graph: dict) -> None:
    """The rule the book calls disqualifying, checked on the actual graph."""
    for name, node in graph.items():
        if name.startswith("police"):
            assert not any(edge.startswith("thief") for edge in node.imports), name
        if name.startswith("thief"):
            assert not any(edge.startswith("police") for edge in node.imports), name


def test_core_never_imports_either_role(graph: dict) -> None:
    """Shared code stays role-blind, so one build cannot leak into the other."""
    for name, node in graph.items():
        if not name.startswith("core"):
            continue
        assert not any(edge.startswith(("police.", "thief.")) for edge in node.imports), name


def test_no_module_holds_state_for_both_roles(graph: dict) -> None:
    """M#2 is about *live state*, not merely imports.

    Sharing source is permitted and we do it deliberately; sharing a running
    object is the back door. The orchestrator owns state and is built per
    process with exactly one role, so a module importing both role packages
    would be the only way to hold two — and there is none.
    """
    both = [
        name
        for name, node in graph.items()
        if any(e.startswith("police") for e in node.imports)
        and any(e.startswith("thief") for e in node.imports)
    ]
    assert both == []


# --- M#3: one gateway ------------------------------------------------------


def test_a_peripheral_subsystem_never_imports_another(graph: dict) -> None:
    """The strategy never calls the transport; the transport never sees the board."""
    offences: list[str] = []
    for name, node in graph.items():
        origin = _subsystem(name)
        if origin not in PERIPHERAL:
            continue
        for edge in node.imports:
            target = _subsystem(edge)
            if target in PERIPHERAL and target != origin:
                offences.append(f"{name} -> {edge}")
    assert offences == [], "peripheral modules must meet only through the gateway (M#3)"


def test_peripheral_subsystems_may_use_the_foundations(graph: dict) -> None:
    """The rule forbids sideways edges, not downward ones — confirm it is not vacuous."""
    downward = [
        f"{name} -> {edge}"
        for name, node in graph.items()
        if _subsystem(name) in PERIPHERAL
        for edge in node.imports
        if _subsystem(edge) in FOUNDATIONS
    ]
    assert downward, "expected at least one peripheral module to use core.domain"


def test_the_foundations_never_depend_upwards(graph: dict) -> None:
    """``core.domain`` must stay testable with no network, no clock, no config file."""
    for name, node in graph.items():
        if _subsystem(name) != "core.domain":
            continue
        for edge in node.imports:
            assert _subsystem(edge) in ("core.domain", "core.shared", "core.crypto"), (
                f"{name} imports {edge}; the domain layer must stay pure"
            )


def test_only_the_gateway_joins_subsystems(graph: dict) -> None:
    """Anything reaching two peripheral subsystems must live in the gateway."""
    for name, node in graph.items():
        touched = {_subsystem(edge) for edge in node.imports} & set(PERIPHERAL)
        if len(touched) > 1:
            assert _subsystem(name) in GATEWAY, f"{name} joins {sorted(touched)}"


def test_the_ui_reaches_nothing_but_the_facade(graph: dict) -> None:
    """Excellence guide §4.1, as a graph assertion rather than a grep."""
    for name, node in graph.items():
        if not name.startswith("core.ui"):
            continue
        for edge in node.imports:
            assert edge.startswith(("core.ui", "core.domain", "core.sdk")), f"{name} -> {edge}"


# --- M#25: movement is never decided by a language model -------------------

# Everything that decides a move. **Not just modules named "brain"**: the
# advanced Cop of Phase 8 is split across `police/search.py`,
# `police/evaluation.py`, `police/barrier_policy.py` and `police/phases.py`, and
# the earlier name-based check would have waved every one of them through. The
# rule was always about strategy code, so the test now says strategy code.
STRATEGY_PACKAGES = ("police", "thief")


def _is_strategy(name: str) -> bool:
    """Whether *name* is a module that participates in choosing a move."""
    return name.startswith(STRATEGY_PACKAGES) or "brain" in name


def test_no_brain_can_reach_a_language_model(graph: dict) -> None:
    """Ch. 6: "the move decision is always algorithmic and in Python code".

    A model hallucinates in Cartesian space — it will propose a move into a
    wall — and an illegal move is a technical loss (M#13). The model's job is
    the verbal layer only. Checked on the graph so no brain can acquire the
    dependency quietly.
    """
    forbidden = ("llm", "groq", "ollama", "anthropic", "openai")
    for name, node in graph.items():
        if not _is_strategy(name):
            continue
        for edge in node.imports:
            assert not any(word in edge.lower() for word in forbidden), f"{name} -> {edge}"


def test_a_brain_never_reaches_the_transport_or_the_protocol(graph: dict) -> None:
    """A strategy that could send its own messages could bypass commit-reveal."""
    for name, node in graph.items():
        if not _is_strategy(name):
            continue
        for edge in node.imports:
            assert not edge.startswith(("core.infra", "core.protocol")), f"{name} -> {edge}"


def test_the_check_covers_more_than_the_files_called_brain(graph: dict) -> None:
    """Otherwise the two tests above would pass by looking at almost nothing.

    Phase 8 is where a role package stops being one file, so the guard has to be
    seen covering the modules that arrived with it. Asserted against the role
    **this repository ships**, not both — demanding both would fail in every
    published repo, which is the mistake the split-repository gate exists to
    catch (see `test_the_brains_are_actually_in_the_graph`).
    """
    for role in STRATEGY_PACKAGES:
        if not (ROOT / role).is_dir():
            continue
        modules = {name for name in graph if name.startswith(f"{role}.")}
        assert modules, f"{role} ships no modules at all"
        assert modules <= {name for name in graph if _is_strategy(name)}, sorted(modules)


def test_the_brains_are_actually_in_the_graph(graph: dict) -> None:
    """Otherwise the two tests above pass by looking at nothing.

    Asserts the brains *this repository ships*, not both: a published repo holds
    one role package. Demanding both would fail in every real repository, which
    is the same mistake the split-repository gate exists to catch.
    """
    shipped = {f"{role}.brain" for role in ("police", "thief") if (ROOT / role).is_dir()}
    assert shipped, "no role package present at all"
    assert shipped <= set(graph)


def test_the_graph_is_not_empty(graph: dict) -> None:
    """Guards against a silent walk failure turning every test above green."""
    assert len(graph) > 25
    assert "core.runtime.orchestrator" in graph
