"""Explicit action labels and their presentation-only scalar basis changes.

These tests do not assert a new HFPSS Picard theorem: the source-declared
20+H comparison and its obligations remain visible on every affected tile.
No test rewrites the runtime matrices into a different basis.
"""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.actions import expanded_action_basis, normalized_scalar_ratio, transported_expression
from domain.atlas_transport import SOURCE_REPRESENTATIONS, atlas_display_coefficient, ensure_q8_atlas_transports
from domain.migrations import migrate_project
from domain.models import Proposition, project_from_dict
from domain.seed import demo_project


@pytest.mark.parametrize("expression,unit,normalized", [
    ("D", 3, "D"), ("x", 2, "x"), ("y", 3, "y"), ("j", 2, "j"),
    ("g", 1, "g"), ("c", 1, "c"), ("d", 1, "d"),
    (r"h_1h_2v_1k", 1, r"h_1h_2v_1k"),
    (r"D^{-1}", 2, r"D^{-1}"),
    (r"2D", 3, "2D"), (r"4D^2", 2, "4D^{2}"),
])
def test_omega_weights_preserve_integer_and_witt_factors(expression, unit, normalized):
    result = expanded_action_basis(expression, 1)
    assert result["status"] == "exact"
    assert result["unit"] == unit and result["expression"] == normalized
    assert not any(wrapper in result["expanded_expression"] for wrapper in (r"\omega", r"\psi", "P_{"))
    assert r"\," not in result["expanded_expression"]


def test_rotated_quadratic_and_euler_labels_keep_their_relative_coefficients():
    quadratic = expanded_action_basis(r"(x^2+y^2)D^2u_{2\sigma_i}", 1)
    assert quadratic["unit"] == 1
    assert quadratic["expression"] == r"(x^{2}+\zeta^2y^{2})D^{2}u_{2\sigma_j}"
    euler = expanded_action_basis(r"a_{\sigma_i}", 1)
    assert euler["unit"] == 2
    assert euler["expression"] == r"(x+\zeta y)u_{\sigma_j}"
    assert euler["expanded_expression"] == r"\zeta(x+\zeta y)u_{\sigma_j}"
    # Multiplication has NOT been reduced in a characteristic-two ring.
    witt_sum = expanded_action_basis(r"2(h_1+\zeta xv_1)u_{2\sigma_j}", reflected=True)
    assert witt_sum["expanded_expression"] == r"2(h_1+\zeta^2xv_1)u_{2\sigma_k}"


def test_psi_and_omega_composition_on_explicit_coefficients_is_semilinear_once():
    expression = r"\zeta^2xD^2u_{\sigma_i+2\sigma_j}"
    result = expanded_action_basis(expression, power=1, reflected=True)
    assert result["unit"] == 1
    assert result["expanded_expression"] == r"xD^{2}u_{\sigma_j+2\sigma_i}"
    assert transported_expression(transported_expression(expression, reflected=True), reflected=True) == transported_expression(expression)
    assert expanded_action_basis(r"j^2D^{-1}", power=1)["unit"] == 1


@pytest.mark.parametrize("expression", [r"D^{-1}u_{2\sigma_i}", r"j^{-2}D^2x",
                                        r"4\zeta D^2u_{\sigma_i}", r"(h_1+xv_1)D^{-1}u_{3\sigma_i}"])
def test_repeated_action_parses_its_own_tex_command_boundaries(expression):
    original = transported_expression(expression)
    rotated = original
    for _ in range(3):
        rotated = transported_expression(rotated, power=1)
    assert rotated == original
    assert expanded_action_basis(r"{\zeta}D", reflected=True)["unit"] == 3
    assert expanded_action_basis(r"\zeta{}D", reflected=True)["unit"] == 3


def test_normalized_arrow_ratio_cancels_common_units_and_conjugates_only_once():
    assert normalized_scalar_ratio(3, 3) == 1
    assert normalized_scalar_ratio(1, 2) == 2
    assert normalized_scalar_ratio(2, 1) == 3
    assert normalized_scalar_ratio(None, 1) is None
    assert normalized_scalar_ratio(True, 1) is None
    common = atlas_display_coefficient(expanded_action_basis("D", 1), expanded_action_basis("Dh_1", 1))
    assert common["basis_ratio"] == common["value"] == common["transported_value"] == 1
    # psi(A)=A and psi(zeta^2 B)=zeta B changes the normalized arrow by zeta.
    changed = atlas_display_coefficient(expanded_action_basis("h_1", reflected=True),
                                        expanded_action_basis(r"\zeta^2h_1", reflected=True))
    assert changed["basis_ratio"] == changed["value"] == 2
    fixed = {"id": "mixed_d11_R", "value": 3, "domain": [3], "frobenius_power": 1}
    result = atlas_display_coefficient({"unit": 3}, {"unit": 3}, fixed)
    assert result["resolved"] and result["transported_value"] == result["value"] == 2
    assert fixed["value"] == 3 and fixed["frobenius_power"] == 1


@pytest.mark.parametrize("parameter", [
    {"id": "c", "value": None, "domain": [1, 2, 3], "frobenius_power": 0},
    {"id": "linked", "value": 1, "frobenius_power": 0, "source_parameter": {"workspace_id": "source"}},
    {"id": "vector", "value": 2, "frobenius_power": 0, "target_component": "S22H"},
    {"id": "quotient", "value": 2, "frobenius_power": 0, "inverse_parameter_id": "c"},
    {"id": "invalid", "value": 2, "domain": [1], "frobenius_power": 0},
])
def test_unresolved_or_vector_parameters_are_not_presented_as_fixed_scalars(parameter):
    result = atlas_display_coefficient({"unit": 2}, {"unit": 3}, parameter)
    assert result["basis_ratio"] == 2
    assert not result["resolved"] and result["value"] is None
    assert result["transported_parameter"] == parameter


@pytest.mark.parametrize("value,offset,reflected,expected", [
    (1, 1, 0, 0), (1, 1, 1, 0), (2, 1, 0, 3), (2, 1, 1, 2),
])
def test_fixed_affine_coefficient_is_evaluated_before_frobenius(value, offset, reflected, expected):
    parameter = {"id": "c", "value": value, "domain": [1, 2, 3],
                 "affine_offset": offset, "frobenius_power": reflected}
    result = atlas_display_coefficient({"unit": 2}, {"unit": 2}, parameter)
    assert result["resolved"] and not result["requires_runtime"]
    assert result["transported_value"] == result["value"] == expected
    assert result["transported_parameter"] == parameter


@pytest.mark.parametrize("condition", [None, {},
    {"parameter_id": "b", "equals": 1, "otherwise": "zero-euler-image"},
])
def test_even_fixed_affine_scalars_do_not_resolve_an_unchecked_condition(condition):
    parameter = {"id": "c", "value": 1, "domain": [1, 2, 3],
                 "affine_offset": 1, "frobenius_power": 0}
    result = atlas_display_coefficient({"unit": 1}, {"unit": 3}, parameter,
                                       coefficient_condition=condition)
    assert result["basis_ratio"] == 3
    assert not result["resolved"] and result["requires_runtime"]
    assert result["value"] is result["transported_value"] is None
    assert result["coefficient_condition"] == condition


def test_linked_affine_and_matrix_endpoints_cannot_reuse_a_raw_label_ratio():
    linked = {"id": "c", "value": 1, "domain": [1, 2, 3], "affine_offset": 1,
              "frobenius_power": 0, "source_parameter": {"workspace_id": "source"}}
    result = atlas_display_coefficient({"unit": 1}, {"unit": 2}, linked)
    assert not result["resolved"] and result["requires_runtime"] and result["value"] is None
    matrix = atlas_display_coefficient({"unit": 1}, {"unit": 2}, matrix_endpoint=True)
    assert matrix["basis_ratio"] is None
    assert matrix["endpoint_basis_status"] == "requires-effective-matrix-image"
    assert not matrix["resolved"] and matrix["value"] is None


@pytest.mark.parametrize("parameter", [{}, {"value": 1},
    {"id": "bad", "value": 1}, {"id": "bad", "value": 1, "frobenius_power": True},
])
def test_invalid_parameter_metadata_does_not_fall_back_to_a_unit_one_map(parameter):
    result = atlas_display_coefficient({"unit": 1}, {"unit": 1}, parameter)
    assert not result["resolved"] and result["requires_runtime"] and result["value"] is None


def test_unknown_atoms_and_prose_do_not_acquire_invented_action_units():
    for expression in ("A", r"d_{13}\text{-target}", r"\frac{x}{y}"):
        result = expanded_action_basis(expression, 1, True)
        assert result["status"] == "unresolved" and result["unit"] is None
        assert not atlas_display_coefficient(result, {"unit": 1})["resolved"]


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def test_only_five_independent_charts_and_eleven_explicit_transports(project):
    assert set(SOURCE_REPRESENTATIONS) == {"ws_integer", "ws_sigma_i", "ws_2sigma_i",
                                           "ws_3sigma_i", "ws_sigma_i_2sigma_j"}
    images = [ws for ws in project.workspaces if ws.settings.get("atlas_transport")]
    assert len(images) == 11
    exact, unresolved = [], []
    for workspace in images:
        for node in workspace.classes:
            basis = node.style.get("atlas_display_basis")
            if not basis:
                continue
            assert node.expression == node.label == basis["expanded_expression"]
            assert not any(wrapper in node.label for wrapper in (r"\omega", r"\psi", "P_{"))
            (exact if basis["status"] == "exact" else unresolved).append(node)
    assert len(exact) > 1500
    assert unresolved and all("target" in node.label for node in unresolved)


def test_selected_s11_s32_picard_paths_define_the_thom_basis_without_promoting_obligations(project):
    workspaces = {ws.id: ws for ws in project.workspaces}
    for ident, source, shift, exponent in (
        ("ws_q8-ro-a1-b1", "ws_3sigma_i", 16, 2),
        ("ws_q8-ro-a3-b2", "ws_sigma_i_2sigma_j", -32, -4),
    ):
        image = workspaces[ident]
        plan = image.settings["atlas_transport"]
        thom = plan["display_thom_basis"]
        assert plan["source_workspace_id"] == source and plan["stem_shift"] == shift
        assert thom["display_D_exponent"] == exponent
        assert thom["status"] == plan["normalization"]["status"] == "source-declared"
        assert thom["obligations"] == plan["normalization"]["obligations"]
        assert thom["obligations"] and thom["external_thom_unit"] is None
        assert thom["D_shift_is_permanent_period"] is False
        assert thom["picard_factors"] and "Picard_multiplier" in thom["definition"]
        assert "a_{\\mathbb H}" in thom["picard_multiplier"]
        assert any(n.style.get("atlas_display_basis", {}).get("picard_D_exponent") == exponent
                   for n in image.classes)
    s11 = workspaces["ws_q8-ro-a1-b1"]
    # This D² factor is inserted AFTER omega², so it contributes no new zeta.
    u = next(n for n in s11.classes if n.style.get("atlas_display_basis", {}).get("source_expression")
             == r"v_1^2u_{3\sigma_i}")
    assert u.style["atlas_display_basis"]["unit"] == 1


def test_s71_import_alias_is_not_confused_with_higher_euler_power(project):
    corrections = [node.style["atlas_display_basis"] for ws in project.workspaces for node in ws.classes
                   if node.style.get("atlas_display_basis", {}).get("source_alias_correction")]
    assert corrections
    for basis in corrections:
        correction = basis["source_alias_correction"]
        assert correction["source_expression"].startswith("a_{")
        assert correction["expanded_expression"].startswith("(x+y)u_{")
        assert basis["status"] == "exact" and basis["unit"] in (1, 2, 3)
        assert "Euler a_V" in correction["reason"]


def test_arrow_stores_separate_normalized_display_coefficient_and_roundtrips(project):
    restored = project_from_dict(asdict(project))
    restored_rows = {row.id: row for ws in restored.workspaces for row in ws.differentials}
    count = 0
    for workspace in project.workspaces:
        if not workspace.settings.get("atlas_transport"):
            continue
        claims = {claim.id: claim for claim in workspace.propositions}
        for row in workspace.differentials:
            if not row.display_coefficient:
                continue
            metadata = claims[row.proposition_id].conclusion["atlas_display_coefficient"]
            assert row.display_coefficient == metadata == restored_rows[row.id].display_coefficient
            assert metadata["runtime_basis"] == "transported source basis (unchanged)"
            assert metadata["frobenius_applied_to_parameter_once"]
            count += 1
    assert count > 100


def test_real_condition_and_matrix_rows_keep_runtime_resolution_requirements(project):
    conditional = matrices = 0
    for workspace in project.workspaces:
        if not workspace.settings.get("atlas_transport"):
            continue
        claims = {claim.id: claim for claim in workspace.propositions}
        for row in workspace.differentials:
            conclusion = claims[row.proposition_id].conclusion
            if "coefficient_condition" in conclusion:
                conditional += 1
                assert row.display_coefficient["coefficient_condition"] == conclusion["coefficient_condition"]
                assert not row.display_coefficient["resolved"]
                assert row.display_coefficient["requires_runtime"]
                assert row.display_coefficient["value"] is None
            if row.linear_map_id:
                matrices += 1
                assert row.display_coefficient["basis_ratio"] is None
                assert not row.display_coefficient["resolved"]
                assert row.display_coefficient["requires_runtime"]
                assert row.display_coefficient["value"] is None
    assert conditional > 0 and matrices > 0


def test_refresh_preserves_pages_runtime_coordinates_witt_layers_and_parameters(project):
    refreshed = deepcopy(project)
    source_snapshot = {ws.id: asdict(ws) for ws in refreshed.workspaces if ws.id in SOURCE_REPRESENTATIONS}
    before = {}
    for ws in refreshed.workspaces:
        if not ws.settings.get("atlas_transport"):
            continue
        ws.page = 11
        before[ws.id] = {
            "matrices": [asdict(m) for m in ws.differential_maps],
            "nodes": {n.id: (deepcopy(n.style.get("e2_components")), n.style.get("two_valuation"),
                              n.style.get("j_order"), list(n.coordinates)) for n in ws.classes},
            "parameters": {p.id: deepcopy(p.conclusion["coefficient_parameter"]) for p in ws.propositions
                           if "coefficient_parameter" in p.conclusion},
        }
    ensure_q8_atlas_transports(refreshed)
    for ws in refreshed.workspaces:
        if ws.id in source_snapshot:
            assert asdict(ws) == source_snapshot[ws.id]
        if ws.id not in before:
            continue
        assert ws.page == 11
        assert [asdict(m) for m in ws.differential_maps] == before[ws.id]["matrices"]
        assert {n.id: (n.style.get("e2_components"), n.style.get("two_valuation"), n.style.get("j_order"), n.coordinates)
                for n in ws.classes} == before[ws.id]["nodes"]
        assert {p.id: p.conclusion["coefficient_parameter"] for p in ws.propositions
                if "coefficient_parameter" in p.conclusion} == before[ws.id]["parameters"]


def test_full_migration_does_not_add_e2_only_claims_for_expanded_atlas_images(project):
    refreshed = deepcopy(project)
    before = {ws.id: {p.id: asdict(p) for p in ws.propositions} for ws in refreshed.workspaces}
    migrate_project(refreshed)
    assert {ws.id: {p.id: asdict(p) for p in ws.propositions} for ws in refreshed.workspaces} == before
    sectors = {sector.workspace_id: sector.id for sector in refreshed.grading_sectors}
    for ws in refreshed.workspaces:
        if not ws.settings.get("atlas_transport"):
            continue
        prefix = f"atlas_{sectors[ws.id]}_"
        assert not any(p.id.startswith((f"source_{prefix}", f"source_e2_edge_{prefix}"))
                       and p.rule.startswith("ThomIsomorphism") for p in ws.propositions)


def test_e2_duplicate_cleanup_preserves_similarly_named_manual_and_unmanaged_claims(project):
    refreshed = deepcopy(project)
    target = next(ws for ws in refreshed.workspaces if ws.id == "ws_q8-ro-a3-b2")
    prefix = "atlas_q8-ro-a3-b2_"
    node = next(n for n in target.classes if n.id.startswith(prefix))
    records = [
        Proposition(f"source_{prefix}manual", "source", "Manual same-prefix claim",
                    rule="manual", conclusion={"class_id": node.id}),
        Proposition(f"source_e2_edge_{prefix}manual", "relation", "Manual same-prefix edge",
                    rule="manual", conclusion={"source_id": node.id}),
        Proposition(f"source_{prefix}unmanaged", "source", "Unmanaged endpoint",
                    rule="ThomIsomorphism + DKLLW24 E2 pattern", conclusion={"class_id": "manual-point"}),
        Proposition("manual-thom-image-claim", "source", "Local image claim",
                    rule="ThomIsomorphism + DKLLW24 E2 pattern", conclusion={"class_id": node.id}),
    ]
    generated = Proposition(f"source_{prefix}generated", "source", "Duplicate imported image claim",
                            rule="ThomIsomorphism + DKLLW24 E2 pattern", conclusion={"class_id": node.id})
    expected = {p.id: asdict(p) for p in records}
    target.propositions.extend(records + [generated])
    ensure_q8_atlas_transports(refreshed)
    remaining = {p.id: asdict(p) for p in target.propositions}
    assert {ident: remaining[ident] for ident in expected} == expected
    assert generated.id not in remaining
