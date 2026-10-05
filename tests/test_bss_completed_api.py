"""j-completed chart API: exact coefficient modules and bounded display axes."""
import gzip
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import app as app_module


@pytest.fixture
def client(monkeypatch, tmp_path):
    isolated_path = tmp_path / "untouched-project.json"
    monkeypatch.setattr(app_module, "DATA_PATH", isolated_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Completed BSS charts must not touch the saved project")

    for name in ("load_project", "_load_project_uncached", "save_project", "checkpoint"):
        monkeypatch.setattr(app_module, name, forbidden)
    with app_module.app.test_client() as client:
        yield client
    assert not isolated_path.exists()


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_default_has_symbolic_j_modules_not_a_v1_window(client, sector):
    response = client.get(f"/api/v2/2-bss/{sector}/completed-chart")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["sector"] == sector
    assert payload["spectral_sequence"] == "2-bss"
    assert payload["projection"] == "cohomology"
    assert "v1_max" not in payload["window"]
    nodes = [node for node in payload["chart"]["classes"] if node["style"].get("bss_in_window")]
    assert nodes
    assert all(node["style"].get("bss_j_module") for node in nodes)
    assert {node["style"]["bss_j_module"]["kind"] for node in nodes} == {"free", "torsion"}
    assert payload["chart"]["periodicity"]["stem"] == 8


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_projection_does_not_change_modules_or_equations(client, sector, page):
    url = f"/api/v2/2-bss/{sector}/completed-chart?page={page}&filtration_max=4&h0_max=2"
    s_response = client.get(url + "&projection=cohomology")
    p_response = client.get(url + "&projection=bockstein")
    assert s_response.status_code == p_response.status_code == 200
    s_payload, p_payload = s_response.get_json(), p_response.get_json()
    assert s_payload["window"] == p_payload["window"]
    assert s_payload["differential_degree"] == p_payload["differential_degree"] == [-1, 1, page]
    assert s_payload["projected_differential_degree"] == [-1, 1]
    assert p_payload["projected_differential_degree"] == [-1, page]
    s_nodes = {node["id"]: node for node in s_payload["chart"]["classes"]}
    p_nodes = {node["id"]: node for node in p_payload["chart"]["classes"]}
    assert s_nodes.keys() == p_nodes.keys()
    for key, node in s_nodes.items():
        other = p_nodes[key]
        assert node["label"] == other["label"]
        assert node["style"].get("bss_j_module") == other["style"].get("bss_j_module")
    assert [claim["statement"] for claim in s_payload["chart"]["propositions"]] == [
        claim["statement"] for claim in p_payload["chart"]["propositions"]]


@pytest.mark.parametrize("query", [
    "page=0", "page=5", "page=2.5", "page=true", "page=",
    "filtration_min=-1", "filtration_min=8&filtration_max=7", "filtration_max=129",
    "filtration_max=NaN", "filtration_max=3.5", "h0_max=-1", "h0_max=13",
    "h0_max=no", "projection=adams", "projection=", "v1_max=4",
])
def test_invalid_bounds_and_finite_v1_cap_are_rejected(client, query):
    response = client.get(f"/api/v2/2-bss/integer/completed-chart?{query}")
    assert response.status_code == 400
    assert response.get_json()["error"]


def test_unknown_sector_is_not_replaced(client):
    response = client.get("/api/v2/2-bss/unknown/completed-chart")
    assert response.status_code == 404


def test_compression_and_cache_preserve_payload(client):
    url = "/api/v2/2-bss/integer/completed-chart?page=3&filtration_max=4"
    plain = client.get(url)
    compressed = client.get(url, headers={"Accept-Encoding": "gzip"})
    assert plain.status_code == compressed.status_code == 200
    assert compressed.headers["Content-Encoding"] == "gzip"
    assert plain.get_json() == json.loads(gzip.decompress(compressed.data))
    assert len(compressed.data) < len(plain.data)
    cached = client.get(url, headers={"Accept-Encoding": "gzip", "If-None-Match": compressed.headers["ETag"]})
    assert cached.status_code == 304


def test_source_review_distinguishes_q8_and_g24_completion_parameters():
    from domain.bss_reference import create_bss_reference_workspaces
    for workspace in create_bss_reference_workspaces():
        review = workspace.settings["literature_review"]
        assert "j=v1^4 D^(-1)" in review["completed_coefficient_ring"]
        proof = review["completion_provenance"]
        assert proof["status"] == "derived-from-published-algebra"
        assert "j^3" in proof["scope"]
        assert "A.22" in proof["source_ref"]
