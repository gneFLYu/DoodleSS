"""An isolated unknown F4 unit determines a finite image, not a scalar value."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain.fate import _isolated_rank_one_unit, class_is_live_on_page, derive_class_fate, sync_workspace_fates
from domain.models import ClassNode, Differential, Grade, Proposition, Workspace


def fixture():
    workspace = Workspace("mix", "Mixed", spectral_sequence="hfpss")
    representation = {"sigma_i": -1, "sigma_j": -2}
    source = ClassNode("s", "VD3", Grade(24, 2, representation),
                       style={"e2_pattern": "S02", "two_valuation": 0, "j_order": 0})
    target = ClassNode("t", "Rk4D5", Grade(23, 19, representation),
                       style={"e2_pattern": "S73", "two_valuation": 0, "j_order": 0})
    workspace.classes = [source, target]
    arrow = Differential("d17", "s", "t", 17, status="verified", proposition_id="claim", period_stem=64)
    claim = Proposition("claim", "differential", "Nonzero finite map", status="verified", conclusion={
        "source_id": "s", "target_id": "t", "page": 17, "coefficient_scope": "exact-port",
        "coefficient_parameter": {"id": "lambda17", "value": None, "domain": [1, 2, 3], "frobenius_power": 0},
        "rank_one_unit_certificate": {"status": "verified", "kind": "isolated-finite-F4-isomorphism",
                                      "page": 17, "source_pattern": "S02", "target_pattern": "S73",
                                      "coefficient_scope": "exact-port"},
    })
    workspace.differentials = [arrow]
    workspace.propositions = [claim]
    return workspace, arrow, claim, source, target


def assert_unresolved(workspace, arrow):
    assert not _isolated_rank_one_unit(workspace, arrow)
    sync_workspace_fates(workspace)
    for ident in (arrow.source_id, arrow.target_id):
        assert derive_class_fate(workspace, ident).first_hfpss_death is None


def add_other(workspace, node, *, stem=0, filtration=0, pattern=None, period=64, page=17):
    shared = deepcopy(node)
    shared.id = "other-s"
    shared.grade = Grade(node.grade.stem + stem, node.grade.filtration + filtration, dict(node.grade.representation))
    if pattern:
        shared.style = {"e2_pattern": pattern}
    target = ClassNode("other-t", "Other", Grade(shared.grade.stem - 1, shared.grade.filtration + page,
                                                 dict(shared.grade.representation)), style={"e2_pattern": "unrelated"})
    workspace.classes += [shared, target]
    arrow = Differential("other", shared.id, target.id, page, status="verified", period_stem=period,
                         proposition_id="other-claim")
    claim = Proposition("other-claim", "differential", "Other map", status="verified",
                        conclusion={"source_id": shared.id, "target_id": target.id, "page": page})
    workspace.differentials.append(arrow)
    workspace.propositions.append(claim)
    return arrow, claim


@pytest.mark.parametrize("power", [0, 1])
def test_unknown_nonzero_unit_has_same_finite_fate_without_an_assignment(power):
    workspace, arrow, claim, _, _ = fixture()
    claim.conclusion["coefficient_parameter"]["frobenius_power"] = power
    original = deepcopy(claim.conclusion)
    assert _isolated_rank_one_unit(workspace, arrow)
    sync_workspace_fates(workspace)
    history = [asdict(event) for event in workspace.differential_events]
    for ident, role in (("s", "supports"), ("t", "receives")):
        assert class_is_live_on_page(workspace, ident, 17)
        assert not class_is_live_on_page(workspace, ident, 18)
        assert derive_class_fate(workspace, ident).first_hfpss_death == {
            "page": 17, "role": role, "claim_id": arrow.id}
    assert claim.conclusion == original
    assert "coefficient_assignments" not in workspace.settings
    sync_workspace_fates(workspace)
    assert [asdict(event) for event in workspace.differential_events] == history


@pytest.mark.parametrize("key,value", [("status", "review"), ("kind", "rank-one"), ("page", 9),
                                       ("coefficient_scope", "all-multiples"), ("source_pattern", "S11"),
                                       ("target_pattern", "S73V")])
def test_certificate_must_be_exact(key, value):
    workspace, arrow, claim, _, _ = fixture()
    claim.conclusion["rank_one_unit_certificate"][key] = value
    assert_unresolved(workspace, arrow)


@pytest.mark.parametrize("on_claim", [False, True])
def test_both_current_claim_and_arrow_must_be_accepted(on_claim):
    workspace, arrow, claim, _, _ = fixture()
    (claim if on_claim else arrow).status = "review"
    assert_unresolved(workspace, arrow)


@pytest.mark.parametrize("change", [
    {"two_valuation": 1}, {"j_order": 1}, {"e2_pattern": "S11"},
    {"e2_components": {"S02": 1}}, {"e2_components": {"S02": 1, "S73": 2}},
    {"e2_basis_patterns": ["S02"]},
])
def test_witt_series_and_explicit_vector_ports_are_not_shortcut(change):
    workspace, arrow, _, source, _ = fixture()
    source.style.update(change)
    assert_unresolved(workspace, arrow)


@pytest.mark.parametrize("field,value", [("cell_id", "cell"), ("coordinates", ["1"]), ("archived", True), ("page", 18)])
def test_non_native_or_unavailable_endpoints_are_rejected(field, value):
    workspace, arrow, _, source, _ = fixture()
    setattr(source, field, value)
    assert_unresolved(workspace, arrow)


def test_pattern_name_does_not_certify_an_impossible_filtration_zero_cell():
    workspace, arrow, _, source, target = fixture()
    source.grade.filtration = 0
    target.grade.filtration = 17
    assert_unresolved(workspace, arrow)


@pytest.mark.parametrize("extra", [{"affine_offset": 0}, {"target_component": "S73"},
                                    {"inverse_parameter_id": "b"}, {"source_parameter": {}},
                                    {"domain": [0, 1]}, {"frobenius_power": True}])
def test_no_affine_component_inverse_link_or_invalid_unit_domain(extra):
    workspace, arrow, claim, _, _ = fixture()
    claim.conclusion["coefficient_parameter"].update(extra)
    assert_unresolved(workspace, arrow)


@pytest.mark.parametrize("kind", ["condition", "constraint", "inverse", "duplicate", "bad-assignment", "matrix"])
def test_coupled_or_invalid_parameter_metadata_is_not_promoted(kind):
    workspace, arrow, claim, _, _ = fixture()
    if kind == "condition":
        claim.conclusion["coefficient_condition"] = {"parameter_id": "c", "equals": 1, "otherwise": "zero-euler-image"}
    elif kind == "constraint":
        claim.conclusion["coefficient_constraints"] = [{"parameter_ids": ["lambda17", "b"]}]
    elif kind == "inverse":
        workspace.propositions.append(Proposition("inverse", "differential", "Inverse", conclusion={
            "coefficient_parameter": {"id": "c", "inverse_parameter_id": "lambda17"}}))
    elif kind == "duplicate":
        other = deepcopy(claim)
        other.id = "duplicate"
        workspace.propositions.append(other)
    elif kind == "bad-assignment":
        workspace.settings["coefficient_assignments"] = {"lambda17": 0}
    else:
        arrow.linear_map_id = "matrix"
    assert_unresolved(workspace, arrow)


@pytest.mark.parametrize("endpoint", [0, 1])
@pytest.mark.parametrize("shift", [(0, 0, 64), (64, 0, 64), (-64, 0, 64), (20, 4, 64), (-20, -4, 64),
                                  (32, 0, 32)])
def test_other_arrow_periodic_source_or_target_incidence_blocks_shortcut(endpoint, shift):
    workspace, arrow, _, source, target = fixture()
    stem, filtration, period = shift
    add_other(workspace, (source, target)[endpoint], stem=stem, filtration=filtration, period=period)
    assert_unresolved(workspace, arrow)


def test_unrelated_residue_and_unrelated_basis_do_not_prevent_admission():
    for extra in ({"stem": 32}, {"pattern": "S53"}):
        workspace, arrow, _, source, _ = fixture()
        add_other(workspace, source, **extra)
        assert _isolated_rank_one_unit(workspace, arrow)
        sync_workspace_fates(workspace)
        assert not class_is_live_on_page(workspace, source.id, 18)


def test_implicit_vector_family_can_couple_an_otherwise_singleton_port():
    workspace, arrow, _, source, _ = fixture()
    vector = deepcopy(source)
    vector.id = "diagonal"
    vector.style = {"e2_components": {"S02": 1, "other": 2}}
    workspace.classes.append(vector)
    assert_unresolved(workspace, arrow)


def test_zero_outgoing_conflict_still_blocks_unit_invariant_events():
    workspace, arrow, _, _, _ = fixture()
    workspace.propositions.append(Proposition("zero", "zero-differential", "Zero outgoing", status="verified",
        conclusion={"source_id": "s", "page": 17, "coefficient_scope": "exact-port"}))
    sync_workspace_fates(workspace)
    assert derive_class_fate(workspace, "s").conclusion == "unresolved"
    assert derive_class_fate(workspace, "t").first_hfpss_death is None
    assert len(workspace.differential_events) == 2


def test_incoming_cycle_certificate_does_not_block_a_verified_nonzero_map():
    workspace, _, _, _, _ = fixture()
    workspace.propositions.append(Proposition("target-cycle", "permanent-cycle", "Zero outgoing", status="verified",
        conclusion={"source_id": "t", "page": 2, "coefficient_scope": "exact-port"}))
    sync_workspace_fates(workspace)
    assert derive_class_fate(workspace, "t").conclusion == "is_hit"


def test_prior_accepted_incidence_does_not_authorize_a_late_image():
    workspace, arrow, _, source, _ = fixture()
    add_other(workspace, source, page=3)
    assert_unresolved(workspace, arrow)


def test_removing_certificate_rechecks_cached_fate_without_rewriting_history():
    workspace, _, claim, _, _ = fixture()
    sync_workspace_fates(workspace)
    history = deepcopy(workspace.differential_events)
    assert not class_is_live_on_page(workspace, "s", 18)
    claim.conclusion.pop("rank_one_unit_certificate")
    assert class_is_live_on_page(workspace, "s", 18)
    assert workspace.differential_events == history
