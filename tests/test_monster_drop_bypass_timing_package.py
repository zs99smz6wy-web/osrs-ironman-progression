from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_monster_drop_bypass_timing import analyze_monster_drop_bypass_timing  # noqa: E402
from evaluate_progression import load_json, validate_account_state  # noqa: E402


class MonsterDropBypassTimingPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load_json(ROOT / "tests" / "fixtures" / "fresh-account.json")
        self.actions = load_json(ROOT / "data" / "progression" / "actions.json")
        self.contexts = load_json(ROOT / "strategy" / "monster-drop-bypass-timing-contexts.json")
        self.research = load_json(ROOT / "research" / "monster-drop-bypass-timing.json")
        self.readiness = load_json(ROOT / "data" / "facts" / "drop-bypass-readiness.json")

    def _report(self, state: dict, objectives: dict[str, str] | None = None) -> dict:
        return analyze_monster_drop_bypass_timing(
            state, self.actions, self.contexts, self.research, self.readiness, objectives
        )

    @staticmethod
    def _entry(report: dict, bypass_id: str) -> dict:
        return next(item for item in report["bypasses"] if item["bypass_id"] == bypass_id)

    @staticmethod
    def _record_tree_spirit_context(state: dict) -> None:
        state["milestones"] = ["fairytale_ii_fairy_godfather_permission", "woodcutting_axe_available"]
        state["items"] = {"dramen_staff": 1}
        state["combat_readiness_observation"] = {
            "observed_at": "2026-08-25T12:00:00Z",
            "loadouts": {"melee": ["bronze_sword"], "ranged": [], "magic": ["fire_strike"]},
            "current_hitpoints": 10,
            "current_prayer": 1,
            "food_healing_available": 0,
            "prayer_restore_points_available": 0,
            "emergency_teleport_available": False,
            "recovery_tolerance": "low",
        }
        state["encounter_observations"] = {
            "tree-spirit": {
                "observed_at": "2026-08-25T12:10:00Z",
                "attempts": 1,
                "successful_completions": 1,
                "elapsed_minutes": 4,
                "supply_use": {"shrimp": 1},
                "deaths": 0,
                "banking_trips": 0,
            }
        }

    def test_default_report_never_selects_rare_drops(self) -> None:
        original = copy.deepcopy(self.state)
        report = self._report(self.state)
        rune_axe = self._entry(report, "tree-spirit-rune-axe")

        self.assertEqual(original, self.state)
        self.assertEqual("formal_access_incomplete", rune_axe["timing_status"])
        self.assertEqual("unselected", rune_axe["explicit_objective"]["status"])
        self.assertFalse(rune_axe["recommended_by_default"])
        self.assertTrue(all(not value for value in report["inference_guarantees"].values()))

    def test_explicit_objective_and_observations_only_make_a_bounded_candidate(self) -> None:
        state = copy.deepcopy(self.state)
        self._record_tree_spirit_context(state)
        validate_account_state(state)

        report = self._report(state, {"tree-spirit-rune-axe": "avoid the modeled guild purchase"})
        rune_axe = self._entry(report, "tree-spirit-rune-axe")

        self.assertEqual("eligible", rune_axe["factual_access"]["status"])
        self.assertEqual("bounded_rng_bypass_candidate", rune_axe["timing_status"])
        self.assertEqual("recorded", rune_axe["explicit_objective"]["status"])
        self.assertEqual("modeled", rune_axe["normal_path"]["status"])
        probability = rune_axe["selected_rng_bypass"]["drop_probability_context"]
        self.assertEqual("4/128 (1/32)", probability["rate_description"])
        self.assertNotIn("expected_kills", probability)
        self.assertFalse(probability["drop_inferred"])
        self.assertFalse(rune_axe["throughput_or_completion_time_inferred"])
        self.assertFalse(rune_axe["route_order_selected"])

    def test_observed_target_or_intermediate_item_stops_collection_status(self) -> None:
        state = copy.deepcopy(self.state)
        state["items"] = {"rune_axe": 1, "broken_zombie_axe": 1}
        report = self._report(state, {
            "tree-spirit-rune-axe": "content variety",
            "armoured-zombie-zombie-axe": "weapon upgrade",
        })

        rune_axe = self._entry(report, "tree-spirit-rune-axe")
        zombie_axe = self._entry(report, "armoured-zombie-zombie-axe")
        self.assertEqual("target_item_already_owned", rune_axe["timing_status"])
        self.assertTrue(rune_axe["item_observation"]["current_target_item_owned"])
        self.assertEqual("intermediate_drop_observed", zombie_axe["timing_status"])
        self.assertEqual(["broken_zombie_axe"], zombie_axe["item_observation"]["observed_intermediate_item_keys"])

    def test_unknown_deterministic_alternative_remains_unknown(self) -> None:
        report = self._report(self.state, {"armoured-zombie-zombie-axe": "weapon upgrade"})
        zombie_axe = self._entry(report, "armoured-zombie-zombie-axe")

        self.assertEqual("not_modeled", zombie_axe["normal_path"]["status"])
        self.assertIn("No deterministic alternative", zombie_axe["normal_path"]["description"])
        self.assertFalse(zombie_axe["selected_rng_bypass"]["drop_probability_context"]["expected_kills_calculated"])


if __name__ == "__main__":
    unittest.main()
