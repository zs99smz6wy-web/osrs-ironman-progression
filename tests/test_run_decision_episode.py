from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_progression import DEFAULT_ACTIONS, load_json  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402
from run_decision_episode import MAX_EPISODE_STEPS, run_decision_episode  # noqa: E402
from score_candidates import DEFAULT_CANDIDATES  # noqa: E402
from analyze_quest_xp_timing import DEFAULT_EDGES, DEFAULT_NODES  # noqa: E402


FRESH_ACCOUNT = ROOT / "tests" / "fixtures" / "fresh-account.json"
RUNNER = ROOT / "scripts" / "run_decision_episode.py"


class RunDecisionEpisodeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load_json(FRESH_ACCOUNT)
        self.actions = load_json(DEFAULT_ACTIONS)
        self.candidates = load_json(DEFAULT_CANDIDATES)
        self.nodes = load_json(DEFAULT_NODES)
        self.edges = load_json(DEFAULT_EDGES)

    def run_episode(self, steps: list[dict]) -> dict:
        return run_decision_episode(
            self.state,
            steps,
            self.actions,
            self.candidates,
            self.nodes,
            self.edges,
        )

    def test_applies_only_confirmed_steps_in_order_and_preserves_inputs(self) -> None:
        original_state = copy.deepcopy(self.state)
        original_actions = copy.deepcopy(self.actions)
        report = self.run_episode(
            [
                {"action_id": "action:tree-gnome-village", "completion_confirmed": True},
                {"action_id": "action:natural-history-quiz", "completion_confirmed": True},
            ]
        )

        self.assertEqual("all_confirmed_steps_applied", report["episode_status"])
        self.assertEqual(2, report["recorded_step_count"])
        self.assertTrue(all(step["status"] == "applied_confirmed_completion" for step in report["steps"]))
        self.assertIn("Tree Gnome Village", report["final_account_state"]["quests_completed"])
        self.assertEqual(28, report["final_account_state"]["counters"]["kudos"])
        self.assertTrue(all("recommendation_chapter_before_selection" in step for step in report["steps"]))
        self.assertTrue(all(step["application"]["guaranteed_effects_recorded"] for step in report["steps"]))
        self.assertEqual(original_state, self.state)
        self.assertEqual(original_actions, self.actions)
        self.assertFalse(report["boundaries"]["action_auto_selected"])
        self.assertFalse(report["boundaries"]["completion_inferred"])

    def test_missing_or_false_confirmation_halts_without_applying_the_plan(self) -> None:
        for step in (
            {"action_id": "action:tree-gnome-village"},
            {"action_id": "action:tree-gnome-village", "completion_confirmed": False},
        ):
            with self.subTest(step=step):
                report = self.run_episode([step])
                recorded = report["steps"][0]

                self.assertEqual("halted_completion_unconfirmed", report["episode_status"])
                self.assertEqual("not_applied_completion_unconfirmed", recorded["status"])
                self.assertEqual("eligible", recorded["eligibility_before_selection"]["status"])
                self.assertNotIn("application", recorded)
                self.assertEqual(self.state, report["final_account_state"])
                self.assertFalse(report["boundaries"]["planned_or_unconfirmed_action_applied"])

    def test_ineligible_action_is_reported_without_applying_it(self) -> None:
        report = self.run_episode(
            [{"action_id": "action:waterfall-quest", "completion_confirmed": True}]
        )

        recorded = report["steps"][0]
        self.assertEqual("halted_not_eligible", report["episode_status"])
        self.assertEqual("not_applied_not_eligible", recorded["status"])
        self.assertEqual("needs_preparation", recorded["eligibility_before_selection"]["status"])
        self.assertEqual(self.state, report["final_account_state"])

    def test_option_choice_is_passed_explicitly_to_canonical_apply_action(self) -> None:
        for skill, level in (("Agility", 10), ("Herblore", 10), ("Thieving", 25)):
            self.state["skill_xp"][skill] = minimum_xp_for_level(level)
            self.state["skills"][skill] = level
        self.state["items"].update(
            {
                "vial": 1,
                "pestle_and_mortar": 1,
                "tinderbox": 1,
                "cup_of_tea": 1,
                "rope": 2,
                "opal": 1,
                "uncut_opal": 1,
                "charcoal": 1,
            }
        )

        without_option = self.run_episode(
            [{"action_id": "action:the-dig-site", "completion_confirmed": True}]
        )
        self.assertEqual("halted_apply_action_choice_required", without_option["episode_status"])
        self.assertEqual(
            "not_applied_apply_action_choice_required", without_option["steps"][0]["status"]
        )
        self.assertEqual(self.state, without_option["final_account_state"])

        report = self.run_episode(
            [
                {
                    "action_id": "action:the-dig-site",
                    "completion_confirmed": True,
                    "option_id": "uncut-opal",
                }
            ]
        )

        step = report["steps"][0]
        self.assertEqual("applied_confirmed_completion", step["status"])
        self.assertEqual("uncut-opal", step["application"]["selected_option_id"])
        self.assertEqual(0, report["final_account_state"]["items"]["uncut_opal"])
        self.assertEqual(1, report["final_account_state"]["items"]["opal"])

    def test_episode_is_bounded(self) -> None:
        steps = [
            {"action_id": "action:tree-gnome-village", "completion_confirmed": True}
            for _ in range(MAX_EPISODE_STEPS + 1)
        ]

        with self.assertRaisesRegex(ValueError, "at most"):
            self.run_episode(steps)

    def test_cli_emits_report_without_mutating_input_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "account-state.json"
            selections_path = Path(directory) / "episode.json"
            state_path.write_text(json.dumps(self.state), encoding="utf-8")
            selections_path.write_text(
                json.dumps([{"action_id": "action:tree-gnome-village", "completion_confirmed": True}]),
                encoding="utf-8",
            )
            original_state = state_path.read_text(encoding="utf-8")
            original_selections = selections_path.read_text(encoding="utf-8")

            completed = subprocess.run(
                [sys.executable, str(RUNNER), str(state_path), str(selections_path)],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(original_state, state_path.read_text(encoding="utf-8"))
            self.assertEqual(original_selections, selections_path.read_text(encoding="utf-8"))

        report = json.loads(completed.stdout)
        self.assertEqual("all_confirmed_steps_applied", report["episode_status"])
        self.assertIn("Tree Gnome Village", report["final_account_state"]["quests_completed"])


if __name__ == "__main__":
    unittest.main()
