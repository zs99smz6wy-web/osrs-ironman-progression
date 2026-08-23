from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_minigame_packages import validate  # noqa: E402


class MinigamePackageValidationTests(unittest.TestCase):
    def test_manifested_minigame_packages_validate(self) -> None:
        errors, report = validate()

        self.assertEqual([], errors)
        self.assertEqual(17, report["packages"])
        self.assertEqual(182, report["source_references"])
        self.assertEqual(172, report["canonical_sources"])
        self.assertEqual(182, report["package_scoped_aliases"])
        self.assertGreater(report["community_strategy_aliases"], 0)


if __name__ == "__main__":
    unittest.main()
