"""Metadata for conditional mixed Euler images, not a mathematical admission.

FN-2I-016 supplies an E9 equation after omega and permanent Euler multiplication.
It is a NONZERO mixed differential only when c=1: otherwise its target is already
a d5 boundary. These tests inspect real production rows and the independently
enumerated E2 cells, without rewriting production arrays or choosing gamma=1.
The runtime cases explicitly adopt hypotheses only in copied projects; they
verify conditional rendering/quotients, not the mathematical truth of a unit.
The Q equation uses the same gamma divided by b. Positive-j zeros have a
separate negative-source Tate certificate. Thus each studied rank-three cell
has a fully specified map; this is not a claim of global mixed convergence.
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
from domain.e2_import import verified_e2_classes
from domain.atlas_transport import ensure_q8_atlas_transports
from domain.formal_notes_chart import DERIVED_FORMAL_ARROWS, FORMAL_ARROWS, ensure_formal_notes_chart
from domain.migrations import migrate_project
from domain.models import project_from_dict
from domain.published_differentials import _normalise_label
from domain.seed import demo_project
from test_mixed_d5_parameters import MIXED_ATLAS, candidate_project


WORKSPACE = "ws_sigma_i_2sigma_j"
IDS = {m: f"formal_diff_mixed_d9_p_D{m}_euler_derived" for m in (2, 6)}
Q_IDS = {m: f"formal_diff_mixed_d9_q_D{m}_derived" for m in (2, 6)}
ZERO_IDS = {m: f"formal_prop_der-mix-d9-jq-d{m}-zero" for m in (2, 6)}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def records(project, power, *, q=False):
    ws = next(w for w in project.workspaces if w.id == WORKSPACE)
    row = next(d for d in ws.differentials if d.id == (Q_IDS if q else IDS)[power])
    claim = next(p for p in ws.propositions if p.id == row.proposition_id)
    nodes = {n.id: n for n in ws.classes}
    return ws, row, claim, nodes[row.source_id], nodes[row.target_id]


def patterns_at(stem, filtration):
    """Check E2 support from the catalogue, not from a candidate's certificate."""
    if filtration < 0:
        return set()
    patterns = set()
    for cell in verified_e2_classes("sigma_i"):
        shift = filtration - cell.filtration
        if shift < 0 or shift % 4:
            continue
        if (stem - cell.stem - 20 * (shift // 4)) % 64 == 0:
            patterns.add(cell.pattern_key)
    return patterns


def test_candidates_are_four_new_derived_rows_not_extra_printed_equations():
    assert len(FORMAL_ARROWS) == 40
    assert len([a for a in FORMAL_ARROWS if a.workspace_id == WORKSPACE]) == 8
    assert not any(a.fact_id.startswith("DER-MIX-D9") for a in FORMAL_ARROWS)
    rows = [a for a in DERIVED_FORMAL_ARROWS if a.fact_id.startswith("DER-MIX-D9")]
    assert {a.differential_id for a in rows} == set(IDS.values()) | set(Q_IDS.values())
    assert {a.fact_id for a in rows} == {f"DER-MIX-D9-{column}-D{m}" for column in ("P", "Q") for m in (2, 6)}


@pytest.mark.parametrize("power", (2, 6))
def test_real_rows_have_exact_endpoints_review_status_and_permanent_64_repeat(project, power):
    ws, row, claim, source, target = records(project, power)
    metadata = claim.conclusion
    assert row.status == claim.status == "review"
    assert metadata["admission_status"] == "review"
    assert metadata["source_status"] == "derived-review"
    assert metadata["evidence_kind"] == "conditional-Euler-image-derived"
    assert row.page == 9 and row.period_stem == metadata["period_stem"] == 64
    assert metadata["period_kind"] == "same-object"
    assert metadata["period_multiplier"] == "D^8" and metadata["period_is_invertible"]
    assert metadata["paired_pattern_stem"] == 32
    assert "forward g=kD^3" in row.period_notes
    assert "D^4 is not used as a 9-cycle" in metadata["derivation"]
    assert (source.grade.stem, source.grade.filtration) == (8 * power + 2, 2)
    assert (target.grade.stem, target.grade.filtration) == (8 * power + 1, 11)
    assert _normalise_label(source.label) == _normalise_label(
        rf"\{{yh_2+xh_1v_1\}}D^{power}u_{{\sigma_i+2\sigma_j}}")
    assert _normalise_label(target.label) == _normalise_label(
        rf"\{{x+y\}}h_1^2k^2D^{power + 1}u_{{\sigma_i+2\sigma_j}}")
    assert source.style["e2_pattern"] == "S22Y"
    assert target.style["e2_pattern"] == "S13"
    for node in (source, target):
        assert node.style["j_order"] == node.style["two_valuation"] == 0
    assert not row.linear_map_id  # P is one column, never the whole (P,Q) cell.
    assert "FN-2I-016" in metadata["derived_from"]
    transport = metadata["premise_transport_certificate"]
    assert transport["status"] == "verified-equation" and transport["premise"] == "FN-2I-016"
    assert (transport["action"], transport["multiplier"]) == ("omega", "a_sigma_i")
    assert "520-526" in claim.source_ref
    assert "does not admit" in transport["admission"]


@pytest.mark.parametrize("power", (2, 6))
def test_verified_gamma_does_not_assign_the_independent_c_condition(project, power):
    ws, row, claim, _, _ = records(project, power)
    metadata = claim.conclusion
    parameter = metadata["coefficient_parameter"]
    assert {key: value for key, value in parameter.items() if key != "fixed_reason"} == {
        "id": f"mixed_d9_PD{power}", "symbol": r"\zeta^2",
        "domain": [3], "value": 3, "frobenius_power": 0}
    assert "Verified FN-2I-016" in parameter["fixed_reason"]
    assert parameter["symbol"] in claim.statement
    assert parameter["id"] not in ws.settings.get("coefficient_assignments", {})
    condition = metadata["coefficient_condition"]
    assert condition["parameter_id"] == "mixed_d5_A" and condition["equals"] == 1
    assert condition["otherwise"] == "zero-euler-image"
    assert "520-526" in condition["source_ref"]
    assert "source-field assignment" in condition["derivation"]
    assert "without Frobenius-conjugating" in condition["derivation"]
    assert "does not remove" in condition["derivation"]
    assert f"gamma_{power}=zeta^2*lambda_{power}" in metadata["coefficient_constraint"]
    assert "independently proved m=2,6" in metadata["coefficient_constraint"]
    assert "fixes gamma, not c or b" in metadata["coefficient_constraint"]
    assert "no D4 cycle" in metadata["coefficient_constraint"]
    assert metadata["premise_transport_certificate"]["mixed_coefficient"] == 3
    assert metadata["conditional_statement"].startswith(r"c=1\Longrightarrow")
    assert any("Unresolved c" in blocker for blocker in metadata["source_blockers"])


@pytest.mark.parametrize("power", (2, 6))
def test_finite_target_certificate_matches_independent_e2_enumeration(project, power):
    _, _, claim, source, target = records(project, power)
    metadata = claim.conclusion
    certificate = metadata["target_survival"]
    assert certificate["bidegree"] == [target.grade.stem, 11]
    assert certificate["nonzero_condition"] == "c=1"
    assert "Euler image" in certificate["cycle_premise"]
    incoming = {row["page"]: row for row in certificate["incoming"]}
    assert set(incoming) == {3, 5, 7}
    for g_power in (0, 1, 2, 5):
        s, f = target.grade.stem + 20 * g_power, 11 + 4 * g_power
        assert patterns_at(s, f) == {"S13"}
        assert patterns_at(s + 1, f - 3) == set()
        assert patterns_at(s + 1, f - 5) == {"S62", "S62V"}
        assert patterns_at(s + 1, f - 7) == set()
        assert all(not patterns_at(s + 1, f - r) for r in (2, 4, 6, 8))
    for page, item in incoming.items():
        assert item["source_bidegree"] == [target.grade.stem + 1, 11 - page]
    directions = {item["e2_pattern"]: item for item in incoming[5]["directions"]}
    assert directions["S62"]["representative"] == f"A k D^{power + 1}"
    assert directions["S62"]["target_coefficient"] == "c+1"
    assert directions["S62V"]["representative"] == f"U h1^2 k D^{power}"
    assert directions["S62V"]["exclusion"] == "d3-source"
    assert directions["S62V"]["fact_id"] == "FN-MIX-001"
    assert patterns_at(source.grade.stem, 2) == {"S22Y", "S22H"}
    assert not patterns_at(source.grade.stem + 1, 0)  # incoming d2
    assert all(not patterns_at(source.grade.stem + 1, 2 - r) for r in range(3, 9))
    assert "Euler image" in metadata["source_survival"]["cycle_premise"]


def test_resynchronization_keeps_two_conditional_candidates_and_their_verified_units(project):
    candidate = deepcopy(project)
    for _ in range(2):
        ensure_formal_notes_chart(candidate)
    ws = next(w for w in candidate.workspaces if w.id == WORKSPACE)
    rows = [d for d in ws.differentials if d.id in IDS.values()]
    assert len(rows) == 2
    for power in (2, 6):
        _, row, claim, _, _ = records(candidate, power)
        assert row.status == claim.status == "review"
        assert claim.conclusion == records(project, power)[2].conclusion
        assert not any(e.differential_claim_id == row.id for e in ws.differential_events)


@pytest.mark.parametrize("power", (2, 6))
def test_q_coefficient_is_the_shared_ratio_with_an_independent_positive_j_zero(project, power):
    ws, row, claim, source, target = records(project, power, q=True)
    p_claim = records(project, power)[2]
    metadata = claim.conclusion
    assert row.status == claim.status == "review"
    assert row.page == 9 and row.period_stem == 64
    assert source.style["e2_pattern"] == "S22H" and source.style["j_order"] == 0
    assert target.id == records(project, power)[4].id
    assert metadata["coefficient_condition"] == p_claim.conclusion["coefficient_condition"]
    assert metadata["coefficient_parameter"] == {
        **p_claim.conclusion["coefficient_parameter"], "inverse_parameter_id": "mixed_d5_B",
        "expression": r"\zeta^2/b",
    }
    assert metadata["coefficient_parameter"]["expression"] in claim.statement
    assert "g(P+bQ)D^m=d5(BD^(m+3))" in metadata["derivation"]
    for key in ("source_survival", "target_survival", "g_injection_certificate"):
        assert metadata[key]["scope"] == "source-workspace"
        assert metadata[key]["source_workspace_id"] == WORKSPACE
    g_certificate = metadata["g_injection_certificate"]
    assert g_certificate["g_target_bidegree"] == [8 * power + 21, 15]
    for entry in g_certificate["incoming"]:
        s, f = entry["source_bidegree"]
        assert patterns_at(s, f) == ({"S62", "S62V"} if entry["page"] == 5 else set())
    zero = next(p for p in ws.propositions if p.id == ZERO_IDS[power])
    assert zero.status == "review" and zero.kind == "zero-differential"
    evidence = zero.conclusion
    assert evidence["zero"] and evidence["page"] == 9 and evidence["period_stem"] == 64
    assert evidence["j_order"] == 1 and evidence["e2_components"] == {"S22H": 1}
    assert evidence["source_component"] == "positive-j"
    assert "coefficient_parameter" not in evidence and "coefficient_condition" not in evidence
    j_source = next(n for n in ws.classes if n.id == evidence["source_id"])
    assert j_source.id != source.id
    assert j_source.style["e2_pattern"] == "S22H" and j_source.style["j_order"] == 1
    assert (j_source.grade.stem, j_source.grade.filtration) == (8 * power + 2, 2)
    certificate = evidence["comparison_certificate"]
    assert certificate["source_bidegree"] == [8 * power + 3, -1]
    assert certificate["target_bidegree"] == [8 * power + 2, 2]
    assert certificate["scope"] == "source-workspace" and certificate["source_workspace_id"] == WORKSPACE
    assert certificate["n_min"] == 1 and "never delete" in certificate["interpretation"]
    assert "Neither argument sets d9(QD^m)=0" in evidence["derivation"]


CONDITIONAL_RUNTIME = r"""
const fs=require('node:fs'), vm=require('node:vm');
const inputs=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for(const file of ['graded-quotient.js','vector-page-algebra.js','page-algebra.js'])
  vm.runInContext(fs.readFileSync('backend/static/'+file,'utf8'),context);
const app=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(app.slice(0,app.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.inputs=inputs;
const output=vm.runInContext(`inputs.flatMap(input=>{
 state.project=input.project;
 return input.workspaceIds.map(workspaceId=>{
  const ws=state.project.workspaces.find(w=>w.id===workspaceId);
  const plan=ws.settings.atlas_transport || {}, shift=Number(plan.stem_shift || 0);
  const bounds={stemMin:shift,stemMax:63+shift,filtrationMin:0,filtrationMax:15};
  const definitions=()=>JSON.stringify([ws.classes,ws.cells,ws.differential_maps,ws.propositions,ws.differentials]);
  const before=definitions(), claims=new Map(ws.propositions.map(p=>[p.id,p]));
  const rows=ws.differentials.filter(d=>/^DER-MIX-D9-[PQ]-D/.test(d.label));
  const pages=[5,6,9,10].map(page=>{
   ws.page=page;
   const algebra=pageAlgebra(ws,bounds), edges=periodicDifferentials(ws,bounds);
   const points=periodicClassInstances(ws,bounds);
   return {page,conflicts:algebra.conflicts,blockedFromPage:algebra.blockedFromPage,
    gTailLive:algebra.live({style:{e2_pattern:'S22H',j_order:1}},{stem:38+shift,filtration:6}),
    rows:rows.map(row=>{
     const pair=algebra.endpoints(row), source=pair.source,target=pair.target;
     const claim=claims.get(row.proposition_id), fact=claim.conclusion.fact_id;
     const ownEdges=edges.filter(edge=>edge.diff.id===row.id);
     const qDirections=[0,1].map(j_order=>{
      const q={style:{e2_pattern:'S22H',j_order}};
      return {j_order,live:algebra.live(q,source.grade),known:algebra.knownCycle(q,source.grade)};
     });
     const rawB=ws.settings.coefficient_assignments.mixed_d5_B;
     const b=plan.reflected ? ({1:1,2:3,3:2})[rawB] : rawB;
     const sum={style:{e2_components:{S22Y:1,S22H:b}}};
     return {id:row.id,fact,condition:algebra.conditionState(row),coefficient:algebra.coefficientState(row),
      zero:algebra.isZero(row),canApply:algebra.canApply(row),
      sourceGrade:source.grade,targetGrade:target.grade,
      sourceLive:algebra.live(source,source.grade),sourceKnown:algebra.knownCycle(source,source.grade),
      targetLive:algebra.live(target,target.grade),
      sourceSlots:algebra.endpointSlots(source,source.grade),qDirections,
      kernel:{live:algebra.live(sum,source.grade),known:algebra.knownCycle(sum,source.grade)},
      rendered:ownEdges.length,certified:ownEdges.filter(edge=>edge.diff.status==='admitted').length,
      sourceDisplayed:points.some(p=>p.grade.stem===source.grade.stem && p.grade.filtration===2
        && p.item.style.e2_pattern===source.style.e2_pattern
        && (p.modulePorts || []).includes('0:0'))};
    })};
  });
  return {name:input.name,workspaceId,shift,reflected:Boolean(plan.reflected),pages,
    unchanged:before===definitions()};
 });
})`,context);
process.stdout.write(JSON.stringify(output));
"""


def conditional_candidate(original, c, gammas):
    # Reuse the real d3/d5 and zero-direction hypothesis fixture. All changed
    # fields here are statuses and user parameter assignments, never formula,
    # endpoint, basis, condition or map replacement data.
    copied = candidate_project(original, c if c is not None else 1, 2, close_zero_directions=True)
    ws = next(w for w in copied["workspaces"] if w["id"] == WORKSPACE)
    assignments = ws["settings"]["coefficient_assignments"]
    if c is None:
        assignments.pop("mixed_d5_A")
    claims = {p["id"]: p for p in ws["propositions"]}
    for row in ws["differentials"]:
        if row["id"] in set(IDS.values()) | set(Q_IDS.values()):
            row["status"] = "admitted"
            claims[row["proposition_id"]]["status"] = "admitted"
            claims[row["proposition_id"]]["conclusion"]["test_hypothesis"] = True
    for claim_id in ZERO_IDS.values():
        claims[claim_id]["status"] = "admitted"
    if gammas is not None:
        assignments.update({f"mixed_d9_PD{m}": value for m, value in zip((2, 6), gammas)})
    else:
        assert all(f"mixed_d9_PD{m}" not in assignments for m in (2, 6))
    return copied


@pytest.fixture(scope="module")
def conditional_runtime(project):
    original = asdict(project)
    snapshot = json.dumps(original, sort_keys=True)
    inputs = []
    for name, c, gammas in (("nonzero", 1, None), ("zero-zeta", 2, None),
                            ("zero-zeta2", 3, None), ("unknown-c", None, None),
                            ("conflicting-gamma", 1, (2, 3))):
        inputs.append({"name": name, "workspaceIds": [WORKSPACE],
                       "project": conditional_candidate(original, c, gammas)})
    for name, c, gammas in (("atlas-nonzero", 1, None), ("atlas-zero", 2, None)):
        copied = conditional_candidate(original, c, gammas)
        source_claims = {p["conclusion"]["fact_id"]: p for workspace in copied["workspaces"]
                         if workspace["id"] == WORKSPACE for p in workspace["propositions"]
                         if p["conclusion"].get("fact_id", "").startswith(("DER-MIX-D9-P-D", "DER-MIX-D9-Q-D"))}
        transported = ensure_q8_atlas_transports(project_from_dict(copied))
        images = [w for w in transported.workspaces if w.id == WORKSPACE
                  or w.settings.get("atlas_transport", {}).get("source_workspace_id") == WORKSPACE]
        assert {w.id for w in images} == set(MIXED_ATLAS)
        for ws in images:
            reflected, shift = MIXED_ATLAS[ws.id]
            claims = [p for p in ws.propositions if p.conclusion.get("fact_id", "").startswith(("DER-MIX-D9-P-D", "DER-MIX-D9-Q-D"))]
            assert len(claims) == 4
            assert ws.settings["coefficient_assignments"]["mixed_d5_A"] == c
            assert ws.settings.get("atlas_transport", {}).get("stem_shift", 0) == shift
            for claim in claims:
                metadata = claim.conclusion
                assert metadata["coefficient_condition"] == source_claims[metadata["fact_id"]]["conclusion"]["coefficient_condition"]
                spec = metadata["coefficient_parameter"]
                assert spec["frobenius_power"] == int(reflected)
                assert spec["value"] == 3 and spec["domain"] == [3]
                if "-Q-" in metadata["fact_id"]:
                    assert spec["inverse_parameter_id"] == "mixed_d5_B"
                assert ws.settings["coefficient_assignments"]["mixed_d5_B"] == 2
                if gammas is not None:
                    power = int(metadata["fact_id"].rsplit("D", 1)[1])
                    assert ws.settings["coefficient_assignments"][spec["id"]] == {2: 2, 6: 3}[power]
                else:
                    assert spec["id"] not in ws.settings["coefficient_assignments"]
        inputs.append({"name": name, "workspaceIds": list(MIXED_ATLAS), "project": asdict(transported)})
    assert json.dumps(original, sort_keys=True) == snapshot
    result = subprocess.run(["node", "-e", CONDITIONAL_RUNTIME], cwd=ROOT,
                            input=json.dumps(inputs), text=True, encoding="utf-8",
                            capture_output=True, check=True, timeout=120)
    return {(r["name"], r["workspaceId"]): r for r in json.loads(result.stdout)}


def assert_full_known_cell_quotient(page, *, zero=False):
    assert page["blockedFromPage"] is None
    assert not page["conflicts"]
    if page["page"] >= 10:
        for row in page["rows"]:
            assert row["qDirections"] == [
                {"j_order": 0, "live": zero, "known": zero},
                {"j_order": 1, "live": True, "known": True},
            ]
            assert row["kernel"] == {"live": True, "known": True}


def assert_nonzero_branch(result, reflected=False, shift=0):
    assert result["unchanged"]
    pages = {p["page"]: p for p in result["pages"]}
    for page in pages.values():
        assert_full_known_cell_quotient(page)
    assert len(pages[9]["rows"]) == 4
    for before, after in zip(pages[9]["rows"], pages[10]["rows"]):
        power = int(before["fact"].rsplit("D", 1)[1])
        value = 2 if "-Q-" in before["fact"] else 3
        if reflected:
            value = {1: 1, 2: 3, 3: 2}[value]
        assert before["coefficient"]["resolved"] and before["coefficient"]["value"] == value
        assert before["condition"]["value"] == 1 and before["condition"]["nonzero"]
        assert before["sourceGrade"]["stem"] == 8 * power + 2 + shift
        assert before["targetGrade"]["stem"] == 8 * power + 1 + shift
        assert before["sourceLive"] and before["targetLive"] and before["sourceKnown"]
        assert before["sourceDisplayed"] and before["certified"] > 0
        assert before["rendered"] == before["certified"]
        assert not before["zero"] and before["canApply"]
        assert not after["sourceLive"] and not after["targetLive"]
        assert not after["sourceDisplayed"] and after["rendered"] == 0


def test_verified_gamma_without_user_assignment_draws_d9_then_forms_e10_quotient(conditional_runtime):
    assert_nonzero_branch(conditional_runtime[("nonzero", WORKSPACE)])


def test_zero_d9_certificate_never_revives_the_previously_hit_forward_g_tail(conditional_runtime):
    # j g QD^2 at (38,6) is already the d3 image of U h1^3 D^4
    # at (39,3). The base's permanent j-tail cannot be extended to a
    # claim of survival for all forward-g translates.
    for result in conditional_runtime.values():
        for page in result["pages"]:
            assert not page["gTailLive"], (result["name"], result["workspaceId"], page["page"])


@pytest.mark.parametrize("name,c", (("zero-zeta", 2), ("zero-zeta2", 3)))
def test_zero_euler_image_needs_no_gamma_and_cannot_kill_the_source(conditional_runtime, name, c):
    result = conditional_runtime[(name, WORKSPACE)]
    assert result["unchanged"]
    for page in result["pages"]:
        assert_full_known_cell_quotient(page, zero=True)
        for row in page["rows"]:
            assert row["condition"]["resolved"] and row["condition"]["value"] == c
            assert not row["condition"]["nonzero"]
            assert row["coefficient"]["resolved"] and row["coefficient"]["value"] == 0
            assert row["coefficient"]["zeroEulerImage"] and row["zero"]
            assert row["sourceLive"] and row["sourceDisplayed"]
            assert row["rendered"] == row["certified"] == 0
            if page["page"] >= 6:
                assert not row["targetLive"]  # Earlier genuine d5, not a new d9 death.


def test_unknown_c_stops_at_the_unresolved_d5_and_cannot_certify_later_arrows(conditional_runtime):
    result = conditional_runtime[("unknown-c", WORKSPACE)]
    assert result["unchanged"]
    for page in result["pages"]:
        if page["page"] >= 6:
            assert page["blockedFromPage"] == 5
            assert any("unresolved" in c["reason"] for c in page["conflicts"])
        for row in page["rows"]:
            assert not row["condition"]["resolved"]
            assert not row["coefficient"]["resolved"]
            assert row["certified"] == 0 and not row["canApply"]
            assert row["sourceLive"]  # An unresolved map never certifies death.


def test_a_conflicting_gamma_override_cannot_replace_the_verified_coefficient(conditional_runtime):
    result = conditional_runtime[("conflicting-gamma", WORKSPACE)]
    pages = {p["page"]: p for p in result["pages"]}
    assert result["unchanged"] and pages[9]["blockedFromPage"] is None
    assert pages[10]["blockedFromPage"] == 9
    for page in (pages[9], pages[10]):
        for row in page["rows"]:
            if not row["fact"].endswith("D2"):
                continue
            assert row["condition"]["resolved"] and row["condition"]["nonzero"]
            assert not row["coefficient"]["resolved"]
            assert row["certified"] == 0 and row["sourceLive"] and row["targetLive"]


@pytest.mark.parametrize("workspace_id", tuple(MIXED_ATLAS))
def test_all_six_atlas_images_preserve_the_predicate_and_conjugate_only_units(conditional_runtime, workspace_id):
    reflected, shift = MIXED_ATLAS[workspace_id]
    assert_nonzero_branch(conditional_runtime[("atlas-nonzero", workspace_id)], reflected, shift)
    zero = conditional_runtime[("atlas-zero", workspace_id)]
    assert zero["unchanged"]
    for page in zero["pages"]:
        assert_full_known_cell_quotient(page, zero=True)
        for row in page["rows"]:
            assert row["condition"]["value"] == 2  # Source c, not Frobenius(c)=3.
            assert row["coefficient"]["value"] == 0 and row["coefficient"]["zeroEulerImage"]
            assert row["sourceLive"] and row["sourceDisplayed"]
            assert row["rendered"] == row["certified"] == 0
