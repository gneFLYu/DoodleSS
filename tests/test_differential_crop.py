"""Viewport clipping must not remove long arrows whose sources are offscreen."""
import json
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.migrations import migrate_project
from domain.seed import demo_project


@pytest.fixture(scope="module")
def crop_audit():
    script = r'''
const fs=require("node:fs"),vm=require("node:vm");
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for(const name of ["graded-quotient","vector-page-algebra","page-algebra"])
  vm.runInContext(fs.readFileSync(`backend/static/${name}.js`,"utf8"),context);
const source=fs.readFileSync("backend/static/app.js","utf8");
vm.runInContext(source.slice(0,source.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.project=JSON.parse(fs.readFileSync(0,"utf8"));
const result=vm.runInContext(`
state.project=project;
const ws=project.workspaces.find(w=>w.id==="ws_integer");ws.page=23;
const bounds={stemMin:0,stemMax:63,filtrationMin:0,filtrationMax:32};
const cases={
  full:bounds,
  high:{...bounds,filtrationMin:14},
  targetOnly:{stemMin:56,stemMax:56,filtrationMin:14,filtrationMax:32},
  crossing:{stemMin:56,stemMax:57,filtrationMin:14,filtrationMax:20},
  nearMiss:{stemMin:56,stemMax:56.1,filtrationMin:1,filtrationMax:2}
};
const edges=Object.fromEntries(Object.entries(cases).map(([name,crop])=>[name,
  periodicDifferentials(ws,crop).map(edge=>({id:edge.diff.id,source:edge.sourceGrade,target:edge.targetGrade}))]));
const matrix=project.workspaces.find(w=>w.id==="ws_3sigma_i");matrix.page=5;
const matrixEdges=periodicDifferentials(matrix,{stemMin:6,stemMax:7,filtrationMin:3,filtrationMax:5})
  .map(edge=>({id:edge.diff.id,map:edge.diff.linear_map_id,source:edge.sourceGrade,target:edge.targetGrade}));
({edges,matrixEdges,
  horizontal:segmentIntersectsBounds({stem:-1,filtration:0},{stem:3,filtration:0},{stemMin:0,stemMax:2,filtrationMin:0,filtrationMax:2}),
  parallelOutside:segmentIntersectsBounds({stem:-1,filtration:3},{stem:3,filtration:3},{stemMin:0,stemMax:2,filtrationMin:0,filtrationMax:2})})
`,context);
process.stdout.write(JSON.stringify(result));
'''
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, encoding="utf-8",
                            input=json.dumps(asdict(migrate_project(demo_project()))),
                            capture_output=True, check=True)
    return json.loads(result.stdout)


def row_at(edges, row, stem, filtration):
    return next((edge for edge in edges if edge["id"] == f"published_diff_ws_integer_{row}"
                 and edge["source"]["stem"] == stem
                 and edge["source"]["filtration"] == filtration), None)


def test_high_filtration_crop_retains_all_three_d23_rows(crop_audit):
    for row, stem, filtration in ((22, 57, 1), (23, 18, 2), (24, 43, 3)):
        full = row_at(crop_audit["edges"]["full"], row, stem, filtration)
        cropped = row_at(crop_audit["edges"]["high"], row, stem, filtration)
        assert full is not None and cropped == full
        assert cropped["target"]["stem"] == stem - 1
        assert cropped["target"]["filtration"] == filtration + 23


def test_target_only_and_crossing_segments_are_visible_but_near_misses_are_not(crop_audit):
    for case in ("targetOnly", "crossing"):
        assert row_at(crop_audit["edges"][case], 22, 57, 1) is not None
    assert row_at(crop_audit["edges"]["nearMiss"], 22, 57, 1) is None
    assert crop_audit["horizontal"] and not crop_audit["parallelOutside"]


def test_periodic_matrix_backed_sum_arrow_uses_the_same_clipping(crop_audit):
    arrow = next(edge for edge in crop_audit["matrixEdges"] if edge["id"] == "diff_three_d5_sum")
    assert arrow["map"] == "linear_diff_three_d5_sum"
    assert (arrow["source"]["stem"], arrow["source"]["filtration"]) == (7, 1)
    assert (arrow["target"]["stem"], arrow["target"]["filtration"]) == (6, 6)
