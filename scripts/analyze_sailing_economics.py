from __future__ import annotations

import copy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTEXTS = ROOT / "strategy" / "sailing-economics-contexts.json"

REQUIRED_CONTEXT_KEYS = {
    "id",
    "action_id",
    "fact_ids",
    "entry_note",
    "prepared_note",
    "unprepared_note",
    "material_boundary_note",
    "stop_condition",
    "reentry_condition",
    "objective",
}
REQUIRED_OBJECTIVE_KEYS = {
    "id",
    "name",
    "action_id",
    "fact_ids",
    "completion_signal",
    "requirements",
    "objective_note",
}


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _validate_context_document(document: dict[str, Any], action_ids: set[str]) -> list[dict[str, Any]]:
    if set(document) != {"schema_version", "scope", "contexts"}:
        raise ValueError("Sailing economics context document has invalid keys")
    if document["schema_version"] != 1 or not _is_non_empty_string(document["scope"]):
        raise ValueError("Sailing economics context document has invalid metadata")
    contexts = document["contexts"]
    if not isinstance(contexts, list) or not contexts:
        raise ValueError("Sailing economics contexts must be a non-empty list")

    ids: set[str] = set()
    linked_actions: set[str] = set()
    for context in contexts:
        if not isinstance(context, dict) or set(context) != REQUIRED_CONTEXT_KEYS:
            raise ValueError("Sailing economics context has invalid keys")
        for key in REQUIRED_CONTEXT_KEYS - {"fact_ids", "objective"}:
            if not _is_non_empty_string(context[key]):
                raise ValueError(f"Sailing economics context {key} must be a non-empty string")
        if context["id"] in ids or context["action_id"] in linked_actions:
            raise ValueError("Sailing economics contexts must have unique IDs and action IDs")
        if context["action_id"] not in action_ids:
            raise ValueError("Sailing economics context references an unknown action")
        if not isinstance(context["fact_ids"], list) or not context["fact_ids"] or not all(
            _is_non_empty_string(fact_id) for fact_id in context["fact_ids"]
        ):
            raise ValueError("Sailing economics context fact_ids must be non-empty strings")

        objective = context["objective"]
        if not isinstance(objective, dict) or set(objective) != REQUIRED_OBJECTIVE_KEYS:
            raise ValueError("Sailing economics objective has invalid keys")
        for key in REQUIRED_OBJECTIVE_KEYS - {"fact_ids", "completion_signal", "requirements"}:
            if not _is_non_empty_string(objective[key]):
                raise ValueError(f"Sailing economics objective {key} must be a non-empty string")
        if objective["action_id"] not in action_ids:
            raise ValueError("Sailing economics objective references an unknown action")
        if not isinstance(objective["fact_ids"], list) or not objective["fact_ids"] or not all(
            _is_non_empty_string(fact_id) for fact_id in objective["fact_ids"]
        ):
            raise ValueError("Sailing economics objective fact_ids must be non-empty strings")
        signal = objective["completion_signal"]
        if not isinstance(signal, dict) or set(signal) != {"state", "key"} or signal["state"] != "items" or not _is_non_empty_string(signal["key"]):
            raise ValueError("Sailing economics objective completion_signal must be an item signal")
        requirements = objective["requirements"]
        if set(requirements) != {"skills", "resources"}:
            raise ValueError("Sailing economics objective requirements have invalid keys")
        for group_name in ("skills", "resources"):
            group = requirements[group_name]
            if not isinstance(group, dict) or not group or not all(
                _is_non_empty_string(key) and isinstance(value, int) and value >= 0
                for key, value in group.items()
            ):
                raise ValueError(f"Sailing economics objective {group_name} requirements are invalid")
        ids.add(context["id"])
        linked_actions.add(context["action_id"])
    return contexts


def _shortfalls(requirements: dict[str, dict[str, int]], account_state: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    skill_shortfalls = [
        {"kind": "skill", "key": skill, "have": account_state["skills"][skill], "need": need, "shortfall": need - account_state["skills"][skill]}
        for skill, need in requirements["skills"].items()
        if account_state["skills"][skill] < need
    ]
    resource_shortfalls = [
        {"kind": "resource", "key": resource, "have": account_state["resources"].get(resource, 0), "need": need, "shortfall": need - account_state["resources"].get(resource, 0)}
        for resource, need in requirements["resources"].items()
        if account_state["resources"].get(resource, 0) < need
    ]
    return skill_shortfalls, resource_shortfalls


def analyze_sailing_economics(
    context_document: dict[str, Any], actions_document: dict[str, Any], account_state: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Explain account-backed Sailing timing without changing eligibility or score."""
    action_ids = {action["id"] for action in actions_document["actions"]}
    contexts = _validate_context_document(context_document, action_ids)
    results: dict[str, dict[str, Any]] = {}

    for context in contexts:
        objective = context["objective"]
        completion_key = objective["completion_signal"]["key"]
        objective_complete = account_state["items"].get(completion_key, 0) >= 1
        skill_shortfalls, resource_shortfalls = _shortfalls(objective["requirements"], account_state)
        objective_ready = not objective_complete and not skill_shortfalls and not resource_shortfalls
        entry_complete = "Pandemonium" in account_state["quests_completed"]
        if objective_complete:
            status = "fixed_next_objective_complete"
            note = "The fixed Skiff objective is already recorded. Select later Sailing work only from a current, source-backed goal."
        elif objective_ready:
            status = "fixed_next_objective_ready"
            note = context["prepared_note"]
        elif entry_complete:
            status = "sailing_unlocked_no_fixed_next_objective"
            note = context["unprepared_note"]
        else:
            status = "entry_unlock_available"
            note = context["entry_note"]

        results[context["action_id"]] = {
            "context_id": context["id"],
            "status": status,
            "formal_eligibility_preserved": True,
            "score_adjustment": 0,
            "fact_ids": copy.deepcopy(context["fact_ids"]),
            "entry_complete": entry_complete,
            "note": note,
            "fixed_next_objective": {
                "id": objective["id"],
                "name": objective["name"],
                "action_id": objective["action_id"],
                "fact_ids": copy.deepcopy(objective["fact_ids"]),
                "complete": objective_complete,
                "ready": objective_ready,
                "skill_shortfalls": skill_shortfalls,
                "resource_shortfalls": resource_shortfalls,
                "objective_note": objective["objective_note"],
            },
            "material_planning": {
                "status": "uncommitted_target_no_shortfall_calculated",
                "note": context["material_boundary_note"],
                "resource_shortfalls": [],
            },
            "stop_condition": context["stop_condition"],
            "reentry_condition": context["reentry_condition"],
            "future_purchase_required_for_entry": False,
            "variable_loot_or_income_inferred": False,
            "resource_source_inferred": False,
        }
    return results
