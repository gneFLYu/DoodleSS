import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as app_module
from app import app
from domain.models import ClassNode, Differential, Grade, PeriodicityRule, Project, Proposition, Workspace
from domain.periodicity import (
    D8_RULE_ID,
    PeriodicityOperationError,
    materialize_periodic_translate,
    preview_periodic_translate,
)


def rule():
    return PeriodicityRule(
        id=D8_RULE_ID,
        name="D8",
        workspace_id="ws_integer",
        multiplier_expression="D^8",
        grade_shift=Grade(64, 0),
        valid_from_page=3,
        valid_to_page="infinity",
        spectral_sequence="hfpss",
        horizontal_only=True,
        certificate_proposition_id="d8-certificate",
        period_family_id="period_integer_D8",
        status="established",
        source_ref="DKLLW24, Proposition 4.1 (local PDF p. 25); section 6.1.2 (local PDF p. 51)",
    )


def periodic_project(with_differential=False):
    source = ClassNode("source", "x", Grade(5, 0))
    target = ClassNode("target", "y", Grade(4, 3))
    workspace = Workspace(
        id="ws_integer", name="Integer", spectral_sequence="hfpss", classes=[source, target],
        propositions=[
            Proposition(
                id="d8-certificate", kind="permanent-cycle", status="established",
                statement="D8 is invertible", conclusion={"class_id": "D8"},
                source_ref="DKLLW24, Proposition 4.1", source_refs=["DKLLW24, Proposition 4.1"],
            ),
        ],
    )
    if with_differential:
        workspace.propositions.append(Proposition(
            id="source-diff-prop", kind="differential", status="established", statement="d3(x)=y",
            conclusion={"source_id": "source", "target_id": "target", "page": 3},
            source_ref="A cited differential", source_refs=["A cited differential"],
        ))
        workspace.differentials.append(Differential(
            "source-diff", "source", "target", 3, status="established", proposition_id="source-diff-prop",
        ))
    return Project(id="project", name="Project", workspaces=[workspace], periodicity_rules=[rule()]), workspace


class D8PeriodicityDomainTest(unittest.TestCase):
    def test_preview_is_nonmutating_horizontal_and_never_e2(self):
        project, workspace = periodic_project()
        payload = {"rule_id": D8_RULE_ID, "anchor_class_id": "source", "page": 3, "translation": 1}
        preview = preview_periodic_translate(project, workspace, payload)

        self.assertFalse(preview["persisted"])
        self.assertEqual(preview["rule"]["valid_from_page"], 3)
        self.assertEqual(preview["class_copies"][0]["grade"], {"stem": 69, "filtration": 0, "representation": {}})
        self.assertEqual(len(workspace.classes), 2)
        self.assertEqual(len(workspace.propositions), 1)
        with self.assertRaisesRegex(PeriodicityOperationError, "E_3"):
            preview_periodic_translate(project, workspace, {**payload, "page": 2})

    def test_materializes_distinct_records_idempotently_and_keeps_provenance(self):
        project, workspace = periodic_project(with_differential=True)
        payload = {
            "rule_id": D8_RULE_ID, "anchor_class_id": "source", "page": 3,
            "translation": 1, "differential_id": "source-diff",
        }
        result = materialize_periodic_translate(project, workspace, payload)

        self.assertEqual(len(result["created_class_ids"]), 2)
        self.assertIsNotNone(result["created_differential_id"])
        translated_source = next(item for item in workspace.classes if item.id == result["created_class_ids"][0])
        translated_target = next(item for item in workspace.classes if item.id == result["created_class_ids"][1])
        self.assertEqual((translated_source.grade.stem, translated_source.grade.filtration), (69, 0))
        self.assertEqual((translated_target.grade.stem, translated_target.grade.filtration), (68, 3))
        self.assertEqual(translated_source.period_stem, 0)
        self.assertEqual(translated_source.periodicity_rule_id, D8_RULE_ID)
        self.assertEqual(translated_source.periodicity_anchor_class_id, "source")
        translated_differential = next(item for item in workspace.differentials if item.id == result["created_differential_id"])
        self.assertEqual((translated_differential.source_id, translated_differential.target_id, translated_differential.page), (translated_source.id, translated_target.id, 3))
        self.assertEqual(translated_differential.periodicity_rule_id, D8_RULE_ID)
        translated_claim = next(item for item in workspace.propositions if item.id == translated_differential.proposition_id)
        self.assertIn("DKLLW24, Proposition 4.1", translated_claim.source_refs)
        self.assertIn("A cited differential", translated_claim.source_refs)

        repeated = materialize_periodic_translate(project, workspace, payload)
        self.assertEqual(repeated["created_class_ids"], [])
        self.assertEqual(repeated["created_differential_id"], None)
        self.assertEqual(repeated["reused_differential_id"], translated_differential.id)
        self.assertEqual(len(workspace.classes), 4)
        self.assertEqual(len(workspace.differentials), 2)

    def test_rejects_conflicting_cell_and_under_review_arrow(self):
        project, workspace = periodic_project(with_differential=True)
        workspace.classes.append(ClassNode("manual", "manual", Grade(69, 0)))
        payload = {"rule_id": D8_RULE_ID, "anchor_class_id": "source", "page": 3, "translation": 1}
        with self.assertRaisesRegex(PeriodicityOperationError, "already occupies"):
            preview_periodic_translate(project, workspace, payload)

        workspace.classes.pop()
        workspace.differentials[0].status = "under-review"
        with self.assertRaisesRegex(PeriodicityOperationError, "accepted source differential"):
            preview_periodic_translate(project, workspace, {**payload, "differential_id": "source-diff"})


class D8PeriodicityApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.data_dir = TemporaryDirectory()
        self.old_data_path = app_module.DATA_PATH
        app_module.DATA_PATH = Path(self.data_dir.name) / "project.json"

    def tearDown(self):
        app_module.DATA_PATH = self.old_data_path
        self.data_dir.cleanup()

    def test_api_lists_rule_previews_then_materializes_without_e2_or_duplicate_records(self):
        rules = self.client.get("/api/v2/periodicity-rules")
        self.assertEqual(rules.status_code, 200)
        d8 = next(item for item in rules.get_json()["periodicity_rules"] if item["id"] == D8_RULE_ID)
        self.assertEqual((d8["grade_shift"]["stem"], d8["grade_shift"]["filtration"], d8["valid_from_page"]), (64, 0, 3))
        self.assertIn("section 6.1.2", d8["source_ref"])

        payload = {"rule_id": D8_RULE_ID, "anchor_class_id": "int_D", "page": 5, "translation": 1}
        preview = self.client.post("/api/v2/workspaces/ws_integer/periodicity/preview", json=payload)
        self.assertEqual(preview.status_code, 200)
        self.assertFalse(preview.get_json()["persisted"])
        rejected_e2 = self.client.post("/api/v2/workspaces/ws_integer/periodicity/preview", json={**payload, "page": 2})
        self.assertEqual(rejected_e2.status_code, 400)

        created = self.client.post("/api/v2/workspaces/ws_integer/periodicity/materialize", json=payload)
        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.get_json()["persisted"])
        self.assertEqual(len(created.get_json()["created_class_ids"]), 1)
        again = self.client.post("/api/v2/workspaces/ws_integer/periodicity/materialize", json=payload)
        self.assertEqual(again.status_code, 201)
        self.assertEqual(again.get_json()["created_class_ids"], [])
