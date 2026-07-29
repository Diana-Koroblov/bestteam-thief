# PRD 4 — Scent and Belief
### Layer 4 of 7 · milestone M4 · owner [D] + [I] · ⚠️ **highest risk layer**

**Covers:** FR-4.1 … FR-4.10 · **Book:** Chapters 4 and 6 · **Depends on:** Layers 1–3
**Exit criterion:** free-text hints drive inference; the scent map updates and decays each step;
the verbal layer emits a truthful or deceptive hint of at most 15 words.

Most of the project's schedule slack is allocated here. This is where uncertainty — the actual
subject of the project — is born.

---

## 1. Purpose

Turn a game of perfect information into a game of inference. Two mechanisms arrive together, and
their interaction is the point:

1. **Scent** — an involuntary, unfalsifiable trace each agent leaves by existing.
2. **Language** — a voluntary, entirely falsifiable statement each agent makes about itself.

One cannot lie; the other can. Cross-referencing them is how an agent catches a liar, and
knowing this is possible is what makes lying a real decision rather than a free action.

---

## 2. Background

### 2.1 Stigmergy

Ants coordinate with no leader, no language and no shared memory: each leaves pheromone, each
reacts to it, and the environment itself becomes the shared blackboard. This is *stigmergy* —
indirect coordination through environmental modification — and it underpins ant-colony
optimisation. Here it attacks partial observability: an agent that cannot see its opponent can
still read where the opponent has recently been.

Decay is as important as deposition. Without it, trails accumulate forever, every cell eventually
looks visited, and the signal dies. The decay rate sets how far into the past an agent can see.

### 2.2 Belief as a probability distribution

Each side maintains a distribution over all cells representing where the hidden opponent probably
is. Two evidence sources update it — the scent field (reliable) and the verbal hint (unreliable,
weighted by a learned coefficient). This is textbook Bayesian filtering over a small discrete
state space, which on 49 cells is computationally free.

---

## 3. Requirements

### 3.1 Emission

| ID | Requirement |
|---|---|
| 4.1 | Field of side `pheromone_grid_size` (5, **fixed**) centred on the agent. |
| 4.2 | Centre intensity `pheromone_center_intensity` (0.9, **fixed**). |
| 4.3 | Radial falloff. Reference values from the book's figure: 0.90 centre; 0.62 orthogonal; 0.42 diagonal; 0.20 / 0.14 / 0.04 at the rim. |
| 4.4 | **Both** agents emit. Each reads only the *opponent's* field, never its own. |

Radial rather than single-cell deposition is a robustness choice: with a point deposit, one
missed reading erases the signal; with a hill, the neighbours still indicate direction.

### 3.2 Decay

| ID | Requirement |
|---|---|
| 4.5 | At the end of each **full** turn — after both agents have moved — apply: |

```
τ_ij(t+1) = max(0, (1 − ρ) · τ_ij(t) + Δτ_ij)
```

| ID | Requirement |
|---|---|
| 4.6 | ρ = `pheromone_decay` = 0.10, **fixed**. |
| 4.7 | Truncated at zero — intensity is never negative. |
| 4.8 | A single deposit crosses half its peak around turn 7, giving roughly a six-to-seven turn readable trail. |

The formula holds two opposing forces: `(1−ρ)·τ` is forgetting, `Δτ` is recording. Their balance
decides how deep into the past each agent can see.

**Cryptographic lock (M#23).** Before the series opens, both teams exchange the emission and decay
model *including a concrete worked example* — e.g. a centre cell at τ=0.9 decays to 0.81 after one
turn — and hash the agreement. Any later divergence is then provable rather than arguable. The book
explicitly permits one team to supply the other with the scent code itself; offering to do so is
worth considering, since it guarantees parity and lets us set the reference implementation.

### 3.3 Belief

| ID | Requirement |
|---|---|
| 4.9 | Full posterior over all `grid_size²` cells. Sums to 1.0 within float tolerance after every update. |
| 4.10 | Uniform initialisation: 1/49 per cell at step 0. |
| 4.11 | **Prediction:** the opponent moved one orthogonal step or stayed. Mass spreads only to legal neighbours. |
| 4.12 | **Update from scent:** cells consistent with the observed field gain mass. |
| 4.13 | **Update from hint:** scaled by the per-opponent reliability coefficient. |
| 4.14 | **Mask:** barriers and own cell hold exactly 0. |
| 4.15 | **Normalise** after every update. |

### 3.4 Reliability coefficient — original extension

| ID | Requirement |
|---|---|
| 4.16 | Maintain `r ∈ [0,1]` per opponent: how well their statements have matched their scent trail. |
| 4.17 | After each hint, compare the claim against the observed field and adjust `r`. |
| 4.18 | `r` weights the hint likelihood in 4.13. Against a consistent liar `r → 0`; against a truthful opponent `r → 1`. |
| 4.19 | Record `r` per turn in the match log for the README plot. |

This is our own extension beyond the specification. It converts "the opponent lied" from an
anecdote into a measured, plottable quantity — and it makes the agent's credulity adaptive rather
than fixed. Worked example from Chapter 4: the Thief announces "moving north" while its scent mass
sits at τ=0.81 in the south-east and the north reads 0.00. The expected trace had it moved north
would be ≈0.81. The gap is total, so the claim is rejected, `r` falls, and pursuit redirects toward
the real source. Deception, caught by the environment, becomes self-incriminating.

### 3.5 Verbal layer

| ID | Requirement |
|---|---|
| 4.20 | Provider selected from the **private** `[trash_talk] provider`: `template` \| `ollama` \| `groq`. |
| 4.21 | `template` — pre-written sentences chosen in Python. Zero tokens, no network. Default and fallback. |
| 4.22 | `ollama` — local model at `localhost:11434`. Zero API tokens. |
| 4.23 | `groq` — cloud, routed through the Gatekeeper, metered against `token_budget_per_series`. |
| 4.24 | **Automatic fallback to `template`** on any provider error or timeout. A dead provider must never cost a match. |
| 4.25 | `every_n_steps` throttle — the model speaks every 2–3 turns, not every turn. |
| 4.26 | Hint capped at `hint_max_words` (15) for **every** provider, including in the LLM system prompt. |
| 4.27 | Communication is free natural language (M#26). |
| 4.28 | Outgoing text is scanned for bare numeric coordinates and regenerated if found (M#27). |
| 4.29 | Optional landmark flavour from `map_area`; empty string gives generic landmarks. |
| 4.30 | The `Intent` flag (`truth` \| `lie`) is chosen by the **brain**, not the model, and committed with the move. |

4.30 is the crux. The model writes the sentence; the algorithm decides whether that sentence is
true. Deception stays a strategic choice, cryptographically bound at commit time so it cannot be
retro-fitted at reveal.

### 3.6 Inbound parsing

| ID | Requirement |
|---|---|
| 4.31 | Parse free text into a directional intent plus a confidence score. |
| 4.32 | Low confidence defers to the belief map alone rather than guessing. |
| 4.33 | Classify bluffs by comparing the claim against the scent field; feed the result to 4.17. |

---

## 4. Interface

```python
# core/domain/scent.py
ScentField(grid_size: int, config: Config)
  .emit(pos: tuple[int, int]) -> None
  .decay() -> None                       # end of full turn only
  .intensity(pos) -> float
  .model_digest() -> str                 # for the M#23 pre-series lock

# core/domain/belief.py
BeliefMap(grid_size: int)
  .predict(barriers) -> None
  .update_from_scent(field: ScentField) -> None
  .update_from_hint(intent: ParsedHint, reliability: float) -> None
  .argmax() -> tuple[int, int]
  .entropy() -> float
  .as_matrix() -> list[list[float]]      # for the GUI heatmap

# core/domain/reliability.py
ReliabilityTracker(initial: float = 0.5)
  .observe(claim: ParsedHint, field: ScentField) -> None
  .value -> float
  .history -> list[float]

# core/infra/llm/base.py
class TextProvider(Protocol):
    def generate(self, prompt: str, max_words: int) -> str: ...
```

---

## 5. Constraints

- Files ≤150 lines. `belief.py` and `scent.py` are the most likely to breach — split emission from
  decay, and prediction from update, at the first sign.
- No test may contact a live LLM. Providers are mocked.
- The belief update must run well inside the 30-second step deadline; on 49 cells this is
  microseconds, but the constraint is recorded because a future larger board must not break it.

---

## 6. Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| Full posterior | Most-likely-cell estimate | Discards distribution shape, which is what enables expectimax, entropy-driven search and bluff detection |
| Full posterior | Particle filter | Overkill on 49 cells; adds sampling noise for no gain |
| Reliability coefficient | Fixed hint weight | A fixed weight cannot adapt to an opponent who always lies — and adaptation is exactly what the "Adaptation" success metric measures |
| Brain chooses `Intent` | LLM chooses whether to lie | Deception is strategy, not prose. It must also be committed before reveal, which the model cannot guarantee |
| Automatic `template` fallback | Fail the turn on provider error | A dead provider would forfeit a match over a cosmetic feature |
| Ollama primary for graded matches | Cloud model | Computational fairness is scored; zero tokens is an advantage, not a confession |

---

## 7. Test scenarios

| # | Scenario | Expected |
|---|---|---|
| T4.1 | Emit at a central cell | 5×5 field matching the book's figure to 2 dp |
| T4.2 | Emit near an edge | Field clipped, no out-of-bounds write |
| T4.3 | One deposit, then decay for 10 turns | Follows `0.9·(0.9)^t`; half-peak near turn 7 |
| T4.4 | Agent stays 8 turns then leaves | Plateau then decay, matching the book's second curve |
| T4.5 | Decay applied twice in one turn | Test fails — decay is once per **full** turn |
| T4.6 | Read own scent field | Not possible via the public API |
| T4.7 | Belief after any update | Sums to 1.0 ± 1e-9 |
| T4.8 | Belief on a barrier cell | Exactly 0 |
| T4.9 | Hint contradicted by the scent field | Mass moves *away* from the claim |
| T4.10 | Consistently lying opponent over 20 turns | `r` converges toward 0 |
| T4.11 | Consistently truthful opponent | `r` converges toward 1 |
| T4.12 | 20-word hint generated | Truncated or regenerated to ≤15 |
| T4.13 | Hint containing `(3,4)` | Rejected and regenerated (M#27) |
| T4.14 | Provider raises | Silent fallback to `template`; turn completes |
| T4.15 | Provider exceeds `step_deadline_seconds` | Fallback to `template`; no technical loss |
| T4.16 | `every_n_steps = 3` | Model invoked on turns 1, 4, 7 |
| T4.17 | Scent model digest, two peers, same config | Identical |
| T4.18 | Worked example from Ch. 4 (τ=0.9, one turn, ρ=0.10) | 0.81 |

---

## 8. Traceability

| Rule | Where |
|---|---|
| M#23 | §3.2 — pre-series cryptographic lock of the scent model |
| M#25 | §3.5 — movement stays algorithmic; the model writes prose only |
| M#26 | §3.5 — free natural language |
| M#27 | §3.5 — numeric position protocols prohibited |
| F | field 5×5, centre 0.9, ρ 0.10, hint 15 words, token budget 200 000 |

**TODO tasks:** 4.1.1 – 4.6.4 · **Milestone:** M4
