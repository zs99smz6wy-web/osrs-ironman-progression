"""Focused coverage for transparent strategic candidate scoring."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from evaluate_progression import load_json  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402
from score_candidates import (  # noqa: E402
    ALL_DIMENSIONS,
    COST_DIMENSIONS,
    POSITIVE_DIMENSIONS,
    _result_document,
    score_candidates,
)


FIXTURES = Path(__file__).parent / "fixtures"
ACTIONS_PATH = REPOSITORY_ROOT / "data" / "progression" / "actions.json"
CANDIDATES_PATH = REPOSITORY_ROOT / "strategy" / "candidates.json"


class ScoreCandidatesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.actions_document = load_json(ACTIONS_PATH)
        cls.candidates_document = load_json(CANDIDATES_PATH)

    def score_fixture(self, name: str) -> list[dict]:
        return score_candidates(
            self.candidates_document,
            self.actions_document,
            load_json(FIXTURES / name),
        )

    @staticmethod
    def candidate_by_id(ranked: list[dict], action_id: str) -> dict:
        return next(candidate for candidate in ranked if candidate["action_id"] == action_id)

    def test_strategy_pilot_annotations_cover_requested_actions_and_timing_policy(self) -> None:
        target_ids = {
            "action:a-kingdom-divided",
            "action:establish-player-owned-house",
            "action:build-poh-superior-garden",
            "action:upgrade-ornate-rejuvenation-pool",
            "action:upgrade-crystalline-portal-nexus",
            "action:claim-explorers-ring-current",
            "action:buy-coal-bag",
            "action:buy-gem-bag",
            "action:perilous-moons-quest",
            "action:moons-of-peril",
            "action:motherlode-mine",
        }
        annotations = {candidate["action_id"]: candidate for candidate in self.candidates_document["candidates"]}

        self.assertTrue(target_ids.issubset(annotations))
        for action_id in target_ids:
            dimensions = annotations[action_id]["dimensions"]
            self.assertEqual(set(ALL_DIMENSIONS), set(dimensions))
            self.assertTrue(all(isinstance(value, int) and 0 <= value <= 4 for value in dimensions.values()))
            self.assertTrue(annotations[action_id]["stop_condition"])
            self.assertTrue(annotations[action_id]["reentry_condition"])

        self.assertIn("fixed skill XP", annotations["action:a-kingdom-divided"]["stop_condition"])
        self.assertIn("material", annotations["action:claim-explorers-ring-current"]["stop_condition"])
        self.assertIn("demand", annotations["action:build-poh-superior-garden"]["stop_condition"])
        self.assertIn("demand", annotations["action:upgrade-crystalline-portal-nexus"]["reentry_condition"])
        self.assertIn("self-contained", annotations["action:moons-of-peril"]["stop_condition"])
        self.assertIn("observed combat readiness", annotations["action:moons-of-peril"]["reentry_condition"])
        self.assertIn("99 Mining", annotations["action:motherlode-mine"]["stop_condition"])

        state = load_json(FIXTURES / "fresh-account.json")
        state["skills"]["Mining"] = 30
        state["skill_xp"]["Mining"] = minimum_xp_for_level(30)
        state["resources"]["golden_nuggets"] = 100
        ranked = score_candidates(self.candidates_document, self.actions_document, state)
        by_id = {candidate["action_id"]: candidate for candidate in ranked}

        self.assertIn("action:motherlode-mine", by_id)
        self.assertIn("action:buy-coal-bag", by_id)
        self.assertIn("action:buy-gem-bag", by_id)
        self.assertEqual(11, by_id["action:motherlode-mine"]["base_score"])
        self.assertEqual(1, by_id["action:motherlode-mine"]["adjustments"]["attention_window"])

    def test_only_evaluator_eligible_actions_are_ranked(self) -> None:
        ranked = self.score_fixture("fresh-account.json")
        ranked_ids = {candidate["action_id"] for candidate in ranked}

        self.assertEqual(
            {
                "action:tree-gnome-village",
                "action:children-of-the-sun",
                "action:the-restless-ghost",
                "action:pandemonium",
                "action:royal-titans",
            },
            ranked_ids,
        )
        self.assertNotIn("action:waterfall-quest", ranked_ids)  # needs_preparation
        self.assertNotIn("action:grand-tree", ranked_ids)  # blocked
        self.assertNotIn("action:fossil-island-access", ranked_ids)  # blocked

    def test_infrastructure_and_sailing_tranche_scores_when_factually_eligible(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        state["skills"].update({"Firemaking": 60, "Farming": 34, "Runecraft": 27, "Sailing": 30})
        for skill in ("Firemaking", "Farming", "Runecraft", "Sailing"):
            state["skill_xp"][skill] = minimum_xp_for_level(state["skills"][skill])
        state["quests_completed"].extend(
            [
                "The Dig Site",
                "Bone Voyage",
                "Heroes' Quest",
                "The Fremennik Trials",
                "Temple of the Eye",
                "Sleeping Giants",
                "Pandemonium",
            ]
        )
        state["transport_flags"].append("balloon_transport")
        state["items"].update(
            {
                "clean_necklace": 1,
                "digsite_pendant_charge": 1,
                "magic_logs": 3,
                "iron_bar": 1,
                "common_non_silver_ring": 1,
                "logs": 1,
                "spade": 1,
                "seed_dibber": 1,
                "watering_can": 1,
                "pickaxe": 1,
                "bucket": 1,
                "salvaging_hook": 1,
                "sailing_raft": 1,
            }
        )
        state["resources"].update(
            {
                "coins": 15000,
                "foundry_metal_value_bars": 2,
                "telekinetic_pizazz": 150,
                "graveyard_pizazz": 150,
                "enchantment_pizazz": 1500,
                "alchemist_pizazz": 200,
            }
        )
        state["passive_loops"].update({"kingdom": True, "tears_of_guthix": True})
        state["recurring_observations"] = {
            "kingdom": {"state": "ready", "observed_at": "2026-08-22T10:00:00Z", "ready_at": "2026-08-22T10:00:00Z"},
            "tears_of_guthix": {"state": "ready", "observed_at": "2026-08-22T10:00:00Z", "ready_at": "2026-08-22T10:00:00Z"},
        }
        state["attention_window"]["mode"] = "true_afk"
        state["preferences"] = {"diversity_preference": 0, "intensity_tolerance": 0, "risk_tolerance": 0}

        ranked = score_candidates(self.candidates_document, self.actions_document, state)
        by_id = {candidate["action_id"]: candidate for candidate in ranked}

        expected_ids = {
            "action:learn-digsite-pendant-enchantment",
            "action:bind-fossil-island-pendant-destination",
            "action:unlock-balloon-grand-tree",
            "action:throne-of-miscellania",
            "action:collect-kingdom-resources",
            "action:complete-tears-of-guthix-session",
            "action:guardians-of-the-rift",
            "action:tithe-farm",
            "action:giants-foundry",
            "action:buy-mta-rune-pouch",
            "action:buy-sailing-skiff",
            "action:sailing-bounty-task",
            "action:salvage-shipwrecks",
        }
        self.assertTrue(expected_ids.issubset(by_id))
        self.assertNotIn("action:pandemonium", by_id)  # already completed in this state

        self.assertEqual(13, by_id["action:throne-of-miscellania"]["total_score"])
        self.assertEqual(13, by_id["action:collect-kingdom-resources"]["total_score"])
        self.assertEqual(3, by_id["action:collect-kingdom-resources"]["adjustments"]["attention_window"])
        self.assertEqual(12, by_id["action:giants-foundry"]["total_score"])
        self.assertEqual(3, by_id["action:buy-mta-rune-pouch"]["total_score"])
        self.assertEqual(13, by_id["action:buy-sailing-skiff"]["total_score"])
        self.assertEqual(10, by_id["action:sailing-bounty-task"]["total_score"])
        self.assertEqual(10, by_id["action:salvage-shipwrecks"]["total_score"])

    def test_ranked_results_have_complete_signed_breakdowns_and_stable_totals(self) -> None:
        first = self.score_fixture("passive-loops-ready.json")
        second = self.score_fixture("passive-loops-ready.json")

        self.assertEqual(first, second)
        self.assertTrue(first)
        for candidate in first:
            breakdown = candidate["dimension_breakdown"]
            self.assertEqual(set(ALL_DIMENSIONS), set(breakdown))
            self.assertTrue(all(breakdown[key] >= 0 for key in POSITIVE_DIMENSIONS))
            self.assertTrue(all(breakdown[key] <= 0 for key in COST_DIMENSIONS))
            self.assertEqual(
                sum(value for key, value in breakdown.items() if key != "afk_fit"),
                candidate["base_score"],
            )
            self.assertEqual(
                candidate["base_score"]
                + sum(candidate["adjustments"].values())
                + sum(candidate["contextual_adjustments"].values()),
                candidate["total_score"],
            )

    def test_low_attention_and_preferences_apply_documented_adjustments(self) -> None:
        state = load_json(FIXTURES / "passive-loops-ready.json")
        state["attention_window"]["mode"] = "low_attention"
        state["preferences"] = {
            "diversity_preference": 4,
            "intensity_tolerance": 4,
            "risk_tolerance": 4,
        }

        ranked = score_candidates(self.candidates_document, self.actions_document, state)
        seaweed = self.candidate_by_id(ranked, "action:giant-seaweed-loop")
        wintertodt = self.candidate_by_id(ranked, "action:wintertodt")

        self.assertEqual(
            {
                "lifetime_utility": 4,
                "content_unlock": 1,
                "economic_infrastructure": 4,
                "multi_output": 3,
                "diversity": 3,
                "afk_fit": 3,
                "detour_cost": -1,
                "burnout_risk": 0,
                "danger_risk": -1,
            },
            seaweed["dimension_breakdown"],
        )
        self.assertEqual(
            {
                "attention_window": 1,
                "diversity_preference": 3,
                "intensity_tolerance": 0,
                "risk_tolerance": 1,
            },
            seaweed["adjustments"],
        )
        self.assertEqual(13, seaweed["base_score"])
        self.assertEqual(18, seaweed["total_score"])

        self.assertEqual(
            {
                "attention_window": 0,
                "diversity_preference": 2,
                "intensity_tolerance": 3,
                "risk_tolerance": 2,
            },
            wintertodt["adjustments"],
        )
        self.assertEqual(4, wintertodt["base_score"])
        self.assertEqual(11, wintertodt["total_score"])

    def test_missing_candidate_coverage_is_exposed_as_eligible_unscored(self) -> None:
        candidates_document = copy.deepcopy(self.candidates_document)
        candidates_document["candidates"] = [
            candidate
            for candidate in candidates_document["candidates"]
            if candidate["action_id"] != "action:tree-gnome-village"
        ]

        result = _result_document(
            candidates_document,
            self.actions_document,
            load_json(FIXTURES / "fresh-account.json"),
        )

        self.assertNotIn(
            "action:tree-gnome-village",
            {candidate["action_id"] for candidate in result["ranked_eligible_candidates"]},
        )
        unscored = {action["id"]: action for action in result["eligible_unscored_actions"]}
        self.assertEqual(
            {
                "id": "action:tree-gnome-village",
                "name": "Complete Tree Gnome Village",
                "kind": "quest",
                "fact_ids": ["tree-gnome-village"],
                "status": "eligible",
            },
            unscored["action:tree-gnome-village"],
        )
        self.assertIn("action:natural-history-quiz", unscored)
        self.assertNotIn("action:pandemonium", unscored)

    def test_unknown_candidate_action_id_raises_value_error(self) -> None:
        candidates_document = copy.deepcopy(self.candidates_document)
        candidates_document["candidates"][0]["action_id"] = "action:not-normalized"

        with self.assertRaisesRegex(ValueError, "must refer to normalized factual actions"):
            score_candidates(
                candidates_document,
                self.actions_document,
                load_json(FIXTURES / "fresh-account.json"),
            )

    def test_duplicate_candidate_action_id_raises_value_error(self) -> None:
        candidates_document = copy.deepcopy(self.candidates_document)
        candidates_document["candidates"].append(copy.deepcopy(candidates_document["candidates"][0]))

        with self.assertRaisesRegex(ValueError, "must be unique"):
            score_candidates(
                candidates_document,
                self.actions_document,
                load_json(FIXTURES / "fresh-account.json"),
            )

    def test_invalid_candidate_dimensions_raise_value_error(self) -> None:
        candidates_document = copy.deepcopy(self.candidates_document)
        candidates_document["candidates"][1]["dimensions"].pop("danger_risk")

        with self.assertRaisesRegex(ValueError, "Candidate dimensions must be exactly"):
            score_candidates(
                candidates_document,
                self.actions_document,
                load_json(FIXTURES / "fresh-account.json"),
            )


if __name__ == "__main__":
    unittest.main()
