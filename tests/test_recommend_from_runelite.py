"""Focused synthetic coverage for the local RuneLite recommendation pipeline."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compose_recommendation_chapter import compose_recommendation_chapter  # noqa: E402
from analyze_quest_xp_timing import DEFAULT_EDGES, DEFAULT_NODES  # noqa: E402
from evaluate_progression import DEFAULT_ACTIONS, load_json  # noqa: E402
from import_runelite_export import import_runelite_export, load_export_documents  # noqa: E402
from recommend_from_runelite import recommend_from_runelite  # noqa: E402
from score_candidates import DEFAULT_CANDIDATES  # noqa: E402


FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "runelite-export"
ACCOUNT_DIR = FIXTURE_ROOT / "Sample Iron"
BASE_STATE = ROOT / "graph" / "account-state.example.json"
PIPELINE = ROOT / "scripts" / "recommend_from_runelite.py"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RecommendFromRuneLiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = read_json(BASE_STATE)
        self.documents, self.warnings = load_export_documents(ACCOUNT_DIR)
        self.actions = load_json(DEFAULT_ACTIONS)
        self.candidates = load_json(DEFAULT_CANDIDATES)
        self.nodes = load_json(DEFAULT_NODES)
        self.edges = load_json(DEFAULT_EDGES)

    def direct_sequence(self, *, base: dict | None = None) -> dict:
        imported = import_runelite_export(
            self.base if base is None else base,
            self.documents,
            account_directory=ACCOUNT_DIR,
            expected_account_name="Sample Iron",
            warnings=self.warnings,
        )
        return {
            "import_report": imported["import_report"],
            "recommendation_chapter": compose_recommendation_chapter(
                imported["updated_account_state"],
                self.actions,
                self.candidates,
                self.nodes,
                self.edges,
                active_limit=2,
                afk_limit=2,
                preparation_limit=2,
                quest_xp_limit=2,
                afk_mode="semi_afk",
            ),
        }

    def test_pure_pipeline_matches_separate_import_then_composition(self):
        expected = self.direct_sequence()
        actual = recommend_from_runelite(
            self.base,
            self.documents,
            self.actions,
            self.candidates,
            self.nodes,
            self.edges,
            account_directory=ACCOUNT_DIR,
            expected_account_name="Sample Iron",
            warnings=self.warnings,
            active_limit=2,
            afk_limit=2,
            preparation_limit=2,
            quest_xp_limit=2,
            afk_mode="semi_afk",
        )
        self.assertEqual(expected, actual)

    def test_state_is_omitted_by_default_and_can_be_requested(self):
        result = recommend_from_runelite(
            self.base,
            self.documents,
            self.actions,
            self.candidates,
            self.nodes,
            self.edges,
            account_directory=ACCOUNT_DIR,
            expected_account_name="Sample Iron",
            warnings=self.warnings,
        )
        self.assertNotIn("updated_account_state", result)
        with_state = recommend_from_runelite(
            self.base,
            self.documents,
            self.actions,
            self.candidates,
            self.nodes,
            self.edges,
            account_directory=ACCOUNT_DIR,
            expected_account_name="Sample Iron",
            warnings=self.warnings,
            include_state=True,
        )
        self.assertEqual(10, with_state["updated_account_state"]["skills"]["Sailing"])

    def test_cli_is_deterministic_and_does_not_mutate_input_state(self):
        original = copy.deepcopy(self.base)
        command = [
            sys.executable,
            str(PIPELINE),
            "--account-directory",
            str(ACCOUNT_DIR),
            "--base-state",
            str(BASE_STATE),
            "--active-limit",
            "2",
            "--afk-limit",
            "2",
            "--preparation-limit",
            "2",
            "--quest-xp-limit",
            "2",
            "--afk-mode",
            "semi_afk",
        ]
        first = subprocess.run(command, check=True, capture_output=True, text=True)
        second = subprocess.run(command, check=True, capture_output=True, text=True)
        self.assertEqual(first.stdout, second.stdout)
        document = json.loads(first.stdout)
        self.assertNotIn("updated_account_state", document)
        self.assertEqual(original, read_json(BASE_STATE))

    def test_cli_include_state_and_output_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "recommendation.json"
            command = [
                sys.executable,
                str(PIPELINE),
                "--export-root",
                str(FIXTURE_ROOT),
                "--account-name",
                "Sample Iron",
                "--include-state",
                "--output",
                str(output),
            ]
            first = subprocess.run(command, check=True, capture_output=True, text=True)
            document = read_json(output)
            self.assertIn("updated_account_state", document)
            self.assertEqual("Sample Iron", document["import_report"]["account_name"])
            self.assertEqual("", first.stdout)

            refused = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(0, refused.returncode)
            self.assertIn("refusing to overwrite", refused.stderr)

            forced = subprocess.run([*command, "--force"], check=True, capture_output=True, text=True)
            self.assertEqual("", forced.stdout)


if __name__ == "__main__":
    unittest.main()
