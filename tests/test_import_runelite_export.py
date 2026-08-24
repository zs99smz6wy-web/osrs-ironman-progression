"""Focused coverage for the intentionally bounded RuneLite export importer."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from import_runelite_export import (  # noqa: E402
    ImportError,
    import_runelite_export,
    load_export_documents,
    resolve_account_directory,
    sanitize_account_name,
)


FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "runelite-export"
ACCOUNT_DIR = FIXTURE_ROOT / "Sample Iron"
BASE_STATE = ROOT / "graph" / "account-state.example.json"
IMPORTER = ROOT / "scripts" / "import_runelite_export.py"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RuneLiteImportTests(unittest.TestCase):
    def documents(self) -> dict:
        documents, _ = load_export_documents(ACCOUNT_DIR)
        return documents

    def import_fixture(self, *, documents: dict | None = None, base: dict | None = None) -> dict:
        return import_runelite_export(
            read_json(BASE_STATE) if base is None else base,
            self.documents() if documents is None else documents,
            account_directory=ACCOUNT_DIR,
            expected_account_name="Sample Iron",
        )

    def test_folder_resolution_matches_upstream_sanitization_and_rejects_missing(self):
        self.assertEqual("A_B-C D", sanitize_account_name("A:B-C D"))
        self.assertEqual(ACCOUNT_DIR.resolve(), resolve_account_directory(export_root=FIXTURE_ROOT, account_name="Sample Iron"))
        with self.assertRaisesRegex(ImportError, "no Character Export folder"):
            resolve_account_directory(export_root=FIXTURE_ROOT, account_name="Absent")
        with self.assertRaisesRegex(ImportError, "cannot be combined"):
            resolve_account_directory(account_directory=ACCOUNT_DIR, account_name="Sample Iron")

    def test_imports_all_real_levels_and_xp_including_sailing_but_not_boosts(self):
        result = self.import_fixture()
        state = result["updated_account_state"]
        self.assertEqual(10, state["skills"]["Sailing"])
        self.assertEqual(1_154, state["skill_xp"]["Sailing"])
        self.assertEqual(10, state["skills"]["Hitpoints"])
        self.assertNotIn("boosted_level", state["skills"])
        self.assertEqual(24, result["import_report"]["imported"]["skills"])

    def test_imports_finished_quests_only_and_preserves_confirmed_base_quests(self):
        base = read_json(BASE_STATE)
        base["quests_completed"] = ["Cook's Assistant"]
        result = self.import_fixture(base=base)
        self.assertEqual(["Cook's Assistant", "The Restless Ghost"], result["updated_account_state"]["quests_completed"])
        self.assertNotIn("Waterfall Quest", result["updated_account_state"]["quests_completed"])

    def test_deep_copy_preserves_private_state_and_diaries_are_report_only(self):
        base = read_json(BASE_STATE)
        base["items"] = {"private_bank_marker": 7}
        base["resources"] = {"private_resource_marker": 9, "coins": 200}
        base_before = copy.deepcopy(base)
        result = self.import_fixture(base=base)
        state = result["updated_account_state"]
        self.assertEqual(base_before, base)
        self.assertEqual(7, state["items"]["private_bank_marker"])
        self.assertEqual(9, state["resources"]["private_resource_marker"])
        self.assertEqual(200, state["resources"]["coins"])
        self.assertEqual(base_before["diary_tiers"], state["diary_tiers"])
        self.assertNotIn("diary_task_observations", state)
        diary = result["import_report"]["diaries"]
        self.assertEqual("reported_only", diary["status"])
        self.assertTrue(diary["areas"]["Ardougne"]["easy"]["named_tasks_present"])
        self.assertFalse(diary["areas"]["Ardougne"]["medium"]["named_tasks_present"])
        self.assertFalse(result["import_report"]["false_inference_flags"]["diary_tiers_mutated"])

    def test_rejects_mixed_required_sessions_malformed_quest_state_and_bad_skill_layout(self):
        documents = self.documents()
        documents["quests"] = copy.deepcopy(documents["quests"])
        documents["quests"]["session_id"] = "different-session"
        with self.assertRaisesRegex(ImportError, "mixed export sessions"):
            self.import_fixture(documents=documents)

        documents = self.documents()
        documents["quests"] = copy.deepcopy(documents["quests"])
        documents["quests"]["quests"][0]["state"] = "COMPLETE"
        with self.assertRaisesRegex(ImportError, "state must be one of"):
            self.import_fixture(documents=documents)

        documents = self.documents()
        documents["character"] = copy.deepcopy(documents["character"])
        del documents["character"]["stats"]["Sailing"]
        with self.assertRaisesRegex(ImportError, "skill layout"):
            self.import_fixture(documents=documents)

    def test_rejects_duplicate_quests_and_level_xp_mismatch(self):
        documents = self.documents()
        documents["quests"] = copy.deepcopy(documents["quests"])
        documents["quests"]["quests"].append({"id": 1, "name": "A Different Quest", "state": "FINISHED"})
        with self.assertRaisesRegex(ImportError, "duplicate quest id"):
            self.import_fixture(documents=documents)

        documents = self.documents()
        documents["character"] = copy.deepcopy(documents["character"])
        documents["character"]["stats"]["Sailing"]["real_level"] = 11
        with self.assertRaisesRegex(ImportError, "level/XP mismatch"):
            self.import_fixture(documents=documents)

    def test_container_imports_numeric_ids_across_distinct_containers(self):
        result = self.import_fixture()
        state = result["updated_account_state"]
        self.assertEqual(125, state["resources"]["coins"])
        self.assertEqual(25, state["items"]["feathers"])
        self.assertEqual(1, state["items"]["axe"])
        self.assertNotIn("watering_can", state["items"])
        self.assertEqual(50, state["items"]["low_level_birdhouse_seed"])
        self.assertEqual(4, state["items"]["logs"])
        containers = result["import_report"]["containers"]
        self.assertEqual("imported", containers["datasets"]["equipment"]["status"])
        coins = next(entry for entry in containers["resolved"] if entry["model_key"] == "coins")
        self.assertEqual({995: 125}, coins["physical_item_quantities"])
        self.assertEqual(["bank", "inventory"], coins["source_containers"])
        self.assertTrue({5340, 99999}.issubset({entry["item_id"] for entry in containers["unmapped_exported_items"]}))
        feathers = next(entry for entry in containers["resolved"] if entry["model_key"] == "feathers")
        self.assertEqual({314: 25}, feathers["physical_item_quantities"])

    def test_container_staleness_and_malformed_data_warn_without_empty_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "Sample Iron"
            shutil.copytree(ACCOUNT_DIR, destination)
            (destination / "bank.json").write_text("this is deliberately not JSON", encoding="utf-8")
            seed_vault = read_json(destination / "seed_vault.json")
            seed_vault["session_id"] = "older-container-session"
            (destination / "seed_vault.json").write_text(json.dumps(seed_vault), encoding="utf-8")
            diary = read_json(destination / "diaries.json")
            diary["session_id"] = "older-diary-session"
            diary["plugin_version"] = "0.5.0"
            (destination / "diaries.json").write_text(json.dumps(diary), encoding="utf-8")
            documents, warnings = load_export_documents(destination)
            result = import_runelite_export(read_json(BASE_STATE), documents, warnings=warnings)
        reported_warnings = result["import_report"]["warnings"]
        self.assertTrue(any("bank.json is malformed" in warning for warning in reported_warnings))
        self.assertTrue(any("seed_vault.json was not imported" in warning for warning in reported_warnings))
        self.assertTrue(any("diaries.json is from a different export session" in warning for warning in reported_warnings))
        self.assertEqual("missing_or_unreadable", result["import_report"]["containers"]["datasets"]["bank"]["status"])
        self.assertEqual("skipped", result["import_report"]["containers"]["datasets"]["seed_vault"]["status"])
        self.assertEqual("reported_only", result["import_report"]["diaries"]["status"])

    def test_missing_optional_files_are_warnings_not_empty_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "Sample Iron"
            shutil.copytree(ACCOUNT_DIR, destination)
            (destination / "diaries.json").unlink()
            (destination / "bank.json").unlink()
            documents, warnings = load_export_documents(destination)
            result = import_runelite_export(read_json(BASE_STATE), documents, warnings=warnings)
        self.assertEqual("missing", result["import_report"]["diaries"]["status"])
        self.assertTrue(any("bank.json" in warning for warning in result["import_report"]["warnings"]))
        self.assertFalse(result["import_report"]["false_inference_flags"]["item_containers_treated_as_empty"])

    def test_container_mismatch_or_bad_shape_is_skipped_and_display_names_are_not_guessed(self):
        documents = self.documents()
        documents["inventory"] = copy.deepcopy(documents["inventory"])
        documents["inventory"]["item_count"] = 3
        documents["equipment"] = copy.deepcopy(documents["equipment"])
        documents["equipment"]["account_name"] = "Different Iron"
        documents["bank"] = copy.deepcopy(documents["bank"])
        documents["bank"]["items"][0] = {"slot": 0, "id": 99998, "quantity": 50, "name": "Coins"}
        result = self.import_fixture(documents=documents)
        state = result["updated_account_state"]
        self.assertEqual(read_json(BASE_STATE)["resources"].get("coins", 0), state["resources"].get("coins", 0))
        self.assertEqual("skipped", result["import_report"]["containers"]["datasets"]["inventory"]["status"])
        self.assertEqual("skipped", result["import_report"]["containers"]["datasets"]["equipment"]["status"])
        unmapped_ids = {entry["item_id"] for entry in result["import_report"]["containers"]["unmapped_exported_items"]}
        self.assertIn(99998, unmapped_ids)

    def test_cli_stdout_and_overwrite_protection(self):
        command = [sys.executable, str(IMPORTER), "--account-directory", str(ACCOUNT_DIR)]
        stdout = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual("Sample Iron", json.loads(stdout.stdout)["import_report"]["account_name"])
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "import.json"
            output.write_text("existing", encoding="utf-8")
            denied = subprocess.run([*command, "--output", str(output)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(2, denied.returncode)
            self.assertEqual("existing", output.read_text(encoding="utf-8"))
            allowed = subprocess.run([*command, "--output", str(output), "--force"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, allowed.returncode)
            self.assertIn("updated_account_state", json.loads(output.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
