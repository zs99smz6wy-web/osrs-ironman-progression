"""Focused coverage for strategic early-transport payoff bundles."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from analyze_transport_bundles import analyze_transport_bundles, contextual_bonus_by_action  # noqa: E402
from evaluate_progression import evaluate_actions, load_json  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402
from score_candidates import score_candidates  # noqa: E402


FIXTURES = Path(__file__).parent / "fixtures"
ACTIONS = REPOSITORY_ROOT / "data" / "progression" / "actions.json"
CANDIDATES = REPOSITORY_ROOT / "strategy" / "candidates.json"
BUNDLES = REPOSITORY_ROOT / "strategy" / "transport-bundles.json"


class TransportBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.actions = load_json(ACTIONS)
        cls.candidates = load_json(CANDIDATES)
        cls.bundle_document = load_json(BUNDLES)

    def analyze(self, state: dict) -> dict:
        return analyze_transport_bundles(
            self.bundle_document, evaluate_actions(self.actions, state), state
        )[0]

    @staticmethod
    def component(bundle: dict, component_id: str) -> dict:
        return next(component for component in bundle["components"] if component["id"] == component_id)

    def test_fresh_state_explains_eligible_and_blocked_components_without_assumptions(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        original = copy.deepcopy(state)

        bundle = self.analyze(state)
        spirit_trees = self.component(bundle, "spirit-trees")
        chronicle = self.component(bundle, "chronicle")
        games_necklace = self.component(bundle, "games-necklace")

        self.assertEqual("eligible", spirit_trees["status"])
        self.assertEqual(1, spirit_trees["contextual_score_bonus"])
        self.assertEqual("blocked", chronicle["status"])
        self.assertEqual("blocked", games_necklace["status"])
        self.assertTrue(games_necklace["missing"])
        self.assertIn("explicitly recorded card", chronicle["usage_caveat"])
        self.assertTrue(bundle["network_incomplete"])
        self.assertEqual(original, state)

    def test_partial_network_gives_each_distinct_durable_capability_at_most_one_bonus(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        state["transport_flags"].append("spirit_trees")
        state["skills"]["Agility"] = 25
        state["skill_xp"]["Agility"] = minimum_xp_for_level(25)
        state["quests_completed"].extend(["Fairytale I - Growing Pains"])
        state["items"].update({"dramen_staff": 1})
        state["resources"]["coins"] = 300
        state["skills"]["Magic"] = 7
        state["skill_xp"]["Magic"] = minimum_xp_for_level(7)
        state["items"].update({"sapphire_necklace": 1, "cosmic_rune": 1, "water_rune": 1})

        bundle = self.analyze(state)
        bonuses = contextual_bonus_by_action([bundle])
        ranked = {candidate["action_id"]: candidate for candidate in score_candidates(self.candidates, self.actions, state)}

        self.assertEqual("complete", self.component(bundle, "spirit-trees")["status"])
        self.assertEqual("eligible", self.component(bundle, "gnome-gliders")["status"])
        self.assertEqual("eligible", self.component(bundle, "fairy-rings")["status"])
        self.assertEqual("eligible", self.component(bundle, "chronicle")["status"])
        self.assertEqual("eligible", self.component(bundle, "games-necklace")["status"])
        self.assertEqual(1, bonuses["action:grand-tree"])
        self.assertEqual(1, bonuses["action:fairy-ring-permission"])
        self.assertEqual(0, bonuses["action:buy-chronicle"])
        self.assertEqual(0, bonuses["action:enchant-games-necklace"])
        self.assertEqual({"early_transport_bundle": 1}, ranked["action:grand-tree"]["contextual_adjustments"])
        self.assertEqual({"early_transport_bundle": 1}, ranked["action:fairy-ring-permission"]["contextual_adjustments"])
        self.assertEqual({"early_transport_bundle": 0}, ranked["action:buy-chronicle"]["contextual_adjustments"])
        self.assertEqual({"early_transport_bundle": 0}, ranked["action:enchant-games-necklace"]["contextual_adjustments"])

    def test_complete_network_uses_observed_state_and_stops_all_bundle_bonus(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        state["transport_flags"].extend(["spirit_trees", "gnome_gliders"])
        state["milestones"].append("fairytale_ii_fairy_godfather_permission")
        state["items"].update(
            {
                "ardougne_cloak_current": 1,
                "chronicle": 1,
                "games_necklace_8": 1,
                "ring_of_dueling_8": 1,
            }
        )

        bundle = self.analyze(state)

        self.assertFalse(bundle["network_incomplete"])
        self.assertEqual(7, bundle["coverage"]["complete"])
        self.assertEqual(0, bundle["coverage"]["eligible"])
        self.assertTrue(all(component["contextual_score_bonus"] == 0 for component in bundle["components"]))
        chronicle = self.component(bundle, "chronicle")
        self.assertEqual("complete", chronicle["status"])
        self.assertEqual("completed", chronicle["source_action_status"])
        self.assertIn("explicitly recorded card", chronicle["usage_caveat"])

    def test_manifest_rejects_duplicate_benefits_before_scoring(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        invalid = copy.deepcopy(self.bundle_document)
        invalid["bundles"][0]["components"][1]["benefit_id"] = "permanent-spirit-tree-access"

        with self.assertRaisesRegex(ValueError, "duplicates a component or benefit"):
            analyze_transport_bundles(invalid, evaluate_actions(self.actions, state), state)


if __name__ == "__main__":
    unittest.main()
