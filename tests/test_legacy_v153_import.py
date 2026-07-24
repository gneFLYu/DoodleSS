"""API regression for additive conversion of a real sseq ver15.3 save file."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT.parent / "frontEnd_lty" / "2sigma_Dec23.json"
DEC30_FIXTURE = ROOT.parent / "frontEnd_lty" / "2sigma_Dec30.json"
sys.path.insert(0, str(ROOT / "backend"))

import app as app_module
from app import app
from domain.history import clear_history


class LegacyV153ImportApiTest(unittest.TestCase):
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

    def test_real_2sigma_canvas_previews_appends_applies_and_round_trips(self):
        if not FIXTURE.exists():
            self.skipTest(f"Optional local integration fixture is unavailable: {FIXTURE}")
        legacy = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual((len(legacy["generators"]), len(legacy["connections"]), len(legacy["periodicityRules"])), (2013, 2655, 2))
        before = self.client.get("/api/project").get_json()
        before_workspace_ids = {item["id"] for item in before["workspaces"]}

        started = time.perf_counter()
        response = self.client.post(
            "/api/project/import/preview?source_name=2sigma_Dec23.json&workspace_name=Imported%202sigma%20Dec23",
            json=legacy,
        )
        elapsed = time.perf_counter() - started
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertLess(elapsed, 15.0, f"Large legacy preview took {elapsed:.2f}s")
        body = response.get_json()
        self.assertTrue(body["valid"])
        self.assertEqual(body["import"]["format"], "legacy-sseq-ver15.3")
        self.assertEqual(body["import"]["operation"], "append-workspace")
        self.assertEqual(body["import"]["legacy_summary"], {
            "generators_received": 2013,
            "classes_created": 2013,
            "connections_received": 2655,
            "connection_propositions_created": 2655,
            "relations_created": 1829,
            "differentials_created": 822,
            "differential_anomalies": 4,
            "periodic_visual_connections": 2579,
            "periodicity_rules_received": 2,
            "manual_periodicity_rules_created": 2,
        })
        anomaly = next(item for item in body["import"]["warnings"] if item["code"] == "differential-bidegree-anomalies")
        self.assertEqual(anomaly["count"], 4)

        converted = body["project"]
        raw_apply_bytes = len(json.dumps(legacy, separators=(",", ":")).encode("utf-8"))
        old_apply_bytes = len(json.dumps(converted, separators=(",", ":")).encode("utf-8"))
        self.assertLess(raw_apply_bytes, old_apply_bytes)
        self.assertGreater(old_apply_bytes, 4_500_000)
        self.assertTrue(before_workspace_ids.issubset({item["id"] for item in converted["workspaces"]}))
        self.assertEqual(len(converted["workspaces"]), len(before["workspaces"]) + 1)
        self.assertEqual(body["imported_workspace_id"], body["import"]["imported_workspace_id"])
        imported = next(item for item in converted["workspaces"] if item["id"] == body["import"]["imported_workspace_id"])
        self.assertEqual(imported["name"], "Imported 2sigma Dec23")
        self.assertEqual((len(imported["classes"]), len(imported["differentials"]), len(imported["propositions"])), (2013, 822, 4668))

        origin = [item for item in imported["classes"] if item["grade"]["stem"] == 0 and item["grade"]["filtration"] == 0]
        self.assertGreaterEqual(len(origin), 3)
        self.assertEqual(len({item["id"] for item in origin}), len(origin))
        self.assertEqual(
            [item["style"]["legacy_y_offset"] for item in origin[:3]],
            [0.0, 0.2, 0.4],
        )
        imported_rules = [
            item for item in converted["manual_periodicity_rules"]
            if item["workspace_id"] == imported["id"]
        ]
        self.assertEqual(
            [(item["name"], item["period_vector"]["stem"], item["period_vector"]["filtration"], item["status"]) for item in imported_rules],
            [("D^8", 64, 0, "manual-unverified"), ("kD^3", 20, 4, "manual-unverified")],
        )
        self.assertEqual(self.client.get("/api/history").get_json()["undo_depth"], 0)
        self.assertEqual(
            {item["id"] for item in self.client.get("/api/project").get_json()["workspaces"]},
            before_workspace_ids,
        )

        applied = self.client.post("/api/project/import/apply", json={
            "legacy_canvas": legacy,
            "preview_sha256": body["preview_sha256"],
            "expected_revision": body["current_revision"],
            "imported_workspace_id": imported["id"],
            "source_name": "2sigma_Dec23.json",
            "workspace_name": "Imported 2sigma Dec23",
        })
        self.assertEqual(applied.status_code, 201, applied.get_json())
        self.assertEqual(applied.get_json()["imported_workspace_id"], imported["id"])
        self.assertEqual(applied.get_json()["import"]["imported_workspace_id"], imported["id"])
        self.assertNotIn("project", applied.get_json())
        self.assertEqual(applied.get_json()["undo_depth"], 1)
        after = self.client.get("/api/project").get_json()
        self.assertEqual(len(after["workspaces"]), len(before["workspaces"]) + 1)
        self.assertTrue(before_workspace_ids.issubset({item["id"] for item in after["workspaces"]}))

        exported = self.client.get("/api/project/export").get_json()
        round_trip = self.client.post("/api/project/import/preview", json=exported)
        self.assertEqual(round_trip.status_code, 200, round_trip.get_json())
        round_project = round_trip.get_json()["project"]
        round_workspace = next(item for item in round_project["workspaces"] if item["id"] == imported["id"])
        self.assertEqual(len(round_workspace["classes"]), 2013)
        self.assertEqual(len([item for item in round_project["manual_periodicity_rules"] if item["workspace_id"] == imported["id"]]), 2)

        self.assertEqual(self.client.post("/api/history/undo").status_code, 200)
        self.assertEqual(
            {item["id"] for item in self.client.get("/api/project").get_json()["workspaces"]},
            before_workspace_ids,
        )

    def test_real_dec30_uses_compact_apply_below_vercel_payload_limit(self):
        if not DEC30_FIXTURE.exists():
            self.skipTest(f"Optional local integration fixture is unavailable: {DEC30_FIXTURE}")
        legacy = json.loads(DEC30_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(
            (len(legacy["generators"]), len(legacy["connections"]), len(legacy["periodicityRules"])),
            (2096, 2780, 1),
        )
        preview_response = self.client.post(
            "/api/project/import/preview?source_name=2sigma_Dec30.json",
            json=legacy,
        )
        self.assertEqual(preview_response.status_code, 200, preview_response.get_json())
        preview = preview_response.get_json()
        summary = preview["import"]["legacy_summary"]
        self.assertEqual(
            (summary["classes_created"], summary["relations_created"], summary["differentials_created"], summary["differential_anomalies"]),
            (2096, 1830, 948, 2),
        )
        compact_bytes = len(json.dumps({
            "legacy_canvas": legacy,
            "preview_sha256": preview["preview_sha256"],
            "expected_revision": preview["current_revision"],
            "imported_workspace_id": preview["imported_workspace_id"],
            "source_name": "2sigma_Dec30.json",
            "workspace_name": preview["import"]["workspace_name"],
        }, separators=(",", ":")).encode("utf-8"))
        old_project_bytes = len(json.dumps({
            "project": preview["project"],
            "preview_sha256": preview["preview_sha256"],
            "expected_revision": preview["current_revision"],
            "imported_workspace_id": preview["imported_workspace_id"],
        }, separators=(",", ":")).encode("utf-8"))
        self.assertLess(compact_bytes, 4_500_000)
        self.assertGreater(old_project_bytes, 4_500_000)
        self.assertLess(compact_bytes, old_project_bytes / 4)

        applied = self.client.post("/api/project/import/apply", json={
            "legacy_canvas": legacy,
            "preview_sha256": preview["preview_sha256"],
            "expected_revision": preview["current_revision"],
            "imported_workspace_id": preview["imported_workspace_id"],
            "source_name": "2sigma_Dec30.json",
            "workspace_name": preview["import"]["workspace_name"],
        })
        self.assertEqual(applied.status_code, 201, applied.get_json())
        self.assertNotIn("project", applied.get_json())
        self.assertEqual(applied.get_json()["imported_workspace_id"], preview["imported_workspace_id"])

    def test_self_contained_legacy_preview_apply_undo_and_round_trip(self):
        legacy = {
            "generators": [
                {"id": "g-source", "p": 1, "q": 0, "name": "x", "xOffset": 0, "yOffset": 0, "isBaseGenerator": True, "page": 2},
                {"id": "g-target", "p": 0, "q": 2, "name": "y", "xOffset": 0, "yOffset": 0, "isBaseGenerator": True, "page": 2},
                {"id": "g-same-cell", "p": 0, "q": 2, "name": "z", "xOffset": 0, "yOffset": 0.2, "isBaseGenerator": True, "page": 2},
            ],
            "connections": [
                {"id": "c-d2", "fromId": "g-source", "toId": "g-target", "type": "differential", "isPeriodic": False, "page": 2},
                {"id": "c-relation", "fromId": "g-target", "toId": "g-same-cell", "type": "relation", "isPeriodic": True, "page": 2},
            ],
            "periodicityRules": [
                {"id": "r-P", "name": "P", "p": 4, "q": 0},
            ],
        }
        before = self.client.get("/api/project").get_json()
        before_ids = {item["id"] for item in before["workspaces"]}
        preview_response = self.client.post(
            "/api/project/import/preview?source_name=small-fixture.json&workspace_name=Small%20legacy%20fixture",
            json=legacy,
        )
        self.assertEqual(preview_response.status_code, 200, preview_response.get_json())
        preview = preview_response.get_json()
        imported_id = preview["imported_workspace_id"]
        self.assertEqual(imported_id, preview["import"]["imported_workspace_id"])
        self.assertEqual(preview["import"]["legacy_summary"], {
            "generators_received": 3,
            "classes_created": 3,
            "connections_received": 2,
            "connection_propositions_created": 2,
            "relations_created": 1,
            "differentials_created": 1,
            "differential_anomalies": 0,
            "periodic_visual_connections": 1,
            "periodicity_rules_received": 1,
            "manual_periodicity_rules_created": 1,
        })
        imported = next(item for item in preview["project"]["workspaces"] if item["id"] == imported_id)
        self.assertEqual((len(imported["classes"]), len(imported["differentials"]), len(imported["propositions"])), (3, 1, 5))
        same_cell = [item for item in imported["classes"] if item["grade"]["stem"] == 0 and item["grade"]["filtration"] == 2]
        self.assertEqual(len(same_cell), 2)
        self.assertEqual({item["style"]["legacy_y_offset"] for item in same_cell}, {0.0, 0.2})
        self.assertEqual(self.client.get("/api/history").get_json()["undo_depth"], 0)

        missing_id = self.client.post("/api/project/import/apply", json={
            "legacy_canvas": legacy,
            "preview_sha256": preview["preview_sha256"],
            "expected_revision": preview["current_revision"],
            "imported_workspace_id": "not-in-reviewed-project",
            "source_name": "small-fixture.json",
            "workspace_name": "Small legacy fixture",
        })
        self.assertEqual(missing_id.status_code, 422)
        self.assertEqual(self.client.get("/api/history").get_json()["undo_depth"], 0)

        applied = self.client.post("/api/project/import/apply", json={
            "legacy_canvas": legacy,
            "preview_sha256": preview["preview_sha256"],
            "expected_revision": preview["current_revision"],
            "imported_workspace_id": imported_id,
            "source_name": "small-fixture.json",
            "workspace_name": "Small legacy fixture",
        })
        self.assertEqual(applied.status_code, 201, applied.get_json())
        self.assertEqual(applied.get_json()["imported_workspace_id"], imported_id)
        self.assertEqual(applied.get_json()["import"]["imported_workspace_id"], imported_id)
        self.assertNotIn("project", applied.get_json())
        self.assertEqual(applied.get_json()["undo_depth"], 1)
        after_apply = self.client.get("/api/project").get_json()
        self.assertTrue(before_ids.issubset({item["id"] for item in after_apply["workspaces"]}))

        exported = self.client.get("/api/project/export").get_json()
        round_trip = self.client.post("/api/project/import/preview", json=exported)
        self.assertEqual(round_trip.status_code, 200, round_trip.get_json())
        round_workspace = next(item for item in round_trip.get_json()["project"]["workspaces"] if item["id"] == imported_id)
        self.assertEqual(len(round_workspace["classes"]), 3)
        self.assertEqual(len([item for item in round_trip.get_json()["project"]["manual_periodicity_rules"] if item["workspace_id"] == imported_id]), 1)

        self.assertEqual(self.client.post("/api/history/undo").status_code, 200)
        self.assertEqual(
            {item["id"] for item in self.client.get("/api/project").get_json()["workspaces"]},
            before_ids,
        )

    def test_current_page_import_preserves_workspace_and_lossy_export_uses_dots(self):
        legacy = {
            "generators": [
                {"id": "legacy-x", "p": 4, "q": 0, "name": "D", "xOffset": 0, "yOffset": 0, "isBaseGenerator": True},
                {"id": "legacy-2x", "p": 4, "q": 0, "name": "2D", "xOffset": 0, "yOffset": 0.2, "isBaseGenerator": True},
            ],
            "connections": [
                {"id": "times-two", "fromId": "legacy-x", "toId": "legacy-2x", "type": "relation", "isPeriodic": False},
            ],
            "periodicityRules": [],
        }
        before = self.client.get("/api/project").get_json()
        before_ids = [item["id"] for item in before["workspaces"]]
        preview_response = self.client.post(
            "/api/project/import/preview?source_name=current.json&target_workspace_id=ws_integer&target_page=5",
            json=legacy,
        )
        self.assertEqual(preview_response.status_code, 200, preview_response.get_json())
        preview = preview_response.get_json()
        self.assertEqual(preview["import"]["operation"], "merge-current-page")
        self.assertEqual(preview["import"]["workspace_id"], "ws_integer")
        self.assertEqual(preview["import"]["target_page"], 5)
        self.assertEqual([item["id"] for item in preview["project"]["workspaces"]], before_ids)
        target = next(item for item in preview["project"]["workspaces"] if item["id"] == "ws_integer")
        imported = [item for item in target["classes"] if item["style"].get("legacy_import")]
        self.assertEqual([item["page"] for item in imported], [5, 5])

        applied = self.client.post("/api/project/import/apply", json={
            "legacy_canvas": legacy,
            "preview_sha256": preview["preview_sha256"],
            "expected_revision": preview["current_revision"],
            "imported_workspace_id": "ws_integer",
            "source_name": "current.json",
            "target_workspace_id": "ws_integer",
            "target_page": 5,
        })
        self.assertEqual(applied.status_code, 201, applied.get_json())
        after = self.client.get("/api/project").get_json()
        self.assertEqual([item["id"] for item in after["workspaces"]], before_ids)

        exported_response = self.client.get("/api/workspaces/ws_integer/legacy-export?page=5")
        self.assertEqual(exported_response.status_code, 200, exported_response.get_json())
        self.assertIn("forgotten as ordinary legacy dots", exported_response.headers["X-HFPSS-Lossy-Export"])
        exported = exported_response.get_json()
        self.assertEqual({item["name"] for item in exported["generators"] if item["name"] in {"D", "2D"}}, {"D", "2D"})
        self.assertTrue(all(item["page"] == 5 for item in exported["generators"]))
        self.assertNotIn("style", exported["generators"][0])


if __name__ == "__main__":
    unittest.main()
