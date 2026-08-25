from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from evaluate_progression import DEFAULT_ACTIONS, DEFAULT_STATE, evaluate_actions, load_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "strategy" / "content-window-catalog.json"
DEFAULT_PROFILE = ROOT / "strategy" / "default-guide-objective-profile.json"
ATTENTION_MODES = {"active", "semi_afk", "low_attention", "true_afk"}
CONTEXT_FIELDS = {
    "attention_mode",
    "declared_purpose_ids",
    "ideal_trigger_ids",
    "prior_stop_window_ids",
    "reentry_trigger_ids",
}


def _unique_trimmed_strings(values: Any, label: str) -> list[str]:
    if (
        not isinstance(values, list)
        or any(not isinstance(value, str) or not value.strip() or value != value.strip() for value in values)
        or len(values) != len(set(values))
    ):
        raise ValueError(f"{label} must be an array of unique non-empty trimmed strings")
    return values


def validate_decision_context(context: dict[str, Any]) -> None:
    if not isinstance(context, dict) or set(context) != CONTEXT_FIELDS:
        raise ValueError(f"Decision context fields must be exactly {sorted(CONTEXT_FIELDS)}")
    for field in CONTEXT_FIELDS - {"attention_mode"}:
        _unique_trimmed_strings(context[field], f"Decision context {field}")
    if context["attention_mode"] is not None and context["attention_mode"] not in ATTENTION_MODES:
        raise ValueError("Decision context attention_mode must be null or a supported attention mode")


def empty_decision_context() -> dict[str, Any]:
    return {
        "attention_mode": None,
        "declared_purpose_ids": [],
        "ideal_trigger_ids": [],
        "prior_stop_window_ids": [],
        "reentry_trigger_ids": [],
    }


def validate_profile(profile: dict[str, Any]) -> dict[str, int]:
    try:
        weights = profile["universal_defaults"]["priority_weights"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Objective profile must define universal_defaults.priority_weights") from exc
    if not isinstance(weights, dict) or not weights:
        raise ValueError("Objective profile priority_weights must be a non-empty object")
    for key, value in weights.items():
        if not isinstance(key, str) or not key.strip() or key != key.strip():
            raise ValueError("Objective profile has an invalid priority tag")
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 4:
            raise ValueError(f"Objective profile priority {key} must be an integer from 0 to 4")
    return weights


def validate_catalog(
    catalog: dict[str, Any], actions_document: dict[str, Any], priority_weights: dict[str, int]
) -> None:
    if catalog.get("schema_version") != 1 or not isinstance(catalog.get("windows"), list):
        raise ValueError("Content-window catalog must use schema_version 1 and contain windows")

    action_ids = [action.get("id") for action in actions_document.get("actions", [])]
    known_actions = set(action_ids)
    if len(action_ids) != len(known_actions):
        raise ValueError("Normalized action IDs must be unique")

    expected_fields = {
        "window_id",
        "action_id",
        "domain",
        "priority_tags",
        "purpose_ids",
        "ideal_trigger_ids",
        "attention_modes",
        "stop_condition",
        "reentry_condition",
    }
    seen_windows: set[str] = set()
    seen_actions: set[str] = set()
    for index, window in enumerate(catalog["windows"]):
        label = f"Content-window catalog windows[{index}]"
        if not isinstance(window, dict) or set(window) != expected_fields:
            raise ValueError(f"{label} fields must be exactly {sorted(expected_fields)}")
        for field in ("window_id", "action_id", "domain", "stop_condition", "reentry_condition"):
            value = window[field]
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError(f"{label}.{field} must be a non-empty trimmed string")
        if window["window_id"] in seen_windows:
            raise ValueError("Content-window catalog window IDs must be unique")
        if window["action_id"] in seen_actions:
            raise ValueError("Content-window catalog action IDs must be unique")
        if window["action_id"] not in known_actions:
            raise ValueError(f"Unknown content-window action ID: {window['action_id']}")
        seen_windows.add(window["window_id"])
        seen_actions.add(window["action_id"])

        for field in ("priority_tags", "purpose_ids", "ideal_trigger_ids", "attention_modes"):
            _unique_trimmed_strings(window[field], f"{label}.{field}")
        unknown_tags = sorted(set(window["priority_tags"]) - set(priority_weights))
        if unknown_tags:
            raise ValueError(f"{label} has unknown priority tags: {unknown_tags}")
        if not window["purpose_ids"]:
            raise ValueError(f"{label}.purpose_ids must not be empty")
        invalid_attention = sorted(set(window["attention_modes"]) - ATTENTION_MODES)
        if invalid_attention or not window["attention_modes"]:
            raise ValueError(f"{label}.attention_modes contains invalid values: {invalid_attention}")


def _classify_window(
    window: dict[str, Any],
    action: dict[str, Any],
    account_state: dict[str, Any],
    context: dict[str, Any],
) -> tuple[str, str, list[str], list[str]]:
    declared_purposes = set(context["declared_purpose_ids"])
    ideal_triggers = set(context["ideal_trigger_ids"])
    reentry_triggers = set(context["reentry_trigger_ids"])
    purpose_evidence = sorted(declared_purposes.intersection(window["purpose_ids"]))
    ideal_evidence = sorted(ideal_triggers.intersection(window["ideal_trigger_ids"]))
    reentry_evidence = sorted(
        reentry_triggers.intersection(set(window["purpose_ids"]) | set(window["ideal_trigger_ids"]))
    )
    prior_stop = window["window_id"] in context["prior_stop_window_ids"]

    if prior_stop and reentry_evidence and action["status"] in {"eligible", "completed"}:
        return "reentry_candidate", "confirmed", ideal_evidence, reentry_evidence
    if action["status"] == "completed":
        return "stop_reached", "confirmed" if purpose_evidence else "unconfirmed", ideal_evidence, []
    if action["status"] == "blocked":
        return "blocked", "confirmed" if purpose_evidence else "unconfirmed", ideal_evidence, []

    attention_mode = context["attention_mode"] or account_state["attention_window"]["mode"]
    purpose_status = "confirmed" if purpose_evidence else "unconfirmed"
    if action["status"] == "needs_preparation" or not purpose_evidence or attention_mode not in window["attention_modes"]:
        return "accessible_not_ready", purpose_status, ideal_evidence, []
    if ideal_evidence:
        return "ideal_candidate", purpose_status, ideal_evidence, []
    return "ready_candidate", purpose_status, [], []


def evaluate_content_windows(
    catalog: dict[str, Any],
    profile: dict[str, Any],
    actions_document: dict[str, Any],
    account_state: dict[str, Any],
    decision_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = empty_decision_context() if decision_context is None else decision_context
    validate_decision_context(context)
    priority_weights = validate_profile(profile)
    validate_catalog(catalog, actions_document, priority_weights)

    evaluated = {action["id"]: action for action in evaluate_actions(actions_document, account_state)}
    rows: list[dict[str, Any]] = []
    for window in catalog["windows"]:
        action = evaluated[window["action_id"]]
        classification, purpose_status, ideal_evidence, reentry_evidence = _classify_window(
            window, action, account_state, context
        )
        tag_weights = {tag: priority_weights[tag] for tag in window["priority_tags"]}
        readiness_gaps: list[str] = []
        if purpose_status == "unconfirmed" and action["status"] not in {"blocked", "completed"}:
            readiness_gaps.append("no declared purpose matches this window")
        effective_attention = context["attention_mode"] or account_state["attention_window"]["mode"]
        if effective_attention not in window["attention_modes"]:
            readiness_gaps.append(
                f"attention mode {effective_attention} is not supported"
            )
        if action["status"] == "needs_preparation":
            readiness_gaps.append("normalized preparation is incomplete")

        rows.append(
            {
                "window_id": window["window_id"],
                "action_id": action["id"],
                "name": action["name"],
                "domain": window["domain"],
                "classification": classification,
                "factual_action_status": action["status"],
                "missing_hard_requirements": action["missing"],
                "missing_preparation": action["missing_preparation"],
                "purpose_status": purpose_status,
                "matched_purpose_ids": sorted(
                    set(context["declared_purpose_ids"]).intersection(window["purpose_ids"])
                ),
                "ideal_trigger_evidence": ideal_evidence,
                "reentry_trigger_evidence": reentry_evidence,
                "profile_priority_weights": tag_weights,
                "profile_priority_max": max(tag_weights.values()),
                "readiness_gaps": readiness_gaps,
                "stop_condition": window["stop_condition"],
                "reentry_condition": window["reentry_condition"],
                "fact_ids": action["fact_ids"],
            }
        )

    counts = Counter(row["classification"] for row in rows)
    return {
        "schema_version": 1,
        "profile_id": profile.get("id"),
        "scope": "bounded content-window evaluation",
        "effective_attention_mode": context["attention_mode"] or account_state["attention_window"]["mode"],
        "route_selected": False,
        "objectives": rows,
        "summary": {
            "counts_by_classification": dict(sorted(counts.items())),
            "window_count": len(rows),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify a bounded set of content windows without selecting a route."
    )
    parser.add_argument("account_state", nargs="?", type=Path, default=DEFAULT_STATE)
    parser.add_argument("decision_context", nargs="?", type=Path)
    parser.add_argument("--actions", type=Path, default=DEFAULT_ACTIONS)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    args = parser.parse_args()

    context = load_json(args.decision_context) if args.decision_context else empty_decision_context()
    result = evaluate_content_windows(
        load_json(args.catalog),
        load_json(args.profile),
        load_json(args.actions),
        load_json(args.account_state),
        context,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
