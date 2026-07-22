import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.e2_import import (
    materialize_verified_e2_records,
    review_legacy_e2_payload,
    verified_e2_classes,
    verified_e2_relations,
)
from domain.migrations import migrate_project
from domain.models import ClassNode, CrossGradedProduct, Differential, Grade, Project, Proposition, Workspace


class E2CatalogueTest(unittest.TestCase):
    def test_catalogue_is_explicitly_cited_and_d_localized(self):
        integer = verified_e2_classes("integer")
        sigma = verified_e2_classes("sigma_i")

        self.assertEqual(len(integer), 9)
        self.assertEqual(len(sigma), 4)
        self.assertEqual(next(item for item in integer if item.id == "e2_integer_D").stem, 8)
        shifted = next(item for item in sigma if item.id == "e2_sigma_xplusy_usigma_i")
        self.assertEqual((shifted.stem, shifted.filtration), (-1, 1))
        self.assertEqual(shifted.representation, {"sigma_i": -1})
        for item in (*integer, *sigma):
            self.assertIn("PDF p.", item.source_ref)
            self.assertIn("D-localized", item.scope)
            self.assertEqual(item.review_status, "source-verified")

    def test_relations_are_cited_propositions_not_automatic_rewrites(self):
        relations = verified_e2_relations()
        self.assertIn("Dy^2 = h_2^2", {item.expression for item in relations})
        self.assertIn("4v_1^2u_{\\sigma_i}k = 0", {item.expression for item in relations})
        self.assertTrue(all("PDF p." in item.source_ref for item in relations))


class LegacyReviewTest(unittest.TestCase):
    def test_only_explicit_e2_exact_matches_are_promoted_to_source_match(self):
        payload = {
            "generators": [
                {"id": "verified", "name": "k", "p": -4, "q": 4, "page": 2},
                {"id": "wrong-page", "name": "k", "p": -4, "q": 4, "page": 3},
                {"id": "unknown", "name": "invented", "p": 9, "q": 9, "page": 2},
                {"id": "no-stage", "name": "k", "p": -4, "q": 4},
            ]
        }
        plan = review_legacy_e2_payload(payload, "integer")
        reviews = {item.point.legacy_id: item for item in plan.point_reviews}

        self.assertEqual(reviews["verified"].status, "source-match")
        self.assertEqual(reviews["verified"].verified_record_id, "e2_integer_k")
        self.assertEqual(reviews["wrong-page"].status, "out-of-scope")
        self.assertEqual(reviews["unknown"].status, "needs-manual-review")
        self.assertEqual(reviews["no-stage"].status, "needs-stage-attestation")

    def test_matching_requires_the_exact_shifted_label(self):
        payload = {
            "generators": [
                {"id": "missing-orientation", "name": "\\{x+y\\}", "p": -1, "q": 1, "page": 2},
                {"id": "exact", "name": "\\{x+y\\}u_{\\sigma_i}", "p": -1, "q": 1, "page": 2},
            ]
        }
        plan = review_legacy_e2_payload(payload, "sigma_i")
        reviews = {item.point.legacy_id: item for item in plan.point_reviews}

        self.assertEqual(reviews["missing-orientation"].status, "needs-manual-review")
        self.assertEqual(reviews["exact"].status, "source-match")


class MaterializationTest(unittest.TestCase):
    def test_materialization_adds_only_catalogue_records_and_is_idempotent(self):
        workspace = Workspace(
            id="ws_integer",
            name="integer",
            classes=[ClassNode("existing-D", "D", Grade(8, 0))],
        )

        first = materialize_verified_e2_records(workspace, "integer")
        second = materialize_verified_e2_records(workspace, "integer")

        self.assertIn("existing-D", first["existing_classes"])
        self.assertEqual(len(workspace.classes), 9)
        self.assertEqual(len(workspace.differentials), 0)
        self.assertEqual(len(workspace.propositions), 14)  # nine class witnesses and five relations
        self.assertFalse(second["added_classes"])
        self.assertFalse(second["added_propositions"])
        source = next(item for item in workspace.propositions if item.id == "source_e2_integer_k")
        self.assertEqual(source.status, "established")
        self.assertIn("PDF p. 16", source.source_ref)
        self.assertIn("does not assert survival", source.notes)

    def test_materialization_rejects_wrong_target_workspace(self):
        workspace = Workspace(id="ws_integer", name="integer")
        with self.assertRaises(ValueError):
            materialize_verified_e2_records(workspace, "sigma_i")

    def test_loading_an_existing_project_does_not_silently_import_the_catalogue(self):
        project = Project(id="existing", name="existing", workspaces=[Workspace(id="ws_integer", name="integer")])
        migrate_project(project)
        self.assertFalse(project.workspaces[0].classes)
        self.assertFalse(project.workspaces[0].propositions)

    def test_duplicate_merge_retargets_every_class_reference_before_removal(self):
        legacy = ClassNode(id="sig_xplusy", label="{x+y}u", grade=Grade(stem=0, filtration=1))
        imported = ClassNode(id="e2_sigma_xplusy_usigma_i", label="{x+y}u", grade=Grade(stem=-1, filtration=1))
        sigma = Workspace(
            id="ws_sigma_i", name="sigma", classes=[legacy, imported],
            differentials=[Differential("d", imported.id, legacy.id, 2)],
            propositions=[Proposition("p", "source", "old imported class", conclusion={"source_id": imported.id, "class_id": imported.id})],
        )
        project = Project(
            id="legacy-duplicate", name="legacy duplicate", workspaces=[Workspace(id="ws_integer", name="integer"), sigma],
            cross_graded_products=[CrossGradedProduct(
                id="product", left_workspace_id=sigma.id, left_class_id=imported.id,
                right_workspace_id=sigma.id, right_class_id=legacy.id, page=2,
                left_sector_id="s", right_sector_id="s", raw_representation_sum={},
                result_sector_id="s", result_stem=0, result_filtration=0,
            )],
        )
        migrate_project(project)
        self.assertEqual([item.id for item in sigma.classes], [legacy.id])
        self.assertEqual((sigma.differentials[0].source_id, sigma.differentials[0].target_id), (legacy.id, legacy.id))
        self.assertEqual(sigma.propositions[0].conclusion["source_id"], legacy.id)
        self.assertEqual(sigma.propositions[0].conclusion["class_id"], legacy.id)
        self.assertEqual(project.cross_graded_products[0].left_class_id, legacy.id)


if __name__ == "__main__":
    unittest.main()
