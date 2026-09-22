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
        derived_id = "formal_diff_three_d5_tate_positive_derived"
        self.assertEqual(len([item for item in d5 if item["id"] != derived_id]), 5)
        derived = [item for item in d5 if item["id"] == derived_id]
        self.assertEqual(len(derived), 1)
        self.assertEqual(derived[0]["status"], "verified")
        claim = next(item for item in workspace["propositions"] if item["id"] == derived[0]["proposition_id"])
        metadata = claim["conclusion"]
        self.assertEqual(claim["status"], "verified")
        self.assertEqual(metadata["source_status"], "independently-verified")
        self.assertEqual(metadata["source_blockers"], [])
        self.assertEqual(metadata["evidence_kind"], "Tate-comparison-derived")
        self.assertEqual(metadata["comparison_translation"],
                         {"g_exponent": -2, "D_exponent": 4, "spectral_sequence": "tate"})
        self.assertEqual((metadata["comparison_source_filtration"], metadata["comparison_target_filtration"]), (2, 7))
        self.assertIn("FN-3I-002", metadata["derived_from"])
        certificate = metadata["verification_certificate"]
        self.assertEqual(certificate["status"], "verified")
        self.assertEqual(certificate["method"], "Euler image and finite incoming-source exclusion")
        self.assertIn("FN-2I-010", certificate["premises"])
        self.assertTrue(certificate["source_refs"])
        self.assertFalse({"FN-3I-010", "FN-3I-010-pc"} & set(certificate["premises"]))
        self.assertTrue(all(item["period_stem"] == 16 for item in d5))
        d9 = [item for item in workspace["differentials"] if item["page"] == 9]
        original_d9 = [item for item in d9 if item["id"] in {"diff_three_d9_25", "diff_three_d9_25b"}]
        self.assertEqual(len(original_d9), 2)
        self.assertTrue(all(item["period_stem"] == 64 and item["status"] == "verified" for item in original_d9))
        siblings = [item for item in d9 if item["id"] in {
            "formal_diff_three_d9_t_D7_sibling", "formal_diff_three_d9_b_D7_sibling"}]
        self.assertEqual(len(siblings), 2)
        self.assertTrue(all(item["period_stem"] == 64 and item["status"] == "verified" for item in siblings))
        claims = {item["id"]: item for item in workspace["propositions"]}
        for item in original_d9 + siblings:
            metadata = claims[item["proposition_id"]]["conclusion"]
            self.assertEqual(metadata["paired_pattern_stem"], 32)
            self.assertIn(metadata["coefficient_parameter"]["id"], {"three_sigma_d9_CD3", "three_sigma_d9_CD7"})
            self.assertEqual(metadata["verification_certificate"]["method"],
                             "Euler products, finite target survival and h1 detection")
            self.assertTrue(metadata["verification_certificate"]["no_withdrawn_premise"])
        derived_d9 = [item for item in d9 if item["label"].startswith("DER-")]
        self.assertEqual(len(derived_d9), 10)
        even_facts = {"DER-3I-D9-P", "DER-3I-D9-Q", "DER-3I-D9-C"}
        self.assertEqual(sum(item["label"] in even_facts for item in derived_d9), 6)
        for item in derived_d9:
            metadata = claims[item["proposition_id"]]["conclusion"]
            self.assertEqual(item["period_stem"], 64)
            if item["label"] in even_facts:
                self.assertEqual(item["status"], "verified")
                self.assertEqual(claims[item["proposition_id"]]["status"], "verified")
                self.assertEqual(metadata["source_status"], "independently-verified")
                self.assertEqual(metadata["verification_certificate"]["status"], "verified")
                self.assertEqual(metadata["verification_certificate"]["method"], "Euler image, finite g-injection and h1 lift")
                self.assertFalse({"FN-3I-010", "FN-3I-010-pc"} & set(metadata["derived_from"]))
            else:
                self.assertIn(item["label"], {"DER-3I-EULER-D9-B", "DER-3I-EULER-D9-C"})
                self.assertEqual(item["status"], "verified")
                self.assertEqual(claims[item["proposition_id"]]["status"], "verified")
                self.assertEqual(metadata["source_status"], "independently-verified")
                self.assertEqual(metadata["verification_certificate"]["status"], "verified")
                self.assertEqual(metadata["verification_certificate"]["method"],
                                 "Euler products, finite target survival and h1 detection")
                self.assertFalse({"FN-3I-010", "FN-3I-010-pc"} & set(metadata["derived_from"]))
        d11 = [item for item in workspace["differentials"] if item["page"] == 11]
        original_d11_ids = {"diff_three_d11_30", "formal_diff_fn-3i-009_2"}
        cd1_d11_id = "formal_diff_three_d11_c_D1_euler_forced"
        self.assertEqual(len(d11), 3)
        self.assertEqual({item["id"] for item in d11}, original_d11_ids | {cd1_d11_id})
        nodes = {item["id"]: item for item in workspace["classes"]}
        original_d11_grades = {
            "diff_three_d11_30": ((30, 2), (29, 13)),
            "formal_diff_fn-3i-009_2": ((31, 3), (30, 14)),
        }
        for item in (row for row in d11 if row["id"] in original_d11_ids):
            metadata = claims[item["proposition_id"]]["conclusion"]
            self.assertEqual(metadata["fact_id"], "FN-3I-009")
            self.assertEqual(tuple((nodes[item[key]]["grade"]["stem"], nodes[item[key]]["grade"]["filtration"])
                                   for key in ("source_id", "target_id")), original_d11_grades[item["id"]])
            self.assertEqual(item["status"], "verified")
            self.assertEqual(claims[item["proposition_id"]]["status"], "verified")
            self.assertEqual(item["period_stem"], 32)
            self.assertFalse(metadata["period_is_invertible"])
            self.assertEqual(metadata["verification_certificate"]["method"],
                             "C4 restriction detection and finite E11 quotient")
            self.assertTrue(metadata["verification_certificate"]["no_withdrawn_premise"])
        cd1 = next(item for item in d11 if item["id"] == cd1_d11_id)
        claim = claims[cd1["proposition_id"]]
        metadata = claim["conclusion"]
        self.assertEqual(cd1["label"], "DER-3I-EULER-CD1-D11")
        self.assertEqual(metadata["fact_id"], cd1["label"])
        self.assertEqual((cd1["status"], claim["status"], metadata["source_status"]),
                         ("verified", "verified", "independently-verified"))
        self.assertEqual((cd1["period_stem"], metadata["period_stem"]), (64, 64))
        self.assertTrue(metadata["period_is_invertible"])
        self.assertEqual(metadata["coefficient_scope"], "exact-port")
        for key, grade, pattern, two in (("source_id", (9, 1), "S11", 0), ("target_id", (8, 12), "S40", 1)):
            node = nodes[cd1[key]]
            self.assertEqual((node["grade"]["stem"], node["grade"]["filtration"]), grade)
            self.assertEqual((node["style"]["e2_pattern"], node["style"].get("two_valuation", 0),
                              node["style"].get("j_order", 0)), (pattern, two, 0))
        certificate = metadata["verification_certificate"]
        self.assertEqual((certificate["status"], certificate["method"]),
                         ("verified", "Euler13 product and complete finite incoming inventory"))
        self.assertEqual(certificate["period"],
                         {"D_power": 8, "stem": 64, "forward_g": True, "D5_block_inferred": False})
        self.assertIn("DKLLW24 Table 9 d13", certificate["premises"])
        self.assertTrue(certificate["source_refs"])
        self.assertTrue(certificate["no_withdrawn_premise"])
        self.assertFalse({"FN-3I-010", "FN-3I-010-pc"} & set(certificate["premises"]))
        self.assertEqual(metadata["source_blockers"], [])
        self.assertEqual({item["page"] for item in workspace["differentials"] if item["page"] >= 19}, {19, 23})

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
        # FN-2I-018 has only the permanent D^8 repeat. The old 32 fallback
        # killed the FN-2I-019 target before its d21 page.
        self.assertEqual(periods["diff_two_d13"], 64)
        d13 = next(item for item in workspace["differentials"] if item["id"] == "diff_two_d13")
        claim = next(item for item in workspace["propositions"] if item["id"] == d13["proposition_id"])
        self.assertEqual(claim["conclusion"]["period_stem"], d13["period_stem"])

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
        self.assertIn("differential.period_stem", script)
        self.assertIn("function periodsForDifferential", script)
        self.assertIn("__add_page", script)
        self.assertIn("Upper half-plane", script)
        self.assertIn("function periodsForClassOnPage", script)
        self.assertIn("function handleHotkey", script)
        self.assertIn('document.addEventListener("keydown", handleHotkey, true)', script)
        self.assertNotIn("settings.rendering?.periodicity?.[0]", script)
        self.assertIn("function workspaceRenderPeriods", script)
        self.assertIn("function latticeCopies", script)
        self.assertIn("legacy_x_offset", script)
        self.assertIn("function renderClassList", script)
        self.assertIn("matching.slice(0, limit)", script)
        markup = (Path(__file__).resolve().parents[1] / "backend" / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="cancel-class"', markup)
        self.assertIn('id="class-filter"', markup)
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
