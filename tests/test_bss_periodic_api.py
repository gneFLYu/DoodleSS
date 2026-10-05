"""Read-only periodic BSS API, independent projections, and HTTP negotiation."""
import gzip
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import app as app_module


@pytest.fixture
def client(monkeypatch, tmp_path):
    # A source-engine endpoint must not read, migrate, save, or checkpoint
    # the user's live project. Also isolate the configured path defensively.
    isolated_path = tmp_path / "untouched-project.json"
    monkeypatch.setattr(app_module, "DATA_PATH", isolated_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("Periodic BSS chart must not touch the saved project")

    for name in ("load_project", "_load_project_uncached", "save_project", "checkpoint"):
        monkeypatch.setattr(app_module, name, forbidden)
    with app_module.app.test_client() as client:
        yield client
    assert not isolated_path.exists()


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_defaults_have_cohomology_projection_and_compact_seed_strip(client, sector):
    response = client.get(f"/api/v2/2-bss/{sector}/periodic-chart")
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert "Content-Encoding" not in response.headers
    payload = response.get_json()
    assert payload["sector"] == sector and payload["spectral_sequence"] == "2-bss"
    assert payload["projection"] == "cohomology"
    assert payload["window"] == {"page": 1, "stem_min": 0, "stem_max": 7,
                                  "filtration_min": 0, "filtration_max": 8,
                                  "v1_max": 4, "h0_max": 2}
    assert payload["chart"]["periodicity"]["stem"] == 8
    assert payload["chart"]["periodicity"]["permanent"]
    assert "classes" not in payload and "differentials" not in payload and "records" not in payload
    assert all(0 <= node["grade"]["stem"] <= 7 for node in payload["chart"]["classes"])


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_projection_changes_y_not_page_or_monomial_identity(client, sector, page):
    query = f"page={page}&filtration_max=4&v1_max=4&h0_max=2"
    url = f"/api/v2/2-bss/{sector}/periodic-chart?{query}"
    responses = [client.get(url+f"&projection={projection}") for projection in ("cohomology", "bockstein")]
    assert all(response.status_code == 200 for response in responses)
    s_payload, p_payload = [response.get_json() for response in responses]
    assert s_payload["window"] == p_payload["window"]
    assert s_payload["page"] == p_payload["page"] == page
    assert s_payload["differential_degree"] == p_payload["differential_degree"] == [-1, 1, page]
    assert s_payload["projected_differential_degree"] == [-1, 1]
    assert p_payload["projected_differential_degree"] == [-1, page]
    s_nodes = {node["id"]: node for node in s_payload["chart"]["classes"]}
    p_nodes = {node["id"]: node for node in p_payload["chart"]["classes"]}
    assert s_nodes.keys() == p_nodes.keys()
    for identifier, s_node in s_nodes.items():
        p_node = p_nodes[identifier]
        assert s_node["label"] == p_node["label"]
        assert s_node["grade"]["stem"] == p_node["grade"]["stem"]
        assert s_node["grade"]["filtration"] == p_node["style"]["bss_cohomological_filtration"]
        assert p_node["grade"]["filtration"] == p_node["style"]["bockstein_filtration"]
        assert s_node["style"]["bss_periodic_family_key"] == p_node["style"]["bss_periodic_family_key"]
    assert {claim["id"] for claim in s_payload["chart"]["propositions"]} == {
        claim["id"] for claim in p_payload["chart"]["propositions"]}


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_gzip_is_lossless_respects_q_zero_and_supports_conditional_get(client, sector):
    url = f"/api/v2/2-bss/{sector}/periodic-chart?page=2&filtration_max=4&v1_max=2&h0_max=1"
    plain = client.get(url)
    compressed = client.get(url, headers={"Accept-Encoding": "gzip"})
    refused = client.get(url, headers={"Accept-Encoding": "gzip;q=0, identity;q=1"})
    assert plain.status_code == compressed.status_code == refused.status_code == 200
    assert compressed.headers["Content-Encoding"] == "gzip"
    assert "Content-Encoding" not in refused.headers
    assert "Accept-Encoding" in compressed.headers["Vary"]
    assert plain.get_json() == json.loads(gzip.decompress(compressed.data)) == refused.get_json()
    assert len(compressed.data) < len(plain.data)
    cached = client.get(url, headers={"Accept-Encoding": "gzip", "If-None-Match": compressed.headers["ETag"]})
    assert cached.status_code == 304 and not cached.data


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("query", [
    "page=0", "page=5", "page=-1", "page=2.5", "page=true", "page=",
    "projection=adams", "projection=", "projection=total",
    "filtration_min=-1", "filtration_min=8&filtration_max=7", "filtration_max=129",
    "filtration_max=NaN", "filtration_max=3.5", "v1_max=-1", "v1_max=49",
    "v1_max=1.2", "h0_max=-1", "h0_max=13", "h0_max=no",
])
def test_invalid_page_projection_and_caps_return_json_error(client, sector, query):
    response = client.get(f"/api/v2/2-bss/{sector}/periodic-chart?{query}")
    assert response.status_code == 400
    assert response.mimetype == "application/json"
    assert isinstance(response.get_json()["error"], str) and response.get_json()["error"]


@pytest.mark.parametrize("sector", ["C4", "1-minus-sigma", "ws_q8_bss_integer", "unknown"])
def test_unknown_sector_is_not_silently_replaced(client, sector):
    response = client.get(f"/api/v2/2-bss/{sector}/periodic-chart")
    assert response.status_code == 404 and response.get_json()["error"]


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_high_cohomology_is_allowed_and_independent_of_plotted_h0(client, sector):
    response = client.get(f"/api/v2/2-bss/{sector}/periodic-chart?page=1&projection=bockstein"
                          "&filtration_min=128&filtration_max=132&v1_max=0&h0_max=0")
    assert response.status_code == 200
    payload = response.get_json()
    seeds = [node for node in payload["chart"]["classes"] if node["style"].get("bss_in_window")]
    assert seeds
    assert all(128 <= node["style"]["bss_cohomological_filtration"] <= 132 for node in seeds)
    assert all(node["grade"]["filtration"] == 0 for node in seeds)


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_source_operator_claims_are_unique_and_sigma_vectors_do_not_add_rank(client, sector):
    response = client.get(f"/api/v2/2-bss/{sector}/periodic-chart?page=1&filtration_max=4&v1_max=4&h0_max=2")
    assert response.status_code == 200
    payload = response.get_json()
    chart = payload["chart"]
    keys = [(claim["kind"], claim["conclusion"]["source_id"],
             claim["conclusion"].get("multiplier", "d1")) for claim in chart["propositions"]]
    assert len(keys) == len(set(keys))
    assert len(chart["propositions"]) == len({claim["id"] for claim in chart["propositions"]})
    nodes = {node["id"]: node for node in chart["classes"]}
    combinations = [node for node in nodes.values() if node["style"].get("bss_combination")]
    assert bool(combinations) == (sector == "sigma")
    for node in combinations:
        assert node["style"]["bss_in_window"] is False
        assert not node["style"].get("bss_boundary")
        assert not node["style"].get("window_endpoint_only")
        assert all(item["class_id"] in nodes for item in node["style"]["bss_combination_terms"])
    assert payload["coverage_details"]["displayed_class_count"] == sum(
        bool(node["style"].get("bss_in_window")) for node in nodes.values())
    assert payload["coverage_details"]["combination_count"] == len(combinations)
