# League Log

Every counted match, one row. This is the evidence base for the honest
game-count declaration required at the start of each match (M#37) — a false
declaration disqualifies the whole project (M#38).

**Rules that govern this table**

| Rule | Constraint |
|---|---|
| M#31 | Minimum **2** counted matches vs. different teams to be eligible for any grade |
| F | Maximum **10** counted matches per team |
| M#52 | **One** counted match per opponent. Warm-ups are uncounted and allowed |
| M#35 | Both teams must send their own report. A missing or contradictory report voids the match and scores **0 for both** |
| M#36 | Mutual log audit must complete **before** agreeing the result |
| M#53 | The exact commit hash played is declared per match and recorded here |

---

## Counted matches

| # | Date | Opponent team | Our role | Sub-games | Our score | Their score | Audit | Our report sent | Theirs confirmed | Commit hash | Config file |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-08-18 | imreeyal | alternating, cop on odds | 6/6 | 40 | 60 | ☑ | ☑ | ☑ | cop 22e41379 / thief 67e859b6 | config_bestteam-vs-imreeyal_g01-06.json (cca1243e) |
| 2 | | | | /6 | | | ☐ | ☐ | ☐ | | |
| 3 | | | | /6 | | | ☐ | ☐ | ☐ | | |
| 4 | | | | /6 | | | ☐ | ☐ | ☐ | | |
| 5 | | | | /6 | | | ☐ | ☐ | ☐ | | |
| 6 | | | | /6 | | | ☐ | ☐ | ☐ | | |
| 7 | | | | /6 | | | ☐ | ☐ | ☐ | | |
| 8 | | | | /6 | | | ☐ | ☐ | ☐ | | |

**Counted matches so far: 1** ← this is the number declared to every new opponent (M#37)

> ⚠️ **This table is parsed, not just read.** `core/shared/league_log.py` counts the rows whose
> **Opponent team** cell is filled and refuses to hand the handshake a number when that count
> disagrees with the total above — so adding a row without updating the line stops the next
> negotiation with an error instead of declaring a wrong figure (M#38). The column is located by
> name, so it may be reordered; the heading `## Counted matches` may not be renamed. Warm-ups and
> booked fixtures live under their own headings and are never counted.

---

## Warm-up matches (uncounted)

Permitted and recommended: they shake out protocol bugs and let you profile an
opponent's hint style and barrier habits before the match that counts (M#52).

| Date | Opponent | Purpose | What we learned |
|---|---|---|---|
| | | | |

---

## Scheduling pipeline

Booked slots. **This table is the binding constraint on the final grade** —
league position spans 25 grade points, and you cannot play teams you never
contacted.

| Opponent team | Contact | Status | Agreed date | Our role | Notes |
|---|---|---|---|---|---|
| vibecode | agentsorch@gmail.com (Ron Marom, Amit Kuperminz) | ☑ contacted / ☑ agreed / ☐ played | friendly, hour TBD by us | cop on 1/3/5 | ALL SETTLED, nothing left to negotiate. a284082d; 81ebee59 chebyshev + merge-by-max, 0.800/0.500/0.200 on the wire; game_uid d570f249; config d16427a2 diffed key-by-key against their file — 36/36 identical, and their file produces a284082d through OUR loader. Payload re-hashed as supplied (proved their side). Public repos = counted-T precondition only. Our heads 6f5a7ed1 / a671fe05, clean and published. Open: name T; optionally verify their bundles at c956604a / da8d3b54 |
| | | ☐ contacted / ☐ agreed / ☐ played | | | |
| | | ☐ contacted / ☐ agreed / ☐ played | | | |
| | | ☐ contacted / ☐ agreed / ☐ played | | | |
| | | ☐ contacted / ☐ agreed / ☐ played | | | |
| | | ☐ contacted / ☐ agreed / ☐ played | | | |

---

## Per-match checklist

Copy this block for each counted match.

```markdown
### Match N — <opponent> — <date>

Before
- [ ] Shared config negotiated; config_sha256 verified identical both sides (M#11)
- [ ] Scent model + worked numeric example exchanged and hashed (M#23)
- [ ] Counted-games-so-far declared honestly to the opponent (M#37)
- [ ] Step-0 declarations exchanged, including github_commit (M#24, M#53)
- [ ] Working tree clean; commit hash recorded below
- [ ] Any negotiated rule extension written into the config JSON

After
- [ ] Mutual log audit passed, all nonces revealed (M#36)
- [ ] Result agreed with the opponent
- [ ] Our result JSON sent to rmisegal+uoh26finalgame@gmail.com (M#51)
- [ ] Opponent CONFIRMED they sent theirs (M#35 — a gap here scores 0 for BOTH)
- [ ] config JSON + match log committed to both repos
- [ ] Row added to the table above

Commit hash: ________________
Outcome: ________________
```
