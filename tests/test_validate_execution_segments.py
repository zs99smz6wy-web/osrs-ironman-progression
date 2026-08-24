from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_execution_segments import _canonical_action_facts, _canonical_fact_ids, load_json, validate, validate_segment  # noqa: E402


PROOF = ROOT / "research" / "execution-segments" / "post-tutorial-varrock-museum-proof.json"


class ExecutionSegmentValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.segment = load_json(PROOF)
        self.action_facts = _canonical_action_facts(ROOT)
        self.fact_ids = _canonical_fact_ids(ROOT)

    def validate_proof(self, segment: dict) -> list[str]:
        return validate_segment(segment, self.action_facts, self.fact_ids, "proof.json")

    def test_manifested_proof_segment_validates_and_keeps_partial_quest_external(self) -> None:
        errors, report = validate()

        self.assertEqual([], errors)
        self.assertEqual(1, report["segments"])
        self.assertEqual(1, report["linked_normalized_actions"])
        self.assertEqual(3, report["sourced_unmodeled_steps"])
        self.assertEqual(1, report["unresolved_partial_quest_checkpoints"])
        partial = self.segment["checkpoints"][0]
        self.assertEqual("external_partial_quest", partial["kind"])
        self.assertEqual("unresolved", partial["coverage"]["status"])
        self.assertNotIn("normalized_action_id", partial["coverage"])

    def test_partial_quest_checkpoint_cannot_be_represented_as_normalized_completion(self) -> None:
        invalid = copy.deepcopy(self.segment)
        coverage = invalid["checkpoints"][0]["coverage"]
        coverage.update(
            {
                "status": "normalized_action",
                "normalized_action_id": "action:the-restless-ghost",
                "fact_ids": ["the-restless-ghost"],
                "source_ids": ["wiki-kudos"],
            }
        )

        errors = self.validate_proof(invalid)

        self.assertTrue(any("partial quest checkpoints cannot be normalized actions" in error for error in errors))

    def test_every_linked_coarse_action_needs_an_explicit_boundary(self) -> None:
        invalid = copy.deepcopy(self.segment)
        invalid["normalization_boundaries"] = [
            boundary
            for boundary in invalid["normalization_boundaries"]
            if boundary["normalized_action_id"] != "action:claim-minas-rune-mysteries"
        ]

        errors = self.validate_proof(invalid)

        self.assertIn(
            "proof.json: linked normalized action action:claim-minas-rune-mysteries lacks a coarse-action boundary",
            errors,
        )

    def test_sourced_substep_cannot_silently_link_a_normalized_action(self) -> None:
        invalid = copy.deepcopy(self.segment)
        invalid["execution_steps"][0]["coverage"]["normalized_action_id"] = "action:natural-history-quiz"

        errors = self.validate_proof(invalid)

        self.assertTrue(any("unsupported coverage fields" in error for error in errors))

    def test_safety_never_infers_survival_and_passive_checks_need_an_interruption_policy(self) -> None:
        invalid_safety = copy.deepcopy(self.segment)
        invalid_safety["safety_hcim"]["never_inferred_survival"] = False
        safety_errors = self.validate_proof(invalid_safety)
        self.assertIn("proof.json.safety_hcim.never_inferred_survival: must be true", safety_errors)

        invalid_passive = copy.deepcopy(self.segment)
        del invalid_passive["passive_recurring_checks"][0]["interruption_policy"]
        passive_errors = self.validate_proof(invalid_passive)
        self.assertTrue(any("passive check fields are invalid" in error for error in passive_errors))

    def test_purpose_must_keep_account_applicability_outside_route_selection(self) -> None:
        invalid = copy.deepcopy(self.segment)
        invalid["purpose"]["applicability_is_not_route_selection"] = False

        errors = self.validate_proof(invalid)

        self.assertIn("proof.json.purpose.applicability_is_not_route_selection: must be true", errors)


if __name__ == "__main__":
    unittest.main()
