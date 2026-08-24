from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_void_elite_void_timing import analyze_void_elite_void_timing  # noqa: E402
from evaluate_progression import load_json, validate_account_state  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402


class VoidEliteVoidTimingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load_json(ROOT / "tests" / "fixtures" / "fresh-account.json")

    @staticmethod
    def _purchase_skill_state(state: dict) -> None:
        for skill in ("Attack", "Strength", "Defence", "Hitpoints", "Ranged", "Magic"):
            state["skills"][skill] = 42
            state["skill_xp"][skill] = minimum_xp_for_level(42)
        state["skills"]["Prayer"] = 22
        state["skill_xp"]["Prayer"] = minimum_xp_for_level(22)

    @staticmethod
    def _set_level(state: dict, skill: str, level: int) -> None:
        state["skills"][skill] = level
        state["skill_xp"][skill] = minimum_xp_for_level(level)

    def test_lower_boat_regular_void_access_is_not_blocked_by_combat_100(self) -> None:
        state = copy.deepcopy(self.state)
        self._purchase_skill_state(state)
        report = analyze_void_elite_void_timing(
            state, {"objective": "regular_void_one_helmet", "veteran_wait": "none"}
        )

        self.assertTrue(report["regular_void_access"]["purchase_skill_requirements_met"])
        self.assertLess(report["regular_void_access"]["combat_level_observed"], 100)
        self.assertEqual("novice", report["regular_void_access"]["highest_eligible_lander"]["id"])
        self.assertTrue(report["regular_void_access"]["regular_void_available_before_combat_100"])
        self.assertFalse(report["regular_void_access"]["combat_100_is_regular_void_requirement"])
        self.assertEqual("regular_void_enter_candidate", report["timing"]["status"])

    def test_veteran_wait_is_a_strategy_consideration_not_a_regular_void_gate(self) -> None:
        state = copy.deepcopy(self.state)
        self._purchase_skill_state(state)
        report = analyze_void_elite_void_timing(
            state, {"objective": "elite_void_one_helmet", "veteran_wait": "prefer"}
        )

        self.assertEqual("wait_veteran_rate_consideration", report["timing"]["status"])
        self.assertTrue(report["regular_void_access"]["regular_void_available_before_combat_100"])
        self.assertFalse(report["timing"]["route_selected"])

    def test_hard_diary_regular_pieces_and_observed_points_make_upgrade_a_candidate(self) -> None:
        state = copy.deepcopy(self.state)
        for skill in ("Attack", "Strength", "Defence", "Hitpoints", "Ranged", "Magic"):
            self._set_level(state, skill, 85)
        self._set_level(state, "Prayer", 70)
        state["items"] = {
            "void_knight_top": 1,
            "void_knight_robe": 1,
            "void_knight_gloves": 1,
            "void_ranger_helm": 1,
        }
        state["diary_tiers"]["Western Provinces"] = "hard"
        state["minigame_activity_observations"] = {
            "pest-control": {
                "observed_at": "2026-08-24T12:00:00Z",
                "currency_balances": [
                    {"currency_id": "currency:pest-control:commendation-points", "amount": 400, "capacity": 4000}
                ],
                "session": {"status": "ended"},
            }
        }
        validate_account_state(state)
        report = analyze_void_elite_void_timing(state, {"objective": "elite_void_one_helmet"})

        self.assertEqual("veteran", report["regular_void_access"]["highest_eligible_lander"]["id"])
        self.assertEqual("elite_void_upgrade_candidate", report["timing"]["status"])
        self.assertTrue(report["elite_void_upgrade"]["both_upgrades_candidate"])
        self.assertEqual("stopped_or_reentry_candidate_observed", report["stop_reentry"]["session_context"])
        self.assertFalse(report["elite_void_upgrade"]["upgrade_inferred"])

    def test_analysis_is_non_mutating_and_never_infers_pest_control_outcomes(self) -> None:
        state = copy.deepcopy(self.state)
        original = copy.deepcopy(state)
        report = analyze_void_elite_void_timing(state)

        self.assertEqual(original, state)
        for field in ("team_inferred", "round_outcome_inferred", "points_earned_inferred", "purchase_inferred", "upgrade_inferred"):
            self.assertFalse(report["inference_guarantees"][field])

    def test_owned_elite_pieces_satisfy_corresponding_regular_set_slots(self) -> None:
        state = copy.deepcopy(self.state)
        self._purchase_skill_state(state)
        state["items"] = {
            "elite_void_top": 1,
            "elite_void_robe": 1,
            "void_knight_gloves": 1,
            "void_mage_helm": 1,
        }
        state["diary_tiers"]["Western Provinces"] = "hard"

        report = analyze_void_elite_void_timing(
            state, {"objective": "elite_void_one_helmet", "veteran_wait": "none"}
        )

        self.assertTrue(report["regular_void_set"]["complete_one_helmet_set_observed"])
        self.assertTrue(report["elite_void_upgrade"]["complete_one_helmet_elite_set_observed"])
        self.assertEqual(0, report["elite_void_upgrade"]["remaining_upgrade_point_cost"])
        self.assertEqual("elite_void_objective_observed", report["timing"]["status"])


if __name__ == "__main__":
    unittest.main()
