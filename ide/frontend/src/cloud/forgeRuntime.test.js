import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = (relativeUrl) => readFileSync(new URL(relativeUrl, import.meta.url), 'utf8')

test('Monaco is bundled locally with local Vite workers and no CDN loader', () => {
  const main = source('../main.jsx')
  const packageJson = JSON.parse(source('../../package.json'))

  assert.ok(packageJson.dependencies['monaco-editor'])
  assert.match(main, /loader\.config\(\{ monaco \}\)/)
  assert.match(main, /monaco-editor\/esm\/vs\/editor\/editor\.worker\?worker/)
  assert.match(main, /MonacoEnvironment\s*=\s*\{/)
  assert.doesNotMatch(main, /https?:\/\/[^\s'"`]*(jsdelivr|unpkg|cdnjs)/i)
})

test('terminal cosmetics update in place without changing the PTY lifecycle key', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /\}, \[role, banner\]\)/)
  assert.match(app, /term\.options\.fontSize\s*=\s*fontSize/)
  assert.match(app, /term\.options\.theme\s*=\s*terminalPalette\(skin\)/)
})

test('dev hot refresh rebinds terminals without closing the PTY session', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /__QUESTLAB_TERMINAL_SESSIONS__/)
  assert.match(app, /session\.consumer\s*=\s*\{/)
  assert.match(app, /scheduleTerminalDetach\(session\)/)
  assert.match(app, /connectTerminalSession\(session, banner\)/)
  assert.match(app, /if \(session\.consumer\?\.term === term\) session\.consumer = null/)
})

test('tutor polling distinguishes clean updates from dirty external conflicts', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /window\.setInterval\(pollTutor, 1000\)/)
  assert.match(app, /PYR updated tutor\.py/)
  assert.match(app, /Reload external version/)
  assert.match(app, /Keep my edits/)
})

test('campaign projections use revision polling and state-service events', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const combat = source('../combatShell.js')

  assert.match(app, /\/api\/state\/revision/)
  assert.match(app, /window\.setInterval\(pollCampaignRevision, 1000\)/)
  assert.match(app, /state_events/)
  assert.match(app, /questlab:campaign-updated/)
  assert.match(app, /<RewardQueue items=\{rewardQueue\} \/>/)
  assert.match(views, /data-testid="forge-encounter-resolve"/)
  assert.match(views, /progress\.codex\?\.encounters/)
  assert.match(views, /data-campaign-revision=\{revision\}/)
  assert.match(combat, /questlab:campaign-updated/)
  assert.doesNotMatch(combat, /setInterval\(refreshCampaignIfChanged/)
  assert.doesNotMatch(combat, /fetch\('\/api\/state\/revision'/)
  assert.match(combat, /React owns the Character, Homestead and Quest Journal surfaces now/)
  assert.doesNotMatch(combat, /function render\(\) \{\s*renderCharacterGear\(\)\s*renderQuestBattleShell\(\)/)
  assert.doesNotMatch(views, /mob\.encounter \|\| 'This encounter has not revealed/)
})

test('campaign loading never presents starter values as a reset', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const legacy = source('../App.jsx')

  assert.match(app, /const campaignReady = Boolean\(campaign && campaign\.progress/)
  assert.match(app, /campaignReady \? `LV \$\{player\.level/)
  assert.match(app, /campaignReady \? `\$\{player\.coins \?\? 0\}c` : '—'/)
  assert.match(app, /campaignReady \? `\$\{player\.xp \?\? 0\}/)
  assert.match(app, /Syncing campaign state/)
  assert.match(views, /data-testid="campaign-loading"/)
  assert.match(views, /No starter values are being substituted/)
  assert.match(views, /campaignReady = true/)
  assert.match(legacy, /const campaignReady = Boolean\(campaign && campaign\.progress/)
  assert.match(legacy, /campaignReady \? `LV \$\{player\.level/)
  assert.match(legacy, /: 'SYNCING'/)
  assert.match(legacy, /function LegacyStatIcon/)
  assert.match(legacy, /campaignReady=\{campaignReady\}/)
  assert.doesNotMatch(legacy, /♥ \{player\.hp \?\? 100\}/)
})

test('launcher marks the frontend bundle so stale UI cannot appear healthy', () => {
  const app = source('../AppV2.jsx')
  const vite = source('../../vite.config.js')
  const quest = source('../../../quest.py')

  assert.match(app, /FRONTEND_BUILD_SHA = typeof __QUESTLAB_BUILD_SHA__ === 'string'/)
  assert.match(app, /runtimeBuildMismatch/)
  assert.match(app, /FRONTEND STALE · restart current launcher/)
  assert.match(app, /data-frontend-build-sha=\{FRONTEND_BUILD_SHA \|\| 'unmarked'\}/)
  assert.match(vite, /QUESTLAB_BUILD_SHA/)
  assert.match(vite, /__QUESTLAB_BUILD_SHA__/)
  assert.match(vite, /execFileSync\('git'/)
  assert.match(vite, /rev-parse.*HEAD/)
  assert.match(quest, /def checkout_head_sha\(root: Path\)/)
  assert.match(quest, /env\["QUESTLAB_BUILD_SHA"\] = checkout_head_sha\(REPO_ROOT\)/)
})

test('manual Vite launches still stamp the current checkout when no env marker is supplied', () => {
  const vite = source('../../vite.config.js')

  assert.match(vite, /const repoRoot = path\.resolve\(projectDir, '\.\.', '\.\.'/)
  assert.match(vite, /process\.env\.QUESTLAB_BUILD_SHA \|\| \(\(\) => \{/)
  assert.match(vite, /execFileSync\('git', \['-C', repoRoot, 'rev-parse', '--verify', 'HEAD'\]/)
  assert.match(vite, /timeout: 1_000/)
})

test('PYR context submissions use the bounded local bridge and current editor selection', () => {
  const app = source('../AppV2.jsx')
  const enhancements = source('../forgeEnhancements.js')
  const pyrClient = source('./pyrClient.js')

  assert.match(app, /\/api\/pyr\/context/)
  assert.match(app, /client_id: pyrClientId\(\)/)
  assert.match(enhancements, /client_id: pyrClientId\(\)/)
  assert.match(pyrClient, /questlab\.pyr\.client-id/)
  assert.match(pyrClient, /sessionStorage/)
  assert.match(app, /editorSelectionRef\.current/)
  assert.match(app, /getText\(\)/)
  assert.match(app, /__questlabPublishPyrContext/)
  assert.match(enhancements, /requestPyrContext/)
  assert.match(enhancements, /contextPrompt/)
  assert.match(enhancements, /Validated current quest\/mob state/)
  assert.match(enhancements, /\/api\/pyr\/verdict/)
  assert.match(enhancements, /Battle verdict challenge/)
  assert.match(enhancements, /battle-submission/)
  assert.match(enhancements, /active_file/)
  assert.match(enhancements, /git\?\.diff/)
})

test('provider launch unlocks bounded Tutor/Practice requests for this tab', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /sessionStorage\.setItem\('questlab\.aiProvider', command\)/)
  assert.match(app, /const provider = sessionStorage\.getItem\('questlab\.aiProvider'\)/)
  assert.match(app, /Practice drill requested from \$\{provider\}/)
})

test('GitHub Copilot CLI is an available raw provider without becoming a state authority', () => {
  const app = source('../AppV2.jsx')
  const server = source('../../../server/app_v2.py')
  const commandPalette = source('../commandPalette.js')
  const enhancements = source('../forgeEnhancements.js')
  const state = source('../../../server/state.py')

  assert.match(app, /commands\.copilot === false/)
  assert.match(app, /summon\('copilot'\)/)
  assert.match(app, />Copilot<\/button>/)
  assert.match(app, /Choose Codex, Claude, AGY, or Copilot above\./)
  assert.match(server, /"copilot": command_available\("copilot"\)/)
  assert.match(commandPalette, /Launch Copilot CLI/)
  assert.match(enhancements, /'Copilot'/)
  assert.doesNotMatch(state, /copilot.*reward|reward.*copilot/i)
})

test('Forge binds the active campaign file before provider adjudication', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')

  assert.match(app, /const forgeSubmission = \(\) =>/)
  assert.match(app, /answer_source: 'forge_active_file'/)
  assert.match(app, /source_path: forge\.path/)
  assert.match(app, /file_digest: context\?\.active_file\?\.digest/)
  assert.match(app, /pasteAiPrompt/)
  assert.match(app, /File sent|Battle answer sent to/)
  assert.match(app, /Bounded Quest Lab context/)
  assert.match(app, /Active Forge file \(\$\{forge\.path/)
  assert.match(app, /const submitCampaignRun = async/)
  assert.match(app, /__questlabSubmitCampaignRun/)
  assert.match(views, /data-testid="forge-document-tabs"|className="forge-document-tabs"/)
  assert.match(views, /quest\.md <small>STATE VIEW<\/small>/)
  assert.match(views, /data-testid="pyr-sidebar-companion"/)
  assert.doesNotMatch(views, /data-testid="forge-file-submission"/)
  assert.doesNotMatch(views, /Submit current Forge file to PYR/)
  assert.doesNotMatch(views, /battle-answer-editor/)
  assert.doesNotMatch(views, /function BattleSubmission/)
})

test('Forge left panel can collapse to file shortcuts and restore its drawable encounter view', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(app, /const \[leftPanelCollapsed, setLeftPanelCollapsed\] = usePersistentState\('questlab\.leftPanelCollapsed', false\)/)
  assert.match(app, /const leftPanelColumns = leftPanelCollapsed \? '76px 5px'/)
  assert.match(app, /compact=\{leftPanelCollapsed\}/)
  assert.match(app, /onToggleCompact=\{\(\) => setLeftPanelCollapsed/)
  assert.match(views, /data-testid="forge-compact-panel"/)
  assert.match(views, /Open quest\.md state view/)
  assert.match(views, /Compact Forge sidebar/)
  assert.match(views, /Expand Forge sidebar/)
  assert.match(views, /onClick=\{\(\) => setActiveView\('tutor'\)\} title="Open Tutor Notebook"/)
  assert.match(views, /className="sidebar-collapse-toggle"/)
  assert.match(views, /className="forge-compact-expand"[\s\S]*?className=\{`forge-compact-file/)
  assert.match(foundation, /\.forge-compact-panel \{ display: flex;/)
  assert.match(foundation, /\.forge-compact-file\.active/)
  assert.match(foundation, /\.campaign-battle-sidebar \.pyr-sidebar-companion \{ margin: 30px auto 24px;/)
  assert.match(foundation, /\.campaign-battle-sidebar \.pyr-pixel-character, \.campaign-battle-sidebar \.pyr-pixel-character svg \{ width: 44px; height: 44px;/)
})

test('Tutor and Infinite Dungeon can collapse to a slim route rail', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /function ContextCompactPanel/)
  assert.match(views, /data-testid=\{`\$\{mode\}-compact-panel`\}/)
  assert.match(views, /title=\{`Compact \$\{label\} sidebar`\}/)
  assert.match(views, /title=\{`Expand \$\{label\} sidebar`\}/)
  assert.match(views, /if \(compact && collapsibleContext\) return <ContextCompactPanel/)
  assert.match(views, /activeView !== 'dungeon' && <button onClick=\{\(\) => setActiveView\('forge'\)\}/)
  assert.match(views, /activeView === 'dungeon' && <ContextCollapseButton label="Dungeon"/)
  assert.match(foundation, /\.context-compact-file \{ cursor: default;/)
  assert.match(foundation, /\.panel-title-actions > button svg/)
  assert.match(foundation, /\.forge-compact-expand \{ margin: 0 0 8px;/)
  assert.doesNotMatch(foundation, /\.forge-compact-expand \{ margin-top: auto;/)
})

test('Forge boot has a short fade-in with reduced-motion and preference fallbacks', () => {
  const foundation = source('../foundation.css')

  assert.match(foundation, /\.app-shell \{ animation: questlab-boot-in \.36s ease-out both; \}/)
  assert.match(foundation, /@keyframes questlab-boot-in/)
  assert.match(foundation, /prefers-reduced-motion: reduce/)
  assert.match(foundation, /\.app-shell\.no-animations \{ animation: none !important; \}/)
})

test('PYR companion has a restrained pet idle loop, lower boss-gate placement, and motion-safe fallback', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')
  const v2 = source('../v2.css')

  assert.match(views, /data-pyr-motion="idle"/)
  assert.match(views, /className="pyr-eye pyr-eye-left"/)
  assert.match(views, /className="pyr-eye pyr-eye-right"/)
  assert.match(foundation, /@keyframes pyr-float/)
  assert.match(foundation, /@keyframes pyr-blink/)
  assert.match(foundation, /prefers-reduced-motion: reduce/)
  assert.match(foundation, /\.no-animations \.pyr-pixel-character, \.no-animations \.pyr-eye \{ animation: none !important;/)
  assert.match(v2, /data-boss-gate="true"\][\s\S]*?\.campaign-battle-sidebar \.pyr-sidebar-companion \{[\s\S]*?margin-top: auto;/)
})

test('Dungeon checkpoints and Practice remain separate learning modes', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')

  assert.match(app, /\/api\/dungeon\/start/)
  assert.match(app, /\/api\/dungeon\/editor/)
  assert.match(app, /\/api\/pyr\/dungeon-submission/)
  assert.match(app, /\/api\/pyr\/dungeon-verdict/)
  assert.match(app, /\/api\/practice\/session/)
  assert.match(app, /\/api\/pyr\/practice-submission/)
  assert.match(app, /\/api\/pyr\/practice-verdict/)
  assert.match(app, /question_id: questionId/)
  assert.match(app, /saveDungeon/)
  assert.match(app, /dungeonSaving/)
  assert.match(app, /activeView === 'dungeon'/)
  assert.match(views, /data-testid="dungeon"/)
  assert.match(views, /dungeon\.py · current room buffer/)
  assert.match(views, /data-testid="practice"/)
  assert.match(views, /Practice is unlimited and separate from Campaign and Dungeon/)
  assert.match(views, /Submit to PYR/)
  assert.match(views, /RECENT PRACTICE HISTORY/)
  assert.match(views, /id: 'tutor', label: 'Tutor Notebook'/)
  assert.doesNotMatch(views, /<option value="python-basics">python-basics<\/option>/)
  assert.match(app, /Tutor Notebook and Practice intentionally share one tutor\.py IDE surface/)
  assert.match(app, /\/api\/tutor\/format/)
})

test('Dungeon exposes a state-preserving map and editable code-editor tab', () => {
  const views = source('../RpgViews.jsx')

  assert.match(views, /role="tablist" aria-label="Dungeon workspace"/)
  assert.match(views, /Map & route/)
  assert.match(views, /Code editor/)
  assert.match(views, /dungeon-tab-panel/)
  assert.match(views, /dungeon\.py · current room buffer/)
  assert.match(views, /Open code editor/)
})

test('Dungeon main route keeps prototype proportions and owns the page scroll', () => {
  const views = source('../RpgViews.jsx')
  const v2 = source('../v2.css')

  assert.match(views, /dungeon-class-card-top/)
  assert.match(views, /dungeon-class-weapon/)
  assert.match(views, /dungeon-class-passive/)
  assert.match(views, /dungeon-class-cta/)
  assert.match(views, /viewBox="0 0 100 120"/)
  assert.match(v2, /F-225: the canonical Dungeon route is a state-backed port/)
  assert.match(v2, /\.forge-v2\.dungeon-mode \.game-screen \{[\s\S]*?overflow-y: auto;/)
  assert.match(v2, /grid-template-columns: minmax\(300px, \.92fr\) minmax\(390px, 1\.14fr\) minmax\(285px, \.84fr\)/)
  assert.match(v2, /grid-template-rows: repeat\(8, 54px\)/)
  assert.match(v2, /\.forge-v2\.dungeon-mode \.dungeon-class-card \{[\s\S]*?min-height: 340px;/)
  assert.match(v2, /\.forge-v2\.dungeon-mode \.dungeon-workspace-tabs \{ display: none; \}/)
})

test('navigation keeps Tutor as the single practice workspace and uses one app-level menu', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const v2 = source('../v2.css')
  const foundation = source('../foundation.css')
  const palette = source('../commandPalette.js')

  assert.match(app, /const normalizeView = \(value\) => value === 'practice' \? 'tutor' : value === 'quests' \? 'codex' : value/)
  assert.doesNotMatch(app, /value === 'dungeon' \? 'forge'/)
  assert.match(app, /return normalizeView\(candidate\)/)
  assert.doesNotMatch(views, /id: 'practice', icon:/)
  assert.doesNotMatch(palette, /Open Quest Journal/)
  assert.match(app, /gridStyle = wideSurface\s*\? \{/)
  assert.match(app, /const wideSurface = \['hub', 'character', 'homestead', 'codex', 'settings'\]/)
  assert.match(app, /import \{ buildQuestDocument, ContextPanel, GameScreen, RewardQueue, SurfaceNavigation, TutorPracticeBar \}/)
  assert.match(app, /<SurfaceNavigation activeView=\{activeView\} onNavigate=\{setActiveView\} \/>/)
  assert.doesNotMatch(app, /!wideSurface && <ActivityRail/)
  assert.match(views, /data-testid="wide-route-nav"/)
  assert.match(views, /aria-label="Wide route navigation"/)
  assert.match(views, /data-wide-route=\{activeView\}/)
  assert.match(views, /<SurfaceNavigation activeView="codex" onNavigate=\{onNavigate\} \/>/)
  assert.match(views, /const wideRoute = \['hub', 'character', 'homestead', 'codex', 'settings'\]/)
  assert.match(views, /purchaseCosmetic, equipCosmetic, equipCampaignItem, saveCodexNote/)
  assert.match(foundation, /\.surface-nav \{ position: sticky;/)
  assert.match(views, /withWideNavigation/)
  assert.match(views, /function RouteIcon\(/)
  assert.match(views, /className="activity-rail" data-react-owned="true"/)
  assert.doesNotMatch(views, /icon:\s*['"`]/)
  assert.match(foundation, /\.wide-screen-frame > \.game-screen-scroll/)
  assert.match(foundation, /\.wide-screen-frame > \.codex-screen \{ flex: 1 1 auto; min-height: 0; height: auto; \}/)
  assert.match(foundation, /\.surface-nav-link\.active/)
  assert.match(foundation, /\.surface-nav-link > span:first-child svg/)
  assert.match(app, /aiGridVisible\s*\?\s*`0px \$\{leftPanelColumns\}/)
  assert.match(app, /aiGridVisible\s*\?\s*''\s*:\s*aiPopoverOpen/)
  assert.match(v2, /ai-panel-parked/)
  assert.match(v2, /wide-mode \.game-screen\{grid-column:1/)
  assert.match(v2, /hub-mode \.game-screen\{grid-column:1/)
  assert.match(app, /initialLaunch\.returning \? `Welcome back, \$\{welcomeName\}`/)
  assert.match(foundation, /questlab-splash-in/)
  assert.match(v2, /F-176: route navigation is one app-level surface/)
})

test('wide settings never inherits the Forge rail and the level HUD stays centered', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const v2 = source('../v2.css')

  assert.match(app, /const wideSurface = \['hub', 'character', 'homestead', 'codex', 'settings'\]/)
  assert.match(views, /const wideRoute = \['hub', 'character', 'homestead', 'codex', 'settings'\]/)
  assert.match(v2, /F-185: keep the level\/title\/XP strip on the page centre line/)
  assert.match(v2, /\.forge-v2 \.topbar \{[\s\S]*display: grid;[\s\S]*grid-template-columns: minmax\(165px, 1fr\) minmax\(0, min\(360px, 35vw\)\) minmax\(0, 1fr\)/)
  assert.match(v2, /\.forge-v2 \.topbar \.hud-xp \{ justify-self: center;/)
})

test('Forge-first rail keeps the locked route order', () => {
  const views = source('../RpgViews.jsx')
  const expected = [
    "{ id: 'hub', label: 'Quest Hub' }",
    "{ id: 'forge', label: 'Forge' }",
    "{ id: 'tutor', label: 'Tutor Notebook' }",
    "{ id: 'dungeon', label: 'Infinite Dungeon' }",
    "{ id: 'codex', label: 'Codex' }",
    "{ id: 'character', label: 'Character' }",
    "{ id: 'homestead', label: 'Homestead' }",
    "{ id: 'settings', label: 'Settings' }",
  ]
  const start = views.indexOf('export const viewItems')
  const rail = views.slice(start, views.indexOf(']', start) + 1)
  assert.deepEqual(expected, expected.filter((item) => rail.indexOf(item) >= 0).sort((a, b) => rail.indexOf(a) - rail.indexOf(b)))
  assert.equal(rail.includes("{ id: 'practice'"), false)
  assert.equal(rail.includes("{ id: 'dungeon'"), true)
})

test('splash idle timing follows real activity instead of a background heartbeat', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /const LAUNCH_IDLE_MS = 20 \* 60 \* 1000/)
  assert.match(app, /window\.addEventListener\('pointerdown', onActivity/)
  assert.match(app, /window\.addEventListener\('keydown', onActivity/)
  assert.doesNotMatch(app, /window\.setInterval\(touch, 60_000\)/)
})

test('legacy shell wires wide-route navigation back to the active view', () => {
  const legacy = source('../App.jsx')
  assert.match(legacy, /<GameScreen[\s\S]*onNavigate=\{setActiveView\}[\s\S]*campaignReady=\{campaignReady\}/)
  assert.match(legacy, /value === 'quests' \? 'codex'/)
})

test('Hub and legacy quest context hide locked future identities behind silhouettes', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /mob\.status === 'locked' \? 'Unknown encounter' : mob\.name/)
  assert.match(views, /locked \? 'Unknown chapter' : project\.name/)
  assert.match(views, /locked \? 'Hidden until previous clear' : mob\.category/)
  assert.match(views, /mob\.status === 'locked' \? 'Unknown encounter' : mob\.name/)
  assert.match(foundation, /F-151: future chapters and encounters stay silhouettes/)
  assert.match(foundation, /\.chapter-card\.locked \.chapter-art,[\s\S]*?\.encounter-silhouette\.locked > span/)
})

test('legacy rail icon enhancement yields to the React-owned SVG rail', () => {
  const views = source('../RpgViews.jsx')
  const enhancements = source('../forgeEnhancements.js')
  assert.match(views, /data-react-owned="true"/)
  assert.match(enhancements, /const reactRail = document\.querySelector\('\.activity-rail\[data-react-owned="true"\]'\)/)
  assert.match(enhancements, /if \(reactRail\) return/)
})

test('Forge and Codex keep the active encounter projection visible without Battle Shell UI', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /data-testid="forge-encounter-resolve"/)
  assert.match(views, /buildQuestDocument\(campaign\)/)
  assert.match(views, /encounter\.mob\?\.lore/)
  assert.match(views, /reward_envelope/)
  assert.match(views, /quest\.md <small>STATE VIEW<\/small>/)
  assert.match(views, /data-testid="pyr-sidebar-companion"/)
  assert.doesNotMatch(views, /data-testid="forge-file-submission"/)
  assert.match(views, /data-testid="codex-active-quest"/)
  assert.match(views, /data-testid="codex-folio-controls"/)
  assert.doesNotMatch(views, /data-testid="codex-mode-tabs"/)
  assert.doesNotMatch(views, /data-testid="quest-battle-screen"/)
  assert.doesNotMatch(views, /journal-mode-tabs/)
  assert.match(views, /className="codex-screen"/)
  assert.match(views, /data-testid="codex-mastery"/)
  assert.match(views, /function Codex\(\{ progress, revision, codexProjection, encounter, saveCodexNote/)
  assert.doesNotMatch(views, /id: 'quests', label:/)
  assert.match(app, /value === 'quests' \? 'codex'/)
  assert.match(views, /data-testid="dungeon-inventory"/)
  assert.match(views, /onEquip=\{onDungeonEquip\}/)
  assert.match(app, /\/api\/dungeon\/equip/)
  assert.match(foundation, /quest-journal-screen \.journal-page \{ grid-template-columns: minmax\(0, 1fr\); \}/)
  assert.match(foundation, /\.codex-screen \{ display: grid; grid-template-rows: auto auto minmax\(0, 1fr\);/)
  assert.match(foundation, /\.codex-screen > \.codex-tab-page \{ display: flex; min-height: 0; overflow: hidden;/)
  assert.match(foundation, /\.codex-screen \.codex-book-page \{ display: flex; flex-direction: column; min-height: 0; overflow: hidden;/)
  assert.match(foundation, /\.codex-book-section \{ flex: 1 1 auto; min-height: 0; overflow-y: auto;/)
  assert.match(foundation, /\.codex-screen \{ grid-template-rows: auto auto minmax\(0, 1fr\); height: 100%; min-height: 0; overflow: hidden;/)
  assert.doesNotMatch(foundation, /\.codex-screen \.codex-book-page \{ min-height: 0; overflow-y: auto;/)
  assert.doesNotMatch(foundation, /\.codex-screen \{ grid-template-rows: auto auto auto; height: auto; overflow: auto;/)
  assert.match(views, /data-testid="codex-book-tabs"/)
  assert.match(views, /data-testid="codex-page-controls"/)
  assert.match(views, /data-codex-folio=\{readSubpage\}/)
  assert.match(views, /<section className="codex-book-section codex-mastery-panel" data-testid="codex-mastery">/)
  assert.match(views, /data-testid="workspace-transfer"/)
  assert.match(app, /\/api\/workspace-transfer/)
  assert.match(app, /onWorkspaceTransferApplyPull/)
})

test('Codex book surface keeps readable paper hierarchy across themes', () => {
  const foundation = source('../foundation.css')

  assert.match(foundation, /\.codex-screen \.codex-library \{\r?\n  border-radius: 16px;/)
  assert.match(foundation, /\.codex-screen \.codex-book-page \{\r?\n  position: relative;/)
  assert.match(foundation, /\.codex-screen \.codex-page-heading h3,[\s\S]*?font-family: inherit;/)
  assert.match(foundation, /\.codex-screen \.codex-examples pre \{[\s\S]*?color: var\(--text\);[\s\S]*?border-left: 3px solid/)
  assert.doesNotMatch(foundation, /\.codex-screen \.codex-examples pre \{[\s\S]*?background: #090b09/)
})

test('Codex final cascade has one bounded reading owner instead of an outer feed', () => {
  const foundation = source('../foundation.css')

  assert.match(foundation, /F-154: final Codex reader contract/)
  assert.match(foundation, /\.game-screen > \.codex-screen \{[\s\S]*?position: absolute;[\s\S]*?overflow: hidden;/)
  assert.match(foundation, /\.game-screen > \.codex-screen > \.codex-tab-page\[data-codex-tab="books"\] \.codex-book-section \{[\s\S]*?overflow-y: auto;/)
  assert.match(foundation, /\.game-screen > \.codex-screen > \.codex-tab-page\[data-codex-tab="books"\] \.codex-page-list \{[\s\S]*?overflow: visible;/)
  assert.match(foundation, /\.game-screen > \.codex-screen > \.codex-tab-page\[data-codex-tab="books"\] \.codex-index \{[\s\S]*?overflow: hidden;/)
})

test('Codex stays a bounded book surface instead of growing an outer feed', () => {
  const foundation = source('../foundation.css')

  assert.match(foundation, /\.game-screen \{ position: relative; width: 100%; height: 100%; min-width: 0; min-height: 0; overflow: hidden; \}/)
  assert.match(foundation, /\.game-screen > \.codex-screen \{[\s\S]*?position: absolute;[\s\S]*?inset: 0;[\s\S]*?overflow: hidden;[\s\S]*?contain: layout paint;/)
  assert.match(foundation, /\.codex-screen \.codex-book-section \{[\s\S]*?overflow-y: auto;[\s\S]*?scrollbar-gutter: stable;/)
  assert.match(foundation, /\.codex-screen \.codex-index \{ display: flex; flex-direction: column; min-width: 0; min-height: 0; overflow: hidden;/)
  assert.match(foundation, /\.codex-screen \.codex-page-list \{ flex: 1 1 auto; min-height: 0; max-height: none; overflow-y: auto;/)
})

test('Codex owns its viewport shell instead of inheriting the generic feed wrapper', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /<div className="codex-screen" data-testid="codex"/)
  assert.doesNotMatch(views, /className="game-screen-scroll codex-screen"/)
  assert.match(foundation, /\.game-screen > \.codex-screen \{[\s\S]*?padding: 18px;[\s\S]*?overscroll-behavior: none;/)
  assert.match(foundation, /\.codex-screen \.codex-book-section \{[\s\S]*?overflow-x: hidden;/)
})

test('Codex finite reading room keeps header and book frame bounded', () => {
  const foundation = source('../foundation.css')

  assert.match(foundation, /F-130: the Codex is a finite reading room/)
  assert.match(foundation, /\.game-screen > \.codex-screen \{[\s\S]*?grid-template-rows: auto auto minmax\(0, 1fr\);[\s\S]*?gap: 10px;/)
  assert.match(foundation, /\.codex-screen > \.screen-hero \{[\s\S]*?grid-template-columns: minmax\(0, 1fr\) minmax\(300px, auto\);[\s\S]*?max-height: none;/)
  assert.match(foundation, /\.codex-screen > \.codex-tab-page \{[\s\S]*?width: 100%;[\s\S]*?min-height: 0;/)
})

test('Codex bookshelf uses finite pages and a calmer reading-room hierarchy', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /data-testid="codex-shelf-controls"/)
  assert.match(views, /const bookShelfPageSize = 5/)
  assert.match(views, /shelfPages\.map\(\(page\)/)
  assert.match(views, /const bookPages = normalizedQuery \? filteredPages : pages/)
  assert.match(views, /data-testid="codex-chapter-select"/)
  assert.match(foundation, /F-133: make the Codex a quiet reading room/)
  assert.match(foundation, /\.codex-screen \.codex-page-list \{[\s\S]*?overflow: visible;/)
  assert.match(foundation, /\.codex-shelf-controls \{[\s\S]*?grid-template-columns: 23px auto 23px;/)
  assert.match(foundation, /\.codex-screen \.codex-book-page::before \{[\s\S]*?background: color-mix/)
})

test('Codex mastery and companion surfaces keep the SVG icon language', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.doesNotMatch(views, /[🔥🛡]/)
  assert.match(views, /skill\.shield\?\.tier !== 'none' \? 'shield' : 'codex'/)
  assert.match(views, /<RouteIcon id="flame" \/>/)
  assert.match(foundation, /\.skill-icon svg,[\s\S]*?\.pyr-orb svg,[\s\S]*?\.homestead-hearth > svg/)
})

test('Character and Homestead props keep the shared SVG icon language', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.doesNotMatch(views, /[◈✦♛⌨]/)
  assert.match(views, /RouteIcon id="spark"/)
  assert.match(views, /RouteIcon id="window"/)
  assert.match(views, /RouteIcon id="forge" \/>/)
  assert.match(foundation, /F-134: extend the shared 24px monochrome icon grid/)
  assert.match(foundation, /\.equipment-list > div > span svg,[\s\S]*?\.homestead-shelf > svg/)
})

test('Codex evidence stays in a finite page frame with explicit record paging', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /entryShelfPageSize = 3/)
  assert.match(views, /data-testid="codex-entry-pager"/)
  assert.match(views, /visibleEntries\.map\(\(entry\)/)
  assert.match(views, /data-testid="codex-notes-entry-pager"/)
  assert.match(foundation, /F-135: keep the Codex a finite reader/)
  assert.match(foundation, /\.codex-screen \.codex-book-section \{[\s\S]*?overflow-y: auto;/)
  assert.match(foundation, /\.codex-entry-pager \{[\s\S]*?letter-spacing: \.08em;/)
})

test('route, quest and Dungeon markers use the shared SVG vocabulary', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.doesNotMatch(views, /[✓○◌◆◇◐⌘]/)
  for (const icon of ['check', 'target', 'lock', 'plus']) assert.match(views, new RegExp(`['"]${icon}['"]`))
  assert.match(foundation, /F-136: finish SVG parity on route, quest and Dungeon markers/)
  assert.match(foundation, /\.dungeon-map-node > span svg,[\s\S]*?\.panel-title > button svg/)
})

test('Codex active quest rail stays compact while preserving chapter selection', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /data-testid="codex-chapter-select"/)
  assert.match(views, /Choose campaign chapter/)
  assert.match(views, /setSelectedChapterId\(event\.target\.value\)/)
  assert.doesNotMatch(views, /className="codex-chapter-list"/)
  assert.doesNotMatch(foundation, /\.codex-chapter-list/)
  assert.match(foundation, /F-137: keep the active-quest rail compact/)
  assert.match(foundation, /\.codex-screen \.codex-chapter-select select \{[\s\S]*?min-height: 31px;/)
})

test('Codex folio has no unbounded reading scroll and pages mastery records', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /const masteryPageSize = 4/)
  assert.match(views, /data-testid="codex-mastery-pager"/)
  assert.match(views, /visibleSkills\.map\(\(skill\)/)
  assert.match(foundation, /F-139: the Codex is a folio, not a social feed/)
  assert.match(foundation, /\.codex-screen \.codex-book-section \{[\s\S]*?overflow: hidden;[\s\S]*?scrollbar-width: none;/)
  assert.match(foundation, /\.codex-screen \.codex-page-grid \{[\s\S]*?overflow: hidden;/)
  assert.match(foundation, /\.codex-screen \.codex-book-section::-webkit-scrollbar \{ display: none; \}/)
})

test('Codex folio fits the Forge viewport without inheriting the legacy 520px feed height', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /className="screen-hero codex-hero"/)
  assert.match(views, /<h2>Codex<\/h2>/)
  assert.match(foundation, /F-141: the Codex is a compact folio/)
  assert.match(foundation, /\.codex-screen > \.codex-tab-page,\s*\.codex-screen > \.codex-tab-page\[data-codex-tab="books"\] \{[\s\S]*?height: 100%;[\s\S]*?overflow: hidden;/)
  assert.match(foundation, /\.codex-screen > \.codex-tab-page\[data-codex-tab="battle"\] \{[\s\S]*?display: block;[\s\S]*?overflow: auto;/)
  assert.match(foundation, /\.codex-screen \.codex-library \{[\s\S]*?min-height: 0;[\s\S]*?height: 100%;[\s\S]*?margin-bottom: 0;/)
  assert.match(foundation, /\.codex-screen \.codex-book-section \{[\s\S]*?flex: 1 1 0;[\s\S]*?height: auto;/)
})

test('Codex shared library primitive cannot reintroduce a feed-sized minimum', () => {
  const foundation = source('../foundation.css')
  const styles = source('../styles.css')

  assert.match(foundation, /\/\* The Codex owns its height from the viewport-pinned shell below\./)
  assert.match(foundation, /\.codex-library \{ grid-template-columns: minmax\(210px, \.28fr\) minmax\(0, 1fr\); min-height: 0; \}/)
  assert.doesNotMatch(foundation, /\.codex-library \{[^}]*min-height: (?:5|6)\d\dpx/)
  assert.match(styles, /\.codex-library\{[^}]*min-height:0\}/)
  assert.doesNotMatch(styles, /\.codex-library\{[^}]*min-height:520px\}/)
})

test('Codex base primitives leave paging in charge instead of adding fallback scrollbars', () => {
  const styles = source('../styles.css')

  assert.match(styles, /\.codex-page-list\{[^}]*max-height:none;overflow:visible\}/)
  assert.match(styles, /\.codex-entry-picker\{[^}]*max-height:none;overflow:visible\}/)
  assert.match(styles, /@media\(max-width:760px\)\{.*?\.codex-page-list\{max-height:none;overflow:visible\}.*?\.codex-page-grid\{/s)
  assert.doesNotMatch(styles, /\.codex-page-list\{[^}]*max-height:440px;overflow:auto\}/)
  assert.doesNotMatch(styles, /\.codex-page-list\{max-height:180px\}/)
  assert.doesNotMatch(styles, /\.codex-entry-picker\{[^}]*max-height:150px;overflow:auto\}/)
})

test('Codex reader contract keeps the outer page finite and the shelf paged', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /<h2>Codex<\/h2>/)
  assert.match(views, /data-testid="codex-folio-controls"/)
  assert.match(views, /Definition.*Examples.*Mistakes & signals/)
  assert.doesNotMatch(views, /codex-mode-tabs/)
  assert.match(foundation, /Final Forge-first cascade/)
  assert.match(foundation, /\.wide-screen-frame > \.codex-screen > \.codex-library \{[\s\S]*?height: 100%;[\s\S]*?overflow: hidden;/)
  assert.match(foundation, /\.codex-screen \.codex-book-section \{[\s\S]*?overflow-y: auto;/)
  assert.match(foundation, /\.codex-screen \.codex-page-list \{[\s\S]*?overflow: visible;/)
})

test('Codex reader chrome uses a single field-guide visual language', () => {
  const foundation = source('../foundation.css')

  assert.match(foundation, /F-147: visual reader pass/)
  assert.match(foundation, /--codex-paper:/)
  assert.match(foundation, /\.codex-screen > \.screen-hero\.codex-hero \{[\s\S]*?box-shadow: inset 0 -1px 0/)
  assert.match(foundation, /\.codex-screen > \.codex-tab-page\[data-codex-tab="books"\] > \.codex-library \{[\s\S]*?box-shadow: 0 18px 40px/)
  assert.match(foundation, /\.codex-screen > \.codex-tab-page\[data-codex-tab="books"\] \.codex-book-page \{[\s\S]*?var\(--codex-paper\)/)
  assert.match(foundation, /\.codex-screen \.codex-examples pre \{[\s\S]*?border-left: 3px solid/)
})

test('Codex folio pages do not become a desktop infinite-scroll document', () => {
  const foundation = source('../foundation.css')

  assert.match(foundation, /F-157: the Codex is a page-turning folio/)
  assert.match(foundation, /\.game-screen > \.codex-screen \{[\s\S]*?grid-template-rows: auto minmax\(96px, auto\) minmax\(0, 1fr\);/)
  assert.match(foundation, /\.game-screen > \.codex-screen > \.codex-mode-tabs \{[\s\S]*?grid-row: 2;[\s\S]*?align-self: end;/)
  assert.match(foundation, /\.codex-screen \.codex-book-section \{[\s\S]*?overflow: hidden;[\s\S]*?scrollbar-width: none;/)
  assert.match(foundation, /data-testid="codex-read-section"\] \.codex-page-grid \{[\s\S]*?overflow: hidden;/)
  assert.match(foundation, /data-testid="codex-encounters-section"\] \.codex-entry-picker-expanded,[\s\S]*?max-height: 78px;/)
})

test('Codex final cascade keeps desktop folios finite after the legacy viewport rules', () => {
  const foundation = source('../foundation.css')

  assert.match(foundation, /F-158: the old cascade still won on desktop/)
  assert.match(foundation, /\.game-screen > \.codex-screen > \.codex-tab-page\[data-codex-tab="books"\] \.codex-book-section \{[\s\S]*?display: flex;[\s\S]*?overflow-y: hidden;[\s\S]*?scrollbar-width: none;/)
  assert.match(foundation, /\.game-screen > \.codex-screen > \.codex-tab-page\[data-codex-tab="books"\] \.codex-book-section::-webkit-scrollbar \{ display: none; \}/)
  assert.match(foundation, /@media \(max-width: 760px\) \{[\s\S]*?\.game-screen > \.codex-screen > \.codex-tab-page\[data-codex-tab="books"\] \.codex-book-section \{[\s\S]*?overflow-y: auto;/)
})

test('Codex uses the shared wide-surface frame instead of nesting a page in the Forge grid', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /withWideNavigation\(<Codex[\s\S]*?showNavigation=\{false\}/)
  assert.match(views, /showNavigation && <SurfaceNavigation activeView="codex" onNavigate=\{onNavigate\} \/>/)
  assert.match(foundation, /F-161: wide RPG surfaces share one bounded frame/)
  assert.match(foundation, /\.wide-screen-frame > \.codex-screen \{[\s\S]*?display: grid;[\s\S]*?overflow: hidden;/)
  assert.match(foundation, /\.wide-screen-frame > \.codex-screen > \.codex-tab-page\[data-codex-tab="books"\] > \.codex-library \{[\s\S]*?height: 100%;[\s\S]*?overflow: hidden;/)
  assert.match(foundation, /\.wide-screen-frame > \.codex-screen > \.codex-tab-page\[data-codex-tab="books"\] \.codex-book-section \{[\s\S]*?overflow-y: hidden;/)
})

test('Codex and legacy Journal Battle Shells are removed from the campaign surface', () => {
  const views = source('../RpgViews.jsx')

  assert.doesNotMatch(views, /function QuestBattleScreen/)
  assert.doesNotMatch(views, /function QuestJournal/)
  assert.doesNotMatch(views, /journal-mode-tabs|codex-mode-tabs|battle-answer-editor/)
  assert.match(views, /className="forge-document-tabs"/)
  assert.doesNotMatch(views, /function ForgeBossSubmission|function ForgeObjectiveSubmission|function EncounterMechanics/)
  assert.doesNotMatch(views, /Send current goal to PYR|Submit current Forge file to PYR/)
})

test('friend packages strip tracked player state before archive output', () => {
  const packager = source('../../../../tools/questlab-package.ps1')

  assert.match(packager, /archive --format=tar/)
  assert.match(packager, /protectedPackagePaths = @\('progress\.json', 'tutor\.py', 'dungeon\.py', 'notes'\)/)
  assert.match(packager, /Remove-Item -LiteralPath \$protectedPath -Recurse -Force/)
  assert.match(packager, /Player state, tutor\.py, dungeon\.py and notes are local/)
  assert.match(packager, /Refusing to package player-owned paths/)
})

test('Dungeon renders state-owned adaptive mob identity and reward feedback', () => {
  const views = source('../RpgViews.jsx')
  const app = source('../AppV2.jsx')

  assert.match(views, /dungeon-mob-banner/)
  assert.match(views, /run\.encounter\.name/)
  assert.match(app, /title: event\.mob_name \? 'MOB DEFEATED'/)
  assert.match(app, /event\.mob_name \? 'MOB COUNTERATTACK'/)
})

test('Campaign boss validation remains a state-service boundary without a second answer screen', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')

  assert.match(app, /event\.boss_unlocked/)
  assert.match(app, /BOSS GATE UNLOCKED/)
  assert.match(app, /action === 'record_boss_clear'/)
  assert.match(app, /BOSS DEFEATED/)
  assert.match(app, /CAMPAIGN COMPLETE/)
  assert.match(app, /answer_source: 'forge_active_file'/)
  assert.match(views, /data-testid="forge-boss-resolve"/)
  assert.match(views, /data-testid="pyr-sidebar-companion"/)
  assert.match(app, /const submitCampaignRun = async/)
  assert.match(app, /return submitBoss\(\)/)
  assert.doesNotMatch(views, /function ForgeBossSubmission|BOSS \/ MOB MECHANICS/)
  assert.doesNotMatch(views, /Send current goal to PYR/)
  assert.doesNotMatch(views, /data-testid="boss-gate"|data-testid="campaign-complete"/)
  assert.doesNotMatch(views, /boss.*reward.*\+100/)
})

test('boss gate provider bridge binds behaviour, explanation and interview evidence', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const server = source('../../../server/app_v2.py')

  assert.match(app, /const submitBoss = async/)
  assert.match(app, /\/api\/pyr\/boss-submission/)
  assert.match(app, /\/api\/pyr\/boss-verdict/)
  assert.match(app, /A correct verdict applies the canonical damage and reveals the next goal/)
  assert.match(app, /const submitCampaignRun = async/)
  assert.match(app, /window\.__questlabSubmitCampaignRun/)
  assert.match(views, /quest\.md <small>STATE VIEW<\/small>/)
  assert.match(views, /data-testid="forge-boss-resolve"/)
  assert.doesNotMatch(views, /data-testid="forge-boss-submission"|CURRENT QUEST|data-testid="forge-encounter-mechanics"/)
  assert.doesNotMatch(views, /Send current goal to PYR/)
  assert.match(server, /class PyrBossSubmissionRequest/)
  assert.match(server, /class PyrBossVerdictRequest/)
  assert.match(server, /answer_source: Literal\["manual", "forge_active_file"\]/)
  assert.match(server, /current_requirement\.get\("question_type"\)/)
  assert.match(server, /all\(requirement in verified for requirement in BOSS_REQUIREMENTS\)/)
})

test('boss phases and bounded trinket triggers stay state-service sourced', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const server = source('../../../server/state.py')

  assert.match(server, /record_boss_requirement/)
  assert.match(server, /verified_boss_requirements/)
  assert.match(server, /Ember Scythe/)
  assert.match(server, /Guardian Sigil/)
  assert.match(server, /Phoenix Ember/)
  assert.match(app, /BOSS PHASE VERIFIED/)
  assert.match(app, /TRINKET TRIGGERED/)
  assert.match(views, /data-testid="forge-boss-resolve"/)
  assert.match(views, /data-testid="pyr-sidebar-companion"/)
  assert.doesNotMatch(views, /function ForgeBossSubmission/)
  assert.doesNotMatch(views, /data-testid="boss-phase-track"/)
})

test('boss gate keeps Resolve in the sidebar and moves the state-owned quest into quest.md', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const server = source('../../../server/state.py')
  const bridge = source('../../../server/context_bridge.py')
  const v2 = source('../v2.css')

  assert.match(views, /data-testid="forge-boss-resolve"/)
  assert.match(views, /data-testid="pyr-sidebar-companion"/)
  assert.match(views, /quest\.md <small>STATE VIEW<\/small>/)
  assert.match(views, /STATE-OWNED CURRENT ENCOUNTER/)
  assert.match(views, /## Current quest/)
  assert.match(views, /## Boss \/ mob mechanics/)
  assert.match(views, /## Loot at stake/)
  assert.doesNotMatch(views, /data-testid="forge-boss-current-goal"|data-testid="forge-boss-reward"|CURRENT QUEST|data-testid="forge-encounter-mechanics"/)
  assert.doesNotMatch(views, /Send current goal to PYR/)
  assert.doesNotMatch(views, /<span>Requirement<\/span><select/)
  assert.match(app, /const currentGoal = context\?\.encounter\?\.boss_current_requirement/)
  assert.match(app, /const requirementId = currentGoal\?\.id/)
  assert.match(server, /boss_current_requirement/)
  assert.match(server, /boss_resolve_before/)
  assert.match(server, /boss_damage/)
  assert.match(server, /ENCOUNTER_MECHANICS/)
  assert.match(bridge, /"current_requirement": current_requirement/)
  assert.match(bridge, /"mechanics"/)
  assert.match(app, /data-boss-gate=\{bossGateActive \? 'true' : 'false'\}/)
  assert.match(v2, /F-176: route navigation is one app-level surface/)
  assert.match(v2, /data-boss-gate="true"\]\s+\.campaign-battle-sidebar[\s\S]*max-height: none/)
  assert.match(app, /const effectiveLeftWidth = Math\.max\(260, Number\(leftWidth\)/)
  assert.match(source('../styles.css'), /left-resizer/)
})

test('single-file Forge steps hide the workspace tree while multifile projects can reveal it', () => {
  const views = source('../RpgViews.jsx')

  assert.match(views, /const multiFileProject = activeProject\?\.multi_file === true/)
  assert.match(views, /data-testid="forge-active-file-summary"/)
  assert.match(views, /Show project files/)
  assert.match(views, /Hide project files/)
})

test('PTY state commands inherit the canonical gateway instead of workspace progress.json', () => {
  const app = source('../../../server/app_v2.py')
  const cli = source('../../../state_cli.py')

  assert.match(app, /def terminal_environment\(role: str\)/)
  assert.match(app, /QUESTLAB_CANONICAL_STATE_PATH/)
  assert.match(app, /env\["PYTHONPATH"\]/)
  assert.match(app, /str\(REPO_ROOT\)/)
  assert.match(app, /QUESTLAB_PYTHON.*sys\.executable/)
  assert.match(cli, /subparsers\.add_parser\("authority"/)
  assert.match(cli, /subparsers\.add_parser\("campaign"/)
})

test('runtime health exposes the checkout and one canonical state authority', () => {
  const app = source('../../../server/app_v2.py')
  const launcher = source('../../../quest.py')
  const cli = source('../../../state_cli.py')
  const views = source('../AppV2.jsx')

  assert.match(app, /expected_branch/)
  assert.match(app, /workspace_git/)
  assert.match(app, /repo_git/)
  assert.match(app, /include_upstream=True/)
  assert.match(app, /behind_upstream/)
  assert.match(app, /canonical_state_path/)
  assert.match(app, /sync_storage_namespace/)
  assert.match(app, /state_custody/)
  assert.match(cli, /subparsers\.add_parser\("custody"/)
  assert.match(launcher, /QUESTLAB_EXPECTED_BRANCH/)
  assert.match(views, /CHECKOUT MISMATCH/)
  assert.match(views, /CHECKOUT STALE/)
  assert.match(views, /runtimeContractMissing/)
  assert.match(views, /RUNTIME STALE · use current launcher/)
  assert.match(views, /canonical_authoritative !== true/)
  assert.match(views, /legacy_authoritative !== false/)
  assert.match(views, /legacy_path !== null/)
  assert.match(views, /!runtimeAuthority\.legacy_path\.trim\(\)/)
  assert.match(views, /setCheckoutIdentity\(next\.sync_storage_namespace\)/)
})

test('terminal reconnect control uses the stable session handler', () => {
  const app = source('../AppV2.jsx')
  assert.match(app, /const reconnectTerminal = \(\) => \{/)
  assert.match(app, /reconnect: reconnectTerminal/)
  assert.match(app, /onClick=\{reconnectTerminal\}/)
  assert.doesNotMatch(app, /onClick=\{connect\}/)
})

test('legacy Quest Journal is not rendered; Codex owns the active quest rail', () => {
  const journal = source('../RpgViews.jsx')
  assert.doesNotMatch(journal, /function QuestJournal|function QuestBattleScreen/)
  assert.match(journal, /data-testid="codex-active-quest"/)
  assert.match(journal, /data-testid="codex-folio-controls"/)
})

test('Codex renders a searchable concept library and writes bounded field notes through the gateway', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const server = source('../../../server/app_v2.py')
  const state = source('../../../server/state.py')

  assert.match(app, /saveCodexNote/)
  assert.match(app, /\/api\/codex\/note/)
  assert.match(views, /CODEX \/ FIELD LIBRARY/)
  assert.match(views, /Search Codex/)
  assert.match(views, /Add a field note/)
  assert.match(views, /codex-page-/)
  assert.match(views, /entrySearchText/)
  assert.ok(views.includes('concept === pageKey || concept.startsWith(`${pageKey} `)'))
  assert.doesNotMatch(views, /entry\.concept\?\.toLowerCase\(\)\.includes\(page\.title/)
  assert.match(views, /page\.examples/)
  assert.match(views, /WEAKNESSES \/ PATTERNS/)
  assert.match(views, /VERIFIED RESULTS/)
  assert.match(views, /data-testid="codex-entry-insights"/)
  assert.match(server, /@app\.get\("\/api\/codex"\)/)
  assert.match(server, /@app\.post\("\/api\/codex\/note"\)/)
  assert.match(state, /"record_codex_note": ActionDefinition\(frozenset\(\{"player"\}\)\)/)
  assert.match(state, /MAX_CODEX_NOTE_BYTES/)
  assert.match(state, /def codex_projection\(/)
})

test('Codex and Homestead expose live evidence and loadout summaries', () => {
  const views = source('../RpgViews.jsx')

  assert.match(views, /codex-summary-grid/)
  assert.match(views, /codex-page-summary/)
  assert.match(views, /codexMetrics\.verifiedResults/)
  assert.match(views, /pageQuestionTypes/)
  assert.match(views, /pageWeaknesses/)
  assert.match(views, /homestead-live-status/)
  assert.match(views, /homestead-overview-grid/)
  assert.match(views, /CANONICAL REV/)
  assert.match(views, /equipment\.armor/)
  assert.match(views, /equipment\.trinket/)
})

test('campaign equipment loadout stays bounded and state-service sourced', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const sync = source('./syncEngine.js')
  const server = source('../../../server/app_v2.py')
  const state = source('../../../server/state.py')

  assert.match(server, /@app\.post\("\/api\/equipment\/equip"\)/)
  assert.match(server, /equipment_projection/)
  assert.match(state, /"equip_equipment": ActionDefinition\(frozenset\(\{"player"\}\)\)/)
  assert.match(state, /"record_equipment_unlock": ActionDefinition\(frozenset\(\{SYSTEM_ACTOR\}\), internal=True\)/)
  assert.match(state, /def equipment_projection\(/)
  assert.match(state, /Unlock this campaign item before equipping it/)
  assert.match(app, /const equipCampaignItem = async/)
  assert.match(app, /\/api\/equipment\/equip/)
  assert.match(views, /data-testid="campaign-loadout"/)
  assert.match(views, /Future loot stays hidden/)
  assert.match(views, /equipCampaignItem/)
  assert.match(sync, /owned_armor/)
  assert.match(sync, /owned_trinkets/)
})

test('top HUD stat pills style only direct stats and reset nested SVG content', () => {
  const styles = source('../styles.css')
  const v2 = source('../v2.css')
  const app = source('../AppV2.jsx')
  const polish = source('../uiPolish.js')

  assert.match(styles, /\.top-stats\s*>\s*span,\.git-pill/)
  assert.doesNotMatch(styles, /\.top-stats\s+span,\.git-pill/)
  assert.match(styles, /\.top-stats\s*>\s*span\s+\.quest-icon/)
  assert.match(styles, /\.top-stats\s*>\s*span\s+\[data-stat-value\]/)
  assert.match(styles, /\.top-stats\s*>\s*span\{[^}]*min-width:6ch[^}]*min-height:26px[^}]*white-space:nowrap/)
  assert.match(styles, /\.top-stats\s*>\s*span\s+\.quest-icon\{[^}]*flex:0 0 14px/)
  assert.match(styles, /\.top-stats\s*>\s*span\s+\[data-stat-value\]\{[^}]*min-width:2ch[^}]*text-align:right/)
  assert.match(v2, /data-hud="hud-adventurer"\]\s+\.top-stats\s*>\s*span/)
  assert.match(v2, /top-stats\s*>\s*span\s+\.quest-icon/)
  assert.ok(polish.includes("querySelectorAll('.top-stats > span')"))
  assert.match(polish, /data-stat-value/)
  assert.match(polish, /function replaceTopStat\(node\) \{[\s\S]*node\.dataset\.reactStat === 'true'/)
  assert.match(app, /function StatIcon\(\{ name \}\)/)
  for (const icon of ['heart', 'coin', 'flame', 'shield', 'sword']) assert.match(app, new RegExp(`name="${icon}"`))
  assert.match(polish, /dataset\.reactStat === 'true'/)
  assert.doesNotMatch(app, /[♥◈🔥🛡⚔]/)
})

test('combat projection treats legacy cleared mobs as terminal', () => {
  const combat = source('../combatShell.js')
  const views = source('../RpgViews.jsx')

  assert.match(combat, /isMobDefeated\s*=\s*\(mob\)\s*=>\s*mob\?\.status === 'defeated' \|\| mob\?\.status === 'cleared'/)
  assert.match(combat, /mobs\.findIndex\(\(mob\) => !isMobDefeated\(mob\)\)/)
  assert.match(views, /const isMobDefeated = \(status\) => status === 'defeated' \|\| status === 'cleared'/)
  assert.doesNotMatch(views, /mob\.status === 'defeated' \? '✓'/)
})

test('legacy reconciliation renders validated restoration feedback without inventing rewards', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /action === 'reconcile_legacy_progress'/)
  assert.match(app, /PROGRESS RESTORED/)
  assert.match(app, /restored_xp/)
  assert.match(app, /restored_coins/)
  assert.match(app, /restored_mobs/)
  assert.match(app, /restored_fields/)
  assert.match(app, /CODEX UPDATED/)
})

test('reward presentation never invents a boss XP amount', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /const bossRewardValue = event\.boss_reward_xp \?\? event\.reward_xp/)
  assert.match(app, /typeof bossRewardValue === 'number' && Number\.isFinite\(bossRewardValue\)/)
  assert.match(app, /bossRewardXp !== null \? `\+\$\{bossRewardXp\} XP` : ''/)
  assert.doesNotMatch(app, /event\.boss_reward_xp \?\? event\.reward_xp \?\? 100/)
})

test('campaign projection accepts a deliberate revision rollback as a new authority', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /const revisionRegressed = campaignInitializedRef\.current && campaignRevisionRef\.current !== null && nextRevision < campaignRevisionRef\.current/)
  assert.match(app, /campaignInitializedRef\.current = false/)
  assert.match(app, /campaignRevisionRef\.current = null/)
  assert.match(app, /seenStateEventsRef\.current = new Set\(\)/)
  assert.doesNotMatch(app, /nextRevision < campaignRevisionRef\.current\) return/)
})

test('bounded player-state sync stays behind one engine with revision/conflict controls', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const engine = source('./syncEngine.js')

  assert.match(app, /syncEngine\.observeCampaign\(next\)/)
  assert.match(app, /metadata\.sync_storage_namespace/)
  assert.match(app, /resolveCloudConflict/)
  assert.match(views, /Use cloud copy/)
  assert.match(views, /Keep this device/)
  assert.match(engine, /\/api\/state\/sync/)
  assert.match(engine, /save_player_state/)
  assert.match(engine, /SYNC_OUTBOX_STORAGE_KEY/)
  assert.match(engine, /checkoutStorageNamespace/)
  assert.match(engine, /setCheckoutIdentity\(identity\)/)
  assert.match(engine, /resolveConflict\(choice\)/)
  assert.match(engine, /localPlayer: playerSummary\(local\?\.projection\)/)
  assert.match(engine, /cloudPlayer: playerSummary\(cloud\?\.state\)/)
  assert.match(engine, /isStarterProjection/)
  assert.match(engine, /published to the starter cloud copy/)
  assert.match(engine, /window\.setInterval\(\(\) => \{[\s\S]*void this\.sync\(\{ silent: true \}\)/)
})

test('top HUD SVG icons are nested content, not nested stat pills', () => {
  const styles = source('../styles.css')
  const v2 = source('../v2.css')

  assert.match(styles, /\.top-stats\s*>\s*span,\.git-pill/)
  assert.match(styles, /\.app-shell\[data-hud="hud-adventurer"\] \.top-stats\s*>\s*span/)
  assert.match(v2, /\.forge-v2\[data-hud="hud-adventurer"\] \.top-stats\s*>\s*span/)
  assert.doesNotMatch(styles, /\.top-stats\s+span,\.git-pill/)
  assert.match(styles, /\.top-stats\s*>\s*span\s+\.quest-icon/)
  assert.match(styles, /\.top-stats\s*>\s*span\s+\[data-stat-value\]/)
  assert.match(styles, /\.top-stats\s+\.cloud-pill\{[^}]*min-width:15ch/)
})

test('Codex chrome and workspace files stay readable and bounded', () => {
  const views = source('../RpgViews.jsx')
  const app = source('../AppV2.jsx')
  const v2 = source('../v2.css')
  const server = source('../../../server/app_v2.py')

  assert.match(v2, /F-172: Codex folio chrome must reserve its own rows/)
  assert.match(v2, /grid-template-rows: max-content max-content max-content minmax\(0, 1fr\)/)
  assert.match(v2, /F-173: the three read folios need visible editorial hierarchy/)
  assert.match(v2, /codex-definition-card/)
  assert.match(v2, /codex-example-card/)
  assert.match(v2, /codex-signal-card/)
  assert.match(views, /role="tree" aria-label="Workspace files"/)
  assert.match(views, /role="treeitem"/)
  assert.match(views, /Collapse all folders/)
  assert.match(views, /const treeFiles = files\.filter/)
  assert.match(app, /data-stat-label="HP"/)
  assert.match(app, /title=\{campaignReady \? `HP/)
  assert.match(server, /"\\\\"/)
  assert.match(server, /child\.is_symlink\(\)/)
})

test('Codex lesson reader keeps theory, practice and evidence in one simple path', () => {
  const views = source('../RpgViews.jsx')
  const v2 = source('../v2.css')
  const state = source('../../../server/state.py')

  assert.match(v2, /F-226: simplify Codex into a focused lesson reader/)
  assert.match(views, /data-testid="codex-study-prompt"/)
  assert.match(views, /selectedPage\.check_prompt/)
  assert.match(views, /onNavigate\('tutor'\)/)
  assert.match(views, /selectedPage\.common_mistakes/)
  assert.match(views, /ResourceCodexExamples/)
  assert.match(views, /ResourceEncounterRecords/)
  assert.match(views, /page\.mistake_examples/)
  assert.match(views, /entry\.code_snippet/)
  assert.match(views, /resource-practice-signals/)
  assert.match(v2, /codex-study-prompt/)
  assert.match(v2, /resource-signals \{ display: grid; grid-template-columns: minmax\(0, 1fr\)/)
  assert.match(v2, /codex-page-list button\.active/)
  assert.match(state, /"common_mistakes":/)
  assert.match(state, /"check_prompt":/)
  assert.match(state, /"mistake_examples":/)
  assert.match(state, /"code_snippet": str\(entry\.get\("code_snippet"/)
  assert.match(state, /"common_mistakes": \[item for item in page\.get\("common_mistakes"/)
})

test('Codex reader typography stays book-like without adding another scroll owner', () => {
  const foundation = source('../foundation.css')

  assert.match(foundation, /F-155: make the bounded reader feel like a field guide/)
  assert.match(foundation, /--codex-display-font: Georgia/)
  assert.match(foundation, /\.codex-screen \.codex-page-heading h3,[\s\S]*font-family: var\(--codex-display-font\)/)
  assert.match(foundation, /\.codex-screen \.codex-book-tabs button[\s\S]*font-family: var\(--codex-body-font\)/)
  assert.match(foundation, /\.codex-screen \.codex-book-section \{[\s\S]*scroll-behavior: smooth;/)
})

test('submit shortcut is intercepted before Monaco can insert a newline', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /modifier && event\.shiftKey && event\.key === 'Enter'/)
  assert.match(app, /document\.querySelector\('\[data-qol-submit\]'\)\?\.click\(\)/)
  assert.match(app, /event\.preventDefault\(\)[\s\S]*event\.stopPropagation\(\)[\s\S]*data-qol-submit/)
})

test('account settings exposes revision diagnostics without changing sync authority', () => {
  const views = source('../RpgViews.jsx')
  const styles = source('../styles.css')

  assert.match(views, /data-testid="account-sync-diagnostics"/)
  assert.match(views, /Local campaign revision/)
  assert.match(views, /Cloud cursor/)
  assert.match(views, /Queued changes/)
  assert.match(views, /revision=\{revision\}/)
  assert.match(styles, /\.account-sync-diagnostics\{display:grid/)
  assert.match(styles, /grid-template-columns:repeat\(3,minmax\(0,1fr\)/)
})

test('account settings exposes validated portrait transport status', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /data-testid="account-avatar-sync"/)
  assert.match(views, /const avatar = account\.avatar \|\| \{\}/)
  assert.match(views, /PRIVATE CLOUD/)
  assert.match(views, /CACHED CLOUD/)
  assert.match(views, /no portrait available/)
  assert.match(foundation, /F-156: expose portrait transport state/)
  assert.match(foundation, /\.account-avatar-sync\s*\{[\s\S]*display: grid;/)
})

test('workspace transfer exposes hash comparisons before any file apply', () => {
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /data-testid="workspace-transfer-summary"/)
  assert.match(views, /local_sha256/)
  assert.match(views, /remote_sha256/)
  assert.match(views, /Hash mismatch: review the local and remote digests/)
  assert.match(views, /excludedCount/)
  assert.match(foundation, /\.workspace-transfer-summary \{ display: flex;/)
  assert.match(foundation, /\.workspace-transfer-file-meta small/)
})

test('avatar controls use the account-scoped storage boundary with a local fallback', () => {
  const enhancements = source('../forgeEnhancements.js')
  const views = source('../RpgViews.jsx')
  const app = source('../AppV2.jsx')
  const engine = source('./syncEngine.js')
  const avatar = source('./avatarStorage.js')

  assert.match(enhancements, /syncEngine\.setAvatarDataUrl\(dataUrl\)/)
  assert.match(enhancements, /syncEngine\.removeAvatar\(\)/)
  assert.match(enhancements, /questlab:avatar-updated/)
  assert.match(enhancements, /dataset\.reactAvatar !== 'true'/)
  assert.match(enhancements, /syncEngine\.getState\(\)\?\.avatar\?\.dataUrl/)
  assert.match(views, /data-react-avatar="true"/)
  assert.match(views, /quest-avatar-img compact/)
  assert.match(views, /quest-avatar-img character/)
  assert.match(app, /avatarDataUrl={cloudState\.avatar\?\.dataUrl \|\| ''}/)
  assert.match(engine, /AVATAR_BUCKET/)
  assert.match(engine, /dataUrl: normalizedDataUrl/)
  assert.match(engine, /_saveAvatarProfilePath/)
  assert.match(engine, /_pollAvatarReference/)
  assert.match(engine, /readCachedAvatar\(this\.storage, userId\)/)
  assert.match(avatar, /AVATAR_MAX_BYTES = 1_000_000/)
  assert.match(avatar, /avatarObjectPath\(userId\)/)
})
