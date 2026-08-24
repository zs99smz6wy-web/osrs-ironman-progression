import copy
import unittest

from scripts.validate_partial_quest_packages import validate_manifest, validate_package


class PartialQuestPackageValidationTests(unittest.TestCase):
    def test_manifest_validates(self) -> None:
        report, errors = validate_manifest()
        self.assertEqual([], errors)
        self.assertGreaterEqual(report["packages"], 1)
        self.assertGreaterEqual(report["checkpoints"], 2)

    def test_partial_checkpoint_cannot_be_normalized_completion(self) -> None:
        package = {
            "package_schema_version": 1,
            "package_type": "research-only-partial-quest",
            "quest_id": "sample",
            "quest_name": "Sample",
            "status": "research",
            "scope": "Test fixture.",
            "sources": [{"id": "wiki", "url": "https://oldschool.runescape.wiki/", "used_for": "fixture", "verified_at": "2026-08-24"}],
            "requirements": {"quests": [], "skills": [], "items": [], "gp": 0, "other": []},
            "checkpoints": [],
            "completion": {"normalized_action_id": None, "rewards": [], "unlocks": [], "post_completion_claims": []},
            "boundaries": {"route_selected": False, "partial_progress_is_quest_completion": False, "action_auto_applied": False, "items_or_rewards_inferred": False, "lamp_target_selected": False, "survival_inferred": False},
        }
        checkpoint = {"id": "checkpoint:sample-started", "sequence": 1, "state": "start", "location": "Somewhere", "description": "Started.", "item_changes": [], "hazards": [], "observation": {"class": "player_confirmation", "instruction": "Confirm it.", "sufficient_by_itself": True, "runelite_boundary": "Not imported."}, "promotion": {"status": "normalized_completion", "reason": "Invalid fixture."}, "source_ids": ["wiki"]}
        package["checkpoints"] = [checkpoint, {**copy.deepcopy(checkpoint), "id": "checkpoint:sample-complete", "sequence": 2, "state": "completion", "promotion": {"status": "research_only", "reason": "Fixture."}}]
        errors = validate_package(package, "sample.json")
        self.assertTrue(any("only completion checkpoints" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
