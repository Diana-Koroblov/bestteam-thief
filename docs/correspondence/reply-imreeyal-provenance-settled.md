# Reply to imreeyal — §2 corrected and the mechanism found, four dispositions accepted, and one disclosure of our own that is worse than any of them

Subject: bestteam ↔ imreeyal — §2 corrected to the wire (and it was our bug, not a
judgement call); §1/§3/§4/§5 accepted; and we filed no logs for either series

Hi imreeyal —

All five settled, four of them your way. §2 is corrected in our copy and we found the
mechanism that produced the wrong value, which is uglier than "we picked the wrong hash"
and worth putting on the record. And we owe you a disclosure that outranks every item in
your letter: **we have no logs for either series.**

**The score is untouched and was never in question: 40–60, 4–2 to imreeyal.**

---

## §2 — ACCEPTED, corrected, and it was never a judgement call on our side

You asked us to file `5bf3cfc…` for you in all six. Done:

    g01: 662d2866... -> 5bf3cfcce27a05a6c16263fa1314f8533bf1657f
    g03: 662d2866... -> 5bf3cfcce27a05a6c16263fa1314f8533bf1657f
    g05: 662d2866... -> 5bf3cfcce27a05a6c16263fa1314f8533bf1657f

Hash-neutral, checked before we wrote rather than after:

    recomputed consensus (before) : ff77bb1d6e31751a...  OK, matches the filed value
    recomputed consensus (after)  : ff77bb1d6e31751a...  UNCHANGED

**But we did not "hold" 662d2866 in any meaningful sense, and you should know why.** We
went looking for where our copy got it, expecting a reader pointed at the wrong field.
It was worse. At match time the line was:

    their_commit = str(getattr(args, "their_commit", "") or "")

That is the whole derivation. `--their-commit`, the command-line flag, and **nothing
else** — our filed column never touched the wire at any point. The value came from us
typing your heads in from this thread, one per terminal, matched to role on the
assumption that you run one repository per role the way we do. The perfect mirror of our
own alternation in that column is not evidence about your topology; it is our assumption
reflected back at us.

So your §2 is not us conceding a close reading. Your account is the only one with a
source behind it, and ours had none. It now reads from the identity block the two peers
actually exchange, with the flag left as an operator override.

**One precision, because this thread runs on them.** Our fixed reader takes your
`github_commit` from the **identity block in the handshake**, not from your **sealed
step-0 record**. For you the two agree, so nothing turns on it here — but your §2
argument was specifically "our file matches the wire, the only source either audit layer
can check", and the sealed record is the stronger of the two wires: it is inside the
commitment and cannot be revised afterwards, which the handshake block can. If you would
rather we read the sealed record, say so and we will move it. We would rather match the
source you are arguing from than the one that happened to be easier to reach.

## The disclosure: we filed no logs. Not for this series, not for the 16/08 one.

This is ours to volunteer and it is worse than anything in your letter.

Going to check your §2 against our own sealed records, we found there was nothing to
check it against. Our `--out` directory for 17/08 contains exactly one file:

    results/2026-08-17-friendly/
      result_bestteam-vs-imreeyal.json        <- and nothing else

No `log_*.json`, no `config_*.json`, no `declaration_*.json`. Same for 16/08. The cause
is that our reference-protocol path wrote the result artefact and only the result
artefact — while our own module docstring said *"the series is over and its logs are on
disk"* and our match-day document claimed the path *"files the four artefacts"*. Two
statements, both false in the same direction, so neither ever contradicted the other and
the gap survived two complete series.

Three consequences, stated plainly:

1. **Neither series can be replayed.** Both our copies name `log_bestteam-vs-imreeyal_
   g01.json` and friends in their `log_files` field. Those files were never written. If
   you have been treating that field as a pointer to something we hold, it is not.
2. **Our acceptance of §2 is not independent.** We are taking your sealed records on your
   word plus the bug we found on our own side, which corroborates you. That is enough for
   a friendly and we are content with it; it would not have been enough for a counted
   match, and we would rather say so than let you assume we cross-checked you.
3. **The `steps` disagreement in your §5 cannot be settled by either of us.** You count
   g02 at 20, we count 21. You declined to file the field and you were right, but your
   reasoning was that the counts live in the logs where the disagreement is trivia — and
   on our side they do not live anywhere.

**Fixed, today, and tested rather than asserted.** The path now writes the log, the
per-sub-game config snapshot and the declaration beside the result. The log carries both
sides' `{payload, nonce, commit}` records verbatim plus the live commits your turns
actually arrived with, so it re-audits off disk under the same rule that verified it
live — including the re-sealed-record attack, which self-consistency alone would pass.
The test that keeps it honest re-reads a written log and re-verifies it rather than
inspecting fields, because the DoD is the round trip and not the shape.

The two false sentences are corrected in place, each with what it cost written next to
it.

## §1 — ACCEPTED, and we will re-file alongside you

Nothing for us to change: our copy already carries the role-alternating table (police
`fc01a448` on 1/3/5, thief `57e3cdaf` on 2/4/6) and always has. We will re-file the
moment you tell us your reader fix has landed, so both copies land together as you
proposed. Ours is ready now and waiting on your word rather than the other way round.

## §3 — ACCEPTED

Your channel argument is right and better than the field we proposed: a friendly is
defined by never reaching the grader's inbox, not by a marker inside a file no grader
reads. Our `league` block stays on our own friendly copies as our own policy, and it
comes off our counted files — that commitment stands and is now in our counted checklist
rather than only in this thread. Yours stay template-pure and we will not ask again.

## §4 — ACCEPTED, no change either side

Process lifetimes against engagement windows, both honest, both outside every hash, both
now explained on the record. Your 1.1-second g03/g02 overlap needs no defence from our
side; our thief process being up from 11:15 and merely waiting needs none from yours.

## §5 — ACCEPTED

Declared-not-filed, per your convention. See the third consequence above for why we now
agree more strongly than we would have yesterday: it is the one field where two honest
conventions visibly disagree, and neither of us can currently produce the evidence that
would settle it.

---

So: your §1 reader, our §2 correction (done), and we re-file together on your signal. If
you would prefer we read your sealed step-0 record rather than your handshake block,
that is a one-line change and we will make it before the re-file rather than after.

And yes — we would like to play again. Ours has not got meaner yet, but it can now prove
what it did, which last week it could not.

— bestteam
   Itay Malich, Diana Koroblov
   itay.malich2@gmail.com
