"""Independent production P d5: no hypothetical admissions or coefficient choices.

P=(yh2+xh1v1)u is S22Y, Q=(h1+xv1)h1u is S22H, and R=x^3u
is S53. The verified P map does not finish the coupled P/Q/jQ quotient.
"""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.migrations import migrate_project
from domain.coefficient_proofs import BINDING
from domain.seed import demo_project


MIXED = "ws_sigma_i_2sigma_j"
MIXED_ATLAS = {
    MIXED: (False, 0),
    "ws_q8-ro-a1-b3": (False, -16),
    "ws_q8-ro-a2-b1": (True, 0),
    "ws_q8-ro-a2-b3": (False, -32),
    "ws_q8-ro-a3-b1": (True, -16),
    "ws_q8-ro-a3-b2": (True, -32),
}
P_FACT = "FN-MIX-004"
P_ZERO = "FN-MIX-004-even-zero"
Q_ZERO = "FN-MIX-005-Q-zero"


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def by_fact(ws, fact):
    return [p for p in ws.propositions if p.conclusion.get("fact_id") == fact]


def test_p_family_and_separately_proof_bound_c_preserve_unresolved_b_in_all_atlases(project):
    images = [w for w in project.workspaces if w.id == MIXED
              or w.settings.get("atlas_transport", {}).get("source_workspace_id") == MIXED]
    assert {w.id for w in images} == set(MIXED_ATLAS)
    for ws in images:
        reflected, shift = MIXED_ATLAS[ws.id]
        plan = ws.settings.get("atlas_transport", {})
        assert bool(plan.get("reflected", False)) == reflected
        assert plan.get("stem_shift", 0) == shift
        claims = by_fact(ws, P_FACT)
        assert len(claims) == 1
        claim = claims[0]
        row = next(d for d in ws.differentials if d.proposition_id == claim.id)
        nodes = {n.id: n for n in ws.classes}
        source, target = nodes[row.source_id], nodes[row.target_id]
        assert row.status == claim.status == "verified"
        assert row.page == 5 and row.period_stem == 16
        assert claim.conclusion["period_kind"] == "repeated-differential-pattern"
        assert not claim.conclusion["period_is_invertible"]
        assert (source.grade.stem, source.grade.filtration) == (10 + shift, 2)
        assert (target.grade.stem, target.grade.filtration) == (9 + shift, 7)
        assert (source.style["e2_pattern"], target.style["e2_pattern"]) == ("S22Y", "S53")
        for node in (source, target):
            assert node.style.get("two_valuation", 0) == node.style.get("j_order", 0) == 0
        assert claim.conclusion["verification_certificate"]["method"] == (
            "omega-transported Euler product and target survival")
        assert claim.conclusion["premise_transport_certificate"]["status"] == "verified"
        assert "coefficient_normalization" not in claim.conclusion

        zeros = by_fact(ws, P_ZERO)
        assert len(zeros) == 1
        zero = zeros[0]
        assert zero.status == "verified" and zero.kind == "zero-differential"
        assert zero.conclusion["page"] == 5 and zero.conclusion["period_stem"] == 16
        assert zero.conclusion["grade"] == {"stem": 2 + shift, "filtration": 2}
        assert zero.conclusion["e2_components"] == {"S22Y": 1}
        assert zero.conclusion["forward_period"] == {
            "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True}

        q_zeros = by_fact(ws, Q_ZERO)
        assert len(q_zeros) == 1 and q_zeros[0].status == "verified"
        assert q_zeros[0].kind == "zero-differential"
        assert q_zeros[0].conclusion["period_stem"] == 8
        # The separate c source proof is now bound without a numerical user
        # assignment. P/Q zero certificates still do not determine b.
        for fact in ("FN-MIX-002", "FN-MIX-003", "DER-MIX-D5-A-EVEN"):
            proven = by_fact(ws, fact)
            assert proven and all(p.status == "source-verified" for p in proven)
            for p in proven:
                spec = p.conclusion["coefficient_parameter"]
                assert spec["id"] == "mixed_d5_A" and spec["value"] is None
                assert spec["proof_binding"] == BINDING
                assert next(d for d in ws.differentials if d.proposition_id == p.id).status == "source-verified"
        for fact in ("FN-MIX-005",):
            pending = by_fact(ws, fact)
            assert pending and all(p.status == "review" for p in pending)
        for p in by_fact(ws, "FN-MIX-005"):
            spec = p.conclusion["coefficient_parameter"]
            assert spec["id"] == "mixed_d5_B" and spec["value"] is None
            assert "proof_binding" not in spec
        assert not ws.settings.get("coefficient_assignments")


RUNTIME = r"""
const fs=require('node:fs'), vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for(const file of ['graded-quotient.js','vector-page-algebra.js','page-algebra.js'])
  vm.runInContext(fs.readFileSync('backend/static/'+file,'utf8'),context);
const app=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(app.slice(0,app.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.input=input;
const output=vm.runInContext(`
state.project=input.project;
const ws=state.project.workspaces.find(w=>w.id===input.workspaceId);
const shift=Number(ws.settings.atlas_transport?.stem_shift||0);
const bounds={stemMin:shift-1,stemMax:shift+90,filtrationMin:0,filtrationMax:12};
const definitions=()=>JSON.stringify([ws.classes,ws.cells,ws.differential_maps,
  ws.differentials,ws.propositions,ws.settings]);
const before=definitions();
const pClaim=ws.propositions.find(p=>p.conclusion?.fact_id==='FN-MIX-004');
const row=ws.differentials.find(d=>d.proposition_id===pClaim.id);
const probes=[
 ['P', 'S22Y',10,2,0], ['P16','S22Y',26,2,0], ['P64','S22Y',74,2,0], ['Pg','S22Y',30,6,0],
 ['R', 'S53',9,7,0], ['R16','S53',25,7,0], ['R64','S53',73,7,0], ['Rg','S53',29,11,0],
 ['Peven','S22Y',2,2,0], ['Peven16','S22Y',18,2,0], ['Peveng','S22Y',22,6,0],
 ['Q','S22H',10,2,0], ['jQ','S22H',10,2,1],
 ['Qeven','S22H',18,2,0], ['jQeven','S22H',18,2,1],
];
const pages=[3,4,5,6].map(page=>{
 ws.page=page;
 const algebra=pageAlgebra(ws,bounds), pair=algebra.endpoints(row);
 const edges=periodicDifferentials(ws,bounds).filter(e=>e.diff.id===row.id);
 const points=periodicClassInstances(ws,bounds);
 return {page,blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
   coefficient:algebra.coefficientState(row),canApply:algebra.canApply(row),
   targetComponents:pair.target.style.e2_components||{[pair.target.style.e2_pattern]:1},
   edges:edges.map(e=>({source:e.sourceGrade,target:e.targetGrade,
     sourceLive:algebra.live(e.sourceNode,e.sourceGrade),targetLive:algebra.live(e.targetNode,e.targetGrade),
     maps:algebra.maps(e.sourceNode,e.targetNode,e.sourceGrade,e.targetGrade).length})),
   probes:probes.map(([id,pattern,stem,filtration,j])=>{
     const grade={stem:stem+shift,filtration};
     const node={style:{e2_pattern:pattern,e2_components:{[pattern]:1},two_valuation:0,j_order:j}};
     return {id,live:algebra.live(node,grade),knownCycle:algebra.knownCycle(node,grade),
       slots:algebra.endpointSlots(node,grade),ports:[...(algebra.ports(node,grade)||[])],
       displayed:points.some(p=>p.grade.stem===grade.stem&&p.grade.filtration===filtration
         &&p.item.style.e2_pattern===pattern&&(p.modulePorts||[]).includes('0:'+j))};
   })};
});
({id:ws.id,shift,rowId:row.id,pages,definitionsUnchanged:before===definitions()});
`,context);
process.stdout.write(JSON.stringify(output));
"""


@pytest.fixture(scope="module", params=list(MIXED_ATLAS))
def runtime(request, project):
    # Separate atlas processes retain full coverage without a single large
    # sixteen-workspace timeout. No claim is changed from the migrated project.
    completed = subprocess.run(
        ["node", "-e", RUNTIME], cwd=ROOT,
        input=json.dumps({"project": asdict(project), "workspaceId": request.param}),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=120,
    )
    return json.loads(completed.stdout)


def page(runtime, r):
    return next(item for item in runtime["pages"] if item["page"] == r)


def probe(row, ident):
    return next(item for item in row["probes"] if item["id"] == ident)


def test_fixed_unit_is_one_in_actual_and_reflected_bases_without_mutation(runtime):
    assert runtime["definitionsUnchanged"]
    for row in runtime["pages"]:
        assert row["blocked"] is None
        assert row["coefficient"]["resolved"] and row["coefficient"]["value"] == 1
        assert row["targetComponents"] == {"S53": 1}
        assert row["canApply"]
    assert not page(runtime, 3)["conflicts"]
    assert not page(runtime, 4)["conflicts"]
    assert not page(runtime, 5)["conflicts"]


def test_actual_d5_arrows_have_sixteen_stem_D8_and_forward_g_translates(runtime):
    shift = runtime["shift"]
    arrows = page(runtime, 5)["edges"]
    positions = {(a["source"]["stem"] - shift, a["source"]["filtration"],
                  a["target"]["stem"] - shift, a["target"]["filtration"]) for a in arrows}
    assert {(10, 2, 9, 7), (26, 2, 25, 7), (74, 2, 73, 7), (30, 6, 29, 11)} <= positions
    assert not {(2, 2), (18, 2), (22, 6)} & {(s, f) for s, f, _, _ in positions}
    assert all(a["sourceLive"] and a["targetLive"] and a["maps"] for a in arrows)
    for r in (3, 4, 6):
        assert not page(runtime, r)["edges"]


def test_true_d3_then_d5_quotients_remove_only_odd_p_and_the_s53_images(runtime):
    odd_and_targets = ("P", "P16", "P64", "Pg", "R", "R16", "R64", "Rg")
    for r in (3, 4, 5):
        for ident in odd_and_targets:
            item = probe(page(runtime, r), ident)
            assert item["live"] and item["knownCycle"], (r, ident, item)
            assert "0:0" in item["ports"]
    e6 = page(runtime, 6)
    for ident in odd_and_targets:
        item = probe(e6, ident)
        assert not item["live"] and not item["knownCycle"], (ident, item)
        assert not item["displayed"]
    for ident in ("Peven", "Peven16", "Peveng"):
        item = probe(e6, ident)
        assert item["live"] and item["knownCycle"], (ident, item)
        assert "0:0" in item["ports"]


def test_q_and_positive_j_q_are_known_cycles_from_the_independent_zero_certificate(runtime):
    e6 = page(runtime, 6)
    assert e6["blocked"] is None
    assert not e6["conflicts"]
    for ident in ("Q", "jQ", "Qeven", "jQeven"):
        before, after = probe(page(runtime, 5), ident), probe(e6, ident)
        assert before["live"] and before["knownCycle"], (ident, before)
        assert after["live"] and after["knownCycle"], (ident, after)
        assert ("0:1" if ident.startswith("j") else "0:0") in after["ports"]
