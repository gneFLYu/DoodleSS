import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as app_module
from app import app
from domain.history import clear_history


class UndoRedoApiTest(unittest.TestCase):
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

    def make_claim_workspace(self):
        workspace = self.client.post("/api/workspaces", json={"name": "History claims"}).get_json()["workspace"]
        source = self.client.post(
            f"/api/workspaces/{workspace['id']}/classes",
            json={"label": "x", "expression": "x", "stem": 5, "filtration": 0},
        ).get_json()["class"]
        target = self.client.post(
            f"/api/workspaces/{workspace['id']}/classes",
            json={"label": "y", "expression": "y", "stem": 4, "filtration": 3},
        ).get_json()["class"]
        clear_history(app_module.history_key())
        return workspace, source, target

    def saved_workspace(self, workspace_id):
        project = self.client.get("/api/project").get_json()
        return next(item for item in project["workspaces"] if item["id"] == workspace_id)

    def test_differential_and_its_proposition_undo_and_redo_as_one_transaction(self):
        workspace, source, target = self.make_claim_workspace()
        created = self.client.post(
            f"/api/workspaces/{workspace['id']}/differentials",
            json={"source_id": source["id"], "target_id": target["id"], "page": 3},
        )
        self.assertEqual(created.status_code, 201)
        differential = created.get_json()["differential"]
        status = self.client.get("/api/history").get_json()
        self.assertEqual(status["undo_depth"], 1)
        self.assertIn("differential", status["undo_label"].lower())

        after_create = self.saved_workspace(workspace["id"])
        self.assertIn(differential["id"], {item["id"] for item in after_create["differentials"]})
        self.assertIn(differential["proposition_id"], {item["id"] for item in after_create["propositions"]})

        undone = self.client.post("/api/history/undo")
        self.assertEqual(undone.status_code, 200)
        after_undo = self.saved_workspace(workspace["id"])
        self.assertNotIn(differential["id"], {item["id"] for item in after_undo["differentials"]})
        self.assertNotIn(differential["proposition_id"], {item["id"] for item in after_undo["propositions"]})
        self.assertEqual(after_undo["differential_events"], [])
        self.assertEqual(undone.get_json()["redo_depth"], 1)

        redone = self.client.post("/api/history/redo")
        self.assertEqual(redone.status_code, 200)
        after_redo = self.saved_workspace(workspace["id"])
        self.assertIn(differential["id"], {item["id"] for item in after_redo["differentials"]})
        self.assertIn(differential["proposition_id"], {item["id"] for item in after_redo["propositions"]})
        self.assertEqual(len(after_redo["differential_events"]), 2)

    def test_relation_is_present_in_the_same_history_stack(self):
        workspace, source, target = self.make_claim_workspace()
        statement = "Relation: x ~ y"
        created = self.client.post(
            f"/api/workspaces/{workspace['id']}/propositions",
            json={
                "kind": "relation",
                "statement": statement,
                "status": "candidate",
                "conclusion": {"source_id": source["id"], "target_id": target["id"], "page": 2},
            },
        )
        self.assertEqual(created.status_code, 201)
        proposition_id = created.get_json()["proposition"]["id"]
        history = self.client.get("/api/history").get_json()
        self.assertIn("relation", history["undo_label"].lower())
        self.assertIn(statement, history["undo_stack"][0])

        self.assertEqual(self.client.post("/api/history/undo").status_code, 200)
        self.assertNotIn(proposition_id, {item["id"] for item in self.saved_workspace(workspace["id"])["propositions"]})
        self.assertEqual(self.client.post("/api/history/redo").status_code, 200)
        self.assertIn(proposition_id, {item["id"] for item in self.saved_workspace(workspace["id"])["propositions"]})

    def test_new_edit_after_undo_clears_redo_stack(self):
        workspace, source, _ = self.make_claim_workspace()
        self.client.patch(
            f"/api/workspaces/{workspace['id']}/classes/{source['id']}",
            json={"label": "x-prime"},
        )
        self.assertEqual(self.client.post("/api/history/undo").status_code, 200)
        self.assertEqual(self.client.get("/api/history").get_json()["redo_depth"], 1)

        self.client.patch(
            f"/api/workspaces/{workspace['id']}/classes/{source['id']}",
            json={"label": "x-new"},
        )
        self.assertEqual(self.client.get("/api/history").get_json()["redo_depth"], 0)
        self.assertEqual(self.client.post("/api/history/redo").status_code, 409)

    def test_archive_is_reversible_without_losing_claim_history(self):
        workspace, source, target = self.make_claim_workspace()
        relation = self.client.post(
            f"/api/workspaces/{workspace['id']}/propositions",
            json={"kind": "relation", "statement": "x relates to y", "status": "candidate"},
        ).get_json()["proposition"]
        clear_history(app_module.history_key())

        self.assertEqual(
            self.client.delete(f"/api/workspaces/{workspace['id']}/classes/{source['id']}").status_code,
            200,
        )
        archived = self.saved_workspace(workspace["id"])
        self.assertTrue(next(item for item in archived["classes"] if item["id"] == source["id"])["archived"])
        self.assertIn(relation["id"], {item["id"] for item in archived["propositions"]})

        self.client.post("/api/history/undo")
        restored = self.saved_workspace(workspace["id"])
        self.assertFalse(next(item for item in restored["classes"] if item["id"] == source["id"])["archived"])
        self.assertIn(relation["id"], {item["id"] for item in restored["propositions"]})


if __name__ == "__main__":
    unittest.main()
