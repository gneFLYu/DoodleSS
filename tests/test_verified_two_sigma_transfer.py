"""The repaired FN-2I-006 transfer argument, on unmodified production charts.

The coefficient Euler sequence is exact on E2, not on every Er. Transfer
naturality forces a nonzero d5; the separately declared Galois-fixed basis
fixes its F4 unit. No review differential is admitted by this test module.
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
from domain.seed import demo_project


TWO = "ws_2sigma_i"
ATLAS = {TWO: 0, "ws_q8-ro-a0-b2": 0, "ws_q8-ro-a2-b2": -32}
FACT = "FN-2I-006"


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def test_repaired_certificate_and_exact_ports_are_transported_to_all_three_charts(project):
    images = [w for w in project.workspaces if w.id == TWO
              or w.settings.get("atlas_transport", {}).get("source_workspace_id") == TWO]
    assert {w.id for w in images} == set(ATLAS)
    for ws in images:
        shift = ATLAS[ws.id]
        assert ws.settings.get("atlas_transport", {}).get("stem_shift", 0) == shift
        claims = {p.id: p for p in ws.propositions}
        matching = [d for d in ws.differentials if claims[d.proposition_id].conclusion.get("fact_id") == FACT]
        assert len(matching) == 1
        row = matching[0]
        claim = claims[row.proposition_id]
        nodes = {n.id: n for n in ws.classes}
        source, target = nodes[row.source_id], nodes[row.target_id]
        assert row.status == claim.status == "verified"
        assert row.page == 5 and row.period_stem == 8
        assert (source.grade.stem, source.grade.filtration) == (shift, 2)
        assert (target.grade.stem, target.grade.filtration) == (shift - 1, 7)
        assert (source.style["e2_pattern"], target.style["e2_pattern"]) == ("I02", "I33")
        for node in (source, target):
            assert node.style.get("two_valuation", 0) == node.style.get("j_order", 0) == 0
        conclusion = claim.conclusion
        assert conclusion["source_status"] == "independently-verified"
        assert not conclusion["source_blockers"]
        certificate = conclusion["verification_certificate"]
        assert certificate["method"] == "coefficient Euler sequence and transfer naturality"
        assert certificate["status"] == "verified" and certificate["source_refs"]
        assert certificate["derivation"]
        assert {"FN-2I-001", "FN-2I-005"} <= set(certificate["premises"])
        assert certificate["coefficient_sequence"] == (
            "0 -> M tensor sigma_j -> Ind_C4<j>^Q8 Res(M) -> M -> 0, at E2 only")
        assert certificate["transfer_subgroups"] == {"nonkernel": "C4<j>", "kernel": "C4<i>"}
        assert certificate["c4_period"]["degree"] == "14+2sigma"
        assert certificate["c4_period"]["permanent_unit"]
        assert "F4[[mu]]{t} / (mu*t) = F4{t}" in certificate["c4_target_quotient"]
        assert "d3(P^-1 T2 varpi^2)=mu*t" in certificate["c4_target_quotient"]
        assert "alpha nonzero" in certificate["derivation"]
        assert "Nonzero follows from transfer" in certificate["normalization"]
        assert "separately" in certificate["normalization"]
        assert "never im(transfer)=ker(Euler) on arbitrary Er" in certificate["scope"]
        assert "not permanence of D" in certificate["scope"]
        assert conclusion["period_kind"] == "repeated-differential-pattern"
        assert not conclusion["period_is_invertible"]
        assert conclusion["coefficient_normalization"]["id"] == "pure-sigma-i-galois-fixed"
        assert conclusion["coefficient_normalization"]["value"] == 1
        assert not ws.settings.get("coefficient_assignments")

        # The earlier transfer proof gives a different coefficient port,
        # different subgroup, and different scope (zero outgoing, not death).
        pc = next(p for p in ws.propositions if p.conclusion.get("fact_id") == "DER-2I-TRANSFER-TWO-cycle")
        assert pc.status == "verified" and pc.kind == "permanent-cycle"
        assert pc.conclusion["cycle_constraint"] == "outgoing-only"
        pc_source = nodes[pc.conclusion["source_id"]]
        assert pc_source.style["e2_pattern"] == "I00"
        assert pc_source.style["two_valuation"] == 1
        assert pc.conclusion["transfer_certificate"]["subgroup"] == "C4<i>"
        # Later rows require their own d23-product/finite-quotient certificates,
        # not an implicit promotion from this transfer proof.
        for fact in ("FN-2I-019", "FN-2I-020", "FN-2I-021"):
            later = [p for p in ws.propositions if p.conclusion.get("fact_id") == fact]
            assert later and all(p.status == "verified" for p in later)
            for claim in later:
                certificate = claim.conclusion["verification_certificate"]
                assert certificate["status"] == "verified"
                assert certificate["method"] == "Published d23 product and finite E21 quotient"
                assert certificate["source_refs"] and certificate["premises"]
                assert certificate["table_comparison"]["table_period_stem"] == 64


RUNTIME = r"""
const fs=require('node:fs'),vm=require('node:vm');
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
const bounds={stemMin:shift-2,stemMax:shift+80,filtrationMin:0,filtrationMax:32};
const definitions=()=>JSON.stringify([ws.classes,ws.cells,ws.differential_maps,
 ws.differentials,ws.propositions,ws.settings]);
const before=definitions();
const claims=new Map(ws.propositions.map(p=>[p.id,p]));
const row=ws.differentials.find(d=>claims.get(d.proposition_id)?.conclusion?.fact_id==='FN-2I-006');
const probeSpecs=[
 ...[0,8,16,24,32,64].flatMap(s=>[
  ['A'+s,'I02',s,2,0,0],['T'+s,'I33',s-1,7,0,0],['jT'+s,'I33',s-1,7,0,1]]),
 ['Ag','I02',20,6,0,0],['Tg','I33',19,11,0,0],
 ...[0,8,16,24,32].flatMap(s=>[
  ['twoD'+s,'I00',s,0,1,0],['fourD'+s,'I00',s,0,2,0],['tailD'+s,'I00',s,0,3,0]]),
 ...[7,23].flatMap(s=>[['kh2'+s,'I31',s,5,0,0],['twoKh2'+s,'I31',s,5,1,0]]),
 ...[11,19,27].flatMap(s=>[['h2'+s,'I31',s,1,0,0],['twoH2'+s,'I31',s,1,1,0]]),
 ['reviewH1D3','I11',25,1,0,0],['reviewH1D4','I11',33,1,0,0],
 ['reviewD4two','I00',24,8,1,0],['reviewD5four','I00',32,8,2,0],
];
const pages=[3,4,5,6,7,8,9,10,11,12,13,14,21,22,23,24].map(page=>{
 ws.page=page;
 const algebra=pageAlgebra(ws,bounds),edges=periodicDifferentials(ws,bounds);
 const active=ws.differentials.filter(d=>d.page===page);
 const snapshots=active.map(d=>{
   const pair=algebra.endpoints(d),s=pair.source,t=pair.target;
   return {id:d.id,fact:claims.get(d.proposition_id)?.conclusion?.fact_id,status:d.status,
     canApply:algebra.canApply(d),source:s.grade,target:t.grade,
     sourceLive:algebra.live(s,s.grade),targetLive:algebra.live(t,t.grade),
     sourceKnown:algebra.knownCycle(s,s.grade),targetKnown:algebra.knownCycle(t,t.grade),
     sourceTwo:s.style.two_valuation||0,targetTwo:t.style.two_valuation||0,
     maps:algebra.maps(s,t,s.grade,t.grade).length};
 });
 return {page,blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
   coefficient:algebra.coefficientState(row),snapshots,
   edges:edges.map(e=>({id:e.diff.id,fact:claims.get(e.diff.proposition_id)?.conclusion?.fact_id,
     source:e.sourceGrade,target:e.targetGrade,canApply:algebra.canApply(e.diff),
     sourceLive:algebra.live(e.sourceNode,e.sourceGrade),targetLive:algebra.live(e.targetNode,e.targetGrade),
     maps:algebra.maps(e.sourceNode,e.targetNode,e.sourceGrade,e.targetGrade).length})),
   probes:probeSpecs.map(([id,pattern,stem,filtration,two,j])=>{
     const grade={stem:stem+shift,filtration};
     const node={style:{e2_pattern:pattern,e2_components:{[pattern]:1},two_valuation:two,j_order:j}};
     return {id,live:algebra.live(node,grade),knownCycle:algebra.knownCycle(node,grade),
       ports:[...(algebra.ports(node,grade)||[])]};
   })};
});
({id:ws.id,shift,rowId:row.id,pages,definitionsUnchanged:before===definitions()});
`,context);
process.stdout.write(JSON.stringify(output));
"""


@pytest.fixture(scope="module", params=list(ATLAS))
def runtime(request, project):
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


def test_e5_draws_every_eight_stem_family_and_forward_g_with_live_endpoints(runtime):
    e5 = page(runtime, 5)
    shift = runtime["shift"]
    edges = [edge for edge in e5["edges"] if edge["fact"] == FACT]
    positions = {(e["source"]["stem"] - shift, e["source"]["filtration"],
                  e["target"]["stem"] - shift, e["target"]["filtration"]) for e in edges}
    assert {(s, 2, s - 1, 7) for s in (0,8,16,24,32,64)} <= positions
    assert (20, 6, 19, 11) in positions
    assert all(e["canApply"] and e["sourceLive"] and e["targetLive"] and e["maps"] for e in edges)
    assert e5["coefficient"]["resolved"] and e5["coefficient"]["value"] == 1
    for r in (3, 4, 6):
        assert not [e for e in page(runtime, r)["edges"] if e["fact"] == FACT]


def test_d3_tails_and_d5_constants_are_distinct_actual_quotients(runtime):
    for s in (0,8,16,24,32,64):
        assert probe(page(runtime, 3), "jT" + str(s))["live"]
        for r in (4,5):
            for prefix in ("A", "T"):
                item = probe(page(runtime, r), prefix + str(s))
                assert item["live"] and item["knownCycle"], (r, prefix, s, item)
            assert not probe(page(runtime, r), "jT" + str(s))["live"]
        for prefix in ("A", "T", "jT"):
            item = probe(page(runtime, 6), prefix + str(s))
            assert not item["live"], (prefix, s, item)
    for ident in ("Ag", "Tg"):
        assert probe(page(runtime, 5), ident)["live"]
        assert not probe(page(runtime, 6), ident)["live"]


def test_witt_two_layer_and_other_sixteen_and_thirty_two_stem_families_stay_distinct(runtime):
    e5, e6 = page(runtime, 5), page(runtime, 6)
    for s in (0,16,32):
        assert probe(e5, "twoD" + str(s))["live"]
        assert probe(e6, "twoD" + str(s))["live"]
    for s in (8,24):
        assert probe(e5, "twoD" + str(s))["live"]
        assert not probe(e6, "twoD" + str(s))["live"]
        assert probe(e6, "fourD" + str(s))["live"]
        assert probe(e6, "tailD" + str(s))["live"]
    for s in (7,23):
        assert probe(e5, "twoKh2" + str(s))["live"]
        assert not probe(e6, "twoKh2" + str(s))["live"]
        assert probe(e6, "kh2" + str(s))["live"]
    for s in (11,27):
        assert probe(e5, "h2" + str(s))["live"]
        assert not probe(e6, "h2" + str(s))["live"]
        assert probe(e6, "twoH2" + str(s))["live"]
    assert probe(e6, "h219")["live"]
    for ident in ("reviewH1D3", "reviewH1D4", "reviewD4two", "reviewD5four"):
        assert probe(e6, ident)["live"], (ident, probe(e6, ident))
    for fact, two in (("FN-2I-012", 1), ("FN-2I-013", 2)):
        row = next(r for r in page(runtime, 7)["snapshots"] if r["fact"] == fact)
        assert row["status"] == "verified" and row["canApply"]
        assert row["targetTwo"] == two and row["sourceLive"] and row["targetLive"]
    for fact in ("FN-2I-003", "FN-2I-004", "FN-2I-005"):
        assert any(e["fact"] == fact for e in e5["edges"])


def test_new_family_does_not_create_later_conflicts_or_apply_review_differentials(runtime):
    assert runtime["definitionsUnchanged"]
    for row in runtime["pages"]:
        assert row["blocked"] is None, (row["page"], row["conflicts"])
        # The verified FN020 and the permanent Euler sum now specify the
        # entire two-line E21 source map, including its surviving kernel.
        assert not row["conflicts"], (row["page"], row["conflicts"])
        if row["page"] == 21:
            for fact in ("FN-2I-019", "FN-2I-020", "FN-2I-021"):
                snapshots = [item for item in row["snapshots"] if item["fact"] == fact]
                assert snapshots and all(item["status"] == "verified" and item["canApply"]
                                         for item in snapshots), (fact, snapshots)
                assert any(edge["fact"] == fact and edge["canApply"] for edge in row["edges"])
        for edge in row["edges"]:
            if edge["canApply"]:
                assert edge["sourceLive"] and edge["targetLive"] and edge["maps"], (row["page"], edge)
        for pending in row["snapshots"]:
            if pending["status"] == "review":
                assert not pending["canApply"], (row["page"], pending)
    assert all(probe(row, "twoD0")["live"] for row in runtime["pages"])
