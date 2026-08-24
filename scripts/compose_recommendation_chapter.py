from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from analyze_passive_status import analyze_passive_status
from analyze_quest_xp_timing import DEFAULT_EDGES, DEFAULT_NODES, analyze_quest_xp_timing
from evaluate_progression import DEFAULT_ACTIONS, DEFAULT_STATE, evaluate_actions, load_json, validate_account_state
from score_candidates import DEFAULT_CANDIDATES, score_candidates


AFK_MODES = ("true_afk", "low_attention", "semi_afk")
DEFAULT_ACTIVE_LIMIT = 5
DEFAULT_AFK_LIMIT = 5


def _validate_limit(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _scenario_state(account_state: dict[str, Any], attention_mode: str) -> dict[str, Any]:
    """Copy a snapshot and alter only the attention label used for one ranking scenario."""
    scenario = copy.deepcopy(account_state)
    scenario["attention_window"]["mode"] = attention_mode
    return scenario


def _preparation_gaps(evaluated_actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "action_id": action["id"],
            "name": action["name"],
            "kind": action["kind"],
            "fact_ids": action["fact_ids"],
            "missing_preparation": action["missing_preparation"],
        }
        for action in evaluated_actions
        if action["status"] == "needs_preparation"
    ]


def _eligible_unscored_gaps(
    evaluated_actions: list[dict[str, Any]], ranked_candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    scored_ids = {candidate["action_id"] for candidate in ranked_candidates}
    return [
        {
            "action_id": action["id"],
            "name": action["name"],
            "kind": action["kind"],
            "fact_ids": action["fact_ids"],
        }
        for action in evaluated_actions
        if action["status"] == "eligible" and action["id"] not in scored_ids
    ]


def compose_recommendation_chapter(
    account_state: dict[str, Any],
    actions_document: dict[str, Any],
    candidates_document: dict[str, Any],
    nodes_document: dict[str, Any],
    edges_document: dict[str, Any],
    *,
    active_limit: int = DEFAULT_ACTIVE_LIMIT,
    afk_limit: int = DEFAULT_AFK_LIMIT,
    afk_mode: str = "low_attention",
) -> dict[str, Any]:
    """Compose bounded recommendation options without selecting or applying an action."""
    validate_account_state(account_state)
    _validate_limit(active_limit, "active_limit")
    _validate_limit(afk_limit, "afk_limit")
    if afk_mode not in AFK_MODES:
        raise ValueError(f"afk_mode must be one of: {', '.join(AFK_MODES)}")

    evaluated_actions = evaluate_actions(actions_document, account_state)
    active_ranked = score_candidates(
        candidates_document, actions_document, _scenario_state(account_state, "active")
    )
    afk_ranked = score_candidates(
        candidates_document, actions_document, _scenario_state(account_state, afk_mode)
    )
    passive_status = analyze_passive_status(account_state)
    quest_xp_timing = analyze_quest_xp_timing(
        account_state, actions_document, nodes_document, edges_document
    )

    return {
        "chapter_type": "recommendation_options",
        "lanes": {
            "active": {
                "scenario": True,
                "attention_mode": "active",
                "limit": active_limit,
                "ranked_options": active_ranked[:active_limit],
            },
            "afk_or_low_attention": {
                "scenario": True,
                "attention_mode": afk_mode,
                "limit": afk_limit,
                "afk_fit_filter": "afk_fit > 0",
                "ranked_options": [
                    candidate
                    for candidate in afk_ranked
                    if candidate["dimension_breakdown"]["afk_fit"] > 0
                ][:afk_limit],
            },
        },
        "passive_and_recurring_check_ins": {
            "explicit_observations": passive_status["explicit_observations"],
            "established_systems_without_observation": passive_status[
                "established_systems_without_observation"
            ],
            "elapsed_time_inferred": passive_status["elapsed_time_inferred"],
        },
        "quest_xp_timing_opportunities": quest_xp_timing["quest_xp_timing_inputs"],
        "gaps": {
            "preparation": _preparation_gaps(evaluated_actions),
            "eligible_unscored": _eligible_unscored_gaps(evaluated_actions, active_ranked),
        },
        "boundaries": {
            "route_selected": False,
            "action_selected": False,
            "action_completion_simulated": False,
            "elapsed_time_inferred": False,
            "random_outputs_inferred": False,
            "combat_wins_inferred": False,
            "minigame_outputs_inferred": False,
            "account_state_mutated": False,
        },
    }


def _print_human_chapter(chapter: dict[str, Any]) -> None:
    print("Recommendation options only. No action is selected or applied.")
    for lane_name, lane in chapter["lanes"].items():
        print(f"\n{lane_name} ({lane['attention_mode']} scenario):")
        if not lane["ranked_options"]:
            print("  no scored eligible options")
        for option in lane["ranked_options"]:
            print(f"  [{option['total_score']}] {option['name']}")
            print(f"    stop: {option['stop_condition']}")
            print(f"    re-entry: {option['reentry_condition']}")

    check_ins = chapter["passive_and_recurring_check_ins"]
    print(f"\nExplicit passive check-ins: {len(check_ins['explicit_observations'])}")
    print(f"Preparation gaps: {len(chapter['gaps']['preparation'])}")
    print(f"Eligible unscored gaps: {len(chapter['gaps']['eligible_unscored'])}")
    print(f"Quest-XP timing opportunities: {len(chapter['quest_xp_timing_opportunities'])}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compose active and AFK recommendation options without selecting a route or applying actions."
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES, type=Path)
    parser.add_argument("--nodes", default=DEFAULT_NODES, type=Path)
    parser.add_argument("--edges", default=DEFAULT_EDGES, type=Path)
    parser.add_argument("--active-limit", default=DEFAULT_ACTIVE_LIMIT, type=int)
    parser.add_argument("--afk-limit", default=DEFAULT_AFK_LIMIT, type=int)
    parser.add_argument("--afk-mode", choices=AFK_MODES, default="low_attention")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    try:
        chapter = compose_recommendation_chapter(
            load_json(args.state),
            load_json(args.actions),
            load_json(args.candidates),
            load_json(args.nodes),
            load_json(args.edges),
            active_limit=args.active_limit,
            afk_limit=args.afk_limit,
            afk_mode=args.afk_mode,
        )
    except ValueError as error:
        parser.error(str(error))

    if args.json:
        print(json.dumps(chapter, indent=2))
    else:
        _print_human_chapter(chapter)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
