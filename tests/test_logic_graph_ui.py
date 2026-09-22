import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import app as app_module
from app import app
from domain.logic_graph import build_logic_graph, validate_logic_graph
from domain.migrations import migrate_project
from domain.models import Project, Proposition, Workspace
from domain.seed import demo_project


class LogicGraphTest(unittest.TestCase):
    def test_required_premises_cannot_be_erased_or_malformed_in_review_graph(self):
        leaf = Proposition("leaf", "manual", "verified leaf", status="verified")
        claim = Proposition("dependent", "differential", "derived map", status="verified",
                            premise_ids=["leaf"], conclusion={"required_admitted_premises": True})
        legacy = Proposition("legacy", "manual", "independent fact", status="verified")
        project = Project("proof-gate", "proof gate", [Workspace("ws", "ws", propositions=[leaf, claim, legacy])])
        for premises in ([], None, "leaf", [None], [[]], [""]):
            with self.subTest(premises=premises):
                claim.premise_ids = premises
                graph = build_logic_graph(project)
                nodes = {node["record_id"]: node for node in graph["nodes"] if node["kind"] == "proposition"}
                self.assertFalse(nodes["dependent"]["admitted"])
                self.assertIn("premises:invalid-or-required", nodes["dependent"]["blocked_by"])
                self.assertTrue(nodes["legacy"]["admitted"])
        claim.premise_ids = ["leaf"]
        restored = next(node for node in build_logic_graph(project)["nodes"] if node.get("record_id") == "dependent")
        self.assertTrue(restored["admitted"])

    def test_graph_has_typed_nodes_and_evidence_edges(self):
        graph = build_logic_graph(migrate_project(demo_project()))
        self.assertEqual(validate_logic_graph(graph), [])
        node_kinds = {item["kind"] for item in graph["nodes"]}
        edge_kinds = {item["kind"] for item in graph["edges"]}

        self.assertTrue({"proposition", "coefficient-context", "differential-claim", "differential-event", "class-fate", "period-family", "grading-sector", "c3-action"}.issubset(node_kinds))
        self.assertTrue({"asserts", "updates", "certifies", "belongs-to", "tracks-orbit", "requires-coefficients"}.issubset(edge_kinds))
        self.assertEqual(len(graph["nodes"]), len({item["id"] for item in graph["nodes"]}))
        self.assertGreater(graph["admission"]["admitted"], 0)
        self.assertGreater(graph["admission"]["review_queue"], 0)

    def test_dkllw_f4_audit_is_an_admitted_dependency_chain(self):
        graph = build_logic_graph(migrate_project(demo_project()))
        nodes = {item["id"]: item for item in graph["nodes"]}
        conclusion = nodes["proposition:prop_dkllw_f4_audit_conclusion"]

        self.assertTrue(conclusion["admitted"])
        self.assertGreaterEqual(conclusion["dependency_depth"], 3)
        self.assertEqual(conclusion["conclusion"]["verdict"], "qualified-yes")
        self.assertIn("q8-witt-f4", conclusion["coefficient_context_ids"])
        self.assertIn(
            {
                "source": "proposition:prop_dkllw_unit_ambiguity",
                "target": "proposition:prop_dkllw_f4_audit_conclusion",
                "kind": "uses",
            },
            graph["edges"],
        )

    def test_dkllw_fact_chain_exposes_types_implications_and_period_identity(self):
        graph = build_logic_graph(migrate_project(demo_project()))
        nodes = {item["id"]: item for item in graph["nodes"]}
        chain = [item for ident, item in nodes.items() if ident.startswith("proposition:prop_chain_")]
        period = nodes["proposition:prop_chain_q8_D8_pc"]
        bss = nodes["proposition:prop_chain_2bss_int_survivors"]

        self.assertGreaterEqual(len(chain), 40)
        self.assertTrue(all(item["admitted"] for item in chain))
        self.assertEqual(period["conclusion"]["datum_type"], "permanent-cycle")
        self.assertIn("D^(8n)", period["conclusion"]["period_identity"])
        self.assertEqual(bss["conclusion"]["role"], "HFPSS-E2-input")
        self.assertIn("prop_chain_q8_hurewicz_pc", bss["implies_ids"])
        self.assertIn(
            {
                "source": "proposition:prop_chain_q8_D8_pc",
                "target": "period-family:period_integer_D8",
                "kind": "belongs-to-period",
            },
            graph["edges"],
        )

    def test_unverified_or_cyclic_claims_do_not_enter_the_fact_dag(self):
        project = migrate_project(demo_project())
        propositions = {item.id: item for workspace in project.workspaces for item in workspace.propositions}
        self.assertFalse(
            next(
                item for item in build_logic_graph(project)["nodes"]
                if item["id"] == "proposition:prop_two_d3_u"
            )["admitted"]
        )

        propositions["prop_int_d5_D"].premise_ids = ["prop_int_d5_D2"]
        propositions["prop_int_d5_D2"].premise_ids = ["prop_int_d5_D"]
        errors = validate_logic_graph(build_logic_graph(project))
        self.assertIn("Proposition dependencies must form a directed acyclic graph.", errors)

    def test_differential_proposition_asserts_its_claim(self):
        graph = build_logic_graph(migrate_project(demo_project()))
        self.assertIn(
            {
                "source": "proposition:prop_two_d3_u",
                "target": "differential:diff_two_d3_u",
                "kind": "asserts",
            },
            graph["edges"],
        )


class V2ApiAndUiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.data_dir = TemporaryDirectory()
        self.old_data_path = app_module.DATA_PATH
        app_module.DATA_PATH = Path(self.data_dir.name) / "project.json"

    def tearDown(self):
        app_module.DATA_PATH = self.old_data_path
        self.data_dir.cleanup()

    def test_v2_graph_fate_and_period_endpoints(self):
        graph = self.client.get("/api/v2/logic-graph")
        self.assertEqual(graph.status_code, 200)
        self.assertTrue(graph.get_json()["nodes"])
        periods = self.client.get("/api/v2/period-families")
        self.assertEqual(periods.status_code, 200)
        self.assertTrue(periods.get_json()["period_families"])
        fates = self.client.get("/api/v2/workspaces/ws_2sigma_i/fates")
        self.assertEqual(fates.status_code, 200)
        self.assertTrue(fates.get_json()["events"])

    def test_tex_exports_are_deterministic_and_keep_review_statuses(self):
        chart = self.client.get("/api/v2/render/workspaces/ws_3sigma_i/chart.tex?page=9")
        self.assertEqual(chart.status_code, 200)
        self.assertEqual(chart.mimetype, "application/x-tex")
        self.assertIn(b"Generated by HFPSS Studio", chart.data)
        self.assertIn(b"review differential", chart.data)
        self.assertIn(b'"proposition_id"', chart.data)
        self.assertIn(b"custom_tikz_template=", chart.data)
        self.assertIn(b"d9/.style", chart.data)
        self.assertNotIn(b"spectralsequences", chart.data)

        article = self.client.get("/api/v2/render/workspaces/ws_3sigma_i/article.tex?page=9")
        self.assertEqual(article.status_code, 200)
        self.assertIn(b"Differential register", article.data)
        self.assertIn(b"under-review", article.data)
        self.assertIn(b"Proof appendix", article.data)

        invalid = self.client.get("/api/v2/render/workspaces/ws_3sigma_i/unknown.tex")
        self.assertEqual(invalid.status_code, 404)

    def test_frontend_exposes_atlas_fate_graph_and_product_workflows(self):
        markup = (ROOT / "backend" / "templates" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "backend" / "static" / "app.js").read_text(encoding="utf-8")

        for ident in ("grading-atlas", "fate-inspector", "logic-graph", "proof-admission", "product-form", "product-preview"):
            self.assertIn(f'id="{ident}"', markup)
        self.assertIn("first_hfpss_death", script)
        self.assertIn("tate_only_negative_source", script)
        self.assertIn("function renderGradingAtlas", script)
        self.assertIn("function renderFateInspector", script)
        self.assertIn("function renderLogicGraph", script)
        self.assertIn("Admitted facts", markup)
        self.assertIn("dependency_depth", script)
        self.assertIn("implies_ids", script)
        self.assertIn("period_identity", script)
        self.assertIn("/api/v2/products/preview", script)
        self.assertIn("usablePeriodFamily", script)
        self.assertNotIn(".filter((item) => item.page < page)\n      .flatMap", script)
        self.assertIn("proof history retained", script)
        self.assertIn('id="export-chart"', markup)
        self.assertIn('id="export-article"', markup)
        self.assertIn("function downloadTex", script)

    def test_javascript_is_syntactically_valid_when_node_is_available(self):
        try:
            completed = subprocess.run(
                ["node", "--check", str(ROOT / "backend" / "static" / "app.js")],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except FileNotFoundError:
            self.skipTest("Node.js is not installed in this environment.")
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
