"""**Local truth: the test whose failure is project disqualification** (7.4.2).

M#8 and M#9 forbid displaying the objective board state. This is not defensive
programming — it is insurance against a mistake that ends the project, made by
somebody adding a debug label at midnight.

So it is checked three ways, because one way is a promise and three are a
control:

1. **By type.** `GuiState` has no field that could hold the opponent's position.
2. **By construction.** It is built from an `Observation`, which has no such
   field either, so there is nothing to build it from.
3. **By import.** `core/ui/` reaches nothing below `core/sdk/` (7.5.4), so no
   GUI module can go and fetch what it was not given.

Deliberately **not** excluded from coverage even though `core/ui/` is: this is a
correctness test, not a rendering test (PRD 7 §5).
"""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import pytest

from core.domain.board import Board
from core.domain.brain_base import Observation
from core.sdk.peer_sdk import PeerSDK
from core.sdk.view_state import LOCKED, YOUR_TURN, GuiState, heat_colour
from tests.paths import PRESENT_ROLES, REPO_ROOT, role_dir

UI_DIR = REPO_ROOT / "core" / "ui"

# Anything naming the other side. `own_position` is legitimate and must not trip
# this, so the patterns are about the *opponent*, not about positions.
FORBIDDEN_NAMES = ("opponent", "thief_position", "cop_position", "true_position", "game_state")


@pytest.fixture
def observation() -> Observation:
    return Observation(
        board=Board(grid_size=7),
        own_position=(2, 2),
        barriers=frozenset({(0, 1)}),
        step=4,
        barriers_remaining=9,
        belief={(3, 3): 0.5, (4, 4): 0.25, (1, 1): 0.25},
        hints=("heading north",),
    )


# --- 1. by type -------------------------------------------------------------


def test_the_state_has_nowhere_to_put_the_opponents_position() -> None:
    """**Never handing the data over cannot fail; filtering it can.**

    Filtering a `GameState` at render time works until somebody adds a debug
    label, and that failure is silent, visible only on screen, and worth the
    whole project.
    """
    names = {member.name for member in fields(GuiState)}
    for forbidden in FORBIDDEN_NAMES:
        assert not any(forbidden in name for name in names), f"{forbidden} in {names}"


def test_the_state_carries_a_distribution_not_a_position(observation) -> None:
    """A belief is what we *infer*. Being wrong about it is the game."""
    state = GuiState.from_observation(observation)
    assert isinstance(state.belief, dict)
    assert state.own_position == (2, 2)


# --- 2. by construction -----------------------------------------------------


def test_the_source_observation_has_no_opponent_position() -> None:
    """The GUI gets the same view as the brain. If the display could show what
    the strategy cannot use, the two are looking at different games."""
    names = {member.name for member in fields(Observation)}
    for forbidden in FORBIDDEN_NAMES:
        assert not any(forbidden in name for name in names)


@pytest.mark.parametrize("role", PRESENT_ROLES)
def test_the_sdk_frame_never_contains_both_positions(role: str) -> None:
    """The live path, end to end, on the real shipped config."""
    from core.protocol.schemas import Role

    sdk = PeerSDK(role_dir(role), Role.COP if role == "police" else Role.THIEF)
    state = sdk.gui_state()
    view = sdk.board_view()

    # `board_view` legitimately holds both — it is for the CLI and self-play.
    assert view.cop and view.thief
    # The GUI frame holds exactly one, and it is ours.
    assert state.own_position in (view.cop, view.thief)
    assert not any(getattr(state, name, None) for name in FORBIDDEN_NAMES)


# --- 3. by import -----------------------------------------------------------


def imported_modules(path: Path) -> set[str]:
    """Return every module *path* imports, by AST rather than by grep."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
        elif isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
    return found


@pytest.mark.parametrize("module", sorted(UI_DIR.rglob("*.py")), ids=lambda p: p.name)
def test_the_ui_reaches_nothing_below_the_sdk(module: Path) -> None:
    """**7.5.4, X §4.1.** `core.ui` imports only `core.sdk`.

    By AST, not by grep: a grep for `from core.domain` misses
    `import core.domain.board` and would pass a module that reached straight
    past the facade.
    """
    forbidden = ("core.domain", "core.runtime", "core.protocol", "core.infra", "core.crypto")
    for imported in imported_modules(module):
        assert not imported.startswith(forbidden), f"{module.name} imports {imported}"


def test_no_ui_module_calls_board_view() -> None:
    """`board_view()` carries **both** true positions.

    It is legitimate — the CLI and self-play use it — which is exactly why the
    GUI must be checked for it rather than trusted not to reach for the nearest
    convenient accessor.

    By AST again, and the first draft of this test is why: a substring search
    fails on the docstring that *explains* the rule, so the only way to keep it
    passing would have been to stop writing the explanation down.
    """
    for module in UI_DIR.rglob("*.py"):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        accessed = {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        } | {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        }
        assert "board_view" not in accessed, module.name


# --- the heatmap and the banner (7.4.1.a, 7.4.1.c) --------------------------


def test_the_deepest_cell_is_the_posterior_argmax(observation) -> None:
    """**T7.14.** Otherwise the heatmap is decoration that disagrees with the
    belief it claims to draw."""
    state = GuiState.from_observation(observation)
    assert state.hottest() == (3, 3)
    assert state.heat((3, 3)) == 1.0
    assert state.heat((4, 4)) == 0.5


def test_intensity_is_normalised_against_the_peak() -> None:
    """A uniform prior over 47 cells peaks at 0.021 and would render as a blank
    board — hiding the one thing the heatmap exists to show."""
    flat = GuiState(grid_size=7, own_position=(0, 0), belief=dict.fromkeys(
        [(r, c) for r in range(7) for c in range(7)], 1 / 49
    ))
    assert flat.heat((3, 3)) == 1.0


def test_darker_red_means_higher_probability() -> None:
    """7.4.1.a, as arithmetic rather than as a screenshot."""
    cold, warm, hot = heat_colour(0.0), heat_colour(0.5), heat_colour(1.0)
    assert cold != warm != hot
    assert _redness(hot) > _redness(warm) > _redness(cold)


def _redness(colour: str) -> float:
    """How dark the red is: full red channel minus the other two."""
    red, green, blue = (int(colour[i : i + 2], 16) for i in (1, 3, 5))
    return red - (green + blue) / 2


def test_an_empty_belief_renders_cold_rather_than_crashing() -> None:
    """Before the first hint there is nothing to draw, and that is not an error."""
    blank = GuiState(grid_size=7, own_position=(0, 0))
    assert blank.hottest() is None
    assert blank.heat((0, 0)) == 0.0


def test_input_is_ignored_while_locked() -> None:
    """**7.4.1.c.** Our commit is already on the wire.

    Accepting a keystroke here would let a human change a move the opponent
    holds a digest of — the exact failure commit-reveal exists to prevent,
    arriving through the keyboard instead of the network.
    """
    live = GuiState(grid_size=7, own_position=(0, 0), locked=False)
    held = GuiState(grid_size=7, own_position=(0, 0), locked=True)

    assert live.accepts_input() and live.banner() == YOUR_TURN
    assert not held.accepts_input() and held.banner() == LOCKED
