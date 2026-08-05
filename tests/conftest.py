"""Shared fixtures (TODO 1.5.1).

Two of the six fixtures named in the TODO — ``mock_llm_provider`` and
``mock_mcp_peer`` — are deliberately **absent**. The interfaces they would
double do not exist yet: the LLM provider seam arrives in Phase 7 and the MCP
peer in Phase 2. A mock written before its interface is a mock of a guess, and
it would need rewriting the moment the real thing lands. They are tracked
against those phases instead.

The DoD requires every fixture here to be used by at least one test, so nothing
in this file is speculative.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from core.domain.barriers import BarrierManager
from core.domain.board import Board, Position
from core.domain.game_state import GameState
from core.domain.rules import Rules
from core.domain.scoring import ScoreTable
from core.shared.config_manager import Config, load_config
from tests.paths import PRESENT_ROLES, brain_class, role_dir

DEFAULT_COP: Position = (0, 0)
DEFAULT_THIEF: Position = (3, 3)

# A published repository ships **one** role package (ADR-001), so a test module
# that imports the other one at top level takes the whole suite down during
# *collection* — before any skip marker gets a chance to run. `needs_brain` in
# `tests/paths.py` cannot help here: a marker skips a test, it does not stop the
# import that precedes it.
#
# So the modules that unit-test one role's strategy are dropped from collection
# outright when that role is absent, and they carry a `test_<role>_` prefix to
# say so in their own filenames. Caught by `scripts/check_split_repos.py`, which
# is the only place the split is real before a push.
_ROLE_ONLY_PREFIXES = {"police": "unit/test_cop_", "thief": "unit/test_thief_"}

collect_ignore_glob = [
    f"{prefix}*.py" for role, prefix in _ROLE_ONLY_PREFIXES.items() if brain_class(role) is None
]


@pytest.fixture(scope="session")
def minimal_config() -> Config:
    """The real shipped configuration for whichever role this repository holds.

    Deliberately the genuine file rather than a hand-built dict: a fixture that
    invents its own values would keep passing after the shipped config drifted
    away from Appendix F, which is the one thing these tests exist to catch.
    """
    return load_config(role_dir(PRESENT_ROLES[0]))


@pytest.fixture
def board_7x7() -> Board:
    """The default board. Appendix F minimum, and what every match starts from."""
    return Board(grid_size=7)


@pytest.fixture
def rules(board_7x7: Board, minimal_config: Config) -> Rules:
    """Terminal conditions under our negotiated defaults."""
    return Rules.from_config(minimal_config, board_7x7)


@pytest.fixture
def score_table(minimal_config: Config) -> ScoreTable:
    """The Appendix F scoring values, read from the shipped config."""
    return ScoreTable.from_config(minimal_config)


@pytest.fixture
def barrier_manager(board_7x7: Board, minimal_config: Config) -> BarrierManager:
    """A manager at the negotiated quota, not a hardcoded 14."""
    return BarrierManager(
        max_barriers=minimal_config.require("movement_and_barriers.max_barriers"),
        board=board_7x7,
    )


@pytest.fixture
def game_state_factory() -> Callable[..., GameState]:
    """Return a builder for game states with sensible starting defaults.

    Keyword arguments override any field, so a test states only what it cares
    about:

        state = game_state_factory(thief=(0, 0), step=34)
    """

    def build(
        cop: Position = DEFAULT_COP,
        thief: Position = DEFAULT_THIEF,
        barriers: frozenset[Position] | None = None,
        **fields: object,
    ) -> GameState:
        return GameState(
            cop=cop,
            thief=thief,
            barriers=barriers if barriers is not None else frozenset(),
            **fields,  # type: ignore[arg-type]
        )

    return build
