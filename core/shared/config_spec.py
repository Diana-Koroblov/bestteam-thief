"""The binding parameter table from Appendix F, as data.

Appendix F is the **only** source of truth for numeric values in this project,
and it assigns each parameter one of three statuses:

* ``fixed`` — may not change at all. Deviating disqualifies the team.
* ``minimum`` — may be raised by mutual agreement, **never** lowered (M#12).
* ``negotiable`` — any value both sides agree on.

Encoding that here rather than in prose means a proposed match configuration can
be *checked* instead of eyeballed. Agreeing to an illegal value disqualifies both
teams, so "the opponent asked for it" is not a defence — which is exactly why
this runs before a match rather than after.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "FIXED",
    "MINIMUM",
    "NEGOTIABLE",
    "Parameter",
    "PARAMETERS",
    "dotted_get",
    "legal",
    "classify",
    "violations",
    "invariant_violations",
]

FIXED = "fixed"
MINIMUM = "minimum"
NEGOTIABLE = "negotiable"


@dataclass(frozen=True)
class Parameter:
    """One entry of the Appendix F table.

    Attributes:
        path: Dotted location in the shared config, e.g. ``scoring.tie_score``.
        status: ``fixed``, ``minimum`` or ``negotiable``.
        default: The published value. For ``minimum`` this is the floor.
        ours: True for the seven rows **we** added, which are in no Appendix at
            all. It was a comment until an opponent's proposal needed reviewing
            and the distinction turned out to decide fixtures: a peer sending a
            plain Appendix F config is missing our extensions and is entirely
            legal, so refusing them over a row we invented would forfeit a match
            for nothing. See `classify`.
    """

    path: str
    status: str
    default: Any
    ours: bool = False


PARAMETERS: tuple[Parameter, ...] = (
    # --- board and agents -------------------------------------------------
    Parameter("board_and_agents.grid_size", MINIMUM, 7),
    Parameter("board_and_agents.num_agents", FIXED, 2),
    Parameter("board_and_agents.thief_start", NEGOTIABLE, [3, 3]),
    Parameter("board_and_agents.cop_start", NEGOTIABLE, [0, 0]),
    Parameter("board_and_agents.axis_origin_corner", NEGOTIABLE, "top-left"),
    Parameter("board_and_agents.axis_start_index", NEGOTIABLE, 0),
    # --- world ------------------------------------------------------------
    Parameter("world.map_area", NEGOTIABLE, "New York"),
    Parameter("world.hint_max_words", NEGOTIABLE, 15),
    # --- movement and barriers -------------------------------------------
    Parameter("movement_and_barriers.move_set", FIXED, ["N", "S", "E", "W", "STAY"]),
    Parameter("movement_and_barriers.max_barriers", MINIMUM, 14),
    Parameter("movement_and_barriers.max_moves", MINIMUM, 35),
    Parameter("movement_and_barriers.survival_threshold", MINIMUM, 35),
    # Our addition. See CONTRADICTIONS C-018.
    Parameter("movement_and_barriers.seal_barrier_cell", NEGOTIABLE, True, ours=True),
    # --- scoring ----------------------------------------------------------
    Parameter("scoring.capture_cop", FIXED, 20),
    Parameter("scoring.capture_thief", FIXED, 5),
    Parameter("scoring.survival_cop", FIXED, 5),
    Parameter("scoring.survival_thief", FIXED, 10),
    Parameter("scoring.tie_score", FIXED, 2),
    Parameter("scoring.technical_loss", FIXED, 0),
    # --- pheromones -------------------------------------------------------
    Parameter("pheromones.pheromone_center_intensity", FIXED, 0.9),
    Parameter("pheromones.pheromone_decay", FIXED, 0.10),
    Parameter("pheromones.pheromone_grid_size", FIXED, 5),
    # The reference constitution's own extra key — a floor under the centre
    # intensity, which the reference signs as a term and imreeyal's game.json
    # carries explicitly. In no Appendix, like our seven below, and `ours`
    # marks exactly that leniency: a peer sending a plain Appendix F config
    # without it stays legal (added 14/08 when our file adopted it verbatim).
    Parameter("pheromones.pheromone_min_center_intensity", NEGOTIABLE, 0.5, ours=True),
    # Our additions, all negotiable. See CONTRADICTIONS C-005, C-007, C-008.
    Parameter("pheromones.decay_model", NEGOTIABLE, "multiplicative", ours=True),
    Parameter("pheromones.field_includes_current_turn", NEGOTIABLE, True, ours=True),
    Parameter("pheromones.seal_scent_digest", NEGOTIABLE, True, ours=True),
    # --- capture resolution (C-006), all negotiable ------------------------
    Parameter("capture.resolution", NEGOTIABLE, "after_moves", ours=True),
    Parameter("capture.stay_counts_as_move", NEGOTIABLE, False, ours=True),
    Parameter("capture.swap_is_capture", NEGOTIABLE, True, ours=True),
    # --- network and league ----------------------------------------------
    Parameter("network_and_league.response_timeout_sec", NEGOTIABLE, 30),
    Parameter("network_and_league.watchdog_timeout_sec", NEGOTIABLE, 60),
    Parameter("network_and_league.num_games", FIXED, 6),
    Parameter("network_and_league.diversity_reward", FIXED, 10),
    Parameter("network_and_league.min_games_to_pass", FIXED, 2),
    Parameter("network_and_league.max_games_per_team", FIXED, 10),
    Parameter("network_and_league.token_budget_per_series", NEGOTIABLE, 200_000),
    # --- gatekeeper -------------------------------------------------------
    Parameter("rate_limiter_gatekeeper.requests_per_minute", MINIMUM, 30),
    Parameter("rate_limiter_gatekeeper.concurrent_requests", MINIMUM, 2),
    Parameter("rate_limiter_gatekeeper.retry_backoff_sec", MINIMUM, 5),
    Parameter("rate_limiter_gatekeeper.max_retries", MINIMUM, 3),
    Parameter("rate_limiter_gatekeeper.queue_depth", MINIMUM, 100),
)

_MISSING = object()


def dotted_get(data: dict, path: str, default: Any = _MISSING) -> Any:
    """Return the value at a dotted *path*, or *default* when absent."""
    node: Any = data
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            if default is _MISSING:
                raise KeyError(path)
            return default
        node = node[key]
    return node


def classify(config: dict) -> tuple[list[str], list[str]]:
    """Return *config*'s breaches split into ``(illegal, absent)``.

    The split exists because the two call for opposite responses, and merging
    them is only safe when the configuration is our own.

    * **illegal** — a *fixed* value changed or a *minimum* lowered. Agreeing to
      one disqualifies **both** teams, so "the opponent asked for it" is not a
      defence (M#12). Never negotiable, by us or by them.
    * **absent** — a key their proposal does not carry. Seven of the rows above
      are **our own** additions and appear in no Appendix, so a peer sending a
      plain Appendix F config is missing them and is entirely legal; refusing
      would forfeit a fixture over a rule the book does not state. Each line
      therefore says which kind it is, and a human settles it before play.

    For our own configuration the distinction does not arise — an absent key is
    a value we cannot play with either way — which is why `violations` still
    returns both together and `load_config` still refuses on either.
    """
    illegal: list[str] = []
    absent: list[str] = []
    for parameter in PARAMETERS:
        value = dotted_get(config, parameter.path, None)
        if value is None:
            source = "our extension, in no Appendix" if parameter.ours else "Appendix F"
            absent.append(f"{parameter.path}: missing ({source})")
        elif legal(parameter, value):
            continue
        elif parameter.status == FIXED:
            illegal.append(
                f"{parameter.path}: {value!r} but this value is FIXED at {parameter.default!r}"
            )
        else:
            illegal.append(
                f"{parameter.path}: {value!r} is below the binding minimum "
                f"{parameter.default!r} - raising is legal, lowering is not (M#12)"
            )
    return illegal, absent


def legal(parameter: Parameter, value: Any) -> bool:
    """Whether *value* is permitted for *parameter* by Appendix F's status column.

    Separate from `classify` because two callers need the same answer and only
    one of them wants a sentence. A reviewer listing an opponent's changes must
    not present a lowered minimum as a judgement call *and* refuse it two lines
    higher — a document that contradicts itself is worse than one that is merely
    wrong, and this one exists to settle disputes.
    """
    if parameter.status == FIXED:
        return value == parameter.default
    if parameter.status == MINIMUM:
        return value >= parameter.default
    return True


def violations(config: dict) -> list[str]:
    """Return a human-readable list of Appendix F breaches in *config*.

    An empty list means the configuration is legal to play. Missing keys are
    reported too: a value that is absent is a value neither peer agreed on.
    """
    illegal, absent = classify(config)
    return illegal + absent


def invariant_violations(config: dict) -> list[str]:
    """Return breaches of invariants Appendix F permits but the game cannot survive.

    These are legal under the letter of Appendix F and still produce a game with
    no defined outcome, so we refuse to sign them. See docs/PARAMETERS.md 4.2.
    """
    found: list[str] = []
    max_moves = dotted_get(config, "movement_and_barriers.max_moves", None)
    survival = dotted_get(config, "movement_and_barriers.survival_threshold", None)
    if max_moves is not None and survival is not None and survival != max_moves:
        found.append(
            f"survival_threshold ({survival}) != max_moves ({max_moves}): both are "
            "minimums and may be raised independently, but the win conditions are only "
            "defined when they are equal. Raise them together or not at all "
            "(docs/PARAMETERS.md 4.2)."
        )
    return found
