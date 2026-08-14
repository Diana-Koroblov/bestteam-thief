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
| **A. Genuine gaps** — the rulebook does not define the behaviour anywhere | C-005, C-006b, C-006c, C-010, C-011, C-013, C-018 | **Must be settled in the pre-match agreement.** Every one appears in `PRD_negotiation.md`. |
| **B. Resolved by the rulebook** — looked ambiguous, settled on a closer reading | C-006a | Implemented as read. Flag kept only because an opponent may arrive with the other reading. |
| **C. Reference-implementation defects** — the book is unambiguous, the reference diverges | C-001, C-007, C-009, C-008 | **Watch items.** Most opponents will build on the reference and inherit these. Detect at the handshake. |
| **D. Gaps outside the game rules** — engineering and process | C-002, C-004, C-014, C-015 | Our own decisions, recorded for the reviewer. |

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
| **Our choice** | The transmitted field **includes** the current turn's deposit. A received field is first acted on when deciding the **following** turn. |
| **Why** | Including the deposit matches the reference implementation, so it is what most opponents will send. Uncertainty survives regardless: both peers move again afterwards, leaving ≥5 candidate cells. The one-turn lag is not a choice — our move for turn *k* is committed before their reveal for turn *k* can arrive — but it has to be **stated**, because a peer that acts on the current turn's field is revealing before committing, which is the single attack commit-reveal exists to prevent. |
| **Effect** | `pheromones.field_includes_current_turn = true`. Both halves are sealed inside the M#23 scent-model digest as `field_includes_current_turn` and `sampling_mode = end_of_previous_full_turn` (`core/crypto/scent_model.py`), and both appear in the agreement artefact. Negotiation item **N13**; TODO 9.1.7. |

## C-006b — M#46 timing: a barrier on a cell the thief is leaving

| | |
|---|---|
| **Where** | M#46 — a barrier on the cell where the thief stands *"at that moment"* — under commit-reveal, where neither side sees the other's action before choosing |
| **The gap** | Cop commits "place at (6,6)" while the thief commits "move to (6,5)". Is the thief captured? *"At that moment"* could mean commit time or after resolution. Appendix F has no parameter for this, so nothing there settles it. |
| **Our choice** | **Positions are evaluated after both actions apply.** A barrier on a vacated cell does not capture. |
| **Why** | The alternative makes the cop overwhelming: any adjacency becomes a guaranteed capture and the thief can never escape once approached, which cannot be the intended balance. M#46 still matters under our reading — it catches a thief that chose STAY, which is common and predictable. |
| **Effect** | `capture.resolution = "after_moves"`. Negotiation item **N15**. ⚠️ Integration note for Phase 3: `BarrierManager.place()` compares against whatever `thief_pos` the caller passes, so the turn loop must pass the **post-move** position under this setting. |
| **The mirror case, found 05/08** | The note was never actioned, and the **mirror** of the case above was silently broken: a thief moving **onto** the cell the cop is walling resolved as neither capture nor blocked move. It ended the turn standing **inside a barrier** — a state no rule describes — `are_connected` could not reach it (an impassable cell is never expanded into), and it walked straight out the next turn, because a barrier blocks entry and not exit. Found by the Phase 8.2 self-play, which reaches positions the baseline thief never did; it surfaced as 4 bogus `cop_separations` against 3.5.4's and 8.QG.4's requirement of 0. |
| **Resolved 05/08** | **It captures.** The turn loop resolves the thief's move first and hands the **post-move** cell to `BarrierManager.place`, so both halves of this entry now come out of one value: a wall on a vacated cell misses, a wall on the cell the thief steps onto captures. Chosen because it is what this entry's own rule already says — *positions are evaluated after both actions apply* — and because it does not unbalance the game the way the rejected reading would: the cop still has to guess correctly which cell the thief is moving to, so it is a 1-in-N shot rather than a guaranteed capture on adjacency. Worth four sub-games over 48 openings, and it took self-separation to 0. Asserted both ways in `tests/unit/test_simultaneous_barrier.py`. ⚠️ **`capture.resolution` sits in the shared `game.json` and therefore inside the M#11 digest**, so this reading must be confirmed with the opponent at negotiation item **N15** — two peers disagreeing here would have the end-of-match audit report forgery against two honest teams. |

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
| **Second gap, found building the series runner** | `"3-3"` is **symmetric**, so two peers can agree on it completely and still disagree about who plays cop first. The split says how many sub-games each side takes and never which side starts. |
| **Our choice** | The plan is built from the role *this process* holds (`roles_for(split, first, count)` in `core/runtime/series.py`), and `negotiation.settle` **refuses** two peers claiming the same role. Without the refusal the disagreement first surfaced as `PeerRuntime._require_opponent` rejecting the opponent's opening commit — a technical loss for both teams, worth 0 each, over something the handshake settles for free. |

## C-013 — A series of technical losses is arithmetically a tie

| | |
|---|---|
| **Where** | Appendix F Table 17 row 5 vs. Ch. 3.5 |
| **The gap** | `tie_score` is **fixed** at 2, so the *value* is not in question — but *when a tie is declared* is not a quantity and Appendix F does not define it. Table 17 pays each side `tie_score` when the cumulative total ends level. A series where every sub-game ended in a technical loss is level, at 0-0. Read literally, both teams collect the bonus for a series neither played. |
| **Why it matters** | It inverts the incentive Ch. 3.5 exists to create: *"a technical loss zeroes both sides alike, thereby incentivising both to maintain protocol correctness rather than to win on a timeout"*. Two teams that crashed six times each would outscore a team that played honestly and lost narrowly. |
| **Our choice** | The tie bonus is paid only when **at least one** sub-game produced a real result. An all-technical-loss series, and an empty series, return 0-0. |
| **Why** | It is the reading that cannot be gamed, and the one the Ch. 3.5 rationale plainly intends. Where a literal reading and a stated purpose disagree, implement the purpose. |
| **Effect** | `core/domain/scoring.aggregate()` filters technical losses before deciding the tie; three tests pin it. **Needs a negotiation item — see N19.** |

## C-018 — A barrier placement is declared but not sealed

| | |
|---|---|
| **Where** | Ch. 3.4 and M#15/M#16 (open, truthful declaration of every placement) vs. Ch. 5.3.1 (`H = SHA256(State ‖ Move ‖ Intent ‖ Nonce)`) |
| **The gap** | Placing costs the cop its move, so a placement travels as `STAY`. The four sealed fields therefore cannot tell "the cop stood still" apart from "the cop walled (2,3)" — the cell exists only in the declaration, which is not inside any hash. Two duties are stated and never joined: the book requires the placement to be declared truthfully, and requires moves to be unforgeable, but the declaration is the one part of a turn no commitment covers. |
| **Why it matters** | It is the single move in the game a peer can still revise after seeing the opponent's reveal. A cop could commit `STAY`, watch the thief's move arrive, and only then declare which of up to five adjacent cells it walled — recovering exactly the after-the-fact advantage commit-reveal exists to remove, while every step in its log still audits clean. It is also the *asymmetric* hole: the thief has no equivalent, so leaving it open favours whichever side plays cop. |
| **Our choice** | Seal the cell as an optional `barrier_cell` key inside the step payload, present **only** on turns that place one. Proposed at negotiation, never assumed. |
| **Why** | Presence-not-value mirrors `scent_digest` (C-008), and that is what keeps an opponent who declines auditable by the same code: an ordinary turn hashes byte-identically whether or not either peer implements this, so the extension can only ever affect turns that actually wall a cell. Sealing unilaterally would be worse than not sealing — the opponent recomputes our digests with their own payload builder, and one key they do not add fails every barrier turn we ever sent, making an honest peer look like a forger. |
| **Effect** | `movement_and_barriers.seal_barrier_cell = true`. `commitment_payload` takes the cell; `LocalTruth.sealed_barrier` is the only thing that decides whether it is passed, applying both conditions (a barrier was placed *and* it was agreed). The log carries `barrier_cell` for the reader always and `sealed_barrier_cell` only when it was hashed, so a peer that declares without sealing still passes its own audit. Negotiation item **N20**; closes TODO 1.3.2.b. |

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

## C-014 — Two deviations from PRD 7's Gatekeeper interface

| | |
|---|---|
| **Category** | D — our own engineering, not a rulebook conflict. Appendix F sets the Gatekeeper's *numbers* (Table 19) and is silent on its shape, so §0 admits this. |
| **Where** | `PRD_7_reporting.md` §3.1 (gate order) and §4 (exception names) vs. `core/shared/gatekeeper.py` |
| **The problem** | Both are cases where following our own PRD literally produces something worse. **(a) Gate order.** §3.1 draws quota → bucket → detector. Taken literally the detector is blind to the case it exists for: once the quota is spent every call is rejected before reaching it, so a runaway loop hammering an exhausted quota is invisible. **(b) Exception names.** §4 specifies `GatekeeperLocked` and `QuotaExhausted`. Ruff's `N818` rejects both, and 5.QG.1 requires zero violations — so the PRD as written cannot pass our own gate. |
| **Our choice** | **(a)** Detector first: `detector → quota → bucket`. **(b)** `GatekeeperLockedError`, `QuotaExhaustedError`, matching the `Error` suffix every other exception in this codebase already uses. |
| **Why** | **(a)** Nothing goes out under either order, so the account is safe either way — but only one *names* the fault. "Locked: 400 calls in 10 s, this is a loop" is a diagnosis; "quota exhausted", repeated ten thousand times, is not. **(b)** A linter that is a binding gate outranks a naming choice in a design document, and the codebase is already unanimous: `PeerError`, `TunnelError`, `ConfigError`, `RateLimitsError`. One pair of exceptions spelled differently would be the inconsistency, not the fix. |
| **Effect** | `core/shared/gatekeeper.py` — the reordering is argued in the module docstring beside the corrected diagram. `PRD_7_reporting.md` is left as written: it records what we designed, this file records what we shipped and why they differ. |

## C-015 — A turn number in a phase machine that forbids turn numbers

| | |
|---|---|
| **Category** | D — our own engineering. Appendix F says nothing about barrier *timing*; it sets the quota (14, a minimum) and stops. |
| **Where** | `PRD_strategy_advanced.md` §3.4 **A1.11** — *"phase transitions are driven by measured state… never by turn number"* — vs. `[strategy] barrier_hold_until_turn = 8`, shipped in both `config/police/game.toml` and `config/thief/game.toml` since Phase 0. |
| **The problem** | The config key predates the requirement and directly contradicts it. Deleting the key loses a real safety property: early barriers are the classic way a cop throws a sub-game, and a hard floor is cheap insurance while the phase thresholds are still untuned. Honouring the key as written makes the turn counter a trigger, which is exactly what A1.11 forbids — and it would also veto A1.12, which requires spending barriers *earlier* against an orbiting thief. |
| **Our choice** | The key is **suppressive only**. Below that turn it can hold the cop in HERD; it can never by itself cause a placement. A measured ORBITER classification lifts it. Every transition *into* SEAL or SQUEEZE is caused by entropy, exit count or region size. |
| **Why** | A guard that can only ever make us more conservative is not driving the decision — it is bounding it, the way `max_retries` bounds the Gatekeeper without deciding when to call. That reading satisfies A1.11's intent (no schedule) and A1.12's requirement (measurement can always override) at once, and keeps the insurance. Measured across sixteen openings the floor is currently inert — identical captures, steps, barriers and separations at 0 and at 8 — so it costs nothing to keep. |
| **Effect** | `police/phases.py` — argued in the module docstring, asserted by `test_the_turn_floor_can_only_delay_a_placement` and `test_a_measured_orbiter_lifts_the_turn_floor`. The shipped value stays 8; `PhaseSettings()` defaults it to 0, so a caller with no config is driven purely by measurement. |

## C-016 — Is "flee-greedy or orbiter" one profiled trait or two?

| | |
|---|---|
| **Category** | D — our own engineering. Appendix F says nothing about opponent modelling at all; the cap is ours, from `PRD_strategy_advanced.md`. |
| **Where** | `PRD_strategy_advanced.md` §5.2 **A3.6** — *"At most four traits. Adding a fifth requires evidence it survives the noise"* — and its table, which names **barrier rate, flee-greediness, hint-responsiveness and reliability `r`**. Against `police/phases.py` as shipped in 8.1.10, which already measured **two**: a flee fraction and an orbit fraction. |
| **The problem** | Four named in the table plus orbit detection already in the code is five, and A3.6 caps it at four. Dropping orbit is not free: A1.12 requires the cop to spend barriers **earlier** against a thief that circles, because an orbiter never corners itself and the chase never converges — behaviour that shipped in 8.1.10 with tests, and that a greedy-fleer reading cannot substitute for. Keeping both and calling it five needs the evidence A3.6 demands, which is a measurement run on the critical path for a distinction the phase machine already handles. |
| **Our choice** | **One trait, two thresholds.** `OpponentProfile.style()` returns a three-way category — `FLEE_GREEDY`, `ORBITER`, `UNKNOWN` — read off a single observation stream (the belief-peak trajectory) behind a single sample gate. The four are then movement style, barrier rate, hint-responsiveness and reliability. |
| **Why** | A3.6's limit exists for a statistical reason, not an arithmetic one: 200 observed steps per series cannot support many independent estimates without fitting noise. What costs sample size is an independent *observation stream* with its own gate, and flee and orbit are not that — they are two questions asked of one trajectory, gated together at `MIN_MOVEMENT_SAMPLES`, and a mutually exclusive answer is returned. Counting them as two would also make the cap depend on how a category happens to be spelled: a single `MovementStyle` enum with three values is exactly the same measurement as two fractions with two thresholds. Where they genuinely compete — a fleer on a finite board eventually revisits cells too — the tie is resolved in favour of the stronger evidence rather than by adding a trait. |
| **Effect** | `core/domain/opponent_profile.py` — the four are listed in `TRAITS`, and `test_we_profile_exactly_the_number_of_traits_the_config_permits` compares that tuple against `[strategy] max_profiled_traits` in the **shipped** config. The key had been present since Phase 0 and read by nothing, which made the cap unenforceable: a fifth trait could have been added without a single test noticing. It is now the thing that would fail. |

## C-017 — One deviation from PRD_negotiation §4's interface

| | |
|---|---|
| **Category** | D — our own engineering, not a rulebook conflict. Appendix F fixes what must be *agreed*; the shape of the function that agrees it is ours. |
| **Where** | `PRD_negotiation.md` §4 specifies `negotiate(proposed, opponent_url, games_played) -> tuple[NegotiationResult, LockedAgreement]`, against `core/protocol/negotiation.py` as shipped. |
| **The problem** | One function that takes a URL cannot be tested without a network, and it is the function whose *refusals* most need testing — a refusal path nobody exercises is a refusal path that fires for the first time in a graded match. Returning the result alongside the agreement also duplicates it: `LockedAgreement.result` is the same value, and two copies of one verdict can disagree. `games_played` as a caller-supplied integer is worse still: M#38 disqualifies the whole project for one wrong declaration, and a parameter is a place to type a stale number. |
| **Our choice** | Three functions and no network. `proposal(config, role, games_played, scent_digest, step_zero, role_split)` builds what we send; `settle(ours, theirs)` compares two messages and returns a `LockedAgreement` carrying its own `result`; `refused_by_opponent(ours, detail)` records the asymmetric case. The URL and the environment move up one layer to `core/runtime/prematch.py`, which reads the commit from git, the counted total from `LEAGUE_LOG.md` and the model from the provider registry. |
| **Why** | Every refusal is now provokable from two plain dataclasses, so all five outcomes are tested rather than the one the happy path reaches. Splitting the environment out is also what makes the declaration honest: nothing accepts a hand-typed game count, because the only caller reads the log. The extra `refused_by_opponent` exists because the handshake **is** asymmetric — whoever answers raises, whoever asked receives an error string — and without it the initiating peer would learn of a refusal as a traceback and file no record of the outcome most likely to be disputed. |
| **Effect** | `core/protocol/negotiation.py` (the comparison), `core/protocol/agreement.py` (the verdict and the artefact), `core/runtime/prematch.py` (the environment). `PRD_negotiation.md` is left as written: it records what we designed, this file records what we shipped and why they differ — the same posture as C-014. |

## C-019 — Our MCP tool surface is not the one every other team built

| | |
|---|---|
| **Category** | D — our own engineering. Appendix F governs game *values*; the rulebook mandates MCP and FastMCP and is silent on tool names. |
| **Where** | `PRD_2_mcp_infra.md` §3.5 (our six tools) vs. the Appendix D example repository, `src/police_thief/infra/mcp_server.py`, which exposes four. Ch. 2.3.2 shows a *third* set — a single illustrative `receive_move(signed_move, signature)` that nobody implements. |
| **The problem** | Not a contradiction: nothing was breached. But the reference is what most teams started from, so its surface is the de-facto standard and ours is the outlier. Discovered on 13/08 against `nis-yar1`, a team that had already played several others without difficulty; two scheduled friendly slots were lost to it. Under M#31 a project with fewer than two counted matches scores nothing at all, so "the opponent should adapt" is a plan that risks the whole grade on other teams' goodwill. |
| **How deep it goes** | Names are the smallest part. The reference tools are **fire-and-forget mailboxes** returning `{"ok": true}`: a peer pushes and every answer arrives later as a separate inbound call, where ours are synchronous and return payloads. Its `TurnMessage` carries `hint`, `smell_grid` and `commit` and **never the move**, so each peer tracks only its own position and infers the other's — where `match_driver._resolve` applies the opponent's revealed move to a board holding both. Reveals are deferred to one `submit_audit` at the end rather than sent per turn. The thief opens; there is no separate turn signal. |
| **Our choice** | **Speak both.** `core/compat/` implements the reference protocol as an additive second path, selected with `--protocol reference`. The native path is untouched. |
| **Why not migrate** | The native path is what our PRDs, tests, self-play and four filed artefacts describe, and it is the one whose commit-reveal ordering the audit was written against. Replacing it to satisfy an opponent's wire format would put the graded core of the project through surgery on a match night. Why not *only* the native path is the entry above. |
| **Why the surface replaces rather than extends** | Both protocols spell one tool `negotiate` and mean different things by it — different parameter name, different return contract. A server exposing both would answer that call wrongly for one of the two, so the flag picks a side. |
| **Worth stealing from them** | Their audit records ship `{payload, nonce, commit}` together, so a verifier re-hashes exactly what the sender supplied and **no shared payload schema is needed**. Ours requires both peers to build byte-identical payloads, which is what C-008 and C-018 spend their length managing. Theirs is the better design for playing strangers. |
| **Effect** | `core/compat/` (`sealing`, `wire`, `mailbox`, `exchange`, `turns`, `session`), `core/cli_compat.py`, `--protocol` in `core/cli_args.py`, an optional tool-set override on `PeerSDK.server_spec`, and an `argument` parameter on `OpponentClient.call` because their tools bind `message` where ours bind `payload`. Asserted by `tests/unit/test_compat_protocol.py`, including that their hash formula and ours stay **different**. |
| **Update 13/08 — measured, not assumed** | `python -m core a2a --probe https://inches-drawings-dem-extends.trycloudflare.com` lists **nine** tools on nis-yar1's server: our six *and* their `receive_turn`, `submit_audit`, `receive_control`. They have added our surface, so the friendly can run on the native path with no compatibility layer on either side. `core/compat/` stays — it was built for the teams we have not probed yet, and one opponent adapting does not make the reference surface stop being the de-facto standard. The lesson is the probe itself: which protocol an opponent speaks is a **fact about their running server**, answerable in ten seconds, and both lost slots were lost to assuming it instead. |

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
