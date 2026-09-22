import unittest
from copy import deepcopy
from dataclasses import asdict

from backend.domain.logic_graph import build_logic_graph, validate_logic_graph
from backend.domain.migrations import migrate_project
from backend.domain.seed import demo_project
from backend.domain.reu_fact_chain import ensure_reu_fact_chain


class ReuFactChainTests(unittest.TestCase):
    def setUp(self):
        self.project = migrate_project(demo_project())
        self.graph = build_logic_graph(self.project)
        self.nodes = {item["id"]: item for item in self.graph["nodes"]}

    def test_exact_d3_uses_the_chosen_pure_galois_normalization(self):
        nonzero = self.nodes["proposition:prop_reu_d3_nonzero_line"]
        exact = self.nodes["proposition:prop_reu_d3_unit"]
        normalization = self.nodes["proposition:prop_reu_thom_normalization"]

        self.assertTrue(nonzero["admitted"])
        self.assertTrue(normalization["admitted"])
        self.assertTrue(exact["admitted"])
        self.assertEqual(exact["blocked_by"], [])
        self.assertEqual(normalization["status"], "verified")
        scalar = exact["conclusion"]["coefficient_normalization"]
        self.assertEqual(scalar["id"], "pure-sigma-i-galois-fixed")
        self.assertEqual(scalar["value"], 1)
        self.assertTrue(scalar["preserves_witt_layers"])
        self.assertFalse(self.nodes["proposition:prop_reu_mixed_formulas_review"]["admitted"])

    def test_saved_normalization_refresh_preserves_research_additions(self):
        props = {p.id: p for w in self.project.workspaces for p in w.propositions}
        old_notes = {
            "prop_reu_thom_normalization": "Fixing the representation does not automatically fix a selected generator without a unit; this remains a review obligation.",
            "prop_reu_d3_unit": "The equation c=c^2 is valid, but the exact Thom normalization is not yet admitted.",
        }
        unrelated = props["prop_reu_mixed_formulas_review"]
        unrelated.notes = "Researcher-owned mixed-sector investigation"
        unrelated_before = deepcopy(asdict(unrelated))
        for ident, old_note in old_notes.items():
            prop = props[ident]
            prop.status = "under-review"
            prop.notes = old_note + "\n\nResearcher note: retain the Witt layer."
            prop.conclusion["researcher_coordinate"] = [25, 1]
            prop.source_ref = "researcher:private-locator"
            prop.source_refs.append("researcher:extra-source")
        ensure_reu_fact_chain(self.project)
        for ident, old_note in old_notes.items():
            prop = props[ident]
            self.assertEqual(prop.status, "verified")
            self.assertNotIn(old_note, prop.notes)
            self.assertIn("Researcher note: retain the Witt layer.", prop.notes)
            self.assertEqual(prop.conclusion["researcher_coordinate"], [25, 1])
            self.assertIn("researcher:private-locator", prop.source_refs)
            self.assertIn("researcher:extra-source", prop.source_refs)
        self.assertEqual(asdict(unrelated), unrelated_before)
        before = {ident: deepcopy(asdict(props[ident])) for ident in old_notes}
        ensure_reu_fact_chain(self.project)
        self.assertEqual(before, {ident: asdict(props[ident]) for ident in old_notes})
        graph = build_logic_graph(self.project)
        self.assertEqual(validate_logic_graph(graph), [])
        self.assertTrue(next(n for n in graph["nodes"] if n["id"] == "proposition:prop_reu_d3_unit")["admitted"])

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
