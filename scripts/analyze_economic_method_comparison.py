"""Compare bounded economic-method context against a supplied account state."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Iterable

from analyze_cash_commitments import analyze_cash_commitments
from evaluate_progression import DEFAULT_ACTIONS, DEFAULT_STATE, evaluate_actions, load_json, validate_account_state


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESEARCH = ROOT / "research" / "economic-method-comparison.json"
DEFAULT_CONTEXT = ROOT / "strategy" / "economic-method-comparison-contexts.json"
DEFAULT_FACTS = ROOT / "data" / "facts" / "economic-bottlenecks.json"


def _predicates(condition: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Flatten predicates for display; evaluator status remains authoritative for all/any logic."""
    if "all" in condition or "any" in condition:
        key = "all" if "all" in condition else "any"
        for child in condition[key]:
            yield from _predicates(child)
        return
    yield condition


def _observed_value(predicate: dict[str, Any], state: dict[str, Any]) -> Any:
    kind = predicate["type"]
    key = predicate["key"]
    if kind == "skill_at_least":
        return state["skills"].get(key)
    if kind == "quest_completed":
        return key in state["quests_completed"]
    if kind == "milestone":
        return key in state["milestones"]
    if kind == "transport_flag":
        return key in state["transport_flags"]
    if kind == "item_at_least":
        return state["items"].get(key, 0)
    if kind == "resource_at_least":
        return state["resources"].get(key, 0)
    if kind == "counter_at_least":
        return state["counters"].get(key, 0)
    if kind == "passive_loop":
        return state["passive_loops"].get(key, False)
    return None


def _requirement_signals(condition: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "type": predicate["type"],
            "key": predicate["key"],
            "required_value": predicate.get("value", True),
            "observed_value": _observed_value(predicate, state),
        }
        for predicate in _predicates(condition)
    ]


def _attention_fit(state: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    window = state["attention_window"]
    requires_present = profile["requires_player_present"]
    player_present = window["player_present"]
    mode = window["mode"]
    allowed_modes = profile["allowed_attention_modes"]
    return {
        "attention_profile": profile["attention_profile"],
        "observed_mode": mode,
        "observed_duration_minutes": window["duration_minutes"],
        "player_present_observed": player_present,
        "allowed_attention_modes": copy.deepcopy(allowed_modes),
        "requires_player_present": requires_present,
        "fit": (not requires_present or player_present) and mode in allowed_modes,
        "attention_assumption_inferred": False,
    }


def _funding_target(cash_report: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (
            copy.deepcopy(commitment)
            for commitment in cash_report["ordered_commitments"]
            if commitment["cumulative_shortfall"] > 0
        ),
        None,
    )


def _economic_fact_map(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {record["id"]: record for record in document["records"]}


def _method_report(
    method: dict[str, Any],
    action: dict[str, Any],
    action_result: dict[str, Any],
    fact: dict[str, Any],
    profile: dict[str, Any],
    account_state: dict[str, Any],
    funding_target: dict[str, Any] | None,
) -> dict[str, Any]:
    attention = _attention_fit(account_state, profile)
    if funding_target is None:
        comparison_status = "no_declared_unfunded_commitment"
    elif action_result["status"] == "blocked":
        comparison_status = "blocked_factual_access"
    elif action_result["status"] == "needs_preparation":
        comparison_status = "needs_factual_preparation"
    elif not attention["fit"]:
        comparison_status = "attention_mismatch"
    else:
        comparison_status = "comparison_candidate"

    return {
        "id": method["id"],
        "action_id": action["id"],
        "action_name": action["name"],
        "economic_fact_id": fact["id"],
        "fact_source_ids": copy.deepcopy(fact["source_ids"]),
        "comparison_status": comparison_status,
        "factual_access": {
            "action_status": action_result["status"],
            "hard_requirements": copy.deepcopy(action["requirements"]),
            "requirement_signals": _requirement_signals(action["requirements"], account_state),
            "missing_hard_access": copy.deepcopy(action_result["missing"]),
            "hard_access_inferred": False,
        },
        "factual_preparation": {
            "preparation_requirements": copy.deepcopy(action["preparation"]),
            "preparation_signals": _requirement_signals(action["preparation"], account_state),
            "missing_preparation": copy.deepcopy(action_result["missing_preparation"]),
            "preparation_inferred": False,
        },
        "output_boundary": {
            "summary": method["output_boundary"],
            "reported_action_effects": copy.deepcopy(action["transition"]["reported_effects"]),
            "payout_or_mechanics": copy.deepcopy(fact.get("payout", fact.get("mechanics", {}))),
            "community_rate_estimates_used": False,
            "gp_rate_inferred": False,
            "session_output_inferred": False,
        },
        "secondary_benefits": {
            "documented_fact_outputs": copy.deepcopy(fact.get("side_outputs", [])),
            "strategy_benefit_categories": copy.deepcopy(profile["secondary_benefit_categories"]),
            "benefit_received_inferred": False,
        },
        "attention_fit": attention,
        "stop_reentry": {
            "named_funding_commitment": copy.deepcopy(funding_target),
            "stop_or_reassess_when": (
                profile["stop_reentry"] if funding_target is not None
                else "No named unfunded commitment is declared, so this package has no funding stop target."
            ),
            "reentry_when": (
                "A later account snapshot declares an unfunded commitment and factual access, preparation, and attention are reconsidered."
            ),
            "commitment_funded_inferred": False,
        },
        "method_selected": False,
    }


def analyze_economic_method_comparison(
    account_state: dict[str, Any],
    actions_document: dict[str, Any],
    research_package: dict[str, Any],
    strategy_context: dict[str, Any],
    facts_document: dict[str, Any],
) -> dict[str, Any]:
    """Describe possible funding methods without forecasting or selecting one."""
    validate_account_state(account_state)
    cash_report = analyze_cash_commitments(account_state)
    actions = {action["id"]: action for action in actions_document["actions"]}
    action_results = {result["id"]: result for result in evaluate_actions(actions_document, account_state)}
    facts = _economic_fact_map(facts_document)
    funding_target = _funding_target(cash_report)
    reports = []
    for method in research_package["methods"]:
        action = actions.get(method["action_id"])
        fact = facts.get(method["economic_fact_id"])
        profile = strategy_context["methods"].get(method["id"])
        if action is None or fact is None or profile is None:
            raise ValueError(f"Economic method mapping is incomplete for {method['id']}")
        reports.append(_method_report(method, action, action_results[action["id"]], fact, profile, account_state, funding_target))

    return {
        "package_id": research_package["research_id"],
        "commitment_pressure": {
            **copy.deepcopy(cash_report),
            "named_unfunded_commitment": funding_target,
            "status": (
                "no_declared_commitments" if not cash_report["ordered_commitments"]
                else "all_declared_commitments_observed_funded" if funding_target is None
                else "named_unfunded_commitment_observed"
            ),
        },
        "method_comparisons": reports,
        "inference_guarantees": {
            **copy.deepcopy(strategy_context["comparison_boundaries"]),
            "route_selected": False,
            "account_state_mutated": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare bounded economic method context without inferring GP, outputs, or a selected method."
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument("--research", default=DEFAULT_RESEARCH, type=Path)
    parser.add_argument("--context", default=DEFAULT_CONTEXT, type=Path)
    parser.add_argument("--facts", default=DEFAULT_FACTS, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()
    report = analyze_economic_method_comparison(
        load_json(args.state), load_json(args.actions), load_json(args.research), load_json(args.context), load_json(args.facts)
    )
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    pressure = report["commitment_pressure"]
    print(f"Commitment pressure: {pressure['status']}")
    print(f"Total shortfall: {pressure['total_shortfall']}")
    for method in report["method_comparisons"]:
        print(f"[{method['comparison_status'].upper()}] {method['action_name']}")
    print("Method selected: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
