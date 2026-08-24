"""Focused production-pilot coverage for observation-gated AFK actions."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from compose_recommendation_chapter import compose_recommendation_chapter  # noqa: E402
from evaluate_progression import evaluate_actions, load_json  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402
from score_candidates import score_candidates  # noqa: E402


FIXTURES = REPOSITORY_ROOT / "tests" / "fixtures"
ACTIONS = REPOSITORY_ROOT / "data" / "progression" / "actions.json"
CANDIDATES = REPOSITORY_ROOT / "strategy" / "candidates.json"
NODES = REPOSITORY_ROOT / "graph" / "nodes.json"
EDGES = REPOSITORY_ROOT / "graph" / "edges.json"


class ObservedAfkPilotActionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.actions = load_json(ACTIONS)
        cls.candidates = load_json(CANDIDATES)
        cls.nodes = load_json(NODES)
        cls.edges = load_json(EDGES)

    @staticmethod
    def _star_observation(availability: str = "available") -> dict:
        unknown = availability != "available"
        return {
            "observed_at": "2026-08-24T12:00:00Z",
            "availability": availability,
            "selected_variant": None if unknown else "tier-3",
            "location": None if unknown else "player-confirmed landing site",
            "safety": "unknown" if unknown else "acceptable",
            "session_status": "unknown" if unknown else "not_started",
        }

    @staticmethod
    def _combat_observation() -> dict:
        return {
            "observed_at": "2026-08-24T12:00:00Z",
            "availability": "available",
            "selected_variant": "Sand Crabs",
            "location": "player-confirmed Hosidius coast location",
            "safety": "acceptable",
            "session_status": "not_started",
        }

    @staticmethod
    def _combat_readiness() -> dict:
        return {
            "observed_at": "2026-08-24T12:00:00Z",
            "loadouts": {"melee": [], "ranged": [], "magic": []},
            "current_hitpoints": 10,
            "current_prayer": 1,
            "food_healing_available": 0,
            "prayer_restore_points_available": 0,
            "emergency_teleport_available": False,
            "recovery_tolerance": "none",
        }

    def _results(self, state: dict) -> dict[str, dict]:
        return {result["id"]: result for result in evaluate_actions(self.actions, state)}

    def _chapter(self, state: dict) -> dict:
        return compose_recommendation_chapter(
            state, self.actions, self.candidates, self.nodes, self.edges, active_limit=50, afk_limit=50
        )

    def test_absent_or_unknown_observations_do_not_make_actions_eligible(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        results = self._results(state)
        self.assertEqual("blocked", results["action:shooting-stars"]["status"])
        self.assertEqual("blocked", results["action:safe-combat-training"]["status"])

        state["skills"]["Mining"] = 10
        state["skill_xp"]["Mining"] = minimum_xp_for_level(10)
        state["items"]["pickaxe"] = 1
        state["afk_method_observations"] = {"shooting-stars": self._star_observation("unknown")}
        results = self._results(state)
        self.assertEqual("blocked", results["action:shooting-stars"]["status"])
        self.assertIn("current: unknown", results["action:shooting-stars"]["missing"][0])

    def test_observed_star_needs_pickaxe_then_becomes_report_only_eligible(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["skills"]["Mining"] = 10
        state["skill_xp"]["Mining"] = minimum_xp_for_level(10)
        state["afk_method_observations"] = {"shooting-stars": self._star_observation()}
        results = self._results(state)
        self.assertEqual("needs_preparation", results["action:shooting-stars"]["status"])
        self.assertIn("1 x pickaxe (current: 0)", results["action:shooting-stars"]["missing_preparation"])

        state["items"]["pickaxe"] = 1
        results = self._results(state)
        self.assertEqual("eligible", results["action:shooting-stars"]["status"])
        action = next(action for action in self.actions["actions"] if action["id"] == "action:shooting-stars")
        self.assertEqual([], action["transition"]["effects"])
        self.assertEqual(["variable_activity_output"], [effect["type"] for effect in action["transition"]["reported_effects"]])
        self.assertIn("no output or state effect is applied", action["transition"]["reported_effects"][0]["description"])

    def test_safe_combat_requires_each_observation_and_becomes_eligible_only_when_prepared(self) -> None:
        state = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        state["afk_method_observations"] = {"safe-combat-training": self._combat_observation()}
        results = self._results(state)
        self.assertEqual("blocked", results["action:safe-combat-training"]["status"])
        self.assertIn("combat readiness observation", results["action:safe-combat-training"]["missing"][0])

        state["combat_readiness_observation"] = self._combat_readiness()
        results = self._results(state)
        self.assertEqual("eligible", results["action:safe-combat-training"]["status"])
        action = next(action for action in self.actions["actions"] if action["id"] == "action:safe-combat-training")
        self.assertEqual([], action["transition"]["effects"])
        self.assertEqual(["variable_activity_output"], [effect["type"] for effect in action["transition"]["reported_effects"]])
        self.assertIn("do not infer access", action["transition"]["reported_effects"][0]["description"])

    def test_chapters_hide_unobserved_methods_and_show_only_prepared_observed_methods(self) -> None:
        fresh = copy.deepcopy(load_json(FIXTURES / "fresh-account.json"))
        fresh_ids = {
            candidate["action_id"]
            for candidate in self._chapter(fresh)["lanes"]["afk_or_low_attention"]["ranked_options"]
        }
        self.assertNotIn("action:shooting-stars", fresh_ids)
        self.assertNotIn("action:safe-combat-training", fresh_ids)

        prepared = copy.deepcopy(fresh)
        prepared["skills"]["Mining"] = 10
        prepared["skill_xp"]["Mining"] = minimum_xp_for_level(10)
        prepared["items"]["pickaxe"] = 1
        prepared["afk_method_observations"] = {
            "shooting-stars": self._star_observation(),
            "safe-combat-training": self._combat_observation(),
        }
        prepared["combat_readiness_observation"] = self._combat_readiness()
        ranked_ids = {candidate["action_id"] for candidate in score_candidates(self.candidates, self.actions, prepared)}
        chapter_ids = {
            candidate["action_id"]
            for candidate in self._chapter(prepared)["lanes"]["afk_or_low_attention"]["ranked_options"]
        }
        self.assertTrue({"action:shooting-stars", "action:safe-combat-training"}.issubset(ranked_ids))
        self.assertTrue({"action:shooting-stars", "action:safe-combat-training"}.issubset(chapter_ids))


if __name__ == "__main__":
    unittest.main()
