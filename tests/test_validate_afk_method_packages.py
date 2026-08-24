from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_afk_method_packages import validate  # noqa: E402


class AfkMethodPackageValidationTests(unittest.TestCase):
    def test_completed_manifest_validates_all_research_packages(self) -> None:
        errors, report = validate()
        self.assertEqual([], errors)
        self.assertEqual(5, report["planned_packages"])
        self.assertEqual(5, report["completed_packages"])

    def test_completed_package_rejects_invalid_source_reference(self) -> None:
        root = self.make_completed_fixture()
        package = self.load_package(root)
        package["access"]["requirements"] = {"source_id": "missing-source"}
        self.write_package(root, package)
        self.assert_contains(root, "missing-source")

    def test_completed_package_rejects_invalid_source_date_and_url(self) -> None:
        root = self.make_completed_fixture()
        package = self.load_package(root)
        package["source_catalog"][0]["checked_at"] = "2026-02-30"
        package["source_catalog"][0]["url"] = "not-a-url"
        self.write_package(root, package)
        self.assert_contains(root, "checked_at must be a real ISO date")
        self.assert_contains(root, "absolute HTTP(S) URI")

    def test_completed_package_rejects_bad_attention_claim(self) -> None:
        root = self.make_completed_fixture()
        package = self.load_package(root)
        package["attention_profile"]["player_presence_required"] = False
        self.write_package(root, package)
        self.assert_contains(root, "expected constant True")

    def test_completed_package_rejects_output_boundary_leakage(self) -> None:
        root = self.make_completed_fixture()
        package = self.load_package(root)
        package["outputs"]["variable"].append({"id": "xp:mining", "description": "duplicate", "source_ids": ["wiki-stars"], "boundary": "variable"})
        self.write_package(root, package)
        self.assert_contains(root, "appears in more than one output boundary")

    def test_completed_packages_reject_duplicate_proposed_ids(self) -> None:
        root = self.make_completed_fixture()
        manifest = self.load_manifest(root)
        second = deepcopy(manifest["packages"][0])
        second.update({"path": "research/afk-method-packages/basic-fishing.json", "package_id": "research-afk-basic-fishing", "method": "Basic fishing", "phase": "completed"})
        manifest["packages"][1] = second
        self.write_json(root / "research/afk-method-packages/integration-manifest.json", manifest)
        package = self.load_package(root)
        package["package_id"] = "research-afk-basic-fishing"
        package["method"] = "Basic fishing"
        self.write_json(root / "research/afk-method-packages/basic-fishing.json", package)
        self.assert_contains(root, "duplicate proposed action id action:shooting-stars")

    def test_completed_package_rejects_strategy_leakage(self) -> None:
        root = self.make_completed_fixture()
        package = self.load_package(root)
        package["strategy_score"] = 10
        self.write_package(root, package)
        self.assert_contains(root, "forbidden strategy field")

    def make_completed_fixture(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        schema_source = ROOT / "research/package-schemas/afk-method-package.schema.json"
        schema_target = root / "research/package-schemas/afk-method-package.schema.json"
        schema_target.parent.mkdir(parents=True)
        schema_target.write_text(schema_source.read_text(encoding="utf-8"), encoding="utf-8")
        manifest = json.loads((ROOT / "research/afk-method-packages/integration-manifest.json").read_text(encoding="utf-8"))
        manifest["packages"][0]["phase"] = "completed"
        self.write_json(root / "research/afk-method-packages/integration-manifest.json", manifest)
        self.write_package(root, self.valid_package())
        return root

    def valid_package(self) -> dict[str, object]:
        return {
            "package_schema_version": 1,
            "package_type": "afk-low-attention-research",
            "package_id": "research-afk-shooting-stars",
            "method": "Shooting stars",
            "status": "research-proposal",
            "checked_at": "2026-08-24",
            "facts_strategy_boundary": {"included": ["Sourced mechanics."], "excluded": ["Strategy scoring, route order, account readiness inference, recommended 99 targets, and guaranteed RNG or hourly rates."]},
            "source_catalog": [{"id": "wiki-stars", "publisher": "Old School RuneScape Wiki", "kind": "wiki", "url": "https://oldschool.runescape.wiki/w/Shooting_Stars", "checked_at": "2026-08-24", "use": "Fixture mechanics source."}],
            "access": {"requirements": {"source_id": "wiki-stars"}, "tools": [], "locations": [{"name": "observed landing site", "source_ids": ["wiki-stars"]}], "transport_options": []},
            "preparation": {"inventory_inputs": [], "bank_inputs": [], "reusable_items": [], "consumed_inputs": [], "capacity_constraints": []},
            "attention_profile": {"class": "low_attention", "interaction_cadence": [{"claim": "Interaction cadence is source-defined.", "evidence_type": "source", "source_ids": ["wiki-stars"]}], "player_presence_required": True, "unattended_safety_claim": "never_infer"},
            "session_mechanics": {"entry_condition": "A star is present.", "duration_evidence": {"basis": "source", "source_ids": ["wiki-stars"]}, "session_end_events": ["The star depletes."], "repeatable": True, "offline_progression": False},
            "outputs": {"deterministic": [{"id": "xp:mining", "description": "Observed XP event.", "source_ids": ["wiki-stars"], "boundary": "deterministic"}], "variable": [{"id": "item:gem-bag", "description": "Variable reward boundary.", "source_ids": ["wiki-stars"], "boundary": "variable"}], "player_observed": [{"id": "observation:shooting-stars:result", "description": "Player-recorded result.", "source_ids": [], "boundary": "player_observed"}]},
            "safety_and_logout": {"damage_sources": [], "death_possible": "unknown", "logout_behavior": ["Source-defined idle behavior."], "safe_boundary": "No unattended safety is inferred."},
            "stop_reentry_mechanics": {"mechanical_stop_conditions": ["Star depletion."], "mechanical_reentry_conditions": ["A new star is found."], "reset_or_cleanup_requirements": []},
            "proposed_normalization": {"facts": [{"id": "fact:shooting-stars-access"}], "actions": [{"id": "action:shooting-stars"}], "nodes": [{"id": "activity:shooting-stars"}], "edges": [{"id": "edge:shooting-stars-access"}], "observations": [{"id": "observation:shooting-stars:state"}]},
            "conflicts_and_unknowns": [],
            "coverage": {"access": True, "preparation": True, "attention": True, "session": True, "outputs": True, "safety": True, "stop_reentry": True, "sources": True, "normalization": True},
        }

    def load_manifest(self, root: Path) -> dict[str, object]:
        return json.loads((root / "research/afk-method-packages/integration-manifest.json").read_text(encoding="utf-8"))

    def load_package(self, root: Path) -> dict[str, object]:
        return json.loads((root / "research/afk-method-packages/shooting-stars.json").read_text(encoding="utf-8"))

    def write_package(self, root: Path, package: dict[str, object]) -> None:
        self.write_json(root / "research/afk-method-packages/shooting-stars.json", package)

    def write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def assert_contains(self, root: Path, expected: str) -> None:
        errors, _ = validate(root)
        self.assertTrue(any(expected in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
