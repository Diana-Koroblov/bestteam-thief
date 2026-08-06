"""Run whole sub-games in one process. No network, no LLM, no tokens.

Strategy is the grade, and you cannot tune what you cannot measure. Everything
from here on is A/B'd against the baselines rather than trusted, and this is
what makes that cheap enough to do on every change: a hundred sub-games in
seconds, for nothing.

**This is not a referee.** It uses the same `core.domain` rules both peers
enforce independently in a real match. If it disagreed with them the measurement
would be meaningless, so it has no rules of its own — it drives the two brains
and applies the engine.

Both agents move **simultaneously**, as commit-reveal requires: neither
decision sees the other. Deciding sequentially would let the second brain react
to the first and quietly inflate whichever role moved last.

**Hints and scent are exchanged here too, on the protocol's own timing** (TODO
4.1.6, 8.3.4). Both travel with the reveal of the turn that produced them, so
both are first readable on turn *k+1*: our move for turn *k* is sealed before
their reveal for turn *k* arrives, and that ordering is the whole of
commit-reveal rather than an inconvenience around it.

🐛 **The scent field used not to be held back, and every Phase 8 number was
measured through that hole.** With both trails in one process there was nothing
to stop `observe` reading the deposit the opponent was laying *this* turn, one
turn fresher than any wire can deliver. `test_the_harness_shows_brains_no_more
_than_a_real_match_does` is named for exactly this and asserted only that the
live belief summed to 1.0 — a guard that could not fail. The field is now taken
from `sent`, which is written at the end of the turn.

The sentences come from the template bank, so this stays free and deterministic —
but they are real sentences through the real safety rules, read by the real
parser, because the point of measuring the verbal layer is to measure the one
that will actually play.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core.domain.barriers import BarrierManager, PlacementOutcome
from core.domain.board import Board, Position
from core.domain.brain_base import BrainBase, Decision, Observation
from core.domain.connectivity import are_connected, exit_count
from core.domain.filter import BeliefFilter
from core.domain.game_state import GameState
from core.domain.movement import resolve_move
from core.domain.rules import Outcome, Rules, Verdict
from core.infra.llm.writer import HintWriter, compass_word

__all__ = ["SubGameResult", "play_sub_game"]

# One writer, shared by both sides. `HintWriter.write` holds no per-peer state
# and the template bank keys on the prompt, which already carries the step and
# the bearing — so two writers would produce identical text at twice the cost.
_WRITER = HintWriter()


@dataclass
class SubGameResult:
    """What one sub-game produced, and enough detail to explain why.

    Attributes:
        outcome: The verdict and the rule that ended it.
        steps: Turns played.
        barriers_placed: Walls the Cop actually spent.
        cop_separations: Turns on which the Cop could **not** reach the Thief.
            The self-inflicted loss from ``connectivity.py``. **Must be 0** for
            any cop we would field (TODO 3.5.4).
        history: Every state, for rendering and for the replay.
        reasons: Each turn's ``(cop_reason, thief_reason)``, so a surprising
            game explains itself instead of being a sequence of moves.
    """

    outcome: Outcome
    steps: int = 0
    barriers_placed: int = 0
    cop_separations: int = 0
    history: list[GameState] = field(default_factory=list)
    reasons: list[tuple[str, str]] = field(default_factory=list)


def _observe(
    state: GameState,
    board: Board,
    own: Position,
    remaining: int,
    belief: dict[Position, float],
    known: Position | None = None,
    hints: tuple[str, ...] = (),
) -> Observation:
    """Build one side's view.

    Args:
        known: **Measurement only.** When set, the belief collapses to a point
            mass on that cell — a perfect-information agent.
        hints: Every hint the opponent has revealed so far, oldest first — the
            same cumulative tuple `PeerRuntime.observe` builds, so a brain that
            reads it here reads the identical shape in a graded match.

    ``known`` exists to measure the *ceiling*: how well a strategy plays when
    its belief is perfect. The gap between that and normal play is exactly what
    the Phase 4 belief filter is worth, which turns "is the filter good?" into a
    number instead of an opinion.

    A brain cannot ask for this. The harness passes it, never the agent, and
    ``PeerRuntime`` has no equivalent — so it can never leak into a real match.
    """
    return Observation(
        board=board,
        own_position=own,
        barriers=state.barriers,
        step=state.step,
        barriers_remaining=remaining,
        belief={known: 1.0} if known else belief,
        hints=hints,
    )


def _said(decision: Decision, step: int) -> str:
    """Render one turn's claim as the sentence the opponent will actually read.

    Runs the decision through the same `HintWriter` a live peer uses, on the
    `template` provider: zero tokens, deterministic from the prompt's hash, and
    subject to every rule in `safety.py`. Writing a bare phrase here instead
    would measure a verbal layer nobody plays — the parser's confidence is
    computed from real sentence shape, hedges and negations included.
    """
    return _WRITER.write(compass_word(decision.claim), decision.intent, step).text


def _apply(decision: Decision, position: Position, state: GameState, board: Board) -> Position:
    """Return where an agent ends up, holding position on an illegal move.

    A brain that proposes an illegal move would forfeit in a real match. Here
    it holds instead, so one bad decision does not abort a hundred-game batch —
    and the reason string still records what it tried.
    """
    try:
        return resolve_move(position, decision.move, state.barriers, board)
    except ValueError:
        return position


def play_sub_game(
    cop: BrainBase,
    thief: BrainBase,
    rules: Rules,
    quota: int,
    start: GameState,
    oracle: bool = False,
) -> SubGameResult:
    """Play one sub-game to a terminal state and return what happened.

    Args:
        cop: The Cop's brain.
        thief: The Thief's brain.
        rules: Terminal conditions, built from the negotiated config.
        quota: ``max_barriers``.
        start: The opening position.
        oracle: **Measurement only.** Give the Cop the Thief's true position,
            to measure the ceiling a perfect belief would reach. Never used in
            a real match; see ``_observe``.
    """
    board = rules.board
    barriers = BarrierManager(max_barriers=quota, board=board)
    state = start
    rate, model = 0.10, "multiplicative"
    cop_side = BeliefFilter(board=board, rate=rate, model=model)
    thief_side = BeliefFilter(board=board, rate=rate, model=model)
    # What each side has *received*. A field is transmitted with the reveal of
    # the turn that produced it, so it is first readable on the turn after —
    # see the note in `play_sub_game`.
    sent: dict[str, dict[Position, float]] = {"cop": {}, "thief": {}}
    result = SubGameResult(outcome=Outcome(Verdict.SURVIVAL, "not started"))
    result.history.append(state)
    # What each side has *heard*, which is what the opponent revealed on earlier
    # turns. Never this turn's: a hint travels with the reveal it was sealed
    # beside, so it cannot reach the opponent before their own move is committed.
    heard: dict[str, tuple[str, ...]] = {"cop": (), "thief": ()}

    while True:
        if not are_connected(state.cop, state.thief, state.barriers, board):
            result.cop_separations += 1

        # Both agents emit, then each reads only the opponent's trail (Ch. 4)
        # **as it stood at the end of the previous turn**. Reading the field
        # they are depositing right now would hand both brains a turn of scent
        # commit-reveal cannot deliver: our move for this turn is sealed before
        # their reveal for this turn arrives.
        cop_side.deposit(state.cop)
        thief_side.deposit(state.thief)
        cop_side.observe(sent["thief"], state.barriers, state.cop)
        thief_side.observe(sent["cop"], state.barriers, state.thief)

        seen = state.thief if oracle else None
        cop_move = cop.decide(
            _observe(
                state, board, state.cop, barriers.remaining, cop_side.belief, seen, heard["cop"]
            )
        )
        # The Thief is told the true remaining quota, not 0. Every placement is
        # declared with its exact cell (M#15), so counting what the Cop has left
        # is public arithmetic, not a leak — and `PeerRuntime.observe` has always
        # passed the real number for both roles. Hardcoding 0 here made the
        # harness disagree with the live runtime, so a thief strategy tuned in
        # self-play would meet a different observation in a graded match.
        thief_move = thief.decide(
            _observe(
                state, board, state.thief, barriers.remaining, thief_side.belief, None, heard["thief"]
            )
        )
        result.reasons.append((cop_move.reason, thief_move.reason))
        # Both peers reveal: the hint and the scent field travel together, and
        # neither is readable before the next turn.
        sent = {"cop": dict(cop_side.trail), "thief": dict(thief_side.trail)}
        heard = {
            "cop": heard["cop"] + (_said(thief_move, state.step),),
            "thief": heard["thief"] + (_said(cop_move, state.step),),
        }

        before = state
        # The Thief's destination is resolved **first**, against the barriers as
        # they stood when both sides committed, and then handed to the placement
        # so capture is judged on where the Thief actually ends up (C-006b).
        # Doing it the other way round let a Thief walk into the wall being
        # built and stand inside it — see `tests/unit/test_simultaneous_barrier.py`.
        thief_to = _apply(thief_move, state.thief, state, board)
        placed = _place(cop_move, barriers, state, thief_to)
        state = _advance(state, cop_move, board, placed, thief_to)
        result.history.append(state)

        outcome = _resolve(before, state, rules, placed, barriers)
        if outcome is not None:
            result.outcome = outcome
            break

    result.steps = state.step
    result.barriers_placed = barriers.placed_count
    return result


def _place(decision: Decision, barriers: BarrierManager, state: GameState, thief_to: Position):
    """Apply a barrier placement if the Cop asked for one.

    Args:
        thief_to: Where the Thief ends this turn, **not** where it started.
            `capture.resolution = "after_moves"` evaluates positions once both
            actions apply, so this is the cell M#46 is judged against — a wall on
            a vacated cell misses, and a wall on the cell the Thief steps onto
            captures. Both halves follow from the same value.
    """
    if decision.barrier is None:
        return None
    return barriers.place(decision.barrier, state.cop, thief_pos=thief_to)


def _advance(state, cop_move, board, placed, thief_to: Position) -> GameState:
    """Return the next state with both moves applied simultaneously.

    *thief_to* is passed in rather than recomputed so the cell the capture was
    judged against and the cell the Thief is recorded on cannot drift apart.
    """
    cop_to = state.cop if placed else _apply(cop_move, state.cop, state, board)
    return state.advanced(
        cop=cop_to,
        thief=thief_to,
        barriers=state.barriers | ({placed.cell} if placed and placed.succeeded else set()),
        barriers_placed=state.barriers_placed + (1 if placed and placed.succeeded else 0),
    )


def _resolve(before, after, rules, placed, barriers) -> Outcome | None:
    """Return the verdict for this turn, if any."""
    if placed is not None and placed.outcome is PlacementOutcome.CAPTURE:
        return Outcome(Verdict.CAPTURE, f"barrier at {placed.cell} captured the thief")
    if exit_count(after.thief, after.barriers, rules.board) == 0 and not rules.stay_counts_as_move:
        return Outcome(Verdict.CAPTURE, f"thief sealed in at {after.thief} (M#47)")
    return rules.turn_verdict(before, after)
