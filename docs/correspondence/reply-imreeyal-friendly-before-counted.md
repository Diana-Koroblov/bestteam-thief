# Request: one more friendly before the counted — to execute the item 3 fix once before it cannot be redone

Subject: bestteam ↔ imreeyal — confirms stand, heads stand; asking for ONE more friendly
before the counted, because our item 3 fix has never run in a live match

Hi imreeyal —

Everything in our checklist reply stands: the ten confirms, the artefacts line (14), and the
frozen pair

    cop    d72b1f765effd0edb96be632a132ec56e06db337   (bestteam-cop,   origin/itay)
    thief  11f616e2dcf13cc8b5d7688824500d928f3e1eab   (bestteam-thief, origin/itay)

One ask before you lock the counted T, and we would rather make it explicitly than
manoeuvre for it.

## What we want, and why

**One more friendly, on the same terms, into its own fresh `--out`.**

The reason is item 3. We found that defect by auditing for your checklist, and we fixed it —
`games_played_including_this` now files each side's declaration plus one on a counted
series, gated so a friendly still counts for nobody. It is pinned by tests.

But it has **never executed in a live match.** Every test of it is our own, against our own
fixtures. The first time that code path runs against a real peer, producing a real artefact
that a real grader reads, would be the counted series — the one series that by your own
item 2 can never be run again.

That is the wrong place to discover we fixed it wrongly. A friendly is the right place, and
it is what friendlies are for. We are not asking to re-open anything settled; we are asking
to execute one corrected code path once, under real conditions, before it becomes
irreversible.

## What we would check in the thread, and then be done

Two lines, no more:

1. **`games_played_including_this` on a friendly reads bestteam 0 / imreeyal 6** — unchanged,
   because a friendly counts for nobody. If it reads 1 / 7 our gate is wrong in the other
   direction and we would rather see that here.
2. **`diversity_reward_applied` is all-false on a friendly**, as it correctly was on the 2200
   file, so we know the `counted` gate is the thing actually driving both fields.

If both read as expected, we are ready for the counted immediately after — same session if
you have the time, and we will not ask for anything else.

## What is unchanged

Same terms (`a284082d` / `81ebee59` / `229ae648` / `020947da`), same role split, your thief
opens g01, same T protocol including the identity probe. Same frozen heads above — the
friendly and the counted would both seal from that pair, and nothing lands between them.
Fresh empty `--out` for each, per item 6.

And to be plain about our own interest: we have played **zero** counted matches, we need two
to pass at all, and you are the pairing furthest along. We are not slow-walking the counted.
We want it locked, and we want it to be the one where nothing surprises either of us.

If you would rather skip straight to the counted, say so and we will arm on your word — the
confirms are unconditional either way.

— bestteam
   Itay Malich, Diana Koroblov
   itay.malich2@gmail.com
