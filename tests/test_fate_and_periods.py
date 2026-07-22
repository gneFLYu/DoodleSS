import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as app_module
from app import app
from domain.fate import sync_workspace_fates
from domain.migrations import migrate_project
from domain.models import (
    ClassNode,
    Differential,
    DifferentialEvent,
    Grade,
    Project,
    Proposition,
    Workspace,
)
from domain.periods import validate_period_family
from domain.seed import demo_project


def fate_map(workspace):
    return {item.class_id: item for item in workspace.fates}


class FateDerivationTest(unittest.TestCase):
    def workspace_with_differential(self, status="derived"):
        workspace = Workspace(id="w", name="HFPSS", spectral_sequence="hfpss")
        workspace.classes = [
            ClassNode("source", "x", Grade(5, 0)),
            ClassNode("target", "y", Grade(4, 3)),
        ]
        workspace.propositions = [
            Proposition(
                id="claim",
                kind="differential",
                statement="d_3(x)=y",
                status=status,
                conclusion={"source_id": "source", "target_id": "target", "page": 3},
                source_ref="notes.tex:12",
                source_refs=["notes.tex:12"],
            )
        ]
        workspace.differentials = [
            Differential("diff", "source", "target", 3, status=status, proposition_id="claim")
        ]
        return workspace

    def test_accepted_hfpss_differential_kills_both_endpoints_on_next_page(self):
        workspace = self.workspace_with_differential("derived")
        sync_workspace_fates(workspace)
        fates = fate_map(workspace)

        self.assertEqual(fates["source"].conclusion, "supports_differential")
        self.assertEqual(fates["target"].conclusion, "is_hit")
        self.assertEqual(fates["source"].last_hfpss_live_page, 3)
        self.assertEqual(fates["target"].first_hfpss_death["page"], 3)
        self.assertEqual(len(workspace.differential_events), 2)

    def test_under_review_arrow_is_visible_but_does_not_determine_fate(self):
        workspace = self.workspace_with_differential("under-review")
        sync_workspace_fates(workspace)
        fates = fate_map(workspace)

        self.assertEqual(fates["source"].conclusion, "unresolved")
        self.assertEqual(fates["target"].conclusion, "unresolved")
        self.assertEqual(fates["source"].hfpss_outgoing_events, ["event_diff_supports"])
        self.assertIsNone(fates["target"].first_hfpss_death)

    def test_negative_source_tate_hit_stays_out_of_hfpss_incoming_events(self):
        workspace = Workspace(id="w", name="HFPSS", spectral_sequence="hfpss")
        workspace.classes = [ClassNode("x", "x", Grade(0, 0))]
        workspace.differential_events = [
            DifferentialEvent(
                id="tate-negative-hit",
                spectral_sequence="tate",
                page=5,
                role="receives",
                class_id="x",
                counterpart_class_id="negative-z",
                differential_claim_id="tate-diff",
                source_filtration=-4,
                target_filtration=0,
                source_exists_in_hfpss=False,
                comparison_status="tate_only_negative_source",
                proposition_id="tate-prop",
                source_refs=["Tate comparison proposition"],
                status="established",
            )
        ]
        sync_workspace_fates(workspace)
        fate = workspace.fates[0]

        self.assertEqual(fate.tate_incoming_events, ["tate-negative-hit"])
        self.assertEqual(fate.hfpss_incoming_events, [])
        self.assertEqual(fate.conclusion, "unresolved")
        self.assertIsNone(fate.first_hfpss_death)

    def test_legacy_permanent_badge_is_not_a_proof(self):
        workspace = Workspace(id="w", name="HFPSS")
        workspace.classes = [ClassNode("x", "x", Grade(), state="permanent")]
        sync_workspace_fates(workspace)
        self.assertEqual(workspace.fates[0].conclusion, "unresolved")

        workspace.propositions.append(
            Proposition(
                id="pc",
                kind="permanent-cycle",
                statement="x is permanent",
                status="established",
                conclusion={"class_id": "x"},
                source_ref="comparison theorem",
                source_refs=["comparison theorem"],
            )
        )
        sync_workspace_fates(workspace)
        self.assertEqual(workspace.fates[0].conclusion, "permanent_cycle")
        self.assertEqual(workspace.fates[0].last_hfpss_live_page, "infinity")


class PeriodMigrationTest(unittest.TestCase):
    def test_seed_differentials_are_linked_and_periods_are_auditable(self):
        project = migrate_project(demo_project())
        family_ids = {item.id for item in project.period_families}

        for workspace in project.workspaces:
            proposition_ids = {item.id for item in workspace.propositions}
            for differential in workspace.differentials:
                self.assertIn(differential.proposition_id, proposition_ids)
                if differential.period_stem or differential.period_filtration:
                    self.assertIn(differential.period_family_id, family_ids)
                    self.assertEqual(differential.anchor_differential_id, differential.id)
                    self.assertEqual(differential.period_translation, [0])
                    self.assertEqual(validate_period_family(project, differential), [])

        families_before = len(project.period_families)
        propositions_before = sum(len(item.propositions) for item in project.workspaces)
        migrate_project(project)
        self.assertEqual(len(project.period_families), families_before)
        self.assertEqual(sum(len(item.propositions) for item in project.workspaces), propositions_before)

    def test_migrated_period_certificate_remains_under_review(self):
        project = migrate_project(demo_project())
        workspace = next(item for item in project.workspaces if item.id == "ws_2sigma_i")
        differential = next(item for item in workspace.differentials if item.id == "diff_two_d3_u")
        family = next(item for item in project.period_families if item.id == differential.period_family_id)
        certificate = next(item for item in workspace.propositions if item.id == family.certificate_proposition_id)

        self.assertEqual(family.status, "under-review")
        self.assertEqual(certificate.status, "under-review")
        self.assertIn("require review", certificate.statement)
        self.assertTrue(certificate.source_refs)


class LifecycleApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.data_dir = TemporaryDirectory()
        self.old_data_path = app_module.DATA_PATH
        app_module.DATA_PATH = Path(self.data_dir.name) / "project.json"

    def tearDown(self):
        app_module.DATA_PATH = self.old_data_path
        self.data_dir.cleanup()

    def test_new_differential_is_linked_validated_and_updates_fate(self):
        workspace = self.client.post("/api/workspaces", json={"name": "Claims"}).get_json()["workspace"]
        source = self.client.post(
            f"/api/workspaces/{workspace['id']}/classes",
            json={"label": "x", "stem": 5, "filtration": 0},
        ).get_json()["class"]
        target = self.client.post(
            f"/api/workspaces/{workspace['id']}/classes",
            json={"label": "y", "stem": 4, "filtration": 3},
        ).get_json()["class"]

        response = self.client.post(
            f"/api/workspaces/{workspace['id']}/differentials",
            json={
                "source_id": source["id"],
                "target_id": target["id"],
                "page": 3,
                "status": "derived",
                "source_ref": "notes.tex:20",
            },
        )
        self.assertEqual(response.status_code, 201)
        differential = response.get_json()["differential"]
        self.assertTrue(differential["proposition_id"])

        saved = self.client.get("/api/project").get_json()
        saved_workspace = next(item for item in saved["workspaces"] if item["id"] == workspace["id"])
        fates = {item["class_id"]: item for item in saved_workspace["fates"]}
        self.assertEqual(fates[source["id"]]["conclusion"], "supports_differential")
        self.assertEqual(fates[target["id"]]["conclusion"], "is_hit")

    def test_invalid_bidegree_is_rejected(self):
        workspace = self.client.post("/api/workspaces", json={"name": "Claims"}).get_json()["workspace"]
        source = self.client.post(f"/api/workspaces/{workspace['id']}/classes", json={"label": "x", "stem": 5, "filtration": 0}).get_json()["class"]
        target = self.client.post(f"/api/workspaces/{workspace['id']}/classes", json={"label": "bad", "stem": 5, "filtration": 3}).get_json()["class"]
        response = self.client.post(
            f"/api/workspaces/{workspace['id']}/differentials",
            json={"source_id": source["id"], "target_id": target["id"], "page": 3},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("must shift", response.get_json()["error"])

    def test_tate_workspace_accepts_negative_filtration(self):
        workspace = self.client.post(
            "/api/workspaces",
            json={"name": "Tate", "spectral_sequence": "tate"},
        ).get_json()["workspace"]
        response = self.client.post(
            f"/api/workspaces/{workspace['id']}/classes",
            json={"label": "z", "stem": 0, "filtration": -3},
        )
        self.assertEqual(response.status_code, 201)

    def test_archiving_a_class_preserves_claim_history(self):
        project = self.client.get("/api/project").get_json()
        workspace = next(item for item in project["workspaces"] if item["id"] == "ws_integer")
        differential_ids = {item["id"] for item in workspace["differentials"]}
        proposition_ids = {item["id"] for item in workspace["propositions"]}

        response = self.client.delete("/api/workspaces/ws_integer/classes/int_D")
        self.assertEqual(response.status_code, 200)
        updated = self.client.get("/api/project").get_json()
        updated_workspace = next(item for item in updated["workspaces"] if item["id"] == "ws_integer")
        archived = next(item for item in updated_workspace["classes"] if item["id"] == "int_D")
        self.assertTrue(archived["archived"])
        self.assertTrue(differential_ids.issubset({item["id"] for item in updated_workspace["differentials"]}))
        self.assertTrue(proposition_ids.issubset({item["id"] for item in updated_workspace["propositions"]}))


if __name__ == "__main__":
    unittest.main()
