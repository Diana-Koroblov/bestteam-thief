# Reply to imreeyal — rule 46/47 conceded and fixed, and two corrections

Subject: bestteam ↔ imreeyal — rules 46 and 47 wired, terms accepted; your addendum
was right and your fix instruction was one rule short

Hi imreeyal —

Thank you for both messages, and particularly for the addendum. You read our published
heads and came back with a more precise root cause than the one you started with; that
saved us from fixing the wrong thing. Two corrections below, one of them load-bearing.

## 1. g02 was a capture. Conceded, on the record.

No dispute, no re-file. Your cop walled (5,0) and (6,1); (6,0) is a corner, the other
two sides are board edge, and our thief sat imprisoned from step 20. Book-true series
is 60–40, 4–2 to imreeyal. It goes in our log that way.

**Correction to your first message's diagnosis.** Our check does *not* require four
walls, and corner geometry was never the gap. `is_immobilised` asks
`board.is_passable` about each orthogonal neighbour, and that function treats a board
edge and a barrier identically — a cornered thief needs two walls, not four, and our
unit tests have covered that case since it was written. We re-ran it against your exact
g02 position before touching anything:

    M#47 corner cage (6,0), walls {(5,0),(6,1)}:
       is_immobilised  -> True
       rules.sealed_in -> True
       rules.verdict   -> CAPTURE  "thief sealed in at (6, 0) (M#47)"

So the honest answer to "why did your D-item test miss it" is not corner geometry. It
is that **no test asserted the compat path concedes anything**, because the compat path
had no concession to assert. Your addendum found exactly that.

## 2. Your fix instruction would have left rule 46 broken.

This is the one that matters, and we would have shipped a half-fix if we had followed
it literally.

You wrote: *"Wire the compat path to the verdict your native path already trusts."* We
checked the verdict before wiring anything to it. It does not implement rule 46:

    M#46 barrier ON thief's cell (3,3), all four exits open:
       thief in barriers -> True
       is_immobilised    -> False
       rules.verdict     -> None

M#46 lived only in `BarrierManager._captures()` — the **placement** path. It fires for
the cop laying the wall down and is unreachable by anything judging from a state. So
`verdict()` returned None for a thief standing on a barriered cell, which means your
characterisation of our native path as "already correct" is generous: it concedes rule
47 and would have denied rule 46 just as the compat path did. You were right that rule
46 is the more common wall form; it was also the more broken one.

So the fix landed in two places, not one:

- **`Rules.thief_is_trapped(state)`** — new, and it states M#46 and M#47 as properties
  of a *state*. Both are decidable from the thief's own cell and the barriers alone,
  with no knowledge of where the cop stands — which is precisely what makes them
  answerable on a wire where a peer never learns the opponent's position. M#46 is
  deliberately not gated on `stay_counts_as_move`: that flag settles how M#47 reads a
  legal STAY (our C-006a), and a wall on your own cell captures under either reading.
  `verdict()` now routes through it, so the native path is fixed by the same change.

- **`core/compat/turns.py`** now calls it — and concedes **whether or not a claim
  arrived**. That was the second half of why g02 went unconceded: placing a barrier
  costs the cop its move, our `_claim` correctly stays silent on a STAY, so nobody ever
  asks on the turn the cage closes. A peer that only answers claims will never concede
  a cage no matter how correct its rules engine is. The concession rides on
  `claim_response.caught` — the only channel this wire has for it — with an additive
  `rule` key naming which rule fired, so a conceded capture is distinguishable from a
  mis-answered claim.

Seven new tests, including your g02 position replayed as an arriving barrier. Full
suite green.

## 3. Terms accepted, all four.

1. Rule 46 — a barrier arriving on our thief's cell concedes, sealed, that turn. Done.
2. Rule 47 — imprisonment concedes, on the movement reading (walls, edges, or the cop's
   cell). Done.
3. Clean, pushed, declared head for any T. Done, and made mechanical — see below.
4. One more friendly before any counted talk, verified together from the logs. Yes.
   Our T is any time; name it and we will be up 5 minutes early.

## 4. The commit — your theory is wrong, and the truth is less fixable.

`55ddff06…` is **not** a local commit sitting unpushed on top of the published heads.
It is the HEAD of `p2p-chase`, our development tree, which **has no git remote at all**
and never has. The published repos carry separate squashed histories — `bestteam-cop`'s
`4ea3a51` is literally *"chore: take the p2p-chase tree as authoritative"*. So there is
nothing to push, and tonight's declaration cannot heal retroactively. We are telling you
this rather than quietly pushing something, because a hash that resolves is worth
nothing if it is not the hash that played.

What actually happened is duller than a code fault: both processes were launched from
the wrong directory. The code that played was content-identical to the published heads,
but the hash we sealed named a tree only we can see. That is our fault and it wasted
three of your windows.

It is now a pre-flight rather than a procedure. Every reference-protocol run prints the
head it is about to declare and **refuses to arm** when that head is dirty, sits in a
clone with no remote, or is committed but on no remote branch:

    declared head   : 4ea3a51f93675004bc8facbbd952ef6562719db9  (published on origin/main)

    refusing to arm: C:\...\p2p-chase has no git remote, so its commits are local by
    construction and 55ddff06 can never resolve for an opponent (M#53).
      Launch each role from ITS OWN published repository, not the development tree.

There is an `--allow-local-head` escape hatch, and it exists only for drills against
ourselves. It cannot be reached by accident in a match against you: the refusal is the
default. Five tests, against real throwaway clones rather than a mocked git, because a
stub would only have asserted that we wrote the strings we meant to write — which is
exactly what passed while three windows declared an unfetchable hash.

## 5. The double mail — rule accepted, mechanism found, not yet fixed.

Accepted without reservation: one report per series; if a filed artefact turns out
corrupted, the move is STOP and agree the correction in writing before any second send.
Two filed results from one team is the shape rule 35 punishes, and you are right that
last night was the only time that lesson is free.

We found the mechanism and we are not going to pretend it is fixed. Our filer merges its
rows into any existing `result_<game_id>.json` in `--out`, and that filename is keyed on
**the two group names only** — so a previous series against you is indistinguishable
from the other role process's half of the current one. Our cop process finished first,
merged its fresh g1/g3/g5 over a previous series' g2/g4/g6, reached six rows, passed the
completeness gate and mailed. The thief process then filed the real rows, which is the
correction you received.

The clean fix is a per-series token both our role processes carry and the merge refuses
to cross. We have not built it yet; we would rather tell you it is open than ship a
timestamp heuristic that breaks the legitimate two-process merge. Until it is in, we
will run each series into its own empty `--out` directory, which closes it operationally.

Also noted: your commit truncated to 8 characters in our file. That is what was handed
to us on the command line and we passed it straight through. We will carry the full 40.

## 6. Where that leaves us

Your gate items 1 and 2 are closed and tested. Item 3 is closed and now mechanically
enforced. Item 4 is yours to schedule — name a T and we will bring both roles up from
the published repos, post both heads in the thread before we arm, and verify from the
logs together afterwards: a sealed thief emits the caught-final, a barrier on the cell
concedes, zero outcome_mismatch events.

Thank you for the physics result too — zero refusals on 105 of 105 frames is the first
clean bill either of us has had on that channel, and it only exists because you built a
checker and pointed it at us.

— bestteam
   itay.malich2@gmail.com
