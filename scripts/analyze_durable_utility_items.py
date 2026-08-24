from __future__ import annotations

import copy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTEXTS = ROOT / "strategy" / "durable-utility-item-contexts.json"

REQUIRED_ITEM_KEYS = {
    "id", "name", "item_key", "fact_ids", "benefit_id", "demand_note",
    "stop_condition", "reentry_condition", "paths",
}


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and value == value.strip() and bool(value)


def validate_context_document(document: dict[str, Any], action_ids: set[str]) -> list[dict[str, Any]]:
    if set(document) != {"schema_version", "scope", "items"}:
        raise ValueError("Durable utility context document has invalid keys")
    if document["schema_version"] != 1 or not _non_empty(document["scope"]):
        raise ValueError("Durable utility context document has invalid metadata")
    if not isinstance(document["items"], list) or not document["items"]:
        raise ValueError("Durable utility contexts must be a non-empty list")

    ids: set[str] = set()
    benefit_ids: set[str] = set()
    path_actions: set[str] = set()
    for item in document["items"]:
        allowed = REQUIRED_ITEM_KEYS | {"unmodeled_path_note"}
        if not isinstance(item, dict) or not REQUIRED_ITEM_KEYS.issubset(item) or not set(item).issubset(allowed):
            raise ValueError("Durable utility item context has invalid keys")
        for key in REQUIRED_ITEM_KEYS - {"fact_ids", "paths"}:
            if not _non_empty(item[key]):
                raise ValueError(f"Durable utility item {key} must be a non-empty string")
        if item["id"] in ids or item["benefit_id"] in benefit_ids:
            raise ValueError("Durable utility item IDs and benefit IDs must be unique")
        if not isinstance(item["fact_ids"], list) or not item["fact_ids"] or not all(_non_empty(value) for value in item["fact_ids"]):
            raise ValueError("Durable utility fact_ids must be non-empty strings")
        if not isinstance(item["paths"], list) or not item["paths"]:
            raise ValueError("Durable utility item paths must be non-empty")
        for path in item["paths"]:
            if set(path) != {"action_id", "name"} or not all(_non_empty(value) for value in path.values()):
                raise ValueError("Durable utility acquisition path has invalid keys")
            if path["action_id"] not in action_ids or path["action_id"] in path_actions:
                raise ValueError("Durable utility acquisition path must reference one unique action")
            path_actions.add(path["action_id"])
        ids.add(item["id"])
        benefit_ids.add(item["benefit_id"])
    return document["items"]


def analyze_durable_utility_items(
    context_document: dict[str, Any],
    actions_document: dict[str, Any],
    evaluated_actions: list[dict[str, Any]],
    account_state: dict[str, Any],
) -> list[dict[str, Any]]:
    """Report fixed utility paths and gaps without choosing a purchase or inferring demand."""
    action_ids = {action["id"] for action in actions_document["actions"]}
    contexts = validate_context_document(context_document, action_ids)
    evaluated = {action["id"]: action for action in evaluated_actions}
    configured_actions = {action["id"]: action for action in actions_document["actions"]}
    results: list[dict[str, Any]] = []

    for context in contexts:
        owned = account_state["items"].get(context["item_key"], 0) >= 1
        paths = []
        for configured_path in context["paths"]:
            action = evaluated[configured_path["action_id"]]
            requirements = configured_actions[action["id"]]["requirements"].get("all", [])
            resource_requirements = {
                condition["key"]: condition["value"]
                for condition in requirements
                if condition.get("type") == "resource_at_least"
            }
            paths.append({
                "action_id": action["id"],
                "name": configured_path["name"],
                "action_name": action["name"],
                "status": action["status"],
                "missing": copy.deepcopy(action["missing"]),
                "missing_preparation": copy.deepcopy(action["missing_preparation"]),
                "resource_requirements": resource_requirements,
            })

        ready_paths = [path for path in paths if path["status"] == "eligible"]
        if owned:
            status = "owned"
        elif ready_paths:
            status = "purchase_ready_needs_demand_confirmation"
        else:
            status = "requirements_or_currency_incomplete"

        result = {
            "id": context["id"],
            "name": context["name"],
            "item_key": context["item_key"],
            "benefit_id": context["benefit_id"],
            "fact_ids": copy.deepcopy(context["fact_ids"]),
            "status": status,
            "owned": owned,
            "paths": paths,
            "ready_path_count": len(ready_paths),
            "demand_observed": False,
            "demand_note": context["demand_note"],
            "selected_path": None,
            "shared_currency_contention": [],
            "purchase_selected": False,
            "score_adjustment": 0,
            "stop_condition": context["stop_condition"],
            "reentry_condition": context["reentry_condition"],
            "currency_generated": False,
            "ownership_inferred": False,
        }
        if "unmodeled_path_note" in context:
            result["unmodeled_path_note"] = context["unmodeled_path_note"]
        results.append(result)

    ready_paths = [
        (context, path)
        for context in results
        for path in context["paths"]
        if path["status"] == "eligible"
    ]
    for context, path in ready_paths:
        for other_context, other_path in ready_paths:
            if context["id"] >= other_context["id"]:
                continue
            shared = set(path["resource_requirements"]) & set(other_path["resource_requirements"])
            for resource in sorted(shared):
                combined = path["resource_requirements"][resource] + other_path["resource_requirements"][resource]
                observed = account_state["resources"].get(resource, 0)
                if observed >= combined:
                    continue
                contention = {
                    "resource": resource,
                    "observed": observed,
                    "combined_cost": combined,
                    "paths": [path["action_id"], other_path["action_id"]],
                    "purchase_order_selected": False,
                }
                context["shared_currency_contention"].append(copy.deepcopy(contention))
                other_context["shared_currency_contention"].append(copy.deepcopy(contention))
    return results


def context_by_action(contexts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        path["action_id"]: {
            "item_id": context["id"],
            "item_name": context["name"],
            "benefit_id": context["benefit_id"],
            "status": context["status"],
            "demand_observed": context["demand_observed"],
            "demand_note": context["demand_note"],
            "selected_path": context["selected_path"],
            "score_adjustment": 0,
        }
        for context in contexts
        for path in context["paths"]
    }
