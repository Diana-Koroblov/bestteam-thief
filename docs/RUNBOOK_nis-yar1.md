# Runbook — the warm-up against nis-yar1, 2026-08-19 16:30 Israel time

cmd.exe, one command per line. Adapted from the vibecode runbook; the differences from that
one are flagged.

| | |
|---|---|
| Opponent | `nis-yar1` — Nissim Deri, Yarden Tziar, `nissimderi123@gmail.com` |
| Counted? | **No. Warm-up.** Reports to the two teams only. |
| Role plan | **we are cop on 1/3/5, thief on 2/4/6** |
| Who opens | nis-yar1 opens sub-game 1 as thief |
| Protocol | `reference` — four mailboxes, confirmed |
| Scent | subtractive chebyshev `81ebee59`, `0.900 → 0.800` |
| Their doors | **not known yet** — rotating Cloudflare, posted at ~16:15 |
| Their heads | cop `7633fbc8…`, thief `3f2d0216…` (both repos 404 to us; not gating a warm-up) |
| Turn wait | **1200 s both sides** — raised from our 900 s default to match theirs |

Same `--first cop` and `--role-split 1-1-1-1-1-1` as vibecode. Nothing about the contract
changes: `agreed_between` still names vibecode in our shipped `game.json`, and that is fine —
it is not one of the fourteen signed terms and nis-yar1 does not gate on `config_sha256`.

## The one new trap: hold mode holds the domain

Their sequence has **us up first**, then they open their tunnels. So our doors go up in hold
mode before we know their URLs.

**Hold mode binds the reserved ngrok domain. `play --tunnel` cannot bind a domain that is
already bound.** So both hold-mode processes must be stopped — Ctrl-C, and let them exit —
before the two `play` commands are started. An orphaned hold-mode agent is exactly the
"reserved domain already in use" failure, and it will look like an ngrok account problem.

## 16:10 — doors up in hold mode, then post "up"

Two cmd windows. Check the token in **each** first; it must print `[]`.

```
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-cop
echo [%NGROK_AUTHTOKEN%]
uv run python -m core peer --role cop --serve --tunnel
```

```
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-thief
echo [%NGROK_AUTHTOKEN%]
uv run python -m core peer --role thief --serve --tunnel
```

Confirm the cop window prints `itinerary…` and the thief window prints `denotatively…`. If they
are the other way round, that clone's `.env` is wrong — stop and fix it, do not play.

Then post one line in the thread saying we are up. From a third window, confirm what they will
see:

```
curl -s -o NUL -w "%{http_code}\n" https://itinerary-single-overjoyed.ngrok-free.dev/mcp
curl -s -o NUL -w "%{http_code}\n" https://denotatively-sciuroid-florine.ngrok-free.dev/mcp
```

Anything other than `404` means an agent is behind the door. `404` still means it is not.

## 16:20 — probe theirs, once they post

```
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\p2p-chase
uv run python -m core probe <their COP url>
uv run python -m core probe <their THIEF url>
```

Exit 0 and the four mailboxes. **Check which door answers as which role** — our cop dials
their thief. They post rotating URLs, so use the pair from the 16:15 post and no earlier one.

## 16:30 — stop hold mode, then play

**Ctrl-C both hold-mode windows and wait for them to exit.** Then, in the same two windows:

```
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-cop
uv run python -m core play --role cop --protocol reference --tunnel --first cop --role-split 1-1-1-1-1-1 --turn-wait 1200 --wait 600 --out C:\Users\itaym\Documents\hw6-ai-orchestration\results\2026-08-19-nis-yar1-warmup\ --report-to nissimderi123@gmail.com,itay.malich2@gmail.com --opponent <their THIEF url>
```

```
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-thief
uv run python -m core play --role thief --protocol reference --tunnel --first cop --role-split 1-1-1-1-1-1 --turn-wait 1200 --wait 600 --out C:\Users\itaym\Documents\hw6-ai-orchestration\results\2026-08-19-nis-yar1-warmup\ --report-to nissimderi123@gmail.com,itay.malich2@gmail.com --opponent <their COP url>
```

What changed from the vibecode commands, and why:

| | |
|---|---|
| `--turn-wait 1200` | New. Matches the figure they raised theirs to; our default is 900. Both sides above the 1,050 s worst case the signed `max_steps` permits. |
| `--out …nis-yar1-warmup\` | Fresh directory, **shared by both terminals**, outside both clones. Both halves must land together or the report is held back at 3 of 6, and a directory inside a clone dirties it and blocks arming. |
| `--report-to nissimderi123@…` | Their inbox and ours. Warm-up, so no `--counted` and nothing to the lecturer. |
| `--opponent` | **Crossed, and not known until 16:15.** Cop dials their thief; thief dials their cop. |

`--first cop` and `--role-split 1-1-1-1-1-1` are unchanged and must be identical in both windows.

## What good looks like

```
handshake       : AGREED
our sub-games   : 1, 3, 5
  sub-game 1  cop  ...  audit passed
```

`audit passed` on every row. Anything other than `AGREED` exits 1 with no move sent and prints
the reason — that is correct behaviour, not a bug.

## Afterwards

1. Agree the figures with them before anyone files; both scoreboards must mirror.
2. The report sends itself from whichever process files the sixth sub-game, to both inboxes.
3. **No LEAGUE_LOG row** — this is a warm-up. The counted figure stays at 2.
4. Copy the artefacts into `p2p-chase/results/` and ship only if you want them in the repos;
   a warm-up is not evidence anyone grades.
