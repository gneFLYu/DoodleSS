"""The user's fixed pure-sector basis is not an admission of a differential.

Pure F4 units are 1, independently of the withdrawn Jan. 29 proof.  Witt
2/4-levels and mixed-sector units remain separate data.  Abstract cells below
exercise the actual JS/Python guards without assuming the withdrawn maps.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain import formal_notes_chart
from domain.atlas_transport import ensure_q8_atlas_transports
from domain.fate import class_is_live_on_page, sync_project_fates, sync_workspace_fates
from domain.migrations import migrate_project
from domain.models import Workspace
from domain.seed import demo_project
from test_coefficient_runtime import PARAMETER, runtime
from test_linked_parameter_fate import linked_fixture, resolved
from test_linked_parameter_runtime import LINKED
from test_parameterized_fate import add_arrow, parameter


PURE = {"ws_2sigma_i", "ws_3sigma_i"}
NORMALIZATION = {
    "id": "pure-sigma-i-galois-fixed",
    "value": 1,
    "coefficient_field": "F4",
    "witness": "psi",
    "basis": "Galois-fixed generators and Thom classes",
    "source_ref": "User Galois normalization declaration (2026-09-20)",
    "admission_independent": True,
}
THREE_IDS = {f"three_sigma_d9_{suffix}" for suffix in ("D2", "D6", "BD4", "BD8", "CD3", "CD7")}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def pure_claims(ws):
    return [p for p in ws.propositions if p.conclusion.get("fact_id", "").startswith(("FN-", "DER-"))]


def pin(conclusion, workspace_id="ws_3sigma_i"):
    formal_notes_chart._apply_pure_galois_normalization(conclusion, workspace_id)
    return conclusion


def test_migrated_pure_formal_and_zero_claims_have_independent_normalization(project):
    seen_zero = set()
    for ws in project.workspaces:
        if ws.id not in PURE:
            continue
        claims = pure_claims(ws)
        assert claims
        for claim in claims:
            assert claim.conclusion["coefficient_normalization"] == {**NORMALIZATION, "source_workspace_id": ws.id}
            assert "no exact unit is fixed" not in " ".join(claim.conclusion.get("source_blockers", []))
            if claim.kind == "zero-differential":
                seen_zero.add(ws.id)
        assert not ws.settings.get("coefficient_assignments")
    assert seen_zero == PURE


def test_all_six_three_sigma_units_and_fourteen_independently_proved_d9_rows_are_verified(project):
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    claims = [p for p in ws.propositions if p.conclusion.get("coefficient_parameter")
              and p.conclusion.get("page") == 9]
    assert {p.conclusion["coefficient_parameter"]["id"] for p in claims} == THREE_IDS
    even_facts = {"DER-3I-D9-P", "DER-3I-D9-Q", "DER-3I-D9-C"}
    odd_facts = {"DER-3I-EULER-D9-B", "DER-3I-EULER-D9-C", "FN-3I-007", "FN-3I-008"}
    assert len(claims) == 14
    seen_facts = set()
    for claim in claims:
        spec = claim.conclusion["coefficient_parameter"]
        assert spec["value"] == 1 and spec["domain"] == [1]
        assert spec["frobenius_power"] == 0 and "source_parameter" not in spec
        arrows = [d for d in ws.differentials if d.proposition_id == claim.id]
        fact = claim.conclusion["fact_id"]
        assert fact in even_facts | odd_facts
        seen_facts.add(fact)
        assert claim.status == claim.conclusion["admission_status"] == "verified"
        assert arrows and all(d.status == "verified" and d.page == 9 for d in arrows)
        assert claim.conclusion["source_status"] == "independently-verified"
        certificate = claim.conclusion["verification_certificate"]
        assert certificate["status"] == "verified"
        assert certificate["method"] == (
            "Euler image, finite g-injection and h1 lift" if fact in even_facts
            else "Euler products, finite target survival and h1 detection")
        assert certificate["source_refs"] and certificate["premises"]
        assert certificate["no_withdrawn_premise"] is True
        assert not {"FN-3I-010", "FN-3I-010-pc"} & set(certificate["premises"])
    assert seen_facts == even_facts | odd_facts
    assert not ws.settings.get("coefficient_assignments")


def test_early_d3_and_later_d5_have_separate_certificates_not_witt_normalizations(project):
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    rows = [d for d in ws.differentials if d.label == "FN-3I-001"]
    props = {p.id: p for p in ws.propositions}
    assert len(rows) == 4
    for row in rows:
        claim = props[row.proposition_id]
        assert row.page == 3 and row.period_stem == 8
        assert row.status == claim.status == "verified"
        proof = claim.conclusion["d3_product_certificate"]
        assert proof["status"] == "verified"
        assert "FN-2I-001" in proof["premises"]
        assert "not a 2-torsion group" in proof["scope"]
        assert "actual hidden h1 extension" in proof["actual_products"]["R*h1"]
    zero = props["formal_prop_fn-3i-001-zero"]
    assert zero.status == "verified" and zero.conclusion["page"] == 3
    assert zero.kind == "zero-differential"  # never a permanent-cycle claim
    later = props["formal_prop_fn-3i-001-q-zero"]
    assert later.status == "verified" and later.conclusion["page"] == 5
    assert "d3_product_certificate" not in later.conclusion
    certificate = later.conclusion["verification_certificate"]
    assert certificate["status"] == "verified"
    assert certificate["method"] == "Euler product, actual hidden h2 product, and d5 squared"
    assert "(0,6)" in certificate["derivation"] and "(4,2)" in certificate["derivation"]
    assert "not an implication from d3(C)=0" in later.conclusion["derivation"]
    assert "No FN-3I-002, Jan29" in certificate["scope"]


def test_atlas_carries_fixed_pure_basis_metadata_not_new_assignments(project):
    sources = {w.id: w for w in project.workspaces}
    seen = set()
    for image in project.workspaces:
        plan = image.settings.get("atlas_transport", {})
        source_id = plan.get("source_workspace_id")
        if source_id not in PURE:
            continue
        seen.add(source_id)
        prefix = f"atlas_{plan['sector_id']}_"
        by_id = {p.id: p for p in image.propositions}
        for original in pure_claims(sources[source_id]):
            claim = by_id[prefix + original.id]
            assert claim.status == original.status
            assert claim.conclusion["coefficient_normalization"] == {**NORMALIZATION, "source_workspace_id": source_id}
            assert claim.conclusion["coefficient_normalization"] is not original.conclusion["coefficient_normalization"]
            spec = claim.conclusion.get("coefficient_parameter")
            if spec:
                assert spec["value"] == 1 and spec["domain"] == [1]
                assert spec["id"] == original.conclusion["coefficient_parameter"]["id"]
                assert spec["frobenius_power"] == int(plan["reflected"])
        assert not image.settings.get("coefficient_assignments")
    assert seen == PURE


def test_independently_verified_mixed_units_do_not_fix_unknown_units_or_source_links(project):
    seen_local, seen_links, seen_fixed = set(), set(), set()
    seen_d11 = {}
    for ws in project.workspaces:
        plan = ws.settings.get("atlas_transport", {})
        if ws.id != "ws_sigma_i_2sigma_j" and plan.get("source_workspace_id") != "ws_sigma_i_2sigma_j":
            continue
        for claim in ws.propositions:
            spec = claim.conclusion.get("coefficient_parameter")
            if not spec:
                continue
            assert "coefficient_normalization" not in claim.conclusion
            if spec["id"] == "mixed_d3_C":
                assert spec["value"] == 2 and spec["domain"] == [2]
                assert spec["frobenius_power"] == int(plan.get("reflected", False))
                assert "source_parameter" not in spec
                assert claim.status == "verified"
                certificate = claim.conclusion["verification_certificate"]
                assert certificate["status"] == "verified"
                assert "W/4" in certificate["derivation"]
                assert "Witt two-layer" in certificate["scope"]
                seen_fixed.add(ws.id)
                continue
            if spec["id"] == "mixed_d11_R":
                assert spec["value"] == 3 and spec["domain"] == [3]
                assert spec["frobenius_power"] == int(plan.get("reflected", False))
                assert "source_parameter" not in spec
                assert claim.status == "verified"
                metadata = claim.conclusion
                assert metadata["verification_certificate"]["status"] == "verified"
                assert metadata["coefficient_correction"]["normalized_target_unit"] == 3
                assert metadata["printed_source_formula"]["coefficient"] == 1
                assert metadata["period_stem"] == 64
                assert metadata["paired_pattern_stem"] == 32
                seen_d11.setdefault(ws.id, set()).add(claim.id)
                continue
            if spec["id"] in {"mixed_d9_PD2", "mixed_d9_PD6"}:
                assert spec["value"] == 3 and spec["domain"] == [3]
                assert spec["frobenius_power"] == int(plan.get("reflected", False))
                assert "Verified FN-2I-016" in spec["fixed_reason"]
                assert claim.status == "review"  # c/b admission is separate from the fixed numerator.
                seen_local.add(spec["id"])
                continue
            assert spec["value"] is None and spec["domain"] == [1, 2, 3]
            if "source_parameter" in spec:
                assert spec["source_parameter"]["workspace_id"] == "ws_3sigma_i"
                assert spec["source_parameter"]["parameter_id"] == spec["id"]
                seen_links.add(spec["id"])
            else:
                seen_local.add(spec["id"])
    assert {"mixed_d5_A", "mixed_d5_B", "mixed_d9_PD2", "mixed_d9_PD6"} <= seen_local
    assert seen_links == {"three_sigma_d9_D2", "three_sigma_d9_D6", "three_sigma_d9_CD3", "three_sigma_d9_CD7"}
    assert len(seen_fixed) == 6 and "ws_sigma_i_2sigma_j" in seen_fixed
    assert set(seen_d11) == seen_fixed
    assert all(len(claim_ids) == 2 for claim_ids in seen_d11.values())


def test_withdrawn_january_proof_is_not_reinstated_by_unit_one(project):
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    claims = [p for p in ws.propositions if p.conclusion.get("fact_id") in {"FN-3I-010", "FN-3I-010-pc"}]
    assert claims
    assert {p.kind for p in claims} >= {"differential", "permanent-cycle"}
    for claim in claims:
        assert claim.status == "review"
        assert claim.conclusion["source_status"] == "withdrawn-proof"
        assert "is not rejected by this audit" not in claim.conclusion.get("machine_verification_pending", "")
        assert claim.conclusion["coefficient_normalization"] == {**NORMALIZATION, "source_workspace_id": ws.id}
    final = next(d for d in ws.differentials if d.label == "FN-3I-010" and d.page == 23)
    nodes = {n.id: n for n in ws.classes}
    assert final.status == "review"
    assert nodes[final.source_id].grade.stem == 12
    assert nodes[final.source_id].grade.filtration == 0
    assert nodes[final.target_id].grade.stem == 11
    assert nodes[final.target_id].grade.filtration == 23
    assert nodes[final.source_id].label == r"2v_1^2Du_{3\sigma_i}"
    assert nodes[final.target_id].label == r"x^2h_1k^5D^4u_{3\sigma_i}"


def test_pin_preserves_witt_layers_frobenius_and_linked_source_definition():
    conclusion = {"coefficient_parameter": parameter("alpha", frobenius_power=1),
                  "two_valuation": 2, "j_order": 1, "target_label": "4D"}
    pin(conclusion)
    assert conclusion["coefficient_normalization"] == {**NORMALIZATION, "source_workspace_id": "ws_3sigma_i"}
    assert conclusion["coefficient_parameter"] == parameter(
        "alpha", 1, domain=[1], frobenius_power=1, fixed_reason="pure-sigma-i-galois-fixed")
    assert (conclusion["two_valuation"], conclusion["j_order"], conclusion["target_label"]) == (2, 1, "4D")
    binding = parameter("alpha", source_parameter={"workspace_id": "elsewhere", "parameter_id": "alpha",
                                                    "differential_id": "source", "page": 9})
    linked = {"coefficient_parameter": deepcopy(binding)}
    pin(linked)
    assert linked["coefficient_parameter"] == binding


def test_refresh_does_not_silently_rewrite_old_source_or_mixed_assignments(project):
    candidate = deepcopy(project)
    source = next(w for w in candidate.workspaces if w.id == "ws_3sigma_i")
    mixed = next(w for w in candidate.workspaces if w.id == "ws_sigma_i_2sigma_j")
    source.settings["coefficient_assignments"] = {"three_sigma_d9_D2": "zeta"}
    mixed.settings["coefficient_assignments"] = {"mixed_d5_A": 3, "mixed_d5_B": 2}
    formal_notes_chart.ensure_formal_notes_chart(candidate)
    ensure_q8_atlas_transports(candidate)
    assert source.settings["coefficient_assignments"] == {"three_sigma_d9_D2": "zeta"}
    assert mixed.settings["coefficient_assignments"] == {"mixed_d5_A": 3, "mixed_d5_B": 2}
    specs = [p.conclusion["coefficient_parameter"] for p in source.propositions
             if p.conclusion.get("coefficient_parameter", {}).get("id") == "three_sigma_d9_D2"]
    assert specs and all(s["value"] == 1 and s["domain"] == [1] for s in specs)


@pytest.mark.parametrize("override", [2, 3, "zeta", "zeta^2"])
def test_real_js_fixed_value_rejects_nonone_override_and_keeps_review_inert(override):
    metadata = pin({"coefficient_parameter": parameter("alpha")})
    result = runtime(PARAMETER + r"""
      const metadata=METADATA, fixed=claim('fixed',metadata.coefficient_parameter);
      fixed.conclusion=metadata;
      const ws=workspace(4,[A,B,AB,T],[diff('a','A','T'),attach(diff('b','B','T'),'fixed')],[fixed]);
      const first=compute(ws);
      ws.settings.coefficient_assignments={alpha:OVERRIDE};
      const blocked=compute(ws);
      delete ws.settings.coefficient_assignments.alpha;
      const restored=compute(ws);
      ws.differentials.forEach(d=>d.status='review'); fixed.status='review';
      const review=compute(ws);
      console.log(JSON.stringify({initial:kernel(first),restored:kernel(restored),
        blocked:blocked.blockedFromPage,errors:blocked.conflicts,
        unchanged:metadata.coefficient_parameter.value===1,distinct:first!==blocked&&blocked!==restored,
        live:[A,B,T].map(n=>review.live(n,n.grade)),status:fixed.status}));
    """.replace("METADATA", json.dumps(metadata)).replace("OVERRIDE", json.dumps(override)))
    assert result["initial"] == result["restored"] == [[1, 1]]
    assert result["blocked"] == 3
    assert any("conflicting assignments" in c["reason"] for c in result["errors"])
    assert result["unchanged"] and result["distinct"]
    assert result["live"] == [True, True, True] and result["status"] == "review"


@pytest.mark.parametrize("override", [2, 3])
def test_python_fate_rechecks_pin_without_overriding_assignments_or_history(override):
    ws = Workspace("ws_3sigma_i", "Fixed pure coefficient", spectral_sequence="hfpss")
    arrow, claim = add_arrow(ws, "fixed", spec=parameter("alpha"))
    pin(claim.conclusion)
    sync_workspace_fates(ws)
    assert not class_is_live_on_page(ws, arrow.source_id, 6)
    history = deepcopy(ws.differential_events)
    ws.settings["coefficient_assignments"] = {"alpha": override}
    assert class_is_live_on_page(ws, arrow.source_id, 6)
    sync_workspace_fates(ws)
    assert ws.differential_events == history
    assert ws.settings["coefficient_assignments"] == {"alpha": override}
    assert claim.conclusion["coefficient_parameter"]["value"] == 1
    del ws.settings["coefficient_assignments"]["alpha"]
    arrow.status = claim.status = "review"
    assert class_is_live_on_page(ws, arrow.source_id, 6)


def test_real_js_mixed_link_reads_fixed_source_only_after_source_admission(project):
    source = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    mixed = next(w for w in project.workspaces if w.id == "ws_sigma_i_2sigma_j")
    target_claim = next(p for p in mixed.propositions
                        if p.conclusion.get("coefficient_parameter", {}).get("source_parameter", {}).get("parameter_id")
                        == "three_sigma_d9_CD7")
    target_spec = target_claim.conclusion["coefficient_parameter"]
    source_row = next(d for d in source.differentials if d.id == target_spec["source_parameter"]["differential_id"])
    source_claim = next(p for p in source.propositions if p.id == source_row.proposition_id)
    result = runtime(LINKED + r"""
      const f=fixtureLinked(), states=[];
      f.sourceClaim.conclusion=SOURCE; f.sourceSpec=f.sourceClaim.conclusion.coefficient_parameter;
      f.ws.propositions.find(p=>p.id==='linked-claim').conclusion={coefficient_parameter:TARGET};
      f.spec=f.ws.propositions.find(p=>p.id==='linked-claim').conclusion.coefficient_parameter;
      const ref=f.spec.source_parameter;
      f.source.id=ref.workspace_id; f.sourceRow.id=ref.differential_id; f.sourceRow.page=ref.page;
      f.source.settings={}; f.ws.settings={};
      function record(){states.push(compute(f.ws).coefficientState(f.row));}
      f.sourceRow.status=f.sourceClaim.status='review'; record();
      f.sourceRow.status=f.sourceClaim.status='proven'; record();
      f.spec.frobenius_power=1; record();
      f.ws.settings.coefficient_assignments={[f.spec.id]:1}; record();
      delete f.ws.settings.coefficient_assignments[f.spec.id];
      f.source.settings.coefficient_assignments={[f.spec.id]:2}; record();
      console.log(JSON.stringify({states,pin:f.sourceSpec.value,local:f.spec.value}));
    """.replace("SOURCE", json.dumps(source_claim.conclusion)).replace("TARGET", json.dumps(target_spec)))
    states = result["states"]
    assert not states[0]["resolved"] and "not admitted" in states[0]["reason"]
    assert states[1]["resolved"] and states[1]["value"] == 1
    assert states[2]["resolved"] and states[2]["value"] == 1
    assert not states[3]["resolved"] and "local assignment" in states[3]["reason"]
    assert not states[4]["resolved"] and "conflicting linked" in states[4]["reason"]
    assert result["pin"] == 1 and result["local"] is None


def test_python_link_keeps_review_source_and_local_override_blocked():
    candidate, source, source_row, source_claim, target, image, _ = linked_fixture()
    source.settings.clear()
    pin(source_claim.conclusion)
    source_row.status = source_claim.status = "review"
    sync_project_fates(candidate)
    assert not resolved(candidate, target)["resolved"]
    assert class_is_live_on_page(target, image.source_id, 12, project=candidate)
    source_row.status = source_claim.status = "admitted"
    assert resolved(candidate, target) == {"resolved": True, "id": "gamma", "value": 1}
    assert not class_is_live_on_page(target, image.source_id, 12, project=candidate)
    target.settings["coefficient_assignments"] = {"gamma": 1}
    assert not resolved(candidate, target)["resolved"]
    assert class_is_live_on_page(target, image.source_id, 12, project=candidate)
