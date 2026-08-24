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
        base_before = copy.deepcopy(base)
        result = self.import_fixture(base=base)
        state = result["updated_account_state"]
        self.assertEqual(base_before, base)
        self.assertEqual({"private_bank_marker": 7}, state["items"])
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

    def test_optional_file_staleness_is_a_warning_not_a_blocker(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "Sample Iron"
            shutil.copytree(ACCOUNT_DIR, destination)
            (destination / "bank.json").write_text("this is deliberately not JSON", encoding="utf-8")
            diary = read_json(destination / "diaries.json")
            diary["session_id"] = "older-diary-session"
            diary["plugin_version"] = "0.5.0"
            (destination / "diaries.json").write_text(json.dumps(diary), encoding="utf-8")
            documents, warnings = load_export_documents(destination)
            result = import_runelite_export(read_json(BASE_STATE), documents, warnings=warnings)
        reported_warnings = result["import_report"]["warnings"]
        self.assertTrue(any("bank.json is present but unsupported" in warning for warning in reported_warnings))
        self.assertTrue(any("diaries.json is from a different export session" in warning for warning in reported_warnings))
        self.assertEqual("reported_only", result["import_report"]["diaries"]["status"])

    def test_missing_optional_files_are_warnings_not_empty_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "Sample Iron"
            shutil.copytree(ACCOUNT_DIR, destination)
            (destination / "diaries.json").unlink()
            documents, warnings = load_export_documents(destination)
            result = import_runelite_export(read_json(BASE_STATE), documents, warnings=warnings)
        self.assertEqual("missing", result["import_report"]["diaries"]["status"])
        self.assertTrue(any("bank.json" in warning for warning in result["import_report"]["warnings"]))
        self.assertFalse(result["import_report"]["false_inference_flags"]["item_containers_treated_as_empty"])

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
