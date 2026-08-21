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

    def test_current_waterfall_transition_applies_only_declared_effects(self) -> None:
        self.state["items"] = {"rope": 1, "air_rune": 6, "earth_rune": 6, "water_rune": 6}

        result = apply_action(self.actions_document, self.state, "action:waterfall-quest")

        self.assertEqual("applied", result["status"])
        self.assertIn("Waterfall Quest", result["next_state"]["quests_completed"])
        self.assertEqual(2, result["next_state"]["items"]["diamond"])
        self.assertEqual(1, result["next_state"]["skills"].get("Attack", 1))
        self.assertEqual(13750, result["reported_effects"][0]["amount"])

    def test_current_bone_voyage_transition_consumes_verified_items(self) -> None:
        state = load_json(REPOSITORY_ROOT / "tests" / "fixtures" / "fossil-island-ready.json")

        result = apply_action(self.actions_document, state, "action:fossil-island-access")

        self.assertEqual("applied", result["status"])
        self.assertEqual(0, result["next_state"]["items"]["vodka"])
        self.assertEqual(105, result["next_state"]["counters"]["kudos"])
        self.assertIn("fossil_island", result["next_state"]["transport_flags"])

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
            ],
            reported_effects=[{"kind": "xp_award", "skill": "Attack", "amount": 13750}],
        )
        original = copy.deepcopy(self.state)

        result = apply_action(document(quest), self.state, quest["id"])

        self.assertEqual("applied", result["status"])
        self.assertEqual(original, self.state)
        self.assertIn("Waterfall Quest", result["next_state"]["quests_completed"])
        self.assertIn(quest["id"], result["next_state"]["completed_actions"])
        self.assertEqual(10, result["next_state"]["resources"]["coins"])

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

    def test_reported_xp_does_not_mutate_a_skill_level(self) -> None:
        quest = action(
            "action:xp-report",
            reported_effects=[{"kind": "xp_award", "skill": "Attack", "amount": 13750}],
        )

        result = apply_action(document(quest), self.state, quest["id"])

        self.assertEqual(1, result["next_state"]["skills"].get("Attack", 1))
        self.assertEqual(quest["transition"]["reported_effects"], result["reported_effects"])

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
