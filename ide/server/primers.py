"""Calm, short primer cards shown by "Start Today" before a bounty begins.

Each primer follows the Teach -> Practice -> Teach-back steps of
``LEARNING_PROTOCOL.md``: a few tiny steps, then one predict-the-output check.
Examples deliberately live in a different domain from the campaign (bakery,
garden, music, weather) so they teach the idea without being pasteable into the
bounty. Primers are static reference material: they are never written to the
player's save, award nothing and have no penalty for a wrong answer.

The ``check`` code is real Python. ``test_primers.py`` runs every snippet and
asserts that the marked answer is what it really prints.
"""

from __future__ import annotations

from typing import Any

PRIMERS: dict[str, dict[str, Any]] = {
    "input-output": {
        "title": "Running Python and showing output",
        "steps": [
            {"heading": "The idea", "body": "A Python program is a text file of instructions. Python reads it from the top, one line at a time, and does each one. The editor changes the file; the terminal runs it."},
            {"heading": "A picture", "body": "Think of a recipe card. The card does nothing until a cook follows it. print() is the cook announcing a step out loud so you can hear it.", "code": "print('Proofing the dough')\nprint('Baking')"},
            {"heading": "Watch for", "body": "Text goes inside quotes. input() waits for the person to type, and always hands back text, even if they typed digits."},
        ],
        "check": {
            "question": "What does this print?",
            "code": "print('Oven')\nprint('ready')",
            "options": ["Oven ready", "Oven\nready", "ready\nOven"],
            "answer": 1,
            "explain": "Each print() starts a new line, and lines run top to bottom.",
        },
    },
    "variables": {
        "title": "Variables: names for values",
        "steps": [
            {"heading": "The idea", "body": "A variable is a name stuck on a value. The = sign does not mean 'equals' here. It means 'store the right side under the name on the left'."},
            {"heading": "A picture", "body": "A labelled jar. You can empty it and put something else in, and the label stays.", "code": "loaves = 6\nloaves = loaves - 2\nprint(loaves)"},
            {"heading": "Watch for", "body": "Python works out the right side first, using the old value, then stores the result. Text, whole numbers and decimals are different types."},
        ],
        "check": {
            "question": "What does this print?",
            "code": "seeds = 10\nseeds = seeds + 5\nprint(seeds)",
            "options": ["10", "5", "15"],
            "answer": 2,
            "explain": "The right side is 10 + 5 = 15, and that is stored back under the name seeds.",
        },
    },
    "conditionals": {
        "title": "Conditionals: choosing a path",
        "steps": [
            {"heading": "The idea", "body": "An if statement checks a question that is True or False. If True, the indented block under it runs. If not, Python skips it (or runs the else block)."},
            {"heading": "A picture", "body": "A fork on a hiking trail with a signpost. == asks 'are these the same?', while = stores a value.", "code": "temp = 3\nif temp <= 0:\n    print('ice')\nelse:\n    print('water')"},
            {"heading": "Watch for", "body": "Boundaries. Is 0 included? Test the exact edge value, not only the easy ones."},
        ],
        "check": {
            "question": "What does this print?",
            "code": "score = 50\nif score >= 50:\n    print('pass')\nelse:\n    print('retry')",
            "options": ["pass", "retry", "nothing"],
            "answer": 0,
            "explain": ">= includes the edge: 50 >= 50 is True, so the first block runs.",
        },
    },
    "loops": {
        "title": "Loops: repeating without retyping",
        "steps": [
            {"heading": "The idea", "body": "A for loop takes a collection and runs the same block once per item. A while loop repeats as long as its condition stays True."},
            {"heading": "A picture", "body": "A conveyor belt past a worker. The worker does the same job to each box that arrives.", "code": "total = 0\nfor tempo in [60, 90, 120]:\n    total = total + tempo\nprint(total)"},
            {"heading": "Watch for", "body": "Ask what changes each time round. A while loop must change something, or it never stops."},
        ],
        "check": {
            "question": "What does this print?",
            "code": "count = 0\nfor note in ['do', 're', 'mi']:\n    count = count + 1\nprint(count)",
            "options": ["0", "3", "mi"],
            "answer": 1,
            "explain": "The loop body runs once for each of the 3 items, adding 1 each time.",
        },
    },
    "functions": {
        "title": "Functions: a named, reusable step",
        "steps": [
            {"heading": "The idea", "body": "A function packages some steps under a name. Parameters are the inputs it expects. return hands a result back to whoever called it."},
            {"heading": "A picture", "body": "A coffee machine: put beans and water in, get a cup out. You do not rebuild the machine each time.", "code": "def tip(bill, percent):\n    return bill * percent / 100\n\nprint(tip(80, 10))"},
            {"heading": "Watch for", "body": "Defining a function does not run it. Calling it, with parentheses, does. print shows something on screen; return gives a value back."},
        ],
        "check": {
            "question": "What does this print?",
            "code": "def double(n):\n    return n * 2\n\nprint(double(4) + 1)",
            "options": ["9", "8", "10"],
            "answer": 0,
            "explain": "double(4) returns 8, and then 8 + 1 is 9.",
        },
    },
    "lists": {
        "title": "Lists: ordered collections",
        "steps": [
            {"heading": "The idea", "body": "A list keeps values in order inside square brackets. You can add, remove and change items. Counting starts at zero, so the first item is index 0."},
            {"heading": "A picture", "body": "A playlist. Songs have a position, you can add one to the end, and the order matters.", "code": "songs = ['calm', 'jazz', 'rock']\nsongs.append('blues')\nprint(songs[0])\nprint(len(songs))"},
            {"heading": "Watch for", "body": "The last valid index is one less than the length. Asking for an index that does not exist is an error."},
        ],
        "check": {
            "question": "What does this print?",
            "code": "plants = ['fern', 'moss', 'aloe']\nprint(plants[1])",
            "options": ["fern", "moss", "aloe"],
            "answer": 1,
            "explain": "Index 0 is fern, so index 1 is moss.",
        },
    },
    "dictionaries": {
        "title": "Dictionaries: look things up by name",
        "steps": [
            {"heading": "The idea", "body": "A dictionary pairs keys with values. Use one when a meaningful name, not a position, finds the thing you want."},
            {"heading": "A picture", "body": "A phone contact list: you search by the person's name, not by their row number.", "code": "rain_mm = {'mon': 4, 'tue': 0}\nprint(rain_mm['mon'])\nprint(rain_mm.get('sun', 'no data'))"},
            {"heading": "Watch for", "body": "Square brackets on a missing key raise an error. .get() lets you choose what happens instead."},
        ],
        "check": {
            "question": "What does this print?",
            "code": "cost = {'tea': 3, 'cake': 5}\nprint(cost.get('jam', 0))",
            "options": ["0", "an error", "None"],
            "answer": 0,
            "explain": ".get() returns the second argument when the key is missing, so you see 0 and no crash.",
        },
    },
    "exceptions": {
        "title": "Exceptions: when something goes wrong",
        "steps": [
            {"heading": "The idea", "body": "When Python cannot continue it raises an exception and stops with a traceback. Read the last line first: it names the error and says why."},
            {"heading": "A picture", "body": "A smoke alarm. It tells you what went wrong and roughly where, and try/except is you deciding what to do about it.", "code": "try:\n    gears = int('twelve')\nexcept ValueError:\n    gears = 0\nprint(gears)"},
            {"heading": "Watch for", "body": "Catch the specific error you can handle, such as ValueError. A bare catch-everything hides real bugs."},
        ],
        "check": {
            "question": "What does this print?",
            "code": "try:\n    n = int('4x')\nexcept ValueError:\n    n = -1\nprint(n)",
            "options": ["4", "-1", "an error message"],
            "answer": 1,
            "explain": "int('4x') fails with ValueError, the except block runs, and n becomes -1.",
        },
    },
    "testing": {
        "title": "Testing: checking your code on purpose",
        "steps": [
            {"heading": "The idea", "body": "A test compares what your code really does with what you expect. assert says 'this must be True', and it stops loudly if it is not."},
            {"heading": "A picture", "body": "Taste-testing a soup before serving: small, quick checks, repeated after every change.", "code": "def to_fahrenheit(c):\n    return c * 9 / 5 + 32\n\nassert to_fahrenheit(0) == 32\nassert to_fahrenheit(100) == 212\nprint('ok')"},
            {"heading": "Watch for", "body": "Test the edges: zero, empty, wrong input. Run the tests again after every change."},
        ],
        "check": {
            "question": "What does this print?",
            "code": "def add(a, b):\n    return a + b\n\nassert add(2, 2) == 4\nprint('checked')",
            "options": ["checked", "AssertionError", "4"],
            "answer": 0,
            "explain": "add(2, 2) really is 4, so the assert passes silently and the next line runs.",
        },
    },
    "classes": {
        "title": "Classes: blueprints for objects",
        "steps": [
            {"heading": "The idea", "body": "A class describes what a kind of thing holds and does. Each object you make from it keeps its own data. self means 'this particular object'."},
            {"heading": "A picture", "body": "A cookie cutter and the cookies. One cutter, many cookies, each with its own icing.", "code": "class Mug:\n    def __init__(self, colour):\n        self.colour = colour\n\n    def describe(self):\n        return 'a ' + self.colour + ' mug'\n\nprint(Mug('blue').describe())"},
            {"heading": "Watch for", "body": "Give every object its own fresh list in __init__. A list created outside it is shared by all of them."},
        ],
        "check": {
            "question": "What does this print?",
            "code": "class Lamp:\n    def __init__(self):\n        self.on = False\n\n    def toggle(self):\n        self.on = not self.on\n\nlamp = Lamp()\nlamp.toggle()\nprint(lamp.on)",
            "options": ["False", "True", "None"],
            "answer": 1,
            "explain": "The lamp starts off (False), toggle() flips it, so it ends True.",
        },
    },
    "files-json": {
        "title": "Files and JSON: remembering between runs",
        "steps": [
            {"heading": "The idea", "body": "Variables vanish when a program ends. Writing to a file keeps data. JSON is a plain-text format for dictionaries and lists, and json.dumps / json.loads convert between data and text."},
            {"heading": "A picture", "body": "A notebook on a shelf. You write, close it, and next week it is still there.", "code": "import json\nrecipe = {'name': 'soup', 'steps': 3}\ntext = json.dumps(recipe)\nprint(json.loads(text)['name'])"},
            {"heading": "Watch for", "body": "A file may be missing or damaged. Plan for both before trusting what you load."},
        ],
        "check": {
            "question": "What does this print?",
            "code": "import json\ndata = json.loads('{\"lives\": 3}')\nprint(data['lives'] + 1)",
            "options": ["3", "4", "an error"],
            "answer": 1,
            "explain": "json.loads gives back a real dictionary, and 3 + 1 is 4.",
        },
    },
}


def primer_ids() -> list[str]:
    return list(PRIMERS)


def public_primer(sign: str) -> dict[str, Any] | None:
    """Return a primer without its answer key, or None when none is written."""

    primer = PRIMERS.get(sign)
    if primer is None:
        return None
    check = primer["check"]
    return {
        "sign": sign,
        "title": primer["title"],
        "steps": [dict(step) for step in primer["steps"]],
        "check": {
            "question": check["question"],
            "code": check["code"],
            "options": list(check["options"]),
        },
    }


def grade_check(sign: str, choice: int) -> dict[str, Any] | None:
    """Grade one teach-back answer. Nothing is stored and nothing is awarded."""

    primer = PRIMERS.get(sign)
    if primer is None:
        return None
    check = primer["check"]
    correct = choice == check["answer"]
    result: dict[str, Any] = {"ok": True, "sign": sign, "correct": correct, "explain": check["explain"]}
    if correct:
        result["answer"] = check["answer"]
    return result


def today_plan(progress: Any, contract_lookup: Any, limit: int = 3) -> dict[str, Any]:
    """Build the Start Today view: the next bounties and a primer for each.

    ``contract_lookup(branch, mob_name)`` returns the authored contract (which
    carries the concept ``sign``). Bounties without a written primer are still
    listed, with ``primer`` set to None, so the screen can go straight to the
    work instead of inventing teaching.
    """

    projects = progress.get("projects") if isinstance(progress, dict) else None
    project = next(
        (item for item in projects or [] if isinstance(item, dict) and item.get("status") == "active"),
        None,
    )
    if project is None:
        return {"ok": True, "project": None, "bounties": []}
    bounties: list[dict[str, Any]] = []
    for mob in project.get("mobs") or []:
        if not isinstance(mob, dict) or mob.get("status") in {"defeated", "cleared"}:
            continue
        contract = contract_lookup(project.get("branch"), mob.get("name")) or {}
        sign = contract.get("sign") if isinstance(contract.get("sign"), str) else None
        bounties.append(
            {
                "name": str(mob.get("name") or ""),
                "concept": str(mob.get("concept") or ""),
                "task": str(mob.get("encounter") or ""),
                "sign": sign,
                "primer": public_primer(sign) if sign else None,
            }
        )
        if len(bounties) >= limit:
            break
    return {
        "ok": True,
        "project": {"name": str(project.get("name") or project.get("branch") or "")},
        "bounties": bounties,
    }
