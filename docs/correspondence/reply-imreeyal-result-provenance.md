# Draft — to imreeyal: five provenance fields in your copy of `result_bestteam-vs-imreeyal.json`

Send from **itay.malich2@gmail.com**. Nothing here disputes the score. Do not send until
someone has re-read §3 — it is the only item with a deadline attached.

Subject: bestteam ↔ imreeyal 17/08 friendly — the result is agreed, five provenance fields
in your copy are not

Hi imreeyal —

Thanks for the copy of your result file. **The outcome is agreed and we are not disputing
it**: 60–40 to you, 4–2, and your `mutual_agreement.sha256` `ff77bb1d6e31…0bdc9`
reproduces exactly from our copy. We re-derived it independently over the five symmetric
row keys (`sub_game_number`, `roles`, `result`, `winner_group`, `score`) plus the five
aggregate keys, spaced-form JSON, sign-then-insert. Byte-equal. Your cop beat our cop
fairly and we have no argument with the series.

What follows is entirely about **provenance fields, which sit outside the consensus hash**
— which is exactly why both our copies can say `confirmed: true` while disagreeing
underneath. Five items, one of which we think matters to you as much as to us.

---

## 1. Our commits are recorded as `unknown` in all six sub-games

Your rows carry `github_commit.bestteam: "unknown"` for g01–g06.

We declared both heads in the Step-0 identity block at every handshake, and in writing in
the invitation before the match. They are pushed and fetchable:

    cop     fc01a448101a8a9c748dc9d48468bb633487e042    Diana-Koroblov/bestteam-cop, origin/main
    thief   57e3cdafad031ed2cf8cfc0df3052b97ce9af837    Diana-Koroblov/bestteam-thief, origin/main

We field two repositories and two processes, so the correct value **alternates with the
role**:

| Sub-game | Our role | `github_commit.bestteam` |
|---|---|---|
| 1, 3, 5 | police | `fc01a448101a8a9c748dc9d48468bb633487e042` |
| 2, 4, 6 | thief | `57e3cdafad031ed2cf8cfc0df3052b97ce9af837` |

This is the third filing that records `unknown` against us and we would rather it not become
the league's record of who we are. For what it is worth, the cause on our side was real and
is now fixed: our own report builder read the commit from the process working directory
while the declaration read it from the repository root, so a run launched from the wrong
directory declared one head and filed another. Both now come from the single declared
value. If your generator reads the commit from somewhere other than the identity block,
that may be the same class of bug.

## 2. Your own thief commit is missing from your copy

Your rows carry `5bf3cfcce27a05a6c16263fa1314f8533bf1657f` for **all six** sub-games. That
is your cop repository. From your declared identity blocks we recorded:

| Sub-game | Your role | `github_commit.imreeyal` |
|---|---|---|
| 1, 3, 5 | thief | `662d28660effd0968ce67cf6e7cbe668e70e7af5` |
| 2, 4, 6 | police | `5bf3cfcce27a05a6c16263fa1314f8533bf1657f` |

We have filed those two values against you. If we have your thief head wrong, tell us and we
will correct our copy — we would rather match you than be right on our own.

## 3. Your copy does not say the series was a friendly — please add this one before filing

This is the item with consequences. Our copy carries a top-level block:

```json
"league": {
  "authority": "book App. E rule 52 - one counted series per pairing",
  "counted": false,
  "reason": "friendly"
}
```

Yours has no equivalent. A copy that says nothing about whether it counts can be ingested as
a **counted** series, and under App. E rule 52 there is only one counted series per pairing —
so an uncounted afternoon would silently spend the slot, for both of us, on a friendly. Our
`LEAGUE_LOG` records **0 counted matches** and we intend to keep declaring 0 (M#37), which
your copy as it stands would contradict.

We are not asking you to adopt our field names. Any marker your grader recognises is fine;
what matters is that the artefact says it does not count.

## 4. The timestamps do not describe how the series was played

Your rows show six strictly sequential sub-games of about 116 s (when we were police) and
176 s (when we were thief), each starting within milliseconds of the previous one ending.

We played the six as **two concurrent streams**, one per role process, on two tunnels:

    police stream   g01 11:14:43 → 11:21:23 → g03 → 11:24:56 → g05 → 11:29:47
    thief  stream   g02 11:15:12 → 11:23:00 → g04 → 11:27:52 → g06 → 11:32:44

So g01 and g02 overlap by about six minutes, and real durations ran 213–468 s. Your own
sequence also does not close on itself: your g03 starts at `11:23:04.842536`, which is 1.1 s
**before** your g02 ends at `11:23:05.947349`. We mention it because a grader diffing the two
copies will see it, and it is easier to explain now than later.

## 5. `steps` is absent from your rows

Ours records the step count each sub-game reached: 34, 21, 34, 35, 35, 35 — with g02 at 21
being your capture. Not required by the schema as far as we can tell, but it is the one field
that makes a result readable against the logs without opening them.

---

## What we are not asking for

- **No change to any score, role, winner or the aggregate.** All agreed.
- **No re-derivation of the hash.** `ff77bb1d…` is correct and stays correct — every field
  above is outside its scope.
- **`games_played_including_this`** we make no complaint about. Yours reads
  `{bestteam: 0, imreeyal: 6}` and so does ours: 0 is our honest counted total, since both
  our series against you were friendlies.

If you re-file, we will re-file alongside you so the two copies land together. If you would
rather leave items 1, 2, 4 and 5 as they are, we can live with that — but we would ask you
not to skip **§3**, because that one costs us both a counted slot we cannot get back.

Happy to play again once we have both fixed our cops.

— Itay, bestteam
itay.malich2@gmail.com
