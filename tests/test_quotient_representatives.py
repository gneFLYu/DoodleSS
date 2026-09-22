"""Synthetic quotient directions remain visible without editing saved classes."""
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def quotient_ui():
    script = r'''
const fs = require("node:fs"), vm = require("node:vm");
const elements = new Map();
const document = {body: {dataset: {}}, querySelector(selector) {
  if (!elements.has(selector)) elements.set(selector, {textContent: "", dataset: {}, setAttribute() {}, querySelectorAll() {return [];}});
  return elements.get(selector);
}};
const context = vm.createContext({document, window: {}});
for (const name of ["graded-quotient", "vector-page-algebra", "page-algebra", "cell-layout"])
  vm.runInContext(fs.readFileSync(`backend/static/${name}.js`, "utf8"), context);
context.window.HFPSSCellLayout = context.HFPSSCellLayout;
const source = fs.readFileSync("backend/static/app.js", "utf8");
vm.runInContext(source.slice(0, source.lastIndexOf('if (PAGE_MODE === "reviewing")')), context);
const output = vm.runInContext(`
const node = (id, label, stem, filtration, style) => ({id, label, grade: {stem,filtration},page:2,style});
const ws = {id:"test", page:2, classes:[
  node("a","xD",0,0,{e2_pattern:"A"}), node("b","yD",0,0,{e2_pattern:"B"}),
  node("sum","xD+yD",0,0,{e2_components:{A:1,B:1}}),
  node("decoy","z",0,0,{e2_pattern:"F"}),
  node("c","C",-1,3,{e2_pattern:"C"}), node("zeta-c","zeta C",-1,3,{e2_components:{C:2}})
], differentials:[
  {id:"da",source_id:"a",target_id:"c",page:3,status:"admitted",period_stem:64},
  {id:"db",source_id:"b",target_id:"zeta-c",page:3,status:"admitted",period_stem:64}
], propositions:[], cells:[], differential_maps:[], fates:[], settings:{rendering:{enumerated_e2_pattern:"integer",
  enumerated_horizontal_period:64,period_lattice:[{stem:64,filtration:0,exponent_domain:"integer"}]}}};
state.project={workspaces:[ws],period_families:[],page_period_cycles:[]}; state.workspaceId=ws.id;
const bounds={stemMin:0,stemMax:64,filtrationMin:0,filtrationMax:6};
const initial=periodicClassInstances(ws,bounds);
ws.page=4;
const before=JSON.stringify(state.project), points=periodicClassInstances(ws,bounds);
const computed=points.filter(p=>p.readOnlyRepresentative);
const algebra=pageAlgebra(ws,bounds);
const kernel={style:{e2_components:{A:1,B:3}}};
const actualSlots=algebra.endpointSlots(kernel,{stem:0,filtration:0});
dimensions=()=>({width:640,height:480}); viewportBounds=()=>bounds;
escapeHtml=value=>String(value).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
cellChartLayout=()=>new Map(); cellMapSvg=()=>""; cellGlyphSvg=()=>"";
drawingPeriodicityPreviewSvg=()=>""; renderMathInChart=()=>{};
let markup="", messages=[], ordinaryClicks=0;
replaceSvgMarkup=(_svg,text)=>{markup=text;}; toast=message=>messages.push(message);
onClassClick=()=>{ordinaryClicks++;};
periodicDifferentials=()=>[{diff:{id:"probe",source_id:"a",target_id:"c",page:4,status:"review"},
  sourceNode:kernel,targetNode:ws.classes[4],sourceGrade:{stem:0,filtration:0},targetGrade:{stem:-1,filtration:4}}];
renderChart();
const record=computed.find(p=>p.grade.stem===0);
const packed=packedClassInstances(ws,bounds,chartMetrics()).find(p=>p.instanceKey===record.instanceKey);
const expectedPoint=packedPoint(packed,chartMetrics());
const edge=markup.match(/data-differential="probe"[^>]*x1="([^"]+)" y1="([^"]+)"/);
const dataNode={dataset:{point:record.item.id,classInstance:record.instanceKey,readonlyRepresentative:"true"}};
for(const tool of ["inspect","delete","rename","differential","relation","class"]){
  state.tool=tool; state.connectionStart="a";
  document.querySelector("#chart").onclick({stopPropagation(){},target:{closest(s){return s==="[data-point]"?dataNode:null;}}});
}
document.querySelector("#chart").onkeydown({key:"Enter",preventDefault(){},stopPropagation(){},target:{closest(s){return s==="[data-point]"?dataNode:null;}}});
const unknown={...record,uncertain:true,size:3.6};
const partial=pageStatusText(ws,{conflicts:[{page:3,block:"A+B",reason:"outgoing map is only specified on a proper subspace"}]});
const patterns=new Map([["A",[ws.classes[0]]]]);
const seriesLabel=quotientRepresentativeLabel(ws,{grade:{stem:64,filtration:0},terms:[{pattern:"A",two:1,j:1,coefficient:2}]},patterns);
({initialCount:initial.filter(p=>p.grade.stem===0).length,
  computed:computed.map(p=>({label:p.item.label,id:p.item.id,slot:p.algebraSlots[0],grade:p.grade,terms:p.representativeTerms})),
  actualSlots,slotVisible:computed.some(p=>p.algebraSlots.includes(actualSlots[0])),
  edgeStart:edge&&[Number(edge[1]),Number(edge[2])],expectedPoint:[expectedPoint.x,expectedPoint.y],
  ordinaryClicks,messages,unchanged:before===JSON.stringify(state.project),connectionStart:state.connectionStart,
  readOnlyMarkup:markup.includes('data-readonly-representative="true"'),partial,
  uncertainGlyph:classGlyphMarkup(unknown,{x:0,y:0},"unknown"),seriesLabel,
  classClickGuard:${JSON.stringify(source.includes('state.drag || event.target.closest?.("[data-readonly-representative]")'))}})
`, context);
process.stdout.write(JSON.stringify(output));
'''
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True,
                            encoding="utf-8", capture_output=True, check=True)
    return json.loads(result.stdout)


def test_missing_kernel_line_gets_its_own_read_only_representative(quotient_ui):
    result = quotient_ui
    assert result["initialCount"] == 3  # A, B, and the unrelated F; not A+B again.
    assert len(result["computed"]) == 2  # D^8 copies at stems 0 and 64.
    assert result["computed"][0]["label"] == r"xD+\zeta^{2}\left(yD\right)"
    assert result["computed"][1]["label"] == r"xD^{9}+\zeta^{2}\left(yD^{9}\right)"
    assert all(point["id"].startswith("computed-quotient:") for point in result["computed"])
    assert result["slotVisible"] and result["readOnlyMarkup"]
    assert result["edgeStart"] == result["expectedPoint"]


def test_computed_points_cannot_mutate_or_connect_saved_classes(quotient_ui):
    assert quotient_ui["unchanged"]
    assert quotient_ui["ordinaryClicks"] == 0
    assert quotient_ui["connectionStart"] == "a"
    assert len(quotient_ui["messages"]) == 7
    assert all("Read-only" in message for message in quotient_ui["messages"])
    assert quotient_ui["classClickGuard"]


def test_partial_representatives_and_coefficient_tails_are_explicit(quotient_ui):
    assert "partial / unknown quotient" in quotient_ui["partial"]
    assert "a complete quotient is not claimed" in quotient_ui["partial"]
    assert "#d97706" in quotient_ui["uncertainGlyph"]
    assert quotient_ui["seriesLabel"] == r"2\zeta j\left(xD^{9}\right)".replace(" ", "")


def test_public_renderer_matches_backend():
    assert (ROOT / "backend/static/app.js").read_bytes() == (ROOT / "public/static/app.js").read_bytes()
