"""SVG-only coalescing of aliases of an identical certified differential.

The chart's raw periodic occurrences retain every claim. Rendering may combine
them only with the same verified fact, exact endpoint vectors and coefficient
ports, occurrence grades and resolved coefficient state. Source IDs and proof
references remain available in the SVG title and alias attribute.
"""

from dataclasses import asdict
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess

import pytest

from backend.domain.migrations import migrate_project
from backend.domain.seed import demo_project


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = r"""
const fs=require('node:fs'),vm=require('node:vm');
const elements=new Map();
const document={body:{dataset:{}},createElement(){
  return {textContent:'',get innerHTML(){return String(this.textContent)
    .replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');}};
},querySelector(selector){
  if(!elements.has(selector)) elements.set(selector,{textContent:'',dataset:{},
    setAttribute(){},querySelectorAll(){return [];}});
  return elements.get(selector);
}};
const context=vm.createContext({document,window:{}});
for(const name of ['graded-quotient','vector-page-algebra','page-algebra'])
  vm.runInContext(fs.readFileSync('backend/static/'+name+'.js','utf8'),context);
const app=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(app.slice(0,app.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
"""


@pytest.fixture(scope="module")
def synthetic():
    script = BOOTSTRAP + r"""
const output=vm.runInContext(`
function fixture(change=()=>{}){
  const make=id=>({diff:{id,proposition_id:'claim-'+id,page:21,status:'verified',label:'FN-test'},
    sourceNode:{id:'source-'+id,style:{e2_pattern:'I31',two_valuation:0,j_order:0}},
    targetNode:{id:'target-'+id,style:{e2_components:{I62X:1,I62Y:1},two_valuation:0,j_order:0}},
    sourceGrade:{stem:55,filtration:5,representation:{sigma_i:-2}},
    targetGrade:{stem:54,filtration:26,representation:{sigma_i:-2}},periodic:id==='alias'});
  const rows=[make('primary'),make('alias')];
  const ws={id:'synthetic',page:21,settings:{},classes:[],propositions:rows.map(row=>({
    id:row.diff.proposition_id,status:'verified',statement:'equation-'+row.diff.id,
    source_ref:'reference-'+row.diff.id,source_refs:['secondary-'+row.diff.id],
    conclusion:{fact_id:'FN-test',admission_status:'verified',verification_certificate:{
      status:'verified',method:'proof-'+row.diff.id,source_refs:['certificate-'+row.diff.id]}}
  }))};
  const coefficients={primary:{resolved:true,value:1},alias:{value:1,resolved:true}};
  const apply={primary:true,alias:true};
  change({rows,ws,coefficients,apply});
  const algebra={coefficientState:diff=>coefficients[diff.id],canApply:diff=>apply[diff.id],
    endpointSlots:()=>[],conflicts:[],blockedFromPage:null};
  const before=JSON.stringify({rows,ws,coefficients,apply});
  const groups=differentialRenderGroups(ws,rows,algebra);
  return {rows,ws,algebra,groups,unchanged:before===JSON.stringify({rows,ws,coefficients,apply})};
}
const cases={};
const run=(name,change)=>{const f=fixture(change);cases[name]={
  ids:f.groups.map(g=>g.renderAliases.map(a=>a.id)),unchanged:f.unchanged,
  title:f.groups.map(differentialRenderTitle).join(' / ')};};
run('same');
run('reordered',({rows})=>{rows[1].targetNode.style.e2_components={I62Y:1,I62X:1};});
run('scalar_encoding',({rows})=>{rows[1].sourceNode.style={e2_components:{I31:1}};});
run('target_vector',({rows})=>{rows[1].targetNode.style.e2_components.I62Y=2;});
run('source_vector',({rows})=>{rows[1].sourceNode.style={e2_components:{I31:1,I11:1}};});
run('source_two',({rows})=>{rows[1].sourceNode.style.two_valuation=1;});
run('target_two',({rows})=>{rows[1].targetNode.style.two_valuation=1;});
run('source_j',({rows})=>{rows[1].sourceNode.style.j_order=1;});
run('target_j',({rows})=>{rows[1].targetNode.style.j_order=1;});
run('coefficient',({coefficients})=>{coefficients.alias.value=2;});
run('coefficient_state',({coefficients})=>{coefficients.alias.component='I62Y';});
run('unresolved',({coefficients})=>{coefficients.primary={resolved:false};coefficients.alias={resolved:false};});
run('not_admitted',({apply})=>{apply.primary=false;apply.alias=false;});
run('other_fact',({ws})=>{ws.propositions[1].conclusion.fact_id='other-table-row';});
run('missing_fact',({ws})=>{for(const claim of ws.propositions) delete claim.conclusion.fact_id;});
run('review_diff',({rows})=>{for(const row of rows) row.diff.status='review';});
run('review_claim',({ws})=>{for(const claim of ws.propositions) claim.status='review';});
run('review_conclusion',({ws})=>{for(const claim of ws.propositions) claim.conclusion.admission_status='review';});
run('review_certificate',({ws})=>{for(const claim of ws.propositions) claim.conclusion.verification_certificate.status='review';});
run('missing_certificate',({ws})=>{for(const claim of ws.propositions) delete claim.conclusion.verification_certificate;});
run('manual',({rows})=>{for(const row of rows) row.diff.manual_periodicity_id='manual';});
run('unknown_endpoint',({rows})=>{for(const row of rows) row.sourceNode.style={};});
run('grade',({rows})=>{rows[1].sourceGrade.stem+=8;rows[1].targetGrade.stem+=8;});
run('representation',({rows})=>{rows[1].sourceGrade.representation={sigma_j:-2};});
run('context',({rows})=>{rows[1].sourceNode.coefficient_context_id='other-field';});
run('page',({rows})=>{rows[1].diff.page=23;});
const historical=({rows,ws,coefficients,apply})=>{
  ws.propositions[0].conclusion.render_equation_aliases=[{
    fact_id:'historical',page:21,status:'review',scope:'same-equation-only'}];
  const old=ws.propositions[1];
  old.status=rows[1].diff.status=old.conclusion.admission_status='review';
  old.conclusion.fact_id='historical';
  old.conclusion.verification_certificate.status='review';
  coefficients.primary.id='newly-proved-coefficient';
  apply.alias=false;
};
const history=(name,change=()=>{})=>run('historical_'+name,f=>{historical(f);change(f);});
history('same');
history('old_first',({rows})=>rows.reverse());
history('other_source',({rows})=>{rows[1].sourceNode.style.e2_pattern='I11';});
history('other_target',({rows})=>{rows[1].targetNode.style.e2_components.I62Y=2;});
history('two',({rows})=>{rows[1].sourceNode.style.two_valuation=1;});
history('j',({rows})=>{rows[1].targetNode.style.j_order=1;});
history('other_occurrence',({rows})=>{rows[1].sourceGrade.stem+=32;rows[1].targetGrade.stem+=32;});
history('coefficient',({coefficients})=>{coefficients.alias.value=2;});
history('component',({coefficients})=>{coefficients.alias.component='I62Y';});
history('unresolved',({coefficients})=>{coefficients.alias.resolved=false;});
history('conditional',({rows})=>{rows[1].candidate={conditional:true,variants:[{coefficient:{value:1}}]};});
history('manual',({rows})=>{rows[1].diff.manual_periodicity_id='manual';});
history('context',({rows})=>{rows[1].targetNode.coefficient_context_id='other';});
history('rejected',({rows,ws})=>{rows[1].diff.status=ws.propositions[1].status='rejected';});
history('owner_not_admitted',({apply})=>{apply.primary=false;});
history('owner_unproved',({ws})=>{ws.propositions[0].conclusion.verification_certificate.status='review';});
history('missing_authorization',({ws})=>{delete ws.propositions[0].conclusion.render_equation_aliases;});
history('wrong_scope',({ws})=>{ws.propositions[0].conclusion.render_equation_aliases[0].scope='all';});
history('wrong_page',({ws})=>{ws.propositions[0].conclusion.render_equation_aliases[0].page=23;});
history('other_fact',({ws})=>{ws.propositions[1].conclusion.fact_id='other';});
const f=fixture();
state.project={workspaces:[f.ws],period_families:[],page_period_cycles:[]};state.workspaceId=f.ws.id;
const bounds={stemMin:50,stemMax:60,filtrationMin:0,filtrationMax:30};
chartMetrics=()=>({width:640,height:640,axisX:0,axisY:620,cell:20});
viewportBounds=()=>bounds;pageAlgebra=()=>f.algebra;pageStatusText=()=>'';
packedClassInstances=()=>[];drawingPeriodicityPreviewInstances=()=>[];
liveClassesAt=()=>[];periodicRelations=()=>[];periodicDifferentials=()=>f.rows;
cellChartLayout=()=>new Map();cellMapSvg=()=>'';cellGlyphSvg=()=>'';
drawingPeriodicityPreviewSvg=()=>'';renderMathInChart=()=>{};
let markup='';replaceSvgMarkup=(_svg,text)=>{markup=text;};
renderChart();
({cases,markup,primary:f.groups[0].diff.id,aliases:f.groups[0].renderAliases,
  textEscapeDoesNotQuote:escapeHtml('"')==='"'})
`,context);
process.stdout.write(JSON.stringify(output));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True,
                            encoding="utf-8", capture_output=True, check=True, timeout=30)
    return json.loads(result.stdout)


def test_identical_certified_fact_maps_merge_independently_of_object_key_order(synthetic):
    for name in ("same", "reordered", "scalar_encoding"):
        assert synthetic["cases"][name]["ids"] == [["primary", "alias"]]
    assert synthetic["primary"] == "primary"


def test_geometry_does_not_merge_different_vectors_ports_coefficients_or_claims(synthetic):
    exceptions = {"same", "reordered", "scalar_encoding", "historical_same", "historical_old_first"}
    for name, case in synthetic["cases"].items():
        if name not in exceptions:
            assert case["ids"] == [["primary"], ["alias"]], name


def test_explicit_historical_equation_alias_preserves_verified_primary_and_review_provenance(synthetic):
    for name in ("historical_same", "historical_old_first"):
        case = synthetic["cases"][name]
        assert case["ids"] == [["primary", "alias"]]
        assert case["unchanged"]
        assert "Historical equation alias (proof remains under review)" in case["title"]
        assert "equation-primary" in case["title"] and "equation-alias" in case["title"]
        assert "reference-primary" in case["title"] and "reference-alias" in case["title"]


def test_grouping_is_read_only_and_keeps_both_source_proofs(synthetic):
    assert all(case["unchanged"] for case in synthetic["cases"].values())
    title = synthetic["cases"]["same"]["title"]
    for name in ("primary", "alias"):
        for prefix in ("equation-", "claim-", "proof-", "reference-", "secondary-", "certificate-"):
            assert prefix + name in title
    assert {alias["id"] for alias in synthetic["aliases"]} == {"primary", "alias"}


def test_svg_has_one_arrow_with_primary_pick_id_and_all_alias_ids(synthetic):
    # Exercise the production text-node escape, which does not escape quotes.
    # Parse markup as HTML: a regex-only check can miss JSON becoming attributes.
    assert synthetic["textEscapeDoesNotQuote"]
    class Lines(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.arrows = []

        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            if tag == "line" and "data-differential" in attributes:
                self.arrows.append(attributes)

    parser = Lines()
    parser.feed(synthetic["markup"])
    assert len(parser.arrows) == 1
    attributes = parser.arrows[0]
    assert attributes["data-differential"] == "primary"
    assert json.loads(attributes["data-differential-aliases"]) == ["primary", "alias"]
    assert set(attributes) == {"class", "data-differential", "data-differential-aliases",
                               "data-pattern-period", "x1", "y1", "x2", "y2"}
    arrows = re.findall(r'<line\b[^>]*\bdata-differential="[^"]+"[^>]*>.*?</line>', synthetic["markup"])
    assert len(arrows) == 1
    assert 'data-differential="primary"' in arrows[0]
    title = unescape(re.search(r"<title>(.*?)</title>", arrows[0])[1])
    assert "equation-primary" in title and "equation-alias" in title
    assert "reference-primary" in title and "reference-alias" in title


@pytest.fixture(scope="module")
def production():
    project = migrate_project(demo_project())
    selected = [ws for ws in project.workspaces if ws.id == "ws_2sigma_i" or
                ws.settings.get("atlas_transport", {}).get("source_workspace_id") == "ws_2sigma_i"]
    assert len(selected) == 3
    script = BOOTSTRAP + r"""
context.input=JSON.parse(fs.readFileSync(0,'utf8'));
const output=vm.runInContext(`
state.project=input.project;
input.workspaces.map(id=>{
  const ws=state.project.workspaces.find(workspace=>workspace.id===id);
  ws.page=21;
  const shift=ws.settings.atlas_transport?.stem_shift||0;
  const bounds={stemMin:shift-8,stemMax:shift+96,filtrationMin:0,filtrationMax:30};
  const before=JSON.stringify(ws);
  const algebra=pageAlgebra(ws,bounds),raw=periodicDifferentials(ws,bounds);
  const snapshot=JSON.stringify(raw),groups=differentialRenderGroups(ws,raw,algebra);
  const claims=new Map(ws.propositions.map(claim=>[claim.id,claim]));
  return {id:ws.id,shift,rawCount:raw.length,groupCount:groups.length,
    unchanged:before===JSON.stringify(ws)&&snapshot===JSON.stringify(raw),
    conflicts:algebra.conflicts,
    raw:raw.map(item=>({id:item.diff.id,source:item.sourceGrade,target:item.targetGrade})),
    groups:groups.map(group=>({source:group.sourceGrade,target:group.targetGrade,
      primary:group.diff.id,aliases:group.renderAliases.map(alias=>alias.id),
      facts:group.renderAliases.map(alias=>claims.get(alias.propositionId)?.conclusion?.fact_id),
      sameProofIds:group.renderAliases.every(alias=>differentialRenderTitle(group).includes(alias.id))}))};
})`,context);
process.stdout.write(JSON.stringify(output));
"""
    # Retain the integer period-fate authority and every linked workspace.
    # Isolate each chart process to limit memory without truncating the project.
    serialized = asdict(project)
    observations = []
    for workspace in selected:
        result = subprocess.run(["node", "-e", script], cwd=ROOT,
                                input=json.dumps({"project": serialized, "workspaces": [workspace.id]}),
                                text=True, encoding="utf-8", capture_output=True, check=True, timeout=150)
        observations.extend(json.loads(result.stdout))
    return observations


def test_production_e21_all_three_atlas_group_aliases_without_losing_raw_rows(production):
    assert len(production) == 3
    for ws in production:
        assert ws["unchanged"] and not ws["conflicts"]
        assert ws["groupCount"] < ws["rawCount"]
        assert sum(len(group["aliases"]) for group in ws["groups"]) == ws["rawCount"]
        expected = sorted((row["id"], row["source"]["stem"], row["source"]["filtration"],
                           row["target"]["stem"], row["target"]["filtration"]) for row in ws["raw"])
        retained = sorted((ident, group["source"]["stem"], group["source"]["filtration"],
                           group["target"]["stem"], group["target"]["filtration"])
                          for group in ws["groups"] for ident in group["aliases"])
        assert retained == expected
        for group in ws["groups"]:
            assert group["primary"] == group["aliases"][0] and group["sameProofIds"]
            if len(group["aliases"]) > 1:
                assert len(set(group["facts"])) == 1 and group["facts"][0] in {"FN-2I-019", "FN-2I-021"}


def test_production_e21_consolidates_both_h2_seeds_and_all_three_four_layer_seeds(production):
    for ws in production:
        for stem, filtration, fact, suffixes in (
            (55, 5, "FN-2I-019", {"formal_diff_fn-2i-019_1", "formal_diff_two_d21_h2_low_derived"}),
            (16, 8, "FN-2I-021", {"formal_diff_fn-2i-021_1", "formal_diff_two_d21_tate_positive_derived",
                                  "formal_diff_two_d21_four_f0_derived"}),
        ):
            matches = [group for group in ws["groups"] if
                       (group["source"]["stem"], group["source"]["filtration"]) == (stem + ws["shift"], filtration)
                       and group["facts"][0] == fact]
            assert len(matches) == 1, (ws["id"], stem, matches)
            aliases = matches[0]["aliases"]
            assert len(aliases) == len(suffixes)
            assert all(any(ident.endswith(suffix) for ident in aliases) for suffix in suffixes)


def test_static_mirror_is_identical():
    assert (ROOT / "backend/static/app.js").read_bytes() == (ROOT / "public/static/app.js").read_bytes()
