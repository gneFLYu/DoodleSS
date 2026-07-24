import json
import unittest
from pathlib import Path

from api.index import app as vercel_app


ROOT = Path(__file__).resolve().parents[1]


class VercelDeploymentTest(unittest.TestCase):
    def test_vercel_framework_detector_has_an_explicit_flask_entrypoint(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('requires-python = ">=3.10,<3.14"', pyproject)
        self.assertIn('[tool.vercel]', pyproject)
        self.assertIn('entrypoint = "api.index:app"', pyproject)
        self.assertNotIn('[tool.vercel.scripts]', pyproject)
        self.assertNotIn('python build.py', pyproject)
        self.assertFalse((ROOT / "build.py").exists())

    def test_vercel_wsgi_entrypoint_is_healthy(self):
        response = vercel_app.test_client().get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["application"], "HFPSS Studio")

    def test_vercel_configuration_bundles_backend_and_public_assets_exist(self):
        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(config["functions"]["api/index.py"]["includeFiles"], "backend/**")
        self.assertIn("tests/**", config["functions"]["api/index.py"]["excludeFiles"])
        for filename in ("app.js", "cell-layout.js", "style.css", "delete-cursor.svg"):
            backend_asset = ROOT / "backend" / "static" / filename
            public_asset = ROOT / "public" / "static" / filename
            self.assertTrue(public_asset.is_file())
            self.assertEqual(public_asset.read_bytes(), backend_asset.read_bytes())


if __name__ == "__main__":
    unittest.main()
