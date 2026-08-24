from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_economic_method_comparison import analyze_economic_method_comparison  # noqa: E402
from evaluate_progression import load_json  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402


class EconomicMethodComparisonTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load_json(ROOT / "tests" / "fixtures" / "fresh-account.json")
        self.actions = load_json(ROOT / "data" / "progression" / "actions.json")
        self.research = load_json(ROOT / "research" / "economic-method-comparison.json")
        self.context = load_json(ROOT / "strategy" / "economic-method-comparison-contexts.json")
        self.facts = load_json(ROOT / "data" / "facts" / "economic-bottlenecks.json")

    def analyze(self, state: dict) -> dict:
        return analyze_economic_method_comparison(state, self.actions, self.research, self.context, self.facts)

    def test_empty_commitments_leave_every_method_unselected(self) -> None:
        report = self.analyze(copy.deepcopy(self.state))

        self.assertEqual("no_declared_commitments", report["commitment_pressure"]["status"])
        self.assertIsNone(report["commitment_pressure"]["named_unfunded_commitment"])
        self.assertTrue(all(item["comparison_status"] == "no_declared_unfunded_commitment" for item in report["method_comparisons"]))
        self.assertTrue(all(not item["method_selected"] for item in report["method_comparisons"]))
        self.assertFalse(report["inference_guarantees"]["method_selected"])

    def test_access_preparation_and_attention_are_kept_separate(self) -> None:
        state = copy.deepcopy(self.state)
        state["resources"]["coins"] = 500
        state["cash_commitments"] = [{"purpose": "Sailing skiff", "coins": 15000, "deadline": "next_goal"}]
        state["skills"]["Sailing"] = 15
        state["skill_xp"]["Sailing"] = minimum_xp_for_level(15)
        state["quests_completed"] = ["Pandemonium"]
        state["attention_window"] = {"duration_minutes": 30, "mode": "low_attention", "player_present": True}

        salvage = next(item for item in self.analyze(state)["method_comparisons"] if item["id"] == "shipwreck_salvaging")

        self.assertEqual("needs_factual_preparation", salvage["comparison_status"])
        self.assertEqual("needs_preparation", salvage["factual_access"]["action_status"])
        self.assertEqual([], salvage["factual_access"]["missing_hard_access"])
        self.assertTrue(salvage["factual_preparation"]["missing_preparation"])
        self.assertTrue(salvage["attention_fit"]["fit"])
        self.assertEqual("Sailing skiff", salvage["stop_reentry"]["named_funding_commitment"]["purpose"])

    def test_eligible_method_can_be_a_comparison_candidate_without_a_rate_or_selection(self) -> None:
        state = copy.deepcopy(self.state)
        state["resources"]["coins"] = 0
        state["cash_commitments"] = [{"purpose": "Barrows gloves", "coins": 130000, "deadline": "near_term"}]
        state["skills"]["Agility"] = 30
        state["skill_xp"]["Agility"] = minimum_xp_for_level(30)
        state["attention_window"] = {"duration_minutes": 45, "mode": "active", "player_present": True}

        pyramid = next(item for item in self.analyze(state)["method_comparisons"] if item["id"] == "agility_pyramid")

        self.assertEqual("comparison_candidate", pyramid["comparison_status"])
        self.assertFalse(pyramid["output_boundary"]["gp_rate_inferred"])
        self.assertFalse(pyramid["output_boundary"]["session_output_inferred"])
        self.assertFalse(pyramid["method_selected"])
        self.assertEqual("Barrows gloves", pyramid["stop_reentry"]["named_funding_commitment"]["purpose"])

    def test_analysis_is_non_mutating_and_does_not_infer_funding_completion(self) -> None:
        state = copy.deepcopy(self.state)
        state["cash_commitments"] = [{"purpose": "House move", "coins": 5000, "deadline": "now"}]
        original = copy.deepcopy(state)

        report = self.analyze(state)

        self.assertEqual(original, state)
        self.assertFalse(report["inference_guarantees"]["account_state_mutated"])
        self.assertFalse(report["inference_guarantees"]["funding_completion_inferred"])
        self.assertTrue(all(not item["stop_reentry"]["commitment_funded_inferred"] for item in report["method_comparisons"]))


if __name__ == "__main__":
    unittest.main()
