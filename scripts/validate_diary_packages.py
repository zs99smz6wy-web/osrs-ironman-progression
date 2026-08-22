from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DIARY_DIR = ROOT / "research" / "diary-packages"
MANIFEST_PATH = DIARY_DIR / "integration-manifest.json"
SCHEMA_PATH = ROOT / "research" / "package-schemas" / "diary-package.schema.json"
SOURCES_PATH = ROOT / "research" / "sources.json"
TIER_ORDER = ("easy", "medium", "hard", "elite")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def valid_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def package_key(path: str) -> str:
    return Path(path).stem


def package_tasks(package: dict[str, Any], label: str, errors: list[str]) -> list[tuple[str, dict[str, Any]]]:
    tasks = package.get("tasks")
    tiers = package.get("tiers")
    flat_tasks = tasks if isinstance(tasks, list) else None
    nested_tiers = tiers if isinstance(tiers, list) else None

    if flat_tasks is not None and flat_tasks:
        if nested_tiers:
            errors.append(f"{label}: may use either flat tasks or non-empty nested tiers, not both")
        result: list[tuple[str, dict[str, Any]]] = []
        for task in flat_tasks:
            if not isinstance(task, dict):
                errors.append(f"{label}: flat task must be an object")
                continue
            tier = task.get("tier")
            if tier not in TIER_ORDER:
                errors.append(f"{label}:{task.get('id', '<missing id>')}: flat task needs a canonical tier")
                continue
            result.append((tier, task))
        return result

    if nested_tiers is not None and nested_tiers:
        result = []
        seen_tiers: set[str] = set()
        for tier_record in nested_tiers:
            if not isinstance(tier_record, dict) or tier_record.get("tier") not in TIER_ORDER:
                errors.append(f"{label}: nested tier needs a canonical tier name")
                continue
            tier = tier_record["tier"]
            if tier in seen_tiers:
                errors.append(f"{label}: duplicate nested tier {tier}")
            seen_tiers.add(tier)
            tier_tasks = tier_record.get("tasks")
            if not isinstance(tier_tasks, list) or not tier_tasks:
                errors.append(f"{label}:{tier}: tier needs a non-empty tasks array")
                continue
            for task in tier_tasks:
                if not isinstance(task, dict):
                    errors.append(f"{label}:{tier}: nested task must be an object")
                else:
                    result.append((tier, task))
        return result

    errors.append(f"{label}: needs either non-empty flat tasks or non-empty nested tiers")
    return []


def package_claim_tiers(package: dict[str, Any]) -> set[str]:
    for key in ("tier_reward_claims", "tier_rewards", "tier_claims"):
        claims = package.get(key)
        if isinstance(claims, list):
            return {claim.get("tier") for claim in claims if isinstance(claim, dict)}
    tiers = package.get("tiers")
    if isinstance(tiers, list):
        return {tier.get("tier") for tier in tiers if isinstance(tier, dict) and isinstance(tier.get("reward"), dict)}
    return set()


def source_resolution(
    sources_document: dict[str, Any], package_id: str, source_id: str
) -> dict[str, Any] | None:
    canonical_sources = {
        source.get("id"): source
        for source in sources_document.get("sources", [])
        if isinstance(source, dict) and isinstance(source.get("id"), str)
    }
    for alias in sources_document.get("source_aliases", []):
        if not isinstance(alias, dict):
            continue
        package_ids = alias.get("package_ids", [])
        if package_id in package_ids and alias.get("package_source_id") == source_id:
            canonical_id = alias.get("canonical_source_id")
            canonical = canonical_sources.get(canonical_id)
            if canonical is None:
                return {"error": f"alias targets unknown canonical source {canonical_id}"}
            return {"source": canonical, "alias": alias}
    canonical = canonical_sources.get(source_id)
    return {"source": canonical, "alias": None} if canonical else None


def validate() -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    report: dict[str, Any] = {"packages": 0, "tasks": 0, "catalog_inheritance_packages": []}
    manifest = load_json(MANIFEST_PATH)
    schema = load_json(SCHEMA_PATH)
    sources_document = load_json(SOURCES_PATH)

    required_schema_keys = {"$schema", "$id", "title", "description", "properties", "$defs"}
    missing_schema_keys = required_schema_keys - schema.keys()
    if missing_schema_keys:
        errors.append(f"diary schema missing {sorted(missing_schema_keys)}")

    inventory = manifest.get("input_set", {}).get("region_inventory", [])
    package_paths = manifest.get("input_set", {}).get("package_paths", [])
    if not isinstance(inventory, list) or not isinstance(package_paths, list) or len(inventory) != 12 or len(package_paths) != 12:
        errors.append("manifest must define exactly twelve diary packages and inventory rows")
        return errors, report

    inventory_by_package = {row.get("package"): row for row in inventory if isinstance(row, dict)}
    expected_paths = {Path(path).as_posix() for path in package_paths}
    actual_paths = {
        path.relative_to(ROOT).as_posix()
        for path in DIARY_DIR.glob("*.json")
        if path.name != MANIFEST_PATH.name
    }
    if actual_paths != expected_paths:
        errors.append(f"diary package paths differ from manifest: expected {sorted(expected_paths)}, got {sorted(actual_paths)}")

    per_task_packages = set(
        manifest.get("validation_results", {})
        .get("source_reference_coverage", {})
        .get("per_task_or_tier_source_ids", [])
    )
    catalog_only_packages = set(
        manifest.get("validation_results", {})
        .get("source_reference_coverage", {})
        .get("catalog_level_source_coverage_only", [])
    )
    expected_package_ids = {package_key(path) for path in package_paths}
    if per_task_packages | catalog_only_packages != expected_package_ids or per_task_packages & catalog_only_packages:
        errors.append("manifest source-provenance coverage must partition the twelve packages")

    registered_sources = sources_document.get("sources", [])
    canonical_sources = {
        source.get("id"): source
        for source in registered_sources
        if isinstance(source, dict) and isinstance(source.get("id"), str)
    }
    if len(canonical_sources) != len(registered_sources):
        grouped_sources: dict[str, set[str]] = {}
        for source in registered_sources:
            if not isinstance(source, dict) or not isinstance(source.get("id"), str) or not source["id"]:
                errors.append("research source registry must use non-empty source ids")
                continue
            grouped_sources.setdefault(source["id"], set()).add(str(source.get("url")))
        for source_id, urls in grouped_sources.items():
            if len(urls) > 1:
                errors.append(f"research source registry uses conflicting URLs for {source_id}")
    alias_keys: set[tuple[str, str]] = set()
    for alias in sources_document.get("source_aliases", []):
        if not isinstance(alias, dict):
            errors.append("source alias must be an object")
            continue
        package_ids = alias.get("package_ids")
        source_id = alias.get("package_source_id")
        canonical_id = alias.get("canonical_source_id")
        if not isinstance(package_ids, list) or not package_ids or not isinstance(source_id, str) or not isinstance(canonical_id, str):
            errors.append("source alias needs package_ids, package_source_id, and canonical_source_id")
            continue
        canonical = canonical_sources.get(canonical_id)
        if canonical is None or alias.get("url") != canonical.get("url") or not valid_date(alias.get("checked_at")):
            errors.append(f"source alias {source_id} must name a current canonical source with the exact URL")
        for package_id in package_ids:
            key = (package_id, source_id)
            if package_id not in expected_package_ids:
                errors.append(f"source alias {source_id} references unknown package {package_id}")
            if key in alias_keys:
                errors.append(f"duplicate package-scoped source alias {package_id}:{source_id}")
            alias_keys.add(key)

    seen_task_ids: set[str] = set()
    observed_tier_totals = {tier: 0 for tier in TIER_ORDER}
    for relative_path in package_paths:
        path = ROOT / relative_path
        label = path.stem
        package = load_json(path)
        report["packages"] += 1
        expected = inventory_by_package.get(path.name)
        if expected is None:
            errors.append(f"{label}: missing manifest inventory row")
            continue
        if not isinstance(package.get("status"), str) or not package["status"]:
            errors.append(f"{label}: missing status")
        if not isinstance(package.get("scope"), str) or not package["scope"]:
            errors.append(f"{label}: missing scope")
        boundary = package.get("facts_strategy_boundary")
        if not isinstance(boundary, dict) or not isinstance(boundary.get("included"), list) or not isinstance(boundary.get("excluded"), list):
            errors.append(f"{label}: needs included and excluded facts/strategy boundary lists")
        if not valid_date(package.get("checked_at", package.get("researched_at"))):
            errors.append(f"{label}: needs a valid checked_at or researched_at date")
        normalization = next(
            (
                package[key]
                for key in (
                    "normalization_proposal",
                    "proposed_normalization",
                    "proposed_normalized_action_specs",
                    "proposed_graph",
                )
                if key in package
            ),
            None,
        )
        if not isinstance(normalization, (dict, list)):
            errors.append(f"{label}: needs a proposed normalization artifact")

        catalog = package.get("source_catalog")
        local_sources: dict[str, dict[str, Any]] = {}
        if not isinstance(catalog, list) or not catalog:
            errors.append(f"{label}: source_catalog must be a non-empty array")
        else:
            for source in catalog:
                if not isinstance(source, dict) or not isinstance(source.get("id"), str) or not isinstance(source.get("url"), str):
                    errors.append(f"{label}: source catalog entries need id and url")
                    continue
                source_id = source["id"]
                if source_id in local_sources:
                    errors.append(f"{label}: duplicate package source id {source_id}")
                    continue
                local_sources[source_id] = source
                if not valid_date(source.get("checked_at")):
                    errors.append(f"{label}:{source_id}: invalid checked_at")
                    continue
                resolution = source_resolution(sources_document, label, source_id)
                if resolution is None:
                    errors.append(f"{label}:{source_id}: no registry entry or explicit alias")
                    continue
                if "error" in resolution:
                    errors.append(f"{label}:{source_id}: {resolution['error']}")
                    continue
                registry_source = resolution["source"]
                alias = resolution["alias"]
                if registry_source.get("url") != source["url"]:
                    errors.append(f"{label}:{source_id}: registry URL must exactly equal package URL")
                if alias is not None:
                    if alias.get("url") != source["url"] or alias.get("checked_at") != source["checked_at"]:
                        errors.append(f"{label}:{source_id}: alias provenance must exactly match package URL and checked_at")
                elif not valid_date(registry_source.get("checked_at")) or registry_source["checked_at"] < source["checked_at"]:
                    errors.append(f"{label}:{source_id}: registry checked_at must be current for the package")

        tasks = package_tasks(package, label, errors)
        task_counts = {tier: 0 for tier in TIER_ORDER}
        for tier, task in tasks:
            task_id = task.get("id")
            if not isinstance(task_id, str) or not task_id.strip():
                errors.append(f"{label}:{tier}: task needs a non-empty id")
                continue
            if task_id in seen_task_ids:
                errors.append(f"duplicate source task id {task_id}")
            seen_task_ids.add(task_id)
            if not isinstance(task.get("task", task.get("name")), str) or not task.get("task", task.get("name")).strip():
                errors.append(f"{label}:{task_id}: task needs task text or a name")
            task_counts[tier] += 1
            observed_tier_totals[tier] += 1
            source_ids = task.get("source_ids")
            if label in per_task_packages:
                if not isinstance(source_ids, list) or not source_ids:
                    errors.append(f"{label}:{task_id}: per-task provenance requires source_ids")
                elif any(source_id not in local_sources for source_id in source_ids):
                    errors.append(f"{label}:{task_id}: task source_ids must be declared by its package catalog")
            elif source_ids is not None:
                if not isinstance(source_ids, list) or any(source_id not in local_sources for source_id in source_ids):
                    errors.append(f"{label}:{task_id}: optional task source_ids must be declared by its package catalog")

        expected_counts = expected.get("tasks", {})
        for tier in TIER_ORDER:
            if task_counts[tier] != expected_counts.get(tier):
                errors.append(f"{label}:{tier}: expected {expected_counts.get(tier)} tasks, got {task_counts[tier]}")
        if len(tasks) != expected_counts.get("total"):
            errors.append(f"{label}: expected {expected_counts.get('total')} tasks, got {len(tasks)}")
        claims = package_claim_tiers(package)
        if claims != set(TIER_ORDER):
            errors.append(f"{label}: tier reward/claim coverage must contain easy, medium, hard, and elite")
        if label in catalog_only_packages:
            report["catalog_inheritance_packages"].append(label)

    expected_totals = manifest.get("input_set", {}).get("tier_totals", {})
    if observed_tier_totals != expected_totals:
        errors.append(f"tier totals differ from manifest: expected {expected_totals}, got {observed_tier_totals}")
    report["tasks"] = sum(observed_tier_totals.values())
    return errors, report


def main() -> int:
    errors, report = validate()
    if errors:
        print("Diary package validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(
        "Diary package validation passed: "
        f"{report['packages']} packages, {report['tasks']} tasks, "
        f"catalog inheritance for {', '.join(report['catalog_inheritance_packages'])}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
