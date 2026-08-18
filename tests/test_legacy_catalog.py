import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import app
from domain.legacy_catalog import CATALOG, catalog_workspace_dict, manifest


class LegacyCatalogTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_manifest_covers_all_21_valid_canvases(self):
        entries = manifest()
        self.assertEqual(len(entries), 21)
        self.assertEqual({item["id"] for item in entries}, {item.id for item in CATALOG})
        self.assertTrue(all(item["statistics"]["dangling_connections"] == 0 for item in entries))
        self.assertTrue(all(item["statistics"]["generators"] > 0 for item in entries))

    def test_every_manifest_entry_maps_to_a_complete_workspace(self):
        statistics = {item["id"]: item["statistics"] for item in manifest()}
        for entry in CATALOG:
            workspace = catalog_workspace_dict(entry.id)
            self.assertEqual(len(workspace["classes"]), statistics[entry.id]["generators"])
            self.assertEqual(len(workspace["propositions"]), statistics[entry.id]["connections"])
            self.assertEqual(len(workspace["differentials"]), statistics[entry.id]["differentials"])

    def test_representative_sectors_map_to_read_only_workspaces(self):
        for entry_id in ("2sigma-dec30", "3sigma-public", "mixed-july20"):
            workspace = catalog_workspace_dict(entry_id)
            self.assertTrue(workspace["settings"]["read_only_catalog"])
            self.assertGreater(len(workspace["classes"]), 1000)
            self.assertEqual(len(workspace["propositions"]), workspace["settings"]["catalog_entry"]["statistics"]["connections"])

    def test_differential_page_controls_endpoint_liveness(self):
        workspace = catalog_workspace_dict("2sigma-dec30")
        differential = next(item for item in workspace["differentials"] if item["page"] == 3)
        fates = {item["class_id"]: item for item in workspace["fates"]}
        for class_id in (differential["source_id"], differential["target_id"]):
            self.assertEqual(fates[class_id]["first_hfpss_death"]["page"], 3)
            self.assertEqual(fates[class_id]["last_hfpss_live_page"], 3)

    def test_current_and_conflict_statuses_remain_visible(self):
        entries = {item["id"]: item for item in manifest()}
        self.assertEqual(entries["2sigma-dec30"]["status"], "current")
        self.assertEqual(entries["mixed-conflict-feb12"]["status"], "conflict")
        self.assertEqual(entries["mixed-e5-2"]["status"], "rejected")
        self.assertIn("formal_notes.tex", entries["mixed-july20"]["evidence_ref"])

    def test_deployment_static_copies_match(self):
        for filename in ("app.js", "style.css"):
            self.assertEqual(
                (ROOT / "backend" / "static" / filename).read_bytes(),
                (ROOT / "public" / "static" / filename).read_bytes(),
            )

    def test_catalog_api_does_not_mutate_saved_project(self):
        before = self.client.get("/api/project").get_json()
        listing = self.client.get("/api/v2/legacy-catalog")
        entry = self.client.get("/api/v2/legacy-catalog/3sigma-public")
        after = self.client.get("/api/project").get_json()
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.get_json()["entries"]), 21)
        self.assertEqual(entry.status_code, 200)
        self.assertTrue(entry.get_json()["workspace"]["settings"]["read_only_catalog"])
        self.assertEqual(before, after)

    def test_unknown_catalog_entry_is_404(self):
        self.assertEqual(self.client.get("/api/v2/legacy-catalog/not-a-chart").status_code, 404)

    def test_computation_page_exposes_catalog_controls(self):
        markup = self.client.get("/").get_data(as_text=True)
        self.assertIn('id="legacy-catalog-select"', markup)
        self.assertIn('id="open-legacy-catalog"', markup)
        self.assertIn('id="close-legacy-catalog"', markup)


if __name__ == "__main__":
    unittest.main()
