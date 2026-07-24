from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.algebra_labels import (
    AlgebraLabelError,
    multiply_algebra_labels,
    multiply_label_by_period,
    parse_algebra_label,
    prepare_class_label_edit,
)
from domain.models import ClassNode, Grade


class AlgebraLabelTest(unittest.TestCase):
    def test_label_is_the_expression_and_registers_basic_generators(self):
        parsed = parse_algebra_label(r"1\,v_1 h_1D^3")

        self.assertEqual(parsed.label, r"v_1h_1D^{3}")
        self.assertEqual(
            [item.label for item in parsed.registered_generators],
            ["v_1", "h_1", "D"],
        )
        self.assertNotIn(r"\,", parsed.label)
        self.assertEqual(parse_algebra_label("1").registered_generators, ())

    def test_multiply_collects_powers_without_evaluation(self):
        product = multiply_algebra_labels("2xD^2", "3Dk")
        translated = multiply_label_by_period("x", "kD^3", 2)

        self.assertEqual(product.label, r"6xD^{3}k")
        self.assertEqual(translated.label, r"xk^{2}D^{6}")

    def test_rejects_non_monomials_calls_and_bad_separators(self):
        for label in ("x+y", "x=y", "f(x)", "__import__", "*x", "x*"):
            with self.subTest(label=label):
                with self.assertRaises(AlgebraLabelError):
                    parse_algebra_label(label)

    def test_negative_power_requires_explicit_unit(self):
        with self.assertRaises(AlgebraLabelError):
            parse_algebra_label("D^{-1}")
        parsed = parse_algebra_label("D^{-1}", unit_labels=["D"])
        self.assertEqual(parsed.label, "D^{-1}")
        self.assertEqual(parsed.registered_generators[0].kind, "unit")

    def test_page_specific_label_edit_does_not_reset_to_e2(self):
        node = ClassNode("x", "old", Grade(1, 2), page=2, expression="different")
        edited = prepare_class_label_edit(node, r"u_{\sigma_i}h_1", target_page=7)

        self.assertEqual(edited.page, 7)
        self.assertEqual(edited.label, edited.expression)
        self.assertEqual(edited.label, r"u_{\sigma_i}h_1")
        self.assertEqual(node.page, 2)


if __name__ == "__main__":
    unittest.main()
