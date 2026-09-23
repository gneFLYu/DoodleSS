import sys
import re
from copy import deepcopy
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from domain.formal_notes_chart import (
    DERIVED_FORMAL_ARROWS, FORMAL_ARROWS, ensure_formal_notes_chart, formal_arrow_counts,
)
from domain.cell_linear_algebra import transition_data
from domain.periodic_fate_ledger import load_periodic_fate_ledger
from domain.algebra_labels import parse_algebra_label
from domain.migrations import migrate_project
from domain.seed import demo_project
from domain.fate import class_is_live_on_page, resolve_raw_coefficient_parameter, sync_workspace_fates
from domain.models import Workspace
from domain.algebra import F4Element


MIXED_A_BINDING = {
    "workspace_id": "ws_sigma_i_2sigma_j",
    "parameter_id": "mixed_d5_A",
    "proposition_id": "coefficient_proof_mixed_d5_A",
}


def assert_current_mixed_a_binding(project, workspace, claim):
    metadata = claim.conclusion
    assert metadata["fact_id"] in {"FN-MIX-002", "FN-MIX-003", "DER-MIX-D5-A-EVEN"}
    assert claim.status == metadata["admission_status"] == "source-verified"
    assert metadata["source_status"] == "proof-bound-coefficient"
    assert metadata["source_blockers"] == metadata["machine_verification_pending"] == []
    assert metadata["required_admitted_premises"] is True
    parameter = metadata["coefficient_parameter"]
    assert parameter["id"] == "mixed_d5_A"
    assert parameter["value"] is None and parameter["domain"] == [1, 2, 3]
    assert parameter["proof_binding"] == MIXED_A_BINDING
    assert any(ident.endswith(MIXED_A_BINDING["proposition_id"]) for ident in claim.premise_ids)
    assert resolve_raw_coefficient_parameter(workspace, "mixed_d5_A", project=project) == {
        "resolved": True, "proof_bound": True, "id": "mixed_d5_A", "value": 3,
    }


def test_all_sixteen_sectors_are_materialized_from_exactly_two_thom_patterns():
    project = migrate_project(demo_project())
    assert len(project.grading_sectors) == 16
    assert all(sector.status == "imported" and sector.class_ids for sector in project.grading_sectors)

    workspaces = {item.id: item for item in project.workspaces}
    for sector in project.grading_sectors:
        workspace = workspaces[sector.workspace_id]
        expected = "integer" if sector.a % 2 == 0 and sector.b % 2 == 0 else "sigma_i"
        assert workspace.settings["rendering"]["enumerated_e2_pattern"] == expected

    for workspace_id in (
        "ws_integer", "ws_sigma_i", "ws_2sigma_i", "ws_3sigma_i",
        "ws_sigma_i_2sigma_j",
    ):
        assert workspaces[workspace_id].settings["rendering"]["enumerated_e2_pattern"] in {"integer", "sigma_i"}

    sigma_j = workspaces["ws_q8-ro-a0-b1"]
    transported = [item for item in sigma_j.classes if item.style.get("atlas_transport")]
    assert transported
    source_classes = {item.id: item for item in workspaces["ws_sigma_i"].classes}
    for node in transported:
        transport = node.style["atlas_transport"]
        assert transport["source_workspace_id"] == "ws_sigma_i"
        source = source_classes[transport["source_class_id"]]
        assert transport["omega_power"] == 1
        assert not transport["reflected"]
        basis = node.style["atlas_display_basis"]
        assert basis["source_expression"] == (source.expression or source.label)
        assert node.label == node.expression == basis["expanded_expression"]
        assert not any(wrapper in node.label for wrapper in (r"\omega", r"\psi", "P_{"))
        if basis["status"] == "exact":
            assert basis["unit"] in {1, 2, 3}
        else:
            assert basis["unit"] is None
        assert node.grade.filtration == source.grade.filtration
        assert node.grade.stem == source.grade.stem + transport["stem_shift"]
        assert node.grade.representation == {"sigma_j": -1}
        # The scalar extraction changes presentation, not the coordinates in
        # the transported basis or any Witt/series layer of the actual class.
        assert node.coordinates == source.coordinates
        for field in ("e2_components", "two_valuation", "two_adic_valuation", "j_order"):
            assert node.style.get(field) == source.style.get(field)
    euler = next(node for node in transported
                 if node.style["atlas_transport"]["source_class_id"] == "sig_a")
    assert euler.style["atlas_display_basis"]["unit"] == 2
    assert euler.style["atlas_display_basis"]["expression"] == r"(x+\zeta y)u_{\sigma_j}"
    assert euler.label == r"\zeta(x+\zeta y)u_{\sigma_j}"
    # omega(v1² D u_i) = zeta² v1² D u_j in the chosen transported Thom
    # basis; a bare i-to-j replacement would lose this nontrivial D factor.
    d_column = next(node for node in transported
                    if source_classes[node.style["atlas_transport"]["source_class_id"]].style.get("e2_pattern") == "S40"
                    and node.grade.stem == 12 and node.grade.filtration == 0)
    assert d_column.style["atlas_display_basis"]["unit"] == 3
    assert d_column.style["atlas_display_basis"]["picard_D_exponent"] == 0
    assert d_column.style["atlas_display_basis"]["series_action"]["omega_unit"] == 2
    assert sigma_j.settings["atlas_transport"]["basis_convention"].startswith("Runtime uses transported source coordinates;")


def test_hollow_series_records_the_four_stem_bottom_truncation_rule():
    project = migrate_project(demo_project())
    integer = next(item for item in project.workspaces if item.id == "ws_integer")
    hollow = [item for item in integer.classes if item.style.get("dkllw_glyph") == "j-positive-series"]
    assert len(hollow) == 8
    assert all(item.style["series_stem_step"] == 4 for item in hollow)
    assert all(item.style["series_bottom_loss_per_step"] == 1 for item in hollow)
    assert all(item.style["series_object_period_stem"] == 64 for item in hollow)

    script = (Path(__file__).resolve().parents[1] / "backend" / "static" / "app.js").read_text(encoding="utf-8")
    assert 'record.size * 0.92' in script
    assert 'function seriesTruncation(record)' in script
    assert 'data-series-bottom-order' in script


def test_active_formal_notes_arrows_are_complete_and_have_correct_bidegree():
    assert formal_arrow_counts() == {
        "ws_2sigma_i": 20,
        "ws_3sigma_i": 12,
        "ws_sigma_i_2sigma_j": 8,
    }
    assert len(FORMAL_ARROWS) == 40
    assert all(
        arrow.target_stem - arrow.source_stem == -1
        and arrow.target_filtration - arrow.source_filtration == arrow.page
        for arrow in FORMAL_ARROWS
    )
    assert not any(arrow.fact_id.startswith("FN-REJ-") for arrow in FORMAL_ARROWS)

    project = migrate_project(demo_project())
    workspaces = {item.id: item for item in project.workspaces}
    for workspace_id, count in formal_arrow_counts().items():
        formal_ids = {
            arrow.differential_id or f"formal_diff_{arrow.fact_id.lower()}"
            for arrow in FORMAL_ARROWS if arrow.workspace_id == workspace_id
        }
        # Repeated fact families receive numbered generated IDs, so the exact
        # migrated count is the source-of-truth completeness assertion.
        migrated = [
            item for item in workspaces[workspace_id].differentials
            if item.label.startswith("FN-")
            and item.id not in {arrow.differential_id for arrow in DERIVED_FORMAL_ARROWS}
        ]
        assert len(migrated) == count
        assert all(item.status != "rejected" for item in migrated)


def test_formal_labels_independently_have_their_declared_adams_bidegrees():
    # Checking target-source=(-1,r) alone misses errors in BOTH coordinates.
    # Compute degrees from the named factors (Thom u has displayed degree 0)
    # and check every summand separately, without using the endpoint grades.
    degrees = {"x": (-1, 1), "y": (-1, 1), "h_1": (1, 1), "h_2": (3, 1),
               "v_1": (2, 0), "k": (-4, 4), "D": (8, 0), r"\zeta": (0, 0)}
    for arrow in FORMAL_ARROWS + DERIVED_FORMAL_ARROWS:
        for label, expected in ((arrow.source_label, (arrow.source_stem, arrow.source_filtration)),
                                (arrow.target_label, (arrow.target_stem, arrow.target_filtration))):
            text = re.sub(r"u_\{[^}]*\}", "", label)
            text = text.replace(r"\zeta", "")  # coefficient has degree (0,0)
            text = text.replace(r"\{", "(").replace(r"\}", ")")
            group = re.search(r"\(([^()]*)\)", text)
            terms = ([text[:group.start()] + term + text[group.end():] for term in group.group(1).split("+")]
                     if group else [text or "1"])
            for term in terms:
                parsed = parse_algebra_label(term, unit_labels=("D",))
                actual = tuple(sum(degrees[factor.label][i] * factor.power for factor in parsed.factors)
                               for i in (0, 1))
                assert actual == expected, (arrow.fact_id, label, term, actual, expected)


def test_formal_notes_zero_maps_are_metadata_not_fake_arrows():
    project = migrate_project(demo_project())
    workspaces = {item.id: item for item in project.workspaces}
    expected = {
        "ws_2sigma_i": {
            "FN-2I-003-zero": (5, 16),
            "FN-2I-005-zero": (5, 16),
            "FN-2I-004-derived-zero": (5, 16),
            "FN-2I-003-h2-zero": (5, 16),
            "FN-2I-004-h2-square-zero": (5, 8),
            "FN-2I-003-euler-h2-zero": (21, 64),
        },
        "ws_3sigma_i": {
            "FN-3I-001-zero": (3, 8),
            "FN-3I-003-even-zero": (5, 16),
            "FN-3I-001-Q-zero": (5, 8),
            "DER-3I-D5-A-EVEN": (5, 16),
            "DER-3I-D5-C-zero": (5, 8),
            "DER-3I-D7-C-zero": (7, 8),
            "DER-3I-D7-Q-zero": (7, 8),
            "DER-3I-D7-P-EVEN": (7, 16),
            "DER-3I-D5-B-zero": (5, 8),
            "DER-3I-D7-B-zero": (7, 8),
            **{f"DER-3I-D9-J{column}-D{power}-zero": (9, 64)
               for power in (2, 6) for column in ("C", "Q")},
            **{f"DER-3I-D9-JC-D{power}-zero": (9, 64) for power in (3, 7)},
            "DER-3I-EULER-CD1-D9-zero": (9, 64),
            "DER-3I-EULER-CD5-D9-zero": (9, 64),
            **{f"DER-3I-LEIBNIZ-TD{power}-D9-zero": (9, 64) for power in (1, 5)},
            **{f"DER-3I-W5-TARGET-D{page}-zero": (page, 64) for page in (19, 23)},
            "DER-3I-CD1-D11-J-zero": (11, 64),
            "DER-3I-AD6-D19-zero": (19, 64),
        },
    }
    zero_claims = [
        item
        for workspace_id in ("ws_2sigma_i", "ws_3sigma_i")
        for item in workspaces[workspace_id].propositions
        if item.kind == "zero-differential" and item.conclusion.get("zero")
    ]
    assert len(zero_claims) == 30
    for workspace_id, facts in expected.items():
        actual = [claim for claim in workspaces[workspace_id].propositions
                  if claim.kind == "zero-differential" and claim.conclusion.get("zero")]
        assert len(actual) == len(facts)
        assert {claim.conclusion["fact_id"]: (claim.conclusion["page"], claim.conclusion["period_stem"])
                for claim in actual} == facts
        nodes = {node.id: node for node in workspaces[workspace_id].classes}
        arrow_claim_ids = {arrow.proposition_id for arrow in workspaces[workspace_id].differentials}
        for claim in actual:
            assert claim.id not in arrow_claim_ids  # A zero constraint is never a fake differential.
            assert claim.conclusion["source_id"] in nodes
            assert claim.source_refs
            fact = claim.conclusion["fact_id"]
            if not fact.startswith("DER-3I-"):
                continue
            metadata = claim.conclusion
            assert claim.status == metadata["admission_status"] == "verified"
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"]
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["source_workspace_id"] == workspace_id
            assert certificate["page"] == metadata["page"]
            assert certificate["premises"]
            assert not {"FN-3I-010", "FN-3I-010-pc"} & set(certificate["premises"])
            if fact.startswith("DER-3I-D9-J") or fact == "DER-3I-CD1-D11-J-zero":
                assert certificate["method"] == "Primitive d3 and negative-source Tate comparison"
                assert certificate["tate_source_bidegree"][1] < 0
                assert certificate["tate_target_bidegree"][1] == metadata["grade"]["filtration"]
                assert metadata["source_component"] == "positive-j"
                assert nodes[metadata["source_id"]].style["j_order"] == 1
            elif fact in {"DER-3I-EULER-CD1-D9-zero", "DER-3I-EULER-CD5-D9-zero"}:
                assert certificate["method"] == "Square-zero on a one-dimensional finite target"
                assert metadata["cycle_constraint"] == "outgoing-only"
                assert metadata["coefficient_scope"] == certificate["coefficient_scope"] == "exact-port"
                assert metadata["e2_components"] == {"S11": 1}
                stem = 9 if fact == "DER-3I-EULER-CD1-D9-zero" else 41
                assert metadata["grade"] == {"stem": stem, "filtration": 1}
                assert certificate["source_survival"]["bidegree"] == [stem, 1]
                assert certificate["source_survival"]["port"] == "0:0"
                assert certificate["finite_target"]["bidegree"] == [stem - 1, 10]
                assert certificate["finite_target"]["pattern"] == "S02"
                assert certificate["finite_target"]["dimension"] == 1
                assert certificate["no_withdrawn_premise"] is True
            elif fact.startswith("DER-3I-LEIBNIZ-TD"):
                assert certificate["method"] == "Two equal Leibniz terms in a finite order-two line"
                assert metadata["cycle_constraint"] == "outgoing-only"
                assert metadata["coefficient_scope"] == "exact-port"
                assert metadata["e2_components"] == {"S13": 1}
                power = 1 if fact == "DER-3I-LEIBNIZ-TD1-D9-zero" else 5
                assert metadata["grade"] == {"stem": 8 * power + 1, "filtration": 3}
                assert certificate["source_survival"]["port"] == "0:0"
                assert certificate["potential_target"]["bidegree"] == [8 * power, 12]
                assert certificate["potential_target"]["port"] == "1:0"
                assert certificate["Leibniz_terms"] == [f"2U k^3 D^{power + 1}"] * 2
                assert certificate["torsion_relation"] == "4kU=0"
                assert certificate["factor_verification"]["status"] == "verified"
                assert certificate["no_withdrawn_premise"] is True
            elif fact.startswith("DER-3I-W5-TARGET-D"):
                assert certificate["method"] in {"Verified target survival", "Same-page square-zero"}
                assert metadata["cycle_constraint"] == "outgoing-only"
                assert metadata["coefficient_scope"] == "exact-port"
                assert metadata["e2_components"] == {"S73": 1}
                assert metadata["grade"] == {"stem": 43, "filtration": 23}
                assert certificate["source"]["port"] == "0:0"
                assert certificate["boundary_from_page"] == 24 and not certificate["survival_override"]
                assert claim.premise_ids == ["formal_prop_der-3i-leibniz-w5-d23_1"]
            elif fact == "DER-3I-AD6-D19-zero":
                assert certificate["method"] == "Earlier target differential"
                assert metadata["coefficient_scope"] == "exact-port"
                assert metadata["grade"] == {"stem": 46, "filtration": 2}
                assert certificate["target_differential"] == {"source": [45, 21], "target": [44, 32], "page": 11}
                assert claim.premise_ids == ["formal_prop_der-3i-euler-cd1-d11_1"]
                assert not certificate["survival_override"]
            else:
                assert certificate["method"] == "Actual E2 product and finite target enumeration"
                assert certificate["derivation"]
    for claim in zero_claims:
        metadata = claim.conclusion
        assert metadata["source_id"]
        assert metadata["e2_components"]
        assert metadata["period_stem"] in {8, 16, 64}
        assert metadata["forward_period"] == {
            "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
        }
    differential_statements = {
        item.statement
        for workspace_id in ("ws_2sigma_i", "ws_3sigma_i")
        for item in workspaces[workspace_id].propositions
        if item.kind == "differential"
    }
    assert all(item.statement not in differential_statements for item in zero_claims)


def test_hidden_h2_product_evidence_survives_atlas_transport_without_losing_the_four_layer():
    # Only the order-two ideal 4W/8W is reduced to F4 here, not W/8 itself.
    zeta, zeta2 = F4Element.parse("zeta"), F4Element.parse("zeta^2")
    assert zeta + zeta2 == F4Element.one()
    for scalar in ("0", "1", "zeta", "zeta^2"):
        value = F4Element.parse(scalar)
        assert (zeta * value == zeta2 * value) is (scalar == "0")

    project = migrate_project(demo_project())
    checked = set()
    for workspace in project.workspaces:
        if workspace.id != "ws_2sigma_i" and workspace.settings.get("atlas_transport", {}).get(
                "source_workspace_id") != "ws_2sigma_i":
            continue
        arrow = next(d for d in workspace.differentials
                     if d.id.endswith("formal_diff_two_d5_h2_sum_derived"))
        claim = next(p for p in workspace.propositions if p.id == arrow.proposition_id)
        target = next(c for c in workspace.classes if c.id == arrow.target_id)
        evidence = claim.conclusion["actual_product_certificate"]
        assert evidence["status"] == "verified"
        assert evidence["coefficient_ring"] == "W(F4)"
        assert evidence["nonzero_product"] == "x^2 h2^2=4kD"
        assert evidence["zero_product"] == "y^2 h2^2=0"
        assert evidence["omega_weight_exponents"] == {"y^2 h2^2": 1, "4kD": 2}
        assert evidence["weight_difference_mod_2"] == 1
        assert "970-983" in evidence["source_refs"][0]
        assert "Remark rmk:h2ext" in claim.conclusion["derivation"]
        assert arrow.page == 5
        assert target.style["e2_pattern"] == "I00"
        assert target.style["two_valuation"] == claim.conclusion["target_two_valuation"] == 2
        checked.add(workspace.id)
    assert checked == {"ws_2sigma_i", "ws_q8-ro-a0-b2", "ws_q8-ro-a2-b2"}


def test_two_sigma_d5_basis_complement_is_derived_not_assumed_zero():
    project = migrate_project(demo_project())
    workspace = next(item for item in project.workspaces if item.id == "ws_2sigma_i")
    classes = {item.id: item for item in workspace.classes}
    props = {item.id: item for item in workspace.propositions}
    derived = next(item for item in workspace.differentials if item.id == "formal_diff_two_d5_y2_derived")
    source, target = classes[derived.source_id], classes[derived.target_id]
    assert (source.grade.stem, source.grade.filtration) == (14, 2)
    assert (target.grade.stem, target.grade.filtration) == (13, 7)
    assert source.style["e2_pattern"] == "I62Y"
    assert target.style["e2_pattern"] == "I13"
    assert derived.page == 5 and derived.period_stem == 16
    assert derived.status == "verified-pattern"
    evidence = props[derived.proposition_id].conclusion
    assert evidence["evidence_kind"] == "Leibniz-derived"
    assert evidence["derived_from"] == ["FN-2I-004"]
    assert derived.label == "FN-2I-004"  # no fabricated printed proposition
    assert len(FORMAL_ARROWS) == 40 and len(DERIVED_FORMAL_ARROWS) == 43
    assert any(row.differential_id == "formal_diff_three_d19_a_D2_euler_forced"
               and row.fact_id == "DER-3I-EULER-AD2-D19" for row in DERIVED_FORMAL_ARROWS)
    assert any(row.differential_id == "formal_diff_three_d11_c_D1_euler_forced"
               and row.fact_id == "DER-3I-EULER-CD1-D11" for row in DERIVED_FORMAL_ARROWS)
    assert any(row.differential_id == "formal_diff_mixed_d17_v_D3_forced"
               and row.fact_id == "DER-MIX-D17-V-D3" for row in DERIVED_FORMAL_ARROWS)
    assert any(row.differential_id == "formal_diff_mixed_d19_x_D4_forced"
               and row.fact_id == "DER-MIX-D19-X-D4" for row in DERIVED_FORMAL_ARROWS)

    odd_zero = props["formal_prop_fn-2i-004-derived-zero"]
    assert odd_zero.conclusion["e2_components"] == {"I62Y": 1}
    assert odd_zero.conclusion["evidence_kind"] == "Leibniz-derived"
    assert odd_zero.status == derived.status
    assert odd_zero.conclusion["grade"] == {"stem": 6, "filtration": 2}
    assert "invertibility on E5, not permanence" in odd_zero.conclusion["derivation"]
    even_zero = props["formal_prop_fn-2i-003-zero"]
    assert even_zero.conclusion["e2_components"] == {"I62X": 1, "I62Y": 1}
    assert even_zero.conclusion["grade"] == {"stem": 14, "filtration": 2}

    # In the source basis (A=x²+y², B=y²), the odd-D block sends A to
    # C+E and B to zero; the even-D block sends A to zero and B to E.
    odd = transition_data(2, [["1", "0"], ["1", "0"]], [])
    even = transition_data(2, [["0", "0"], ["0", "1"]], [])
    assert odd["quotient_rank"] == even["quotient_rank"] == 1
    assert odd["kernel_basis"] == [["0", "1"]]
    assert even["kernel_basis"] == [["1", "0"]]


def test_mixed_low_d5_has_a_positive_filtration_comparison_not_an_extra_open_premise():
    project = migrate_project(demo_project())
    ws = next(w for w in project.workspaces if w.id == "ws_sigma_i_2sigma_j")
    claims = {p.conclusion.get("fact_id"): p for p in ws.propositions}
    low = claims["FN-MIX-003"]
    high = claims["FN-MIX-002"]
    certificate = low.conclusion["comparison_certificate"]
    for claim in (low, high):
        assert_current_mixed_a_binding(project, ws, claim)
    assert certificate["status"] == "verified-comparison-conditional-on-premise"
    assert certificate["scope"] == "source-workspace-comparison"
    assert certificate["premise"] == "FN-MIX-002"
    translation = certificate["translation"]
    assert translation["spectral_sequence"] == "tate"
    ds = 20 * translation["g_exponent"] + 8 * translation["D_exponent"]
    df = 4 * translation["g_exponent"]
    assert (ds, df) == (-8, -8)
    assert certificate["source_bidegree"] == [14 + ds, 10 + df]
    assert certificate["target_bidegree"] == [13 + ds, 15 + df]
    assert min(certificate["source_bidegree"][1], certificate["target_bidegree"][1]) > 0
    assert "4h2=0" in certificate["derivation"]
    assert "not a permanent period" in certificate["derivation"]
    history = low.conclusion["coefficient_proof_history"]
    assert history["source_status"] == "active-proof-with-review"
    assert "coefficient remain under review" in history["source_blockers"][0]

def test_every_formal_d3_family_uses_the_integer_D_three_cycle():
    # The Thom factors do not change d3(D)=0.  A missing period here leaves
    # seven out of eight D translates undrawn in a permanent D^8 block.
    assert all(arrow.period_stem == 8 for arrow in FORMAL_ARROWS if arrow.page == 3)


def test_mixed_d5_affine_branch_keeps_one_parameter_and_its_actual_premises():
    project = migrate_project(demo_project())
    source = next(w for w in project.workspaces if w.id == "ws_sigma_i_2sigma_j")
    claims = {p.conclusion.get("fact_id"): p for p in source.propositions}
    odd = claims["FN-MIX-003"].conclusion["coefficient_parameter"]
    assert claims["FN-MIX-002"].conclusion["coefficient_parameter"] == odd
    assert odd == {"id": "mixed_d5_A", "symbol": "c", "domain": [1, 2, 3],
                   "value": None, "frobenius_power": 0, "proof_binding": MIXED_A_BINDING}
    derived = next(p for p in source.propositions
                   if p.conclusion.get("coefficient_parameter", {}).get("affine_offset") == 1)
    for claim in (claims["FN-MIX-002"], claims["FN-MIX-003"], derived):
        assert_current_mixed_a_binding(project, source, claim)
    assert derived.conclusion["coefficient_parameter"] == {
        **odd, "affine_offset": 1, "expression": "(c+1)",
    }
    assert claims["FN-MIX-002"].conclusion["premise_transport_certificate"]["premise"] == "FN-2I-010"
    assert claims["FN-MIX-004"].conclusion["premise_transport_certificate"]["premise"] == "FN-2I-004"
    images = []
    for workspace in project.workspaces:
        plan = workspace.settings.get("atlas_transport", {})
        if plan.get("source_workspace_id") != source.id:
            continue
        image = next(p for p in workspace.propositions if p.id.endswith(derived.id))
        assert_current_mixed_a_binding(project, workspace, image)
        assert image.conclusion["coefficient_parameter"] == {
            **derived.conclusion["coefficient_parameter"], "frobenius_power": int(plan["reflected"]),
        }
        assert not workspace.settings.get("coefficient_assignments")
        images.append(workspace.id)
    assert len(images) == 5


def test_old_period_tables_remain_source_provenance_in_all_formal_atlas_images():
    project = migrate_project(demo_project())
    expected = {"ws_2sigma_i": "2sigma_i", "ws_3sigma_i": "3sigma_i",
                "ws_sigma_i_2sigma_j": "sigma_i+2sigma_j"}
    checked = set()
    for workspace in project.workspaces:
        source_id = workspace.settings.get("atlas_transport", {}).get("source_workspace_id", workspace.id)
        if source_id not in expected:
            continue
        claims = [p for p in workspace.propositions if p.conclusion.get("related_period_table")]
        assert claims
        for claim in claims:
            table = claim.conclusion["related_period_table"]
            assert table["sector"] == expected[source_id]
            assert table["column"] == "Period"
            assert "table_Q8.tex:" in table["source_ref"]
            if claim.conclusion.get("fact_id", "").startswith("DER-MIX-PHI-D9-"):
                assert table["status"] == "independently-compared"
                assert table["printed_period_stem"] == 32
                assert "D4 is not used as a permanent unit" in table["interpretation"]
                assert "linked pure source" in table["authority"]
                assert claim.status == "verified"
            else:
                assert table["status"] == "historical-review"
                assert "does not override formal_notes.tex" in table["authority"]
                assert "not a claim" in table["interpretation"]
            assert "table_number" not in claim.conclusion
        if source_id == "ws_sigma_i_2sigma_j":
            odd = next(p for p in claims if p.conclusion.get("fact_id") == "FN-MIX-003")
            assert_current_mixed_a_binding(project, workspace, odd)
            assert odd.conclusion["related_period_table"]["status"] == "historical-review"
            assert odd.conclusion["coefficient_proof_history"]["source_status"] == "active-proof-with-review"
            assert "c=zeta" in odd.conclusion["source_conflicts"][0]["conditional_family"]
            mixed_b = next(p for p in claims if p.conclusion.get("fact_id") == "FN-MIX-005")
            assert mixed_b.status == "review"
            assert mixed_b.conclusion["coefficient_parameter"]["value"] is None
            assert "proof_binding" not in mixed_b.conclusion["coefficient_parameter"]
            cycle = mixed_b.conclusion["verified_cycle_subpremise"]
            assert cycle["status"] == "verified" and cycle["runtime_admission"] is False
            assert cycle["source_fact_id"] == "DER-2I-TATE-H2-cycle" and cycle["action"] == "omega"
            conflict = mixed_b.conclusion["source_conflicts"][0]
            assert conflict["kind"] == "mixed-F4-target-choice-not-exhaustive"
            assert conflict["omitted_targets"] == ["P+zeta*Q", "P+zeta^2*Q"]
            assert conflict["runtime_admission"] is False
            assert not workspace.settings.get("coefficient_assignments")
        checked.add(source_id)
    assert checked == set(expected)


def test_formal_d23_source_retains_its_coefficient_two_level():
    project = migrate_project(demo_project())
    workspace = next(item for item in project.workspaces if item.id == "ws_3sigma_i")
    d23 = next(item for item in workspace.differentials if item.label == "FN-3I-010" and item.page == 23)
    source = next(item for item in workspace.classes if item.id == d23.source_id)
    d3 = next(item for item in workspace.differentials if item.label == "FN-3I-001" and item.page == 3)
    d3_source = next(item for item in workspace.classes if item.id == d3.source_id)
    assert source.label == r"2v_1^2Du_{3\sigma_i}"
    assert (source.grade.stem, source.grade.filtration) == (12, 0)
    assert source.style["coefficient_port"] is True
    assert source.style["two_adic_valuation"] == 1
    assert source.style["two_valuation"] == 1  # the page-algebra renderer's coefficient port
    assert source.style["e2_pattern"] == d3_source.style["e2_pattern"] == "S40"
    assert not d3_source.style.get("coefficient_port")
    assert source.id != d3.source_id
    assert not source.archived


def test_formal_sum_targets_have_rank_one_images_in_both_sectors():
    project = migrate_project(demo_project())
    for workspace_id, fact_id in (("ws_3sigma_i", "FN-3I-006"), ("ws_sigma_i_2sigma_j", "FN-MIX-005")):
        workspace = next(item for item in project.workspaces if item.id == workspace_id)
        differential = next(item for item in workspace.differentials if item.label == fact_id and item.linear_map_id)
        linear = next(item for item in workspace.differential_maps if item.id == differential.linear_map_id)
        target = next(item for item in workspace.classes if item.id == differential.target_id)
        target_cell = next(item for item in workspace.cells if item.id == linear.target_cell_id)
        assert target.style["e2_components"] == {"S22Y": 1, "S22H": 1}
        assert "e2_pattern" not in target.style
        assert len(target_cell.basis) == 2
        assert target.coordinates == ["1", "1"]
        assert linear.matrix == [["1"], ["1"]]
        assert transition_data(2, [], linear.matrix)["quotient_rank"] == 1
        expected_status = "verified" if fact_id == "FN-3I-006" else "review"
        assert linear.status == differential.status == expected_status
        assert linear.proposition_id == differential.proposition_id
        claim = next(item for item in workspace.propositions if item.id == differential.proposition_id)
        assert claim.status == expected_status
        if fact_id == "FN-3I-006":
            certificate = claim.conclusion["verification_certificate"]
            assert certificate["status"] == "verified"
            assert "P+Q image has rank one" in certificate["scope"]


def test_two_sigma_declared_basis_sum_is_not_identified_with_y_squared():
    project = migrate_project(demo_project())
    workspace = next(item for item in project.workspaces if item.id == "ws_2sigma_i")
    d5 = next(item for item in workspace.differentials if item.label == "FN-2I-003")
    source = next(item for item in workspace.classes if item.id == d5.source_id)
    target = next(item for item in workspace.classes if item.id == d5.target_id)
    assert source.style["e2_components"] == {"I62X": 1, "I62Y": 1}
    assert target.style["e2_components"] == {"I13X": 1, "I13": 1}
    assert "e2_pattern" not in source.style
    assert "e2_pattern" not in target.style


def test_formal_admission_is_separate_from_written_proofs_and_repeated_patterns():
    project = migrate_project(demo_project())
    ledger = {item["id"]: item for item in load_periodic_fate_ledger()["fact_families"]}
    for workspace in project.workspaces:
        for differential in workspace.differentials:
            if not differential.label.startswith("FN-"):
                continue
            proposition = next(item for item in workspace.propositions if item.id == differential.proposition_id)
            metadata = proposition.conclusion
            assert differential.status == proposition.status
            if differential.label in {"FN-MIX-002", "FN-MIX-003"}:
                # The historical table is not rewritten when current c evidence is bound.
                assert ledger[differential.label]["status"] == "review"
                assert_current_mixed_a_binding(project, workspace, proposition)
                history = metadata["coefficient_proof_history"]
                assert history["source_status"] == "active-proof-with-review"
                assert history["source_blockers"]
                if differential.label == "FN-MIX-002":
                    assert "[TBD]" in " ".join(history["source_blockers"])
            else:
                assert differential.status == ledger[differential.label]["status"]
            assert metadata["admission_status"] == differential.status
            assert metadata["period_is_invertible"] == (metadata["period_stem"] == 64)
            if differential.label == "FN-MIX-005":
                assert differential.status == "review"
                assert metadata["coefficient_parameter"]["value"] is None
                assert metadata["coefficient_parameter"]["domain"] == [1, 2, 3]
                blockers = " ".join(metadata["source_blockers"])
                assert "proof_binding" not in metadata["coefficient_parameter"]
                assert "relative unit in P+bQ remains unresolved" in blockers
                certificate = metadata["nonzero_parameter_certificate"]
                assert certificate["id"] == "DER-MIX-D5-B-NONZERO"
                assert certificate["status"] == "verified"
                assert certificate["parameter_id"] == "mixed_d5_B"
                assert certificate["domain"] == [1, 2, 3] and certificate["value"] is None
            if differential.label == "FN-3I-010":
                assert differential.status == "review"
                assert ledger[differential.label]["source_status"] == metadata["source_status"] == "withdrawn-proof"
                assert ledger[differential.label]["printed_status"] == metadata["printed_source_status"] == "source-proved"
                assert "earlier independently supported propositions prevail" in ledger[differential.label]["authority_reason"]
                assert metadata["period_stem"] == 32
                assert metadata["period_kind"] == "repeated-differential-pattern"


def test_source_proof_editorial_warning_and_machine_check_are_distinct():
    project = migrate_project(demo_project())
    props = {
        item.conclusion.get("fact_id"): item
        for workspace in project.workspaces
        if workspace.id in {"ws_2sigma_i", "ws_3sigma_i", "ws_sigma_i_2sigma_j"}
        for item in workspace.propositions if item.kind == "differential"
    }
    for fact_id in ("FN-2I-019", "FN-2I-020", "FN-2I-021"):
        metadata = props[fact_id].conclusion
        assert props[fact_id].status == "verified"
        assert metadata["source_status"] == "independently-verified"
        assert metadata["source_blockers"] == metadata["machine_verification_pending"] == []
        certificate = metadata["verification_certificate"]
        assert certificate["status"] == "verified"
        assert certificate["method"] == "Published d23 product and finite E21 quotient"
        assert certificate["table_comparison"]["table_period_stem"] == 64
    for fact_id in ("FN-2I-017", "FN-2I-018", "FN-3I-002", "FN-3I-007", "FN-3I-008", "FN-3I-009"):
        metadata = props[fact_id].conclusion
        assert props[fact_id].status == "verified"
        assert metadata["source_status"] == "independently-verified"
        assert metadata["verification_certificate"]["status"] == "verified"
        assert metadata["source_blockers"] == metadata["machine_verification_pending"] == []
    d11_metadata = props["FN-3I-009"].conclusion
    assert d11_metadata["verification_certificate"]["method"] == "C4 restriction detection and finite E11 quotient"
    assert d11_metadata["verification_certificate"]["no_withdrawn_premise"] is True
    assert d11_metadata["period_stem"] == 32 and d11_metadata["period_is_invertible"] is False
    final_metadata = props["FN-3I-010"].conclusion
    assert final_metadata["source_status"] == "withdrawn-proof"
    assert final_metadata["printed_source_status"] == "source-proved"
    assert final_metadata["source_blockers"] and final_metadata["machine_verification_pending"]
    assert final_metadata["source_conflicts"][0]["kind"] == "euler-preimage-exclusion-conflicts-with-recorded-product"
    assert props["FN-3I-010"].status == "review"  # original source status remains provenance only
    for fact_id in ("FN-3I-003", "FN-3I-004", "FN-3I-006"):
        metadata = props[fact_id].conclusion
        assert metadata["source_status"] == "independently-verified"
        assert metadata["source_blockers"] == []
        assert metadata["representation_warning"]
        assert props[fact_id].status == "verified"
        certificate = metadata["verification_certificate"]
        assert certificate["status"] == "verified"
        assert certificate["method"] == "Euler product, actual hidden h2 product, and d5 squared"
        assert "No FN-3I-002, Jan29" in certificate["scope"]
        assert metadata["machine_verification_pending"] == []
    mixed_verified = props["FN-MIX-004"]
    assert mixed_verified.status == "verified"
    assert mixed_verified.conclusion["source_status"] == "independently-verified"
    assert mixed_verified.conclusion["source_blockers"] == []
    assert mixed_verified.conclusion["machine_verification_pending"] == []
    assert mixed_verified.conclusion["premise_transport_certificate"]["status"] == "verified"
    assert mixed_verified.conclusion["verification_certificate"]["method"] == "omega-transported Euler product and target survival"
    assert "coefficient_normalization" not in mixed_verified.conclusion
    corrected = props["FN-MIX-006"]
    metadata = corrected.conclusion
    assert corrected.status == metadata["admission_status"] == "verified"
    assert metadata["source_status"] == "independently-verified"
    assert metadata["source_blockers"] == metadata["machine_verification_pending"] == []
    certificate = metadata["verification_certificate"]
    assert certificate["status"] == "verified"
    assert certificate["method"] == "omega-Euler product and finite E11 target survival"
    assert "FN-2I-009" in certificate["premises"]
    assert not {"FN-MIX-002", "FN-MIX-005", "FN-3I-010"} & set(certificate["premises"])
    assert metadata["printed_source_formula"]["coefficient"] == 1
    assert metadata["printed_source_formula"]["status"] == "review-corrected"
    assert metadata["coefficient_correction"]["normalized_target_unit"] == 3
    assert metadata["coefficient_parameter"]["value"] == 3
    assert metadata["period_stem"] == 64 and metadata["period_is_invertible"] is True
    assert metadata["paired_pattern_stem"] == 32
    mixed_workspace = next(w for w in project.workspaces if w.id == "ws_sigma_i_2sigma_j")
    for fact_id in ("FN-MIX-002", "FN-MIX-003"):
        assert_current_mixed_a_binding(project, mixed_workspace, props[fact_id])
        assert props[fact_id].conclusion["coefficient_proof_history"]["source_status"] == "active-proof-with-review"
    assert "[TBD]" in " ".join(props["FN-MIX-002"].conclusion["coefficient_proof_history"]["source_blockers"])
    mixed_b = props["FN-MIX-005"].conclusion
    assert props["FN-MIX-005"].status == "review"
    assert mixed_b["source_status"] == "active-proof-with-review"
    assert mixed_b["coefficient_parameter"]["domain"] == [1, 2, 3]
    assert mixed_b["coefficient_parameter"]["value"] is None
    assert "proof_binding" not in mixed_b["coefficient_parameter"]
    assert "relative unit in P+bQ remains unresolved" in " ".join(mixed_b["source_blockers"])
    nonzero = mixed_b["nonzero_parameter_certificate"]
    assert nonzero["id"] == "DER-MIX-D5-B-NONZERO" and nonzero["status"] == "verified"
    assert "DER-MIX-EULER-H2-cycle" in nonzero["premises"]
    assert nonzero["domain"] == [1, 2, 3] and nonzero["value"] is None
    assert nonzero["withdrawn_premises_used"] == []


def test_two_sigma_d5_transfer_admission_has_its_own_certificate_not_fn006():
    project = migrate_project(demo_project())
    workspace = next(item for item in project.workspaces if item.id == "ws_2sigma_i")
    claims = {p.id: p for p in workspace.propositions}
    nodes = {n.id: n for n in workspace.classes}
    row = next(d for d in workspace.differentials if d.label == "FN-2I-005")
    claim = claims[row.proposition_id]
    assert row.status == claim.status == "verified"
    assert row.page == 5 and row.period_stem == 16
    assert nodes[row.source_id].style["two_valuation"] == 1
    assert nodes[row.target_id].style["two_valuation"] == 1
    certificate = claim.conclusion["verification_certificate"]
    assert certificate["status"] == "verified"
    assert certificate["method"] == "kernel-subgroup transfer and Leibniz"
    assert "ker(sigma_i)=C4<i>" in certificate["derivation"]
    assert "det(-I_2)=+1" in certificate["derivation"]
    assert "4h2=0" in certificate["derivation"]
    assert "W/4 two-layer survives d3" in certificate["derivation"]
    assert "does not admit FN-2I-006" in certificate["scope"]
    zero = next(p for p in workspace.propositions if p.conclusion.get("fact_id") == "FN-2I-005-zero")
    assert zero.status == "verified" and zero.kind == "zero-differential"
    assert zero.conclusion["verification_certificate"] == certificate
    fn006 = next(d for d in workspace.differentials if d.label == "FN-2I-006")
    assert fn006.status == claims[fn006.proposition_id].status == "verified"
    assert claims[fn006.proposition_id].conclusion["verification_certificate"] != certificate


def test_formal_d3_h1_products_cut_only_the_positive_j_target_at_filtration_six():
    project = migrate_project(demo_project())
    for workspace_id, key, fact_id in (
        ("ws_3sigma_i", "three", "FN-3I-001"),
        ("ws_sigma_i_2sigma_j", "mixed", "FN-MIX-001"),
    ):
        workspace = next(item for item in project.workspaces if item.id == workspace_id)
        nodes = {item.id: item for item in workspace.classes}
        props = {item.id: item for item in workspace.propositions}
        for power, source_pattern, target_pattern, target_j in (
            (1, "S51", "S00", 0), (2, "S62V", "S11", 1), (3, "S73V", "S22H", 1),
        ):
            arrow = next(item for item in workspace.differentials if item.id == f"formal_diff_{key}_d3_h1_{power}_derived")
            source, target = nodes[arrow.source_id], nodes[arrow.target_id]
            assert (source.grade.stem, source.grade.filtration) == (4 + power, power)
            assert (target.grade.stem, target.grade.filtration) == (3 + power, 3 + power)
            assert source.style["e2_pattern"] == source_pattern
            assert target.style["e2_pattern"] == target_pattern
            assert source.style["j_order"] == 0
            assert target.style["j_order"] == target_j
            assert arrow.period_stem == 8 and arrow.page == 3
            assert props[arrow.proposition_id].conclusion["derived_from"] == [fact_id]
            claim = props[arrow.proposition_id]
            assert arrow.status == claim.status == "verified"
            certificate_key = "d3_product_certificate" if key == "three" else "verification_certificate"
            assert claim.conclusion[certificate_key]["status"] == "verified"

        # Admission comes from the independent certificates, not this
        # linear-algebra probe, for both the pure and mixed d3.
        # In coordinates (constant, j-tail),
        # its target image is the tail and the quotient is the constant line.
        assumed_d3_target = transition_data(2, [], [["0"], ["1"]])
        assert assumed_d3_target["quotient_rank"] == 1
        assert assumed_d3_target["quotient_basis"] == [["1", "0"]]
        # The filtration-2 Q family has no such incoming d3 (negative source
        # filtration). This regression prohibits a global S22H tail deletion.
        lower = [item for item in workspace.classes if item.style.get("e2_pattern") == "S22H"
                 and item.grade.filtration == 2 and not item.style.get("formal_notes_occurrence")]
        assert lower and all(item.style.get("j_order", 0) == 0 for item in lower)


def test_formal_chart_sync_is_idempotent_for_endpoint_ports_and_matrices():
    project = migrate_project(demo_project())
    def snapshot():
        return {
            workspace.id: (len(workspace.classes), len(workspace.cells), len(workspace.differential_maps),
                           len(workspace.propositions), len(workspace.differentials))
            for workspace in project.workspaces
        }
    before = snapshot()
    ensure_formal_notes_chart(project)
    assert snapshot() == before


def test_two_sigma_printed_d3_j_mismatch_is_explicit_and_not_admitted():
    project = migrate_project(demo_project())
    workspace = next(item for item in project.workspaces if item.id == "ws_2sigma_i")
    props = {item.id: item for item in workspace.propositions}
    rows = [item for item in workspace.differentials if item.label == "FN-2I-002"]
    assert len(rows) == 2  # Keep both printed equations, not a silent rewrite.
    for row in rows:
        claim = props[row.proposition_id]
        assert row.status == claim.status == "source-proved"
        assert claim.conclusion["source_status"] == "active-proof-with-review"
        blocker = " ".join(claim.conclusion["source_blockers"])
        assert "j D h1^3" in blocker
        assert "constant j coefficient" in blocker
        assert claim.conclusion["machine_verification_pending"]
        assert claim.conclusion["period_stem"] == 8


def test_two_sigma_derived_d3_uses_integer_table_not_the_erroneous_printed_target():
    project = migrate_project(demo_project())
    workspace = next(item for item in project.workspaces if item.id == "ws_2sigma_i")
    props = {item.id: item for item in workspace.propositions}
    nodes = {item.id: item for item in workspace.classes}
    for key, source_pattern, target_pattern in (
        ("v6", "I40", "I33"), ("h1_1", "I51", "I00"),
        ("h1_2", "I62V", "I11"), ("h1_3", "I73V", "I22H"),
    ):
        row = next(item for item in workspace.differentials if item.id == f"formal_diff_two_d3_{key}_derived")
        source, target = nodes[row.source_id], nodes[row.target_id]
        metadata = props[row.proposition_id].conclusion
        assert row.status == "verified-pattern" and row.period_stem == 8
        assert source.style["e2_pattern"] == source_pattern and source.style["j_order"] == 0
        assert target.style["e2_pattern"] == target_pattern and target.style["j_order"] == 1
        assert "FN-2I-002" not in metadata["derived_from"]
        assert "FN-2I-001" in metadata["derived_from"]
        assert metadata["evidence_kind"] == "Leibniz-derived"
        assert metadata["target_component"] == "positive-j"


def test_explicitly_reviewed_formal_claims_do_not_escalate_to_canonical_death():
    project = migrate_project(demo_project())
    for workspace_id, fact_id, page, status in (
        ("ws_2sigma_i", "FN-2I-019", 21, "verified"),
        ("ws_3sigma_i", "FN-3I-010", 23, "review"),
        ("ws_sigma_i_2sigma_j", "FN-MIX-006", 11, "verified"),
    ):
        original = next(item for item in project.workspaces if item.id == workspace_id)
        arrow = deepcopy(next(item for item in original.differentials if item.label == fact_id and item.page == page))
        proposition = deepcopy(next(item for item in original.propositions if item.id == arrow.proposition_id))
        endpoints = deepcopy([item for item in original.classes if item.id in {arrow.source_id, arrow.target_id}])
        sample = Workspace(id="formal-status-audit", name="status audit", classes=endpoints,
                            differentials=[arrow], propositions=[proposition])
        assert arrow.status == proposition.status == status
        # Test the review gate on an isolated copy, even for independently
        # verified production rows; do not downgrade their persisted evidence.
        arrow.status = proposition.status = "review"
        sync_workspace_fates(sample)
        assert all(class_is_live_on_page(sample, node.id, page + 1) for node in endpoints)
        assert all(fate.first_hfpss_death is None for fate in sample.fates)
        # The same isolated nonzero row, when explicitly admitted, does have
        # its usual r-to-r+1 lifecycle.  This checks the policy, not mere text.
        sample.differential_events = []
        arrow.status = proposition.status = "admitted"
        sync_workspace_fates(sample)
        assert all(class_is_live_on_page(sample, node.id, page) for node in endpoints)
        assert all(not class_is_live_on_page(sample, node.id, page + 1) for node in endpoints)
