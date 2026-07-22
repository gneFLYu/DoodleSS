import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as app_module
from app import app
from domain.candidate_enumeration import (
    enumerate_comparison_transport_candidates,
    enumerate_differential_candidates,
)
from domain.models import ClassNode, Comparison, Differential, Grade, Project, Proposition, Workspace


class DifferentialCandidateEnumerationTest(unittest.TestCase):
    def test_direct_candidates_are_bidegree_representation_and_liveness_filtered(self):
        source = ClassNode("source", "a", Grade(5, 1, {"sigma_i": -3}))
        compatible = ClassNode("compatible", "b", Grade(4, 5, {"sigma_i": -3}))
        wrong_representation = ClassNode("wrong-rep", "c", Grade(4, 5, {"sigma_i": -2}))
        wrong_page = ClassNode("late", "d", Grade(4, 5, {"sigma_i": -3}), page=5)
        workspace = Workspace(
            id="target", name="Target", classes=[source, compatible, wrong_representation, wrong_page],
        )

        candidates = enumerate_differential_candidates(workspace, source.id, 4)

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate.status, "candidate")
        self.assertEqual(candidate.rule, "BidegreeAndLiveness")
        self.assertEqual(candidate.conclusion["target_id"], compatible.id)
        self.assertEqual(workspace.differentials, [])
        self.assertEqual(workspace.propositions, [])

    def test_comparison_candidates_require_an_accepted_source_arrow_and_existing_endpoints(self):
        source_from = ClassNode("source-from", "a", Grade(5, 1, {"sigma_i": 1}))
        source_to = ClassNode("source-to", "b", Grade(4, 4, {"sigma_i": 1}))
        source_workspace = Workspace(
            id="source-ws", name="Source", classes=[source_from, source_to],
            differentials=[Differential("source-diff", source_from.id, source_to.id, 3, status="derived", proposition_id="source-prop")],
            propositions=[Proposition(
                id="source-prop", kind="differential", statement="d_3(a)=b", status="derived",
                conclusion={"source_id": source_from.id, "target_id": source_to.id, "page": 3},
                source_ref="Source theorem 4.2", source_refs=["Source theorem 4.2"],
            )],
        )
        target_from = ClassNode("target-from", "Ta", Grade(9, 1, {"sigma_i": 1, "H": -1}))
        target_to = ClassNode("target-to", "Tb", Grade(8, 4, {"sigma_i": 1, "H": -1}))
        target_workspace = Workspace(id="target-ws", name="Target", classes=[target_from, target_to])
        comparison = Comparison(
            id="comparison", source_workspace_id="source-ws", target_workspace_id="target-ws",
            name="Shift", mode="restriction", grade_shift=Grade(4, 0, {"H": -1}), source_ref="Map construction 2.1",
        )
        project = Project(id="project", name="Project", workspaces=[source_workspace, target_workspace], comparisons=[comparison])

        candidates = enumerate_comparison_transport_candidates(
            project, target_workspace, target_from.id, 3, comparison.id,
        )

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertEqual(candidate.status, "candidate")
        self.assertEqual(candidate.rule, "ComparisonTransportCandidate")
        self.assertEqual(candidate.conclusion["target_id"], target_to.id)
        self.assertEqual(candidate.premise_ids, ["source-prop"])
        self.assertIn("Map construction 2.1", candidate.source_refs)
        self.assertIn("Source theorem 4.2", candidate.source_refs)
        self.assertTrue(any("Comparison 'comparison'" in item for item in candidate.hypotheses))
        self.assertEqual(target_workspace.differentials, [])
        self.assertEqual(target_workspace.propositions, [])


class DifferentialCandidateApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.data_dir = TemporaryDirectory()
        self.old_data_path = app_module.DATA_PATH
        app_module.DATA_PATH = Path(self.data_dir.name) / "project.json"

    def tearDown(self):
        app_module.DATA_PATH = self.old_data_path
        self.data_dir.cleanup()

    def test_endpoint_is_read_only_and_returns_only_compatible_candidates(self):
        workspace = self.client.post("/api/workspaces", json={"name": "Candidates"}).get_json()["workspace"]
        source = self.client.post(f"/api/workspaces/{workspace['id']}/classes", json={
            "label": "a", "stem": 5, "filtration": 1, "representation": {"sigma_i": -3},
        }).get_json()["class"]
        target = self.client.post(f"/api/workspaces/{workspace['id']}/classes", json={
            "label": "b", "stem": 4, "filtration": 5, "representation": {"sigma_i": -3},
        }).get_json()["class"]
        wrong = self.client.post(f"/api/workspaces/{workspace['id']}/classes", json={
            "label": "c", "stem": 4, "filtration": 5, "representation": {"sigma_i": -2},
        }).get_json()["class"]
        before = self.client.get("/api/project").get_json()
        revision_before = before["revision"]
        fates_before = next(item for item in before["workspaces"] if item["id"] == workspace["id"])["fates"]

        response = self.client.post(
            f"/api/v2/workspaces/{workspace['id']}/differential-candidates",
            json={"source_id": source["id"], "page": 4},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["persisted"])
        self.assertEqual([item["conclusion"]["target_id"] for item in data["candidates"]], [target["id"]])
        self.assertNotIn(wrong["id"], [item["conclusion"]["target_id"] for item in data["candidates"]])
        project_after = self.client.get("/api/project").get_json()
        self.assertEqual(project_after["revision"], revision_before)
        created_workspace = next(item for item in project_after["workspaces"] if item["id"] == workspace["id"])
        self.assertEqual(created_workspace["differentials"], [])
        self.assertEqual(created_workspace["propositions"], [])
        self.assertEqual(created_workspace["fates"], fates_before)
