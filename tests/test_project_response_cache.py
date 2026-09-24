"""A disposable restart cache cannot replace current source/code validation."""
import gzip
import json
import os
from pathlib import Path
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import app as app_module
from project_response_cache import ProjectResponseCache


@pytest.fixture
def wire_cache(tmp_path, monkeypatch):
    root = tmp_path / "backend"
    (root / "data" / "review").mkdir(parents=True)
    (root / "domain").mkdir()
    code = root / "domain" / "algebra.py"
    code.write_text("VERSION = 1", encoding="utf-8")
    source = root / "data" / "review" / "certificate.json"
    source.write_text('{"value":1}', encoding="utf-8")
    path = root / "data" / "project.json"
    path.write_text(json.dumps({"id": "private-cache-test", "name": "First", "workspaces": []}), encoding="utf-8")
    cache = ProjectResponseCache(root, tmp_path / "private")
    monkeypatch.setattr(app_module, "DATA_PATH", path)
    monkeypatch.setattr(app_module, "_PROJECT_WIRE_CACHE", cache)
    app_module._invalidate_project_cache()
    yield cache, path, source, code
    app_module._invalidate_project_cache()


def test_restart_reuses_identical_full_wire_response_without_models(wire_cache, monkeypatch):
    cache, path, _, _ = wire_cache
    client = app_module.app.test_client()
    first = client.get("/api/project", headers={"Accept-Encoding": "gzip"})
    assert first.status_code == 200
    assert cache.read(path, cache.key(path)) == first.data
    app_module._invalidate_project_cache()
    monkeypatch.setattr(app_module, "_project_snapshot", Mock(side_effect=AssertionError("model rebuilt")))
    second = client.get("/api/project", headers={"Accept-Encoding": "gzip"})
    assert second.status_code == 200 and second.data == first.data
    plain = client.get("/api/project")
    assert plain.data == gzip.decompress(first.data)
    assert client.get("/api/project", headers={"Accept-Encoding": "gzip",
        "If-None-Match": first.headers["ETag"]}).status_code == 304


@pytest.mark.parametrize("change", ["project", "certificate", "code", "new-code", "runtime"])
def test_any_current_input_change_invalidates_restart_cache(wire_cache, change):
    cache, path, source, code = wire_cache
    before = cache.key(path)
    cache.write(path, before, gzip.compress(b'{"old":true}'))
    if change == "project":
        path.write_text(path.read_text().replace("First", "Other"), encoding="utf-8")
    elif change == "certificate":
        source.write_text('{"value":2}', encoding="utf-8")
    elif change == "code":
        code.write_text("VERSION = 2", encoding="utf-8")
    elif change == "new-code":
        (code.parent / "new.py").write_text("NEW = True", encoding="utf-8")
    else:
        cache.runtime = (*cache.runtime, "different-runtime")
    now = cache.key(path)
    assert now != before
    if now is not None:
        assert cache.read(path, now) is None
    if change in {"code", "new-code"}:
        assert now is None  # Old imported code may not publish a new-code result.
        restarted = ProjectResponseCache(cache.root, cache.directory)
        assert restarted.key(path) not in {None, before}


def test_corrupted_disk_cache_rebuilds_from_real_project(wire_cache):
    cache, path, _, _ = wire_cache
    client = app_module.app.test_client()
    first = client.get("/api/project", headers={"Accept-Encoding": "gzip"})
    target = cache._path(path)
    damaged = bytearray(target.read_bytes())
    damaged[-1] ^= 1
    target.write_bytes(damaged)
    assert cache.read(path, cache.key(path)) is None
    app_module._invalidate_project_cache()
    second = client.get("/api/project", headers={"Accept-Encoding": "gzip"})
    assert second.status_code == 200 and second.data == first.data
    assert cache.read(path, cache.key(path)) == second.data


def test_storage_failure_is_optional_and_keeps_previous_atomic_file(wire_cache, monkeypatch):
    cache, path, _, _ = wire_cache
    key = cache.key(path)
    body = gzip.compress(b'{}')
    cache.write(path, key, body)
    def denied(*args, **kwargs):
        raise PermissionError("read-only cache storage")
    monkeypatch.setattr("project_response_cache.os.replace", denied)
    cache.write(path, key, gzip.compress(b'{"changed":true}'))
    assert cache.read(path, key) == body
    assert list(cache.directory.glob("*.tmp")) == []
    monkeypatch.setattr(Path, "open", denied)
    assert cache.read(path, key) is None
    assert cache.key(path) is None


def test_missing_nonfilesystem_and_overridden_migrations_are_not_cached(wire_cache, monkeypatch):
    cache, path, _, _ = wire_cache
    assert cache.key(None) is None
    assert cache.key(path.with_name("missing.json")) is None
    monkeypatch.setattr(app_module, "migrate_project", lambda value: value)
    assert app_module._wire_cache_key() is None


def test_save_cannot_return_pre_edit_restart_response(wire_cache):
    _, _, _, _ = wire_cache
    client = app_module.app.test_client()
    first = client.get("/api/project").get_json()
    project = app_module.load_project()
    project.name = "Saved"
    app_module.save_project(project)
    app_module._invalidate_project_cache()
    current = client.get("/api/project").get_json()
    assert current["name"] == "Saved" and current["revision"] == first["revision"] + 1


def test_cache_size_is_bounded_and_bad_headers_fail_closed(wire_cache):
    cache, path, _, _ = wire_cache
    key = cache.key(path)
    cache.MAX_BYTES = 4
    cache.write(path, key, b"too large")
    assert not cache._path(path).exists()
    cache.directory.mkdir()
    cache._path(path).write_bytes(b"{invalid json}\nanything")
    assert cache.read(path, key) is None


@pytest.mark.skipif(os.name == "nt", reason="Windows uses the user temp ACL")
def test_posix_cache_rejects_shared_or_symlink_directories(wire_cache, tmp_path):
    cache, path, _, _ = wire_cache
    key = cache.key(path)
    cache.directory.mkdir(mode=0o755)
    cache.write(path, key, gzip.compress(b'{}'))
    assert cache.read(path, key) is None
    assert not cache._path(path).exists()
    link = tmp_path / "cache-link"
    link.symlink_to(cache.directory, target_is_directory=True)
    cache.directory = link
    cache.write(path, key, gzip.compress(b'{}'))
    assert cache.read(path, key) is None
