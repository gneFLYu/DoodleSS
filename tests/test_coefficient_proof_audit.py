"""Read-only coefficient evidence is separate from the historical fact ledger."""
from copy import deepcopy
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.migrations import migrate_project
from domain.seed import demo_project
from domain.undecided_differential_audit import audit_undecided_differentials


MIXED = "ws_sigma_i_2sigma_j"
PARAMETER = "mixed_d5_A"
PROOF = "coefficient_proof_mixed_d5_A"
REMAINING = {
    "mixed_d5_B", "mixed_d17_VD3", "mixed_d19_XD4",
    "mixed_d11_R_D2", "mixed_d11_R_D6", "mixed_d19_R_D5",
}
MIXED_IMAGES = {
    MIXED, "ws_q8-ro-a1-b3", "ws_q8-ro-a2-b1", "ws_q8-ro-a2-b3",
    "ws_q8-ro-a3-b1", "ws_q8-ro-a3-b2",
}


@pytest.fixture(scope="module")
def canonical_project():
    project = demo_project()
    # A default value is deliberately present: resolution must not be reported
    # as a numerical proof merely because the document profile selected one.
    project.research_brief["document_baseline"] = True
    return migrate_project(project)


def parameters(report, workspace_id=MIXED):
    record = next(w for w in report["coefficient_evidence"]["runtime_workspaces"]
                  if w["workspace_id"] == workspace_id)
    return {p["parameter_id"]: p for p in record["parameters"]}


def historical(report):
    return {key: value for key, value in report.items() if key != "coefficient_evidence"}


def withdrawn_project(project):
    copied = deepcopy(project)
    workspace = next(w for w in copied.workspaces if w.id == MIXED)
    next(p for p in workspace.propositions if p.id == PROOF).status = "review"
    for claim in workspace.propositions:
        spec = claim.conclusion.get("coefficient_parameter")
        if isinstance(spec, dict) and spec.get("id") == PARAMETER:
            spec["value"] = 3
    workspace.settings["coefficient_assignments"] = {PARAMETER: 3}
    return copied


def assert_six_separate_units(report):
    evidence = report["coefficient_evidence"]
    units = evidence["remaining_numeric_units"]
    assert evidence["remaining_numeric_unit_count"] == len(units) == 6
    assert {p["parameter_id"] for p in units} == REMAINING
    assert PARAMETER not in REMAINING
    assert all(p["numeric_status"] == "unresolved" and p["value"] is None for p in units)
    by_id = {p["parameter_id"]: p for p in units}
    assert by_id["mixed_d11_R_D2"]["source_D_residue_mod_8"] == 2
    assert by_id["mixed_d11_R_D6"]["source_D_residue_mod_8"] == 6


def test_source_only_audit_does_not_claim_to_have_inspected_a_runtime_project():
    report = audit_undecided_differentials()
    assert_six_separate_units(report)
    evidence = report["coefficient_evidence"]
    assert evidence["runtime_project_inspected"] is False
    assert evidence["runtime_workspaces"] == []
    assert evidence["source_coefficient_audit"]["source_value"] == 3
    assert report["obligations"]


def test_live_six_atlas_proof_values_are_separate_from_document_defaults(canonical_project):
    report = audit_undecided_differentials(project=canonical_project)
    assert_six_separate_units(report)
    evidence = report["coefficient_evidence"]
    assert evidence["runtime_project_inspected"] is True
    assert {w["workspace_id"] for w in evidence["runtime_workspaces"]} == MIXED_IMAGES
    for workspace_id in MIXED_IMAGES:
        records = parameters(report, workspace_id)
        assert set(records) == REMAINING | {PARAMETER}
        current = records[PARAMETER]
        assert current["resolution"]["resolved"] is True
        assert current["resolution"]["value"] == 3
        assert current["resolution"]["proof_bound"] is True
        assert current["numeric_proof_status"] == "proved-current"
        for ident in REMAINING:
            record = records[ident]
            assert record["numeric_proof_status"] == "not-numerically-proved", (workspace_id, ident)
            assert record["document_default"]["value"] == 1
            assert record["document_default"]["status"] == "document-adopted-only"
    # The b value is actually selected by the profile, yet remains unproved.
    b = parameters(report)["mixed_d5_B"]
    assert b["resolution"]["resolved"] is True and b["resolution"]["value"] == 1
    assert b["resolution"]["proof_bound"] is False


def test_withdrawn_proof_is_unresolved_despite_three_in_raw_fields_and_settings(canonical_project):
    before = audit_undecided_differentials(project=canonical_project)
    copied = withdrawn_project(canonical_project)
    after = audit_undecided_differentials(project=copied)
    assert historical(after) == historical(before)
    assert after["coefficient_evidence"]["source_coefficient_audit"] == before["coefficient_evidence"]["source_coefficient_audit"]
    assert_six_separate_units(after)
    for workspace_id in MIXED_IMAGES:
        current = parameters(after, workspace_id)[PARAMETER]
        assert current["resolution"]["resolved"] is False
        assert current["resolution"]["proof_bound"] is True
        assert "value" not in current["resolution"] or current["resolution"]["value"] is None
        assert current["numeric_proof_status"] == "unresolved-proof"


def test_audit_is_observational_and_does_not_migrate_or_change_the_input(canonical_project):
    copied = withdrawn_project(canonical_project)
    before = asdict(copied)
    audit_undecided_differentials(project=copied)
    audit_undecided_differentials(project=copied, workspace_id=MIXED)
    assert asdict(copied) == before


@pytest.mark.parametrize("workspace_id", [MIXED, "ws_q8-ro-a2-b1", "missing-workspace"])
def test_workspace_filter_applies_to_runtime_records_and_historical_occurrences(canonical_project, workspace_id):
    report = audit_undecided_differentials(project=canonical_project, workspace_id=workspace_id)
    assert report["workspace_filter"] == workspace_id
    expected = [] if workspace_id == "missing-workspace" else [workspace_id]
    assert [w["workspace_id"] for w in report["coefficient_evidence"]["runtime_workspaces"]] == expected
    assert all(row["workspace_id"] == workspace_id
               for obligation in report["obligations"] for row in obligation["occurrences"])
    assert_six_separate_units(report)


def test_cli_reads_a_unicode_project_without_migration_or_file_changes(canonical_project, tmp_path):
    copied = withdrawn_project(canonical_project)
    path = tmp_path / "撤回证明-project.json"
    path.write_text(json.dumps(asdict(copied), ensure_ascii=False), encoding="utf-8")
    before = path.read_bytes()
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    completed = subprocess.run(
        [sys.executable, str(ROOT / "backend" / "audit_undecided_differentials.py"),
         "--project", str(path), "--workspace", MIXED, "--json"],
        cwd=ROOT, env=environment, capture_output=True, text=True,
        encoding="utf-8", check=True, timeout=60,
    )
    report = json.loads(completed.stdout)
    assert path.read_bytes() == before
    assert report == audit_undecided_differentials(project=copied, workspace_id=MIXED)
    assert_six_separate_units(report)
    current = parameters(report)[PARAMETER]
    assert current["resolution"]["resolved"] is False
    assert current["resolution"]["proof_bound"] is True
    assert current["numeric_proof_status"] == "unresolved-proof"
    assert report["coefficient_evidence"]["runtime_project_inspected"] is True
    assert historical(report) == historical(audit_undecided_differentials(workspace_id=MIXED))
