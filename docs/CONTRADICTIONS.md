# Documented Contradictions and Interpretation Choices

The rulebook grants academic freedom where it contradicts itself, on one condition: *state where you
found the contradiction, what you chose, and why.* It guarantees that a documented, reasoned choice
is not held against the team.

This file is that record. Each entry is also summarised in the README of both repositories.

---

## C-001 — `num_games`: 1 in the sample config, 6 in Appendix F

| | |
|---|---|
| **Where** | Appendix F table 18 vs. the sample `config/game.json` in Appendix B |
| **The conflict** | Appendix F lists `[number of sub-games]` = **6**, status *fixed*. The sample config ships `"num_games": 1`, annotated as a single example sub-game. |
| **Our choice** | **6.** |
| **Why** | The book states plainly that Appendix F is the sole source of truth for numeric values, and that where the book and the sample code repository disagree, the book governs. The sample's `1` is a development convenience for running a single sub-game; the accompanying text itself notes that a full league series requires the full count. |
| **Effect** | `config/<role>/game.json` ships `"num_games": 6`. A negotiated match may raise it by mutual agreement; it is never lowered. |

---

## C-002 — Do docstrings count toward the 150-line limit?

| | |
|---|---|
| **Where** | Excellence guide §3.2 vs. §3.3 |
| **The conflict** | §3.2 caps every source file at 150 lines of code, excluding blank lines and comment lines. §3.3 *mandates* a detailed docstring on every module, class and function. The guide does not say which category a docstring falls into. |
| **Our choice** | **Docstrings are documentation, not code, and are excluded from the count.** |
| **Why** | Counting them would place the two requirements in direct opposition: the better a file is documented, the closer it would sit to the limit, creating an incentive to under-document exactly where the guide demands the opposite. Reading a docstring as a comment resolves the tension in the direction both sections point. |
| **Scope of the exemption** | Only genuine docstrings — the leading string expression of a module, class or function. A triple-quoted string bound to a variable is data and counts as code. Implemented in `core/shared/loc_counter.py` via `ast`, and unit-tested. |
| **Transparency** | `FileReport` carries both `code_lines` (the enforced metric) and `total_lines` (every physical line), so the raw size of a file is always visible and nothing is hidden by the interpretation. |

---

## C-003 — Board size: 7×7 in Appendix F, 10×10 in the belief-map figure

| | |
|---|---|
| **Where** | Appendix F table 13 vs. figure 8 in Chapter 6 |
| **The conflict** | Appendix F sets `[board size]` = 7 (minimum). The Bayesian belief-map illustration in Chapter 6 is drawn on a 10×10 grid and its caption reads "for example 10×10". |
| **Our choice** | **7×7 as the default**, with the board size read from config and never hardcoded. |
| **Why** | The book's own framing rule states that figures and examples illustrate but do not bind, and that Appendix F is the only binding source for quantities. 7 is a *minimum*, so a 10×10 board remains legal if both teams agree — our engine handles any size without a code change. |
| **Effect** | `grid_size` is a config value. Tests parametrise over 5×5, 7×7 and 10×10 to keep the engine size-agnostic. |

---

## C-004 — Line endings and the byte-identical config requirement

| | |
|---|---|
| **Where** | M#11 (shared config must be byte-identical on both sides) vs. cross-platform Git defaults |
| **The problem** | Not a contradiction in the book, but a trap it does not mention. Git on Windows checks files out with CRLF by default; on macOS and Linux with LF. Two teams on different platforms would hold configs that are semantically identical but **byte-different**, so `config_sha256` would not match and the handshake would refuse the match before the first move. |
| **Our choice** | Pin LF for all text files via `.gitattributes` (`* text=auto eol=lf`), published to both repositories. |
| **Why** | M#11 is enforced on bytes, not meaning. The failure would appear only when playing an opponent on a different operating system — the worst possible moment to discover it. |
| **Effect** | `.gitattributes` is in `SHARED_PATHS` and unit-tested. Opponents on any platform hash the same bytes. Also silences Git's CRLF warnings on Windows. |

---

## C-005 — When is the opponent's scent field sampled?

| | |
|---|---|
| **Where** | Chapter 4 — "each agent can sample the board and receive the opponent's scent map" |
| **The problem** | Decay is deterministic and its rate is locked before the series (M#23). If the full field is observed on consecutive turns, this turn's emission is recoverable exactly: `Δτ = τ_t − (1−ρ)·τ_{t−1}`. That residual is a clean 5×5 pattern centred on the emitter, so the belief map collapses to a single cell. Chapter 4's own worked example reasons this way — it computes the expected fresh trace as `(1−ρ)·0.9 ≈ 0.81` and reads cells across the whole board — so global observation is clearly intended. But an entire chapter is then built on probabilistic belief, which would be unnecessary if localisation were exact. |
| **The real hinge** | Not *scope* but *timing*. If the field is sampled **after** the opponent's move, the residual gives its current cell and there is no uncertainty at all. If it reflects the state at the **end of the previous full turn**, we know exactly where it *was*, it has since moved one step, and the belief is spread over ≤5 cells. |
| **Our choice** | **End of the previous full turn.** The residual localises the opponent's *previous* position, not its current one. |
| **Why** | It is the only reading under which the rest of Chapter 4 and the whole of Chapter 6 make sense. It leaves genuine, bounded uncertainty; it makes the verbal hint meaningful, because its job is to disambiguate among the ≤5 candidates; and it therefore makes deception worth something, which the book clearly intends. Claiming instead that the board is only *locally* observable would contradict Chapter 4's explicit example. |
| **Effect** | `scent_sampling` is a config key with two values, `end_of_previous_full_turn` (our default) and `live`. Both are implemented, so an opponent who insists on the other reading can be accommodated without a code change. Added to the M#23 pre-series exchange alongside the worked numeric example. |

---

## C-006 — Capture resolution under simultaneous commit

Three related gaps, all invisible until the moment they decide a match. All three are
implemented as config flags and settled in the pre-match agreement.

### C-006a — Does STAY count as "a legal move" for M#47?

| | |
|---|---|
| **Where** | M#47 vs. the move set in Appendix F |
| **The conflict** | M#47 captures a thief "imprisoned without any legal move". Chapter 3 adds "(all adjacent cells blocked by barriers and/or board edges)". But the move set is fixed as `N, S, E, W, STAY` — so STAY is *always* legal, and under a literal reading M#47 could never fire. |
| **Our choice** | Capture is defined by **adjacency**. All four orthogonal neighbours blocked → captured, regardless of STAY. |
| **Why** | The parenthetical is explicit, and the alternative reading makes a mandatory rule dead on arrival. |
| **Stakes** | A thief at `(6,6)` with barriers at `(5,6)` and `(6,5)`: captured (cop 20 / thief 5) under our reading, survives (cop 5 / thief 10) under the other. A 15-point swing on identical boards. |

### C-006b — M#46 timing: barrier on a cell the thief is leaving

| | |
|---|---|
| **Where** | M#46 — "a barrier placed on the cell where the thief stands **at that moment**" — under a commit-reveal protocol where neither side sees the other's action before choosing |
| **The conflict** | If the cop commits "place at (6,6)" while the thief commits "move to (6,5)", is the thief captured? "At that moment" could mean commit time (capture) or after resolution (no capture). |
| **Our choice** | **Positions are evaluated after both moves are applied.** A barrier placed on a vacated cell does not capture. |
| **Why** | The alternative makes the cop overwhelming — any adjacency becomes a guaranteed capture and the thief can never escape once approached, which cannot be the intended balance. Under our reading M#46 still matters: it catches a thief that chose STAY, which is a real and predictable situation. |

### C-006c — The swap

| | |
|---|---|
| **Where** | Not addressed anywhere in the rulebook |
| **The conflict** | Cop at `(5,6)` moves to `(6,6)`; thief at `(6,6)` moves to `(5,6)`. They pass through each other and neither ends on the other's cell. Capture, or not? |
| **Our choice** | **A swap counts as a capture.** |
| **Why** | Standard in pursuit-evasion games, and the alternative gives the thief a free escape every time the cop closes to adjacency — which would break the endgame entirely. |

---

## Template for future entries

```markdown
## C-00N — short title

| | |
|---|---|
| **Where** | chapter / appendix / file |
| **The conflict** | what the two sources say |
| **Our choice** | what we implemented |
| **Why** | the reasoning |
| **Effect** | what changes in the code or config |
```
