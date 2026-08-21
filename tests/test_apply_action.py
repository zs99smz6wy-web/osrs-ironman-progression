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
from osrs_xp import minimum_xp_for_level  # noqa: E402


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
        self.assertEqual(100, result["next_state"]["counters"]["kudos"])
        self.assertIn("fossil_island", result["next_state"]["transport_flags"])
        self.assertEqual([], result["reported_effects"])

    def test_pandemonium_unlocks_sailing_with_only_fixed_rewards(self) -> None:
        result = apply_action(self.actions_document, self.state, "action:pandemonium")

        self.assertEqual("applied", result["status"])
        self.assertIn("Pandemonium", result["next_state"]["quests_completed"])
        self.assertIn("sailing_access", result["next_state"]["milestones"])
        self.assertEqual(1, result["next_state"]["items"]["sailing_raft"])
        self.assertEqual(1, result["next_state"]["items"]["captains_log"])
        self.assertEqual(25, result["next_state"]["items"]["sawmill_coupon"])
        self.assertEqual(300, result["next_state"]["skill_xp"]["Sailing"])
        self.assertEqual([], result["reported_effects"])

    def test_skiff_spends_its_verified_purchase_cost(self) -> None:
        self.state["quests_completed"].append("Pandemonium")
        self.state["resources"]["coins"] = 15000
        self.state["skill_xp"]["Sailing"] = minimum_xp_for_level(15)
        self.state["skills"]["Sailing"] = 15

        result = apply_action(self.actions_document, self.state, "action:buy-sailing-skiff")

        self.assertEqual("applied", result["status"])
        self.assertEqual(0, result["next_state"]["resources"]["coins"])
        self.assertEqual(1, result["next_state"]["items"]["sailing_skiff"])

    def test_fallen_from_grace_applies_official_xp_and_unlocks_without_item_rewards(self) -> None:
        self.state["transport_flags"].append("wyrmscraig")
        for skill, level in (("Sailing", 62), ("Crafting", 60), ("Runecraft", 47), ("Mining", 53)):
            self.state["skill_xp"][skill] = minimum_xp_for_level(level)
            self.state["skills"][skill] = level

        result = apply_action(self.actions_document, self.state, "action:fallen-from-grace")

        self.assertEqual("applied", result["status"])
        self.assertEqual(minimum_xp_for_level(62) + 12500, result["next_state"]["skill_xp"]["Sailing"])
        self.assertEqual(minimum_xp_for_level(60) + 10000, result["next_state"]["skill_xp"]["Crafting"])
        self.assertIn("sunstone_golem_crafting_access", result["next_state"]["milestones"])
        self.assertIn("wyrmscraig_slayer_ring_teleport", result["next_state"]["transport_flags"])
        self.assertNotIn("jewellers_chisel", result["next_state"]["items"])

    def test_sunstone_golem_crafting_reports_variable_outputs_without_claiming_chisel(self) -> None:
        self.state["quests_completed"].append("Fallen From Grace")
        self.state["skill_xp"]["Crafting"] = minimum_xp_for_level(60)
        self.state["skills"]["Crafting"] = 60
        self.state["items"] = {"hammer": 1, "chisel": 1, "sunstone": 1, "hunter_fur": 1}

        result = apply_action(self.actions_document, self.state, "action:sunstone-golem-crafting")

        self.assertEqual("applied", result["status"])
        self.assertEqual(self.state["items"], result["next_state"]["items"])
        self.assertNotIn("jewellers_chisel", result["next_state"]["items"])
        self.assertEqual("variable_activity_output", result["reported_effects"][0]["type"])

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
        self.assertTrue(result["next_state"]["passive_loops"]["kingdom"])
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

    def test_giant_seaweed_setup_consumes_two_spores_and_keeps_diving_gear(self) -> None:
        state = load_json(REPOSITORY_ROOT / "tests" / "fixtures" / "passive-loops-ready.json")

        result = apply_action(self.actions_document, state, "action:giant-seaweed-loop")

        self.assertEqual("applied", result["status"])
        self.assertTrue(result["next_state"]["passive_loops"]["seaweed"])
        self.assertEqual(0, result["next_state"]["items"]["seaweed_spore"])
        self.assertEqual(1, result["next_state"]["items"]["fishbowl_helmet"])
        self.assertEqual(1, result["next_state"]["items"]["diving_apparatus"])
        self.assertEqual("variable_activity_output", result["reported_effects"][0]["type"])

    def test_confirmed_recurring_collection_requires_ready_and_clears_observation(self) -> None:
        collection = action(
            "action:collect-birdhouses",
            requirements={"all": [{"type": "recurring_state", "key": "birdhouses", "value": "ready"}]},
            completion={"all": []},
            effects=[{"op": "clear_observation", "state": "recurring_observations", "key": "birdhouses"}],
            reported_effects=[{"type": "variable_activity_output", "description": "Player reports actual loot."}],
            repeatable=True,
        )

        blocked = apply_action(document(collection), self.state, collection["id"])
        self.assertEqual("not_eligible", blocked["status"])

        self.state["recurring_observations"]["birdhouses"] = {
            "state": "ready",
            "observed_at": "2026-08-21T09:30:00-07:00",
            "ready_at": "2026-08-21T09:30:00-07:00",
        }
        applied = apply_action(document(collection), self.state, collection["id"])
        self.assertEqual("applied", applied["status"])
        self.assertNotIn("birdhouses", applied["next_state"]["recurring_observations"])
        self.assertIn("birdhouses", self.state["recurring_observations"])

    def test_normalized_recurring_actions_never_invent_variable_outputs(self) -> None:
        state = load_json(REPOSITORY_ROOT / "tests" / "fixtures" / "passive-loops-ready.json")
        state["passive_loops"]["birdhouses"] = True
        state["recurring_observations"]["birdhouses"] = {
            "state": "ready",
            "observed_at": "2026-08-21T09:30:00-07:00",
            "ready_at": "2026-08-21T09:30:00-07:00",
        }
        birdhouses = apply_action(self.actions_document, state, "action:collect-reset-birdhouses")
        self.assertEqual("applied", birdhouses["status"])
        self.assertEqual(0, birdhouses["next_state"]["items"]["logs"])
        self.assertEqual(0, birdhouses["next_state"]["items"]["low_level_birdhouse_seed"])
        self.assertNotIn("birdhouses", birdhouses["next_state"]["recurring_observations"])

        state["passive_loops"]["seaweed"] = True
        state["recurring_observations"]["seaweed"] = {
            "state": "ready",
            "observed_at": "2026-08-21T09:30:00-07:00",
            "ready_at": "2026-08-21T09:30:00-07:00",
        }
        seaweed = apply_action(self.actions_document, state, "action:harvest-replant-giant-seaweed")
        self.assertEqual("applied", seaweed["status"])
        self.assertEqual(0, seaweed["next_state"]["items"]["seaweed_spore"])
        self.assertNotIn("giant_seaweed", seaweed["next_state"]["items"])
        self.assertNotIn("seaweed", seaweed["next_state"]["recurring_observations"])

        for loop_key, action_id in (
            ("tears_of_guthix", "action:complete-tears-of-guthix-session"),
            ("kingdom", "action:collect-kingdom-resources"),
        ):
            observed = load_json(FRESH_ACCOUNT)
            observed["passive_loops"][loop_key] = True
            observed["recurring_observations"][loop_key] = {
                "state": "ready",
                "observed_at": "2026-08-21T09:30:00-07:00",
                "ready_at": "2026-08-21T09:30:00-07:00",
            }
            result = apply_action(self.actions_document, observed, action_id)
            self.assertEqual("applied", result["status"])
            self.assertNotIn(loop_key, result["next_state"]["recurring_observations"])
            self.assertEqual(observed["items"], result["next_state"]["items"])
            self.assertEqual(observed["skill_xp"], result["next_state"]["skill_xp"])
            self.assertEqual("variable_activity_output", result["reported_effects"][0]["type"])

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

    def test_enter_the_abyss_and_temple_of_the_eye_apply_verified_runecraft_xp(self) -> None:
        self.state["quests_completed"].append("Rune Mysteries")
        self.state["skill_xp"]["Runecraft"] = minimum_xp_for_level(10)
        self.state["skills"]["Runecraft"] = 10

        abyss = apply_action(self.actions_document, self.state, "action:enter-the-abyss")
        temple = apply_action(self.actions_document, abyss["next_state"], "action:temple-of-the-eye")

        self.assertEqual("applied", temple["status"])
        self.assertEqual(minimum_xp_for_level(10) + 1000 + 9210, temple["next_state"]["skill_xp"]["Runecraft"])
        self.assertIn("Temple of the Eye", temple["next_state"]["quests_completed"])
        self.assertIn("guardians_of_the_rift_access", temple["next_state"]["milestones"])
        self.assertEqual(1, temple["next_state"]["items"]["medium_pouch"])

    def test_guardians_of_the_rift_reports_variable_rewards_without_adding_pearls(self) -> None:
        self.state["quests_completed"].append("Temple of the Eye")
        self.state["skill_xp"]["Runecraft"] = minimum_xp_for_level(27)
        self.state["skills"]["Runecraft"] = 27
        self.state["items"] = {"pickaxe": 1}

        result = apply_action(self.actions_document, self.state, "action:guardians-of-the-rift")

        self.assertEqual("applied", result["status"])
        self.assertNotIn("abyssal_pearls", result["next_state"]["resources"])
        self.assertEqual("variable_activity_output", result["reported_effects"][0]["type"])

    def test_raiments_purchase_requires_and_spends_abyssal_pearls(self) -> None:
        self.state["quests_completed"].append("Temple of the Eye")
        self.state["resources"]["abyssal_pearls"] = 1349

        blocked = apply_action(self.actions_document, self.state, "action:buy-full-raiments-of-the-eye")
        self.assertEqual("not_eligible", blocked["status"])
        self.assertEqual(1349, blocked["next_state"]["resources"]["abyssal_pearls"])

        self.state["resources"]["abyssal_pearls"] = 1350
        result = apply_action(self.actions_document, self.state, "action:buy-full-raiments-of-the-eye")

        self.assertEqual("applied", result["status"])
        self.assertEqual(0, result["next_state"]["resources"]["abyssal_pearls"])
        for item in ("hat_of_the_eye", "robe_top_of_the_eye", "robe_bottoms_of_the_eye", "boots_of_the_eye"):
            self.assertEqual(1, result["next_state"]["items"][item])

    def test_colossal_pouch_requires_skills_and_consumes_component_pouches(self) -> None:
        self.state["skill_xp"]["Runecraft"] = minimum_xp_for_level(25)
        self.state["skills"]["Runecraft"] = 25
        self.state["skill_xp"]["Crafting"] = minimum_xp_for_level(55)
        self.state["skills"]["Crafting"] = 55
        self.state["items"] = {
            "abyssal_needle": 1,
            "small_pouch": 1,
            "medium_pouch": 1,
            "large_pouch": 1,
            "giant_pouch": 1,
        }

        blocked = apply_action(self.actions_document, self.state, "action:create-colossal-pouch")
        self.assertEqual("not_eligible", blocked["status"])
        self.assertEqual(1, blocked["next_state"]["items"]["abyssal_needle"])

        self.state["skill_xp"]["Crafting"] = minimum_xp_for_level(56)
        self.state["skills"]["Crafting"] = 56
        result = apply_action(self.actions_document, self.state, "action:create-colossal-pouch")

        self.assertEqual("applied", result["status"])
        self.assertEqual(1, result["next_state"]["items"]["colossal_pouch"])
        for item in ("abyssal_needle", "small_pouch", "medium_pouch", "large_pouch", "giant_pouch"):
            self.assertEqual(0, result["next_state"]["items"][item])

    def test_sleeping_giants_fixed_xp_unlocks_foundry_without_granting_reputation(self) -> None:
        self.state["skill_xp"]["Smithing"] = minimum_xp_for_level(15)
        self.state["skills"]["Smithing"] = 15

        quest = apply_action(self.actions_document, self.state, "action:sleeping-giants")
        foundry_state = quest["next_state"]
        foundry_state["items"] = {"bucket": 1}
        foundry_state["resources"]["foundry_metal_value_bars"] = 2
        activity = apply_action(self.actions_document, foundry_state, "action:giants-foundry")

        self.assertEqual("applied", quest["status"])
        self.assertEqual(minimum_xp_for_level(15) + 6000, quest["next_state"]["skill_xp"]["Smithing"])
        self.assertIn("giants_foundry_access", quest["next_state"]["milestones"])
        self.assertEqual("applied", activity["status"])
        self.assertNotIn("foundry_reputation", activity["next_state"]["resources"])

    def test_motherlode_upgrades_require_nuggets_and_upper_level_for_super_hopper(self) -> None:
        self.state["skill_xp"]["Mining"] = minimum_xp_for_level(57)
        self.state["skills"]["Mining"] = 57
        self.state["resources"]["golden_nuggets"] = 100

        upper = apply_action(self.actions_document, self.state, "action:unlock-motherlode-upper-level")
        blocked_hopper = apply_action(self.actions_document, upper["next_state"], "action:buy-motherlode-super-hopper")

        self.assertEqual("applied", upper["status"])
        self.assertEqual(0, upper["next_state"]["resources"]["golden_nuggets"])
        self.assertEqual("not_eligible", blocked_hopper["status"])

        hopper_state = upper["next_state"]
        hopper_state["resources"]["golden_nuggets"] = 50
        hopper = apply_action(self.actions_document, hopper_state, "action:buy-motherlode-super-hopper")

        self.assertEqual("applied", hopper["status"])
        self.assertEqual(0, hopper["next_state"]["resources"]["golden_nuggets"])
        self.assertIn("motherlode_super_hopper", hopper["next_state"]["milestones"])

    def test_motherlode_mine_does_not_guarantee_golden_nuggets(self) -> None:
        self.state["skill_xp"]["Mining"] = minimum_xp_for_level(30)
        self.state["skills"]["Mining"] = 30

        result = apply_action(self.actions_document, self.state, "action:motherlode-mine")

        self.assertEqual("applied", result["status"])
        self.assertNotIn("golden_nuggets", result["next_state"]["resources"])
        self.assertEqual("variable_activity_output", result["reported_effects"][0]["type"])

    def test_tithe_and_foundry_purchases_spend_their_accumulated_currencies(self) -> None:
        self.state["skill_xp"]["Farming"] = minimum_xp_for_level(34)
        self.state["skills"]["Farming"] = 34
        self.state["resources"]["tithe_farm_points"] = 50

        auto_weed = apply_action(self.actions_document, self.state, "action:buy-auto-weed")

        self.assertEqual("applied", auto_weed["status"])
        self.assertEqual(0, auto_weed["next_state"]["resources"]["tithe_farm_points"])
        self.assertIn("auto_weed", auto_weed["next_state"]["milestones"])

        foundry_state = load_json(FRESH_ACCOUNT)
        foundry_state["quests_completed"] = ["Sleeping Giants", "Dwarf Cannon"]
        foundry_state["resources"]["foundry_reputation"] = 2000
        mould = apply_action(self.actions_document, foundry_state, "action:buy-double-ammo-mould")

        self.assertEqual("applied", mould["status"])
        self.assertEqual(0, mould["next_state"]["resources"]["foundry_reputation"])
        self.assertEqual(1, mould["next_state"]["items"]["double_ammo_mould"])

    def test_tempoross_does_not_guarantee_a_fish_barrel(self) -> None:
        self.state["skill_xp"]["Fishing"] = minimum_xp_for_level(35)
        self.state["skills"]["Fishing"] = 35

        result = apply_action(self.actions_document, self.state, "action:tempoross")

        self.assertEqual("applied", result["status"])
        self.assertNotIn("fish_barrel", result["next_state"]["items"])
        self.assertEqual("variable_activity_output", result["reported_effects"][0]["type"])

    def test_new_rng_activities_do_not_invent_items_or_coins(self) -> None:
        rng_action_ids = {
            "action:steal-valuables",
            "action:steal-silk-stalls",
            "action:blackjack-bandits",
            "action:salvage-shipwrecks",
            "action:steal-port-roberts-stalls",
            "action:fight-enchanted-valley-tree-spirits",
            "action:fight-armoured-zombies",
            "action:fight-warped-creatures",
            "action:fight-zamorak-warriors-for-rune-scimitar",
            "action:fight-fire-giants-for-rune-scimitar",
            "action:fight-warriors-guild-cyclopes-for-dragon-defender",
        }
        actions_by_id = {action["id"]: action for action in self.actions_document["actions"]}
        for action_id in rng_action_ids:
            transition = actions_by_id[action_id]["transition"]
            self.assertTrue(actions_by_id[action_id]["repeatable"])
            self.assertEqual([], transition["effects"])
            self.assertEqual("variable_activity_output", transition["reported_effects"][0]["type"])

        self.state["quests_completed"].append("Children of the Sun")
        self.state["skills"]["Thieving"] = 50
        self.state["skill_xp"]["Thieving"] = minimum_xp_for_level(50)
        original_items = copy.deepcopy(self.state["items"])
        original_coins = self.state["resources"]["coins"]

        result = apply_action(self.actions_document, self.state, "action:steal-valuables")

        self.assertEqual("applied", result["status"])
        self.assertEqual(original_items, result["next_state"]["items"])
        self.assertEqual(original_coins, result["next_state"]["resources"]["coins"])
        self.assertEqual("variable_activity_output", result["reported_effects"][0]["type"])

    def test_zombie_axe_repair_is_deterministic(self) -> None:
        self.state["skills"]["Smithing"] = 70
        self.state["skill_xp"]["Smithing"] = minimum_xp_for_level(70)
        self.state["items"]["broken_zombie_axe"] = 1

        result = apply_action(self.actions_document, self.state, "action:repair-zombie-axe")

        self.assertEqual("applied", result["status"])
        self.assertEqual(0, result["next_state"]["items"]["broken_zombie_axe"])
        self.assertEqual(1, result["next_state"]["items"]["zombie_axe"])
        self.assertEqual(minimum_xp_for_level(70) + 500, result["next_state"]["skill_xp"]["Smithing"])
        self.assertEqual([], result["reported_effects"])


if __name__ == "__main__":
    unittest.main()
