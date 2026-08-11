import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import app


class PageModeTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_computation_page_has_tabs_and_no_logic_graph(self):
        response = self.client.get("/")
        markup = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('aria-label="Studio mode"', markup)
        self.assertIn('aria-current="page">Computation', markup)
        self.assertIn('id="chart"', markup)
        self.assertNotIn('id="logic-graph"', markup)

    def test_review_page_is_dedicated_to_fact_graph(self):
        response = self.client.get("/review")
        markup = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('aria-current="page">Review', markup)
        self.assertIn('id="logic-graph"', markup)
        self.assertIn('id="proof-tree"', markup)
        self.assertIn('id="logic-node-detail"', markup)
        self.assertNotIn('id="chart"', markup)
        self.assertNotIn('aria-label="Chart controls"', markup)


if __name__ == "__main__":
    unittest.main()
