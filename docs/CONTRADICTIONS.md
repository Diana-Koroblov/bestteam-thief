# Contradictions, Gaps and Interpretation Choices

The rulebook grants academic freedom where it contradicts itself, on one condition: *state where
you found the contradiction, what you chose, and why.* A documented, reasoned choice is not held
against the team.

This file is that record. Each entry is also summarised in the README of both repositories.

---

## 0. The test every entry must now pass

**Appendix F is the single source of truth for every quantitative value in this project.** It says
so in its own opening line, and its status column defines exactly three regimes:

| Status | Hebrew | What it means | Can there be a contradiction? |
|---|---|---|---|
| **Fixed** | fixed | The value cannot change at all. Deviating disqualifies the team. | **No.** The value *is* the value. Anything printed elsewhere that disagrees is an error in that other place, not a conflict. |
| **Minimum** | minimum | May be raised by mutual agreement, never lowered. | **No.** A different figure elsewhere is a legal raised value, not a conflict. |
| **Negotiable** | negotiable | "determined entirely in negotiation between the parties; the value shown is an example only" — decided entirely in negotiation; the printed value is **an example only**. | **No.** Choosing a value is negotiation, not resolving a contradiction. |

So a genuine contradiction can only exist where Appendix F is **silent** — that is, about *mechanisms
and timing*, never about numbers.

**This document was re-audited on 31/07 against that test, and several entries failed it.** They
were reclassified rather than deleted, because each still describes something real that has to be
watched for — just not a contradiction in the rulebook.

**What changed:** C-001, C-007 and C-009 are no longer contradictions but reference-implementation
defects. C-006a is a clarification the rulebook itself supplies. Three entries — C-003, the
`survival_threshold` half of C-011, and C-012 — **left this document entirely**; see the appendix.

### Index by category

| Category | Entries | What to do about them |
|---|---|---|
| **A. Genuine gaps** — the rulebook does not define the behaviour anywhere | C-005, C-006b, C-006c, C-010, C-011, C-013 | **Must be settled in the pre-match agreement.** Every one appears in `PRD_negotiation.md`. |
| **B. Resolved by the rulebook** — looked ambiguous, settled on a closer reading | C-006a | Implemented as read. Flag kept only because an opponent may arrive with the other reading. |
| **C. Reference-implementation defects** — the book is unambiguous, the reference diverges | C-001, C-007, C-009, C-008 | **Watch items.** Most opponents will build on the reference and inherit these. Detect at the handshake. |
| **D. Gaps outside the game rules** — engineering and process | C-002, C-004 | Our own decisions, recorded for the reviewer. |

---

# Category A — Genuine gaps in the rulebook

Appendix F is silent on all of these because none of them is a quantity. Each **must** be agreed
before the first move, because two honest implementations will otherwise diverge mid-match and the
log audit will blame both teams.

## C-005 — The scent field is transmitted, not sampled

| | |
|---|---|
| **Where** | Ch. 4 describes a decaying scent map; nothing states *how* a peer obtains the opponent's field |
| **The gap** | There is no shared board. Each peer sends its own emitted field with its turn message, so what you receive is what the opponent chose to send. The book never says whether that field includes the sender's current-turn deposit or only the state before it. |
| **Our choice** | The transmitted field **includes** the current turn's deposit. |
| **Why** | It matches the reference implementation, so it is what most opponents will send. Uncertainty survives regardless: both peers move again afterwards, leaving ≥5 candidate cells. |
| **Effect** | `pheromones.field_includes_current_turn = true`. Negotiation item **N13**. |

## C-006b — M#46 timing: a barrier on a cell the thief is leaving

| | |
|---|---|
| **Where** | M#46 — a barrier on the cell where the thief stands *"at that moment"* — under commit-reveal, where neither side sees the other's action before choosing |
| **The gap** | Cop commits "place at (6,6)" while the thief commits "move to (6,5)". Is the thief captured? *"At that moment"* could mean commit time or after resolution. Appendix F has no parameter for this, so nothing there settles it. |
| **Our choice** | **Positions are evaluated after both actions apply.** A barrier on a vacated cell does not capture. |
| **Why** | The alternative makes the cop overwhelming: any adjacency becomes a guaranteed capture and the thief can never escape once approached, which cannot be the intended balance. M#46 still matters under our reading — it catches a thief that chose STAY, which is common and predictable. |
| **Effect** | `capture.resolution = "after_moves"`. Negotiation item **N15**. ⚠️ Integration note for Phase 3: `BarrierManager.place()` compares against whatever `thief_pos` the caller passes, so the turn loop must pass the **post-move** position under this setting. |

## C-006c — The swap

| | |
|---|---|
| **Where** | Not addressed anywhere in the rulebook |
| **The gap** | Cop at `(5,6)` moves to `(6,6)`; thief at `(6,6)` moves to `(5,6)`. They pass through each other and neither ends on the other's cell. Capture, or not? |
| **Our choice** | **A swap counts as a capture.** |
| **Why** | Standard in pursuit-evasion games, and the alternative gives the thief a free escape every time the cop closes to adjacency, which would break the endgame entirely. |
| **Effect** | `capture.swap_is_capture = true`. Negotiation item **N16**. |

## C-010 — A position tuple has no defined component order

| | |
|---|---|
| **Where** | Appendix F Table 13 rows 3–6 negotiate *where* `(0,0)* sits and *what* the axes count from — but never whether a position is `(row, col)` or `(x, y)` |
| **The gap** | The published defaults hide it perfectly: cop at `(0,0)`, thief at `(3,3)`, both order-invariant. The first asymmetric coordinate — `(0,1)` — is where two honest implementations silently disagree, and by then every barrier declaration and capture claim is mirrored. |
| **Why it is not an Appendix F question** | Component order is not a value, so no status applies to it. It is a pure mechanism gap, which is exactly the kind Appendix F cannot cover. |
| **Our choice** | `(row, col)`, origin top-left, index from 0. Increasing `col` is **East**; increasing `row` is **South**. `Position` is a 2-tuple used consistently throughout `core/domain`. |
| **Effect** | The negotiation payload carries a **worked example**, not a label: *"we read `[0, 1]` as row 0, column 1 — one cell East of the cop's start; confirm."* Verified visually by `scripts/demo_m1.py`. **Needs a negotiation item — see N18.** |

## C-011 — How the sub-games divide between the two roles

| | |
|---|---|
| **Where** | Appendix F Table 18 fixes `[number of sub-games]` = 6, status **fixed**. Nothing anywhere says who plays cop in which of them. |
| **The gap** | We field both roles from two repositories, so an uneven split is expressible. An opponent strong in one role has an obvious interest in one. |
| **Our choice** | **3–3**, stated explicitly in the handshake. |
| **Why** | It is the symmetric default and trivially defensible. Conceding an uneven split gives away an edge for nothing. |
| **Effect** | Explicit field in the negotiation payload. Negotiation item **N17**. |

## C-013 — A series of technical losses is arithmetically a tie

| | |
|---|---|
| **Where** | Appendix F Table 17 row 5 vs. Ch. 3.5 |
| **The gap** | `tie_score` is **fixed** at 2, so the *value* is not in question — but *when a tie is declared* is not a quantity and Appendix F does not define it. Table 17 pays each side `tie_score` when the cumulative total ends level. A series where every sub-game ended in a technical loss is level, at 0-0. Read literally, both teams collect the bonus for a series neither played. |
| **Why it matters** | It inverts the incentive Ch. 3.5 exists to create: *"a technical loss zeroes both sides alike, thereby incentivising both to maintain protocol correctness rather than to win on a timeout"*. Two teams that crashed six times each would outscore a team that played honestly and lost narrowly. |
| **Our choice** | The tie bonus is paid only when **at least one** sub-game produced a real result. An all-technical-loss series, and an empty series, return 0-0. |
| **Why** | It is the reading that cannot be gamed, and the one the Ch. 3.5 rationale plainly intends. Where a literal reading and a stated purpose disagree, implement the purpose. |
| **Effect** | `core/domain/scoring.aggregate()` filters technical losses before deciding the tie; three tests pin it. **Needs a negotiation item — see N19.** |

---

# Category B — Resolved by the rulebook itself

## C-006a — Does STAY count as "a legal move" for M#47?

| | |
|---|---|
| **Where** | M#47 vs. the fixed move set in Appendix F Table 15 |
| **The apparent conflict** | M#47 captures a thief "imprisoned without any legal move". The move set is **fixed** as `N, S, E, W, STAY`, so STAY is *always* legal — under a literal reading M#47 could never fire. |
| **Resolved by** | The barrier law on **p. 21** states the definition in the rule text itself: *"Thief sealed in with no legal move at all (**all adjacent cells blocked by barriers and/or the board edge**) is likewise considered captured"*. The parenthetical **defines** "without any legal move" as adjacency, and names barriers *and board edges* as equivalent blockers. |
| **Our choice** | Capture by **adjacency**: all four orthogonal neighbours blocked, regardless of STAY. Board edges count. |
| **Status** | This is a clarification, not a contradiction — the rulebook answers it. The config flag `capture.stay_counts_as_move = false` is kept anyway, because an opponent who read only M#47 may arrive with the other reading, and the point of the pre-match agreement is that we never have to argue about it. |
| **Stakes** | Thief at `(6,6)` with barriers at `(5,6)` and `(6,5)`: captured (20/5) under the correct reading, survives (5/10) under the other. A 15-point swing on identical boards. Negotiation item **N14**. |

---

# Category C — Reference-implementation defects

The book is unambiguous in all four. The reference repository diverges. These are **watch items**:
most opponents will build on that repository and inherit the divergence, so each is something to
detect during the handshake rather than discover during the audit.

## C-001 — The reference config ships `num_games: 1`

| | |
|---|---|
| **Appendix F says** | Table 18 row 1: `[number of sub-games]` = **6**, status **fixed (fixed)**. Not raisable, not negotiable. |
| **The reference ships** | `"num_games": 1` in `config/police/game.json` and in the sample run. |
| **Reclassified 31/07** | **Not a contradiction.** A fixed value admits no conflict — the reference is simply non-conformant, and a team that plays a 1-sub-game series has deviated from a fixed value. |
| **Our value** | 6, as Appendix F requires. |
| **Why it stays in this document** | An opponent who copied the reference config will propose `num_games: 1`. Accepting it means **both** teams deviate from a fixed value. `core/shared/config_spec.py` flags it automatically as a FIXED-value breach before the digest is computed. |

## C-007 — The reference decay formula diverges from the book

| | |
|---|---|
| **Appendix F says** | Table 16: `[scent decay rate]` = **0.10**, status **fixed**. The *rate* is settled. |
| **The gap that remains** | The **formula** is not a quantity, so Appendix F cannot settle it. The book's worked example uses multiplicative decay `(1−ρ)·τ + Δτ`, giving 0.9 → **0.81**. The reference implements subtractive `τ − ρ`, giving 0.9 → **0.80**. |
| **Reclassified 31/07** | Not a book contradiction — the book is self-consistent. It is a reference divergence sitting on a mechanism Appendix F does not cover. |
| **Our choice** | The book's multiplicative model. Appendix D says the book prevails over the repository. |
| **Effect** | `pheromones.decay_model = "multiplicative"`. The M#23 worked example (0.81 vs 0.80) catches the mismatch **before** the match and also reveals which implementation the opponent built on. Negotiation item **N13b**. |

## C-008 — The reference transmits the scent field but never seals it

| | |
|---|---|
| **Where** | Reference `smell_grid` handling vs. the commit-reveal payload |
| **The problem** | The field is transmitted with each turn but left outside the commitment hash, so a fabricated field passes the log audit undetected. Appendix F has no parameter here; this is a protocol gap the reference makes concrete. |
| **Our choice** | Seal a digest of the emitted field inside the per-step payload. |
| **Why** | We seal ours whether or not the opponent agrees. It costs nothing, and the log then carries evidence of our own integrity even when theirs does not. |
| **Effect** | `pheromones.seal_scent_digest = true`. Proposed at negotiation, not demanded. Negotiation item **N13c**. |

## C-009 — Reference `Board` defaults to 8-direction king movement

| | |
|---|---|
| **Appendix F says** | Table 15 row 1: `[movement set]` = four single orthogonal steps + STAY, **no diagonals**, status **fixed**. M#14 makes the sanction explicit. |
| **The reference does** | `Board.__init__(self, size, moves=None)` falls back to `tuple(Direction)` — all eight directions — when no move set is passed. Its own docstring admits it: *"the legacy 8-direction king movement is used when no move set is supplied."* The shipped config does pass the correct four, so the simulator itself is compliant. |
| **Reclassified 31/07** | **Not a contradiction.** The move set is fixed; this is a latent defect in code we were invited to reuse. |
| **Our choice** | Our `Direction` enum contains **no diagonals at all** — an illegal move is unrepresentable rather than merely rejected. |
| **Why it stays** | Any team porting that class and forgetting the `moves` argument plays an illegal game and only finds out when an opponent rejects a move mid-match. A test asserts `abs(Δrow) + abs(Δcol) ≤ 1` for every delta, so a careless port cannot reintroduce them here. |

---

# Category D — Gaps outside the game rules

Engineering and process. Appendix F governs game values; neither of these is one, but both are
places where a source left something undetermined and we had to choose.

## C-002 — Do docstrings count toward the 150-line limit?

| | |
|---|---|
| **Where** | Excellence guide §3.2 vs. §3.3 — not the rulebook, and not a game value |
| **The conflict** | §3.2 caps every source file at 150 lines of code excluding blanks and comments. §3.3 *mandates* a detailed docstring on every module, class and function. Neither says which category a docstring falls into. |
| **Our choice** | **Docstrings are documentation, not code, and are excluded.** |
| **Why** | Counting them puts the two requirements in direct opposition: the better a file is documented, the closer it sits to the limit — an incentive to under-document exactly where the guide demands the opposite. |
| **Scope** | Only genuine docstrings: the leading string expression of a module, class or function. A triple-quoted string bound to a variable is data and counts as code. Implemented via `ast` in `core/shared/loc_counter.py`. |
| **Transparency** | `FileReport` carries both `code_lines` (enforced) and `total_lines` (every physical line), so nothing is hidden by the interpretation. |

## C-004 — Line endings and the byte-identical config requirement

| | |
|---|---|
| **Where** | M#11 (shared config byte-identical on both sides) vs. cross-platform Git defaults |
| **The problem** | Not a contradiction, a trap the book does not mention. Git on Windows checks out CRLF, on macOS and Linux LF. Two teams on different platforms hold configs that are semantically identical but **byte-different**, so `config_sha256` will not match and the handshake refuses the match before the first move. |
| **Our choice** | Pin LF for all text files via `.gitattributes` (`* text=auto eol=lf`), published to both repositories. |
| **Why** | M#11 is enforced on bytes, not meaning. The failure appears only against an opponent on a different operating system — the worst possible moment to discover it. |
| **Effect** | `.gitattributes` is in `SHARED_PATHS` and unit-tested. Also silences Git's CRLF warnings on Windows. |

---

# Appendix — entries removed from this document

Three entries were deleted in the 31/07 re-audit, not because they were wrong but because they were
never contradictions. Each described a real decision; each now lives where that kind of decision
belongs. The IDs are **retired** and will not be reused, so anything referring to them still
resolves.

| Retired | What it said | Why it was not a contradiction | Where it lives now |
|---|---|---|---|
| **C-003** | Board size 7×7 in Appendix F vs. a 10×10 belief-map figure | `[board size]` is a **minimum**. A 10×10 figure illustrates a legal raised value; nothing conflicts. | `PARAMETERS.md` §4.3 — including the reason we decline increases: 14 barriers cover 28.6 % of a 7×7 but only 14 % of a 10×10, so a bigger board is strongly thief-favouring. |
| **C-011a** | `survival_threshold` and `max_moves` can be raised apart | Both are **minimums**; Appendix F explicitly permits raising either. It produces a *degenerate* configuration, not a contradiction. | `PARAMETERS.md` §4.2 — the invariant `survival_threshold == max_moves`, enforced by `config_spec.invariant_violations()`, deliberately kept separate from `violations()` because Appendix F itself is content with the unequal pair. |
| **C-012** | Our LLM provider was not one of the book's four modes | Table 21 states the choice is *"private to each peer... and is not subject to negotiation"* — private, outside the agreed config, not negotiated. It was our own configuration drift, not an ambiguity in any source. | `PARAMETERS.md` §5.2 — resolved 30/07: selector moved to `[trash_talk] provider`, committed value `template`, per-machine override via `P2P_LLM_PROVIDER`. |

**The lesson worth keeping.** All three were logged early, when "anything that looked odd" went into
this file. Applying the §0 test retrospectively removed a quarter of it. A document that lists
non-contradictions as contradictions is worse than a shorter one: it invites a reviewer to conclude
we had not understood which values were actually ours to choose.

---

## Template for future entries

Before adding an entry, apply the §0 test: **is Appendix F silent on this?** If the value is
*fixed*, *minimum* or *negotiable*, there is no contradiction — there is a value, a floor, or a
negotiation. Only mechanisms and timing can genuinely conflict.

```markdown
## C-00N — short title

| | |
|---|---|
| **Category** | A genuine gap / B resolved by the book / C reference defect / D not a conflict / E out of scope |
| **Where** | chapter / appendix / file |
| **The gap** | what is undefined, and why Appendix F cannot settle it |
| **Our choice** | what we implemented |
| **Why** | the reasoning |
| **Effect** | config key, code location, negotiation item |
```
