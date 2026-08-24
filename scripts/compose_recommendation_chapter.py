from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from analyze_passive_status import analyze_passive_status
from analyze_quest_xp_timing import DEFAULT_EDGES, DEFAULT_NODES, analyze_quest_xp_timing
from analyze_quest_xp_thresholds import (
    DEFAULT_CONTEXT as DEFAULT_QUEST_XP_THRESHOLD_CONTEXT,
    DEFAULT_RESEARCH as DEFAULT_QUEST_XP_THRESHOLD_RESEARCH,
    analyze_quest_xp_thresholds,
)
from analyze_transport_bundles import DEFAULT_TRANSPORT_BUNDLES, analyze_transport_bundles
from analyze_sailing_economics import DEFAULT_CONTEXTS as DEFAULT_SAILING_ECONOMICS_CONTEXTS, analyze_sailing_economics
from analyze_durable_utility_items import DEFAULT_CONTEXTS as DEFAULT_DURABLE_UTILITY_CONTEXTS, analyze_durable_utility_items
from analyze_pvm_readiness import DEFAULT_CONTEXTS as DEFAULT_PVM_READINESS_CONTEXTS, analyze_pvm_readiness
from analyze_mastering_mixology import analyze_mastering_mixology
from analyze_void_elite_void_timing import analyze_void_elite_void_timing
from analyze_economic_method_comparison import (
    DEFAULT_CONTEXT as DEFAULT_ECONOMIC_CONTEXT,
    DEFAULT_FACTS as DEFAULT_ECONOMIC_FACTS,
    DEFAULT_RESEARCH as DEFAULT_ECONOMIC_RESEARCH,
    analyze_economic_method_comparison,
)
from analyze_monster_drop_bypass_timing import (
    DEFAULT_CONTEXTS as DEFAULT_BYPASS_CONTEXTS,
    DEFAULT_READINESS_FACTS as DEFAULT_BYPASS_READINESS_FACTS,
    DEFAULT_RESEARCH as DEFAULT_BYPASS_RESEARCH,
    analyze_monster_drop_bypass_timing,
)
from evaluate_progression import DEFAULT_ACTIONS, DEFAULT_STATE, evaluate_actions, load_json, validate_account_state
from score_candidates import DEFAULT_CANDIDATES, score_candidates


AFK_MODES = ("true_afk", "low_attention", "semi_afk")
DEFAULT_ACTIVE_LIMIT = 5
DEFAULT_AFK_LIMIT = 5
DEFAULT_PREPARATION_LIMIT = 5
DEFAULT_QUEST_XP_LIMIT = 5
DEFAULT_TRANSPORT_BUNDLE_LIMIT = 7
DEFAULT_VOID_STRATEGY_INTENT = {
    "objective": "elite_void_one_helmet",
    "veteran_wait": "prefer",
}


def _validate_limit(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _scenario_state(account_state: dict[str, Any], attention_mode: str) -> dict[str, Any]:
    """Copy a snapshot and alter only the attention label used for one ranking scenario."""
    scenario = copy.deepcopy(account_state)
    scenario["attention_window"]["mode"] = attention_mode
    return scenario


def _strategic_action_order(candidates_document: dict[str, Any]) -> dict[str, int]:
    """Keep the curated strategy subset ahead of unannotated preparation gaps."""
    return {
        candidate["action_id"]: index
        for index, candidate in enumerate(candidates_document["candidates"])
    }


def _preparation_gaps(
    evaluated_actions: list[dict[str, Any]], candidates_document: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    strategic_order = _strategic_action_order(candidates_document)
    all_gaps = [
        {
            "action_id": action["id"],
            "name": action["name"],
            "kind": action["kind"],
            "status": action["status"],
            "fact_ids": action["fact_ids"],
            "missing_preparation": action["missing_preparation"],
        }
        for action in evaluated_actions
        if action["status"] == "needs_preparation"
    ]
    all_gaps.sort(
        key=lambda gap: (
            0 if gap["action_id"] in strategic_order else 1,
            strategic_order.get(gap["action_id"], 0),
            gap["action_id"],
        )
    )
    strategic_total = sum(gap["action_id"] in strategic_order for gap in all_gaps)
    return all_gaps, {
        "prioritized_by": ["strategic_annotation", "annotation_order", "action_id"],
        "total_count": len(all_gaps),
        "strategically_annotated_total": strategic_total,
    }


def _quest_xp_priority(quest: dict[str, Any]) -> tuple[int, int, int, str]:
    levels_skipped = sum(skill["levels_skipped"] for skill in quest["skills"])
    requirements_crossed = sum(
        len(skill["modeled_requirements_crossed"]) for skill in quest["skills"]
    )
    return (
        0 if quest["status"] == "eligible" else 1,
        -levels_skipped,
        -requirements_crossed,
        quest["action_id"],
    )


def _quest_xp_opportunities(
    quest_xp_timing: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    opportunities = sorted(
        quest_xp_timing["quest_xp_timing_inputs"], key=_quest_xp_priority
    )
    eligible_count = sum(quest["status"] == "eligible" for quest in opportunities)
    return opportunities, {
        "prioritized_by": [
            "evaluator_status:eligible_before_needs_preparation",
            "levels_skipped_descending",
            "modeled_requirement_levels_crossed_descending",
            "action_id",
        ],
        "total_count": len(opportunities),
        "eligible_total": eligible_count,
        "needs_preparation_total": len(opportunities) - eligible_count,
    }


def _quest_xp_threshold_sequences(report: dict[str, Any]) -> list[dict[str, Any]]:
    status_order = {
        "do_now": 0,
        "gather_inputs": 1,
        "train_requirement": 2,
        "finish_quest_chain": 3,
        "completed": 4,
    }
    return sorted(
        report["quest_xp_timing_windows"],
        key=lambda quest: (
            status_order[quest["primary_timing_status"]],
            -sum(effect["levels_skipped"] for effect in quest["skill_effects"]),
            quest["action_id"],
        ),
    )


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


def _bounded_transport_bundles(
    bundles: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    bounded: list[dict[str, Any]] = []
    for bundle in bundles:
        result = copy.deepcopy(bundle)
        components = result["components"]
        result["components"] = components[:limit]
        result["component_coverage"] = {
            "limit": limit,
            "shown_count": len(result["components"]),
            "omitted_count": max(0, len(components) - limit),
        }
        bounded.append(result)
    return bounded


def compose_recommendation_chapter(
    account_state: dict[str, Any],
    actions_document: dict[str, Any],
    candidates_document: dict[str, Any],
    nodes_document: dict[str, Any],
    edges_document: dict[str, Any],
    *,
    active_limit: int = DEFAULT_ACTIVE_LIMIT,
    afk_limit: int = DEFAULT_AFK_LIMIT,
    preparation_limit: int = DEFAULT_PREPARATION_LIMIT,
    quest_xp_limit: int = DEFAULT_QUEST_XP_LIMIT,
    transport_bundle_limit: int = DEFAULT_TRANSPORT_BUNDLE_LIMIT,
    afk_mode: str = "low_attention",
    bypass_objectives: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Compose bounded recommendation options without selecting or applying an action."""
    validate_account_state(account_state)
    _validate_limit(active_limit, "active_limit")
    _validate_limit(afk_limit, "afk_limit")
    _validate_limit(preparation_limit, "preparation_limit")
    _validate_limit(quest_xp_limit, "quest_xp_limit")
    _validate_limit(transport_bundle_limit, "transport_bundle_limit")
    if afk_mode not in AFK_MODES:
        raise ValueError(f"afk_mode must be one of: {', '.join(AFK_MODES)}")

    evaluated_actions = evaluate_actions(actions_document, account_state)
    transport_bundles = _bounded_transport_bundles(
        analyze_transport_bundles(
            load_json(DEFAULT_TRANSPORT_BUNDLES), evaluated_actions, account_state
        ),
        transport_bundle_limit,
    )
    active_ranked = score_candidates(
        candidates_document, actions_document, _scenario_state(account_state, "active")
    )
    afk_ranked = score_candidates(
        candidates_document, actions_document, _scenario_state(account_state, afk_mode)
    )
    passive_status = analyze_passive_status(account_state)
    sailing_economics = analyze_sailing_economics(
        load_json(DEFAULT_SAILING_ECONOMICS_CONTEXTS), actions_document, account_state
    )
    durable_utility_items = analyze_durable_utility_items(
        load_json(DEFAULT_DURABLE_UTILITY_CONTEXTS), actions_document, evaluated_actions, account_state
    )
    pvm_readiness = analyze_pvm_readiness(
        load_json(DEFAULT_PVM_READINESS_CONTEXTS), actions_document, account_state
    )
    mastering_mixology_timing = analyze_mastering_mixology(account_state)
    void_elite_void_timing = analyze_void_elite_void_timing(
        account_state, DEFAULT_VOID_STRATEGY_INTENT
    )
    economic_method_comparison = analyze_economic_method_comparison(
        account_state,
        actions_document,
        load_json(DEFAULT_ECONOMIC_RESEARCH),
        load_json(DEFAULT_ECONOMIC_CONTEXT),
        load_json(DEFAULT_ECONOMIC_FACTS),
    )
    monster_drop_bypass_timing = analyze_monster_drop_bypass_timing(
        account_state,
        actions_document,
        load_json(DEFAULT_BYPASS_CONTEXTS),
        load_json(DEFAULT_BYPASS_RESEARCH),
        load_json(DEFAULT_BYPASS_READINESS_FACTS),
        bypass_objectives,
    )
    quest_xp_timing = analyze_quest_xp_timing(
        account_state, actions_document, nodes_document, edges_document
    )
    quest_xp_threshold_report = analyze_quest_xp_thresholds(
        account_state,
        actions_document,
        load_json(DEFAULT_QUEST_XP_THRESHOLD_RESEARCH),
        load_json(DEFAULT_QUEST_XP_THRESHOLD_CONTEXT),
    )
    preparation_gaps, preparation_coverage = _preparation_gaps(
        evaluated_actions, candidates_document
    )
    quest_xp_opportunities, quest_xp_coverage = _quest_xp_opportunities(quest_xp_timing)
    quest_xp_sequences = _quest_xp_threshold_sequences(quest_xp_threshold_report)
    preparation_coverage.update(
        {
            "limit": preparation_limit,
            "shown_count": len(preparation_gaps[:preparation_limit]),
            "omitted_count": max(0, len(preparation_gaps) - preparation_limit),
            "strategically_annotated_shown": sum(
                gap["action_id"] in _strategic_action_order(candidates_document)
                for gap in preparation_gaps[:preparation_limit]
            ),
        }
    )
    quest_xp_coverage.update(
        {
            "limit": quest_xp_limit,
            "shown_count": len(quest_xp_opportunities[:quest_xp_limit]),
            "omitted_count": max(0, len(quest_xp_opportunities) - quest_xp_limit),
        }
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
        "quest_xp_timing_opportunities": quest_xp_opportunities[:quest_xp_limit],
        "quest_xp_timing_coverage": quest_xp_coverage,
        "quest_xp_threshold_sequences": quest_xp_sequences[:quest_xp_limit],
        "quest_xp_threshold_sequence_coverage": {
            "limit": quest_xp_limit,
            "shown_count": len(quest_xp_sequences[:quest_xp_limit]),
            "total_count": len(quest_xp_sequences),
            "omitted_count": max(0, len(quest_xp_sequences) - quest_xp_limit),
        },
        "unallocated_player_chosen_xp_rewards": quest_xp_timing[
            "unallocated_player_chosen_xp_rewards"
        ],
        "transport_payoff_bundles": transport_bundles,
        "sailing_economics_timing": list(sailing_economics.values()),
        "durable_utility_item_timing": durable_utility_items,
        "pvm_readiness": pvm_readiness,
        "mastering_mixology_timing": mastering_mixology_timing,
        "void_elite_void_timing": void_elite_void_timing,
        "economic_method_comparison": economic_method_comparison,
        "monster_drop_bypass_timing": monster_drop_bypass_timing,
        "gaps": {
            "preparation": preparation_gaps[:preparation_limit],
            "preparation_coverage": preparation_coverage,
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
            "player_chosen_xp_allocated": False,
            "utility_demand_inferred": False,
            "utility_purchase_path_selected": False,
            "pvm_readiness_inferred": False,
            "mixology_inputs_inferred": False,
            "mixology_reward_selected": False,
            "quest_training_method_selected": False,
            "void_purchase_or_upgrade_inferred": False,
            "economic_method_selected": False,
            "bypass_selected_by_default": False,
            "bypass_completion_time_inferred": False,
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
            print(f"    formal eligibility: {option['formal_eligibility']}")
            practical = option["practical_readiness_context"]
            if practical is not None:
                print(f"    practical context: {practical['status']}")
                print(f"    tactics: {practical['tactical_options_note']}")
                print(f"    timing: {practical['note']}")
            print(f"    stop: {option['stop_condition']}")
            print(f"    re-entry: {option['reentry_condition']}")

    check_ins = chapter["passive_and_recurring_check_ins"]
    print(f"\nExplicit passive check-ins: {len(check_ins['explicit_observations'])}")
    print("\nSailing economics timing:")
    for context in chapter["sailing_economics_timing"]:
        objective = context["fixed_next_objective"]
        print(f"  [{context['status'].upper()}] {objective['name']}")
        print(f"    timing: {context['note']}")
        shortfalls = objective["skill_shortfalls"] + objective["resource_shortfalls"]
        if shortfalls:
            print("    fixed-objective shortfalls: " + "; ".join(
                f"{entry['key']} {entry['have']}/{entry['need']} (short {entry['shortfall']})"
                for entry in shortfalls
            ))
        print(f"    stop: {context['stop_condition']}")
        print(f"    re-entry: {context['reentry_condition']}")
        print(f"    material boundary: {context['material_planning']['note']}")
    print("\nDurable utility timing:")
    for context in chapter["durable_utility_item_timing"]:
        print(f"  [{context['status'].upper()}] {context['name']}")
        for path in context["paths"]:
            print(f"    {path['name']}: {path['status']}")
            gaps = path["missing"] + path["missing_preparation"]
            if gaps:
                print(f"      gaps: {_concise_list(gaps)}")
        for contention in context["shared_currency_contention"]:
            print(
                f"    shared currency: {contention['resource']} has {contention['observed']} "
                f"for {contention['combined_cost']} across ready alternatives; purchase order not selected"
            )
        print(f"    demand: {context['demand_note']}")
        print(f"    stop: {context['stop_condition']}")
        print(f"    re-entry: {context['reentry_condition']}")
    print("\nPvM readiness context:")
    for context in chapter["pvm_readiness"]:
        print(f"  [{context['readiness_status'].upper()}] {context['name']}")
        print(f"    formal access: {context['factual_access']['status']}")
        print(f"    timing: {context['timing_status']}")
    mixology = chapter["mastering_mixology_timing"]
    print("\nMastering Mixology timing:")
    print(f"  hard access: {mixology['hard_access']['status']}")
    print(f"  timing: {mixology['timing']['status']}")
    print(f"  recipe coverage through 81: {mixology['recipe_coverage']['full_recipe_set_available']}")
    print(f"  stop/re-entry: {mixology['stop_reentry']['status']}")
    void = chapter["void_elite_void_timing"]
    print("\nVoid and Elite Void timing:")
    print(f"  timing: {void['timing']['status']}")
    print(f"  combat level: {void['regular_void_access']['combat_level_observed']}")
    lander = void["regular_void_access"]["highest_eligible_lander"]
    print(f"  highest eligible boat: {lander['id'] if lander else 'none'}")
    print(f"  Western hard observed: {void['elite_void_upgrade']['western_provinces_hard_claimed_observed']}")
    economy = chapter["economic_method_comparison"]
    pressure = economy["commitment_pressure"]
    print("\nEconomic method comparison:")
    print(f"  commitment pressure: {pressure['status']}")
    target = pressure["named_unfunded_commitment"]
    if target is not None:
        print(
            f"  target: {target['purpose']} ({target['cumulative_shortfall']} coin cumulative shortfall)"
        )
        for method in economy["method_comparisons"]:
            print(f"  [{method['comparison_status'].upper()}] {method['action_name']}")
            print(f"    attention fit: {method['attention_fit']['fit']}")
    bypasses = chapter["monster_drop_bypass_timing"]
    print("\nMonster-drop bypass timing:")
    for bypass in bypasses["bypasses"]:
        print(f"  [{bypass['timing_status'].upper()}] {bypass['name']}")
        print(f"    formal access: {bypass['factual_access']['status']}")
        print(f"    objective: {bypass['explicit_objective']['status']}")
    sequence_coverage = chapter["quest_xp_threshold_sequence_coverage"]
    print(
        "\nQuest-XP threshold sequencing: "
        f"{sequence_coverage['shown_count']} of {sequence_coverage['total_count']} shown"
    )
    for quest in chapter["quest_xp_threshold_sequences"]:
        print(f"  [{quest['primary_timing_status'].upper()}] {quest['quest_name']}")
        blockers = quest["missing_hard_requirements"] + quest["missing_preparation"]
        if blockers:
            print(f"    blockers: {_concise_list(blockers)}")
        for effect in quest["skill_effects"]:
            print(
                f"    {effect['skill']}: level {effect['current_level']} -> "
                f"{effect['resulting_level']} from {effect['fixed_xp']} fixed XP"
            )
    preparation_coverage = chapter["gaps"]["preparation_coverage"]
    print(
        "Preparation gaps: "
        f"{preparation_coverage['shown_count']} of {preparation_coverage['total_count']} shown"
    )
    print(f"Eligible unscored gaps: {len(chapter['gaps']['eligible_unscored'])}")
    quest_xp_coverage = chapter["quest_xp_timing_coverage"]
    print(
        "\nQuest-XP timing opportunities: "
        f"{quest_xp_coverage['shown_count']} of {quest_xp_coverage['total_count']} shown"
    )
    for quest in chapter["quest_xp_timing_opportunities"]:
        print(f"  [{quest['status'].upper()}] {quest['quest_name']}")
        if quest["missing_preparation"]:
            print(f"    prepare: {_concise_list(quest['missing_preparation'])}")
        for skill in quest["skills"]:
            crossed = [str(item["level"]) for item in skill["modeled_requirements_crossed"]]
            crossed_text = ", ".join(crossed) if crossed else "none"
            print(
                f"    {skill['skill']}: level {skill['current_level']} -> "
                f"{skill['resulting_level']} (crossed modeled requirement levels: {crossed_text})"
            )
    lamps = chapter["unallocated_player_chosen_xp_rewards"]
    print(f"Player-chosen XP rewards remain unallocated: {len(lamps)}")
    for bundle in chapter["transport_payoff_bundles"]:
        coverage = bundle["coverage"]
        bounded = bundle["component_coverage"]
        print(
            f"\n{bundle['name']}: {coverage['complete']} complete, {coverage['eligible']} eligible, "
            f"{coverage['needs_preparation']} need preparation, {coverage['blocked']} blocked "
            f"({bounded['shown_count']} of {coverage['total']} shown)"
        )
        for component in bundle["components"]:
            print(f"  [{component['status'].upper()}] {component['name']} - {component['action_name']}")
            print(f"    payoff: {component['payoff_note']}")
            if component["missing_preparation"]:
                print(f"    prepare: {_concise_list(component['missing_preparation'])}")
            elif component["missing"]:
                print(f"    blocked by: {_concise_list(component['missing'])}")
            print(f"    caveat: {component['usage_caveat']}")


def _concise_list(values: list[str], limit: int = 3) -> str:
    shown = values[:limit]
    omitted = len(values) - len(shown)
    return "; ".join(shown) + (f"; +{omitted} more" if omitted else "")


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
    parser.add_argument("--preparation-limit", default=DEFAULT_PREPARATION_LIMIT, type=int)
    parser.add_argument("--quest-xp-limit", default=DEFAULT_QUEST_XP_LIMIT, type=int)
    parser.add_argument("--transport-bundle-limit", default=DEFAULT_TRANSPORT_BUNDLE_LIMIT, type=int)
    parser.add_argument("--afk-mode", choices=AFK_MODES, default="low_attention")
    parser.add_argument(
        "--bypass-objectives",
        type=Path,
        help="Optional JSON object mapping known bypass IDs to explicit player objectives.",
    )
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
            preparation_limit=args.preparation_limit,
            quest_xp_limit=args.quest_xp_limit,
            transport_bundle_limit=args.transport_bundle_limit,
            afk_mode=args.afk_mode,
            bypass_objectives=load_json(args.bypass_objectives) if args.bypass_objectives else None,
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
