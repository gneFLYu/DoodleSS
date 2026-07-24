from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.dkllw_chart import (
    ChartSemanticError,
    annotate_class_glyph,
    annotate_connection,
    class_semantic_from_glyph,
)
from domain.models import ClassNode, Grade


class DKLLWChartSemanticTest(unittest.TestCase):
    def test_class_shape_not_fate_or_generic_color_controls_algebra_type(self):
        killed = ClassNode(
            "x",
            "x",
            Grade(0, 0),
            state="killed",
            style={"color": "gray"},
        )

        self.assertEqual(class_semantic_from_glyph("dot").algebra_type, "k")
        self.assertEqual(
            class_semantic_from_glyph("fat dot").algebra_type,
            r"k[\![j]\!]",
        )
        self.assertEqual(
            class_semantic_from_glyph("circle").algebra_type,
            r"k[\![j]\!]\{j\}",
        )
        self.assertEqual(
            class_semantic_from_glyph("square").algebra_type,
            r"\mathbb W(k)",
        )
        annotation = annotate_class_glyph(killed, "circle")
        self.assertEqual(annotation["inference_inputs"], ["explicit-glyph"])
        self.assertIn("class.state", annotation["ignored_inputs"])

    def test_vertical_is_two_extension_in_same_bidegree(self):
        semantic = annotate_connection(
            kind="vertical-two",
            source_grade=Grade(12, 0),
            target_grade=Grade(12, 0),
            spectral_sequence="hfpss",
            claim_source_ref="Notebook: identified 2-extension",
        )

        self.assertEqual(semantic.multiplier, "2")
        self.assertEqual(semantic.target_shift, Grade())
        with self.assertRaises(ChartSemanticError):
            annotate_connection(
                kind="vertical-two",
                source_grade=Grade(12, 0),
                target_grade=Grade(12, 1),
                spectral_sequence="hfpss",
                claim_source_ref="Notebook",
            )

    def test_h1_and_h2_use_exact_slopes(self):
        h1 = annotate_connection(
            kind="h1",
            source_grade=Grade(2, 1),
            target_grade=Grade(3, 2),
            spectral_sequence="hfpss",
            claim_source_ref="Notebook",
        )
        h2 = annotate_connection(
            kind="h2",
            source_grade=Grade(2, 1),
            target_grade=Grade(5, 2),
            spectral_sequence="hfpss",
            claim_source_ref="Notebook",
        )

        self.assertEqual(h1.multiplier, "h_1")
        self.assertEqual(h2.multiplier, "h_2")
        self.assertEqual(h2.target_shift, Grade(3, 1))

    def test_dashed_hidden_extension_is_2bss_only_and_stays_candidate(self):
        semantic = annotate_connection(
            kind="hidden-extension",
            source_grade=Grade(0, 0),
            target_grade=Grade(0, 0),
            spectral_sequence="2BSS",
            claim_source_ref="Notebook hidden-extension claim",
        )

        self.assertTrue(semantic.hidden_extension)
        self.assertEqual(semantic.status, "candidate")
        with self.assertRaises(ChartSemanticError):
            annotate_connection(
                kind="hidden-extension",
                source_grade=Grade(),
                target_grade=Grade(),
                spectral_sequence="hfpss",
                claim_source_ref="Notebook",
            )
        with self.assertRaises(ChartSemanticError):
            annotate_connection(
                kind="h1",
                source_grade=Grade(),
                target_grade=Grade(1, 1),
                spectral_sequence="hfpss",
                claim_source_ref="",
            )


if __name__ == "__main__":
    unittest.main()
