from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from analyze_dependencies import analyze_dependency_closure  # noqa: E402
from evaluate_progression import load_json  # noqa: E402


class AnalyzeDependenciesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.actions_document = load_json(REPOSITORY_ROOT / "data" / "progression" / "actions.json")
        cls.fresh_state = load_json(REPOSITORY_ROOT / "tests" / "fixtures" / "fresh-account.json")

    @staticmethod
    def _action_node(analysis: dict, action_id: str) -> dict:
        return next(node for node in analysis["closure"]["actions"] if node["action_id"] == action_id)

    @staticmethod
    def _predicates(condition: dict) -> list[dict]:
        if "predicate" in condition:
            return [condition]
        return [predicate for child in condition["children"] for predicate in AnalyzeDependenciesTests._predicates(child)]

    @classmethod
    def _predicate(cls, action_node: dict, phase: str, predicate_type: str, key: str) -> dict:
        condition = next(entry["condition"] for entry in action_node["conditions"] if entry["phase"] == phase)
        return next(
            predicate
            for predicate in cls._predicates(condition)
            if predicate["predicate"]["type"] == predicate_type and predicate["predicate"]["key"] == key
        )

    def test_fossil_island_finds_dig_site_and_leaves_kudos_unresolved_without_producer(self) -> None:
        actions_without_kudos = copy.deepcopy(self.actions_document)
        actions_without_kudos["actions"] = [
            action for action in actions_without_kudos["actions"] if action["id"] != "action:museum-kudos-100"
        ]

        analysis = analyze_dependency_closure(
            actions_without_kudos,
            copy.deepcopy(self.fresh_state),
            "action:fossil-island-access",
        )

        fossil = self._action_node(analysis, "action:fossil-island-access")
        dig_site = self._predicate(fossil, "requirements", "quest_completed", "The Dig Site")
        self.assertEqual(["action:the-dig-site"], dig_site["producer_actions"])
        kudos = self._predicate(fossil, "requirements", "counter_at_least", "kudos")
        self.assertEqual([], kudos["producer_actions"])
        self.assertTrue(
            any(entry["predicate"] == kudos["predicate"] for entry in analysis["external_inputs"])
        )
        self.assertTrue(
            any(entry["predicate"] == kudos["predicate"] for entry in analysis["missing_modeled_producers"])
        )

    def test_fairy_ring_preparation_keeps_all_bypass_alternatives_separate(self) -> None:
        analysis = analyze_dependency_closure(
            self.actions_document,
            copy.deepcopy(self.fresh_state),
            "action:fairy-ring-permission",
            include_preparation=True,
        )

        fairy = self._action_node(analysis, "action:fairy-ring-permission")
        preparation = next(entry["condition"] for entry in fairy["conditions"] if entry["phase"] == "preparation")
        self.assertEqual("any", preparation["operator"])
        self.assertEqual(3, len(preparation["children"]))
        self.assertEqual(
            ["dramen_staff", "lunar_staff", "lumbridge_draynor_elite_diary"],
            [child["predicate"]["key"] for child in preparation["children"]],
        )
        alternative = next(
            entry for entry in analysis["alternatives"] if entry["condition_id"] == preparation["id"]
        )
        self.assertEqual([child["id"] for child in preparation["children"]], alternative["branch_ids"])

    def test_analysis_has_no_route_or_ranking_fields(self) -> None:
        analysis = analyze_dependency_closure(
            self.actions_document,
            copy.deepcopy(self.fresh_state),
            "action:fossil-island-access",
        )
        prohibited = {"route", "ranking", "ranked", "recommendation", "score", "next_action"}

        def collect_keys(value: object) -> set[str]:
            if isinstance(value, dict):
                return set(value) | set().union(*(collect_keys(child) for child in value.values()))
            if isinstance(value, list):
                return set().union(*(collect_keys(child) for child in value)) if value else set()
            return set()

        self.assertFalse(prohibited & collect_keys(analysis))

    def test_unknown_goal_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown goal action ID"):
            analyze_dependency_closure(
                self.actions_document,
                copy.deepcopy(self.fresh_state),
                "action:not-in-actions",
            )

    def test_preparation_is_opt_in(self) -> None:
        without_preparation = analyze_dependency_closure(
            self.actions_document,
            copy.deepcopy(self.fresh_state),
            "action:fairy-ring-permission",
        )
        with_preparation = analyze_dependency_closure(
            self.actions_document,
            copy.deepcopy(self.fresh_state),
            "action:fairy-ring-permission",
            include_preparation=True,
        )
        without_node = self._action_node(without_preparation, "action:fairy-ring-permission")
        with_node = self._action_node(with_preparation, "action:fairy-ring-permission")
        self.assertEqual(["requirements"], [entry["phase"] for entry in without_node["conditions"]])
        self.assertEqual(["requirements", "preparation"], [entry["phase"] for entry in with_node["conditions"]])

    def test_action_does_not_claim_its_own_xp_reward_as_prerequisite_progress(self) -> None:
        analysis = analyze_dependency_closure(
            self.actions_document,
            copy.deepcopy(self.fresh_state),
            "action:the-dig-site",
        )
        dig_site = self._action_node(analysis, "action:the-dig-site")
        herblore = self._predicate(dig_site, "requirements", "skill_at_least", "Herblore")

        self.assertFalse(
            any(progress["action_id"] == "action:the-dig-site" for progress in herblore.get("partial_progress", []))
        )

    def test_transition_options_are_explicit_and_never_selected(self) -> None:
        analysis = analyze_dependency_closure(
            self.actions_document,
            copy.deepcopy(self.fresh_state),
            "action:priest-in-peril",
        )

        priest = self._action_node(analysis, "action:priest-in-peril")
        self.assertEqual(
            ["pure-essence", "rune-essence"],
            [choice["option_id"] for choice in priest["transition_choices"]],
        )
        self.assertEqual(
            ["unselected", "unselected"],
            [choice["selection"] for choice in priest["transition_choices"]],
        )
        self.assertEqual(
            priest["transition_choices"],
            [choice for choice in analysis["choices"] if choice["action_id"] == "action:priest-in-peril"],
        )

    def test_royal_trouble_resolves_through_throne_while_its_quest_prerequisites_remain_external(self) -> None:
        analysis = analyze_dependency_closure(
            self.actions_document,
            copy.deepcopy(self.fresh_state),
            "action:royal-trouble",
        )

        royal = self._action_node(analysis, "action:royal-trouble")
        throne_requirement = self._predicate(
            royal,
            "requirements",
            "quest_completed",
            "Throne of Miscellania",
        )
        self.assertEqual(["action:throne-of-miscellania"], throne_requirement["producer_actions"])

        throne = self._action_node(analysis, "action:throne-of-miscellania")
        heroes = self._predicate(throne, "requirements", "quest_completed", "Heroes' Quest")
        fremennik = self._predicate(throne, "requirements", "quest_completed", "The Fremennik Trials")
        self.assertEqual([], heroes["producer_actions"])
        self.assertEqual([], fremennik["producer_actions"])
        self.assertTrue(any(entry["predicate"] == heroes["predicate"] for entry in analysis["external_inputs"]))
        self.assertTrue(any(entry["predicate"] == fremennik["predicate"] for entry in analysis["external_inputs"]))

    def test_descendant_reward_is_not_a_usable_prerequisite_producer(self) -> None:
        analysis = analyze_dependency_closure(
            self.actions_document,
            copy.deepcopy(self.fresh_state),
            "action:royal-trouble",
            include_preparation=True,
        )
        throne = self._action_node(analysis, "action:throne-of-miscellania")
        coins = self._predicate(throne, "preparation", "resource_at_least", "coins")

        self.assertEqual([], coins["producer_actions"])
        self.assertEqual("action:royal-trouble", coins["cyclic_producer_evidence"][0]["action_id"])
        self.assertTrue(analysis["cycles"])

    def test_synthetic_dependency_cycle_is_reported(self) -> None:
        def action(action_id: str, requires_quest: str, completed_quest: str) -> dict:
            return {
                "id": action_id,
                "name": action_id,
                "kind": "quest",
                "status": "verified",
                "fact_ids": ["synthetic"],
                "requirements": {"all": [{"type": "quest_completed", "key": requires_quest}]},
                "preparation": {"all": []},
                "completion": {"all": [{"type": "quest_completed", "key": completed_quest}]},
                "outcomes": [],
                "repeatable": False,
                "transition": {
                    "effects": [
                        {
                            "op": "set_add",
                            "state": "quests_completed",
                            "key": completed_quest,
                            "fact_id": "synthetic",
                        }
                    ],
                    "options": [],
                    "reported_effects": [],
                },
            }

        cycle_document = {
            "actions": [
                action("action:synthetic-a", "Synthetic B", "Synthetic A"),
                action("action:synthetic-b", "Synthetic A", "Synthetic B"),
            ]
        }
        analysis = analyze_dependency_closure(
            cycle_document,
            copy.deepcopy(self.fresh_state),
            "action:synthetic-a",
        )

        self.assertEqual(
            [{"action_ids": ["action:synthetic-a", "action:synthetic-b", "action:synthetic-a"]}],
            analysis["cycles"],
        )


if __name__ == "__main__":
    unittest.main()
