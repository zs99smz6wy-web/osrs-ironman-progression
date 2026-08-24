from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from evaluate_progression import (
    DEFAULT_ACTIONS,
    DEFAULT_STATE,
    evaluate_actions,
    load_json,
    validate_account_state,
)
from osrs_xp import MAX_XP, level_from_xp, minimum_xp_for_level


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NODES = ROOT / "graph" / "nodes.json"
DEFAULT_EDGES = ROOT / "graph" / "edges.json"


def _condition_predicates(condition: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield every leaf predicate without assigning a preferred alternative path."""
    if "all" in condition:
        for child in condition["all"]:
            yield from _condition_predicates(child)
        return
    if "any" in condition:
        for child in condition["any"]:
            yield from _condition_predicates(child)
        return
    yield condition


def _quest_completion_keys(action: dict[str, Any]) -> list[str]:
    return [
        effect["key"]
        for effect in action["transition"]["effects"]
        if effect["op"] == "set_add" and effect["state"] == "quests_completed"
    ]


def _fixed_xp_by_skill(action: dict[str, Any]) -> dict[str, int]:
    awards: dict[str, int] = defaultdict(int)
    for effect in action["transition"]["effects"]:
        if effect["op"] == "gain_xp" and effect["state"] == "skill_xp":
            awards[effect["key"]] += effect["amount"]
    return dict(awards)


def _skill_requirement_index(actions: list[dict[str, Any]]) -> dict[str, dict[int, list[dict[str, str]]]]:
    """Index modeled skill gates without treating alternatives as selected actions."""
    requirements: dict[str, dict[int, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for action in actions:
        for scope, condition in (
            ("hard_requirement", action["requirements"]),
            ("preparation", action["preparation"]),
        ):
            for predicate in _condition_predicates(condition):
                if predicate["type"] != "skill_at_least":
                    continue
                requirements[predicate["key"]][predicate["value"]].append(
                    {"action_id": action["id"], "action_name": action["name"], "scope": scope}
                )
    return requirements


def _next_requirement(
    skill: str,
    current_level: int,
    current_xp: int,
    requirement_index: dict[str, dict[int, list[dict[str, str]]]],
) -> dict[str, Any] | None:
    levels = sorted(level for level in requirement_index.get(skill, {}) if level > current_level)
    if not levels:
        return None
    level = levels[0]
    xp_threshold = minimum_xp_for_level(level)
    return {
        "level": level,
        "xp_threshold": xp_threshold,
        "xp_remaining": max(0, xp_threshold - current_xp),
        "action_references": sorted(
            requirement_index[skill][level],
            key=lambda reference: (reference["action_id"], reference["scope"]),
        ),
    }


def _crossed_requirements(
    skill: str,
    before_level: int,
    after_level: int,
    requirement_index: dict[str, dict[int, list[dict[str, str]]]],
) -> list[dict[str, Any]]:
    return [
        {
            "level": level,
            "action_references": sorted(
                requirement_index[skill][level],
                key=lambda reference: (reference["action_id"], reference["scope"]),
            ),
        }
        for level in sorted(requirement_index.get(skill, {}))
        if before_level < level <= after_level
    ]


def _quest_node_ids(quest_keys: list[str], nodes_document: dict[str, Any]) -> list[str]:
    wanted_labels = {f"{quest_key} completed" for quest_key in quest_keys}
    return sorted(
        node["id"]
        for node in nodes_document["nodes"]
        if node["id"].startswith("quest:") and node.get("label") in wanted_labels
    )


def _downstream_references(
    quest_keys: list[str], nodes_document: dict[str, Any], edges_document: dict[str, Any]
) -> list[dict[str, str]]:
    quest_node_ids = set(_quest_node_ids(quest_keys, nodes_document))
    return [
        {
            "from": edge["from"],
            "to": edge["to"],
            "relationship": edge["type"],
            "evidence": edge["evidence"],
        }
        for edge in edges_document["edges"]
        if edge["from"] in quest_node_ids
    ]


def _unallocated_lamp_rewards(action: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "type": effect["type"],
            "description": effect["description"],
            "fact_id": effect["fact_id"],
        }
        for effect in action["transition"]["reported_effects"]
        if effect["type"] == "xp_choice_award"
    ]


def analyze_quest_xp_timing(
    account_state: dict[str, Any],
    actions_document: dict[str, Any],
    nodes_document: dict[str, Any],
    edges_document: dict[str, Any],
) -> dict[str, Any]:
    """Describe fixed quest-XP timing inputs without selecting a quest or mutating state."""
    validate_account_state(account_state)
    action_results = {result["id"]: result for result in evaluate_actions(actions_document, account_state)}
    actions = actions_document["actions"]
    requirement_index = _skill_requirement_index(actions)

    timing_inputs: list[dict[str, Any]] = []
    completed_excluded: list[dict[str, str]] = []
    hard_blocked_excluded: list[dict[str, Any]] = []
    no_fixed_xp_excluded: list[dict[str, str]] = []
    unallocated_lamps: list[dict[str, Any]] = []

    for action in actions:
        if action["kind"] != "quest" or action["repeatable"]:
            continue
        status = action_results[action["id"]]["status"]
        fixed_xp = _fixed_xp_by_skill(action)
        quest_keys = _quest_completion_keys(action)
        quest_name = quest_keys[0] if len(quest_keys) == 1 else action["name"]

        if status == "completed":
            if fixed_xp:
                completed_excluded.append({"action_id": action["id"], "quest_name": quest_name})
            continue
        if status == "blocked":
            if fixed_xp:
                hard_blocked_excluded.append(
                    {
                        "action_id": action["id"],
                        "quest_name": quest_name,
                        "missing_hard_requirements": action_results[action["id"]]["missing"],
                    }
                )
            continue

        lamps = _unallocated_lamp_rewards(action)
        if lamps:
            unallocated_lamps.append(
                {
                    "action_id": action["id"],
                    "quest_name": quest_name,
                    "status": status,
                    "rewards": lamps,
                    "allocated_skill": None,
                }
            )
        if not fixed_xp:
            no_fixed_xp_excluded.append({"action_id": action["id"], "quest_name": quest_name})
            continue

        skill_reports: list[dict[str, Any]] = []
        for skill, fixed_xp in sorted(fixed_xp.items()):
            current_xp = account_state["skill_xp"][skill]
            current_level = level_from_xp(current_xp)
            resulting_xp = min(MAX_XP, current_xp + fixed_xp)
            resulting_level = level_from_xp(resulting_xp)
            skill_reports.append(
                {
                    "skill": skill,
                    "current_xp": current_xp,
                    "current_level": current_level,
                    "fixed_xp": fixed_xp,
                    "resulting_xp": resulting_xp,
                    "resulting_level": resulting_level,
                    "levels_skipped": resulting_level - current_level,
                    "next_modeled_requirement_before": _next_requirement(
                        skill, current_level, current_xp, requirement_index
                    ),
                    "next_modeled_requirement_after": _next_requirement(
                        skill, resulting_level, resulting_xp, requirement_index
                    ),
                    "modeled_requirements_crossed": _crossed_requirements(
                        skill, current_level, resulting_level, requirement_index
                    ),
                }
            )
        timing_inputs.append(
            {
                "action_id": action["id"],
                "quest_name": quest_name,
                "status": status,
                "hard_requirements_satisfied": True,
                "missing_preparation": action_results[action["id"]]["missing_preparation"],
                "skills": skill_reports,
                "downstream_unlock_references": _downstream_references(
                    quest_keys, nodes_document, edges_document
                ),
            }
        )

    return {
        "quest_xp_timing_inputs": timing_inputs,
        "completed_quests_excluded": completed_excluded,
        "hard_blocked_quests_excluded": hard_blocked_excluded,
        "hard_eligible_quests_without_fixed_xp_excluded": no_fixed_xp_excluded,
        "unallocated_player_chosen_xp_rewards": unallocated_lamps,
        "quest_selected": False,
        "route_selected": False,
        "account_state_mutated": False,
        "player_chosen_xp_allocated": False,
        "variable_or_training_xp_included": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report fixed one-time quest XP timing inputs without selecting a quest or route."
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument("--nodes", default=DEFAULT_NODES, type=Path)
    parser.add_argument("--edges", default=DEFAULT_EDGES, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    result = analyze_quest_xp_timing(
        load_json(args.state), load_json(args.actions), load_json(args.nodes), load_json(args.edges)
    )
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    for quest in result["quest_xp_timing_inputs"]:
        print(f"[{quest['status'].upper()}] {quest['quest_name']}")
        for skill in quest["skills"]:
            print(
                f"  - {skill['skill']}: {skill['current_xp']} XP / level {skill['current_level']} + "
                f"{skill['fixed_xp']} fixed XP = {skill['resulting_xp']} XP / level "
                f"{skill['resulting_level']} (levels skipped: {skill['levels_skipped']})"
            )
        for missing in quest["missing_preparation"]:
            print(f"  - prepare: {missing}")
    print(f"Completed fixed-XP quests excluded: {len(result['completed_quests_excluded'])}")
    print(f"Hard-blocked fixed-XP quests excluded: {len(result['hard_blocked_quests_excluded'])}")
    print("Player-chosen XP allocated: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
