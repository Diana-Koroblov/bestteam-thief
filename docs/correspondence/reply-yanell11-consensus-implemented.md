# Reply to yanell11 — consensus envelope built to your spec, and which door to use

Subject: bestteam <-> yanell11 — series_consensus implemented, one endpoint answer, ready to arm

Hi Nell, Yanal —

Thanks for the exact spec — that's exactly what we needed, not a description to
reverse-engineer. Built and tested against it, not guessed at.

## Your endpoint question, answered

Send it to **our thief door**: `https://itinerary-single-overjoyed.ngrok-free.dev/mcp`.

Reasoning, since you asked in good faith and deserve the actual reason rather
than just an answer: we run two processes too. Our cop plays 1/3/5 and exits
its own loop once sub-game 5 ends — the series isn't over yet, so it stays up,
but it never sees all six rows and never sends a report. Our thief plays 2/4/6;
after sub-game 6 it merges its three rows with the three our cop already filed
to disk, and *that* merge — the one that actually reaches six — is what
triggers our real send. So our thief process is the only one of our two that
will ever be looking at `inboxes.consensus` at the moment that matters. If your
own architecture is the mirror of that (your cop plays your last sub-game, 6,
against our thief), send it there.

One thing we noticed while implementing this and want to flag rather than
assume: you gave us one endpoint, not two, even though you sent two separate
repo URLs. If that's one process serving both roles internally, ignore
everything above — there's only one door regardless of who plays last, and
you can send it there. If you do have a second address and we simply weren't
given it, we need it, or our consensus push and any per-role handshake after
sub-game 3 has nowhere correct to land on your side either.

## What we built, to your exact shape

```
{"sender": "thief", "records": [], "result_claim": "series_consensus",
 "consensus_sha": "<our own mutual_agreement.sha256, unmodified>"}
```

Sent via `submit_audit` (arg `payload`), once, right after our merge produces
all six rows and before we mail or file our own send decision. Routed on
receipt to a queue that only this envelope ever touches — never the one a real
sub-game's reveal lands in — so the two can never be read as each other
regardless of arrival order.

We wait 20s for yours back. If nothing arrives we file the series exactly as
we would anyway (a peer who hasn't implemented this yet is a peer who hasn't,
not a fault); if something does, we compare it to our own hash and log
MATCH/MISMATCH. This is a local comparison on our side only — we are not
folding `peer_sha256` into the artefact's schema itself, since that isn't a
field either the standard report shape or the lecturer's tooling expects, and
we'd rather not carry a second report shape for one pairing.

Repos: public now, thanks. One thing worth flagging rather than silently
patching around: `cda33cda...` does resolve, but it's an ancestor of both your
current `main` branches, not their tip — your two repos have moved to
`d0b26e8e...` (cop) and `45a2cb63...` (thief) since you sent us that hash.
Normal if you've kept pushing, but per the same rule your own spec would apply
to us: resend whichever commit you're actually running before we arm, and
we'll do the same if we push again first.

Fresh heads after this change:
```
cop repo    a5a1530a6b1841f81b066273745e2d50274b321e -> 322e82173e83b6da24b0a130e3dc343c6b3758a9
thief repo  8c78842eb49954ee3d56f371e554d71e6572819b -> 0c76074e44810968d0b4a67b5a68cbc9da7b2faf
```

Bringing our process up now. Say go.

— bestteam
   Itay Malich, Diana Koroblov
   itay.malich2@gmail.com
