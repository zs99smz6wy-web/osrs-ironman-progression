from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_diary_packages import validate  # noqa: E402


class DiaryPackageValidationTests(unittest.TestCase):
    def test_manifested_diary_packages_validate(self) -> None:
        errors, report = validate()

        self.assertEqual([], errors)
        self.assertEqual(12, report["packages"])
        self.assertEqual(488, report["tasks"])
        self.assertEqual(
            ["action-integration-decision.json", "integration-manifest.json"],
            report["recognized_non_package_artifacts"],
        )
        self.assertEqual(
            {
                "ardougne",
                "falador",
                "fremennik",
                "kandarin",
                "karamja",
                "lumbridge-draynor",
                "morytania",
                "western-provinces",
                "wilderness",
            },
            set(report["catalog_inheritance_packages"]),
        )


if __name__ == "__main__":
    unittest.main()
