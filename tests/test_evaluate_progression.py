"""Scenario coverage for the normalized, non-routing progression evaluator."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from evaluate_progression import evaluate_actions, load_json, validate_account_state  # noqa: E402


FIXTURES = Path(__file__).parent / "fixtures"
ACTIONS_PATH = REPOSITORY_ROOT / "data" / "progression" / "actions.json"


class EvaluateProgressionScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.actions_document = load_json(ACTIONS_PATH)

    def evaluate_fixture(self, name: str) -> dict[str, dict]:
        account_state = load_json(FIXTURES / name)
        results = evaluate_actions(self.actions_document, account_state)
        self.assertIsInstance(results, list)
        self.assertTrue(all({"id", "status", "missing", "missing_preparation"} <= result.keys() for result in results))
        return {result["id"]: result for result in results}

    def assert_missing(self, result: dict, requirement: str) -> None:
        self.assertIn(requirement, result["missing"])

    def test_fresh_account_can_start_no_requirement_actions(self) -> None:
        results = self.evaluate_fixture("fresh-account.json")

        self.assertEqual("needs_preparation", results["action:waterfall-quest"]["status"])
        self.assertEqual("eligible", results["action:tree-gnome-village"]["status"])
        self.assertEqual("eligible", results["action:children-of-the-sun"]["status"])
        self.assertEqual("blocked", results["action:grand-tree"]["status"])

    def test_grand_tree_is_blocked_below_25_agility(self) -> None:
        results = self.evaluate_fixture("fresh-account.json")
        grand_tree = results["action:grand-tree"]

        self.assertEqual("blocked", grand_tree["status"])
        self.assert_missing(grand_tree, "Agility 25 (current: 1)")

    def test_fossil_island_requires_dig_site_and_kudos_then_becomes_eligible(self) -> None:
        blocked_results = self.evaluate_fixture("fresh-account.json")
        fossil_island = blocked_results["action:fossil-island-access"]

        self.assertEqual("blocked", fossil_island["status"])
        self.assert_missing(fossil_island, "complete The Dig Site")
        self.assert_missing(fossil_island, "kudos 100 (current: 0)")

        eligible_results = self.evaluate_fixture("fossil-island-ready.json")
        self.assertEqual("eligible", eligible_results["action:fossil-island-access"]["status"])
        self.assertEqual([], eligible_results["action:fossil-island-access"]["missing"])

    def test_passive_loops_explain_fossil_island_skill_and_resource_gates(self) -> None:
        fresh_results = self.evaluate_fixture("fresh-account.json")
        birdhouses = fresh_results["action:birdhouse-loop"]
        seaweed = fresh_results["action:giant-seaweed-loop"]

        self.assertEqual("blocked", birdhouses["status"])
        self.assert_missing(birdhouses, "unlock transport: fossil_island")
        self.assert_missing(birdhouses, "Crafting 5 (current: 1)")
        self.assert_missing(birdhouses, "Hunter 5 (current: 1)")

        self.assertEqual("blocked", seaweed["status"])
        self.assert_missing(seaweed, "unlock transport: fossil_island")
        self.assert_missing(seaweed, "Farming 23 (current: 1)")
        self.assertIn("1 x seaweed_spore (current: 0)", seaweed["missing_preparation"])

        ready_results = self.evaluate_fixture("passive-loops-ready.json")
        self.assertEqual("eligible", ready_results["action:birdhouse-loop"]["status"])
        self.assertEqual("eligible", ready_results["action:giant-seaweed-loop"]["status"])

    def test_hard_gates_and_preparation_are_reported_separately(self) -> None:
        results = self.evaluate_fixture("fresh-account.json")
        waterfall = results["action:waterfall-quest"]

        self.assertEqual([], waterfall["missing"])
        self.assertIn("1 x rope (current: 0)", waterfall["missing_preparation"])

    def test_completed_one_time_action_and_repeatable_activity_have_distinct_statuses(self) -> None:
        results = self.evaluate_fixture("completed-and-repeatable.json")

        self.assertEqual("completed", results["action:waterfall-quest"]["status"])
        self.assertEqual([], results["action:waterfall-quest"]["missing"])
        self.assertEqual("eligible", results["action:wintertodt"]["status"])
        self.assertEqual([], results["action:wintertodt"]["missing"])

    def test_imported_completed_quest_does_not_require_action_history(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        state["quests_completed"].append("Waterfall Quest")

        results = {result["id"]: result for result in evaluate_actions(self.actions_document, state)}
        self.assertEqual("completed", results["action:waterfall-quest"]["status"])

    def test_fairy_permission_does_not_imply_usable_transport_flag(self) -> None:
        fairy_action = next(action for action in self.actions_document["actions"] if action["id"] == "action:fairy-ring-permission")
        self.assertNotIn("fairy_rings", {outcome["key"] for outcome in fairy_action["outcomes"]})

    def test_malformed_account_state_is_rejected(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        del state["items"]

        with self.assertRaisesRegex(ValueError, "missing required keys"):
            evaluate_actions(self.actions_document, state)

    def test_skill_level_must_match_exact_xp(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["skill_xp"]["Agility"] = 83

        with self.assertRaisesRegex(ValueError, "XP-derived level 2"):
            validate_account_state(state)

    def test_every_supported_skill_is_required(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        del state["skill_xp"]["Sailing"]

        with self.assertRaisesRegex(ValueError, "every supported skill exactly"):
            validate_account_state(state)


if __name__ == "__main__":
    unittest.main()
