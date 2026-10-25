"""OpenCode-backed PYR: grading, question writing and hints.

The player's own OpenCode install (and the provider accounts already signed in
there) is the model runtime, so Quest Lab never stores an AI credential. Every
call runs ``opencode run --agent questlab-pyr --format json`` (a no-tools
agent defined in the scratch directory) with all context inside the prompt, and the reply must be one strict
JSON object. Callers decide what a reply is allowed to change: grading verdicts
still go through the existing PYR verdict gateway, which owns rewards, damage
and HP.

AI settings are device-local (``$XDG_STATE_HOME/QuestLab/ai.json``) because
``progress.json`` is tracked in git and synced.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_SECONDS = 150
STATUS_TIMEOUT_SECONDS = 25
MAX_CONTEXT_CHARS = 24_000
MAX_ANSWER_CHARS = 20_000
# Must fit the verdict gateway (state.MAX_REASON_LENGTH); longer reasons fail validation.
MAX_REASON_CHARS = 240
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._:/@#+-]{0,200}$")

DEFAULT_SETTINGS: dict[str, Any] = {
    "provider": "opencode",
    # "opencode": PYR is built in and grades automatically (default).
    # "classic": the Forge PYR terminal, where the player launches a CLI
    # harness (Claude, AGY, Codex, Copilot) that receives pasted prompts.
    "mode": "opencode",
    # Empty means "Auto": the first signed-in model from AUTO_MODEL_PREFERENCES.
    "model": "",
    "auto_grade": True,
    "generate_dungeon_questions": True,
    "choose_practice_lens": True,
}

TUTOR_RULES = (
    "You are PYR, a Socratic Python tutor inside a learning game called Quest Lab. "
    "The learner writes every line of project code themselves. Never write the solution "
    "for the current project, never paste a finished function, and never reveal hidden "
    "future questions or answer keys. Prefer one precise question, a hint, or short "
    "pseudocode in a different context from the project. Do not use tools, do not read or "
    "edit files, and do not run commands: everything you need is in this message."
)

# One model call at a time: each one holds a model request open for tens of
# seconds and the app targets machines with little spare RAM.
_CALL_LOCK = threading.Lock()
_SETTINGS_LOCK = threading.Lock()
_MODELS_CACHE: dict[str, Any] = {"at": 0.0, "models": []}


class AiTutorError(Exception):
    """A model call failed in a way that must not be treated as a verdict."""

    def __init__(self, message: str, *, kind: str = "error", status_code: int = 502):
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code


# ── Device-local settings ──────────────────────────────────────────────


def state_dir() -> Path:
    override = os.getenv("QUESTLAB_AI_STATE_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    base = os.getenv("XDG_STATE_HOME", "").strip() or str(Path.home() / ".local" / "state")
    return Path(base) / "QuestLab"


def settings_path() -> Path:
    return state_dir() / "ai.json"


def load_settings() -> dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)
    try:
        stored = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings
    if isinstance(stored, dict):
        for key, default in DEFAULT_SETTINGS.items():
            if isinstance(stored.get(key), type(default)):
                settings[key] = stored[key]
    return settings


def save_settings(update: dict[str, Any]) -> dict[str, Any]:
    with _SETTINGS_LOCK:
        settings = load_settings()
        for key, value in update.items():
            if key not in DEFAULT_SETTINGS or value is None:
                continue
            if not isinstance(value, type(DEFAULT_SETTINGS[key])):
                raise AiTutorError(f"Invalid value for {key}", kind="invalid", status_code=422)
            if key == "model" and not MODEL_PATTERN.match(value):
                raise AiTutorError("Model must look like provider/model", kind="invalid", status_code=422)
            if key == "mode" and value not in {"opencode", "classic"}:
                raise AiTutorError("Mode must be opencode or classic", kind="invalid", status_code=422)
            settings[key] = value
        path = settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
        return settings


# ── OpenCode discovery ─────────────────────────────────────────────────


def opencode_binary() -> str | None:
    """Find OpenCode even when the app starts from a desktop launcher, whose
    environment usually lacks the ~/.opencode/bin entry a login shell adds."""

    override = os.getenv("QUESTLAB_OPENCODE_BIN", "").strip()
    candidates = [override] if override else []
    found = shutil.which("opencode")
    if found:
        candidates.append(found)
    candidates.append(str(Path.home() / ".opencode" / "bin" / "opencode"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def _run(argv: list[str], *, timeout: float, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = None
    if cwd:
        # OpenCode resolves its project directory (and so which opencode.json
        # agents exist) from $PWD, which `cwd=` alone leaves pointing at the
        # parent's directory.
        env = {**os.environ, "PWD": str(cwd)}
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def status() -> dict[str, Any]:
    binary = opencode_binary()
    report: dict[str, Any] = {
        "installed": bool(binary),
        "path": binary,
        "version": None,
        "integrations": [],
        "ready": False,
        "detail": "",
    }
    if not binary:
        report["detail"] = "OpenCode is not installed. Install it from https://opencode.ai, then run `opencode auth login`."
        return report
    try:
        version = _run([binary, "--version"], timeout=STATUS_TIMEOUT_SECONDS)
        report["version"] = (version.stdout or version.stderr).strip().splitlines()[0] if (version.stdout or version.stderr).strip() else None
        # Names only: `auth list` prints integration name, kind and a stored
        # flag. Credentials are never read (no `auth export`).
        listing = _run([binary, "auth", "list"], timeout=STATUS_TIMEOUT_SECONDS)
    except (OSError, subprocess.SubprocessError) as exc:
        report["detail"] = f"OpenCode did not respond: {exc}"
        return report
    integrations = []
    for line in listing.stdout.splitlines():
        parts = re.split(r"\s{2,}", line.strip())
        if len(parts) >= 2 and parts[0]:
            integrations.append(parts[0])
    report["integrations"] = integrations
    report["ready"] = bool(integrations)
    report["detail"] = (
        f"Signed in to {len(integrations)} integration(s)."
        if integrations
        else "OpenCode has no signed-in providers yet. Run `opencode auth login` in a terminal."
    )
    return report


def list_models(*, max_age: float = 300.0) -> list[str]:
    if _MODELS_CACHE["models"] and time.monotonic() - _MODELS_CACHE["at"] < max_age:
        return list(_MODELS_CACHE["models"])
    binary = opencode_binary()
    if not binary:
        return []
    try:
        listing = _run([binary, "models"], timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    # The `opencode/` provider is OpenCode's own free tier, which refuses any
    # agent but OpenCode's built-in ones, so it can never run PYR; hide it.
    models = sorted(
        {
            line.strip()
            for line in listing.stdout.splitlines()
            if "/" in line and " " not in line.strip() and not line.strip().startswith("opencode/")
        }
    )
    _MODELS_CACHE.update({"at": time.monotonic(), "models": models})
    return models


# ── Model calls ────────────────────────────────────────────────────────

AGENT_NAME = "questlab-pyr"
# A dedicated agent, written into the scratch directory's opencode.json. The
# built-in `plan` agent carries a "Plan mode" system prompt that made models
# chat and withhold verdicts, and the player's global config may allow every
# tool; this agent has no tools, denies every permission and answers in JSON.
# (No maxSteps: forcing a text-only step uses assistant prefill, which some
# models reject.)
AGENT_CONFIG = {
    "$schema": "https://opencode.ai/config.json",
    "agent": {
        AGENT_NAME: {
            "description": "Quest Lab PYR: grades and writes questions as one JSON object; never uses tools",
            "mode": "primary",
            "prompt": (
                "You are PYR, the tutor inside the Quest Lab learning game. You are called by a program, "
                "not chatting with a person. Read the task, decide, and answer with exactly one JSON object "
                "in the shape the task asks for. No preamble, no follow-up questions, no markdown outside "
                "the JSON. Never use tools."
            ),
            "tools": {"*": False, "bash": False, "edit": False, "write": False, "read": False, "webfetch": False, "task": False},
            "permission": {"edit": "deny", "bash": "deny", "webfetch": "deny", "external_directory": "deny"},
        }
    },
}

# Used when the player leaves the model on "Auto". OpenCode's free tier only
# serves OpenCode's own agents, so Auto picks the first signed-in model from
# this list of quick, JSON-reliable models.
AUTO_MODEL_PREFERENCES = (
    "opencode-go/beam-free",
    "opencode-go/claude-haiku-5-5",
    "opencode-go/deepseek-v4.1-flash",
    "opencode-go/qwen3.8-flash",
    "github-copilot/gpt-5.4-nano",
    "google/gemini-3.8-flash",
    "openai/gpt-5.6-luna-fast",
)


def resolve_model(model: str) -> str:
    if model:
        return model
    available = set(list_models())
    return next((candidate for candidate in AUTO_MODEL_PREFERENCES if candidate in available), "")


def prepare_scratch() -> Path:
    """Return the empty working directory that holds the agent config.

    OpenCode's background service caches each directory's config the first
    time it sees it, so the directory is named after the config's hash: any
    change to the agent lands in a fresh directory the service reads anew.
    """

    rendered = json.dumps(AGENT_CONFIG, indent=2) + "\n"
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()[:10]
    scratch = state_dir() / f"pyr-agent-{digest}"
    scratch.mkdir(parents=True, exist_ok=True)
    config = scratch / "opencode.json"
    if not config.is_file() or config.read_text(encoding="utf-8") != rendered:
        config.write_text(rendered, encoding="utf-8")
    return scratch


def run_prompt(prompt: str, *, title: str, model: str | None = None, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> str:
    """Run one prompt through OpenCode and return the final assistant text."""

    binary = opencode_binary()
    if not binary:
        raise AiTutorError("OpenCode is not installed", kind="unavailable", status_code=503)
    model = (model if model is not None else load_settings()["model"]).strip()
    if not MODEL_PATTERN.match(model):
        raise AiTutorError("Model must look like provider/model", kind="invalid", status_code=422)
    model = resolve_model(model)
    argv = [binary, "run", "--agent", AGENT_NAME, "--format", "json", "--title", title]
    if model:
        argv += ["--model", model]
    argv.append(prompt)

    scratch = prepare_scratch()
    if not _CALL_LOCK.acquire(blocking=False):
        raise AiTutorError("PYR is already thinking about another request", kind="busy", status_code=409)
    try:
        completed = _run(argv, timeout=timeout, cwd=scratch)
    except subprocess.TimeoutExpired as exc:
        raise AiTutorError(f"OpenCode took longer than {int(timeout)}s", kind="timeout", status_code=504) from exc
    except OSError as exc:
        raise AiTutorError(f"OpenCode could not start: {exc}", kind="unavailable", status_code=503) from exc
    finally:
        _CALL_LOCK.release()

    texts: list[str] = []
    errors: list[str] = []
    for line in completed.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "text":
            text = (event.get("part") or {}).get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text)
        elif event.get("type") == "error":
            error = event.get("error") or {}
            errors.append(str(error.get("message") or error.get("type") or "unknown error"))
    if errors and not texts:
        raise AiTutorError(f"OpenCode error: {errors[-1]}", kind="provider")
    if not texts:
        detail = (completed.stderr or "").strip().splitlines()[-1:] or ["no reply"]
        raise AiTutorError(f"OpenCode returned no answer ({detail[0][:200]})", kind="empty")
    # A reply can arrive as several text parts (a short preamble, then the
    # JSON); keep all of them so the object can be found wherever it landed.
    return "\n".join(texts).strip()


def _remember_unparseable(text: str) -> None:
    try:
        path = state_dir() / "last-unparseable-reply.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text[-20_000:], encoding="utf-8")
    except OSError:
        pass


def extract_json_object(text: str) -> dict[str, Any]:
    """Return the JSON object in a reply.

    Models are asked for a bare object, but some wrap it in a fence or add a
    sentence around it. Take the last decodable top-level object; callers
    then validate its exact shape, so tolerance here never loosens grading.
    """

    candidate = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, flags=re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        value = json.loads(candidate)
    except ValueError:
        value = None
        decoder = json.JSONDecoder()
        position = candidate.find("{")
        while position != -1:
            try:
                decoded, end = decoder.raw_decode(candidate, position)
            except ValueError:
                position = candidate.find("{", position + 1)
                continue
            if isinstance(decoded, dict):
                value = decoded
            position = candidate.find("{", end)
    if not isinstance(value, dict):
        _remember_unparseable(text)
        raise AiTutorError("PYR's reply was not valid JSON", kind="unparseable")
    return value


def _bounded(value: Any, limit: int) -> str:
    text = value if isinstance(value, str) else json.dumps(value, indent=1, default=str)
    return text if len(text) <= limit else text[:limit] + "\n…[truncated]"


# The verdict gateway rejects control characters and path-like characters
# (/ \ :) in a reason, and PYR's explanations often quote code ("Correct: ..."),
# so swap them for look-alike text instead of losing the verdict.
_REASON_SWAPS = str.maketrans({":": " —", "/": "∕", "\\": "∖"})


def _reason(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AiTutorError("PYR's reply had no reason", kind="unparseable")
    text = " ".join(value.split()).translate(_REASON_SWAPS)
    return text.replace("  —", " —")[:MAX_REASON_CHARS].strip()


# ── Tasks ──────────────────────────────────────────────────────────────


JUDGE_TASKS = {
    "battle": "a campaign bounty objective, judged against the current encounter objective in the context",
    "boss": "one boss requirement, judged against the current boss requirement in the context",
    "dungeon": "the current Infinite Dungeon question in the context",
    "practice": "a Tutor Notebook practice question",
}


def judge(kind: str, *, context: Any, answer: str, question: str = "") -> dict[str, str]:
    """Grade one bound answer. Raises AiTutorError rather than guessing."""

    if kind not in JUDGE_TASKS:
        raise AiTutorError(f"Unsupported grading kind: {kind}", kind="invalid", status_code=422)
    prompt = "\n\n".join(
        part
        for part in (
            TUTOR_RULES,
            (
                f"Task: decide whether the learner's submission satisfies {JUDGE_TASKS[kind]}. "
                "Be fair to beginners: correct-but-unpolished work passes; work that misses the "
                "objective, does not run, or answers a different question fails."
            ),
            f"Question / objective:\n{_bounded(question, 4_000)}" if question else "",
            f"Bounded game context (JSON):\n{_bounded(context, MAX_CONTEXT_CHARS)}",
            f"Learner submission:\n```\n{_bounded(answer, MAX_ANSWER_CHARS)}\n```",
            (
                'Reply with ONLY this JSON object and nothing else: '
                '{"verdict": "correct" or "incorrect", "reason": "ONE short sentence (under 200 characters) addressed to the learner; '
                'if incorrect, name the gap as a question or hint without giving the fix"}'
            ),
        )
        if part
    )
    reply = extract_json_object(run_prompt(prompt, title=f"Quest Lab · grade {kind}"))
    verdict = reply.get("verdict")
    if verdict not in {"correct", "incorrect"} or set(reply) - {"verdict", "reason"}:
        raise AiTutorError("PYR's verdict was not strictly correct/incorrect", kind="unparseable")
    return {"verdict": verdict, "reason": _reason(reply.get("reason"))}


DUNGEON_QUESTION_SHAPES = {
    "true_false": "a true/false statement; options must be exactly [\"True\", \"False\"]",
    "multiple_choice": "a multiple-choice question with 3 or 4 short SINGLE-LINE options (one correct); put any code the options refer to in the prompt",
    "code_checkpoint": "a request to write working Python code; options must be []",
    "bug_hunt": "a short buggy Python snippet (inside the prompt) with a request to find and explain the bug; options must be []",
    "short_explanation": "a request to explain an idea in two or three sentences; options must be []",
}


# How much code a Dungeon task asks for: harder rooms are longer and more
# practical, and a boss saves its biggest program for the last question.
DUNGEON_CODE_SIZES = {
    "encounter": "a short practical task of about 5-10 lines",
    "elite": "a practical function of about 10-20 lines",
    "boss": "a practical function of about 15-25 lines",
    "boss_final": "a small practical program of about 25-40 lines that combines several ideas",
}
CHOICE_QUESTION_TYPES = frozenset({"multiple_choice", "true_false"})


def _answer_key(reply: dict[str, Any], options: list[str]) -> dict[str, Any]:
    """The correct option index and a one-line why, when the reply has a valid one."""

    answer = reply.get("answer")
    index = None
    if isinstance(answer, bool):
        index = 0 if answer else 1 if options == ["True", "False"] else None
    elif isinstance(answer, int) and 0 <= answer < len(options):
        index = answer
    elif isinstance(answer, str):
        wanted = " ".join(answer.split()).casefold()
        index = next((position for position, option in enumerate(options) if option.casefold() == wanted), None)
    if index is None or len({option.casefold() for option in options}) != len(options):
        return {}
    why = reply.get("why")
    return {"answer": index, "why": _bounded(why, 300) if isinstance(why, str) and why.strip() else ""}


def write_dungeon_question(*, concept: str, question_type: str, difficulty: int, room_type: str, floor: int, fight_step: int = 1, fight_total: int = 1) -> dict[str, Any]:
    shape = DUNGEON_QUESTION_SHAPES.get(question_type, DUNGEON_QUESTION_SHAPES["short_explanation"])
    choice = question_type in CHOICE_QUESTION_TYPES
    size_key = "boss_final" if room_type == "boss" and fight_step >= fight_total else room_type if room_type in DUNGEON_CODE_SIZES else "encounter"
    guidance = (
        "Prefer reading real code (what does this print, which line breaks) over definitions or theory."
        if choice
        else f"Size: {DUNGEON_CODE_SIZES[size_key]}. Make it a practical, game-like task (scores, inventories, cards, maps), not theory."
    )
    reply_shape = (
        '{"prompt": "the question text (may include a fenced code snippet)", "options": ["..."], '
        '"answer": the 0-based index of the correct option, "why": "one short sentence on why it is right"}'
        if choice
        else '{"prompt": "the question text (may include a fenced code snippet)", "options": []}'
    )
    prompt = "\n\n".join(
        (
            TUTOR_RULES,
            "Task: write one fresh Infinite Dungeon question for a Python learner.",
            (
                f"Concept: {concept}\nQuestion type: {question_type} ({shape})\n"
                f"Difficulty: {difficulty} of 5\nRoom: {room_type} on floor {floor}, question {fight_step} of {fight_total} "
                "(elite and boss rooms should be noticeably harder)"
            ),
            guidance,
            "Keep it answerable in the in-game editor. Never put the answer in the prompt.",
            f"Reply with ONLY this JSON object: {reply_shape}",
        )
    )
    reply = extract_json_object(run_prompt(prompt, title="Quest Lab · dungeon question"))
    text = reply.get("prompt")
    options = reply.get("options", [])
    if not isinstance(text, str) or not text.strip() or len(text) > 6_000:
        raise AiTutorError("PYR's question had no usable prompt", kind="unparseable")
    if not isinstance(options, list) or not all(isinstance(item, str) and item.strip() for item in options):
        raise AiTutorError("PYR's question options were malformed", kind="unparseable")
    if question_type == "true_false":
        options = ["True", "False"]
    elif question_type != "multiple_choice":
        options = []
    elif not 2 <= len(options) <= 5:
        raise AiTutorError("PYR's multiple-choice question needs 2-5 options", kind="unparseable")
    # Options are single-line text in the game state; collapse any line breaks
    # (models sometimes put a two-line code snippet in an option).
    options = [" ".join(item.split())[:200] for item in options]
    written: dict[str, Any] = {"prompt": text.strip(), "options": options}
    if options:
        # The key never reaches the save or the browser; the server grades clicks with it.
        written.update(_answer_key(reply, options))
    return written


def choose_practice_lens(*, concept: str, lenses: list[dict[str, str]], learner: Any) -> dict[str, str]:
    allowed = {lens["id"] for lens in lenses}
    catalogue = "\n".join(f"- {lens['id']}: {lens['label']} — {lens['prompt']}" for lens in lenses)
    prompt = "\n\n".join(
        (
            TUTOR_RULES,
            (
                f"Task: pick the practice lens that will help this learner most with '{concept}' right now, "
                "then write one practice question in that lens (in a context unrelated to their current project)."
            ),
            f"Available lenses:\n{catalogue}",
            f"What we know about the learner (JSON):\n{_bounded(learner, 6_000)}",
            (
                'Reply with ONLY this JSON object: {"lens_id": "one of the ids above", "question": "the practice '
                'question", "why": "one short sentence on why this lens"}'
            ),
        )
    )
    reply = extract_json_object(run_prompt(prompt, title="Quest Lab · practice lens"))
    lens_id = reply.get("lens_id")
    question = reply.get("question")
    if lens_id not in allowed or not isinstance(question, str) or not question.strip():
        raise AiTutorError("PYR's lens choice was not usable", kind="unparseable")
    why = reply.get("why") if isinstance(reply.get("why"), str) else ""
    return {"lens_id": lens_id, "question": question.strip()[:3_000], "why": why.strip()[:300]}


def ask(*, question: str, concept: str = "", code: str = "", context: Any = None) -> str:
    prompt = "\n\n".join(
        part
        for part in (
            TUTOR_RULES,
            (
                "Task: answer the learner's question with the smallest useful nudge (a question back, a hint, "
                "or a tiny example in a different context). Keep it under 120 words."
            ),
            f"Concept they are studying: {concept}" if concept else "",
            f"Their scratch file (tutor.py):\n```python\n{_bounded(code, 8_000)}\n```" if code.strip() else "",
            f"Game context (JSON):\n{_bounded(context, 8_000)}" if context else "",
            f"Learner's question:\n{_bounded(question, 2_000)}",
            'Reply with ONLY this JSON object: {"reply": "your answer to the learner"}',
        )
        if part
    )
    reply = extract_json_object(run_prompt(prompt, title="Quest Lab · ask PYR"))
    text = reply.get("reply")
    if not isinstance(text, str) or not text.strip():
        raise AiTutorError("PYR's reply was empty", kind="unparseable")
    return text.strip()[:2_000]


def test_connection(model: str | None = None) -> dict[str, Any]:
    chosen = resolve_model((model if model is not None else load_settings()["model"]).strip())
    started = time.monotonic()
    reply = extract_json_object(
        run_prompt('Reply with ONLY this JSON object: {"ok": true}', title="Quest Lab · connection test", model=model, timeout=90)
    )
    if reply.get("ok") is not True:
        raise AiTutorError("The model answered, but not with the expected test reply", kind="unparseable")
    return {"ok": True, "seconds": round(time.monotonic() - started, 1), "model": chosen or "OpenCode default"}
