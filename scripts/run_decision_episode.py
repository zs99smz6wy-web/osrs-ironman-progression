"""Record a bounded sequence of player-confirmed progression actions."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from analyze_quest_xp_timing import DEFAULT_EDGES, DEFAULT_NODES
from apply_action import apply_action
from compose_recommendation_chapter import compose_recommendation_chapter
from evaluate_progression import DEFAULT_ACTIONS, evaluate_actions, load_json, validate_account_state
from score_candidates import DEFAULT_CANDIDATES


MAX_EPISODE_STEPS = 25


def _validated_steps(selected_steps: Any) -> list[dict[str, Any]]:
    if not isinstance(selected_steps, list):
        raise ValueError("episode selections must be a JSON array")
    if len(selected_steps) > MAX_EPISODE_STEPS:
        raise ValueError(f"episode selections may contain at most {MAX_EPISODE_STEPS} steps")

    validated: list[dict[str, Any]] = []
    for index, step in enumerate(selected_steps):
        if not isinstance(step, dict):
            raise ValueError(f"episode step {index} must be an object")
        unexpected = set(step) - {"action_id", "completion_confirmed", "option_id"}
        if unexpected:
            raise ValueError(f"episode step {index} has unsupported fields: {', '.join(sorted(unexpected))}")
        action_id = step.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            raise ValueError(f"episode step {index} requires a non-empty action_id")
        if "completion_confirmed" in step and not isinstance(step["completion_confirmed"], bool):
            raise ValueError(f"episode step {index} completion_confirmed must be boolean when present")
        if "option_id" in step and (not isinstance(step["option_id"], str) or not step["option_id"]):
            raise ValueError(f"episode step {index} option_id must be a non-empty string when present")
        validated.append(copy.deepcopy(step))
    return validated


def _chapter(
    state: dict[str, Any],
    actions_document: dict[str, Any],
    candidates_document: dict[str, Any],
    nodes_document: dict[str, Any],
    edges_document: dict[str, Any],
) -> dict[str, Any]:
    return compose_recommendation_chapter(
        state,
        actions_document,
        candidates_document,
        nodes_document,
        edges_document,
    )


def _application_receipt(result: dict[str, Any]) -> dict[str, Any]:
    """Keep the report focused on the confirmed transition rather than duplicate state snapshots."""
    return {
        "status": result["status"],
        "selected_option_id": result["selected_option_id"],
        "guaranteed_effects_recorded": copy.deepcopy(result["applied_effects"]),
        "reported_effects": copy.deepcopy(result["reported_effects"]),
    }


def run_decision_episode(
    account_state: dict[str, Any],
    selected_steps: list[dict[str, Any]],
    actions_document: dict[str, Any],
    candidates_document: dict[str, Any],
    nodes_document: dict[str, Any],
    edges_document: dict[str, Any],
) -> dict[str, Any]:
    """Apply only bounded, explicit, player-confirmed action completions in order.

    A selected action is never treated as completed until its step attests
    ``completion_confirmed: true``. The function does not write or mutate its inputs.
    """
    validate_account_state(account_state)
    steps = _validated_steps(selected_steps)
    current_state = copy.deepcopy(account_state)
    action_names = {
        action["id"]: action["name"]
        for action in actions_document.get("actions", [])
        if isinstance(action.get("id"), str) and isinstance(action.get("name"), str)
    }
    report_steps: list[dict[str, Any]] = []
    episode_status = "all_confirmed_steps_applied"

    for index, selected_step in enumerate(steps):
        action_id = selected_step["action_id"]
        completion_confirmed = selected_step.get("completion_confirmed") is True
        chapter = _chapter(
            current_state,
            actions_document,
            candidates_document,
            nodes_document,
            edges_document,
        )
        evaluated = {result["id"]: result for result in evaluate_actions(actions_document, current_state)}
        eligibility = copy.deepcopy(evaluated.get(action_id))
        step_report: dict[str, Any] = {
            "index": index,
            "action_id": action_id,
            "action_name": action_names.get(action_id),
            "option_id": selected_step.get("option_id"),
            "selection_source": "explicit_player_input",
            "completion_attestation": {
                "required": True,
                "present": "completion_confirmed" in selected_step,
                "confirmed": completion_confirmed,
            },
            "recommendation_chapter_before_selection": chapter,
            "eligibility_before_selection": eligibility,
        }

        if action_id not in evaluated:
            step_report["status"] = "not_applied_unknown_action"
            report_steps.append(step_report)
            episode_status = "halted_unknown_action"
            break

        if not completion_confirmed:
            step_report["status"] = "not_applied_completion_unconfirmed"
            report_steps.append(step_report)
            episode_status = "halted_completion_unconfirmed"
            break

        if eligibility["status"] != "eligible":
            step_report["status"] = "not_applied_not_eligible"
            report_steps.append(step_report)
            episode_status = "halted_not_eligible"
            break

        applied = apply_action(
            actions_document,
            current_state,
            action_id,
            selected_step.get("option_id"),
        )
        step_report["application"] = _application_receipt(applied)
        if applied["status"] != "applied":
            step_report["status"] = f"not_applied_apply_action_{applied['status']}"
            report_steps.append(step_report)
            episode_status = f"halted_apply_action_{applied['status']}"
            break

        step_report["status"] = "applied_confirmed_completion"
        report_steps.append(step_report)
        current_state = applied["next_state"]

    if not steps:
        episode_status = "no_steps_requested"

    return {
        "episode_type": "explicit_decision_episode",
        "episode_status": episode_status,
        "selection_limit": MAX_EPISODE_STEPS,
        "requested_step_count": len(steps),
        "recorded_step_count": len(report_steps),
        "steps": report_steps,
        "final_account_state": copy.deepcopy(current_state),
        "boundaries": {
            "route_selected": False,
            "action_auto_selected": False,
            "completion_inferred": False,
            "planned_or_unconfirmed_action_applied": False,
            "elapsed_time_inferred": False,
            "random_outputs_inferred": False,
            "combat_wins_inferred": False,
            "minigame_outputs_inferred": False,
            "input_files_mutated": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record a bounded episode of explicit, player-confirmed progression actions."
    )
    parser.add_argument("state", type=Path, help="Path to an account-state JSON file")
    parser.add_argument("selections", type=Path, help="Path to an ordered JSON array of episode steps")
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES, type=Path)
    parser.add_argument("--nodes", default=DEFAULT_NODES, type=Path)
    parser.add_argument("--edges", default=DEFAULT_EDGES, type=Path)
    args = parser.parse_args()

    try:
        report = run_decision_episode(
            load_json(args.state),
            load_json(args.selections),
            load_json(args.actions),
            load_json(args.candidates),
            load_json(args.nodes),
            load_json(args.edges),
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Decision episode failed: {error}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
