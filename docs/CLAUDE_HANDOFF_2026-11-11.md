# Quest Lab handoff for Claude — 11 Nov 2026

This is a task-focused summary of the relevant decisions and open work from the
Codex conversation. It is not a verbatim transcript. The original chat remains
the source for older design discussions. No passwords, invitation codes, API
keys, or other credentials are included.

## Current instruction

Lazi asked for a handoff so Claude can take over the current work. The immediate
goal was to get an installed Windows client on PapaSmurff playing PvP against
Lazi's Linux client. Lazi most recently asked to leave the VM open so they can
view it. Do not keep driving the VM unless Lazi asks; the last handoff left its
SPICE view open in the in-app browser.

Keep replies concise and action-focused. Do not claim a match worked until both
clients are in the fight and a real turn exchange has completed.

## Worktree and preservation rules

- Repository/worktree: `/home/lazi/projects/python-tutorial-DiddyDungeon/.claude/worktrees/tauri-arcade`
- Branch: `feature/tauri-arcade`, 173 commits ahead of `origin/feature/tauri-arcade` at last check.
- The worktree is heavily dirty: 67 tracked paths were modified, with many
  existing untracked files and assets. `progress.json` is modified and is the
  user's real save. Do not reset, clean, stash, checkout, or overwrite it. Do
  not stage all files or commit this handoff with unrelated work.
- No code/tests/builds were changed or run for this handoff. Keep this file as
  an isolated, uncommitted addition unless Lazi asks otherwise.
- The repo's top-level `CLAUDE_HANDOFF.md` is older project history; this file
  records the current priorities and VM state.

## Online PvP: what is known

### Product decisions

- Private group for Lazi and two friends; Windows clients for friends and Linux
  for Lazi. Friends should not need Tailscale. PapaSmurff is the always-on
  online host; Tailscale is currently an admin/test path.
- PvP lives under **Colosseum**. The online walkable hub was removed from the
  short-term scope; a simple menu is enough while PvP is finished.
- Keep group and invite labels plain. Modes: unranked/fair, friendly/borrowed
  gear, and ranked/earned gear. The code task is the core of a round; the next
  prompt should build on the code. MCQ and true/false are occasional bonus
  rounds, not the main duel. Keep the arena layout and readable combat HUD.
- Online shop should show **Coming soon** for now rather than opening a black
  screen. Wins can award small online currency while the future raid is the
  primary source. The future online merchant is Sir Getrich and currency is
  Wazi Bucks, but neither is a reason to delay PvP.
- Each account has its own campaign/save. The Windows `codex` test account is
  separate from Lazi's `WAZI` account.

### Windows build and VM

- Candidate installer:
  `.build/tauri-target/x86_64-pc-windows-msvc/release/bundle/nsis/Quest Lab_0.2.0_x64-setup.exe`
- Last checked: 327,089,928 bytes; SHA-256
  `6d23172c482992be876185f9be686d7e01359a028de0c948c69a41d7da58c68f`.
  The installed copy was placed side-by-side at `C:\QLTest`; previous work
  verified that the copied installer matched this candidate. Do not uninstall
  or overwrite the user's other install/save.
- The installer ran and the app opened. The separate Windows Python console
  appeared over the app. Lazi asked whether that console can be hidden and its
  work kept within the app. Yes: suppress the Windows console for the spawned
  backend and keep app output in the app's own terminal/log UI.
- Current source to inspect for that fix:
  `ide/tauri-app/src-tauri/src/lib.rs`, `spawn_backend`. It uses
  `Command::new`, pipes stdout, and sends stderr to a log, but does not apply
  Windows `CREATE_NO_WINDOW` via `std::os::windows::process::CommandExt`.
  Add the Windows-only creation flag and verify packaged Python launch, the
  embedded API, file run/output inside the app, and clean shutdown. Don't close
  the current backend console during a live match if it is still serving the
  app.
- The SPICE stream for PapaSmurff is currently exposed in the browser at
  `http://127.0.0.1:18767/spice.html`; local 18767 uses a temporary loopback-only
  helper, and local SSH forward 18766 reaches PapaSmurff's websockify on 8766.
  The VM is running. The user asked to see it and then to hand off. Do not
  expose or copy the console password; do not change security settings or
  restart the VM. The current view may show the Python console over Quest Lab.
- The test lobby last visibly showed **wazi**, **2/3 online**, with `WAZI` and
  `codex` present and the match service ready. Lazi said they sent a challenge,
  but the Windows view did not reach the duel; no PvP match or turn exchange
  has been verified. A previous attempt to click the visible setup control did
  not produce a verified transition. Don't repeat blind coordinates or open
  Windows Search/Edge. Ask Lazi to take over if UI control is unclear.

### Next PvP acceptance check

Only continue this if Lazi asks Claude to resume the VM test:

1. Confirm both clients remain signed in to their own accounts and are in the
   same `wazi` group; verify both presence entries are online.
2. On the Linux side, send one friendly challenge to `codex`; on Windows,
   accept that actual incoming challenge. Verify the duel screen on both sides.
3. Confirm both players can edit/run their own code, the timer/deadline works,
   and one correct/missed submission produces the expected HP/animation change
   on both clients. Complete at least one chained coding exchange and the
   result/return-to-lobby path. Do not use the user's real save as a test
   fixture.
4. Record exact observed failures and whether they are UI, auth/presence,
   transport, evaluator, or settlement. Do not share the candidate installer
   with friends until the real installed-client flow passes.

Relevant code: `ide/frontend/src/OnlineHideout.jsx` (menu/entry),
`ide/frontend/src/OnlineDuel.jsx` (challenge, incoming challenges, match),
`ide/frontend/src/cloud/onlineDuel.js`, and `ide/server/` online duel routes.
Relevant plans: `docs/online/ONLINE_SECTION_COMPLETION_PLAN.md`,
`docs/online/PVP_AND_HUB.md`, `docs/online/PRIVATE_RELEASE_PLAN.md`, and
`docs/online/FRIENDS_QUICKSTART.md`.

## Combat and art work to carry forward

The user asked that the handoff include the Godot image workflow and remaining
combat work. Keep these as the next art/gameplay backlog after the PvP handoff,
unless Lazi reprioritizes.

### Art direction and workflow

- Maintain the game's Castlevania-inspired pixel style and the hunter's
  established dark-haired, dark-clothed identity. Make real, inspectable art
  assets and animated Godot scenes; do not substitute CSS-drawn props or flat
  placeholder silhouettes for final art.
- Use `prototypes/godot-combat/` as the combat scene/art integration project.
  Read `prototypes/godot-combat/SKIN_WORKFLOW.md` first. It documents the
  weapon sheet layout, anchors, cast origins, import/registration, Godot
  preview/export, and existing animation smoke scripts. Use Godot for scene
  composition, animation timing, lighting/backgrounds, and actual in-game
  preview; use Pixelorama or the existing sheet pipeline where pixel cleanup
  is appropriate. Review frames at game scale for feet, grip, alpha edges,
  bleeding/cropping, and silhouette before importing.
- Avoid heavy GPU use on PapaSmurff's fanless GPU and avoid memory-heavy
  parallel/headless browser runs. Use the Compatibility renderer and small,
  bounded verification steps.

### Specific open combat tasks from the conversation

- Make normal mobs, elites, and bosses visually distinct, with region-specific
  fight backgrounds. User wants the Lantern Vale cast done first; the region
  has since been renamed **Mysterys in Shandumballa**. The campaign boss is
  **Lord Twang III**. Check every existing elite/boss composition and anchor;
  **Endless Echo** was specifically reported as sitting on the floor. Some
  animation cells bleed across frames and need proper cropping.
- Boss phase presentation: no phase label in the HP bar. Change the fill color
  and matching fight-scene frame by phase, growing more intense as phases
  advance. The final interview's HP bar should pulse gently. An HP-bar border is
  only wanted when it matches that phase color.
- Add authored idle, attack, and hurt motion to combatants. Earlier review
  praised the weapon-style prototype but asked for more frames, especially
  mob/boss idle, attacks, and hurt reactions. Keep weapon contact/grip grounded
  and readable; the equipped armour and weapon must match the character art.
- Combat weapon style comes from equipped weapons, not a mode toggle. Current
  project workflow covers sword, staff, whip, greatsword, hand magic, scythe,
  and oil. Make sure a trinket is represented as wearable/effect art, not a
  green floating dot. Add styles/skins through the catalog and the documented
  sheet workflow, not ad-hoc overlays.
- Sparring should look like a simulated environment. Infinite Dungeon and
  campaign fights should use the appropriate floor/region backgrounds while
  retaining the familiar side-by-side combat composition.
- Armour needs genuinely distinct silhouettes, not only recolors. The user
  wants historically inspired sets (including Norse, Roman, and East African)
  and a few playful cosmetics, with tiered variants where appropriate. The
  existing workflow reports 39 armour entries still falling back to shared
  palette/classic art. Prioritize named outfits and clear silhouettes, then
  provide Home walk/idle plus weapon-specific combat poses.
- Treat the latest `SKIN_WORKFLOW.md` as the accurate asset inventory; do not
  assume the conversation's older named previews or the old CLAUDE_HANDOFF are
  fully current.

## Other active/reported UX follow-ups

These are lower priority than the Windows PvP proof and should be rechecked in
the current app before editing:

- Colosseum Shop previously rendered black for Lazi; since the shop is deferred,
  show a deliberate Coming Soon screen instead of a dead route.
- Online account needs editable username and profile picture.
- Forge combat panel: remove or replace the text under the combat scene with a
  short useful hint. Infinite Dungeon should not show its step-by-step guide
  below the combat scene.
- Code hover tips should show variable values/types and function signatures/
  return types. A screenshot showed a tooltip clipped at the editor boundary;
  it should reposition within the viewport.
- Infinite Dungeon: verify elite/mob drops actually enter the run pack and are
  usable; after opening the market or reaching camp, verify the player can
  interact with it again. The player should understand whether an item is
  temporary run gear or a permanent Journal unlock.
- Merchant armor art should depict the actual armor class/outfit; do not use
  generic coats. Selecting an item can show the hunter wearing it with idle or
  attack motion in the detail pane. Weapon previews should likewise show the
  correct equipped weapon.

## Short conversation decision history

- Lazi prefers a playable, reviewable slice over long plans and speculative
  filler. If blocked, report the exact blocker and what was actually observed.
- Online scope is private and invite-only for a few friends, Windows and Linux
  first, no public matchmaking, no need for Tailscale on friends' devices.
- A full online hub was intentionally removed from the near-term PvP release;
  do not reintroduce it unless asked. The retained product names are Shax
  Champions House (future hub) and Colosseum (current PvP page).
- The user has authorized testing the disposable `codex` account on the VM and
  using the VM as a test device, but the most recent instruction is to leave
  the VM visible for them and hand this work to Claude.
- Never expose secrets or the invitation code in this file, screenshots,
  console output, or future test instructions. Do not edit `progress.json`.

