"""Preserve withdrawn January 29 proofs without admitting their conclusions.

The source's candidate xh1^2 D^4 u_2sigma is in (33,3), not the (1,3)
residue killed by FN-2I-020. This audit records a proof issue, not a replacement
for the printed d19/d23 formulas and not an assertion that they are false.
Fixing pure-sector F4 units by Galois symmetry does not repair these proofs.
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
from domain.fate import is_accepted, sync_project_fates
from domain.formal_notes_chart import ensure_formal_notes_chart
from domain.migrations import migrate_project
from domain.seed import demo_project


CONFLICT_KIND = "euler-preimage-exclusion-conflicts-with-recorded-product"
ROW_IDS = ("formal_diff_fn-3i-010_1", "formal_diff_fn-3i-010_2")
WITHDRAWN_ARTIFACTS = {
    "FN-3I-010": [
        "笔记 2026年1月29日 10_52_56.pdf, page 3 (D^5 block)",
        "笔记 2026年1月29日 11_21_30.pdf, pages 1-3 (D block)",
    ],
    "FN-3I-010-pc": ["笔记 2026年1月29日 10_52_56.pdf, pages 1-3"],
}


@pytest.fixture(scope="module")
def source_project():
    return migrate_project(demo_project())


def workspace(project, ident):
    return next(item for item in project.workspaces if item.id == ident)


def conflict_for(claim):
    return next(item for item in claim.conclusion.get("source_conflicts", [])
                if item.get("kind") == CONFLICT_KIND)


def assert_withdrawn_proof(claim):
    conclusion = claim.conclusion
    assert claim.status == conclusion["admission_status"] == "review"
    assert not is_accepted(claim.status)
    assert conclusion["source_status"] == "withdrawn-proof"
    assert conclusion["printed_source_status"] == "source-proved"
    assert conclusion["source_artifacts"] == WITHDRAWN_ARTIFACTS[conclusion["fact_id"]]
    assert "User withdrew the Jan.29 handwritten proof" in conclusion["authority_decision"]
    assert "without asserting its negation or a replacement" in conclusion["authority_decision"]
    normalization = conclusion["coefficient_normalization"]
    assert normalization["id"] == "pure-sigma-i-galois-fixed"
    assert normalization["value"] == 1
    assert normalization["admission_independent"] is True


def test_printed_final_formulas_are_preserved_but_their_proof_issue_blocks_automatic_admission(source_project):
    ws = workspace(source_project, "ws_3sigma_i")
    claims = {item.id: item for item in ws.propositions}
    classes = {item.id: item for item in ws.classes}
    expected = {
        ROW_IDS[0]: (19, (14, 2), (13, 21)),
        ROW_IDS[1]: (23, (12, 0), (11, 23)),
    }
    for ident, (page, source_grade, target_grade) in expected.items():
        arrow = next(item for item in ws.differentials if item.id == ident)
        claim = claims[arrow.proposition_id]
        source, target = classes[arrow.source_id], classes[arrow.target_id]
        assert arrow.status == claim.status == "review"
        assert not is_accepted(arrow.status)
        assert arrow.page == page and arrow.period_stem == 32
        assert (source.grade.stem, source.grade.filtration) == source_grade
        assert (target.grade.stem, target.grade.filtration) == target_grade
        assert claim.conclusion["fact_id"] == "FN-3I-010"
        assert_withdrawn_proof(claim)
        conflict = conflict_for(claim)
        assert conflict["checked_identity"]
        assert "formal_notes.tex" in conflict["source_ref"]
        assert "770" in conflict["source_ref"]
        assert "833" in conflict["source_ref"] or "839" in conflict["source_ref"]
        assert "x^3*h2" in conflict["checked_identity"]
        assert "d23(A)=0" in conflict["conditional_family"]
        assert "nonzero on E14" in conflict["conditional_family"]
        assert "(29,5)->(28,16)" in conflict["conditional_correction"]
        assert "no replacement map is installed" in conflict["conditional_correction"]


def test_final_proof_conflict_is_preserved_on_every_three_sigma_atlas_image(source_project):
    source = workspace(source_project, "ws_3sigma_i")
    source_claims = {item.id: item for item in source.propositions}
    images = [item for item in source_project.workspaces
              if item.settings.get("atlas_transport", {}).get("source_workspace_id") == source.id]
    assert len(images) == 2
    for target in images:
        plan = target.settings["atlas_transport"]
        prefix = f"atlas_{plan['sector_id']}_"
        claims = {item.id: item for item in target.propositions}
        for ident in ROW_IDS:
            original = next(item for item in source.differentials if item.id == ident)
            image = next(item for item in target.differentials if item.id == prefix + ident)
            source_claim = source_claims[original.proposition_id]
            target_claim = claims[image.proposition_id]
            assert image.status == target_claim.status == "review"
            assert not is_accepted(image.status)
            assert_withdrawn_proof(target_claim)
            assert target_claim.conclusion["source_artifacts"] == source_claim.conclusion["source_artifacts"]
            assert target_claim.conclusion["authority_decision"] == source_claim.conclusion["authority_decision"]
            assert conflict_for(target_claim) == conflict_for(source_claim)
            assert target_claim.conclusion["atlas_transport"]["source_workspace_id"] == source.id


def test_euler_permanent_cycle_keeps_its_distinct_withdrawn_proof_and_restriction_conflict(source_project):
    sectors = [item for item in source_project.workspaces
               if item.id == "ws_3sigma_i"
               or item.settings.get("atlas_transport", {}).get("source_workspace_id") == "ws_3sigma_i"]
    assert len(sectors) == 3
    for ws in sectors:
        claim = next(item for item in ws.propositions
                     if item.conclusion.get("fact_id") == "FN-3I-010-pc")
        assert claim.kind == "permanent-cycle"
        assert_withdrawn_proof(claim)
        assert not [item for item in claim.conclusion.get("source_conflicts", [])
                    if item.get("kind") == CONFLICT_KIND]
        restriction = next(item for item in claim.conclusion.get("source_conflicts", [])
                           if item.get("kind") == "euler-restriction-uses-kernel-subgroup")
        assert "Res_C4<i>(3sigma_i)=3" in restriction["checked_identity"]
        assert "a_3=0" in restriction["checked_identity"]
        assert "main.tex:515-520" in restriction["source_ref"]
        assert "C4<j>" in restriction["conditional_correction"]
        assert claim.conclusion["source_blockers"]
        assert claim.conclusion["machine_verification_pending"]
        assert not is_accepted(claim.status)


def test_galois_normalization_and_refresh_cannot_readmit_withdrawn_january_claims(source_project):
    candidate = deepcopy(source_project)
    source = workspace(candidate, "ws_3sigma_i")
    originals = {
        claim.id: (claim.statement, claim.source_ref, deepcopy(claim.conclusion["source_conflicts"]))
        for claim in source.propositions
        if claim.conclusion.get("fact_id") in WITHDRAWN_ARTIFACTS
    }
    assert len(originals) == 3
    # Model a persisted project that still carries the old admission. The
    # authority withdrawal, not the coefficient normalization, must win.
    for claim in source.propositions:
        if claim.id in originals:
            claim.status = "admitted"
            claim.conclusion["admission_status"] = "admitted"
    for arrow in source.differentials:
        if arrow.id in ROW_IDS:
            arrow.status = "admitted"
    ensure_formal_notes_chart(candidate)
    ensure_q8_atlas_transports(candidate)
    sync_project_fates(candidate)
    sectors = [item for item in candidate.workspaces
               if item.id == source.id
               or item.settings.get("atlas_transport", {}).get("source_workspace_id") == source.id]
    assert len(sectors) == 3
    for ws in sectors:
        claims = {claim.id: claim for claim in ws.propositions
                  if claim.conclusion.get("fact_id") in WITHDRAWN_ARTIFACTS}
        assert len(claims) == 3
        for claim in claims.values():
            assert_withdrawn_proof(claim)
        arrows = [arrow for arrow in ws.differentials if arrow.proposition_id in claims]
        assert len(arrows) == 2
        assert all(arrow.status == "review" and not is_accepted(arrow.status) for arrow in arrows)
        events = [event for event in ws.differential_events
                  if event.differential_claim_id in {arrow.id for arrow in arrows}]
        # Review events preserve the original evidence; none may act as an
        # accepted death or differential after the authority withdrawal.
        assert all(event.status == "review" and not is_accepted(event.status) for event in events)
    for claim in source.propositions:
        if claim.id in originals:
            assert (claim.statement, claim.source_ref, claim.conclusion["source_conflicts"]) == originals[claim.id]
    # All changes above are confined to the hypothesis copy.
    for claim in workspace(source_project, source.id).propositions:
        if claim.id in originals:
            assert_withdrawn_proof(claim)


def test_conditional_two_sigma_quotient_does_not_kill_the_other_d4_residue(source_project):
    original = workspace(source_project, "ws_2sigma_i")
    original_statuses = (
        [(item.id, item.status) for item in original.differentials],
        [(item.id, item.status) for item in original.propositions],
    )
    candidate = deepcopy(source_project)
    ws = workspace(candidate, original.id)
    # These are explicit test-only premises, exactly as in the convergence
    # audit; the documented missing-j FN-2I-002 remains unadmitted.
    for arrow in ws.differentials:
        if arrow.label.startswith("FN-") and arrow.label != "FN-2I-002":
            arrow.status = "admitted"
    for claim in ws.propositions:
        fact = claim.conclusion.get("fact_id", "")
        if fact.startswith("FN-") and fact != "FN-2I-002":
            claim.status = "admitted"
    payload = {
        "project": asdict(candidate), "workspaces": [ws.id], "pages": [21, 22, 24],
        "bounds": {"stemMin": 0, "stemMax": 63, "filtrationMin": 0, "filtrationMax": 40},
        "vectorAudit": True, "auditNoClipping": True,
        "probes": [{"pattern": "I13", "stem": stem, "filtration": 3} for stem in (1, 33)],
    }
    completed = subprocess.run(
        ["node", "tests/chart_runtime.cjs"], cwd=ROOT, input=json.dumps(payload),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=60,
    )
    pages = json.loads(completed.stdout)[0]["pages"]
    assert [page["page"] for page in pages] == [21, 22, 24]
    for page in pages:
        assert not page["conflicts"]
        probes = {probe["stem"]: probe["ports"] for probe in page["probes"]}
        assert probes[1] == (["0:0"] if page["page"] == 21 else [])
        assert probes[33] == ["0:0"]
    assert original_statuses == (
        [(item.id, item.status) for item in original.differentials],
        [(item.id, item.status) for item in original.propositions],
    )
    original_row = next(item for item in original.differentials if item.label == "FN-2I-020")
    assert original_row.status == "verified"
    original_claim = next(item for item in original.propositions if item.id == original_row.proposition_id)
    assert original_claim.conclusion["verification_certificate"]["method"] == "Published d23 product and finite E21 quotient"
