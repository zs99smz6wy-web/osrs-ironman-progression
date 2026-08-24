"""Focused factual and transition coverage for durable utility-item alternatives."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from apply_action import apply_action  # noqa: E402
from evaluate_progression import evaluate_actions, load_json, validate_account_state  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402


ACTIONS = ROOT / "data" / "progression" / "actions.json"
FACTS = ROOT / "data" / "facts" / "durable-utility-items.json"
FRESH_ACCOUNT = ROOT / "tests" / "fixtures" / "fresh-account.json"
NODES = ROOT / "graph" / "nodes.json"
EDGES = ROOT / "graph" / "edges.json"


class DurableUtilityItemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actions = load_json(ACTIONS)

    @staticmethod
    def _set_level(state: dict, skill: str, level: int) -> None:
        state["skills"][skill] = level
        state["skill_xp"][skill] = minimum_xp_for_level(level)

    def test_catalog_has_exact_current_costs_and_storage_boundaries(self) -> None:
        records = {record["id"]: record for record in load_json(FACTS)["records"]}
        herb = records["durable-utility-herb-sack"]
        self.assertEqual([250, 750], [path["cost"] for path in herb["acquisition_alternatives"]])
        self.assertIn("450 total", herb["ownership_and_storage"]["stores"])
        self.assertEqual(250, records["durable-utility-seed-box"]["acquisition_alternatives"][0]["cost"])
        self.assertIn("60 each", records["durable-utility-gem-bag"]["ownership_and_storage"]["stores"])
        self.assertEqual(100, records["durable-utility-coal-bag"]["acquisition_alternatives"][0]["cost"])
        self.assertEqual(75, records["durable-utility-rune-pouch"]["acquisition_alternatives"][1]["cost"])

    def test_herb_sack_paths_require_herblore_and_consume_only_reported_currency(self) -> None:
        state = load_json(FRESH_ACCOUNT)
        self._set_level(state, "Farming", 34)
        state["resources"]["tithe_farm_points"] = 250
        self.assertEqual("not_eligible", apply_action(self.actions, state, "action:buy-tithe-herb-sack")["status"])

        self._set_level(state, "Herblore", 58)
        tithe = apply_action(self.actions, state, "action:buy-tithe-herb-sack")
        self.assertEqual("applied", tithe["status"])
        self.assertEqual(0, tithe["next_state"]["resources"]["tithe_farm_points"])
        self.assertEqual(1, tithe["next_state"]["items"]["herb_sack"])

        slayer = load_json(FRESH_ACCOUNT)
        self._set_level(slayer, "Herblore", 58)
        slayer["resources"]["slayer_reward_points"] = 750
        result = apply_action(self.actions, slayer, "action:buy-slayer-herb-sack")
        self.assertEqual("applied", result["status"])
        self.assertEqual(0, result["next_state"]["resources"]["slayer_reward_points"])
        self.assertEqual(1, result["next_state"]["items"]["herb_sack"])

    def test_rune_pouch_slayer_alternative_is_fixed_and_lms_remains_non_executable(self) -> None:
        state = load_json(FRESH_ACCOUNT)
        state["resources"]["slayer_reward_points"] = 750
        result = apply_action(self.actions, state, "action:buy-slayer-rune-pouch")
        self.assertEqual("applied", result["status"])
        self.assertEqual(0, result["next_state"]["resources"]["slayer_reward_points"])
        self.assertEqual(1, result["next_state"]["items"]["rune_pouch"])
        self.assertNotIn("action:buy-lms-rune-pouch", {action["id"] for action in self.actions["actions"]})

    def test_observation_balances_do_not_promote_purchase_readiness(self) -> None:
        state = load_json(FRESH_ACCOUNT)
        self._set_level(state, "Farming", 34)
        self._set_level(state, "Herblore", 58)
        state["minigame_activity_observations"] = {
            "tithe-farm": {
                "observed_at": "2026-08-24T20:00:00Z",
                "currency_balances": [{"currency_id": "currency:tithe-farm-points", "amount": 250, "capacity": 16000}]
            }
        }
        original = copy.deepcopy(state)
        validate_account_state(state)
        result = {record["id"]: record for record in evaluate_actions(self.actions, state)}["action:buy-tithe-herb-sack"]
        self.assertEqual("blocked", result["status"])
        self.assertEqual(original, state)

    def test_graph_connects_fixed_alternatives_without_claiming_activity_outputs(self) -> None:
        nodes = {node["id"] for node in load_json(NODES)["nodes"]}
        edges = {(edge["from"], edge["to"]): edge for edge in load_json(EDGES)["edges"]}
        self.assertTrue({"condition:herblore-58", "activity:last-man-standing", "currency:last-man-standing:points"}.issubset(nodes))
        self.assertEqual("alternative", edges[("currency:slayer-reward-points", "item:herb-sack")]["type"])
        self.assertEqual("alternative", edges[("currency:slayer-reward-points", "goal:mta-rune-pouch")]["type"])
        self.assertEqual("makes_obtainable", edges[("activity:last-man-standing", "currency:last-man-standing:points")]["type"])


if __name__ == "__main__":
    unittest.main()
