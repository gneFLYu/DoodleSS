import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.cell_linear_algebra import (
    CellLinearAlgebraError,
    canonical_scalar,
    matrix_vector_product,
    nullspace,
    projective_normal_form,
    quotient_basis,
    rref,
    transition_data,
    validate_display_basis,
)


class F4CellLinearAlgebraTest(unittest.TestCase):
    def test_scalar_rref_and_kernel_are_exact(self):
        self.assertEqual(canonical_scalar("1+zeta"), "zeta^2")
        self.assertNotEqual(canonical_scalar("1+zeta"), "0")
        reduced, pivots = rref([["1", "zeta"], ["0", "1"]])
        self.assertEqual(reduced, [["1", "0"], ["0", "1"]])
        self.assertEqual(pivots, [0, 1])
        self.assertEqual(nullspace([["1", "1"]]), [["1", "1"]])
        self.assertEqual(matrix_vector_product([["1", "zeta"]], ["1", "zeta"]), ["zeta"])

    def test_projective_ports_identify_only_nonzero_scalar_multiples(self):
        self.assertEqual(projective_normal_form(["zeta", "zeta^2"]), ["1", "zeta"])
        self.assertEqual(projective_normal_form(["1", "zeta"]), ["1", "zeta"])
        self.assertNotEqual(projective_normal_form(["1", "1"]), projective_normal_form(["1", "zeta"]))
        with self.assertRaisesRegex(CellLinearAlgebraError, "zero vector"):
            projective_normal_form(["0", "0"])

    def test_display_basis_must_be_invertible(self):
        self.assertEqual(validate_display_basis([["1", "1"], ["0", "1"]], 2), [["1", "1"], ["0", "1"]])
        with self.assertRaisesRegex(CellLinearAlgebraError, "invertible"):
            validate_display_basis([["1", "1"], ["zeta", "zeta"]], 2)

    def test_hitting_a_plus_b_kills_a_line_not_two_basis_vectors(self):
        result = transition_data(2, [], [["1"], ["1"]])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["image_basis"], [["1", "1"]])
        self.assertEqual(result["quotient_rank"], 1)
        self.assertEqual(result["quotient_basis"], [["1", "0"]])
        self.assertEqual(quotient_basis([["1", "0"], ["0", "1"]], [["1", "1"]]), [["1", "0"]])

    def test_missing_maps_and_nonzero_d_squared_are_not_silently_resolved(self):
        self.assertEqual(transition_data(2, None, []) ["status"], "underdetermined")
        inconsistent = transition_data(2, [["1", "0"]], [["1"], ["0"]])
        self.assertEqual(inconsistent["status"], "inconsistent")
        self.assertIn("d_r^2", inconsistent["error"])


if __name__ == "__main__":
    unittest.main()
