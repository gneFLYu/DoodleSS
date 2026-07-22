import sys
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import app as app_module
from app import app


class StudioApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.data_dir = TemporaryDirectory()
        self.old_data_path = app_module.DATA_PATH
        app_module.DATA_PATH = Path(self.data_dir.name) / "project.json"

    def tearDown(self):
        app_module.DATA_PATH = self.old_data_path
        self.data_dir.cleanup()

    def test_project_and_proof_suggestions_are_available(self):
        project = self.client.get("/api/project").get_json()
        self.assertGreaterEqual(len(project["workspaces"]), 2)
        workspace = project["workspaces"][0]
        response = self.client.post(f"/api/workspaces/{workspace['id']}/suggestions", json={"rules": ["LeibnizRule", "VanishingLine"]})
        self.assertEqual(response.status_code, 200)
        self.assertIn("suggestions", response.get_json())

    def test_chart_is_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"HFPSS Studio", response.data)
        self.assertIn(b"katex", response.data)
        self.assertIn(b"legacy-toolbar", response.data)
        self.assertNotIn(b"RESEARCH DOSSIER", response.data)
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.get_json()["application"], "HFPSS Studio")

    def test_can_create_a_class(self):
        workspace = self.client.get("/api/project").get_json()["workspaces"][0]
        response = self.client.post(f"/api/workspaces/{workspace['id']}/classes", json={"label": "m", "stem": 12, "filtration": 4})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["class"]["grade"]["stem"], 12)

    def test_new_workspace_uses_the_25_page_default(self):
        response = self.client.post("/api/workspaces", json={"name": "New workspace"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["workspace"]["settings"]["page_limit"], 25)

    def test_class_can_be_renamed_and_deleted_with_its_local_arrows(self):
        workspace = self.client.get("/api/project").get_json()["workspaces"][0]
        created = self.client.post(f"/api/workspaces/{workspace['id']}/classes", json={"label": "m", "stem": 12, "filtration": 4}).get_json()["class"]
        renamed = self.client.patch(f"/api/workspaces/{workspace['id']}/classes/{created['id']}", json={"label": "m'"})
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.get_json()["class"]["label"], "m'")
        deleted = self.client.delete(f"/api/workspaces/{workspace['id']}/classes/{created['id']}")
        self.assertEqual(deleted.status_code, 200)

    def test_research_seed_exposes_provenance_and_project_wide_tree(self):
        project = self.client.get("/api/project").get_json()
        workspace_ids = {workspace["id"] for workspace in project["workspaces"]}
        self.assertIn("ws_2sigma_i", workspace_ids)
        self.assertIn("ws_tate", workspace_ids)
        self.assertIn("source", project["research_brief"])
        rendering = project["workspaces"][0]["settings"]["rendering"]
        self.assertEqual(project["workspaces"][0]["settings"]["page_limit"], 25)
        self.assertEqual(rendering["buffer_cells"], 6)
        self.assertGreaterEqual(project["workspaces"][0]["settings"]["grid"]["filtration_min"], 0)
        self.assertEqual(rendering["periodicity"], [])

        tree = self.client.get("/api/proof-tree").get_json()
        node_ids = {node["id"] for node in tree["nodes"]}
        self.assertIn("prop_two_d3_u", node_ids)
        self.assertTrue(any(node["source_ref"] for node in tree["nodes"]))

    def test_three_sigma_seed_covers_documented_pages_not_e_infinity(self):
        project = self.client.get("/api/project").get_json()
        workspace = next(item for item in project["workspaces"] if item["id"] == "ws_3sigma_i")
        self.assertEqual(workspace["settings"]["known_page_max"], 12)
        d3 = next(item for item in workspace["differentials"] if item["id"] == "diff_three_d3")
        self.assertEqual(d3["period_stem"], 8)
        d5 = [item for item in workspace["differentials"] if item["page"] == 5]
        self.assertEqual(len(d5), 5)
        self.assertTrue(all(item["period_stem"] == 16 for item in d5))
        d9 = [item for item in workspace["differentials"] if item["page"] == 9]
        self.assertEqual(len(d9), 5)
        self.assertTrue(all(item["period_stem"] == 32 for item in d9))
        self.assertEqual(next(item for item in workspace["differentials"] if item["page"] == 11)["period_stem"], 32)

    def test_two_sigma_differential_periods_follow_the_documented_families(self):
        project = self.client.get("/api/project").get_json()
        workspace = next(item for item in project["workspaces"] if item["id"] == "ws_2sigma_i")
        periods = {item["id"]: item["period_stem"] for item in workspace["differentials"]}
        self.assertEqual(periods["diff_two_d3_u"], 8)
        self.assertEqual(periods["diff_two_d5_h2D"], 16)
        self.assertEqual(periods["diff_two_d5_2D"], 16)
        self.assertEqual(periods["diff_two_d5_xh1"], 8)
        self.assertEqual(periods["diff_two_d9"], 32)
        self.assertEqual(periods["diff_two_d11"], 32)
        self.assertEqual(periods["diff_two_d13"], 32)

    def test_legacy_project_periods_are_migrated_without_overwriting_existing_values(self):
        project = app_module.demo_project()
        workspace = next(item for item in project.workspaces if item.id == "ws_2sigma_i")
        d5 = next(item for item in workspace.differentials if item.id == "diff_two_d5_h2D")
        d5.period_stem = 0
        app_module.migrate_legacy_periods(project)
        self.assertEqual(d5.period_stem, 16)
        d5.period_stem = 24
        app_module.migrate_legacy_periods(project)
        self.assertEqual(d5.period_stem, 24)

    def test_frontend_has_page_liveness_and_per_differential_periodicity(self):
        script = (Path(__file__).resolve().parents[1] / "backend" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function liveClassesAt", script)
        self.assertIn("item.page === ws.page", script)
        self.assertIn("diff.period_stem", script)
        self.assertIn("__add_page", script)
        self.assertIn("Upper half-plane", script)
        self.assertIn("function periodsForClassOnPage", script)
        self.assertIn("function handleHotkey", script)
        self.assertIn('document.addEventListener("keydown", handleHotkey, true)', script)
        self.assertNotIn("settings.rendering?.periodicity?.[0]", script)
        markup = (Path(__file__).resolve().parents[1] / "backend" / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="cancel-class"', markup)
        self.assertNotIn('method="dialog" id="class-form"', markup)

    def test_class_creation_rejects_invalid_inputs(self):
        workspace = self.client.get("/api/project").get_json()["workspaces"][0]
        empty = self.client.post(f"/api/workspaces/{workspace['id']}/classes", json={"label": "   ", "stem": 0, "filtration": 0})
        self.assertEqual(empty.status_code, 400)
        negative = self.client.post(f"/api/workspaces/{workspace['id']}/classes", json={"label": "x", "stem": 0, "filtration": -1})
        self.assertEqual(negative.status_code, 400)

    def test_page_limit_can_be_extended_but_not_shrunk_below_default(self):
        workspace = self.client.get("/api/project").get_json()["workspaces"][0]
        extended = self.client.patch(f"/api/workspaces/{workspace['id']}/settings", json={"page_limit": 26})
        self.assertEqual(extended.status_code, 200)
        self.assertEqual(extended.get_json()["settings"]["page_limit"], 26)
        invalid = self.client.patch(f"/api/workspaces/{workspace['id']}/settings", json={"page_limit": 24})
        self.assertEqual(invalid.status_code, 400)


if __name__ == "__main__":
    unittest.main()
