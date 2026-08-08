# External Accounts Setup (TODO 0.2)

Step-by-step for the four external services. Verified against the current
consoles on 28 July 2026 — Google renamed several pages, so older tutorials will
send you to menus that no longer exist.

Verify everything at the end with:

```powershell
uv run python scripts/check_setup.py
```

---

## ⚠️ Read this before you start: two traps

**1. Your OAuth app must be published to production, or reporting dies mid-league.**
A Google Cloud project left in **Testing** status issues refresh tokens that
**expire after 7 days**. Your project runs to 12 August — roughly 15 days. The
token would die somewhere around your first counted matches, the automated
report would silently fail, and a missing report scores **0 for both teams**
(M#35). Step 0.2.1.7 below fixes this. Do not skip it.

**2. Keep `credentials.json` outside both repositories.**
Not merely git-ignored — physically outside. A secret committed once lives in
the Git history forever (M#39, M#40). Use a folder such as
`C:\Users\diana\.p2p-secrets\`.

---

## 0.2.1 — Gmail API and OAuth 2.0

### 0.2.1.a Create the project and enable the Gmail API

1. Go to <https://console.cloud.google.com/>
2. Project dropdown (top left) → **New Project**
3. Name it `p2p-cop-chase` → **Create**
4. Make sure the new project is selected in the dropdown
5. Go to <https://console.cloud.google.com/apis/enableflow?apiid=gmail.googleapis.com>
6. Click **Enable**

✅ **Done when:** the Gmail API page shows *API Enabled*.

### 0.2.1.b Configure the consent screen

The old "OAuth consent screen" page is now **Google Auth platform**.

1. Go to <https://console.cloud.google.com/auth/branding>
2. If you see *Google Auth platform not configured yet*, click **Get Started**
3. **App Information** → App name: `p2p-cop-chase`; User support email: your address → **Next**
4. **Audience** → select **External**
   *(Internal exists only for Google Workspace organisations. A personal
   `@gmail.com` account must use External — this is not the same as making
   anything public.)*
5. **Contact Information** → your email → **Next**
6. Accept the User Data Policy → **Continue** → **Create**

### 0.2.1.c Add yourself as a test user

1. Go to <https://console.cloud.google.com/auth/audience>
2. Under **Test users** → **Add users** → your own Gmail address → **Save**

Without this you get `Error 403: access_denied` at the consent screen.

### 0.2.1.d Add the send-only scope

1. Go to <https://console.cloud.google.com/auth/scopes>
2. **Add or remove scopes** → filter for `gmail.send`
3. Tick **`https://www.googleapis.com/auth/gmail.send`** → **Update** → **Save**

Add **only** this scope. Send-only is mandatory (M#30); requesting read access
would be a security overreach the grader can see in your code.

### 0.2.1.e Create the Desktop app client

1. Go to <https://console.cloud.google.com/auth/clients>
2. **Create Client**
3. **Application type** → **Desktop app**
4. Name: `p2p-cop-chase-desktop` → **Create**
5. **Download JSON** in the dialog (or the ⬇ icon in the client list afterwards)

### 0.2.1.f Store it outside the repository

```powershell
mkdir C:\Users\diana\.p2p-secrets
Move-Item $HOME\Downloads\client_secret_*.json C:\Users\diana\.p2p-secrets\credentials.json
```

Then in `C:\Users\diana\final_project\p2p-chase\.env`:

```
GMAIL_CREDENTIALS_PATH=C:\Users\diana\.p2p-secrets\credentials.json
GMAIL_TOKEN_PATH=C:\Users\diana\.p2p-secrets\token.json
```

### 0.2.1.g ⚠️ Publish the app — removes the 7-day token expiry

**Do this BEFORE the consent flow in 0.2.1.h.** Publishing does not repair
tokens that already exist: a grant minted in Testing keeps its 7-day life, so
publishing afterwards means re-consenting anyway. Order matters.

1. Go to <https://console.cloud.google.com/auth/audience>
2. Find the **Publishing status** panel at the top. It reads **Testing**.
3. Click **Publish app**.
4. A dialog appears — *"Your app will be available to any user with a Google
   Account"* — and may list your scopes with a note that `gmail.send` is a
   **restricted** scope. Click **Confirm**.
5. The panel should now read **Publishing status: In production**.

**What "restricted scope" changes, and what it does not.** Every Gmail scope is
restricted in Google's classification, so the dialog may warn that verification
is required. Verification is required to *distribute* the app — to show it
without a warning screen and to exceed 100 users. It is not required for the app
to work. Your own account is one user of an app you wrote, and clicking through
your own warning screen is the whole interaction.

At the consent screen you will now see **"Google hasn't verified this app"**.
That is expected: click **Advanced** → **Go to p2p-cop-chase (unsafe)**. The
word "unsafe" refers to Google not having reviewed the app, not to anything
about the grant — which is still `gmail.send` and still cannot read your
mailbox.

**If Google refuses to publish** — some projects are pushed into a verification
queue instead — leave it in Testing and re-run 0.2.1.h **every 7 days**, marking
it in your calendar. A token that dies mid-league costs 0 to *both* teams
(M#35), so an unglamorous recurring reminder beats a silent failure.

✅ **Done when:** publishing status reads **In production**.

### 0.2.1.h Run the consent flow — this is what creates the token

Steps a–g produce `credentials.json`, which identifies the **application**. It
is not an email and password: your Google password is typed only into Google's
own page, and what comes back is a token. This step is that exchange, and until
it runs there is no token and nothing can send.

```powershell
uv run python scripts/gmail_consent.py
```

A browser opens. Sign in with the account that will send the reports, click
through the unverified-app warning, and grant **Send email on your behalf** —
the only permission it should ask for. If it asks for anything more, stop: the
scope in 0.2.1.d is wrong.

Then prove the whole path works, end to end, before a match depends on it:

```powershell
uv run python scripts/gmail_consent.py --test-to your.own@gmail.com
```

This sends one real message through the Gatekeeper, the message builder and the
Gmail API, with a throwaway attachment. `--test-to` has no default on purpose:
the configured recipient is the lecturer (M#51), and a self-test that defaulted
to it would mail him a fake report the first time anyone ran it.

**The sending account must match `[email] sender` in `config/<role>/game.toml`.**
Gmail sends as whoever authenticated, and `build_message` puts the config value
in the `From:` header — two different addresses make the header contradict the
sender.

✅ **Done when:** the test message is in your inbox **and** your Sent folder, and
`scripts/check_setup.py` reports the token `[ OK ]`.

**Re-consenting later.** `gmail_consent.py` will not overwrite an existing
token; pass `--force`. You need this if the grant is revoked, if the account
changes, or if a `RefreshError: invalid_grant` appears — which means the grant
is gone rather than merely expired, and is what a Testing-status project looks
like on day 8.

---

## 0.2.2 — Groq API key (Diana's machine)

1. Go to <https://console.groq.com/keys>
2. Sign in → **Create API Key** → name it `p2p-cop-chase` → copy it immediately
   (it is shown once)
3. Add to `.env`:

```
GROQ_API_KEY=gsk_your_key_here
```

✅ **Done when:**

```powershell
uv run python -c "from core.shared.env import optional, redact; print(redact(optional('GROQ_API_KEY')))"
```

prints your key, not `None`.

Groq is your development provider only. Graded matches run from Itay's machine
on Ollama, at zero tokens — computational fairness is scored (ADR-003).

---

## 0.2.3 — Ollama (Itay's machine)

1. Download from <https://ollama.com/download> → install
2. Pull a small model. It must return a 15-word bluff inside the 30-second step
   deadline, so start small and only go bigger if latency allows:

```powershell
ollama pull llama3.2:3b
```

3. Time it:

```powershell
Measure-Command { ollama run llama3.2:3b "In 15 words or fewer, taunt an opponent chasing you through New York." }
```

✅ **Done when:** the response arrives in **under 10 seconds**.

If it is comfortably fast, try `llama3.1:8b` for better language. If it is slow,
drop to `qwen2.5:1.5b`. Record the choice in PRD Q3 — it goes into the Step-0
hardware declaration for every match (M#24).

Ollama serves on `http://localhost:11434` by default; that is already the
`OLLAMA_BASE_URL` value in `.env-example`.

---

## 0.2.4 — ngrok (both machines)

1. Sign up at <https://dashboard.ngrok.com/signup>
2. Copy your authtoken from <https://dashboard.ngrok.com/get-started/your-authtoken>
3. Install and register it:

```powershell
winget install ngrok.ngrok
ngrok config add-authtoken YOUR_TOKEN_HERE
```

4. Test:

```powershell
ngrok http 8081
```

✅ **Done when:** a `https://....ngrok-free.dev` URL appears and the session
stays open. `Ctrl+C` to stop.

The port must match `[network] listen_port` in `config/<role>/game.toml`, which
is **8081**. This page said 8801 until 02/08 — a transposition that survived
because nothing executes these snippets, and the first thing it would have
broken is the two-machine rehearsal, where the cost of a wrong digit is a
booked slot with both people present.

Also add the token to `.env` so the tunnel can be started programmatically in
Phase 5:

```
NGROK_AUTHTOKEN=your_token_here
```

---

## 0.2.5 — Static domain or dynamic URLs? **Answered: static.**

ngrok now gives **every free account a permanent dev domain** on
`ngrok-free.dev`, assigned automatically and kept for as long as the account
exists. Reserving a *custom* name still needs a paid plan, but you do not need
one — you need a URL that does not change between matches.

**Decision: use the free static dev domain.**

Find yours at <https://dashboard.ngrok.com/domains> (Gateway → Domains), then
start the tunnel pinned to it:

```powershell
ngrok http 8081 --url YOUR-DOMAIN.ngrok-free.dev
```

Why this matters: with a rotating URL, every match would need the address
re-exchanged during negotiation, and any tunnel restart mid-series would strand
your opponent at a dead address. A fixed URL goes into the declaration JSON once
and stays valid.

Free plan limits — comfortably above what a league series needs: 20k HTTP
requests/month, 1 GB bandwidth/month, 3 concurrent endpoints.

### Recorded domains

`config/<role>/game.toml` does not exist yet — it is created in task 1.1.4, at the start of
Phase 1. Until then this table is where the domains live, so nothing is lost.

| Machine | Owner | Static domain | Recorded |
|---|---|---|---|
| Diana's | [D] | `customs-countdown-uncork.ngrok-free.dev` | 2026-07-28 |
| Itay's | [I] | `denotatively-sciuroid-florine.ngrok-free.dev` | 2026-08-02 |

Start the tunnel pinned to it:

```powershell
ngrok http 8081 --url customs-countdown-uncork.ngrok-free.dev
```

These move into `[network]` in the private per-peer TOML when task 1.1.4 creates it, and are
published in the declaration JSON at the start of every match.

---

## Verify everything

```powershell
uv run python scripts/check_setup.py
```

Checks the `.env` file, the Groq key format, the credentials file (existence,
type, and that it is **not** inside either repository), the token's publishing
status, Ollama reachability, and the ngrok binary and authtoken. Every failure
names the step above that fixes it.

---

## Sources

- [Gmail API Python quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [Manage App Audience — publishing status and the 7-day test-user expiry](https://support.google.com/cloud/answer/15549945?hl=en)
- [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
- [Static dev domains for all ngrok users](https://ngrok.com/blog/free-static-domains-ngrok-users)
- [ngrok Domains documentation](https://ngrok.com/docs/gateway/domains)
