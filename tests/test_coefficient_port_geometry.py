"""A compressed 2-tower has distinct, selectable coefficient endpoints."""
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def tower_rendering():
    setup = r'''
const fs = require("node:fs"), vm = require("node:vm");
const elements = new Map();
const document = {body: {dataset: {}}, querySelector(selector) {
  if (!elements.has(selector)) elements.set(selector, {
    textContent: "", dataset: {}, setAttribute() {}, querySelectorAll() {return [];}
  });
  return elements.get(selector);
}};
const context = vm.createContext({document, window: {}});
for (const name of ["graded-quotient", "vector-page-algebra", "page-algebra", "cell-layout",
                    "display-basis", "chart-presentation"])
  vm.runInContext(fs.readFileSync(`backend/static/${name}.js`, "utf8"), context);
context.window.HFPSSCellLayout = context.HFPSSCellLayout;
const source = fs.readFileSync("backend/static/app.js", "utf8");
vm.runInContext(source.slice(0, source.lastIndexOf('if (PAGE_MODE === "reviewing")')), context);
'''
    body = r'''
dimensions = () => ({width: 640, height: 480});
const bounds = {stemMin: 0, stemMax: 8, filtrationMin: 0, filtrationMax: 9};
viewportBounds = () => bounds;
escapeHtml = value => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
cellChartLayout = () => new Map(); cellMapSvg = () => ""; cellGlyphSvg = () => "";
drawingPeriodicityPreviewSvg = () => ""; renderMathInChart = () => {};
renderFateInspector = () => {}; toast = () => {};
let markup = "", clicks = [];
replaceSvgMarkup = (_svg, text) => { markup = text; };
onClassClick = (id, occurrence) => { clicks.push({id, port: occurrence.selectedPort,
  label: selectedPortLabel(occurrence), point: occurrence.point, payload: chartEndpointPayload(occurrence)}); };
const node = (id, label, stem, filtration, style) => ({id, label, expression: label,
  grade: {stem, filtration, representation: {}}, page: 2, style});
const base = node("tower", "kD", 4, 4, {e2_pattern: "I00"});
const doubled = node("double", "2kD", 4, 4, {e2_pattern: "I00", two_valuation: 1});
const quadrupled = node("quadruple", "4kD", 4, 4, {e2_pattern: "I00", two_valuation: 2});
const aliases = [base, doubled, quadrupled];
// Synthetic rank-one maps isolate SVG routing; they assert no Q8 theorem.
const targets = aliases.map((_, n) => node("target" + n, "t" + n, 3, 7, {e2_pattern: "T" + n}));
const sources = aliases.map((_, n) => node("source" + n, "s" + n, 1, 3, {e2_pattern: "R" + n}));
const ws = {id: "geometry", page: 3, classes: [...aliases, ...targets, ...sources],
  differentials: aliases.map((a, n) => ({id: "d-port" + n, source_id: a.id,
    target_id: targets[n].id, page: 3, status: "proven", period_stem: 64, coefficient_scope: "exact-port"})),
  propositions: aliases.map((a, n) => ({id: "r-port" + n, kind: "relation", status: "proven",
    conclusion: {source_id: sources[n].id, target_id: a.id, page: 2}})),
  cells: [], differential_maps: [], fates: [], settings: {rendering: {
    enumerated_e2_pattern: "integer", enumerated_horizontal_period: 64,
    period_lattice: [{stem: 64, filtration: 0, exponent_domain: "integer"}]}}};
state.project = {workspaces: [ws], period_families: [], page_period_cycles: []};
state.workspaceId = ws.id; state.tool = "inspect"; state.selectedClassId = null;
const before = JSON.stringify(state.project), metrics = chartMetrics();
const algebra = pageAlgebra(ws, bounds);
const occurrences = periodicDifferentials(ws, bounds, [], algebra);
const presentation = window.HFPSSChartPresentation.create(algebra, occurrences, bounds);
const packed = packedClassInstances(ws, bounds, metrics, [], presentation, algebra);
const tower = packed.find(p => p.item.id === "tower" && p.grade.stem === 4);
const points = ["0:0", "1:0", "2:0"].map(port => coefficientPortPoint(tower, metrics, port));
const center = packedPoint(tower, metrics);
renderChart();
const initialMarkup = markup;
const dataNode = {dataset: {point: "tower", classInstance: tower.instanceKey}};
for (const port of ["0:0", "1:0", "2:0"]) {
  const portNode = {dataset: {coefficientPort: port}};
  document.querySelector("#chart").onclick({stopPropagation() {}, target: {closest(selector) {
    return selector === "[data-point]" ? dataNode : selector === "[data-coefficient-port]" ? portNode : null;
  }}});
}
// The endpoint of the remaining 2/4 layer is its own lowest point, not the
// missing original layer and not the centre of the shortened tower.
const shortened = {...tower, modulePorts: ["1:0", "2:0"]};
({markup: initialMarkup, points, center, clicks, shape: tower.shape,
  defaultPoint: coefficientPortPoint(tower, metrics),
  shortenedDefault: coefficientPortPoint(shortened, metrics),
  shortenedFirst: coefficientPortPoint(shortened, metrics, "1:0"),
  unchanged: before === JSON.stringify(state.project)});
'''
    script = setup + "\nconst result = vm.runInContext(" + json.dumps(body) + ", context);\n"
    script += "process.stdout.write(JSON.stringify(result));"
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True,
                               text=True, encoding="utf-8", check=True, timeout=30)
    return json.loads(completed.stdout)


def _edge(markup, attribute, ident):
    root = ET.fromstring("<svg>" + markup + "</svg>")
    return next(node for node in root.iter("line") if node.get(attribute) == ident)


def test_finite_tower_coefficient_points_are_bottom_middle_top(tower_rendering):
    row = tower_rendering
    assert row["shape"] == "finite-two-tower"
    low, middle, high = row["points"]
    assert low["x"] == middle["x"] == high["x"]
    assert low["y"] > middle["y"] > high["y"]
    assert middle == row["center"]
    assert row["defaultPoint"] == low
    assert row["shortenedDefault"] == row["shortenedFirst"]


@pytest.mark.parametrize("level", [0, 1, 2])
def test_actual_differential_svg_uses_the_named_source_coefficient(tower_rendering, level):
    edge = _edge(tower_rendering["markup"], "data-differential", f"d-port{level}")
    point = tower_rendering["points"][level]
    assert [float(edge.get("x1")), float(edge.get("y1"))] == [point["x"], point["y"]]


@pytest.mark.parametrize("level", [0, 1, 2])
def test_actual_relation_svg_uses_the_named_target_coefficient(tower_rendering, level):
    edge = _edge(tower_rendering["markup"], "data-relation", f"r-port{level}")
    point = tower_rendering["points"][level]
    assert [float(edge.get("x2")), float(edge.get("y2"))] == [point["x"], point["y"]]


def test_tower_selection_names_and_payloads_preserve_two_valuations(tower_rendering):
    clicks = tower_rendering["clicks"]
    assert [click["label"] for click in clicks] == ["kD", "2kD", "4kD"]
    assert [click["port"] for click in clicks] == ["0:0", "1:0", "2:0"]
    assert [click["payload"]["two"] for click in clicks] == [0, 1, 2]
    assert [click["point"] for click in clicks] == tower_rendering["points"]
    assert tower_rendering["unchanged"]


def test_coefficient_dots_receive_pointer_events_in_local_and_deployed_css():
    # A group-level invisible hit target must not steal a click on 2a or 4a.
    # The generic .class-point rule disables pointer events; a real, more
    # specific descendant selector must re-enable them on coefficient dots.
    for directory in ("backend/static", "public/static"):
        css = (ROOT / directory / "style.css").read_text(encoding="utf-8")
        rule = re.search(r"\.class-point\s+\[data-coefficient-port\]\s*\{([^}]+)\}", css)
        assert rule is not None, directory
        assert re.search(r"pointer-events\s*:\s*all\s*;", rule.group(1)), directory
