"""Finite F4 hypothesis audit, not an admission of the mixed-sector formulas.

All candidate changes exist only in deep-copied test data. Neither a consistent
candidate nor a smaller quotient selects a mathematical coefficient.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.migrations import migrate_project
from domain.atlas_transport import ensure_q8_atlas_transports
from domain.models import project_from_dict
from domain.seed import demo_project


MIXED = "ws_sigma_i_2sigma_j"
MIXED_ATLAS = {
    MIXED: (False, 0), "ws_q8-ro-a1-b3": (False, -16),
    "ws_q8-ro-a2-b1": (True, 0), "ws_q8-ro-a2-b3": (False, -32),
    "ws_q8-ro-a3-b1": (True, -16), "ws_q8-ro-a3-b2": (True, -32),
}
PRODUCTION_ZERO_CLAIMS = {
    "formal_prop_fn-mix-004-even-zero": 16,
    "formal_prop_fn-mix-005-q-zero": 8,
}


def candidate_project(original, c, b, *, close_zero_directions=False):
    """Assume the printed d3, PD d5, and parameterized A/B d5 formulas.

    Ah2=T is the Table 6 product checked by the source audit. Consequently
    d5(AD^2)=(c+1)kD^2T; F4 addition is bitwise XOR, not integer addition.
    """
    assert c in (1, 2, 3) and b in (None, 1, 2, 3)
    project = deepcopy(original)
    ws = next(w for w in project["workspaces"] if w["id"] == MIXED)
    ws["settings"].setdefault("coefficient_assignments", {})["mixed_d5_A"] = c
    if b is None:
        ws["settings"]["coefficient_assignments"].pop("mixed_d5_B", None)
    else:
        ws["settings"]["coefficient_assignments"]["mixed_d5_B"] = b
    claims = {p["id"]: p for p in ws["propositions"]}
    matrices = {m["id"]: m for m in ws["differential_maps"]}
    rows = {d["id"]: d for d in ws["differentials"]}
    for row in rows.values():
        if row["page"] not in (3, 5):
            continue
        row["status"] = "admitted"
        claim = claims[row["proposition_id"]]
        claim["status"] = "admitted"
        claim["conclusion"]["test_hypothesis"] = True
        if row["label"] in {"FN-MIX-002", "FN-MIX-003"}:
            assert claim["conclusion"]["coefficient_parameter"]["id"] == "mixed_d5_A"
        if row["label"] == "FN-MIX-005":
            parameter = claim["conclusion"]["coefficient_parameter"]
            assert parameter["id"] == "mixed_d5_B" and parameter["value"] is None
            if row["linear_map_id"]:
                assert parameter["target_component"] == "S22H"
                matrices[row["linear_map_id"]]["status"] = "admitted"
            else:
                assert "target_component" not in parameter

    # Use the real affine row, including its c=1 -> zero-map runtime path.
    # A private replacement would conceal broken production metadata or UI.
    production_even = rows["formal_diff_mixed_d5_a_D2_leibniz_derived"]
    parameter = claims[production_even["proposition_id"]]["conclusion"]["coefficient_parameter"]
    assert parameter["id"] == "mixed_d5_A" and parameter["affine_offset"] == 1
    if close_zero_directions:
        for claim_id in PRODUCTION_ZERO_CLAIMS:
            # Only admit the production certificates in this copied hypothesis.
            # No private classes or invented zero maps complete the block.
            claims[claim_id]["status"] = "admitted"
    return project


RUNTIME = r"""
const fs=require('node:fs'), vm=require('node:vm');
const inputs=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for(const file of ['graded-quotient.js','vector-page-algebra.js','page-algebra.js'])
  vm.runInContext(fs.readFileSync('backend/static/'+file,'utf8'),context);
const app=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(app.slice(0,app.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.inputs=inputs;
const result=vm.runInContext(`inputs.flatMap(input=>{
 state.project=input.project;
 return (input.workspaceIds || ['ws_sigma_i_2sigma_j']).map(workspaceId=>{
 const ws=state.project.workspaces.find(w=>w.id===workspaceId);
 const plan=ws.settings.atlas_transport || {}, shift=Number(plan.stem_shift || 0);
 const reflected=Boolean(plan.reflected);
 const effectiveB=input.b===null ? null : reflected ? ({1:1,2:3,3:2})[input.b] : input.b;
 const bounds={stemMin:shift,stemMax:63+shift,filtrationMin:0,filtrationMax:24};
 const definitions=()=>JSON.stringify([ws.classes,ws.cells,ws.differential_maps]);
 const before=definitions();
 const claims=new Map(ws.propositions.map(p=>[p.id,p]));
 const probe=(algebra,components,stem,filtration)=>{
   const node={style:{e2_components:components}};
   const entries=Object.entries(components);
   if(entries.length===1 && entries[0][1]===1) node.style.e2_pattern=entries[0][0];
   const grade={stem:stem+shift,filtration};
   return {components,stem:grade.stem,filtration,live:algebra.live(node,grade),
     knownCycle:algebra.knownCycle(node,grade),slots:algebra.endpointSlots(node,grade)};
 };
 const pages=[3,4,5,6].map(page=>{
  ws.page=page;
  const algebra=pageAlgebra(ws,bounds);
  const edges=periodicDifferentials(ws,bounds);
  const coefficientRows=ws.differentials.filter(d=>claims.get(d.proposition_id)?.conclusion?.coefficient_parameter?.id==='mixed_d5_B').map(d=>{
   const pair=algebra.endpoints(d);
   return {id:d.id,state:algebra.coefficientState(d),canApply:algebra.canApply(d),
     maps:algebra.maps(pair.source,pair.target,pair.source.grade,pair.target.grade).length};
  });
  const anchors=ws.differentials.filter(d=>d.page===page).map(d=>{
   const pair=algebra.endpoints(d),s=pair.source,t=pair.target;
   return {id:d.id,coefficientValue:algebra.coefficientState(d).value,
     coefficientResolved:algebra.coefficientState(d).resolved,canApply:algebra.canApply(d),
     targetComponents:t.style.e2_components || {[t.style.e2_pattern]:1},
     sourceLive:algebra.live(s,s.grade),targetLive:algebra.live(t,t.grade),
     sourceKnown:algebra.knownCycle(s,s.grade),targetKnown:algebra.knownCycle(t,t.grade),
     sourceSlots:algebra.endpointSlots(s,s.grade),targetSlots:algebra.endpointSlots(t,t.grade),
     acceptedMaps:algebra.maps(s,t,s.grade,t.grade).length};
  });
  return {page,conflicts:algebra.conflicts,blockedFromPage:algebra.blockedFromPage,coefficientRows,
    rows:[...new Set(edges.map(e=>e.diff.id))],anchors,
    blocks:[...algebra.vectorBlocks.values()].map(v=>({id:v.id,rank:v.q.dimension,barriers:v.barriers.length})),
    probes:[probe(algebra,{S62:1},6,2),probe(algebra,{S62:1},14,2),
      probe(algebra,{S22Y:1},6,6),probe(algebra,{S22H:1},6,6),
      // Unknown b: P+Q is a concrete probe, not an assignment to the unknown map.
      probe(algebra,{S22Y:1,S22H:effectiveB ?? 1},6,6),
      probe(algebra,{S22Y:1},14,6),probe(algebra,{S22H:1},14,6),
      probe(algebra,{S22Y:1,S22H:1},6,6)]};
 });
 return {c:input.c,b:input.b,closed:input.closed,workspaceId,shift,reflected,effectiveB,
   pages,definitionsUnchanged:before===definitions()};
 });
})`,context);
process.stdout.write(JSON.stringify(result));
"""


def run_audit(candidates):
    # Isolate each full project in a fresh VM/process instead of retaining
    # every candidate and its page caches in one Node heap. Keep each input's
    # complete workspace list, pages, bounds and probes, and preserve order.
    results = []
    for candidate in candidates:
        completed = subprocess.run(["node", "-e", RUNTIME], cwd=ROOT,
                                   input=json.dumps([candidate]), text=True, encoding="utf-8",
                                   capture_output=True, check=True, timeout=120)
        results.extend(json.loads(completed.stdout))
    return results


@pytest.fixture(scope="module")
def mixed_parameter_audit():
    original = asdict(migrate_project(demo_project()))
    snapshot = json.dumps(original, sort_keys=True)
    candidates = [
        {"c": c, "b": b, "closed": closed,
         "project": candidate_project(original, c, b, close_zero_directions=closed)}
        for closed in (False, True) for c in (1, 2, 3) for b in (1, 2, 3)
    ]
    assert json.dumps(original, sort_keys=True) == snapshot
    return run_audit(candidates)


@pytest.fixture(scope="module")
def mixed_atlas_parameter_audit():
    original = asdict(migrate_project(demo_project()))
    snapshot = json.dumps(original, sort_keys=True)
    inputs = []
    for b in (1, 2, 3, None):
        candidate = candidate_project(original, 1, b, close_zero_directions=True)
        transported = ensure_q8_atlas_transports(project_from_dict(candidate))
        images = [w for w in transported.workspaces if w.id == MIXED
                  or w.settings.get("atlas_transport", {}).get("source_workspace_id") == MIXED]
        assert {w.id for w in images} == set(MIXED_ATLAS)
        for workspace in images:
            reflected, shift = MIXED_ATLAS[workspace.id]
            specs = [p.conclusion["coefficient_parameter"] for p in workspace.propositions
                     if p.conclusion.get("coefficient_parameter", {}).get("id") == "mixed_d5_B"]
            assert len(specs) == 2
            assert sorted(spec.get("target_component", "whole") for spec in specs) == ["S22H", "whole"]
            assert all(spec["value"] is None and spec["domain"] == [1, 2, 3]
                       and spec["frobenius_power"] == int(reflected) for spec in specs)
            assignments = workspace.settings["coefficient_assignments"]
            assert assignments.get("mixed_d5_B") == b  # never pre-conjugate source assignment
            assert workspace.settings.get("atlas_transport", {}).get("stem_shift", 0) == shift
        inputs.append({"c": 1, "b": b, "closed": True, "workspaceIds": list(MIXED_ATLAS),
                       "project": asdict(transported)})
    assert json.dumps(original, sort_keys=True) == snapshot
    return run_audit(inputs)


def test_nine_coefficients_only_assign_production_parameters_and_never_rewrite_the_maps():
    original = asdict(migrate_project(demo_project()))
    snapshot = json.dumps(original, sort_keys=True)
    original_ws = next(w for w in original["workspaces"] if w["id"] == MIXED)
    original_claims = {p["id"]: p for p in original_ws["propositions"]}
    for claim_id, period in PRODUCTION_ZERO_CLAIMS.items():
        claim = original_claims[claim_id]
        assert claim["status"] == "verified" and claim["kind"] == "zero-differential"
        assert claim["conclusion"]["period_stem"] == period
        assert claim["conclusion"]["evidence_kind"] == "Leibniz-derived"
        assert claim["conclusion"]["derivation"]
    q_certificate = original_claims["formal_prop_fn-mix-005-q-zero"]["conclusion"]
    assert "nonzero b" in q_certificate["coefficient_constraint"]
    assert "FN-MIX-004" in q_certificate["derived_from"]
    assert "FN-MIX-005" in q_certificate["derived_from"]
    closed = candidate_project(original, 1, 1, close_zero_directions=True)
    closed_ws = next(w for w in closed["workspaces"] if w["id"] == MIXED)
    assert closed_ws["classes"] == original_ws["classes"]
    assert closed_ws["cells"] == original_ws["cells"]
    assert len(closed_ws["propositions"]) == len(original_ws["propositions"])
    closed_claims = {p["id"]: p for p in closed_ws["propositions"]}
    for claim_id in PRODUCTION_ZERO_CLAIMS:
        assert closed_claims[claim_id] == {**original_claims[claim_id], "status": "admitted"}
    for c in (1, 2, 3):
        for b in (1, 2, 3):
            project = candidate_project(original, c, b)
            ws = next(w for w in project["workspaces"] if w["id"] == MIXED)
            matrix = next(m for m in ws["differential_maps"] if m["id"] == "linear_diff_mixed_d5_sum")
            row = next(d for d in ws["differentials"] if d.get("linear_map_id") == matrix["id"])
            assert ws["settings"]["coefficient_assignments"]["mixed_d5_B"] == b
            assert ws["classes"] == original_ws["classes"]
            assert ws["cells"] == original_ws["cells"]
            assert [{k: v for k, v in m.items() if k != "status"} for m in ws["differential_maps"]] == [
                {k: v for k, v in m.items() if k != "status"} for m in original_ws["differential_maps"]]
            assert row["target_id"] == next(d for d in original_ws["differentials"] if d["id"] == row["id"])["target_id"]
            for claim in ws["propositions"]:
                assert claim["conclusion"].get("coefficient_parameter") == original_claims[claim["id"]]["conclusion"].get("coefficient_parameter")
                if claim["id"] in PRODUCTION_ZERO_CLAIMS:
                    assert claim == original_claims[claim["id"]]
            production_even = [d for d in ws["differentials"] if d["id"] == "formal_diff_mixed_d5_a_D2_leibniz_derived"]
            assert len(production_even) == 1
            assert not any(d["id"].startswith("hypothesis_even_") for d in ws["differentials"])
            assert not any(p["id"].startswith("hypothesis_even_") for p in ws["propositions"])
    assert json.dumps(original, sort_keys=True) == snapshot


def test_all_nine_pairs_preserve_the_real_d3_quotient(mixed_parameter_audit):
    for candidate in mixed_parameter_audit:
        e3, e4 = candidate["pages"][:2]
        assert len(e3["rows"]) == 5
        assert not e3["conflicts"] and not e4["conflicts"], candidate
        assert all(a["sourceLive"] and a["targetLive"] for a in e3["anchors"])
        assert candidate["definitionsUnchanged"]


def test_production_b_scales_only_the_selected_target_component(mixed_parameter_audit):
    for candidate in mixed_parameter_audit:
        anchors = candidate["pages"][2]["anchors"]
        odd = next(a for a in anchors if a["id"] == "formal_diff_fn-mix-005_1")
        even = next(a for a in anchors if a["id"] == "formal_diff_fn-mix-005_2")
        assert odd["coefficientResolved"] and even["coefficientResolved"]
        assert odd["targetComponents"] == {"S22Y": 1, "S22H": candidate["b"]}
        assert even["targetComponents"] == {"S22H": candidate["b"]}


def test_independent_zero_certificates_close_all_nine_d5_choices(mixed_parameter_audit):
    for candidate in (item for item in mixed_parameter_audit if not item["closed"]):
        e6 = candidate["pages"][-1]
        assert not e6["conflicts"] and e6["blockedFromPage"] is None, candidate
        assert not any(block["barriers"] for block in e6["blocks"])


def test_closed_nine_pair_audit_has_no_square_or_cycle_contradiction(mixed_parameter_audit):
    for candidate in (item for item in mixed_parameter_audit if item["closed"]):
        for page in candidate["pages"]:
            assert not page["conflicts"], candidate
            assert page["blockedFromPage"] is None
        e5 = candidate["pages"][2]
        assert all(a["sourceLive"] and a["targetLive"] and a["sourceKnown"] and a["targetKnown"] and a["acceptedMaps"]
                   for a in e5["anchors"] if a["coefficientValue"]), candidate
        zero_ids = {a["id"] for a in e5["anchors"] if a["coefficientValue"] == 0}
        assert zero_ids.isdisjoint(e5["rows"])
        even = next(a for a in e5["anchors"] if a["id"] == "formal_diff_mixed_d5_a_D2_leibniz_derived")
        assert even["coefficientValue"] == (candidate["c"] ^ 1)
        assert (even["id"] in e5["rows"]) == (candidate["c"] != 1)
        e6 = candidate["pages"][-1]
        probes = e6["probes"]
        assert not probes[0]["live"]
        assert probes[1]["live"] == (candidate["c"] == 1)
        assert probes[2]["live"] and probes[3]["live"]
        assert not probes[4]["live"]  # the boundary is P+bQ, not two columns
        assert not probes[5]["live"] and not probes[6]["live"]
        assert probes[7]["live"] == (candidate["b"] != 1)


def test_unknown_production_b_blocks_the_quotient_in_all_six_mixed_charts(mixed_atlas_parameter_audit):
    unknown = [item for item in mixed_atlas_parameter_audit if item["b"] is None]
    assert {item["workspaceId"] for item in unknown} == set(MIXED_ATLAS)
    for item in unknown:
        e5, e6 = item["pages"][2:]
        assert all(not row["state"]["resolved"] and not row["canApply"]
                   for row in e5["coefficientRows"])
        assert e6["blockedFromPage"] == 5
        assert any(c.get("id") == "mixed_d5_B" and c["reason"] == "coefficient parameter is unresolved"
                   for c in e6["conflicts"])
        assert all(not row["canApply"] and row["maps"] == 0 for row in e6["coefficientRows"])
        # The entire d5 quotient is uncomputed, including the otherwise assigned A row.
        assert all(probe["live"] and not probe["knownCycle"] for probe in e6["probes"])
        assert item["definitionsUnchanged"]


def test_all_six_mixed_atlas_images_use_b_or_frobenius_b_in_the_actual_quotient(mixed_atlas_parameter_audit):
    known = [item for item in mixed_atlas_parameter_audit if item["b"] is not None]
    assert len(known) == 18
    for b in (1, 2, 3):
        assert {item["workspaceId"] for item in known if item["b"] == b} == set(MIXED_ATLAS)
    for item in known:
        reflected, shift = MIXED_ATLAS[item["workspaceId"]]
        expected = {1: 1, 2: 3, 3: 2}[item["b"]] if reflected else item["b"]
        assert (item["reflected"], item["shift"], item["effectiveB"]) == (reflected, shift, expected)
        assert all(not page["conflicts"] and page["blockedFromPage"] is None for page in item["pages"])
        anchors = item["pages"][2]["anchors"]
        odd = next(a for a in anchors if a["id"].endswith("formal_diff_fn-mix-005_1"))
        even = next(a for a in anchors if a["id"].endswith("formal_diff_fn-mix-005_2"))
        assert odd["targetComponents"] == {"S22Y": 1, "S22H": expected}
        assert even["targetComponents"] == {"S22H": expected}
        probes = item["pages"][-1]["probes"]
        assert probes[2]["live"] and probes[3]["live"]
        assert not probes[4]["live"]  # only P+psi^epsilon(b)Q is the boundary line
        assert probes[7]["live"] == (expected != 1)
        assert item["definitionsUnchanged"]
