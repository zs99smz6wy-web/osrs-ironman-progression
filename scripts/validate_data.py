from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FACTS_DIR = ROOT / "data" / "facts"
RESEARCH_DIR = ROOT / "research"
GRAPH_DIR = ROOT / "graph"

REQUIRED_FACT_KEYS = {"id", "name", "category", "status", "verified_at", "source_ids"}
VALID_CATEGORIES = {"quest", "transport", "activity", "minigame", "reward", "sailing", "afk", "bypass", "economy"}
VALID_STATUSES = {"verified", "needs_revalidation", "research_queue"}
REQUIRED_ACCOUNT_STATE_KEYS = {
    "skills",
    "quests_completed",
    "transport_flags",
    "gear_thresholds",
    "resources",
    "passive_loops",
    "attention_window",
    "notable_drops",
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    errors: list[str] = []
    sources = {source["id"] for source in load_json(RESEARCH_DIR / "sources.json")["sources"]}
    node_ids = {node["id"] for node in load_json(GRAPH_DIR / "nodes.json")["nodes"]}
    account_state = load_json(GRAPH_DIR / "account-state.example.json")

    missing_state_keys = REQUIRED_ACCOUNT_STATE_KEYS - account_state.keys()
    if missing_state_keys:
        errors.append(f"account-state.example.json missing {sorted(missing_state_keys)}")
    attention = account_state.get("attention_window", {})
    if not isinstance(attention.get("duration_minutes"), int) or attention.get("duration_minutes", 0) < 1:
        errors.append("account-state.example.json has invalid attention duration")
    if attention.get("mode") not in {"true_afk", "low_attention", "semi_afk", "active"}:
        errors.append("account-state.example.json has invalid attention mode")

    for path in sorted(FACTS_DIR.glob("*.json")):
        for record in load_json(path).get("records", []):
            missing = REQUIRED_FACT_KEYS - record.keys()
            if missing:
                errors.append(f"{path.name}:{record.get('id', '<missing id>')} missing {sorted(missing)}")
                continue
            if record["category"] not in VALID_CATEGORIES:
                errors.append(f"{path.name}:{record['id']} has invalid category")
            if record["status"] not in VALID_STATUSES:
                errors.append(f"{path.name}:{record['id']} has invalid status")
            try:
                date.fromisoformat(record["verified_at"])
            except ValueError:
                errors.append(f"{path.name}:{record['id']} has invalid verified_at date")
            for source_id in record["source_ids"]:
                if source_id not in sources:
                    errors.append(f"{path.name}:{record['id']} references unknown source {source_id}")

    edge_signatures: set[tuple[str, str, str]] = set()
    for edge in load_json(GRAPH_DIR / "edges.json")["edges"]:
        if edge["from"] not in node_ids or edge["to"] not in node_ids:
            errors.append(f"graph edge has unknown endpoint: {edge}")
        signature = (edge["from"], edge["to"], edge["type"])
        if signature in edge_signatures:
            errors.append(f"duplicate graph edge: {signature}")
        edge_signatures.add(signature)

    if errors:
        print("Validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    print("Validation passed: factual records, sources, and graph endpoints are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
