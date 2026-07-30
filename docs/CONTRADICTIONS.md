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

## C-005 — The scent field is transmitted, not sampled

**Revised 28/07 after reading the reference implementation.** The original entry framed this as a
question of *when the board is sampled*. That framing was wrong: nobody samples anything.

| | |
|---|---|
| **Where** | Chapter 4 — "each agent can sample the board and receive the opponent's scent map" — vs. `Game-P2P-Cop-Chase/src/police_thief/domain/protocol.py` and `peer/turn_sender.py` |
| **What the code actually does** | `TurnMessage` carries a `smell_grid` field. Each peer **sends its own scent field** to the opponent as part of every turn message; the receiver merges it with `SmellField.absorb()`. There is no board to sample and no shared world state — the field is a message payload. |
| **Observed ordering** | `turn_sender.send()` does `deposit(current_position)` → `decay_all()` → `snapshot()` → send. So the transmitted field **includes the sender's current-turn deposit**. |
| **Why uncertainty survives anyway** | The field arrives with the opponent's reveal, telling you where they were when they sent it. Both peers then commit their next move simultaneously. By the time your action lands they have moved again — leaving **≤5 candidate cells** (four orthogonal neighbours plus STAY, minus barriers and edges). |
| **Our choice** | Match the reference: the transmitted field includes our current-turn deposit. Config key `scent_field_includes_current_turn`, default `true`. |
| **Why** | Opponents who started from the reference simulator will behave this way, and matching them removes a whole class of dispute. It also preserves exactly the bounded uncertainty the rest of Chapter 4 and all of Chapter 6 depend on: enough that the belief map is real, little enough that the verbal hint has a job — disambiguating among the ≤5 candidates. That is what makes deception worth anything. |
| **Effect** | Both modes implemented. The residual technique is still worth computing, but note it is far weaker against this implementation than against the book's formula — see C-007. Part of the M#23 exchange. |

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

## C-007 — The reference decay formula contradicts the book

| | |
|---|---|
| **Where** | Chapter 4's formula vs. `Game-P2P-Cop-Chase/src/police_thief/domain/smell.py` |
| **The book** | Multiplicative: `τ(t+1) = max(0, (1−ρ)·τ(t) + Δτ)`. Its own worked example states a centre cell at 0.9 decays to **0.81** after one turn at ρ = 0.10. |
| **The reference code** | Subtractive: `self._values[cell] = max(0.0, round(self._values[cell] - self._decay, 3))`. The same cell decays to **0.80**. Merging is also `max(existing, new)` rather than additive, and the falloff is linear in Chebyshev distance (`intensity − intensity/(half+1) · ring`) rather than the radial values in the book's figure. |
| **How far they diverge** | Book: 0.900 → 0.810 → 0.729 → … → 0.387 at step 9, asymptotic, never zero. Code: 0.900 → 0.800 → 0.700 → … → **0.000** at step 9. Different curve, different trail length, different half-life. |
| **Our choice** | **Implement the book's formula.** Appendix D is explicit that where the repository deviates from the book, the book prevails. |
| **Why this is the single most valuable finding so far** | It is exactly what M#23's mandatory worked numeric example exists to catch. Any opponent who started from the simulator will compute 0.80 where we compute 0.81 — and the pre-series exchange will surface that **before** the first move rather than as an unresolvable dispute afterwards. |
| **Effect** | `decay_model` config key: `multiplicative` (book, our default) and `subtractive` (reference-compatible). We can play either way. The worked example we send is `τ=0.9, ρ=0.10, one turn → 0.81`; if the reply says 0.80 we know immediately which implementation they built on, which is also useful intelligence about the rest of their behaviour. |

---

## C-008 — The scent field is transmitted but never sealed

| | |
|---|---|
| **Where** | Chapter 4's claim vs. `domain/crypto.py` and `domain/protocol.py` |
| **The book** | *"The scent map cannot lie — it is emitted by the very act of movement and cannot be falsified."* |
| **The reference code** | The commitment is `SHA256(canonical_json(payload) | nonce)` over `state | move | verdict`. **`smell_grid` is not in the sealed payload** — it travels in the clear inside `TurnMessage`. A peer could transmit a fabricated field every turn and the end-of-game audit would recompute every commit successfully and report no tampering. |
| **Consequence** | The one channel the whole belief model treats as unfalsifiable is, under this protocol, the *only* channel with no integrity guarantee at all. The verbal hint is sealed via `Intent`; the scent field is not. |
| **Our choice** | **Include a digest of our emitted field in the sealed per-step payload**, and require the same of an opponent by agreement. We do not fabricate fields under any circumstance. |
| **Why** | Sealing it costs one hash and closes the gap. Not sealing it means our own honest play is indistinguishable from a dishonest opponent's, and we would have no way to prove the difference at audit. |
| **Effect** | `seal_scent_digest` config key, default `true`. If an opponent refuses, we still seal ours — it costs nothing and the log then contains evidence of our own integrity even if theirs does not. Raised during negotiation as a proposal, not a demand. |

---

## C-009 — Reference `Board` defaults to 8-direction king movement

| | |
|---|---|
| **Where** | `Game-P2P-Cop-Chase/src/police_thief/domain/board.py` |
| **The problem** | `Board.__init__(self, size, moves=None)` falls back to `tuple(Direction)` — **all eight directions** — when no move set is supplied. The docstring is candid about it: *"the legacy 8-direction king movement is used when no move set is supplied."* The shipped config does pass the correct four, so the simulator itself is compliant. |
| **Why it matters to us** | Diagonal movement is explicitly prohibited (M#14), with technical loss as the sanction. Any team reusing this class and forgetting the `moves` argument silently plays an illegal game — and would only discover it when an opponent rejects a move mid-match. |
| **Our choice** | Our `Direction` enum contains **no diagonals at all**. An illegal move is unrepresentable rather than merely rejected. |
| **Why** | Already recorded as a design decision in `PRD_1_base_logic.md` §6; this entry records the concrete trap it protects against, found in code we were invited to reuse. |
| **Effect** | If we port anything from the reference `board.py`, the diagonal deltas are deleted rather than defaulted away. Test T1.3 asserts no diagonal exists in the enum. |

---

## C-010 — A position tuple has no defined component order

| | |
|---|---|
| **Where** | Appendix F, Table 13 rows 3–6 (p. 135) vs. every coordinate carried on the wire |
| **The problem** | The book negotiates `axis_origin_corner` ("top-left") and `axis_start_index` (0), which fixes *where* cell (0,0) sits and *what* the axes count from. It never states whether a position is `(row, col)` or `(x, y)`. The published defaults hide the gap perfectly: the cop starts at `(0,0)` and the thief at `(3,3)`, and both are order-invariant. The first asymmetric coordinate in the game — `(0,1)` — is the point at which two honest implementations silently disagree, and by then every barrier declaration and capture claim is mirrored. |
| **Why it matters** | Mirrored coordinates are not a gameplay bug, they are an **audit** bug. Our capture claim lands where their log says nothing happened; their barrier declaration lands on a cell we recorded as open. The `log-audit` reports board forgery, and the sanction is disqualification for **both** teams — including the honest one. |
| **Our choice** | `(row, col)`, origin top-left, index from 0: `[r, c]` means row `r` from the top, column `c` from the left. Increasing `c` is **East**; increasing `r` is **South**. Fixed in `PRD_1_base_logic.md` and unrepresentable otherwise, since `Position` is a named 2-tuple, not a bare list. |
| **Why** | It matches `axis_origin_corner = "top-left"`, matches the reference implementation, and matches the way the board is drawn in the book's figures. |
| **Effect** | The negotiation payload carries a **worked example**, not a label: *"we read `[0, 1]` as row 0, column 1 — one cell East of the cop's start; confirm."* One sentence, exchanged before the first move. A disagreement here is the cheapest possible thing to detect and the most expensive to discover late. Added to `PRD_negotiation.md` as a mandatory confirmation item. |

---

## C-011 — `survival_threshold` and `max_moves` can be negotiated apart

| | |
|---|---|
| **Where** | Appendix F, Table 15 rows 3–4 (p. 137) |
| **The problem** | Both default to 35 and both carry status **minimum**, so either may be raised independently by agreement. The book never says they must stay equal. Raising `survival_threshold` to 40 while `max_moves` stays at 35 produces a game that terminates at step 35 with the thief having survived 35 of a required 40 — a state no win condition in Chapter 3.5 covers. Raising `max_moves` alone is merely inert: the thief has already won at 35. |
| **Related gap** | Appendix F fixes `num_games = 6` (Table 18 row 1) but never says how the six sub-games divide between the two roles. We field both roles from two repositories, so an uneven split is expressible — and an opponent strong in one role has an obvious interest in one. |
| **Our choice** | We treat `survival_threshold == max_moves` as an invariant of every configuration we propose or accept, and we insist on a **3–3** role split in the handshake. |
| **Why** | The equal-value case is the only one the win conditions fully define. A team proposing them unequal has either an implementation bug or a trap, and either way we want to know before the match rather than during the audit. On the role split, 3–3 is the symmetric default and is easy to defend; conceding an uneven split gives away an edge for nothing. |
| **Effect** | A validator rejects `survival_threshold != max_moves` before the digest is computed, so an illegal pair can never be signed. The role split is an explicit field in the negotiation payload. See `docs/PARAMETERS.md` §4.2 and §7. |

---

## C-012 — Our LLM provider is not one of the book's four modes

| | |
|---|---|
| **Where** | Appendix F, Table 21 (p. 142) vs. `config/<role>/game.toml` and ADR-003 |
| **The problem** | Table 21 enumerates exactly four LLM modes — `template`, `ollama`, `claude_api`, `claude_cli` — and locates the selector at **`[trash_talk] provider`**. Our config ships `[llm] provider = "groq"`: a fifth provider, under a different section name. |
| **Mitigating** | The same table states the choice is "פרטית לכל עמית, אינה חלק מקובץ התצורה המוסכם ואינה נתונה למשא ומתן" — private to each peer, outside the agreed config, and not negotiated. So this is not a rule breach and cannot disqualify us. |
| **Why it still matters** | It is a gratuitous deviation from a reference table in a project graded partly on conformance, and it puts a network dependency inside the move loop for no competitive gain. Table 21 also notes that in `template` and `ollama` modes the entire six-sub-game series runs at **zero tokens**, and "כל התחרות עוברת לאיכות אלגוריתם התנועה" — the whole contest reduces to movement-algorithm quality, which is where our work actually is. |
| **Our choice** | **Resolved 30 Jul.** The selector moved to `[trash_talk] provider` where the book puts it, and the **committed** value is `template` — the book's own default, zero tokens, no network in the move loop, so a fresh clone always runs. Each machine overrides via `P2P_LLM_PROVIDER` in `.env`: Diana `groq` (development only), Itay `ollama` (graded matches). `[llm]` keeps the per-provider settings, matching PLAN.md §7 and ADR-003. |
| **Why** | Groq was never intended for a graded match — ADR-003 always hosted matches from Itay's machine on `ollama`, which is one of the book's four modes. So the deviation only ever existed in development, and putting `template` in the committed file removes it from the repository entirely. Note this was our own drift: ADR-003 already said `[trash_talk] provider`; the config written in task 1.1.4 said `[llm] provider`. |
| **Effect** | `config/<role>/game.toml` and `.env-example` updated. Two consequences follow, tracked separately: matches now depend on **Itay's** ngrok domain rather than Diana's (TODO 0.2.4, 0.2.6 are blocking for the league, not optional), and a single hosting machine is a single point of failure — Diana's machine must stay match-capable on `template` as a fallback, since a no-show is a technical loss worth 0. |

---

## C-013 — A series of technical losses is arithmetically a tie

| | |
|---|---|
| **Where** | Appendix F Table 17 row 5 vs. Ch. 3.5 |
| **The conflict** | Table 17 defines `tie_score` as *"ניקוד לכל צד כאשר הניקוד המצטבר של כל המשחקונים מול יריבה מסתיים בתיקו"* — points to **each** side when the cumulative total against an opponent ends level. Ch. 3.5 separately fixes a technical loss at 0-0 and explains why: *"ההפסד הטכני מאפס את שני הצדדים כאחד, ובכך מתמרץ את שניהם לשמור על תקינות פרוטוקולרית ולא לנצח בפסק זמן"*. A series in which every sub-game ended in a technical loss satisfies both: the totals are equal, at 0-0. Read literally, both teams collect `tie_score` for a series neither managed to play. |
| **Why it matters** | It inverts the incentive the technical-loss rule exists to create. Two teams that both crash six times out of six would score better than one team that played honestly and lost narrowly. It also makes an empty series — no sub-games at all — worth 2 points a side. |
| **Our choice** | The tie bonus is paid only when **at least one** sub-game produced a real result. A series of nothing but technical losses returns `TECHNICAL_LOSS` at 0-0, and so does an empty series. A series with *some* failures and a genuine level finish still pays the bonus normally. |
| **Why** | It is the reading that cannot be gamed, and it is the one the Ch. 3.5 rationale plainly intends. Where a literal reading and a stated purpose disagree, the purpose is the safer thing to implement — we would rather under-claim two points than have a scoring dispute in the league table. |
| **Effect** | `core/domain/scoring.aggregate()` filters technical losses before deciding the tie; three tests pin the behaviour. Worth raising during negotiation only if a series actually degenerates that way — it costs nothing to agree in advance and is awkward to argue afterwards. |

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
