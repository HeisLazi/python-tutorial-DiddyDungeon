from __future__ import annotations

import re
import unittest
from pathlib import Path

from ide.server.state import (
    CODEX_CONCEPT_PAGES,
    DUNGEON_REGIONS,
    HUNTER_BEASTS,
    HUNTER_SIGN_CONCEPTS,
    HUNTER_SIGN_KEYWORDS,
)

VIEWS = Path(__file__).resolve().parents[1] / "frontend" / "src" / "RpgViews.jsx"


def block(source: str, start: str) -> str:
    """The text of a top-level `const NAME = {` or `[` literal."""

    begin = source.index(start)
    end = source.index("\n}\n" if start.rstrip().endswith("{") else "\n]\n", begin)
    return source[begin:end]


def has_key(text: str, key: str) -> bool:
    return re.search(rf"^\s*(?:'{re.escape(key)}'|{re.escape(key)}):", text, re.MULTILINE) is not None


class CodexBestiaryTests(unittest.TestCase):
    def test_every_sign_has_a_page_a_beast_a_concept_and_one_region(self):
        signs = set(HUNTER_SIGN_KEYWORDS)
        self.assertEqual({page["id"] for page in CODEX_CONCEPT_PAGES}, signs)
        self.assertEqual(set(HUNTER_BEASTS), signs)
        self.assertEqual(set(HUNTER_SIGN_CONCEPTS), signs)
        homes = [sign for region in DUNGEON_REGIONS.values() for sign in region["signs"]]
        self.assertEqual(sorted(homes), sorted(signs), "each sign lives in exactly one region")
        for page in CODEX_CONCEPT_PAGES:
            for key in ("title", "definition", "when_to_use", "check_prompt"):
                self.assertTrue(str(page[key]).strip(), (page["id"], key))
            self.assertEqual(len(page["common_mistakes"]), len(page["mistake_examples"]), page["id"])

    def test_the_frontend_codex_knows_every_sign_and_region(self):
        source = VIEWS.read_text(encoding="utf-8")
        beasts = block(source, "const HUNT_BEASTS = {")
        sigils = block(source, "const HUNT_SIGILS = {")
        regions = block(source, "const HUNT_REGIONS = [")
        bosses = source[source.index("const DELVE_BOSSES = {"):].split("\n", 1)[0]
        for sign in HUNTER_SIGN_KEYWORDS:
            with self.subTest(sign=sign):
                self.assertTrue(has_key(beasts, sign), "HUNT_BEASTS")
                self.assertTrue(has_key(sigils, sign), "HUNT_SIGILS")
                self.assertIn(f"'{sign}'", regions, "HUNT_REGIONS")
        for region in DUNGEON_REGIONS.values():
            with self.subTest(region=region["id"]):
                self.assertIn(f"id: '{region['id']}'", regions)
                self.assertIn(region["boss"], bosses)
                self.assertLessEqual(region["danger"], 4)


if __name__ == "__main__":
    unittest.main()
