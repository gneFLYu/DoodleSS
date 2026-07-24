"""API contract for compact, page-aware period cycles."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import app as app_module
from app import app
from domain.history import clear_history


class PagePeriodicityApiTest(unittest.TestCase):
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

    def test_register_and_plan_are_compact_and_page_specific(self):
        before = self.client.get("/api/project").get_json()
        integer = next(item for item in before["workspaces"] if item["id"] == "ws_integer")
        class_count = len(integer["classes"])

        preview = self.client.post(
            "/api/v2/workspaces/ws_integer/page-periods/preview",
            json={
                "page": 2,
                "cycle_class_id": "int_D",
                "label": "D",
                "basis": "Integer-page D-periodicity.",
                "source_ref": "DKLLW24 Section 6.1.2.",
                "status": "candidate",
            },
        )
        self.assertEqual(preview.status_code, 200, preview.get_json())
        self.assertTrue(preview.get_json()["virtual"])
        self.assertEqual(preview.get_json()["created_class_ids"], [])

        created = self.client.post(
            "/api/v2/workspaces/ws_integer/page-periods",
            json={
                "id": "integer-D-page-period",
                "page": 2,
                "cycle_class_id": "int_D",
                "label": "D",
                "basis": "Integer-page D-periodicity.",
                "source_ref": "DKLLW24 Section 6.1.2.",
                "status": "candidate",
            },
        )
        self.assertEqual(created.status_code, 201, created.get_json())
        after = self.client.get("/api/project").get_json()
        after_integer = next(item for item in after["workspaces"] if item["id"] == "ws_integer")
        self.assertEqual(len(after_integer["classes"]), class_count)
        self.assertEqual(
            [item["id"] for item in after["page_period_cycles"]],
            ["integer-D-page-period"],
        )

        plan = self.client.post(
            "/api/v2/workspaces/ws_integer/page-periods/integer-D-page-period/instances",
            json={
                "page": 2,
                "base_class_ids": ["e2_integer_h1"],
                "translations": [1, 2],
            },
        )
        self.assertEqual(plan.status_code, 200, plan.get_json())
        body = plan.get_json()
        self.assertFalse(body["persisted"])
        self.assertEqual(body["created_class_ids"], [])
        self.assertEqual(
            [item["label"] for item in body["instances"]],
            ["h_1D", "h_1D^{2}"],
        )
        final = self.client.get("/api/project").get_json()
        final_integer = next(item for item in final["workspaces"] if item["id"] == "ws_integer")
        self.assertEqual(len(final_integer["classes"]), class_count)


if __name__ == "__main__":
    unittest.main()
