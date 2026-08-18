# The walker: no hotfix, no code change — a command-line argument, and the field that would have shown you is the one we file empty

Subject: bestteam ↔ imreeyal — plainly: nothing was hotfixed. The walker difference was
one CLI argument, 3-3 against alternating. Re-file ACKED; artefact fix shipped and heads
RE-DECLARED to 22e41379 / 67e859b6

Hi imreeyal —

Taking your two in your order, and the answer to the second one is short.

## Your corrected re-file: ACKED — send it

Understood, and thank you for catching it on your own side and saying so before we did.
Disregarding the copy in our inbox. One send, flagged as the correction; we will diff it
against our file and confirm `ff77bb1d` in this thread.

For what it is worth, your root cause is the better-stated version of ours: **the configured
pairing names the series, and an inbound identity is adopted only when it agrees.** A
stranger's record renaming a series is the same family as a typed commit outranking a sealed
one — the record that should have been evidence got treated as authority. We have no
criticism to offer and one thing to admire: you found it in your own artefact after a window
you won.

## The walker: no hotfix. It was an argument.

Plainly, because you asked plainly and because a timing story would be worse than useless:

**Nothing was hotfixed. No code changed. No config changed. Nothing was rebuilt, patched or
reverted between the two windows.** The code that refused 18 of 18 this morning is
byte-identical to the code that played a clean six tonight.

What changed is a **command-line argument on the two `play` invocations**:

    this morning   --role-split 3-3
    tonight        --role-split 1-1-1-1-1-1

Our agreed term is alternating — bestteam cop on odds. `3-3` is blocks: cop on 1-2-3, thief
on 4-5-6. We armed with the wrong one. It is operator error at the keyboard, not a defect in
the walker, and the walker was doing exactly what it was told.

**Your receipts prove it better than our word does.** Blocks and alternating coincide on
precisely two sub-games — 1 (cop under both) and 4 (thief under both). Those are the two that
settled this morning. Every other window disagreed by construction, which is why the refusals
were not intermittent but total, and why 03 and 06 never engaged at all.

**Verify us rather than believe us.** Both windows were played on the pair we declared, and
both clones sat clean at it — zero modified files, matching `origin/itay` exactly:

    cop    51dbf196b45b659e9ff0b6b0cd81d33e6ac497ff   (bestteam-cop,   origin/itay)
    thief  8ecb84892371f6e2ca5ca881e6f152bdbceeba78   (bestteam-thief, origin/itay)

There was no local delta to push, because there was no local delta. Fetch either head and you
have the bytes that played both windows — this morning's and tonight's alike.

**That pair is now superseded, deliberately, by the fix below — see the re-declaration.**

## The part that is genuinely our defect, and your question is the proof of it

You should not have had to ask.

The filed config artefact has a `role_split` field precisely so a reader can see the plan a
sub-game was played under. **Ours files it as an empty string** — the gap we disclosed to you
after the 2200 window, and which you folded into this window's four checks. It is still
unfixed on the wire, so it filed empty again tonight, in the very artefacts you were reading
when you had to write and ask us what changed.

Had it been populated, this morning's artefact would read `3-3`, tonight's would read
`1-1-1-1-1-1`, and the difference would have been visible in a diff without a letter. That is
now our strongest argument for shipping it, and it is a better one than "an opponent
mentioned it".

## Done, not promised: the artefact fix is shipped, and this is the re-declaration

**1. The artefact fix is pushed.** `role_split` and `scent_model_digest` are populated in the
filed config snapshot. The scent value is the one we **declare on the wire**, resolved the
same way our handshake resolves it — a lookup keyed on the negotiated `pheromones.decay_model`
— so the artefact records the number we actually sent rather than a second internal one.
Green on our full suite, 1803 tests, with lint, file-size, secret-scan and split-repository
gates clear.

**2. Re-declared, and this line is that re-declaration.** New pair, live on `origin/itay`,
verified against the remote rather than against our clones:

    cop    22e4137970478a4d9890e9fd2f3798b0f95a3b0c   (bestteam-cop,   origin/itay)
    thief  67e859b66c227de3af7e50bc1013faeffa2a6d35   (bestteam-thief, origin/itay)

Nothing lands after this line. The superseded pair `51dbf196` / `8ecb8489` still resolves and
still descends correctly if you want to re-verify either of today's windows against it.

**3. The counted plays only what resolves on `origin/itay`.** Agreed without qualification —
posted == played == sealed. Both of today's windows already met that bar; the counted will
meet it with the artefact proving the plan rather than us asserting it.

We are not asking for the operator error to be treated as anything other than what it is. It
cost a window, it cost you twenty minutes of refusals, and the guard that caught it was
yours. The one thing we would ask you to weigh is that it was recoverable in a friendly and
would have been unrecoverable in the counted — which is the argument you made to us for
having this friendly at all, arriving back at our door.

Your pair, unchanged and pinned: cop `bdbce8a2…` / thief `aa9c5c0b…`.

— bestteam
   Itay Malich, Diana Koroblov
   itay.malich2@gmail.com
