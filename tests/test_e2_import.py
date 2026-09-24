import sys
import re
from pathlib import Path
import unittest
from copy import deepcopy
from dataclasses import asdict


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.e2_import import (
    materialize_verified_e2_records,
    review_legacy_e2_payload,
    verified_e2_classes,
    verified_e2_relations,
)
from domain.migrations import migrate_project
from domain.models import ClassNode, CrossGradedProduct, Differential, Grade, Project, Proposition, Workspace
from domain.algebra_labels import parse_algebra_label


class E2CatalogueTest(unittest.TestCase):
    def test_catalogue_is_explicitly_cited_and_d_localized(self):
        integer = verified_e2_classes("integer")
        sigma = verified_e2_classes("sigma_i")

        self.assertEqual(len(integer), 120)
        self.assertEqual(len(sigma), 120)
        self.assertEqual(len({(item.stem, item.filtration) for item in integer}), 88)
        self.assertEqual(len({(item.stem, item.filtration) for item in sigma}), 96)
        self.assertEqual(
            {item.label for item in integer if (item.stem, item.filtration) == (2, 2)},
            {"h_1^2"},
        )
        self.assertEqual(
            {item.label for item in integer if (item.stem, item.filtration) == (6, 2)},
            {"x^2D", "y^2D", "v_1^2h_1^2"},
        )
        self.assertEqual(
            {item.label for item in sigma if (item.stem, item.filtration) == (2, 2)},
            {r"(yh_2+xh_1v_1)u_{\sigma_i}", r"(h_1^2+xh_1v_1)u_{\sigma_i}"},
        )
        sigma_v12 = next(item for item in sigma if item.label == r"v_1^2u_{\sigma_i}")
        self.assertEqual((sigma_v12.stem, sigma_v12.filtration), (4, 0))
        self.assertFalse(any(r"\Theta_i" in item.label for item in sigma))
        self.assertEqual(next(item for item in integer if item.label == "D").stem, 8)
        unit = next(item for item in integer if item.label == "1")
        self.assertEqual((unit.stem, unit.filtration, unit.pattern_key), (0, 0, "I00"))
        shifted = next(item for item in sigma if item.stem == -1 and item.filtration == 1)
        self.assertEqual((shifted.stem, shifted.filtration), (-1, 1))
        self.assertEqual(shifted.representation, {"sigma_i": -1})
        for item in (*integer, *sigma):
            self.assertIn("PDF p.", item.source_ref)
            self.assertIn("D-localized", item.scope)
            self.assertEqual(item.review_status, "source-verified")

    def test_every_catalogue_label_has_its_independently_computed_bidegree(self):
        # Both tables use x,y in (-1,1); D is (8,0).  Enumerating a visually
        # plausible motif at the wrong coordinate must fail independently of
        # the implementation's stored pattern keys and coordinate deltas.
        degrees = {"x": (-1, 1), "y": (-1, 1), "h_1": (1, 1), "h_2": (3, 1),
                   "v_1": (2, 0), "k": (-4, 4), "D": (8, 0)}
        for record in verified_e2_classes():
            label = record.label.replace(r"a_{\sigma_i}", "(x+y)")
            label = re.sub(r"u_\{[^}]*\}", "", label)
            label = label.replace(r"\{", "(").replace(r"\}", ")")
            group = re.search(r"\(([^()]*)\)", label)
            terms = ([label[:group.start()] + term + label[group.end():] for term in group.group(1).split("+")]
                     if group else [label or "1"])
            for term in terms:
                parsed = parse_algebra_label(term, unit_labels=("D",))
                actual = tuple(sum(degrees[factor.label][i] * factor.power for factor in parsed.factors)
                               for i in (0, 1))
                self.assertEqual(actual, (record.stem, record.filtration), (record.id, record.label, term))

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
        self.assertIsNotNone(reviews["verified"].verified_record_id)
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
    def test_exact_catalogue_match_restores_only_missing_source_quarantine(self):
        reason = "Archived during source audit: active local display point had no source locator or notes."
        restored = [ClassNode(f"local-h1-{power}", "h_1" if power == 1 else f"h_1^{power}",
                              Grade(power, power), archived=True, archived_reason=reason,
                              notes="Keep my observation.") for power in (1, 2, 3)]
        incorrect = ClassNode("old-wrong-degree", "v_1^4D^{-1}", Grade(4, 0),
                              archived=True, archived_reason=reason)
        manual = ClassNode("manual-hidden", "h_1D", Grade(9, 1),
                           archived=True, archived_reason="Archived by researcher.")
        workspace = Workspace(id="ws_integer", name="integer", classes=[*restored, incorrect, manual])
        first = materialize_verified_e2_records(workspace, "integer")
        self.assertEqual(set(first["restored_classes"]), {node.id for node in restored})
        for node in restored:
            self.assertFalse(node.archived)
            self.assertEqual(node.notes, "Keep my observation.")
            self.assertEqual(node.style["source_audit_restoration"]["archived_reason"], reason)
            self.assertIn("Table 2", node.style["source_audit_restoration"]["source_ref"])
        self.assertTrue(incorrect.archived)
        self.assertTrue(manual.archived)
        edges = {(p.conclusion.get("source_id"), p.conclusion.get("target_id"))
                 for p in workspace.propositions if p.kind == "relation"}
        self.assertIn((restored[0].id, restored[1].id), edges)
        self.assertIn((restored[1].id, restored[2].id), edges)
        before = deepcopy(asdict(workspace))
        self.assertFalse(materialize_verified_e2_records(workspace, "integer")["restored_classes"])
        self.assertEqual(asdict(workspace), before)

    def test_current_generated_edges_rebind_retired_targets_without_changing_manual_edges(self):
        workspace = Workspace(id="ws_integer", name="integer")
        materialize_verified_e2_records(workspace, "integer")
        originals = {p.id: deepcopy(p) for p in workspace.propositions
                     if p.id in {"source_e2_edge_e2_integer_h1_h1", "source_e2_edge_e2_integer_xh1_h1",
                                 "source_e2_edge_e2_integer_h2_h2"}}
        self.assertEqual(len(originals), 3)
        old_target = ClassNode("e2_integer_cell_s2_f2_dp0", r"\{x^2,y^2,h_1^2\}", Grade(2, 2))
        workspace.classes.append(old_target)
        for edge in workspace.propositions:
            if edge.id not in originals:
                continue
            edge.conclusion["target_id"] = old_target.id
            edge.conclusion["researcher_note"] = "Retain this note."
            edge.notes = "Original observation."
        manual = Proposition("manual-relation", "relation", "My conjecture", status="review",
                             conclusion={"source_id": "e2_integer_h1", "target_id": old_target.id})
        workspace.propositions.append(manual)
        manual_before = asdict(manual)
        materialize_verified_e2_records(workspace, "integer")
        self.assertTrue(old_target.archived)
        for edge in workspace.propositions:
            if edge.id not in originals:
                continue
            self.assertEqual(edge.status, "established")
            self.assertEqual(edge.conclusion["target_id"], originals[edge.id].conclusion["target_id"])
            self.assertNotIn("source_schema_retirement", edge.conclusion)
            self.assertEqual(edge.conclusion["source_schema_rebinding"]["previous_target_id"], old_target.id)
            self.assertEqual(edge.conclusion["researcher_note"], "Retain this note.")
            self.assertEqual(edge.notes, "Original observation.")
        self.assertEqual(asdict(manual), manual_before)
        before = deepcopy(asdict(workspace))
        materialize_verified_e2_records(workspace, "integer")
        self.assertEqual(asdict(workspace), before)

    def test_materialization_adds_only_catalogue_records_and_is_idempotent(self):
        workspace = Workspace(
            id="ws_integer",
            name="integer",
            classes=[ClassNode("existing-D", "D", Grade(8, 0))],
        )

        first = materialize_verified_e2_records(workspace, "integer")
        second = materialize_verified_e2_records(workspace, "integer")

        self.assertIn("existing-D", first["existing_classes"])
        self.assertEqual(len(workspace.classes), 120)
        self.assertEqual(len(workspace.differentials), 0)
        self.assertGreater(len(workspace.propositions), 125)  # cells, cited relations, and chart edges
        self.assertFalse(second["added_classes"])
        self.assertFalse(second["added_propositions"])
        source = next(item for item in workspace.propositions if item.id.startswith("source_e2_integer_cell_"))
        self.assertEqual(source.status, "established")
        self.assertIn("PDF p. 16", source.source_ref)
        self.assertIn("does not assert survival", source.notes)

    def test_enumerated_catalogue_carries_series_glyphs_and_periodic_edges(self):
        workspace = Workspace(id="ws_sigma_i", name="sigma")
        materialize_verified_e2_records(workspace, "sigma_i")
        self.assertEqual(len(workspace.classes), 120)
        self.assertIn("j-series", {item.style.get("dkllw_glyph") for item in workspace.classes})
        edges = [item for item in workspace.propositions if item.conclusion.get("chart_connection")]
        self.assertTrue(edges)
        self.assertTrue(all(item.conclusion.get("period_scope") == ["D^8", "kD^3"] for item in edges))
        integer = Workspace(id="ws_integer", name="integer")
        materialize_verified_e2_records(integer, "integer")
        unit = next(item for item in integer.classes if item.label == "1")
        self.assertTrue(unit.style.get("multiplicative_unit"))

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
