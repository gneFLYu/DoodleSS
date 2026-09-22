"""Production FN009 d11 detected by C4 restriction, without admissions.

A=(x^2+y^2)u and R=x^2 h1 u support d11 on the independently
detected D4 and D8 blocks. They target C=(h1+xv1)u and Q=C*h1.
At the Q target, primitive d3 first removes the positive-j ideal and
FN006 d5 removes P+Q, with P=(yh2+xh1v1)u. Thus d11 hits the
remaining common finite class [P]=[Q], not two independent targets.
The 32-stem repeated formula does not assert that D4 is a unit.
"""

from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess

import pytest

from backend.domain.migrations import migrate_project
from backend.domain.seed import demo_project


ROOT = Path(__file__).resolve().parents[1]
THREE = "ws_3sigma_i"
FACT = "FN-3I-009"
IDS = {"diff_three_d11_30", "formal_diff_fn-3i-009_2"}
PAGES = (3, 4, 5, 6, 9, 10, 11, 12)
TRANSLATES = {
    "anchor": (0, 0), "D8": (64, 0),
    "g": (20, 4), "D8g": (84, 4),
}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    selected = [ws for ws in project.workspaces if ws.id == THREE or
                ws.settings.get("atlas_transport", {}).get("source_workspace_id") == THREE]
    assert len(selected) == 3 and any(ws.id == THREE for ws in selected)
    return selected


def shift_of(workspace):
    return workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)


def family_rows(workspace):
    selected = [row for row in workspace.differentials if
                any(row.id.endswith(suffix) for suffix in IDS)]
    assert len(selected) == 2
    return selected


RUNTIME = r"""
const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for(const name of ['graded-quotient.js','vector-page-algebra.js','page-algebra.js'])
  vm.runInContext(fs.readFileSync('backend/static/'+name,'utf8'),context);
const app=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(app.slice(0,app.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.input=input;
const output=vm.runInContext(`
state.project=input.project;
state.project.workspaces.map(ws=>{
  const originalPage=ws.page,shift=ws.settings.atlas_transport?.stem_shift||0;
  const definitions=()=>JSON.stringify([ws.classes,ws.cells,ws.differential_maps,
    ws.propositions,ws.differentials,ws.settings]);
  const before=definitions();
  const claims=ws.propositions.filter(p=>p.conclusion?.fact_id==='FN-3I-009');
  const claimIds=new Set(claims.map(p=>p.id));
  const rows=ws.differentials.filter(d=>claimIds.has(d.proposition_id));
  if(rows.length!==2) throw Error('Expected two production FN009 maps: '+ws.id);
  const bounds={stemMin:shift+28,stemMax:shift+151,filtrationMin:0,filtrationMax:19};
  const pages=input.pages.map(page=>{
    ws.page=page;
    const algebra=pageAlgebra(ws,bounds);
    if(!algebra) throw Error('Missing page algebra: '+ws.id);
    const edges=periodicDifferentials(ws,bounds).filter(e=>rows.some(d=>d.id===e.diff.id));
    function probe(components,grade,extra={}){
      const style={e2_components:components,...extra};
      const terms=Object.entries(components);
      if(terms.length===1 && terms[0][1]===1) style.e2_pattern=terms[0][0];
      const node={style};
      return {grade,live:algebra.live(node,grade),knownCycle:algebra.knownCycle(node,grade),
        trusted:algebra.inTrustedDomain(grade),slots:algebra.endpointSlots(node,grade)};
    }
    function ports(pattern,grade){
      return [...(algebra.ports({style:{e2_pattern:pattern}},grade)||[])];
    }
    function block(grade){
      const residue=((grade.stem%64)+64)%64;
      const value=algebra.vectorBlocks.get('S22H+S22Y:'+residue+':'+grade.filtration);
      return value ? {rank:value.q.dimension,barriers:value.barriers.length} : null;
    }
    const occurrences=input.blocks.flatMap(power=>input.translates.map(([name,ds,df])=>{
      const base=8*power+shift+ds;
      const aGrade={stem:base-2,filtration:2+df},rGrade={stem:base-1,filtration:3+df};
      const cGrade={stem:base-3,filtration:13+df},qGrade={stem:base-2,filtration:14+df};
      return {power,name,aGrade,rGrade,cGrade,qGrade,
        A:probe({S62:1},aGrade),R:probe({S73:1},rGrade),
        C:probe({S11:1},cGrade),Cj:probe({S11:1},cGrade,{j_order:1}),
        P:probe({S22Y:1},qGrade),Q:probe({S22H:1},qGrade),
        Qj:probe({S22H:1},qGrade,{j_order:1}),
        PplusQ:probe({S22Y:1,S22H:1},qGrade),
        PplusZetaQ:probe({S22Y:1,S22H:2},qGrade),
        sourcePorts:{A:ports('S62',aGrade),R:ports('S73',rGrade)},
        targetPorts:{C:ports('S11',cGrade),P:ports('S22Y',qGrade),Q:ports('S22H',qGrade)},
        targetBlock:block(qGrade),
        maps:rows.map(diff=>{
          const pair=algebra.endpoints(diff),isA=pair.source.style.e2_pattern==='S62';
          const sourceGrade=isA?aGrade:rGrade,targetGrade=isA?cGrade:qGrade;
          const same=(a,b)=>a.stem===b.stem && a.filtration===b.filtration;
          return {id:diff.id,sourceGrade,targetGrade,
            sourcePattern:pair.source.style.e2_pattern,targetPattern:pair.target.style.e2_pattern,
            canApply:algebra.canApply(diff),coefficient:algebra.coefficientState(diff),
            sourceLive:algebra.live(pair.source,sourceGrade),targetLive:algebra.live(pair.target,targetGrade),
            count:algebra.maps(pair.source,pair.target,sourceGrade,targetGrade).length,
            rendered:edges.filter(e=>e.diff.id===diff.id && same(e.sourceGrade,sourceGrade)
              && same(e.targetGrade,targetGrade)).map(e=>({status:e.diff.status,
                sourceLive:algebra.live(pair.source,e.sourceGrade),targetLive:algebra.live(pair.target,e.targetGrade)}))};
        })};
    }));
    return {page,blockedFromPage:algebra.blockedFromPage,conflicts:algebra.conflicts,
      occurrences,renderedCount:edges.length};
  });
  ws.page=originalPage;
  return {id:ws.id,shift,pages,definitionsUnchanged:before===definitions()};
});
`,context);
process.stdout.write(JSON.stringify(output));
"""


@pytest.fixture(scope="module")
def audit(project):
    # Omit independent sectors only from serialization; do not alter any
    # selected class, claim, matrix, coefficient, or admission status.
    payload = {
        "project": asdict(replace(project, workspaces=images(project))),
        "pages": list(PAGES), "blocks": [4, 8],
        "translates": [[name, *delta] for name, delta in TRANSLATES.items()],
    }
    completed = subprocess.run(
        ["node", "-e", RUNTIME], cwd=ROOT, input=json.dumps(payload),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=180,
    )
    return json.loads(completed.stdout)


def observations(audit, page):
    for workspace in audit:
        result = next(row for row in workspace["pages"] if row["page"] == page)
        for occurrence in result["occurrences"]:
            yield workspace, result, occurrence


def test_fn009_verified_certificate_is_independent_of_january_and_odd_d9(project):
    for workspace in images(project):
        claims = {p.id: p for p in workspace.propositions}
        for row in family_rows(workspace):
            claim = claims[row.proposition_id]
            metadata = claim.conclusion
            assert metadata["fact_id"] == FACT
            assert row.status == claim.status == metadata["admission_status"] == "verified"
            assert row.page == metadata["page"] == 11
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"]
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["method"] == "C4 restriction detection and finite E11 quotient"
            assert certificate["source_refs"] and certificate["derivation"]
            assert "BBHS20 Proposition 5.28" in certificate["premises"]
            assert certificate["no_withdrawn_premise"] is True
            for premise in certificate["premises"]:
                assert not any(token in premise.lower() for token in (
                    "fn-3i-007", "fn-3i-008", "fn-3i-010", "euler-d9", "jan29", "2026-01-29",
                )), (row.id, premise)
            assert certificate["D_blocks"] == [4, 8]
            assert certificate["same_object_period"] == "D^8"
            assert row.period_stem == metadata["period_stem"] == certificate["paired_pattern_stem"] == 32
            assert metadata["period_kind"] == "repeated-differential-pattern"
            assert metadata["period_is_invertible"] is False
            assert metadata["coefficient_normalization"]["value"] == 1
            if row.linear_map_id:
                assert next(m for m in workspace.differential_maps if m.id == row.linear_map_id).status == "verified"
        assert not workspace.settings.get("coefficient_assignments")


def test_fn009_uses_finite_exact_endpoint_columns_on_all_three_atlas(project):
    for workspace in images(project):
        nodes = {n.id: n for n in workspace.classes}
        for row in family_rows(workspace):
            source, target = nodes[row.source_id], nodes[row.target_id]
            is_a = row.id.endswith("diff_three_d11_30")
            expected = ("S62", "S11", 30, 2) if is_a else ("S73", "S22H", 31, 3)
            source_pattern, target_pattern, stem, filtration = expected
            assert (source.style["e2_pattern"], target.style["e2_pattern"]) == (source_pattern, target_pattern)
            assert (source.grade.stem, source.grade.filtration) == (stem + shift_of(workspace), filtration)
            assert (target.grade.stem, target.grade.filtration) == (stem - 1 + shift_of(workspace), filtration + 11)
            for node in (source, target):
                assert node.style.get("two_valuation", 0) == node.style.get("j_order", 0) == 0


def test_runtime_preserves_production_data_and_covers_both_blocks_and_periods(audit):
    assert len(audit) == 3 and any(ws["id"] == THREE for ws in audit)
    for workspace in audit:
        assert workspace["definitionsUnchanged"]
        assert [row["page"] for row in workspace["pages"]] == list(PAGES)
        for row in workspace["pages"]:
            assert row["blockedFromPage"] is None, (workspace["id"], row)
            assert not row["conflicts"], (workspace["id"], row["page"], row["conflicts"])
            assert {(o["power"], o["name"]) for o in row["occurrences"]} == {
                (power, name) for power in (4, 8) for name in TRANSLATES
            }
            for occurrence in row["occurrences"]:
                ds, df = TRANSLATES[occurrence["name"]]
                base = 8 * occurrence["power"] + workspace["shift"] + ds
                assert occurrence["aGrade"] == {"stem": base - 2, "filtration": 2 + df}
                assert occurrence["rGrade"] == {"stem": base - 1, "filtration": 3 + df}
                assert occurrence["cGrade"] == {"stem": base - 3, "filtration": 13 + df}
                assert occurrence["qGrade"] == {"stem": base - 2, "filtration": 14 + df}


def test_primitive_d3_removes_target_j_ideals_without_killing_constants(audit):
    for _, row, occurrence in observations(audit, 3):
        assert occurrence["Cj"]["live"] and occurrence["Qj"]["live"], (row, occurrence)
        assert set(occurrence["targetPorts"]["C"]) == {"0:0", "0:1"}
        assert set(occurrence["targetPorts"]["Q"]) == {"0:0", "0:1"}
    for page in (4, 5, 6, 9, 10, 11):
        for _, row, occurrence in observations(audit, page):
            assert not occurrence["Cj"]["live"] and not occurrence["Qj"]["live"], (row, occurrence)
            assert occurrence["C"]["live"] and occurrence["Q"]["live"]
            assert set(occurrence["targetPorts"]["C"]) == {"0:0"}
            assert all(set(ports) <= {"0:0"} for ports in occurrence["targetPorts"].values())


def test_d5_leaves_the_nonzero_common_pq_target_not_two_independent_d11_targets(audit):
    for _, row, occurrence in observations(audit, 5):
        assert occurrence["targetBlock"] == {"rank": 2, "barriers": 0}, (row, occurrence)
        assert occurrence["P"]["live"] and occurrence["Q"]["live"] and occurrence["PplusQ"]["live"]
    for page in (6, 9, 10, 11):
        for _, row, occurrence in observations(audit, page):
            assert occurrence["targetBlock"] == {"rank": 1, "barriers": 0}, (row, occurrence)
            assert not occurrence["PplusQ"]["live"]
            assert occurrence["P"]["live"] and occurrence["Q"]["live"] and occurrence["PplusZetaQ"]["live"]
            assert len(occurrence["P"]["slots"]) == 1
            assert occurrence["P"]["slots"] == occurrence["Q"]["slots"]
            assert sum(len(occurrence["targetPorts"][name]) for name in ("P", "Q")) == 1


def test_e11_has_48_unit_one_arrows_with_live_exact_source_and_target_ports(audit):
    count = 0
    for _, row, occurrence in observations(audit, 11):
        for name in ("A", "R", "C", "P", "Q"):
            assert occurrence[name]["live"] and occurrence[name]["knownCycle"], (row, occurrence, name)
            assert occurrence[name]["trusted"]
        assert occurrence["sourcePorts"] == {"A": ["0:0"], "R": ["0:0"]}
        for edge in occurrence["maps"]:
            assert edge["canApply"] and edge["sourceLive"] and edge["targetLive"]
            assert edge["coefficient"]["resolved"] and edge["coefficient"]["value"] == 1
            assert edge["count"] > 0 and len(edge["rendered"]) == 1, (row, occurrence, edge)
            assert edge["rendered"][0] == {"status": "verified", "sourceLive": True, "targetLive": True}
            assert edge["targetGrade"]["stem"] == edge["sourceGrade"]["stem"] - 1
            assert edge["targetGrade"]["filtration"] == edge["sourceGrade"]["filtration"] + 11
            count += 1
    assert count == 48


def test_e12_removes_only_after_sources_and_finite_target_quotients_reach_e11(audit):
    for _, row, occurrence in observations(audit, 12):
        for name in ("A", "R", "C", "Cj", "P", "Q", "Qj", "PplusQ", "PplusZetaQ"):
            assert not occurrence[name]["live"] and not occurrence[name]["knownCycle"], (row, occurrence, name)
        assert occurrence["sourcePorts"] == {"A": [], "R": []}
        assert occurrence["targetPorts"] == {"C": [], "P": [], "Q": []}
        assert occurrence["targetBlock"] == {"rank": 0, "barriers": 0}
        assert all(edge["count"] == 0 and not edge["rendered"] for edge in occurrence["maps"])


def test_d11_is_never_drawn_on_the_wrong_page(audit):
    for workspace in audit:
        for row in workspace["pages"]:
            if row["page"] == 11:
                assert row["renderedCount"] > 0
            else:
                assert row["renderedCount"] == 0, (workspace["id"], row["page"])
                assert not any(edge["rendered"] for occurrence in row["occurrences"] for edge in occurrence["maps"])
