"""Focused behavioural coverage for the atomic one-action transition engine."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

from apply_action import apply_action  # noqa: E402
from evaluate_progression import load_json  # noqa: E402


FRESH_ACCOUNT = REPOSITORY_ROOT / "tests" / "fixtures" / "fresh-account.json"
ACTIONS = REPOSITORY_ROOT / "data" / "progression" / "actions.json"


def action(
    action_id: str,
    *,
    requirements: dict | None = None,
    preparation: dict | None = None,
    completion: dict | None = None,
    effects: list[dict] | None = None,
    options: list[dict] | None = None,
    reported_effects: list[dict] | None = None,
    repeatable: bool = False,
) -> dict:
    uses_default_completion = completion is None
    resolved_completion = completion or {
        "all": [{"type": "milestone", "key": f"{action_id}:complete"}]
    }
    resolved_effects = list(effects or [])
    if uses_default_completion and not repeatable:
        resolved_effects.append(
            {"op": "set_add", "state": "milestones", "key": f"{action_id}:complete"}
        )
    return {
        "id": action_id,
        "name": action_id,
        "kind": "test",
        "fact_ids": [],
        "requirements": requirements or {"all": []},
        "preparation": preparation or {"all": []},
        "completion": resolved_completion,
        "repeatable": repeatable,
        "transition": {
            "effects": resolved_effects,
            "options": options or [],
            "reported_effects": reported_effects or [],
        },
    }


def document(*actions: dict) -> dict:
    return {"actions": list(actions)}


class ApplyActionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = load_json(FRESH_ACCOUNT)
        self.actions_document = load_json(ACTIONS)

    def test_current_waterfall_transition_applies_fixed_quest_xp(self) -> None:
        self.state["items"] = {"rope": 1, "air_rune": 6, "earth_rune": 6, "water_rune": 6}

        result = apply_action(self.actions_document, self.state, "action:waterfall-quest")

        self.assertEqual("applied", result["status"])
        self.assertIn("Waterfall Quest", result["next_state"]["quests_completed"])
        self.assertEqual(2, result["next_state"]["items"]["diamond"])
        self.assertEqual(30, result["next_state"]["skills"]["Attack"])
        self.assertEqual(13750, result["next_state"]["skill_xp"]["Attack"])
        self.assertEqual(30, result["next_state"]["skills"]["Strength"])
        self.assertEqual([], result["reported_effects"])

    def test_current_bone_voyage_transition_consumes_verified_items(self) -> None:
        state = load_json(REPOSITORY_ROOT / "tests" / "fixtures" / "fossil-island-ready.json")

        result = apply_action(self.actions_document, state, "action:fossil-island-access")

        self.assertEqual("applied", result["status"])
        self.assertEqual(0, result["next_state"]["items"]["vodka"])
        self.assertEqual(105, result["next_state"]["counters"]["kudos"])
        self.assertIn("fossil_island", result["next_state"]["transport_flags"])

    def test_throne_of_miscellania_unlocks_management_and_seeds_coffer(self) -> None:
        self.state["quests_completed"] = ["Heroes' Quest", "The Fremennik Trials"]
        self.state["resources"]["coins"] = 1875
        self.state["items"] = {
            "iron_bar": 1,
            "common_non_silver_ring": 1,
            "logs": 1,
        }

        result = apply_action(self.actions_document, self.state, "action:throne-of-miscellania")

        self.assertEqual("applied", result["status"])
        self.assertIn("Throne of Miscellania", result["next_state"]["quests_completed"])
        self.assertIn("kingdom_management_unlocked", result["next_state"]["milestones"])
        self.assertIn("ring_of_wealth_miscellania", result["next_state"]["transport_flags"])
        self.assertEqual(10000, result["next_state"]["resources"]["kingdom_coffer_coins"])
        self.assertEqual(0, result["next_state"]["items"]["common_non_silver_ring"])

    def test_royal_trouble_applies_fixed_coins_and_xp(self) -> None:
        self.state["quests_completed"].append("Throne of Miscellania")
        for skill in ("Agility", "Slayer"):
            self.state["skills"][skill] = 40
            self.state["skill_xp"][skill] = 37224

        result = apply_action(self.actions_document, self.state, "action:royal-trouble")

        self.assertEqual("applied", result["status"])
        self.assertEqual(20000, result["next_state"]["resources"]["coins"])
        self.assertEqual(42224, result["next_state"]["skill_xp"]["Agility"])
        self.assertEqual(42224, result["next_state"]["skill_xp"]["Slayer"])
        self.assertEqual(6154, result["next_state"]["skill_xp"]["Hitpoints"])
        self.assertIn("kingdom_management_expanded", result["next_state"]["milestones"])

    def test_current_birdhouse_transition_requires_seed_choice_when_both_are_ready(self) -> None:
        state = load_json(REPOSITORY_ROOT / "tests" / "fixtures" / "passive-loops-ready.json")
        state["items"]["high_level_birdhouse_seed"] = 20

        result = apply_action(self.actions_document, state, "action:birdhouse-loop")

        self.assertEqual("choice_required", result["status"])
        self.assertFalse(result["next_state"]["passive_loops"]["birdhouses"])

    def test_one_time_action_is_atomic_and_does_not_mutate_original(self) -> None:
        quest = action(
            "action:waterfall",
            completion={"all": [{"type": "quest_completed", "key": "Waterfall Quest"}]},
            effects=[
                {"op": "set_add", "state": "quests_completed", "key": "Waterfall Quest"},
                {"op": "ensure_min", "state": "resources", "key": "coins", "value": 10},
                {"op": "gain_xp", "state": "skill_xp", "key": "Attack", "amount": 13750},
            ],
        )
        original = copy.deepcopy(self.state)

        result = apply_action(document(quest), self.state, quest["id"])

        self.assertEqual("applied", result["status"])
        self.assertEqual(original, self.state)
        self.assertIn("Waterfall Quest", result["next_state"]["quests_completed"])
        self.assertIn(quest["id"], result["next_state"]["completed_actions"])
        self.assertEqual(10, result["next_state"]["resources"]["coins"])
        self.assertEqual(13750, result["next_state"]["skill_xp"]["Attack"])
        self.assertEqual(30, result["next_state"]["skills"]["Attack"])

    def test_reapplying_a_completed_one_time_action_returns_already_completed(self) -> None:
        quest = action(
            "action:tree-gnome",
            completion={"all": [{"type": "quest_completed", "key": "Tree Gnome Village"}]},
            effects=[
                {"op": "set_add", "state": "quests_completed", "key": "Tree Gnome Village"},
                {"op": "set_add", "state": "transport_flags", "key": "spirit_trees"},
            ],
        )
        applied = apply_action(document(quest), self.state, quest["id"])

        result = apply_action(document(quest), applied["next_state"], quest["id"])

        self.assertEqual("already_completed", result["status"])
        self.assertEqual(applied["next_state"], result["next_state"])

    def test_factual_completion_with_missing_bookkeeping_or_unlock_is_inconsistent(self) -> None:
        quest = action(
            "action:tree-gnome",
            completion={"all": [{"type": "quest_completed", "key": "Tree Gnome Village"}]},
            effects=[
                {"op": "set_add", "state": "quests_completed", "key": "Tree Gnome Village"},
                {"op": "set_add", "state": "transport_flags", "key": "spirit_trees"},
            ],
        )
        self.state["quests_completed"].append("Tree Gnome Village")
        original = copy.deepcopy(self.state)

        result = apply_action(document(quest), self.state, quest["id"])

        self.assertEqual("state_inconsistent", result["status"])
        self.assertEqual(original, result["next_state"])

    def test_tree_gnome_transport_effect_does_not_duplicate_existing_transport(self) -> None:
        unlock = action(
            "action:tree-gnome-village",
            completion={"all": [{"type": "quest_completed", "key": "Tree Gnome Village"}]},
            effects=[
                {"op": "set_add", "state": "quests_completed", "key": "Tree Gnome Village"},
                {"op": "set_add", "state": "transport_flags", "key": "spirit_trees"},
            ],
        )
        self.state["transport_flags"].append("spirit_trees")

        result = apply_action(document(unlock), self.state, unlock["id"])

        self.assertEqual("applied", result["status"])
        self.assertEqual(1, result["next_state"]["transport_flags"].count("spirit_trees"))

    def test_multiple_viable_options_require_an_explicit_choice(self) -> None:
        setup = action(
            "action:birdhouses",
            options=[
                {
                    "id": "low-seeds",
                    "requires": {"all": [{"type": "item_at_least", "key": "low_seed", "value": 40}]},
                    "effects": [{"op": "delta", "state": "items", "key": "low_seed", "amount": -40}],
                },
                {
                    "id": "high-seeds",
                    "requires": {"all": [{"type": "item_at_least", "key": "high_seed", "value": 20}]},
                    "effects": [{"op": "delta", "state": "items", "key": "high_seed", "amount": -20}],
                },
            ],
        )
        self.state["items"] = {"low_seed": 40, "high_seed": 20}

        result = apply_action(document(setup), self.state, setup["id"])

        self.assertEqual("choice_required", result["status"])
        self.assertEqual(self.state, result["next_state"])

    def test_unavailable_selected_option_is_not_eligible_and_does_not_spend(self) -> None:
        setup = action(
            "action:birdhouses",
            options=[
                {
                    "id": "low-seeds",
                    "requires": {"all": [{"type": "item_at_least", "key": "low_seed", "value": 40}]},
                    "effects": [{"op": "delta", "state": "items", "key": "low_seed", "amount": -40}],
                }
            ],
        )
        self.state["items"] = {"low_seed": 39}

        result = apply_action(document(setup), self.state, setup["id"], "low-seeds")

        self.assertEqual("not_eligible", result["status"])
        self.assertEqual(39, result["next_state"]["items"]["low_seed"])

    def test_underflow_rejects_every_effect_atomically(self) -> None:
        spend = action(
            "action:underflow",
            effects=[
                {"op": "ensure_min", "state": "resources", "key": "coins", "value": 10},
                {"op": "delta", "state": "resources", "key": "coins", "amount": -11},
            ],
        )

        result = apply_action(document(spend), self.state, spend["id"])

        self.assertEqual("not_eligible", result["status"])
        self.assertEqual(0, result["next_state"]["resources"]["coins"])
        self.assertNotIn(spend["id"], result["next_state"]["completed_actions"])

    def test_choice_xp_report_does_not_mutate_a_skill_level(self) -> None:
        quest = action(
            "action:xp-report",
            reported_effects=[{"type": "xp_choice_award", "description": "Choose one skill"}],
        )

        result = apply_action(document(quest), self.state, quest["id"])

        self.assertEqual(1, result["next_state"]["skills"].get("Attack", 1))
        self.assertEqual(quest["transition"]["reported_effects"], result["reported_effects"])

    def test_fixed_xp_caps_at_200m_and_receipt_records_actual_gain(self) -> None:
        self.state["skill_xp"]["Attack"] = 199_999_995
        self.state["skills"]["Attack"] = 99
        quest = action(
            "action:xp-cap",
            effects=[{"op": "gain_xp", "state": "skill_xp", "key": "Attack", "amount": 10}],
        )

        result = apply_action(document(quest), self.state, quest["id"])

        self.assertEqual(200_000_000, result["next_state"]["skill_xp"]["Attack"])
        receipt = next(effect for effect in result["applied_effects"] if effect["op"] == "gain_xp")
        self.assertEqual(5, receipt["amount"])

    def test_repeatable_action_never_records_completion_or_invents_rewards(self) -> None:
        activity = action(
            "action:wintertodt",
            repeatable=True,
            reported_effects=[{"kind": "rng_reward", "source": "Wintertodt"}],
        )

        result = apply_action(document(activity), self.state, activity["id"])

        self.assertEqual("applied", result["status"])
        self.assertNotIn(activity["id"], result["next_state"]["completed_actions"])
        self.assertEqual({}, result["next_state"]["items"])
        self.assertEqual([{"kind": "rng_reward", "source": "Wintertodt"}], result["reported_effects"])

    def test_counter_delta_must_be_positive_but_ensure_min_can_set_a_floor(self) -> None:
        progress = action(
            "action:kudos",
            effects=[
                {"op": "ensure_min", "state": "counters", "key": "kudos", "value": 100},
                {"op": "delta", "state": "counters", "key": "kudos", "amount": 5},
            ],
        )

        result = apply_action(document(progress), self.state, progress["id"])

        self.assertEqual("applied", result["status"])
        self.assertEqual(105, result["next_state"]["counters"]["kudos"])
        invalid = action("action:invalid-counter", effects=[{"op": "delta", "state": "counters", "key": "kudos", "amount": 0}])
        with self.assertRaisesRegex(ValueError, "counter deltas must be positive"):
            apply_action(document(invalid), self.state, invalid["id"])

    def test_only_evaluator_eligible_actions_can_apply(self) -> None:
        blocked = action(
            "action:blocked",
            requirements={"all": [{"type": "skill_at_least", "key": "Agility", "value": 25}]},
            effects=[{"op": "ensure_min", "state": "resources", "key": "coins", "value": 100}],
        )

        result = apply_action(document(blocked), self.state, blocked["id"])

        self.assertEqual("not_eligible", result["status"])
        self.assertEqual(0, result["next_state"]["resources"]["coins"])


if __name__ == "__main__":
    unittest.main()
