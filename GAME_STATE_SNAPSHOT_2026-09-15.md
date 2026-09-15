# Forge game snapshot — 2026-09-15

This is the persistent baseline for the current full-roadmap pass. It records
the actual source/save state, the local runtimes that were inspected, and the
remaining release gates. It is a snapshot, not a progression mutation.

## Source baseline

- Branch: `feature/cloud-sync-desktop`
- Local and remote HEAD at snapshot time: `772ab8e` (`docs: log React-owned HUD icon verification`)
- Canonical checkout: `/mnt/c/Users/lazar/OneDrive/Documents/ChatGPT/Python Quest Lab`
- The checkout has user-owned working-tree state in `progress.json` and an
  untracked root `tutor.py`. Neither was staged, overwritten, or used as test
  data.
- No Lazi OS files, legacy `progress.json`, Supabase seed, or account data were
  changed for this snapshot.

## Canonical state observed read-only

The canonical `progress.json` currently reports revision 2 and the previously
approved Blackjack reconciliation:

- Level 2; 50 / 100 current XP; 150 lifetime XP; 55 coins;
- HP 100 / 100;
- Blackjack at 38% project progress;
- The Empty Table, The Dealer's Hand and The Count Keeper defeated;
- The Hitman available as the current Mob 3; later mobs locked;
- three Codex encounter records;
- First Blood unlocked;
- Apprentice Coat equipped, no trinket, Apprentice Coder title;
- no validated mastery shield, companion evolution, interview completion or
  unsupported equipment reward was inferred.

The canonical state contains two reconciliation events (revisions 1 and 2).
The second is the idempotent current-quest correction; no reward history was
invented. The workspace/legacy save remains evidence only.

## Runtime map

- The older long-lived Forge on port 5173/backend 7332 still serves
  `/home/lazi/projects/python-tutorial-DiddyDungeon` on `feature/quest-lab-ide`.
  Its shell/AI PTYs were not restarted.
- The current checkout has a separate long-lived verification runtime on
  port 5174/backend 7333. A disposable current-branch runtime on
  `http://127.0.0.1:5183/` (backend 7350) was launched and stopped after the
  latest namespace K&M check; it used an isolated `/tmp` save and workspace.
- No runtime from this pass changed the user's live save or existing PTY
  sessions.

## Confirmed surfaces

- One canonical local state-service authority with revision/event polling;
- live HUD, Character, Homestead, Quest Journal and Codex projections;
- queued state-service reward/event notifications;
- Campaign Tutor Notebook (`tutor.py`) kept separate from Practice;
- Battle submission/verdict boundary with canonical Resolve, HP, Codex and
  mob-clear mutations;
- Infinite Dungeon checkpoint, blank-on-rotation, adaptive local loop,
  rest/market, death reset and local leaderboard foundation;
- independent Practice sessions/history with no Campaign/Dungeon rewards;
- searchable Codex concept/encounter pages and bounded field notes;
- guarded Windows/WSL launcher, upstream freshness diagnostics and executable
  `questlab-state`;
- checkout-scoped browser sync metadata (device identity/label, cursor and
  outbox) using an opaque runtime namespace;
- explicit campaign-loading placeholders so a stale/miswired backend cannot
  masquerade as a Level 1 starter reset;
- read-only local-custody preview through `/api/state/custody` and
  `questlab-state custody`, with no automatic migration;
- monochrome SVG top-stat icons using direct-child stat-pill selectors.

## Latest verification evidence

- WSL backend suite: 66 tests passing.
- Frontend source/runtime suite: 31 tests passing.
- Windows Vite production build: passed.
- Clean ext4 archive: WSL `npm ci` plus Vite build passed after 1,344 modules.
- Browser verification used only click/scroll/type K&M automation. A fresh
  runtime showed Level 2 / 55 XP / 62 coins and all five SVG icons; a typed
  compare-and-swap state-service mutation changed HUD and Character coins to
  63 without refresh. Quest Journal stayed on Mob 3 The Hitman, Codex kept
  validated records, and both shell/AI surfaces stayed `CONNECTED`.
- A clean ext4 K&M runtime showed the explicit campaign-loading guard and
  typed `questlab-state custody` output. Two disposable local roots then
  returned distinct namespaces; mutating device A advanced only A's revision.
- Forge v2 now owns the five top-stat SVG icons in React; K&M showed them
  visible after a live Level 2 projection and after Codex navigation, with no
  emoji fallback or nested stat-pill mutation.

## Remaining release gates

- F-001/F-009/F-010: provider-authenticated adjudication and tab/account-scoped
  challenge storage before hosted learning proof;
- F-018: hosted Dungeon state/leaderboard and cross-device run resume;
- F-025/F-031: the old 5173 process remains an explicitly user-managed stale
  checkout; new launches use the guarded launcher;
- F-033: shared OneDrive `node_modules` still needs Linux-local installation,
  although clean ext4 packaging is proven; the guarded launcher now fails
  early with an actionable native-Rollup message;
- F-034/F-035: WSL Claude CLI auth and dev-only HMR limitation;
- F-039: tracked canonical cache plus OneDrive third-writer custody remains an
  explicit migration decision, not a silent move; launcher opt-in is now
  implemented but real-save approval is still required;
- clean-install/two-device mailbox acceptance, native/Tauri packaging and
  hosted friends/presence/raids remain unstarted or gated.

## Safety boundary

All progression writes continue through the canonical state service. A
workspace `progress.json` is legacy evidence, never a second save. Browser
verification must use keyboard/mouse automation only; Playwright is excluded.
