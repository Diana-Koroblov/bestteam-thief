# Known issues — what broke, what's fixed, what's still open

Working log from the najamjad/yanell11 match-prep sessions (17-18/08). Not a
permanent doc — a scratch record so we don't re-discover the same thing twice
or forget something real is still open.

## Fixed

- **Silent audit-push failure (17/08).** `core/cli_compat.py`'s outbound
  `submit_audit` call was wrapped in `contextlib.suppress(PeerError)` with no
  retry and no error message. A stale connection (the peer that just won can
  exit the moment it reads its inbox) made the push fail invisibly — our own
  log showed nothing wrong while najamjad recorded `AUDIT SKIPPED`. Fixed:
  extracted to `core.compat.turn_wait.push_audit` (one redial, one retry,
  reports every failure). Proven against real transport code, not mocks, in
  `tests/integration/test_audit_push_recovers.py`. Shipped in commit
  `fix(compat): retry the outbound submit_audit push...`.
- **Two stale test thresholds** in `test_advanced_selfplay.py` and
  `test_advanced_thief_selfplay.py`, both predating the 15/08 barrier-deadlock
  fix (`seal_exits`/`weight_reach` in `game.toml`) and an earlier scent-timing
  fix (TODO 4.1.6). Re-measured and documented rather than silently bumped —
  see those files' own dated comments for the numbers.
- **The advanced Cop self-separated from the advanced Thief, 6/48 openings
  (18/08).** Traced to a specific mechanism, not guessed: the Cop's belief
  stayed 98%+ confident about a cell the Thief had already left (opening
  cop=(2,1)/thief=(4,5), full trace below), and stepping into that
  now-sealed-behind-us pocket blended to a near-certain-capture value on
  belief's confidence alone — `separation_mass` reported nothing stranded,
  because almost all believed mass sat *inside* the trap. Two false starts
  before the real fix: (1) a barrier-placement guard in
  `barrier_policy.rejection_for` — reverted, the wall itself doesn't
  geometrically trap the Cop at the moment it's placed, an escape cell is
  still open; (2) an isolation term inside `evaluate()` alone — barely moved
  the number, because `search._value_of` blends `caught * CAPTURE_VALUE` with
  `(1 - caught) * ahead`, and at `caught = 0.97` the isolation-aware `ahead`
  term is scaled to noise. **Real fix**: a new `CopWeights.isolation` term
  applied to the full blended value in `_value_of` (`police/search.py`), not
  just the leaf evaluation — belief-independent, so a wrong filter cannot buy
  its way past it. Default `weight_isolation = 100.0`
  (`config/police/game.toml`). Confirmed on the full 48-opening benchmark:
  6/48 separations to 0/48, zero regression on every matchup that already
  worked (`test_advanced_league_benchmark.py -m slow`, all re-run clean).
  Unit tests: `test_isolation_*` in `test_cop_evaluation.py`,
  `test_isolation_discounts_a_wall_that_would_leave_a_tiny_pocket` in
  `test_cop_barrier_policy.py`.

  **What this did NOT fix, so nobody assumes otherwise.** Advanced-cop-vs-
  advanced-thief is still 0/48 captures — self-separation was never the main
  cause of that number, something deeper in the pursuit itself is. Still
  open, see below.

## Open — does NOT block a match from running, affects whether we win

- **The advanced Cop still never captures the advanced Thief, 0/48 openings**
  (`test_the_competitive_cell_is_reported_and_not_gated` and
  `test_a_better_cop_is_still_a_harder_cop`, same slow benchmark). Confirmed
  this is a separate, deeper issue from the self-separation bug above — fixing
  that changed 0 of these 48 outcomes. Not investigated further yet. A lost
  sub-game still completes and audits cleanly, so this costs points, not
  participation in tomorrow's match.
- **The advanced Cop is now slower than the baseline Cop against the baseline
  Thief** (`test_the_advanced_cop_captures_faster_than_the_baseline_one`),
  the accepted trade-off from the 15/08 barrier-deadlock fix — see that
  commit and `test_advanced_selfplay.py`'s module docstring. Not a new
  finding, not re-chased today.

## Operational gotchas learned the hard way tonight (not code bugs)

- **Playing ANY match — including a rehearsal against the kit's own practice
  bot — overwrites `config/<role>/game.json` in place** with whatever got
  negotiated: `agreed_between`, `map_area`, `decay_model`, all silently
  rewritten to the rehearsal opponent's values. Found live (18/08): a
  sparring-bot rehearsal left `bestteam-thief`'s own `config/thief/game.json`
  declaring `agreed_between: ["bestteam", "sparring-local"]` and
  `decay_model: "multiplicative"` — the REAL opponent (najamjad) needs
  `"najamjad"` and `"subtractive"`. Had this shipped or been left in place, the
  next real match would have negotiated the wrong terms entirely. **Always
  `git diff config/` after any rehearsal, in every repo it touched
  (`p2p-chase` AND both split repos if run from there), before playing the
  real match or running `ship.py`.**

- **Killing and restarting our `core play` processes mid-series desyncs the
  opponent.** Their per-sub-game watchdog keeps running on their own clock; a
  restart on our side doesn't reset it, and they'll report sub-games as
  timed-out or audit-skipped even though we're still genuinely playing. Once
  armed, let a series run to completion rather than restarting to fix
  something else.
- **Free ngrok tunnels fail TLS handshakes under load** (~120 req/min), not a
  clean error — `SSL: UNEXPECTED_EOF_WHILE_READING` on both sides. Repeated
  restarts + curl probing + both sides' retries can trigger this. If it
  happens, stop everything and let it cool down a few minutes before retrying;
  don't restart into it.
- **`scripts/ship.py` / `publish.py` wipes each split repo's `results/`
  folder** with whatever is in `p2p-chase/results/` (which has none of the
  match files, since matches are run from inside `bestteam-cop`/
  `bestteam-thief` directly). Shipping a code change mid-match-prep silently
  deletes any result artifacts sitting only in the split repos. Copy anything
  worth keeping out first.
- **A real match must run from the published repo, not `p2p-chase`.** `core
  play` refuses with "no git remote" from the dev tree — launch from inside
  `bestteam-cop`/`bestteam-thief`, each with its own `.env` (copied, gitignored)
  and its own `uv sync`.
- **Bash + Windows path syntax**: `--out results\` (trailing backslash, copied
  from the PowerShell-flavoured docs) gets swallowed by Git Bash as an escaped
  space, eating the next flag. Use `--out results` (no trailing separator) when
  running through the Bash tool.
- **Orphaned `ngrok.exe` can outlive its Python process.** Check
  `tasklist //FI "IMAGENAME eq ngrok.exe"` and the tunnel's own
  `127.0.0.1:4040/api/tunnels` if a tunnel seems to still be answering after
  you thought you'd stopped it.
