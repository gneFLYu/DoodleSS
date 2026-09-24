"""Display-only basis adaptation uses actual page-vector endpoint witnesses."""
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]

RUNTIME = r"""
const L=require('./backend/static/graded-quotient.js');
require('./backend/static/display-basis.js');
require('./backend/static/vector-page-algebra.js');
require('./backend/static/page-algebra.js');
require('./backend/static/chart-presentation.js');
const identity=n=>Array.from({length:n},(_,i)=>Array.from({length:n},(_,j)=>+(i===j)));
const bounds={stemMin:0,stemMax:63,filtrationMin:0,filtrationMax:6};
const node=(id,pattern,grade)=>({id,label:id,page:2,grade,style:{e2_pattern:pattern}});
function fixture(ports=['0:0'], qPorts=ports) {
  const sourceGrade={stem:6,filtration:0}, targetGrade={stem:5,filtration:3};
  const source=node('source','S',sourceGrade), p=node('p','P',targetGrade), q=node('q','Q',targetGrade);
  const target={id:'sum',label:'P+zeta Q',page:2,grade:targetGrade,style:{e2_components:{P:1,Q:2}}};
  const diff={id:'a',page:3,status:'proven',source_id:source.id,target_id:target.id};
  const ws={id:'test',page:3,classes:[source,p,q,target],differentials:[diff],differential_maps:[]};
  const cells=new Map([['S:6:0',new Set(ports)],['P:5:3',new Set(ports)],['Q:5:3',new Set(qPorts)]]);
  const vectors=HFPSSVectorPageAlgebra.create(ws,cells,[],{filtrationMin:0,filtrationMax:6});
  const f={sourceGrade,targetGrade,source,p,q,target,diff,ws,cells,vectors,resolved:true,allowed:true};
  f.algebra={
    vectorBlocks:vectors.blocks, blockedFromPage:null,
    inTrustedDomain:grade=>grade.filtration>=0&&grade.filtration<=6,
    canApply:()=>f.allowed, coefficientState:()=>({resolved:f.resolved,value:1}),
    maps:(...args)=>vectors.maps(...args),
    ports:(...args)=>vectors.ports(...args), displaySlots:(...args)=>vectors.slots(...args),
  };
  f.edge={diff,sourceNode:source,targetNode:target,sourceGrade,targetGrade};
  f.edges=[f.edge];
  f.create=()=>HFPSSChartPresentation.create(f.algebra,f.edges,bounds);
  f.block=[...vectors.blocks.values()][0];
  return f;
}
const summary=line=>line&&({
  live:line.live,uncertain:line.uncertain||false,coordinates:line.coordinates,
  entries:line.entries,adapted:line.adapted,terms:line.terms
});
"""


def run(body):
    completed = subprocess.run(
        ["node", "--max-old-space-size=128", "-e", RUNTIME + body],
        cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=True, timeout=15,
    )
    return json.loads(completed.stdout)


def test_exact_incoming_target_becomes_one_dot_and_other_vectors_keep_coordinates():
    result = run(r"""
const f=fixture(), before=JSON.stringify({ws:f.ws,q:f.block.q});
const view=f.create();
console.log(JSON.stringify({
 target:summary(view.endpoint(f.target,f.targetGrade)),p:summary(view.endpoint(f.p,f.targetGrade)),
 q:summary(view.endpoint(f.q,f.targetGrade)),representatives:view.representatives(bounds),
 dimension:f.block.q.dimension,unchanged:before===JSON.stringify({ws:f.ws,q:f.block.q})
}));
""")
    assert result["unchanged"] and result["dimension"] == 2
    assert len(result["representatives"]) == 2
    assert result["target"]["coordinates"] == [1, 0]
    assert [entry["coefficient"] for entry in result["target"]["entries"]] == [1]
    assert result["p"]["coordinates"] == [0, 1]
    assert result["q"]["coordinates"] == [3, 3]
    assert [entry["coefficient"] for entry in result["q"]["entries"]] == [3, 3]
    assert result["representatives"][0]["terms"] == [
        {"pattern": "P", "two": 0, "j": 0, "coefficient": 1},
        {"pattern": "Q", "two": 0, "j": 0, "coefficient": 2},
    ]


@pytest.mark.parametrize("guard", ["unresolved", "conditional", "unadmitted"])
def test_uncertain_coefficient_or_admission_does_not_choose_a_display_basis(guard):
    result = run(r"""
const f=fixture();
if (GUARD==='unresolved') f.resolved=false;
if (GUARD==='conditional') f.edge.candidate={conditional:true,variants:[{coefficient:{value:2}}]};
if (GUARD==='unadmitted') f.allowed=false;
const view=f.create();
console.log(JSON.stringify({line:summary(view.endpoint(f.target,f.targetGrade)),reps:view.representatives(bounds)}));
""".replace("GUARD", json.dumps(guard)))
    assert result["line"]["coordinates"] == [1, 2]
    assert result["line"]["adapted"] is False
    assert all(not point["displayBasis"]["adapted"] for point in result["reps"])


def test_multiple_dependent_images_keep_a_combination_instead_of_inventing_an_extra_basis_dot():
    result = run(r"""
const f=fixture();
const second={...f.target,id:'second',style:{e2_components:{P:1,Q:3}}};
const third={...f.target,id:'third',style:{e2_components:{P:2,Q:2}}};
f.edges.push({...f.edge,diff:{...f.diff,id:'b'},targetNode:second},
             {...f.edge,diff:{...f.diff,id:'c'},targetNode:third});
const view=f.create(), forward=view.representatives(bounds);
f.edges.reverse();const reverse=f.create().representatives(bounds);
console.log(JSON.stringify({first:summary(view.endpoint(f.target,f.targetGrade)),
 second:summary(view.endpoint(second,f.targetGrade)),third:summary(view.endpoint(third,f.targetGrade)),
 count:forward.length,stable:JSON.stringify(forward)===JSON.stringify(reverse)}));
""")
    assert result["count"] == 2 and result["stable"]
    assert result["first"]["coordinates"] == [1, 0]
    assert result["second"]["coordinates"] == [0, 1]
    assert result["third"]["coordinates"] == [3, 1]
    assert len(result["third"]["entries"]) == 2


def test_d8_repetitions_use_the_same_exact_basis_at_distinct_actual_stems():
    result = run(r"""
const f=fixture(), view=f.create(), wide={...bounds,stemMin:-59,stemMax:69};
console.log(JSON.stringify({points:view.representatives(wide),
 lines:[-59,5,69].map(stem=>summary(view.endpoint(f.target,{stem,filtration:3})))}));
""")
    assert len(result["points"]) == 6
    assert {point["grade"]["stem"] for point in result["points"]} == {-59, 5, 69}
    assert len({point["slot"] for point in result["points"]}) == 6
    assert all(line["coordinates"] == [1, 0] for line in result["lines"])
    assert len({line["entries"][0]["slot"] for line in result["lines"]}) == 3


def test_two_levels_and_positive_j_ports_remain_independent():
    result = run(r"""
const f=fixture(['0:0','1:0','0:1','1:1']), view=f.create();
const cases=[[0,0],[1,0],[0,1],[1,1]];
console.log(JSON.stringify({dimension:f.block.q.dimension,points:view.representatives(bounds),
 lines:cases.map(([two,j])=>summary(view.endpoint(f.target,f.targetGrade,two,j)))}));
""")
    assert result["dimension"] == len(result["points"]) == 8
    assert all(len(line["entries"]) == 1 for line in result["lines"])
    assert len({line["entries"][0]["slot"] for line in result["lines"]}) == 4
    for line, port in zip(result["lines"], [(0, 0), (1, 0), (0, 1), (1, 1)]):
        assert {(term["two"], term["j"]) for term in line["terms"]} == {port}
    for point in result["points"]:
        assert len({(term["two"], term["j"]) for term in point["terms"]}) == 1


@pytest.mark.parametrize("guard", ["zero-scalar-source", "missing-source", "outside-source", "outside-target"])
def test_missing_zero_or_untrusted_endpoints_cannot_supply_preferences(guard):
    result = run(r"""
const f=fixture();
if(GUARD==='zero-scalar-source') f.cells.get('S:6:0').clear();
if(GUARD==='missing-source') f.edge.sourceNode=null;
if(GUARD==='outside-source') f.edge.sourceGrade={stem:6,filtration:7};
if(GUARD==='outside-target') f.edge.targetGrade={stem:5,filtration:7};
const view=f.create();
console.log(JSON.stringify({line:summary(view.endpoint(f.target,f.targetGrade)),
 outside:summary(view.endpoint(f.target,{stem:5,filtration:7}))}));
""".replace("GUARD", json.dumps(guard)))
    assert result["line"]["adapted"] is False
    assert result["line"]["coordinates"] == [1, 2]
    assert result["outside"] is None


@pytest.mark.parametrize("guard", ["noncycle", "boundary", "barrier-nonzero", "barrier-unknown"])
def test_unavailable_or_uncertain_target_directions_do_not_adapt_the_basis(guard):
    result = run(r"""
const f=fixture();
if(GUARD==='noncycle') f.block.q=L.quotient({ambientDimension:2,cycles:[[1,0]],boundaries:[]});
if(GUARD==='boundary') f.block.q=L.quotient({ambientDimension:2,cycles:identity(2),boundaries:[[1,2]]});
if(GUARD==='barrier-nonzero') f.block.barriers.push({q:f.block.q,map:L.partialMap({
 sourceDimension:2,targetDimension:1,constraints:[{source:[1,2],target:[1]}]})});
if(GUARD==='barrier-unknown') f.block.barriers.push({q:f.block.q,map:L.partialMap({
 sourceDimension:2,targetDimension:1,constraints:[{source:[1,0],target:[0]}]})});
const view=f.create();
console.log(JSON.stringify({line:summary(view.endpoint(f.target,f.targetGrade)),points:view.representatives(bounds)}));
""".replace("GUARD", json.dumps(guard)))
    assert all(not point["displayBasis"]["adapted"] for point in result["points"])
    if guard == "barrier-unknown":
        assert result["line"]["uncertain"] is True
    else:
        assert result["line"]["live"] is False


def test_blocked_page_does_not_offer_an_alternative_presentation():
    assert run(r"""
const f=fixture();f.algebra.blockedFromPage=3;
console.log(JSON.stringify(f.create()));
""") is None


@pytest.mark.parametrize("adapted", [False, True])
def test_dependent_alias_does_not_draw_a_second_copy_of_a_shared_j_tail(adapted):
    result = run(r"""
const f=fixture(['0:0','0:1'],['0:0']);
if (!ADAPTED) f.edges=[];
const view=f.create(), grade=f.targetGrade;
const app=require('node:fs').readFileSync('backend/static/app.js','utf8');
eval(app.slice(app.indexOf('function uniqueClassDisplaySlots('),app.indexOf('function quotientRepresentativeLabel(')));
const candidates=[f.p,f.q,f.target].map(n=>({item:n,instanceKey:n.id,grade,
  algebraSlots:view.displaySlots(n,grade),modulePorts:[...view.ports(n,grade)],
  displayBasisPriority:Number(n===f.target && ADAPTED)})).filter(r=>r.modulePorts.length);
const allocated=uniqueClassDisplaySlots(candidates);
console.log(JSON.stringify({
  target:summary(view.endpoint(f.target,grade)),
  pPorts:allocated.find(r=>r.item===f.p)?.modulePorts || [],
  qPorts:allocated.find(r=>r.item===f.q)?.modulePorts || [],
  targetPorts:allocated.find(r=>r.item===f.target)?.modulePorts || [],
  slots:allocated.flatMap(r=>r.algebraSlots),
  stable:JSON.stringify(allocated.map(r=>r.algebraSlots).sort())===JSON.stringify(uniqueClassDisplaySlots([...candidates].reverse()).map(r=>r.algebraSlots).sort()),
  representatives:view.representatives(bounds).map(r=>r.slot),
  rawTargetPorts:[...f.vectors.ports(f.target,grade)],
  rawTargetLive:f.vectors.endpoint(f.target,grade).live
}));
""".replace("ADAPTED", json.dumps(adapted)))
    assert result["target"]["live"] and result["rawTargetLive"]
    assert result["stable"]
    assert result["rawTargetPorts"] == ["0:1"]  # the shared j-tail remains nonzero in the algebra
    assert len(result["slots"]) == len(set(result["slots"])) == 3
    assert set(result["slots"]) == set(result["representatives"])
    if adapted:
        assert result["targetPorts"] == ["0:0", "0:1"]
        assert result["qPorts"] == []
        assert result["pPorts"] == ["0:0"]
        assert len(result["target"]["entries"]) == 1
    else:
        assert result["targetPorts"] == []
        assert result["pPorts"] == ["0:0", "0:1"]
        assert result["qPorts"] == ["0:0"]
        assert len(result["target"]["entries"]) == 2
