"""Auxiliary sequences must never acquire HFPSS fates by fallback."""
from dataclasses import asdict
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import app as app_module
from domain.fate import class_is_live_on_page, sync_workspace_fates, workspace_sequence_kind
from domain.models import ClassNode, Differential, Grade, Project, Workspace


def bss_sample():
    return Workspace("bss_test", "Auxiliary 2-BSS", spectral_sequence="2-bss", page=1,
                     settings={"source_reference": True}, classes=[
                         ClassNode("v", "v_1", Grade(2, 0), page=1,
                                   style={"bockstein_filtration": 0, "last_page": 1}),
                         ClassNode("h", "h_0h_1", Grade(1, 1), page=1,
                                   style={"bockstein_filtration": 1, "last_page": 1}),
                     ], differentials=[Differential("d", "v", "h", 1, status="source-verified")])


def test_bss_events_never_transported_to_hfpss():
    workspace = bss_sample()
    sync_workspace_fates(workspace)
    assert workspace_sequence_kind(workspace) == "2-bss"
    assert not workspace.fates
    assert len(workspace.differential_events) == 2
    for event in workspace.differential_events:
        assert event.spectral_sequence == "2-bss"
        assert event.comparison_status == "auxiliary_bockstein_only"
        assert not event.source_exists_in_hfpss
    assert class_is_live_on_page(workspace, "v", 1)
    assert not class_is_live_on_page(workspace, "v", 2)
    assert not class_is_live_on_page(workspace, "missing", 1)


@pytest.mark.parametrize("method,path", [
    ("post", "/api/workspaces/bss_test/classes"),
    ("patch", "/api/workspaces/bss_test/settings"),
    ("get", "/api/v2/render/workspaces/bss_test/chart.tex"),
    ("get", "/api/workspaces/bss_test/legacy-export"),
])
def test_source_review_rejects_incompatible_operations(monkeypatch, method, path):
    project = Project("test", "Test", workspaces=[bss_sample()])
    before = asdict(project)
    monkeypatch.setattr(app_module, "load_project", lambda: project)
    response = getattr(app_module.app.test_client(), method)(path, json={})
    assert response.status_code == 409
    assert "read-only source review" in response.get_json()["error"]
    assert asdict(project) == before


def test_reference_installation_is_add_only_and_independent():
    from domain.literature_references import ensure_literature_references
    legacy = Workspace("ws_c4_j", "User's C4 restriction reference")
    project = Project("test", "Test", workspaces=[legacy])
    ensure_literature_references(project)
    assert project.workspaces[0] is legacy
    assert len(project.workspaces) == 5
    assert len({workspace.id for workspace in project.workspaces}) == 5
    project.workspaces[-1].summary = "Preserve this user note"
    before = asdict(project)
    ensure_literature_references(project)
    assert asdict(project) == before
    for workspace in project.workspaces[1:]:
        assert workspace.settings["source_reference"]
        assert "enumerated_e2_pattern" not in workspace.settings.get("rendering", {})
        sync_workspace_fates(workspace)
        assert not workspace.fates


def test_exact_bss_window_api_preserves_third_degree_and_external_targets():
    response = app_module.app.test_client().get(
        "/api/v2/2-bss/integer/window?page=2&stem_min=3&stem_max=4&filtration_max=1&v1_max=2&h0_max=0")
    assert response.status_code == 200
    result = response.get_json()
    assert result["differential_degree"] == [-1, 1, 2]
    arrow = next(item for item in result["differentials"]
                 if item["source"]["basis"] == "1" and item["source"]["v1"] == 2)
    assert arrow["target"]["basis"] == "h2"
    assert arrow["target"]["bockstein_filtration"] == 2
    assert not arrow["target_in_window"]
    assert "omitted, not zero" in result["coverage"]


def test_sigma_bss_window_api_keeps_twisted_sector_and_exact_target():
    response = app_module.app.test_client().get(
        "/api/v2/2-bss/sigma/window?page=2&stem_min=0&stem_max=1&filtration_max=4&v1_max=2&h0_max=0")
    assert response.status_code == 200
    result = response.get_json()
    assert result["sector"] == "sigma"
    arrow = next(item for item in result["differentials"]
                 if item["source"]["basis"] == "xh1^2" and item["source"]["k"] == 0
                 and item["source"]["D"] == 0)
    assert arrow["target"]["basis"] == "1"
    assert arrow["target"]["v1"] == 2
    assert arrow["target"]["k"] == 1
    assert arrow["target"]["h0"] == 2
    assert arrow["target"]["grade"] == {"stem": 0, "filtration": 4, "representation": {"sigma_i": -1}}
    assert all(node["label"].endswith(r"u_{\sigma_i}")
               for node in result["chart"]["classes"])


def test_bss_api_rejects_unknown_sector():
    response = app_module.app.test_client().get("/api/v2/2-bss/mixed/window")
    assert response.status_code == 404


def test_computed_chart_compact_and_compressed_wire_formats():
    import gzip
    import json
    client = app_module.app.test_client()
    url = "/api/v2/2-bss/sigma/window?page=1&stem_min=-1&stem_max=1&filtration_max=2&v1_max=2&h0_max=1&format=chart"
    plain = client.get(url)
    compressed = client.get(url, headers={"Accept-Encoding": "gzip"})
    assert compressed.status_code == 200
    assert compressed.headers["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in compressed.headers["Vary"]
    assert json.loads(gzip.decompress(compressed.data)) == plain.get_json()
    assert len(compressed.data) < len(plain.data) / 2
    assert "classes" not in plain.get_json()
    assert "records" not in plain.get_json()
    assert plain.get_json()["chart"]["classes"]


def test_c4_integer_window_api_retains_nonprincipal_coefficient_ideal():
    response = app_module.app.test_client().get(
        "/api/v2/c4/integer/window?page=14&stem_min=8&stem_max=8&filtration_max=0")
    assert response.status_code == 200
    result = response.get_json()
    branches = [node["style"]["c4_coefficient_branch"] for node in result["chart"]["classes"]
                if not node["style"].get("window_endpoint_only")]
    assert {(b["mu_min"], b["two_min"], b["two_max"]) for b in branches} == {(0, 2, None), (1, 0, None)}
    assert result["differential_degree"] == [-1, 14]
    assert "hidden extensions" in result["coverage"]


def test_c4_shifted_api_retains_its_own_late_kernel_and_sector():
    response = app_module.app.test_client().get(
        "/api/v2/c4/1-minus-sigma/window?page=14&stem_min=-4&stem_max=-4&filtration_max=0&format=chart")
    assert response.status_code == 200
    result = response.get_json()
    branches = [node["style"]["c4_coefficient_branch"] for node in result["chart"]["classes"]]
    assert {(b["mu_min"], b["two_min"], b["two_max"]) for b in branches} == {(0, 2, None), (1, 1, None)}
    assert all(node["grade"]["representation"] == {"1": 1, "sigma": -1}
               for node in result["chart"]["classes"])
    assert "cells" not in result


@pytest.mark.parametrize("query", ["page=1", "page=15", "filtration_min=-1", "filtration_max=65",
                                   "stem_min=4&stem_max=3", "stem_min=0&stem_max=129", "page=3.5"])
def test_c4_api_rejects_invalid_bounds(query):
    response = app_module.app.test_client().get("/api/v2/c4/integer/window?"+query)
    assert response.status_code == 400


def test_ro_reduction_api_reports_exact_certificate():
    response = app_module.app.test_client().get("/api/v2/c4/reduce-ro?alpha=2&beta=-2&gamma=0")
    assert response.status_code == 200
    result = response.get_json()
    assert result["stem_shift"] == 16 and result["sector"] == 0
    recovered = result["representative"][:]
    for unit in result["permanent_unit_powers"]:
        recovered = [x + unit["exponent"]*y for x, y in zip(recovered, unit["degree"])]
    assert recovered == [2, -2, 0]


def test_foundations_do_not_reinterpret_or_modify_reference_data():
    from domain.literature_references import ensure_literature_references
    from domain.migrations import ensure_foundations
    project = Project("test", "Test")
    ensure_literature_references(project)
    before = [asdict(workspace) for workspace in project.workspaces]
    ensure_foundations(project)
    assert [asdict(workspace) for workspace in project.workspaces] == before


@pytest.mark.parametrize("query", ["page=0", "page=5", "v1_max=49", "h0_max=13",
                                   "filtration_min=-1", "stem_min=4&stem_max=3", "page=1.5"])
def test_bss_api_rejects_invalid_or_excessive_bounds(query):
    response = app_module.app.test_client().get("/api/v2/2-bss/integer/window?"+query)
    assert response.status_code == 400
