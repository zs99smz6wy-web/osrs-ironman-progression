from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analyze_transport_bundles import (
    DEFAULT_TRANSPORT_BUNDLES,
    analyze_transport_bundles,
    contextual_bonus_by_action,
)
from analyze_combat_quest_readiness import (
    DEFAULT_CONTEXTS as DEFAULT_COMBAT_QUEST_CONTEXTS,
    analyze_combat_quest_readiness,
)
from evaluate_progression import DEFAULT_ACTIONS, DEFAULT_STATE, evaluate_actions, load_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "strategy" / "candidates.json"
POSITIVE_DIMENSIONS = (
    "lifetime_utility",
    "content_unlock",
    "economic_infrastructure",
    "multi_output",
    "diversity",
    "afk_fit",
)
COST_DIMENSIONS = ("detour_cost", "burnout_risk", "danger_risk")
ALL_DIMENSIONS = POSITIVE_DIMENSIONS + COST_DIMENSIONS


def _score_dimension_breakdown(dimensions: dict[str, Any]) -> dict[str, int]:
    if set(dimensions) != set(ALL_DIMENSIONS):
        missing = sorted(set(ALL_DIMENSIONS) - set(dimensions))
        unexpected = sorted(set(dimensions) - set(ALL_DIMENSIONS))
        raise ValueError(f"Candidate dimensions must be exactly {ALL_DIMENSIONS}; missing={missing}, unexpected={unexpected}")

    breakdown: dict[str, int] = {}
    for dimension in POSITIVE_DIMENSIONS:
        value = dimensions[dimension]
        if not isinstance(value, int) or not 0 <= value <= 4:
            raise ValueError(f"{dimension} must be an integer from 0 to 4")
        breakdown[dimension] = value
    for dimension in COST_DIMENSIONS:
        value = dimensions[dimension]
        if not isinstance(value, int) or not 0 <= value <= 4:
            raise ValueError(f"{dimension} must be an integer from 0 to 4")
        breakdown[dimension] = -value
    return breakdown


def _preference_adjustments(dimensions: dict[str, Any], account_state: dict[str, Any]) -> dict[str, int]:
    preferences = account_state.get("preferences", {})
    attention_mode = account_state.get("attention_window", {}).get("mode", "active")
    diversity_preference = preferences.get("diversity_preference", 0)
    intensity_tolerance = preferences.get("intensity_tolerance", 0)
    risk_tolerance = preferences.get("risk_tolerance", 0)

    if not isinstance(diversity_preference, int) or not 0 <= diversity_preference <= 4:
        raise ValueError("preferences.diversity_preference must be an integer from 0 to 4")
    if not isinstance(intensity_tolerance, int) or not 0 <= intensity_tolerance <= 4:
        raise ValueError("preferences.intensity_tolerance must be an integer from 0 to 4")
    if not isinstance(risk_tolerance, int) or not 0 <= risk_tolerance <= 4:
        raise ValueError("preferences.risk_tolerance must be an integer from 0 to 4")

    afk_fit = dimensions["afk_fit"]
    attention_adjustment = {
        "true_afk": afk_fit,
        "low_attention": afk_fit // 2,
        "semi_afk": 0,
        "active": 0,
    }.get(attention_mode)
    if attention_adjustment is None:
        raise ValueError(f"Unknown attention_window.mode: {attention_mode}")

    return {
        "attention_window": attention_adjustment,
        "diversity_preference": (diversity_preference * dimensions["diversity"]) // 4,
        "intensity_tolerance": min(intensity_tolerance, dimensions["burnout_risk"]),
        "risk_tolerance": min(risk_tolerance, dimensions["danger_risk"]),
    }


def _evaluated_actions_and_annotations(
    candidates_document: dict[str, Any], actions_document: dict[str, Any], account_state: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Evaluate factual actions and validate the strategic annotations that name them."""
    evaluated = evaluate_actions(actions_document, account_state)
    evaluated_ids = {result["id"] for result in evaluated}

    annotations = candidates_document["candidates"]
    annotation_ids = [annotation["action_id"] for annotation in annotations]
    if len(annotation_ids) != len(set(annotation_ids)):
        raise ValueError("Candidate action_id values must be unique")
    unexpected = sorted(set(annotation_ids) - evaluated_ids)
    if unexpected:
        raise ValueError(
            "Candidate annotations must refer to normalized factual actions; "
            f"unexpected={unexpected}"
        )
    return evaluated, annotations


def _rank_eligible_annotations(
    annotations: list[dict[str, Any]],
    evaluated: list[dict[str, Any]],
    account_state: dict[str, Any],
    transport_bundles: list[dict[str, Any]],
    combat_quest_contexts: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    eligible = {result["id"]: result for result in evaluated if result["status"] == "eligible"}
    transport_bonus_by_action = contextual_bonus_by_action(transport_bundles)
    transport_component_by_action = {
        component["action_id"]: {
            "bundle_id": bundle["id"],
            "bundle_name": bundle["name"],
            "component_id": component["id"],
            "component_name": component["name"],
            "benefit_id": component["benefit_id"],
            "payoff_kind": component["payoff_kind"],
            "status": component["status"],
            "payoff_note": component["payoff_note"],
            "usage_caveat": component["usage_caveat"],
        }
        for bundle in transport_bundles
        for component in bundle["components"]
    }
    ranked: list[dict[str, Any]] = []
    for annotation in annotations:
        action_id = annotation["action_id"]
        if action_id not in eligible:
            continue

        dimensions = annotation["dimensions"]
        dimension_breakdown = _score_dimension_breakdown(dimensions)
        adjustments = _preference_adjustments(dimensions, account_state)
        contextual_adjustments = {
            "early_transport_bundle": transport_bonus_by_action.get(action_id, 0)
        }
        base_score = sum(value for key, value in dimension_breakdown.items() if key != "afk_fit")
        total_score = base_score + sum(adjustments.values()) + sum(contextual_adjustments.values())
        evaluated_action = eligible[action_id]
        ranked.append(
            {
                "action_id": action_id,
                "name": evaluated_action["name"],
                "kind": evaluated_action["kind"],
                "fact_ids": evaluated_action["fact_ids"],
                "dimension_breakdown": dimension_breakdown,
                "adjustments": adjustments,
                "contextual_adjustments": contextual_adjustments,
                "transport_bundle_context": transport_component_by_action.get(action_id),
                "formal_eligibility": "eligible",
                "practical_readiness_context": combat_quest_contexts.get(action_id),
                "base_score": base_score,
                "total_score": total_score,
                "stop_condition": annotation["stop_condition"],
                "reentry_condition": annotation["reentry_condition"],
            }
        )
    return sorted(ranked, key=lambda candidate: (-candidate["total_score"], candidate["name"]))


def score_candidates(
    candidates_document: dict[str, Any], actions_document: dict[str, Any], account_state: dict[str, Any]
) -> list[dict[str, Any]]:
    """Rank eligible factual actions that have a strategic annotation."""
    evaluated, annotations = _evaluated_actions_and_annotations(
        candidates_document, actions_document, account_state
    )
    transport_bundles = analyze_transport_bundles(
        load_json(DEFAULT_TRANSPORT_BUNDLES), evaluated, account_state
    )
    combat_quest_contexts = analyze_combat_quest_readiness(
        load_json(DEFAULT_COMBAT_QUEST_CONTEXTS), actions_document, account_state
    )
    return _rank_eligible_annotations(
        annotations, evaluated, account_state, transport_bundles, combat_quest_contexts
    )


def _eligible_unscored_actions(
    evaluated: list[dict[str, Any]], annotations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    annotated_ids = {annotation["action_id"] for annotation in annotations}
    return [
        {
            "id": action["id"],
            "name": action["name"],
            "kind": action["kind"],
            "fact_ids": action["fact_ids"],
            "status": action["status"],
        }
        for action in evaluated
        if action["status"] == "eligible" and action["id"] not in annotated_ids
    ]


def _result_document(
    candidates_document: dict[str, Any], actions_document: dict[str, Any], account_state: dict[str, Any]
) -> dict[str, Any]:
    evaluated, annotations = _evaluated_actions_and_annotations(
        candidates_document, actions_document, account_state
    )
    transport_bundles = analyze_transport_bundles(
        load_json(DEFAULT_TRANSPORT_BUNDLES), evaluated, account_state
    )
    combat_quest_contexts = analyze_combat_quest_readiness(
        load_json(DEFAULT_COMBAT_QUEST_CONTEXTS), actions_document, account_state
    )
    ranked = _rank_eligible_annotations(
        annotations, evaluated, account_state, transport_bundles, combat_quest_contexts
    )
    return {
        "formula": {
            "base_score": "sum(lifetime_utility, content_unlock, economic_infrastructure, multi_output, diversity) - detour_cost - burnout_risk - danger_risk; afk_fit is applied only by attention_window",
            "attention_window": "true_afk adds afk_fit; low_attention adds floor(afk_fit / 2); semi_afk and active add 0",
            "diversity_preference": "floor(preferences.diversity_preference * diversity / 4)",
            "intensity_tolerance": "min(preferences.intensity_tolerance, burnout_risk), reducing the practical penalty of a tolerated repetitive activity",
            "risk_tolerance": "min(preferences.risk_tolerance, danger_risk), reducing the practical penalty of danger the player explicitly accepts",
            "early_transport_bundle": "a bounded 0 or 1 strategic context point for an eligible distinct durable transport capability while that bundle remains incomplete; replenishable transport items score 0",
            "combat_quest_readiness": "a sourced strategy-only context appended after factual eligibility and scoring; it never adds a hard gate or score adjustment",
        },
        "transport_bundles": transport_bundles,
        "ranked_eligible_candidates": ranked,
        "eligible_unscored_actions": _eligible_unscored_actions(evaluated, annotations),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rank eligible progression pilot actions using transparent strategic annotations."
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES, type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    result = _result_document(load_json(args.candidates), load_json(args.actions), load_json(args.state))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    print("Strategic ranking of evaluator-eligible actions only.")
    print("Hard requirements remain in scripts/evaluate_progression.py and are not rescored here.")
    for candidate in result["ranked_eligible_candidates"]:
        print(f"\n[{candidate['total_score']}] {candidate['name']} ({candidate['action_id']})")
        print(
            f"  base: {candidate['base_score']}; adjustments: {candidate['adjustments']}; "
            f"context: {candidate['contextual_adjustments']}"
        )
        print(f"  dimensions: {candidate['dimension_breakdown']}")
        if candidate["transport_bundle_context"]:
            context = candidate["transport_bundle_context"]
            print(f"  transport bundle: {context['component_name']} ({context['payoff_kind']})")
            print(f"    payoff: {context['payoff_note']}")
        print(f"  stop: {candidate['stop_condition']}")
        print(f"  re-entry: {candidate['reentry_condition']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
