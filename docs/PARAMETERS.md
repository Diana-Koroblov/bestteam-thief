# Parameter Decision Register — Appendix F

**Status:** authoritative. Verified line-by-line against the rulebook PDF, Appendix F,
Tables 13–19 (pp. 135–139) on 30 Jul 2026.
**Companion code:** `core/shared/config_spec.py` (the same table, as data) and
`config/<role>/game.json` (the values we actually ship).

This file answers three questions for every parameter: *may we change it*, *should we*,
and *when is it decided*.

---

## 1. What the book actually says

Appendix F opens with a sentence that governs everything below it:

> "הערכים המוצגים בעמודת ״ערך לדוגמה״ הם המינימום המחייב"
> — the values in the *example value* column are the binding minimum.

And the status column has exactly three meanings (Appendix F §1, p. 139):

| Status | Hebrew | What it permits | If breached |
|---|---|---|---|
| **Fixed** | קבוע | Nothing. The value cannot change at all. | "סטייה מן הערך הזה פוסלת את הקבוצה" — deviation **disqualifies the team**. |
| **Minimum** | מינימום | Both sides may agree to move it **only in the direction that makes the game harder** (normally: raise it). Never below the example value. | Same disqualification exposure; and the audit sees it. |
| **Negotiable** | משא ומתן | Any value both sides agree on. The printed value is an example only. | — |

### 1.1 The default rule — this is the answer to "what do we do now"

Appendix F says the same sentence twice, once for *minimum* and once for *negotiable*:

> "בהיעדר הגדרה מפורשת מוסכמת בין הצדדים, על הקוד להבטיח שהערך לדוגמה הוא ברירת המחדל"
> — absent an explicit agreement between the parties, **the code must ensure the example
> value is the default the team uses.**

So the printed defaults are not a suggestion we are free to improve on. They are what our
code is **required** to fall back to. Shipping anything else as a default is a bug even
when the value would be legal after negotiation.

**Therefore: for the initial phase we ship every published default, unchanged.** That is
not caution, it is the rule. This is exactly what `config/police/game.json` and
`config/thief/game.json` now contain.

### 1.2 Values are chosen per game, not once

Appendix F §2 (Mandatory Rules):

- **Rule 1** — every value must appear in the config file, identical on both sides, and be
  cryptographically locked.
- **Rule 2** — "בכל משחק חדש רשאית הקבוצה לשנות את ההגדרות, כל עוד הן תואמות להסכמה עם
  הקבוצה היריבה" — **for each new game a team may change the settings**, provided the
  opponent agrees.
- **Rule 3** — each game's config file must have a **different name**, so any game can be
  reproduced.
- **Rule 4** — every game's config file must be **committed to GitHub**.
- **Rule 5** — every game needs an email to the lecturer with the commit hash used.

Rule 2 is the important one for your question. Parameters are not a one-time decision made
now. They are re-decided **at the negotiation step of every match**, and they may
legitimately differ between opponent A and opponent B — even between sub-game 1 and
sub-game 4 of the same series.

---

## 2. The three stages at which a parameter gets decided

| Stage | When | What is decided | Who |
|---|---|---|---|
| **S1 — Default** | Now, Phase 1 | Every parameter takes its published Appendix F value. Mandatory (§1.1). | Code |
| **S2 — Evidence** | Phase 8, self-play & ablation | Whether *we* benefit from raising any of the four movable values, measured over hundreds of simulated games. Not argued, measured. | Simulation |
| **S3 — Negotiation** | Phase 5 / 9, before each match | The values actually used against a specific opponent, agreed and hash-locked. Re-run per match. | Handshake |

The point of S2 is that we arrive at S3 with a number and a reason instead of an opinion.
The point of S1 is that if S2 finds nothing and S3 fails to agree, we still play — at the
default, which is always available and always legal.

**The strongest fact about our negotiating position:** we can never be forced. Both
*minimum* and *negotiable* changes require mutual agreement, and the fallback is the
published default. So "no" is always a complete, rule-compliant answer. We never need to
accept a value we dislike.

---

## 3. The full table — all 32 parameters

Appendix F contains **32** parameters across seven tables. (Our earlier docs said 31; that
was an undercount, corrected here and in `PRD.md`.)

Legend for **Decision**: 🔒 nothing to decide · ✅ keep the default · 📊 revisit with Phase 8
data · ⚠️ must be explicitly confirmed in the handshake, cheap to get wrong.

### Table 13 — Board, axes and starting positions

| # | Book name | Our key | Status | Default | Decision | Stage |
|---|---|---|---|---|---|---|
| 1 | גודל הלוח | `board_and_agents.grid_size` | Minimum | 7×7 | 📊 keep 7×7 | S3 |
| 2 | מספר הסוכנים | `board_and_agents.num_agents` | Fixed | 2 | 🔒 | — |
| 3 | ראשית מערכת הצירים | `board_and_agents.axis_origin_corner` | Negotiable | top-left | ⚠️ keep, confirm explicitly | S3 |
| 4 | אינדקס התחלת הצירים | `board_and_agents.axis_start_index` | Negotiable | 0 | ⚠️ keep, confirm explicitly | S3 |
| 5 | עמדת פתיחה – גנב | `board_and_agents.thief_start` | Negotiable | centre (3,3) | ✅ keep | S3 |
| 6 | עמדת פתיחה – שוטר | `board_and_agents.cop_start` | Negotiable | corner (0,0) | ✅ keep | S3 |

### Table 14 — Arena and verbal hints

| # | Book name | Our key | Status | Default | Decision | Stage |
|---|---|---|---|---|---|---|
| 7 | זירת המשחק | `world.map_area` | Negotiable | "New York" | ✅ keep | S3 |
| 8 | מגבלת מילים ברמז | `world.hint_max_words` | Negotiable | 15 | ✅ keep | S3 |

### Table 15 — Movement and barriers

| # | Book name | Our key | Status | Default | Decision | Stage |
|---|---|---|---|---|---|---|
| 9 | מערך התנועה | `movement_and_barriers.move_set` | **Fixed** | 4 orthogonal + STAY, no diagonals | 🔒 **refuse any variant** | — |
| 10 | מכסת המחסומים | `movement_and_barriers.max_barriers` | Minimum | 14 | 📊 keep 14 | S3 |
| 11 | תקרת הצעדים | `movement_and_barriers.max_moves` | Minimum | 35 | 📊 keep 35 | S3 |
| 12 | סף ההישרדות | `movement_and_barriers.survival_threshold` | Minimum | 35 | 📊 keep 35, **always equal to #11** | S3 |

### Table 16 — Dynamic pheromones

| # | Book name | Our key | Status | Default | Decision | Stage |
|---|---|---|---|---|---|---|
| 13 | עוצמת הריח במוקד | `pheromones.pheromone_center_intensity` | Fixed | 0.9 | 🔒 | — |
| 14 | קצב דעיכת הריח | `pheromones.pheromone_decay` | Fixed | 0.10 | 🔒 | — |
| 15 | גודל שדה הריח | `pheromones.pheromone_grid_size` | Fixed | 5×5 | 🔒 | — |

### Table 17 — Scoring

| # | Book name | Our key | Status | Default | Decision | Stage |
|---|---|---|---|---|---|---|
| 16 | ניקוד לכידה – שוטר | `scoring.capture_cop` | Fixed | 20 | 🔒 | — |
| 17 | ניקוד לכידה – גנב | `scoring.capture_thief` | Fixed | 5 | 🔒 | — |
| 18 | ניקוד הישרדות – שוטר | `scoring.survival_cop` | Fixed | 5 | 🔒 | — |
| 19 | ניקוד הישרדות – גנב | `scoring.survival_thief` | Fixed | 10 | 🔒 | — |
| 20 | ציון תיקו | `scoring.tie_score` | Fixed | 2 | 🔒 | — |

### Table 18 — Network and league

| # | Book name | Our key | Status | Default | Decision | Stage |
|---|---|---|---|---|---|---|
| 21 | מספר המשחקונים | `network_and_league.num_games` | **Fixed** | **6** | 🔒 the reference ships 1; see C-001 | — |
| 22 | תגמול גיוון | `network_and_league.diversity_reward` | Fixed | 10 | 🔒 — but see §5.1, this drives our whole league plan | — |
| 23 | מינימום משחקים למעבר | `network_and_league.min_games_to_pass` | Fixed | 2 | 🔒 | — |
| 24 | אומדן טוקנים לסדרה | `network_and_league.token_budget_per_series` | Negotiable | ~200 000 | ✅ keep — and see §5.2, we plan to spend 0 | S3 |
| 25 | מספר המשחקים המרבי לכל קבוצה | `network_and_league.max_games_per_team` | Fixed | 10 | 🔒 | — |

### Table 19 — Gatekeeper, rate limiting and network protection

| # | Book name | Our key | Status | Default | Decision | Stage |
|---|---|---|---|---|---|---|
| 26 | בקשות לדקה | `rate_limiter_gatekeeper.requests_per_minute` | Minimum | 30 | ✅ keep | S3 |
| 27 | בקשות מקבילות | `rate_limiter_gatekeeper.concurrent_requests` | Minimum | 2 | ✅ keep | S3 |
| 28 | השהיה לאחר שגיאה | `rate_limiter_gatekeeper.retry_backoff_sec` | Minimum | 5 s | ✅ keep | S3 |
| 29 | ניסיונות חוזרים | `rate_limiter_gatekeeper.max_retries` | Minimum | 3 | ✅ keep | S3 |
| 30 | עומק התור | `rate_limiter_gatekeeper.queue_depth` | Minimum | 100 | ✅ keep | S3 |
| 31 | מגבלת זמן התגובה | `network_and_league.response_timeout_sec` | Negotiable | 30 s | ⚠️ keep, and budget 20 s internally | S3 |
| 32 | סף כלב השמירה | `network_and_league.watchdog_timeout_sec` | Negotiable | 60 s | ⚠️ keep, must stay ≥ 2× #31 | S3 |

> **Why #31 and #32 sit under `network_and_league` in our JSON although the book prints
> them in Table 19:** the reference implementation
> (`rmisegal/Game-P2P-Cop-Chase`, `config/police/game.json`) groups them there, and most
> opponents will build from it. The shared file must be **byte-identical** with the
> opponent's, so matching the reference layout is worth more than matching the book's
> table boundaries. The grouping carries no rule meaning; the values do.

**Totals: 14 fixed · 9 minimum · 9 negotiable.** Our config carries all 32, verified by
`test_shipped_config_is_legal` and `test_defaults_alone_are_legal`.

---

## 4. The parameters that actually deserve a decision

Fourteen are fixed and need no thought. Of the remaining eighteen, five matter.

### 4.1 `max_barriers` — 14 is a **minimum**, and yes it can be raised

This was your direct question, so, precisely: **14 is the floor. Both teams together may
agree to raise it to 16, 20, anything. Neither team may lower it, and neither team can be
made to raise it.** Refusing is always legal, and the result of refusing is 14.

Now the part that changes the answer. From the barrier rule (Chapter 3.4):

> "בתור שבו השוטר מוותר על תנועה הוא רשאי להציב מחסום"
> — **in a turn where the cop forgoes movement**, it may place a barrier.

A barrier costs the cop its move. So on the default settings the cop has 35 turns and can
convert at most 14 of them into walls, leaving 21 turns of actual pursuit. **The cop's
scarce resource is turns, not barriers.** Raising the quota from 14 to 20 hands the cop six
more walls it has no spare turns to place — close to worthless.

That reframes the lever. The parameter worth discussing is not #10, it is #11/#12.

**Decision: keep 14. Do not spend negotiating capital raising it.**

### 4.2 `max_moves` and `survival_threshold` — the real lever, and they must move together

Both default to 35, both are minimums, both may be raised.

- Raising **both** together gives the cop more turns to spend on walls *and* pursuit while
  the thief's survival requirement rises equally. Net effect: **cop-favouring**, because the
  cop's binding constraint is the clock and the thief's is not.
- Raising **only** `max_moves` is meaningless — the thief has already won at step 35.
- Raising **only** `survival_threshold` above `max_moves` creates a game that ends before
  either win condition can fire. **Never agree to this.**

**Rule we adopt: `survival_threshold == max_moves`, always, in every proposal we make or
accept.** If an opponent proposes them unequal, that is either a bug in their
implementation or a trap, and it is worth finding out which.

**Decision: keep 35/35 for now.** Whether to propose 45/45 is an S2 question: it is only
good for us if our cop converts extra turns into captures better than a generic cop *and*
our thief loses less than a generic thief to the same extra turns. The Phase 8 ablation
(task 8.2.6) measures exactly that. Until it reports, proposing a change would be guessing
in a direction that helps whichever side is stronger — and we do not yet know that it is us.

### 4.3 `grid_size` — 7×7 is a minimum; keep it

14 barriers on a 7×7 board is 14 walls over 49 cells — **28.6 %** of the board can be
sealed. On 10×10 the same 14 barriers cover **14 %**, and the cop's Manhattan distance from
(0,0) to the centre grows from 6 to 9 while the clock stays at 35.

A larger board is strongly **thief-favouring**: more cycles to circulate in, more distance
to open, a barrier budget that no longer buys a cut. Our cop plan (diagonal minimum cuts,
driving the thief's exit count to 1) is calibrated to the barrier-to-area ratio at 7×7 and
degrades faster than linearly as the board grows.

**Decision: keep 7×7, and treat a proposal to enlarge it as information.** A team that
opens by asking for 10×10 is telling us they rate their thief above their cop. That belongs
in the opponent profile (`docs/PRD_strategy_advanced.md` §5) whether we accept or not — and
we should not accept.

### 4.4 `cop_start`, `thief_start` and the coordinate system — the cheap catastrophe

You are right that these are examples, not fixtures. The book prints "פינה (0,0)" for the
cop and "מרכז (3,3)" for the thief and marks both **negotiable**.

The defaults are deliberately thief-friendly: the thief starts on the highest-mobility
square on the board with four exits and maximum cycle access; the cop starts in a corner
with **two** exits, six Manhattan steps away. Moving the cop to, say, (2,2) would make the
cop dramatically stronger.

We keep them anyway, for three reasons: the defaults are what the reference implementation
ships and therefore what every opponent will propose; we field both roles, so a
role-favouring change is close to a wash for us and pure noise in our Phase 8 data; and any
change here invalidates every simulation we are about to run.

**Decision: keep (0,0) and (3,3).**

**But #3 and #4 are a different matter, and this is the one item on this page I would call
dangerous.** `axis_origin_corner` and `axis_start_index` are negotiable *conventions*. If we
read (0,0) as top-left and the opponent reads it as bottom-left, every coordinate we
exchange is mirrored: our capture claims disagree with theirs, our barrier declarations land
on the wrong cells, and the end-of-game log audit reports **forgery against two honest
teams**. Both score 0.

Worse, the book never states whether a position tuple is `(row, col)` or `(x, y)`. At (3,3)
the ambiguity is invisible. At (0,1) it is a mirror. **This gap is logged as C-010** and the
handshake must resolve it with a worked example, not a label:

> "We read `[0, 1]` as row 0, column 1 — one cell **East** of the cop's start. Confirm."

One sentence, exchanged before the first move, that removes an entire class of disqualification.

### 4.5 `response_timeout_sec` — 30 s is our search budget

Every move our agent returns must arrive inside 30 seconds, including LLM latency and
network. Expectimax at depth 3 over a 7×7 belief grid is comfortably inside that; depth 4
may not be, and a cloud LLM call on a slow link may not be.

**Decision: keep 30 s, budget 20 s internally, and make the search *anytime*** — it returns
the best move found so far when the budget expires rather than overrunning. A timeout is a
technical loss (0 points); a slightly shallower search is not.

An opponent proposing a **shorter** timeout is attacking our search depth. It is negotiable,
so we simply decline and the default stands. An opponent proposing a longer one is telling
us their agent is slow — which usually means a deep search or a cloud LLM in the move loop.
Profile note, not a favour to grant reflexively.

`watchdog_timeout_sec` must stay comfortably above it; **keep 60 s, never below 2× the
response timeout.**

---

## 5. Two parameters that are fixed but should still change our behaviour

### 5.1 `diversity_reward = 10` — the highest-value item in the whole project

Ten points for beating a **new** opponent. That is worth as much as an entire thief
survival win, and it is available up to `max_games_per_team = 10` times.

Consider two teams that play equally well:

- Team A plays the minimum 2 opponents. Best case ≈ 2 series of match points + 20 diversity.
- Team B plays 10 opponents. Same per-series quality, + **100** diversity.

The gap is larger than anything our search algorithm can produce. **Scheduling more distinct
opponents outperforms every technical improvement in this project**, and it is the only
lever with a hard deadline attached — other teams fill their calendars too, and we have 15
days.

This is TODO 0.3.1 (contact 6–8 teams) and 0.3.2 (book a warm-up), both ⏰ and both waiting
on you. They are, on the arithmetic, more urgent than anything on my list.

### 5.2 `token_budget_per_series` — negotiable, and we intend to spend zero

Appendix F Table 21 defines four LLM modes, and the choice is explicitly **private to each
peer and not negotiated**:

| Mode | Where it runs | Token cost |
|---|---|---|
| `template` | in-process, pre-written sentences | **zero** — the book's default |
| `ollama` | local model at `localhost:11434` | **zero** API tokens |
| `claude_api` | cloud Haiku via API | real, counted against the budget |
| `claude_cli` | `claude -p` via Claude Code CLI | highest cost |

The book then says something worth reading twice:

> "במצבי `template` ו-`ollama` ניתן לשחק את כל הסדרה בת [ מספר המשחקונים ] המשחקונים באפס
> טוקנים, וכל התחרות עוברת לאיכות אלגוריתם התנועה."
> — in `template` and `ollama` modes the entire series can be played at zero tokens, and
> **the whole competition reduces to the quality of the movement algorithm.**

That is precisely where our work is: expectimax over a Bayesian belief, connectivity-based
barrier placement, cycle-aware evasion. Running at zero tokens removes budget risk, removes
a network dependency in the move loop, removes a source of timeout, and moves the contest
onto our strongest ground.

**Resolved 30 Jul (C-012).** The selector now sits at `[trash_talk] provider` where the book
puts it, and the **committed** value is `template`. Each machine overrides it in `.env`:

| Machine | `P2P_LLM_PROVIDER` | Used for | Token cost |
|---|---|---|---|
| Diana (no GPU) | `groq` | development and self-play only | ours, not the series budget |
| Itay (stronger) | `ollama` | **all graded matches** | zero |
| any fresh clone | `template` | fallback, always works | zero |

Every graded match therefore runs in `ollama`, one of the book's four modes, at zero tokens.
Groq never appears in a scored game and never appears in the committed config.

**Two consequences of hosting matches from Itay's machine**, both worth acting on:

1. **His ngrok domain is the one that matters**, not Diana's. TODO 0.2.4 and 0.2.6 move from
   "Itay's task, whenever" to blocking for the league.
2. **One hosting machine is a single point of failure.** If it is down at match time the
   result is a no-show, and a no-show is a technical loss worth 0 — for both sub-games and
   possibly the series. Diana's machine should stay match-capable on `template`, which costs
   nothing to maintain because `template` is already the committed default.

---

## 6. Keys we ship that Appendix F does **not** define

Seven, all deliberate. Each is negotiable by construction, and each exists because leaving
it undefined caused a documented contradiction.

| Key | Default | Why | Contradiction |
|---|---|---|---|
| `scoring.technical_loss` | 0 | Not in Table 17, but present in the reference config, and the mandatory rules assign 0 for a technical loss. Keeping it matches the reference and makes the sanction explicit. | — |
| `capture.resolution` | `after_moves` | The book leaves the ordering of simultaneous moves and capture evaluation open. | C-006b |
| `capture.stay_counts_as_move` | `false` | M#47 vs the survival counter. | C-006a |
| `capture.swap_is_capture` | `true` | Two agents crossing through each other. | C-006c |
| `pheromones.decay_model` | `multiplicative` | The book's worked example gives 0.81; the reference implementation's subtractive decay gives 0.80. Whoever is silent about this loses the audit. | C-007 |
| `pheromones.field_includes_current_turn` | `true` | Whether the emitted field includes the turn being committed. | C-005 |
| `pheromones.seal_scent_digest` | `true` | The scent grid is transmitted but not sealed, so a fabricated field passes audit unless we seal it. | C-008 |

Adding keys to the shared file raises the bar for a byte-identical match, so each one costs
us something at negotiation. All seven are worth it: every one of them is a case where two
honest implementations would otherwise diverge mid-match and the audit would blame both.

---

## 7. Negotiation playbook

**Open with the pure default file.** It is what the reference ships, what most opponents
will propose, and the value our code is required to fall back to. A byte-identical match on
the first exchange is the cheapest possible handshake.

**Confirm before agreeing** — the two items a label does not settle:

1. Coordinate convention, with a worked example (§4.4).
2. `survival_threshold == max_moves` (§4.2).

**Refuse without hesitation:**

- Any change to a **fixed** value — accepting disqualifies *both* teams, so "they asked for
  it" is not a defence. `core/shared/config_spec.py` catches this automatically.
- Diagonals in `move_set` (#9). The reference implementation's `Board` class defaults to
  8-direction king movement (C-009), so this will come up by accident, not malice — but the
  answer is the same.
- Any value **below** a published minimum.
- `survival_threshold > max_moves`.
- A response timeout below 30 s.

**Decline politely, and write it down:**

- A larger board (§4.3).
- A cop start closer to the centre.
- A raised barrier quota without a matching move cap (§4.1).

Each of these is a free read on how the opponent rates their own two roles. Log it in
`docs/LEAGUE_LOG.md` whether we accept or not.

**Propose a change only when Phase 8 says so**, and only ever `max_moves` +
`survival_threshold` together.

**One item Appendix F does not parameterise at all: how the 6 sub-games split between the
two roles.** The book fixes `num_games = 6` and never says who plays cop. We field both
roles, so the natural split is 3–3, but an opponent strong in one role has an obvious
interest in an uneven one. **Pin it explicitly in the handshake and insist on 3–3.** Logged
as C-011 and carried as negotiation item N17.

---

## 8. What is decided, and what is still open

**Decided now (S1), and already shipped:** all 32 parameters at their published defaults.
This is mandatory, not a preference.

**Open until Phase 8 (S2):** whether to propose `max_moves` / `survival_threshold` at 45/45.
One question, one ablation, one number.

**Open until each match (S3):** everything negotiable, re-decided per opponent, written to
`config_<game_id>_g<NN>.json`, hash-locked, and committed (Appendix F §2 rules 2–4).

**Open for you:** the LLM provider question in §5.2, and — far more valuable than anything
on this page — TODO 0.3.1, booking opponents (§5.1).
