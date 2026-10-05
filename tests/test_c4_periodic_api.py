"""Periodic C4 seeds are independent of saved projects and horizontal view bounds."""
import gzip
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import app as app_module


@pytest.mark.parametrize("sector", ["integer", "1-minus-sigma"])
def test_periodic_api_is_source_scoped_and_compressed(monkeypatch, sector):
    def forbidden(*args, **kwargs):
        raise AssertionError("Periodic source chart must not read or mutate the saved project")
    monkeypatch.setattr(app_module, "load_project", forbidden)
    response = app_module.app.test_client().get(
        f"/api/v2/c4/{sector}/periodic-chart?page=3&filtration_min=0&filtration_max=16",
        headers={"Accept-Encoding": "gzip"})
    assert response.status_code == 200
    assert response.headers["Content-Encoding"] == "gzip"
    result = json.loads(gzip.decompress(response.data))
    assert result["sector"] == sector
    assert result["chart"]["periodicity"]["permanent"]
    assert result["chart"]["periodicity"]["stem"] == 32
    assert "cells" not in result
    assert all(0 <= node["grade"]["stem"] < 32 for node in result["chart"]["classes"])
    assert {item["kind"] for item in result["chart"]["propositions"]} == {"relation", "differential"}


@pytest.mark.parametrize("query", ["page=1", "page=15", "page=2.5", "filtration_min=-1",
    "filtration_min=10&filtration_max=9", "filtration_max=300", "filtration_max=NaN"])
def test_periodic_api_rejects_invalid_bounds(query):
    response = app_module.app.test_client().get("/api/v2/c4/integer/periodic-chart?" + query)
    assert response.status_code == 400
    assert response.get_json()["error"]


def test_high_filtration_is_not_a_hard_computation_cap():
    response = app_module.app.test_client().get(
        "/api/v2/c4/integer/periodic-chart?page=2&filtration_min=128&filtration_max=140")
    assert response.status_code == 200
    assert response.get_json()["chart"]["classes"]


def test_unknown_sector_is_not_silently_integer():
    response = app_module.app.test_client().get("/api/v2/c4/sigma/periodic-chart")
    assert response.status_code == 404
