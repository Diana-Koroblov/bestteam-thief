# PRD — Pre-Match Negotiation
### Cross-cutting · owner [D] · required from Layer 5, exercised in Phase 9

**Book:** Chapter 3 §3.2, Chapter 9, Appendix B, Appendix F §2
**Exit criterion:** two peers agree a configuration, verify it is byte-identical, declare game
counts honestly, and lock the agreement cryptographically before the first move.

---

## 1. Purpose

Establish the rules of a specific match between two teams who have never met, who do not trust
each other, and who have no arbiter. Everything the match depends on — board size, scoring, decay
rate, timeouts — must be identical on both sides, and each side must be able to *prove* it is.

This is also, quietly, a competitive instrument. The book states that the agreed contract is
**a floor and not a ceiling**, and that it is *"permitted and even wise to legally exploit any gap
not defined here, for the benefit of both sides or for competitive advantage."* That is an explicit
invitation, and most teams will not read it as one.

---

## 2. Background

With a central server, the server dictates physics and both clients obey. Without one, each side
runs its own copy of the rules — and if the two copies disagree on any value, the match splits into
two irreconcilable realities. The fix is a single shared source of truth, loaded byte-identically
on both ends and sealed with a hash.

The split between shared and private configuration follows one test: *must the opponent agree to
this value, or depend on it?* If yes, it belongs in the signed JSON. If no, it stays in the private
TOML. Board size is shared. Which language model we use is not.

---

## 3. Requirements

### 3.1 The handshake

| ID | Requirement |
|---|---|
| N1 | Exchange the proposed `config/game.json` and compare `config_sha256` on both sides. |
| N2 | Any mismatch **refuses the match**. Do not play and reconcile later (M#11). |
| N3 | Exchange the scent emission and decay model **with a concrete worked example** — e.g. centre τ=0.9 decays to 0.81 after one turn at ρ=0.10 — and hash the agreement (M#23). |
| N4 | Declare honestly how many counted matches we have already played (M#37). |
| N5 | Exchange Step-0 declarations including `github_commit` (M#24, M#53). |
| N6 | Exchange public MCP URLs. |
| N7 | Record every negotiated deviation in the config JSON and in `CONTRADICTIONS.md`. |

N3 exists because agreeing on a *formula* is not the same as agreeing on its *interpretation*. A
worked number removes the ambiguity that a symbolic agreement leaves. The book explicitly permits
one team to hand the other the scent code itself — offering this is worth considering, since it
guarantees behavioural parity and makes us the reference implementation.

### 3.2 Honest declaration

| ID | Requirement |
|---|---|
| N8 | The declared count must match `LEAGUE_LOG.md`. |
| N9 | A false declaration disqualifies the entire project (M#38). |

This is not enforced by trust. Both teams email the lecturer after every match, so the true count
is known centrally at all times — a false declaration is discovered at grading, not during play.

### 3.3 What may be negotiated

From Appendix F. `minimum` may only be raised, never lowered (M#12). `fixed` cannot change at all.

| Parameter | Default | Status | Our stance |
|---|---|---|---|
| Board size | 7×7 | minimum | Accept 7; accept larger if proposed — our engine is size-agnostic |
| Axis origin / index base | top-left / 0 | negotiable | **Confirm explicitly.** If one side counts from 0 and the other from 1, `[3,3]` means different cells and the match silently diverges |
| Thief start | (3,3) | negotiable | Centre suits an evader; concede reluctantly when playing Thief |
| Cop start | (0,0) | negotiable | Corner is a real handicap for the pursuer; propose closer when playing Cop |
| Map area | New York | negotiable | Propose a region whose landmark vocabulary our local model handles well |
| Hint word limit | 15 | negotiable | Accept |
| Barrier quota | 14 | minimum | Propose higher when playing Cop — our trap planning scales with it |
| Max moves / survival threshold | 35 | minimum | Longer favours the Cop; shorter is not permitted |
| Response timeout | 30 s | negotiable | Raise if the rehearsal shows p95 latency close to it |
| Watchdog threshold | 60 s | negotiable | Raise together with the response timeout |
| Token budget | 200 000 | negotiable | Accept; we spend near zero |
| Everything marked *fixed* | — | fixed | Not open to discussion, including by us |

### 3.4 Negotiation as strategy

Legitimate, documented moves — every one recorded in the config JSON:

- **Ask for a higher barrier quota when playing Cop.** Raising a minimum is always legal, and our
  trap planning benefits more from extra barriers than a greedy opponent's does.
- **Confirm the coordinate convention in writing.** Cheap insurance against the most silent failure
  in the whole protocol.
- **Choose the map area.** Free flavour that costs nothing and slightly favours whoever picked it.
- **Offer our scent implementation.** Guarantees parity, removes a class of dispute, and reads
  extremely well in the README.
- **Propose start positions that suit our style.** Both are negotiable and most teams will accept
  the defaults without thinking about them.

The line we do not cross: nothing that weakens a rule, lowers a minimum, or disadvantages an
opponent without their informed agreement. The book permits exploiting undefined gaps; it does not
permit dishonesty, and a reputation for sharp practice in a small league is worth less than any
match.

### 3.6 Ambiguities that must be settled in writing

These gaps decide matches and are invisible until they do. Each is implemented as a config flag, so
we can play under either reading without a code change — but the reading must be agreed **before**
the first move, because with no referee a disagreement discovered mid-match is unresolvable, and
under M#35 a disputed result can void the match and score **0 for both teams**.

**Why only these.** Appendix F is the single source of truth for every quantitative value, and its
status column already settles all of them: *fixed* cannot change, *minimum* may only be raised,
*negotiable* is decided here and the printed figure is an example. So a value can never be in
conflict — only **mechanisms and timing** can, and that is exactly what this table covers. See
`CONTRADICTIONS.md` §0 for the full audit; several entries that once looked like contradictions
turned out to be reference-implementation defects or simply parameters awaiting a choice.

| # | Gap | Our proposed reading | Ref |
|---|---|---|---|
| N13 | **Scent field exchange.** The field is *transmitted* with each turn message, not sampled from a shared board. Does the sent field include the sender's current-turn deposit? | **Yes** — matching the reference implementation. Uncertainty survives anyway, since both peers then move again, leaving ≤5 candidates. | C-005 |
| N13b | **Decay model.** The book specifies multiplicative `(1−ρ)·τ + Δτ`; the reference simulator implements subtractive `τ − ρ`. At ρ=0.10 these give 0.81 and 0.80 from 0.9. | **The book's multiplicative model.** Appendix D says the book prevails over the repository. | C-007 |
| N13c | **Sealing the scent field.** The reference leaves `smell_grid` outside the commit, so a fabricated field passes audit undetected. | **Seal a digest of the emitted field** in the per-step payload. Proposed, not demanded — we seal ours regardless. | C-008 |
| N14 | **STAY and M#47.** STAY is always a legal action, so "no legal move" read literally can never occur. | Capture is defined by **adjacency**: all four orthogonal neighbours blocked, regardless of STAY. | C-006a |
| N15 | **M#46 timing.** Under commit-reveal, does a barrier capture a thief that simultaneously vacates the cell? | **No.** Positions are evaluated after both moves resolve. A barrier on a vacated cell does not capture. | C-006b |
| N16 | **The swap.** Cop and thief exchange cells in the same turn; neither ends on the other's square. | **Capture.** | C-006c |
| N18 | **Coordinate component order.** Appendix F negotiates *where* `(0,0)` sits and *what* the axes count from, but never whether a tuple is `(row, col)` or `(x, y)`. The published starts — `(0,0)` and `(3,3)` — are order-invariant, so the disagreement stays invisible until the first asymmetric coordinate. | **`(row, col)`, origin top-left, index from 0.** Confirm with a worked example, never a label: *"we read `[0,1]` as row 0, column 1 — one cell **East** of the cop's start."* | C-010 |
| N20 | **Sealing the barrier cell.** A placement costs the cop its move and therefore travels as `STAY`, so Ch. 5.3.1's `State‖Move‖Intent‖Nonce` cannot distinguish "stood still" from "walled (2,3)". The cell is declared openly (M#15) but nothing binds the declaration to the commitment. | **Seal the cell** as an optional `barrier_cell` key, present only on turns that place one. Proposed, not demanded: an opponent who declines simply omits it and both peers hash ordinary turns identically. | C-018 |
| N19 | **A series in which every sub-game ends in a technical loss** is arithmetically level at 0-0, so a literal reading of Table 17 pays both teams `tie_score` for a series neither played. | **No bonus unless at least one sub-game produced a real result.** Ch. 3.5 zeroes both sides on a technical loss precisely so that neither can win by timeout; paying a bonus for six of them inverts that. | C-013 |

Proposed clause, to be pasted into the agreement alongside the scent worked example:

> **Capture resolution.** Actions resolve simultaneously; positions are evaluated after both moves
> are applied. A barrier placed on a cell the thief has vacated does not capture. A thief whose four
> orthogonal neighbours are all blocked by barriers and/or board edges is captured, regardless of
> the availability of STAY. Two agents exchanging cells in the same turn counts as a capture.
> **Scent.** Each peer transmits its own scent field with every turn message, including that
> turn's deposit. Decay is multiplicative: `τ(t+1) = max(0, (1−ρ)·τ(t) + Δτ)`. Worked example at
> ρ = 0.10: a centre cell at 0.900 becomes **0.810** after one turn. Each peer seals a digest of its
> emitted field inside that step's commitment.

**The worked example is also intelligence.** If an opponent's reply gives 0.80 rather than 0.81,
they built on the reference simulator — which tells us in advance that they likely have no
implementation of M#46, M#47 or the swap case either (the reference implements none of them), and
that their scent field is probably unsealed. Ask the question early.

These readings are deliberately balanced rather than self-serving. N14 helps the cop, N15 helps the
thief, N16 helps the cop, N13 is neutral — and we play both roles, so a lopsided proposal would cost
us as often as it gained.

### 3.6b If the opponent refuses

Every negotiable position is a config flag, so disagreement costs a config change rather than a code
change. Four cases, and none of them threatens the project.

| Case | Example | What we do |
|---|---|---|
| **They prefer the other reading** | They want a barrier on a vacated cell to capture; they want the reference's subtractive decay | **Play their way.** Both options are implemented. Flip the flag, record it in the config JSON, play. |
| **They refuse something we wanted** | They will not seal their scent digest; they will not raise the barrier quota | **Play anyway.** We seal ours regardless — their field is then simply unverifiable, and we note that in the log. A quota of 14 is workable. |
| **They propose something illegal** | Barriers below 14, board below 7×7, a changed scoring table or decay rate | **Refuse.** Lowering an Appendix F minimum or altering a `fixed` value disqualifies **both** teams (M#12). Agreement is not a defence. |
| **Deadlock** | They will not play under any terms we can legally accept | **Play someone else.** Two counted matches are required and up to ten are permitted; one difficult team costs a fixture, nothing more. |

**The risk is not disagreement — it is discovering it mid-match.** A refused match costs nothing.
A *disputed* match scores 0 for both teams (M#35), which is why N2 refuses to start play on any
mismatch rather than reconciling afterwards.

**Tone.** Open with *"here is what we have implemented, and we are happy to play either way"* rather
than a list of demands. Most teams will not have considered these cases and will simply accept; the
ones who push back reveal how carefully they have read the book, which is useful either way.

### 3.7 Role split across the series

| ID | Requirement |
|---|---|
| N17 | Confirm explicitly how the `[number of sub-games]` sub-games divide between cop and thief. |

Do not assume. Our scoring analysis (`PRD_strategy_advanced.md` §2.3) assumes an even 3/3 split; a
fixed-role or uneven series changes the arithmetic completely, and with it where effort should go.

### 3.8 Per-match artefacts

| ID | Requirement |
|---|---|
| N10 | Each match gets its own `config_<game_id>_g<NN>.json`, committed to both repos (Appendix F §2.3, §2.4). |
| N11 | Config may change between matches, provided both sides agree each time. |
| N12 | Every match declares the commit hash actually played (M#53). |

---

## 4. Interface

```python
# core/protocol/negotiation.py
NegotiationResult = Literal["AGREED", "REFUSED_CONFIG_MISMATCH", "REFUSED_SCENT_MISMATCH"]

negotiate(
    proposed: Config,
    opponent_url: str,
    games_played: int,
) -> tuple[NegotiationResult, LockedAgreement]

# LockedAgreement
#   config_sha256: str
#   scent_model_sha256: str
#   our_games_played: int
#   their_games_played: int
#   our_commit: str
#   their_commit: str
#   agreed_at: datetime
```

---

## 5. Constraints

- Files ≤150 lines.
- Negotiation completes before the state machine leaves its initial state — no move may be
  computed against an unagreed configuration.
- All hashes use the canonical serialisation from PRD 6. A different serialiser here would produce
  a spurious mismatch and refuse a perfectly valid match.

---

## 6. Alternatives considered

| Decision | Alternative | Why rejected |
|---|---|---|
| Refuse on config mismatch | Warn and play anyway | Two different rule sets produce two different results and an unresolvable dispute |
| Worked numeric example in the scent exchange | Formula only | Symbolic agreement leaves interpretation open; a number does not |
| Declare game count honestly | Under-declare to maximise diversity reward | Both teams report every match to the lecturer, so the true count is already known. Disqualification for a few points is a catastrophic trade |
| Negotiate actively | Accept defaults always | The book explicitly invites legal exploitation of undefined space; declining is leaving points on the table |
| Per-match config file | One config for all matches | Appendix F §2.3 requires a distinct name per match so any match can be reconstructed |

---

## 7. Test scenarios

| # | Scenario | Expected |
|---|---|---|
| TN.1 | Identical configs both sides | `AGREED`; matching `config_sha256` |
| TN.2 | One value differs | `REFUSED_CONFIG_MISMATCH`; no move computed |
| TN.3 | Same values, different key order | Agreed — canonical serialisation is order-independent |
| TN.4 | Same values, CRLF vs LF | Agreed — `.gitattributes` pins LF (C-004) |
| TN.5 | Scent worked example differs | `REFUSED_SCENT_MISMATCH` |
| TN.6 | Opponent proposes barrier quota 20 | Accepted — raising a minimum is legal |
| TN.7 | Opponent proposes barrier quota 10 | Refused — below the Appendix F minimum (M#12) |
| TN.8 | Opponent proposes changing a *fixed* value | Refused |
| TN.9 | Declared game count vs `LEAGUE_LOG.md` | Identical |
| TN.10 | Dirty working tree at negotiation | Warning before the commit hash is declared |
| TN.11 | Move attempted before agreement | Blocked by the state machine |

---

## 8. Traceability

| Rule | Where |
|---|---|
| M#11 | §3.1 — byte-identical config, mismatch refuses the match |
| M#12 | §3.3 — minimums raised only |
| M#23 | §3.1 — scent model locked with a worked example |
| M#24, M#53 | §3.1 — Step-0 and commit hash exchanged |
| M#37, M#38 | §3.2 — honest game-count declaration |
| Ch. 3 §3.2 | §1 — the contract is a floor, not a ceiling |
| Appendix F §2 | §3.5 — per-match config naming and commit |

**TODO tasks:** 9.1.1 – 9.1.5
