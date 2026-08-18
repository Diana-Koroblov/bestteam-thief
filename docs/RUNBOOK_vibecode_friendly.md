# Runbook — the friendly against vibecode, in cmd.exe

Every command checked against the code in this tree. Written for `cmd.exe`, so each command is
one line — **no backtick continuations**, those are PowerShell only.

**The config work is already done and shipped.** Unlike the yamanagh runbook, there is nothing
to edit before you start: `agreed_between` already names vibecode, `decay_model` is already
`subtractive` (which is the `81ebee59…` we declared to them), and both clones are clean and
published. Go straight to §1 to confirm it, then §3 to play.

---

## The agreed shape of this match

| | |
|---|---|
| Opponent | `vibecode` — Ron Marom, Amit Kuperminz |
| Counted? | **No. This is a friendly.** Nothing goes to the lecturer. |
| Role plan | **we are cop on 1/3/5, thief on 2/4/6** — vibecode cop on 2/4/6 |
| Who opens | The thief moves first, so **vibecode opens sub-game 1** |
| Scent | subtractive chebyshev, `81ebee59…`, merge by maximum, `0.900 → 0.800` |
| Protocol | `reference` — the four mailboxes, confirmed by them in writing |
| Their cop door | `http://62.56.220.143:61224/mcp` |
| Their thief door | `http://62.56.220.143:61223/mcp` |
| Our heads | cop `6f5a7ed1…`, thief `a671fe05…` |

**The one thing that differs from every previous runbook: `--first cop`, not `--first thief`.**
`bestteam` sorts before `vibecode`, so their sorted-pair rule makes us cop in sub-game 1.
Verified against `plan_for()` on this tree:

```
--first cop --role-split 1-1-1-1-1-1
  our cop process plays   1, 3, 5
  our thief process plays 2, 4, 6
```

---

## 1. Confirm what will actually play (30 seconds)

Run from the **clones**, not this tree — the clones are what launch.

```
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-cop
git rev-parse HEAD
git status --porcelain
```

You want `6f5a7ed14b6f8180aa3acc08d304deb8fd2422da` and **no output** from `status`. Same for
the thief:

```
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-thief
git rev-parse HEAD
git status --porcelain
```

You want `a671fe05a0a4afb47562e00485443b7f22b694ef` and no output.

Then confirm the contract both processes will hash:

```
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\p2p-chase
uv run python -c "import json,sys;sys.path.insert(0,'.');from core.crypto.canonical import digest;a=json.load(open('../bestteam-cop/config/police/game.json',encoding='utf-8'));b=json.load(open('../bestteam-thief/config/thief/game.json',encoding='utf-8'));print('identical:',a==b);print('agreed_between:',a['agreed_between']);print('config_sha256:',digest(a))"
```

You want `identical: True`, `['bestteam', 'vibecode']`, and
`d16427a258a6cecaebd4b6f85463aa6d2daa22d1c24c06725140ea1a7b153618`. If any of those is wrong,
**stop** — we sent vibecode that digest and playing under another one refuses the handshake.

## 2. Check the machine, and the one trap

```
uv run python scripts/check_setup.py
```

`GROQ_API_KEY not set` and `Ollama not reachable` are both fine — our provider is `template`,
which is what makes our declared zero-token figure true.

**The trap:** if `NGROK_AUTHTOKEN` is set in the shell it beats each clone's `.env`, and our
two domains live on two different ngrok accounts, so the tunnel fails with what looks like a
domain-ownership error. Check it is empty, in **each** terminal:

```
echo [%NGROK_AUTHTOKEN%]
```

You want `[]`. If it prints a token, clear it for that window:

```
set NGROK_AUTHTOKEN=
```

## 3. Probe them (do this in the hold-mode window, before T)

```
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\p2p-chase
uv run python -m core probe http://62.56.220.143:61224/mcp
uv run python -m core probe http://62.56.220.143:61223/mcp
```

Exit 0 means playable. You want the four mailboxes — `negotiate`, `receive_turn`,
`receive_control`, `submit_audit`. If you see six tools instead, drop `--protocol reference`
from both commands in §4 and tell them.

**A silent timeout tells you nothing** — their forward drops rather than refuses, so it cannot
distinguish "not up yet" from "unreachable". Only probe once they say the doors are up.

Confirm which port answers as which role. They label 61224 cop and 61223 thief; probe before
you dial, because these have been posted swapped by other teams before.

## 4. Play — two terminals, both up for the whole series

Open **two** cmd windows. Start terminal 1, then terminal 2 straight away. Both must stay up
for all six windows — each is idle for half the series but still has to answer, because the
next window arrives at it.

**Note the URLs are crossed.** Our cop dials their thief; our thief dials their cop. This is
the easiest thing to get backwards.

**Terminal 1 — our COP. Plays sub-games 1, 3, 5. Dials their THIEF (61223).**

```
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-cop
uv run python -m core play --role cop --protocol reference --tunnel --first cop --role-split 1-1-1-1-1-1 --out C:\Users\itaym\Documents\hw6-ai-orchestration\results\bestteam-vs-vibecode\ --report-to agentsorch@gmail.com,itay.malich2@gmail.com --opponent http://62.56.220.143:61223/mcp
```

**Terminal 2 — our THIEF. Plays sub-games 2, 4, 6. Dials their COP (61224).**

```
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-thief
uv run python -m core play --role thief --protocol reference --tunnel --first cop --role-split 1-1-1-1-1-1 --out C:\Users\itaym\Documents\hw6-ai-orchestration\results\bestteam-vs-vibecode\ --report-to agentsorch@gmail.com,itay.malich2@gmail.com --opponent http://62.56.220.143:61224/mcp
```

### Why each flag is what it is

| Flag | Why |
|---|---|
| `--first cop` | **Identical in both terminals.** It names the role *our team* holds in the first block, not the process you are starting. We are cop in sub-game 1, so both say `cop`. Different values between the two terminals is how our own halves disagree. |
| `--role-split 1-1-1-1-1-1` | Alternating every sub-game. With `--first cop` this gives our cop 1/3/5 and our thief 2/4/6 — verified against `plan_for()`, not assumed. |
| `--protocol reference` | The four mailboxes. Confirmed by vibecode in writing and again by the probe. |
| `--tunnel` | Publishes each process on its own reserved domain. Required to be reachable. |
| `--out <shared dir>` | Files the four artefacts. **Both terminals MUST point at the SAME directory**, and it must NOT be `results\` inside each clone. The two role processes each play three sub-games and merge through the filesystem: the second to finish reads the first's `result_<game_id>.json`, folds its rows in, sees 6 of 6 and mails. Two separate `results\` folders means neither ever sees the other half, both file 3 of 6, and the M#35 completeness gate correctly holds the report back. This cost us the report on 19/08. |
| `--report-to …` | The **friendly** path: their operator inbox and ours. Put it on both terminals; whichever files the sixth sub-game is the one that sends. |
| **no `--counted`** | `--counted` mails the lecturer. **This is a friendly. Do not add it.** |
| **no `--their-commit`** | Deliberately omitted. Their sealed step-0 record outranks anything we type, and carrying this flag from an old runbook is what made us file the wrong opponent hashes on 17/08. |

Defaults you do not need to pass: `--wait 120`, `--turn-wait 900` (15 minutes, the figure we
quoted them), `--linger 20` (keep serving so they can audit us — never set it to 0).

Add `--gui` to either terminal to watch the belief heat map. Closing the window does not
forfeit.

### Before the first move

Each terminal prints its own public URL on startup. Check that the cop window shows
`itinerary…` and the thief window shows `denotatively…` — if they are the other way round,
that clone's `.env` is wrong. Post both URLs and both head hashes in the thread, as promised.

## 5. What you should see

```
handshake       : AGREED
our sub-games   : 1, 3, 5

  sub-game 1  cop  ...  audit passed
```

`audit passed` on every row is the line to check. Anything other than `AGREED` exits 1 with no
move sent and the reason printed — that is the correct outcome, not a bug. Likely causes here,
in order: `--first` differing between the two terminals, a stale clone, or them running
different physics.

Two warnings mean a step was skipped: *"working tree is DIRTY"* → something changed in a clone
since the ship; *"agreed_between names bestteam"* → the config did not take.

## 6. Afterwards

1. **Agree the figures with them before anyone files.** Both scoreboards must mirror.
2. Verify a log:
   ```
   uv run python -m core replay results\log_<game_id>_g01.json --headless
   ```
   You want exit 0 and `Verified OK`.
3. **Do not add a row to the counted table in `docs/LEAGUE_LOG.md`.** This is a friendly; the
   counted figure stays at 1. There is a separate warm-up table.
4. If the report did not send, it is filed and recoverable:
   ```
   uv run python scripts\send_report.py --role cop results\ --dry-run
   ```

---

## The whole thing, once

```
:: terminal 1
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-cop
uv run python -m core play --role cop --protocol reference --tunnel --first cop --role-split 1-1-1-1-1-1 --out C:\Users\itaym\Documents\hw6-ai-orchestration\results\bestteam-vs-vibecode\ --report-to agentsorch@gmail.com,itay.malich2@gmail.com --opponent http://62.56.220.143:61223/mcp

:: terminal 2
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-thief
uv run python -m core play --role thief --protocol reference --tunnel --first cop --role-split 1-1-1-1-1-1 --out C:\Users\itaym\Documents\hw6-ai-orchestration\results\bestteam-vs-vibecode\ --report-to agentsorch@gmail.com,itay.malich2@gmail.com --opponent http://62.56.220.143:61224/mcp
```

---

# The COUNTED series — what changes

Everything above still applies. Four differences, and the last one is the one that is easy to
get wrong because it is not a flag.

1. **Add `--counted`.** It is what routes the report to
   `rmisegal+uoh26finalgame@gmail.com` instead of the two teams' inboxes.
2. **Drop `--report-to`.** `--counted` ignores it, but leaving it on is an invitation to
   confuse the two paths at 2am.
3. **A fresh `--out`, again.** Same terms means the same `game_uid` as both friendlies, so a
   reused directory merges the counted rows into a friendly's file.
4. **Do NOT add the LEAGUE_LOG row until after the match has filed.** `_games_played` reads
   `counted_matches()` and adds 1 for this series. A row written early double-counts it against
   M#38 *and* flips `_first_meeting` to False, which silently drops the diversity reward. File
   first, log second.

```
:: terminal 1 — our COP, sub-games 1/3/5, dials their THIEF
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-cop
uv run python -m core play --role cop --protocol reference --tunnel --counted --first cop --role-split 1-1-1-1-1-1 --out C:\Users\itaym\Documents\hw6-ai-orchestration\results\2026-08-19-COUNTED-vibecode\ --opponent http://62.56.220.143:61223/mcp --wait 600

:: terminal 2 — our THIEF, sub-games 2/4/6, dials their COP
cd /d C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-thief
uv run python -m core play --role thief --protocol reference --tunnel --counted --first cop --role-split 1-1-1-1-1-1 --out C:\Users\itaym\Documents\hw6-ai-orchestration\results\2026-08-19-COUNTED-vibecode\ --opponent http://62.56.220.143:61224/mcp --wait 600
```

Afterwards, in order: agree the figures with them → both reports to the league address only →
exchange message-ids → byte-reconcile → **then** add the row to `docs/LEAGUE_LOG.md` and bump
the "Counted matches so far" line to 2.
