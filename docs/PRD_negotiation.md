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

### 3.5 Per-match artefacts

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
