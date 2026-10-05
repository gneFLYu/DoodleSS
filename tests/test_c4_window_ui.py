"""Completed C4 branches use coefficient-ring labels and exact two-adic ports."""
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET

import pytest

from test_chart_display_conventions import app_helper
from test_bss_window_ui import runtime


ROOT = Path(__file__).resolve().parents[1]


def test_c4_port_labels_scale_relative_to_branch_not_f4():
    result = app_helper(["rawPeriodicDisplayLabel", "shiftC4Delta", "latexPower"], r"""[2,3,4].map(level=>rawPeriodicDisplayLabel({
      item:{label:'4\\Delta_1',style:{c4_coefficient_branch:{two_min:2,two_max:4,representative_tex:'4\\Delta_1'}}},
      selectedPort:level+':0'}))""")["result"]
    assert result == [r"4\Delta_1", r"8\Delta_1", r"16\Delta_1"]


def test_c4_coefficient_badge_does_not_invoke_f4_arithmetic():
    result = app_helper(["differentialCoefficientMarkup", "escapeHtml"], r"""differentialCoefficientMarkup(
      {group:'C4',settings:{source_reference:true}},
      {diff:{id:'c4',display_coefficient:{kind:'c4-coefficient',resolved:true,latex:'\\mu^{2}'}}},
      {coefficientState:()=>{throw new Error('F4 algebra must not run');}},{x:0,y:0},{x:20,y:40})""")["result"]
    assert 'data-coefficient-kind="c4-coefficient"' in result
    assert r'data-latex="\mu^{2}"' in result and 'x="10" y="20"' in result


def test_c4_window_sector_and_lazy_filtration_bounds():
    result = app_helper(["c4Sector", "validateC4Window"], """(() => {
      const errors=[];
      for(const change of [{page:1},{page:15},{filtration_max:257},{filtration_min:-1},{filtration_max:1.5},{filtration_min:15}]) {
        try {validateC4Window({page:2,filtration_min:0,filtration_max:14,...change});errors.push(false);}
        catch(error){errors.push(true);}
      }
      validateC4Window({page:2,filtration_min:1024,filtration_max:1280});
      return [c4Sector({id:'ws_c4_bbhs_integer'}),c4Sector({id:'ws_c4_bbhs_1_minus_sigma'}),c4Sector({id:'ws_c4_j'}),errors];
    })()""")["result"]
    assert result == ["integer", "1-minus-sigma", None, [True] * 6]


def test_c4_loader_uses_compact_api_and_ignores_stale_page_response():
    result = runtime("""
      const ws=workspace();prepareC4Window(ws);prepareC4Window(ws);
      ws.page=5;prepareC4Window(ws);
      requests[0].resolve(payload(0));await flush();
      const before=ws.classes.map(n=>n.id);
      requests[1].resolve(payload(1));await flush();
      return {before,after:ws.classes.map(n=>n.id),requests:requests.map(r=>r.path),
        computed:ws.settings.c4_computed_window.window,page:ws.page};
    """, engine="c4")
    assert result["before"] == [] and result["after"] == ["computed-5"]
    assert len(result["requests"]) == 2
    assert all(path.startswith("/api/v2/c4/integer/periodic-chart?") and "stem_" not in path for path in result["requests"])
    assert result["computed"]["page"] == result["page"] == 5


def test_c4_api_error_keeps_chart_empty_and_does_not_retry_on_every_render():
    result = runtime("""
      const ws=workspace();prepareC4Window(ws);requests[0].reject(new Error('source engine unavailable'));await flush();
      prepareC4Window(ws);prepareC4Window(ws);
      const before={ids:ws.classes.map(n=>n.id),requests:requests.length,errors:[...storage.errors.values()]};
      storage.errors.delete(c4WindowKey(ws));prepareC4Window(ws);
      return {before,retried:requests.length};
    """, engine="c4")
    assert result["before"] == {"ids": [], "requests": 1, "errors": ["source engine unavailable"]}
    assert result["retried"] == 2


def test_horizontal_pan_reuses_strip_but_vertical_pan_loads_quantized_rows():
    result = runtime("""
      let bounds={stemMin:-8,stemMax:32,filtrationMin:0,filtrationMax:20};
      viewportBounds=()=>bounds;
      const ws=workspace();prepareC4Window(ws);requests[0].resolve(payload(0));await flush();
      bounds={...bounds,stemMin:-1000,stemMax:-960};prepareC4Window(ws);
      const horizontalCount=requests.length;
      bounds={...bounds,filtrationMin:100,filtrationMax:120};prepareC4Window(ws);
      return {horizontalCount,verticalCount:requests.length,values:c4WindowValues(ws),retained:ws.classes.map(n=>n.id)};
    """, engine="c4")
    assert result == {"horizontalCount": 1, "verticalCount": 2,
                      "values": {"page": 2, "filtration_min": 80, "filtration_max": 128},
                      "retained": ["computed-2"]}


def test_c4_loader_rejects_uncertified_periodicity():
    result = runtime("""
      prepareC4Window(workspace());const value=payload(0);delete value.chart.periodicity;
      requests[0].resolve(value);await flush();
      return {ids:workspace().classes.map(n=>n.id),errors:[...storage.errors.values()]};
    """, engine="c4")
    assert result["ids"] == []
    assert "uncertified" in result["errors"][0]


@pytest.mark.parametrize("initial_page", [2, 14])
def test_e14_pending_or_failed_never_falls_back_to_e2_catalog(initial_page):
    result = runtime("""
      const ws=workspace();ws.page=INITIAL_PAGE;ws.classes[0].page=2;
      ws.differentials=[{id:'source-d3',page:3}];
      ws.propositions=[{id:'source-relation',kind:'relation'}];
      prepareC4Window(ws);
      if(ws.page===2){requests[0].resolve(payload(0));await flush();ws.page=14;prepareC4Window(ws);}
      const snapshot=()=>({page:ws.page,ids:ws.classes.map(n=>n.id),
        differentials:ws.differentials.map(n=>n.id),propositions:ws.propositions.map(n=>n.id),
        computed:!!ws.settings.c4_computed_window});
      const pending=snapshot();
      requests.at(-1).reject(new Error('E14 unavailable'));await flush();prepareC4Window(ws);
      return {pending,failed:snapshot(),requests:requests.length,
        savedCatalog:storage.catalogs.get(ws).classes.map(n=>n.id)};
    """.replace("INITIAL_PAGE", str(initial_page)), engine="c4")
    empty_e14 = {"page": 14, "ids": [], "differentials": [], "propositions": [], "computed": False}
    assert result["pending"] == result["failed"] == empty_e14
    assert result["savedCatalog"] == ["seed"]
    assert result["requests"] == (2 if initial_page == 2 else 1)


def test_c4_witt_ports_continue_and_periodic_labels_use_delta_not_q8_D():
    result = app_helper(["c4CoefficientPorts", "c4CoefficientShape", "rawPeriodicDisplayLabel",
                         "shiftC4Delta", "latexPower"], r"""(() => {
      const coefficient={two_min:2,two_max:null,completed_mu_tail:true,
        representative_tex:'4\\mu \\Delta_1^{2} \\mathfrak p'};
      return {ports:c4CoefficientPorts(coefficient),shape:c4CoefficientShape(coefficient),
        labels:[-1,0,1].map(horizontalExponent=>rawPeriodicDisplayLabel({
          item:{style:{c4_coefficient_branch:coefficient}},horizontalExponent,selectedPort:'3:0'}))};
    })()""")["result"]
    assert result == {"ports": ["2:0", "3:0", "4:0"], "shape": "c4-witt-tower",
                      "labels": [r"8\mu \Delta_1^{-2} \mathfrak p", r"8\mu \Delta_1^{2} \mathfrak p",
                                 r"8\mu \Delta_1^{6} \mathfrak p"]}


@pytest.fixture(scope="module")
def c4_rendering():
    sys.path.insert(0, str(ROOT / "backend"))
    from domain.c4_chart import build_c4_periodic_chart

    payloads = [build_c4_periodic_chart(sector, page=page,
                                       filtration_min=0, filtration_max=20, include_records=False)
                for sector in ("integer", "1-minus-sigma") for page in range(2, 15)]
    script = r"""
const fs=require('fs'),vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8')),elements=new Map();
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
 dimensions=()=>({width:900,height:720});
 escapeHtml=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
 cellChartLayout=()=>new Map();cellMapSvg=()=>'';cellGlyphSvg=()=>'';
 drawingPeriodicityPreviewSvg=()=>'';renderMathInChart=()=>{};
 prepareC4Window=()=>{};renderC4WindowControls=()=>{};
 let markup='';replaceSvgMarkup=(_svg,text)=>{markup=text;};
 return input.map(payload=>{
   const ws={id:payload.sector==='integer'?'ws_c4_bbhs_integer':'ws_c4_bbhs_1_minus_sigma',group:'C4',spectral_sequence:'hfpss',page:payload.window.page,
     classes:[],differentials:[],propositions:[],fates:[],cells:[],differential_maps:[],
     settings:{source_reference:true,rendering:{buffer_cells:2},literature_review:{coverage:'source'}}};
   state.project={workspaces:[ws],period_families:[],page_period_cycles:[]};state.workspaceId=ws.id;
   state.selectedClassId=null;state.selectedOccurrence=null;
   applyC4Window(ws,payload,'test:'+ws.page);
   const limits=payload.window,bounds={stemMin:-40,stemMax:72,
     filtrationMin:0,filtrationMax:limits.filtration_max+ws.page};
   viewportBounds=()=>bounds;
   const metrics=chartMetrics(),packed=packedClassInstances(ws,bounds,metrics,[],null,null);
   const arrows=periodicDifferentials(ws,bounds,null,null).map(item=>({id:item.diff.id,
     sourceGrade:item.sourceGrade,targetGrade:item.targetGrade}));
   const relations=periodicRelations(ws,new Set(liveClassesAt(ws).map(n=>n.id)),bounds,null).map(item=>({
     id:item.proposition.id,sourceGrade:item.sourceGrade,targetGrade:item.targetGrade}));
   renderChart();
   const printedMarkup=markup;
   const inspector=[];
   mathMarkup=value=>String(value);
   for(const row of ws.differentials){state.selectedClassId=row.source_id;renderFateInspector();inspector.push(document.querySelector('#fate-inspector').innerHTML);}
   return {sector:payload.sector,page:ws.page,markup:printedMarkup,inspector,nodes:ws.classes,differentials:ws.differentials,claims:ws.propositions,
     arrows,relations,
     ports:packed.map(record=>({id:record.item.id,grade:record.grade,shape:record.shape,endpointOnly:!!record.endpointOnly,
       periodic:record.periodic,horizontalExponent:record.horizontalExponent,label:rawPeriodicDisplayLabel(record),
       size:record.size, defaultPoint:coefficientPortPoint(record,metrics),
       ports:Object.fromEntries((record.modulePorts||[]).map(port=>[port,coefficientPortPoint(record,metrics,port)]))}))};
 });
})()`,context);
process.stdout.write(JSON.stringify(output));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(payloads),
                            text=True, encoding="utf-8", capture_output=True, check=True, timeout=60)
    return json.loads(result.stdout)


def test_real_c4_arrows_use_absolute_coefficient_ports(c4_rendering):
    finite_arrows = 0
    seams = 0
    shifts = set()
    assert {(case["sector"], case["page"]) for case in c4_rendering} == {
        (sector, page) for sector in ("integer", "1-minus-sigma") for page in range(2, 15)}
    for case in c4_rendering:
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        edges = [line for line in xml.iter("line") if line.get("data-differential")]
        claims = {claim["id"]: claim for claim in case["claims"]}
        rows = {row["id"]: row for row in case["differentials"]}
        ports = {(record["id"], record["grade"]["stem"], record["grade"]["filtration"]): record
                 for record in case["ports"]}
        assert len(edges) == len(case["arrows"])
        for occurrence, line in zip(case["arrows"], edges):
            assert occurrence["id"] == line.get("data-differential")
            row = rows[occurrence["id"]]
            claim = claims[row["proposition_id"]]["conclusion"]
            assert occurrence["targetGrade"]["stem"] - occurrence["sourceGrade"]["stem"] == -1
            assert occurrence["targetGrade"]["filtration"] - occurrence["sourceGrade"]["filtration"] == case["page"]
            seams += bool(claim["c4_target_period_offset"])
            for name, suffix in (("source", "1"), ("target", "2")):
                grade = occurrence[name + "Grade"]
                record = ports.get((row[name + "_id"], grade["stem"], grade["filtration"]))
                if record is None:  # The clipped segment's endpoint can lie off-screen.
                    continue
                shifts.add(record["horizontalExponent"])
                port = str(claim["c4_" + name + "_two"]) + ":0"
                assert port in record["ports"]
                point = record["ports"][port]
                finite_arrows += record["shape"] == "finite-two-tower"
                assert float(line.get("x" + suffix)) == pytest.approx(point["x"])
                assert float(line.get("y" + suffix)) == pytest.approx(point["y"])
    assert finite_arrows > 0
    assert seams > 0 and min(shifts) < 0 < max(shifts)


def test_real_c4_eta_nu_two_relations_use_occurrence_specific_ports(c4_rendering):
    multipliers, shifts = set(), set()
    seam_count = 0
    for case in c4_rendering:
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        edges = [line for line in xml.iter("line") if line.get("data-relation")]
        claims = {claim["id"]: claim for claim in case["claims"]}
        ports = {(record["id"], record["grade"]["stem"], record["grade"]["filtration"]): record
                 for record in case["ports"]}
        assert len(edges) == len(case["relations"])
        for occurrence, line in zip(case["relations"], edges):
            assert line.get("data-relation") == occurrence["id"]
            claim = claims[occurrence["id"]]["conclusion"]
            multiplier = claim["c4_multiplier"]
            multipliers.add(multiplier)
            source, target = occurrence["sourceGrade"], occurrence["targetGrade"]
            assert (target["stem"] - source["stem"], target["filtration"] - source["filtration"]) == {
                "eta": (1, 1), "nu": (3, 1), "2": (0, 0)}[multiplier]
            seam_count += bool(claim["c4_target_period_offset"])
            for name, suffix in (("source", "1"), ("target", "2")):
                grade = occurrence[name + "Grade"]
                record = ports.get((claim[name + "_id"], grade["stem"], grade["filtration"]))
                if record is None:
                    continue
                shifts.add(record["horizontalExponent"])
                point = record["ports"][str(claim["c4_" + name + "_two"]) + ":0"]
                assert float(line.get("x" + suffix)) == pytest.approx(point["x"])
                assert float(line.get("y" + suffix)) == pytest.approx(point["y"])
            if multiplier == "2":
                assert float(line.get("x1")) == pytest.approx(float(line.get("x2")))
                assert float(line.get("y2")) < float(line.get("y1"))
    assert multipliers == {"eta", "nu", "2"}
    assert seam_count > 0 and min(shifts) < 0 < max(shifts)


def test_c4_inspector_uses_exact_source_equation_and_mu_badges(c4_rendering):
    badges = {"differential": 0, "relation": 0}
    for case in c4_rendering:
        claims = {claim["id"]: claim for claim in case["claims"]}
        for row, markup in zip(case["differentials"], case["inspector"]):
            assert claims[row["proposition_id"]]["statement"] in markup
            assert "Completed coefficient module" in markup
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        found = {item.get("data-coefficient-for"): item for item in xml.iter("foreignObject")
                 if item.get("data-coefficient-kind") == "c4-coefficient"}
        differential_ids = {row["id"] for row in case["differentials"]}
        relation_ids = {claim["id"] for claim in case["claims"] if claim["kind"] == "relation"}
        expected_differentials = {row["id"] for row in case["differentials"] if row["display_coefficient"]["latex"] != "1"}
        expected_relations = {claim["id"] for claim in case["claims"] if claim["kind"] == "relation"
                              and claim["conclusion"]["display_coefficient"]["latex"] != "1"}
        assert set(found) & differential_ids == expected_differentials
        assert set(found) & relation_ids == expected_relations
        assert set(found) == expected_differentials | expected_relations
        badges["differential"] += len(expected_differentials)
        badges["relation"] += len(expected_relations)
    assert all(badges.values())


def test_periodic_c4_witt_glyphs_show_continuation_not_finite_rank(c4_rendering):
    cases_with_witt = 0
    for case in c4_rendering:
        xml = ET.fromstring("<svg>" + case["markup"] + "</svg>")
        glyphs = [item for item in xml.iter("g") if "c4-witt-tower" in item.get("class", "").split()]
        assert len(glyphs) == sum(record["shape"] == "c4-witt-tower" and not record["endpointOnly"]
                                  for record in case["ports"])
        for glyph in glyphs:
            cases_with_witt += 1
            assert any(line.get("class") == "c4-tower-continuation" for line in glyph.iter("line"))
            assert len(list(glyph.iter("rect"))) == 1
            assert len(list(glyph.iter("circle"))) == 2
            assert {mark.get("data-coefficient-port") for mark in glyph if mark.get("data-coefficient-port")}
    assert cases_with_witt > 0


def test_periodic_c4_copies_keep_size_and_witt_does_not_shrink_isolated_dots(c4_rendering):
    for case in c4_rendering:
        sizes = {}
        for record in case["ports"]:
            if record["endpointOnly"]:
                continue
            sizes.setdefault(record["id"], set()).add(round(record["size"], 8))
        assert all(len(values) == 1 for values in sizes.values())
    assert any(record["shape"] == "dot" and record["size"] >= 2
               for case in c4_rendering for record in case["ports"])
