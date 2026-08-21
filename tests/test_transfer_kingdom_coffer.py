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

from evaluate_progression import load_json  # noqa: E402
from transfer_kingdom_coffer import (  # noqa: E402
    BASE_COFFER_CAP,
    ROYAL_TROUBLE_COFFER_CAP,
    kingdom_coffer_cap,
    transfer_kingdom_coffer,
)


FRESH_ACCOUNT = REPOSITORY_ROOT / "tests" / "fixtures" / "fresh-account.json"


class TransferKingdomCofferTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = copy.deepcopy(load_json(FRESH_ACCOUNT))
        self.state["passive_loops"]["kingdom"] = True
        self.state["resources"].update({"coins": 1_000_000, "kingdom_coffer_coins": 10_000})

    def test_deposit_returns_a_new_state_and_preserves_input(self) -> None:
        original_state = copy.deepcopy(self.state)

        next_state = transfer_kingdom_coffer(self.state, "deposit", 250_000)

        self.assertIsNot(next_state, self.state)
        self.assertEqual(750_000, next_state["resources"]["coins"])
        self.assertEqual(260_000, next_state["resources"]["kingdom_coffer_coins"])
        self.assertEqual(original_state, self.state)

    def test_withdrawal_reverses_an_exact_transfer(self) -> None:
        deposited = transfer_kingdom_coffer(self.state, "deposit", 250_000)

        restored = transfer_kingdom_coffer(deposited, "withdraw", 250_000)

        self.assertEqual(self.state, restored)

    def test_requires_managing_miscellania_unlock_without_mutating_state(self) -> None:
        self.state["passive_loops"]["kingdom"] = False
        original_state = copy.deepcopy(self.state)

        with self.assertRaisesRegex(ValueError, "Managing Miscellania must be unlocked"):
            transfer_kingdom_coffer(self.state, "deposit", 1)

        self.assertEqual(original_state, self.state)

    def test_rejects_non_positive_or_non_integer_amounts_atomically(self) -> None:
        original_state = copy.deepcopy(self.state)
        for amount in (0, -1, True, 1.5):
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    transfer_kingdom_coffer(self.state, "deposit", amount)
                self.assertEqual(original_state, self.state)

    def test_rejects_unknown_direction_atomically(self) -> None:
        original_state = copy.deepcopy(self.state)

        with self.assertRaisesRegex(ValueError, "direction must be one of"):
            transfer_kingdom_coffer(self.state, "collect", 1)

        self.assertEqual(original_state, self.state)

    def test_rejects_missing_or_invalid_explicit_coffer_balance_atomically(self) -> None:
        del self.state["resources"]["kingdom_coffer_coins"]
        original_state = copy.deepcopy(self.state)

        with self.assertRaisesRegex(ValueError, "resources.kingdom_coffer_coins"):
            transfer_kingdom_coffer(self.state, "deposit", 1)

        self.assertEqual(original_state, self.state)

    def test_rejects_deposit_and_withdrawal_underflow_atomically(self) -> None:
        original_state = copy.deepcopy(self.state)

        with self.assertRaisesRegex(ValueError, "underflow resources.coins"):
            transfer_kingdom_coffer(self.state, "deposit", 1_000_001)
        self.assertEqual(original_state, self.state)

        with self.assertRaisesRegex(ValueError, "underflow resources.kingdom_coffer_coins"):
            transfer_kingdom_coffer(self.state, "withdraw", 10_001)
        self.assertEqual(original_state, self.state)

    def test_pre_royal_trouble_cap_boundary(self) -> None:
        self.state["resources"].update({"coins": 1, "kingdom_coffer_coins": BASE_COFFER_CAP - 1})

        capped = transfer_kingdom_coffer(self.state, "deposit", 1)
        self.assertEqual(BASE_COFFER_CAP, capped["resources"]["kingdom_coffer_coins"])

        capped["resources"]["coins"] = 1
        original_state = copy.deepcopy(capped)
        with self.assertRaisesRegex(ValueError, f"{BASE_COFFER_CAP}-coin cap"):
            transfer_kingdom_coffer(capped, "deposit", 1)
        self.assertEqual(original_state, capped)

    def test_royal_trouble_raises_coffer_cap_and_preserves_boundary(self) -> None:
        self.state["quests_completed"].append("Royal Trouble")
        self.state["resources"].update({"coins": 1, "kingdom_coffer_coins": ROYAL_TROUBLE_COFFER_CAP - 1})

        capped = transfer_kingdom_coffer(self.state, "deposit", 1)

        self.assertEqual(ROYAL_TROUBLE_COFFER_CAP, kingdom_coffer_cap(capped))
        self.assertEqual(ROYAL_TROUBLE_COFFER_CAP, capped["resources"]["kingdom_coffer_coins"])
        capped["resources"]["coins"] = 1
        original_state = copy.deepcopy(capped)
        with self.assertRaisesRegex(ValueError, f"{ROYAL_TROUBLE_COFFER_CAP}-coin cap"):
            transfer_kingdom_coffer(capped, "deposit", 1)
        self.assertEqual(original_state, capped)

    def test_rejects_existing_balance_above_quest_appropriate_cap_atomically(self) -> None:
        self.state["resources"]["kingdom_coffer_coins"] = BASE_COFFER_CAP + 1
        original_state = copy.deepcopy(self.state)

        with self.assertRaisesRegex(ValueError, "balance exceeds"):
            transfer_kingdom_coffer(self.state, "withdraw", 1)

        self.assertEqual(original_state, self.state)

    def test_cli_prints_next_state_without_writing_input_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "account-state.json"
            state_path.write_text(json.dumps(self.state), encoding="utf-8")
            original_contents = state_path.read_text(encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(REPOSITORY_ROOT / "scripts" / "transfer_kingdom_coffer.py"),
                    str(state_path),
                    "deposit",
                    "125",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertEqual(original_contents, state_path.read_text(encoding="utf-8"))

        result = json.loads(completed.stdout)
        self.assertEqual(999_875, result["resources"]["coins"])
        self.assertEqual(10_125, result["resources"]["kingdom_coffer_coins"])
        self.assertEqual(self.state["passive_loops"], result["passive_loops"])


if __name__ == "__main__":
    unittest.main()
