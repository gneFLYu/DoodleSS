from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.fate import sync_workspace_fates
from domain.models import (
    ClassNode,
    Differential,
    Grade,
    ManualPeriodicity,
    Project,
    Proposition,
    Workspace,
    project_from_dict,
    project_to_dict,
)
from domain.page_periodicity import (
    PagePeriodicityError,
    apply_manual_periodicity_retirement,
    page_period_status,
    plan_virtual_period_instances,
    prepare_page_period_cycle,
    preview_manual_periodicity_retirement,
    register_page_period_cycle,
)


def period_project():
    period = ClassNode("P", "P", Grade(8, 0), page=2)
    base = ClassNode("x", "x", Grade(1, 1), page=2)
    target = ClassNode("target", "y", Grade(7, 2), page=2)
    workspace = Workspace(
        id="ws",
        name="Page-aware periods",
        page=3,
        classes=[period, base, target],
    )
    sync_workspace_fates(workspace)
    return Project("project", "Project", [workspace]), workspace


def declare_period(project, workspace, **overrides):
    payload = {
        "id": "period-P",
        "cycle_class_id": "P",
        "page": 3,
        "basis": "User selected P as a page period.",
        "source_ref": "Research notebook, period P",
    }
    payload.update(overrides)
    cycle = prepare_page_period_cycle(project, workspace.id, payload)
    register_page_period_cycle(project, cycle)
    return cycle


class PagePeriodCycleTest(unittest.TestCase):
    def test_declared_period_applies_earlier_and_virtual_instances_do_not_mutate(self):
        project, workspace = period_project()
        cycle = declare_period(project, workspace)
        before = (
            len(workspace.classes),
            len(workspace.differentials),
            len(workspace.propositions),
        )

        self.assertTrue(page_period_status(project, cycle.id, 2).eligible)
        preview = plan_virtual_period_instances(
            project,
            cycle.id,
            page=3,
            base_class_ids=["x"],
            translations=[1, 2],
        )

        self.assertEqual(
            before,
            (
                len(workspace.classes),
                len(workspace.differentials),
                len(workspace.propositions),
            ),
        )
        self.assertFalse(preview["persisted"])
        self.assertEqual(preview["created_class_ids"], [])
        self.assertEqual(
            [item["label"] for item in preview["instances"]],
            ["xP", r"xP^{2}"],
        )
        self.assertEqual(
            preview["instances"][1]["grade"],
            {"stem": 17, "filtration": 1, "representation": {}},
        )
        self.assertTrue(all(item["page"] == 3 for item in preview["instances"]))
        self.assertNotIn("state", preview["instances"][0])
        self.assertNotIn("style", preview["instances"][0])

    def test_cycle_passes_forward_only_without_incoming_or_outgoing_differential(self):
        project, workspace = period_project()
        cycle = declare_period(project, workspace)
        self.assertTrue(page_period_status(project, cycle.id, 4).eligible)

        workspace.differentials.append(
            Differential("d3-P", "P", "target", 3, status="candidate")
        )
        sync_workspace_fates(workspace)
        blocked = page_period_status(project, cycle.id, 4)

        self.assertFalse(blocked.eligible)
        self.assertEqual(blocked.blocking_differential_ids, ("d3-P",))
        with self.assertRaises(PagePeriodicityError):
            plan_virtual_period_instances(
                project,
                cycle.id,
                page=4,
                base_class_ids=["x"],
                translations=[1],
            )

    def test_unlinked_explicit_cycle_cannot_be_propagated_later(self):
        project, workspace = period_project()
        cycle = prepare_page_period_cycle(
            project,
            workspace.id,
            {
                "id": "explicit",
                "label": "Q",
                "grade": {"stem": 4, "filtration": 2, "representation": {}},
                "page": 5,
                "basis": "Explicit user input",
                "source_ref": "Notebook",
            },
        )
        register_page_period_cycle(project, cycle)

        self.assertTrue(page_period_status(project, cycle.id, 3).eligible)
        self.assertFalse(page_period_status(project, cycle.id, 6).eligible)

    def test_separate_expression_is_rejected_and_model_round_trips(self):
        project, workspace = period_project()
        with self.assertRaisesRegex(PagePeriodicityError, "separate expression"):
            prepare_page_period_cycle(
                project,
                workspace.id,
                {
                    "label": "P",
                    "expression": "Q",
                    "cycle_class_id": "P",
                    "page": 3,
                    "basis": "Input",
                    "source_ref": "Notebook",
                },
            )
        cycle = declare_period(project, workspace)
        restored = project_from_dict(project_to_dict(project))
        self.assertEqual(restored.page_period_cycles[0], cycle)


class ManualPeriodicityRetirementTest(unittest.TestCase):
    def retirement_project(self):
        base = ClassNode("base", "x", Grade(0, 0))
        generated_source = ClassNode(
            "generated-source",
            "xP",
            Grade(1, 0),
            manual_periodicity_id="manual-1",
            manual_periodicity_anchor_class_id="base",
        )
        generated_target = ClassNode(
            "generated-target",
            "yP",
            Grade(0, 2),
            manual_periodicity_id="manual-1",
            manual_periodicity_anchor_class_id="base",
        )
        proposition = Proposition(
            "generated-prop",
            "differential",
            "Manual periodic copy",
            status="candidate",
            conclusion={
                "source_id": generated_source.id,
                "target_id": generated_target.id,
                "page": 2,
                "manual_periodicity_id": "manual-1",
            },
            source_ref="Manual drawing operation",
        )
        differential = Differential(
            "generated-diff",
            generated_source.id,
            generated_target.id,
            2,
            status="candidate",
            proposition_id=proposition.id,
            manual_periodicity_id="manual-1",
        )
        workspace = Workspace(
            "ws",
            "Retirement",
            classes=[base, generated_source, generated_target],
            differentials=[differential],
            propositions=[proposition],
        )
        sync_workspace_fates(workspace)
        record = ManualPeriodicity(
            "manual-1",
            workspace.id,
            mode="box",
            rule_ids=["P"],
            bounds={"p_min": 0, "p_max": 1, "q_min": 0, "q_max": 2},
            basis="Legacy drawing operation",
            source_ref="Local project",
            created_class_ids=[generated_source.id, generated_target.id],
            created_differential_ids=[differential.id],
            created_proposition_ids=[proposition.id],
        )
        return Project(
            "project",
            "Project",
            workspaces=[workspace],
            manual_periodicities=[record],
        ), workspace, record

    def test_exact_owned_records_retire_and_user_class_remains(self):
        project, workspace, record = self.retirement_project()
        preview = preview_manual_periodicity_retirement(project, [record.id])

        self.assertTrue(preview["can_apply"])
        self.assertEqual(preview["counts"]["classes"], 2)
        self.assertEqual(preview["counts"]["active_classes"], 2)
        self.assertEqual(preview["counts"]["archived_classes"], 0)
        self.assertEqual(preview["counts"]["differentials"], 1)
        self.assertEqual(preview["counts"]["propositions"], 1)
        applied = apply_manual_periodicity_retirement(project, preview)

        self.assertTrue(applied["persisted"])
        self.assertEqual([item.id for item in workspace.classes], ["base"])
        self.assertEqual(workspace.differentials, [])
        self.assertEqual(workspace.propositions, [])
        self.assertEqual(record.storage_mode, "retired-compact")
        self.assertEqual(record.created_class_ids, [])
        self.assertEqual(record.retirement_summary["counts"]["classes"], 2)
        original_summary = dict(record.retirement_summary)
        repeated_preview = preview_manual_periodicity_retirement(
            project,
            [record.id],
        )
        self.assertFalse(repeated_preview["would_change"])
        repeated = apply_manual_periodicity_retirement(
            project,
            repeated_preview,
        )
        self.assertFalse(repeated["persisted"])
        self.assertEqual(record.retirement_summary, original_summary)
        restored = project_from_dict(project_to_dict(project))
        self.assertEqual(
            restored.manual_periodicities[0].storage_mode,
            "retired-compact",
        )

    def test_owner_mismatch_never_deletes_unrelated_class(self):
        project, workspace, record = self.retirement_project()
        user = ClassNode("user", "z", Grade(4, 0))
        workspace.classes.append(user)
        record.created_class_ids.append(user.id)

        preview = preview_manual_periodicity_retirement(project, [record.id])

        self.assertFalse(preview["can_apply"])
        self.assertIn(
            "class-owner-mismatch",
            {item["reason"] for item in preview["conflicts"]},
        )
        with self.assertRaises(PagePeriodicityError):
            apply_manual_periodicity_retirement(project, preview)
        self.assertIn(user, workspace.classes)

    def test_external_reference_blocks_retirement(self):
        project, workspace, record = self.retirement_project()
        workspace.propositions.append(
            Proposition(
                "user-proof",
                "relation",
                "A user proposition that uses the generated class",
                conclusion={"class_id": "generated-source"},
                source_ref="User notebook",
            )
        )

        preview = preview_manual_periodicity_retirement(project, [record.id])

        self.assertFalse(preview["can_apply"])
        self.assertTrue(
            any(
                item.get("object_id") == "user-proof"
                and item.get("target_id") == "generated-source"
                for item in preview["conflicts"]
            )
        )


if __name__ == "__main__":
    unittest.main()
