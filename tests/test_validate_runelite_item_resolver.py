"""Focused checks for the production RuneLite item resolver contract."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_runelite_item_resolver import predicate_targets, validate_resolver  # noqa: E402


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RuneLiteResolverTests(unittest.TestCase):
    def setUp(self):
        self.resolver = read_json(ROOT / "data" / "import" / "runelite-item-resolver.v1.json")
        self.sources = {source["id"] for source in read_json(ROOT / "research" / "sources.json")["sources"]}
        self.targets = predicate_targets(read_json(ROOT / "data" / "progression" / "actions.json")["actions"])

    def test_production_resolver_is_valid_and_corrects_feathers_to_items(self):
        self.assertEqual([], validate_resolver(self.resolver, source_ids=self.sources, targets=self.targets))
        feathers = next(mapping for mapping in self.resolver["mappings"] if mapping["model_key"] == "feathers")
        self.assertEqual("items", feathers["model_state"])

    def test_rejects_duplicate_targets_ids_unknown_sources_and_bad_group_contracts(self):
        resolver = copy.deepcopy(self.resolver)
        resolver["mappings"].append(copy.deepcopy(resolver["mappings"][0]))
        resolver["mappings"][1]["runelite_item_ids"] = [resolver["mappings"][0]["runelite_item_ids"][0]]
        resolver["mappings"][1]["display_names"] = ["Duplicate"]
        resolver["mappings"][1]["source_ids"] = ["missing-source"]
        resolver["mappings"][1].pop("grouping_rationale", None)
        resolver["mappings"][1]["aggregation"] = "not-an-aggregation"
        errors = validate_resolver(resolver, source_ids=self.sources, targets=self.targets)
        joined = "\n".join(errors)
        self.assertIn("duplicate model key", joined)
        self.assertIn("unknown sources", joined)
        self.assertIn("invalid aggregation", joined)
        self.assertIn("already maps", joined)

    def test_rejects_max_without_variant_values_and_wrong_predicate_state(self):
        resolver = copy.deepcopy(self.resolver)
        resolver["mappings"].append({
            "model_state": "items", "model_key": "feather", "runelite_item_ids": [900001, 900002],
            "display_names": ["Can (1)", "Can (2)"], "aggregation": "max",
            "source_ids": ["runelite-itemid-current"], "checked_at": "2026-08-24",
            "notes": "Synthetic variant contract coverage.", "grouping_rationale": "Two positive-dose variants.",
            "item_id_values": {"900001": 1, "900002": 2},
        })
        resolver["mappings"][-1].pop("item_id_values")
        feathers = next(mapping for mapping in resolver["mappings"] if mapping["model_key"] == "feathers")
        feathers["model_state"] = "resources"
        errors = validate_resolver(resolver, source_ids=self.sources, targets=self.targets)
        joined = "\n".join(errors)
        self.assertIn("max aggregation needs one item_id_values", joined)
        self.assertIn("resources.feathers is not a current item/resource predicate", joined)


if __name__ == "__main__":
    unittest.main()
