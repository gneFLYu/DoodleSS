import unittest

from backend.domain.logic_graph import build_logic_graph, validate_logic_graph
from backend.domain.migrations import migrate_project
from backend.domain.seed import demo_project


class ReuFactChainTests(unittest.TestCase):
    def setUp(self):
        self.graph = build_logic_graph(migrate_project(demo_project()))
        self.nodes = {item["id"]: item for item in self.graph["nodes"]}

    def test_exact_d3_stays_blocked_by_thom_normalization(self):
        nonzero = self.nodes["proposition:prop_reu_d3_nonzero_line"]
        exact = self.nodes["proposition:prop_reu_d3_unit"]
        normalization = self.nodes["proposition:prop_reu_thom_normalization"]

        self.assertTrue(nonzero["admitted"])
        self.assertFalse(normalization["admitted"])
        self.assertFalse(exact["admitted"])
        self.assertIn("prop_reu_thom_normalization", exact["blocked_by"])

    def test_corrections_and_period_snf_are_visible(self):
        guard = self.nodes["proposition:prop_reu_mixed_sector_guard"]
        quotient = self.nodes["proposition:prop_reu_period_quotient"]
        stale = self.nodes["proposition:prop_reu_bad_period_exercise"]

        self.assertTrue(guard["admitted"])
        self.assertTrue(quotient["admitted"])
        self.assertEqual(quotient["conclusion"]["quotient_invariants"], [64, 4, 4, 2])
        self.assertFalse(stale["admitted"])
        self.assertEqual(validate_logic_graph(self.graph), [])


if __name__ == "__main__":
    unittest.main()
