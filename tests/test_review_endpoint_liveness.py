"""Review arrows cannot revive a typed boundary through a manual endpoint."""
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def endpoint_audit():
    script = r'''
const fs = require("node:fs"), vm = require("node:vm");
const context = vm.createContext({document: {body: {dataset: {}}}, window: {}});
for (const name of ["graded-quotient", "vector-page-algebra", "page-algebra"])
  vm.runInContext(fs.readFileSync(`backend/static/${name}.js`, "utf8"), context);
const app = fs.readFileSync("backend/static/app.js", "utf8");
vm.runInContext(app.slice(0, app.lastIndexOf('if (PAGE_MODE === "reviewing")')), context);
const output = vm.runInContext(`
const node = (id, stem, filtration, style = {}) => ({id, label: id, page: 2,
  grade: {stem, filtration}, style});
const bounds = {stemMin: -1, stemMax: 65, filtrationMin: 0, filtrationMax: 50};
function makeWorkspace({direction = "source", reviewPage = 23, value = null,
    power = 0, vector = false, series = false, manual = false, id = "audit"} = {}) {
  const boundaryFiltration = direction === "source" ? 3 : reviewPage + 3;
  const typed = vector ? {e2_components: {B: 1, C: 1}} : {e2_pattern: series ? "I11" : "B"};
  const boundary = node("boundary", 0, boundaryFiltration, typed);
  const early = node("early", 1, boundaryFiltration - 3, {e2_pattern: "A"});
  const other = direction === "source" ? node("manual", -1, boundaryFiltration + reviewPage)
    : node("manual", 1, boundaryFiltration - reviewPage);
  const source = direction === "source" ? boundary : other;
  const target = direction === "source" ? other : boundary;
  const ws = {id, page: 2, classes: [early, boundary, other], differentials: [
    {id: "early-d3", source_id: early.id, target_id: boundary.id, page: 3,
      status: "verified", period_stem: 64},
    {id: "review", source_id: source.id, target_id: target.id, page: reviewPage,
      status: "review", period_stem: 64, proposition_id: "review-claim"}
  ], propositions: [{id: "review-claim", kind: "differential", status: "review",
    conclusion: {coefficient_parameter: {id: "unit", domain: [1, 2, 3],
      value, frobenius_power: power}}}], cells: [], differential_maps: [], fates: [],
    settings: {rendering: {enumerated_e2_pattern: "integer", enumerated_horizontal_period: 64,
      period_lattice: [{stem: 64, filtration: 0, exponent_domain: "integer"}]}}};
  if (manual) {
    const independent = node("independent", boundary.grade.stem, boundary.grade.filtration);
    ws.classes.push(independent);
    ws.differentials[1][direction === "source" ? "source_id" : "target_id"] = independent.id;
  }
  if (series) {
    // A nonzero map from the constant layer to a j-torsion class leaves jR.
    early.grade = {stem: -1, filtration: boundaryFiltration + 3};
    ws.differentials[0].source_id = boundary.id;
    ws.differentials[0].target_id = early.id;
  }
  state.project = {workspaces: [ws], period_families: [], page_period_cycles: []};
  state.workspaceId = ws.id;
  return ws;
}
function inspect(ws, page) {
  ws.page = page;
  const original = JSON.stringify(ws), algebra = pageAlgebra(ws, bounds), boundary = ws.classes[1];
  const edges = periodicDifferentials(ws, bounds).map(e => ({id: e.diff.id,
    status: e.diff.status, source: e.sourceGrade, target: e.targetGrade}));
  const points = periodicClassInstances(ws, bounds);
  return {page, edges, live: algebra.live(boundary, boundary.grade),
    maps: algebra.maps(boundary, boundary, boundary.grade, boundary.grade).length,
    ports: [...(algebra.ports(boundary, boundary.grade) || [])],
    coefficient: algebra.coefficientState(ws.differentials.find(d => d.id === "review")),
    boundaryDot: points.some(p => p.item.id === boundary.id
      && p.grade.stem === boundary.grade.stem && p.grade.filtration === boundary.grade.filtration),
    blocked: algebra.blockedFromPage, conflicts: algebra.conflicts,
    unchanged: original === JSON.stringify(ws)};
}
const cases = [];
for (const direction of ["source", "target"]) for (const vector of [false, true])
  for (const [value, power] of [[null, 0], [2, 0], [2, 1]]) {
    const ws = makeWorkspace({direction, value, power, vector});
    cases.push({direction, vector, value, power, pages: [2, 3, 4, 23, 24].map(p => inspect(ws, p))});
  }
const timing = [];
for (const direction of ["source", "target"]) for (const reviewPage of [2, 3, 4]) {
  const ws = makeWorkspace({direction, reviewPage});
  timing.push({direction, reviewPage, result: inspect(ws, reviewPage)});
}
const controls = [];
for (const direction of ["source", "target"]) for (const manual of [false, true]) {
  const ws = makeWorkspace({direction, manual});
  if (!manual) ws.differentials = ws.differentials.filter(d => d.id !== "early-d3");
  controls.push({direction, manual, pages: [22, 23, 24].map(p => inspect(ws, p))});
}
const acceptedManual = [];
for (const direction of ["source", "target"]) {
  const ws = makeWorkspace({direction, manual: true, value: 1});
  ws.differentials[1].status = ws.propositions[0].status = "verified";
  acceptedManual.push({direction, pages: [22, 23, 24].map(p => inspect(ws, p))});
}
const seriesWorkspace = makeWorkspace({series: true});
const series = inspect(seriesWorkspace, 23);
const atlas = [];
for (let a = 0; a < 4; a++) for (let b = 0; b < 4; b++) {
  const ws = makeWorkspace({id: "q8-ro-a" + a + "-b" + b, power: b % 2});
  // Synthetic grading shells test display independence, not a new transport theorem.
  for (const c of ws.classes) c.grade.rep = "-" + a + "sigma_i-" + b + "sigma_j";
  atlas.push({id: ws.id, result: inspect(ws, 23)});
}
({cases, timing, controls, acceptedManual, series, atlas});
`, context);
process.stdout.write(JSON.stringify(output));
'''
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True,
                            encoding="utf-8", capture_output=True, check=True, timeout=30)
    return json.loads(result.stdout)


@pytest.mark.parametrize("direction", ["source", "target"])
@pytest.mark.parametrize("vector", [False, True])
def test_review_d23_never_uses_an_earlier_boundary(endpoint_audit, direction, vector):
    cases = [c for c in endpoint_audit["cases"] if c["direction"] == direction and c["vector"] == vector]
    assert len(cases) == 3
    for case in cases:
        for result in case["pages"]:
            assert result["blocked"] is None and not result["conflicts"]
            assert result["unchanged"]
            assert result["live"] is (result["page"] <= 3)
            assert bool(result["maps"]) is (result["page"] <= 3)
            if result["page"] > 3:
                assert not result["boundaryDot"]
            assert not any(edge["id"] == "review" for edge in result["edges"])
            early_edges = [edge for edge in result["edges"] if edge["id"] == "early-d3"]
            assert bool(early_edges) is (result["page"] == 3)
            if early_edges:
                assert {edge["target"]["stem"] for edge in early_edges} == {0, 64}
        coefficient = case["pages"][-2]["coefficient"]
        assert coefficient["resolved"] is (case["value"] is not None)
        if coefficient["resolved"]:
            assert coefficient["value"] == (3 if case["power"] else 2)


@pytest.mark.parametrize("direction", ["source", "target"])
def test_review_endpoint_remains_available_before_and_on_its_boundary_page(endpoint_audit, direction):
    cases = [c for c in endpoint_audit["timing"] if c["direction"] == direction]
    assert {c["reviewPage"] for c in cases} == {2, 3, 4}
    for case in cases:
        edges = [e for e in case["result"]["edges"] if e["id"] == "review"]
        assert bool(edges) is (case["reviewPage"] <= 3)
        assert all(e["status"] == "review" for e in edges)
        assert case["result"]["unchanged"]


def test_legitimate_manual_and_mixed_review_arrows_remain_page_local(endpoint_audit):
    assert len(endpoint_audit["controls"]) == 4
    for case in endpoint_audit["controls"]:
        for result in case["pages"]:
            edges = [e for e in result["edges"] if e["id"] == "review"]
            assert bool(edges) is (result["page"] == 23)
            assert all(e["status"] == "review" for e in edges)
            if edges:
                assert {e["source"]["stem"] for e in edges} == ({0, 64} if case["direction"] == "source" else {1, 65})
            assert result["unchanged"]


def test_a_surviving_completed_ideal_is_not_confused_with_its_absent_constant(endpoint_audit):
    result = endpoint_audit["series"]
    assert result["blocked"] is None and not result["conflicts"]
    assert not result["live"]
    assert result["ports"] == ["0:1"]
    assert result["maps"] and result["boundaryDot"]
    assert any(e["id"] == "review" for e in result["edges"])
    assert result["unchanged"]


def test_verified_manual_arrows_keep_their_status_and_page(endpoint_audit):
    assert len(endpoint_audit["acceptedManual"]) == 2
    for case in endpoint_audit["acceptedManual"]:
        for result in case["pages"]:
            edges = [e for e in result["edges"] if e["id"] == "review"]
            assert bool(edges) is (result["page"] == 23)
            assert all(e["status"] == "verified" for e in edges)
            assert result["unchanged"]


def test_all_sixteen_synthetic_grading_shells_and_d8_copies_filter_boundaries(endpoint_audit):
    rows = endpoint_audit["atlas"]
    assert {row["id"] for row in rows} == {f"q8-ro-a{a}-b{b}" for a in range(4) for b in range(4)}
    for row in rows:
        result = row["result"]
        assert not result["maps"] and not result["boundaryDot"]
        assert not any(edge["id"] == "review" for edge in result["edges"])
        assert result["unchanged"]


def test_public_renderer_matches_backend():
    assert (ROOT / "backend/static/app.js").read_bytes() == (ROOT / "public/static/app.js").read_bytes()
