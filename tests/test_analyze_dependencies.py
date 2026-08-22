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

    def test_fossil_island_finds_dig_site_and_exact_partial_kudos_producers(self) -> None:
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
        self.assertEqual(
            [
                "action:display-museum-ancient-coin",
                "action:display-museum-ancient-symbol",
                "action:display-museum-old-coin",
                "action:display-museum-old-symbol",
                "action:display-museum-pottery",
                "action:natural-history-quiz",
            ],
            kudos["producer_actions"],
        )
        self.assertEqual("partial_progress", kudos["status"])
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

    def test_recurring_readiness_remains_an_external_observation(self) -> None:
        analysis = analyze_dependency_closure(
            self.actions_document,
            copy.deepcopy(self.fresh_state),
            "action:collect-reset-birdhouses",
        )

        action_node = self._action_node(analysis, "action:collect-reset-birdhouses")
        readiness = self._predicate(action_node, "requirements", "recurring_state", "birdhouses")
        self.assertEqual("unobserved", readiness["current_value"])
        self.assertEqual([], readiness["producer_actions"])
        self.assertTrue(any(entry["predicate"] == readiness["predicate"] for entry in analysis["external_inputs"]))
        self.assertFalse(
            any(entry["predicate"] == readiness["predicate"] for entry in analysis["missing_modeled_producers"])
        )

    def test_slayer_task_target_remains_an_external_player_observation(self) -> None:
        actions = {
            "actions": [
                {
                    "id": "action:synthetic-slayer-task-consumer",
                    "name": "Use current Slayer task",
                    "kind": "activity",
                    "status": "verified",
                    "fact_ids": ["synthetic"],
                    "requirements": {
                        "all": [{"type": "slayer_task_target", "key": "Aberrant spectres"}],
                    },
                    "preparation": {"all": []},
                    "completion": {"all": []},
                    "outcomes": [],
                    "repeatable": True,
                    "transition": {"effects": [], "options": [], "reported_effects": []},
                }
            ]
        }

        analysis = analyze_dependency_closure(
            actions,
            copy.deepcopy(self.fresh_state),
            "action:synthetic-slayer-task-consumer",
        )

        consumer = self._action_node(analysis, "action:synthetic-slayer-task-consumer")
        task = self._predicate(consumer, "requirements", "slayer_task_target", "Aberrant spectres")
        self.assertIsNone(task["current_value"])
        self.assertEqual([], task["producer_actions"])
        self.assertTrue(any(entry["predicate"] == task["predicate"] for entry in analysis["external_inputs"]))
        self.assertFalse(
            any(entry["predicate"] == task["predicate"] for entry in analysis["missing_modeled_producers"])
        )

    def test_diary_tier_remains_an_external_confirmed_claim_observation(self) -> None:
        actions = {
            "actions": [
                {
                    "id": "action:synthetic-diary-tier-consumer",
                    "name": "Use confirmed diary claim",
                    "kind": "activity",
                    "status": "verified",
                    "fact_ids": ["synthetic"],
                    "requirements": {
                        "all": [{"type": "diary_tier_at_least", "key": "Falador", "value": "hard"}],
                    },
                    "preparation": {"all": []},
                    "completion": {"all": []},
                    "outcomes": [],
                    "repeatable": True,
                    "transition": {"effects": [], "options": [], "reported_effects": []},
                }
            ]
        }

        analysis = analyze_dependency_closure(
            actions,
            copy.deepcopy(self.fresh_state),
            "action:synthetic-diary-tier-consumer",
        )

        consumer = self._action_node(analysis, "action:synthetic-diary-tier-consumer")
        tier = self._predicate(consumer, "requirements", "diary_tier_at_least", "Falador")
        self.assertEqual("none", tier["current_value"])
        self.assertEqual([], tier["producer_actions"])
        self.assertTrue(any(entry["predicate"] == tier["predicate"] for entry in analysis["external_inputs"]))
        self.assertFalse(
            any(entry["predicate"] == tier["predicate"] for entry in analysis["missing_modeled_producers"])
        )

    def test_kourend_memoir_predicates_are_external_without_effects_but_resolve_from_explicit_effects(self) -> None:
        consumer = {
            "id": "action:synthetic-memoir-consumer",
            "name": "Use memoir transport",
            "kind": "activity",
            "status": "verified",
            "fact_ids": ["synthetic"],
            "requirements": {"all": [
                {"type": "kourend_memoir_owned", "key": "kourend_memoir"},
                {"type": "kourend_memoir_form", "key": "memoirs"},
                {"type": "kourend_memoir_page", "key": "the_fishers_flute"},
                {"type": "kourend_memoir_charges_at_least", "key": "charges", "value": 20},
                {"type": "kourend_memoir_charge_space_at_least", "key": "charges", "value": 1},
            ]},
            "preparation": {"all": []},
            "completion": {"all": []},
            "outcomes": [],
            "repeatable": True,
            "transition": {"effects": [], "options": [], "reported_effects": []},
        }
        source = {
            "id": "action:synthetic-memoir-source",
            "name": "Build memoir transport",
            "kind": "activity",
            "status": "verified",
            "fact_ids": ["synthetic"],
            "requirements": {"all": []},
            "preparation": {"all": []},
            "completion": {"all": []},
            "outcomes": [],
            "repeatable": True,
            "transition": {
                "effects": [
                    {"op": "obtain_kourend_memoir", "state": "kourend_memoir", "key": "memoirs", "fact_id": "synthetic"},
                    {"op": "add_kourend_memoir_page", "state": "kourend_memoir", "key": "the_fishers_flute", "fact_id": "synthetic"},
                    {"op": "spend_kourend_memoir_charges", "state": "kourend_memoir", "key": "charges", "amount": 1, "fact_id": "synthetic"},
                ],
                "options": [],
                "reported_effects": [],
            },
        }

        external_analysis = analyze_dependency_closure({"actions": [consumer]}, copy.deepcopy(self.fresh_state), consumer["id"])
        external_node = self._action_node(external_analysis, consumer["id"])
        for predicate_type, key in (
            ("kourend_memoir_owned", "kourend_memoir"),
            ("kourend_memoir_form", "memoirs"),
            ("kourend_memoir_page", "the_fishers_flute"),
            ("kourend_memoir_charges_at_least", "charges"),
            ("kourend_memoir_charge_space_at_least", "charges"),
        ):
            predicate = self._predicate(external_node, "requirements", predicate_type, key)
            self.assertTrue(any(entry["predicate"] == predicate["predicate"] for entry in external_analysis["external_inputs"]))
            self.assertFalse(any(entry["predicate"] == predicate["predicate"] for entry in external_analysis["missing_modeled_producers"]))

        produced_analysis = analyze_dependency_closure({"actions": [consumer, source]}, copy.deepcopy(self.fresh_state), consumer["id"])
        produced_node = self._action_node(produced_analysis, consumer["id"])
        for predicate_type, key in (
            ("kourend_memoir_owned", "kourend_memoir"),
            ("kourend_memoir_form", "memoirs"),
            ("kourend_memoir_page", "the_fishers_flute"),
            ("kourend_memoir_charges_at_least", "charges"),
            ("kourend_memoir_charge_space_at_least", "charges"),
        ):
            predicate = self._predicate(produced_node, "requirements", predicate_type, key)
            self.assertEqual([source["id"]], predicate["producer_actions"])

        observed_state = copy.deepcopy(self.fresh_state)
        observed_state["kourend_memoir"] = {
            "form": "memoirs",
            "pages": ["the_fishers_flute"],
            "charges": 15,
        }
        observed_analysis = analyze_dependency_closure({"actions": [consumer]}, observed_state, consumer["id"])
        observed_node = self._action_node(observed_analysis, consumer["id"])
        space = self._predicate(
            observed_node,
            "requirements",
            "kourend_memoir_charge_space_at_least",
            "charges",
        )
        self.assertEqual(5, space["current_value"])

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
        actions_document = {
            "actions": [
                action
                for action in self.actions_document["actions"]
                if action["id"] in {"action:throne-of-miscellania", "action:royal-trouble"}
            ]
        }
        analysis = analyze_dependency_closure(
            actions_document,
            copy.deepcopy(self.fresh_state),
            "action:royal-trouble",
            include_preparation=True,
        )
        throne = self._action_node(analysis, "action:throne-of-miscellania")
        coins = self._predicate(throne, "preparation", "resource_at_least", "coins")

        self.assertEqual([], coins["producer_actions"])
        self.assertEqual("action:royal-trouble", coins["cyclic_producer_evidence"][0]["action_id"])
        self.assertTrue(analysis["cycles"])

    def test_fallen_from_grace_closure_resolves_wyrmscraig_and_preserves_skill_inputs(self) -> None:
        analysis = analyze_dependency_closure(
            self.actions_document,
            copy.deepcopy(self.fresh_state),
            "action:fallen-from-grace",
        )

        fallen = self._action_node(analysis, "action:fallen-from-grace")
        wyrmscraig = self._predicate(fallen, "requirements", "transport_flag", "wyrmscraig")
        sailing = self._predicate(fallen, "requirements", "skill_at_least", "Sailing")

        self.assertEqual(["action:wyrmscraig-access"], wyrmscraig["producer_actions"])
        self.assertEqual([], sailing["producer_actions"])
        self.assertTrue(any(entry["predicate"] == sailing["predicate"] for entry in analysis["external_inputs"]))

    def test_sunstone_golem_keeps_tools_and_inputs_as_preparation_not_guaranteed_rewards(self) -> None:
        analysis = analyze_dependency_closure(
            self.actions_document,
            copy.deepcopy(self.fresh_state),
            "action:sunstone-golem-crafting",
            include_preparation=True,
        )

        golem = self._action_node(analysis, "action:sunstone-golem-crafting")
        preparation = next(entry["condition"] for entry in golem["conditions"] if entry["phase"] == "preparation")
        keys = [predicate["predicate"]["key"] for predicate in self._predicates(preparation)]

        self.assertEqual(["hammer", "chisel", "sunstone", "hunter_fur"], keys)
        self.assertFalse(any("jeweller" in str(node).lower() for node in analysis["closure"]["actions"]))

    def test_rng_reward_reports_do_not_produce_guaranteed_closure_inputs(self) -> None:
        actions = copy.deepcopy(self.actions_document)
        actions["actions"].append(
            {
                "id": "action:fish-barrel-consumer",
                "name": "Use a Fish Barrel",
                "kind": "activity",
                "status": "verified",
                "fact_ids": ["tempoross-fish-barrel"],
                "requirements": {"all": [{"type": "item_at_least", "key": "fish_barrel", "value": 1}]},
                "preparation": {"all": []},
                "completion": {"all": []},
                "outcomes": [],
                "repeatable": True,
                "transition": {"effects": [], "options": [], "reported_effects": []},
            }
        )

        analysis = analyze_dependency_closure(
            actions,
            copy.deepcopy(self.fresh_state),
            "action:fish-barrel-consumer",
        )

        consumer = self._action_node(analysis, "action:fish-barrel-consumer")
        fish_barrel = self._predicate(consumer, "requirements", "item_at_least", "fish_barrel")
        self.assertEqual([], fish_barrel["producer_actions"])
        self.assertTrue(any(entry["predicate"] == fish_barrel["predicate"] for entry in analysis["external_inputs"]))
        self.assertNotIn("action:tempoross", [node["action_id"] for node in analysis["closure"]["actions"]])

    def test_reported_rng_item_and_coin_outputs_are_not_action_producers(self) -> None:
        actions = {
            "actions": [
                {
                    "id": "action:rng-drop-report",
                    "name": "Report an RNG drop",
                    "kind": "activity",
                    "status": "verified",
                    "fact_ids": ["synthetic"],
                    "requirements": {"all": []},
                    "preparation": {"all": []},
                    "completion": {"all": []},
                    "outcomes": [],
                    "repeatable": True,
                    "transition": {
                        "effects": [],
                        "options": [],
                        "reported_effects": [
                            {
                                "type": "rng_item_drop",
                                "item": "rune_axe",
                                "fact_id": "synthetic",
                            },
                            {
                                "type": "variable_activity_output",
                                "resource": "coins",
                                "fact_id": "synthetic",
                            },
                        ],
                    },
                },
                {
                    "id": "action:rng-output-consumer",
                    "name": "Use reported RNG outputs",
                    "kind": "activity",
                    "status": "verified",
                    "fact_ids": ["synthetic"],
                    "requirements": {
                        "all": [
                            {"type": "item_at_least", "key": "rune_axe", "value": 1},
                            {"type": "resource_at_least", "key": "coins", "value": 1000},
                        ]
                    },
                    "preparation": {"all": []},
                    "completion": {"all": []},
                    "outcomes": [],
                    "repeatable": True,
                    "transition": {"effects": [], "options": [], "reported_effects": []},
                },
            ]
        }

        analysis = analyze_dependency_closure(
            actions,
            copy.deepcopy(self.fresh_state),
            "action:rng-output-consumer",
        )

        consumer = self._action_node(analysis, "action:rng-output-consumer")
        rune_axe = self._predicate(consumer, "requirements", "item_at_least", "rune_axe")
        coins = self._predicate(consumer, "requirements", "resource_at_least", "coins")
        self.assertEqual([], rune_axe["producer_actions"])
        self.assertEqual([], coins["producer_actions"])
        self.assertTrue(any(entry["predicate"] == rune_axe["predicate"] for entry in analysis["external_inputs"]))
        self.assertTrue(any(entry["predicate"] == coins["predicate"] for entry in analysis["external_inputs"]))
        self.assertNotIn("action:rng-drop-report", [node["action_id"] for node in analysis["closure"]["actions"]])

    def test_deterministic_purchase_can_produce_item_while_rng_currency_remains_external(self) -> None:
        def action(action_id: str, requirements: dict, effects: list[dict], reports: list[dict]) -> dict:
            return {
                "id": action_id,
                "name": action_id,
                "kind": "activity",
                "status": "verified",
                "fact_ids": ["synthetic"],
                "requirements": requirements,
                "preparation": {"all": []},
                "completion": {"all": []},
                "outcomes": [],
                "repeatable": True,
                "transition": {"effects": effects, "options": [], "reported_effects": reports},
            }

        actions = {
            "actions": [
                action(
                    "action:rewards-guardian-search",
                    {"all": []},
                    [],
                    [{"type": "variable_activity_output", "fact_id": "synthetic"}],
                ),
                action(
                    "action:pearl-purchase",
                    {"all": [{"type": "resource_at_least", "key": "abyssal_pearls", "value": 750}]},
                    [{"op": "ensure_min", "state": "items", "key": "abyssal_needle", "value": 1, "fact_id": "synthetic"}],
                    [],
                ),
                action(
                    "action:colossal-pouch",
                    {"all": [{"type": "item_at_least", "key": "abyssal_needle", "value": 1}]},
                    [],
                    [],
                ),
            ]
        }

        analysis = analyze_dependency_closure(
            actions,
            copy.deepcopy(self.fresh_state),
            "action:colossal-pouch",
        )

        pouch = self._action_node(analysis, "action:colossal-pouch")
        needle = self._predicate(pouch, "requirements", "item_at_least", "abyssal_needle")
        self.assertEqual(["action:pearl-purchase"], needle["producer_actions"])
        purchase = self._action_node(analysis, "action:pearl-purchase")
        pearls = self._predicate(purchase, "requirements", "resource_at_least", "abyssal_pearls")
        self.assertEqual([], pearls["producer_actions"])
        self.assertTrue(any(entry["predicate"] == pearls["predicate"] for entry in analysis["external_inputs"]))
        self.assertNotIn("action:rewards-guardian-search", [node["action_id"] for node in analysis["closure"]["actions"]])

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
