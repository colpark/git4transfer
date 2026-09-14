"""Known-input and must-fail controls for the reference-correction algebra."""

import math
import unittest

from reference_energy import AMINO_ACIDS, corrected_delta


class ReferenceEnergyTests(unittest.TestCase):
    def setUp(self):
        self.table = {aa: 0.0 for aa in AMINO_ACIDS}

    def test_known_delta_and_zero_control(self):
        self.table["A"] = 2.0
        self.table["R"] = 5.0
        result = corrected_delta(10.0, "A", "R", self.table, "synthetic algebra control")
        self.assertEqual(result["unfolded_reference_delta_kj_per_mol"], 3.0)
        self.assertEqual(result["corrected_delta_kj_per_mol"], 7.0)
        self.assertFalse(result["eligible_for_w2_scoring"])
        self.assertEqual(corrected_delta(0.0, "A", "A", self.table, "zero control")
                         ["corrected_delta_kj_per_mol"], 0.0)

    def test_missing_or_nonfinite_reference_must_fail(self):
        with self.assertRaises(ValueError):
            corrected_delta(1.0, "A", "R", {"A": 0.0}, "incomplete")
        self.table["R"] = math.nan
        with self.assertRaises(ValueError):
            corrected_delta(1.0, "A", "R", self.table, "nonfinite")
        with self.assertRaises(ValueError):
            corrected_delta(1.0, "A", "R", {aa: 0.0 for aa in AMINO_ACIDS}, "")


if __name__ == "__main__":
    unittest.main()
