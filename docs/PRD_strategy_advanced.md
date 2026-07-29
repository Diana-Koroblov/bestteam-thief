# PRD — Advanced Strategy
### Phase 8 · owner [D] Cop, [I] Thief · **this is where the league grade is decided**

**Depends on:** Layer 4 (belief and scent) · **Runs parallel to:** Layers 5–7
**Exit criterion:** the advanced brains beat the Phase 3 baselines in ≥70 % of self-play sub-games.

---

## 1. Purpose

Everything else in this project is a threshold: build it correctly and you pass. This document is
the only one about *winning*, and the league position it decides spans **25 grade points** — last
place 75, first place 100.

The lecturer is explicit that the rulebook is a necessary but not sufficient condition, and that
top marks require interpretation, original thinking and flair. The extensions below are that
attempt.

---

## 2. Background

### 2.1 What the baseline leaves on the table

The Phase 3 baseline minimises Manhattan distance to the belief argmax. Against a distance-
maximising evader on an open board this is close to futile: a tail chase cancels out almost
exactly, and the gap only closes where the evader is forced to turn — at a wall, or against a
barrier. Chasing the single most likely cell also discards the shape of the distribution, which is
where the information actually lives.

### 2.2 The asymmetry

Scoring is deliberately lopsided: capture 20/5, survival 5/10. The Cop's maximum comes from
catching; the Thief's from patience. Neither side's optimal play mirrors the other's, and a team
strong in only one role leaks points every time it draws the other.

### 2.3 The barrier is the Cop's real weapon

Fourteen barriers on 49 cells is roughly 29 % of the board. Enough to build a genuine cage — and
enough to wall yourself in. The book warns explicitly that a greedy placement can trap the Cop
behind its own wall or open a new escape route for the Thief. Most teams will discover this the
expensive way.

---

## 3. Cop strategy

### 3.1 Expectimax over the belief map

| ID | Requirement |
|---|---|
| A1.1 | Search depth 2–3 plies over the belief distribution, not a point estimate. |
| A1.2 | Chance nodes weight successor states by posterior mass. |
| A1.3 | Evaluation combines expected distance-to-capture, Thief mobility, and barriers remaining. |
| A1.4 | Depth is config-driven and must complete well inside the 30 s step deadline. |

Expectimax rather than minimax: we do not know the Thief's policy, and assuming worst-case play
against an unknown opponent is needlessly pessimistic on a board this size.

### 3.2 Barrier-trap planning

| ID | Requirement |
|---|---|
| A1.5 | Score each candidate placement by the reduction it causes in the Thief's 3-step reachable-cell count. |
| A1.6 | **Self-entrapment guard:** reject any placement that reduces the Cop's own mobility below a threshold. |
| A1.7 | Budget pacing — never spend so freely that the endgame squeeze has no barriers left. |
| A1.8 | Prefer placements that convert an open region into a pocket with a single exit the Cop can cover. |

A1.5 is the substantive change from greedy blocking: the metric is not "does this barrier sit
between us" but "how much smaller does the Thief's world become".

### 3.3 Entropy-aware pursuit

| ID | Requirement |
|---|---|
| A1.9 | When the posterior is multimodal, prefer the move that most reduces expected entropy after the next observation. |
| A1.10 | When it is unimodal and confident, revert to direct pursuit. |

Chasing the argmax of a two-peaked distribution can mean running to a point between two
possibilities and committing to neither. Sometimes the better move is the one that will *tell you
which peak is real*.

---

## 4. Thief strategy

### 4.1 Escape-route maximisation

| ID | Requirement |
|---|---|
| A2.1 | Evaluate moves by reachable-cell count several steps ahead, not immediate distance. |
| A2.2 | Weight by the posterior over the Cop's position, not a point estimate. |
| A2.3 | Penalise regions whose exits the Cop could close with its remaining barriers. |

Distance from the Cop is a poor proxy for safety. A cell far away with one exit is worse than a
nearer cell with four.

### 4.2 Scent-aware movement

| ID | Requirement |
|---|---|
| A2.4 | Treat one's own emission as a cost: revisiting cells deepens an already-readable trail. |
| A2.5 | Avoid lingering in a cul-de-sac, where re-emission plateaus at full strength and advertises position. |

Standing still is loud. Re-emission holds intensity near peak for as long as the agent stays,
whereas a single pass decays to half within about seven turns.

### 4.3 False-anchor tactic — original extension

| ID | Requirement |
|---|---|
| A2.6 | Deliberately build a strong trail in one region, then break away decisively. |
| A2.7 | Trigger only when the estimated payoff exceeds the cost of the turns spent. |
| A2.8 | Measure the effect: survival rate with and without, against the baseline Cop. |

The scent map cannot lie — but it can be *fed*. An agent that understands decay knows a fresh
strong trail dominates the pursuer's posterior for several turns, and that those turns can be
bought cheaply. This is deception through the one channel the opponent believes is honest, and it
is entirely within the rules.

---

## 5. Shared

### 5.1 Reliability-driven bluffing

| ID | Requirement |
|---|---|
| A3.1 | Use the tracked reliability coefficient (PRD 4 §3.4) to decide whether lying is worth it. |
| A3.2 | High reliability — the opponent trusts us — makes a lie valuable. |
| A3.3 | Low reliability — they discount everything — makes truth cheap and occasionally useful for rebuilding credibility. |
| A3.4 | The brain sets the `Intent` flag; the language model only writes the sentence. |

A3.3 is the interesting case: against an opponent who has stopped believing us, honesty becomes a
resource. Rebuild trust over several turns, then spend it once.

### 5.2 Benchmarking

| ID | Requirement |
|---|---|
| A3.5 | Self-play harness: advanced vs. baseline, ≥100 sub-games, both roles. |
| A3.6 | Adopt only on ≥70 % win rate. |
| A3.7 | Seeded randomness; the seed is recorded so any result is reproducible. |
| A3.8 | Results feed the sensitivity study and the README. |

---

## 6. Constraints

- Files ≤150 lines. Brains grow fastest — split search, evaluation and policy from the start.
- Deterministic given a seed. Non-reproducible strategy cannot be unit-tested, and coverage ≥85 %
  is mandatory.
- The movement decision stays pure Python. No LLM involvement (M#25).
- Search must fit the 30 s step deadline **on the slowest machine we will play from**, with margin.

---

## 7. Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| Expectimax over belief | Minimax | We do not know the opponent's policy; worst-case assumptions waste the distribution we worked to build |
| Expectimax | Monte Carlo tree search | 49 cells and depth 3 is exhaustively searchable; MCTS adds variance and tuning for no gain |
| Heuristic evaluation | Reinforcement learning | Not taught in the course, non-stationary against a learning opponent, and would consume the remaining schedule. See ADR-002 |
| Reachable-cell reduction | Distance-based barrier scoring | Distance ignores topology: a barrier that halves the Thief's world may not sit between the agents at all |
| False-anchor as an opt-in tactic | Always laying false trails | Costs turns; only worth it when the payoff is estimated to exceed the cost |
| 70 % adoption threshold | Ship whatever is newest | Without a control, "improvements" are just changes |

---

## 8. Test scenarios

| # | Scenario | Expected |
|---|---|---|
| TA.1 | Advanced Cop vs. baseline Thief, 100 sub-games | ≥70 % capture rate |
| TA.2 | Advanced Thief vs. baseline Cop, 100 sub-games | ≥70 % survival rate |
| TA.3 | Advanced vs. advanced | Completes; no timeouts, no illegal moves |
| TA.4 | Barrier placement that would trap the Cop | Rejected by the self-entrapment guard |
| TA.5 | Barrier budget across 35 steps | Barriers remain for the endgame |
| TA.6 | Bimodal posterior | Entropy-reducing move chosen over the argmax chase |
| TA.7 | Unimodal confident posterior | Direct pursuit chosen |
| TA.8 | Thief offered a high-count / low-exit region | Prefers the region with more exits |
| TA.9 | False-anchor triggered | Survival rate measurably higher than without |
| TA.10 | Search at configured depth, worst-case board | Completes in ≪30 s |
| TA.11 | Same seed twice | Identical move sequence |
| TA.12 | Import scan of brain modules | No `core.infra.llm` reference |

---

## 9. Traceability

| Rule | Where |
|---|---|
| M#25 | §6 — movement stays algorithmic |
| M#15, M#16 | Barrier placements declared truthfully; the tactic is topological, never concealed |
| F | 14 barriers, 35 steps, scoring 20/5/5/10 |
| Ch. 3 | §2.3 — the book's own self-entrapment warning |
| Ch. 6 | §3 — heuristics presented as equal-standing with RL |

**TODO tasks:** 8.1.1 – 8.3.3 · **Supersedes:** `PRD_3_strategy_baseline.md`
