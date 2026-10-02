"""Initial-page Thom patterns have the same ports, layout and line incidence.

Names and later differential data stay sector-specific. This tests the actual
browser rendering functions, not just a shared pattern-name setting.
"""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.migrations import migrate_project
from domain.seed import demo_project


RUNTIME = r"""
const fs = require('node:fs'), vm = require('node:vm');
const context = vm.createContext({document: {body: {dataset: {}}}, window: {}});
for (const name of ['graded-quotient', 'vector-page-algebra', 'page-algebra', 'display-basis', 'chart-presentation']) {
  vm.runInContext(fs.readFileSync(`backend/static/${name}.js`, 'utf8'), context);
}
context.window.HFPSSCellLayout = require(process.cwd() + '/backend/static/cell-layout.js');
const app = fs.readFileSync('backend/static/app.js', 'utf8');
vm.runInContext(app.slice(0, app.lastIndexOf('if (PAGE_MODE === "reviewing")')), context);
context.input = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = vm.runInContext(`
  state.project = input;
  input.grading_sectors.map(sector => {
    const ws = input.workspaces.find(w => w.id === sector.workspace_id);
    ws.page = 2;
    const shift = Number(ws.settings.atlas_transport?.stem_shift || 0);
    const bounds = {stemMin: shift, stemMax: shift + 63, filtrationMin: 0, filtrationMax: 7};
    const algebra = pageAlgebra(ws, bounds);
    const occurrences = periodicDifferentials(ws, bounds, [], algebra);
    const presentation = window.HFPSSChartPresentation.create(algebra, occurrences, bounds);
    const points = packedClassInstances(ws, bounds, {cell: 28}, [], presentation, algebra);
    const pointSlots = new Map();
    for (const point of points) {
      for (const slot of point.algebraSlots || []) pointSlots.set(slot, point);
      const scalarSlot = e2DisplaySlot(point.item, point.grade);
      if (scalarSlot) pointSlots.set(scalarSlot, point);
    }
    const describe = p => [p.grade.stem - shift, p.grade.filtration,
      p.item.style.e2_pattern, p.modulePorts, p.shape, p.dx, p.dy, p.size];
    const relations = periodicRelations(ws, new Set(liveClassesAt(ws).map(n => n.id)), bounds, algebra);
    const edges = [], missing = [];
    for (const relation of relations) {
      if (!inBounds(relation.sourceGrade, bounds) || !inBounds(relation.targetGrade, bounds)) continue;
      const branches = algebra.maps(relation.source, relation.target, relation.sourceGrade, relation.targetGrade);
      if (!branches.length) { missing.push(relation.proposition.id); continue; }
      const branch = branches[0];
      const a = presentation?.endpoint(relation.source, relation.sourceGrade, branch.two || 0, branch.j || 0);
      const b = presentation?.endpoint(relation.target, relation.targetGrade, branch.two || 0, branch.j || 0);
      const slots = (node, grade, endpoint) => {
        const vector = endpoint?.entries?.map(e => e.slot) || algebra.endpointSlots(node, grade);
        return vector.length ? vector : [e2DisplaySlot(node, grade)];
      };
      const from = slots(relation.source, relation.sourceGrade, a).map(s => pointSlots.get(s)).filter(Boolean);
      const to = slots(relation.target, relation.targetGrade, b).map(s => pointSlots.get(s)).filter(Boolean);
      if (!from.length || !to.length) missing.push(relation.proposition.id);
      edges.push([relation.sourceGrade.stem - shift, relation.sourceGrade.filtration,
        relation.targetGrade.stem - shift, relation.targetGrade.filtration,
        relation.source.style.e2_pattern, relation.target.style.e2_pattern,
        relation.proposition.conclusion.chart_connection?.kind,
        from.map(describe), to.map(describe)]);
    }
    return {id: ws.id, pattern: ws.settings.rendering.enumerated_e2_pattern,
      points: points.map(describe).sort((a,b) => JSON.stringify(a).localeCompare(JSON.stringify(b))),
      edges: [...new Set(edges.map(e => JSON.stringify(e)))].sort(), missing,
      differentialPages: [...new Set(ws.differentials.map(d => d.page))].sort((a,b) => a-b)};
  });
`, context);
process.stdout.write(JSON.stringify(result));
"""


@pytest.fixture(scope="module")
def actual_atlas_e2():
    project = migrate_project(demo_project())
    result = subprocess.run(
        ["node", "-e", RUNTIME], cwd=ROOT, input=json.dumps(asdict(project)),
        capture_output=True, text=True, encoding="utf-8", check=True, timeout=90,
    )
    return json.loads(result.stdout)


def test_all_sixteen_actual_e2_layouts_have_exactly_two_thom_patterns(actual_atlas_e2):
    assert len(actual_atlas_e2) == 16
    reference = {row["pattern"]: row for row in actual_atlas_e2
                 if row["id"] in {"ws_integer", "ws_sigma_i"}}
    for row in actual_atlas_e2:
        assert row["points"] == reference[row["pattern"]]["points"], row["id"]


def test_all_sixteen_e2_relations_connect_the_same_typed_ports(actual_atlas_e2):
    reference = {row["pattern"]: row for row in actual_atlas_e2
                 if row["id"] in {"ws_integer", "ws_sigma_i"}}
    for row in actual_atlas_e2:
        assert row["missing"] == [], row["id"]
        assert row["edges"] == reference[row["pattern"]]["edges"], row["id"]


def test_shared_e2_layout_does_not_copy_later_differentials(actual_atlas_e2):
    rows = {row["id"]: row for row in actual_atlas_e2}
    assert rows["ws_sigma_i"]["differentialPages"] != rows["ws_3sigma_i"]["differentialPages"]
    assert rows["ws_integer"]["differentialPages"] != rows["ws_2sigma_i"]["differentialPages"]


def test_all_atlas_circle_dot_h1_relations_follow_straight_diagonals(actual_atlas_e2):
    series_shapes = {"j-series", "j-positive-series", "witt-j-series"}
    for row in actual_atlas_e2:
        checked = 0
        for encoded in row["edges"]:
            edge = json.loads(encoded)
            if (edge[2] - edge[0], edge[3] - edge[1]) != (1, 1):
                continue
            for source in edge[7]:
                for target in edge[8]:
                    if source[4] not in series_shapes or target[4] not in series_shapes:
                        continue
                    # Screen y is negative filtration. Equal dx+dy means
                    # the endpoints lie on the same slope-minus-one line,
                    # even when either cell has additional finite summands.
                    assert source[5] + source[6] == pytest.approx(target[5] + target[6]), (row["id"], edge)
                    checked += 1
        assert checked > 0, row["id"]


def test_initial_packing_ignores_transported_names_and_anchor_status():
    script = r"""
const layout = require('./backend/static/cell-layout.js');
const make = (pattern, label, periodic) => ({key: label, label, periodic,
  cellKey: '2:2', e2CanonicalOrder: true, item: {style: {e2_pattern: pattern}},
  modulePorts: pattern === 'S22H' ? ['0:0', '0:1'] : ['0:0'], size: 3});
const first = [make('S22Y', 'a', false), make('S22H', 'z', true)];
const other = [make('S22H', 'a', false), make('S22Y', 'z', true)];
const positions = rows => layout.packInstances(rows, 28).map(p => [p.item.style.e2_pattern,p.dx,p.dy,p.size]);
process.stdout.write(JSON.stringify([positions(first),positions(other)]));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True,
                            text=True, check=True, timeout=20)
    first, other = json.loads(result.stdout)
    assert first == other
