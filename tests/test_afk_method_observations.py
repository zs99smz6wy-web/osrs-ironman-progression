"""Focused tests for explicit AFK-method account-state observations."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from evaluate_progression import (  # noqa: E402
    evaluate_condition,
    load_json,
    report_afk_method_observations,
    validate_account_state,
)
from validate_data import validate_condition  # noqa: E402


FRESH_ACCOUNT = REPOSITORY_ROOT / "tests" / "fixtures" / "fresh-account.json"


class AfkMethodObservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = copy.deepcopy(load_json(FRESH_ACCOUNT))

    @staticmethod
    def _available_observation() -> dict:
        return {
            "observed_at": "2026-08-24T12:00:00Z",
            "availability": "available",
            "selected_variant": "ammonite-crabs",
            "location": "Mushroom Forest",
            "safety": "acceptable",
            "session_status": "active",
            "interaction_interval_seconds": 600,
        }

    def test_observations_are_optional_and_valid_when_recorded(self) -> None:
        validate_account_state(self.state)

        self.state["afk_method_observations"] = {
            "safe-combat-training": self._available_observation(),
        }
        validate_account_state(self.state)

    def test_validation_rejects_unknown_certainty_and_incoherent_positive_claims(self) -> None:
        self.state["afk_method_observations"] = {
            "shooting-stars": {
                "observed_at": "2026-08-24T12:00:00Z",
                "availability": "unknown",
                "selected_variant": "tier-5",
                "location": None,
                "safety": "unknown",
                "session_status": "unknown",
            }
        }
        with self.assertRaisesRegex(ValueError, "unknown availability cannot include certainty"):
            validate_account_state(self.state)

        self.state["afk_method_observations"] = {
            "shooting-stars": {
                "observed_at": "2026-08-24T12:00:00Z",
                "availability": "available",
                "selected_variant": "tier-5",
                "location": None,
                "safety": "unknown",
                "session_status": "not_started",
            }
        }
        with self.assertRaisesRegex(ValueError, "available availability requires selected_variant and location"):
            validate_account_state(self.state)

        self.state["afk_method_observations"] = {
            "shooting-stars": {
                "observed_at": "not-a-timestamp",
                "availability": "unavailable",
                "selected_variant": None,
                "location": None,
                "safety": "acceptable",
                "session_status": "not_started",
                "interaction_interval_seconds": -1,
            }
        }
        with self.assertRaisesRegex(ValueError, "observed_at must be RFC 3339"):
            validate_account_state(self.state)

    def test_predicates_require_explicit_observations_and_render_current_state(self) -> None:
        conditions = {
            "available": {"type": "afk_method_available", "key": "safe-combat-training"},
            "safe": {"type": "afk_method_safety_acceptable", "key": "safe-combat-training"},
            "combat": {"type": "combat_readiness_observed", "key": "combat_readiness_observation"},
        }
        for condition in conditions.values():
            satisfied, missing = evaluate_condition(condition, self.state)
            self.assertFalse(satisfied)
            self.assertTrue(missing)
        self.assertIn("current: unobserved", evaluate_condition(conditions["available"], self.state)[1][0])
        satisfied, missing = evaluate_condition(
            {"type": "combat_readiness_observed", "key": "combat"}, self.state
        )
        self.assertFalse(satisfied)
        self.assertIn("must be combat_readiness_observation", missing[0])

        self.state["afk_method_observations"] = {"safe-combat-training": self._available_observation()}
        self.state["combat_readiness_observation"] = {
            "observed_at": "2026-08-24T12:00:00Z",
            "loadouts": {"melee": [], "ranged": [], "magic": []},
            "current_hitpoints": 10,
            "current_prayer": 1,
            "food_healing_available": 0,
            "prayer_restore_points_available": 0,
            "emergency_teleport_available": False,
            "recovery_tolerance": "none",
        }
        validate_account_state(self.state)
        for condition in conditions.values():
            satisfied, missing = evaluate_condition(condition, self.state)
            self.assertTrue(satisfied, missing)

    def test_report_copies_only_observed_state_and_never_infers(self) -> None:
        self.state["afk_method_observations"] = {"safe-combat-training": self._available_observation()}
        original = copy.deepcopy(self.state)

        report = report_afk_method_observations(self.state)

        self.assertEqual(self.state["afk_method_observations"], report["observations"])
        self.assertIsNot(self.state["afk_method_observations"], report["observations"])
        for flag in (
            "availability_inferred",
            "safety_inferred",
            "results_inferred",
            "action_eligibility_inferred",
            "outputs_inferred",
        ):
            self.assertFalse(report[flag])
        self.assertEqual(original, self.state)

    def test_data_validator_requires_exact_observation_predicates(self) -> None:
        for condition in (
            {"type": "afk_method_available", "key": "shooting-stars"},
            {"type": "afk_method_safety_acceptable", "key": "shooting-stars"},
            {"type": "combat_readiness_observed", "key": "combat_readiness_observation"},
        ):
            errors: list[str] = []
            validate_condition(condition, "synthetic", errors)
            self.assertEqual([], errors)

        errors = []
        validate_condition({"type": "afk_method_available", "key": " shooting-stars"}, "synthetic", errors)
        self.assertEqual(1, len(errors))
        errors = []
        validate_condition({"type": "combat_readiness_observed", "key": "combat"}, "synthetic", errors)
        self.assertEqual(1, len(errors))


if __name__ == "__main__":
    unittest.main()
