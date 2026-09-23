"""Source-derived closures, with research hypotheses separated from admission."""
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
from domain.seed import demo_project
from test_three_sigma_convergence import assert_absent_ad6_d19, assert_tate_cycle_conflict


@pytest.fixture(scope="module")
def source_project():
    return migrate_project(demo_project())


def runtime(project, pages):
    payload = {
        "project": asdict(project), "workspaces": ["ws_3sigma_i"], "pages": pages,
        "bounds": {"stemMin": 0, "stemMax": 63, "filtrationMin": 0, "filtrationMax": 40},
        "vectorAudit": True,
        "probes": [{"pattern": "S40", "stem": s, "filtration": f}
                   for s, f in ((12, 0), (32, 4), (52, 8), (8, 12))],
        "vectorProbes": [{"components": c, "stem": s, "filtration": f}
                         for c, s, f in (
                             ({"S22Y": 1}, 2, 2), ({"S22H": 1}, 2, 2),
                             ({"S22Y": 1}, 10, 2), ({"S22H": 1}, 10, 2),
                             ({"S62": 1}, 6, 2), ({"S62": 1}, 14, 2),
                             ({"S22H": 1}, 0, 6))],
    }
    result = subprocess.run(["node", "tests/chart_runtime.cjs"], cwd=ROOT,
                            input=json.dumps(payload), text=True, encoding="utf-8",
                            capture_output=True, check=True, timeout=90)
    return json.loads(result.stdout)[0]["pages"]


@pytest.fixture(scope="module")
def three_hypothesis(source_project):
    project = deepcopy(source_project)
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    for arrow in ws.differentials:
        if arrow.label.startswith("FN-"):
            arrow.status = "admitted"
    for claim in ws.propositions:
        if claim.conclusion.get("fact_id", "").startswith("FN-"):
            claim.status = "admitted"
    for matrix in ws.differential_maps:
        if any(d.linear_map_id == matrix.id and d.status == "admitted" for d in ws.differentials):
            matrix.status = "admitted"
    # Counterfactual admission of the historical arrows tests their algebra,
    # not their proofs. Galois normalization fixes units in production too.
    ws.settings["coefficient_assignments"] = {"three_sigma_d9_CD3": 1, "three_sigma_d9_CD7": 1}
    return project, runtime(project, [2, 3, 4, 5, 6, 9, 11, 12, 19, 20, 23, 24])


def test_three_sigma_zero_constraints_have_independent_mathematical_reasons(source_project):
    ws = next(w for w in source_project.workspaces if w.id == "ws_3sigma_i")
    props = {p.id: p for p in ws.propositions}
    even = props["formal_prop_fn-3i-003-even-zero"]
    q = props["formal_prop_fn-3i-001-q-zero"]
    assert even.status == q.status == "verified"
    assert even.conclusion["e2_components"] == {"S22Y": 1}
    assert q.conclusion["e2_components"] == {"S22H": 1}
    assert even.conclusion["period_stem"] == 16
    assert q.conclusion["period_stem"] == 8
    assert "relative coefficient 1" in even.conclusion["coefficient_constraint"]
    assert "admission of the source differential is separate" in even.conclusion["coefficient_constraint"]
    assert even.conclusion["coefficient_normalization"]["admission_independent"] is True
    assert "empty target" in q.conclusion["derivation"]
    assert "not an implication from d3(C)=0" in q.conclusion["derivation"]
    for claim in (even, q):
        certificate = claim.conclusion["verification_certificate"]
        assert certificate["status"] == "verified"
        assert certificate["method"] == "Euler product, actual hidden h2 product, and d5 squared"
        assert "FN-2I-004" in certificate["derivation"]
        assert "No FN-3I-002, Jan29" in certificate["scope"]
        assert "d3_product_certificate" not in claim.conclusion
        assert claim.conclusion["source_status"] == "independently-verified"


def test_d5_zero_degree_argument_and_parity_kernels_run_in_real_chart(three_hypothesis):
    _, pages = three_hypothesis
    e2 = next(p for p in pages if p["page"] == 2)
    assert not next(p for p in e2["vectorProbes"] if p["stem"] == 0 and p["filtration"] == 6)["displayed"]
    e6 = next(p for p in pages if p["page"] == 6)
    def live(pattern, stem):
        return next(p["live"] for p in e6["vectorProbes"] if p["components"] == {pattern: 1}
                    and p["stem"] == stem and p["filtration"] == 2)
    assert live("S22Y", 2) and live("S22H", 2)
    assert not live("S22Y", 10) and live("S22H", 10)
    assert not live("S62", 6) and live("S62", 14)
    for page in pages:
        if page["page"] < 23:
            for conflict in page["conflicts"]:
                assert page["page"] >= 19
                assert_absent_ad6_d19(conflict)
    for row in pages:
        if row["page"] >= 23:
            assert_tate_cycle_conflict(row)
    assert not [(p["page"], b) for p in pages for b in p["blocks"] if b["barriers"]]


def test_removing_zero_constraints_restores_unknown_directions(three_hypothesis):
    project, _ = three_hypothesis
    project = deepcopy(project)
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    zero_ids = {"formal_prop_fn-3i-003-even-zero", "formal_prop_fn-3i-001-q-zero"}
    ws.propositions = [p for p in ws.propositions if p.id not in zero_ids]
    e6 = runtime(project, [6])[0]
    assert any(b["barriers"] for b in e6["blocks"])
    assert any("proper subspace" in c["reason"] for c in e6["conflicts"])


def test_counterfactual_three_sigma_d23_preserves_the_actual_witt_cycle_quotient(three_hypothesis):
    _, pages = three_hypothesis
    for page in (4, 6, 12, 20, 23):
        row = next(p for p in pages if p["page"] == page)
        for probe in row["probes"]:
            # The g^3 image is already the independent CD1 d11 target;
            # its outgoing-cycle certificate cannot restore that boundary.
            if probe["filtration"] == 12 and page >= 12:
                assert not probe["ports"]
            else:
                assert "1:0" in probe["ports"]
    e23 = next(p for p in pages if p["page"] == 23)
    assert_tate_cycle_conflict(e23)
    assert "formal_diff_fn-3i-010_2" not in e23["rows"]
    e24 = next(p for p in pages if p["page"] == 24)
    assert_tate_cycle_conflict(e24)
    low = next(p for p in e24["probes"] if p["filtration"] == 0)
    assert set(low["ports"]) == {"1:0", "2:0", "3:0", "1:1", "2:1", "3:1"}
    # Blocking contradictory assumptions retains the entire pre-d23 quotient,
    # not merely w. It must not manufacture a high-filtration vanishing line.
    assert [p["ports"] for p in e24["probes"]] == [p["ports"] for p in e23["probes"]]


def test_low_three_sigma_seed_has_independent_tate_proof_not_a_printed_corollary(source_project):
    ws = next(w for w in source_project.workspaces if w.id == "ws_3sigma_i")
    arrow = next(d for d in ws.differentials if d.id == "formal_diff_three_d5_tate_positive_derived")
    claim = next(p for p in ws.propositions if p.id == arrow.proposition_id)
    assert arrow.status == claim.status == "verified"
    assert claim.conclusion["verification_certificate"]["method"] == "Euler image and finite incoming-source exclusion"
    assert claim.conclusion["fact_id"] == "FN-3I-002"
    assert claim.conclusion["evidence_kind"] == "Tate-comparison-derived"
    assert claim.conclusion["comparison_translation"] == {
        "g_exponent": -2, "D_exponent": 4, "spectral_sequence": "tate"}
    assert "commented" in claim.conclusion["derivation"]
    assert arrow.period_stem == 16


def test_mixed_d5_repeats_are_conditioned_on_two_torsion_not_permanence(source_project):
    ws = next(w for w in source_project.workspaces if w.id == "ws_sigma_i_2sigma_j")
    props = {p.id: p for p in ws.propositions}
    rows = [d for d in ws.differentials if d.page == 5]
    originals = [d for d in rows if props[d.proposition_id].conclusion["fact_id"].startswith("FN-")]
    derived = [d for d in rows if d not in originals]
    assert len(originals) == 5 and len(derived) == 1
    assert derived[0].id == "formal_diff_mixed_d5_a_D2_leibniz_derived"
    parameter = props[derived[0].proposition_id].conclusion["coefficient_parameter"]
    assert parameter["id"] == "mixed_d5_A" and parameter["affine_offset"] == 1
    for row in rows:
        metadata = props[row.proposition_id].conclusion
        expected_status = ("source-verified" if metadata.get("coefficient_parameter", {}).get("proof_binding")
                           else "verified" if metadata["fact_id"] == "FN-MIX-004" else "review")
        assert row.status == props[row.proposition_id].status == expected_status
        assert row.period_stem == metadata["period_stem"] == 16
        assert metadata["period_kind"] == "repeated-differential-pattern"
        assert not metadata["period_is_invertible"]
        if metadata["fact_id"] == "FN-MIX-004":
            assert "2P=0" in metadata["period_source_ref"]
            assert "verified 16-stem differential pattern by Leibniz" in metadata["period_source_ref"]
        else:
            assert "extra Leibniz term vanishes" in metadata["period_source_ref"]


def test_new_closures_are_transported_without_upgrading_admission(source_project):
    by_id = {w.id: w for w in source_project.workspaces}
    checked = set()
    for target in source_project.workspaces:
        plan = target.settings.get("atlas_transport")
        if not plan or plan["source_workspace_id"] not in {"ws_3sigma_i", "ws_sigma_i_2sigma_j"}:
            continue
        prefix = f"atlas_{plan['sector_id']}_"
        diffs = {d.id: d for d in target.differentials}
        for source in by_id[plan["source_workspace_id"]].differentials:
            if source.page != 5:
                continue
            image = diffs[prefix + source.id]
            assert image.status == source.status
            assert image.period_stem == source.period_stem == 16
        checked.add(plan["source_workspace_id"])
    assert checked == {"ws_3sigma_i", "ws_sigma_i_2sigma_j"}


def test_mixed_source_conflicts_separate_unresolved_units_from_verified_corrections(source_project):
    checked = set()
    for ws in source_project.workspaces:
        for claim in ws.propositions:
            fact = claim.conclusion.get("fact_id")
            if fact not in {"FN-MIX-005", "FN-MIX-006"}:
                continue
            conflict, = claim.conclusion["source_conflicts"]
            assert "1409-1413" in conflict["source_ref"]
            assert any("1409-1413" in ref for ref in claim.source_refs)
            if fact == "FN-MIX-005":
                assert claim.status == "review"
                assert "formal_notes remains primary" in conflict["authority"]
                blockers = " ".join(claim.conclusion["source_blockers"])
                assert "b nonzero" in blockers and "relative unit" in blockers
                assert "remains unresolved" in blockers
                proof = claim.conclusion["nonzero_parameter_certificate"]
                assert proof["id"] == conflict["repair_certificate_id"] == "DER-MIX-D5-B-NONZERO"
                assert proof["status"] == "verified"
                assert proof["domain"] == [1, 2, 3] and proof["value"] is None
                parameter = claim.conclusion["coefficient_parameter"]
                assert parameter["domain"] == [1, 2, 3] and parameter["value"] is None
                assert parameter["id"] not in ws.settings.get("coefficient_assignments", {})
                assert conflict["runtime_admission"] is False
                assert "value not determined" in conflict["unit_parameter"]
                assert "bQ" in conflict["conditional_family"]
            else:
                assert claim.status == "verified"
                assert claim.conclusion["source_blockers"] == []
                assert conflict["kind"] == "historical-rejection-and-factorization-unit-mismatch"
                assert conflict["status"] == "resolved-by-independent-corrected-proof"
                assert "printed coefficient 1 for review" in conflict["authority"]
                assert "verifies coefficient zeta^2" in conflict["authority"]
                assert "1+zeta^2=zeta" in conflict["checked_identity"]
                assert "lambda*zeta^2" in conflict["conditional_correction"]
                assert "fixes lambda=1" in conflict["conditional_correction"]
                printed = claim.conclusion["printed_source_formula"]
                assert printed["coefficient"] == 1 and printed["status"] == "review-corrected"
                assert "formal_notes.tex:972-991" in printed["source_ref"]
                assert "zeta" not in printed["statement"]
                correction = claim.conclusion["coefficient_correction"]
                assert correction["status"] == "verified"
                assert (correction["source_product_unit"], correction["rotated_premise_unit"],
                        correction["normalized_target_unit"]) == (2, 1, 3)
                assert claim.conclusion["coefficient_parameter"]["value"] == 3
            checked.add((ws.id, fact))
    assert {f for _, f in checked} == {"FN-MIX-005", "FN-MIX-006"}
    assert len({ws for ws, _ in checked}) > 1
