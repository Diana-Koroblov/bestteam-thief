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

## Open — does NOT block a match from running, affects whether we win

- **The advanced Cop self-separates from the advanced Thief 6/48 times**
  (`test_the_cop_never_walls_itself_away_from_the_thief`, in
  `test_advanced_league_benchmark.py`, the 192-sub-game slow suite —
  `uv run pytest tests/integration/test_advanced_league_benchmark.py -m slow`).
  Same run: advanced-cop-vs-advanced-thief is currently 48/48 survivals — the
  advanced Cop never catches a Thief that plays like ours does. A
  self-separated or lost sub-game still completes and audits cleanly, so it
  does not stop a match from running or block the count of matches played —
  it costs points, not participation. Deliberately parked, not chased, on
  2026-08-18 to prioritize getting tomorrow's match running first.

  **Root cause, actually traced 18/08 (opening cop=(2,1)/thief=(4,5)), and it
  is narrower than it first looked.** It is NOT the barrier-placement guard in
  `barrier_policy.rejection_for` — tried adding a geometric self-trap check
  there (refuse a wall that shrinks the Cop's own reachable region below a
  floor), reverted it after re-running the exact reproduction: the trace was
  byte-identical, because the wall in question (`(2,6)`) does not geometrically
  trap the Cop at the moment it is placed — cell `(3,6)` is still open. **The
  actual mistake is one turn later, in ordinary movement, not in barrier
  placement**: from `(2,6)`, the Cop's expectimax search chose to step to
  `(1,6)` — a dead end, since `(2,6)` is now barriered and cannot be
  re-entered — over `(3,6)`, which stays connected to the rest of the board.
  Almost certainly stale belief: the Thief had already slipped out of the area
  the Cop was still weighting heavily, so the move toward `(1,6)` scored well
  against a belief that was one step behind reality, and by the next scent
  reading the mistake was already irreversible. A real fix would need to touch
  move evaluation under a just-placed wall (e.g. penalise a move that cannot
  be undone if it is not corroborated by *current* observation), not the
  barrier guard — more involved and riskier to get right before tomorrow than
  time allows to also re-verify on the full 48-opening benchmark. Still
  parked; this entry replaces the guess in the previous version with what was
  actually confirmed.

## Operational gotchas learned the hard way tonight (not code bugs)

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
