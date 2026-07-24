"""Regression coverage for manual, non-theorem drawing periodicity.

The batch tests deliberately use two named rules with the same vector.  This
guards the important chart invariant that a cell may contain several distinct
algebraic dots: equal grades must not collapse different periodicity orbits.
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as app_module
from app import app
from domain.history import clear_history
from domain.manual_periodicity import (
    add_manual_rule,
    materialize_batch_preview,
    preview_all_rules_to_box,
    preview_differentials_only,
    preview_manual_periodicity,
)
from domain.migrations import ensure_foundations
from domain.models import ClassNode, Differential, Grade, Project, Proposition, Workspace, project_from_dict, project_to_dict
from domain.project_io import prepare_project_import
from domain.seed import demo_project


def drawing_project():
    source = ClassNode("source", "x", Grade(0, 0), page=2)
    target = ClassNode("target", "y", Grade(-1, 2), page=2)
    differential_proposition = Proposition(
        id="base-diff-prop", kind="differential", status="candidate",
        statement="Displayed base arrow", conclusion={"source_id": "source", "target_id": "target", "page": 2},
        source_ref="Local drawing input", source_refs=["Local drawing input"],
    )
    relation = Proposition(
        id="base-relation", kind="relation", status="candidate",
        statement="Displayed base relation", conclusion={"source_id": "source", "target_id": "target", "page": 2},
        source_ref="Local drawing input", source_refs=["Local drawing input"],
    )
    differential = Differential(
        "base-diff", "source", "target", 2, status="candidate", proposition_id="base-diff-prop",
    )
    workspace = Workspace(
        id="drawing", name="Drawing", spectral_sequence="hfpss",
        classes=[source, target], differentials=[differential],
        propositions=[differential_proposition, relation], page=2,
    )
    return Project(id="drawing-project", name="Drawing Project", workspaces=[workspace]), workspace


class ManualDrawingPeriodicityDomainTest(unittest.TestCase):
    def add_rule(self, project, workspace, name, p=1, q=0):
        return add_manual_rule(project, workspace, {
            "name": name, "p": p, "q": q,
            "basis": "An explicit local drawing convention, not a theorem.",
            "source_ref": "Research notebook entry",
        })

    def test_box_keeps_same_cell_orbits_distinct_and_round_trips(self):
        project, workspace = drawing_project()
        self.add_rule(project, workspace, "P")
        self.add_rule(project, workspace, "Q")

        preview = preview_all_rules_to_box(project, workspace, {
            "page": 2, "p_min": 1, "p_max": 1, "q_min": 0, "q_max": 0,
            "basis": "Manual beta chart construction.", "source_ref": "Notebook p. 1",
        })
        same_cell = [item for item in preview["cycle_copies"] if item["grade"]["stem"] == 1 and item["grade"]["filtration"] == 0]
        self.assertGreater(len(same_cell), 1)
        self.assertTrue(all(item["action"] == "create" for item in same_cell))
        self.assertEqual(len({tuple(item["exponents"]) for item in same_cell}), len(same_cell))
        self.assertEqual(preview["summary"]["conflicts"], 0)

        result = materialize_batch_preview(project, workspace, preview)
        self.assertTrue(result["changed"])
        materialized_same_cell = [
            item for item in workspace.classes
            if item.grade.stem == 1 and item.grade.filtration == 0 and item.manual_periodicity_id == preview["manual_periodicity_id"]
        ]
        self.assertEqual(len(materialized_same_cell), len(same_cell))
        self.assertEqual(len({tuple(item.manual_periodicity_exponents) for item in materialized_same_cell}), len(same_cell))
        self.assertGreaterEqual(len(result["created_differential_ids"]), 1)
        self.assertGreaterEqual(len(result["created_relation_proposition_ids"]), 1)

        repeated = preview_all_rules_to_box(project, workspace, {
            "page": 2, "p_min": 1, "p_max": 1, "q_min": 0, "q_max": 0,
            "basis": "Manual beta chart construction.", "source_ref": "Notebook p. 1",
        })
        self.assertEqual(repeated["summary"]["cycles_to_create"], 0)
        self.assertEqual(repeated["summary"]["differentials_to_create"], 0)
        self.assertEqual(repeated["summary"]["relations_to_create"], 0)
        self.assertEqual(repeated["summary"]["conflicts"], 0)

        raw = project_to_dict(project)
        parsed = project_from_dict(raw)
        self.assertEqual(len(parsed.manual_periodicity_rules), 2)
        self.assertEqual(len(parsed.manual_periodicities), 1)
        self.assertEqual(raw["manual_periodicities"][0]["mode"], "box")
        self.assertEqual(len(raw["manual_periodicities"][0]["rule_ids"]), 2)

    def test_unit_coefficient_and_latex_spacing_are_omitted(self):
        project, workspace = drawing_project()
        source = next(item for item in workspace.classes if item.id == "source")
        source.label = "1"
        source.expression = "1"

        single = preview_manual_periodicity(workspace, {
            "anchor_class_id": source.id,
            "page": 2,
            "period_stem": 8,
            "period_filtration": 0,
            "translation_start": 1,
            "translation_end": 1,
            "cycle_label": "D",
            "include_cycles": True,
        })
        copy = single["cycle_copies"][0]
        self.assertEqual(copy["label"], "D")
        self.assertEqual(copy["expression"], "D")
        self.assertNotIn(r"\,", copy["label"])

        self.add_rule(project, workspace, "D", p=1, q=0)
        self.add_rule(project, workspace, "k", p=0, q=1)
        combined = preview_all_rules_to_box(project, workspace, {
            "page": 2, "p_min": 1, "p_max": 1, "q_min": 1, "q_max": 1,
            "basis": "Manual product-label formatting test.",
            "source_ref": "Research notebook entry",
        })
        combined_copy = next(
            item for item in combined["cycle_copies"]
            if item["base_class_id"] == source.id
        )
        self.assertEqual(combined_copy["label"], "Dk")
        self.assertEqual(combined_copy["expression"], "Dk")
        self.assertNotIn(r"\,", combined_copy["label"])

    def test_legacy_manual_product_labels_migrate_idempotently(self):
        project, workspace = drawing_project()
        workspace.classes.append(ClassNode(
            "legacy-product", r"1\,D\,k", Grade(20, 4),
            expression=r"(1)*(D\,k)",
            manual_periodicity_id="legacy-manual-period",
        ))

        ensure_foundations(project)
        migrated = next(item for item in workspace.classes if item.id == "legacy-product")
        self.assertEqual(migrated.label, "Dk")
        self.assertEqual(migrated.expression, "Dk")

        ensure_foundations(project)
        self.assertEqual(migrated.label, "Dk")
        self.assertEqual(migrated.expression, "Dk")

    def test_founded_demo_import_stays_strict_while_manual_rules_round_trip(self):
        project = demo_project()
        workspace = next(item for item in project.workspaces if item.id == "ws_integer")
        self.add_rule(project, workspace, "manual-test-period")
        imported, metadata = prepare_project_import(project_to_dict(project))
        self.assertEqual(metadata["summary"]["manual_periodicity_rules"], 1)
        self.assertEqual(
            len([item for item in imported.manual_periodicity_rules if item.workspace_id == "ws_integer"]), 1,
        )

    def test_legacy_rule_vectors_migrate_once_into_canonical_rules(self):
        project, _ = drawing_project()
        raw = project_to_dict(project)
        raw["manual_periodicities"] = [{
            "id": "legacy-batch", "workspace_id": "drawing", "page": 2,
            "operation_kind": "all-rules-box",
            "rule_vectors": [{"id": "legacy-P", "name": "P", "p": 1, "q": 0}],
            "bounds": {"p_min": 1, "p_max": 1, "q_min": 0, "q_max": 0},
            "basis": "Old local manual record.",
            "source_ref": "Legacy local drawing operation",
        }]
        restored = project_from_dict(raw)
        record = restored.manual_periodicities[0]
        self.assertEqual(record.mode, "box")
        self.assertEqual(record.rule_ids, ["legacy-P"])
        self.assertEqual([item.id for item in restored.manual_periodicity_rules], ["legacy-P"])
        self.assertNotIn("manual_periodicity_rules", restored.workspaces[0].settings)

    def test_differentials_only_creates_exactly_the_missing_endpoint(self):
        project, workspace = drawing_project()
        workspace.classes.append(ClassNode("shifted-source", "x'", Grade(1, 0), page=2))

        preview = preview_differentials_only(project, workspace, {
            "page": 2, "p": 1, "q": 0,
            "basis": "Manual arrow copy requested by the user.", "source_ref": "Notebook p. 2",
        })
        candidate = next(item for item in preview["connection_copies"] if item.get("translation") == 1)
        self.assertEqual(candidate["endpoint_case"], "create-missing-target")
        self.assertEqual(candidate["action"], "create")
        self.assertEqual(preview["summary"]["cycles_to_create"], 1)
        self.assertEqual(preview["summary"]["existing_endpoints"], 1)
        self.assertGreater(preview["summary"]["skipped"], 0)

        result = materialize_batch_preview(project, workspace, preview)
        self.assertEqual(len(result["created_class_ids"]), 1)
        self.assertEqual(len(result["created_differential_ids"]), 1)


class ManualDrawingPeriodicityApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.data_dir = TemporaryDirectory()
        self.old_data_path = app_module.DATA_PATH
        app_module.DATA_PATH = Path(self.data_dir.name) / "project.json"
        clear_history(app_module.history_key())

    def tearDown(self):
        clear_history(app_module.history_key())
        app_module.DATA_PATH = self.old_data_path
        self.data_dir.cleanup()

    def test_invalid_and_noop_rule_requests_do_not_create_history_entries(self):
        workspace_id = "ws_integer"
        invalid = self.client.post(f"/api/v2/workspaces/{workspace_id}/drawing-periodicity/rules", json={
            "name": "bad", "p": 0, "q": 0, "basis": "Test",
        })
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(self.client.get("/api/history").get_json()["undo_depth"], 0)

        created = self.client.post(f"/api/v2/workspaces/{workspace_id}/drawing-periodicity/rules", json={
            "name": "P", "p": 1, "q": 0, "basis": "A manual test rule.",
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        rule_id = created.get_json()["rule"]["id"]
        self.assertEqual(self.client.get("/api/history").get_json()["undo_depth"], 1)

        duplicate = self.client.post(f"/api/v2/workspaces/{workspace_id}/drawing-periodicity/rules", json={
            "name": "P", "p": 1, "q": 0, "basis": "A manual test rule.",
        })
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(self.client.get("/api/history").get_json()["undo_depth"], 1)

        removed = self.client.delete(f"/api/v2/workspaces/{workspace_id}/drawing-periodicity/rules/{rule_id}")
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(self.client.get("/api/history").get_json()["undo_depth"], 2)
        repeated = self.client.delete(f"/api/v2/workspaces/{workspace_id}/drawing-periodicity/rules/{rule_id}")
        self.assertEqual(repeated.status_code, 200)
        self.assertFalse(repeated.get_json()["changed"])
        self.assertEqual(self.client.get("/api/history").get_json()["undo_depth"], 2)

    def test_explicit_zero_filtration_is_created_and_boolean_is_rejected(self):
        created = self.client.post("/api/workspaces/ws_integer/classes", json={
            "label": "zero-filtration", "stem": 7, "filtration": 0, "page": 2,
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        self.assertEqual(created.get_json()["class"]["grade"]["filtration"], 0)
        invalid = self.client.post("/api/workspaces/ws_integer/classes", json={
            "label": "bad-filtration", "stem": 7, "filtration": False, "page": 2,
        })
        self.assertEqual(invalid.status_code, 400)
        fractional = self.client.post("/api/workspaces/ws_integer/classes", json={
            "label": "fractional-filtration", "stem": 7, "filtration": 0.5, "page": 2,
        })
        self.assertEqual(fractional.status_code, 400)

    def test_exported_materialized_batch_is_accepted_by_full_import_preview(self):
        rule = self.client.post("/api/v2/workspaces/ws_integer/drawing-periodicity/rules", json={
            "name": "P", "p": 1, "q": 0, "basis": "Manual beta test vector.",
            "source_ref": "Notebook p. 3",
        })
        self.assertEqual(rule.status_code, 201, rule.get_json())
        applied = self.client.post("/api/v2/workspaces/ws_integer/drawing-periodicity/box/apply", json={
            "page": 2, "p_min": 9, "p_max": 9, "q_min": 0, "q_max": 0,
            "basis": "Materialize an explicitly requested manual drawing copy.",
            "source_ref": "Notebook p. 3",
        })
        self.assertEqual(applied.status_code, 201, applied.get_json())
        self.assertTrue(applied.get_json()["created_class_ids"])

        exported = self.client.get("/api/project/export")
        self.assertEqual(exported.status_code, 200)
        preview = self.client.post("/api/project/import/preview", json=exported.get_json())
        self.assertEqual(preview.status_code, 200, preview.get_json())
        payload = preview.get_json()
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["import"]["summary"]["manual_periodicity_rules"], 1)
        self.assertEqual(payload["import"]["summary"]["manual_periodicities"], 1)
        manual = payload["project"]["manual_periodicities"][0]
        self.assertTrue(manual["created_class_ids"])
        workspace = next(item for item in payload["project"]["workspaces"] if item["id"] == "ws_integer")
        generated = next(item for item in workspace["classes"] if item["id"] == manual["created_class_ids"][0])
        self.assertEqual(generated["manual_periodicity_id"], manual["id"])


if __name__ == "__main__":
    unittest.main()
