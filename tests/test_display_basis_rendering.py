"""The real SVG renderer uses exact, read-only adapted display coordinates."""
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rendered():
    setup = r'''
const fs = require("node:fs"), vm = require("node:vm");
const elements = new Map();
const document = {body: {dataset: {}}, querySelector(selector) {
  if (!elements.has(selector)) elements.set(selector, {
    textContent: "", dataset: {}, setAttribute() {}, querySelectorAll() { return []; }
  });
  return elements.get(selector);
}};
const context = vm.createContext({document, window: {}});
for (const name of ["graded-quotient", "vector-page-algebra", "page-algebra", "cell-layout",
                    "display-basis", "chart-presentation"])
  vm.runInContext(fs.readFileSync("backend/static/" + name + ".js", "utf8"), context);
context.window.HFPSSCellLayout = context.HFPSSCellLayout;
const source = fs.readFileSync("backend/static/app.js", "utf8");
vm.runInContext(source.slice(0, source.lastIndexOf('if (PAGE_MODE === "reviewing")')), context);
'''
    body = r'''
const viewBounds = {stemMin:0, stemMax:10, filtrationMin:0, filtrationMax:6};
dimensions = () => ({width:640, height:480});
viewportBounds = () => viewBounds;
escapeHtml = value => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
cellChartLayout = () => new Map(); cellMapSvg = () => ""; cellGlyphSvg = () => "";
drawingPeriodicityPreviewSvg = () => ""; renderMathInChart = () => {};
renderFateInspector = () => {};
let markup = "", messages = [], ordinaryClicks = 0;
replaceSvgMarkup = (_svg, text) => { markup = text; };
toast = message => messages.push(message);
onClassClick = () => { ordinaryClicks++; };
const node = (id, label, stem, filtration, style) => ({
  id, label, expression:label, grade:{stem, filtration, representation:{}}, page:2, style
});
const pLabel = "\\{xh_1v_1+yh_2\\}kDu_{3\\sigma_i}";
const qLabel = "\\{xh_1v_1+h_1^2\\}kDu_{3\\sigma_i}";
function renderCase(value, mode = "constant") {
  const patterns = mode === "positive-j" ? ["I33","I11","I51"]
    : ["higher-two","constant-and-two"].includes(mode) ? ["S00","I00","S40"] : ["A","P","Q"];
  const [A,P,Q] = patterns;
  const a = node("a", "a", 6, 0, {e2_pattern:A});
  const p = node("p", pLabel, 5, 3, {e2_pattern:P});
  const q = node("q", qLabel, 5, 3, {e2_pattern:Q});
  const sum = node("sum", "(" + pLabel + ")+(" + qLabel + ")", 5, 3, {e2_components:{[P]:1,[Q]:1}});
  const scaled = node("scaled", "scaled target", 5, 3,
    {e2_components:{[P]:2,[Q]:f4DisplayMultiply(2,value)}});
  const ws = {id:"test-" + value + "-" + mode, grading_label:"synthetic", page:3, classes:[a,p,q,sum,scaled],
    differentials:[{id:"incoming",source_id:"a",target_id:"sum",page:3,
      status:"proven",proposition_id:"claim",period_stem:64}],
    propositions:[
      {id:"claim",kind:"differential",status:"proven",conclusion:{coefficient_parameter:{
        id:"b",symbol:"b",value,domain:[1,2,3],frobenius_power:0,target_component:Q}}},
      {id:"to-Q",kind:"relation",status:"proven",statement:"r(a)=Q",
        conclusion:{source_id:"a",target_id:"q",page:3}},
      {id:"to-scaled",kind:"relation",status:"proven",statement:"s(a)=zeta target",
        conclusion:{source_id:"a",target_id:"scaled",page:3}}
    ], cells:[],differential_maps:[],fates:[],settings:{rendering:{
      enumerated_e2_pattern:"integer",enumerated_horizontal_period:64,
      period_lattice:[{stem:64,filtration:0,exponent_domain:"integer"}]}}};
  // Actual exact-port d2 rows remove the lower layers. No fixture changes
  // the computed quotient or stubs its live-branch/admission decisions.
  let previous = 0;
  function removePort(base, two, j, outgoing) {
    const id = "prior-" + previous++;
    const alias = node(id + "-alias", base.label, base.grade.stem, base.grade.filtration,
      {...base.style,two_valuation:two,j_order:j});
    const other = node(id + "-other", id, base.grade.stem + (outgoing ? -1 : 1),
      base.grade.filtration + (outgoing ? 2 : -2), {e2_pattern:"T" + previous});
    ws.classes.push(alias, other);
    ws.differentials.push({id,page:2,status:"proven",period_stem:64,coefficient_scope:"exact-port",
      source_id:outgoing ? alias.id : other.id,target_id:outgoing ? other.id : alias.id});
  }
  if (mode === "positive-j") {
    removePort(a,0,0,true); removePort(p,0,0,false); removePort(q,0,0,false);
  } else if (["higher-two","constant-and-two"].includes(mode)) {
    for (const [two,j] of [[0,0],[2,0],[3,0],[0,1],[1,1],[2,1],[3,1]])
      if (mode === "higher-two" || two || j) removePort(a,two,j,true);
    for (const [two,j] of [[0,0],[2,0],[0,1]])
      if (mode === "higher-two" || two || j) removePort(p,two,j,false);
    for (const [two,j] of [[0,0],[0,1]])
      if (mode === "higher-two" || two || j) removePort(q,two,j,false);
    if (mode === "constant-and-two") ws.differentials[0].coefficient_scope = "exact-port";
  }
  state.project = {workspaces:[ws],period_families:[],page_period_cycles:[]};
  state.workspaceId = ws.id; state.selectedClassId = null; state.selectedOccurrence = null;
  state.selectedQuotientInstance = null; state.selectedCombinationKey = null;
  state.connectionStart = null; state.tool = "inspect";
  messages = []; ordinaryClicks = 0;
  const projectBefore = JSON.stringify(state.project);
  const algebra = pageAlgebra(ws, viewBounds);
  const occurrences = periodicDifferentials(ws, viewBounds);
  const incoming = occurrences.find(edge => edge.diff.id === "incoming" && edge.sourceGrade.stem === 6);
  if (!incoming) throw Error("The real coefficient-aware differential occurrence is missing");
  const presentation = window.HFPSSChartPresentation.create(algebra, occurrences, viewBounds);
  const branch = algebra.maps(incoming.sourceNode,incoming.targetNode,incoming.sourceGrade,incoming.targetGrade)
    .find(branch => window.HFPSSPageAlgebra.allowsConstraintBranch(incoming.diff,branch.two || 0,branch.j || 0));
  if (!branch) throw Error("The actual incoming differential has no surviving coefficient branch");
  const endpoint = presentation.endpoint(incoming.targetNode, incoming.targetGrade, branch.two || 0, branch.j || 0);
  const targetSlot = endpoint.entries[0].slot;
  const packed = packedClassInstances(ws, viewBounds, chartMetrics(), [], presentation);
  const targetRecord = packed.find(record => record.algebraSlots?.includes(targetSlot));
  if (!targetRecord) throw Error("The adapted incoming target has no rendered basis record");
  const targetPoint = packedPoint(targetRecord, chartMetrics());
  const sourceRecord = packed.find(record => record.item.id === "a" && record.grade.stem === 6);
  const sourcePoint = packedPoint(sourceRecord, chartMetrics());
  const targetRecords = packed.filter(record => record.grade.stem === 5 && record.grade.filtration === 3);
  const targetPoints = targetRecords.map(record => packedPoint(record, chartMetrics()));
  const blocksBefore = JSON.stringify([...algebra.vectorBlocks.values()].map(block => block.q));
  renderChart();
  const initialMarkup = markup;
  const combination = initialMarkup.match(/data-combination-endpoint="([^"]+)"/);
  if (!combination) throw Error("The dependent Q direction has no exact combination port");
  const combinationNode = {dataset:{combinationEndpoint:combination[1]}};
  document.querySelector("#chart").onclick({
    stopPropagation() {}, target:{closest(selector) {
      return selector === "[data-combination-endpoint]" ? combinationNode : null;
    }}
  });
  const selectedCombinationMarkup = markup;
  if (targetRecord.readOnlyRepresentative) {
    const dataNode = {dataset:{point:targetRecord.item.id,classInstance:targetRecord.instanceKey,
      readonlyRepresentative:"true"}};
    for (const tool of ["inspect","delete","rename","differential","relation","class"]) {
      state.tool = tool;
      document.querySelector("#chart").onclick({
        stopPropagation() {}, target:{closest(selector) { return selector === "[data-point]" ? dataNode : null; }}
      });
    }
  }
  return {value,mode,branch:[branch.two || 0,branch.j || 0],markup:initialMarkup,selectedCombinationMarkup,targetKey:targetRecord.instanceKey,
    targetLabel:periodicDisplayLabel(targetRecord),targetCoordinates:endpoint.coordinates,
    targetPoint:[targetPoint.x,targetPoint.y],targetPoints:targetPoints.map(point => [point.x,point.y]),
    sourcePoint:[sourcePoint.x,sourcePoint.y],
    records:targetRecords.map(record => ({id:record.item.id,key:record.instanceKey,
      label:periodicDisplayLabel(record),storedLabel:record.item.label,ports:record.modulePorts})),
    targetDots:targetRecords.length,dimension:endpoint.block.q.dimension,
    qCoordinates:presentation.endpoint(q,q.grade,branch.two || 0,branch.j || 0).coordinates,
    scaledCoordinates:presentation.endpoint(scaled,scaled.grade,branch.two || 0,branch.j || 0).coordinates,
    targetReadOnly:!!targetRecord.readOnlyRepresentative,ordinaryClicks,messages,
    projectUnchanged:projectBefore === JSON.stringify(state.project),
    quotientUnchanged:blocksBefore === JSON.stringify([...algebra.vectorBlocks.values()].map(block => block.q))};
}
[renderCase(2), renderCase(1), renderCase(2,"positive-j"), renderCase(2,"higher-two"),
 renderCase(2,"constant-and-two")];
'''
    script = setup + "\nconst output = vm.runInContext(" + json.dumps(body) + ", context);\n"
    script += "process.stdout.write(JSON.stringify(output));"
    completed = subprocess.run(
        ["node", "--max-old-space-size=128", "-e", script],
        cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=True, timeout=25,
    )
    return {case["value"] if case["mode"] == "constant" else case["mode"]: case
            for case in json.loads(completed.stdout)}


def svg(case, selected=False):
    return ET.fromstring("<svg>" + case["selectedCombinationMarkup" if selected else "markup"] + "</svg>")


def by_attribute(tree, attribute, value):
    matches = [element for element in tree.iter() if element.get(attribute) == value]
    assert len(matches) == 1, (attribute, value, len(matches))
    return matches[0]


def point(element, x="x", y="y"):
    return [float(element.get(x)), float(element.get(y))]


def test_resolved_relative_target_is_one_classic_arrow_to_a_basis_dot(rendered):
    case = rendered[2]
    tree = svg(case)
    edge = by_attribute(tree, "data-differential", "incoming")
    target = by_attribute(tree, "data-class-instance", case["targetKey"])
    hit = next(element for element in target if element.get("class") == "class-hit-target")
    assert point(edge, "x2", "y2") == point(hit, "cx", "cy") == case["targetPoint"]
    assert case["targetCoordinates"] == [1, 0]
    assert case["targetDots"] == case["dimension"] == 2
    assert target.get("data-readonly-representative") == "true"
    assert r"\zeta" in target.get("aria-label")


def test_relative_parameter_is_not_misrepresented_as_an_overall_arrow_scalar(rendered):
    for case in rendered.values():
        assert not any(element.get("data-coefficient-for") == "incoming" for element in svg(case).iter())
        assert r"\text{vector}" not in case["markup"]


def test_legacy_equal_coefficient_target_cancels_repeated_monomials_in_real_svg(rendered):
    case = rendered[1]
    expected = r"\left(yh_2+h_1^{2}\right)kDu_{3\sigma_i}"
    assert case["targetLabel"] == expected
    target = by_attribute(svg(case), "data-class-instance", case["targetKey"])
    assert expected in target.get("aria-label")
    assert "xh_1v_1" not in target.get("aria-label")
    assert case["targetDots"] == case["dimension"] == 2


def test_other_relation_uses_exact_combination_port_not_an_unweighted_centroid(rendered):
    case = rendered[2]
    tree = svg(case)
    edge = by_attribute(tree, "data-relation", "to-Q")
    combinations = [element for element in tree.iter() if element.get("class") == "combination-endpoint"]
    assert len(combinations) == 1
    port = combinations[0]
    mark = port.find("text")
    assert mark.text == "Σ"
    assert point(edge, "x2", "y2") == point(mark)
    centroid = [sum(pair[axis] for pair in case["targetPoints"]) / 2 for axis in (0, 1)]
    assert point(mark) != centroid
    assert case["qCoordinates"] == [3, 3]
    assert r"displayed-basis coordinates [\zeta^{2}, \zeta^{2}]" in port.find("title").text
    assert "not an extra basis generator" in port.find("title").text
    selected = svg(case, selected=True)
    assert any(element.get("class") == "selected-bidegree" for element in selected.iter())


def test_nontrivial_one_hot_relation_scalar_is_retained_at_arrow_midpoint(rendered):
    case = rendered[2]
    tree = svg(case)
    edge = by_attribute(tree, "data-relation", "to-scaled")
    badge = by_attribute(tree, "data-coefficient-for", "to-scaled")
    assert case["scaledCoordinates"] == [2, 0]
    assert point(edge, "x2", "y2") == case["targetPoint"]
    assert badge.get("data-coefficient") == "2"
    assert next(iter(badge)).get("data-latex") == r"\zeta"
    assert point(badge) == [(float(edge.get("x1")) + float(edge.get("x2"))) / 2,
                            (float(edge.get("y1")) + float(edge.get("y2"))) / 2]


def test_render_and_combination_inspection_do_not_mutate_saved_equations_or_quotient(rendered):
    for case in rendered.values():
        assert case["projectUnchanged"] and case["quotientUnchanged"]
        assert case["ordinaryClicks"] == 0
    assert rendered[2]["targetReadOnly"]
    assert len([message for message in rendered[2]["messages"] if "Read-only" in message]) == 6


@pytest.mark.parametrize("mode,branch", [("positive-j", [0, 1]), ("higher-two", [1, 0])])
def test_actual_surviving_two_or_j_branch_connects_both_rendered_endpoints(rendered, mode, branch):
    case = rendered[mode]
    tree = svg(case)
    edge = by_attribute(tree, "data-differential", "incoming")
    target = by_attribute(tree, "data-class-instance", case["targetKey"])
    hit = next(element for element in target if element.get("class") == "class-hit-target")
    assert case["branch"] == branch
    assert point(edge, "x1", "y1") == case["sourcePoint"]
    assert point(edge, "x2", "y2") == point(hit, "cx", "cy") == case["targetPoint"]
    assert case["targetCoordinates"] == [1, 0]
    assert case["targetDots"] == case["dimension"] == 2
    assert case["projectUnchanged"] and case["quotientUnchanged"]
    assert case["ordinaryClicks"] == 0 and case["targetReadOnly"]
    assert not any(element.get("data-coefficient-for") == "incoming" for element in tree.iter())


def test_named_point_owned_only_by_two_layer_keeps_integer_multiple_exactly_once(rendered):
    case = rendered["constant-and-two"]
    q = next(record for record in case["records"] if record["id"] == "q")
    assert q["ports"] == ["1:0"]
    assert q["storedLabel"] == r"\{xh_1v_1+h_1^2\}kDu_{3\sigma_i}"
    assert q["label"] == r"2\left(\{xh_1v_1+h_1^2\}kDu_{3\sigma_i}\right)"
    target = by_attribute(svg(case), "data-class-instance", q["key"])
    assert target.get("aria-label").startswith(q["label"] + " at ")
    assert case["dimension"] == 4  # Two F4 residue ports for each of P and Q.
    assert case["projectUnchanged"] and case["quotientUnchanged"]


def test_presentation_scripts_are_loaded_in_order_and_static_twins_match():
    template = (ROOT / "backend/templates/index.html").read_text(encoding="utf-8")
    names = ["graded-quotient", "display-basis", "chart-presentation", "app"]
    offsets = [template.index(name + ".js") for name in names]
    assert offsets == sorted(offsets)
    for name in ["display-basis", "chart-presentation", "app"]:
        assert (ROOT / ("backend/static/" + name + ".js")).read_bytes() == (
            ROOT / ("public/static/" + name + ".js")).read_bytes()
