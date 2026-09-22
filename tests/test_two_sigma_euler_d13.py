"""FN018 as an actual Euler image, including its rank-one target quotient.

No claim admission or coefficient assignment is inserted by these tests.
At (29,15), K=h2^3 k^3 D^4 u and L=x^2 h2 k^3 D^5 u are the
two finite I13/I13X directions. Earlier d5 kills K+L, not both columns.
The Euler d13 kills their remaining common class and the surviving
A=x^2+y^2 source cycle. D8 and positive g translates are checked separately.
"""

from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess

import pytest

from backend.domain.migrations import migrate_project
from backend.domain.seed import demo_project


ROOT = Path(__file__).resolve().parents[1]
SOURCE_WORKSPACE = "ws_2sigma_i"
FACT = "FN-2I-018"
WORKSPACES = {SOURCE_WORKSPACE, "ws_q8-ro-a0-b2", "ws_q8-ro-a2-b2"}
SHIFTS = {"anchor": (0, 0), "D8": (64, 0), "g": (20, 4)}
PAGES = (3, 4, 5, 6, 9, 10, 13, 14)


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    selected = [ws for ws in project.workspaces if ws.id == SOURCE_WORKSPACE or
                ws.settings.get("atlas_transport", {}).get("source_workspace_id") == SOURCE_WORKSPACE]
    assert {ws.id for ws in selected} == WORKSPACES
    return selected


def shift_of(workspace):
    return workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)


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
  const claims=ws.propositions.filter(p=>p.conclusion?.fact_id==='FN-2I-018');
  if(claims.length!==1) throw Error('Expected one production FN018: '+ws.id);
  const claim=claims[0],rows=ws.differentials.filter(d=>d.proposition_id===claim.id);
  if(rows.length!==1) throw Error('Expected one production FN018 differential: '+ws.id);
  const diff=rows[0];
  const bounds={stemMin:shift+24,stemMax:shift+120,filtrationMin:0,filtrationMax:24};
  const pages=input.pages.map(page=>{
    ws.page=page;
    const algebra=pageAlgebra(ws,bounds);
    if(!algebra) throw Error('Missing page algebra: '+ws.id);
    const pair=algebra.endpoints(diff);
    const edges=periodicDifferentials(ws,bounds).filter(e=>e.diff.id===diff.id);
    function probe(components,grade,extra={}){
      const style={e2_components:components,...extra};
      const terms=Object.entries(components);
      if(terms.length===1 && terms[0][1]===1) style.e2_pattern=terms[0][0];
      const node={style};
      return {components,grade,live:algebra.live(node,grade),
        knownCycle:algebra.knownCycle(node,grade),trusted:algebra.inTrustedDomain(grade),
        slots:algebra.endpointSlots(node,grade)};
    }
    function block(members,grade){
      const residue=((grade.stem%64)+64)%64;
      const value=algebra.vectorBlocks.get(members+':'+residue+':'+grade.filtration);
      return value ? {rank:value.q.dimension,barriers:value.barriers.length} : null;
    }
    const occurrences=input.shifts.map(([name,ds,df])=>{
      const sourceGrade={stem:30+shift+ds,filtration:2+df};
      const targetGrade={stem:29+shift+ds,filtration:15+df};
      const d9SourceGrade={stem:30+shift+ds,filtration:6+df};
      const gradeMatches=(a,b)=>a.stem===b.stem && a.filtration===b.filtration;
      return {name,sourceGrade,targetGrade,
        source:probe({I62X:1,I62Y:1},sourceGrade),
        sourceX:probe({I62X:1},sourceGrade),sourceY:probe({I62Y:1},sourceGrade),
        K:probe({I13:1},targetGrade),L:probe({I13X:1},targetGrade),
        KplusL:probe({I13:1,I13X:1},targetGrade),
        KplusZetaL:probe({I13:1,I13X:2},targetGrade),
        sourceBlock:block('I62X+I62Y',sourceGrade),
        targetBlock:block('I13+I13X',targetGrade),
        d9Source:probe({I22H:1},d9SourceGrade),
        d9SourceJ:probe({I22H:1},d9SourceGrade,{j_order:1}),
        targetPorts:Object.fromEntries(['I13','I13X'].map(pattern=>[pattern,
          [...(algebra.ports({style:{e2_pattern:pattern}},targetGrade)||[])]])),
        maps:algebra.maps(pair.source,pair.target,sourceGrade,targetGrade).length,
        rendered:edges.filter(e=>gradeMatches(e.sourceGrade,sourceGrade)
          && gradeMatches(e.targetGrade,targetGrade))
          .map(e=>({status:e.diff.status,canApply:algebra.canApply(e.diff)}))};
    });
    return {page,blockedFromPage:algebra.blockedFromPage,conflicts:algebra.conflicts,
      canApply:algebra.canApply(diff),coefficient:algebra.coefficientState(diff),occurrences};
  });
  ws.page=originalPage;
  return {id:ws.id,shift,pages,definitionsUnchanged:before===definitions()};
});
`,context);
process.stdout.write(JSON.stringify(output));
"""


@pytest.fixture(scope="module")
def audit(project):
    # Keep every production claim and matrix of these three charts unchanged.
    # The other independent sectors are omitted only from serialization to
    # bound memory. No linked mixed coefficient is needed by this pure family.
    selected = images(project)
    payload = {
        "project": asdict(replace(project, workspaces=selected)),
        "pages": list(PAGES),
        "shifts": [[name, *delta] for name, delta in SHIFTS.items()],
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


def test_fn018_has_an_independent_verified_actual_product_certificate(project):
    for workspace in images(project):
        claim = next(p for p in workspace.propositions if p.conclusion.get("fact_id") == FACT)
        row = next(d for d in workspace.differentials if d.proposition_id == claim.id)
        metadata = claim.conclusion
        assert row.status == claim.status == metadata["admission_status"] == "verified"
        assert row.page == metadata["page"] == 13
        assert metadata["source_status"] == "independently-verified"
        assert not metadata["source_blockers"]
        certificate = metadata["verification_certificate"]
        assert certificate["status"] == "verified"
        assert certificate["method"] == "Euler image and actual-product target quotient"
        assert certificate["source_refs"] and certificate["derivation"]
        assert {"FN-2I-001", "FN-2I-003", "FN-2I-004", "FN-2I-009"} <= set(certificate["premises"])
        assert not any(FACT in premise for premise in certificate["premises"])
        assert row.period_stem == metadata["period_stem"] == 64
        assert metadata["period_multiplier"] == "D^8"
        assert metadata["period_is_invertible"] is True
        assert metadata["coefficient_normalization"]["value"] == 1
        assert "coefficient_parameter" not in metadata
        if row.linear_map_id:
            assert next(m for m in workspace.differential_maps if m.id == row.linear_map_id).status == "verified"
        assert not workspace.settings.get("coefficient_assignments")


def test_fn018_uses_the_sum_source_and_exact_constant_target_in_all_three_atlas(project):
    for workspace in images(project):
        claim = next(p for p in workspace.propositions if p.conclusion.get("fact_id") == FACT)
        row = next(d for d in workspace.differentials if d.proposition_id == claim.id)
        nodes = {node.id: node for node in workspace.classes}
        source, target, shift = nodes[row.source_id], nodes[row.target_id], shift_of(workspace)
        assert (source.grade.stem, source.grade.filtration) == (30 + shift, 2)
        assert (target.grade.stem, target.grade.filtration) == (29 + shift, 15)
        assert source.style["e2_components"] == {"I62X": 1, "I62Y": 1}
        assert target.style["e2_pattern"] == "I13"
        for node in (source, target):
            assert node.style.get("two_valuation", 0) == node.style.get("j_order", 0) == 0


def test_runtime_keeps_production_definitions_and_audits_each_declared_translate(audit):
    assert {workspace["id"] for workspace in audit} == WORKSPACES
    for workspace in audit:
        assert workspace["definitionsUnchanged"]
        assert [row["page"] for row in workspace["pages"]] == list(PAGES)
        for row in workspace["pages"]:
            assert row["blockedFromPage"] is None, (workspace["id"], row)
            assert {occurrence["name"] for occurrence in row["occurrences"]} == set(SHIFTS)
            for occurrence in row["occurrences"]:
                ds, df = SHIFTS[occurrence["name"]]
                assert occurrence["sourceGrade"] == {"stem": 30 + workspace["shift"] + ds, "filtration": 2 + df}
                assert occurrence["targetGrade"] == {"stem": 29 + workspace["shift"] + ds, "filtration": 15 + df}
                assert occurrence["source"]["trusted"] and occurrence["K"]["trusted"]


def test_d5_kills_only_k_plus_l_not_both_target_columns(audit):
    for _, row, occurrence in observations(audit, 5):
        assert occurrence["targetBlock"] == {"rank": 2, "barriers": 0}, (row, occurrence)
        assert occurrence["K"]["live"] and occurrence["L"]["live"]
        assert occurrence["KplusL"]["live"]
    for page in (6, 13):
        for _, row, occurrence in observations(audit, page):
            assert occurrence["targetBlock"] == {"rank": 1, "barriers": 0}, (row, occurrence)
            assert not occurrence["KplusL"]["live"]
            for name in ("K", "L", "KplusZetaL"):
                assert occurrence[name]["live"] and occurrence[name]["knownCycle"], (row, occurrence)
            assert len(occurrence["K"]["slots"]) == 1
            assert occurrence["K"]["slots"] == occurrence["L"]["slots"]
            assert sum(len(ports) for ports in occurrence["targetPorts"].values()) == 1


def test_source_is_the_d5_kernel_sum_not_either_original_column(audit):
    for _, row, occurrence in observations(audit, 5):
        assert occurrence["sourceBlock"] == {"rank": 2, "barriers": 0}, (row, occurrence)
        assert occurrence["source"]["live"]
        assert occurrence["sourceX"]["live"] and occurrence["sourceY"]["live"]
    for page in (6, 13):
        for _, row, occurrence in observations(audit, page):
            assert occurrence["sourceBlock"] == {"rank": 1, "barriers": 0}, (row, occurrence)
            assert occurrence["source"]["live"] and occurrence["source"]["knownCycle"]
            # y^2 D^4 has nonzero d5; x^2 has the same d5, so their
            # sum survives in the kernel. This is different from K=L
            # being equal classes in the *target* quotient above.
            assert not occurrence["sourceX"]["live"] and not occurrence["sourceY"]["live"]


def test_earlier_d3_removes_the_potential_d9_sources_j_tail_not_its_constant(audit):
    for _, row, occurrence in observations(audit, 3):
        assert occurrence["d9Source"]["live"] and occurrence["d9SourceJ"]["live"], (row, occurrence)
    for page in (4, 5, 6, 9, 10, 13, 14):
        for _, row, occurrence in observations(audit, page):
            if occurrence["name"] == "g" and page >= 10:
                # g*h1^2*k*D^4u = h1^2*k^2*D^7u is the FN016
                # D^6-block d9 target at (50,10). Zero outgoing does
                # not protect it from this independently verified incoming.
                assert not occurrence["d9Source"]["live"], (row, occurrence)
                assert not occurrence["d9Source"]["knownCycle"], (row, occurrence)
            elif page <= 13:
                assert occurrence["d9Source"]["live"] and occurrence["d9Source"]["knownCycle"], (row, occurrence)
            assert not occurrence["d9SourceJ"]["live"], (row, occurrence)
    # The finite K/L target never represented a separate formal j-series line.
    for page in PAGES:
        for _, _, occurrence in observations(audit, page):
            assert all(set(ports) <= {"0:0"} for ports in occurrence["targetPorts"].values())


def test_e13_draws_nine_real_unit_one_arrows_with_live_known_endpoints(audit):
    count = 0
    for _, row, occurrence in observations(audit, 13):
        assert row["canApply"] and row["coefficient"]["resolved"]
        assert row["coefficient"]["value"] == 1
        assert occurrence["source"]["live"] and occurrence["source"]["knownCycle"], (row, occurrence)
        assert occurrence["K"]["live"] and occurrence["K"]["knownCycle"]
        assert occurrence["maps"] > 0 and occurrence["rendered"], (row, occurrence)
        assert all(edge["status"] == "verified" and edge["canApply"] for edge in occurrence["rendered"])
        count += 1
    assert count == 9
    for page in (3, 4, 5, 6, 9, 10, 14):
        assert not any(occurrence["rendered"] for _, _, occurrence in observations(audit, page))


def test_e14_kills_only_after_the_exact_source_kernel_and_target_quotient_survive_to_e13(audit):
    for _, row, occurrence in observations(audit, 14):
        assert not occurrence["source"]["live"] and not occurrence["source"]["knownCycle"], (row, occurrence)
        assert occurrence["maps"] == 0
        assert occurrence["sourceBlock"] == {"rank": 0, "barriers": 0}, (row, occurrence)
        assert not occurrence["sourceX"]["live"] and not occurrence["sourceY"]["live"]
        assert occurrence["targetBlock"] == {"rank": 0, "barriers": 0}
        for name in ("K", "L", "KplusL", "KplusZetaL"):
            assert not occurrence[name]["live"] and not occurrence[name]["knownCycle"]
        assert not any(occurrence["targetPorts"].values())
