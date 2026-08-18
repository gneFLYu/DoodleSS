import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as app_module
from app import app
from domain.history import clear_history


class CellApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.data_dir = TemporaryDirectory()
        self.old_data_path = app_module.DATA_PATH
        app_module.DATA_PATH = Path(self.data_dir.name) / "project.json"
        clear_history(app_module.history_key())
        project = self.client.get("/api/project").get_json()
        self.workspace_id = next(item["id"] for item in project["workspaces"] if item["id"] == "ws_integer")

    def tearDown(self):
        clear_history(app_module.history_key())
        app_module.DATA_PATH = self.old_data_path
        self.data_dir.cleanup()

    def create_cell(self, stem, filtration, basis, display_basis=None):
        payload = {
            "grade": {"stem": stem, "filtration": filtration, "representation": {}},
            "page": 2,
            "coefficient_context_id": "q8-residue-f4",
            "basis": [{"label": label} for label in basis],
            "display_basis": display_basis or [],
            "named_vectors": [],
        }
        response = self.client.post(f"/api/v2/workspaces/{self.workspace_id}/cells", json=payload)
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()["cell"]

    def test_cell_authoring_normalizes_f4_and_is_undoable(self):
        cell = self.create_cell(6, 0, ["a", "b", "c"], [
            {"label": "a+b", "coordinates": ["1", "1", "0"]},
            {"label": "b", "coordinates": ["0", "1", "0"]},
            {"label": "c", "coordinates": ["0", "0", "1"]},
        ])
        response = self.client.patch(
            f"/api/v2/workspaces/{self.workspace_id}/cells/{cell['id']}",
            json={"named_vectors": [{"label": "a+(1+zeta)b", "coordinates": ["1", "1+zeta", "0"]}]},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["cell"]["named_vectors"][0]["coordinates"], ["1", "zeta^2", "0"])
        self.assertGreaterEqual(self.client.get("/api/history").get_json()["undo_depth"], 2)
        self.assertEqual(self.client.post("/api/history/undo").status_code, 200)

    def test_candidate_map_is_preview_only_and_sum_target_gives_rank_one_quotient(self):
        source = self.create_cell(7, 1, ["x"])
        target = self.create_cell(6, 6, ["a", "b"])
        created = self.client.post(f"/api/v2/workspaces/{self.workspace_id}/differential-maps", json={
            "source_cell_id": source["id"],
            "target_cell_id": target["id"],
            "page": 5,
            "matrix": [["1"], ["1"]],
            "coverage": "complete",
            "status": "candidate",
        })
        self.assertEqual(created.status_code, 201, created.get_json())
        item = created.get_json()["differential_map"]
        self.assertEqual(created.get_json()["image_ports"][0]["projective_coordinates"], ["1", "1"])

        canonical = self.client.get(
            f"/api/v2/workspaces/{self.workspace_id}/cells/{target['id']}/page-transition?page=5"
        ).get_json()["transition"]
        self.assertEqual(canonical["status"], "underdetermined")

        preview = self.client.post(f"/api/v2/workspaces/{self.workspace_id}/page-transitions/preview", json={
            "cell_id": target["id"], "page": 5,
            "incoming_map_id": item["id"], "outgoing_zero": True,
        })
        self.assertEqual(preview.status_code, 200, preview.get_json())
        transition = preview.get_json()["transition"]
        self.assertEqual(transition["status"], "complete")
        self.assertEqual(transition["image_basis"], [["1", "1"]])
        self.assertEqual(transition["quotient_rank"], 1)
        self.assertFalse(transition["canonical"])

    def test_witt_context_and_noninvertible_display_basis_are_rejected(self):
        witt = self.client.post(f"/api/v2/workspaces/{self.workspace_id}/cells", json={
            "grade": {"stem": 0, "filtration": 0},
            "coefficient_context_id": "q8-witt-f4",
            "basis": [{"label": "a"}],
        })
        self.assertEqual(witt.status_code, 400)
        self.assertIn("will not be reduced", witt.get_json()["error"])
        singular = self.client.post(f"/api/v2/workspaces/{self.workspace_id}/cells", json={
            "grade": {"stem": 0, "filtration": 0},
            "coefficient_context_id": "q8-residue-f4",
            "basis": [{"label": "a"}, {"label": "b"}],
            "display_basis": [
                {"label": "a+b", "coordinates": ["1", "1"]},
                {"label": "zeta(a+b)", "coordinates": ["zeta", "zeta"]},
            ],
        })
        self.assertEqual(singular.status_code, 400)
        self.assertIn("invertible", singular.get_json()["error"])

    def test_accepted_composable_maps_must_square_to_zero(self):
        first = self.create_cell(2, 0, ["a"])
        middle = self.create_cell(1, 3, ["b"])
        last = self.create_cell(0, 6, ["c"])
        payload = {
            "page": 3, "matrix": [["1"]], "coverage": "complete",
            "status": "established", "source_ref": "formal_notes.tex:test",
        }
        one = self.client.post(f"/api/v2/workspaces/{self.workspace_id}/differential-maps", json={
            **payload, "source_cell_id": first["id"], "target_cell_id": middle["id"],
        })
        self.assertEqual(one.status_code, 201, one.get_json())
        two = self.client.post(f"/api/v2/workspaces/{self.workspace_id}/differential-maps", json={
            **payload, "source_cell_id": middle["id"], "target_cell_id": last["id"],
        })
        self.assertEqual(two.status_code, 400)
        self.assertIn("d_r^2", two.get_json()["error"])

    def test_formal_notes_sample_and_review_graph_expose_matrix_semantics(self):
        project = self.client.get("/api/project").get_json()
        workspace = next(item for item in project["workspaces"] if item["id"] == "ws_3sigma_i")
        target = next(item for item in workspace["cells"] if item["id"] == "cell_three_sum_target")
        linear_map = next(item for item in workspace["differential_maps"] if item["id"] == "linear_diff_three_d5_sum")
        named = next(item for item in target["named_vectors"] if item["id"] == "vector_three_sum_target")
        self.assertEqual(named["coordinates"], ["1", "1"])
        self.assertEqual(linear_map["matrix"], [["1"], ["1"]])
        self.assertEqual(linear_map["image_ports"][0]["projective_coordinates"], ["1", "1"])
        self.assertIn("formal_notes.tex:749-760", linear_map["source_ref"])

        graph = self.client.get("/api/v2/logic-graph").get_json()
        kinds = {item["kind"] for item in graph["nodes"]}
        self.assertIn("cell-vector-space", kinds)
        self.assertIn("differential-map", kinds)


if __name__ == "__main__":
    unittest.main()
