"""Flask API integration for explicit DKLLW glyph and multiplication semantics."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import app as app_module
from app import app
from domain.history import clear_history


class DKLLWApiTest(unittest.TestCase):
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

    def test_explicit_glyph_and_same_cell_two_multiplication_round_trip(self):
        created_ids = []
        for label, glyph in (("a", "dot"), ("2a", "square")):
            response = self.client.post(
                "/api/workspaces/ws_integer/classes",
                json={
                    "label": label,
                    "stem": 30,
                    "filtration": 0,
                    "page": 4,
                    "glyph": glyph,
                },
            )
            self.assertEqual(response.status_code, 201, response.get_json())
            created_ids.append(response.get_json()["class"]["id"])
            self.assertEqual(
                response.get_json()["class"]["style"]["module_pattern"],
                glyph,
            )

        relation = self.client.post(
            "/api/workspaces/ws_integer/propositions",
            json={
                "kind": "relation",
                "statement": "2 multiplication: a to 2a",
                "status": "candidate",
                "conclusion": {
                    "source_id": created_ids[0],
                    "target_id": created_ids[1],
                    "page": 4,
                },
                "chart_connection_kind": "vertical-two",
                "source_ref": "Explicit local claim for review.",
            },
        )
        self.assertEqual(relation.status_code, 201, relation.get_json())
        semantic = relation.get_json()["proposition"]["conclusion"]["chart_connection"]
        self.assertEqual(semantic["kind"], "vertical-two")
        self.assertEqual(semantic["multiplier"], "2")
        self.assertEqual(semantic["target_shift"], {
            "stem": 0,
            "filtration": 0,
            "representation": {},
        })

    def test_specific_multiplication_requires_a_source_locator(self):
        response = self.client.post(
            "/api/workspaces/ws_integer/propositions",
            json={
                "kind": "relation",
                "statement": "uncited h1 multiplication",
                "conclusion": {
                    "source_id": "e2_integer_h1",
                    "target_id": "e2_integer_xh1",
                    "page": 2,
                },
                "chart_connection_kind": "h1",
                "source_ref": "",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("source locator", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
