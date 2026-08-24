"""Validate bounded research-only execution segment packages."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SEGMENTS_RELATIVE = Path("research/execution-segments")
SCHEMA_RELATIVE = Path("research/package-schemas/execution-segment.schema.json")
BOUNDARY_KEYS = {
    "route_selected",
    "action_auto_applied",
    "completion_inferred",
    "items_or_gp_acquired",
    "outputs_inferred",
    "timing_inferred",
    "combat_success_inferred",
}
SEGMENT_KEYS = {
    "segment_schema_version",
    "segment_type",
    "segment_id",
    "name",
    "status",
    "purpose",
    "facts_strategy_boundary",
    "source_catalog",
    "source_ids",
    "starting_state",
    "checkpoints",
    "execution_steps",
    "branches",
    "safety_hcim",
    "passive_recurring_checks",
    "stop_reentry_conditions",
    "estimated_time",
    "completion_observations",
    "normalization_boundaries",
    "boundaries",
}
STATUS_NORMALIZED = "normalized_action"
STATUS_SOURCED = "sourced_unmodeled_substep"
STATUS_UNRESOLVED = "unresolved"


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _verify_ascii_and_whitespace(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        errors.append(f"{path.name}: must use ASCII")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.rstrip() != line:
            errors.append(f"{path.name}:{line_number}: trailing whitespace")


def _source_ids(value: Any, catalog_ids: set[str], context: str, errors: list[str], *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list) or any(not _is_nonempty_string(item) for item in value):
        errors.append(f"{context}: source_ids must be an array of non-empty strings")
        return []
    if len(value) != len(set(value)):
        errors.append(f"{context}: source_ids must be unique")
    if not allow_empty and not value:
        errors.append(f"{context}: source_ids must not be empty")
    for source_id in value:
        if source_id not in catalog_ids:
            errors.append(f"{context}: references unknown local source {source_id}")
    return value


def _validate_boundary(value: Any, context: str, errors: list[str]) -> None:
    if not isinstance(value, dict) or set(value) != BOUNDARY_KEYS:
        errors.append(f"{context}: must contain exactly the execution boundary flags")
        return
    for key in BOUNDARY_KEYS:
        if value[key] is not False:
            errors.append(f"{context}.{key}: must be false")


def _validate_string_array(value: Any, context: str, errors: list[str], *, minimum: int = 1) -> None:
    if not isinstance(value, list) or len(value) < minimum or any(not _is_nonempty_string(item) for item in value):
        errors.append(f"{context}: must be an array of at least {minimum} non-empty strings")


def _validate_purpose(value: Any, context: str, errors: list[str]) -> None:
    required = {"accomplishes", "account_applicability", "timing_observation", "applicability_is_not_route_selection"}
    if not isinstance(value, dict) or set(value) != required:
        errors.append(f"{context}: purpose fields are invalid")
        return
    _validate_string_array(value["accomplishes"], f"{context}.accomplishes", errors)
    _validate_string_array(value["account_applicability"], f"{context}.account_applicability", errors)
    if not _is_nonempty_string(value["timing_observation"]):
        errors.append(f"{context}.timing_observation: is required")
    if value["applicability_is_not_route_selection"] is not True:
        errors.append(f"{context}.applicability_is_not_route_selection: must be true")


def _validate_safety(value: Any, context: str, catalog_ids: set[str], errors: list[str]) -> None:
    required = {"hazard_facts", "player_risk_requirements", "current_observations_required", "never_inferred_survival"}
    if not isinstance(value, dict) or set(value) != required:
        errors.append(f"{context}: safety fields are invalid")
        return
    hazards = value["hazard_facts"]
    if not isinstance(hazards, list):
        errors.append(f"{context}.hazard_facts: must be an array")
    else:
        hazard_ids: set[str] = set()
        for index, hazard in enumerate(hazards):
            hazard_context = f"{context}.hazard_facts[{index}]"
            if not isinstance(hazard, dict) or set(hazard) != {"id", "description", "source_ids"}:
                errors.append(f"{hazard_context}: hazard fields are invalid")
                continue
            if not _is_nonempty_string(hazard["id"]) or hazard["id"] in hazard_ids or not _is_nonempty_string(hazard["description"]):
                errors.append(f"{hazard_context}: hazard id and description are required and unique")
            hazard_ids.add(hazard["id"])
            _source_ids(hazard["source_ids"], catalog_ids, hazard_context, errors, allow_empty=False)
    _validate_string_array(value["player_risk_requirements"], f"{context}.player_risk_requirements", errors)
    _validate_string_array(value["current_observations_required"], f"{context}.current_observations_required", errors)
    if value["never_inferred_survival"] is not True:
        errors.append(f"{context}.never_inferred_survival: must be true")


def _validate_passive_checks(value: Any, context: str, catalog_ids: set[str], errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{context}: must be an array")
        return
    check_ids: set[str] = set()
    required = {"id", "trigger_when", "required_current_observation", "interruption_policy", "source_ids"}
    for index, check in enumerate(value):
        check_context = f"{context}[{index}]"
        if not isinstance(check, dict) or set(check) != required:
            errors.append(f"{check_context}: passive check fields are invalid")
            continue
        if not _is_nonempty_string(check["id"]) or check["id"] in check_ids:
            errors.append(f"{check_context}: passive check id is required and unique")
        check_ids.add(check["id"])
        for key in ("trigger_when", "required_current_observation", "interruption_policy"):
            if not _is_nonempty_string(check[key]):
                errors.append(f"{check_context}.{key}: is required")
        _source_ids(check["source_ids"], catalog_ids, check_context, errors, allow_empty=True)


def _validate_requirements(value: Any, context: str, errors: list[str]) -> None:
    required = {"carried_items", "banked_items", "carried_gp", "banked_gp"}
    if not isinstance(value, dict) or set(value) != required:
        errors.append(f"{context}: must declare exact carried/banked items and GP")
        return
    for gp_key in ("carried_gp", "banked_gp"):
        if not _is_nonnegative_int(value[gp_key]):
            errors.append(f"{context}.{gp_key}: must be a non-negative integer")
    for item_key in ("carried_items", "banked_items"):
        items = value[item_key]
        if not isinstance(items, list):
            errors.append(f"{context}.{item_key}: must be an array")
            continue
        ids: set[str] = set()
        for index, item in enumerate(items):
            item_context = f"{context}.{item_key}[{index}]"
            if not isinstance(item, dict) or set(item) != {"id", "quantity"}:
                errors.append(f"{item_context}: must contain only id and quantity")
                continue
            if not _is_nonempty_string(item["id"]) or not _is_nonnegative_int(item["quantity"]) or item["quantity"] < 1:
                errors.append(f"{item_context}: has invalid item requirement")
            if item.get("id") in ids:
                errors.append(f"{context}.{item_key}: has duplicate item {item.get('id')}")
            ids.add(item.get("id"))


def _validate_coverage(
    value: Any,
    context: str,
    errors: list[str],
    catalog_ids: set[str],
    fact_ids: set[str],
    action_facts: dict[str, set[str]],
) -> str | None:
    keys = {"status", "fact_ids", "source_ids", "boundary"}
    if not isinstance(value, dict):
        errors.append(f"{context}: coverage must be an object")
        return None
    status = value.get("status")
    if status == STATUS_NORMALIZED:
        keys.add("normalized_action_id")
    if set(value) != keys:
        errors.append(f"{context}: has unsupported coverage fields for {status!r}")
        return None
    if status not in {STATUS_NORMALIZED, STATUS_SOURCED, STATUS_UNRESOLVED}:
        errors.append(f"{context}: has invalid coverage status")
        return None
    if not _is_nonempty_string(value.get("boundary")):
        errors.append(f"{context}: requires a non-empty coverage boundary")
    local_sources = _source_ids(value.get("source_ids"), catalog_ids, context, errors, allow_empty=status == STATUS_UNRESOLVED)
    referenced_facts = value.get("fact_ids")
    if not isinstance(referenced_facts, list) or any(not _is_nonempty_string(item) for item in referenced_facts):
        errors.append(f"{context}: fact_ids must be an array of non-empty strings")
        referenced_facts = []
    elif len(referenced_facts) != len(set(referenced_facts)):
        errors.append(f"{context}: fact_ids must be unique")
    for fact_id in referenced_facts:
        if fact_id not in fact_ids:
            errors.append(f"{context}: references unknown factual record {fact_id}")
    if status == STATUS_UNRESOLVED:
        if referenced_facts or local_sources:
            errors.append(f"{context}: unresolved coverage cannot claim facts or sources")
    else:
        if not referenced_facts or not local_sources:
            errors.append(f"{context}: sourced coverage requires fact_ids and source_ids")
    if status == STATUS_NORMALIZED:
        action_id = value.get("normalized_action_id")
        if action_id not in action_facts:
            errors.append(f"{context}: references unknown normalized action {action_id}")
        elif not set(referenced_facts) & action_facts[action_id]:
            errors.append(f"{context}: normalized action {action_id} must share a factual record")
    return status


def _validate_checkpoint(
    checkpoint: Any,
    context: str,
    errors: list[str],
    catalog_ids: set[str],
    fact_ids: set[str],
    action_facts: dict[str, set[str]],
) -> tuple[str | None, str | None]:
    if not isinstance(checkpoint, dict) or set(checkpoint) != {"id", "kind", "description", "coverage"}:
        errors.append(f"{context}: checkpoint fields are invalid")
        return None, None
    checkpoint_id = checkpoint.get("id")
    kind = checkpoint.get("kind")
    if not isinstance(checkpoint_id, str) or re.fullmatch(r"(?:checkpoint|external):[a-z0-9][a-z0-9-]*", checkpoint_id) is None:
        errors.append(f"{context}: checkpoint id is invalid")
    if kind not in {"geographic", "bank", "external_partial_quest", "external_quest_completion", "player_observation"}:
        errors.append(f"{context}: checkpoint kind is invalid")
    if not _is_nonempty_string(checkpoint.get("description")):
        errors.append(f"{context}: checkpoint description is required")
    status = _validate_coverage(checkpoint.get("coverage"), f"{context}.coverage", errors, catalog_ids, fact_ids, action_facts)
    if kind == "external_partial_quest" and status == STATUS_NORMALIZED:
        errors.append(f"{context}: partial quest checkpoints cannot be normalized actions")
    if kind == "external_partial_quest" and status not in {STATUS_SOURCED, STATUS_UNRESOLVED}:
        errors.append(f"{context}: partial quest checkpoints require sourced-unmodeled or unresolved coverage")
    return checkpoint_id if isinstance(checkpoint_id, str) else None, kind if isinstance(kind, str) else None


def _validate_step(
    step: Any,
    context: str,
    errors: list[str],
    catalog_ids: set[str],
    fact_ids: set[str],
    action_facts: dict[str, set[str]],
    checkpoint_ids: set[str],
    linked_actions: set[str],
) -> int | None:
    allowed = {"id", "sequence", "instruction", "coverage", "checkpoint_ids"}
    if not isinstance(step, dict) or set(step) - allowed or not {"id", "sequence", "instruction", "coverage"} <= set(step):
        errors.append(f"{context}: step fields are invalid")
        return None
    if not isinstance(step.get("id"), str) or re.fullmatch(r"step:[a-z0-9][a-z0-9-]*", step["id"]) is None:
        errors.append(f"{context}: step id is invalid")
    sequence = step.get("sequence")
    if not _is_nonnegative_int(sequence) or sequence < 1:
        errors.append(f"{context}: step sequence must be a positive integer")
    if not _is_nonempty_string(step.get("instruction")):
        errors.append(f"{context}: step instruction is required")
    status = _validate_coverage(step.get("coverage"), f"{context}.coverage", errors, catalog_ids, fact_ids, action_facts)
    if status == STATUS_NORMALIZED:
        linked_actions.add(step["coverage"]["normalized_action_id"])
    step_checkpoints = step.get("checkpoint_ids", [])
    if not isinstance(step_checkpoints, list) or any(not isinstance(item, str) for item in step_checkpoints):
        errors.append(f"{context}: checkpoint_ids must be a string array")
    else:
        for checkpoint_id in step_checkpoints:
            if checkpoint_id not in checkpoint_ids:
                errors.append(f"{context}: references unknown checkpoint {checkpoint_id}")
    return sequence if _is_nonnegative_int(sequence) else None


def _validate_ordered_steps(
    steps: Any,
    context: str,
    errors: list[str],
    catalog_ids: set[str],
    fact_ids: set[str],
    action_facts: dict[str, set[str]],
    checkpoint_ids: set[str],
    linked_actions: set[str],
) -> None:
    if not isinstance(steps, list) or not steps:
        errors.append(f"{context}: must contain at least one ordered step")
        return
    sequences = [
        _validate_step(step, f"{context}[{index}]", errors, catalog_ids, fact_ids, action_facts, checkpoint_ids, linked_actions)
        for index, step in enumerate(steps)
    ]
    if all(sequence is not None for sequence in sequences) and sequences != list(range(1, len(sequences) + 1)):
        errors.append(f"{context}: sequences must be contiguous and begin at 1")


def _validate_observations(value: Any, context: str, catalog_ids: set[str], errors: list[str], *, minimum: int) -> None:
    if not isinstance(value, list) or len(value) < minimum:
        errors.append(f"{context}: must contain at least {minimum} observations")
        return
    for index, observation in enumerate(value):
        item_context = f"{context}[{index}]"
        if not isinstance(observation, dict) or set(observation) != {"id", "description", "source_ids"}:
            errors.append(f"{item_context}: observation fields are invalid")
            continue
        if not _is_nonempty_string(observation.get("id")) or not _is_nonempty_string(observation.get("description")):
            errors.append(f"{item_context}: observation id and description are required")
        _source_ids(observation.get("source_ids"), catalog_ids, item_context, errors, allow_empty=True)


def validate_segment(segment: dict[str, Any], action_facts: dict[str, set[str]], fact_ids: set[str], label: str) -> list[str]:
    """Validate one non-template segment; exposed for focused boundary tests."""
    errors: list[str] = []
    if set(segment) != SEGMENT_KEYS:
        errors.append(f"{label}: must contain exactly the execution segment contract fields")
        return errors
    if segment.get("segment_schema_version") != 1 or segment.get("segment_type") != "research-only-execution-segment":
        errors.append(f"{label}: has invalid schema version or segment type")
    if not isinstance(segment.get("segment_id"), str) or re.fullmatch(r"segment:[a-z0-9][a-z0-9-]*", segment["segment_id"]) is None:
        errors.append(f"{label}: segment_id is invalid")
    if not _is_nonempty_string(segment.get("name")) or segment.get("status") != "research-proof":
        errors.append(f"{label}: requires a name and research-proof status")
    _validate_purpose(segment.get("purpose"), f"{label}.purpose", errors)
    _validate_boundary(segment.get("facts_strategy_boundary"), f"{label}.facts_strategy_boundary", errors)
    _validate_boundary(segment.get("boundaries"), f"{label}.boundaries", errors)

    catalog = segment.get("source_catalog")
    if not isinstance(catalog, list) or not catalog:
        errors.append(f"{label}: source_catalog must not be empty")
        catalog = []
    catalog_ids: set[str] = set()
    for index, source in enumerate(catalog):
        source_context = f"{label}.source_catalog[{index}]"
        if not isinstance(source, dict) or set(source) != {"id", "url", "used_for", "verified_at"}:
            errors.append(f"{source_context}: source fields are invalid")
            continue
        source_id = source.get("id")
        if not isinstance(source_id, str) or re.fullmatch(r"[a-z0-9][a-z0-9-]*", source_id) is None or source_id in catalog_ids:
            errors.append(f"{source_context}: source id is invalid or duplicated")
        catalog_ids.add(source_id)
        parsed = urlparse(source.get("url", ""))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append(f"{source_context}: source URL must be an HTTP(S) URL")
        if not _is_nonempty_string(source.get("used_for")):
            errors.append(f"{source_context}: used_for is required")
        try:
            date.fromisoformat(source.get("verified_at", ""))
        except (TypeError, ValueError):
            errors.append(f"{source_context}: verified_at must be an ISO date")
    _source_ids(segment.get("source_ids"), catalog_ids, f"{label}.source_ids", errors, allow_empty=False)

    starting = segment.get("starting_state")
    if not isinstance(starting, dict) or set(starting) != {"assumptions", "requirements", "geographic_checkpoint", "bank_checkpoint"}:
        errors.append(f"{label}.starting_state: fields are invalid")
        starting = {}
    assumptions = starting.get("assumptions", [])
    if not isinstance(assumptions, list) or any(not _is_nonempty_string(item) for item in assumptions):
        errors.append(f"{label}.starting_state.assumptions: must be an array of non-empty strings")
    _validate_requirements(starting.get("requirements"), f"{label}.starting_state.requirements", errors)

    checkpoint_ids: set[str] = set()
    checkpoint_kinds: dict[str, str] = {}
    for key, expected_kind in (("geographic_checkpoint", "geographic"), ("bank_checkpoint", "bank")):
        checkpoint_id, kind = _validate_checkpoint(starting.get(key), f"{label}.starting_state.{key}", errors, catalog_ids, fact_ids, action_facts)
        if kind != expected_kind:
            errors.append(f"{label}.starting_state.{key}: must be a {expected_kind} checkpoint")
        if checkpoint_id:
            checkpoint_ids.add(checkpoint_id)
            checkpoint_kinds[checkpoint_id] = kind or ""
    checkpoints = segment.get("checkpoints")
    if not isinstance(checkpoints, list) or not checkpoints:
        errors.append(f"{label}.checkpoints: must not be empty")
        checkpoints = []
    for index, checkpoint in enumerate(checkpoints):
        checkpoint_id, kind = _validate_checkpoint(checkpoint, f"{label}.checkpoints[{index}]", errors, catalog_ids, fact_ids, action_facts)
        if checkpoint_id in checkpoint_ids:
            errors.append(f"{label}.checkpoints: duplicate checkpoint {checkpoint_id}")
        if checkpoint_id:
            checkpoint_ids.add(checkpoint_id)
            checkpoint_kinds[checkpoint_id] = kind or ""

    linked_actions: set[str] = set()
    _validate_ordered_steps(segment.get("execution_steps"), f"{label}.execution_steps", errors, catalog_ids, fact_ids, action_facts, checkpoint_ids, linked_actions)
    branches = segment.get("branches")
    if not isinstance(branches, list):
        errors.append(f"{label}.branches: must be an array")
        branches = []
    branch_ids: set[str] = set()
    for index, branch in enumerate(branches):
        branch_context = f"{label}.branches[{index}]"
        if not isinstance(branch, dict) or set(branch) != {"id", "when", "steps", "coverage"}:
            errors.append(f"{branch_context}: branch fields are invalid")
            continue
        branch_id = branch.get("id")
        if not isinstance(branch_id, str) or re.fullmatch(r"branch:[a-z0-9][a-z0-9-]*", branch_id) is None or branch_id in branch_ids:
            errors.append(f"{branch_context}: branch id is invalid or duplicated")
        branch_ids.add(branch_id)
        if not _is_nonempty_string(branch.get("when")):
            errors.append(f"{branch_context}: requires an explicit branch condition")
        _validate_coverage(branch.get("coverage"), f"{branch_context}.coverage", errors, catalog_ids, fact_ids, action_facts)
        _validate_ordered_steps(branch.get("steps"), f"{branch_context}.steps", errors, catalog_ids, fact_ids, action_facts, checkpoint_ids, linked_actions)

    _validate_safety(segment.get("safety_hcim"), f"{label}.safety_hcim", catalog_ids, errors)
    _validate_passive_checks(segment.get("passive_recurring_checks"), f"{label}.passive_recurring_checks", catalog_ids, errors)
    _validate_observations(segment.get("completion_observations"), f"{label}.completion_observations", catalog_ids, errors, minimum=1)
    stop_reentry = segment.get("stop_reentry_conditions")
    if not isinstance(stop_reentry, dict) or set(stop_reentry) != {"stop_conditions", "reentry_conditions"}:
        errors.append(f"{label}.stop_reentry_conditions: fields are invalid")
    else:
        for key in ("stop_conditions", "reentry_conditions"):
            if not isinstance(stop_reentry[key], list) or not stop_reentry[key] or any(not _is_nonempty_string(item) for item in stop_reentry[key]):
                errors.append(f"{label}.stop_reentry_conditions.{key}: must be a non-empty string array")
    estimated_time = segment.get("estimated_time")
    if not isinstance(estimated_time, dict) or not {"status", "source_ids", "uncertainty"} <= set(estimated_time):
        errors.append(f"{label}.estimated_time: fields are invalid")
    else:
        status = estimated_time.get("status")
        allowed = {"status", "source_ids", "uncertainty"}
        if status == "sourced_range":
            allowed |= {"minutes_min", "minutes_max"}
        if set(estimated_time) != allowed or status not in {"not_estimated", "sourced_range"}:
            errors.append(f"{label}.estimated_time: has invalid timing contract")
        _source_ids(estimated_time.get("source_ids"), catalog_ids, f"{label}.estimated_time", errors, allow_empty=status == "not_estimated")
        if not _is_nonempty_string(estimated_time.get("uncertainty")):
            errors.append(f"{label}.estimated_time: uncertainty is required")
        if status == "not_estimated" and estimated_time.get("source_ids"):
            errors.append(f"{label}.estimated_time: not_estimated cannot claim timing sources")
        if status == "sourced_range":
            if not _is_nonnegative_int(estimated_time.get("minutes_min")) or not _is_nonnegative_int(estimated_time.get("minutes_max")) or estimated_time["minutes_min"] > estimated_time["minutes_max"]:
                errors.append(f"{label}.estimated_time: sourced range bounds are invalid")
    boundaries = segment.get("normalization_boundaries")
    if not isinstance(boundaries, list) or not boundaries:
        errors.append(f"{label}.normalization_boundaries: must not be empty")
        boundaries = []
    bounded_actions: set[str] = set()
    for index, boundary in enumerate(boundaries):
        boundary_context = f"{label}.normalization_boundaries[{index}]"
        if not isinstance(boundary, dict) or set(boundary) != {"normalized_action_id", "does_not_prove", "requires_separate_player_observation"}:
            errors.append(f"{boundary_context}: fields are invalid")
            continue
        action_id = boundary.get("normalized_action_id")
        if action_id not in action_facts or action_id in bounded_actions:
            errors.append(f"{boundary_context}: normalized action is unknown or repeated")
        bounded_actions.add(action_id)
        does_not_prove = boundary.get("does_not_prove")
        if not isinstance(does_not_prove, list) or not does_not_prove or any(not _is_nonempty_string(item) for item in does_not_prove):
            errors.append(f"{boundary_context}: does_not_prove must be a non-empty string array")
        if boundary.get("requires_separate_player_observation") is not True:
            errors.append(f"{boundary_context}: must require separate player observation")
    for action_id in linked_actions - bounded_actions:
        errors.append(f"{label}: linked normalized action {action_id} lacks a coarse-action boundary")
    if any(kind == "external_partial_quest" for kind in checkpoint_kinds.values()):
        if any("partial" in item.lower() for boundary in boundaries if isinstance(boundary, dict) for item in boundary.get("does_not_prove", []) if isinstance(item, str)) is False:
            errors.append(f"{label}: partial quest coverage requires a coarse-action boundary that explicitly excludes partial progress")
    return errors


def _canonical_action_facts(root: Path) -> dict[str, set[str]]:
    actions = load_json(root / "data/progression/actions.json")["actions"]
    return {action["id"]: set(action["fact_ids"]) for action in actions}


def _canonical_fact_ids(root: Path) -> set[str]:
    fact_ids: set[str] = set()
    for path in (root / "data/facts").glob("*.json"):
        fact_ids.update(record["id"] for record in load_json(path).get("records", []))
    return fact_ids


def validate(root: Path = ROOT) -> tuple[list[str], dict[str, int]]:
    """Validate manifested execution segments without modifying account or route state."""
    errors: list[str] = []
    report = {"segments": 0, "linked_normalized_actions": 0, "sourced_unmodeled_steps": 0, "unresolved_partial_quest_checkpoints": 0}
    schema_path = root / SCHEMA_RELATIVE
    manifest_path = root / SEGMENTS_RELATIVE / "integration-manifest.json"
    if not schema_path.exists() or not manifest_path.exists():
        return ["execution segment schema and manifest must exist"], report
    _verify_ascii_and_whitespace(schema_path, errors)
    schema = load_json(schema_path)
    if schema.get("additionalProperties") is not False or schema.get("properties", {}).get("segment_schema_version", {}).get("const") != 1:
        errors.append("execution segment schema must be strict and versioned")
    coverage_statuses = schema.get("$defs", {}).get("coverage", {}).get("properties", {}).get("status", {}).get("enum")
    if coverage_statuses != [STATUS_NORMALIZED, STATUS_SOURCED, STATUS_UNRESOLVED]:
        errors.append("execution segment schema must enumerate the three coverage states")
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict) or set(manifest) != {"manifest_schema_version", "package_type", "segments", "template", "boundary"}:
        return errors + ["execution segment manifest fields are invalid"], report
    if manifest["manifest_schema_version"] != 1 or manifest["package_type"] != "research-only-execution-segment" or not _is_nonempty_string(manifest["boundary"]):
        errors.append("execution segment manifest has invalid metadata")
    segment_names = manifest.get("segments")
    if not isinstance(segment_names, list) or not segment_names or len(segment_names) != len(set(segment_names)):
        return errors + ["execution segment manifest must list unique segment files"], report
    action_facts = _canonical_action_facts(root)
    fact_ids = _canonical_fact_ids(root)
    for segment_name in segment_names:
        if not isinstance(segment_name, str) or Path(segment_name).name != segment_name or not segment_name.endswith(".json"):
            errors.append(f"execution segment manifest has unsafe segment name {segment_name!r}")
            continue
        path = root / SEGMENTS_RELATIVE / segment_name
        if not path.exists():
            errors.append(f"execution segment file is missing: {segment_name}")
            continue
        _verify_ascii_and_whitespace(path, errors)
        segment = load_json(path)
        errors.extend(validate_segment(segment, action_facts, fact_ids, segment_name))
        report["segments"] += 1
        for step in segment.get("execution_steps", []):
            status = step.get("coverage", {}).get("status") if isinstance(step, dict) else None
            report["linked_normalized_actions"] += status == STATUS_NORMALIZED
            report["sourced_unmodeled_steps"] += status == STATUS_SOURCED
        for checkpoint in segment.get("checkpoints", []):
            if isinstance(checkpoint, dict) and checkpoint.get("kind") == "external_partial_quest" and checkpoint.get("coverage", {}).get("status") == STATUS_UNRESOLVED:
                report["unresolved_partial_quest_checkpoints"] += 1
    return errors, report


def main() -> int:
    errors, report = validate()
    if errors:
        print("Execution segment validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Execution segment validation passed: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
