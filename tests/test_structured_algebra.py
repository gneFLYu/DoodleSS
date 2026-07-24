from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as app_module
from app import app
from domain.structured_algebra import AlgebraValidationError, preview_structured_algebra


def integer_request(operation="canonicalize", **values):
    payload = {
        "operation": operation,
        "source_ref": "Research notebook, algebra test 1",
        "coefficient_context": {
            "id": "formal-integer-presentation",
            "domain": "integers",
            "source_ref": "Coefficient convention, integral presentation A",
        },
        "generators": [
            {
                "id": "x",
                "label": "x",
                "kind": "generator",
                "grade": {
                    "stem": 1,
                    "filtration": 2,
                    "representation": {"sigma_i": -1},
                },
                "source_ref": "Research notebook, generator x",
            },
            {
                "id": "y",
                "label": "y",
                "kind": "generator",
                "grade": {
                    "stem": 2,
                    "filtration": 4,
                    "representation": {"sigma_i": -2},
                },
                "source_ref": "Research notebook, generator y",
            },
            {
                "id": "u",
                "label": "u",
                "kind": "unit",
                "grade": {
                    "stem": 0,
                    "filtration": 0,
                    "representation": {"H": 1},
                },
                "source_ref": "Research notebook, unit u",
            },
        ],
    }
    payload.update(values)
    return payload


def f4_request(operation="add", **values):
    payload = {
        "operation": operation,
        "source_ref": "Research notebook, F4 test",
        "coefficient_context": {"id": "q8-residue-f4", "domain": "F4"},
        "generators": [
            {
                "id": "a",
                "label": "a",
                "kind": "generator",
                "grade": {"stem": 1, "filtration": 0, "representation": {}},
            }
        ],
    }
    payload.update(values)
    return payload


class StructuredAlgebraUnitTest(unittest.TestCase):
    def test_canonicalization_collects_terms_and_preserves_full_ro_grade(self):
        result = preview_structured_algebra(integer_request(
            polynomial={
                "terms": [
                    {"coefficient": 2, "powers": {"x": 2, "u": -1}},
                    {"coefficient": 3, "powers": {"u": -1, "x": 2}},
                    {"coefficient": -5, "powers": {"x": 2, "u": -1}},
                ]
            },
        ))
        self.assertEqual(result["result"]["terms"], [])
        self.assertTrue(result["result"]["homogeneous"])
        self.assertIsNone(result["result"]["grade"])
        self.assertFalse(result["persisted"])
        self.assertEqual(result["claims_created"], 0)

        nonzero = preview_structured_algebra(integer_request(
            polynomial={"terms": [{"coefficient": 5, "powers": {"x": 2, "u": -1}}]},
        ))
        self.assertEqual(nonzero["result"]["grade"], {
            "stem": 2,
            "filtration": 4,
            "representation": {"H": -1, "sigma_i": -2},
        })
        self.assertEqual(nonzero["provenance"]["generator_ids"], ["x", "u"])
        self.assertIn(
            "Coefficient convention, integral presentation A",
            nonzero["provenance"]["source_refs"],
        )

    def test_safe_sympy_expand_uses_only_internally_constructed_symbols(self):
        result = preview_structured_algebra(integer_request(
            operation="expand",
            factors=[
                {"terms": [
                    {"coefficient": 1, "powers": {"x": 1}},
                    {"coefficient": 1, "powers": {}},
                ]},
                {"terms": [
                    {"coefficient": 1, "powers": {"x": 1}},
                    {"coefficient": -1, "powers": {}},
                ]},
            ],
        ))
        self.assertEqual(result["engine"], "sympy-safe-structured")
        self.assertIn("version", result["sympy"])
        self.assertEqual(
            [(term["coefficient"], term["powers"]) for term in result["result"]["terms"]],
            [(1, {"x": 2}), (-1, {})],
        )
        self.assertFalse(result["validation"]["untrusted_text_parsing"])

        malicious = integer_request(
            polynomial="__import__('pathlib').Path('owned').write_text('x')",
        )
        with self.assertRaisesRegex(AlgebraValidationError, "must be an object"):
            preview_structured_algebra(malicious)

    def test_expand_rejects_a_conservatively_explosive_product(self):
        many_terms = {
            "terms": [
                {"coefficient": 1, "powers": {"x": exponent}}
                for exponent in range(317)
            ]
        }
        with self.assertRaisesRegex(AlgebraValidationError, "product safety limit"):
            preview_structured_algebra(integer_request(
                operation="expand",
                factors=[many_terms, many_terms],
            ))

    def test_f4_add_and_multiply_are_exact_and_do_not_mix_contexts(self):
        zeta = {"a": 0, "b": 1}
        zeta_squared = {"a": 1, "b": 1}
        added = preview_structured_algebra(f4_request(
            left={"terms": [{"coefficient": zeta, "powers": {"a": 1}}]},
            right={"terms": [{"coefficient": zeta_squared, "powers": {"a": 1}}]},
        ))
        self.assertEqual(added["result"]["terms"][0]["coefficient"], {"a": 1, "b": 0})
        self.assertEqual(added["engine"], "native-exact")
        self.assertNotIn("sympy", added)

        multiplied = preview_structured_algebra(f4_request(
            operation="multiply",
            left={"terms": [{"coefficient": zeta, "powers": {"a": 1}}]},
            right={"terms": [{"coefficient": zeta, "powers": {"a": 1}}]},
        ))
        self.assertEqual(multiplied["result"]["terms"][0]["coefficient"], zeta_squared)
        self.assertEqual(multiplied["result"]["terms"][0]["powers"], {"a": 2})

    def test_witt_context_is_rejected_instead_of_reducing_two_to_zero(self):
        payload = integer_request()
        payload["coefficient_context"] = {
            "id": "q8-witt-f4",
            "domain": "W(F4)/2-adic",
        }
        payload["generators"] = [{
            **payload["generators"][0],
            "coefficient_context_id": "q8-witt-f4",
        }]
        payload["polynomial"] = {"terms": [{"coefficient": 2, "powers": {"x": 1}}]}
        with self.assertRaisesRegex(AlgebraValidationError, "never infers 2 = 0"):
            preview_structured_algebra(payload)

    def test_negative_powers_require_an_explicit_unit(self):
        with self.assertRaisesRegex(AlgebraValidationError, "requires kind='unit'"):
            preview_structured_algebra(integer_request(
                polynomial={"terms": [{"coefficient": 1, "powers": {"x": -1}}]},
            ))

    def test_normal_form_is_homogeneous_terminating_and_provenance_aware(self):
        result = preview_structured_algebra(integer_request(
            operation="normal-form",
            polynomial={"terms": [{"coefficient": 3, "powers": {"x": 3}}]},
            relations=[{
                "id": "square-to-y",
                "lhs": {"coefficient": 1, "powers": {"x": 2}},
                "rhs": {"terms": [{"coefficient": 1, "powers": {"y": 1}}]},
                "source_ref": "Research notebook, relation square-to-y",
            }],
        ))
        self.assertEqual(result["result"]["terms"][0]["coefficient"], 3)
        self.assertEqual(result["result"]["terms"][0]["powers"], {"x": 1, "y": 1})
        self.assertEqual(result["result"]["terms"][0]["grade"], {
            "stem": 3,
            "filtration": 6,
            "representation": {"sigma_i": -3},
        })
        self.assertEqual(result["provenance"]["relation_ids"], ["square-to-y"])
        self.assertEqual(result["provenance"]["generator_ids"], ["x", "y"])
        self.assertIn("Research notebook, generator y", result["provenance"]["source_refs"])
        self.assertTrue(result["rewrite_validation"]["terminating"])
        self.assertTrue(result["rewrite_validation"]["confluent"])


class StructuredAlgebraApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.data_dir = TemporaryDirectory()
        self.old_data_path = app_module.DATA_PATH
        app_module.DATA_PATH = Path(self.data_dir.name) / "project.json"

    def tearDown(self):
        app_module.DATA_PATH = self.old_data_path
        self.data_dir.cleanup()

    def test_preview_endpoint_is_read_only_and_rejects_expression_strings(self):
        before = self.client.get("/api/project").get_json()
        payload = integer_request(
            operation="collect",
            polynomial={"terms": [
                {"coefficient": 2, "powers": {"x": 1}},
                {"coefficient": 3, "powers": {"x": 1}},
            ]},
        )
        response = self.client.post("/api/v2/algebra/preview", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["result"]["terms"][0]["coefficient"], 5)
        self.assertFalse(response.get_json()["persisted"])
        self.assertEqual(response.get_json()["claims_created"], 0)
        after = self.client.get("/api/project").get_json()
        self.assertEqual(after, before)

        payload["polynomial"] = "x + __import__('os').system('echo unsafe')"
        rejected = self.client.post("/api/v2/algebra/preview", json=payload)
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("must be an object", rejected.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
