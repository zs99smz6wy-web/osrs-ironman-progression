"""Focused coverage for bounded state-aware content-window classification."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_content_windows import (  # noqa: E402
    empty_decision_context,
    evaluate_content_windows,
)
from evaluate_progression import load_json  # noqa: E402


CATALOG = ROOT / "strategy" / "content-window-catalog.json"
PROFILE = ROOT / "strategy" / "default-guide-objective-profile.json"
DEFAULT_OPENING_CONTEXT = ROOT / "strategy" / "default-opening-decision-context.json"
ACTIONS = ROOT / "data" / "progression" / "actions.json"
FRESH = ROOT / "tests" / "fixtures" / "fresh-account.json"


class EvaluateContentWindowsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_json(CATALOG)
        cls.profile = load_json(PROFILE)
        cls.actions = load_json(ACTIONS)

    def evaluate(self, state: dict | None = None, context: dict | None = None) -> dict:
        return evaluate_content_windows(
            self.catalog,
            self.profile,
            self.actions,
            state or load_json(FRESH),
            context,
        )

    @staticmethod
    def by_id(result: dict, window_id: str) -> dict:
        return next(row for row in result["objectives"] if row["window_id"] == window_id)

    def test_factual_status_is_preserved_without_creating_a_recommendation(self) -> None:
        result = self.evaluate()
        varlamore = self.by_id(result, "window:varlamore-entry")
        gliders = self.by_id(result, "window:gnome-gliders")

        self.assertEqual("eligible", varlamore["factual_action_status"])
        self.assertEqual("accessible_not_ready", varlamore["classification"])
        self.assertEqual("unconfirmed", varlamore["purpose_status"])
        self.assertIn("no declared purpose", varlamore["readiness_gaps"][0])
        self.assertEqual("blocked", gliders["factual_action_status"])
        self.assertEqual("blocked", gliders["classification"])
        self.assertTrue(gliders["missing_hard_requirements"])
        self.assertFalse(result["route_selected"])

    def test_declared_purpose_and_ideal_trigger_promote_only_timing_state(self) -> None:
        context = empty_decision_context()
        context["attention_mode"] = "active"
        context["declared_purpose_ids"] = ["varlamore_access"]
        context["ideal_trigger_ids"] = ["first_varrock_bundle"]

        row = self.by_id(
            self.evaluate(context=context), "window:varlamore-entry"
        )

        self.assertEqual("ideal_candidate", row["classification"])
        self.assertEqual(["varlamore_access"], row["matched_purpose_ids"])
        self.assertEqual(["first_varrock_bundle"], row["ideal_trigger_evidence"])
        self.assertEqual("eligible", row["factual_action_status"])

    def test_declared_purpose_without_ideal_trigger_is_ready_candidate(self) -> None:
        context = empty_decision_context()
        context["attention_mode"] = "active"
        context["declared_purpose_ids"] = ["spirit_tree_access"]

        row = self.by_id(self.evaluate(context=context), "window:spirit-trees")

        self.assertEqual("ready_candidate", row["classification"])
        self.assertEqual("confirmed", row["purpose_status"])

    def test_factual_coin_blocker_cannot_become_ideal(self) -> None:
        context = empty_decision_context()
        context["declared_purpose_ids"] = ["early_transport"]
        context["ideal_trigger_ids"] = ["first_varrock_bundle"]

        row = self.by_id(self.evaluate(context=context), "window:chronicle")

        self.assertEqual("blocked", row["factual_action_status"])
        self.assertEqual("blocked", row["classification"])
        self.assertTrue(row["missing_hard_requirements"])

    def test_completed_one_time_window_stops_until_explicit_reentry(self) -> None:
        state = load_json(FRESH)
        state["quests_completed"].append("Children of the Sun")
        stopped = self.by_id(self.evaluate(state=state), "window:varlamore-entry")
        self.assertEqual("stop_reached", stopped["classification"])

        context = empty_decision_context()
        context["prior_stop_window_ids"] = ["window:varlamore-entry"]
        context["reentry_trigger_ids"] = ["named_varlamore_activity"]
        reentry = self.by_id(
            self.evaluate(state=state, context=context), "window:varlamore-entry"
        )
        self.assertEqual("reentry_candidate", reentry["classification"])
        self.assertEqual(["named_varlamore_activity"], reentry["reentry_trigger_evidence"])

    def test_catalog_rejects_unknown_action_and_profile_tag(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["windows"][0]["action_id"] = "action:not-real"
        with self.assertRaisesRegex(ValueError, "Unknown content-window action ID"):
            evaluate_content_windows(
                catalog, self.profile, self.actions, load_json(FRESH)
            )

        catalog = copy.deepcopy(self.catalog)
        catalog["windows"][0]["priority_tags"] = ["not_a_profile_priority"]
        with self.assertRaisesRegex(ValueError, "unknown priority tags"):
            evaluate_content_windows(
                catalog, self.profile, self.actions, load_json(FRESH)
            )

    def test_malformed_decision_context_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Decision context fields must be exactly"):
            self.evaluate(context={})

    def test_default_opening_context_preserves_provisional_decision(self) -> None:
        result = self.evaluate(context=load_json(DEFAULT_OPENING_CONTEXT))
        classifications = {
            row["window_id"]: row["classification"] for row in result["objectives"]
        }

        self.assertEqual("active", result["effective_attention_mode"])
        self.assertEqual("ideal_candidate", classifications["window:natural-history-quiz"])
        self.assertEqual("ideal_candidate", classifications["window:varlamore-entry"])
        self.assertEqual("ideal_candidate", classifications["window:sailing-entry"])
        self.assertEqual("ready_candidate", classifications["window:restless-ghost"])
        self.assertEqual("accessible_not_ready", classifications["window:x-marks-the-spot"])
        self.assertEqual("accessible_not_ready", classifications["window:daddys-home"])
        self.assertEqual("accessible_not_ready", classifications["window:poh-foundation"])
        self.assertEqual("blocked", classifications["window:chronicle"])


if __name__ == "__main__":
    unittest.main()
