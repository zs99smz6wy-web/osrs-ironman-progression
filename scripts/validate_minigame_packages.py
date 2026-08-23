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
PACKAGES_DIR = ROOT / "research" / "minigame-packages"
MANIFEST_PATH = PACKAGES_DIR / "integration-manifest.json"
SCHEMA_PATH = ROOT / "research" / "package-schemas" / "minigame-package.schema.json"
SOURCES_PATH = ROOT / "research" / "sources.json"
W0_ID = "W0-source-provenance-and-contract"
W0_TARGETS = {
    "research/sources.json",
    "scripts/validate_minigame_packages.py",
    "tests/test_validate_minigame_packages.py",
}
COMMUNITY_KINDS = {"github", "guide", "reddit", "youtube"}


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


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_uri(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_schema_value(value: Any, schema: dict[str, Any], context: str, errors: list[str]) -> None:
    """Validate the schema constructs used by the research package contract.

    This intentionally small validator keeps the repository self-contained while
    enforcing every constraint present in minigame-package.schema.json.
    """

    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
        type_matches = {
            "object": isinstance(value, dict),
            "array": isinstance(value, list),
            "string": isinstance(value, str),
            "number": is_number(value),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
            "null": value is None,
        }
        if not any(type_matches.get(name, False) for name in expected_types):
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
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_schema_value(item, item_schema, f"{context}[{index}]", errors)

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{context}: missing required key {key}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unexpected = set(value) - set(properties)
            if unexpected:
                errors.append(f"{context}: unexpected keys {sorted(unexpected)}")
        for key, property_schema in properties.items():
            if key in value and isinstance(property_schema, dict):
                validate_schema_value(value[key], property_schema, f"{context}.{key}", errors)


def package_source_references(value: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key == "source_catalog":
                continue
            if key == "source_ids" and isinstance(child, list):
                for index, source_id in enumerate(child):
                    yield f"{child_path}[{index}]", source_id
                continue
            if key == "source_id":
                yield child_path, child
                continue
            yield from package_source_references(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from package_source_references(child, f"{path}[{index}]")


def verify_ascii_and_whitespace(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.isascii():
        errors.append(f"{path.relative_to(ROOT).as_posix()}: must contain ASCII only")
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.rstrip(" \t") != line:
            errors.append(f"{path.relative_to(ROOT).as_posix()}:{line_number}: trailing whitespace")


def validate_w0_boundary(manifest: dict[str, Any], errors: list[str]) -> None:
    waves = manifest.get("integration_waves")
    if not isinstance(waves, list) or not waves:
        errors.append("manifest must declare integration waves")
        return
    wave = waves[0]
    if not isinstance(wave, dict) or wave.get("id") != W0_ID:
        errors.append("first integration wave must be W0-source-provenance-and-contract")
        return
    if set(wave.get("target_files", [])) != W0_TARGETS:
        errors.append("W0 target files must remain limited to sources, validator, and focused test")
    must_not_do = str(wave.get("must_not_do", "")).lower()
    for protected_surface in ("production facts", "actions", "graph nodes", "account-state"):
        if protected_surface not in must_not_do:
            errors.append(f"W0 must explicitly protect {protected_surface}")


def validate() -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    report: dict[str, Any] = {
        "packages": 0,
        "source_references": 0,
        "canonical_sources": 0,
        "package_scoped_aliases": 0,
        "community_strategy_aliases": 0,
    }
    manifest = load_json(MANIFEST_PATH)
    schema = load_json(SCHEMA_PATH)
    sources_document = load_json(SOURCES_PATH)
    if not isinstance(manifest, dict) or not isinstance(schema, dict) or not isinstance(sources_document, dict):
        return ["manifest, schema, and source registry must be JSON objects"], report

    validate_w0_boundary(manifest, errors)
    expected_rows = manifest.get("input_set", {}).get("packages", [])
    expected_count = manifest.get("input_set", {}).get("package_count")
    if not isinstance(expected_rows, list) or expected_count != 17 or len(expected_rows) != expected_count:
        errors.append("manifest must inventory exactly seventeen minigame packages")
        return errors, report

    expected_by_path: dict[str, dict[str, Any]] = {}
    for row in expected_rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            errors.append("manifest package inventory rows need a path")
            continue
        if row["path"] in expected_by_path:
            errors.append(f"manifest repeats package path {row['path']}")
        expected_by_path[row["path"]] = row
    expected_paths = set(expected_by_path)
    actual_paths = {
        path.relative_to(ROOT).as_posix()
        for path in PACKAGES_DIR.glob("*.json")
        if path.name != MANIFEST_PATH.name
    }
    if actual_paths != expected_paths:
        errors.append(f"minigame package paths differ from manifest: expected {sorted(expected_paths)}, got {sorted(actual_paths)}")

    registry_sources = sources_document.get("sources", [])
    if not isinstance(registry_sources, list):
        errors.append("research source registry must contain a sources array")
        return errors, report
    canonical_sources: dict[str, dict[str, Any]] = {}
    for source in registry_sources:
        if not isinstance(source, dict) or not isinstance(source.get("id"), str) or not source["id"]:
            errors.append("research source registry must use non-empty source IDs")
            continue
        source_id = source["id"]
        if source_id in canonical_sources:
            errors.append(f"duplicate canonical source ID {source_id}")
        canonical_sources[source_id] = source

    aliases = sources_document.get("source_aliases", [])
    if not isinstance(aliases, list):
        errors.append("research source registry must contain a source_aliases array")
        return errors, report
    aliases_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for alias in aliases:
        if not isinstance(alias, dict):
            errors.append("source alias must be an object")
            continue
        package_ids = alias.get("package_ids")
        if not isinstance(package_ids, list):
            errors.append("source alias package_ids must be an array")
            continue
        for package_id in package_ids:
            source_id = alias.get("package_source_id")
            key = (package_id, source_id)
            if key in aliases_by_key:
                errors.append(f"duplicate package-scoped source alias {package_id}:{source_id}")
            aliases_by_key[key] = alias

    expected_package_ids: set[str] = set()
    seen_actions: set[str] = set()
    seen_nodes: set[str] = set()
    seen_facts: set[str] = set()
    expected_source_keys: set[tuple[str, str]] = set()
    expected_canonical_ids: set[str] = set()
    expected_reference_count = 0

    for relative_path in sorted(expected_paths):
        path = ROOT / relative_path
        label = path.stem
        verify_ascii_and_whitespace(path, errors)
        package = load_json(path)
        if not isinstance(package, dict):
            errors.append(f"{label}: package must be an object")
            continue
        validate_schema_value(package, schema, label, errors)
        report["packages"] += 1

        expected = expected_by_path[relative_path]
        package_id = package.get("package_id")
        if package_id != expected.get("package_id"):
            errors.append(f"{label}: package_id differs from manifest")
        elif package_id in expected_package_ids:
            errors.append(f"duplicate package ID {package_id}")
        else:
            expected_package_ids.add(package_id)
        if package.get("activity") != expected.get("activity"):
            errors.append(f"{label}: activity differs from manifest")

        normalization = package.get("proposed_normalization", {})
        for field, seen, expected_total in (
            ("facts", seen_facts, expected.get("facts")),
            ("actions", seen_actions, expected.get("actions")),
        ):
            records = normalization.get(field) if isinstance(normalization, dict) else None
            if not isinstance(records, list) or len(records) != expected_total:
                errors.append(f"{label}: expected {expected_total} proposed {field}")
                continue
            for index, record in enumerate(records):
                record_id = record.get("id") if isinstance(record, dict) else None
                if not isinstance(record_id, str) or not record_id.strip():
                    errors.append(f"{label}:{field}[{index}]: needs a non-empty ID")
                elif record_id in seen:
                    errors.append(f"duplicate proposed {field[:-1]} ID {record_id}")
                else:
                    seen.add(record_id)
        nodes = normalization.get("graph_nodes") if isinstance(normalization, dict) else None
        if not isinstance(nodes, list) or len(nodes) != expected.get("nodes"):
            errors.append(f"{label}: expected {expected.get('nodes')} proposed graph nodes")
        else:
            for index, node_id in enumerate(nodes):
                if not isinstance(node_id, str) or not node_id.strip():
                    errors.append(f"{label}:graph_nodes[{index}]: needs a non-empty ID")
                elif node_id in seen_nodes:
                    errors.append(f"duplicate proposed graph node ID {node_id}")
                else:
                    seen_nodes.add(node_id)
        edges = normalization.get("graph_edges") if isinstance(normalization, dict) else None
        if not isinstance(edges, list) or len(edges) != expected.get("edges"):
            errors.append(f"{label}: expected {expected.get('edges')} proposed graph edges")
        observations = normalization.get("account_observations") if isinstance(normalization, dict) else None
        if not isinstance(observations, list) or len(observations) != expected.get("observations"):
            errors.append(f"{label}: expected {expected.get('observations')} proposed account observations")

        boundary = package.get("facts_strategy_boundary")
        if not isinstance(boundary, dict):
            errors.append(f"{label}: needs a facts/strategy boundary")

        catalog = package.get("source_catalog", [])
        local_sources: dict[str, dict[str, Any]] = {}
        if not isinstance(catalog, list):
            errors.append(f"{label}: source_catalog must be an array")
            continue
        for source in catalog:
            if not isinstance(source, dict) or not isinstance(source.get("id"), str):
                errors.append(f"{label}: source catalog entries need an ID")
                continue
            source_id = source["id"]
            if source_id in local_sources:
                errors.append(f"{label}: duplicate package source ID {source_id}")
                continue
            local_sources[source_id] = source
            expected_reference_count += 1
            expected_source_keys.add((package_id, source_id))
            alias = aliases_by_key.get((package_id, source_id))
            if alias is None:
                errors.append(f"{label}:{source_id}: needs an exact package-scoped source alias")
                continue
            canonical_id = alias.get("canonical_source_id")
            canonical = canonical_sources.get(canonical_id)
            if canonical is None:
                errors.append(f"{label}:{source_id}: alias targets unknown canonical source {canonical_id}")
                continue
            expected_canonical_ids.add(canonical_id)
            for field in ("url", "publisher", "kind", "checked_at", "use"):
                if alias.get(field) != source.get(field):
                    errors.append(f"{label}:{source_id}: alias {field} must exactly preserve package provenance")
            if canonical.get("url") != source.get("url"):
                errors.append(f"{label}:{source_id}: canonical source URL must exactly equal package URL")
            community = source.get("kind") in COMMUNITY_KINDS
            if community and alias.get("treatment") != "community-strategy-candidate-not-fact":
                errors.append(f"{label}:{source_id}: community source must be marked strategy-candidate-not-fact")
            if not community and alias.get("treatment") != "factual-source-provenance":
                errors.append(f"{label}:{source_id}: factual source must be marked factual-source-provenance")

        for reference_path, source_id in package_source_references(package):
            if not isinstance(source_id, str):
                errors.append(f"{label}:{reference_path}: source reference must be a string")
            elif source_id not in local_sources:
                errors.append(f"{label}:{reference_path}: source reference {source_id} is absent from source_catalog")

    minigame_alias_keys = {
        key for key in aliases_by_key if isinstance(key[0], str) and key[0].startswith("research-minigame-")
    }
    unexpected_aliases = minigame_alias_keys - expected_source_keys
    if unexpected_aliases:
        errors.append(f"unexpected minigame aliases {sorted(unexpected_aliases)}")
    if len(expected_source_keys) != expected_reference_count:
        errors.append("package source catalog keys must be unique across each package")
    if report["packages"] != expected_count or len(expected_package_ids) != expected_count:
        errors.append("minigame package count or package IDs do not match the manifest")

    report["source_references"] = expected_reference_count
    report["canonical_sources"] = len(expected_canonical_ids)
    report["package_scoped_aliases"] = len(expected_source_keys & minigame_alias_keys)
    report["community_strategy_aliases"] = sum(
        1
        for package_id, source_id in expected_source_keys
        if aliases_by_key[(package_id, source_id)].get("treatment") == "community-strategy-candidate-not-fact"
    )
    verify_ascii_and_whitespace(SOURCES_PATH, errors)
    return errors, report


def main() -> int:
    errors, report = validate()
    if errors:
        print("Minigame package validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        "Minigame package validation passed: "
        f"{report['packages']} packages, {report['source_references']} source references, "
        f"{report['canonical_sources']} canonical sources, "
        f"{report['package_scoped_aliases']} package-scoped aliases, and "
        f"{report['community_strategy_aliases']} community strategy aliases."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
