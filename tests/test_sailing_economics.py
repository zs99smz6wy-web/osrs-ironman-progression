from __future__ import annotations

import contextlib
import copy
import io
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from analyze_sailing_economics import analyze_sailing_economics  # noqa: E402
from compose_recommendation_chapter import _print_human_chapter, compose_recommendation_chapter  # noqa: E402
from apply_action import apply_action  # noqa: E402
from evaluate_progression import load_json  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402
from score_candidates import score_candidates  # noqa: E402


FIXTURES = REPOSITORY_ROOT / "tests" / "fixtures"
ACTIONS = REPOSITORY_ROOT / "data" / "progression" / "actions.json"
CANDIDATES = REPOSITORY_ROOT / "strategy" / "candidates.json"
NODES = REPOSITORY_ROOT / "graph" / "nodes.json"
EDGES = REPOSITORY_ROOT / "graph" / "edges.json"
CONTEXTS = REPOSITORY_ROOT / "strategy" / "sailing-economics-contexts.json"


class SailingEconomicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.actions = load_json(ACTIONS)
        cls.candidates = load_json(CANDIDATES)
        cls.contexts = load_json(CONTEXTS)

    def context(self, state: dict) -> dict:
        return analyze_sailing_economics(self.contexts, self.actions, state)["action:pandemonium"]

    def test_post_tutorial_entry_is_self_contained_and_does_not_penalize_pandemonium(self) -> None:
        state = load_json(FIXTURES / "new-ironman-post-tutorial.json")
        original = copy.deepcopy(state)
        candidate = next(
            item for item in score_candidates(self.candidates, self.actions, state)
            if item["action_id"] == "action:pandemonium"
        )
        context = candidate["sailing_economics_context"]

        self.assertEqual("entry_unlock_available", context["status"])
        self.assertEqual(0, context["score_adjustment"])
        self.assertTrue(context["formal_eligibility_preserved"])
        self.assertFalse(context["future_purchase_required_for_entry"])
        self.assertFalse(context["variable_loot_or_income_inferred"])
        self.assertFalse(context["resource_source_inferred"])
        self.assertEqual(0, candidate["contextual_adjustments"]["early_transport_bundle"])
        self.assertEqual(original, state)

    def test_resource_poor_post_pandemonium_shows_only_fixed_skiff_shortfalls(self) -> None:
        state = load_json(FIXTURES / "new-ironman-post-tutorial.json")
        state = apply_action(self.actions, state, "action:pandemonium")["next_state"]

        context = self.context(state)
        objective = context["fixed_next_objective"]

        self.assertEqual("sailing_unlocked_no_fixed_next_objective", context["status"])
        self.assertFalse(objective["ready"])
        self.assertEqual(
            [{"kind": "resource", "key": "coins", "have": 25, "need": 15000, "shortfall": 14975}],
            objective["resource_shortfalls"],
        )
        self.assertEqual("uncommitted_target_no_shortfall_calculated", context["material_planning"]["status"])
        self.assertEqual([], context["material_planning"]["resource_shortfalls"])
        self.assertIn("Planks, nails", context["material_planning"]["note"])
        self.assertIn("Reassess", context["reentry_condition"])

    def test_prepared_skiff_state_is_concrete_without_assuming_upgrade_materials_or_purchase(self) -> None:
        state = load_json(FIXTURES / "new-ironman-post-tutorial.json")
        state["quests_completed"].append("Pandemonium")
        state["milestones"].append("sailing_access")
        state["items"].update({"sailing_raft": 1, "captains_log": 1, "sawmill_coupon": 25})
        state["skills"]["Sailing"] = 15
        state["skill_xp"]["Sailing"] = minimum_xp_for_level(15)
        state["resources"]["coins"] = 15000

        context = self.context(state)
        chapter = compose_recommendation_chapter(
            state, self.actions, self.candidates, load_json(NODES), load_json(EDGES)
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            _print_human_chapter(chapter)

        self.assertEqual("fixed_next_objective_ready", context["status"])
        self.assertTrue(context["fixed_next_objective"]["ready"])
        self.assertEqual([], context["fixed_next_objective"]["skill_shortfalls"])
        self.assertEqual([], context["fixed_next_objective"]["resource_shortfalls"])
        self.assertEqual([], context["material_planning"]["resource_shortfalls"])
        self.assertFalse(context["future_purchase_required_for_entry"])
        self.assertIn("Sailing economics timing:", output.getvalue())
        self.assertIn("[FIXED_NEXT_OBJECTIVE_READY] Buy a Sailing Skiff", output.getvalue())
        self.assertFalse(chapter["boundaries"]["route_selected"])


if __name__ == "__main__":
    unittest.main()
