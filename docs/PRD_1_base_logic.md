# PRD 1 — Base Logic
### Layer 1 of 7 · milestone M1 · owner [D]

**Covers:** FR-1.1 … FR-1.11 · **Book:** Chapter 3 · **Depends on:** nothing
**Exit criterion:** two agents move legally on a 7×7 grid, a 15th barrier is rejected, and
coordinate overlap triggers capture — **observed**, not merely coded.

---

## 1. Purpose

Establish the physical core of the game with no network, no intelligence and no cryptography.
Everything above this layer assumes these rules are correct; a bug here surfaces later as a
protocol dispute with an opponent, at which point it is expensive to find.

The design decision that shapes this layer: **there is no referee.** Physics is not enforced by a
server but by each peer independently, against a config file both sides load byte-identically
(M#11). This module is therefore written as a pure, deterministic function of `(state, action)`
so that two processes on two machines compute the same result or the disagreement is provable.

---

## 2. Background

The board is a discrete arena, not a continuous simulation: every position, move and blockage is
exactly countable. Enlarging the grid from earlier 5×5 versions to `[board size]` (default 7×7)
is not cosmetic — the Dec-POMDP state space grows as the product of both agents' positions and
every possible barrier layout, which makes exhaustive search computationally infeasible and
forces heuristics rather than enumeration.

---

## 3. Requirements

### 3.1 Board and coordinates

| ID | Requirement |
|---|---|
| 1.1 | Square grid of side `grid_size`, default 7, read from config. **No hardcoded dimension anywhere.** |
| 1.2 | Cells are `(row, col)`. Origin corner and index base are config values (`axis_origin_corner`, `axis_start_index`), defaulting to top-left and 0. |
| 1.3 | `in_bounds(pos)` and `is_passable(pos, barriers)` are the only spatial predicates other modules use. |

The origin and index base are negotiable but **must match** between peers. If one side counts
from 0 and the other from 1, `[3,3]` means different cells and the match silently diverges.

### 3.2 Movement

| ID | Requirement |
|---|---|
| 1.4 | Move set is exactly `{N, S, E, W, STAY}`. **Fixed** by Appendix F — not negotiable. |
| 1.5 | Diagonal movement is prohibited (M#14). No diagonal may exist in the `Direction` enum or the delta table. |
| 1.6 | A move into a barrier or out of bounds is illegal and raises. |
| 1.7 | `get_legal_moves(pos, barriers, board)` returns all passable neighbours plus `STAY`. |

Deleting diagonals from the enum rather than filtering them at validation time is deliberate:
an illegal move cannot be represented, so it cannot be accidentally constructed.

### 3.3 Barriers

| ID | Requirement |
|---|---|
| 1.8 | Only the Cop places barriers, and only on a turn where it **forgoes movement**. |
| 1.9 | Legal target: the Cop's own cell, or one of the **4 orthogonally adjacent** cells. Diagonally adjacent is illegal. |
| 1.10 | Quota `max_barriers`, default 14 (minimum — may be raised by agreement, never lowered). |
| 1.11 | Barriers are **permanent** and impassable to both players. No removal API exists. |
| 1.12 | Every placement is declared truthfully with its exact cell (M#15). Concealment or misreporting is prohibited (M#16). |

### 3.4 Terminal conditions

| ID | Condition | Outcome |
|---|---|---|
| 1.13 | Cop lands on the Thief's cell and issues a Capture Claim | Cop wins |
| 1.14 | Cop places a barrier on the Thief's **current** cell (M#46) | Cop wins |
| 1.15 | Thief has **no** legal move at all — every neighbour blocked by barriers and/or edges (M#47) | Cop wins |
| 1.16 | Thief survives `survival_threshold` (default 35) valid steps | Thief wins |
| 1.17 | Crash, timeout, or cryptographic forgery | Technical loss, 0/0 |

1.15 is easy to miss: a Thief that is walled in has lost even though nobody moved onto it.

### 3.5 Scoring (M#48)

| Outcome | Cop | Thief |
|---|---|---|
| Capture | 20 | 5 |
| Survival | 5 | 10 |
| Tie on cumulative series score | 2 | 2 |
| Technical loss | 0 | 0 |

All five values come from config. Zero numeric literals in `scoring.py`.

The asymmetry is the game's engine: capture is the Cop's maximum but survival is the Thief's, so
neither side's optimal play is the mirror of the other's.

---

## 4. Interface

```python
# core/domain/board.py
Board(grid_size: int)
  .in_bounds(pos: tuple[int, int]) -> bool
  .is_passable(pos, barriers: frozenset) -> bool

# core/domain/movement.py
resolve_move(pos, direction, barriers, board) -> tuple[int, int]   # raises IllegalMoveError
get_legal_moves(pos, barriers, board) -> list[tuple[Direction, tuple[int, int]]]

# core/domain/barriers.py
BarrierManager(max_barriers: int)
  .can_place(target, cop_pos, is_forgoing_move) -> bool
  .place(target) -> PlacementOutcome        # PLACED | CAPTURE | REJECTED
  .remaining -> int

# core/domain/rules.py
terminal_state(state, config) -> Outcome | None

# core/domain/scoring.py
score(outcome, config) -> tuple[int, int]   # (cop_points, thief_points)
```

`GameState` is a frozen dataclass: positions, barriers, step count, barriers placed. Immutability
means a transition returns a new state rather than mutating a shared one, which removes a whole
class of aliasing bug from the turn loop.

---

## 5. Constraints

- Every file ≤150 lines of code. `barriers.py` and `rules.py` are the likeliest to breach; split
  placement validation from quota tracking if needed.
- No imports from `core.infra`, `core.protocol` or `core.runtime`. This layer is pure domain logic
  and must be testable with no network, no clock and no configuration file on disk.
- No randomness. Given the same state and action, the result is identical on both peers — this is
  what makes independent verification possible without a referee.

---

## 6. Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| Delete diagonals from the enum | Keep 8 directions, reject diagonals at validation | An unrepresentable illegal move is safer than one caught by a check somebody might bypass |
| Frozen `GameState`, transitions return new states | Mutable state object | Aliasing bugs across the turn loop and the GUI thread |
| Barrier placement returns an outcome enum | Boolean plus a separate capture check | The barrier-on-thief capture (M#46) is easy to forget when it is a separate call |
| Config-driven scoring | Constants in code | M#12 permits raising minimums by agreement; hardcoding would need a code change per match |

---

## 7. Test scenarios

| # | Scenario | Expected |
|---|---|---|
| T1.1 | Move N/S/E/W from a central cell | New position one cell away |
| T1.2 | `STAY` | Position unchanged, step counter advances |
| T1.3 | Attempt a diagonal | `IllegalMoveError`; no diagonal exists in the enum |
| T1.4 | Move off any edge | `IllegalMoveError` |
| T1.5 | Move into a barrier | `IllegalMoveError` |
| T1.6 | Place barriers 1…14 | All accepted |
| T1.7 | Place barrier 15 | Rejected, quota unchanged |
| T1.8 | Place on a diagonally adjacent cell | Rejected |
| T1.9 | Place while moving | Rejected — placement requires forgoing movement |
| T1.10 | Place on the Thief's current cell | `CAPTURE`, Cop wins |
| T1.11 | Thief enclosed on all four sides | Captured, Cop wins |
| T1.12 | Thief in a board corner with two barriers | Captured (edges count as blocking) |
| T1.13 | Cop moves onto the Thief | Capture on claim |
| T1.14 | Thief survives exactly 35 steps | Thief wins |
| T1.15 | Thief survives 34 steps then captured | Cop wins |
| T1.16 | Score a capture / survival / tie / technical loss | 20-5 / 5-10 / 2-2 / 0-0 |
| T1.17 | Same `(state, action)` on two independent instances | Identical resulting state |
| T1.18 | Board sizes 5, 7 and 10 | Engine works unchanged; no hardcoded 7 |

Coverage target for `core/domain`: **≥85 %**, with every terminal condition exercised.

---

## 8. Traceability

| Rule | Where |
|---|---|
| M#13, M#14 | §3.2 — orthogonal only, diagonals prohibited |
| M#15, M#16 | §3.3 — truthful barrier declaration |
| M#46 | §3.4 T1.10 — barrier on thief = capture |
| M#47 | §3.4 T1.11 — immobilised thief = capture |
| M#48 | §3.5 — scoring table |
| M#11, M#12 | §1, §5 — identical config, minimums never lowered |
| F | grid 7, barriers 14, moves 35, survival 35, scores 20/5/5/10/2/0 |

**TODO tasks:** 1.1.1 – 1.5.5 · **Milestone:** M1
