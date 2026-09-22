"""Parameter assignments qualify current death, never rewrite event history."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain.fate import class_is_live_on_page, derive_class_fate, sync_workspace_fates
from domain.models import ClassNode, Differential, DifferentialMap, Grade, Proposition, Workspace


def add_arrow(workspace, ident, page=5, spec=None, fact=None):
    source, target, claim_id = f"{ident}-source", f"{ident}-target", f"claim-{ident}"
    workspace.classes.extend([ClassNode(source, source, Grade(20, 2)),
                              ClassNode(target, target, Grade(19, 2 + page))])
    conclusion = {"source_id": source, "target_id": target, "page": page}
    if spec is not None:
        conclusion["coefficient_parameter"] = deepcopy(spec)
    if fact:
        conclusion["fact_id"] = fact
    claim = Proposition(claim_id, "differential", ident, status="admitted", conclusion=conclusion)
    arrow = Differential(ident, source, target, page, status="admitted", proposition_id=claim_id)
    workspace.propositions.append(claim)
    workspace.differentials.append(arrow)
    return arrow, claim


def parameter(ident="c", value=None, **kwargs):
    return {"id": ident, "value": value, "domain": [1, 2, 3], "frobenius_power": 0, **kwargs}


def fixture(spec=None):
    workspace = Workspace("w", "HFPSS", spectral_sequence="hfpss")
    arrow, claim = add_arrow(workspace, "a", spec=spec if spec is not None else parameter(affine_offset=1))
    return workspace, arrow, claim


def assert_live(workspace, arrow, expected=True):
    for ident in (arrow.source_id, arrow.target_id):
        assert class_is_live_on_page(workspace, ident, arrow.page + 1) is expected
        assert (derive_class_fate(workspace, ident).first_hfpss_death is None) is expected


def test_assignment_changes_recheck_existing_accepted_events_without_deleting_history():
    workspace, arrow, _ = fixture()
    sync_workspace_fates(workspace)
    history = [asdict(event) for event in workspace.differential_events]
    assert len(history) == 2 and {event["status"] for event in history} == {"admitted"}
    assert_live(workspace, arrow)
    for value, live in (("zeta", False), (1, True), (3, False), (0, True), (None, True)):
        workspace.settings["coefficient_assignments"] = {"c": value}
        # Exercise the cached public liveness query BEFORE a sync as well.
        assert_live(workspace, arrow, live)
        sync_workspace_fates(workspace)
        assert_live(workspace, arrow, live)
        assert [asdict(event) for event in workspace.differential_events] == history


@pytest.mark.parametrize("value", [1, 2, 3, "2", "3", "zeta", r"\zeta^{2}", "ζ²", "1 + zeta"])
def test_nonzero_scalar_encodings_match_the_frontend(value):
    workspace, arrow, _ = fixture(parameter())
    workspace.settings["coefficient_assignments"] = {"c": value}
    sync_workspace_fates(workspace)
    assert_live(workspace, arrow, False)
    assert class_is_live_on_page(workspace, arrow.source_id, arrow.page)


@pytest.mark.parametrize("value", [0, "0", 4, -1, "bad", True, [], {}])
def test_invalid_base_unit_never_determines_death(value):
    workspace, arrow, _ = fixture(parameter())
    workspace.settings["coefficient_assignments"] = {"c": value}
    sync_workspace_fates(workspace)
    assert_live(workspace, arrow)


@pytest.mark.parametrize("changes", [
    {"id": ""}, {"frobenius_power": 2}, {"frobenius_power": True},
    {"domain": [1]}, {"affine_offset": "bad"},
])
def test_invalid_parameter_declaration_cannot_kill(changes):
    workspace, arrow, _ = fixture(parameter(value=2, **changes))
    sync_workspace_fates(workspace)
    assert_live(workspace, arrow)


def test_affine_offset_is_added_before_frobenius():
    workspace, arrow, claim = fixture(parameter(value=2, affine_offset="zeta", frobenius_power=1))
    sync_workspace_fates(workspace)
    assert_live(workspace, arrow)  # (zeta + zeta)^2 = 0, not zeta^2 + zeta = 1
    claim.conclusion["coefficient_parameter"]["affine_offset"] = 1
    assert_live(workspace, arrow, False)


def test_shared_parameter_conflict_including_reviewed_declaration_is_not_ignored():
    workspace, arrow, _ = fixture(parameter(value=2))
    _, other = add_arrow(workspace, "b", spec=parameter(value=3))
    other.status = workspace.differentials[-1].status = "review"
    sync_workspace_fates(workspace)
    assert_live(workspace, arrow)
    other.conclusion["coefficient_parameter"]["value"] = 2
    assert_live(workspace, arrow, False)
    workspace.settings["coefficient_assignments"] = {"c": 1}
    assert_live(workspace, arrow)


def test_earlier_unresolved_row_blocks_later_parameterized_death_not_legacy_history():
    workspace, early, _ = fixture(parameter())
    later, _ = add_arrow(workspace, "later", page=9, spec=parameter("b", 1))
    legacy, _ = add_arrow(workspace, "legacy", page=9)
    sync_workspace_fates(workspace)
    assert_live(workspace, early)
    assert_live(workspace, later)
    assert_live(workspace, legacy, False)
    workspace.settings["coefficient_assignments"] = {"c": 1}
    assert_live(workspace, later, False)


def test_constraint_uses_exact_fact_page_and_current_assignments():
    workspace, first, claim = fixture(parameter("alpha", 2))
    second, _ = add_arrow(workspace, "b", spec=parameter("beta", 2))
    add_arrow(workspace, "d19", page=19, fact="FN-010")
    premise, premise_claim = add_arrow(workspace, "d23", page=23, fact="FN-010")
    claim.conclusion["coefficient_constraints"] = [{
        "id": "compat", "kind": "equal-nonzero-parameters", "page": 5,
        "parameter_ids": ["alpha", "beta"], "required_facts": ["FN-010"],
        "required_differentials": [{"fact_id": "FN-010", "page": 23}],
        "normalization_value": 1,
    }]
    sync_workspace_fates(workspace)
    assert_live(workspace, first)
    assert_live(workspace, second)
    premise.status = premise_claim.status = "review"
    assert_live(workspace, first, False)  # d19 alone is not the required premise
    premise.status = premise_claim.status = "admitted"
    for item in workspace.propositions[:2]:
        item.conclusion["coefficient_parameter"]["value"] = None
    workspace.settings["coefficient_assignments"] = {"alpha": 1, "beta": 1}
    assert_live(workspace, first, False)
    workspace.settings["coefficient_assignments"]["beta"] = 2
    assert_live(workspace, first)


def test_parameterized_events_follow_current_claim_binding_and_admission():
    workspace, arrow, claim = fixture(parameter(value=1))
    sync_workspace_fates(workspace)
    history = deepcopy(workspace.differential_events)
    _, replacement = add_arrow(workspace, "replacement", spec=parameter("b", 1, affine_offset=1))
    arrow.proposition_id = replacement.id
    assert_live(workspace, arrow)
    arrow.proposition_id = claim.id
    arrow.status = "review"
    assert_live(workspace, arrow)
    arrow.status = "admitted"
    assert_live(workspace, arrow, False)
    assert workspace.differential_events == history
    workspace.differentials.remove(arrow)
    assert_live(workspace, arrow)  # orphan parameterized evidence is not a resolved map


def test_unparameterized_accepted_history_is_unchanged_after_arrow_removal():
    workspace = Workspace("w", "HFPSS")
    arrow, _ = add_arrow(workspace, "legacy")
    sync_workspace_fates(workspace)
    workspace.differentials.clear()
    assert_live(workspace, arrow, False)


def test_parameterized_map_requires_current_accepted_nonarchived_matrix():
    workspace, arrow, _ = fixture(parameter(value=1))
    arrow.linear_map_id = "matrix"
    matrix = DifferentialMap("matrix", None, None, 5, [["1"]], status="admitted")
    workspace.differential_maps.append(matrix)
    sync_workspace_fates(workspace)
    assert_live(workspace, arrow, False)
    matrix.archived = True
    assert_live(workspace, arrow)
    matrix.archived = False
    matrix.status = "review"
    assert_live(workspace, arrow)
    matrix.status = "admitted"
    assert_live(workspace, arrow, False)
    workspace.differential_maps.clear()
    assert_live(workspace, arrow)


def test_parameterized_review_history_can_be_admitted_without_rewriting_events():
    workspace, arrow, claim = fixture(parameter(value=1))
    arrow.status = claim.status = "review"
    sync_workspace_fates(workspace)
    history = deepcopy(workspace.differential_events)
    assert_live(workspace, arrow)
    arrow.status = claim.status = "admitted"
    assert_live(workspace, arrow, False)
    sync_workspace_fates(workspace)
    assert workspace.differential_events == history
    assert {event.status for event in history} == {"review"}


@pytest.mark.parametrize("field", ["page", "source_id", "target_id", "proposition_id"])
def test_editing_a_parameterized_arrow_cannot_reuse_its_old_endpoint_events(field):
    workspace, arrow, _ = fixture(parameter())
    replacement, _ = add_arrow(workspace, "replacement", spec=parameter("other", 1))
    sync_workspace_fates(workspace)
    history = deepcopy(workspace.differential_events)
    original_source, original_target = arrow.source_id, arrow.target_id
    setattr(arrow, field, 9 if field == "page" else getattr(replacement, field))
    workspace.settings["coefficient_assignments"] = {"c": 1}
    for ident in (original_source, original_target):
        assert derive_class_fate(workspace, ident).first_hfpss_death is None
    sync_workspace_fates(workspace)
    assert workspace.differential_events == history


def test_rebinding_to_an_unparameterized_claim_does_not_reclassify_old_parameter_history():
    workspace, arrow, _ = fixture(parameter())
    legacy, _ = add_arrow(workspace, "legacy")
    sync_workspace_fates(workspace)
    arrow.proposition_id = legacy.proposition_id
    workspace.settings["coefficient_assignments"] = {"c": 1}
    assert_live(workspace, arrow)


@pytest.mark.parametrize("unit,power", [(1, 0), (2, 0), (3, 0), (2, 1)])
def test_relative_image_does_not_kill_the_printed_sum_for_a_different_unit(unit, power):
    workspace, arrow, _ = fixture(parameter(value=unit, frobenius_power=power, target_component="Q"))
    target = next(node for node in workspace.classes if node.id == arrow.target_id)
    target.style = {"e2_components": {"P": 1, "Q": 1}, "e2_basis_patterns": ["P", "Q"]}
    sync_workspace_fates(workspace)
    assert not class_is_live_on_page(workspace, arrow.source_id, 6)
    assert class_is_live_on_page(workspace, target.id, 6) == (unit != 1)


def test_zero_relative_coefficient_keeps_the_unchanged_target_component_nonzero():
    workspace, arrow, _ = fixture(parameter(value=1, affine_offset=1, target_component="Q"))
    target = next(node for node in workspace.classes if node.id == arrow.target_id)
    target.style = {"e2_components": {"P": 1, "Q": 1}, "e2_basis_patterns": ["P", "Q"]}
    sync_workspace_fates(workspace)
    assert not class_is_live_on_page(workspace, arrow.source_id, 6)
    assert class_is_live_on_page(workspace, target.id, 6)


def test_invalid_relative_column_blocks_later_parameterized_events():
    workspace, arrow, _ = fixture(parameter(value=1, target_component="missing"))
    later, _ = add_arrow(workspace, "later", page=9, spec=parameter("later_b", 1))
    sync_workspace_fates(workspace)
    assert_live(workspace, arrow)
    assert_live(workspace, later)


def test_conditional_fate_uses_source_parameter_and_keeps_zero_image_history_nonfatal():
    workspace, arrow, claim = fixture(parameter("gamma"))
    workspace.propositions.append(Proposition("pc", "coefficient", "source c", status="review",
        conclusion={"coefficient_parameter": parameter("c")}))
    claim.conclusion["coefficient_condition"] = {
        "parameter_id": "c", "equals": 1, "otherwise": "zero-euler-image"}
    sync_workspace_fates(workspace)
    history = deepcopy(workspace.differential_events)
    for c, gamma, live in ((None, 1, True), (1, None, True), (1, 2, False),
                           (2, None, True), (3, None, True)):
        workspace.settings["coefficient_assignments"] = {"c": c, "gamma": gamma}
        assert_live(workspace, arrow, live)
        sync_workspace_fates(workspace)
        assert workspace.differential_events == history


def test_false_condition_does_not_block_later_maps_for_an_unused_unit():
    workspace, early, claim = fixture(parameter("unused_gamma"))
    claim.conclusion["coefficient_condition"] = {
        "parameter_id": "c", "equals": 1, "otherwise": "zero-euler-image"}
    workspace.propositions.append(Proposition("pc", "coefficient", "c", conclusion={
        "coefficient_parameter": parameter("c", value=2, frobenius_power=1)}))
    later, _ = add_arrow(workspace, "later", page=9, spec=parameter("later_unit", 1))
    sync_workspace_fates(workspace)
    assert_live(workspace, early)
    assert_live(workspace, later, False)
    claim.conclusion["coefficient_condition"]["equals"] = 2
    assert_live(workspace, later)  # source-field c=2 activates the unknown gamma


@pytest.mark.parametrize("condition", [None, {}, {"parameter_id": "c", "equals": True, "otherwise": "zero-euler-image"},
    {"parameter_id": "undeclared", "equals": 1, "otherwise": "zero-euler-image"}])
def test_invalid_condition_blocks_current_and_later_parameterized_death(condition):
    workspace, early, claim = fixture(parameter(value=1))
    claim.conclusion["coefficient_condition"] = condition
    later, _ = add_arrow(workspace, "later", page=9, spec=parameter("gamma", 1))
    sync_workspace_fates(workspace)
    assert_live(workspace, early)
    assert_live(workspace, later)
