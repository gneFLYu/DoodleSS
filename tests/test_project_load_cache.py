"""Revision-aware project reads retain full data without repeating migrations."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
import gzip
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import app as app_module
from domain.models import (
    CellBasisVector, CellVectorSpace, DifferentialMap, Grade, NamedVector,
    Project, Workspace,
)


@pytest.fixture
def cached_project(tmp_path, monkeypatch):
    root = tmp_path / "backend"
    review = root / "data" / "review"
    review.mkdir(parents=True)
    source = review / "certificate.json"
    source.write_text('{"value":1}', encoding="utf-8")
    path = root / "data" / "project.json"
    source_cell = CellVectorSpace("source", Grade(1, 0),
        basis=[CellBasisVector("s", "s")])
    target_cell = CellVectorSpace("target", Grade(0, 3),
        basis=[CellBasisVector("p", "P"), CellBasisVector("q", "Q")],
        display_basis=[NamedVector("p", "P", ["zeta", "0"])],
        named_vectors=[NamedVector("sum", "P+Q", ["zeta", "zeta"])])
    project = Project("cache-test", "Complete project", workspaces=[Workspace(
        id="ws", name="Workspace", cells=[source_cell, target_cell],
        differential_maps=[DifferentialMap("d3", "source", "target", 3,
            matrix=[["1"], ["zeta"]])])],
        research_brief={"evidence": {"full_text": "ζ certificate " * 1000}})
    path.write_text(json.dumps(asdict(project)), encoding="utf-8")
    migrate = Mock(side_effect=lambda value: value)
    monkeypatch.setattr(app_module, "ROOT", root)
    monkeypatch.setattr(app_module, "DATA_PATH", path)
    monkeypatch.setattr(app_module, "migrate_legacy_periods", migrate)
    monkeypatch.setattr(app_module, "demo_project", lambda: deepcopy(project))
    app_module._invalidate_project_cache()
    yield SimpleNamespace(path=path, source=source, project=project, migrate=migrate,
                          client=app_module.app.test_client())
    app_module._invalidate_project_cache()


def test_cached_serialization_preserves_complete_api_shape_and_ports(cached_project):
    project = cached_project.project
    expected = asdict(project)
    for raw, ws in zip(expected["workspaces"], project.workspaces):
        for cell in raw["cells"]:
            for key in ("display_basis", "named_vectors"):
                for vector in cell[key]:
                    vector["projective_coordinates"] = app_module.projective_normal_form(vector["coordinates"])
        for raw_map, item in zip(raw["differential_maps"], ws.differential_maps):
            raw_map["image_ports"] = app_module.map_image_ports(ws, item)
    before = asdict(project)
    response = cached_project.client.get("/api/project")
    assert response.get_json() == expected
    assert response.data == (json.dumps(expected, ensure_ascii=False,
                                       separators=(",", ":")) + "\n").encode("utf-8")
    assert response.data == cached_project.client.get("/api/project").data
    assert cached_project.migrate.call_count == 1
    assert asdict(project) == before
    # Serialization-only annotations must never leak into persisted models.
    assert asdict(app_module.load_project()) == before


def test_compressed_json_is_lossless_negotiated_and_cached(cached_project, monkeypatch):
    encode = Mock(wraps=app_module._project_api_json)
    compress = Mock(wraps=app_module.gzip.compress)
    monkeypatch.setattr(app_module, "_project_api_json", encode)
    monkeypatch.setattr(app_module.gzip, "compress", compress)
    plain = cached_project.client.get("/api/project")
    zipped = cached_project.client.get("/api/project", headers={"Accept-Encoding": "gzip"})
    assert gzip.decompress(zipped.data) == plain.data
    assert len(zipped.data) < len(plain.data)
    assert zipped.headers["Content-Encoding"] == "gzip"
    assert "Accept-Encoding" in zipped.headers["Vary"]
    assert zipped.headers["Cache-Control"] == "private, no-cache"
    assert "Content-Encoding" not in cached_project.client.get("/api/project",
        headers={"Accept-Encoding": "gzip;q=0, identity"}).headers
    again = cached_project.client.get("/api/project", headers={"Accept-Encoding": "gzip"})
    assert again.data == zipped.data
    assert encode.call_count == compress.call_count == 1
    conditional = cached_project.client.get("/api/project", headers={
        "Accept-Encoding": "gzip", "If-None-Match": zipped.headers["ETag"]})
    assert conditional.status_code == 304 and conditional.data == b""


def test_each_mutable_load_is_isolated_from_other_reads(cached_project):
    one = app_module.load_project()
    one.name = "unsaved edit"
    one.research_brief["evidence"]["full_text"] = "changed"
    one.workspaces[0].cells[1].named_vectors[0].coordinates[0] = "0"
    two = app_module.load_project()
    assert asdict(two) == asdict(cached_project.project)
    assert cached_project.migrate.call_count == 1


def test_save_invalidates_json_gzip_and_etag(cached_project):
    first = cached_project.client.get("/api/project", headers={"Accept-Encoding": "gzip"})
    project = app_module.load_project()
    project.name = "Saved edit"
    app_module.save_project(project)
    updated = cached_project.client.get("/api/project", headers={
        "Accept-Encoding": "gzip", "If-None-Match": first.headers["ETag"]})
    assert updated.status_code == 200
    data = json.loads(gzip.decompress(updated.data))
    assert data["name"] == "Saved edit" and data["revision"] == 1
    assert updated.headers["ETag"] != first.headers["ETag"]
    assert cached_project.migrate.call_count == 2


def test_external_same_length_atomic_replacement_invalidates(cached_project):
    app_module.load_project()
    raw = cached_project.path.read_text(encoding="utf-8")
    replacement = cached_project.path.with_suffix(".replacement")
    replacement.write_text(raw.replace("Complete project", "External project"), encoding="utf-8")
    replacement.replace(cached_project.path)
    assert app_module.load_project().name == "External project"
    assert cached_project.migrate.call_count == 2


def test_review_source_edit_and_project_path_changes_invalidate(cached_project, monkeypatch):
    app_module.load_project()
    cached_project.source.write_text('{"value":2,"new":true}', encoding="utf-8")
    app_module.load_project()
    assert cached_project.migrate.call_count == 2
    other = cached_project.path.with_name("other.json")
    raw = asdict(cached_project.project)
    raw["name"] = "Other storage"
    other.write_text(json.dumps(raw), encoding="utf-8")
    monkeypatch.setattr(app_module, "DATA_PATH", other)
    assert app_module.load_project().name == "Other storage"
    assert cached_project.migrate.call_count == 3


def test_deletion_and_recreation_invalidate_demo_fallback(cached_project):
    app_module.load_project()
    cached_project.path.unlink()
    assert app_module.load_project().name == "Complete project"
    assert cached_project.migrate.call_count == 2
    raw = asdict(cached_project.project)
    raw["name"] = "Restored file"
    cached_project.path.write_text(json.dumps(raw), encoding="utf-8")
    assert app_module.load_project().name == "Restored file"
    assert cached_project.migrate.call_count == 3


def test_concurrent_initial_reads_share_one_migration(cached_project):
    with ThreadPoolExecutor(max_workers=4) as pool:
        projects = list(pool.map(lambda _: app_module.load_project(), range(4)))
    assert cached_project.migrate.call_count == 1
    assert len({id(project) for project in projects}) == 4


def test_nonfilesystem_adapter_does_not_reuse_stale_snapshot(cached_project, monkeypatch):
    raw = asdict(cached_project.project)
    monkeypatch.setattr(app_module, "DATA_PATH", SimpleNamespace(
        exists=lambda: True, read_text=lambda **kwargs: json.dumps(raw)))
    assert app_module.load_project().name == "Complete project"
    raw["name"] = "Adapter edit"
    assert app_module.load_project().name == "Adapter edit"
    assert cached_project.migrate.call_count == 2


def test_failed_save_retains_last_complete_snapshot(cached_project, monkeypatch):
    first = cached_project.client.get("/api/project").data
    project = app_module.load_project()
    project.name = "Failed save"
    def fail_replace(*args):
        raise OSError("simulated failure")
    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated failure"):
        app_module.save_project(project)
    assert cached_project.client.get("/api/project").data == first
    assert cached_project.migrate.call_count == 1


def test_edit_undo_redo_routes_refresh_the_cached_read_model(cached_project):
    client = cached_project.client
    before = client.get("/api/project", headers={"Accept-Encoding": "gzip"})
    created = client.post("/api/workspaces/ws/classes", json={
        "label": "new", "stem": 2, "filtration": 0,
    })
    assert created.status_code == 201
    class_id = created.get_json()["class"]["id"]

    def current_ids():
        response = client.get("/api/project", headers={
            "Accept-Encoding": "gzip", "If-None-Match": before.headers["ETag"],
        })
        assert response.status_code == 200
        return {item["id"] for item in json.loads(gzip.decompress(response.data))["workspaces"][0]["classes"]}

    assert class_id in current_ids()
    assert client.get("/api/history").get_json()["undo_depth"] == 1
    assert client.post("/api/history/undo").status_code == 200
    assert class_id not in current_ids()
    assert client.post("/api/history/redo").status_code == 200
    assert class_id in current_ids()
