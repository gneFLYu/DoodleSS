"""Corrected Phi/Euler transport with live linked source coefficients.

No project is edited and no relative coefficient is chosen by the fixture.
The four finite mixed lines inherit lambda6/nu7/lambda2/nu3 from the SOURCE
3sigma workspace. All four blocks have independently verified C source maps
and Phi/Euler comparisons, without Jan29 or Ck permanence premises.
The user's Galois-fixed pure-sector basis fixes all four source units to 1,
without independently assigning a mixed-local unit. Mixed c/b remain nontrivial.
Generic linked-parameter tests separately cover Frobenius of nontrivial units;
these real-source tests require accepted source status and reject overrides.
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
from domain.atlas_transport import ensure_q8_atlas_transports
from domain.formal_notes_chart import DERIVED_FORMAL_ARROWS, FORMAL_ARROWS, ensure_formal_notes_chart
from domain.migrations import migrate_project
from domain.models import project_from_dict
from domain.seed import demo_project
from test_mixed_d5_parameters import MIXED_ATLAS, candidate_project
from test_mixed_d9_closures import patterns_at

MIXED = "ws_sigma_i_2sigma_j"
THREE = "ws_3sigma_i"
POWERS = {0: 6, 1: 7, 4: 2, 5: 3}
IDS = {m: f"formal_diff_mixed_phi_d9_D{m}" for m in POWERS}
SOURCE_IDS = {m: f"formal_diff_three_d9_c_D{n}_{'derived' if n % 2 == 0 else 'euler_derived'}"
              for m, n in POWERS.items()}


def parameter_id(n):
    return f"three_sigma_d9_{'D' if n % 2 == 0 else 'CD'}{n}"


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def records(project, power):
    ws = next(w for w in project.workspaces if w.id == MIXED)
    row = next(d for d in ws.differentials if d.id == IDS[power])
    claim = next(p for p in ws.propositions if p.id == row.proposition_id)
    nodes = {n.id: n for n in ws.classes}
    return ws, row, claim, nodes[row.source_id], nodes[row.target_id]


def test_exactly_four_phi_derived_rows_and_no_printed_or_zero_claim_inflation():
    assert len(FORMAL_ARROWS) == 40
    rows = [r for r in DERIVED_FORMAL_ARROWS if r.fact_id.startswith("DER-MIX-PHI-")]
    assert {r.differential_id for r in rows} == set(IDS.values())
    assert {r.fact_id for r in rows} == {f"DER-MIX-PHI-D9-D{m}" for m in POWERS}


@pytest.mark.parametrize("power", POWERS)
def test_phi_metadata_links_the_source_coefficient_and_verifies_every_block(project, power):
    ws, row, claim, source, target = records(project, power)
    metadata, n = claim.conclusion, POWERS[power]
    assert row.status == claim.status == metadata["admission_status"] == "verified"
    assert metadata["source_status"] == "independently-verified"
    assert metadata["evidence_kind"] == "corrected-Phi-Euler-transport"
    assert row.page == 9 and row.period_stem == metadata["period_stem"] == 64
    assert metadata["period_kind"] == "same-object" and metadata["period_multiplier"] == "D^8"
    assert metadata["period_is_invertible"] and "forward g=kD^3" in row.period_notes
    assert (source.grade.stem, source.grade.filtration) == (8 * power, 2)
    assert (target.grade.stem, target.grade.filtration) == (8 * power - 1, 11)
    assert source.style["e2_pattern"] == "S02" and target.style["e2_pattern"] == "S73"
    assert all(node.style["j_order"] == node.style["two_valuation"] == 0 for node in (source, target))
    parameter = metadata["coefficient_parameter"]
    assert parameter == {
        "id": parameter_id(n), "symbol": rf"\lambda_{{{n}}}" if n % 2 == 0 else rf"\nu_{{{n}}}",
        "domain": [1, 2, 3], "value": None, "frobenius_power": 0,
        "source_parameter": {"workspace_id": THREE, "parameter_id": parameter_id(n),
                             "differential_id": SOURCE_IDS[power], "page": 9},
    }
    assert parameter["symbol"] in claim.statement
    assert parameter["id"] not in ws.settings.get("coefficient_assignments", {})
    assert "coefficient_condition" not in metadata  # These finite targets do not depend on c/b.
    transport = metadata["transport_certificate"]
    assert transport["source_differential_id"] == SOURCE_IDS[power]
    assert transport["phi_stem_shift"] == -16 and transport["phi_filtration_shift"] == 0
    assert transport["final_D_exponent"] == (-8 if power < 2 else 0)
    assert transport["action"] == "omega^2" and transport["applied_inverse"]
    assert "positive-filtration" in transport["comparison"]
    assert "common Thom unit cancels" in metadata["derivation"]
    assert "D^4 is not used as a 9-cycle" in metadata["derivation"]
    assert "not an assertion that g is invertible" in metadata["derivation"]
    assert any("(43,31)" in correction.get("corrected", "") for correction in metadata["historical_corrections"])
    source_fact = "DER-3I-D9-C" if n % 2 == 0 else "DER-3I-EULER-D9-C"
    assert source_fact in metadata["derived_from"]
    assert not {"FN-3I-010", "FN-3I-010-pc"} & set(metadata["derived_from"])
    assert metadata["source_blockers"] == metadata["withdrawn_dependencies"] == []
    assert transport["status"] == "verified"
    certificate = metadata["verification_certificate"]
    assert certificate["status"] == "verified"
    assert certificate["method"] == "Permanent Phi transport and finite Euler target survival"
    assert source_fact in certificate["premises"]
    source_ws = next(item for item in project.workspaces if item.id == THREE)
    source_row = next(item for item in source_ws.differentials if item.id == SOURCE_IDS[power])
    source_claim = next(item for item in source_ws.propositions if item.id == source_row.proposition_id)
    assert source_row.status == source_claim.status == "verified"
    assert source_claim.conclusion["source_status"] == "independently-verified"
    assert source_row.label == source_fact
    assert not {"FN-3I-010", "FN-3I-010-pc"} & set(source_claim.conclusion["derived_from"])
    source_parameter = source_claim.conclusion["coefficient_parameter"]
    assert source_parameter["id"] == parameter_id(n)
    assert source_parameter["value"] == 1 and source_parameter["domain"] == [1]


@pytest.mark.parametrize("power", POWERS)
def test_survival_certificate_uses_actual_e2_columns_not_only_finite_motifs(project, power):
    _, _, claim, _, _ = records(project, power)
    metadata = claim.conclusion
    for key in ("source_survival", "target_survival"):
        assert metadata[key]["scope"] == "source-workspace"
        assert metadata[key]["source_workspace_id"] == MIXED
        assert metadata[key]["status"] == "verified"
    incoming = {c["page"]: c for c in metadata["target_survival"]["incoming"]}
    assert incoming[3]["e2_pattern"] == "S00" and "zero d3" in incoming[3]["reason"]
    assert "primitive" in incoming[3]["reason"] and "d3^2=0" in incoming[3]["reason"]
    assert incoming[7]["e2_pattern"] == "S40" and "entire slot is zero on E4" in incoming[7]["reason"]
    assert "S73V" in metadata["target_survival"]["other_e2_direction"]
    for g in (0, 1, 2, 5):
        s, f = 8 * power + 20 * g, 2 + 4 * g
        assert patterns_at(s, f) == {"S02"}
        assert not patterns_at(s - 1, f + 3)
        assert patterns_at(s - 1, f + 5) == {"S33"}
        assert patterns_at(s - 1, f + 9) == {"S73", "S73V"}
        assert patterns_at(s, f + 6) == {"S00"}  # incoming d3, a zero map, NOT an empty cell
        assert not patterns_at(s, f + 4)
        assert patterns_at(s, f + 2) == {"S40"}
    assert not patterns_at(8 * power + 1, 0)


def test_repeat_materialization_preserves_linked_values_and_all_four_verified_admissions(project):
    copied = deepcopy(project)
    ensure_formal_notes_chart(copied)
    ensure_formal_notes_chart(copied)
    for power in POWERS:
        ws, row, claim, _, _ = records(copied, power)
        assert row.status == claim.status == "verified"
        assert claim.conclusion == records(project, power)[2].conclusion
        assert not any(e.differential_claim_id == row.id for e in ws.differential_events)


def hypothesis(original, c=1, units=None, source_admitted=True, local_poison=False):
    candidate = candidate_project(original, c, 2, close_zero_directions=True)
    mixed = next(w for w in candidate["workspaces"] if w["id"] == MIXED)
    source = next(w for w in candidate["workspaces"] if w["id"] == THREE)
    for ws in (mixed, source):
        claims = {p["id"]: p for p in ws["propositions"]}
        for row in ws["differentials"]:
            if ws is source and not source_admitted and row["id"] in SOURCE_IDS.values():
                # All four source rows are now verified in production.
                # Explicitly revoke them only in this negative-test copy;
                # leaving their statuses untouched would not test the gate.
                row["status"] = claims[row["proposition_id"]]["status"] = "review"
            selected = row["id"] in IDS.values() if ws is mixed else (
                source_admitted and (row["page"] in (3, 5) or row["id"] in SOURCE_IDS.values()))
            if selected:
                row["status"] = claims[row["proposition_id"]]["status"] = "admitted"
                claims[row["proposition_id"]]["conclusion"]["test_hypothesis"] = True
        if ws is source:
            for claim in ws["propositions"]:
                if source_admitted and claim["kind"] == "zero-differential" and claim["conclusion"].get("page", 100) <= 5:
                    claim["status"] = "admitted"
        accepted = {d["linear_map_id"] for d in ws["differentials"] if d["status"] == "admitted"}
        reviewed_sources = {d["linear_map_id"] for d in ws["differentials"]
                            if ws is source and not source_admitted and d["id"] in SOURCE_IDS.values()}
        for matrix in ws["differential_maps"]:
            if matrix["id"] in reviewed_sources:
                matrix["status"] = "review"
            elif matrix["id"] in accepted:
                matrix["status"] = "admitted"
    if units is not None:
        source["settings"].setdefault("coefficient_assignments", {}).update(
            {parameter_id(POWERS[m]): value for m, value in zip(POWERS, units)})
    if local_poison:
        mixed["settings"]["coefficient_assignments"].update(
            {parameter_id(n): 1 for n in POWERS.values()})
    return candidate


RUNTIME = r"""
const fs=require('node:fs'),vm=require('node:vm');
const inputs=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for(const file of ['graded-quotient.js','vector-page-algebra.js','page-algebra.js'])
 vm.runInContext(fs.readFileSync('backend/static/'+file,'utf8'),context);
const app=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(app.slice(0,app.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.inputs=inputs;
const result=vm.runInContext(`inputs.flatMap(input=>{
 state.project=input.project;
 return input.workspaceIds.map(workspaceId=>{
  const ws=state.project.workspaces.find(w=>w.id===workspaceId);
  const plan=ws.settings.atlas_transport || {},shift=Number(plan.stem_shift || 0);
  const bounds={stemMin:shift,stemMax:63+shift,filtrationMin:0,filtrationMax:16};
  const definitions=()=>JSON.stringify(state.project.workspaces.map(w=>[w.classes,w.differentials,w.propositions,w.settings.coefficient_assignments]));
  const before=definitions();
  const rows=ws.differentials.filter(d=>d.label.startsWith('DER-MIX-PHI-D9-'));
  const pages=[3,4,5,6,7,9,10].map(page=>{
   ws.page=page;
   const algebra=pageAlgebra(ws,bounds),edges=periodicDifferentials(ws,bounds),points=periodicClassInstances(ws,bounds);
   return {page,conflicts:algebra.conflicts,blockedFromPage:algebra.blockedFromPage,
    rows:rows.map(row=>{
     const pair=algebra.endpoints(row),s=pair.source,t=pair.target;
     const own=edges.filter(e=>e.diff.id===row.id);
     return {id:row.id,fact:row.label,coefficient:algebra.coefficientState(row),canApply:algebra.canApply(row),
      sourceGrade:s.grade,targetGrade:t.grade,sourceLive:algebra.live(s,s.grade),targetLive:algebra.live(t,t.grade),
      sourceKnown:algebra.knownCycle(s,s.grade),targetKnown:algebra.knownCycle(t,t.grade),
      sourceSlots:algebra.endpointSlots(s,s.grade),targetSlots:algebra.endpointSlots(t,t.grade),
      targetBoLive:algebra.live({style:{e2_pattern:'S73V',j_order:0}},t.grade),
      incomingD7Live:algebra.live({style:{e2_pattern:'S40',j_order:0}},{stem:s.grade.stem,filtration:4}),
      rendered:own.length,certified:own.filter(e=>e.diff.status==='admitted').length,
      sourceDisplayed:points.some(p=>p.grade.stem===s.grade.stem && p.grade.filtration===2 && p.item.style.e2_pattern==='S02')};
    })};
  });
  return {name:input.name,workspaceId,shift,reflected:Boolean(plan.reflected),pages,unchanged:before===definitions()};
 });
})`,context);
process.stdout.write(JSON.stringify(result));
"""


@pytest.fixture(scope="module")
def runtime(project):
    original = asdict(project)
    snapshot = json.dumps(original, sort_keys=True)
    inputs = []
    for name, c, units, admitted, poison in (
        ("linked", 1, (1, 1, 1, 1), True, False), ("local-poison", 1, None, True, True),
        ("c-zeta", 2, None, True, False), ("c-zeta2", 3, None, True, False),
        ("unassigned-fixed", 1, None, True, False), ("unadmitted", 1, None, False, False),
        ("source-conflict", 1, (2, 3, 2, 3), True, False),
    ):
        inputs.append({"name": name, "workspaceIds": [MIXED],
                       "project": hypothesis(original, c, units, admitted, poison)})
    transported = ensure_q8_atlas_transports(project_from_dict(hypothesis(original)))
    for ws in transported.workspaces:
        if ws.id not in MIXED_ATLAS:
            continue
        for claim in ws.propositions:
            if not claim.conclusion.get("fact_id", "").startswith("DER-MIX-PHI-D9-"):
                continue
            spec = claim.conclusion["coefficient_parameter"]
            assert spec["source_parameter"]["workspace_id"] == THREE
            assert spec["frobenius_power"] == int(MIXED_ATLAS[ws.id][0])
            assert spec["id"] not in ws.settings.get("coefficient_assignments", {})
    inputs.append({"name": "atlas", "workspaceIds": list(MIXED_ATLAS), "project": asdict(transported)})
    assert json.dumps(original, sort_keys=True) == snapshot
    completed = subprocess.run(["node", "-e", RUNTIME], cwd=ROOT, input=json.dumps(inputs),
                               text=True, encoding="utf-8", capture_output=True, check=True, timeout=120)
    return {(row["name"], row["workspaceId"]): row for row in json.loads(completed.stdout)}


def assert_nonzero(result):
    assert result["unchanged"]
    pages = {row["page"]: row for row in result["pages"]}
    for page in pages.values():
        assert page["blockedFromPage"] is None
        assert not page["conflicts"]
        for row in page["rows"]:
            if page["page"] < 10:
                assert row["sourceLive"] and row["targetLive"]
            if page["page"] >= 4:
                assert not row["targetBoLive"] and not row["incomingD7Live"]
    assert len(pages[9]["rows"]) == 4
    for before, after in zip(pages[9]["rows"], pages[10]["rows"]):
        m = int(before["fact"].rsplit("D", 1)[1])
        assert before["coefficient"]["resolved"] and before["coefficient"]["value"] == 1
        assert before["sourceGrade"]["stem"] == 8 * m + result["shift"]
        assert before["targetGrade"]["stem"] == 8 * m - 1 + result["shift"]
        assert before["canApply"] and before["sourceKnown"] and before["targetKnown"]
        assert before["rendered"] == before["certified"] > 0 and before["sourceDisplayed"]
        assert not after["sourceLive"] and not after["targetLive"]
        assert not after["sourceDisplayed"] and after["rendered"] == 0


@pytest.mark.parametrize("name", ("linked", "unassigned-fixed", "c-zeta", "c-zeta2"))
def test_real_runtime_uses_source_units_and_nonzero_targets_independently_of_c(runtime, name):
    assert_nonzero(runtime[(name, MIXED)])


@pytest.mark.parametrize("name", ("source-conflict", "unadmitted", "local-poison"))
def test_conflicting_source_or_missing_admission_cannot_create_deaths(runtime, name):
    result = runtime[(name, MIXED)]
    pages = {p["page"]: p for p in result["pages"]}
    assert result["unchanged"] and pages[9]["blockedFromPage"] is None
    assert pages[10]["blockedFromPage"] == 9
    for page in (pages[9], pages[10]):
        for row in page["rows"]:
            assert not row["coefficient"]["resolved"]
            assert not row["canApply"] and row["certified"] == 0
            assert row["sourceLive"] and row["targetLive"]
            if name == "local-poison":
                assert "local assignment" in row["coefficient"]["reason"]
            elif name == "source-conflict":
                assert "conflicting linked coefficient source assignments" in row["coefficient"]["reason"]
            else:
                assert "source differential is not admitted" in row["coefficient"]["reason"]


@pytest.mark.parametrize("workspace_id", tuple(MIXED_ATLAS))
def test_all_six_atlas_images_keep_source_link_and_square_exactly_once(runtime, workspace_id):
    assert_nonzero(runtime[("atlas", workspace_id)])
