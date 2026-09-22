"""Verified d9 products with the user's fixed pure-sector units.

The six P/Q/C rows use independent Euler, finite-quotient, g-injectivity and
h1-lift proofs, not the withdrawn Ck premise. The later counterfactual tests
still explicitly admit historical hypotheses only in copies, preserving the
independent Tate-cycle conflict rather than treating normalization as a proof.
"""
from copy import deepcopy
from dataclasses import asdict
import itertools
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.atlas_transport import ensure_q8_atlas_transports
from domain.formal_notes_chart import ensure_formal_notes_chart
from domain.migrations import migrate_project
from domain.seed import demo_project
from test_three_sigma_convergence import assert_tate_cycle_conflict


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def test_six_separate_source_rows_keep_block_ids_but_pin_pure_units(project):
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    claims, nodes = {p.id: p for p in ws.propositions}, {n.id: n for n in ws.classes}
    rows = [d for d in ws.differentials if d.label.startswith("DER-3I-D9")]
    assert len(rows) == 6
    parameters = {}
    for row in rows:
        claim = claims[row.proposition_id]
        assert row.page == 9 and row.period_stem == 64
        assert row.status == claim.status == "verified"
        metadata = claim.conclusion
        assert metadata["admission_status"] == "verified"
        assert metadata["source_status"] == "independently-verified"
        assert metadata["source_blockers"] == metadata["withdrawn_dependencies"] == []
        assert not {"FN-3I-010", "FN-3I-010-pc"} & set(metadata["derived_from"])
        assert "conditional_statement" not in metadata
        parameter = metadata["coefficient_parameter"]
        assert "coefficient is fixed to 1" in row.period_notes
        assert "admission is separate" in row.period_notes
        assert parameter["value"] == 1 and parameter["domain"] == [1]
        assert parameter["fixed_reason"] == "pure-sigma-i-galois-fixed"
        assert metadata["coefficient_normalization"]["admission_independent"]
        assert "D^4 is not used as a 9-cycle" in metadata["derivation"]
        a, b = nodes[row.source_id].grade, nodes[row.target_id].grade
        assert (b.stem, b.filtration) == (a.stem - 1, a.filtration + 9)
        parameters.setdefault(parameter["id"], []).append((a.stem, a.filtration))
    assert {k: sorted(v) for k, v in parameters.items()} == {
        "three_sigma_d9_D2": [(17, 1), (18, 2), (18, 2)],
        "three_sigma_d9_D6": [(49, 1), (50, 2), (50, 2)],
    }


def three_sigma_images(project):
    return [w for w in project.workspaces if w.id == "ws_3sigma_i"
            or w.settings.get("atlas_transport", {}).get("source_workspace_id") == "ws_3sigma_i"]


def test_euler_image_and_verified_target_survival_certify_nonzero_p_arrows(project):
    workspaces = three_sigma_images(project)
    assert len(workspaces) == 3
    for ws in workspaces:
        claims = {p.id: p for p in ws.propositions}
        nodes = {n.id: n for n in ws.classes}
        plan = ws.settings.get("atlas_transport", {})
        rows = [d for d in ws.differentials if d.label == "DER-3I-D9-P"]
        assert len(rows) == 2
        for row in rows:
            claim = claims[row.proposition_id]
            metadata = claim.conclusion
            power = 2 if "_D2_" in row.id else 6
            assert row.status == claim.status == metadata["admission_status"] == "verified"
            assert row.page == 9 and row.period_stem == 64
            assert metadata["source_status"] == "independently-verified"
            assert metadata["evidence_kind"] == "Euler-image-and-finite-target-injection"
            assert metadata["withdrawn_dependencies"] == []
            assert {"FN-2I-016", "FN-3I-002"} <= set(metadata["derived_from"])
            assert not {"FN-3I-010", "FN-3I-010-pc"} & set(metadata["derived_from"])
            assert metadata["source_blockers"] == []
            certificate = metadata["euler_image_certificate"]
            assert certificate["status"] == "verified" and certificate["equation_only"] is False
            assert certificate["target_nonzero"] == "verified"
            assert certificate["scope"] == "source-workspace"
            assert certificate["source_workspace_id"] == "ws_3sigma_i"
            assert {"FN-2I-016", "FN-3I-002"} <= set(certificate["premises"])
            assert not {"FN-3I-010", "FN-3I-010-pc"} & set(certificate["premises"])
            # Nested evidence coordinates remain in the explicitly named
            # source workspace, while actual endpoints are transported.
            assert certificate["source_bidegree"] == [8 * power + 2, 2]
            assert certificate["target_bidegree"] == [8 * power + 1, 11]
            assert nodes[row.source_id].grade.stem == 8 * power + 2 + plan.get("stem_shift", 0)
            assert nodes[row.target_id].grade.stem == 8 * power + 1 + plan.get("stem_shift", 0)
            assert nodes[row.source_id].style["e2_pattern"] == "S22Y"
            assert nodes[row.target_id].style["e2_pattern"] == "S13"
            survival = metadata["target_survival"]
            assert survival["status"] == "verified"
            assert survival["incoming_d5"]["zero_certificate"] == "DER-3I-D5-A-EVEN"
            assert "unverified_premise" not in survival
            assert survival["incoming_d5"]["source_bidegree"] == [8 * power + 2, 6]
            assert survival["incoming_d5"]["finite_source"] == f"A k D^{power + 1}"
            assert survival["incoming_d5"]["finite_source_identity"] == f"g A D^{power - 2}"
            assert "S62V" in survival["incoming_d5"]["other_direction"]
            parameter = metadata["coefficient_parameter"]
            assert parameter["id"] == f"three_sigma_d9_D{power}"
            assert parameter["value"] == 1 and parameter["domain"] == [1]
            assert parameter["frobenius_power"] == int(plan.get("reflected", False))
            assert metadata["coefficient_normalization"]["admission_independent"] is True
            assert "nonzero target unverified" not in claim.statement
            assert "conditional_statement" not in metadata


def test_q_and_c_use_verified_g_injectivity_and_h1_lift_without_withdrawn_premises(project):
    for ws in three_sigma_images(project):
        claims = {p.id: p for p in ws.propositions}
        rows = [d for d in ws.differentials if d.label in {"DER-3I-D9-Q", "DER-3I-D9-C"}]
        assert len(rows) == 4
        for row in rows:
            claim = claims[row.proposition_id]
            metadata = claim.conclusion
            assert row.status == claim.status == metadata["admission_status"] == "verified"
            assert metadata["source_status"] == "independently-verified"
            assert {"FN-2I-016", "FN-3I-002", "FN-3I-006"} <= set(metadata["derived_from"])
            assert not {"FN-3I-010", "FN-3I-010-pc"} & set(metadata["derived_from"])
            assert metadata["withdrawn_dependencies"] == metadata["source_blockers"] == []
            assert "conditional_statement" not in metadata
            assert "Q comes from permanent Ck" not in metadata["derivation"]
            assert "D^4 is not used as a 9-cycle" in metadata["derivation"]
            if row.linear_map_id:
                assert next(m for m in ws.differential_maps if m.id == row.linear_map_id).status == "verified"


def test_verified_refresh_removes_all_six_stale_dependencies_without_history_loss(project):
    candidate = deepcopy(project)
    source = next(w for w in candidate.workspaces if w.id == "ws_3sigma_i")
    old_reason = "Old closure metadata incorrectly required the Jan.29 Ck proof."
    for ws in three_sigma_images(candidate):
        claims = {p.id: p for p in ws.propositions}
        for row in ws.differentials:
            if not row.label.startswith("DER-3I-D9"):
                continue
            row.status = claims[row.proposition_id].status = "review"
            metadata = claims[row.proposition_id].conclusion
            metadata["derived_from"].append("FN-3I-010-pc")
            metadata["withdrawn_dependencies"] = ["FN-3I-010-pc"]
            metadata["source_blockers"] = [old_reason]
            metadata["source_status"] = "derived-review"
            metadata["conditional_statement"] = "Old formula: nonzero target unverified."
            metadata["user_audit_note"] = "Preserve unrelated researcher annotation."
    before_counts = (len(source.classes), len(source.differentials), len(source.propositions))
    snapshots = []
    for _ in range(2):
        ensure_formal_notes_chart(candidate)
        ensure_q8_atlas_transports(candidate)
        assert (len(source.classes), len(source.differentials), len(source.propositions)) == before_counts
        test_euler_image_and_verified_target_survival_certify_nonzero_p_arrows(candidate)
        test_q_and_c_use_verified_g_injectivity_and_h1_lift_without_withdrawn_premises(candidate)
        conclusions = []
        for ws in three_sigma_images(candidate):
            claims = {p.id: p for p in ws.propositions}
            for row in ws.differentials:
                if row.label.startswith("DER-3I-D9"):
                    metadata = claims[row.proposition_id].conclusion
                    assert old_reason not in metadata["source_blockers"]
                    assert "conditional_statement" not in metadata
                    assert metadata["user_audit_note"] == "Preserve unrelated researcher annotation."
                    conclusions.append(deepcopy(metadata))
        assert len(conclusions) == 18
        snapshots.append(conclusions)
    assert snapshots[0] == snapshots[1]


def test_independently_verified_closures_apply_to_the_actual_production_chart(project):
    workspaces = three_sigma_images(project)
    shifts = {w.id: w.settings.get("atlas_transport", {}).get("stem_shift", 0) for w in workspaces}
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces], "pages": [9, 10],
        "vectorAudit": True,
        "boundsByWorkspace": {ident: {"stemMin": shift, "stemMax": shift + 63,
                                      "filtrationMin": 0, "filtrationMax": 12}
                              for ident, shift in shifts.items()},
        "probes": [{"pattern": pattern, "stem": 8 * power + stem + shift, "filtration": filtration}
                   for shift in sorted(set(shifts.values())) for power in (2, 6)
                   for pattern, stem, filtration in (("S22Y", 2, 2), ("S22H", 2, 2),
                                                      ("S11", 1, 1), ("S13", 1, 11), ("S02", 0, 10))],
        "vectorProbes": [{"components": components, "stem": 8 * power + 2 + shift, "filtration": 2}
                         for shift in sorted(set(shifts.values())) for power in (2, 6)
                         for components in ({"S22Y": 1}, {"S22H": 1}, {"S22Y": 1, "S22H": 1})],
    }
    completed = subprocess.run(["node", "tests/chart_runtime.cjs"], cwd=ROOT,
                               input=json.dumps(payload), text=True, encoding="utf-8",
                               capture_output=True, check=True, timeout=90)
    result = {w["id"]: w["pages"] for w in json.loads(completed.stdout)}
    for ws in workspaces:
        e9, e10 = result[ws.id]
        closure_ids = {d.id for d in ws.differentials if d.label.startswith("DER-3I-D9")}
        assert len(closure_ids) == 6 and closure_ids <= set(e9["rows"])
        assert closure_ids.isdisjoint(e10["rows"])
        for row in (e9, e10):
            assert not row["conflicts"] and row["blockedFromPage"] is None
            assert not row["dangling"]
            assert not [block for block in row["blocks"] if block["barriers"]]
        for power in (2, 6):
            for pattern, stem, filtration in (("S22Y", 2, 2), ("S22H", 2, 2),
                                              ("S11", 1, 1), ("S13", 1, 11), ("S02", 0, 10)):
                before = next(p for p in e9["probes"] if (p["pattern"], p["stem"], p["filtration"]) ==
                              (pattern, 8 * power + stem + shifts[ws.id], filtration))
                after = next(p for p in e10["probes"] if (p["pattern"], p["stem"], p["filtration"]) ==
                             (pattern, 8 * power + stem + shifts[ws.id], filtration))
                assert "0:0" in before["ports"]
                assert set(after["ports"]) == ({"0:1"} if pattern in {"S11", "S22H"} else set())
            for components in ({"S22Y": 1}, {"S22H": 1}, {"S22Y": 1, "S22H": 1}):
                before = next(p for p in e9["vectorProbes"] if p["components"] == components and
                              p["stem"] == 8 * power + 2 + shifts[ws.id])
                after = next(p for p in e10["vectorProbes"] if p["components"] == components and
                             p["stem"] == 8 * power + 2 + shifts[ws.id])
                assert before["live"] is True
                assert after["live"] == (len(components) == 2)
        assert not ws.settings.get("coefficient_assignments")


def runtime(project, units):
    candidate = deepcopy(project)
    ws = next(w for w in candidate.workspaces if w.id == "ws_3sigma_i")
    # Isolate the six product rows from the later Euler-cutoff deduction.
    ws.differentials = [d for d in ws.differentials if not d.label.startswith("DER-3I-EULER-D9")]
    # Only this copy is an explicitly stated research hypothesis.
    for row in ws.differentials:
        if row.label.startswith(("FN-", "DER-3I-D9")):
            row.status = "admitted"
    for claim in ws.propositions:
        if claim.conclusion.get("fact_id", "").startswith(("FN-", "DER-3I-D9")):
            claim.status = "admitted"
    for matrix in ws.differential_maps:
        if any(d.linear_map_id == matrix.id and d.status == "admitted" for d in ws.differentials):
            matrix.status = "admitted"
    ws.settings["coefficient_assignments"] = {f"three_sigma_d9_D{m}": value for m, value in zip((2, 6), units)}
    ws.settings["coefficient_assignments"].update(three_sigma_d9_CD3=1, three_sigma_d9_CD7=1)
    payload = {"project": asdict(candidate), "workspaces": [ws.id], "pages": [9, 10, 23, 24],
               "bounds": {"stemMin": 0, "stemMax": 63, "filtrationMin": 0, "filtrationMax": 40},
               "vectorAudit": True,
               "probes": [{"pattern": p, "stem": s, "filtration": f}
                          for p, s, f in (("S11", 17, 1), ("S11", 49, 1), ("S22H", 18, 2),
                                         ("S22H", 50, 2), ("S13", 17, 11), ("S13", 49, 11))],
               "vectorProbes": [{"components": c, "stem": s, "filtration": 2}
                                for s in (18, 50) for c in ({"S22Y": 1}, {"S22H": 1}, {"S22Y": 1, "S22H": 1})]}
    result = subprocess.run(["node", "tests/chart_runtime.cjs"], cwd=ROOT, text=True, encoding="utf-8",
                            input=json.dumps(payload), capture_output=True, check=True, timeout=90)
    return json.loads(result.stdout)[0]["pages"]


def test_fixed_unit_preserves_the_sum_kernel_and_j_tails(project):
    pages = runtime(project, (1, 1))
    e9, e10, e23, e24 = pages
    for page in (e9, e10):
        assert not page["conflicts"] and page["blockedFromPage"] is None
    for page in (e23, e24):
        assert_tate_cycle_conflict(page)
    assert not [b for page in pages for b in page["blocks"] if b["barriers"]]
    for power in (2, 6):
        for column in ("p", "q", "c"):
            assert f"formal_diff_three_d9_{column}_D{power}_derived" in e9["rows"]
    for point in e9["probes"]:
        assert "0:0" in point["ports"]
    for point in e10["probes"]:
        assert set(point["ports"]) == ({"0:1"} if point["pattern"] in {"S11", "S22H"} else set())
    for point in e10["vectorProbes"]:
        assert point["live"] == (len(point["components"]) == 2)
    assert "formal_diff_fn-3i-010_2" not in e23["rows"]
    # These verified products are not a license to invent the still-missing
    # vanishing-forced directions or clip high-filtration classes. The actual
    # Tate-cycle contradiction blocks d23 and retains its source and target
    # families, rather than the old assumed-d23 window count of 34.
    # CD1 d11 removes one more finite direction in this fixed window.
    assert e24["high"] == e23["high"] == 53  # finite window, not a global bound
    assert set(e24["highPatterns"]) == {"S11", "S02", "S73", "S40", "S62"}
    # The AD6 constants remain: their historical d19 targets already support
    # CD1 d11. They are not the separate AD2 block with its verified d19.
    # Check all four occurrences in this window, not just the pattern name.
    retained_ad6 = {
        (point["grade"]["stem"], point["grade"]["filtration"], tuple(point["ports"]))
        for point in e24["highPatterns"]["S62"]
    }
    assert retained_ad6 == {((46 + 20 * g) % 64, 2 + 4 * g, ("0:0",)) for g in range(6, 10)}
    for stem, filtration, _ in retained_ad6:
        assert any(conflict["id"] == "formal_diff_fn-3i-010_1"
                   and conflict["page"] == 19
                   and conflict["reason"] == "source or target port absent on this page"
                   and (conflict["source"]["stem"], conflict["source"]["filtration"]) == (stem, filtration)
                   and (conflict["target"]["stem"], conflict["target"]["filtration"]) == (stem - 1, filtration + 19)
                   for conflict in e24["conflicts"] if "id" in conflict)
    assert e24["highPatterns"] == e23["highPatterns"]
    assert e24["probes"] == e23["probes"] == e10["probes"]
    assert e24["vectorProbes"] == e23["vectorProbes"] == e10["vectorProbes"]
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    assert all(d.status == "verified" for d in ws.differentials if d.label.startswith("DER-3I-D9"))


@pytest.mark.parametrize("units", [pair for pair in itertools.product((1, 2, 3), repeat=2)
                                  if pair != (1, 1)])
def test_nonunit_pure_assignments_block_instead_of_producing_a_false_quotient(project, units):
    pages = runtime(project, units)
    for page in pages[1:]:
        assert page["blockedFromPage"] == 9
        assert any(c["reason"] == "conflicting assignments for the same coefficient parameter"
                   for c in page["conflicts"])
    assert pages[-1]["high"] > 0
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    assert not ws.settings.get("coefficient_assignments")
