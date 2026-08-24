from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from analyze_quest_xp_timing import analyze_quest_xp_timing  # noqa: E402
from evaluate_progression import load_json  # noqa: E402
from osrs_xp import level_from_xp  # noqa: E402


FRESH_ACCOUNT = REPOSITORY_ROOT / "tests" / "fixtures" / "fresh-account.json"
ACTIONS = REPOSITORY_ROOT / "data" / "progression" / "actions.json"
NODES = REPOSITORY_ROOT / "graph" / "nodes.json"
EDGES = REPOSITORY_ROOT / "graph" / "edges.json"


class AnalyzeQuestXpTimingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = copy.deepcopy(load_json(FRESH_ACCOUNT))
        self.actions = load_json(ACTIONS)
        self.nodes = load_json(NODES)
        self.edges = load_json(EDGES)

    def _result_for(self, action_id: str, result: dict[str, object] | None = None) -> dict[str, object]:
        timing = result or analyze_quest_xp_timing(self.state, self.actions, self.nodes, self.edges)
        return next(item for item in timing["quest_xp_timing_inputs"] if item["action_id"] == action_id)

    def test_waterfall_reports_exact_fixed_xp_and_preparation_separately(self) -> None:
        quest = self._result_for("action:waterfall-quest")

        self.assertEqual("needs_preparation", quest["status"])
        self.assertTrue(quest["hard_requirements_satisfied"])
        self.assertTrue(quest["missing_preparation"])
        attack = next(item for item in quest["skills"] if item["skill"] == "Attack")
        self.assertEqual(0, attack["current_xp"])
        self.assertEqual(1, attack["current_level"])
        self.assertEqual(13750, attack["fixed_xp"])
        self.assertEqual(13750, attack["resulting_xp"])
        self.assertEqual(30, attack["resulting_level"])
        self.assertEqual(29, attack["levels_skipped"])

    def test_multi_skill_rewards_and_exact_xp_level_conversion(self) -> None:
        self.state["quests_completed"] = ["The Restless Ghost", "Priest in Peril"]
        self.state["items"] = {"ghostspeak_amulet": 1, "silver_sickle": 1}

        quest = self._result_for("action:nature-spirit")

        self.assertEqual("eligible", quest["status"])
        rewards = {item["skill"]: item["fixed_xp"] for item in quest["skills"]}
        self.assertEqual({"Crafting": 3000, "Defence": 2000, "Hitpoints": 2000}, rewards)
        hitpoints = next(item for item in quest["skills"] if item["skill"] == "Hitpoints")
        self.assertEqual(1154, hitpoints["current_xp"])
        self.assertEqual(3154, hitpoints["resulting_xp"])
        self.assertEqual(level_from_xp(3154), hitpoints["resulting_level"])
        self.assertEqual(17, hitpoints["resulting_level"])

    def test_completed_quest_is_excluded_and_reported(self) -> None:
        self.state["quests_completed"].append("Waterfall Quest")

        result = analyze_quest_xp_timing(self.state, self.actions, self.nodes, self.edges)

        self.assertFalse(any(item["action_id"] == "action:waterfall-quest" for item in result["quest_xp_timing_inputs"]))
        self.assertIn(
            {"action_id": "action:waterfall-quest", "quest_name": "Waterfall Quest"},
            result["completed_quests_excluded"],
        )

    def test_analysis_does_not_mutate_account_or_lamp_rewards(self) -> None:
        original_state = copy.deepcopy(self.state)
        original_actions = copy.deepcopy(self.actions)

        result = analyze_quest_xp_timing(self.state, self.actions, self.nodes, self.edges)

        self.assertEqual(original_state, self.state)
        self.assertEqual(original_actions, self.actions)
        self.assertFalse(result["account_state_mutated"])
        self.assertFalse(result["player_chosen_xp_allocated"])
        lamps = result["unallocated_player_chosen_xp_rewards"]
        x_marks = next(item for item in lamps if item["action_id"] == "action:x-marks-the-spot")
        self.assertIsNone(x_marks["allocated_skill"])

    def test_json_cli_preserves_unallocated_lamps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "account.json"
            state_path.write_text(json.dumps(self.state), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(REPOSITORY_ROOT / "scripts" / "analyze_quest_xp_timing.py"),
                    str(state_path),
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        result = json.loads(completed.stdout)
        self.assertFalse(result["player_chosen_xp_allocated"])
        self.assertTrue(result["unallocated_player_chosen_xp_rewards"])


if __name__ == "__main__":
    unittest.main()
