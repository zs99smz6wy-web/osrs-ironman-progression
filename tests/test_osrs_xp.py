import unittest

from scripts.osrs_xp import MAX_XP, add_xp, level_from_xp, minimum_xp_for_level


class MinimumXpForLevelTests(unittest.TestCase):
    def test_canonical_thresholds(self):
        self.assertEqual(minimum_xp_for_level(1), 0)
        self.assertEqual(minimum_xp_for_level(2), 83)
        self.assertEqual(minimum_xp_for_level(10), 1_154)
        self.assertEqual(minimum_xp_for_level(99), 13_034_431)

    def test_rejects_invalid_levels(self):
        for level in (0, 100, 1.5, True):
            with self.subTest(level=level):
                with self.assertRaises((TypeError, ValueError)):
                    minimum_xp_for_level(level)


class LevelFromXpTests(unittest.TestCase):
    def test_threshold_boundaries(self):
        self.assertEqual(level_from_xp(0), 1)
        self.assertEqual(level_from_xp(82), 1)
        self.assertEqual(level_from_xp(83), 2)
        self.assertEqual(level_from_xp(1_153), 9)
        self.assertEqual(level_from_xp(1_154), 10)
        self.assertEqual(level_from_xp(13_034_430), 98)
        self.assertEqual(level_from_xp(13_034_431), 99)
        self.assertEqual(level_from_xp(MAX_XP), 99)

    def test_rejects_invalid_xp(self):
        for xp in (-1, MAX_XP + 1, 10.5, False):
            with self.subTest(xp=xp):
                with self.assertRaises((TypeError, ValueError)):
                    level_from_xp(xp)


class AddXpTests(unittest.TestCase):
    def test_adds_xp_and_caps_at_200m(self):
        self.assertEqual(add_xp(100, 50), 150)
        self.assertEqual(add_xp(MAX_XP - 1, 10), MAX_XP)

    def test_supports_an_explicit_lower_simulation_cap(self):
        self.assertEqual(add_xp(90, 20, cap=100), 100)

    def test_rejects_invalid_additions(self):
        for args in ((-1, 1), (1, -1), (MAX_XP + 1, 1)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    add_xp(*args)
        with self.assertRaises(ValueError):
            add_xp(100, 1, cap=99)


if __name__ == "__main__":
    unittest.main()
