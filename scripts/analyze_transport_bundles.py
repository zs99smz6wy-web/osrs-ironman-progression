from __future__ import annotations

import copy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRANSPORT_BUNDLES = ROOT / "strategy" / "transport-bundles.json"
COMPONENT_STATUSES = ("complete", "eligible", "needs_preparation", "blocked")
SIGNAL_STATES = {"transport_flags", "milestones", "items", "items_any"}
PAYOFF_KINDS = {"permanent", "replenishable"}


def _validate_completion_signal(signal: Any, context: str) -> None:
    if not isinstance(signal, dict) or signal.get("state") not in SIGNAL_STATES:
        raise ValueError(f"{context} has an invalid completion_signal")
    state = signal["state"]
    expected_keys = {"state", "keys"} if state == "items_any" else {"state", "key"}
    if set(signal) != expected_keys:
        raise ValueError(f"{context} completion_signal has invalid keys")
    values = signal.get("keys") if state == "items_any" else [signal.get("key")]
    if (
        not isinstance(values, list)
        or not values
        or any(not isinstance(value, str) or not value.strip() or value != value.strip() for value in values)
        or len(values) != len(set(values))
    ):
        raise ValueError(f"{context} completion_signal must name unique non-empty state keys")


def _validate_bundles(document: dict[str, Any], evaluated_actions: list[dict[str, Any]]) -> None:
    if set(document) != {"purpose", "bundles"} or not isinstance(document["purpose"], str):
        raise ValueError("Transport bundle document must contain only purpose and bundles")
    if not isinstance(document["bundles"], list) or not document["bundles"]:
        raise ValueError("Transport bundle document must contain at least one bundle")

    action_ids = {action["id"] for action in evaluated_actions}
    bundle_ids: set[str] = set()
    component_ids: set[str] = set()
    benefit_ids: set[str] = set()
    linked_actions: set[str] = set()
    for bundle in document["bundles"]:
        context = f"transport bundle {bundle.get('id', '<missing>')}"
        if set(bundle) != {"id", "name", "score_policy", "components"}:
            raise ValueError(f"{context} has invalid keys")
        if not isinstance(bundle["id"], str) or not bundle["id"] or bundle["id"] in bundle_ids:
            raise ValueError(f"{context} has an invalid or duplicate id")
        bundle_ids.add(bundle["id"])
        if not all(isinstance(bundle[key], str) and bundle[key] for key in ("name", "score_policy")):
            raise ValueError(f"{context} requires non-empty name and score_policy")
        if not isinstance(bundle["components"], list) or not bundle["components"]:
            raise ValueError(f"{context} must contain components")
        for component in bundle["components"]:
            component_context = f"{context} component {component.get('id', '<missing>')}"
            required = {
                "id", "name", "action_id", "benefit_id", "payoff_kind", "completion_signal",
                "score_bonus", "payoff_note", "usage_caveat",
            }
            if not isinstance(component, dict) or set(component) != required:
                raise ValueError(f"{component_context} has invalid keys")
            for key in ("id", "name", "action_id", "benefit_id", "payoff_note", "usage_caveat"):
                value = component[key]
                if not isinstance(value, str) or not value.strip() or value != value.strip():
                    raise ValueError(f"{component_context} has invalid {key}")
            if component["id"] in component_ids or component["benefit_id"] in benefit_ids:
                raise ValueError(f"{component_context} duplicates a component or benefit")
            if component["action_id"] in linked_actions or component["action_id"] not in action_ids:
                raise ValueError(f"{component_context} must reference one distinct normalized action")
            component_ids.add(component["id"])
            benefit_ids.add(component["benefit_id"])
            linked_actions.add(component["action_id"])
            if component["payoff_kind"] not in PAYOFF_KINDS:
                raise ValueError(f"{component_context} has invalid payoff_kind")
            if not isinstance(component["score_bonus"], int) or not 0 <= component["score_bonus"] <= 1:
                raise ValueError(f"{component_context} score_bonus must be 0 or 1")
            if component["payoff_kind"] != "permanent" and component["score_bonus"] != 0:
                raise ValueError(f"{component_context} cannot score a replenishable payoff")
            _validate_completion_signal(component["completion_signal"], component_context)


def _signal_is_complete(signal: dict[str, Any], account_state: dict[str, Any]) -> bool:
    state = signal["state"]
    if state in {"transport_flags", "milestones"}:
        return signal["key"] in account_state[state]
    if state == "items":
        return account_state["items"].get(signal["key"], 0) >= 1
    return any(account_state["items"].get(key, 0) >= 1 for key in signal["keys"])


def analyze_transport_bundles(
    document: dict[str, Any], evaluated_actions: list[dict[str, Any]], account_state: dict[str, Any]
) -> list[dict[str, Any]]:
    """Describe strategic transport bundles from an unmodified evaluator snapshot."""
    _validate_bundles(document, evaluated_actions)
    by_action = {action["id"]: action for action in evaluated_actions}
    results: list[dict[str, Any]] = []
    for bundle in document["bundles"]:
        components: list[dict[str, Any]] = []
        for definition in bundle["components"]:
            action = by_action[definition["action_id"]]
            complete = _signal_is_complete(definition["completion_signal"], account_state) or action["status"] == "completed"
            status = "complete" if complete else action["status"]
            components.append(
                {
                    "id": definition["id"],
                    "name": definition["name"],
                    "action_id": definition["action_id"],
                    "action_name": action["name"],
                    "benefit_id": definition["benefit_id"],
                    "payoff_kind": definition["payoff_kind"],
                    "status": status,
                    "source_action_status": action["status"],
                    "missing": [] if complete else action["missing"],
                    "missing_preparation": [] if complete else action["missing_preparation"],
                    "payoff_note": definition["payoff_note"],
                    "usage_caveat": definition["usage_caveat"],
                    "contextual_score_bonus": 0,
                }
            )

        incomplete_permanent = [
            component for component in components
            if component["payoff_kind"] == "permanent" and component["status"] != "complete"
        ]
        by_component = {component["id"]: component for component in components}
        for definition in bundle["components"]:
            component = by_component[definition["id"]]
            if component["status"] == "eligible" and incomplete_permanent:
                component["contextual_score_bonus"] = definition["score_bonus"]

        coverage = {
            status: sum(component["status"] == status for component in components)
            for status in COMPONENT_STATUSES
        }
        results.append(
            {
                "id": bundle["id"],
                "name": bundle["name"],
                "score_policy": bundle["score_policy"],
                "network_incomplete": bool(incomplete_permanent),
                "coverage": {"total": len(components), **coverage},
                "components": components,
            }
        )
    return copy.deepcopy(results)


def contextual_bonus_by_action(bundles: list[dict[str, Any]]) -> dict[str, int]:
    """Return one non-cumulative, manifest-validated contextual bonus per action."""
    bonuses: dict[str, int] = {}
    for bundle in bundles:
        for component in bundle["components"]:
            action_id = component["action_id"]
            bonus = component["contextual_score_bonus"]
            if action_id in bonuses:
                raise ValueError(f"Transport bundle action appears more than once: {action_id}")
            bonuses[action_id] = bonus
    return bonuses
