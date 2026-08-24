"""Report bounded, account-aware Void and Elite Void timing context."""

from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any

from evaluate_progression import DEFAULT_STATE, load_json, validate_account_state


ROOT = Path(__file__).resolve().parents[1]
CONTEXT_PATH = ROOT / "strategy" / "void-elite-void-timing-contexts.json"
POINT_RESOURCE_KEY = "pest_control_commendation_points"
POINT_CURRENCY_ID = "currency:pest-control:commendation-points"
PIECE_KEYS = ("void_knight_top", "void_knight_robe", "void_knight_gloves")
HELMET_KEYS = ("void_melee_helm", "void_ranger_helm", "void_mage_helm")
ELITE_PIECE_KEYS = ("elite_void_top", "elite_void_robe")
PURCHASE_REQUIREMENTS = {
    "Attack": 42,
    "Strength": 42,
    "Defence": 42,
    "Hitpoints": 42,
    "Ranged": 42,
    "Magic": 42,
    "Prayer": 22,
}
LANDERS = (("novice", 40, 3), ("intermediate", 70, 4), ("veteran", 100, 5))
OBJECTIVES = {"undecided", "regular_void_one_helmet", "elite_void_one_helmet"}
VETERAN_WAIT_VALUES = {"none", "consider", "prefer"}


def non_negative_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def combat_level(skills: dict[str, Any]) -> int | None:
    """Calculate displayed combat level from observed unboosted base skill levels."""
    values = {skill: non_negative_integer(skills.get(skill)) for skill in PURCHASE_REQUIREMENTS}
    if any(value is None for value in values.values()):
        return None
    base = 0.25 * (values["Defence"] + values["Hitpoints"] + math.floor(values["Prayer"] / 2))
    melee = 0.325 * (values["Attack"] + values["Strength"])
    ranged = 0.325 * math.floor(values["Ranged"] * 1.5)
    magic = 0.325 * math.floor(values["Magic"] * 1.5)
    return math.floor(base + max(melee, ranged, magic))


def observed_points(state: dict[str, Any]) -> tuple[int | None, str | None]:
    resources = state.get("resources", {})
    if isinstance(resources, dict):
        amount = non_negative_integer(resources.get(POINT_RESOURCE_KEY))
        if amount is not None:
            return amount, f"resources.{POINT_RESOURCE_KEY}"
    observation = state.get("minigame_activity_observations", {}).get("pest-control", {})
    rows = observation.get("currency_balances", []) if isinstance(observation, dict) else []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("currency_id") == POINT_CURRENCY_ID:
                amount = non_negative_integer(row.get("amount"))
                if amount is not None:
                    return amount, "minigame_activity_observations.pest-control.currency_balances"
    return None, None


def normalized_intent(intent: dict[str, Any] | None) -> dict[str, str]:
    value = intent if isinstance(intent, dict) else {}
    objective = value.get("objective", "undecided")
    veteran_wait = value.get("veteran_wait", "consider")
    if objective not in OBJECTIVES:
        raise ValueError(f"objective must be one of {sorted(OBJECTIVES)}")
    if veteran_wait not in VETERAN_WAIT_VALUES:
        raise ValueError(f"veteran_wait must be one of {sorted(VETERAN_WAIT_VALUES)}")
    return {"objective": objective, "veteran_wait": veteran_wait}


def analyze_void_elite_void_timing(
    account_state: dict[str, Any], strategy_intent: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Describe Void timing gates and strategy context without performing any transition."""
    validate_account_state(account_state)
    context = load_json(CONTEXT_PATH)
    intent = normalized_intent(strategy_intent)
    skills = account_state["skills"]
    items = account_state["items"]
    observed_combat = combat_level(skills)
    missing_purchase_skills = [
        f"{skill} {minimum}" for skill, minimum in PURCHASE_REQUIREMENTS.items()
        if non_negative_integer(skills.get(skill)) is None or skills[skill] < minimum
    ]
    eligible_landers = [
        {"id": name, "minimum_combat_level": minimum, "base_points_per_eligible_win": points}
        for name, minimum, points in LANDERS
        if observed_combat is not None and observed_combat >= minimum
    ]
    highest_lander = eligible_landers[-1] if eligible_landers else None
    points, points_source = observed_points(account_state)
    owned = {
        key: non_negative_integer(items.get(key)) or 0
        for key in (*PIECE_KEYS, *HELMET_KEYS, *ELITE_PIECE_KEYS)
    }
    top_owned = owned["void_knight_top"] > 0 or owned["elite_void_top"] > 0
    robe_owned = owned["void_knight_robe"] > 0 or owned["elite_void_robe"] > 0
    regular_complete = top_owned and robe_owned and owned["void_knight_gloves"] > 0 and any(
        owned[key] > 0 for key in HELMET_KEYS
    )
    regular_missing = []
    if not top_owned:
        regular_missing.append("void_knight_top_or_elite_void_top")
    if not robe_owned:
        regular_missing.append("void_knight_robe_or_elite_void_robe")
    if owned["void_knight_gloves"] < 1:
        regular_missing.append("void_knight_gloves")
    if not any(owned[key] > 0 for key in HELMET_KEYS):
        regular_missing.append("one_void_combat_helmet")
    western_hard = account_state["diary_tiers"].get("Western Provinces") in {"hard", "elite"}
    top_upgraded = owned["elite_void_top"] > 0
    robe_upgraded = owned["elite_void_robe"] > 0
    remaining_upgrade_cost = 200 * int(not top_upgraded) + 200 * int(not robe_upgraded)
    top_upgrade_ready = not top_upgraded and owned["void_knight_top"] > 0 and western_hard and points is not None and points >= 200
    robe_upgrade_ready = not robe_upgraded and owned["void_knight_robe"] > 0 and western_hard and points is not None and points >= 200
    remaining_upgrades_ready = (
        western_hard
        and (top_upgraded or owned["void_knight_top"] > 0)
        and (robe_upgraded or owned["void_knight_robe"] > 0)
        and points is not None
        and points >= remaining_upgrade_cost
    )
    elite_complete = top_upgraded and robe_upgraded and owned["void_knight_gloves"] > 0 and any(
        owned[key] > 0 for key in HELMET_KEYS
    )

    if intent["objective"] == "undecided":
        timing_status = "decision_deferred_no_objective"
    elif missing_purchase_skills:
        timing_status = "delay_regular_void_purchase_skills"
    elif not regular_complete:
        if observed_combat is not None and observed_combat < 100 and intent["veteran_wait"] == "prefer":
            timing_status = "wait_veteran_rate_consideration"
        elif highest_lander is None:
            timing_status = "delay_pest_control_boat_access"
        else:
            timing_status = "regular_void_enter_candidate"
    elif intent["objective"] == "regular_void_one_helmet":
        timing_status = "regular_void_objective_observed"
    elif elite_complete:
        timing_status = "elite_void_objective_observed"
    elif not western_hard:
        timing_status = "wait_western_provinces_hard_for_elite_upgrade"
    elif remaining_upgrades_ready:
        timing_status = "elite_void_upgrade_candidate"
    else:
        timing_status = "wait_observed_elite_upgrade_inputs"

    observation = account_state.get("minigame_activity_observations", {}).get("pest-control")
    session = observation.get("session", {}) if isinstance(observation, dict) else {}
    session_status = session.get("status") if isinstance(session, dict) else "unknown"
    if session_status in {"active", "queued"}:
        session_context = "session_observed"
    elif session_status in {"ended", "reset", "unavailable"}:
        session_context = "stopped_or_reentry_candidate_observed"
    else:
        session_context = "no_active_session_observed"

    return {
        "strategy_intent": intent,
        "regular_void_access": {
            "purchase_skill_requirements_met": not missing_purchase_skills,
            "missing_purchase_skills": missing_purchase_skills,
            "combat_level_observed": observed_combat,
            "eligible_landers": eligible_landers,
            "highest_eligible_lander": highest_lander,
            "combat_100_is_regular_void_requirement": False,
            "regular_void_available_before_combat_100": bool(highest_lander and observed_combat is not None and observed_combat < 100),
        },
        "regular_void_set": {
            "owned_piece_counts": owned,
            "complete_one_helmet_set_observed": regular_complete,
            "missing_piece_keys": regular_missing,
            "one_helmet_set_point_cost": 850,
            "observed_points": points,
            "observed_points_source": points_source,
            "point_budget_ready_for_fresh_one_helmet_set": points is not None and points >= 850,
            "purchase_or_set_completion_inferred": False,
        },
        "elite_void_upgrade": {
            "western_provinces_hard_claimed_observed": western_hard,
            "regular_top_observed": owned["void_knight_top"] > 0,
            "regular_robe_observed": owned["void_knight_robe"] > 0,
            "elite_top_observed": top_upgraded,
            "elite_robe_observed": robe_upgraded,
            "complete_one_helmet_elite_set_observed": elite_complete,
            "points_required_per_piece": 200,
            "points_required_for_both_pieces": 400,
            "remaining_upgrade_point_cost": remaining_upgrade_cost,
            "top_upgrade_candidate": top_upgrade_ready,
            "robe_upgrade_candidate": robe_upgrade_ready,
            "remaining_upgrades_candidate": remaining_upgrades_ready,
            "both_upgrades_candidate": remaining_upgrade_cost == 400 and remaining_upgrades_ready,
            "upgrade_inferred": False,
        },
        "timing": {
            "status": timing_status,
            "veteran_rate_consideration": "Veteran opens at combat 100 with a higher base point value; this is a strategy consideration and does not block lower-boat regular Void.",
            "route_selected": False,
            "boat_selected": False,
            "helmet_selected": False,
        },
        "stop_reentry": {
            "session_context": session_context,
            "stop_conditions": copy.deepcopy(context["stop_reentry"]["stop_conditions"]),
            "reentry_conditions": copy.deepcopy(context["stop_reentry"]["reentry_conditions"]),
        },
        "inference_guarantees": {
            "team_inferred": False,
            "round_outcome_inferred": False,
            "points_earned_inferred": False,
            "point_rate_inferred": False,
            "purchase_inferred": False,
            "upgrade_inferred": False,
            "route_selected": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report bounded Void and Elite Void timing context.")
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--objective", choices=sorted(OBJECTIVES), default="undecided")
    parser.add_argument("--veteran-wait", choices=sorted(VETERAN_WAIT_VALUES), default="consider")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()
    report = analyze_void_elite_void_timing(
        load_json(args.state), {"objective": args.objective, "veteran_wait": args.veteran_wait}
    )
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"Timing: {report['timing']['status']}")
    print(f"Combat level: {report['regular_void_access']['combat_level_observed']}")
    print(f"Highest eligible lander: {report['regular_void_access']['highest_eligible_lander']}")
    print(f"Elite upgrade candidate: {report['elite_void_upgrade']['both_upgrades_candidate']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
