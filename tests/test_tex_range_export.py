"""The browser exporter keeps the lowest page's basis and exact port geometry."""
import json
from pathlib import Path
import subprocess
import sys
from dataclasses import asdict

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "backend/static/tex-export.js"


def run(body):
    result = subprocess.run(
        ["node", "-e", "const T=require('./backend/static/tex-export.js');\n" + body],
        cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=True, timeout=20,
    )
    return json.loads(result.stdout)


DEFAULTS = {"pageStart": 2, "pageEnd": 9,
            "bounds": {"stemMin": -4, "stemMax": 12, "filtrationMin": 0, "filtrationMax": 8}}


@pytest.mark.parametrize("patch", [
    {"pageStart": 0}, {"pageStart": -1}, {"pageEnd": 1}, {"pageStart": 2.5},
    {"pageStart": "2e0"}, {"pageEnd": ""}, {"pageStart": None}, {"pageEnd": True},
    {"bounds": {"stemMin": 4, "stemMax": -4, "filtrationMin": 0, "filtrationMax": 8}},
    {"bounds": {"stemMin": -4, "stemMax": 4, "filtrationMin": -1, "filtrationMax": 8}},
    {"bounds": {"stemMin": -4, "stemMax": 4, "filtrationMin": 5, "filtrationMax": 2}},
    {"bounds": {"stemMin": -4, "stemMax": 4.5, "filtrationMin": 0, "filtrationMax": 8}},
])
def test_invalid_ranges_are_rejected(patch):
    data = DEFAULTS | patch
    result = run("try {T.validateOptions(" + json.dumps(data) + "); console.log(false)} catch(e) {console.log(JSON.stringify(e.message))}")
    assert result and isinstance(result, str)


def test_positive_single_page_and_single_bidegree_are_valid():
    data = {"pageStart": "1", "pageEnd": "1",
            "bounds": {"stemMin": "-3", "stemMax": "-3", "filtrationMin": "0", "filtrationMax": "0"}}
    result = run("console.log(JSON.stringify(T.validateOptions(" + json.dumps(data) + "))); ")
    assert result["pageStart"] == result["pageEnd"] == 1
    assert result["bounds"] == {"stemMin": -3, "stemMax": -3, "filtrationMin": 0, "filtrationMax": 0}


def test_render_includes_inclusive_arrows_template_colors_and_clipping():
    snapshot = DEFAULTS | {"nodes": [{"id": "kD", "x": 4, "y": 4, "stem": 4, "filtration": 4,
        "label": "kD", "shape": "finite-two-tower", "glyphs": [
            {"x": 4, "y": 3.84, "shape": "dot", "two": 0},
            {"x": 4, "y": 4, "shape": "dot", "two": 1},
            {"x": 4, "y": 4.16, "shape": "dot", "two": 2}]}],
        "relations": [{"id": "r", "from": {"x": 4, "y": 3.84}, "to": {"x": 5, "y": 5}, "multiplier": "h_1"}],
        "differentials": [{"id": f"d{r}", "page": r, "from": {"x": 4, "y": 3.84},
            "to": {"x": 3, "y": 3.84 + r}, "coefficient": "\\zeta"} for r in (1, 2, 3, 5, 9, 11)]}
    result = run("console.log(JSON.stringify(T.render(" + json.dumps(snapshot) + "))); ")
    assert "a3paper,landscape" in result
    assert "every path/.style" not in result  # Extra path options invalidate TikZ clipping.
    assert "d3/.style={draw={red},tower}" in result
    assert "d9/.style={draw={violet},tower}" in result
    assert "d17/.style={draw={red!50!pink},tower}" in result
    for r in (2, 3, 5, 9):
        assert f"\\draw[d{r}] (4,3.84)" in result
    for r in (1, 11):
        assert f"\\draw[d{r}]" not in result
    assert "\\draw[multh1] (4,3.84) -- (5,5);" in result
    assert "\\clip (-4.48,-0.48) rectangle (12.48,8.48);" in result
    assert "node[midway,fill=white,inner sep=1pt,scale=.6] {$\\zeta$}" in result
    assert "\\draw[multtwo] (4,3.84) -- (4,4.16);" in result
    assert '"label":"kD"' in result
    assert result.count("circle[radius=.055]") == 3


def test_review_styles_retain_page_color_and_nonfinite_coordinates_fail():
    snapshot = DEFAULTS | {"differentials": [{"id": "under-review", "page": 3,
        "from": {"x": 0, "y": 0}, "to": {"x": -1, "y": 3}, "review": True}]}
    result = run("console.log(JSON.stringify(T.render(" + json.dumps(snapshot) + "))); ")
    assert "\\draw[d3,review differential]" in result
    assert "review differential/.style={dashed,opacity=.75}" in result
    result = run("try {T.render({..." + json.dumps(DEFAULTS) + ",nodes:[{x:Infinity,y:0}]}); console.log(false)} catch(e) {console.log(true)}")
    assert result is True


MOCK = r"""
const classes=[
  {id:'source',label:'D',page:2,grade:{stem:4,filtration:0},style:{}},
  {id:'target',label:'kD',page:2,grade:{stem:3,filtration:3},style:{}},
  {id:'later',label:'D^2',page:2,grade:{stem:8,filtration:0},style:{}},
  {id:'later-target',label:'kD^2',page:2,grade:{stem:7,filtration:5},style:{}}
];
const ws={id:'test',name:'Test',page:23,classes,differentials:[
 {id:'d3',page:3,source_id:'source',target_id:'target'},
 {id:'d5',page:5,source_id:'later',target_id:'later-target'},
 {id:'d11',page:11,source_id:'source',target_id:'target'}
]};
const pages=[],packPages=[],relationPages=[];
const byId=new Map(classes.map(n=>[n.id,n]));
const runtime={
 pageAlgebra:w=>{pages.push(w.page); return {maps:()=>[{two:0,j:0}],coefficientState:()=>({resolved:true,value:1})}},
 periodicDifferentials:w=>w.differentials.filter(d=>d.page===w.page).map(diff=>({diff,
   sourceNode:byId.get(diff.source_id),targetNode:byId.get(diff.target_id),
   sourceGrade:byId.get(diff.source_id).grade,targetGrade:byId.get(diff.target_id).grade})),
 periodicRelations:w=>{relationPages.push(w.page);return [{proposition:{id:'h1',conclusion:{chart_connection:{multiplier:'h_1'}}},
   source:classes[1],target:classes[3],sourceGrade:classes[1].grade,targetGrade:classes[3].grade}]},
 packedClassInstances:(w,b,m)=>{packPages.push(w.page);return classes.map(item=>({item,grade:item.grade,
   instanceKey:item.id,shape:item.id==='target'?'finite-two-tower':'dot',modulePorts:['0:0','1:0','2:0'],dx:0,dy:0,size:4}))},
 differentialRenderGroups:(w,items)=>items,liveClassesAt:w=>w.classes,
 pointFor:(g,m)=>({x:(g.stem+.5)*m.cell,y:-(g.filtration+.5)*m.cell}),
 packedPoint:(r,m)=>runtime.pointFor(r.grade,m),
 coefficientPortPoint:(r,m,port)=>{const p=runtime.pointFor(r.grade,m);
   return r.shape==='finite-two-tower'?{x:p.x,y:p.y+(1-Number((port||'0:0').split(':')[0]))*6.4}:p},
 classInstanceKey:(id,g)=>`${id}:${g.stem}:${g.filtration}`,e2DisplaySlot:()=>'',
 periodicDisplayLabel:r=>r.item.label,quotientRepresentativeLabel:()=>'',
 differentialDisplayCoefficient:()=>({value:1,latex:'1'}),differentialVisualState:()=> 'accepted',
 f4DisplayMultiply:(a,b)=>a*b
};
"""


def test_snapshot_does_not_change_active_page_and_uses_lower_page_for_dots_and_lines():
    result = run(MOCK + "const original=JSON.stringify(ws); const result=T.buildSnapshot(ws," + json.dumps(DEFAULTS) + ",runtime); console.log(JSON.stringify({result,pages,packPages,relationPages,unchanged:original===JSON.stringify(ws)}));")
    assert result["unchanged"]
    assert result["pages"] == [2, 3, 5]
    assert result["packPages"] == [2]
    assert result["relationPages"] == [2]
    snapshot = result["result"]
    assert len(snapshot["nodes"]) == 4
    assert [item["page"] for item in snapshot["differentials"]] == [3, 5]
    arrow = snapshot["differentials"][0]
    # The triple's bottom dot is kD. Never connect to its centre (2kD).
    assert arrow["to"]["y"] == pytest.approx(2.84)
    assert snapshot["relations"][0]["from"] == arrow["to"]


def test_scalar_alias_connects_to_its_own_two_adic_port_not_the_owner_base():
    result = run(MOCK + r"""
const alias={...classes[1],id:'twice-target',label:'2kD',style:{e2_pattern:'K',two_valuation:1}};
classes[1].style.e2_pattern='K'; classes.push(alias); byId.set(alias.id,alias);
ws.differentials[0].target_id=alias.id;
const packed=runtime.packedClassInstances;
runtime.packedClassInstances=(...args)=>packed(...args).filter(record=>record.item.id!==alias.id);
runtime.e2DisplaySlot=(n,g)=>n?.style?.e2_pattern?`${n.style.e2_pattern}:${g.stem}:${g.filtration}`:'';
const snapshot=T.buildSnapshot(ws,{pageStart:2,pageEnd:3,
 bounds:{stemMin:0,stemMax:10,filtrationMin:0,filtrationMax:8}},runtime);
console.log(JSON.stringify(snapshot.differentials[0]));
""")
    assert result["to"]["y"] == 3  # Middle of kD, 2kD, 4kD.


def test_undetermined_overall_scalar_is_not_silently_exported_as_one():
    result = run(MOCK + r"""
ws.differentials[0].proposition_id='claim';
ws.propositions=[{id:'claim',conclusion:{coefficient_parameter:{symbol:'c'}}}];
runtime.differentialDisplayCoefficient=()=>null;
const snapshot=T.buildSnapshot(ws,{pageStart:2,pageEnd:3,
 bounds:{stemMin:0,stemMax:10,filtrationMin:0,filtrationMax:8}},runtime);
console.log(JSON.stringify(snapshot.differentials[0]));
""")
    assert result["coefficient"] == "?"


def test_browser_and_deployed_export_modules_are_identical():
    assert SCRIPT.read_bytes() == (ROOT / "public/static/tex-export.js").read_bytes()


def test_palette_matches_local_reu_template_when_available():
    template = ROOT.parents[1] / "REU Projects/Final Presentation/Figures/Drawing/2Sigma_corrected_E11above.tex"
    if not template.exists():
        pytest.skip("Local research template is not part of the code repository")
    source = template.read_text(encoding="utf-8")
    palette = run("console.log(JSON.stringify(T.palette));")
    for r, color in palette.items():
        if r == "19":
            continue  # No d19 style in the provided template; explicit addition.
        assert f"d{r}/.style={{draw={{{color}}}" in source


def test_real_integer_runtime_exports_periodic_nodes_and_full_requested_arrows():
    sys.path.insert(0, str(ROOT / "backend"))
    from domain.e2_import import materialize_verified_e2_records
    from domain.models import Project, Workspace
    from domain.published_differentials import ensure_published_differential_charts

    workspace = Workspace(id="ws_integer", name="integer")
    materialize_verified_e2_records(workspace, "integer")
    workspace.settings["rendering"]["period_lattice"] = [
        {"id": "D8", "stem": 64, "filtration": 0, "exponent_domain": "integer"},
        {"id": "g", "stem": 20, "filtration": 4, "exponent_domain": "nonnegative"},
    ]
    project = Project("hfpss_studio", "integer", [workspace])
    ensure_published_differential_charts(project)
    script = r'''
const fs=require('node:fs'),vm=require('node:vm');
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for(const name of ['graded-quotient','vector-page-algebra','page-algebra','cell-layout',
 'display-basis','chart-presentation','tex-export'])
 vm.runInContext(fs.readFileSync(`backend/static/${name}.js`,'utf8'),context);
context.window.HFPSSCellLayout=context.HFPSSCellLayout;
const source=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(source.slice(0,source.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.project=JSON.parse(fs.readFileSync(0,'utf8'));
const result=vm.runInContext(`
state.project=project;state.workspaceId='ws_integer';
const ws=project.workspaces[0], old=JSON.stringify(ws);
const snapshot=window.HFPSSChartTex.buildSnapshot(ws,{pageStart:2,pageEnd:5,
 bounds:{stemMin:60,stemMax:85,filtrationMin:0,filtrationMax:8}},
 {pageAlgebra,periodicDifferentials,periodicRelations,packedClassInstances,
 differentialRenderGroups,liveClassesAt,pointFor,packedPoint,classInstanceKey,e2DisplaySlot,
 periodicDisplayLabel,quotientRepresentativeLabel,differentialDisplayCoefficient,
 differentialVisualState,f4DisplayMultiply,f4DisplayLatex,coefficientPortPoint});
({snapshot,unchanged:old===JSON.stringify(ws),tex:window.HFPSSChartTex.render(snapshot),
 debug:ws.differentials.filter(d=>d.page<=5).map(d=>({id:d.id,page:d.page,period:d.period_stem}))})
`,context);
process.stdout.write(JSON.stringify(result));
'''
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(asdict(project)),
                               text=True, encoding="utf-8", capture_output=True, timeout=90)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["unchanged"]
    snapshot = result["snapshot"]
    assert any(node["stem"] == 65 and node["filtration"] == 1 for node in snapshot["nodes"])
    assert snapshot["relations"]
    assert {item["page"] for item in snapshot["differentials"]} == {3, 5}, result["debug"]
    assert any(item["from"]["x"] > 63 for item in snapshot["differentials"])
    assert "E_{2}\\text{ with }d_{2},\\ldots,d_{5}" in result["tex"]


@pytest.fixture(scope="module")
def production_range_exports():
    sys.path.insert(0, str(ROOT / "backend"))
    from domain.migrations import migrate_project
    from domain.seed import demo_project

    script = r'''
const fs=require('node:fs'),vm=require('node:vm');
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for(const name of ['graded-quotient','vector-page-algebra','page-algebra','cell-layout',
 'display-basis','chart-presentation','tex-export'])
 vm.runInContext(fs.readFileSync(`backend/static/${name}.js`,'utf8'),context);
context.window.HFPSSCellLayout=context.HFPSSCellLayout;
const source=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(source.slice(0,source.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.project=JSON.parse(fs.readFileSync(0,'utf8'));
const result=vm.runInContext(`
state.project=project;
const runtime={pageAlgebra,periodicDifferentials,periodicRelations,packedClassInstances,
 differentialRenderGroups,liveClassesAt,pointFor,packedPoint,classInstanceKey,e2DisplaySlot,
 periodicDisplayLabel,quotientRepresentativeLabel,differentialDisplayCoefficient,
 differentialVisualState,f4DisplayMultiply,f4DisplayLatex,coefficientPortPoint};
const output=[];
for(const id of ['ws_integer','ws_sigma_i','ws_2sigma_i','ws_3sigma_i','ws_sigma_i_2sigma_j']) {
 const ws=project.workspaces.find(w=>w.id===id);state.workspaceId=id;
 for(const [start,end] of [[2,24],...[2,3,5,9,11,19,23,24].map(r=>[r,r])]) {
  try {
   const s=window.HFPSSChartTex.buildSnapshot(ws,{pageStart:start,pageEnd:end,
    bounds:{stemMin:-4,stemMax:20,filtrationMin:0,filtrationMax:10}},runtime);
   const tex=window.HFPSSChartTex.render(s);
   output.push({id,start,end,nodes:s.nodes.length,arrows:s.differentials.length,
    valid:tex.endsWith('\\\\end{document}\\n')});
  } catch(error) {output.push({id,start,end,error:error.message});}
 }
}
output
`,context);
process.stdout.write(JSON.stringify(result));
'''
    completed = subprocess.run(["node", "--max-old-space-size=2048", "-e", script], cwd=ROOT,
                               input=json.dumps(asdict(migrate_project(demo_project()))),
                               text=True, encoding="utf-8", capture_output=True, timeout=180)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_all_five_computed_gradings_export_full_range_and_late_pages(production_range_exports):
    assert len(production_range_exports) == 45
    failures = [row for row in production_range_exports if row.get("error") or not row.get("valid")]
    assert failures == []
    for row in production_range_exports:
        if row["start"] == 2:
            assert row["nodes"] > 0
            if row["end"] == 24:
                assert row["arrows"] > 0
