import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import app


class PageModeTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_researching_page_has_tabs_cell_tools_and_no_logic_graph(self):
        response = self.client.get("/")
        markup = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('aria-label="Studio mode"', markup)
        self.assertIn('aria-current="page">Researching', markup)
        self.assertIn('id="chart"', markup)
        self.assertIn('id="cell-inspector"', markup)
        self.assertIn('id="matrix-dialog"', markup)
        self.assertNotIn('class="tool toolbar-tool" title="Add a matrix differential"', markup)
        self.assertIn('Advanced matrix editor', markup)
        self.assertEqual(markup.count('id="legacy-catalog-select"'), 1)
        self.assertNotIn('id="logic-graph"', markup)

    def test_review_page_is_dedicated_to_fact_graph(self):
        response = self.client.get("/review")
        markup = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('aria-current="page">Reviewing', markup)
        self.assertIn('id="logic-graph"', markup)
        self.assertIn('id="proof-tree"', markup)
        self.assertIn('id="logic-node-detail"', markup)
        self.assertIn('id="periodic-fate-audit"', markup)
        self.assertIn('id="periodic-fate-obligations"', markup)
        self.assertNotIn('id="chart"', markup)
        self.assertNotIn('aria-label="Chart controls"', markup)


if __name__ == "__main__":
    unittest.main()
