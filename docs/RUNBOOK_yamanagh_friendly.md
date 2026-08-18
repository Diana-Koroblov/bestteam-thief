# Runbook — the friendly against yamanagh, step by step

Written for the first time you run a match yourself. Every command below has been checked
against the code in this tree, not copied from an older document. Follow it in order and do
not skip §1 — two of its four edits change a digest we have already sent them, and a digest
that has moved refuses the handshake rather than starting a match that cannot be audited.

**`docs/MATCHDAY.md` is the general runbook and is still correct in outline, but three of its
specifics are wrong for this match.** They are all consequences of us now holding two reserved
domains instead of one. Each is flagged below where it bites.

---

## The agreed shape of this match

| | |
|---|---|
| Opponent | `yamanagh` — Nagham Manasra, Yaman Dahle |
| Counted? | **No. This is a friendly.** Nothing goes to the lecturer. |
| Role plan | yamanagh cop on 1/3/5 · **we are thief on 1/3/5 and cop on 2/4/6** |
| Who opens | The thief moves first, so **we open sub-game 1** |
| Scent | multiplicative (book), `0.900 → 0.810` — **we agreed to move to theirs** |
| Their cop door | `https://canal-mesa-installing-poems.trycloudflare.com/mcp` |
| Their thief door | `https://entities-structural-request-leadership.trycloudflare.com/mcp` |
| Time | any — both sides said so |

**Still open until they reply:** the merge rule (maximum vs clamped sum). Option 3 in our
letter — play the friendly with the divergence declared — needs no change on our side, so
you can run everything below without waiting. If they pick option 1 instead, that is a code
change and a re-ship, and this runbook does not cover it.

---

## 1. Before you touch a terminal: four config edits, then ship

All four are made **here**, in `p2p-chase`, and then shipped. Never edit the published clones
directly — `ship.py` overwrites them from this tree.

### 1a. Put their team id in the shared contract — both files, byte-identical

In **`config/police/game.json`** and **`config/thief/game.json`**, change:

```json
"agreed_between": ["bestteam", "imreeyal"],
```

to:

```json
"agreed_between": ["bestteam", "yamanagh"],
```

Both files must end up byte-identical: they are the same shared contract and both of our
processes hash it. This is what makes `config_sha256` come out as the `cc1b49bb…` we already
sent them, so it is not optional.

### 1b. Switch the scent model to theirs — both files

In **`config/police/game.toml`** and **`config/thief/game.toml`**, line 84:

```toml
decay_model = "subtractive"     # <- change to "multiplicative"
```

This is the model we agreed to adopt in the reply. It changes `scent_model_sha256` from
`81ebee59…` to `934c220d…` and leaves `config_sha256` alone, because the model name lives in
the private file rather than the shared contract.

### 1c. Verify before you ship

```powershell
uv run python -c "import json,sys; sys.path.insert(0,'.'); from core.crypto.canonical import digest; from core.compat.wire import SCENT_MODEL_SHA256; from core.shared.config_manager import load_config; from pathlib import Path; c=json.load(open('config/police/game.json',encoding='utf-8')); t=json.load(open('config/thief/game.json',encoding='utf-8')); print('both game.json identical:', c==t); print('config_sha256:', digest(c)); print('  expected   : cc1b49bb0863eaecddf21302cf460ae7d9d187c83eaaffb74009848417b84d6f'); m=str(load_config(Path('config/police')).get('pheromones.decay_model')); print('decay_model  :', m); print('scent digest :', SCENT_MODEL_SHA256[m])"
```

You want `both game.json identical: True`, `config_sha256` matching `cc1b49bb…`, and
`decay_model: multiplicative`. **If the digest does not match, stop and fix it** — sending
them one number and playing under another is the refusal this check exists to prevent.

### 1d. Ship

```powershell
uv run python scripts/ship.py -m "chore: contract names yamanagh and the scent model moves to the book kernel for the friendly"
```

This publishes to both clones and gives you two new head hashes. **Write them down — you must
repost them to yamanagh before you arm**, because the reply you sent declares the previous
pair and step 0 reads the head at match time.

```powershell
git -C ..\bestteam-cop rev-parse HEAD
git -C ..\bestteam-thief rev-parse HEAD
```

---

## 2. Check the machine

```powershell
uv run python scripts/check_setup.py
```

**One trap that is not in `check_setup.py`'s output and has bitten us:** if
`NGROK_AUTHTOKEN` is set in your *shell*, it beats the clone's `.env` and the tunnel fails
with what looks like a domain-ownership error. Our two domains live on two different ngrok
accounts, so each clone must use its own `.env` token. Confirm the shell is clean:

```powershell
echo "[$env:NGROK_AUTHTOKEN]"      # you want [] — empty
```

If it prints a token, clear it for this session: `$env:NGROK_AUTHTOKEN = $null`

---

## 3. Probe them before you play them

Do this from anywhere; it needs no config and no agreed terms.

```powershell
uv run python -m core probe https://canal-mesa-installing-poems.trycloudflare.com/mcp
uv run python -m core probe https://entities-structural-request-leadership.trycloudflare.com/mcp
```

It lists the tools their servers actually expose and tells you which protocol to speak:

- **four mailboxes** (`negotiate` / `receive_turn` / `receive_control` / `submit_audit`) →
  use `--protocol reference`, which is what §4 below assumes and what we proposed to them.
- **six tools** (`receive_commit` / `receive_reveal` / `final_reveal` / …) → drop the
  `--protocol reference` flag from both commands and everything else stays the same.

Exit 0 means playable. **Their URLs are Cloudflare Quick Tunnels and rotate on every
restart** — if either probe fails, ask them to repost rather than assuming they are down.

---

## 4. Play — two terminals, both up at the same time

> **`docs/MATCHDAY.md` says to run the two roles "one after the other, not side by side".
> That is wrong for this match.** It was written when we held one reserved domain that could
> only map to one process at a time. We now hold two, one per role, on separate accounts, and
> the roles alternate every sub-game — so **both processes must be up for the whole series**,
> each idle for half of it but still answering, because the next window arrives at it. A
> process that exits after its own sub-game kills the series at the next handover.

> **`MATCHDAY.md` also says `--opponent` is "the same value in both terminals". Also wrong
> now.** Each of our processes dials the door of the *opposite* role, so the two terminals get
> **different** URLs. Getting this backwards is the single easiest mistake here.

Open both terminals, run terminal 1 first, then terminal 2 straight away.

**Terminal 1 — our thief. Plays sub-games 1, 3, 5. Dials their COP.**

```powershell
cd C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-thief

uv run python -m core play --role thief --protocol reference --tunnel `
    --first thief --role-split 1-1-1-1-1-1 `
    --out results\ `
    --report-to yamandahle@gmail.com,naghammnsor@gmail.com,itay.malich2@gmail.com `
    --opponent https://canal-mesa-installing-poems.trycloudflare.com/mcp
```

**Terminal 2 — our cop. Plays sub-games 2, 4, 6. Dials their THIEF.**

```powershell
cd C:\Users\itaym\Documents\hw6-ai-orchestration\bestteam-cop

uv run python -m core play --role cop --protocol reference --tunnel `
    --first thief --role-split 1-1-1-1-1-1 `
    --out results\ `
    --report-to yamandahle@gmail.com,naghammnsor@gmail.com,itay.malich2@gmail.com `
    --opponent https://entities-structural-request-leadership.trycloudflare.com/mcp
```

### Why each flag is what it is

| Flag | Why |
|---|---|
| `--first thief` | **Identical in both terminals.** It names the role *our team* holds in the first block, not the role of the process you are starting. We are thief in sub-game 1, so both say `thief`. Getting this different between the two terminals is how both of our own halves disagree. |
| `--role-split 1-1-1-1-1-1` | Alternating, swapping every sub-game. With `--first thief` this gives our thief 1/3/5 and our cop 2/4/6 — verified against `plan_for()`, not assumed. |
| `--protocol reference` | Only if the probe showed four mailboxes. Drop it for six tools. |
| `--tunnel` | Publishes each process on its own reserved domain. Required to be reachable. |
| `--out results\` | Files the four artefacts. We promised them the artefacts, so keep it. |
| `--report-to …` | The **friendly** send path — the two teams' inboxes, never the lecturer. Put it on both terminals; whichever files the sixth sub-game is the one that sends. |
| **no `--counted`** | `--counted` mails the lecturer. **This is a friendly. Do not add it.** |
| **no `--their-commit`** | Deliberately omitted. The peer's sealed step-0 record outranks it, and carrying this flag from an old runbook is exactly what caused us to file the wrong opponent hashes on 17/08. Let the evidence win. |

Defaults you do not need to pass: `--wait 120` (handshake retry), `--turn-wait 900` (how long
each process waits for the opponent to reach its sub-game — 15 minutes, which is the figure
we quoted them), `--linger 20` (keep serving so they can audit us; never set it to 0).

Add `--gui` to either terminal if you want to watch the belief heat map. Closing the window
does not forfeit.

### Post your URLs before you arm

Each terminal prints, on startup, the line to paste into the thread:

```
role            : thief
our url         : https://denotatively-sciuroid-florine.ngrok-free.dev/mcp
give them       : --opponent https://denotatively-sciuroid-florine.ngrok-free.dev/mcp
their url       : https://canal-mesa-installing-poems.trycloudflare.com/mcp
```

Check `their url` against what they sent. **Post both of our URLs and both new head hashes in
the thread before the first move**, as we promised. Our cop is `itinerary…`, our thief is
`denotatively…` — if a terminal prints the other way round, something is wrong with that
clone's `.env`.

---

## 5. What you should see

```
handshake       : AGREED
our sub-games   : 1, 3, 5

  sub-game 1  thief  SURVIVAL   5 - 10   35 steps  audit passed
```

**`audit passed` on every row is the line to check.** `FAILED` means their log did not
re-hash — file it and do not score it yourself.

`handshake` anything other than `AGREED` exits 1 with no move sent, and the reason is
printed. That is the correct outcome: a match played under configs differing by one byte
cannot be audited. The likely causes here, in order: a config edit from §1 that did not get
shipped, `--first` differing between our two terminals, or them running different physics.

Two warnings are normal to *see* and mean a step was skipped:

- *"working tree is DIRTY"* → you did not ship after §1.
- *"agreed_between names bestteam"* → §1a did not take.

---

## 6. Afterwards

1. **Agree the figures with them before anyone files.** Both scoreboards must mirror — our
   15–30 is their 30–15.
2. **Verify a log:**
   ```powershell
   uv run python -m core replay results\log_<game_id>_g01.json --headless
   ```
   You want exit 0 and `Verified OK`.
3. **Do not add a row to `docs/LEAGUE_LOG.md`.** That table is counted matches only, and this
   is a friendly — it stays at 1. There is a separate warm-up table for this.
4. If the report did not send, it is filed and recoverable:
   ```powershell
   uv run python scripts\send_report.py --role thief results\ --dry-run
   ```

---

## The whole thing, once you have done it once

```powershell
# 1. edit agreed_between -> yamanagh and decay_model -> multiplicative in all four config files
uv run python scripts/ship.py -m "chore: contract names yamanagh, book scent kernel"
git -C ..\bestteam-cop rev-parse HEAD ; git -C ..\bestteam-thief rev-parse HEAD   # repost these

# 2. probe
uv run python -m core probe https://canal-mesa-installing-poems.trycloudflare.com/mcp

# 3. two terminals, both up, different opponent URLs, same --first
cd ..\bestteam-thief ; uv run python -m core play --role thief --protocol reference --tunnel --first thief --role-split 1-1-1-1-1-1 --out results\ --report-to yamandahle@gmail.com,naghammnsor@gmail.com,itay.malich2@gmail.com --opponent https://canal-mesa-installing-poems.trycloudflare.com/mcp
cd ..\bestteam-cop   ; uv run python -m core play --role cop   --protocol reference --tunnel --first thief --role-split 1-1-1-1-1-1 --out results\ --report-to yamandahle@gmail.com,naghammnsor@gmail.com,itay.malich2@gmail.com --opponent https://entities-structural-request-leadership.trycloudflare.com/mcp
```
