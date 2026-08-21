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

from analyze_passive_status import analyze_passive_status  # noqa: E402
from evaluate_progression import load_json  # noqa: E402


FRESH_ACCOUNT = REPOSITORY_ROOT / "tests" / "fixtures" / "fresh-account.json"


class AnalyzePassiveStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = copy.deepcopy(load_json(FRESH_ACCOUNT))

    def test_reports_establishment_separately_from_preserved_observations(self) -> None:
        self.state["passive_loops"]["birdhouses"] = True
        self.state["passive_loops"]["seaweed"] = True
        self.state["recurring_observations"] = {
            "birdhouses": {
                "state": "ready",
                "observed_at": "2026-08-20T12:00:00Z",
                "ready_at": "2026-08-20T12:00:00Z",
            },
            "tears_of_guthix": {
                "state": "cooldown",
                "observed_at": "2026-08-20T12:05:00-07:00",
                "ready_at": "2026-08-27T12:05:00-07:00",
            },
        }
        original_state = copy.deepcopy(self.state)

        result = analyze_passive_status(self.state)

        self.assertEqual(["birdhouses", "seaweed"], result["permanent_loop_establishment"]["established_systems"])
        self.assertEqual(self.state["recurring_observations"], result["explicit_observations"])
        self.assertEqual(["seaweed"], result["established_systems_without_observation"])
        self.assertFalse(result["elapsed_time_inferred"])
        self.assertEqual(original_state, self.state)

    def test_empty_observations_are_not_inferred(self) -> None:
        self.state["passive_loops"]["birdhouses"] = True
        self.state["recurring_observations"] = {}

        result = analyze_passive_status(self.state)

        self.assertEqual({}, result["explicit_observations"])
        self.assertEqual(["birdhouses"], result["established_systems_without_observation"])
        self.assertFalse(result["elapsed_time_inferred"])

    def test_rejects_invalid_observation_shape_state_and_timestamps(self) -> None:
        self.state["recurring_observations"] = {
            "birdhouses": {
                "state": "finished",
                "observed_at": "2026-08-20T12:00:00Z",
                "ready_at": None,
                "extra": True,
            }
        }
        with self.assertRaisesRegex(ValueError, "invalid fields"):
            analyze_passive_status(self.state)

        self.state["recurring_observations"] = {
            "birdhouses": {
                "state": "finished",
                "observed_at": "2026-08-20T12:00:00Z",
                "ready_at": None,
            }
        }
        with self.assertRaisesRegex(ValueError, "state is invalid"):
            analyze_passive_status(self.state)

        self.state["recurring_observations"]["birdhouses"]["state"] = "ready"
        self.state["recurring_observations"]["birdhouses"]["observed_at"] = "2026-08-20 12:00:00"
        with self.assertRaisesRegex(ValueError, "observed_at must be RFC 3339"):
            analyze_passive_status(self.state)

        self.state["recurring_observations"]["birdhouses"]["observed_at"] = "2026-08-20T12:00:00Z"
        self.state["recurring_observations"]["birdhouses"]["ready_at"] = "tomorrow"
        with self.assertRaisesRegex(ValueError, "ready_at must be RFC 3339 or null"):
            analyze_passive_status(self.state)

    def test_json_cli_preserves_observation_values(self) -> None:
        self.state["recurring_observations"] = {
            "seaweed": {
                "state": "in_progress",
                "observed_at": "2026-08-20T12:00:00.123Z",
                "ready_at": "2026-08-20T12:40:00.123Z",
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "passive-status-state.json"
            state_path.write_text(json.dumps(self.state), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(REPOSITORY_ROOT / "scripts" / "analyze_passive_status.py"), str(state_path), "--json"],
                check=True,
                capture_output=True,
                text=True,
            )

        result = json.loads(completed.stdout)
        self.assertEqual(self.state["recurring_observations"], result["explicit_observations"])
        self.assertFalse(result["elapsed_time_inferred"])

if __name__ == "__main__":
    unittest.main()
