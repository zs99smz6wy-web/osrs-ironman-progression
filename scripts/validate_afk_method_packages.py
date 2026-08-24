from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_RELATIVE_DIRECTORY = Path("research/afk-method-packages")
MANIFEST_NAME = "integration-manifest.json"
TEMPLATE_NAME = "template.json"
SCHEMA_RELATIVE_PATH = Path("research/package-schemas/afk-method-package.schema.json")
PHASES = {"pending", "completed"}
FORBIDDEN_FIELDS = {
    "score",
    "scores",
    "strategy_score",
    "ranking",
    "rank",
    "route_order",
    "preferred_route_order",
    "account_readiness",
    "recommended_99",
    "guaranteed_rng",
    "guaranteed_hourly_rate",
    "hourly_rate",
}
FORBIDDEN_TEXT = re.compile(
    r"\b(?:recommended\s+99|preferred\s+route(?:\s+order)?|account\s+readiness|"
    r"guaranteed\s+(?:rng|.*?(?:hourly|per\s+hour|/hour))|"
    r"(?:rng|hourly|per\s+hour|/hour)\s+guarantee)\b",
    re.IGNORECASE,
)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def valid_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def is_uri(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_schema_value(
    value: Any, schema: dict[str, Any], root_schema: dict[str, Any], context: str, errors: list[str]
) -> None:
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/$defs/"):
        definition = root_schema.get("$defs", {}).get(reference.rsplit("/", 1)[-1])
        if not isinstance(definition, dict):
            errors.append(f"{context}: schema reference {reference} is unavailable")
            return
        validate_schema_value(value, definition, root_schema, context, errors)
        return

    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
        matches = {
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
            "string": isinstance(value, str),
            "number": is_number(value),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
            "null": value is None,
        }
        if not any(matches.get(name, False) for name in expected_types):
            errors.append(f"{context}: expected type {' or '.join(expected_types)}")
            return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{context}: expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{context}: value is not in the allowed enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{context}: string is shorter than minLength")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{context}: string does not match required pattern")
        if schema.get("format") == "uri" and not is_uri(value):
            errors.append(f"{context}: must be an absolute HTTP(S) URI")
    if is_number(value) and "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{context}: must be at least {schema['minimum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{context}: array has fewer than {schema['minItems']} entries")
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                validate_schema_value(item, schema["items"], root_schema, f"{context}[{index}]", errors)
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{context}: missing required key {key}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unexpected = set(value) - set(properties)
            if unexpected:
                errors.append(f"{context}: unexpected keys {sorted(unexpected)}")
        for key, property_schema in properties.items():
            if key in value and isinstance(property_schema, dict):
                validate_schema_value(value[key], property_schema, root_schema, f"{context}.{key}", errors)


def verify_ascii_and_whitespace(path: Path, root: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    label = path.relative_to(root).as_posix()
    if not text.isascii():
        errors.append(f"{label}: must contain ASCII only")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.rstrip(" \t") != line:
            errors.append(f"{label}:{line_number}: trailing whitespace")


def source_references(value: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key == "source_catalog":
                continue
            if key == "source_id":
                yield child_path, child
                continue
            if key == "source_ids" and isinstance(child, list):
                for index, source_id in enumerate(child):
                    yield f"{child_path}[{index}]", source_id
                continue
            yield from source_references(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from source_references(child, f"{path}[{index}]")


def strategy_firewall(value: Any, path: str = "") -> Iterator[str]:
    if path.startswith("facts_strategy_boundary.excluded"):
        return
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key.lower() in FORBIDDEN_FIELDS:
                yield f"{child_path}: factual package contains forbidden strategy field {key}"
            yield from strategy_firewall(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from strategy_firewall(child, f"{path}[{index}]")
    elif isinstance(value, str) and FORBIDDEN_TEXT.search(value):
        yield f"{path}: factual package contains forbidden strategy or guaranteed-rate claim"


def record_ids(records: Any, label: str, errors: list[str]) -> list[str]:
    if not isinstance(records, list):
        errors.append(f"{label}: must be an array")
        return []
    result = []
    for index, record in enumerate(records):
        record_id = record.get("id") if isinstance(record, dict) else None
        if not isinstance(record_id, str) or not record_id.strip():
            errors.append(f"{label}[{index}]: needs a non-empty id")
        else:
            result.append(record_id)
    return result


def validate_package(package: dict[str, Any], schema: dict[str, Any], label: str, errors: list[str]) -> dict[str, set[str]]:
    validate_schema_value(package, schema, schema, label, errors)
    if not valid_date(package.get("checked_at")):
        errors.append(f"{label}: checked_at must be a real ISO date")
    boundary = package.get("facts_strategy_boundary", {})
    excluded = boundary.get("excluded", []) if isinstance(boundary, dict) else []
    excluded_text = " ".join(item.lower() for item in excluded if isinstance(item, str))
    for required_term in ("strategy", "route", "readiness", "99", "rng", "hourly"):
        if required_term not in excluded_text:
            errors.append(f"{label}: facts_strategy_boundary.excluded must explicitly exclude {required_term}")

    catalog = package.get("source_catalog", [])
    local_sources: set[str] = set()
    if isinstance(catalog, list):
        for index, source in enumerate(catalog):
            source_label = f"{label}:source_catalog[{index}]"
            if not isinstance(source, dict):
                continue
            source_id = source.get("id")
            if not isinstance(source_id, str) or not source_id:
                continue
            if source_id in local_sources:
                errors.append(f"{label}: duplicate source catalog id {source_id}")
            local_sources.add(source_id)
            if not valid_date(source.get("checked_at")):
                errors.append(f"{source_label}: checked_at must be a real ISO date")
            if not is_uri(source.get("url")):
                errors.append(f"{source_label}: url must be an absolute HTTP(S) URI")
    for reference_path, source_id in source_references(package):
        if not isinstance(source_id, str) or source_id not in local_sources:
            errors.append(f"{label}:{reference_path}: source reference {source_id!r} is absent from source_catalog")

    attention = package.get("attention_profile", {})
    if isinstance(attention, dict):
        for index, cadence in enumerate(attention.get("interaction_cadence", [])):
            if not isinstance(cadence, dict):
                continue
            source_ids = cadence.get("source_ids")
            if cadence.get("evidence_type") == "source" and (not isinstance(source_ids, list) or not source_ids):
                errors.append(f"{label}:interaction_cadence[{index}]: sourced cadence needs source_ids")
            if cadence.get("evidence_type") == "player_observation" and source_ids:
                errors.append(f"{label}:interaction_cadence[{index}]: observed cadence must not imply a factual source")

    outputs = package.get("outputs", {})
    output_ids: set[str] = set()
    expected_groups = {"deterministic": "deterministic", "variable": "variable", "player_observed": "player_observed"}
    if isinstance(outputs, dict):
        for group, expected_kind in expected_groups.items():
            for output in outputs.get(group, []):
                if not isinstance(output, dict):
                    continue
                output_id = output.get("id")
                if isinstance(output_id, str):
                    if output_id in output_ids:
                        errors.append(f"{label}: output id {output_id} appears in more than one output boundary")
                    output_ids.add(output_id)
                if output.get("boundary") not in {None, expected_kind}:
                    errors.append(f"{label}:{group}: output boundary must be {expected_kind}")

    normalization = package.get("proposed_normalization", {})
    result: dict[str, set[str]] = {}
    if isinstance(normalization, dict):
        for field in ("facts", "actions", "nodes", "edges", "observations"):
            result[field] = set(record_ids(normalization.get(field), f"{label}:proposed_normalization.{field}", errors))
    return result


def validate(root: Path = ROOT) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    report = {"planned_packages": 0, "completed_packages": 0, "source_references": 0}
    package_directory = root / PACKAGE_RELATIVE_DIRECTORY
    manifest_path = package_directory / MANIFEST_NAME
    schema_path = root / SCHEMA_RELATIVE_PATH
    if not manifest_path.exists() or not schema_path.exists():
        return ["AFK package manifest and schema must exist"], report
    verify_ascii_and_whitespace(manifest_path, root, errors)
    verify_ascii_and_whitespace(schema_path, root, errors)
    manifest = load_json(manifest_path)
    schema = load_json(schema_path)
    if not isinstance(manifest, dict) or not isinstance(schema, dict):
        return ["AFK package manifest and schema must be JSON objects"], report
    if manifest.get("template_path") != (PACKAGE_RELATIVE_DIRECTORY / TEMPLATE_NAME).as_posix() or manifest.get("template_inventory_policy") != "excluded":
        errors.append("manifest must explicitly exclude template.json from package inventory")
    rows = manifest.get("packages")
    if not isinstance(rows, list) or len(rows) != 5:
        errors.append("manifest must inventory exactly five planned AFK method packages")
        return errors, report

    expected_paths: set[str] = set()
    expected_ids: set[str] = set()
    completed_rows: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            errors.append("manifest package inventory entries must be objects")
            continue
        path, package_id, method, phase = row.get("path"), row.get("package_id"), row.get("method"), row.get("phase")
        if not all(isinstance(value, str) and value for value in (path, package_id, method)) or phase not in PHASES:
            errors.append("manifest package entries need path, package_id, method, and valid phase")
            continue
        if path in expected_paths or package_id in expected_ids:
            errors.append(f"manifest repeats AFK package path or id {path} / {package_id}")
        expected_paths.add(path)
        expected_ids.add(package_id)
        report["planned_packages"] += 1
        package_path = root / path
        if phase == "pending" and package_path.exists():
            errors.append(f"{path}: pending package must not exist")
        if phase == "completed":
            completed_rows.append(row)
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in package_directory.glob("*.json")
        if path.name not in {MANIFEST_NAME, TEMPLATE_NAME}
    }
    completed_paths = {row["path"] for row in completed_rows}
    if actual_paths != completed_paths:
        errors.append(f"AFK completed package paths differ from manifest: expected {sorted(completed_paths)}, got {sorted(actual_paths)}")

    global_ids = {field: set() for field in ("facts", "actions", "nodes", "edges", "observations")}
    for row in completed_rows:
        path = root / row["path"]
        label = path.stem
        if not path.exists():
            errors.append(f"{row['path']}: completed package is missing")
            continue
        verify_ascii_and_whitespace(path, root, errors)
        package = load_json(path)
        if not isinstance(package, dict):
            errors.append(f"{label}: package must be a JSON object")
            continue
        report["completed_packages"] += 1
        if package.get("package_id") != row["package_id"] or package.get("method") != row["method"]:
            errors.append(f"{label}: package_id or method differs from manifest")
        for finding in strategy_firewall(package):
            errors.append(f"{label}:{finding}")
        normalized_ids = validate_package(package, schema, label, errors)
        report["source_references"] += sum(1 for _ in source_references(package))
        for field, ids in normalized_ids.items():
            duplicates = global_ids[field] & ids
            for identifier in sorted(duplicates):
                errors.append(f"duplicate proposed {field[:-1]} id {identifier}")
            global_ids[field].update(ids)
    return errors, report


def main() -> int:
    errors, report = validate()
    if errors:
        print("AFK method package validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        "AFK method package validation passed: "
        f"{report['planned_packages']} planned packages and {report['completed_packages']} completed packages."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
