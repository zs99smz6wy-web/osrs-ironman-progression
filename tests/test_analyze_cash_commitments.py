from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from analyze_cash_commitments import analyze_cash_commitments  # noqa: E402
from evaluate_progression import load_json  # noqa: E402


FRESH_ACCOUNT = REPOSITORY_ROOT / "tests" / "fixtures" / "fresh-account.json"


class AnalyzeCashCommitmentsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = copy.deepcopy(load_json(FRESH_ACCOUNT))

    def test_orders_deadlines_and_reports_cumulative_shortfalls(self) -> None:
        self.state["resources"]["coins"] = 12000
        self.state["cash_commitments"] = [
            {"purpose": "Kingdom reserve", "coins": 750000, "deadline": "near_term"},
            {"purpose": "Sailing skiff", "coins": 15000, "deadline": "next_goal"},
            {"purpose": "Quest item", "coins": 5000, "deadline": "now"},
        ]

        result = analyze_cash_commitments(self.state)

        self.assertEqual(["Quest item", "Sailing skiff", "Kingdom reserve"], [item["purpose"] for item in result["ordered_commitments"]])
        self.assertEqual([0, 8000, 758000], [item["cumulative_shortfall"] for item in result["ordered_commitments"]])
        self.assertEqual(770000, result["committed_coins"])
        self.assertEqual(758000, result["total_shortfall"])
        self.assertFalse(result["method_selected"])

    def test_empty_commitments_do_not_invent_a_cash_target(self) -> None:
        self.state["resources"]["coins"] = 25000

        result = analyze_cash_commitments(self.state)

        self.assertEqual(0, result["committed_coins"])
        self.assertEqual(0, result["total_shortfall"])
        self.assertEqual([], result["ordered_commitments"])


if __name__ == "__main__":
    unittest.main()
