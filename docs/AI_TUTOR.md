# PYR on OpenCode

PYR, the in-game tutor, runs on your own [OpenCode](https://opencode.ai)
install and whichever providers you have signed in there (OpenCode Go,
GitHub Copilot, OpenAI, Google...). Quest Lab never asks for or stores an API
key.

## Set up

1. Install OpenCode and sign in to at least one provider: `opencode auth login`.
2. Open **Settings → AI Tutor**. It should say **READY** and list your
   integrations.
3. Leave **Model** on **Auto** or pick any model, then press **Test**.
   Auto uses the first one you're signed in to from: `opencode-go/beam-free`
   (Beam, code-focused and free on OpenCode Go), then OpenCode Go Haiku,
   DeepSeek Flash, Qwen Flash, Copilot GPT nano, Gemini Flash, OpenAI Luna.

Some models in the list aren't enabled on every plan; Test tells you
straight away. The `opencode/…` free-tier models are hidden: OpenCode only
serves them to its own agents, so they can't run PYR. (`opencode-go/beam-free`
is different: it comes through your OpenCode Go account and works.)

## PYR mode

| Mode | Forge right panel | Grading |
|---|---|---|
| **OpenCode** (default) | Built-in PYR chat: Ask PYR plus a log of every verdict | Automatic through OpenCode |
| **Classic terminal** | The raw CLI terminal with Claude / AGY / Codex / Copilot buttons | The submission prompt is pasted into the CLI you launched |

Switch in Settings → AI Tutor → PYR mode. OpenCode mode falls back to
Classic on its own if OpenCode isn't ready.

## What PYR does

Each one can be switched off in Settings → AI Tutor.

| Feature | Where | What it changes |
|---|---|---|
| **Grade submissions** | Submit run (Forge), boss goals, Dungeon answers, Tutor "Submit for feedback" | PYR decides `correct` / `incorrect` and writes one short reason. The game applies the verdict through its normal gateway, so XP, coins, HP, Resolve and damage come from the game's rules, never from the model. |
| **Write Dungeon questions** | Each new combat room in the Infinite Dungeon | Rewrites the room's question for its concept, type and difficulty. Only while `dungeon.py` is empty, so it can never wipe an answer. |
| **Choose question lenses** | Tutor → IDE practice → "✦ Let PYR choose" | Picks the lens you need (predict, trace, bug, explain, transfer) and writes a question for it. |
| **Ask PYR** | Forge PYR panel and Tutor → PYR channel | A short Socratic nudge. PYR won't write your project for you. |

In Classic mode (or when OpenCode isn't ready, or grading is off), the
older flow still works: launch a CLI (Codex, Claude, AGY, Copilot) in the
Forge PYR panel and the submission prompt is pasted into it.

## Safety rails

- PYR runs as a dedicated `questlab-pyr` OpenCode agent with **every tool
  disabled and every permission denied**, from an empty scratch directory
  (`~/.local/state/QuestLab/pyr-agent-<hash>/`). It can't read your files or
  run commands, even though your global OpenCode config may allow that for
  other agents.
- Replies must be one JSON object of an exact shape. Anything else is an
  error, not a verdict: **a failed or slow grade never costs HP** and the
  submission stays pending so you can just submit again.
- The answer graded is the one bound to the challenge (checked by its
  SHA-256), so it can't be swapped after binding.
- One model call at a time. While PYR thinks, the Dungeon editor is
  read-only and autosave pauses, so the save can't change under the grade.
- Quest Lab never runs `opencode auth export`; Settings shows integration
  names only.

## Where things live

| What | Path |
|---|---|
| AI settings (device-local, not synced) | `~/.local/state/QuestLab/ai.json` |
| Last reply PYR couldn't parse (debugging) | `~/.local/state/QuestLab/last-unparseable-reply.txt` |
| Backend module | `ide/server/ai_tutor.py` |
| HTTP routes | `/api/ai/{status,models,settings,test,judge,dungeon-question,practice-lens,ask}` in `ide/server/app_v2.py` |
| Tests (stub OpenCode, no real model calls) | `ide/server/test_ai_tutor.py` |

OpenCode keeps a background service running (`opencode serve --service`,
~200 MB) that every PYR call reuses.
