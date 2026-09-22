"""A cross-grading coefficient is a live source-field reference, not a copied unit."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain.fate import (
    _linked_source_parameter,
    class_is_live_on_page,
    derive_class_fate,
    sync_project_fates,
    sync_workspace_fates,
)
from domain.models import (
    ClassNode, DifferentialMap, Grade, GradingSector, PagePeriodCycle,
    PeriodicityRule, Project, Proposition, Workspace,
)
from test_parameterized_fate import add_arrow, parameter


def linked_fixture(unit=2, power=0, offset=0):
    source = Workspace("source", "Source coefficient", spectral_sequence="hfpss")
    # The link must not read this source arrow's conjugated coefficient.
    original, original_claim = add_arrow(source, "source-d9", page=9,
                                         spec=parameter("gamma", frobenius_power=1))
    source.settings["coefficient_assignments"] = {"gamma": unit}
    target = Workspace("target", "Euler or psi image", spectral_sequence="hfpss")
    spec = parameter("gamma", frobenius_power=power, affine_offset=offset, source_parameter={
        "workspace_id": source.id, "parameter_id": "gamma", "differential_id": original.id, "page": 9,
    })
    image, image_claim = add_arrow(target, "image-d11", page=11, spec=spec)
    # Target-first ordering must not need a global hidden "current project".
    project = Project("linked", "Linked coefficients", [target, source])
    return project, source, original, original_claim, target, image, image_claim


def resolved(project, target):
    declarations = [claim.conclusion.get("coefficient_parameter") for claim in target.propositions]
    declarations = [spec for spec in declarations if isinstance(spec, dict) and spec.get("id") == "gamma"]
    return _linked_source_parameter(target, "gamma", declarations, project=project)


def assert_liveness(project, target, arrow, expected):
    for ident in (arrow.source_id, arrow.target_id):
        assert class_is_live_on_page(target, ident, arrow.page + 1, project=project) is expected
        assert (derive_class_fate(target, ident, project=project).first_hfpss_death is None) is expected


def test_every_raw_unit_is_read_before_target_affine_and_frobenius_operations():
    for unit in (1, 2, 3):
        for power in (0, 1):
            for offset in (0, unit):
                project, source, _, source_claim, target, image, image_claim = linked_fixture(unit, power, offset)
                source_snapshot = deepcopy(source_claim.conclusion)
                image_snapshot = deepcopy(image_claim.conclusion)
                assert sync_project_fates(project) is project
                assert resolved(project, target) == {"resolved": True, "id": "gamma", "value": unit}
                assert_liveness(project, target, image, offset == unit)
                assert source.settings["coefficient_assignments"] == {"gamma": unit}
                assert not target.settings.get("coefficient_assignments")
                assert source_claim.conclusion == source_snapshot
                assert image_claim.conclusion == image_snapshot


def test_ratio_uses_the_linked_raw_unit_before_the_target_psi_action():
    for unit in (1, 2, 3):
        for denominator in (1, 2, 3):
            for power in (0, 1):
                project, _, _, _, target, image, claim = linked_fixture(unit, power)
                claim.conclusion["coefficient_parameter"].update(
                    inverse_parameter_id="b", target_component="Q")
                target.propositions.append(Proposition("denominator", "coefficient", "b", conclusion={
                    "coefficient_parameter": parameter("b", denominator),
                }))
                endpoint = next(node for node in target.classes if node.id == image.target_id)
                endpoint.style = {"e2_components": {"P": 1, "Q": 1}, "e2_basis_patterns": ["P", "Q"]}
                sync_project_fates(project)
                assert not class_is_live_on_page(target, image.source_id, 12, project=project)
                # P+(gamma/b)Q is the recorded P+Q line exactly when gamma=b;
                # Frobenius preserves this equality, not the separate raw units.
                assert class_is_live_on_page(target, image.target_id, 12, project=project) is (unit != denominator)


def test_workspace_only_calls_are_conservative_even_after_project_sync_cached_a_death():
    project, _, _, _, target, image, _ = linked_fixture()
    sync_project_fates(project)
    assert_liveness(project, target, image, False)
    assert_liveness(None, target, image, True)
    assert resolved(None, target)["reason"] == "linked coefficient requires project context"
    sync_workspace_fates(target)
    assert all(fate.first_hfpss_death is None for fate in target.fates)
    sync_workspace_fates(target, project=project)
    assert_liveness(project, target, image, False)


def test_source_assignment_changes_and_removals_recheck_existing_events_without_rewriting_history():
    project, source, _, _, target, image, _ = linked_fixture(offset=2, power=1)
    sync_project_fates(project)
    history = deepcopy(target.differential_events)
    for value, live in ((2, True), (3, False), (None, True), (1, False), (0, True)):
        source.settings["coefficient_assignments"]["gamma"] = value
        assert_liveness(project, target, image, live)
        sync_workspace_fates(target, project=project)
        assert target.differential_events == history
    del source.settings["coefficient_assignments"]["gamma"]
    assert_liveness(project, target, image, True)
    assert target.differential_events == history


@pytest.mark.parametrize("case,reason", [
    ("workspace", "source workspace is missing or ambiguous"),
    ("duplicate-workspace", "source workspace is missing or ambiguous"),
    ("arrow", "source differential is missing or ambiguous"),
    ("duplicate-arrow", "source differential is missing or ambiguous"),
    ("page", "source differential page does not match"),
    ("review", "source differential is not accepted"),
    ("claim-review", "source proposition is not accepted"),
    ("claim", "source differential parameter does not match"),
    ("parameter", "source differential parameter does not match"),
    ("unassigned", "source parameter is unresolved"),
    ("zero", "source assignment is invalid"),
    ("boolean", "source assignment is invalid"),
    ("malformed", "source assignment is invalid"),
    ("conflict", "source assignments conflict"),
    ("review-declaration-conflict", "source assignments conflict"),
    ("domain", "source assignment is outside its domain"),
    ("nested", "nested source bindings are unsupported"),
    ("target-value", "cannot have a local assignment"),
    ("target-assignment", "cannot have a local assignment"),
    ("target-unlinked-declaration", "declarations have mismatched source bindings"),
    ("target-different-binding", "declarations have mismatched source bindings"),
    ("binding-id", "parameter id does not match its source binding"),
    ("binding-null", "declarations have mismatched source bindings"),
    ("binding-page-bool", "source binding is invalid"),
    ("binding-page-infinite", "source binding is invalid"),
])
def test_bad_or_stale_link_blocks_current_and_later_parameterized_deaths(case, reason):
    project, source, original, source_claim, target, image, image_claim = linked_fixture()
    later, _ = add_arrow(target, "later", page=17, spec=parameter("later", 1))
    sync_project_fates(project)
    history = deepcopy(target.differential_events)
    spec = source_claim.conclusion["coefficient_parameter"]
    target_spec = image_claim.conclusion["coefficient_parameter"]
    if case == "workspace":
        project.workspaces.remove(source)
    elif case == "duplicate-workspace":
        project.workspaces.append(deepcopy(source))
    elif case == "arrow":
        source.differentials.remove(original)
    elif case == "duplicate-arrow":
        source.differentials.append(deepcopy(original))
    elif case == "page":
        original.page = 11
    elif case == "review":
        original.status = "review"
    elif case == "claim-review":
        source_claim.status = "review"
    elif case == "claim":
        source.propositions.remove(source_claim)
    elif case == "parameter":
        spec["id"] = "different"
    elif case == "unassigned":
        source.settings["coefficient_assignments"].clear()
    elif case in ("zero", "boolean", "malformed"):
        source.settings["coefficient_assignments"]["gamma"] = {"zero": 0, "boolean": True, "malformed": {}}[case]
    elif case == "conflict":
        spec["value"] = 3
    elif case == "review-declaration-conflict":
        source.propositions.append(Proposition("other", "coefficient", "other", status="review",
            conclusion={"coefficient_parameter": parameter("gamma", 3)}))
    elif case == "domain":
        source.propositions.append(Proposition("other", "coefficient", "other", status="review",
            conclusion={"coefficient_parameter": parameter("gamma", domain=[1])}))
    elif case == "nested":
        spec["source_parameter"] = deepcopy(target_spec["source_parameter"])
    elif case == "target-value":
        target_spec["value"] = 2
    elif case == "target-assignment":
        target.settings["coefficient_assignments"] = {"gamma": 2}
    elif case == "target-unlinked-declaration":
        target.propositions.append(Proposition("other", "coefficient", "other",
            conclusion={"coefficient_parameter": parameter("gamma")}))
    elif case == "target-different-binding":
        other = deepcopy(target_spec)
        other["source_parameter"]["page"] = 11
        target.propositions.append(Proposition("other", "coefficient", "other",
            conclusion={"coefficient_parameter": other}))
    elif case == "binding-id":
        target_spec["source_parameter"]["parameter_id"] = "other"
    elif case == "binding-null":
        target_spec["source_parameter"] = None
    elif case == "binding-page-bool":
        target_spec["source_parameter"]["page"] = True
    elif case == "binding-page-infinite":
        target_spec["source_parameter"]["page"] = float("inf")
    assert resolved(project, target)["reason"] == "linked coefficient " + reason
    assert_liveness(project, target, image, True)
    assert_liveness(project, target, later, True)
    sync_workspace_fates(target, project=project)
    assert target.differential_events == history


def test_source_matrix_acceptance_archival_and_removal_are_live_requirements():
    project, source, original, _, target, image, _ = linked_fixture()
    original.linear_map_id = "source-matrix"
    matrix = DifferentialMap("source-matrix", None, None, 9, [["1"]], status="admitted")
    source.differential_maps.append(matrix)
    sync_project_fates(project)
    assert_liveness(project, target, image, False)
    for status, archived in (("review", False), ("admitted", True)):
        matrix.status, matrix.archived = status, archived
        assert resolved(project, target)["reason"] == "linked coefficient source linear map is not accepted"
        assert_liveness(project, target, image, True)
    matrix.status, matrix.archived = "admitted", False
    assert_liveness(project, target, image, False)
    source.differential_maps.clear()
    assert_liveness(project, target, image, True)


def test_linked_parameter_checks_source_constraints_with_exact_premise_page():
    project, source, _, source_claim, target, image, _ = linked_fixture()
    add_arrow(source, "other", page=9, spec=parameter("beta", 2))
    add_arrow(source, "d19", page=19, fact="source-final")
    premise, _ = add_arrow(source, "d23", page=23, fact="source-final")
    source_claim.conclusion["coefficient_constraints"] = [{
        "id": "compat", "kind": "equal-nonzero-parameters", "page": 9,
        "parameter_ids": ["gamma", "beta"], "normalization_value": 1,
        "required_facts": ["source-final"],
        "required_differentials": [{"fact_id": "source-final", "page": 23}],
    }]
    sync_project_fates(project)
    assert resolved(project, target)["reason"] == "linked coefficient source coefficient constraints conflict"
    assert_liveness(project, target, image, True)
    premise.status = "review"
    assert resolved(project, target)["value"] == 2
    assert_liveness(project, target, image, False)


def test_false_zero_euler_image_does_not_require_an_unused_link_but_later_maps_still_work():
    project, source, _, _, target, image, claim = linked_fixture()
    claim.conclusion["coefficient_condition"] = {
        "parameter_id": "c", "equals": 1, "otherwise": "zero-euler-image",
    }
    target.propositions.append(Proposition("condition", "coefficient", "c", conclusion={
        "coefficient_parameter": parameter("c", 2),
    }))
    later, _ = add_arrow(target, "later", page=17, spec=parameter("later", 1))
    project.workspaces.remove(source)
    sync_project_fates(project)
    assert_liveness(project, target, image, True)
    assert_liveness(project, target, later, False)


def test_linked_raw_unit_can_control_a_condition_without_local_assignment_or_extra_conjugation():
    project, source, _, _, target, image, claim = linked_fixture()
    binding = deepcopy(claim.conclusion["coefficient_parameter"])
    claim.conclusion["coefficient_parameter"] = parameter("other", 1)
    claim.conclusion["coefficient_condition"] = {
        "parameter_id": "gamma", "equals": 2, "otherwise": "zero-euler-image",
    }
    target.propositions.append(Proposition("linked-condition", "coefficient", "source gamma",
        conclusion={"coefficient_parameter": binding}))
    sync_project_fates(project)
    assert_liveness(project, target, image, False)
    source.settings["coefficient_assignments"]["gamma"] = 3
    assert_liveness(project, target, image, True)


def test_matching_linked_declarations_and_null_placeholders_do_not_copy_the_source_value():
    project, _, _, _, target, image, claim = linked_fixture()
    duplicate = deepcopy(claim.conclusion["coefficient_parameter"])
    duplicate["frobenius_power"] = 1
    target.propositions.append(Proposition("linked-again", "coefficient", "psi gamma",
        conclusion={"coefficient_parameter": duplicate}))
    target.settings["coefficient_assignments"] = {"gamma": None}
    sync_project_fates(project)
    assert_liveness(project, target, image, False)
    assert duplicate["value"] is None
    assert target.settings["coefficient_assignments"] == {"gamma": None}


def test_candidates_and_chart_export_read_live_source_context():
    from domain.candidate_enumeration import CandidateEnumerationError, enumerate_differential_candidates
    from domain.tex_renderer import render_chart_tex

    project, source, _, _, target, image, _ = linked_fixture(offset=2)
    target.classes.append(ClassNode("candidate", "C", Grade(19, 14)))
    sync_project_fates(project)
    assert len(enumerate_differential_candidates(target, image.source_id, 12, project=project)) == 1
    assert image.source_id in render_chart_tex(project, target, 12)
    source.settings["coefficient_assignments"]["gamma"] = 3
    with pytest.raises(CandidateEnumerationError, match="not live"):
        enumerate_differential_candidates(target, image.source_id, 12, project=project)
    assert image.source_id not in render_chart_tex(project, target, 12)


def test_periodicity_operations_recheck_linked_source_instead_of_stale_target_fate():
    from domain.manual_periodicity import ManualPeriodicityError, preview_manual_periodicity
    from domain.page_periodicity import PagePeriodicityError, plan_virtual_period_instances, prepare_page_period_cycle
    from domain.periodicity import PeriodicityOperationError, preview_periodic_translate

    project, source, _, _, target, image, _ = linked_fixture(offset=2)
    anchor = next(node for node in target.classes if node.id == image.source_id)
    anchor.label = "D"
    target.propositions.append(Proposition("period-proof", "periodicity", "fixture", status="admitted"))
    project.periodicity_rules.append(PeriodicityRule(
        "period", "fixture", target.id, "D^8", Grade(64, 0),
        horizontal_only=True, certificate_proposition_id="period-proof", status="established"))
    project.page_period_cycles.append(PagePeriodCycle("page-period", target.id, "D", Grade(8, 0), 12))
    payload = {"anchor_class_id": anchor.id, "page": 12, "period_stem": 64,
               "period_filtration": 0, "translation_start": 1, "translation_end": 1}
    source_backed = {"rule_id": "period", "anchor_class_id": anchor.id, "page": 12, "translation": 1}
    declaration = {"page": 12, "cycle_class_id": anchor.id, "basis": "fixture", "source_ref": "fixture"}
    sync_project_fates(project)
    assert preview_manual_periodicity(target, payload, project=project)["cycle_copies"]
    assert preview_periodic_translate(project, target, source_backed)
    assert prepare_page_period_cycle(project, target.id, declaration)
    source.settings["coefficient_assignments"]["gamma"] = 3
    with pytest.raises(ManualPeriodicityError, match="not live"):
        preview_manual_periodicity(target, payload, project=project)
    with pytest.raises(PeriodicityOperationError, match="not live"):
        preview_periodic_translate(project, target, source_backed)
    with pytest.raises(PagePeriodicityError, match="not live"):
        prepare_page_period_cycle(project, target.id, declaration)
    preview = plan_virtual_period_instances(project, "page-period", page=12,
                                           base_class_ids=[anchor.id], translations=[1])
    assert preview["instances"] == []
    assert preview["skipped"] == [{"class_id": anchor.id, "reason": "not-live-on-E_12"}]


def test_cross_graded_product_rejects_input_killed_by_linked_source():
    from domain.products import preview_cross_graded_product

    project, _, _, _, target, image, _ = linked_fixture()
    project.grading_sectors.append(GradingSector("sector", 0, 0, {}, "S00", "fixture", target.id))
    sync_project_fates(project)
    with pytest.raises(ValueError, match="live on the same"):
        preview_cross_graded_product(project, "sector", image.source_id, "sector", image.target_id, 12)


def test_api_export_candidates_and_manual_preview_pass_explicit_project(monkeypatch):
    import app as app_module

    project, source, _, _, target, image, _ = linked_fixture(offset=2)
    target.classes.append(ClassNode("candidate", "C", Grade(19, 14)))
    sync_project_fates(project)
    monkeypatch.setattr(app_module, "load_project", lambda: project)
    client = app_module.app.test_client()
    endpoint = f"/api/workspaces/{target.id}/legacy-export?page=12"
    assert image.source_id in {node["id"] for node in client.get(endpoint).get_json()["generators"]}
    source.settings["coefficient_assignments"]["gamma"] = 3
    assert image.source_id not in {node["id"] for node in client.get(endpoint).get_json()["generators"]}
    response = client.post(f"/api/v2/workspaces/{target.id}/differential-candidates",
                           json={"source_id": image.source_id, "page": 12})
    assert response.status_code == 400 and "not live" in response.get_json()["error"]
    response = client.post(f"/api/v2/workspaces/{target.id}/manual-periodicity/preview", json={
        "anchor_class_id": image.source_id, "page": 12, "period_stem": 64, "period_filtration": 0,
    })
    assert response.status_code == 400 and "not live" in response.get_json()["error"]
