# PRD 3 — Baseline Strategy
### Layer 3 of 7 · milestone M3 · owner [D]

**Covers:** FR-3.1 … FR-3.4 · **Book:** Chapter 6 · **Depends on:** Layers 1–2
**Exit criterion:** given a known target position, the agent computes and walks the shortest legal
path with no manual intervention.

---

## 1. Purpose

Isolate the correctness of the decision core **before** uncertainty is introduced. This layer is
deliberately "blind": full information, no scent, no verbal hints, no deception. If the agent
cannot reliably walk to a cell it can see, no amount of Bayesian machinery above will help.

It also establishes the extension point where all later intelligence plugs in, so Layer 4 and
Phase 8 change one class rather than rewiring the runtime.

---

## 2. Background

The infrastructure below knows how to *move a message*; it does not know *what to decide*. That
separation is the boundary between a generic communication component and a thinking agent, and the
book places it precisely: the strategy module sits inside `PeerRuntime`, **after** the incoming
hint is decoded and **before** the outgoing commit is packed. Everything intelligent about the
agent lives between those two points.

**The movement decision is always algorithmic Python.** Language models hallucinate in Cartesian
space — they confuse directions, miscount distances, and will return an illegal or suicidal move
with complete confidence. The LLM's role is verbal only (Layer 4). The rulebook makes this a strong
recommendation rather than a hard rule (M#25), but the reasoning is sound and we adopt it as
architecture: an architecture test asserts no brain module imports `core.infra.llm`.

---

## 3. Requirements

### 3.1 The extension point

| ID | Requirement |
|---|---|
| 3.1 | `BrainBase` is abstract, with `_pick_move(observation) -> Direction` required. |
| 3.2 | `_decide_move()` is overridable; the Cop uses it to choose between moving and placing a barrier. |
| 3.3 | The concrete brain is selected from the **private** config `[strategy]` section: `police_class` / `thief_class`, written `package.module:Class`. |
| 3.4 | An empty `[strategy]` section falls back to the built-in baseline. |
| 3.5 | A bad class path fails **at startup**, never mid-match. |

Brain selection is private per peer and not negotiated — it is the one place where teams genuinely
differ, and it is where the league grade is decided.

### 3.2 Wiring

| ID | Requirement |
|---|---|
| 3.6 | The brain is invoked between hint-decode and commit-pack, exactly as Chapter 6 specifies. |
| 3.7 | A call-order test asserts that placement. |
| 3.8 | The brain receives an **observation**, never the true world state — even in this layer, where the target happens to be known. |

3.8 matters more than it looks. Passing ground truth "just for now" would make Layer 4 a rewrite
instead of an extension, and would risk shipping an agent that sees what it should not.

### 3.3 Baseline Cop

| ID | Requirement |
|---|---|
| 3.9 | Breadth-first search to the target over passable cells. |
| 3.10 | Respects barriers and bounds; returns the first step of the shortest path. |
| 3.11 | Deterministic: identical board and target produce an identical move. |
| 3.12 | No legal path → move to minimise Manhattan distance instead of raising. |

BFS rather than A*: on 49 cells the heuristic buys nothing measurable, and BFS is easier to prove
correct. Optimising this would be optimising the wrong thing.

### 3.4 Baseline Thief

| ID | Requirement |
|---|---|
| 3.13 | Move to maximise Manhattan distance from the known Cop position. |
| 3.14 | Never voluntarily enter a cell whose only exit is the cell just left. |
| 3.15 | Tie-break deterministically, so tests are reproducible. |

3.14 is a cheap dead-end guard, not real evasion. Genuine escape planning arrives in Phase 8; this
exists so the baseline Thief does not walk into a corner and make Layer 4 look better than it is.

### 3.5 Prohibition

| ID | Requirement |
|---|---|
| 3.16 | No brain module may import `core.infra.llm`. Enforced by an architecture test (M#25). |

---

## 4. Interface

```python
# core/domain/brain_base.py
class BrainBase(ABC):
    def __init__(self, config: Config, role: str) -> None: ...

    @abstractmethod
    def _pick_move(self, observation: Observation) -> Direction: ...

    def _decide_move(self, observation: Observation) -> Decision:
        """Default: move. The Cop overrides to weigh barrier placement."""

    def decide(self, observation: Observation) -> Decision:
        """Called by PeerRuntime. Template method; do not override."""

# core/domain/brain_loader.py
load_brain(class_path: str | None, role: str, config: Config) -> BrainBase
```

`Observation` carries only what this peer may legitimately know: own position, known barriers, step
count, barriers remaining, and — from Layer 4 — the opponent's scent field and latest hint. It
never carries the opponent's true position.

`Decision` is either `Move(direction)` or `PlaceBarrier(cell)`, plus the hint text and intent flag
added in Layer 4.

---

## 5. Constraints

- Files ≤150 lines. Split search from policy when the advanced brains land in Phase 8.
- Brains import from `core.domain` only — never `core.infra`, `core.protocol` or `core.runtime`.
- No randomness in the baseline. Phase 8 may introduce controlled randomness with a seeded
  generator, recorded in the match log for reproducibility.

---

## 6. Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| Template-method `decide()` | Let subclasses override the entry point | Guarantees the legality check runs even if a subclass forgets |
| Config-selected brain class | Import the brain directly | The book defines this exact extension point (Appendix F §5); using it keeps us aligned with the reference implementation |
| BFS | A* with Manhattan heuristic | 49 cells; measurable gain is zero and correctness is harder to argue |
| Baseline ships first | Go straight to expectimax | Layer 3's milestone requires a demonstrable blind policy. A baseline that works is also the control we measure Phase 8 against |
| Architecture test bans LLM imports | Trust the convention | Conventions decay under deadline pressure; a test does not |

---

## 7. Test scenarios

| # | Scenario | Expected |
|---|---|---|
| T3.1 | Cop at (0,0), target (3,3), empty board | 6-step path; first move is N or E |
| T3.2 | Barrier wall between Cop and target with one gap | Path routes through the gap |
| T3.3 | Target fully walled off | No crash; falls back to distance minimisation |
| T3.4 | Same board twice | Identical move both times |
| T3.5 | Thief adjacent to Cop | Moves to increase distance |
| T3.6 | Thief offered a dead-end corridor | Declines it |
| T3.7 | Thief with every neighbour blocked | Returns `STAY`; the engine declares capture (M#47) |
| T3.8 | `[strategy]` empty | Baseline brain loads |
| T3.9 | `[strategy]` names a valid class | That class loads |
| T3.10 | `[strategy]` names a missing class | Fails at startup with a readable error |
| T3.11 | Call order inside `PeerRuntime` | Brain runs after hint-decode, before commit-pack |
| T3.12 | Brain receives an `Observation` | No field carries the opponent's true position |
| T3.13 | Import scan of `police/` and `thief/` | No reference to `core.infra.llm` |

---

## 8. Traceability

| Rule | Where |
|---|---|
| M#25 | §3.5 — LLM never decides the move, test-enforced |
| Ch. 6 | §3.2 — insertion point inside `PeerRuntime` |
| Appendix F §5 | §3.1 — `police_class` / `thief_class` keys |
| Ch. 10 milestone 3 | Exit criterion — shortest path, unaided |

**TODO tasks:** 3.1.1 – 3.4.1 · **Milestone:** M3 · **Superseded by:** `PRD_strategy_advanced.md`
