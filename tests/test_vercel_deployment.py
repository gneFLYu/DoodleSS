import json
import unittest
from pathlib import Path

from api.index import app as vercel_app


ROOT = Path(__file__).resolve().parents[1]


class VercelDeploymentTest(unittest.TestCase):
    def test_vercel_wsgi_entrypoint_is_healthy(self):
        response = vercel_app.test_client().get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["application"], "HFPSS Studio")

    def test_vercel_configuration_bundles_backend_and_public_assets_exist(self):
        config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(config["buildCommand"], "python build.py")
        self.assertEqual(config["functions"]["api/index.py"]["includeFiles"], "backend/**")
        for filename in ("app.js", "cell-layout.js", "style.css", "delete-cursor.svg"):
            self.assertTrue((ROOT / "public" / "static" / filename).is_file())


if __name__ == "__main__":
    unittest.main()
