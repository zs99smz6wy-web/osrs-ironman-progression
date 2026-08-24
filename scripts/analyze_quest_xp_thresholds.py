from __future__ import annotations

import argparse
import copy
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from evaluate_progression import (
    DEFAULT_ACTIONS,
    DEFAULT_STATE,
    evaluate_actions,
    evaluate_condition,
    load_json,
    validate_account_state,
)
from osrs_xp import MAX_XP, level_from_xp, minimum_xp_for_level


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESEARCH = ROOT / "research" / "quest-xp-threshold-sequencing.json"
DEFAULT_CONTEXT = ROOT / "strategy" / "quest-xp-threshold-contexts.json"


def _predicates(condition: dict[str, Any]) -> Iterable[dict[str, Any]]:
    if "all" in condition or "any" in condition:
        key = "all" if "all" in condition else "any"
        for child in condition[key]:
            yield from _predicates(child)
        return
    yield condition


def _fixed_xp(action: dict[str, Any]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for effect in action["transition"]["effects"]:
        if effect["op"] == "gain_xp" and effect["state"] == "skill_xp":
            totals[effect["key"]] += effect["amount"]
    return dict(totals)


def _completed_quest(action: dict[str, Any]) -> str | None:
    completed = [
        effect["key"]
        for effect in action["transition"]["effects"]
        if effect["op"] == "set_add" and effect["state"] == "quests_completed"
    ]
    return completed[0] if len(completed) == 1 else None


def _quest_requirements(action: dict[str, Any]) -> list[str]:
    return [
        predicate["key"]
        for predicate in _predicates(action["requirements"])
        if predicate["type"] == "quest_completed"
    ]


def _consumed_item_effects(action: dict[str, Any]) -> list[dict[str, Any]]:
    consumed: list[dict[str, Any]] = []
    for effect in action["transition"]["effects"]:
        if effect["op"] == "delta" and effect["state"] == "items" and effect["amount"] < 0:
            consumed.append({"item_id": effect["key"], "quantity": -effect["amount"], "path": "base_transition"})
    for option in action["transition"]["options"]:
        for effect in option["effects"]:
            if effect["op"] == "delta" and effect["state"] == "items" and effect["amount"] < 0:
                consumed.append(
                    {"item_id": effect["key"], "quantity": -effect["amount"], "path": f"option:{option['id']}"}
                )
    return consumed


def _unsatisfied_predicates(condition: dict[str, Any], account_state: dict[str, Any]) -> list[dict[str, Any]]:
    if "all" in condition:
        return [
            predicate
            for child in condition["all"]
            for predicate in _unsatisfied_predicates(child, account_state)
        ]
    if "any" in condition:
        alternatives = [_unsatisfied_predicates(child, account_state) for child in condition["any"]]
        return [] if any(not alternative for alternative in alternatives) else [
            predicate for alternative in alternatives for predicate in alternative
        ]
    satisfied, _ = evaluate_condition(condition, account_state)
    return [] if satisfied else [copy.deepcopy(condition)]


def _blocker_inventory(action: dict[str, Any], account_state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    consumed = _consumed_item_effects(action)
    consumed_keys = {effect["item_id"] for effect in consumed}
    inventory: dict[str, list[dict[str, Any]]] = {
        "hard_skill_gates": [],
        "preparation_skill_inputs": [],
        "prerequisite_quests": [],
        "required_item_inputs": [],
        "consumed_item_inputs": consumed,
        "reusable_or_equipment_inputs": [],
        "other_hard_requirements": [],
        "other_preparation": [],
        "missing_hard_predicates": _unsatisfied_predicates(action["requirements"], account_state),
        "missing_preparation_predicates": _unsatisfied_predicates(action["preparation"], account_state),
    }
    for scope, condition in (("hard_requirement", action["requirements"]), ("preparation", action["preparation"])):
        for predicate in _predicates(condition):
            predicate_copy = copy.deepcopy(predicate)
            predicate_copy["scope"] = scope
            if predicate["type"] == "skill_at_least":
                current_level = level_from_xp(account_state["skill_xp"][predicate["key"]])
                skill_input = {
                    **predicate_copy,
                    "current_level": current_level,
                    "satisfied": current_level >= predicate["value"],
                }
                inventory["hard_skill_gates" if scope == "hard_requirement" else "preparation_skill_inputs"].append(
                    skill_input
                )
            elif predicate["type"] == "quest_completed":
                inventory["prerequisite_quests"].append(
                    {
                        **predicate_copy,
                        "satisfied": predicate["key"] in account_state["quests_completed"],
                    }
                )
            elif predicate["type"] == "item_at_least":
                item = {
                    **predicate_copy,
                    "current_quantity": account_state["items"].get(predicate["key"], 0),
                    "satisfied": account_state["items"].get(predicate["key"], 0) >= predicate["value"],
                    "input_role": "consumed_input" if predicate["key"] in consumed_keys else "reusable_or_equipment_or_unmodeled_consumption_input",
                }
                inventory["required_item_inputs"].append(item)
                if item["input_role"] == "reusable_or_equipment_or_unmodeled_consumption_input":
                    inventory["reusable_or_equipment_inputs"].append(item)
            elif scope == "hard_requirement":
                inventory["other_hard_requirements"].append(predicate_copy)
            else:
                inventory["other_preparation"].append(predicate_copy)
    return inventory


def _timing_status(result: dict[str, Any], blockers: dict[str, list[dict[str, Any]]]) -> tuple[str, list[str]]:
    if result["status"] == "completed":
        return "completed", []
    statuses: list[str] = []
    if any(not quest["satisfied"] for quest in blockers["prerequisite_quests"]):
        statuses.append("finish_quest_chain")
    if any(
        not skill["satisfied"]
        for skill in blockers["hard_skill_gates"] + blockers["preparation_skill_inputs"]
    ):
        statuses.append("train_requirement")
    missing_inputs_or_other_preparation = any(
        predicate["type"] not in {"quest_completed", "skill_at_least"}
        for predicate in blockers["missing_hard_predicates"] + blockers["missing_preparation_predicates"]
    )
    if missing_inputs_or_other_preparation:
        statuses.append("gather_inputs")
    if not statuses:
        statuses.append("do_now")
    primary_order = ("finish_quest_chain", "train_requirement", "gather_inputs", "do_now")
    return next(status for status in primary_order if status in statuses), statuses


def _quest_closure(action: dict[str, Any], actions_by_quest: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    closure: list[dict[str, Any]] = []
    visited: set[str] = set()

    def visit(quest_name: str) -> None:
        if quest_name in visited:
            return
        visited.add(quest_name)
        prerequisite = actions_by_quest.get(quest_name)
        if prerequisite is None:
            closure.append({"quest_name": quest_name, "modeled_action_id": None, "modeled": False})
            return
        for nested in _quest_requirements(prerequisite):
            visit(nested)
        closure.append(
            {
                "quest_name": quest_name,
                "modeled_action_id": prerequisite["id"],
                "modeled": True,
                "hard_requirements": copy.deepcopy(prerequisite["requirements"]),
                "preparation": copy.deepcopy(prerequisite["preparation"]),
            }
        )

    for quest_name in _quest_requirements(action):
        visit(quest_name)
    return closure


def _thresholds_by_skill(context: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    thresholds: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for threshold in context["thresholds"]:
        thresholds[threshold["skill"]].append(copy.deepcopy(threshold))
    for skill in thresholds:
        thresholds[skill].sort(key=lambda item: item["level"])
    return thresholds


def _threshold_report(skill: str, current_xp: int, fixed_xp: int, thresholds: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    current_level = level_from_xp(current_xp)
    resulting_xp = min(MAX_XP, current_xp + fixed_xp)
    resulting_level = level_from_xp(resulting_xp)
    candidates = thresholds.get(skill, [])
    crossed = [
        {**threshold, "xp_threshold": minimum_xp_for_level(threshold["level"])}
        for threshold in candidates
        if current_level < threshold["level"] <= resulting_level
    ]
    next_before = next((threshold for threshold in candidates if threshold["level"] > current_level), None)
    next_after = next((threshold for threshold in candidates if threshold["level"] > resulting_level), None)

    def decorate(threshold: dict[str, Any] | None, xp: int) -> dict[str, Any] | None:
        if threshold is None:
            return None
        return {
            **threshold,
            "xp_threshold": minimum_xp_for_level(threshold["level"]),
            "xp_remaining": max(0, minimum_xp_for_level(threshold["level"]) - xp),
        }

    return {
        "skill": skill,
        "current_xp": current_xp,
        "current_level": current_level,
        "fixed_xp": fixed_xp,
        "resulting_xp": resulting_xp,
        "resulting_level": resulting_level,
        "levels_skipped": resulting_level - current_level,
        "next_meaningful_modeled_threshold_before": decorate(next_before, current_xp),
        "thresholds_crossed": crossed,
        "next_meaningful_modeled_threshold_after": decorate(next_after, resulting_xp),
    }


def _chosen_xp_rewards(actions: list[dict[str, Any]], action_results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rewards: list[dict[str, Any]] = []
    for action in actions:
        for effect in action["transition"]["reported_effects"]:
            if effect["type"] == "xp_choice_award":
                rewards.append(
                    {
                        "action_id": action["id"],
                        "action_name": action["name"],
                        "status": action_results[action["id"]]["status"],
                        "description": effect["description"],
                        "fact_id": effect["fact_id"],
                        "allocated_skill": None,
                        "allocated_xp": None,
                    }
                )
    return rewards


def analyze_quest_xp_thresholds(
    account_state: dict[str, Any],
    actions_document: dict[str, Any],
    research_package: dict[str, Any],
    strategy_context: dict[str, Any],
) -> dict[str, Any]:
    """Report bounded fixed quest XP timing data without selecting or applying an action."""
    validate_account_state(account_state)
    actions = actions_document["actions"]
    action_by_id = {action["id"]: action for action in actions}
    action_results = {result["id"]: result for result in evaluate_actions(actions_document, account_state)}
    actions_by_quest = {
        quest_name: action
        for action in actions
        if action["kind"] == "quest" and (quest_name := _completed_quest(action)) is not None
    }
    thresholds = _thresholds_by_skill(strategy_context)
    timing_windows: list[dict[str, Any]] = []

    for entry in research_package["bounded_fixed_xp_actions"]:
        action = action_by_id[entry["action_id"]]
        fixed_xp = _fixed_xp(action)
        if action["kind"] != "quest" or action["repeatable"] or not fixed_xp:
            raise ValueError(f"{action['id']} is not a non-repeatable quest with fixed skill XP")
        result = action_results[action["id"]]
        blockers = _blocker_inventory(action, account_state)
        primary_timing_status, timing_statuses = _timing_status(result, blockers)
        timing_windows.append(
            {
                "action_id": action["id"],
                "quest_name": _completed_quest(action) or action["name"],
                "fact_ids": copy.deepcopy(entry["fact_ids"]),
                "status": result["status"],
                "primary_timing_status": primary_timing_status,
                "timing_statuses": timing_statuses,
                "hard_requirements": copy.deepcopy(action["requirements"]),
                "missing_hard_requirements": copy.deepcopy(result["missing"]),
                "missing_hard_predicates": blockers["missing_hard_predicates"],
                "hard_skill_gates": blockers["hard_skill_gates"],
                "preparation_skill_inputs": blockers["preparation_skill_inputs"],
                "immediate_quest_prerequisites": _quest_requirements(action),
                "prerequisite_quest_statuses": blockers["prerequisite_quests"],
                "modeled_prerequisite_quest_closure": _quest_closure(action, actions_by_quest),
                "preparation": copy.deepcopy(action["preparation"]),
                "missing_preparation": copy.deepcopy(result["missing_preparation"]),
                "missing_preparation_predicates": blockers["missing_preparation_predicates"],
                "required_item_inputs": blockers["required_item_inputs"],
                "consumed_item_inputs": blockers["consumed_item_inputs"],
                "reusable_or_equipment_inputs": blockers["reusable_or_equipment_inputs"],
                "other_hard_requirements": blockers["other_hard_requirements"],
                "other_preparation": blockers["other_preparation"],
                "skill_effects": [
                    _threshold_report(skill, account_state["skill_xp"][skill], xp, thresholds)
                    for skill, xp in sorted(fixed_xp.items())
                ],
            }
        )

    return {
        "package_id": research_package["package_id"],
        "quest_xp_timing_windows": timing_windows,
        "unallocated_player_chosen_xp_rewards": _chosen_xp_rewards(actions, action_results),
        "quest_selected": False,
        "route_selected": False,
        "account_state_mutated": False,
        "player_chosen_xp_allocated": False,
        "training_method_selected": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report bounded quest-XP threshold timing inputs.")
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument("--research", default=DEFAULT_RESEARCH, type=Path)
    parser.add_argument("--context", default=DEFAULT_CONTEXT, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()
    result = analyze_quest_xp_thresholds(
        load_json(args.state), load_json(args.actions), load_json(args.research), load_json(args.context)
    )
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    for quest in result["quest_xp_timing_windows"]:
        print(f"[{quest['primary_timing_status'].upper()}] {quest['quest_name']}")
        for effect in quest["skill_effects"]:
            print(
                f"  {effect['skill']}: level {effect['current_level']} + {effect['fixed_xp']} XP -> "
                f"level {effect['resulting_level']} (levels skipped: {effect['levels_skipped']})"
            )
    print("Player-chosen XP allocated: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
