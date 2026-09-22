"""Lightweight provenance checks; no external TeX path or chart runtime needed."""
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "backend/data/review/table_q8_source_audit.v1.json"
sys.path.insert(0, str(ROOT / "backend"))
from domain.formal_notes_chart import (
    FORMAL_ARROWS, DERIVED_FORMAL_ARROWS, _DERIVED_EVIDENCE,
    _DERIVED_ENDPOINT_STYLES, _TATE_CYCLE_EVIDENCE, _VERIFIED_FORMAL_CERTIFICATES,
    ZERO_AND_PERMANENT_CLAIMS,
)


def audit():
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_artifact_pins_source_and_disclaims_runtime_admission():
    data = audit()
    assert data["schema_version"] == 1 and data["status"] == "review-required"
    assert data["runtime_admission"] is False
    assert "not a mathematical verification" in data["scope"]
    source = data["source"]
    assert source["name"] == "table_Q8.tex" and source["role"] == "local-summary"
    assert source["path"].endswith("/REU Projects/table_Q8.tex")
    assert re.fullmatch(r"[0-9a-f]{64}", source["sha256"])
    assert source["sha256"] == "b5923f0328b9cbf71866779b74af49518e035c7d1584d4dd662f937db0df5bac"
    assert "not imported by the runtime" in data["comparison_sources"]["runtime"]["scope"]


def test_crosswalk_covers_all_49_active_local_ro_table_rows():
    data = audit()
    expected_two = {372, 373, 377, 378, 379, 380, 384, 385, 386,
                    391, 392, 393, 394, 398, 402, 407, 408, 409}
    expected_three = {439, 443, 444, 445, 446, 447, 452, 453, 455, 456, 457, 458, 463, 464, 469, 474}
    expected_mixed = {505, 507, 511, 512, 513, 514, 515, 520, 521, 527, 528, 533, 537, 538, 541}
    coverage = data["coverage"]
    assert [coverage[key] for key in ("two_sigma_rows", "three_sigma_rows", "mixed_rows")] == [18, 16, 15]
    assert coverage["total_rows"] == 18 + 16 + 15 == 49
    assert coverage["additional_review_only_mixed_rows"] == len(data["historical_mixed_rows"]) == 5
    assert coverage["excluded_commented_two_sigma_lines"] == [374, 375]
    assert "not a claim that all rows are mathematically verified" in coverage["scope"]
    for key, expected in (("two_sigma_crosswalk", expected_two),
                          ("three_sigma_crosswalk", expected_three),
                          ("mixed_crosswalk", expected_mixed)):
        rows = data[key]
        assert len(rows) == len(expected)
        assert {row["line"] for row in rows} == expected
        for row in rows:
            s, f = row["source_degree"]
            assert row["target_degree"] == [s - 1, f + row["page"]], row
            assert row["printed_period_stem"] in {8, 16, 32, 64}
            assert row["comparison"]
            assert "formal_lines" in row and "runtime_refs" in row


def test_five_additional_mixed_rows_preserve_formulas_degrees_and_review_status():
    data = audit()
    rows = data["historical_mixed_rows"]
    expected = {
        528: (11, [15, 3], [14, 14], 32),
        533: (17, [24, 2], [23, 19], 64),
        537: (19, [29, 3], [28, 22], 64),
        538: (19, [39, 3], [38, 22], 64),
        541: (21, [34, 2], [33, 23], 64),
    }
    assert len(rows) == 5 and {r["source_line"] for r in rows} == set(expected)
    degrees = {"A": (-2, 2), "B": (-1, 1), "C": (1, 1), "Q": (2, 2),
               "h1": (1, 1), "h2": (3, 1), "k": (-4, 4), "D": (8, 0)}
    crosswalk = {row["line"]: row for row in data["mixed_crosswalk"]}
    for row in rows:
        assert (row["page"], row["source_degree"], row["target_degree"], row["printed_period_stem"]) == expected[row["source_line"]]
        assert row["id"] == f'TQ8-MIX-L{row["source_line"]:04d}'
        assert row["status"] == "historical-review" and row["runtime_admission"] is False
        assert row["coefficient_status"] == "historical-unverified"
        assert row["printed_coefficient"] == "1" and row["sector"] == "sigma_i+2sigma_j"
        assert row["formal_statement_lines"] == []
        independent_facts = {533: "DER-MIX-D17-V-D3", 537: "DER-MIX-D19-X-D4"}
        assert row["runtime_fact_ids"] == ([independent_facts[row["source_line"]]]
                                           if row["source_line"] in independent_facts else [])
        assert row["review_obligations"]
        for side in ("source", "target"):
            assert row[f"{side}_tex"] and "sigma_i" in row[f"{side}_tex"]
            monomial = row[f"{side}_monomial"]
            actual = [sum(degrees[symbol][axis] * exponent for symbol, exponent in monomial.items())
                      for axis in (0, 1)]
            assert actual == row[f"{side}_degree"], (row["id"], side)
        link = crosswalk[row["source_line"]]
        assert link["inventory_id"] == row["id"]
        assert link["comparison"] == ("independently-derived-nonzero-unit"
                                      if row["source_line"] in independent_facts else "additional-historical-row")


def test_mixed_row537_resolves_outgoing_d17_by_independent_cycle_not_historical_admission():
    row = next(r for r in audit()["historical_mixed_rows"] if r["source_line"] == 537)
    partial = row["partial_audit"]
    assert row["status"] == "historical-review" and not row["runtime_admission"]
    assert not partial["runtime_admission"] and row["runtime_fact_ids"] == ["DER-MIX-D19-X-D4"]
    assert "x^3 D^4" in partial["low_source_survival"]["identity"]
    resolved = next(r for r in partial["resolved_obligations"]
                    if r["id"] == "outgoing-d9-of-translated-target")
    assert resolved["status"] == "excluded-by-zero-outgoing"
    assert resolved["certificate_ids"] == ["DER-MIX-PHI-BH-D7-D9-zero"]
    zero = next(r for r in ZERO_AND_PERMANENT_CLAIMS if r[0] == resolved["certificate_ids"][0])
    assert zero[1:3] == ("ws_sigma_i_2sigma_j", "zero-differential")
    assert zero[4:7] == ((56, 2), 9, "verified")
    assert resolved["source_degree"] == [zero[4][0]+6*20-2*64, zero[4][1]+6*4]
    assert resolved["target_degree"] == [47, 35]
    assert len(partial["unresolved_gaps"]) == 1
    gap = partial["unresolved_gaps"][0]
    assert (gap["id"], gap["page"]) == ("exact-nonzero-d19-unit", 19)
    assert gap["source_degree"] == [29, 3] and gap["target_degree"] == [28, 22]
    resolved17 = next(r for r in partial["resolved_obligations"]
                      if r["id"] == "outgoing-d17-of-translated-target")
    assert resolved17["source_degree"] == resolved["source_degree"] == [48, 26]
    assert resolved17["target_degree"] == [47, 43] and resolved17["target_pattern"] == "S73"
    assert resolved17["certificate_ids"] == ["DER-MIX-PHI-CD5-VD7-cycle"]
    cycle = next(r for r in ZERO_AND_PERMANENT_CLAIMS if r[0] == resolved17["certificate_ids"][0])
    assert cycle[1:3] == ("ws_sigma_i_2sigma_j", "permanent-cycle")
    assert cycle[4:7] == ((56, 2), 2, "verified")
    assert partial["forward_g_incoming_inventory"]["nonzero_d19_forced"]
    diff = next(r for r in DERIVED_FORMAL_ARROWS if r.fact_id == "DER-MIX-D19-X-D4")
    proof = _DERIVED_EVIDENCE[diff.differential_id]
    assert "DER-MIX-PHI-CD5-VD7-cycle" in proof["derived_from"]
    assert proof["verification_certificate"]["high_target"]["bidegree"] == [48, 26]
    assert proof["coefficient_parameter"]["id"] == gap["parameter_id"]
    assert proof["coefficient_parameter"]["value"] is None


def test_inventory_does_not_silently_create_canonical_runtime_arrows_or_ledger_facts():
    rows = audit()["historical_mixed_rows"]
    ledger = json.loads((ROOT / "backend/data/review/formal_notes_periodic_fate_ledger.v1.json").read_text(encoding="utf-8"))
    ledger_ids = {fact["id"] for fact in ledger["fact_families"]}
    for row in rows:
        assert row["id"] not in ledger_ids
        matches = [arrow for arrow in FORMAL_ARROWS + DERIVED_FORMAL_ARROWS
                   if arrow.workspace_id == "ws_sigma_i_2sigma_j"
                   and arrow.page == row["page"]
                   and [arrow.source_stem, arrow.source_filtration] == row["source_degree"]
                   and [arrow.target_stem, arrow.target_filtration] == row["target_degree"]]
        independent_facts = {533: "DER-MIX-D17-V-D3", 537: "DER-MIX-D19-X-D4"}
        if row["source_line"] in independent_facts:
            assert len(matches) == 1 and matches[0].fact_id == independent_facts[row["source_line"]]
            independent = row["independent_result"]
            assert independent["status"] == "verified-nonzero-unit"
            assert independent["differential_id"] == matches[0].differential_id
            assert "no value assigned" in independent["coefficient"]
            parameter = _DERIVED_EVIDENCE[matches[0].differential_id]["coefficient_parameter"]
            assert parameter["value"] is None and parameter["domain"] == [1, 2, 3]
        else:
            assert not matches, (row["id"], "An independently implemented row needs an explicit provenance reconciliation.")
    # Merely placing a JSON next to the admission ledger must not wire it into
    # any production loader, migration or automatic directory discovery.
    for module in (ROOT / "backend/domain").glob("*.py"):
        text = module.read_text(encoding="utf-8")
        assert "table_q8_source_audit" not in text, module.name


def test_late_three_sigma_formula_has_correct_degree_but_withdrawn_proof():
    rows = {row["line"]: row for row in audit()["three_sigma_crosswalk"]}
    late = rows[474]
    assert late["source_degree"] == [12, 0] and late["target_degree"] == [11, 23]
    assert late["page"] == 23 and late["formal_lines"] == [811, 848]
    assert late["comparison"] == "formula-agrees-with-withdrawn-proof"
    assert late["claim_status"] == "review" and late["runtime_admission"] is False
    assert "target degree is correct" in late["degree_check"]
    assert "NOT" in late["note"]
    assert rows[469]["formal_lines"] == [851, 860]
    assert rows[469]["claim_status"] == "review" and rows[469]["runtime_admission"] is False


def test_coefficient_disagreements_and_pattern_periods_are_not_silently_resolved():
    data = audit()
    rows = {row["line"]: row for row in data["mixed_crosswalk"]}
    assert rows[511]["table_coefficient"] == "zeta" and rows[511]["formal_coefficient"] == "1"
    assert rows[512]["table_coefficient"] == "zeta^2" and rows[512]["runtime_expression"] == "c+1"
    assert rows[514]["table_coefficient_choice"] == "b=1 in P+bQ"
    assert rows[515]["table_coefficient_choice"] == "b=1 in bQ"
    assert rows[527]["conditional_coefficient"] == "lambda*zeta^2"
    assert "does not assert that D^4 is a permanent unit" in data["period_policy"]["printed_32"]
    assert data["period_policy"]["permanent_horizontal_stem"] == 64
    assert "nonnegative" in data["period_policy"]["forward_family"]["exponents"]


def test_four_mixed_phi_anchors_match_verified_runtime_and_linked_source_proofs():
    # Inspect the production proof records directly: no demo migration or JS
    # rendering is necessary for this bounded provenance regression.
    rows = {row["line"]: row for row in audit()["mixed_crosswalk"]}
    by_id = {arrow.differential_id: arrow for arrow in DERIVED_FORMAL_ARROWS}
    source_powers = {0: 6, 1: 7, 4: 2, 5: 3}
    seen = set()
    for line, powers in ((520, [1, 5]), (521, [0, 4])):
        row = rows[line]
        assert row["runtime_claim_status"] == "verified"
        assert row["comparison"] == "agrees-with-independent-derived-code"
        assert row["proof_method"] == "permanent-Phi-Euler-transport-and-finite-target-survival"
        assert row["runtime_D_powers"] == powers
        assert row["printed_period_stem"] == 32
        assert "D8 and forward g" in row["note"]
        for power in powers:
            diff_id = f"formal_diff_mixed_phi_d9_D{power}"
            arrow, proof = by_id[diff_id], _DERIVED_EVIDENCE[diff_id]
            seen.add(power)
            assert arrow.fact_id == f"DER-MIX-PHI-D9-D{power}"
            assert arrow.fact_id in row["runtime_refs"]
            assert arrow.workspace_id == "ws_sigma_i_2sigma_j" and arrow.status == "verified"
            assert arrow.page == 9 and arrow.period_stem == 64
            assert [arrow.source_stem, arrow.source_filtration] == [8 * power, 2]
            assert [arrow.target_stem, arrow.target_filtration] == [8 * power - 1, 11]
            source_power = source_powers[power]
            suffix = "derived" if source_power % 2 == 0 else "euler_derived"
            source_id = f"formal_diff_three_d9_c_D{source_power}_{suffix}"
            source = by_id[source_id]
            assert source.status == "verified" and source.workspace_id == "ws_3sigma_i"
            coefficient = proof["coefficient_parameter"]
            assert coefficient["source_parameter"] == {
                "workspace_id": "ws_3sigma_i", "parameter_id": coefficient["id"],
                "differential_id": source_id, "page": 9,
            }
            assert coefficient["id"] == _DERIVED_EVIDENCE[source_id]["coefficient_parameter"]["id"]
            assert coefficient["id"].startswith("three_sigma_")
            assert "not a mixed-local parameter or assignment" in proof["coefficient_constraint"]
            assert proof["source_status"] == "independently-verified"
            assert proof["source_blockers"] == proof["withdrawn_dependencies"] == []
            assert proof["verification_certificate"]["status"] == "verified"
            transport = proof["transport_certificate"]
            assert transport["source_differential_id"] == source_id
            assert transport["source_power"] == source_power and transport["action"] == "omega^2"
            assert transport["applied_inverse"] is True and transport["euler_multiplier"] == "a_sigma_j"
            assert transport["final_D_exponent"] == (-8 if power < 2 else 0)
            for side, degree, pattern in (("source", [8 * power, 2], "S02"),
                                          ("target", [8 * power - 1, 11], "S73")):
                certificate = proof[f"{side}_survival"]
                assert certificate["status"] == "verified"
                assert certificate["bidegree"] == degree and certificate["e2_pattern"] == pattern
            assert proof["target_survival"]["nonzero_condition"] == "independent of mixed_d5_A and mixed_d5_B"
            assert "D4 is not used as a permanent unit" in proof["related_period_table"]["interpretation"]
            assert proof["related_period_table"]["printed_period_stem"] == 32
            assert [style["e2_pattern"] for style in _DERIVED_ENDPOINT_STYLES[diff_id]] == ["S02", "S73"]
    assert seen == {0, 1, 4, 5}


def test_mixed_b_exact_unit_remains_unresolved_after_full_f4_nonzero_repair():
    rows = {row["line"]: row for row in audit()["mixed_crosswalk"]}
    for line in (514, 515):
        row = rows[line]
        assert row["runtime_claim_status"] == "review"
        assert row["comparison"] == "printed-formula-agrees-relative-unit-unresolved"
        assert row["proof_gap"] == "mixed-relative-unit-unresolved"
        assert row["original_proof_gap"] == "mixed-F4-target-choice-not-exhaustive"
        assert row["omitted_target_directions"] == ["P+zeta Q", "P+zeta^2 Q"]
        assert row["cycle_subpremise"] == "verified-H2-cycle-and-nonzero-b"
        assert row["repair_certificate_id"] == "DER-MIX-D5-B-NONZERO"
    assert "does not determine b" in rows[514]["note"]
    assert "same unresolved b" in rows[515]["note"]
    h2 = _TATE_CYCLE_EVIDENCE["DER-2I-TATE-H2-cycle"]
    assert h2["source_status"] == "independently-verified"
    assert "FN-2I-009" in h2["derived_from"]
    mixed_b = [arrow for arrow in FORMAL_ARROWS if arrow.fact_id == "FN-MIX-005"]
    assert mixed_b and all(arrow.status == "review" for arrow in mixed_b)


def test_table527_preserves_printed_unit_but_links_two_corrected_verified_anchors():
    row = next(row for row in audit()["mixed_crosswalk"] if row["line"] == 527)
    assert row["comparison"] == "printed-unit-corrected-by-independent-proof"
    assert row["runtime_claim_status"] == "verified"
    assert row["printed_coefficient"] == row["formal_coefficient"] == "1"
    assert row["runtime_coefficient"] == "zeta^2"
    assert row["runtime_source_unit"] == 1 and row["runtime_target_unit"] == 3
    assert row["runtime_D_powers"] == [2, 6] and row["printed_period_stem"] == 32
    assert "zeta^2" not in row["printed_formula"] and "zeta^2" in row["corrected_formula"]
    arrows = FORMAL_ARROWS + DERIVED_FORMAL_ARROWS
    for power, diff_id in ((2, "formal_diff_fn-mix-006_1"),
                           (6, "formal_diff_mixed_d11_r_D6_sibling")):
        matching = [arrow for arrow in arrows if arrow.fact_id == "FN-MIX-006"
                    and arrow.source_stem == 8 * power - 3]
        assert len(matching) == 1
        arrow = matching[0]
        assert arrow.status == "verified" and arrow.workspace_id == "ws_sigma_i_2sigma_j"
        assert arrow.page == 11
        assert [arrow.source_stem, arrow.source_filtration] == [8 * power - 3, 3]
        assert [arrow.target_stem, arrow.target_filtration] == [8 * power - 4, 14]
        proof = _DERIVED_EVIDENCE[diff_id]
        correction = proof["coefficient_correction"]
        assert correction["status"] == "verified"
        assert correction["source_product_unit"] == 2
        assert correction["rotated_premise_unit"] == 1
        assert correction["normalized_target_unit"] == 3
        printed = proof["printed_source_formula"]
        assert printed["coefficient"] == 1 and printed["status"] == "review-corrected"
        assert "formal_notes.tex:972-991" in printed["source_ref"]
        assert "table_Q8.tex:527" in printed["source_ref"]
        parameter = proof["coefficient_parameter"]
        assert parameter["id"] == "mixed_d11_R"
        assert parameter["value"] == 3 and parameter["domain"] == [3]
        # The materializer adds the shared fact certificate after the per-map
        # evidence; inspect that same registry instead of requiring duplication.
        certificate = _VERIFIED_FORMAL_CERTIFICATES[arrow.fact_id]
        assert certificate["status"] == "verified"
        assert proof["derivation"] == certificate["derivation"]
        assert proof["source_status"] == "independently-verified"
        assert proof["source_survival"]["status"] == proof["target_survival"]["status"] == "verified"
        assert proof["target_survival"]["nonzero_condition"] == "independent of mixed_d5_A and mixed_d5_B"
        assert [style["e2_pattern"] for style in _DERIVED_ENDPOINT_STYLES[diff_id]] == ["S53", "S02"]
    assert "independent of mixed c,b" in row["note"]
    assert "D8 and forward g" in row["note"]


def test_table528_conditional_target_boundary_does_not_become_blanket_rejection():
    row = next(row for row in audit()["historical_mixed_rows"] if row["source_line"] == 528)
    assert row["runtime_admission"] is False and row["status"] == "historical-review"
    assert row["runtime_fact_ids"] == []
    obstruction = row["conditional_target_death"]
    assert obstruction["status"] == "conditional-derived-obstruction"
    assert obstruction["conditions"] == {"mixed_d5_A": 1, "mixed_d5_B": "nonzero"}
    assert obstruction["page"] == 9 and obstruction["zero_by_page"] == 10
    assert obstruction["transport"] == {
        "g_exponent": 3, "D_exponent": -8,
        "spectral_sequence": "hfpss", "uses_inverse_g": False,
    }
    assert "not automatic rejection" in obstruction["other_branches"]
    for block in obstruction["blocks"]:
        power = block["D_power"]
        assert power in (2, 6)
        target = [8 * power - 2, 14]
        assert block["proposed_d11_target_degree"] == target
        assert block["d9_target_degree"] == [target[0] - 1, target[1] + 9]
        proof = _DERIVED_EVIDENCE[f"formal_diff_mixed_d9_q_D{power}_derived"]
        assert proof["coefficient_condition"]["parameter_id"] == "mixed_d5_A"
        assert proof["coefficient_condition"]["equals"] == 1
        assert proof["coefficient_parameter"]["inverse_parameter_id"] == "mixed_d5_B"
    assert {block["D_power"] for block in obstruction["blocks"]} == {2, 6}


def test_two_sigma_warning_missing_j_and_equivalent_low_d21_source_are_preserved():
    notes = {row["id"]: row for row in audit()["two_sigma_notes"]}
    assert notes["TQ8-2I-CAPTION"]["source_lines"] == [352, 353]
    assert "Need Correction!" in notes["TQ8-2I-CAPTION"]["text"]
    missing_j = notes["TQ8-2I-L0373"]
    assert missing_j["status"] == "coefficient-ideal-conflict"
    assert missing_j["runtime_admission"] is False and missing_j["fact_id"] == "FN-2I-002"
    assert "j h1^3" in missing_j["correct_primitive_consequence"]
    low = notes["TQ8-2I-L0408"]
    assert low["formal_lines"] == [565, 570] and low["fact_id"] == "FN-2I-020"
    assert low["printed_period_stem"] == 64 and "Dy^2=h2^2" in low["identity"]
    assert "through E23" in notes["TQ8-2I-PCS"]["note"]


def test_two_sigma_crosswalk_links_current_facts_and_retains_short_pattern_caveats():
    rows = {row["line"]: row for row in audit()["two_sigma_crosswalk"]}
    arrows = FORMAL_ARROWS + DERIVED_FORMAL_ARROWS
    known_refs = {arrow.fact_id for arrow in arrows} | {arrow.differential_id for arrow in arrows}
    for row in rows.values():
        assert row["formula"] and "u_2sigma_i" in row["formula"]
        assert row["runtime_refs"] and set(row["runtime_refs"]) <= known_refs
    assert rows[373]["comparison"] == "coefficient-ideal-conflict"
    assert rows[373]["runtime_admission"] is False
    assert "formal_diff_two_d3_v6_derived" in rows[373]["runtime_refs"]
    sibling = rows[386]
    assert sibling["runtime_refs"] == ["FN-2I-013"]
    assert sibling["comparison"] == "agrees-with-repeated-pattern-sibling"
    assert sibling["pattern_stem_shift"] == -32
    for side in ("source", "target"):
        s, f = sibling[f"formal_{side}_degree"]
        assert sibling[f"{side}_degree"] == [s - 32, f]
    assert "not an identification by a permanent D4 unit" in sibling["note"]


def test_two_sigma_low_d21_rows_link_independent_finite_source_audits():
    rows = {row["line"]: row for row in audit()["two_sigma_crosswalk"]}
    expected = {
        407: ("FN-2I-019", "formal_diff_two_d21_h2_low_derived", [35, 1], [34, 22],
              "finite-source-audit-and-forward-g-detection"),
        409: ("FN-2I-021", "formal_diff_two_d21_four_f0_derived", [40, 0], [39, 21],
              "finite-filtration-zero-audit-and-forward-g2-detection"),
    }
    by_id = {arrow.differential_id: arrow for arrow in DERIVED_FORMAL_ARROWS}
    for line, (fact_id, diff_id, source, target, method) in expected.items():
        row, arrow = rows[line], by_id[diff_id]
        assert row["runtime_refs"] == [fact_id, diff_id]
        assert row["runtime_claim_status"] == arrow.status == "verified"
        assert arrow.fact_id == fact_id and arrow.workspace_id == "ws_2sigma_i"
        assert row["source_degree"] == [arrow.source_stem, arrow.source_filtration] == source
        assert row["target_degree"] == [arrow.target_stem, arrow.target_filtration] == target
        assert row["page"] == arrow.page == 21
        assert row["printed_period_stem"] == arrow.period_stem == 64
        assert row["proof_method"] == method
    assert "does not cancel g" in rows[407]["note"]
    assert "not a filtration-zero Tate lift" in rows[409]["note"]
    low = rows[408]
    assert low["runtime_refs"] == ["FN-2I-020"] and low["runtime_claim_status"] == "verified"
    assert "Dy^2=h2^2" in low["identity"] and "retains the Euler-product kernel" in low["note"]


def test_resolved_navigation_does_not_promote_review_premises():
    data = audit()
    ledger = json.loads((ROOT / "backend/data/review/formal_notes_periodic_fate_ledger.v1.json").read_text(encoding="utf-8"))
    facts = {fact["id"]: fact for fact in ledger["fact_families"]}
    findings = data["ledger_navigation_findings"]
    assert {finding["fact_id"] for finding in findings} == {
        "FN-MIX-002", "FN-MIX-003", "FN-MIX-005", "FN-MIX-006", "FN-3I-010",
    }
    for finding in findings:
        assert finding["status"] == "resolved-navigation"
        assert "no premise or runtime admission promotion" in finding["resolution_scope"]
        fact = facts[finding["fact_id"]]
        if finding["fact_id"] == "FN-MIX-006":
            # This fact was subsequently re-proved with a corrected scalar;
            # reference repair itself still supplies no admission evidence.
            independent = finding["later_independent_verification"]
            assert independent["status"] == fact["status"] == "verified"
            assert independent["runtime_coefficient"] == "zeta^2"
            assert "not the navigation fix" in independent["note"]
        else:
            assert fact["status"] == "review"
        for start, end in finding["resolved_formal_ranges"]:
            assert f"{start}-{end}" in fact["source_ref"]
