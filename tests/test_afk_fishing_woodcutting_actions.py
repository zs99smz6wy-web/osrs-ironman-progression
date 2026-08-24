"""Focused eligibility and boundary coverage for low-attention fishing and woodcutting."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from evaluate_progression import evaluate_actions, load_json  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402
from score_candidates import score_candidates  # noqa: E402


FIXTURES = REPOSITORY_ROOT / "tests" / "fixtures"
ACTIONS_PATH = REPOSITORY_ROOT / "data" / "progression" / "actions.json"
CANDIDATES_PATH = REPOSITORY_ROOT / "strategy" / "candidates.json"


class LowAttentionFishingWoodcuttingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.actions_document = load_json(ACTIONS_PATH)
        cls.candidates_document = load_json(CANDIDATES_PATH)

    def results_for(self, state: dict) -> dict[str, dict]:
        return {result["id"]: result for result in evaluate_actions(self.actions_document, state)}

    def test_fresh_account_reports_tools_and_levels_without_fake_eligibility(self) -> None:
        results = self.results_for(load_json(FIXTURES / "fresh-account.json"))

        self.assertEqual("needs_preparation", results["action:small-net-fishing"]["status"])
        self.assertIn("1 x small_fishing_net (current: 0)", results["action:small-net-fishing"]["missing_preparation"])
        self.assertEqual("blocked", results["action:fly-fishing"]["status"])
        self.assertIn("Fishing 20 (current: 1)", results["action:fly-fishing"]["missing"])
        self.assertEqual("blocked", results["action:karambwan-fishing"]["status"])
        self.assertIn("Fishing 65 (current: 1)", results["action:karambwan-fishing"]["missing"])
        self.assertEqual("blocked", results["action:willow-woodcutting"]["status"])
        self.assertEqual("blocked", results["action:yew-woodcutting"]["status"])
        self.assertEqual("blocked", results["action:redwood-woodcutting-guild"]["status"])

    def test_fishing_methods_keep_tools_and_partial_quest_access_coupled(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        state["skills"]["Fishing"] = 65
        state["skill_xp"]["Fishing"] = minimum_xp_for_level(65)
        state["items"].update(
            {
                "small_fishing_net": 1,
                "fly_fishing_rod": 1,
                "feathers": 1,
                "karambwan_vessel": 1,
                "raw_karambwanji": 1,
            }
        )
        state["milestones"].append("tai_bwo_wannai_trio_karambwan_fishing_access")

        results = self.results_for(state)
        for action_id in ("action:small-net-fishing", "action:fly-fishing", "action:karambwan-fishing"):
            self.assertEqual("eligible", results[action_id]["status"])

        karambwan = next(action for action in self.actions_document["actions"] if action["id"] == "action:karambwan-fishing")
        self.assertNotIn("fairy_rings", str(karambwan["requirements"]))
        self.assertNotIn("fish_barrel", str(karambwan["preparation"]))
        self.assertEqual([], karambwan["transition"]["effects"])
        self.assertEqual(["variable_activity_output"], [report["type"] for report in karambwan["transition"]["reported_effects"]])

    def test_woodcutting_methods_are_explicit_low_attention_options(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        state["skills"]["Woodcutting"] = 90
        state["skill_xp"]["Woodcutting"] = minimum_xp_for_level(90)
        state["items"]["axe"] = 1
        state["milestones"].append("woodcutting_guild_access")

        results = self.results_for(state)
        for action_id in ("action:willow-woodcutting", "action:yew-woodcutting", "action:redwood-woodcutting-guild"):
            self.assertEqual("eligible", results[action_id]["status"])
            action = next(action for action in self.actions_document["actions"] if action["id"] == action_id)
            self.assertEqual([], action["transition"]["effects"])
            self.assertEqual(["variable_activity_output"], [report["type"] for report in action["transition"]["reported_effects"]])
            self.assertIn("not a true-AFK", str(action["transition"]["reported_effects"]))

    def test_strategy_annotations_rank_only_eligible_concrete_methods(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        state["skills"]["Fishing"] = 65
        state["skill_xp"]["Fishing"] = minimum_xp_for_level(65)
        state["items"].update({"small_fishing_net": 1, "fly_fishing_rod": 1, "feathers": 1, "karambwan_vessel": 1, "raw_karambwanji": 1})
        state["milestones"].append("tai_bwo_wannai_trio_karambwan_fishing_access")

        ranked_ids = {candidate["action_id"] for candidate in score_candidates(self.candidates_document, self.actions_document, state)}
        self.assertTrue({"action:small-net-fishing", "action:fly-fishing", "action:karambwan-fishing"}.issubset(ranked_ids))
        self.assertNotIn("action:willow-woodcutting", ranked_ids)


if __name__ == "__main__":
    unittest.main()
