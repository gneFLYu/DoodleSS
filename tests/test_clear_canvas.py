"""Safety contract for the workspace-level clear-canvas archive action."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as app_module
from app import app
from domain.history import clear_history


class ClearCanvasApiTest(unittest.TestCase):
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

    def workspace(self, workspace_id):
        project = self.client.get("/api/project").get_json()
        return next(item for item in project["workspaces"] if item["id"] == workspace_id)

    def test_clear_archives_all_active_dots_without_deleting_math_and_undo_restores_them(self):
        original_project = self.client.get("/api/project").get_json()
        original = next(item for item in original_project["workspaces"] if item["classes"])
        workspace_id = original["id"]
        active_ids = {item["id"] for item in original["classes"] if not item["archived"]}
        class_ids = {item["id"] for item in original["classes"]}
        differential_ids = {item["id"] for item in original["differentials"]}
        proposition_ids = {item["id"] for item in original["propositions"]}

        response = self.client.post(f"/api/workspaces/{workspace_id}/clear-canvas")
        self.assertEqual(response.status_code, 200, response.get_json())
        body = response.get_json()
        self.assertTrue(body["changed"])
        self.assertEqual(body["archived_count"], len(active_ids))
        self.assertEqual(set(body["archived_class_ids"]), active_ids)
        self.assertIn("no mathematical records were physically deleted", body["message"])
        self.assertEqual(body["undo_depth"], 1)
        self.assertIn("clear current canvas", body["undo_label"].lower())

        cleared = self.workspace(workspace_id)
        self.assertEqual({item["id"] for item in cleared["classes"]}, class_ids)
        self.assertEqual({item["id"] for item in cleared["differentials"]}, differential_ids)
        self.assertEqual({item["id"] for item in cleared["propositions"]}, proposition_ids)
        self.assertTrue(all(item["archived"] for item in cleared["classes"]))
        self.assertEqual({item["class_id"] for item in cleared["fates"]}, class_ids)
        self.assertTrue(all("Clear current canvas" in item["archived_reason"] for item in cleared["classes"] if item["id"] in active_ids))

        self.assertEqual(self.client.post("/api/history/undo").status_code, 200)
        restored = self.workspace(workspace_id)
        self.assertEqual(
            {item["id"] for item in restored["classes"] if not item["archived"]},
            active_ids,
        )
        self.assertEqual(self.client.post("/api/history/redo").status_code, 200)
        redone = self.workspace(workspace_id)
        self.assertTrue(all(item["archived"] for item in redone["classes"]))

    def test_already_empty_canvas_is_a_non_mutating_noop(self):
        workspace = next(item for item in self.client.get("/api/project").get_json()["workspaces"] if item["classes"])
        workspace_id = workspace["id"]
        self.assertEqual(self.client.post(f"/api/workspaces/{workspace_id}/clear-canvas").status_code, 200)
        before_noop = self.client.get("/api/history").get_json()
        before_revision = self.client.get("/api/project").get_json()["revision"]
        no_op = self.client.post(f"/api/workspaces/{workspace_id}/clear-canvas")
        self.assertEqual(no_op.status_code, 200)
        body = no_op.get_json()
        self.assertFalse(body["changed"])
        self.assertEqual(body["archived_count"], 0)
        self.assertEqual(body["revision"], before_revision)
        self.assertEqual(body["undo_depth"], before_noop["undo_depth"])

    def test_unknown_workspace_is_not_mutated(self):
        response = self.client.post("/api/workspaces/not-a-workspace/clear-canvas")
        self.assertEqual(response.status_code, 404)
        self.assertIn("Unknown workspace", response.get_json()["error"])
        self.assertEqual(self.client.get("/api/history").get_json()["undo_depth"], 0)


if __name__ == "__main__":
    unittest.main()
