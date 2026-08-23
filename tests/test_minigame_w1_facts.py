from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def records(path: str) -> dict[str, dict]:
    with (ROOT / path).open(encoding="utf-8") as handle:
        return {record["id"]: record for record in json.load(handle)["records"]}


class MinigameW1FactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gotr = records("data/facts/guardians-of-the-rift.json")
        cls.utility = records("data/facts/utility-skilling-minigames.json")
        cls.loops = records("data/facts/progression-loops.json")
        cls.stop_inputs = records("data/facts/utility-stop-inputs.json")
        cls.diaries = records("data/facts/achievement-diary-utility.json")

    def test_gotr_current_shop_paths_keep_rng_paths_and_permanent_eye(self) -> None:
        needle = self.gotr["abyssal-needle-and-colossal-pouch"]["acquisition"]["abyssal_needle"]
        lantern = self.gotr["abyssal-lantern"]["acquisition"]
        eye = self.gotr["guardians-eye-permanent-pet-metamorphosis"]

        self.assertEqual(750, needle["currency_method"]["abyssal_pearl_cost"])
        self.assertEqual("2026-08-19", needle["currency_method"]["introduced_live"])
        self.assertFalse(needle["rng_method"]["guaranteed"])
        self.assertEqual(1500, lantern["currency_method"]["abyssal_pearl_cost"])
        self.assertEqual("2026-08-19", lantern["currency_method"]["introduced_live"])
        self.assertFalse(lantern["rng_method"]["guaranteed"])
        self.assertIn("Permanent", eye["outputs"][0])
        self.assertIn("former banked-item behavior", eye["notes"])
        self.assertIn("official-summer-sweep-up-hunter-skilling", eye["source_ids"])

    def test_wintertodt_uses_observed_warmth_and_reward_cart_rolls(self) -> None:
        wintertodt = self.loops["wintertodt-current-warmth-and-reward-cart-boundary"]
        mechanics = wintertodt["mechanics"]

        self.assertIn("Warmth rather than Hitpoints", mechanics["survival_resource"])
        self.assertIn("observed stored roll", mechanics["reward_storage"])
        self.assertIn("not a carried Supply Crate", mechanics["persistent_boundary"])
        self.assertTrue(any("low-Hitpoints" in note for note in wintertodt["historical_stale_notes"]))
        self.assertTrue(any("Supply-Crate" in note for note in wintertodt["historical_stale_notes"]))
        self.assertEqual(
            ["wiki-wintertodt", "wiki-reward-cart", "official-wintertodt-updates-2024-mirror"],
            wintertodt["source_ids"],
        )

    def test_fishing_trawler_rejects_the_old_decaying_meter_model(self) -> None:
        trawler = self.loops["fishing-trawler-current-contribution-boundary"]
        meter = trawler["mechanics"]["contribution_meter"]

        self.assertEqual(0, meter["minimum"])
        self.assertEqual(255, meter["maximum"])
        self.assertFalse(meter["decays"])
        self.assertEqual(50, meter["reward_eligibility_threshold"])
        self.assertIn("never inferred", meter["boundary"])
        self.assertIn("variable", trawler["mechanics"]["inspection_boundary"])

    def test_tithe_cap_and_current_shop_preserve_container_rng_boundaries(self) -> None:
        tithe_access = self.utility["utility-tithe-farm-access-and-currency"]
        tithe_rewards = self.utility["utility-tithe-farm-durable-rewards"]["rewards"]
        tithe_stop = self.stop_inputs["utility-stop-tithe-farm"]

        self.assertEqual(16000, tithe_access["mechanics"]["point_cap"])
        self.assertIn("superseded", tithe_access["mechanics"]["historical_stale_point_cap"])
        self.assertIn("free through the current Tithe Farm shop", tithe_rewards["gricollers_can"]["effect"])
        self.assertIn("free", tithe_rewards["auto_weed"]["reactivation"])
        current_shop = tithe_rewards["current_consumables_and_containers"]
        self.assertEqual(30, current_shop["herb_box"]["cost"])
        self.assertIn("observed RNG", current_shop["herb_box"]["boundary"])
        self.assertEqual(30, current_shop["seed_pack"]["cost"])
        self.assertIn("observed RNG", current_shop["seed_pack"]["boundary"])
        self.assertEqual(16000, tithe_stop["deterministic_reward_costs"]["point_cap"])
        self.assertIn("former 1,000-point cap", tithe_stop["uncertainties"][1])

    def test_falador_hard_has_no_mlm_xp_modifier_and_elite_stays_variable(self) -> None:
        falador = self.diaries["diary-falador-hard-utility"]
        motherlode = self.utility["utility-motherlode-mine-access-and-nuggets"]
        distinction = motherlode["mechanics"]["falador_diary_distinction"]

        self.assertTrue(
            any(
                "does not grant a Motherlode Mine pay-dirt experience modifier" in effect
                for effect in falador["fixed_rewards"]["other_permanent_effects"]
            )
        )
        self.assertIn("Elite reward", falador["corrections"][0]["verified_live_mechanic"])
        self.assertIn("no Motherlode Mine pay-dirt experience modifier", distinction["hard"])
        self.assertIn("probabilities only", distinction["elite"])
        self.assertIn("does not guarantee", distinction["elite"])

    def test_lms_excludes_unimplemented_march_proposal(self) -> None:
        lms = self.stop_inputs["utility-stop-last-man-standing-current-shop-boundary"]
        costs = lms["deterministic_reward_costs"]

        self.assertEqual(5, costs["confirmed_current_imbue_rows"]["magic_shortbow_scroll"])
        self.assertEqual(5, costs["confirmed_current_imbue_rows"]["ring_of_wealth_scroll"])
        self.assertEqual(
            ["Emir's Arena reusable Scroll of imbuing", "Blighted surge sacks"],
            costs["excluded_unimplemented_proposals"],
        )
        self.assertIn("not current shop stock", lms["uncertainties"][0])
        self.assertIn("player-observed", lms["random_reward_behavior"]["match_and_shop_boundary"])
        self.assertEqual(
            ["wiki-last-man-standing-current", "official-sailing-lms-eligibility-may-2026"],
            lms["source_ids"],
        )


if __name__ == "__main__":
    unittest.main()
