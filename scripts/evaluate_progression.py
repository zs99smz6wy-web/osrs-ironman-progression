from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

from osrs_xp import MAX_XP, SKILLS, level_from_xp


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ACTIONS = ROOT / "data" / "progression" / "actions.json"
DEFAULT_STATE = ROOT / "graph" / "account-state.example.json"
REQUIRED_STATE_KEYS = {
    "skills", "skill_xp", "quests_completed", "completed_actions", "transport_flags", "milestones",
    "gear_thresholds", "items", "resources", "counters", "passive_loops", "recurring_observations",
    "kingdom_observation", "slayer_task",
    "attention_window", "notable_drops", "preferences", "cash_commitments",
}
LIST_STATE_KEYS = {
    "quests_completed", "completed_actions", "transport_flags", "milestones",
    "gear_thresholds", "notable_drops",
}
RECURRING_OBSERVATION_FIELDS = {"state", "observed_at", "ready_at"}
RECURRING_OBSERVATION_STATES = {"needs_inputs", "in_progress", "ready", "cooldown", "unknown"}
KINGDOM_OBSERVATION_FIELDS = {
    "approval_percent", "worker_assignments", "collection_paused", "observed_at",
}
SLAYER_TASK_FIELDS = {"target", "remaining", "observed_at"}
RFC_3339_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def _is_rfc_3339_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value or not RFC_3339_TIMESTAMP.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_account_state(state: dict[str, Any]) -> None:
    missing = REQUIRED_STATE_KEYS - state.keys()
    if missing:
        raise ValueError(f"Account state missing required keys: {sorted(missing)}")

    for key in LIST_STATE_KEYS:
        values = state[key]
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"Account state {key} must be an array of strings")
        if len(values) != len(set(values)):
            raise ValueError(f"Account state {key} must not contain duplicates")

    for key in ("skills", "skill_xp", "items", "resources", "counters"):
        values = state[key]
        if not isinstance(values, dict):
            raise ValueError(f"Account state {key} must be an object")
        for name, value in values.items():
            minimum = 1 if key == "skills" else 0
            maximum = 99 if key == "skills" else MAX_XP if key == "skill_xp" else None
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"Account state {key}.{name} has an invalid value")
            if maximum is not None and value > maximum:
                raise ValueError(f"Account state {key}.{name} has an invalid value")

    expected_skills = set(SKILLS)
    for key in ("skills", "skill_xp"):
        actual_skills = set(state[key])
        if actual_skills != expected_skills:
            missing_skills = sorted(expected_skills - actual_skills)
            unknown_skills = sorted(actual_skills - expected_skills)
            raise ValueError(
                f"Account state {key} must contain every supported skill exactly; "
                f"missing={missing_skills}, unknown={unknown_skills}"
            )
    for skill in SKILLS:
        derived_level = level_from_xp(state["skill_xp"][skill])
        if state["skills"][skill] != derived_level:
            raise ValueError(
                f"Account state {skill} level {state['skills'][skill]} does not match "
                f"XP-derived level {derived_level}"
            )

    passive_loops = state["passive_loops"]
    if not isinstance(passive_loops, dict) or any(not isinstance(value, bool) for value in passive_loops.values()):
        raise ValueError("Account state passive_loops must contain boolean values")

    observations = state["recurring_observations"]
    if not isinstance(observations, dict):
        raise ValueError("Account state recurring_observations must be an object")
    for system_id, observation in observations.items():
        if system_id not in passive_loops:
            raise ValueError(f"Account state recurring_observations.{system_id} is not a known passive loop")
        if not isinstance(observation, dict) or set(observation) != RECURRING_OBSERVATION_FIELDS:
            raise ValueError(f"Account state recurring_observations.{system_id} has invalid fields")
        if observation["state"] not in RECURRING_OBSERVATION_STATES:
            raise ValueError(f"Account state recurring_observations.{system_id}.state is invalid")
        if not _is_rfc_3339_timestamp(observation["observed_at"]):
            raise ValueError(f"Account state recurring_observations.{system_id}.observed_at must be RFC 3339")
        if observation["ready_at"] is not None and not _is_rfc_3339_timestamp(observation["ready_at"]):
            raise ValueError(f"Account state recurring_observations.{system_id}.ready_at must be RFC 3339 or null")

    kingdom_observation = state["kingdom_observation"]
    if kingdom_observation is not None:
        if not passive_loops.get("kingdom", False):
            raise ValueError("Account state kingdom_observation requires passive_loops.kingdom to be true")
        if not isinstance(kingdom_observation, dict) or set(kingdom_observation) != KINGDOM_OBSERVATION_FIELDS:
            raise ValueError("Account state kingdom_observation has invalid fields")

        approval = kingdom_observation["approval_percent"]
        if isinstance(approval, bool) or not isinstance(approval, int) or not 25 <= approval <= 100:
            raise ValueError("Account state kingdom_observation.approval_percent must be an integer from 25 to 100")

        assignments = kingdom_observation["worker_assignments"]
        if not isinstance(assignments, dict):
            raise ValueError("Account state kingdom_observation.worker_assignments must be an object")
        worker_total = 0
        for category, workers in assignments.items():
            if not isinstance(category, str) or not category.strip():
                raise ValueError("Account state kingdom_observation.worker_assignments has an invalid category")
            if isinstance(workers, bool) or not isinstance(workers, int) or workers < 0 or workers > 10:
                raise ValueError(
                    f"Account state kingdom_observation.worker_assignments.{category} must be an integer from 0 to 10"
                )
            worker_total += workers
        worker_limit = 15 if "Royal Trouble" in state["quests_completed"] else 10
        if worker_total > worker_limit:
            raise ValueError(
                f"Account state kingdom_observation.worker_assignments total must not exceed {worker_limit}"
            )

        if not isinstance(kingdom_observation["collection_paused"], bool):
            raise ValueError("Account state kingdom_observation.collection_paused must be boolean")
        if not _is_rfc_3339_timestamp(kingdom_observation["observed_at"]):
            raise ValueError("Account state kingdom_observation.observed_at must be RFC 3339")

    slayer_task = state["slayer_task"]
    if slayer_task is not None:
        if not isinstance(slayer_task, dict) or set(slayer_task) != SLAYER_TASK_FIELDS:
            raise ValueError("Account state slayer_task has invalid fields")
        target = slayer_task["target"]
        if not isinstance(target, str) or not target or target != target.strip():
            raise ValueError("Account state slayer_task.target must be a non-empty trimmed string")
        remaining = slayer_task["remaining"]
        if isinstance(remaining, bool) or not isinstance(remaining, int) or remaining < 1:
            raise ValueError("Account state slayer_task.remaining must be a positive integer")
        if not _is_rfc_3339_timestamp(slayer_task["observed_at"]):
            raise ValueError("Account state slayer_task.observed_at must be RFC 3339")

    attention = state["attention_window"]
    if not isinstance(attention, dict) or attention.get("mode") not in {"true_afk", "low_attention", "semi_afk", "active"}:
        raise ValueError("Account state attention_window has an invalid mode")
    duration = attention.get("duration_minutes")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
        raise ValueError("Account state attention_window has an invalid duration")
    if not isinstance(attention.get("player_present"), bool):
        raise ValueError("Account state attention_window.player_present must be boolean")

    preferences = state["preferences"]
    for key in ("risk_tolerance", "intensity_tolerance", "diversity_preference"):
        value = preferences.get(key) if isinstance(preferences, dict) else None
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 4:
            raise ValueError(f"Account state preferences.{key} must be an integer from 0 to 4")

    commitments = state["cash_commitments"]
    if not isinstance(commitments, list):
        raise ValueError("Account state cash_commitments must be an array")
    valid_deadlines = {"now", "next_goal", "near_term", "later"}
    for index, commitment in enumerate(commitments):
        if not isinstance(commitment, dict) or set(commitment) != {"purpose", "coins", "deadline"}:
            raise ValueError(f"Account state cash_commitments[{index}] has invalid fields")
        if not isinstance(commitment["purpose"], str) or not commitment["purpose"].strip():
            raise ValueError(f"Account state cash_commitments[{index}].purpose must be non-empty")
        coins = commitment["coins"]
        if isinstance(coins, bool) or not isinstance(coins, int) or coins < 0:
            raise ValueError(f"Account state cash_commitments[{index}].coins has an invalid value")
        if commitment["deadline"] not in valid_deadlines:
            raise ValueError(f"Account state cash_commitments[{index}].deadline is invalid")


def _predicate_result(predicate: dict[str, Any], state: dict[str, Any]) -> tuple[bool, str]:
    predicate_type = predicate["type"]
    key = predicate["key"]
    value = predicate.get("value")

    if predicate_type == "skill_at_least":
        current = state.get("skills", {}).get(key, 1)
        return current >= value, f"{key} {value} (current: {current})"
    if predicate_type == "resource_at_least":
        current = state.get("resources", {}).get(key, 0)
        return current >= value, f"{value} {key} (current: {current})"
    if predicate_type == "item_at_least":
        current = state.get("items", {}).get(key, 0)
        return current >= value, f"{value} x {key} (current: {current})"
    if predicate_type == "counter_at_least":
        current = state.get("counters", {}).get(key, 0)
        return current >= value, f"{key} {value} (current: {current})"
    if predicate_type == "quest_completed":
        return key in state.get("quests_completed", []), f"complete {key}"
    if predicate_type == "transport_flag":
        return key in state.get("transport_flags", []), f"unlock transport: {key}"
    if predicate_type == "milestone":
        return key in state.get("milestones", []), f"reach milestone: {key}"
    if predicate_type == "passive_loop":
        expected = value if value is not None else True
        current = state.get("passive_loops", {}).get(key, False)
        return current is expected, f"passive loop {key} = {str(expected).lower()}"
    if predicate_type == "recurring_state":
        current = state.get("recurring_observations", {}).get(key, {}).get("state", "unobserved")
        return current == value, f"recurring state {key} = {value} (current: {current})"
    if predicate_type == "slayer_task_target":
        task = state.get("slayer_task")
        current = task["target"] if task is not None and task["remaining"] > 0 else "none"
        return current == key, f"current Slayer task {key} (current: {current})"
    if predicate_type == "notable_drop":
        return key in state.get("notable_drops", []), f"obtain notable drop: {key}"
    if predicate_type == "gear_threshold":
        return key in state.get("gear_thresholds", []), f"reach gear threshold: {key}"
    raise ValueError(f"Unknown predicate type: {predicate_type}")


def evaluate_condition(condition: dict[str, Any], state: dict[str, Any]) -> tuple[bool, list[str]]:
    if "all" in condition:
        missing: list[str] = []
        for child in condition["all"]:
            satisfied, child_missing = evaluate_condition(child, state)
            if not satisfied:
                missing.extend(child_missing)
        return not missing, missing

    if "any" in condition:
        alternatives: list[list[str]] = []
        for child in condition["any"]:
            satisfied, child_missing = evaluate_condition(child, state)
            if satisfied:
                return True, []
            alternatives.append(child_missing)
        rendered = " OR ".join(" + ".join(parts) for parts in alternatives)
        return False, [f"one of: {rendered}"]

    satisfied, description = _predicate_result(condition, state)
    return satisfied, [] if satisfied else [description]


def evaluate_actions(actions_document: dict[str, Any], account_state: dict[str, Any]) -> list[dict[str, Any]]:
    validate_account_state(account_state)
    results: list[dict[str, Any]] = []
    for action in actions_document["actions"]:
        satisfied, missing = evaluate_condition(action["requirements"], account_state)
        prepared, missing_preparation = evaluate_condition(action["preparation"], account_state)
        completion_satisfied, _ = evaluate_condition(action["completion"], account_state)
        completed = not action["repeatable"] and (
            action["id"] in account_state.get("completed_actions", []) or completion_satisfied
        )
        if completed:
            status = "completed"
        elif not satisfied:
            status = "blocked"
        elif not prepared:
            status = "needs_preparation"
        else:
            status = "eligible"
        results.append(
            {
                "id": action["id"],
                "name": action["name"],
                "kind": action["kind"],
                "status": status,
                "missing": [] if completed else missing,
                "missing_preparation": [] if completed else missing_preparation,
                "fact_ids": action["fact_ids"],
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate verified progression actions for an account state.")
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    results = evaluate_actions(load_json(args.actions), load_json(args.state))
    if args.json:
        print(json.dumps({"results": results}, indent=2))
        return 0

    for result in results:
        print(f"[{result['status'].upper()}] {result['name']}")
        for missing in result["missing"]:
            print(f"  - missing: {missing}")
        for missing in result["missing_preparation"]:
            print(f"  - prepare: {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
