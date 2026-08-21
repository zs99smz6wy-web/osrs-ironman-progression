"""Scenario coverage for the normalized, non-routing progression evaluator."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from evaluate_progression import evaluate_actions, evaluate_condition, load_json, validate_account_state  # noqa: E402
from validate_data import validate_condition  # noqa: E402


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

    def test_transport_flag_absent_reads_only_confirmed_snapshot_state(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        predicate = {"type": "transport_flag_absent", "key": "lovakengj_minecart_free"}

        self.assertEqual((True, []), evaluate_condition(predicate, state))
        state["transport_flags"].append("lovakengj_minecart_free")
        satisfied, missing = evaluate_condition(predicate, state)
        self.assertFalse(satisfied)
        self.assertEqual(["transport remains locked: lovakengj_minecart_free"], missing)

        valid_errors: list[str] = []
        validate_condition(predicate, "synthetic", valid_errors)
        self.assertEqual([], valid_errors)
        invalid_errors: list[str] = []
        validate_condition(
            {"type": "transport_flag_absent", "key": "lovakengj_minecart_free", "value": True},
            "synthetic",
            invalid_errors,
        )
        self.assertIn("synthetic transport_flag_absent requires a non-empty trimmed key", invalid_errors)

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

    def test_slayer_task_is_required_and_strictly_validated(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        del state["slayer_task"]
        with self.assertRaisesRegex(ValueError, "missing required keys"):
            validate_account_state(state)

        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["slayer_task"] = {}
        with self.assertRaisesRegex(ValueError, "invalid fields"):
            validate_account_state(state)

        state["slayer_task"] = {
            "target": " Aberrant spectres",
            "remaining": 20,
            "observed_at": "2026-08-21T09:30:00Z",
        }
        with self.assertRaisesRegex(ValueError, "non-empty trimmed string"):
            validate_account_state(state)

        state["slayer_task"]["target"] = "Aberrant spectres"
        state["slayer_task"]["remaining"] = 0
        with self.assertRaisesRegex(ValueError, "positive integer"):
            validate_account_state(state)

        state["slayer_task"]["remaining"] = 20
        state["slayer_task"]["observed_at"] = "2026-08-21 09:30:00"
        with self.assertRaisesRegex(ValueError, "observed_at must be RFC 3339"):
            validate_account_state(state)

        state["slayer_task"]["observed_at"] = "2026-08-21T09:30:00-07:00"
        validate_account_state(state)

    def test_slayer_task_target_predicate_uses_only_current_player_observation(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        condition = {"type": "slayer_task_target", "key": "Aberrant spectres"}

        satisfied, missing = evaluate_condition(condition, state)
        self.assertFalse(satisfied)
        self.assertIn("current: none", missing[0])

        state["slayer_task"] = {
            "target": "Aberrant spectres",
            "remaining": 20,
            "observed_at": "2026-08-21T09:30:00Z",
        }
        validate_account_state(state)
        original_state = copy.deepcopy(state)
        satisfied, missing = evaluate_condition(condition, state)
        self.assertTrue(satisfied)
        self.assertEqual([], missing)
        self.assertEqual(original_state, state)

        state["slayer_task"]["remaining"] = 0
        satisfied, missing = evaluate_condition(condition, state)
        self.assertFalse(satisfied)
        self.assertIn("current: none", missing[0])

    def test_diary_tiers_are_required_exact_claim_observations(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        del state["diary_tiers"]
        with self.assertRaisesRegex(ValueError, "missing required keys"):
            validate_account_state(state)

        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        del state["diary_tiers"]["Kandarin"]
        with self.assertRaisesRegex(ValueError, "every canonical region exactly"):
            validate_account_state(state)

        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["diary_tiers"]["Tirannwn"] = "none"
        with self.assertRaisesRegex(ValueError, "every canonical region exactly"):
            validate_account_state(state)

        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["diary_tiers"]["Kandarin"] = "ready"
        with self.assertRaisesRegex(ValueError, "invalid tier"):
            validate_account_state(state)

    def test_diary_tier_predicate_checks_confirmed_claims_not_task_readiness(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["diary_tiers"]["Falador"] = "hard"
        validate_account_state(state)

        satisfied, missing = evaluate_condition(
            {"type": "diary_tier_at_least", "key": "Falador", "value": "medium"}, state
        )
        self.assertTrue(satisfied)
        self.assertEqual([], missing)

        satisfied, missing = evaluate_condition(
            {"type": "diary_tier_at_least", "key": "Falador", "value": "elite"}, state
        )
        self.assertFalse(satisfied)
        self.assertEqual(["Falador diary elite (confirmed: hard)"], missing)

    def test_kourend_memoir_is_a_nullable_strict_account_observation(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        del state["kourend_memoir"]
        with self.assertRaisesRegex(ValueError, "missing required keys"):
            validate_account_state(state)

        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["kourend_memoir"] = {"form": "memoirs", "pages": [], "charges": 1}
        with self.assertRaisesRegex(ValueError, "must not exceed capacity 0"):
            validate_account_state(state)

        state["kourend_memoir"] = {
            "form": "memoirs",
            "pages": ["the_fishers_flute", "the_fishers_flute"],
            "charges": 20,
        }
        with self.assertRaisesRegex(ValueError, "unique canonical page IDs"):
            validate_account_state(state)

        state["kourend_memoir"] = {
            "form": "book_of_the_dead",
            "pages": ["the_fishers_flute"],
            "charges": 20,
        }
        with self.assertRaisesRegex(ValueError, "requires all ordinary pages"):
            validate_account_state(state)

        state["kourend_memoir"] = {
            "form": "book_of_the_dead",
            "pages": [
                "lunch_by_the_lancalliums",
                "the_fishers_flute",
                "history_and_hearsay",
                "jewellery_of_jubilation",
                "a_dark_disposition",
                "secret_page",
            ],
            "charges": 250,
        }
        validate_account_state(state)

    def test_kourend_memoir_predicates_read_only_confirmed_state(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        conditions = {
            "owned": {"type": "kourend_memoir_owned", "key": "kourend_memoir"},
            "form": {"type": "kourend_memoir_form", "key": "memoirs"},
            "page": {"type": "kourend_memoir_page", "key": "the_fishers_flute"},
            "charges": {"type": "kourend_memoir_charges_at_least", "key": "charges", "value": 15},
            "charge_space": {"type": "kourend_memoir_charge_space_at_least", "key": "charges", "value": 5},
        }
        for condition in conditions.values():
            satisfied, _ = evaluate_condition(condition, state)
            self.assertFalse(satisfied)

        state["kourend_memoir"] = {
            "form": "memoirs",
            "pages": ["the_fishers_flute"],
            "charges": 15,
        }
        validate_account_state(state)
        original_state = copy.deepcopy(state)
        for condition in conditions.values():
            satisfied, missing = evaluate_condition(condition, state)
            self.assertTrue(satisfied, missing)
        self.assertEqual(original_state, state)

    def test_data_validator_requires_an_exact_slayer_task_target_predicate(self) -> None:
        valid_errors: list[str] = []
        validate_condition(
            {"type": "slayer_task_target", "key": "Aberrant spectres"},
            "synthetic",
            valid_errors,
        )
        self.assertEqual([], valid_errors)

        invalid_errors: list[str] = []
        validate_condition(
            {"type": "slayer_task_target", "key": " Aberrant spectres", "value": 1},
            "synthetic",
            invalid_errors,
        )
        self.assertIn("synthetic slayer_task_target must contain only type and key", invalid_errors)

    def test_data_validator_requires_an_exact_canonical_diary_tier_predicate(self) -> None:
        valid_errors: list[str] = []
        validate_condition(
            {"type": "diary_tier_at_least", "key": "Kourend & Kebos", "value": "hard"},
            "synthetic",
            valid_errors,
        )
        self.assertEqual([], valid_errors)

        invalid_errors: list[str] = []
        validate_condition(
            {"type": "diary_tier_at_least", "key": "Tirannwn", "value": "ready"},
            "synthetic",
            invalid_errors,
        )
        self.assertIn("synthetic diary_tier_at_least requires a canonical region and tier", invalid_errors)

    def test_data_validator_requires_exact_kourend_memoir_predicates(self) -> None:
        valid_conditions = [
            {"type": "kourend_memoir_owned", "key": "kourend_memoir"},
            {"type": "kourend_memoir_form", "key": "book_of_the_dead"},
            {"type": "kourend_memoir_page", "key": "secret_page"},
            {"type": "kourend_memoir_charges_at_least", "key": "charges", "value": 1},
            {"type": "kourend_memoir_charge_space_at_least", "key": "charges", "value": 1},
        ]
        for condition in valid_conditions:
            errors: list[str] = []
            validate_condition(condition, "synthetic", errors)
            self.assertEqual([], errors)

        invalid_conditions = [
            {"type": "kourend_memoir_owned", "key": "memoirs"},
            {"type": "kourend_memoir_form", "key": "book"},
            {"type": "kourend_memoir_page", "key": "unknown_page"},
            {"type": "kourend_memoir_charges_at_least", "key": "charge", "value": True},
            {"type": "kourend_memoir_charge_space_at_least", "key": "charges", "value": 0},
        ]
        for condition in invalid_conditions:
            errors = []
            validate_condition(condition, "synthetic", errors)
            self.assertEqual(1, len(errors))
            self.assertIn("kourend_memoir", errors[0])


if __name__ == "__main__":
    unittest.main()
