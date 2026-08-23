from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from analyze_activity_observations import analyze_activity_observations  # noqa: E402
from evaluate_progression import load_json, validate_account_state  # noqa: E402


FRESH_ACCOUNT = REPOSITORY_ROOT / "tests" / "fixtures" / "fresh-account.json"


class AnalyzeActivityObservationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = copy.deepcopy(load_json(FRESH_ACCOUNT))
        self.state["sailing_observation"] = {
            "observed_at": "2026-08-22T11:00:00Z",
            "vessel": {
                "boat_type": "skiff",
                "component_tiers": {"hull": 2, "sail": None},
                "facilities": ["salvaging_station"],
                "hull_hitpoints": 32,
                "hull_max_hitpoints": 40,
                "cargo_hold": {"salvage": 3, "port_task_cargo": 8},
                "last_gangplank": "Port Sarim",
                "last_mooring_point": None,
            },
            "recovery": {"last_event": "quick_transport", "cargo_loss_observed": True},
            "tasks": [
                {
                    "task_id": "courier-2026-08-22-1",
                    "kind": "courier",
                    "origin": "Port Sarim",
                    "destination": "Land's End",
                    "cargo_item": "trade_goods",
                    "cargo_quantity": 8,
                    "bounty_target": None,
                    "bounty_item_count": None,
                    "slots_used": 1,
                    "status": "accepted",
                    "cargo_loaded": True,
                    "observed_at": "2026-08-22T11:00:00Z",
                }
            ],
        }
        self.state["perilous_moons_observation"] = {
            "observed_at": "2026-08-22T12:00:00Z",
            "run": {
                "run_id": "moons-2026-08-22-1",
                "bosses_defeated": ["blue_moon", "eclipse_moon"],
                "defeat_order": ["eclipse_moon", "blue_moon"],
                "campsite_location": "central camp",
                "lunar_chest_opened": False,
                "inside_neyzpotli": True,
            },
            "internal_supplies": {
                "raw_bream": 2,
                "cooked_bream": 5,
                "moss_lizard": None,
                "moonlight_grub_paste": 1,
                "moonlight_potion": 2,
                "moth": 0,
            },
            "death_recovery": {
                "last_death_observed_at": "2026-08-22T11:50:00Z",
                "grave_location": "antechamber",
                "grave_active_minutes_remaining": 12,
                "reclaim_status": "in_grave",
            },
        }
        self.state["farming_recurrence_observation"] = {
            "observed_at": "2026-08-22T13:00:00Z",
            "patches": [
                {
                    "patch_id": "hosidius-herb",
                    "patch_type": "herb",
                    "seed_id": "ranarr_seed",
                    "planted_at": "2026-08-22T12:20:00Z",
                    "growth_class": "herb",
                    "growth_ticks_observed": 2,
                    "disease_state": "disease_free",
                    "harvest_lives_remaining": None,
                    "compost_id": "ultracompost",
                    "protection_state": "unprotected",
                    "ready_observed": False,
                    "observed_at": "2026-08-22T13:00:00Z",
                }
            ],
            "hespori": {
                "seed_present": False,
                "planted_at": "2026-08-21T10:00:00Z",
                "state": "growing",
                "last_defeat_at": None,
                "last_harvest_at": None,
                "ready_observed": False,
            },
            "anima_patch": {
                "seed_id": "iasor_seed",
                "planted_at": "2026-08-20T10:00:00Z",
                "state": "active",
                "active_effect": "iasor",
                "ready_observed": None,
            },
        }
        self.state["unique_item_observations"] = {
            "blue_moon_helm": self._unique_item("owned", "confirmed", 1),
            "blue_moon_spear": self._unique_item("not_owned", "confirmed", 0),
            "fish_barrel": self._unique_item("owned", "confirmed", 1),
        }

    @staticmethod
    def _unique_item(possession: str, collection_log: str, quantity: int) -> dict:
        return {
            "observed_at": "2026-08-22T12:00:00Z",
            "possession": possession,
            "collection_log": collection_log,
            "quantity": quantity,
            "variant": None,
            "charges": None,
            "condition": None,
            "usable": None,
            "reclaimable": None,
        }

    def test_reports_only_recorded_state_without_mutation_or_inference(self) -> None:
        original = copy.deepcopy(self.state)
        result = analyze_activity_observations(self.state)

        self.assertEqual(self.state["sailing_observation"], result["sailing_observation"])
        self.assertEqual(self.state["perilous_moons_observation"], result["perilous_moons_observation"])
        self.assertEqual(self.state["farming_recurrence_observation"], result["farming_recurrence_observation"])
        self.assertEqual(
            {"blue_moon_helm", "blue_moon_spear"},
            set(result["moon_equipment_observations"]["blue_moon"]),
        )
        self.assertNotIn("fish_barrel", result["moon_equipment_observations"]["blue_moon"])
        for flag in (
            "clocks_advanced",
            "growth_inferred",
            "readiness_inferred",
            "loot_created",
            "reclaim_fee_calculated",
            "set_completion_inferred",
            "throughput_inferred",
        ):
            self.assertFalse(result[flag])
        self.assertEqual(original, self.state)

    def test_required_observations_remain_nullable_and_strict(self) -> None:
        validate_account_state(self.state)

        for field in ("sailing_observation", "perilous_moons_observation", "farming_recurrence_observation"):
            nullable = copy.deepcopy(self.state)
            nullable[field] = None
            validate_account_state(nullable)

            missing = copy.deepcopy(self.state)
            del missing[field]
            with self.assertRaisesRegex(ValueError, "missing required keys"):
                validate_account_state(missing)

    def test_sailing_rejects_contradictory_or_duplicate_observations(self) -> None:
        state = copy.deepcopy(self.state)
        state["sailing_observation"]["vessel"]["hull_hitpoints"] = 41
        with self.assertRaisesRegex(ValueError, "cannot exceed hull_max_hitpoints"):
            validate_account_state(state)

        state = copy.deepcopy(self.state)
        state["sailing_observation"]["tasks"].append(copy.deepcopy(state["sailing_observation"]["tasks"][0]))
        with self.assertRaisesRegex(ValueError, "unique task IDs"):
            validate_account_state(state)

    def test_moons_rejects_unrecorded_defeat_order_and_duplicate_ids(self) -> None:
        state = copy.deepcopy(self.state)
        state["perilous_moons_observation"]["run"]["defeat_order"].append("blood_moon")
        with self.assertRaisesRegex(ValueError, "subset of bosses_defeated"):
            validate_account_state(state)

        state = copy.deepcopy(self.state)
        state["perilous_moons_observation"]["run"]["bosses_defeated"].append("blue_moon")
        with self.assertRaisesRegex(ValueError, "unique trimmed strings"):
            validate_account_state(state)

    def test_farming_rejects_duplicate_patches_and_non_timestamped_observations(self) -> None:
        state = copy.deepcopy(self.state)
        state["farming_recurrence_observation"]["patches"].append(
            copy.deepcopy(state["farming_recurrence_observation"]["patches"][0])
        )
        with self.assertRaisesRegex(ValueError, "unique patch IDs"):
            validate_account_state(state)

        state = copy.deepcopy(self.state)
        state["farming_recurrence_observation"]["hespori"]["planted_at"] = "yesterday"
        with self.assertRaisesRegex(ValueError, "must be RFC 3339 or null"):
            validate_account_state(state)

    def test_diary_task_observations_are_reported_without_progress_inference(self) -> None:
        self.state["diary_task_observations"] = {
            "diary-task:wilderness:wilderness-elite-kill-big-three": {
                "observed_at": "2026-08-22T14:00:00Z",
                "status": "in_progress",
                "mode": "staged",
                "completion_confirmed": False,
                "stage_ids": ["callisto_or_artio", "venenatis_or_spindel", "vetion_or_calvarion"],
                "completed_stage_ids": ["callisto_or_artio"],
                "invalidated_by_diary_update": False,
                "reset_observed_at": None,
            }
        }
        original = copy.deepcopy(self.state)

        result = analyze_activity_observations(self.state)

        self.assertEqual(
            self.state["diary_task_observations"],
            result["diary_task_observation_report"]["observations"],
        )
        self.assertFalse(result["diary_task_observation_report"]["milestones_inferred"])
        self.assertFalse(result["diary_task_observation_report"]["diary_tiers_inferred"])
        self.assertFalse(result["wilderness_elite_big_three_durable_boss_kills_inferred"])
        self.assertEqual(original, self.state)


if __name__ == "__main__":
    unittest.main()
