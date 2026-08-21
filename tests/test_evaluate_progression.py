"""Scenario coverage for the normalized, non-routing progression evaluator."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from evaluate_progression import evaluate_actions, evaluate_condition, load_json, validate_account_state  # noqa: E402


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
        self.assertIn("2 x seaweed_spore (current: 0)", seaweed["missing_preparation"])
        self.assertIn("1 x seed_dibber (current: 0)", seaweed["missing_preparation"])
        self.assertIn("1 x fishbowl_helmet (current: 0)", seaweed["missing_preparation"])
        self.assertIn("1 x diving_apparatus (current: 0)", seaweed["missing_preparation"])

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

    def test_cash_commitments_are_required_and_validated(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        del state["cash_commitments"]
        with self.assertRaisesRegex(ValueError, "missing required keys"):
            validate_account_state(state)

        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["cash_commitments"] = [{"purpose": "Sailing skiff", "coins": 15000, "deadline": "soon"}]
        with self.assertRaisesRegex(ValueError, "deadline is invalid"):
            validate_account_state(state)

        state["cash_commitments"] = [{"purpose": "", "coins": -1, "deadline": "now"}]
        with self.assertRaisesRegex(ValueError, "purpose must be non-empty"):
            validate_account_state(state)

    def test_kingdom_observation_accepts_explicit_values_without_affecting_actions(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["passive_loops"]["kingdom"] = True
        state["kingdom_observation"] = {
            "approval_percent": 100,
            "worker_assignments": {"maple": 5, "herb": 5},
            "collection_paused": False,
            "observed_at": "2026-08-21T09:30:00Z",
        }

        validate_account_state(state)
        original_state = copy.deepcopy(state)
        results = {result["id"]: result for result in evaluate_actions(self.actions_document, state)}
        self.assertEqual("eligible", results["action:tree-gnome-village"]["status"])
        self.assertEqual(original_state, state)

    def test_kingdom_observation_is_required_and_strictly_validated(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        del state["kingdom_observation"]
        with self.assertRaisesRegex(ValueError, "missing required keys"):
            validate_account_state(state)

        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["kingdom_observation"] = {}
        with self.assertRaisesRegex(ValueError, "requires passive_loops.kingdom"):
            validate_account_state(state)

        state["passive_loops"]["kingdom"] = True
        with self.assertRaisesRegex(ValueError, "invalid fields"):
            validate_account_state(state)

        state["kingdom_observation"] = {
            "approval_percent": 24,
            "worker_assignments": {"maple": 10},
            "collection_paused": False,
            "observed_at": "2026-08-21T09:30:00Z",
        }
        with self.assertRaisesRegex(ValueError, "approval_percent"):
            validate_account_state(state)

        state["kingdom_observation"]["approval_percent"] = 100
        state["kingdom_observation"]["worker_assignments"] = {"maple": 11}
        with self.assertRaisesRegex(ValueError, "integer from 0 to 10"):
            validate_account_state(state)

        state["kingdom_observation"]["worker_assignments"] = {"maple": -1}
        with self.assertRaisesRegex(ValueError, "integer from 0 to 10"):
            validate_account_state(state)

        state["kingdom_observation"]["worker_assignments"] = {"maple": 10, "herb": 1}
        with self.assertRaisesRegex(ValueError, "must not exceed 10"):
            validate_account_state(state)

        state["quests_completed"].append("Royal Trouble")
        state["kingdom_observation"]["worker_assignments"] = {"maple": 10, "herb": 5}
        validate_account_state(state)

        state["kingdom_observation"]["worker_assignments"] = {"maple": 10, "herb": 6}
        with self.assertRaisesRegex(ValueError, "must not exceed 15"):
            validate_account_state(state)

        state["kingdom_observation"]["worker_assignments"] = {"": 1}
        with self.assertRaisesRegex(ValueError, "invalid category"):
            validate_account_state(state)

    def test_kingdom_observation_requires_boolean_pause_and_rfc_3339_timestamp(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["passive_loops"]["kingdom"] = True
        state["kingdom_observation"] = {
            "approval_percent": 25,
            "worker_assignments": {},
            "collection_paused": "false",
            "observed_at": "2026-08-21 09:30:00",
        }
        with self.assertRaisesRegex(ValueError, "collection_paused must be boolean"):
            validate_account_state(state)

        state["kingdom_observation"]["collection_paused"] = False
        with self.assertRaisesRegex(ValueError, "observed_at must be RFC 3339"):
            validate_account_state(state)

    def test_recurring_observations_accept_explicit_observation_without_affecting_actions(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["recurring_observations"] = {
            "birdhouses": {
                "state": "ready",
                "observed_at": "2026-08-20T09:30:00Z",
                "ready_at": "2026-08-20T09:30:00Z",
            }
        }

        validate_account_state(state)
        results = {result["id"]: result for result in evaluate_actions(self.actions_document, state)}
        self.assertEqual("blocked", results["action:birdhouse-loop"]["status"])

    def test_recurring_observations_are_required_and_strictly_validated(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        del state["recurring_observations"]
        with self.assertRaisesRegex(ValueError, "missing required keys"):
            validate_account_state(state)

        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["recurring_observations"] = []
        with self.assertRaisesRegex(ValueError, "must be an object"):
            validate_account_state(state)

        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["recurring_observations"] = {
            "birdhouses": {
                "state": "ready",
                "observed_at": "2026-08-20T09:30:00Z",
                "ready_at": None,
                "extra": True,
            }
        }
        with self.assertRaisesRegex(ValueError, "invalid fields"):
            validate_account_state(state)

        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["recurring_observations"] = {
            "birdhouses": {
                "state": "finished",
                "observed_at": "2026-08-20T09:30:00Z",
                "ready_at": None,
            }
        }
        with self.assertRaisesRegex(ValueError, "state is invalid"):
            validate_account_state(state)

        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["recurring_observations"] = {
            "giant_seaweed": {
                "state": "ready",
                "observed_at": "2026-08-20T09:30:00Z",
                "ready_at": None,
            }
        }
        with self.assertRaisesRegex(ValueError, "is not a known passive loop"):
            validate_account_state(state)

    def test_recurring_observation_timestamps_must_be_rfc_3339(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["recurring_observations"] = {
            "birdhouses": {
                "state": "in_progress",
                "observed_at": "2026-08-20 09:30:00",
                "ready_at": None,
            }
        }
        with self.assertRaisesRegex(ValueError, "observed_at must be RFC 3339"):
            validate_account_state(state)

        state["recurring_observations"]["birdhouses"]["observed_at"] = "2026-08-20T09:30:00+00:00"
        state["recurring_observations"]["birdhouses"]["ready_at"] = "not-a-timestamp"
        with self.assertRaisesRegex(ValueError, "ready_at must be RFC 3339 or null"):
            validate_account_state(state)

    def test_recurring_state_predicate_uses_only_explicit_observations(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        condition = {"type": "recurring_state", "key": "birdhouses", "value": "ready"}

        satisfied, missing = evaluate_condition(condition, state)
        self.assertFalse(satisfied)
        self.assertIn("current: unobserved", missing[0])

        state["recurring_observations"]["birdhouses"] = {
            "state": "ready",
            "observed_at": "2026-08-21T09:30:00-07:00",
            "ready_at": "2026-08-21T09:30:00-07:00",
        }
        satisfied, missing = evaluate_condition(condition, state)
        self.assertTrue(satisfied)
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
