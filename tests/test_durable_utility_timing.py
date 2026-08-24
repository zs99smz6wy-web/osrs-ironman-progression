from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_durable_utility_items import analyze_durable_utility_items  # noqa: E402
from compose_recommendation_chapter import compose_recommendation_chapter  # noqa: E402
from evaluate_progression import evaluate_actions, load_json  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402
from score_candidates import score_candidates  # noqa: E402


ACTIONS = ROOT / "data" / "progression" / "actions.json"
CANDIDATES = ROOT / "strategy" / "candidates.json"
CONTEXTS = ROOT / "strategy" / "durable-utility-item-contexts.json"
FIXTURES = ROOT / "tests" / "fixtures"
NODES = ROOT / "graph" / "nodes.json"
EDGES = ROOT / "graph" / "edges.json"


class DurableUtilityTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.actions = load_json(ACTIONS)
        cls.candidates = load_json(CANDIDATES)
        cls.contexts = load_json(CONTEXTS)

    def analyze(self, state: dict) -> dict[str, dict]:
        results = analyze_durable_utility_items(
            self.contexts, self.actions, evaluate_actions(self.actions, state), state
        )
        return {result["id"]: result for result in results}

    @staticmethod
    def set_level(state: dict, skill: str, level: int) -> None:
        state["skills"][skill] = level
        state["skill_xp"][skill] = minimum_xp_for_level(level)

    def test_post_tutorial_reports_gaps_without_demand_path_or_purchase_inference(self) -> None:
        state = load_json(FIXTURES / "new-ironman-post-tutorial.json")
        original = copy.deepcopy(state)
        contexts = self.analyze(state)

        self.assertTrue(all(item["status"] == "requirements_or_currency_incomplete" for item in contexts.values()))
        self.assertTrue(all(item["selected_path"] is None for item in contexts.values()))
        self.assertTrue(all(not item["demand_observed"] for item in contexts.values()))
        self.assertTrue(all(not item["purchase_selected"] for item in contexts.values()))
        self.assertEqual(original, state)

    def test_one_tithe_balance_exposes_two_ready_purchases_and_currency_contention(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        self.set_level(state, "Farming", 34)
        self.set_level(state, "Herblore", 58)
        state["resources"]["tithe_farm_points"] = 250
        contexts = self.analyze(state)

        self.assertEqual("purchase_ready_needs_demand_confirmation", contexts["herb-sack"]["status"])
        self.assertEqual("purchase_ready_needs_demand_confirmation", contexts["seed-box"]["status"])
        contention = contexts["herb-sack"]["shared_currency_contention"][0]
        self.assertEqual("tithe_farm_points", contention["resource"])
        self.assertEqual(500, contention["combined_cost"])
        self.assertFalse(contention["purchase_order_selected"])

    def test_slayer_alternatives_share_points_without_double_selecting_utility(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        self.set_level(state, "Herblore", 58)
        state["resources"]["slayer_reward_points"] = 750
        contexts = self.analyze(state)
        ranked = {item["action_id"]: item for item in score_candidates(self.candidates, self.actions, state)}

        self.assertEqual(1, contexts["herb-sack"]["ready_path_count"])
        self.assertEqual(1, contexts["rune-pouch"]["ready_path_count"])
        self.assertTrue(contexts["rune-pouch"]["shared_currency_contention"])
        self.assertEqual("herb-sack", ranked["action:buy-slayer-herb-sack"]["durable_utility_context"]["item_id"])
        self.assertEqual("rune-pouch", ranked["action:buy-slayer-rune-pouch"]["durable_utility_context"]["item_id"])
        self.assertEqual(0, ranked["action:buy-slayer-rune-pouch"]["durable_utility_context"]["score_adjustment"])

    def test_owned_item_is_complete_without_inferring_stored_contents(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        state["items"]["coal_bag"] = 1
        context = self.analyze(state)["coal-bag"]
        self.assertEqual("owned", context["status"])
        self.assertTrue(context["owned"])
        self.assertFalse(context["ownership_inferred"])

    def test_chapter_exposes_context_and_preserves_selection_boundaries(self) -> None:
        state = load_json(FIXTURES / "new-ironman-post-tutorial.json")
        chapter = compose_recommendation_chapter(
            state, self.actions, self.candidates, load_json(NODES), load_json(EDGES)
        )
        self.assertEqual(5, len(chapter["durable_utility_item_timing"]))
        self.assertFalse(chapter["boundaries"]["utility_demand_inferred"])
        self.assertFalse(chapter["boundaries"]["utility_purchase_path_selected"])


if __name__ == "__main__":
    unittest.main()
