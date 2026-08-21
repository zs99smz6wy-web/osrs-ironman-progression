"""Apply one verified progression action without choosing a route for the player."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from evaluate_progression import (
    DEFAULT_ACTIONS,
    DEFAULT_STATE,
    LIST_STATE_KEYS,
    evaluate_actions,
    evaluate_condition,
    load_json,
    validate_account_state,
)
from osrs_xp import add_xp, level_from_xp


MUTABLE_COUNTER_STATES = {"items", "resources", "counters"}


def _result(
    status: str,
    state: dict[str, Any],
    applied_effects: list[dict[str, Any]] | None = None,
    reported_effects: list[dict[str, Any]] | None = None,
    selected_option_id: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "next_state": copy.deepcopy(state),
        "applied_effects": copy.deepcopy(applied_effects or []),
        "reported_effects": copy.deepcopy(reported_effects or []),
        "selected_option_id": selected_option_id,
    }


def _action_by_id(actions_document: dict[str, Any], action_id: str) -> dict[str, Any]:
    for action in actions_document.get("actions", []):
        if action.get("id") == action_id:
            return action
    raise ValueError(f"Unknown action ID: {action_id}")


def _require_transition(action: dict[str, Any]) -> dict[str, Any]:
    transition = action.get("transition")
    if not isinstance(transition, dict):
        raise ValueError(f"Action {action['id']} is missing a transition")
    for key in ("effects", "options", "reported_effects"):
        if not isinstance(transition.get(key), list):
            raise ValueError(f"Action {action['id']} transition.{key} must be an array")
    return transition


def _effect_is_satisfied(effect: dict[str, Any], state: dict[str, Any]) -> bool:
    """Check only effects whose completed value can be known from a snapshot."""
    operation = effect.get("op")
    state_key = effect.get("state")
    key = effect.get("key")
    if operation == "set_add":
        return isinstance(state.get(state_key), list) and key in state[state_key]
    if operation == "set":
        return state.get(state_key, {}).get(key) == effect.get("value")
    if operation == "clear_observation":
        return key not in state.get("recurring_observations", {})
    if operation == "ensure_min":
        return state.get(state_key, {}).get(key, 0) >= effect.get("value")
    # A delta has no reconstructable target value in an imported snapshot.
    return True


def _completion_is_consistent(action: dict[str, Any], state: dict[str, Any]) -> bool:
    if action["id"] not in state["completed_actions"]:
        return False
    transition = _require_transition(action)
    return all(_effect_is_satisfied(effect, state) for effect in transition["effects"])


def _validate_effect(effect: dict[str, Any]) -> None:
    if not isinstance(effect, dict):
        raise ValueError("Transition effects must be objects")
    operation = effect.get("op")
    state_key = effect.get("state")
    key = effect.get("key")
    if not isinstance(key, str) or not key:
        raise ValueError("Transition effects require a non-empty key")

    if operation == "set_add":
        if state_key not in LIST_STATE_KEYS:
            raise ValueError(f"set_add requires a set-like account state, got: {state_key}")
        return

    if operation == "set":
        if state_key != "passive_loops" or not isinstance(effect.get("value"), bool):
            raise ValueError("set only supports boolean passive_loops values")
        return

    if operation == "clear_observation":
        if state_key != "recurring_observations" or "value" in effect or "amount" in effect:
            raise ValueError("clear_observation only supports recurring_observations without a value")
        return

    if operation == "delta":
        amount = effect.get("amount")
        if state_key not in MUTABLE_COUNTER_STATES or isinstance(amount, bool) or not isinstance(amount, int):
            raise ValueError("delta requires an integer amount for items, resources, or counters")
        if state_key == "counters" and amount <= 0:
            raise ValueError("counter deltas must be positive")
        return

    if operation == "gain_xp":
        amount = effect.get("amount")
        if state_key != "skill_xp" or isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError("gain_xp requires a positive integer amount for skill_xp")
        return

    if operation == "ensure_min":
        value = effect.get("value")
        if state_key not in MUTABLE_COUNTER_STATES or isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("ensure_min requires a non-negative integer for items, resources, or counters")
        return

    raise ValueError(f"Unknown transition effect operation: {operation}")


def _apply_effect(effect: dict[str, Any], state: dict[str, Any]) -> None:
    _validate_effect(effect)
    operation = effect["op"]
    state_key = effect["state"]
    key = effect["key"]

    if operation == "set_add":
        values = state[state_key]
        if key not in values:
            values.append(key)
        return

    if operation == "set":
        state[state_key][key] = effect["value"]
        return

    if operation == "clear_observation":
        state[state_key].pop(key, None)
        return


    if operation == "gain_xp":
        if key not in state["skill_xp"]:
            raise ValueError(f"XP award references unknown skill: {key}")
        next_xp = add_xp(state["skill_xp"][key], effect["amount"])
        state["skill_xp"][key] = next_xp
        state["skills"][key] = level_from_xp(next_xp)
        return

    current = state[state_key].get(key, 0)
    if operation == "delta":
        next_value = current + effect["amount"]
        if next_value < 0:
            raise ValueError(f"Transition would underflow {state_key}.{key}")
        state[state_key][key] = next_value
        return

    state[state_key][key] = max(current, effect["value"])


def _eligible_options(options: list[dict[str, Any]], state: dict[str, Any]) -> list[dict[str, Any]]:
    viable: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for option in options:
        option_id = option.get("id")
        if not isinstance(option_id, str) or not option_id or option_id in seen_ids:
            raise ValueError("Transition options require unique non-empty IDs")
        seen_ids.add(option_id)
        requires = option.get("requires", {"all": []})
        if not isinstance(option.get("effects", []), list):
            raise ValueError(f"Transition option {option_id} effects must be an array")
        satisfied, _ = evaluate_condition(requires, state)
        if satisfied:
            viable.append(option)
    return viable


def apply_action(
    actions_document: dict[str, Any],
    state: dict[str, Any],
    action_id: str,
    option_id: str | None = None,
) -> dict[str, Any]:
    """Apply one eligible action atomically, returning a new account-state snapshot."""
    validate_account_state(state)
    action = _action_by_id(actions_document, action_id)
    transition = _require_transition(action)
    repeatable = action.get("repeatable")
    if not isinstance(repeatable, bool):
        raise ValueError(f"Action {action_id} repeatable must be boolean")

    completion_satisfied, _ = evaluate_condition(action["completion"], state)
    marked_completed = action_id in state["completed_actions"]
    if repeatable:
        if marked_completed:
            return _result("state_inconsistent", state)
    else:
        if marked_completed and not completion_satisfied:
            return _result("state_inconsistent", state)
        if completion_satisfied:
            if not _completion_is_consistent(action, state):
                return _result("state_inconsistent", state)
            return _result("already_completed", state)

    evaluated = {result["id"]: result for result in evaluate_actions(actions_document, state)}
    if evaluated[action_id]["status"] != "eligible":
        return _result("not_eligible", state)

    viable_options = _eligible_options(transition["options"], state)
    selected_option: dict[str, Any] | None = None
    if option_id is not None:
        selected_option = next((option for option in viable_options if option["id"] == option_id), None)
        if selected_option is None:
            return _result("not_eligible", state)
    elif len(viable_options) > 1:
        return _result("choice_required", state)
    elif len(viable_options) == 1:
        selected_option = viable_options[0]
    elif transition["options"]:
        return _result("not_eligible", state)

    effects = list(transition["effects"])
    reports = list(transition["reported_effects"])
    if selected_option is not None:
        effects.extend(selected_option["effects"])
        reports.extend(selected_option.get("reported_effects", []))

    next_state = copy.deepcopy(state)
    applied_effects: list[dict[str, Any]] = []
    try:
        for effect in effects:
            previous_xp = next_state["skill_xp"].get(effect["key"]) if effect.get("op") == "gain_xp" else None
            _apply_effect(effect, next_state)
            receipt = copy.deepcopy(effect)
            if effect.get("op") == "gain_xp":
                receipt["amount"] = next_state["skill_xp"][effect["key"]] - previous_xp
            applied_effects.append(receipt)
        if not repeatable:
            next_state["completed_actions"].append(action_id)
    except ValueError as error:
        if str(error).startswith("Transition would underflow"):
            return _result("not_eligible", state)
        raise

    validate_account_state(next_state)
    if not repeatable:
        applied_effects.append({"op": "set_add", "state": "completed_actions", "key": action_id})
    return _result(
        "applied",
        next_state,
        applied_effects,
        reports,
        selected_option["id"] if selected_option is not None else None,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply one eligible progression action without writing files.")
    parser.add_argument("state", type=Path, help="Path to an account-state JSON file")
    parser.add_argument("action_id", help="Action ID to apply")
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument("--option-id")
    args = parser.parse_args()

    result = apply_action(load_json(args.actions), load_json(args.state), args.action_id, args.option_id)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
