from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from compose_recommendation_chapter import compose_recommendation_chapter  # noqa: E402
from evaluate_progression import load_json  # noqa: E402


ACTIONS = REPOSITORY_ROOT / "data" / "progression" / "actions.json"
CANDIDATES = REPOSITORY_ROOT / "strategy" / "candidates.json"
NODES = REPOSITORY_ROOT / "graph" / "nodes.json"
EDGES = REPOSITORY_ROOT / "graph" / "edges.json"
FIXTURES = REPOSITORY_ROOT / "tests" / "fixtures"


class ComposeRecommendationChapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actions = load_json(ACTIONS)
        self.candidates = load_json(CANDIDATES)
        self.nodes = load_json(NODES)
        self.edges = load_json(EDGES)

    def compose(self, state: dict, **kwargs: object) -> dict:
        return compose_recommendation_chapter(
            state, self.actions, self.candidates, self.nodes, self.edges, **kwargs
        )

    def test_is_deterministic_and_never_mutates_input_documents(self) -> None:
        state = load_json(FIXTURES / "passive-loops-ready.json")
        original_state = copy.deepcopy(state)
        original_actions = copy.deepcopy(self.actions)
        original_candidates = copy.deepcopy(self.candidates)

        first = self.compose(state, active_limit=3, afk_limit=2, afk_mode="true_afk")
        second = self.compose(state, active_limit=3, afk_limit=2, afk_mode="true_afk")

        self.assertEqual(first, second)
        self.assertEqual(original_state, state)
        self.assertEqual(original_actions, self.actions)
        self.assertEqual(original_candidates, self.candidates)
        self.assertFalse(first["boundaries"]["account_state_mutated"])

    def test_active_and_afk_lanes_are_bounded_and_use_explicit_scenarios(self) -> None:
        state = load_json(FIXTURES / "passive-loops-ready.json")

        chapter = self.compose(state, active_limit=2, afk_limit=2, afk_mode="true_afk")

        active = chapter["lanes"]["active"]
        afk = chapter["lanes"]["afk_or_low_attention"]
        self.assertTrue(active["scenario"])
        self.assertEqual("active", active["attention_mode"])
        self.assertEqual(2, len(active["ranked_options"]))
        self.assertTrue(afk["scenario"])
        self.assertEqual("true_afk", afk["attention_mode"])
        self.assertEqual("afk_fit > 0", afk["afk_fit_filter"])
        self.assertEqual(2, len(afk["ranked_options"]))
        self.assertTrue(
            all(option["dimension_breakdown"]["afk_fit"] > 0 for option in afk["ranked_options"])
        )
        self.assertTrue(all("stop_condition" in option for option in active["ranked_options"]))
        self.assertTrue(all("reentry_condition" in option for option in afk["ranked_options"]))

    def test_passive_check_ins_and_quest_xp_preserve_explicit_boundaries(self) -> None:
        state = load_json(FIXTURES / "passive-loops-ready.json")
        state["recurring_observations"] = {
            "birdhouses": {
                "state": "ready",
                "observed_at": "2026-08-20T12:00:00Z",
                "ready_at": "2026-08-20T12:00:00Z",
            }
        }

        chapter = self.compose(state)

        check_ins = chapter["passive_and_recurring_check_ins"]
        self.assertEqual(state["recurring_observations"], check_ins["explicit_observations"])
        self.assertFalse(check_ins["elapsed_time_inferred"])
        self.assertTrue(chapter["quest_xp_timing_opportunities"])
        self.assertTrue(
            any(item["action_id"] == "action:waterfall-quest" for item in chapter["quest_xp_timing_opportunities"])
        )

    def test_gaps_explain_unprepared_and_unscored_options_without_simulation(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")

        chapter = self.compose(state)

        preparation = {gap["action_id"]: gap for gap in chapter["gaps"]["preparation"]}
        self.assertIn("action:waterfall-quest", preparation)
        self.assertTrue(preparation["action:waterfall-quest"]["missing_preparation"])
        unscored_ids = {gap["action_id"] for gap in chapter["gaps"]["eligible_unscored"]}
        self.assertIn("action:natural-history-quiz", unscored_ids)
        self.assertEqual(
            {
                "route_selected": False,
                "action_selected": False,
                "action_completion_simulated": False,
                "elapsed_time_inferred": False,
                "random_outputs_inferred": False,
                "combat_wins_inferred": False,
                "minigame_outputs_inferred": False,
                "account_state_mutated": False,
            },
            chapter["boundaries"],
        )

    def test_cli_json_and_limit_validation(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "account.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            command = [
                sys.executable,
                str(REPOSITORY_ROOT / "scripts" / "compose_recommendation_chapter.py"),
                str(state_path),
                "--active-limit",
                "1",
                "--afk-limit",
                "1",
                "--afk-mode",
                "semi_afk",
                "--json",
            ]
            completed = subprocess.run(command, check=True, capture_output=True, text=True)
            invalid = subprocess.run(
                [
                    sys.executable,
                    str(REPOSITORY_ROOT / "scripts" / "compose_recommendation_chapter.py"),
                    str(state_path),
                    "--active-limit",
                    "0",
                ],
                capture_output=True,
                text=True,
            )

        chapter = json.loads(completed.stdout)
        self.assertEqual(1, len(chapter["lanes"]["active"]["ranked_options"]))
        self.assertEqual("semi_afk", chapter["lanes"]["afk_or_low_attention"]["attention_mode"])
        self.assertNotEqual(0, invalid.returncode)
        self.assertIn("active_limit must be a positive integer", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
