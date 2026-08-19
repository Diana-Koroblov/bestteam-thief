# 16:30 accepted, your arithmetic is right, and here is the exact order of the four steps before we arm

<!--
NOT PART OF THE MESSAGE. Stripped from the .txt.

  Send from itay.malich2@gmail.com to nissimderi123@gmail.com. SHORT ON PURPOSE.

  ⚠️ HEADS: da8b5cc4 / fa9147d3 are current as written. If ship.py runs before
  this is sent, re-derive both and update section 3 AND the subject line.

  Operational note for us, not them: our doors go up in HOLD MODE first
  (`peer --role <r> --serve --tunnel`). That binds the reserved domain, so both
  hold-mode processes must be STOPPED before `play --tunnel` can bind the same
  domains. See docs/RUNBOOK_nis-yar1.md.

  Regenerate after any edit:
    uv run python <scratchpad>/md2txt.py docs/correspondence/reply-nis-yar1-confirmed-1630.md
-->

Subject: Re: bestteam ↔ nis-yar1 — 16:30 today confirmed. Role sentence locked, heads
da8b5cc4 / fa9147d3, and the four-step order before either side arms

Hi Nissim, Yarden —

**16:30 Israel time today, 2026-08-19, confirmed.** Everything else below is confirmation and
one paragraph of sequencing so the first attempt succeeds.

## 1. The turn wait — thank you, and your arithmetic is right

1,200 s against a 35 × 30 = 1,050 s theoretical maximum, 150 s of margin. That is exactly the
number we were asking about and you did the sum yourself rather than taking ours. Ours is 900 s
and we are raising it to 1,200 s to match, so neither of us is the shorter fuse.

That closes the only open item either of us had.

## 2. The role sentence — locked, verbatim

> Alternating. bestteam plays cop on sub-games 1, 3 and 5 and thief on 2, 4 and 6. nis-yar1
> plays thief on 1, 3 and 5 and cop on 2, 4 and 6. The thief moves first in every sub-game, so
> nis-yar1 opens sub-game 1.

Locked. Our `github_commit` will therefore be our cop repository's head on 1/3/5 and our thief
repository's head on 2/4/6 — one hash across all six rows would be wrong in half of them.

## 3. Our heads at arming

```
cop     da8b5cc41daccb24bdc2aad31105553cca72c7cd   bestteam-cop,   branch itay
thief   fa9147d31cd1103569ae62485874c3a213ef24e1   bestteam-thief, branch itay
```

Both clean, both public, both resolving to an anonymous client. Run `ls-remote` on them rather
than taking this line for it. If either moves before 16:30 you get the new pair in this thread
first, and nothing lands after that post.

Your pair is filed: `7633fbc8…` / `3f2d0216…`.

## 4. The bundles — yes please, and the offer is better than what we asked for

Accepted for the counted series, on your timing. A bundle verifies the head hash and the whole
tree offline with no dependency on your account settings, which is stronger than the anonymous
`GET` we originally asked for — we would take one for a counted series even from a team whose
repositories were public.

Nothing about them gates today. The warm-up files nothing with anybody.

## 5. The order of the four steps before we arm

Worth writing down, because our doors and yours come up in opposite orders and that is the one
thing that can waste the 16:30 slot.

```
16:10   we bring both our doors up and post one line here saying "up"
16:15   you open your two Cloudflare tunnels and post both fresh URLs
        plus your two hashes re-confirmed
16:20   we probe both of yours, you probe both of ours, read-only, no window spent
16:30   we arm and play — six windows, strictly sequential
```

Two notes on that:

**We will say "up" in writing rather than let you infer it from a probe.** Until that line
appears, our two addresses returning `404 / ERR_NGROK_3200` means only that our processes are
not running yet — the domains are reserved and the ngrok edge is answering, so it is not a
fault and there is nothing to chase.

**When you post your URLs, please label which is the cop door and which is the thief door.**
Our cop dials your thief and our thief dials your cop, and a pair posted the other way round
produces a role collision that looks exactly like an intermittent network fault. We have had
posted pairs come back swapped before, which is why we probe rather than assume.

## 6. On the day

- Both our processes stay up for all six windows, idle ones included. Each sits idle for half
  the series and still has to answer, because the next window arrives at it.
- A fresh `negotiate` opens every sub-game, carrying the identical signed terms.
- `submit_audit` is pushed both ways at every sub-game end — we call yours as an independent
  outbound call and separately collect yours; neither is a reply to the other.
- Our sub-games against a comparable opponent ran about 80 seconds each, so a clean six of six
  should take well under fifteen minutes end to end.
- **We do not accept a technical win we did not earn on the board.** If our endpoint drops or
  our process dies, tell us and we replay that sub-game. We ask the same of you, and with
  1,200 s on both sides neither of us should be calling the other absent by accident.

Reports for the warm-up go to the two of us only — yours to `itay.malich2@gmail.com`, ours to
`nissimderi123@gmail.com`. The lecturer is never involved in an uncounted game.

See you at 16:10 for the doors and 16:30 on the wire.

— bestteam
  Itay Malich, Diana Koroblov
  itay.malich2@gmail.com
