"""Exact surviving ports for the five printed DKLLW d23 rows.

Use unchanged production claims, not forced admissions or scalar assignments.
All six workspace/page computations share one Node process. Assertions concern
only these known table endpoints, not unrelated partially specified cells.
"""

from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess

import pytest

from backend.domain.migrations import migrate_project
from backend.domain.seed import demo_project


ROOT = Path(__file__).resolve().parents[1]
WORKSPACES = ("ws_integer", "ws_sigma_i")
PRINTED_SOURCES = {
    (8, 22): (-7, 1),
    (8, 23): (18, 2),
    (8, 24): (43, 3),
    (9, 21): (17, 3),
    (9, 22): (56, 2),
}
SHIFTS = {"anchor": (0, 0), "D8": (64, 0), "g": (20, 4)}


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
const bounds={stemMin:-8,stemMax:120,filtrationMin:0,filtrationMax:30};
const shifts=[['anchor',0,0],['D8',64,0],['g',20,4]];
state.project.workspaces.map(ws=>{
  const originalPage=ws.page;
  const definitions=()=>JSON.stringify([ws.classes,ws.cells,ws.differential_maps,
    ws.propositions,ws.differentials,ws.settings]);
  const before=definitions();
  const claims=new Map(ws.propositions.map(p=>[p.id,p]));
  const rows=ws.differentials.filter(d=>{
    const c=claims.get(d.proposition_id)?.conclusion;
    return d.page===23 && ((c?.table_number===8 && [22,23,24].includes(c.table_row))
      || (c?.table_number===9 && [21,22].includes(c.table_row)));
  });
  const pages=[22,23,24].map(page=>{
    ws.page=page;
    const algebra=pageAlgebra(ws,bounds);
    if(!algebra) throw Error('Missing production page algebra: '+ws.id);
    const edges=periodicDifferentials(ws,bounds)
      .filter(e=>rows.some(d=>d.id===e.diff.id));
    function endpoint(node,grade){
      const port=Number(node.style?.two_valuation||0)+':'+Number(node.style?.j_order||0);
      const ports=[...(algebra.ports(node,grade)||[])];
      return {grade,pattern:node.style?.e2_pattern,port,ports,
        exactPortPresent:ports.includes(port),
        trusted:algebra.inTrustedDomain(grade),
        live:algebra.live(node,grade),knownCycle:algebra.knownCycle(node,grade)};
    }
    const observations=rows.flatMap(d=>{
      const claim=claims.get(d.proposition_id),metadata=claim.conclusion;
      const pair=algebra.endpoints(d);
      return shifts.map(([shift,stem,filtration])=>{
        const sg={...pair.source.grade,stem:pair.source.grade.stem+stem,
          filtration:pair.source.grade.filtration+filtration};
        const tg={...pair.target.grade,stem:pair.target.grade.stem+stem,
          filtration:pair.target.grade.filtration+filtration};
        const rendered=edges.filter(e=>e.diff.id===d.id
          && e.sourceGrade.stem===sg.stem && e.sourceGrade.filtration===sg.filtration
          && e.targetGrade.stem===tg.stem && e.targetGrade.filtration===tg.filtration);
        return {id:d.id,table:metadata.table_number,row:metadata.table_row,shift,
          differentialStatus:d.status,claimStatus:claim.status,period:d.period_stem,
          source:endpoint(pair.source,sg),target:endpoint(pair.target,tg),
          canApply:algebra.canApply(d),maps:algebra.maps(pair.source,pair.target,sg,tg).length,
          rendered:rendered.map(e=>({status:e.diff.status,canApply:algebra.canApply(e.diff)}))};
      });
    });
    const jProbe=ws.id==='ws_integer'
      ? endpoint({style:{e2_pattern:'I33',two_valuation:0,j_order:0}},
        {stem:43,filtration:3}) : null;
    return {page,blockedFromPage:algebra.blockedFromPage,conflicts:algebra.conflicts,
      trustedFiltrationMax:algebra.trustedFiltrationMax,observations,jProbe};
  });
  ws.page=originalPage;
  return {id:ws.id,rows:rows.length,pages,definitionsUnchanged:before===definitions()};
});
`,context);
process.stdout.write(JSON.stringify(result));
"""


@pytest.fixture(scope="module")
def d23_audit():
    project = migrate_project(demo_project())
    # Serialize only the two independent published workspaces to bound memory;
    # retain all project-level period data and every claim within those charts.
    # replace() leaves the production object and its claim statuses untouched.
    selected = [w for w in project.workspaces if w.id in WORKSPACES]
    assert {w.id for w in selected} == set(WORKSPACES)
    completed = subprocess.run(
        ["node", "-e", RUNTIME], cwd=ROOT,
        input=json.dumps({"project": asdict(replace(project, workspaces=selected))}),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=180,
    )
    return json.loads(completed.stdout)


def observations(audit, page):
    for workspace in audit:
        result = next(p for p in workspace["pages"] if p["page"] == page)
        for item in result["observations"]:
            yield result, item


def test_exactly_five_production_rows_and_three_translates_are_audited(d23_audit):
    assert {w["id"]: w["rows"] for w in d23_audit} == {"ws_integer": 3, "ws_sigma_i": 2}
    assert all(w["definitionsUnchanged"] for w in d23_audit)
    for page in (22, 23, 24):
        seen = set()
        for _, item in observations(d23_audit, page):
            key = (item["table"], item["row"])
            stem, filtration = PRINTED_SOURCES[key]
            ds, df = SHIFTS[item["shift"]]
            source, target = item["source"]["grade"], item["target"]["grade"]
            assert (source["stem"], source["filtration"]) == (stem + ds, filtration + df)
            assert (target["stem"], target["filtration"]) == (stem + ds - 1, filtration + df + 23)
            assert item["period"] == 64
            assert item["differentialStatus"] == item["claimStatus"] == "established"
            seen.add((*key, item["shift"]))
        assert seen == {(*key, shift) for key in PRINTED_SOURCES for shift in SHIFTS}


@pytest.mark.parametrize("page", [22, 23])
def test_d23_exact_ports_are_known_live_cycles_before_the_differential(d23_audit, page):
    for result, item in observations(d23_audit, page):
        for endpoint in (item["source"], item["target"]):
            assert endpoint["trusted"] and endpoint["pattern"], (result, item)
            assert endpoint["live"] and endpoint["knownCycle"], (result, item)
            assert endpoint["exactPortPresent"], (result, item)


def test_e23_draws_all_fifteen_accepted_occurrences_with_actual_maps(d23_audit):
    for result, item in observations(d23_audit, 23):
        assert result["blockedFromPage"] is None, result
        assert item["canApply"] and item["maps"] > 0, (result, item)
        assert item["rendered"], (result, item)
        assert all(edge["canApply"] and edge["status"] == "established"
                   for edge in item["rendered"]), item
    for page in (22, 24):
        assert not any(item["rendered"] for _, item in observations(d23_audit, page))


def test_e24_removes_only_the_tested_exact_source_and_target_ports(d23_audit):
    for result, item in observations(d23_audit, 24):
        assert result["blockedFromPage"] is None, result
        for endpoint in (item["source"], item["target"]):
            assert endpoint["trusted"], (result, item)
            assert not endpoint["live"] and not endpoint["knownCycle"], (result, item)
            assert not endpoint["exactPortPresent"], (result, item)
        assert item["maps"] == 0, (result, item)
    # Do not assert all cells, unrelated j tails, or Witt layers vanish.


def test_d5_h1_cubed_constant_is_not_confused_with_its_earlier_j_boundary(d23_audit):
    integer = next(w for w in d23_audit if w["id"] == "ws_integer")
    for result in integer["pages"]:
        probe = result["jProbe"]
        assert probe["trusted"] and probe["port"] == "0:0"
        if result["page"] in (22, 23):
            assert probe["ports"] == ["0:0"]
            assert probe["live"] and probe["knownCycle"]
        else:
            assert "0:0" not in probe["ports"]
            assert not probe["live"]
