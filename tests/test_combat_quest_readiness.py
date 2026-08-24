from __future__ import annotations

import contextlib
import copy
import io
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from compose_recommendation_chapter import _print_human_chapter, compose_recommendation_chapter  # noqa: E402
from evaluate_progression import evaluate_actions, load_json  # noqa: E402
from score_candidates import score_candidates  # noqa: E402


FIXTURE = REPOSITORY_ROOT / "tests" / "fixtures" / "new-ironman-post-tutorial.json"
ACTIONS = REPOSITORY_ROOT / "data" / "progression" / "actions.json"
CANDIDATES = REPOSITORY_ROOT / "strategy" / "candidates.json"
NODES = REPOSITORY_ROOT / "graph" / "nodes.json"
EDGES = REPOSITORY_ROOT / "graph" / "edges.json"


class CombatQuestReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load_json(FIXTURE)
        self.actions = load_json(ACTIONS)
        self.candidates = load_json(CANDIDATES)

    def _candidate(self, state: dict) -> dict:
        ranked = score_candidates(self.candidates, self.actions, state)
        return next(item for item in ranked if item["action_id"] == "action:tree-gnome-village")

    def test_post_tutorial_account_remains_formally_eligible_but_needs_readiness(self) -> None:
        evaluated = {item["id"]: item for item in evaluate_actions(self.actions, self.state)}
        candidate = self._candidate(self.state)
        context = candidate["practical_readiness_context"]

        self.assertEqual("eligible", evaluated["action:tree-gnome-village"]["status"])
        self.assertEqual("eligible", candidate["formal_eligibility"])
        self.assertEqual("needs_practical_readiness", context["status"])
        self.assertTrue(context["formal_eligibility_preserved"])
        self.assertIn("safespot", context["tactical_options_note"])
        self.assertFalse(context["combat_snapshot_recorded"])
        self.assertFalse(context["combat_win_inferred"])
        self.assertFalse(context["supplies_inferred"])
        self.assertFalse(context["player_competence_inferred"])

    def test_recorded_snapshot_keeps_tactic_and_outcome_unconfirmed(self) -> None:
        prepared = copy.deepcopy(self.state)
        prepared["combat_readiness_observation"] = {
            "observed_at": "2026-08-24T12:00:00Z",
            "loadouts": {"melee": [], "ranged": [], "magic": []},
            "current_hitpoints": 10,
            "current_prayer": 1,
            "food_healing_available": None,
            "prayer_restore_points_available": None,
            "emergency_teleport_available": None,
            "recovery_tolerance": "low",
        }

        candidate = self._candidate(prepared)
        context = candidate["practical_readiness_context"]

        self.assertEqual("eligible", candidate["formal_eligibility"])
        self.assertEqual("needs_tactical_confirmation", context["status"])
        self.assertTrue(context["combat_snapshot_recorded"])
        self.assertFalse(context["encounter_success_recorded"])
        self.assertFalse(context["combat_win_inferred"])
        self.assertFalse(context["supplies_inferred"])
        self.assertFalse(context["player_competence_inferred"])

    def test_explicit_encounter_success_is_context_not_generated_completion(self) -> None:
        observed = copy.deepcopy(self.state)
        observed["encounter_observations"] = {
            "tree-gnome-village-khazard-warlord": {
                "observed_at": "2026-08-24T12:00:00Z",
                "attempts": 1,
                "successful_completions": 1,
                "elapsed_minutes": None,
                "supply_use": {},
                "deaths": 0,
                "banking_trips": 0,
            }
        }
        candidate = self._candidate(observed)
        chapter = compose_recommendation_chapter(
            observed, self.actions, self.candidates, load_json(NODES), load_json(EDGES)
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            _print_human_chapter(chapter)

        self.assertEqual("timely_after_observed_encounter", candidate["practical_readiness_context"]["status"])
        self.assertTrue(candidate["practical_readiness_context"]["encounter_success_recorded"])
        self.assertFalse(candidate["practical_readiness_context"]["combat_win_inferred"])
        self.assertEqual([], observed["quests_completed"])
        self.assertIn("formal eligibility: eligible", output.getvalue())
        self.assertIn("practical context: timely_after_observed_encounter", output.getvalue())


if __name__ == "__main__":
    unittest.main()
