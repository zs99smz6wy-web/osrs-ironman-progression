from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from render_execution_segment import DEFAULT_INPUT, load_json, main, render_segment  # noqa: E402


class RenderExecutionSegmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.segment = load_json(DEFAULT_INPUT)

    def test_renderer_includes_the_proof_content_and_research_boundaries(self) -> None:
        page = render_segment(self.segment)

        self.assertIn("Post-Tutorial Varrock Museum Natural History Quiz proof segment", page)
        self.assertIn("Purpose and why now", page)
        self.assertIn("Optional branch", page)
        self.assertIn("Safety and passive checks", page)
        self.assertIn("Reset step checks", page)
        self.assertIn("localStorage", page)
        self.assertIn("Research-only", page)
        self.assertIn("Unresolved", page)
        self.assertIn("https://oldschool.runescape.wiki/w/Kudos", page)
        self.assertIn("does not select a route", page)

    def test_command_writes_a_self_contained_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preview.html"
            self.assertEqual(0, main([str(DEFAULT_INPUT), "--output", str(output)]))
            page = output.read_text(encoding="utf-8")

        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn("<style>", page)
        self.assertIn("<script>", page)
        self.assertNotIn('<script src=', page)
        self.assertNotIn('<link rel="stylesheet"', page)

    def test_renderer_formats_item_quantities_and_uses_unique_branch_heading_ids(self) -> None:
        segment = copy.deepcopy(self.segment)
        segment["starting_state"]["requirements"]["carried_items"] = [
            {"id": "law-rune", "quantity": 3},
            {"id": "potato-seed", "quantity": 1},
        ]
        segment["starting_state"]["requirements"]["banked_items"] = [{"id": "stamina-potion4", "quantity": 2}]
        second_branch = copy.deepcopy(segment["branches"][0])
        second_branch["id"] = "branch:alternate-rune-mysteries-claim"
        segment["branches"].append(second_branch)

        page = render_segment(segment)

        self.assertIn("3 x law-rune", page)
        self.assertIn("1 x potato-seed", page)
        self.assertIn("2 x stamina-potion4", page)
        self.assertNotIn("{&#x27;id&#x27;", page)
        self.assertEqual(1, page.count('id="optional-branch-external-rune-mysteries-claim"'))
        self.assertEqual(1, page.count('id="optional-branch-alternate-rune-mysteries-claim"'))
        self.assertNotIn('id="optional-branch"', page)


if __name__ == "__main__":
    unittest.main()
