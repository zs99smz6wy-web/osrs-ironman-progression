"""Focused W5 coverage for report-backed minigame shop transactions."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from apply_action import apply_action  # noqa: E402
from evaluate_progression import load_json  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402


FRESH_ACCOUNT = ROOT / "tests" / "fixtures" / "fresh-account.json"
ACTIONS = ROOT / "data" / "progression" / "actions.json"
NODES = ROOT / "graph" / "nodes.json"
EDGES = ROOT / "graph" / "edges.json"


class MinigameW5ActionsGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actions_document = load_json(ACTIONS)
        self.action_by_id = {action["id"]: action for action in self.actions_document["actions"]}

    @staticmethod
    def _set_level(state: dict, skill: str, level: int) -> None:
        state["skills"][skill] = level
        state["skill_xp"][skill] = minimum_xp_for_level(level)

    def test_tithe_utility_purchases_consume_reported_points_without_session_output(self) -> None:
        state = load_json(FRESH_ACCOUNT)
        self._set_level(state, "Farming", 34)
        state["resources"]["tithe_farm_points"] = 700

        for action_id, item_key, remaining in (
            ("action:buy-gricollers-can", "gricollers_can", 500),
            ("action:buy-tithe-seed-box", "seed_box", 250),
            ("action:buy-tithe-herb-sack", "herb_sack", 0),
        ):
            result = apply_action(self.actions_document, state, action_id)
            self.assertEqual("applied", result["status"], action_id)
            state = result["next_state"]
            self.assertEqual(1, state["items"][item_key])
            self.assertEqual(remaining, state["resources"]["tithe_farm_points"])

        self.assertNotIn("minigame_activity_observations", state)

    def test_regular_void_pieces_use_exact_observed_shop_costs(self) -> None:
        state = load_json(FRESH_ACCOUNT)
        for skill in ("Attack", "Strength", "Defence", "Hitpoints", "Ranged", "Magic"):
            self._set_level(state, skill, 42)
        self._set_level(state, "Prayer", 22)
        state["resources"]["pest_control_commendation_points"] = 850

        for action_id, item_key, remaining in (
            ("action:buy-void-knight-top", "void_knight_top", 600),
            ("action:buy-void-knight-robe", "void_knight_robe", 350),
            ("action:buy-void-knight-gloves", "void_knight_gloves", 200),
            ("action:buy-void-knight-melee-helm", "void_melee_helm", 0),
        ):
            result = apply_action(self.actions_document, state, action_id)
            self.assertEqual("applied", result["status"], action_id)
            state = result["next_state"]
            self.assertEqual(1, state["items"][item_key])
            self.assertEqual(remaining, state["resources"]["pest_control_commendation_points"])

    def test_nightmare_zone_scroll_and_sepulchre_purchases_do_not_simulate_activities(self) -> None:
        state = load_json(FRESH_ACCOUNT)
        state["resources"]["nightmare_zone_points"] = 1550

        first_scroll = apply_action(self.actions_document, state, "action:buy-nmz-scroll-of-redirection")
        second_scroll = apply_action(self.actions_document, first_scroll["next_state"], "action:buy-nmz-scroll-of-redirection")
        self.assertEqual("applied", first_scroll["status"])
        self.assertEqual("applied", second_scroll["status"])
        self.assertEqual(2, second_scroll["next_state"]["items"]["scroll_of_redirection"])
        self.assertEqual(0, second_scroll["next_state"]["resources"]["nightmare_zone_points"])

        state = second_scroll["next_state"]
        state["quests_completed"].append("Sins of the Father")
        state["resources"]["hallowed_sepulchre_marks"] = 300
        focus = apply_action(self.actions_document, state, "action:buy-hallowed-focus")
        instance = apply_action(
            self.actions_document, focus["next_state"], "action:unlock-hallowed-sepulchre-private-instance"
        )
        self.assertEqual("applied", focus["status"])
        self.assertEqual("applied", instance["status"])
        self.assertEqual(1, instance["next_state"]["items"]["hallowed_focus"])
        self.assertEqual(0, instance["next_state"]["resources"]["hallowed_sepulchre_marks"])
        self.assertIn("hallowed_sepulchre_private_instance_unlocked", instance["next_state"]["milestones"])

    def test_pilot_actions_only_spend_reported_balances_and_do_not_cover_blocked_paths(self) -> None:
        pilot_ids = {
            "action:buy-gricollers-can",
            "action:buy-tithe-seed-box",
            "action:buy-tithe-herb-sack",
            "action:buy-void-knight-top",
            "action:buy-void-knight-robe",
            "action:buy-void-knight-gloves",
            "action:buy-void-knight-melee-helm",
            "action:buy-nmz-scroll-of-redirection",
            "action:buy-hallowed-focus",
            "action:unlock-hallowed-sepulchre-private-instance",
        }
        self.assertTrue(pilot_ids.issubset(self.action_by_id))
        self.assertFalse(any("elite-void" in action_id or "salve" in action_id for action_id in pilot_ids))

        for action_id in pilot_ids:
            effects = self.action_by_id[action_id]["transition"]["effects"]
            self.assertFalse(
                any(effect["op"] == "delta" and effect["state"] == "resources" and effect["amount"] > 0 for effect in effects),
                action_id,
            )

    def test_graph_links_only_exact_purchase_dependencies_for_new_currency_nodes(self) -> None:
        nodes = load_json(NODES)["nodes"]
        edges = load_json(EDGES)["edges"]
        node_ids = {node["id"] for node in nodes}
        self.assertEqual(len(nodes), len(node_ids))
        self.assertTrue(all(edge["from"] in node_ids and edge["to"] in node_ids for edge in edges))

        expected_purchase_edges = {
            ("currency:tithe-farm-points", "item:gricollers-can"),
            ("currency:tithe-farm-points", "item:seed-box"),
            ("currency:tithe-farm-points", "item:herb-sack"),
            ("currency:pest-control:commendation-points", "item:void-knight-top"),
            ("currency:pest-control:commendation-points", "item:void-knight-robe"),
            ("currency:pest-control:commendation-points", "item:void-knight-gloves"),
            ("currency:pest-control:commendation-points", "item:void-melee-helm"),
            ("currency:nightmare-zone:points", "item:scroll-of-redirection"),
            ("currency:hallowed-sepulchre:marks", "item:hallowed-focus"),
            ("currency:hallowed-sepulchre:marks", "unlock:hallowed-sepulchre-private-instance"),
        }
        edge_by_pair = {(edge["from"], edge["to"]): edge for edge in edges}
        for pair in expected_purchase_edges:
            self.assertEqual("requires", edge_by_pair[pair]["type"], pair)

        self.assertFalse(
            any(
                edge["type"] == "produces"
                and edge["from"] in {"activity:pest-control", "activity:nightmare-zone", "activity:hallowed-sepulchre"}
                for edge in edges
            )
        )


if __name__ == "__main__":
    unittest.main()
