from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from compose_recommendation_chapter import compose_recommendation_chapter  # noqa: E402
from evaluate_progression import evaluate_actions, load_json, validate_account_state  # noqa: E402
from osrs_xp import level_from_xp  # noqa: E402


FIXTURE = REPOSITORY_ROOT / "tests" / "fixtures" / "new-ironman-post-tutorial.json"
ACTIONS = REPOSITORY_ROOT / "data" / "progression" / "actions.json"
CANDIDATES = REPOSITORY_ROOT / "strategy" / "candidates.json"
NODES = REPOSITORY_ROOT / "graph" / "nodes.json"
EDGES = REPOSITORY_ROOT / "graph" / "edges.json"


class NewIronmanPostTutorialFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load_json(FIXTURE)

    def test_is_complete_valid_and_level_consistent(self) -> None:
        validate_account_state(self.state)
        for skill, xp in self.state["skill_xp"].items():
            self.assertEqual(self.state["skills"][skill], level_from_xp(xp))

    def test_has_only_confirmed_arrival_items_and_resources(self) -> None:
        self.assertEqual(
            {
                "axe": 1, "bronze_axe": 1, "pickaxe": 1, "bronze_pickaxe": 1,
                "tinderbox": 1, "small_fishing_net": 1, "shrimps": 2,
                "bronze_dagger": 1, "bronze_sword": 1, "wooden_shield": 1,
                "shortbow": 1, "bronze_arrow": 25, "air_rune": 25,
                "mind_rune": 15, "bucket": 1, "pot": 1, "bread": 1,
                "water_rune": 6, "earth_rune": 4, "body_rune": 2,
            },
            self.state["items"],
        )
        self.assertEqual(25, self.state["resources"]["coins"])
        self.assertEqual(1, self.state["counters"]["quest_points"])
        self.assertFalse(any("ironman" in item or "training_" in item for item in self.state["items"]))

    def test_does_not_infer_post_tutorial_progress(self) -> None:
        self.assertEqual([], self.state["quests_completed"])
        self.assertEqual([], self.state["completed_actions"])
        self.assertEqual([], self.state["transport_flags"])
        self.assertEqual([], self.state["milestones"])
        self.assertEqual([], self.state["gear_thresholds"])
        self.assertTrue(all(tier == "none" for tier in self.state["diary_tiers"].values()))
        self.assertTrue(all(not enabled for enabled in self.state["passive_loops"].values()))
        self.assertEqual({}, self.state["recurring_observations"])

    def test_chapter_uses_the_confirmed_starter_net_without_inventing_outputs(self) -> None:
        actions = load_json(ACTIONS)
        results = {result["id"]: result for result in evaluate_actions(actions, self.state)}
        self.assertEqual("eligible", results["action:small-net-fishing"]["status"])
        self.assertEqual([], results["action:small-net-fishing"]["missing_preparation"])

        chapter = compose_recommendation_chapter(
            self.state,
            actions,
            load_json(CANDIDATES),
            load_json(NODES),
            load_json(EDGES),
            active_limit=20,
            afk_limit=5,
            preparation_limit=5,
            quest_xp_limit=5,
            afk_mode="low_attention",
        )
        afk_ids = {
            option["action_id"]
            for option in chapter["lanes"]["afk_or_low_attention"]["ranked_options"]
        }
        self.assertIn("action:small-net-fishing", afk_ids)
        self.assertFalse(chapter["boundaries"]["random_outputs_inferred"])
        self.assertFalse(chapter["boundaries"]["action_selected"])


if __name__ == "__main__":
    unittest.main()
