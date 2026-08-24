from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_mastering_mixology import analyze_mastering_mixology  # noqa: E402
from compose_recommendation_chapter import compose_recommendation_chapter  # noqa: E402
from evaluate_progression import load_json, validate_account_state  # noqa: E402
from osrs_xp import minimum_xp_for_level  # noqa: E402


class MasteringMixologyTimingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load_json(ROOT / "tests" / "fixtures" / "fresh-account.json")

    def test_fresh_account_delays_for_hard_access_without_inference(self) -> None:
        report = analyze_mastering_mixology(self.state)

        self.assertEqual("delay_hard_access", report["timing"]["status"])
        self.assertFalse(report["inference_guarantees"]["activity_output_inferred"])
        self.assertFalse(report["inference_guarantees"]["route_timing_inferred"])

    def test_validated_observation_can_make_entry_a_candidate(self) -> None:
        state = copy.deepcopy(self.state)
        state["skills"]["Herblore"] = 81
        state["skill_xp"]["Herblore"] = minimum_xp_for_level(81)
        state["quests_completed"].append("Children of the Sun")
        state["minigame_activity_observations"] = {
            "mastering-mixology": {
                "observed_at": "2026-08-24T12:00:00Z",
                "session": {
                    "status": "not_started",
                    "mode": "reward:prescription-goggles",
                    "last_event": "potion-opportunity-cost-reviewed",
                },
                "local_supplies": {"avantoe": 100},
                "currency_balances": [
                    {"currency_id": "currency:mixology:mox-resin", "amount": 8600, "capacity": None},
                    {"currency_id": "currency:mixology:aga-resin", "amount": 7000, "capacity": None},
                    {"currency_id": "currency:mixology:lye-resin", "amount": 9350, "capacity": None},
                ],
            }
        }

        validate_account_state(state)
        report = analyze_mastering_mixology(state)

        self.assertEqual("enter_candidate", report["timing"]["status"])
        self.assertTrue(report["observation_boundary"]["globally_registered_in_shared_evaluator"])
        goggles = next(item for item in report["reward_readiness"] if item["id"] == "prescription-goggles")
        self.assertTrue(goggles["selected_objective"])
        self.assertEqual("ready", goggles["resin_readiness"])
        self.assertFalse(goggles["purchase_inferred"])

    def test_chapter_exposes_mixology_without_selecting_reward_or_inputs(self) -> None:
        chapter = compose_recommendation_chapter(
            self.state,
            load_json(ROOT / "data" / "progression" / "actions.json"),
            load_json(ROOT / "strategy" / "candidates.json"),
            load_json(ROOT / "graph" / "nodes.json"),
            load_json(ROOT / "graph" / "edges.json"),
        )

        self.assertEqual("delay_hard_access", chapter["mastering_mixology_timing"]["timing"]["status"])
        self.assertFalse(chapter["boundaries"]["mixology_inputs_inferred"])
        self.assertFalse(chapter["boundaries"]["mixology_reward_selected"])


if __name__ == "__main__":
    unittest.main()
