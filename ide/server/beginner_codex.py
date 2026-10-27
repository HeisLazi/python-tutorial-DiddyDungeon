"""Portable teaching additions for the beginner campaign's existing Codex pages.

These are generic patterns, not solutions to campaign objectives. They remain
static reference material and are never persisted in the player's save.
"""

BEGINNER_CODEX = {
    "input-output": (
        "Python executes a saved .py file from top to bottom. The editor changes the file, while the terminal starts Python. input() reads text; print() shows output. Run a file with python filename.py from its folder. Software development repeats a cycle: understand the problem, plan a small change, write code, run and test it, read errors, improve it and explain how to use it. Version control such as Git records snapshots so you can inspect or recover earlier changes.",
        "# Save as hello.py, then run: python hello.py\nname = input('Name: ')\nprint(f'Hello, {name}!')\n# input returns a string, even when you type digits",
    ),
    "variables": (
        "Values have types: text is a str, whole numbers are int, decimals are float and True/False are bool. Assignment binds a name; an update reads the current value and stores a new one. Trace one line at a time.",
        "coins = 5          # int\nlabel = 'coins'    # str\ncoins = coins - 2\nprint(coins, label)  # 3 coins",
    ),
    "strings": (
        "Strings are text. Methods such as strip() and lower() return new strings; they do not change the original. Convert input to a number only after considering invalid text.",
        "answer = '  YES  '\ncleaned = answer.strip().lower()\nprint(cleaned == 'yes')  # True\nprint(answer)  # still has spaces",
    ),
    "conditionals": (
        "A Boolean condition decides which indented block runs. == compares values, whereas = assigns a name. Check both ordinary inputs and boundaries such as zero.",
        "age = 18\nif age >= 18:\n    print('adult')\nelse:\n    print('under 18')\n# Try 17, 18 and 19",
    ),
    "loops": (
        "A for loop visits values in an iterable; a while loop repeats while its condition is true. Track what changes on each iteration and ensure a while loop can stop.",
        "total = 0\nfor price in [2, 4, 1]:\n    total += price\nprint(total)  # 7; an empty list gives 0",
    ),
    "functions": (
        "Parameters name inputs; arguments supply values; return sends a result back to the caller. A pure function has no side effects and gives the same result for the same inputs. Keep input, printing and file writes at the program boundary when possible. A module is a Python file whose definitions another file can import; a main guard prevents interactive code running on import. Functions can also be passed as callbacks. A lambda is a short anonymous function, useful for a small one-expression rule.",
        "def above_limit(value, limit):\n    return value > limit\n\n# A function is a value; calling it uses parentheses.\ndef choose(values, predicate):\n    return [value for value in values if predicate(value)]\nprint(choose([1, 3, 5], lambda n: n > 2))  # [3, 5]",
    ),
    "lists": (
        "Lists preserve order and can change. Indexes begin at zero. A comprehension builds a new list: its expression transforms each selected item and an optional if filters items. An explicit loop is equally valid. A tuple is an ordered immutable sequence; a set keeps unique values and is useful for membership checks.",
        "names = ['Key', 'map', 'KEY']\nmatches = [name for name in names if name.lower() == 'key']\nprint(matches)  # ['Key', 'KEY']\nprint(names)    # unchanged\nprint(set(['key', 'key']))  # {'key'}\npoint = (2, 3)  # tuple",
    ),
    "dictionaries": (
        "Dictionaries associate keys with values. Use a dictionary when a meaningful name identifies a value; decide what should happen when a key is missing rather than assuming it exists.",
        "prices = {'tea': 3, 'bread': 4}\nprint(prices['tea'])     # 3\nprint(prices.get('jam')) # None, not a KeyError",
    ),
    "classes": (
        "A class describes how to create objects; each instance has its own attributes. A method receives the instance as self. Prefer giving each instance a fresh mutable collection instead of sharing one accidentally. Composition lets objects work together without inheritance.",
        "class Basket:\n    def __init__(self, owner):\n        self.owner = owner\n        self.items = []  # new list for each instance\n\n    def add(self, item):\n        self.items.append(item)\n\na = Basket('Ada')\nb = Basket('Bo')\na.add('tea')\nprint(b.items)  # []",
    ),
    "references": (
        "Assignment gives a second name to the same mutable object; it is not a copy. A shallow copy creates a new outer collection but nested mutable items may still be shared.",
        "original = ['key']\nalias = original\ncopy = original.copy()\nalias.append('map')\nprint(original)  # ['key', 'map']\nprint(copy)      # ['key']",
    ),
    "exceptions": (
        "Read a traceback from the last line for the exception and message, then find the relevant file and line. Catch the specific error you can recover from; a valid number may still fail a separate range check.",
        "text = 'oops'\ntry:\n    count = int(text)\nexcept ValueError:\n    count = 0\nprint(count)  # 0; decide how to report this to a user",
    ),
    "files-json": (
        "Files preserve data between runs. JSON stores basic values such as dictionaries and lists, not arbitrary Python instances; convert an object into data before saving and validate data on load. Missing and malformed files need separate recovery paths.",
        "import json\nrecord = {'name': 'Ada', 'items': ['map']}\ntext = json.dumps(record)\nloaded = json.loads(text)\nassert loaded['name'] == 'Ada'\n# json.load/json.dump work with opened files",
    ),
    "testing": (
        "Tests compare observed results with expected results. A useful test names a behavior and exercises normal cases and boundaries such as zero, empty input, invalid input and repeated actions. Run tests again after every change.",
        "def double(n):\n    return n * 2\n\nassert double(3) == 6\nassert double(0) == 0\nassert double(-2) == -4\n# Run this file with python test_example.py",
    ),
}
