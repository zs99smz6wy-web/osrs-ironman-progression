"""Compare selected monster-drop bypasses without planning RNG or inferring combat readiness."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from evaluate_progression import DEFAULT_ACTIONS, DEFAULT_STATE, evaluate_actions, load_json, validate_account_state


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTEXTS = ROOT / "strategy" / "monster-drop-bypass-timing-contexts.json"
DEFAULT_RESEARCH = ROOT / "research" / "monster-drop-bypass-timing.json"
DEFAULT_READINESS_FACTS = ROOT / "data" / "facts" / "drop-bypass-readiness.json"
REQUIRED_CONTEXT_KEYS = {
    "id", "name", "readiness_path_id", "bypass_fact_id", "access_action_id", "encounter_observation_key",
    "target_item_keys", "intermediate_item_keys", "target_notable_drop_keys", "normal_path", "bypass_benefit",
    "stop_conditions", "reentry_conditions", "source_ids",
}
REQUIRED_RESEARCH_KEYS = {"schema_version", "scope", "factual_inputs", "selected_bypasses", "analysis_boundaries"}


def validate_context_document(document: dict[str, Any], action_ids: set[str]) -> list[dict[str, Any]]:
    if set(document) != {"schema_version", "scope", "policy_reference", "bypasses"}:
        raise ValueError("Monster-drop bypass timing context has invalid metadata")
    if document["schema_version"] != 1 or not isinstance(document["scope"], str) or not isinstance(document["policy_reference"], str):
        raise ValueError("Monster-drop bypass timing context has invalid metadata values")
    if not isinstance(document["bypasses"], list):
        raise ValueError("Monster-drop bypass timing contexts must be a list")

    ids: set[str] = set()
    contexts: list[dict[str, Any]] = []
    for context in document["bypasses"]:
        if not isinstance(context, dict) or set(context) != REQUIRED_CONTEXT_KEYS:
            raise ValueError("Monster-drop bypass timing context has invalid keys")
        for key in ("id", "name", "readiness_path_id", "bypass_fact_id", "access_action_id", "encounter_observation_key", "bypass_benefit"):
            if not isinstance(context[key], str) or not context[key].strip():
                raise ValueError(f"Monster-drop bypass timing context {key} must be a non-empty string")
        if context["id"] in ids or context["access_action_id"] not in action_ids:
            raise ValueError("Monster-drop bypass timing contexts require unique IDs and known actions")
        for key in ("target_item_keys", "target_notable_drop_keys", "stop_conditions", "reentry_conditions", "source_ids"):
            values = context[key]
            if not isinstance(values, list) or not values or any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"Monster-drop bypass timing context {key} must be a non-empty string list")
        if not isinstance(context["intermediate_item_keys"], list) or any(
            not isinstance(value, str) or not value.strip() for value in context["intermediate_item_keys"]
        ):
            raise ValueError("Monster-drop bypass timing context intermediate_item_keys must be a string list")
        normal_path = context["normal_path"]
        if (
            not isinstance(normal_path, dict)
            or set(normal_path) != {"status", "description", "displaced_requirement_or_benefit"}
            or normal_path["status"] not in {"modeled", "not_modeled"}
            or any(not isinstance(value, str) or not value.strip() for value in normal_path.values())
        ):
            raise ValueError("Monster-drop bypass timing context normal_path is invalid")
        ids.add(context["id"])
        contexts.append(context)
    return contexts


def validate_research_index(document: dict[str, Any], contexts: list[dict[str, Any]]) -> None:
    if set(document) != REQUIRED_RESEARCH_KEYS or document["schema_version"] != 1:
        raise ValueError("Monster-drop bypass research index has invalid metadata")
    if not isinstance(document["selected_bypasses"], list):
        raise ValueError("Monster-drop bypass research index selected_bypasses must be a list")
    indexed = {item.get("id"): item for item in document["selected_bypasses"] if isinstance(item, dict)}
    if set(indexed) != {context["id"] for context in contexts}:
        raise ValueError("Monster-drop bypass research index must cover each timing context exactly once")
    for context in contexts:
        item = indexed[context["id"]]
        if set(item) != {"id", "readiness_path_id", "bypass_fact_id", "access_action_id"}:
            raise ValueError("Monster-drop bypass research entry has invalid keys")
        for key in ("readiness_path_id", "bypass_fact_id", "access_action_id"):
            if item[key] != context[key]:
                raise ValueError("Monster-drop bypass research entry and timing context disagree")


def _readiness_paths(document: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    records = document.get("records")
    if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
        raise ValueError("Drop-bypass readiness facts must contain one factual record")
    record = records[0]
    paths = record.get("paths")
    if not isinstance(paths, list):
        raise ValueError("Drop-bypass readiness facts have no paths")
    indexed = {path.get("id"): path for path in paths if isinstance(path, dict) and isinstance(path.get("id"), str)}
    if len(indexed) != len(paths):
        raise ValueError("Drop-bypass readiness facts require unique path IDs")
    model = record.get("probability_model")
    if not isinstance(model, dict) or not isinstance(model.get("assumption"), str):
        raise ValueError("Drop-bypass readiness facts have invalid probability model")
    return indexed, model


def _probability_context(path: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    probability = path.get("drop_probability")
    if not isinstance(probability, dict):
        raise ValueError("Drop-bypass readiness path has no probability context")
    rate_key = "listed_rate" if "listed_rate" in probability else "staged_rates"
    rate = probability.get(rate_key)
    provenance = probability.get("rate_provenance")
    if not isinstance(rate, str) or not isinstance(provenance, str):
        raise ValueError("Drop-bypass readiness probability context is invalid")
    return {
        "rate_description": rate,
        "rate_provenance": provenance,
        "model_assumption": model["assumption"],
        "staged_acquisition": rate_key == "staged_rates",
        "expected_kills_calculated": False,
        "cumulative_probability_calculated": False,
        "drop_inferred": False,
    }


def _item_observation(context: dict[str, Any], account_state: dict[str, Any]) -> dict[str, Any]:
    items = account_state["items"]
    notable_drops = set(account_state["notable_drops"])
    owned_item_keys = [key for key in context["target_item_keys"] if items.get(key, 0) > 0]
    intermediate_item_keys = [key for key in context["intermediate_item_keys"] if items.get(key, 0) > 0]
    notable_target_keys = [key for key in context["target_notable_drop_keys"] if key in notable_drops]
    return {
        "current_target_item_owned": bool(owned_item_keys),
        "owned_target_item_keys": owned_item_keys,
        "intermediate_item_observed": bool(intermediate_item_keys),
        "observed_intermediate_item_keys": intermediate_item_keys,
        "target_notable_drop_recorded": bool(notable_target_keys),
        "recorded_target_notable_drop_keys": notable_target_keys,
        "ownership_inferred": False,
        "drop_inferred": False,
    }


def _encounter_context(context: dict[str, Any], account_state: dict[str, Any]) -> dict[str, Any]:
    observation = account_state["encounter_observations"].get(context["encounter_observation_key"])
    return {
        "key": context["encounter_observation_key"],
        "present": observation is not None,
        "observation": copy.deepcopy(observation),
        "throughput_calculated": False,
        "combat_readiness_inferred": False,
    }


def _decision_status(access: dict[str, Any], objective: str | None, item_observation: dict[str, Any], snapshot_present: bool, encounter_present: bool) -> str:
    if item_observation["current_target_item_owned"]:
        return "target_item_already_owned"
    if item_observation["intermediate_item_observed"]:
        return "intermediate_drop_observed"
    if access["status"] != "eligible":
        return "formal_access_incomplete"
    if objective is None:
        return "not_selected_without_explicit_objective"
    if not snapshot_present and not encounter_present:
        return "needs_player_combat_observations"
    if not snapshot_present:
        return "needs_combat_snapshot"
    if not encounter_present:
        return "needs_encounter_observation"
    return "bounded_rng_bypass_candidate"


def analyze_monster_drop_bypass_timing(
    account_state: dict[str, Any],
    actions_document: dict[str, Any],
    context_document: dict[str, Any],
    research_document: dict[str, Any],
    readiness_document: dict[str, Any],
    objectives: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Report access and observations without recommending or forecasting a monster drop."""
    validate_account_state(account_state)
    action_results = {item["id"]: item for item in evaluate_actions(actions_document, account_state)}
    contexts = validate_context_document(context_document, set(action_results))
    validate_research_index(research_document, contexts)
    readiness_paths, probability_model = _readiness_paths(readiness_document)
    objectives = {} if objectives is None else objectives
    if not isinstance(objectives, dict) or any(
        key not in {context["id"] for context in contexts} or not isinstance(value, str) or not value.strip()
        for key, value in objectives.items()
    ):
        raise ValueError("Monster-drop bypass objectives must map known IDs to non-empty strings")

    snapshot = account_state["combat_readiness_observation"]
    report: list[dict[str, Any]] = []
    for context in contexts:
        path = readiness_paths.get(context["readiness_path_id"])
        if path is None:
            raise ValueError("Monster-drop bypass timing context references an unknown readiness path")
        access = action_results[context["access_action_id"]]
        objective = objectives.get(context["id"])
        item_observation = _item_observation(context, account_state)
        encounter = _encounter_context(context, account_state)
        gaps: list[dict[str, str]] = []
        if access["status"] != "eligible":
            gaps.append({"group": "formal_access", "detail": "Normalized access action is not currently eligible."})
        if snapshot is None:
            gaps.append({"group": "combat_snapshot", "detail": "No player-recorded combat readiness snapshot is available."})
        if not encounter["present"]:
            gaps.append({"group": "encounter_observation", "detail": "No player-recorded encounter observation is available for this source."})
        if objective is None:
            gaps.append({"group": "objective", "detail": "No explicit player objective selects this RNG bypass."})

        status = _decision_status(access, objective, item_observation, snapshot is not None, encounter["present"])
        report.append({
            "bypass_id": context["id"],
            "name": context["name"],
            "fact_ids": [context["bypass_fact_id"], "drop-bypass-readiness"],
            "factual_access": {
                "action_id": context["access_action_id"],
                "status": access["status"],
                "missing": copy.deepcopy(access["missing"]),
                "missing_preparation": copy.deepcopy(access["missing_preparation"]),
            },
            "normal_path": copy.deepcopy(context["normal_path"]),
            "selected_rng_bypass": {
                "benefit_if_drop_observed": context["bypass_benefit"],
                "displaced_requirement_or_benefit": context["normal_path"]["displaced_requirement_or_benefit"],
                "drop_probability_context": _probability_context(path, probability_model),
            },
            "explicit_objective": {"status": "recorded" if objective is not None else "unselected", "value": objective},
            "combat_snapshot": {
                "present": snapshot is not None,
                "observed_at": snapshot["observed_at"] if snapshot is not None else None,
                "readiness_inferred": False,
            },
            "encounter_observation": encounter,
            "item_observation": item_observation,
            "observed_readiness_gaps": gaps,
            "throughput_unknowns": copy.deepcopy(path.get("time_estimate_unknowns", [])),
            "throughput_or_completion_time_inferred": False,
            "timing_status": status,
            "recommended_by_default": False,
            "route_order_selected": False,
            "stop_conditions": copy.deepcopy(context["stop_conditions"]),
            "reentry_conditions": copy.deepcopy(context["reentry_conditions"]),
            "source_ids": copy.deepcopy(context["source_ids"]),
        })

    return {
        "bypasses": report,
        "policy_reference": context_document["policy_reference"],
        "inference_guarantees": {
            "rare_drop_recommended_by_default": False,
            "kills_inferred": False,
            "kills_per_hour_inferred": False,
            "expected_completion_time_inferred": False,
            "drops_inferred": False,
            "combat_readiness_inferred": False,
            "route_selected": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report bounded monster-drop bypass timing context.")
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument("--contexts", default=DEFAULT_CONTEXTS, type=Path)
    parser.add_argument("--research", default=DEFAULT_RESEARCH, type=Path)
    parser.add_argument("--readiness-facts", default=DEFAULT_READINESS_FACTS, type=Path)
    parser.add_argument("--objectives", type=Path, help="Optional JSON object mapping bypass IDs to explicit objectives.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    objectives = load_json(args.objectives) if args.objectives else None
    report = analyze_monster_drop_bypass_timing(
        load_json(args.state), load_json(args.actions), load_json(args.contexts), load_json(args.research),
        load_json(args.readiness_facts), objectives,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for item in report["bypasses"]:
            print(f"{item['name']}: {item['timing_status']} ({item['factual_access']['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
