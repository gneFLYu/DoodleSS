"""The completed 2-BSS chart shows coefficient modules, not sampled j dots."""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET

import pytest

from test_bss_window_ui import render_bss_payloads, runtime
from test_chart_display_conventions import app_helper


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.bss_completed import build_bss_completed_chart
from domain.bss_reference import create_bss_reference_workspaces


@pytest.fixture(scope="module")
def completed_rendering():
    workspaces = {ws.id: asdict(ws) for ws in create_bss_reference_workspaces()}
    inputs = []
    for sector in ("integer", "sigma"):
        for page in (1, 2, 3, 4):
            for projection in ("cohomology", "bockstein"):
                payload = build_bss_completed_chart(sector, page, 0, 4, 2, projection=projection)
                inputs.append({"payload": payload, "workspace": workspaces[payload["workspace_id"]],
                    "bounds": {"stemMin": -1, "stemMax": 9, "filtrationMin": 0, "filtrationMax": 8}})
    return render_bss_payloads(inputs)


def test_completed_loader_has_no_finite_v1_cap():
    result = runtime("""
      const ws=workspace();prepareBssWindow(ws);requests[0].resolve(payload(0));await flush();
      return {path:requests[0].path,window:ws.settings.bss_computed_window.window};
    """)
    assert "/completed-chart?" in result["path"]
    assert "v1_max" not in result["path"] and "v1_max" not in result["window"]
    assert result["window"]["h0_max"] == 2
    template = (ROOT / "backend/templates/index.html").read_text(encoding="utf-8")
    assert 'name="v1_max"' not in template
    assert "Free does not mean every differential is zero" in template


def test_real_free_modules_are_circle_dots_and_j_annihilated_modules_are_dots(completed_rendering):
    seen = set()
    for case in completed_rendering:
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        nodes = {n["id"]: n for n in case["nodes"]}
        assert "NaN" not in case["markup"] and "undefined" not in case["markup"]
        for group in xml.iter("g"):
            if "data-point" not in group.attrib:
                continue
            node = nodes[group.get("data-point")]
            module = node["style"].get("bss_j_module")
            if not module:
                continue
            seen.add((case["sector"], module["kind"]))
            assert group.get("data-bss-j-module") == module["kind"]
            assert group.get("data-bss-j-min") == str(module["j_min"])
            assert group.get("data-bockstein-filtration") == str(node["style"]["bockstein_filtration"])
            classes = [n.get("class", "").split() for n in group.iter()]
            assert any("series-core" in c for c in classes) == (module["kind"] == "free")
            assert any("dot-glyph" in c for c in classes) == (module["kind"] == "torsion")
            assert not any("j-positive-series" in c or "finite-two-tower" in c for c in classes)
    assert seen == {(sector, kind) for sector in ("integer", "sigma") for kind in ("free", "torsion")}


def test_completed_h0_levels_and_dependent_vectors_never_merge(completed_rendering):
    for case in completed_rendering:
        positions = {}
        for record in case["points"]:
            cell = (record["grade"]["stem"], record["grade"]["filtration"])
            point = (record["point"]["x"], record["point"]["y"])
            assert point not in positions.setdefault(cell, set())
            positions[cell].add(point)
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        glyphs = {g.get("data-point"): g for g in xml.iter("g") if g.get("data-point")}
        for node in case["nodes"]:
            if node["style"].get("bss_combination") and node["id"] in glyphs:
                assert any(n.text == "Σ" for n in glyphs[node["id"]].iter("text"))
                assert not any("series-core" in n.get("class", "") for n in glyphs[node["id"]].iter())


def test_exact_j_badges_do_not_use_f4_scalar_or_boolean_j_ports(completed_rendering):
    found = 0
    for case in completed_rendering:
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        claims = {p["id"]: p for p in case["propositions"]}
        by_edge = {p["id"]: p for p in case["propositions"] if p["kind"] == "relation"}
        by_edge.update({d["id"]: claims[d["proposition_id"]] for d in case["differentials"]})
        for badge in xml.iter("foreignObject"):
            if badge.get("data-coefficient-kind") != "bss-j-adic":
                continue
            found += 1
            con = by_edge[badge.get("data-coefficient-for")]["conclusion"]
            label = next(iter(badge))
            assert label.get("data-latex") == con["bss_j_coefficient_tex"]
            assert badge.get("data-coefficient") is None
            if label.get("data-bss-j-target"):
                assert int(label.get("data-bss-j-power")) == con["bss_j_target_power"]
                assert label.get("role") == "button" and label.get("tabindex") == "0"
                if con.get("bss_j_target_label_tex"):
                    assert label.get("data-bss-j-label"), "Actual target must use the engine-collected label"
    assert found > 0


def test_completed_arrows_hit_the_real_h0_module_endpoint(completed_rendering):
    for case in completed_rendering:
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        points = {(r["id"], r["grade"]["stem"], r["grade"]["filtration"]): r["point"] for r in case["points"]}
        occurrences = {}
        for item in case["arrowOccurrences"]:
            occurrences.setdefault(item["id"], []).append(item)
        for line in xml.iter("line"):
            if not line.get("data-differential"):
                continue
            # Occurrences of one seed are distinguished by their actual packed source.
            matches = []
            for item in occurrences[line.get("data-differential")]:
                source = points.get((item["sourceId"], item["sourceGrade"]["stem"], item["sourceGrade"]["filtration"]))
                if source and float(line.get("x1")) == pytest.approx(source["x"]) and float(line.get("y1")) == pytest.approx(source["y"]):
                    matches.append(item)
            if not matches:  # Source beyond the viewport; no visible glyph to compare.
                continue
            item = matches[0]
            target = points.get((item["targetId"], item["targetGrade"]["stem"], item["targetGrade"]["filtration"]))
            if target:
                assert float(line.get("x2")) == pytest.approx(target["x"])
                assert float(line.get("y2")) == pytest.approx(target["y"])


def test_selected_j_power_is_relative_to_the_already_scaled_generator():
    actual = app_helper(["periodicDisplayLabel", "shiftDExponent", "shiftPeriodFactor", "latexPower", "selectedPortLabel"], """
      selectedPortLabel({item:{label:'v_1^{6}D^{-1}h_0^{2}',style:{bss_j_module:{kind:'free',j_min:1}}},
        horizontalExponent:2,selectedJPower:3})
    """)["result"]
    assert actual == r"j^{3}\{v_1^{6}Dh_0^{2}\}"
    # j_min is already in v1^6 D^-1: it must not be multiplied into the label again.
    assert "j^{4}" not in actual


def test_selected_nonconstant_j_element_does_not_highlight_lowest_family_generators():
    actual = app_helper(["classFamilySelection"], """(() => {
      const chosen={id:'a',style:{bss_j_module:{kind:'free'},bss_periodic_family_key:'family'}};
      globalThis.state={selectedClassId:'a',selectedOccurrence:{instanceKey:'a:0:0',selectedJPower:2}};
      const ws={spectral_sequence:'2-bss',classes:[chosen]};
      return ['a:0:0','a:8:0','b:20:4'].map(instanceKey => classFamilySelection(ws,
        {instanceKey,item:{id:'b',style:{bss_j_module:{kind:'free'},bss_periodic_family_key:'family'}}},chosen).selected);
    })()""")["result"]
    assert actual == [True, False, False]


@pytest.mark.parametrize("collected", [False, True])
def test_click_and_refresh_keep_exact_relative_j_power_and_h0(collected):
    script = r"""
const fs=require('fs'),vm=require('vm');
const source=fs.readFileSync('backend/static/app.js','utf8');
const collected=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({window:{},document:{body:{dataset:{}}},collected});
vm.runInContext(source.slice(0,source.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
Promise.resolve(vm.runInContext(`(async()=>{
 const item={id:'module',label:'v_1^{6}D^{-1}h_0^{2}',style:{bss_j_module:{kind:'free',j_min:1,length:null},bockstein_filtration:2}};
 const ws={id:'ws_q8_bss_integer',page:3,spectral_sequence:'2-bss',settings:{source_reference:true},classes:[item]};
 state.project={workspaces:[ws]};state.workspaceId=ws.id;state.tool='inspect';
 renderFateInspector=()=>{};renderPersistentPeriodicityTool=()=>{};renderChart=()=>{};toast=()=>{};fateFor=()=>null;
 const record={item,instanceKey:'copy',grade:{stem:20,filtration:0},horizontalExponent:2,selectedJPower:3};
 if(collected)record.selectedJLabel='v_1^{18}D^{-2}h_0^{2}';
 periodicClassInstances=()=>[{...record,selectedJPower:undefined,selectedJLabel:undefined}];
 await onClassClick(item.id,record);
 const clicked=JSON.parse(JSON.stringify(state.selectedOccurrence));
 refreshSelectedOccurrence();
 const refreshed=JSON.parse(JSON.stringify(state.selectedOccurrence));
 item.style.bss_j_module={kind:'torsion',j_min:0,length:1};
 refreshSelectedOccurrence();
 return {clicked,refreshed,invalid:state.selectedOccurrence};
})()`,context)).then(result=>process.stdout.write(JSON.stringify(result))).catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, input=json.dumps(collected),
                            text=True, encoding="utf-8", check=True, timeout=20)
    result = json.loads(result.stdout)
    for selected in (result["clicked"], result["refreshed"]):
        assert selected["selectedJPower"] == 3
        assert selected["label"] == (r"v_1^{18}D^{-2}h_0^{2}" if collected else r"j^{3}\{v_1^{6}Dh_0^{2}\}")
        if collected:
            assert selected["selectedJLabel"] == selected["label"]
    assert result["invalid"] is None


def test_j_coefficient_markup_escapes_backend_text_and_never_calls_f4_resolver():
    markup = app_helper(["differentialCoefficientMarkup", "escapeHtml"], """(() => {
      globalThis.differentialDisplayCoefficient=()=>{throw Error('must not use F4');};
      const con={bss_j_coefficient_tex:'j^{2}<unsafe>',bss_j_target_power:2};
      return differentialCoefficientMarkup({spectral_sequence:'2-bss',propositions:[{id:'p',conclusion:con}]},
        {diff:{id:'d',proposition_id:'p'}},null,{x:1,y:2},{x:3,y:4});
    })()""")["result"]
    assert "&lt;unsafe&gt;" in markup and "<unsafe>" not in markup
    assert 'data-coefficient-kind="bss-j-adic"' in markup


def test_collected_sigma_target_label_is_transported_from_exact_seed_target_grade():
    markup = app_helper(["differentialCoefficientMarkup", "escapeHtml", "classInstanceKey",
                        "shiftDExponent", "shiftPeriodFactor", "latexPower"], r"""(() => {
      const con={bss_j_coefficient_tex:'j',bss_j_target_power:1,
        bss_j_target_label_tex:'v_1^{4}h_0h_1D^{-1}u_{\\sigma_i}',bss_seed_target_grade:{stem:1,filtration:1}};
      return differentialCoefficientMarkup({spectral_sequence:'2-bss',propositions:[{id:'p',conclusion:con}]},
        {diff:{id:'d',proposition_id:'p'},targetNode:{id:'target',style:{bss_j_module:{kind:'free'}}},
          targetGrade:{stem:17,filtration:1}},null,{x:1,y:2},{x:3,y:4});
    })()""")["result"]
    label = next(iter(ET.fromstring(markup)))
    assert label.get("data-bss-j-label") == r"v_1^{4}h_0h_1Du_{\sigma_i}"
    assert label.get("data-bss-j-power") == "1"
    assert "xv_1" not in label.get("data-bss-j-label")


def test_real_svg_badge_mouse_and_keyboard_route_to_the_packed_target_without_pan_capture():
    payload = build_bss_completed_chart("integer", 3, 0, 4, 2)
    ws = next(asdict(item) for item in create_bss_reference_workspaces() if item.id == payload["workspace_id"])
    script = r"""
const fs=require('fs'),vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8')),elements=new Map(),handlers=new Map();
let captures=0;
const document={body:{dataset:{}},querySelector(selector){
 if(!elements.has(selector))elements.set(selector,{textContent:'',dataset:{},setAttribute(){},
   querySelectorAll(){return [];},addEventListener(name,handler){handlers.set(name,handler);},
   setPointerCapture(){captures++;},classList:{add(){},remove(){}}});
 return elements.get(selector);
}};
const context=vm.createContext({document,window:{},input});
for(const name of ['graded-quotient','vector-page-algebra','page-algebra','cell-layout','display-basis','chart-presentation'])
 vm.runInContext(fs.readFileSync(`backend/static/${name}.js`,'utf8'),context);
context.window.HFPSSCellLayout=context.HFPSSCellLayout;
const source=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(source.slice(0,source.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
const result=vm.runInContext(`(() => {
 dimensions=()=>({width:640,height:480});
 escapeHtml=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
 cellChartLayout=()=>new Map();cellMapSvg=()=>'';cellGlyphSvg=()=>'';
 drawingPeriodicityPreviewSvg=()=>'';renderMathInChart=()=>{};renderFateInspector=()=>{};
 prepareBssWindow=()=>{};renderBssWindowControls=()=>{};
 let markup='';replaceSvgMarkup=(_svg,text)=>{markup=text;};
 const ws=input.workspace;ws.page=3;ws.settings.bss_relations='all';
 state.project={workspaces:[ws],period_families:[],page_period_cycles:[]};state.workspaceId=ws.id;state.tool='inspect';
 applyBssWindow(ws,input.payload,'test');
 viewportBounds=()=>({stemMin:-1,stemMax:9,filtrationMin:0,filtrationMax:30});
 renderChart();
 const match=/data-bss-j-target="([^"]+)" data-bss-j-power="([^"]+)"(?: data-bss-j-label="([^"]+)")?/.exec(markup);
 if(!match)throw Error('Expected a real completed j badge');
 const badge={dataset:{bssJTarget:match[1],bssJPower:match[2],bssJLabel:match[3]}};
 const target={closest:selector=>selector.includes('[data-bss-j-target]')?badge:null};
 const event={target,button:0,altKey:false,pointerId:1,clientX:100,clientY:100,stopPropagation(){},preventDefault(){}};
 const calls=[];onClassClick=(id,record)=>calls.push({id,power:record.selectedJPower,label:record.selectedJLabel,
   instanceKey:record.instanceKey,endpointKey:classInstanceKey(id,record.grade)});
 const svg=$('#chart');svg.onclick(event);svg.onkeydown({...event,key:'Enter'});
 return {calls,badge:badge.dataset,event};
})()`,context);
context.chart=document.querySelector('#chart');
const start=source.indexOf('  chart.addEventListener("pointerdown"');
const end=source.indexOf('  chart.addEventListener("pointermove"',start);
vm.runInContext(source.slice(start,end),context);
handlers.get('pointerdown')(result.event);
process.stdout.write(JSON.stringify({calls:result.calls,badge:result.badge,captures}));
"""
    process = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps({"payload": payload, "workspace": ws}),
                             text=True, encoding="utf-8", capture_output=True, check=True, timeout=20)
    result = json.loads(process.stdout)
    assert result["captures"] == 0
    assert len(result["calls"]) == 2
    for call in result["calls"]:
        assert call["endpointKey"] == result["badge"]["bssJTarget"]
        assert call["instanceKey"] != call["endpointKey"], "Exercise the actual packed-instance / endpoint-key distinction"
        assert call["power"] == int(result["badge"]["bssJPower"])
        assert call["label"] == result["badge"]["bssJLabel"]
