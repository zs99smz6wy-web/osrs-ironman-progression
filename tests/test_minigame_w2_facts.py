from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FACTS_DIR = ROOT / "data" / "facts"
ACCESS_PATH = FACTS_DIR / "minigame-access-and-fixed-shops.json"
UTILITY_PATH = FACTS_DIR / "minigame-durable-utilities.json"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class MinigameW2FactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.access_document = load_json(ACCESS_PATH)
        self.utility_document = load_json(UTILITY_PATH)
        self.access = {record["id"]: record for record in self.access_document["records"]}
        self.utilities = {record["id"]: record for record in self.utility_document["records"]}

    def test_w2_records_have_unique_ids_and_registered_sources(self) -> None:
        records = self.access_document["records"] + self.utility_document["records"]
        record_ids = [record["id"] for record in records]
        source_ids = {source["id"] for source in load_json(ROOT / "research" / "sources.json")["sources"]}

        self.assertEqual(len(record_ids), len(set(record_ids)))
        self.assertEqual(7, len(self.access_document["records"]))
        self.assertEqual(5, len(self.utility_document["records"]))
        self.assertTrue(all(set(record["source_ids"]) <= source_ids for record in records))

    def test_selected_fixed_costs_and_gates_are_preserved(self) -> None:
        barbarian_assault = self.access["minigame-barbarian-assault-static-access-and-shop"]
        self.assertEqual(375, barbarian_assault["selected_fixed_shop_rows"]["fighter_torso"]["cost"]["each_role_honour"])
        self.assertTrue(barbarian_assault["selected_fixed_shop_rows"]["fighter_torso"]["requirements"]["confirmed_penance_queen_kill"])

        mahogany_homes = self.access["minigame-mahogany-homes-static-access-and-shop"]
        self.assertEqual(350, mahogany_homes["selected_fixed_shop_rows"]["plank_sack"]["carpenter_points"])
        self.assertEqual(500, mahogany_homes["selected_fixed_shop_rows"]["amys_saw"]["carpenter_points"])
        self.assertEqual(2000, mahogany_homes["selected_fixed_shop_rows"]["carpenters_outfit"]["total"])

        nightmare_zone = self.access["minigame-nightmare-zone-static-access-and-shop"]
        self.assertEqual(775, nightmare_zone["selected_fixed_shop_rows"]["scroll_of_redirection"]["nightmare_zone_points"])
        self.assertEqual(800000, nightmare_zone["selected_fixed_shop_rows"]["salve_amulet_imbue"]["normal_points"])
        self.assertEqual(400000, nightmare_zone["selected_fixed_shop_rows"]["salve_amulet_imbue"]["hard_combat_achievements_claimed_points"])

        pest_control = self.access["minigame-pest-control-static-access-and-shop"]
        self.assertEqual(850, pest_control["selected_fixed_shop_rows"]["regular_void_set"]["one_complete_set_total"])
        self.assertEqual(200, pest_control["selected_fixed_shop_rows"]["elite_void_top"]["commendation_points"])

        sepulchre = self.access["minigame-hallowed-sepulchre-static-access-and-shop"]
        self.assertEqual({"floor_1": 52, "floor_2": 62, "floor_3": 72, "floor_4": 82, "floor_5": 92}, sepulchre["access"]["unboostable_agility_floor_gates"])
        self.assertEqual(200, sepulchre["selected_fixed_shop_rows"]["private_instance_unlock"]["hallowed_marks"])

    def test_existing_mta_foundry_and_poh_models_are_referenced_not_duplicated(self) -> None:
        foundry = self.access["minigame-giants-foundry-canonical-boundary"]
        mta = self.access["minigame-mta-static-access-and-canonical-utilities"]
        mahogany_homes = self.access["minigame-mahogany-homes-static-access-and-shop"]

        self.assertIn("utility-stop-giants-foundry", foundry["canonical_fact_references"])
        self.assertIn("utility-stop-mage-training-arena", mta["canonical_fact_references"])
        self.assertIn("mta-rune-pouch", mta["canonical_fact_references"])
        self.assertIn("bones-to-peaches", mta["canonical_fact_references"])
        self.assertEqual(["poh-convenience-foundation"], mahogany_homes["canonical_fact_references"])
        self.assertIn("unresolved", foundry["blocked_conflict"])

    def test_w2_facts_do_not_declare_actions_graph_or_transitions(self) -> None:
        for record in self.access_document["records"] + self.utility_document["records"]:
            self.assertNotIn("actions", record)
            self.assertNotIn("graph", record)
            self.assertNotIn("transition", record)


if __name__ == "__main__":
    unittest.main()
