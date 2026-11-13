# PYR runtimes

PYR can use the local OpenCode CLI, hosted Shared PYR, or a manual CLI
terminal. **Local OpenCode is the default** and stays local even when the
player is signed in. Hosted PYR is an explicit opt-in in Settings → AI Tutor.

## Local OpenCode

Install OpenCode and sign in to a provider through the CLI. In Settings → AI
Tutor, choose **Local OpenCode**. The game sends prompts to the local OpenCode
process and does not route them through Supabase. Use **Manual CLI** when you
want the raw terminal panel instead of built-in grading and hints.

## Shared PYR

Signed-in members of a private Hunter group use the shared PYR tutor. Friends
do not need to install OpenCode or create their own AI-provider account. The
provider key stays in Supabase Edge Function Secrets and is never shipped in
the desktop app.

## Cloud setup

1. In OpenCode Console, create a service-account API key for shared use, then
   add it in Supabase → Edge Functions → Secrets as `PYR_AI_API_KEY`. Never add
   its value to the app, repository, or chat.
2. The `pyr` Edge Function uses the OpenCode Console Chat Completions API and
   defaults to `https://opencode.ai/inference/openai/v1` with
   `deepseek-v4.1-flash` (DeepSeek V4.1 Flash). If the OpenCode key uses an
   OpenCode Go subscription, set `PYR_AI_BASE_URL` to
   `https://opencode.ai/inference/go/openai/v1`; the function sends the stable
   per-account session header required by Go. To select another enabled model,
   set `PYR_AI_MODEL` as a function secret. The configured model is shared by
   all players.
3. Players sign in to Quest Lab and join the private Hunter group. The function
   rejects anonymous callers and signed-in accounts outside the group.
4. In Settings → AI Tutor, choose **Shared PYR**. The status should say
   **SHARED PYR READY**. Use **Test shared PYR** to make one small, billable
   provider request.

Each member can make up to 12 requests per minute and 100 per UTC day. The
function limits each prompt to 24,000 characters and each response to 1,200
tokens. Also set a spend limit in the provider account; provider billing is
separate from Supabase.

## Routing behavior

The selected runtime is authoritative. Local OpenCode never silently switches
to Shared PYR because the player signed in, and Shared PYR reports an error
instead of silently falling back to a different provider. Manual CLI disables
built-in grading and leaves the terminal available for a CLI the player starts.

AI calls carry the signed-in player's Supabase JWT from the local app server to
the function. The Edge Function verifies the JWT, confirms private-group
membership, consumes the per-account quota, and calls the provider using its
server-side secret. It has no tool-calling path. The existing local verdict
gateway remains authoritative for XP, HP, Resolve, rewards, and replay checks.

## What PYR does

Each feature can be switched off in Settings → AI Tutor.

| Feature | Where | What it changes |
|---|---|---|
| Grade submissions | Forge, boss goals, Dungeon answers, Tutor feedback | PYR returns a verdict and short reason. The game applies it through the normal state gateway. |
| Write Dungeon questions | New Infinite Dungeon combat rooms | Rewrites the room question for its concept, type, and difficulty, only while the answer file is empty. |
| Choose question lenses | Tutor → IDE practice | Picks a practice lens and writes a question for it. |
| Ask PYR | Forge and Tutor | Returns a Socratic nudge; it must not write the learner's project solution. |

## Implementation

| What | Path |
|---|---|
| Edge Function | `supabase/functions/pyr/index.ts` |
| Per-user quota | `supabase/migrations/20261109090500_pyr_ai_request_quota.sql` |
| Local AI routing and prompt rules | `ide/server/ai_tutor.py` |
| HTTP routes and request-scoped Supabase auth | `ide/server/app_v2.py` |
| Frontend auth forwarding and settings | `ide/frontend/src/AppV2.jsx`, `ide/frontend/src/RpgViews.jsx` |
