"""Exercise E23 in every real saved atlas, without assigning/admitting claims.

This covers production transports and exact ports, not synthetic atlas shells.
It does not claim that the unresolved later three-sigma/mixed mathematics is
complete. Historical equations remain in the project even when a zero-outgoing
certificate excludes their displayed candidate.
"""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app import migrate_legacy_periods
from domain.models import project_from_dict, project_to_dict


SAVED = ROOT / "backend/data/project.json"
SHIFTS = ("anchor", "D8", "g")
THREE_SHIFTS = (*SHIFTS, "g3", "g4")

RUNTIME = r"""
const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for(const name of ['graded-quotient.js','vector-page-algebra.js','page-algebra.js'])
  vm.runInContext(fs.readFileSync('backend/static/'+name,'utf8'),context);
const app=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(app.slice(0,app.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.input=input;
const result=vm.runInContext(`
state.project=input.project;
const ws=state.project.workspaces.find(w=>w.id===input.workspaceId);
state.workspaceId=ws.id;
ws.page=23;
const before=JSON.stringify(ws);
const shift=ws.settings.atlas_transport?.stem_shift||0;
const bounds={stemMin:shift-24,stemMax:shift+128,filtrationMin:0,filtrationMax:40};
const algebra=pageAlgebra(ws,bounds);
const diagnostics=[];
const edges=periodicDifferentials(ws,bounds,diagnostics);
const groups=differentialRenderGroups(ws,edges,algebra);
const points=periodicClassInstances(ws,bounds);
const claims=new Map(ws.propositions.map(p=>[p.id,p]));
const rows=ws.differentials.filter(d=>d.page===23);
const observations=rows.flatMap(diff=>{
  const claim=claims.get(diff.proposition_id),metadata=claim?.conclusion||{};
  const {source,target}=algebra.endpoints(diff);
  const translates=[['anchor',0,0],['D8',64,0],['g',20,4]];
  if(['FN-3I-010','DER-3I-LEIBNIZ-W5-D23'].includes(metadata.fact_id))
    translates.push(['g3',60,12],['g4',80,16]);
  return translates.map(([translate,ds,df])=>{
    const sg={...source.grade,stem:source.grade.stem+ds,filtration:source.grade.filtration+df};
    const tg={...target.grade,stem:target.grade.stem+ds,filtration:target.grade.filtration+df};
    const same=e=>e.sourceGrade.stem===sg.stem && e.sourceGrade.filtration===sg.filtration;
    const candidate=algebra.candidateState(diff,sg,tg);
    return {id:diff.id,fact:metadata.fact_id,table:metadata.table_number,row:metadata.table_row,
      translate,source:sg,target:tg,status:diff.status,claimStatus:claim?.status,
      sourceLive:algebra.live(source,sg),targetLive:algebra.live(target,tg),
      sourcePorts:[...(algebra.ports(source,sg)||[])],
      targetPorts:[...(algebra.ports(target,tg)||[])],
      canApply:algebra.canApply(diff),
      candidate: {status:candidate.status,conditional:candidate.conditional,reasons:candidate.reasons,
        variants:candidate.variants.map(v=>({coefficient:v.coefficient,maps:v.maps}))},
      drawn:edges.filter(e=>e.diff.id===diff.id&&same(e)).map(e=>e.diff.status),
      grouped:groups.some(e=>same(e)&&e.renderAliases.some(a=>a.id===diff.id)),
      exactSourcePoint:points.some(p=>p.grade.stem===sg.stem && p.grade.filtration===sg.filtration
        && p.item.style?.e2_pattern===source.style?.e2_pattern
        && (p.modulePorts||[]).includes('1:0'))};
  });
});
// Inspect the actual earlier CD1 map, not a manually inserted death flag.
// The retained low W1 cycle and its high-g boundaries are different cases.
const priorD11=[];
if(rows.some(d=>claims.get(d.proposition_id)?.conclusion?.fact_id==='FN-3I-010')) {
  ws.page=11;
  const earlyAlgebra=pageAlgebra(ws,bounds);
  const earlyEdges=periodicDifferentials(ws,bounds);
  for(const item of observations.filter(o=>o.fact==='FN-3I-010'&&['g3','g4'].includes(o.translate))) {
    const matches=earlyEdges.filter(e=>e.diff.id.endsWith('formal_diff_three_d11_c_D1_euler_forced')
      &&e.targetGrade.stem===item.source.stem&&e.targetGrade.filtration===item.source.filtration);
    priorD11.push({translate:item.translate,target:item.source,
      witnesses:matches.map(e=>({id:e.diff.id,source:e.sourceGrade,target:e.targetGrade,
        admitted:earlyAlgebra.canApply(e.diff),status:e.diff.status}))});
  }
  ws.page=23;
}
({id:ws.id,source:ws.settings.atlas_transport?.source_workspace_id||ws.id,
  shift,rows:rows.length,observations,priorD11,diagnostics,blocked:algebra.blockedFromPage,
  conflicts:algebra.conflicts,edges:edges.length,unchanged:before===JSON.stringify(ws)});
`,context);
process.stdout.write(JSON.stringify(result));
"""


@pytest.fixture(scope="module")
def actual_atlas():
    raw = SAVED.read_bytes()
    project = migrate_legacy_periods(project_from_dict(json.loads(raw)))
    ids = {s.workspace_id for s in project.grading_sectors}
    assert len(ids) == 16
    payload = project_to_dict(project)
    results = []
    # Each process has the complete source/parameter graph, but computes one
    # chart. No cache accumulates sixteen quotient computations in memory.
    for ident in sorted(ids):
        completed = subprocess.run(
            ["node", "-e", RUNTIME], cwd=ROOT,
            input=json.dumps({"project": payload, "workspaceId": ident}),
            text=True, encoding="utf-8", capture_output=True, check=True, timeout=180,
        )
        results.append(json.loads(completed.stdout))
    assert sha256(SAVED.read_bytes()).digest() == sha256(raw).digest()
    return results


def test_all_sixteen_actual_atlases_are_computed_without_mutation(actual_atlas):
    assert len(actual_atlas) == len({w["id"] for w in actual_atlas}) == 16
    sources = {source: sum(w["source"] == source for w in actual_atlas)
               for source in {w["source"] for w in actual_atlas}}
    assert sources == {"ws_integer": 1, "ws_sigma_i": 3, "ws_2sigma_i": 3,
                       "ws_3sigma_i": 3, "ws_sigma_i_2sigma_j": 6}
    assert all(w["unchanged"] for w in actual_atlas)
    assert sum(w["rows"] for w in actual_atlas) == 15
    assert sum(w["rows"] == 0 for w in actual_atlas) == 9


def test_all_published_d23_rows_and_transports_retain_live_arrows(actual_atlas):
    seen = []
    for ws in actual_atlas:
        for item in ws["observations"]:
            if item.get("table") not in (8, 9):
                continue
            assert ws["blocked"] is None and not ws["conflicts"], ws
            assert item["status"] == item["claimStatus"] == "established"
            assert item["sourceLive"] and item["targetLive"], item
            assert item["candidate"]["status"] == "possible", item
            assert not item["candidate"]["conditional"], item
            assert item["candidate"]["variants"] and item["drawn"] == ["established"]
            assert item["grouped"]
            seen.append((ws["id"], item["table"], item["row"], item["translate"]))
    assert len(seen) == 27  # Three integer rows plus two rows in three sigma images, x3 translates.


def test_withdrawn_d23_distinguishes_low_cycles_from_earlier_high_boundaries(actual_atlas):
    images = [ws for ws in actual_atlas if ws["source"] == "ws_3sigma_i"]
    assert len(images) == 3
    for ws in images:
        assert ws["rows"] == 2 and ws["blocked"] is None
        historical = [item for item in ws["observations"] if item["fact"] == "FN-3I-010"]
        assert len(historical) == 5
        assert {p["translate"] for p in historical} == set(THREE_SHIFTS)
        for item in historical:
            assert item["fact"] == "FN-3I-010" and item["status"] == item["claimStatus"] == "review"
            assert not item["canApply"]
            assert not item["drawn"] and not item["grouped"], item
            if item["translate"] in SHIFTS:
                assert item["candidate"]["status"] == "contradicted", item
                assert item["sourceLive"] and "1:0" in item["sourcePorts"], item
                assert item["exactSourcePoint"], item
                assert "der-3i-tate-w-cycle" in json.dumps(item["candidate"]["reasons"]).lower()
            else:
                assert item["candidate"]["status"] == "absent", item
                assert item["candidate"]["reasons"] == [{
                    "code": "absent-endpoint", "message": "No nonzero branch has both endpoint ports present",
                }]
                assert not item["sourceLive"] and "1:0" not in item["sourcePorts"], item
                assert not item["exactSourcePoint"], item
                witness = next(p for p in ws["priorD11"] if p["translate"] == item["translate"])
                assert len(witness["witnesses"]) == 1, witness
                early = witness["witnesses"][0]
                assert early["status"] == "verified" and early["admitted"]
                assert early["target"] == item["source"]
                assert (early["source"]["stem"], early["source"]["filtration"]) == (
                    item["source"]["stem"]+1, item["source"]["filtration"]-11)
        assert any(d["status"] == "contradicted" for d in ws["diagnostics"])


def test_verified_w5_d23_keeps_its_own_live_witt_layer_in_every_saved_transport(actual_atlas):
    seen = set()
    for ws in actual_atlas:
        for item in ws["observations"]:
            if item.get("fact") != "DER-3I-LEIBNIZ-W5-D23":
                continue
            assert ws["blocked"] is None and not ws["conflicts"], ws
            assert item["status"] == item["claimStatus"] == "verified"
            assert item["canApply"] and item["sourceLive"] and item["targetLive"], item
            assert "1:0" in item["sourcePorts"] and item["targetPorts"] == ["0:0"]
            assert item["drawn"] == ["verified"] and item["grouped"], item
            assert item["candidate"]["status"] == "possible"
            assert not item["candidate"]["conditional"]
            seen.add((ws["id"], item["translate"]))
    images = {w["id"] for w in actual_atlas if w["source"] == "ws_3sigma_i"}
    assert len(images) == 3
    assert seen == {(ident, shift) for ident in images for shift in THREE_SHIFTS}


def test_grading_tiles_without_d23_definitions_have_no_invented_arrows(actual_atlas):
    for ws in actual_atlas:
        if ws["rows"] == 0:
            assert ws["edges"] == 0 and not ws["observations"]
