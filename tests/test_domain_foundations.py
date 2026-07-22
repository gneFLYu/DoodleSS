import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.algebra import F4Element
from domain.migrations import ensure_foundations
from domain.models import (
    ClassNode,
    Grade,
    Project,
    Proposition,
    Workspace,
    project_from_dict,
    project_to_dict,
)


class F4ArithmeticTest(unittest.TestCase):
    def test_complete_addition_and_multiplication_tables(self):
        values = [F4Element.parse(item) for item in ("0", "1", "zeta", "zeta^2")]
        addition = [
            ["0", "1", "zeta", "zeta^2"],
            ["1", "0", "zeta^2", "zeta"],
            ["zeta", "zeta^2", "0", "1"],
            ["zeta^2", "zeta", "1", "0"],
        ]
        multiplication = [
            ["0", "0", "0", "0"],
            ["0", "1", "zeta", "zeta^2"],
            ["0", "zeta", "zeta^2", "1"],
            ["0", "zeta^2", "1", "zeta"],
        ]

        for row, left in enumerate(values):
            for column, right in enumerate(values):
                self.assertEqual(str(left + right), addition[row][column])
                self.assertEqual(str(left * right), multiplication[row][column])

    def test_field_laws_and_parsing(self):
        values = F4Element.elements()
        for left in values:
            for middle in values:
                for right in values:
                    self.assertEqual(left * (middle + right), left * middle + left * right)
        zeta = F4Element.parse("zeta")
        self.assertEqual(zeta**3, F4Element.one())
        self.assertEqual(zeta * zeta.inverse(), F4Element.one())
        self.assertEqual(F4Element.parse("1+zeta"), F4Element.zeta_squared())
        with self.assertRaises(ZeroDivisionError):
            F4Element.zero().inverse()


class FoundationMigrationTest(unittest.TestCase):
    def make_project(self):
        return Project(
            id="p",
            name="test",
            workspaces=[
                Workspace(
                    id="w",
                    name="workspace",
                    classes=[ClassNode("c", "u_1", Grade(0, 0))],
                    propositions=[
                        Proposition(
                            id="prop",
                            kind="source",
                            statement="sourced statement",
                            source_ref="notes.tex:10",
                        )
                    ],
                )
            ],
            research_brief={"source": "local archive", "status": "draft"},
        )

    def test_coefficient_contexts_keep_residue_and_witt_arithmetic_distinct(self):
        project = ensure_foundations(self.make_project())
        contexts = {item.id: item for item in project.coefficient_contexts}
        self.assertEqual(contexts["q8-residue-f4"].scalar_mode, "residue")
        self.assertEqual(contexts["q8-residue-f4"].coefficient_ring, "F4")
        self.assertEqual(contexts["q8-witt-f4"].scalar_mode, "2_adic")
        self.assertIn("W(F4)", contexts["q8-witt-f4"].coefficient_ring)
        self.assertNotEqual(contexts["q8-residue-f4"].id, contexts["q8-witt-f4"].id)

    def test_u1_and_v1_are_separate_source_scoped_symbols(self):
        project = ensure_foundations(self.make_project())
        symbols = {item.id: item for item in project.symbol_definitions}
        self.assertEqual(symbols["symbol-u1"].symbol, "u_1")
        self.assertEqual(symbols["symbol-v1"].symbol, "v_1")
        self.assertNotEqual(symbols["symbol-u1"].grade, symbols["symbol-v1"].grade)
        self.assertIn("do not silently identify", symbols["symbol-v1"].normalization.lower())

    def test_round_trip_preserves_foundations_and_provenance(self):
        original = ensure_foundations(self.make_project())
        restored = ensure_foundations(project_from_dict(project_to_dict(original)))

        self.assertEqual(restored.schema_version, 5)
        self.assertEqual(restored.research_brief, original.research_brief)
        self.assertEqual(restored.workspaces[0].classes[0].expression, "u_1")
        self.assertEqual(restored.workspaces[0].classes[0].coefficient_context_id, "q8-witt-f4")
        self.assertEqual(restored.workspaces[0].propositions[0].source_refs, ["notes.tex:10"])
        self.assertEqual(len(restored.coefficient_contexts), 2)
        self.assertEqual(len(restored.symbol_definitions), 2)

    def test_legacy_payload_loads_and_migration_is_idempotent(self):
        legacy = {
            "id": "legacy",
            "name": "Legacy",
            "research_brief": {"source": "old notes"},
            "workspaces": [
                {
                    "id": "legacy-ws",
                    "name": "Legacy workspace",
                    "classes": [
                        {
                            "id": "legacy-class",
                            "label": "x",
                            "grade": {"stem": 2, "filtration": 1, "representation": {}},
                        }
                    ],
                    "propositions": [],
                    "differentials": [],
                }
            ],
        }
        project = ensure_foundations(project_from_dict(legacy))
        ensure_foundations(project)

        self.assertEqual(project.research_brief["source"], "old notes")
        self.assertEqual(project.workspaces[0].classes[0].expression, "x")
        self.assertEqual(project.workspaces[0].settings["page_limit"], 25)
        self.assertEqual(len(project.coefficient_contexts), 2)
        self.assertEqual(len(project.symbol_definitions), 2)


if __name__ == "__main__":
    unittest.main()
