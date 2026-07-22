import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as app_module
from app import app
from domain.e2_presentation import (
    PresentationValidationError,
    materialize_explicit_presentation,
    normal_form_from_input,
    presentation_from_input,
)
from domain.models import Project, Workspace


def explicit_presentation(workspace_id="ws", **overrides):
    data = {
        "workspace_id": workspace_id,
        "name": "A checked toy presentation",
        "source_ref": "Research notebook, Example 1",
        "scope": "A deliberately finite user-supplied example.",
        "convention_id": "toy-e2-v1",
        "coefficient_context_id": "formal-integer-presentation",
        "coefficient_domain": "integers",
        "generators": [
            {
                "id": "x",
                "label": "x",
                "expression": "x",
                "grade": {"stem": 1, "filtration": 1, "representation": {"sigma_i": 1}},
            },
            {
                "id": "y",
                "label": "y",
                "expression": "y",
                "grade": {"stem": 2, "filtration": 2, "representation": {"sigma_i": 2}},
            },
        ],
        "relations": [
            {
                "id": "x-square",
                "lhs": {"coefficient": 1, "factors": {"x": 2}},
                "rhs": [{"coefficient": 1, "factors": {"y": 1}}],
                "source_ref": "Research notebook, Example 1 (relation)",
            }
        ],
    }
    data.update(overrides)
    return data


class ExplicitE2PresentationTest(unittest.TestCase):
    def test_exact_integer_normal_form_and_grade_validation(self):
        presentation = presentation_from_input(explicit_presentation())
        result = normal_form_from_input(presentation, {
            "terms": [{"coefficient": 3, "factors": {"x": 3}}],
        })
        self.assertEqual(result["normal_form"], [{"coefficient": 3, "factors": {"x": 1, "y": 1}}])
        self.assertTrue(result["validation"]["terminating"])
        self.assertTrue(result["validation"]["confluent"])
        self.assertFalse(result["validation"]["automatic_differentials"])

    def test_rejects_f4_witt_and_nonhomogeneous_inputs(self):
        with self.assertRaisesRegex(PresentationValidationError, "F4 and Witt"):
            presentation_from_input(explicit_presentation(coefficient_context_id="q8-witt-f4"))

        bad_relation = explicit_presentation(relations=[{
            "id": "bad-grade",
            "lhs": {"coefficient": 1, "factors": {"x": 2}},
            "rhs": [{"coefficient": 1, "factors": {"x": 1}}],
        }])
        with self.assertRaisesRegex(PresentationValidationError, "not homogeneous"):
            presentation_from_input(bad_relation)

    def test_materialization_keeps_only_explicit_generators_and_provenance(self):
        project = Project(id="project", name="Test", workspaces=[Workspace(id="ws", name="E2")])
        presentation = presentation_from_input(explicit_presentation())
        result = materialize_explicit_presentation(project, presentation)
        workspace = project.workspaces[0]

        self.assertEqual(len(workspace.classes), 2)
        self.assertEqual(len(workspace.differentials), 0)
        self.assertEqual(len(workspace.propositions), 3)
        self.assertEqual(len(project.e2_presentations), 1)
        self.assertEqual(len(project.coefficient_contexts), 1)
        x = next(item for item in workspace.classes if item.expression == "x")
        self.assertEqual(x.grade.representation, {"sigma_i": 1})
        self.assertEqual(x.convention_id, "toy-e2-v1")
        self.assertEqual(x.coefficient_context_id, "formal-integer-presentation")
        self.assertEqual(workspace.propositions[-1].source_ref, "Research notebook, Example 1 (relation)")
        self.assertEqual(result["created_classes"], [presentation.derived_class_ids["x"], presentation.derived_class_ids["y"]])


class ExplicitE2PresentationApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.data_dir = TemporaryDirectory()
        self.old_data_path = app_module.DATA_PATH
        app_module.DATA_PATH = Path(self.data_dir.name) / "project.json"

    def tearDown(self):
        app_module.DATA_PATH = self.old_data_path
        self.data_dir.cleanup()

    def test_preview_and_materialization_are_explicit_and_api_visible(self):
        workspace = self.client.get("/api/project").get_json()["workspaces"][0]
        payload = explicit_presentation(
            workspace["id"],
            polynomial={"terms": [{"coefficient": 1, "factors": {"x": 2}}]},
        )
        preview = self.client.post("/api/v2/e2-presentations/preview", json=payload)
        self.assertEqual(preview.status_code, 200)
        self.assertFalse(preview.get_json()["persisted"])
        self.assertEqual(preview.get_json()["evaluation"]["normal_form"], [{"coefficient": 1, "factors": {"y": 1}}])

        created = self.client.post("/api/v2/e2-presentations", json=payload)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(len(created.get_json()["materialization"]["created_classes"]), 2)
        self.assertIn("No monomial dots", created.get_json()["limitation"])
        listed = self.client.get("/api/v2/e2-presentations")
        self.assertEqual(len(listed.get_json()["presentations"]), 1)

    def test_api_rejects_f4_or_witt_context_instead_of_using_integer_arithmetic(self):
        workspace = self.client.get("/api/project").get_json()["workspaces"][0]
        rejected = self.client.post("/api/v2/e2-presentations/preview", json=explicit_presentation(
            workspace["id"], coefficient_context_id="q8-residue-f4",
        ))
        self.assertEqual(rejected.status_code, 400)
        self.assertIn("F4 and Witt coefficients", rejected.get_json()["error"])

    def test_api_requires_a_real_source_locator_before_preview_or_materialization(self):
        workspace = self.client.get("/api/project").get_json()["workspaces"][0]
        payload = explicit_presentation(workspace["id"], source_ref="")
        preview = self.client.post("/api/v2/e2-presentations/preview", json=payload)
        materialize = self.client.post("/api/v2/e2-presentations", json=payload)
        self.assertEqual(preview.status_code, 400)
        self.assertEqual(materialize.status_code, 400)
        self.assertIn("source_ref must be a nonempty string", preview.get_json()["error"])
