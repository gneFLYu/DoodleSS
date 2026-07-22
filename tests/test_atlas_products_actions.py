import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import app as app_module
from app import app
from domain.actions import c3_orbit, c3_transport_preview
from domain.grading import normalize_to_q8_sector, q8_representatives
from domain.migrations import migrate_project
from domain.models import ClassNode, Grade, project_from_dict, project_to_dict
from domain.products import create_cross_graded_product, preview_cross_graded_product
from domain.seed import demo_project


EXPECTED_REPRESENTATIVES = [
    "(*)",
    "(* - \\sigma_j)",
    "(* - 2\\sigma_j)",
    "(* - 3\\sigma_j)",
    "(* - \\sigma_i)",
    "(* - \\sigma_i - \\sigma_j)",
    "(* - \\sigma_i - 2\\sigma_j)",
    "(* - \\sigma_i - 3\\sigma_j)",
    "(* - 2\\sigma_i)",
    "(* - 2\\sigma_i - \\sigma_j)",
    "(* - 2\\sigma_i - 2\\sigma_j)",
    "(* - 2\\sigma_i - 3\\sigma_j)",
    "(* - 3\\sigma_i)",
    "(* - 3\\sigma_i - \\sigma_j)",
    "(* - 3\\sigma_i - 2\\sigma_j)",
    "(* - 3\\sigma_i - 3\\sigma_j)",
]


class AtlasTest(unittest.TestCase):
    def test_all_sixteen_representatives_are_persisted_in_declared_order(self):
        project = migrate_project(demo_project())
        self.assertEqual(len(project.grading_sectors), 16)
        self.assertEqual([item.display_label for item in project.grading_sectors], EXPECTED_REPRESENTATIVES)
        self.assertEqual(
            [item.id for item in project.grading_sectors],
            [item[2] for item in q8_representatives()],
        )
        self.assertEqual(len({item.workspace_id for item in project.grading_sectors}), 16)

    def test_empty_sector_is_not_computed_not_zero_and_survives_round_trip(self):
        project = migrate_project(demo_project())
        sector = next(item for item in project.grading_sectors if item.id == "q8-ro-a2-b1")
        self.assertEqual(sector.status, "not-computed")
        self.assertEqual(sector.class_ids, [])

        restored = migrate_project(project_from_dict(project_to_dict(project)))
        restored_sector = next(item for item in restored.grading_sectors if item.id == sector.id)
        self.assertEqual(restored_sector.status, "not-computed")
        self.assertEqual(restored_sector.workspace_id, sector.workspace_id)

    def test_normalization_requires_source_scoped_certificate_outside_tile(self):
        project = migrate_project(demo_project())
        exact = normalize_to_q8_sector(project, {"sigma_i": -1, "sigma_j": -2})
        reduced = normalize_to_q8_sector(project, {"sigma_i": -4})

        self.assertEqual(exact.sector_id, "q8-ro-a1-b2")
        self.assertEqual(exact.status, "exact")
        self.assertEqual(reduced.sector_id, "q8-ro-a0-b0")
        self.assertEqual(reduced.status, "requires-certificate")
        self.assertEqual(reduced.normalization_path, ["q8-rel-four-sigma-i"])


class C3ActionTest(unittest.TestCase):
    def test_declared_omega_has_order_three(self):
        representation = {"sigma_i": -1, "sigma_j": -2}
        orbit = c3_orbit(representation)
        self.assertEqual(orbit[0], {"sigma_i": -1, "sigma_j": -2})
        self.assertEqual(orbit[1], {"sigma_j": -1, "sigma_k": -2})
        self.assertEqual(orbit[2], {"sigma_i": -2, "sigma_k": -1})

    def test_i_plus_2j_and_2i_plus_j_are_distinct_c3_orbits(self):
        first = {tuple(sorted(item.items())) for item in c3_orbit({"sigma_i": -1, "sigma_j": -2})}
        second = {tuple(sorted(item.items())) for item in c3_orbit({"sigma_i": -2, "sigma_j": -1})}
        self.assertTrue(first.isdisjoint(second))

        project = migrate_project(demo_project())
        sectors = {item.id: item for item in project.grading_sectors}
        self.assertNotEqual(sectors["q8-ro-a1-b2"].c3_orbit_id, sectors["q8-ro-a2-b1"].c3_orbit_id)
        preview = c3_transport_preview(project, "q8-ro-a1-b2")
        self.assertFalse(preview["materialization_allowed"])
        self.assertIn("does not supply the transposition", preview["warning"])


class CrossGradedProductTest(unittest.TestCase):
    def make_project_with_two_sigma_j_class(self):
        project = migrate_project(demo_project())
        sector = next(item for item in project.grading_sectors if item.id == "q8-ro-a0-b2")
        workspace = next(item for item in project.workspaces if item.id == sector.workspace_id)
        workspace.classes.append(
            ClassNode(
                id="two-j-class",
                label="rendered two-j label",
                expression="u_{2\\sigma_j}",
                grade=Grade(2, 0, {"sigma_j": -2}),
                sector_id=sector.id,
            )
        )
        migrate_project(project)
        return project

    def test_sigma_i_times_two_sigma_j_lands_in_mixed_sector(self):
        project = self.make_project_with_two_sigma_j_class()
        preview = preview_cross_graded_product(
            project,
            left_sector_id="q8-ro-a1-b0",
            left_class_id="sig_a",
            right_sector_id="q8-ro-a0-b2",
            right_class_id="two-j-class",
            page=2,
        )
        self.assertEqual(preview["result_sector_id"], "q8-ro-a1-b2")
        self.assertEqual(preview["raw_representation_sum"], {"sigma_i": -1, "sigma_j": -2})
        self.assertIn("u_{2\\sigma_j}", preview["resulting_expression"])
        self.assertNotIn("rendered two-j label", preview["resulting_expression"])

        product = create_cross_graded_product(
            project,
            left_sector_id="q8-ro-a1-b0",
            left_class_id="sig_a",
            right_sector_id="q8-ro-a0-b2",
            right_class_id="two-j-class",
            page=2,
        )
        self.assertEqual(product.status, "candidate")
        self.assertEqual(project.cross_graded_products[-1].id, product.id)
        result = next(item for item in project.grading_sectors if item.id == "q8-ro-a1-b2")
        self.assertIn(product.id, result.products_in)

    def test_product_requires_same_page_liveness(self):
        project = self.make_project_with_two_sigma_j_class()
        with self.assertRaisesRegex(ValueError, "live on the same"):
            preview_cross_graded_product(
                project,
                left_sector_id="q8-ro-a2-b0",
                left_class_id="two_u",
                right_sector_id="q8-ro-a0-b2",
                right_class_id="two-j-class",
                page=4,
            )


class AtlasApiTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.data_dir = TemporaryDirectory()
        self.old_data_path = app_module.DATA_PATH
        app_module.DATA_PATH = Path(self.data_dir.name) / "project.json"

    def tearDown(self):
        app_module.DATA_PATH = self.old_data_path
        self.data_dir.cleanup()

    def test_atlas_product_and_c3_endpoints(self):
        sectors = self.client.get("/api/v2/grading-sectors").get_json()["sectors"]
        self.assertEqual(len(sectors), 16)
        two_j = next(item for item in sectors if item["id"] == "q8-ro-a0-b2")
        created = self.client.post(
            f"/api/workspaces/{two_j['workspace_id']}/classes",
            json={
                "label": "two-j",
                "expression": "u_{2\\sigma_j}",
                "stem": 2,
                "filtration": 0,
                "representation": {"sigma_j": -2},
                "sector_id": two_j["id"],
            },
        ).get_json()["class"]
        payload = {
            "left_sector_id": "q8-ro-a1-b0",
            "left_class_id": "sig_a",
            "right_sector_id": two_j["id"],
            "right_class_id": created["id"],
            "page": 2,
        }
        preview = self.client.post("/api/v2/products/preview", json=payload)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.get_json()["preview"]["result_sector_id"], "q8-ro-a1-b2")
        stored = self.client.post("/api/v2/products", json=payload)
        self.assertEqual(stored.status_code, 201)
        self.assertEqual(len(self.client.get("/api/v2/products").get_json()["products"]), 1)

        orbit = self.client.get("/api/v2/c3-actions/omega/orbit/q8-ro-a1-b2")
        self.assertEqual(orbit.status_code, 200)
        self.assertFalse(orbit.get_json()["materialization_allowed"])


if __name__ == "__main__":
    unittest.main()
