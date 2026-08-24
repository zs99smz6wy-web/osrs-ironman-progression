from __future__ import annotations

import copy
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from compose_recommendation_chapter import (  # noqa: E402
    _print_human_chapter,
    _quest_xp_opportunities,
    compose_recommendation_chapter,
)
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

        chapter = self.compose(state, quest_xp_limit=20)

        check_ins = chapter["passive_and_recurring_check_ins"]
        self.assertEqual(state["recurring_observations"], check_ins["explicit_observations"])
        self.assertFalse(check_ins["elapsed_time_inferred"])
        self.assertTrue(chapter["quest_xp_timing_opportunities"])
        self.assertTrue(
            any(item["action_id"] == "action:waterfall-quest" for item in chapter["quest_xp_timing_opportunities"])
        )
        self.assertFalse(chapter["boundaries"]["player_chosen_xp_allocated"])

    def test_quest_xp_shortlist_is_prioritized_bounded_and_deterministic(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")

        first = self.compose(state, quest_xp_limit=3)
        second = self.compose(state, quest_xp_limit=3)
        opportunities = first["quest_xp_timing_opportunities"]

        self.assertEqual(first["quest_xp_timing_opportunities"], second["quest_xp_timing_opportunities"])
        self.assertEqual(3, len(opportunities))
        self.assertTrue(all(item["status"] == "eligible" for item in opportunities))
        self.assertEqual(
            sorted(
                opportunities,
                key=lambda quest: (
                    0 if quest["status"] == "eligible" else 1,
                    -sum(skill["levels_skipped"] for skill in quest["skills"]),
                    -sum(len(skill["modeled_requirements_crossed"]) for skill in quest["skills"]),
                    quest["action_id"],
                ),
            ),
            opportunities,
        )
        coverage = first["quest_xp_timing_coverage"]
        self.assertEqual(3, coverage["limit"])
        self.assertEqual(coverage["total_count"] - 3, coverage["omitted_count"])

    def test_quest_xp_priority_uses_action_id_as_deterministic_final_tie_break(self) -> None:
        base_quest = {
            "status": "eligible",
            "skills": [{"levels_skipped": 2, "modeled_requirements_crossed": []}],
        }
        opportunities, coverage = _quest_xp_opportunities(
            {
                "quest_xp_timing_inputs": [
                    {**base_quest, "action_id": "action:zeta"},
                    {**base_quest, "action_id": "action:alpha"},
                ]
            }
        )

        self.assertEqual(["action:alpha", "action:zeta"], [item["action_id"] for item in opportunities])
        self.assertEqual(2, coverage["eligible_total"])

    def test_gaps_explain_unprepared_and_unscored_options_without_simulation(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")

        chapter = self.compose(state, preparation_limit=2)

        preparation = {gap["action_id"]: gap for gap in chapter["gaps"]["preparation"]}
        self.assertIn("action:waterfall-quest", preparation)
        self.assertEqual("needs_preparation", preparation["action:waterfall-quest"]["status"])
        self.assertTrue(preparation["action:waterfall-quest"]["missing_preparation"])
        annotated_ids = {candidate["action_id"] for candidate in self.candidates["candidates"]}
        self.assertTrue(all(action_id in annotated_ids for action_id in preparation))
        coverage = chapter["gaps"]["preparation_coverage"]
        self.assertEqual(2, coverage["limit"])
        self.assertEqual(2, coverage["shown_count"])
        self.assertGreater(coverage["omitted_count"], 0)
        self.assertGreaterEqual(
            coverage["strategically_annotated_total"], coverage["strategically_annotated_shown"]
        )
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
                "player_chosen_xp_allocated": False,
                "utility_demand_inferred": False,
                "utility_purchase_path_selected": False,
            },
            chapter["boundaries"],
        )

    def test_human_output_explains_quest_xp_preparation_and_unallocated_choice_rewards(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        chapter = self.compose(state, quest_xp_limit=20)
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            _print_human_chapter(chapter)

        text = output.getvalue()
        self.assertIn("Quest-XP timing opportunities:", text)
        self.assertIn("[NEEDS_PREPARATION] Plague City", text)
        self.assertIn("prepare: 1 x hangover_cure", text)
        self.assertIn("Mining: level 1 -> 15", text)
        self.assertIn("crossed modeled requirement levels: 10", text)
        self.assertIn("Player-chosen XP rewards remain unallocated: 1", text)
        choice_rewards = chapter["unallocated_player_chosen_xp_rewards"]
        self.assertEqual(None, choice_rewards[0]["allocated_skill"])

    def test_transport_bundle_is_bounded_and_explains_state_without_route_selection(self) -> None:
        state = load_json(FIXTURES / "fresh-account.json")
        chapter = self.compose(state, transport_bundle_limit=2)
        bundle = chapter["transport_payoff_bundles"][0]
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            _print_human_chapter(chapter)

        self.assertEqual("early-transport-network", bundle["id"])
        self.assertEqual(2, len(bundle["components"]))
        self.assertEqual(2, bundle["component_coverage"]["shown_count"])
        self.assertEqual(5, bundle["component_coverage"]["omitted_count"])
        self.assertIn("Early transport network:", output.getvalue())
        self.assertIn("[ELIGIBLE] Spirit trees", output.getvalue())
        self.assertFalse(chapter["boundaries"]["route_selected"])

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
                "--preparation-limit",
                "1",
                "--quest-xp-limit",
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
            invalid_preparation = subprocess.run(
                [
                    sys.executable,
                    str(REPOSITORY_ROOT / "scripts" / "compose_recommendation_chapter.py"),
                    str(state_path),
                    "--preparation-limit",
                    "0",
                ],
                capture_output=True,
                text=True,
            )
            invalid_quest_xp = subprocess.run(
                [
                    sys.executable,
                    str(REPOSITORY_ROOT / "scripts" / "compose_recommendation_chapter.py"),
                    str(state_path),
                    "--quest-xp-limit",
                    "0",
                ],
                capture_output=True,
                text=True,
            )
            invalid_transport = subprocess.run(
                [
                    sys.executable,
                    str(REPOSITORY_ROOT / "scripts" / "compose_recommendation_chapter.py"),
                    str(state_path),
                    "--transport-bundle-limit",
                    "0",
                ],
                capture_output=True,
                text=True,
            )

        chapter = json.loads(completed.stdout)
        self.assertEqual(1, len(chapter["lanes"]["active"]["ranked_options"]))
        self.assertEqual(1, len(chapter["gaps"]["preparation"]))
        self.assertEqual(1, len(chapter["quest_xp_timing_opportunities"]))
        self.assertEqual("semi_afk", chapter["lanes"]["afk_or_low_attention"]["attention_mode"])
        self.assertNotEqual(0, invalid.returncode)
        self.assertIn("active_limit must be a positive integer", invalid.stderr)
        self.assertIn("preparation_limit must be a positive integer", invalid_preparation.stderr)
        self.assertIn("quest_xp_limit must be a positive integer", invalid_quest_xp.stderr)
        self.assertIn("transport_bundle_limit must be a positive integer", invalid_transport.stderr)


if __name__ == "__main__":
    unittest.main()
