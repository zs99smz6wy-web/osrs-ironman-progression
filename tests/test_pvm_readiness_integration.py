from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_pvm_readiness import DEFAULT_CONTEXTS, analyze_pvm_readiness, context_by_action  # noqa: E402
from evaluate_progression import load_json  # noqa: E402


class PvmReadinessIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load_json(ROOT / "tests" / "fixtures" / "fresh-account.json")
        self.actions = load_json(ROOT / "data" / "progression" / "actions.json")
        self.contexts = load_json(DEFAULT_CONTEXTS)

    def test_core_activities_report_access_and_observation_gaps(self) -> None:
        report = analyze_pvm_readiness(self.contexts, self.actions, self.state)

        self.assertEqual(
            {"royal-titans", "barrows", "perilous-moons", "corrupted-gauntlet"},
            {item["activity_id"] for item in report},
        )
        self.assertTrue(all(item["observation_gaps"] for item in report))
        self.assertTrue(all(not item["combat_win_inferred"] for item in report))
        self.assertTrue(all(not item["loot_inferred"] for item in report))

    def test_context_is_attached_to_each_linked_action_without_score_claim(self) -> None:
        report = analyze_pvm_readiness(self.contexts, self.actions, self.state)
        by_action = context_by_action(report, self.contexts)

        self.assertEqual("royal-titans", by_action["action:royal-titans"]["activity_id"])
        self.assertEqual("perilous-moons", by_action["action:moons-of-peril"]["activity_id"])
        self.assertFalse(by_action["action:corrupted-gauntlet"]["route_order_selected"])


if __name__ == "__main__":
    unittest.main()
