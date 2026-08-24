from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from analyze_quest_xp_thresholds import analyze_quest_xp_thresholds  # noqa: E402
from evaluate_progression import load_json  # noqa: E402


FRESH_ACCOUNT = REPOSITORY_ROOT / "tests" / "fixtures" / "fresh-account.json"
ACTIONS = REPOSITORY_ROOT / "data" / "progression" / "actions.json"
RESEARCH = REPOSITORY_ROOT / "research" / "quest-xp-threshold-sequencing.json"
CONTEXT = REPOSITORY_ROOT / "strategy" / "quest-xp-threshold-contexts.json"


class BoundedQuestXpThresholdPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = copy.deepcopy(load_json(FRESH_ACCOUNT))
        self.actions = load_json(ACTIONS)
        self.research = load_json(RESEARCH)
        self.context = load_json(CONTEXT)

    def _window(self, action_id: str, result: dict[str, object]) -> dict[str, object]:
        return next(item for item in result["quest_xp_timing_windows"] if item["action_id"] == action_id)

    def test_waterfall_exposes_fixed_xp_and_next_meaningful_threshold(self) -> None:
        result = analyze_quest_xp_thresholds(self.state, self.actions, self.research, self.context)
        waterfall = self._window("action:waterfall-quest", result)
        attack = next(item for item in waterfall["skill_effects"] if item["skill"] == "Attack")

        self.assertEqual("needs_preparation", waterfall["status"])
        self.assertEqual("gather_inputs", waterfall["primary_timing_status"])
        self.assertEqual(["gather_inputs"], waterfall["timing_statuses"])
        self.assertEqual(["rope", "air_rune", "earth_rune", "water_rune"], [item["key"] for item in waterfall["required_item_inputs"]])
        self.assertTrue(
            all(
                item["input_role"] == "reusable_or_equipment_or_unmodeled_consumption_input"
                for item in waterfall["required_item_inputs"]
            )
        )
        self.assertEqual(13750, attack["fixed_xp"])
        self.assertEqual(30, attack["resulting_level"])
        self.assertEqual(29, attack["levels_skipped"])
        self.assertIsNone(attack["next_meaningful_modeled_threshold_before"])
        self.assertEqual([], attack["thresholds_crossed"])

    def test_nature_spirit_reports_transitive_prerequisites_and_downstream_threshold(self) -> None:
        self.state["quests_completed"] = ["The Restless Ghost", "Priest in Peril"]
        self.state["items"] = {"ghostspeak_amulet": 1, "silver_sickle": 1}

        result = analyze_quest_xp_thresholds(self.state, self.actions, self.research, self.context)
        nature_spirit = self._window("action:nature-spirit", result)
        crafting = next(item for item in nature_spirit["skill_effects"] if item["skill"] == "Crafting")

        self.assertEqual("eligible", nature_spirit["status"])
        self.assertEqual("do_now", nature_spirit["primary_timing_status"])
        self.assertEqual(["The Restless Ghost", "Priest in Peril"], nature_spirit["immediate_quest_prerequisites"])
        closure = {item["quest_name"]: item for item in nature_spirit["modeled_prerequisite_quest_closure"]}
        self.assertEqual("action:the-restless-ghost", closure["The Restless Ghost"]["modeled_action_id"])
        self.assertEqual("action:priest-in-peril", closure["Priest in Peril"]["modeled_action_id"])
        self.assertEqual(31, crafting["next_meaningful_modeled_threshold_after"]["level"])

    def test_dig_site_keeps_training_and_input_blockers_separate_from_fixed_xp(self) -> None:
        result = analyze_quest_xp_thresholds(self.state, self.actions, self.research, self.context)
        dig_site = self._window("action:the-dig-site", result)

        self.assertEqual("train_requirement", dig_site["primary_timing_status"])
        self.assertEqual(["train_requirement", "gather_inputs"], dig_site["timing_statuses"])
        self.assertEqual({"Agility", "Herblore", "Thieving"}, {gate["key"] for gate in dig_site["hard_skill_gates"]})
        self.assertTrue(all(not gate["satisfied"] for gate in dig_site["hard_skill_gates"]))
        self.assertIn("rope", [item["item_id"] for item in dig_site["consumed_item_inputs"]])
        self.assertIn("pestle_and_mortar", [item["key"] for item in dig_site["reusable_or_equipment_inputs"]])

    def test_player_chosen_xp_is_exposed_but_never_allocated_or_applied(self) -> None:
        original_state = copy.deepcopy(self.state)
        original_actions = copy.deepcopy(self.actions)

        result = analyze_quest_xp_thresholds(self.state, self.actions, self.research, self.context)

        self.assertEqual(original_state, self.state)
        self.assertEqual(original_actions, self.actions)
        self.assertFalse(result["account_state_mutated"])
        self.assertFalse(result["player_chosen_xp_allocated"])
        x_marks = next(
            item for item in result["unallocated_player_chosen_xp_rewards"] if item["action_id"] == "action:x-marks-the-spot"
        )
        self.assertIsNone(x_marks["allocated_skill"])
        self.assertIsNone(x_marks["allocated_xp"])


if __name__ == "__main__":
    unittest.main()
