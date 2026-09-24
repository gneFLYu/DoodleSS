"""The imported integer tower and its edges reach the actual chart runtime."""

from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.e2_import import materialize_verified_e2_records
from domain.models import ClassNode, Grade, Project, Proposition, Workspace
from domain.published_differentials import ensure_published_differential_charts


SOURCE_AUDIT_ARCHIVE = (
    "Archived during source audit: active local display point had no source locator or notes."
)

RUNTIME = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const context = vm.createContext({document: {body: {dataset: {}}}, window: {}});
for (const name of ['graded-quotient', 'vector-page-algebra', 'page-algebra']) {
  vm.runInContext(fs.readFileSync(`backend/static/${name}.js`, 'utf8'), context);
}
const app = fs.readFileSync('backend/static/app.js', 'utf8');
vm.runInContext(app.slice(0, app.lastIndexOf('if (PAGE_MODE === "reviewing")')), context);
context.input = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = vm.runInContext(`
  state.project = input;
  const ws = input.workspaces[0];
  const bounds = {stemMin: 0, stemMax: 88, filtrationMin: 0, filtrationMax: 8};
  [2, 3, 4].map(page => {
    ws.page = page;
    const algebra = pageAlgebra(ws, bounds);
    const points = periodicClassInstances(ws, bounds, null, algebra);
    const liveIds = new Set(points.map(point => point.item.id));
    const relations = periodicRelations(ws, liveIds, bounds, algebra);
    return {page,
      points: points.map(point => ({pattern: point.item.style.e2_pattern,
        stem: point.grade.stem, filtration: point.grade.filtration,
        ports: point.modulePorts, label: periodicDisplayLabel(point)})),
      relations: relations.map(edge => ({source: edge.source.style.e2_pattern,
        target: edge.target.style.e2_pattern, sourceGrade: edge.sourceGrade,
        targetGrade: edge.targetGrade, status: edge.proposition.status}))};
  })
`, context);
process.stdout.write(JSON.stringify(result));
"""


@pytest.fixture(scope="module")
def integer_chart_pages():
    # Model the actual saved-project failure without loading the large demo:
    # exact source-backed names reused quarantined local class IDs, and a
    # stable relation ID still referred to the pre-column-split target.
    workspace = Workspace(
        id="ws_integer", name="integer",
        classes=[
            ClassNode(f"local_h{power}", f"h_1{suffix}", Grade(power, power),
                      archived=True, archived_reason=SOURCE_AUDIT_ARCHIVE)
            for power, suffix in ((1, ""), (2, "^2"), (3, "^3"))
        ] + [ClassNode("e2_integer_cell_s2_f2_dp0", r"\{x^2,y^2,h_1^2\}", Grade(2, 2))],
        propositions=[Proposition(
            "source_e2_edge_e2_integer_h1_h1", "relation", "old combined-column edge",
            status="established", rule="DKLLW24 E2 chart enumeration",
            conclusion={"source_id": "local_h1", "target_id": "e2_integer_cell_s2_f2_dp0",
                        "page": 2, "chart_connection": {"kind": "h1", "multiplier": "h_1"}},
        )],
    )
    materialize_verified_e2_records(workspace, "integer")
    workspace.settings["rendering"]["period_lattice"] = [
        {"id": "D8", "stem": 64, "filtration": 0, "exponent_domain": "integer"},
        {"id": "g", "stem": 20, "filtration": 4, "exponent_domain": "nonnegative"},
    ]
    project = Project(id="hfpss_studio", name="small integer chart", workspaces=[workspace])
    # Production table/Leibniz importer supplies d3(v1^6)=v1^4 h1^3 and
    # its descendants. No full demo migration or independent fake algebra.
    ensure_published_differential_charts(project)
    workspace.differentials = [item for item in workspace.differentials if item.page == 3]
    assert len(workspace.differentials) == 4
    result = subprocess.run(
        ["node", "-e", RUNTIME], cwd=ROOT, input=json.dumps(asdict(project)),
        capture_output=True, text=True, encoding="utf-8", check=True, timeout=45,
    )
    return {row["page"]: row for row in json.loads(result.stdout)}


@pytest.mark.parametrize("page", [2, 3])
@pytest.mark.parametrize("horizontal,vertical", [(0, 0), (64, 0), (20, 4), (84, 4)])
def test_integer_h1_tower_and_relations_survive_source_import(integer_chart_pages, page, horizontal, vertical):
    row = integer_chart_pages[page]
    expected = [("I00", 0, 0), ("I11", 1, 1), ("I22H", 2, 2), ("I33", 3, 3),
                ("I02", 0, 2), ("I13", 1, 3)]
    for pattern, stem, filtration in expected:
        points = [point for point in row["points"] if point["pattern"] == pattern
                  and (point["stem"], point["filtration"]) == (stem + horizontal, filtration + vertical)]
        assert len(points) == 1, (page, pattern, horizontal, vertical, points)
        assert "0:0" in points[0]["ports"]
    for source, target, stem, filtration in [
        ("I00", "I11", 0, 0), ("I11", "I22H", 1, 1),
        ("I22H", "I33", 2, 2), ("I02", "I13", 0, 2),
    ]:
        assert any(edge["source"] == source and edge["target"] == target
                   and edge["status"] == "established"
                   and (edge["sourceGrade"]["stem"], edge["sourceGrade"]["filtration"])
                   == (stem + horizontal, filtration + vertical)
                   and (edge["targetGrade"]["stem"], edge["targetGrade"]["filtration"])
                   == (stem + horizontal + 1, filtration + vertical + 1)
                   for edge in row["relations"]), (page, source, target, horizontal, vertical)


def test_source_restoration_does_not_restore_d3_boundary_j_ideal(integer_chart_pages):
    def ports(page, pattern, stem, filtration):
        point = next(point for point in integer_chart_pages[page]["points"]
                     if (point["pattern"], point["stem"], point["filtration"])
                     == (pattern, stem, filtration))
        return set(point["ports"])

    # The integer d3 hits the positive-j part of h1^3 (not h1^3 itself).
    assert ports(3, "I33", 3, 3) == {"0:0", "0:1"}
    assert ports(4, "I33", 3, 3) == {"0:0"}
    assert ports(4, "I33", 67, 3) == {"0:0"}
    assert ports(4, "I11", 1, 1) == {"0:0", "0:1"}
    assert ports(4, "I22H", 2, 2) == {"0:0", "0:1"}
