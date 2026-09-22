"""A verified nonzero-b premise does not choose b or admit its d5 rows."""
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.fate import is_accepted
from domain.migrations import migrate_project
from domain.seed import demo_project


SOURCE = "ws_sigma_i_2sigma_j"
FACT = "FN-MIX-005"
CERTIFICATE = "DER-MIX-D5-B-NONZERO"
CYCLE_PREMISE = "DER-MIX-EULER-H2-cycle"
PARAMETER = "mixed_d5_B"
ATLAS = {
    SOURCE: (False, 0),
    "ws_q8-ro-a1-b3": (False, -16),
    "ws_q8-ro-a2-b1": (True, 0),
    "ws_q8-ro-a2-b3": (False, -32),
    "ws_q8-ro-a3-b1": (True, -16),
    "ws_q8-ro-a3-b2": (True, -32),
}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def claims(workspace):
    result = [claim for claim in workspace.propositions if claim.conclusion.get("fact_id") == FACT]
    assert len(result) == 2
    return result


def certificate(claim):
    result = claim.conclusion["nonzero_parameter_certificate"]
    assert result["id"] == CERTIFICATE and result["status"] == "verified"
    assert result["scope"] == "source-workspace"
    assert result["source_workspace_id"] == SOURCE
    assert result["parameter_id"] == PARAMETER
    assert result["domain"] == [1, 2, 3] and result["value"] is None
    assert CYCLE_PREMISE in result["premises"]
    return result


def test_nonzero_proof_retains_the_full_f4_target_choice(project):
    source = next(workspace for workspace in project.workspaces if workspace.id == SOURCE)
    for claim in claims(source):
        proof = certificate(claim)
        target = proof["target_space"]
        assert target["bidegree"] == [-2, 6]
        assert target["basis"] == ["kP", "kQ"]
        assert target["general_map"] == "k(alpha P+beta Q)"
        assert target["alpha"] == 0
        assert target["alpha_exclusion"] and target["completed_ideal"]
        assert proof["source_refs"] and not proof["withdrawn_premises_used"]
        # Excluding zero is different from selecting one of the three F4 units.
        assert proof["domain"] == [1, 2, 3] and proof["value"] is None
        parameter = claim.conclusion["coefficient_parameter"]
        assert parameter["id"] == PARAMETER
        assert parameter["domain"] == [1, 2, 3] and parameter["value"] is None
        assert "coefficient_normalization" not in claim.conclusion


def test_counterfactual_has_a_complete_finite_incoming_inventory(project):
    source = next(workspace for workspace in project.workspaces if workspace.id == SOURCE)
    for claim in claims(source):
        proof = certificate(claim)
        counterfactual = proof["counterfactual"]
        assert counterfactual["b"] == 0
        assert counterfactual["target_bidegree"] == [15, 11]
        assert counterfactual["B_survival"] and counterfactual["W_outgoing"] and counterfactual["contradiction"]
        inventory = proof["incoming_inventory"]
        # W is required on E9: later incoming d9/d11 maps are not excluded by this proof.
        assert len(inventory) == 3
        assert {row["page"] for row in inventory} == {3, 5, 7}
        assert "parity" in proof["even_pages"].lower()
        for row in inventory:
            assert row["source_bidegree"] == [16, 11 - row["page"]]
            assert isinstance(row["disposition"], str) and row["disposition"].strip()


@pytest.mark.parametrize("workspace_id", ATLAS)
def test_all_six_atlas_images_preserve_provenance_without_fixing_b(project, workspace_id):
    images = [workspace for workspace in project.workspaces if workspace.id == SOURCE or
              workspace.settings.get("atlas_transport", {}).get("source_workspace_id") == SOURCE]
    assert {workspace.id for workspace in images} == set(ATLAS)
    source = next(workspace for workspace in images if workspace.id == SOURCE)
    source_claims = {claim.id: claim for claim in claims(source)}
    workspace = next(workspace for workspace in images if workspace.id == workspace_id)
    reflected, shift = ATLAS[workspace_id]
    plan = workspace.settings.get("atlas_transport", {})
    assert bool(plan.get("reflected", False)) == reflected
    assert plan.get("stem_shift", 0) == shift
    assert PARAMETER not in workspace.settings.get("coefficient_assignments", {})
    nodes = {node.id: node for node in workspace.classes}
    actual_sources = set()
    for claim in claims(workspace):
        proof = certificate(claim)
        row = next(row for row in workspace.differentials if row.proposition_id == claim.id)
        assert row.status == claim.status == "review"
        assert not is_accepted(row.status) and not is_accepted(claim.status)
        assert row.page == 5 and row.period_stem == 16
        parameter = claim.conclusion["coefficient_parameter"]
        assert parameter["id"] == PARAMETER
        assert parameter["domain"] == [1, 2, 3] and parameter["value"] is None
        assert parameter["frobenius_power"] == int(reflected)
        assert "coefficient_normalization" not in claim.conclusion
        source_node = nodes[row.source_id]
        actual_sources.add((source_node.grade.stem, source_node.grade.filtration))
        if source_node.grade.stem == shift + 7:
            assert parameter["target_component"] == "S22H"
        else:
            assert "target_component" not in parameter
        if workspace_id != SOURCE:
            transport = claim.conclusion["atlas_transport"]
            assert transport["source_workspace_id"] == SOURCE
            source_claim = source_claims[transport["source_proposition_id"]]
            # The proof lives in its source coordinates.  Atlas/Frobenius
            # metadata is separate and must not rewrite its finite inventory.
            assert proof == certificate(source_claim)
    assert actual_sources == {(7 + shift, 1), (15 + shift, 1)}
