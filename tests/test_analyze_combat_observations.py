from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from analyze_combat_observations import analyze_combat_observations  # noqa: E402
from evaluate_progression import load_json, validate_account_state  # noqa: E402


FRESH_ACCOUNT = REPOSITORY_ROOT / "tests" / "fixtures" / "fresh-account.json"


class AnalyzeCombatObservationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = copy.deepcopy(load_json(FRESH_ACCOUNT))

    def test_reports_explicit_measurements_without_deriving_readiness(self) -> None:
        self.state["combat_readiness_observation"] = {
            "observed_at": "2026-08-22T09:30:00Z",
            "loadouts": {
                "melee": ["rune_scimitar", "rune_kiteshield"],
                "ranged": ["maple_shortbow"],
                "magic": [],
            },
            "current_hitpoints": 45,
            "current_prayer": 22,
            "food_healing_available": 60,
            "prayer_restore_points_available": 24,
            "emergency_teleport_available": True,
            "recovery_tolerance": "low",
        }
        self.state["encounter_observations"] = {
            "perilous_moons": {
                "observed_at": "2026-08-22T09:30:00Z",
                "attempts": 4,
                "successful_completions": 3,
                "elapsed_minutes": 90,
                "supply_use": {"shark": 12, "prayer_potion_4": 2},
                "deaths": 1,
                "banking_trips": 1,
            },
            "warriors_guild": {
                "observed_at": "2026-08-22T10:30:00Z",
                "attempts": 8,
                "successful_completions": None,
                "elapsed_minutes": None,
                "supply_use": {},
                "deaths": None,
                "banking_trips": None,
            },
        }
        self.state["slayer_task"] = {
            "target": "Aberrant spectres",
            "remaining": 20,
            "initial_count": 145,
            "master": "Chaeldar",
            "streak": 12,
            "points": 80,
            "blocked_targets": ["Turoth"],
            "observed_at": "2026-08-22T09:30:00Z",
        }
        self.state["unique_item_observations"] = {
            "fish_barrel": {
                "observed_at": "2026-08-22T09:30:00Z",
                "possession": "owned",
                "collection_log": "confirmed",
                "quantity": 1,
                "variant": None,
                "charges": None,
                "condition": "pristine",
                "usable": True,
                "reclaimable": None,
            },
            "dragon_defender": {
                "observed_at": "2026-08-22T09:30:00Z",
                "possession": "not_owned",
                "collection_log": "confirmed",
                "quantity": 0,
                "variant": None,
                "charges": None,
                "condition": None,
                "usable": None,
                "reclaimable": True,
            },
        }

        original_state = copy.deepcopy(self.state)
        result = analyze_combat_observations(self.state)

        self.assertEqual(2, len(result["encounters"]))
        perilous_moons = next(entry for entry in result["encounters"] if entry["encounter_id"] == "perilous_moons")
        self.assertEqual(2, perilous_moons["measured_successes_per_hour"])
        warriors_guild = next(entry for entry in result["encounters"] if entry["encounter_id"] == "warriors_guild")
        self.assertIsNone(warriors_guild["measured_successes_per_hour"])
        self.assertFalse(result["readiness_inferred"])
        self.assertFalse(result["supply_use_inferred"])
        self.assertFalse(result["collection_log_inferred"])
        self.assertEqual(original_state, self.state)

    def test_observation_fields_are_required_and_strict(self) -> None:
        del self.state["combat_readiness_observation"]
        with self.assertRaisesRegex(ValueError, "missing required keys"):
            validate_account_state(self.state)

        self.state = copy.deepcopy(load_json(FRESH_ACCOUNT))
        self.state["encounter_observations"] = {
            "perilous_moons": {
                "observed_at": "2026-08-22T09:30:00Z",
                "attempts": 2,
                "successful_completions": 3,
                "elapsed_minutes": 30,
                "supply_use": {},
                "deaths": 0,
                "banking_trips": 0,
            }
        }
        with self.assertRaisesRegex(ValueError, "cannot exceed attempts"):
            validate_account_state(self.state)

        self.state = copy.deepcopy(load_json(FRESH_ACCOUNT))
        self.state["unique_item_observations"] = {
            "fish_barrel": {
                "observed_at": "2026-08-22T09:30:00Z",
                "possession": "unknown",
                "collection_log": "unknown",
                "quantity": 1,
                "variant": None,
                "charges": None,
                "condition": None,
                "usable": None,
                "reclaimable": None,
            }
        }
        with self.assertRaisesRegex(ValueError, "unknown possession requires null quantity"):
            validate_account_state(self.state)

        self.state = copy.deepcopy(load_json(FRESH_ACCOUNT))
        self.state["slayer_task"] = {
            "target": "Aberrant spectres",
            "remaining": 20,
            "initial_count": 19,
            "master": None,
            "streak": None,
            "points": None,
            "blocked_targets": [],
            "observed_at": "2026-08-22T09:30:00Z",
        }
        with self.assertRaisesRegex(ValueError, "cannot be below remaining"):
            validate_account_state(self.state)


if __name__ == "__main__":
    unittest.main()
