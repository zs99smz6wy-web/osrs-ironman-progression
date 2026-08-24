from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCATION_PATH = ROOT / "data" / "facts" / "minigame-location-state.json"
RNG_PATH = ROOT / "data" / "facts" / "minigame-rng-boundaries.json"


class MinigameW4FactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.location = json.loads(LOCATION_PATH.read_text(encoding="utf-8"))
        cls.rng = json.loads(RNG_PATH.read_text(encoding="utf-8"))

    def test_location_records_are_unique_and_observation_bounded(self) -> None:
        records = self.location["records"]
        self.assertEqual(7, len(records))
        self.assertEqual(len(records), len({record["id"] for record in records}))
        rendered = json.dumps(records).lower()
        self.assertIn("observ", rendered)
        self.assertNotIn('"guaranteed_output"', rendered)

    def test_rng_records_never_claim_deterministic_random_outputs(self) -> None:
        records = self.rng["records"]
        self.assertEqual(6, len(records))
        self.assertEqual(len(records), len({record["id"] for record in records}))
        for record in records:
            self.assertIn(record["acquisition"], {"rng", "mixed"})
            rendered = json.dumps(record).lower()
            self.assertTrue("boundary" in rendered or "protection" in rendered)
            self.assertNotIn('"guaranteed": true', rendered)

    def test_current_corrections_are_preserved(self) -> None:
        locations = {record["id"]: record for record in self.location["records"]}
        rng = {record["id"]: record for record in self.rng["records"]}
        trawler_state = locations["fishing-trawler-session-and-diary-state"]["live_state"]
        self.assertIn("0 to 255", trawler_state)
        self.assertIn("at least 50", trawler_state)
        self.assertEqual(100, rng["pyramid-plunder-sceptre-rng-boundary"]["charge_capacities"]["elite"])
        self.assertEqual("1/12 per eligible successful trip", rng["fishing-trawler-reward-rng-boundary"]["angler_missing_piece_rate"])


if __name__ == "__main__":
    unittest.main()
