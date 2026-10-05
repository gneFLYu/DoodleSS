"""Computed BSS windows are bounded views, never stale-page replacements."""
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET

import pytest

from test_chart_display_conventions import app_helper


ROOT = Path(__file__).resolve().parents[1]


def runtime(body, engine="bss"):
    script = r"""
const fs=require('fs'), vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const source=fs.readFileSync(input.path,'utf8');
function extract(name) {
 const start=source.indexOf(`function ${name}(`);
 const next=/\n(?:async )?function\s/.exec(source.slice(start+1));
 return source.slice(start,next?start+1+next.index:source.length);
}
const makeWorkspace=id=>({id,page:input.engine==='c4'?2:1,spectral_sequence:input.engine==='c4'?'hfpss':'2-bss',settings:{source_reference:true,rendering:{}},
 classes:[{id:'seed',page:1,label:'catalog',style:{}}],differentials:[],propositions:[],differential_events:[],fates:[]});
const storage={configs:new Map(),cache:new Map(),pending:new Map(),errors:new Map(),catalogs:new WeakMap()};
const requests=[],renders=[];
let active=makeWorkspace(input.engine==='c4'?'ws_c4_bbhs_integer':'ws_q8_bss_integer');
const context={URLSearchParams,state:{bssWindows:storage,c4Windows:storage,selectedClassId:'seed',selectedOccurrence:null},
 workspace:()=>active, requests,renders,storage,makeWorkspace,
 chartMetrics:()=>({cell:32}),
 viewportBounds:()=>({stemMin:-8,stemMax:32,filtrationMin:0,filtrationMax:20}),
 activate:ws=>{active=ws;},
 api:path=>new Promise((resolve,reject)=>requests.push({path,resolve,reject})),
 render:()=>{renders.push(active.page);context[input.engine==='c4'?'prepareC4Window':'prepareBssWindow'](active);},
 flush:async()=>{for(let i=0;i<8;i++)await Promise.resolve();},
 payload:index=>{
   const request=requests[index],params=new URL(request.path,'http://localhost').searchParams;
   const values=Object.fromEntries([...params].filter(([k])=>!['format','projection'].includes(k)).map(([k,v])=>[k,Number(v)]));
   return {window:values,projection:params.get('projection')||'cohomology',coverage:'Global kernel/image membership, explicit display caps.',
     chart:{classes:[{id:'computed-'+values.page,page:values.page,label:'computed',style:{bockstein_filtration:1,last_page:values.page}}],
       differentials:[],propositions:[],...(input.engine==='c4'
         ?{periodicity:{generator:'\\Delta_1^4',stem:32,filtration:0,permanent:true}}
         :{periodicity:{generator:'D',stem:8,filtration:0,permanent:true}})}};
 }
};
vm.createContext(context);
const functions=input.engine==='c4'
 ?['c4Sector','c4WindowValues','validateC4Window','c4WindowKey','applyC4Window','prepareC4Window']
 :['bssSector','bssProjection','bssWindowValues','validateBssWindow','bssWindowKey','clearBssWindow','applyBssWindow','prepareBssWindow'];
vm.runInContext(functions.map(extract).join('\n'),context);
Promise.resolve(vm.runInContext(`(async()=>{${input.body}})()`,context)).then(result=>process.stdout.write(JSON.stringify(result))).catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run(["node", "-e", script], input=json.dumps({
        "path": str(ROOT / "backend/static/app.js"), "body": body, "engine": engine,
    }), text=True, encoding="utf-8", capture_output=True, check=True, timeout=20)
    return json.loads(result.stdout)


def test_chart_waits_empty_until_ready_response_and_request_is_deduplicated():
    result = runtime("""
      const ws=workspace(); prepareBssWindow(ws); prepareBssWindow(ws);
      const before=ws.classes.map(n=>n.id);
      requests[0].resolve(payload(0)); await flush();
      prepareBssWindow(ws);
      return {before,after:ws.classes.map(n=>n.id),requests:requests.length,
        computed:ws.settings.bss_computed_window.window,selected:state.selectedClassId};
    """)
    assert result["before"] == [] and result["after"] == ["computed-1"]
    assert result["requests"] == 1 and result["selected"] is None
    assert "v1_max" not in result["computed"] and result["computed"]["h0_max"] == 2


def test_late_page_response_never_overwrites_new_page():
    result = runtime("""
      const ws=workspace(); prepareBssWindow(ws);
      ws.page=2; prepareBssWindow(ws);
      requests[0].resolve(payload(0)); await flush();
      const pending=ws.classes.map(n=>n.id);
      requests[1].resolve(payload(1)); await flush();
      return {pending,ids:ws.classes.map(n=>n.id),page:ws.page,renders};
    """)
    assert result == {"pending": [], "ids": ["computed-2"], "page": 2, "renders": [2]}


def test_new_page_is_empty_instead_of_showing_old_computed_or_catalog_nodes():
    result = runtime("""
      const ws=workspace();prepareBssWindow(ws);requests[0].resolve(payload(0));await flush();
      ws.page=3;prepareBssWindow(ws);
      return {ids:ws.classes.map(n=>n.id),computed:!!ws.settings.bss_computed_window,page:ws.page};
    """)
    assert result == {"ids": [], "computed": False, "page": 3}


def test_workspace_switch_isolated_and_cached_result_reused():
    result = runtime("""
      const integer=workspace();prepareBssWindow(integer);
      const sigma=makeWorkspace('ws_q8_bss_sigma');activate(sigma);prepareBssWindow(sigma);
      requests[0].resolve(payload(0));await flush();
      const sigmaPending=sigma.classes.map(n=>n.id);
      activate(integer);prepareBssWindow(integer);
      return {sigmaPending,integer:integer.classes.map(n=>n.id),count:requests.length,renders};
    """)
    assert result == {"sigmaPending": [], "integer": ["computed-1"], "count": 2, "renders": []}


def test_horizontal_pan_reuses_period_strip_but_vertical_pan_loads_new_rows():
    result = runtime("""
      const ws=workspace();prepareBssWindow(ws);requests[0].resolve(payload(0));await flush();
      globalThis.viewportBounds=()=>({stemMin:1000,stemMax:1040,filtrationMin:0,filtrationMax:20});prepareBssWindow(ws);
      const unchanged=requests.length;
      globalThis.viewportBounds=()=>({stemMin:1000,stemMax:1040,filtrationMin:24,filtrationMax:44});prepareBssWindow(ws);
      const vertical=requests.length,verticalPath=requests[1].path;
      storage.configs.set(ws.id,{...bssWindowValues(ws),h0_max:3});prepareBssWindow(ws);
      return {unchanged,vertical,verticalPath,changed:requests.length,path:requests[2].path};
    """)
    assert result["unchanged"] == 1 and result["vertical"] == 2 and result["changed"] == 3
    assert "stem_min=0&stem_max=7" in result["verticalPath"]
    assert "filtration_min=16" in result["verticalPath"] and "filtration_max=48" in result["verticalPath"]
    assert "h0_max=3" in result["path"] and "v1_max" not in result["path"]
    assert "/completed-chart?" in result["path"]


def test_malformed_response_leaves_chart_empty_and_requires_explicit_retry():
    result = runtime("""
      const ws=workspace();prepareBssWindow(ws);
      requests[0].resolve({window:{page:1},chart:{classes:[]}});await flush();
      prepareBssWindow(ws);
      const first={ids:ws.classes.map(n=>n.id),requests:requests.length,error:[...storage.errors.values()][0]};
      storage.errors.delete(bssWindowKey(ws));prepareBssWindow(ws);
      return {first,retried:requests.length};
    """)
    assert result["first"]["ids"] == [] and result["first"]["requests"] == 1
    assert "incomplete" in result["first"]["error"] and result["retried"] == 2


@pytest.mark.parametrize("change", [
    "page:0", "page:5", "stem_min:40", "stem_max:200", "filtration_min:-1",
    "filtration_min:10", "filtration_max:129", "h0_max:13", "h0_max:1.5",
])
def test_invalid_computation_bounds_rejected(change):
    result = app_helper(["validateBssWindow"], """(() => {
      try {validateBssWindow({page:1,stem_min:-8,stem_max:32,filtration_min:0,filtration_max:8,h0_max:3,CHANGE});return false;}
      catch(error){return true;}
    })()""".replace("CHANGE", change))["result"]
    assert result is True


def test_cohomological_window_accepts_128_rows_at_arbitrary_height():
    result = app_helper(["validateBssWindow"], """validateBssWindow({page:3,stem_min:0,stem_max:7,
      filtration_min:256,filtration_max:384,h0_max:3})""")["result"]
    assert result["filtration_max"] - result["filtration_min"] == 128


def test_projection_switch_requests_distinct_payload_and_never_reuses_wrong_axes():
    result = runtime("""
      const ws=workspace();prepareBssWindow(ws);requests[0].resolve(payload(0));await flush();
      ws.settings.bss_projection='bockstein';prepareBssWindow(ws);
      const waiting=ws.classes.map(n=>n.id);
      requests[1].resolve(payload(1));await flush();
      return {waiting,projection:ws.settings.bss_computed_window.projection,path:requests[1].path,
        key:ws.settings.bss_computed_window.key,count:requests.length};
    """)
    assert result["waiting"] == [] and result["projection"] == "bockstein"
    assert "projection=bockstein" in result["path"] and ":bockstein:" in result["key"]
    assert result["count"] == 2


def test_projection_switch_keeps_h0_bounds_without_truncating_j_series():
    result = runtime("""
      const ws=workspace(); const before=bssWindowValues(ws);
      ws.settings.bss_projection='bockstein';
      const after=bssWindowValues(ws);
      storage.configs.set(ws.id,{h0_max:1,filtration_max:0});
      return {before,after,zero:bssWindowValues(ws)};
    """)
    assert result["before"]["h0_max"] == result["after"]["h0_max"] == 2
    assert "v1_max" not in result["before"] and "v1_max" not in result["after"]
    assert result["zero"]["filtration_max"] == 0 and result["zero"]["h0_max"] == 1


def test_computed_status_exposes_all_caps_without_false_global_completeness():
    result = app_helper(["bssSector", "bssProjection", "bssGradingText", "pageStatusText"], """pageStatusText({page:3,settings:{bss_computed_window:{
      window:{stem_min:-8,stem_max:32,filtration_min:0,filtration_max:8,v1_max:8,h0_max:3},
      coverage:'Omitted powers are not zero; not an HFPSS page.'}}})""")["result"]
    assert "Computed additive 2-BSS" in result and "v₁ exponent ≤ 8" in result and "h₀ exponent ≤ 3" in result
    assert "not yet computed" not in result and "not an HFPSS page" in result


@pytest.fixture(scope="module")
def real_bss_rendering():
    sys.path.insert(0, str(ROOT / "backend"))
    from domain.bss_chart import build_bss_window
    from domain.bss_reference import create_bss_reference_workspaces
    from dataclasses import asdict

    workspaces = {ws.id: asdict(ws) for ws in create_bss_reference_workspaces()}
    inputs = []
    for sector in ("integer", "sigma"):
        for page in (1, 2, 3, 4):
            payload = build_bss_window(sector, page=page, stem_min=-2, stem_max=6,
                                       filtration_min=0, filtration_max=4, v1_max=2,
                                       h0_max=2, include_records=False)
            inputs.append({"payload": payload, "workspace": workspaces[payload["workspace_id"]]})
    return render_bss_payloads(inputs)


def render_bss_payloads(inputs):
    script = r"""
const fs=require('fs'),vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const elements=new Map();
const document={body:{dataset:{}},querySelector(selector){
 if(!elements.has(selector))elements.set(selector,{textContent:'',dataset:{},setAttribute(){},querySelectorAll(){return [];}});
 return elements.get(selector);
}};
const context=vm.createContext({document,window:{},input});
for(const name of ['graded-quotient','vector-page-algebra','page-algebra','cell-layout','display-basis','chart-presentation'])
 vm.runInContext(fs.readFileSync(`backend/static/${name}.js`,'utf8'),context);
context.window.HFPSSCellLayout=context.HFPSSCellLayout;
const source=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(source.slice(0,source.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
const output=vm.runInContext(`(() => {
 dimensions=()=>({width:640,height:480});
 escapeHtml=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
 cellChartLayout=()=>new Map();cellMapSvg=()=>'';cellGlyphSvg=()=>'';
 drawingPeriodicityPreviewSvg=()=>'';renderMathInChart=()=>{};renderFateInspector=()=>{};
 prepareBssWindow=()=>{};renderBssWindowControls=()=>{};
 let markup='';replaceSvgMarkup=(_svg,text)=>{markup=text;};
 return input.map(({payload,workspace:ws,bounds:requestedBounds})=>{
   ws.page=payload.window.page;
   ws.settings.bss_relations='all';ws.settings.bss_projection=payload.projection||'cohomology';
   state.project={workspaces:[ws],period_families:[],page_period_cycles:[]};state.workspaceId=ws.id;
   applyBssWindow(ws,payload,bssWindowKey(ws));
   const bounds=requestedBounds||{stemMin:Math.min(...ws.classes.map(n=>n.grade.stem))-1,
     stemMax:Math.max(...ws.classes.map(n=>n.grade.stem))+1,
     filtrationMin:Math.max(0,Math.min(...ws.classes.map(n=>n.grade.filtration))-1),
     filtrationMax:Math.max(...ws.classes.map(n=>n.grade.filtration))+1};
   viewportBounds=()=>bounds;
   const metrics=chartMetrics(), packed=packedClassInstances(ws,bounds,metrics,[],null,null);
   const arrowOccurrences=periodicDifferentials(ws,bounds,null,null).map(item=>({id:item.diff.id,
     sourceId:item.sourceNode.id,targetId:item.targetNode.id,sourceGrade:item.sourceGrade,targetGrade:item.targetGrade}));
   const relationOccurrences=periodicRelations(ws,new Set(liveClassesAt(ws).map(n=>n.id)),bounds,null).map(item=>({id:item.proposition.id,
     sourceId:item.source.id,targetId:item.target.id,sourceGrade:item.sourceGrade,targetGrade:item.targetGrade}));
   renderChart();
   return {sector:payload.sector,page:ws.page,projection:payload.projection||'cohomology',markup,nodes:ws.classes,differentials:ws.differentials,propositions:ws.propositions,arrowOccurrences,relationOccurrences,
     points:packed.map(record=>({id:record.item.id,endpointOnly:!!record.endpointOnly,
       level:record.item.style.bockstein_filtration,grade:record.grade,point:coefficientPortPoint(record,metrics)}))};
 });
})()`,context);
process.stdout.write(JSON.stringify(output));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(inputs),
                            text=True, encoding="utf-8", capture_output=True, check=True, timeout=30)
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def real_bss_periodic_rendering():
    sys.path.insert(0, str(ROOT / "backend"))
    from domain.bss_periodic import build_bss_periodic_window
    from domain.bss_reference import create_bss_reference_workspaces
    from dataclasses import asdict

    workspaces = {ws.id: asdict(ws) for ws in create_bss_reference_workspaces()}
    inputs = []
    for sector in ("integer", "sigma"):
        for page in (2, 3):
            for projection in ("cohomology", "bockstein"):
                payload = build_bss_periodic_window(sector, page=page, filtration_min=0,
                    filtration_max=4, v1_max=2, h0_max=2, projection=projection)
                inputs.append({"payload": payload, "workspace": workspaces[payload["workspace_id"]],
                    "bounds": {"stemMin": -8, "stemMax": 16, "filtrationMin": 0, "filtrationMax": 8}})
    return render_bss_payloads(inputs)


def test_actual_bss_payload_renders_every_arrow_at_its_own_h0_endpoint(real_bss_rendering):
    for case in real_bss_rendering:
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        points = {point["id"]: point for point in case["points"]}
        nodes = {node["id"]: node for node in case["nodes"]}
        edges = {node.attrib["data-differential"]: node for node in xml.iter("line") if "data-differential" in node.attrib}
        assert len(edges) == len(case["differentials"])
        for differential in case["differentials"]:
            line = edges[differential["id"]]
            source, target = nodes[differential["source_id"]], nodes[differential["target_id"]]
            for suffix, node in (("1", source), ("2", target)):
                expected = points[node["id"]]["point"]
                assert float(line.get("x" + suffix)) == pytest.approx(expected["x"])
                assert float(line.get("y" + suffix)) == pytest.approx(expected["y"])
            assert target["grade"]["stem"] - source["grade"]["stem"] == -1
            assert target["grade"]["filtration"] - source["grade"]["filtration"] == 1
            assert target["style"]["bockstein_filtration"] - source["style"]["bockstein_filtration"] == case["page"]
            if target["style"].get("window_endpoint_only") or target["style"].get("bss_boundary"):
                assert line.get("data-target-outside-window") == "true"


def test_h0_levels_have_distinct_selectable_points_including_boundary_context(real_bss_rendering):
    for case in real_bss_rendering:
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        glyphs = {node.attrib["data-point"]: node for node in xml.iter("g") if "data-point" in node.attrib}
        by_cell = {}
        for record in case["points"]:
            cell = tuple(record["grade"][key] for key in ("stem", "filtration"))
            by_cell.setdefault(cell, []).append(tuple(record["point"][key] for key in ("x", "y")))
            assert not record["endpointOnly"], "BSS map boundaries must be visible, not ghost endpoints"
            assert glyphs[record["id"]].get("data-bockstein-filtration") == str(record["level"])
        for coordinates in by_cell.values():
            assert len(set(coordinates)) == len(coordinates), "Projected coefficient layers overlap"
