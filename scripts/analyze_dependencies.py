from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evaluate_progression import DEFAULT_ACTIONS, DEFAULT_STATE, evaluate_actions, evaluate_condition, load_json


ROOT = Path(__file__).resolve().parents[1]

PREDICATE_STATE = {
    "quest_completed": "quests_completed",
    "transport_flag": "transport_flags",
    "milestone": "milestones",
    "gear_threshold": "gear_thresholds",
    "notable_drop": "notable_drops",
    "passive_loop": "passive_loops",
    "recurring_state": "recurring_observations",
    "item_at_least": "items",
    "resource_at_least": "resources",
    "counter_at_least": "counters",
}
FLOOR_PREDICATES = {"item_at_least", "resource_at_least", "counter_at_least"}
EXTERNAL_INPUT_PREDICATES = {
    "skill_at_least", "item_at_least", "resource_at_least", "recurring_state", "slayer_task_target",
}


def _predicate_view(predicate: dict[str, Any]) -> dict[str, Any]:
    view = {"type": predicate["type"], "key": predicate["key"]}
    if "value" in predicate:
        view["value"] = predicate["value"]
    return view


def _expected_passive_value(predicate: dict[str, Any]) -> bool:
    return predicate.get("value", True)


def _current_value(predicate: dict[str, Any], state: dict[str, Any]) -> Any:
    predicate_type = predicate["type"]
    key = predicate["key"]
    if predicate_type == "skill_at_least":
        return state["skills"][key]
    if predicate_type in FLOOR_PREDICATES:
        return state[PREDICATE_STATE[predicate_type]].get(key, 0)
    if predicate_type == "passive_loop":
        return state["passive_loops"].get(key, False)
    if predicate_type == "recurring_state":
        return state["recurring_observations"].get(key, {}).get("state", "unobserved")
    if predicate_type == "slayer_task_target":
        task = state["slayer_task"]
        return task if task is not None and task["remaining"] > 0 else None
    return key in state[PREDICATE_STATE[predicate_type]]


class DependencyClosureAnalyzer:
    """Build a conservative, read-only explanation of one action's prerequisites."""

    def __init__(
        self,
        actions_document: dict[str, Any],
        state: dict[str, Any],
        *,
        include_preparation: bool,
    ) -> None:
        evaluated = evaluate_actions(actions_document, state)
        self.state = state
        self.include_preparation = include_preparation
        self.actions = {action["id"]: action for action in actions_document["actions"]}
        if len(self.actions) != len(actions_document["actions"]):
            raise ValueError("Progression actions must have unique IDs")
        self.evaluated = {result["id"]: result for result in evaluated}
        self.producers = self._build_producer_index()
        self.action_nodes: dict[str, dict[str, Any]] = {}
        self.alternatives: dict[str, dict[str, Any]] = {}
        self.choices: dict[tuple[str, str], dict[str, Any]] = {}
        self.external_inputs: dict[str, dict[str, Any]] = {}
        self.missing_producers: dict[str, dict[str, Any]] = {}
        self.cycles: dict[tuple[str, ...], dict[str, Any]] = {}
        self.active_actions: list[str] = []

    def analyze(self, goal_id: str) -> dict[str, Any]:
        if goal_id not in self.actions:
            raise ValueError(f"Unknown goal action ID: {goal_id}")

        self._visit_action(goal_id, "goal")
        goal = self.actions[goal_id]
        return {
            "schema_version": 1,
            "goal": {
                "action_id": goal_id,
                "name": goal["name"],
                "current_status": self.evaluated[goal_id]["status"],
            },
            "closure": {
                "actions": [self._normalized_action_node(node) for _, node in sorted(self.action_nodes.items())],
            },
            "alternatives": [self.alternatives[key] for key in sorted(self.alternatives)],
            "choices": [self.choices[key] for key in sorted(self.choices)],
            "external_inputs": [self.external_inputs[key] for key in sorted(self.external_inputs)],
            "missing_modeled_producers": [self.missing_producers[key] for key in sorted(self.missing_producers)],
            "cycles": [self.cycles[key] for key in sorted(self.cycles)],
            "limitations": [
                "This is a dependency closure, not an action sequence or recommendation.",
                "Transition choices are retained as alternatives and are never selected or applied.",
                "Resource conflicts, action timing, repeat counts, and combat feasibility are not resolved.",
                "Gain-XP effects are annotated only; they do not prove skill-level prerequisites.",
                "Only deterministic transition effects are considered producer evidence.",
            ],
        }

    def _build_producer_index(self) -> dict[tuple[str, str], list[dict[str, Any]]]:
        producers: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for action in sorted(self.actions.values(), key=lambda candidate: candidate["id"]):
            for effect in action["transition"]["effects"]:
                effect_type = effect["op"]
                if effect_type == "set_add":
                    predicate_type = {
                        "quests_completed": "quest_completed",
                        "transport_flags": "transport_flag",
                        "milestones": "milestone",
                        "gear_thresholds": "gear_threshold",
                        "notable_drops": "notable_drop",
                    }.get(effect["state"])
                    capability = "set_membership"
                elif effect_type == "set" and effect["state"] == "passive_loops":
                    predicate_type = "passive_loop"
                    capability = "set_value"
                elif effect_type == "ensure_min":
                    predicate_type = {
                        "items": "item_at_least",
                        "resources": "resource_at_least",
                        "counters": "counter_at_least",
                    }.get(effect["state"])
                    capability = "floor"
                elif effect_type == "delta" and effect["amount"] > 0:
                    predicate_type = {
                        "items": "item_at_least",
                        "resources": "resource_at_least",
                        "counters": "counter_at_least",
                    }.get(effect["state"])
                    capability = "incremental"
                else:
                    continue

                if predicate_type is None:
                    continue
                candidate = {
                    "action_id": action["id"],
                    "operation": effect_type,
                    "capability": capability,
                    "fact_id": effect["fact_id"],
                }
                if effect_type == "set":
                    candidate["value"] = effect["value"]
                if effect_type == "ensure_min":
                    candidate["value"] = effect["value"]
                if effect_type == "delta":
                    candidate["amount"] = effect["amount"]
                producers.setdefault((predicate_type, effect["key"]), []).append(candidate)
        return producers

    def _xp_progress(self, predicate: dict[str, Any], action_id: str) -> list[dict[str, Any]]:
        if predicate["type"] != "skill_at_least":
            return []
        progress: list[dict[str, Any]] = []
        for action in sorted(self.actions.values(), key=lambda candidate: candidate["id"]):
            if action["id"] == action_id:
                continue
            for effect in action["transition"]["effects"]:
                if effect["op"] == "gain_xp" and effect["key"] == predicate["key"]:
                    progress.append(
                        {
                            "action_id": action["id"],
                            "operation": "gain_xp",
                            "amount": effect["amount"],
                            "fact_id": effect["fact_id"],
                        }
                    )
        return progress

    def _visit_action(self, action_id: str, needed_for: str) -> None:
        if action_id in self.active_actions:
            self._record_cycle(action_id)
            return

        node = self.action_nodes.get(action_id)
        if node is not None:
            node["needed_for"].add(needed_for)
            return

        action = self.actions[action_id]
        node = {
            "action_id": action_id,
            "name": action["name"],
            "current_status": self.evaluated[action_id]["status"],
            "needed_for": {needed_for},
            "conditions": [],
            "transition_choices": [],
        }
        self.action_nodes[action_id] = node
        self.active_actions.append(action_id)
        node["conditions"].append(
            {
                "phase": "requirements",
                "condition": self._build_condition(action_id, "requirements", action["requirements"], "root"),
            }
        )
        if self.include_preparation:
            node["conditions"].append(
                {
                    "phase": "preparation",
                    "condition": self._build_condition(action_id, "preparation", action["preparation"], "root"),
                }
            )
        for option in sorted(action["transition"]["options"], key=lambda candidate: candidate["id"]):
            choice = {
                "action_id": action_id,
                "option_id": option["id"],
                "selection": "unselected",
                "requires": self._build_condition(
                    action_id,
                    f"transition_option:{option['id']}",
                    option["requires"],
                    "root",
                ),
            }
            node["transition_choices"].append(choice)
            self.choices[(action_id, option["id"])] = choice
        self.active_actions.pop()

    def _record_cycle(self, action_id: str) -> None:
        cycle = tuple(self.active_actions[self.active_actions.index(action_id) :] + [action_id])
        self.cycles.setdefault(cycle, {"action_ids": list(cycle)})

    def _build_condition(
        self,
        action_id: str,
        phase: str,
        condition: dict[str, Any],
        path: str,
    ) -> dict[str, Any]:
        satisfied, _ = evaluate_condition(condition, self.state)
        identifier = f"condition:{action_id}:{phase}:{path}"
        if "all" in condition or "any" in condition:
            operator = "all" if "all" in condition else "any"
            children = condition[operator]
            node = {
                "id": identifier,
                "operator": operator,
                "status": "satisfied" if satisfied else "unmet",
                "children": [
                    self._build_condition(action_id, phase, child, f"{path}.{operator}.{index}")
                    for index, child in enumerate(children)
                ],
            }
            if operator == "any":
                self.alternatives[identifier] = {
                    "condition_id": identifier,
                    "action_id": action_id,
                    "phase": phase,
                    "status": node["status"],
                    "branch_ids": [child["id"] for child in node["children"]],
                }
            return node

        predicate = _predicate_view(condition)
        node = {
            "id": identifier.replace("condition:", "predicate:", 1),
            "predicate": predicate,
            "current_value": _current_value(predicate, self.state),
            "status": "satisfied" if satisfied else "unmet",
            "producer_actions": [],
        }
        if satisfied:
            return node

        # An action cannot use one of its own effects to establish a prerequisite
        # that must already hold before its transition can occur.
        candidates = [
            candidate
            for candidate in self._matching_candidates(predicate)
            if candidate["action_id"] != action_id
        ]
        fully_satisfying: list[dict[str, Any]] = []
        partial: list[dict[str, Any]] = []
        cyclic: list[dict[str, Any]] = []
        for candidate in candidates:
            evidence = dict(candidate)
            if candidate["action_id"] in self.active_actions:
                evidence["cyclic_dependency"] = True
                cyclic.append(evidence)
                self._record_cycle(candidate["action_id"])
                continue
            if candidate["capability"] == "floor":
                evidence["satisfies_predicate"] = candidate["value"] >= predicate["value"]
            elif candidate["capability"] == "incremental":
                outstanding = predicate["value"] - node["current_value"]
                evidence["outstanding_amount"] = outstanding
                evidence["satisfies_predicate"] = candidate["amount"] >= outstanding
            else:
                evidence["satisfies_predicate"] = True
            (fully_satisfying if evidence["satisfies_predicate"] else partial).append(evidence)

        if fully_satisfying or partial:
            evidence = sorted(fully_satisfying + partial, key=lambda item: (item["action_id"], item["operation"]))
            node["producer_evidence"] = evidence
            node["producer_actions"] = sorted({item["action_id"] for item in evidence})
            node["status"] = "producible" if fully_satisfying else "partial_progress"
            for producer_id in node["producer_actions"]:
                self._visit_action(producer_id, node["id"])
            if not fully_satisfying:
                self._record_unresolved(node, "deterministic effects provide only bounded partial progress")
            return node

        if cyclic:
            node["cyclic_producer_evidence"] = sorted(
                cyclic, key=lambda item: (item["action_id"], item["operation"])
            )

        xp_progress = self._xp_progress(predicate, action_id)
        if xp_progress:
            node["partial_progress"] = xp_progress
        self._record_unresolved(node, "no deterministic producer in the supplied action data")
        return node

    def _matching_candidates(self, predicate: dict[str, Any]) -> list[dict[str, Any]]:
        candidates = list(self.producers.get((predicate["type"], predicate["key"]), []))
        if predicate["type"] == "passive_loop":
            expected = _expected_passive_value(predicate)
            candidates = [candidate for candidate in candidates if candidate["value"] == expected]
        return candidates

    def _record_unresolved(self, node: dict[str, Any], reason: str) -> None:
        predicate = node["predicate"]
        entry = {"predicate_id": node["id"], "predicate": predicate, "reason": reason}
        self.external_inputs[node["id"]] = entry
        if predicate["type"] not in EXTERNAL_INPUT_PREDICATES:
            self.missing_producers[node["id"]] = entry

    @staticmethod
    def _normalized_action_node(node: dict[str, Any]) -> dict[str, Any]:
        return {
            "action_id": node["action_id"],
            "name": node["name"],
            "current_status": node["current_status"],
            "needed_for": sorted(node["needed_for"]),
            "conditions": node["conditions"],
            "transition_choices": node["transition_choices"],
        }


def analyze_dependency_closure(
    actions_document: dict[str, Any],
    state: dict[str, Any],
    goal_id: str,
    *,
    include_preparation: bool = False,
) -> dict[str, Any]:
    return DependencyClosureAnalyzer(
        actions_document,
        state,
        include_preparation=include_preparation,
    ).analyze(goal_id)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a read-only deterministic dependency closure for one progression action."
    )
    parser.add_argument("state", nargs="?", default=DEFAULT_STATE, type=Path)
    parser.add_argument("--goal", required=True, help="One normalized action ID to analyze.")
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, type=Path)
    parser.add_argument(
        "--include-preparation",
        action="store_true",
        help="Include preparation conditions alongside hard requirements.",
    )
    parser.add_argument("--json", action="store_true", help="Emit stable machine-readable JSON.")
    args = parser.parse_args()

    try:
        analysis = analyze_dependency_closure(
            load_json(args.actions),
            load_json(args.state),
            args.goal,
            include_preparation=args.include_preparation,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))

    if args.json:
        print(json.dumps(analysis, indent=2, sort_keys=True))
        return 0

    print(f"{analysis['goal']['name']} [{analysis['goal']['current_status']}]")
    print(f"Actions in closure: {len(analysis['closure']['actions'])}")
    print(f"External inputs: {len(analysis['external_inputs'])}")
    print(f"Cycles: {len(analysis['cycles'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
