"""Report formal PvM access and explicit readiness observations without selecting a route."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from evaluate_progression import DEFAULT_ACTIONS, DEFAULT_STATE, evaluate_actions, load_json, validate_account_state


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTEXTS = ROOT / "strategy" / "pvm-readiness-contexts.json"
REQUIRED_CONTEXT_KEYS = {
    "id", "name", "access_action_id", "linked_action_ids", "fact_ids", "encounter_observation_key",
    "required_observation_groups", "style_gap", "supply_gap", "recovery_gap", "tactical_gap",
    "reward_objective_gap", "stop_conditions", "reentry_conditions", "source_ids",
}


def validate_context_document(document: dict[str, Any], action_ids: set[str]) -> list[dict[str, Any]]:
    if set(document) != {"schema_version", "scope", "activities"} or document["schema_version"] != 1:
        raise ValueError("PvM readiness context document has invalid metadata")
    if not isinstance(document["scope"], str) or not isinstance(document["activities"], list):
        raise ValueError("PvM readiness context document has invalid structure")
    ids: set[str] = set()
    contexts: list[dict[str, Any]] = []
    for context in document["activities"]:
        if not isinstance(context, dict) or set(context) != REQUIRED_CONTEXT_KEYS:
            raise ValueError("PvM readiness context has invalid keys")
        if context["id"] in ids or context["access_action_id"] not in action_ids:
            raise ValueError("PvM readiness contexts require unique IDs and known access actions")
        if not context["linked_action_ids"] or any(action_id not in action_ids for action_id in context["linked_action_ids"]):
            raise ValueError("PvM readiness contexts require known linked actions")
        if not all(isinstance(value, str) and value.strip() for key, value in context.items() if key in {
            "id", "name", "access_action_id", "encounter_observation_key", "style_gap", "supply_gap",
            "recovery_gap", "tactical_gap", "reward_objective_gap",
        }):
            raise ValueError("PvM readiness context strings must be non-empty")
        for key in ("linked_action_ids", "fact_ids", "required_observation_groups", "stop_conditions", "reentry_conditions", "source_ids"):
            if not isinstance(context[key], list) or not context[key] or any(not isinstance(value, str) or not value.strip() for value in context[key]):
                raise ValueError(f"PvM readiness context {key} must be a non-empty string list")
        ids.add(context["id"])
        contexts.append(context)
    return contexts


def _moons_observation(account_state: dict[str, Any]) -> dict[str, Any] | None:
    moons = account_state["perilous_moons_observation"]
    if moons is None:
        return None
    bosses = moons["run"]["bosses_defeated"]
    return {
        "observed_at": moons["observed_at"],
        "attempts": None,
        "successful_completions": len(bosses),
        "lunar_chest_opened": moons["run"]["lunar_chest_opened"],
        "source": "perilous_moons_observation",
    }


def _encounter_summary(context: dict[str, Any], account_state: dict[str, Any]) -> dict[str, Any] | None:
    if context["id"] == "perilous-moons":
        return _moons_observation(account_state)
    observation = account_state["encounter_observations"].get(context["encounter_observation_key"])
    if observation is None:
        return None
    return {
        "observed_at": observation["observed_at"],
        "attempts": observation["attempts"],
        "successful_completions": observation["successful_completions"],
        "lunar_chest_opened": None,
        "source": "encounter_observations",
    }


def analyze_pvm_readiness(context_document: dict[str, Any], actions_document: dict[str, Any], account_state: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose PvM context without inferring readiness, victory, loot, or timing."""
    validate_account_state(account_state)
    action_results = {result["id"]: result for result in evaluate_actions(actions_document, account_state)}
    contexts = validate_context_document(context_document, set(action_results))
    snapshot_present = account_state["combat_readiness_observation"] is not None
    results: list[dict[str, Any]] = []
    for context in contexts:
        access = action_results[context["access_action_id"]]
        encounter = _encounter_summary(context, account_state)
        gaps: list[dict[str, str]] = []
        if not snapshot_present:
            gaps.append({"group": "combat_snapshot", "detail": "No combat readiness snapshot is recorded."})
        for group, detail in (("styles", context["style_gap"]), ("supplies", context["supply_gap"]),
                              ("recovery", context["recovery_gap"]), ("tactics", context["tactical_gap"]),
                              ("reward_objective", context["reward_objective_gap"])):
            gaps.append({"group": group, "detail": detail})
        if access["status"] != "eligible":
            readiness_status = "formal_access_incomplete"
            timing_status = "formal_access_before_timing"
        elif encounter is None:
            readiness_status = "needs_player_observations"
            timing_status = "needs_player_selected_objective"
        else:
            readiness_status = "observed_encounter_context_only"
            timing_status = "observations_do_not_select_timing"
        results.append({
            "activity_id": context["id"],
            "name": context["name"],
            "fact_ids": context["fact_ids"],
            "factual_access": {"action_id": context["access_action_id"], "status": access["status"], "missing": copy.deepcopy(access["missing"]), "missing_preparation": copy.deepcopy(access["missing_preparation"])},
            "combat_snapshot_present": snapshot_present,
            "encounter_observation": encounter,
            "reward_objective_observation": None,
            "observation_gaps": gaps,
            "readiness_status": readiness_status,
            "timing_status": timing_status,
            "stop_conditions": context["stop_conditions"],
            "reentry_conditions": context["reentry_conditions"],
            "combat_win_inferred": False,
            "loot_inferred": False,
            "gear_sufficiency_inferred": False,
            "competence_inferred": False,
            "route_order_selected": False,
        })
    return results


def context_by_action(report: list[dict[str, Any]], context_document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    contexts = {context["id"]: context for context in context_document["activities"]}
    return {action_id: item for item in report for action_id in contexts[item["activity_id"]]["linked_action_ids"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Report PvM readiness context without selecting a route or inferring outcomes.")
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument("--contexts", default=DEFAULT_CONTEXTS, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = analyze_pvm_readiness(load_json(args.contexts), load_json(args.actions), load_json(args.state))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for item in report:
            print(f"{item['name']}: {item['readiness_status']} ({item['factual_access']['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
