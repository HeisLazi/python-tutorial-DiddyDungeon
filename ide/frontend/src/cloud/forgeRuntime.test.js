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
  assert.match(views, /data-testid="encounter-resolve"/)
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
  assert.match(quest, /def checkout_head_sha\(root: Path\)/)
  assert.match(quest, /env\["QUESTLAB_BUILD_SHA"\] = checkout_head_sha\(REPO_ROOT\)/)
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

test('Battle Journal binds player answers before provider adjudication', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')

  assert.match(app, /const submitBattle = async/)
  assert.match(app, /pasteAiPrompt/)
  assert.match(app, /Battle answer sent to/)
  assert.match(app, /Bounded Quest Lab context/)
  assert.match(app, /Active file \(\$\{context\.active_file/)
  assert.match(app, /BATTLE ATTEMPT RECORDED/)
  assert.match(views, /data-testid="battle-submission"/)
  assert.match(views, /Send to PYR/)
  assert.match(views, /Resolve and rewards change only after the provider returns a validated verdict/)
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
  assert.match(views, /Send answer to PYR/)
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

test('navigation keeps Tutor as the single practice workspace and parks hidden AI without a blank grid column', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const v2 = source('../v2.css')
  const foundation = source('../foundation.css')
  const palette = source('../commandPalette.js')

  assert.match(app, /const normalizeView = \(value\) => value === 'practice' \? 'tutor' : value === 'quests' \? 'codex' : value/)
  assert.match(app, /return normalizeView\(candidate\)/)
  assert.doesNotMatch(views, /id: 'practice', icon:/)
  assert.doesNotMatch(palette, /Open Quest Journal/)
  assert.match(app, /gridStyle = wideSurface\s*\? \{/)
  assert.match(app, /const wideSurface = \['hub', 'character', 'homestead'\]/)
  assert.match(app, /!wideSurface && <ActivityRail/)
  assert.match(views, /data-testid="wide-route-nav"/)
  assert.match(views, /aria-label="Wide route navigation"/)
  assert.match(views, /data-wide-route=\{activeView\}/)
  assert.match(foundation, /\.surface-nav \{ position: sticky;/)
  assert.match(views, /withWideNavigation/)
  assert.match(views, /function RouteIcon\(/)
  assert.match(views, /className="activity-rail" data-react-owned="true"/)
  assert.doesNotMatch(views, /icon:\s*['"`]/)
  assert.match(foundation, /\.wide-screen-frame > \.game-screen-scroll/)
  assert.match(foundation, /\.surface-nav-link\.active/)
  assert.match(foundation, /\.surface-nav-link > span:first-child svg/)
  assert.match(app, /aiGridVisible\s*\?\s*`48px/)
  assert.match(app, /aiGridVisible\s*\?\s*''\s*:\s*aiPopoverOpen/)
  assert.match(v2, /ai-panel-parked/)
  assert.match(v2, /wide-mode \.game-screen\{grid-column:1/)
  assert.match(v2, /hub-mode \.game-screen\{grid-column:1/)
  assert.match(app, /initialLaunch\.returning \? `Welcome back, \$\{welcomeName\}`/)
  assert.match(foundation, /questlab-splash-in/)
})

test('legacy shell wires wide-route navigation back to the active view', () => {
  const legacy = source('../App.jsx')
  assert.match(legacy, /<GameScreen[\s\S]*onNavigate=\{setActiveView\}[\s\S]*campaignReady=\{campaignReady\}/)
  assert.match(legacy, /value === 'quests' \? 'codex'/)
})

test('legacy rail icon enhancement yields to the React-owned SVG rail', () => {
  const views = source('../RpgViews.jsx')
  const enhancements = source('../forgeEnhancements.js')
  assert.match(views, /data-react-owned="true"/)
  assert.match(enhancements, /const reactRail = document\.querySelector\('\.activity-rail\[data-react-owned="true"\]'\)/)
  assert.match(enhancements, /if \(reactRail\) return/)
})

test('Journal and Codex keep the active encounter projection visible', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const foundation = source('../foundation.css')

  assert.match(views, /data-testid="forge-encounter-resolve"/)
  assert.match(views, /data-testid="quest-battle-screen"/)
  assert.match(views, /journal-mode-tabs/)
  assert.match(views, /battle-answer-editor/)
  assert.match(views, /data-testid="codex-active-quest"/)
  assert.match(views, /data-testid="codex-mode-tabs"/)
  assert.match(views, /data-testid="battle-story-background"/)
  assert.match(views, /data-testid="battle-encounter-details"/)
  assert.match(views, /className="codex-screen"/)
  assert.match(views, /data-testid="codex-mastery"/)
  assert.match(views, /function QuestBattleScreen\(\{ activeProject, currentMob, encounter, resolve/)
  assert.match(views, /currentMob=\{battleMob\}\s+encounter=\{encounter\}/)
  assert.match(views, /function Codex\(\{ progress, revision, codexProjection, encounter, submitBattle, submitBoss/)
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
  assert.match(views, /key=\{`\$\{codexView\}:\$\{selectedPage\?\.id \|\| 'empty'\}:\$\{codexSection\}`\}/)
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
  assert.match(views, /RouteIcon id=\{locked \? 'codex' : project\.completed \? 'shield'/)
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

test('Campaign completion keeps the boss gate and state-service boundary explicit', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')

  assert.match(app, /event\.boss_unlocked/)
  assert.match(app, /BOSS GATE UNLOCKED/)
  assert.match(app, /action === 'record_boss_clear'/)
  assert.match(app, /BOSS DEFEATED/)
  assert.match(app, /CAMPAIGN COMPLETE/)
  assert.match(views, /data-testid="boss-gate"/)
  assert.match(views, /data-testid="campaign-complete"/)
  assert.match(views, /required_behavior.*explanation.*interview/)
  assert.match(views, /No future questions or answers are revealed here/)
  assert.doesNotMatch(views, /boss.*reward.*\+100/)
})

test('boss gate provider bridge binds behaviour, explanation and interview evidence', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const server = source('../../../server/app_v2.py')

  assert.match(app, /const submitBoss = async/)
  assert.match(app, /\/api\/pyr\/boss-submission/)
  assert.match(app, /\/api\/pyr\/boss-verdict/)
  assert.match(app, /A project completes only after all three requirements are separately verified/)
  assert.match(views, /data-testid="boss-submission"/)
  assert.match(views, /Send to PYR/)
  assert.match(server, /class PyrBossSubmissionRequest/)
  assert.match(server, /class PyrBossVerdictRequest/)
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
  assert.match(views, /data-testid="boss-phase-track"/)
  assert.match(views, /bossPhaseLabel/)
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
  assert.match(views, /setCheckoutIdentity\(next\.sync_storage_namespace\)/)
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
