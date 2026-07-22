"""Regression coverage for reviewed, atomic full-project JSON replacement."""

from copy import deepcopy
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as app_module
from app import app
from domain.history import clear_history


class ProjectJsonIoApiTest(unittest.TestCase):
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

    def exported_project(self):
        response = self.client.get("/api/project/export")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        self.assertIn("attachment; filename=", response.headers["Content-Disposition"])
        return response.get_json()

    def preview(self, project):
        response = self.client.post("/api/project/import/preview", json=project)
        self.assertEqual(response.status_code, 200, response.get_json())
        return response.get_json()

    def test_export_is_a_complete_studio_project_download(self):
        project = self.exported_project()
        self.assertTrue(project["id"])
        self.assertTrue(project["name"])
        self.assertGreaterEqual(project["schema_version"], 1)
        self.assertGreaterEqual(len(project["workspaces"]), 1)
        self.assertIn("comparisons", project)
        self.assertIn("periodicity_rules", project)

    def test_preview_is_read_only_and_apply_is_revision_guarded_and_undoable(self):
        before = self.exported_project()
        proposed = deepcopy(before)
        proposed["name"] = "Reviewed imported replacement"

        preview = self.preview(proposed)
        self.assertTrue(preview["valid"])
        self.assertEqual(preview["project"]["name"], "Reviewed imported replacement")
        self.assertIn("neither proves nor independently verifies", preview["mathematical_status_policy"])
        self.assertEqual(self.client.get("/api/project").get_json()["name"], before["name"])
        self.assertEqual(self.client.get("/api/history").get_json()["undo_depth"], 0)

        applied = self.client.post("/api/project/import/apply", json={
            "project": proposed,
            "preview_sha256": preview["preview_sha256"],
            "expected_revision": preview["current_revision"],
        })
        self.assertEqual(applied.status_code, 201, applied.get_json())
        self.assertEqual(applied.get_json()["project"]["name"], "Reviewed imported replacement")
        self.assertEqual(applied.get_json()["revision"], before["revision"] + 1)
        self.assertEqual(applied.get_json()["undo_depth"], 1)
        self.assertIn("import and replace", applied.get_json()["undo_label"].lower())

        undone = self.client.post("/api/history/undo")
        self.assertEqual(undone.status_code, 200)
        self.assertEqual(self.client.get("/api/project").get_json()["name"], before["name"])
        redone = self.client.post("/api/history/redo")
        self.assertEqual(redone.status_code, 200)
        self.assertEqual(self.client.get("/api/project").get_json()["name"], "Reviewed imported replacement")

    def test_rejects_legacy_canvas_uncited_claim_and_broken_reference(self):
        legacy = self.client.post("/api/project/import/preview", json={
            "generators": [], "connections": [], "periodicityRules": [],
        })
        self.assertEqual(legacy.status_code, 422)
        self.assertIn("sseq ver15.3", legacy.get_json()["error"])

        uncited = self.exported_project()
        proposition = next(
            item for workspace in uncited["workspaces"] for item in workspace["propositions"]
            if item["status"] in {"derived", "reviewed", "established", "proven"}
        )
        proposition["source_ref"] = ""
        proposition["source_refs"] = []
        uncited_response = self.client.post("/api/project/import/preview", json=uncited)
        self.assertEqual(uncited_response.status_code, 422)
        self.assertIn("source locator", uncited_response.get_json()["error"])

        broken = self.exported_project()
        workspace = next(item for item in broken["workspaces"] if item["differentials"])
        differential = workspace["differentials"][0]
        differential["target_id"] = "missing-target"
        matching_proposition = next(
            item for item in workspace["propositions"]
            if item["id"] == differential["proposition_id"]
        )
        matching_proposition["conclusion"]["target_id"] = "missing-target"
        broken_response = self.client.post("/api/project/import/preview", json=broken)
        self.assertEqual(broken_response.status_code, 422)
        self.assertIn("endpoint absent", broken_response.get_json()["error"])

    def test_apply_rejects_an_unreviewed_payload_or_stale_revision(self):
        project = self.exported_project()
        preview = self.preview(project)

        altered = deepcopy(project)
        altered["name"] = "Changed after preview"
        wrong_digest = self.client.post("/api/project/import/apply", json={
            "project": altered,
            "preview_sha256": preview["preview_sha256"],
            "expected_revision": preview["current_revision"],
        })
        self.assertEqual(wrong_digest.status_code, 409)
        self.assertIn("differs from the reviewed preview", wrong_digest.get_json()["error"])

        stale = self.client.post("/api/project/import/apply", json={
            "project": project,
            "preview_sha256": preview["preview_sha256"],
            "expected_revision": preview["current_revision"] + 1,
        })
        self.assertEqual(stale.status_code, 409)
        self.assertIn("changed after preview", stale.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
