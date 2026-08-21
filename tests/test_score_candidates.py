"""Focused coverage for transparent strategic candidate scoring."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from evaluate_progression import load_json  # noqa: E402
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

    def test_only_evaluator_eligible_actions_are_ranked(self) -> None:
        ranked = self.score_fixture("fresh-account.json")
        ranked_ids = {candidate["action_id"] for candidate in ranked}

        self.assertEqual(
            {"action:tree-gnome-village", "action:children-of-the-sun", "action:the-restless-ghost"},
            ranked_ids,
        )
        self.assertNotIn("action:waterfall-quest", ranked_ids)  # needs_preparation
        self.assertNotIn("action:grand-tree", ranked_ids)  # blocked
        self.assertNotIn("action:fossil-island-access", ranked_ids)  # blocked

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
                candidate["base_score"] + sum(candidate["adjustments"].values()),
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
        self.assertEqual(
            [
                {
                    "id": "action:tree-gnome-village",
                    "name": "Complete Tree Gnome Village",
                    "kind": "quest",
                    "fact_ids": ["tree-gnome-village"],
                    "status": "eligible",
                }
            ],
            result["eligible_unscored_actions"],
        )

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
