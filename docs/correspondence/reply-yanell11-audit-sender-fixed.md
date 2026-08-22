Subject: bestteam <-> yanell11 — found and fixed the sub-game 1/3 cause, question on sub-game 6

Hi Nell, Yanal —

Both our doors are back up and read 406 right now. Found real causes for both
things you flagged, verified from our own filed logs rather than guessed —
here's what we found before we relaunch.

## Sub-games 1 and 3: found it, fixed it

Our own log shows sub-games 1 and 3 actually played to completion and we
verified your reveal successfully on both — the game itself never desynced.
What failed was our outbound audit push to you, twice, both times with the
same rejection: `expected an audit from 'police'`.

Root cause: our `submit_audit` push was sending `"sender": "cop"` — our own
internal role name — instead of the wire vocabulary's `"police"`. We'd already
fixed this exact translation for every *turn* message after an earlier
incident, but missed the closing audit push, which builds its payload in a
different function. Sub-games 2/4/6 (our thief's) were never affected, since
"thief" needs no translation either way — consistent with it only being your
cop-facing sub-games that failed.

Fixed and shipped. This should be the entire explanation for "sub-game 1 timed
out" from your side — the match was fine, only our own reveal never landed.

## Sub-game 6: here's exactly what our two logs show, not a guess

Turn by turn, from both sides' own sealed records:

```
step 30  your cop moves N to (0,1)      - now adjacent to our thief at (0,0)
step 31  your cop places a barrier at (1,1), stays at (0,1)
step 32  your cop moves W onto (0,0)     - the same cell our thief occupies
```

That's a direct position-overlap capture (the cop walked onto the thief's
cell), not a barrier enclosure. Our own `claim_response` for that turn names
the rule explicitly: `"cop occupies our cell"` — not a barrier claim at all,
and not Rule 47's self-concession either (our thief's two open neighbours,
(0,1) and (1,0), were never walled at that point).

So "our barriers never captured (0,0)" is true on your side, but we never
claimed a barrier capture there — we claimed the simpler thing: you were
standing where we were. Worth checking on your side rather than us assuming
either way: does your audit verifier recognise direct position-overlap as a
valid capture, separate from barrier-enclosure? If it only checks the barrier
condition, that would read exactly like what you saw — a concession your
verifier can't justify from barriers alone, even though the capture itself was
real and simple.

## Ready when you are

Both doors live, fresh processes, the sender fix is in. Say go and we'll
relaunch in parallel with you, sequenced properly this time.

— bestteam
   Itay Malich, Diana Koroblov
   itay.malich2@gmail.com
