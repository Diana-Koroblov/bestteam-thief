# PRD — Advanced Strategy
### Phase 8 · owner [D] Cop, [I] Thief · **this is where the league grade is decided**

**Depends on:** Layer 4 (belief and scent) · **Measured by:** the self-play harness, built at the end of Phase 3
**Exit criterion:** the advanced brains beat the Phase 3 baselines in ≥70 % of self-play sub-games.

---

## 1. Purpose

Everything else in this project is a threshold: build it correctly and you pass. This document is
the only one about *winning*, and the league position it decides spans **25 grade points** — last
place 75, first place 100.

The lecturer is explicit that the rulebook is a necessary but not sufficient condition, and that
top marks require interpretation, original thinking and flair. What follows is that attempt.

---

## 2. Background

### 2.1 A pure chase cannot win

Both agents move one cell per turn. On open ground a distance-maximising evader simply holds the
gap, and the 35-step limit expires. **Barriers are not an optimisation for the cop — they are the
only way to win.**

The deeper reason is graph-theoretic. A grid is dense with cycles, and an evader on a cyclic graph
can circle a pursuer indefinitely. Barriers destroy cycles. The cop's real objective is to reduce
the thief's accessible region to something cycle-free, or small enough to sweep.

### 2.2 What "captured" actually requires

Three win conditions, and each demands a **single decisive action** — because every barrier
placement costs the cop its move and therefore gifts the thief a free step. A seal needing two
placements leaks: the thief walks out through the second gap before the cop arrives.

| Condition | Requirement |
|---|---|
| Land on the thief | cop moves onto its cell (swap also counts — C-006c) |
| Barrier on its cell (M#46) | cop orthogonally adjacent, **and the thief does not vacate** (C-006b) |
| No free neighbours (M#47) | thief has **exactly one** free neighbour and the cop can place there (C-006a) |

So the objective is not "shrink the region". It is:

> **Drive the thief's exit count to 1 while standing next to that exit.**

Everything before that is preparation for one move.

### 2.3 Role economics — where the effort belongs

| Role | Best | Worst | Spread |
|---|---|---|---|
| **Cop** | 20 (capture) | 5 (they survive) | **15** |
| **Thief** | 10 (survive) | 5 (caught) | **5** |

Between two competent teams the expected outcome of every sub-game is *the thief survives*. Both
sides bank survival points, the series ties, and each takes 2 — and the diversity reward pays 10
for a **win**, not a draw.

**So the entire differentiator is whether we can capture even once as cop.** The cop carries three
times the spread and is the only role that can break a tie. Depth of search, barrier planning and
herding all belong there first.

This does **not** mean a simple thief. It means that if effort must be rationed, the cop is where
it goes. The thief's tactics below are retained in full; whether each earns its keep is an
empirical question the self-play harness answers (§7), not a matter of prior belief.

---

## 3. Cop strategy

### 3.1 Expectimax over the belief

| ID | Requirement |
|---|---|
| A1.1 | Search depth 2–3 plies over the belief distribution, not a point estimate. |
| A1.2 | Chance nodes weight successor states by posterior mass. |
| A1.3 | Depth is config-driven and must complete well inside the 30 s step deadline. |

Expectimax rather than minimax: we do not know the opponent's policy, and worst-case assumptions
waste the distribution we worked to build.

### 3.2 Connectivity, not mobility — the corrected guard

An earlier draft of this document rejected any barrier that reduced the cop's own mobility. **That
was wrong, and it would have refused the winning move.**

Co-confinement is a *win*: cop and thief sealed together in a small region means the cop sweeps it
and the thief has nowhere to go. The danger is not low mobility — it is **separation**. Walling
yourself into region A while the thief sits in region B makes capture impossible and hands the
thief a free survival.

| ID | Requirement |
|---|---|
| A1.4 | Compute `component(cop)` — the cells reachable from the cop over passable terrain. |
| A1.5 | **Hard penalty** proportional to `P(unreachable) = Σ b(s)` for `s ∉ component(cop)`. A placement that strands believed thief-mass outside our component is rejected. |
| A1.6 | **Reward** shrinking the *shared* component: `−β · |component containing both cop and thief|`. Smaller is better. |

```
  WRONG                          RIGHT
  ┌─────────┐                    ┌─────────┐
  │ T  ▓    │  cop outside,      │ T       │  cop inside,
  │  ▓      │  thief sealed in   │    C    │  region shrinks
  │ ▓    C  │  → survives        │ ▓ ▓ ▓   │  → capture
  └─────────┘                    └─────────┘
```

**The wall goes behind the cop, never between cop and thief.**

### 3.3 Diagonal minimum cuts

Movement is orthogonal-only, so a diagonally-connected chain of barriers cannot be crossed — there
is no legal diagonal step. This makes the diagonal the **cheapest possible cut** on a 4-connected
grid.

| ID | Requirement |
|---|---|
| A1.7 | Score candidate placements by the reduction they cause in the thief's *k*-step reachable set, not by whether they sit between the agents. |
| A1.8 | Prefer placements that extend an existing diagonal chain — each one continues a cut already begun. |
| A1.9 | Prefer placements that **remove cycles**, converting an open region into a dead end. A region the thief can circle is a region it survives in. |
| A1.10 | Reject any placement whose cut cannot be completed in one further placement. An incomplete seal is a wasted barrier (§2.2). |

Four barriers on a diagonal seal a six-cell corner. The full anti-diagonal is 7 barriers and halves
the board; with a quota of 14 that allows halving twice, then sweeping what remains.

### 3.4 The three-phase plan

Barrier timing is not a schedule. It follows from the fact that **exit count is what makes barriers
lethal**, and exit count only falls when the thief is edge- or corner-bound.

| Phase | Barriers | What happens |
|---|---|---|
| **A — Herd** | **0** | Pure movement. The board's own edges do the cornering: a fleeing thief on a finite board runs out of room. Placing here is wasteful — the thief holds the whole board and one barrier removes 1/49 of it, while gifting a free step. |
| **B — Seal** | 4–6 | Once the thief is corner-committed, walk the diagonal and cut **behind yourself**. Distance cost is now near-zero because there is nowhere left to flee. |
| **C — Squeeze** | rest | Advance and place to shrink the shared region until exit count reaches 1, then take the decisive action. |

| ID | Requirement |
|---|---|
| A1.11 | Phase transitions are driven by measured state — thief edge-adjacency, exit count, belief entropy — never by turn number. |
| A1.12 | **Gate on opponent type.** A flee-greedy thief corners itself and needs no early barriers. An *orbiting* thief never corners itself, and against it the chase never converges — barriers must be spent earlier, specifically to cut the cycle it is using. |

### 3.5 Entropy-aware pursuit

| ID | Requirement |
|---|---|
| A1.13 | When the posterior is multimodal, prefer the move that most reduces expected entropy after the next observation. |
| A1.14 | When it is unimodal and confident, revert to direct pursuit. |
| A1.15 | Never place a barrier while belief entropy is high. A barrier placed where the thief probably is not can open a route *for* it. Uncertainty is a reason to look, not to build. |

---

## 4. Thief strategy

Retained in full. Each tactic's value is measured, not assumed (§7).

### 4.1 Escape-route maximisation

| ID | Requirement |
|---|---|
| A2.1 | Evaluate moves by reachable-cell count several steps ahead, not immediate distance. |
| A2.2 | Weight by the posterior over the cop's position, not a point estimate. |
| A2.3 | Penalise regions whose exits the cop could close with its remaining barriers. |
| A2.4 | **Never let exit count reach 1** while the cop is within placement range of that exit — that is the losing state defined in §2.2. |

Distance from the cop is a poor proxy for safety. A far cell with one exit is worse than a near
cell with four. A2.4 is the mirror image of the cop's win condition, and the single most valuable
line in the thief's evaluation.

### 4.2 Scent-aware movement

| ID | Requirement |
|---|---|
| A2.5 | Treat one's own emission as a cost — revisiting cells deepens an already-readable trail. |
| A2.6 | Avoid lingering in a cul-de-sac, where re-emission plateaus at full strength and advertises position indefinitely. |

Standing still is loud: a single pass decays to half in about seven turns, but staying holds
intensity near peak for as long as the agent remains.

### 4.3 Cycle preservation

| ID | Requirement |
|---|---|
| A2.7 | Prefer regions that still contain a cycle. A cycle is what allows indefinite evasion against a single pursuer (§2.1). |
| A2.8 | Treat the cop's remaining barrier count as the measure of how many cycles it can still destroy. |

This is the direct counter to the cop's §3.3. If the cop's objective is cycle elimination, the
thief's is cycle preservation.

### 4.4 False anchor

| ID | Requirement |
|---|---|
| A2.9 | Deliberately build a strong trail in one region, then break away decisively. |
| A2.10 | Trigger only when the estimated payoff exceeds the cost of the turns spent. |
| A2.11 | Measure the effect: survival rate with and without, against the baseline cop **and** against our own advanced cop. |

The scent map cannot lie — but it can be *fed*. A fresh strong trail dominates the pursuer's
posterior for several turns, and those turns can be bought cheaply.

**Open question, to be settled empirically.** The tactic costs turns for a role whose default
outcome against a competent cop is already survival. A2.11 decides whether it is adopted for
graded matches; it is not assumed either way.

---

## 5. Shared behaviour

### 5.1 Unexploitable by default

If we profile the opponent and they profile us, the recursion has no bottom. The way out is to stop
trying to out-guess and instead be unexploitable — then exploitation becomes optional upside rather
than a requirement.

> **Unexploitability is the floor. Exploitation is upside.**

| ID | Requirement |
|---|---|
| A3.1 | **Randomise near-ties.** When two actions score within ε, choose randomly from a seeded generator; the seed is recorded in the match log for reproducibility. A deterministic tie-break is a signature an opponent can learn. |
| A3.2 | **No fixed lie schedule.** Deception is triggered by board state, never by turn number. |
| A3.3 | Avoid rhythmic movement patterns that are readable without any hint at all. |

### 5.2 Opponent profiling — deliberately crude

Six sub-games against one team is roughly **200 observed steps**. Enough to estimate three or four
coarse traits; nowhere near enough to fit anything subtle. Over-fitting to 200 noisy steps is worse
than not profiling, because we would adapt to phantoms.

| Trait | Measured from | Drives |
|---|---|---|
| **Barrier rate** | Declared placements (public under M#15 — free information) | As thief: a cop that never places cannot catch us, so stop taking risks and run the clock |
| **Flee-greediness** | Fraction of thief moves that are exactly distance-maximising | As cop: herd a greedy thief; expectimax against an orbiter |
| **Hint-responsiveness** | Correlation between what we said and how they then moved | Whether the verbal layer is worth any tokens at all against this opponent |
| **Reliability `r`** | Their hints versus their scent trail | How much to weight their claims; when our lies are worth telling |

| ID | Requirement |
|---|---|
| A3.4 | Each trait carries a confidence threshold. Below it, behaviour stays on the unexploitable default. |
| A3.5 | Profile accumulates across the 6 sub-games of a series and **resets between opponents** — teams may change code between matches. |
| A3.6 | At most four traits. Adding a fifth requires evidence it survives the noise. |

### 5.3 Bluff policy — cheap truth

Honesty is not free: the hint describes our own movement, so it genuinely helps the opponent. But
that cost varies, and the variation is the lever.

| ID | Requirement |
|---|---|
| A3.7 | Compute the hint's **information value** — how much it would shift the opponent's belief *beyond what our scent trail already reveals*. |
| A3.8 | **Low information value → tell the truth.** It costs nothing they did not already have, and still builds `r`. |
| A3.9 | **High information value → consider a lie**, weighted by the credibility banked so far. |
| A3.10 | As cop, spend credibility in **Phase A** — a lie about our own position steers a fleeing thief into the corner we have chosen. The lie's job is herding, not confusion. |
| A3.11 | The **brain** sets the truth/lie flag; the language model only writes the sentence. The flag is committed before reveal, so deception cannot be retro-fitted. |
| A3.12 | If hint-responsiveness measures near zero, the opponent is not listening — stop spending tokens on the verbal layer. |

A3.9's interesting case is a *low* `r`: against an opponent who has stopped believing us, honesty
becomes a resource. Rebuild credibility over several turns, then spend it once.

---

## 6. Constraints

- Files ≤150 lines. Brains grow fastest — split search, evaluation and policy from the start.
- Deterministic given a seed. A3.1's randomness uses a seeded generator recorded in the log.
- Movement stays pure Python. No LLM involvement (M#25).
- Search must fit the 30 s step deadline **on the slowest machine we will play from**, with margin.
- All three capture-resolution readings (C-006a/b/c) and the scent sampling mode (C-005) are config
  flags. The strategy must be correct under whichever the opponent agrees to.

---

## 7. How this gets measured

The self-play harness is built at the **end of Phase 3**, not here — strategy is the grade, and
every change from that point on is A/B'd rather than trusted.

| Tier | Cost | What it proves |
|---|---|---|
| Headless self-play — engine + two brains, one process, no MCP, no LLM | free, thousands of games/second | Does the strategy win? |
| Two-process localhost — real MCP + commit-reveal, `template` provider | free | Does the protocol work? |
| Two-machine over ngrok | free, needs both members | Does it survive the real network? |

| ID | Requirement |
|---|---|
| A4.1 | Self-play harness: advanced vs. baseline, ≥100 sub-games, both roles, seeded. |
| A4.2 | Adopt a change only on ≥70 % win rate against the control. |
| A4.3 | Per-turn ASCII board render for watching a single game in the terminal — better than the GUI for debugging, and free. |
| A4.4 | Report: win rate by role · steps to capture · captures per barrier spent · which win condition fired · **cop self-separation rate, which must be 0**. |
| A4.5 | Ablation runs: each thief tactic (4.1–4.4) on and off, to settle §4.4's open question. |

---

## 8. Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| Connectivity constraint | Mobility guard | Mobility rejects co-confinement, which is the winning position. Separation is the real failure |
| Exit-count-1 objective | "Shrink the region" | Shrinking is necessary but not sufficient; only a one-placement seal completes |
| Herd first, barriers later | Barriers from turn 1 | Early barriers cost a free step when the thief has the whole board, and constrain the cop — who must travel — as much as the thief |
| Expectimax over belief | Minimax | We do not know the opponent's policy |
| Expectimax | Monte Carlo tree search | 49 cells at depth 3 is exhaustively searchable; MCTS adds variance and tuning for nothing |
| Heuristic evaluation | Reinforcement learning | Not taught in the course, non-stationary against a learning opponent, and would consume the schedule. See ADR-002 |
| Unexploitable default | Always exploit | Against a strong opponent, aggressive exploitation is itself an exploitable pattern |
| ≤4 profiled traits | Rich opponent model | 200 steps per series cannot support more without fitting noise |
| Retain all thief tactics | Prune to survival-only | The value is measurable (A2.11, A4.5); pruning on prior belief would discard a possibly-strong tactic untested |

---

## 9. Test scenarios

| # | Scenario | Expected |
|---|---|---|
| TA.1 | Advanced cop vs. baseline thief, 100 sub-games | ≥70 % capture rate |
| TA.2 | Advanced thief vs. baseline cop, 100 sub-games | ≥70 % survival rate |
| TA.3 | Advanced vs. advanced | Completes; no timeouts, no illegal moves |
| TA.4 | Placement that would separate cop from believed thief-mass | Rejected by A1.5 |
| TA.5 | Placement that seals cop and thief together in a small region | **Accepted** — this is the winning move |
| TA.6 | Placement whose cut needs two more barriers | Rejected by A1.10 |
| TA.7 | Bimodal posterior | Entropy-reducing move chosen over the argmax chase |
| TA.8 | High belief entropy | No barrier placed (A1.15) |
| TA.9 | Orbiting thief | Cop spends barriers early to cut the cycle |
| TA.10 | Flee-greedy thief | Cop places no barriers before the corner |
| TA.11 | Thief offered a region with one exit and the cop in range | Declines it (A2.4) |
| TA.12 | Two actions within ε | Choice varies across seeds, is fixed within a seed |
| TA.13 | Opponent ignores all hints | Hint-responsiveness → 0; verbal layer disabled |
| TA.14 | Search at configured depth, worst-case board | Completes in ≪30 s |
| TA.15 | Same seed twice | Identical move sequence |
| TA.16 | Import scan of brain modules | No `core.infra.llm` reference |

---

## 10. Traceability

| Rule | Where |
|---|---|
| M#25 | §6 — movement stays algorithmic |
| M#15 | §5.2 — declared barriers are public, and therefore free intelligence |
| M#46, M#47 | §2.2 — win conditions; resolution settled in C-006 |
| F | 14 barriers, 35 steps, scoring 20/5/5/10, tie 2 |
| Ch. 3 | §3.2 — the book's own self-entrapment warning, here corrected to a connectivity constraint |
| Ch. 6 | §2 — heuristics presented as equal-standing with RL |

**TODO tasks:** 8.1.1 – 8.3.x · **Supersedes:** `PRD_3_strategy_baseline.md`
**Related:** `CONTRADICTIONS.md` C-005, C-006 · `PRD_negotiation.md` §3.6
