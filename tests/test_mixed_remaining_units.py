"""Keep unresolved relative units separate from a document drawing default.

These tests check exact F4 algebra, source identities and audit consistency.
They do not turn a rank-one map or a finite exclusion argument into a proof
of a normalized unit. Local TeX mirrors are optional, not runtime inputs.
"""
from itertools import product
import json
from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.algebra import F4Element
from domain.cell_linear_algebra import in_span, matrix_rank, matrix_vector_product, nullspace
from domain.formal_notes_chart import _DERIVED_EVIDENCE, FORMAL_ARROWS


AUDIT = ROOT / "backend/data/review/mixed_remaining_units.v1.json"
FIELD = F4Element.elements()
ZERO, ONE, ZETA, ZETA2 = FIELD
PARAMETERS = {
    "mixed_d5_B", "mixed_d17_VD3", "mixed_d19_XD4",
    "mixed_d11_R_D2", "mixed_d11_R_D6", "mixed_d19_R_D5",
}


@pytest.fixture(scope="module")
def evidence():
    return json.loads(AUDIT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def local_sources():
    base = ROOT.parents[1]
    paths = {
        "formal": base / "REU Projects/Note/formal_notes.tex",
        "record": base / "REU Projects/Note/record/note.tex",
        "table": base / "REU Projects/table_Q8.tex",
        "dkllw": base / "arXiv-2209.01830v3/main.tex",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        pytest.skip("Local research-source mirrors unavailable: " + "; ".join(missing))
    return {name: re.sub(r"\s+", "", path.read_text(encoding="utf-8"))
            for name, path in paths.items()}


def test_six_units_remain_numerically_unresolved(evidence):
    assert evidence["schema_version"] == 1
    assert evidence["status"] == "underdetermined"
    assert evidence["runtime_admission"] is False
    assert evidence["numeric_units"] == []
    parameters = evidence["parameters"]
    assert len(parameters) == len(PARAMETERS)
    assert {item["parameter_id"] for item in parameters} == PARAMETERS
    for item in parameters:
        assert item["value"] is None
        assert item["domain"] == [1, 2, 3]
        assert item["numeric_status"] == "unresolved"
        assert item["source_refs"] and item["gap"] and item["runtime_rows"]
        default = item["document_default"]
        assert default["value"] == 1
        assert default["status"] == "document-adopted-only"
        assert default["source_refs"]
    for guard in ("assign_settings", "infer_unit_from_rank_or_convergence",
                  "adopt_document_one_as_proof", "share_R_d11_block_parameter"):
        assert evidence["admission_guards"][guard] is False


@pytest.mark.parametrize("encoded", [1, 2, 3])
def test_inverse_and_entire_kernel_use_actual_f4_for_each_b(encoded, evidence):
    b = FIELD[encoded]
    cases = {case["b"]: case for case in evidence["derived_constraints"]["b_d21"]["cases"]}
    case = cases[encoded]
    assert b * FIELD[case["inverse"]] == ONE
    assert FIELD[case["inverse"]] == b.inverse()
    assert [FIELD[index] for index in case["kernel_vector"]] == [ONE, b]
    matrix = [["1", str(b.inverse())]]
    assert matrix_rank(matrix) == 1
    kernel = nullspace(matrix)
    assert len(kernel) == 1 and in_span(["1", str(b)], kernel)
    actual = {tuple(str(x) for x in vector)
              for vector in product(FIELD, repeat=2)
              if matrix_vector_product(matrix, [str(x) for x in vector]) == ["0"]}
    expected = {(str(scale), str(scale * b)) for scale in FIELD}
    assert actual == expected
    # Known P coefficient is one; compatibility uniquely sets Q to b^-1.
    assert {unit for unit in FIELD if ONE + b * unit == ZERO} == {b.inverse()}


@pytest.mark.parametrize("encoded", [1, 2, 3])
def test_positive_j_kernel_is_separate_from_constant_line(encoded, evidence):
    b = FIELD[encoded]
    audit = evidence["derived_constraints"]["b_d21"]
    assert audit["operation"] == "inverse"
    assert audit["new_independent_parameter"] is False
    assert "j F4[[j]]" in audit["completed_kernel"]
    # A finite truncation checks the claimed algebra of evaluation at j=0;
    # the permanent lift and target J-torsion remain cited source premises.
    for p0, q0, q1, q2 in product(FIELD, repeat=4):
        image = p0 + b.inverse() * q0
        assert (image == ZERO) == (q0 == p0 * b)
        # Arbitrary positive-j coefficients do not alter this evaluation.
        assert (p0 + b.inverse() * (q0 + ZERO * q1 + ZERO * q2)) == image


@pytest.mark.parametrize("encoded", [1, 2, 3])
def test_frobenius_preserves_inverse_relation_without_fixing_b(encoded, evidence):
    b = FIELD[encoded]
    assert (b.inverse()) ** 2 == (b ** 2).inverse() == b ** -2
    assert ONE + b ** 2 * (b.inverse()) ** 2 == ZERO
    assert evidence["derived_constraints"]["galois"]["numeric_value_forced"] is False
    assert evidence["derived_constraints"]["galois"]["self_fixed_mixed_basis_asserted"] is False


def test_c_certificate_does_not_narrow_the_other_six_domains(evidence):
    prerequisite = evidence["fixed_prerequisite"]
    assert prerequisite["parameter_id"] == "mixed_d5_A"
    assert FIELD[prerequisite["value"]] == ZETA2
    assert FIELD[prerequisite["even_value"]] == ZETA2 + ONE == ZETA
    assert all(ZETA2 * b != ZERO and (ZETA2 + ONE) * b != ZERO for b in FIELD[1:])
    assert prerequisite["parameter_id"] not in PARAMETERS


def test_r_d11_blocks_are_separate_and_all_late_degrees_are_correct(evidence):
    entries = {item["parameter_id"]: item for item in evidence["parameters"]}
    d2, d6 = entries["mixed_d11_R_D2"], entries["mixed_d11_R_D6"]
    assert d2["runtime_rows"] == d6["runtime_rows"] == ["formal_diff_document_mixed_d11_r_D2"]
    assert (d2["source_D_residue_mod_8"], d6["source_D_residue_mod_8"]) == (2, 6)
    assert d2["same_object_period_stem"] == d6["same_object_period_stem"] == 64
    assert d2["parameter_id"] != d6["parameter_id"]
    # Derive degrees from R=(-1,3), V=(0,2), X=(-3,3), Q=(2,2),
    # with k=(-4,4), D=(8,0), instead of merely comparing stored endpoints.
    base = {"R": (-1, 3), "V": (0, 2), "X": (-3, 3), "Q": (2, 2)}
    cases = [
        ("mixed_d17_VD3", 17, ("V", 0, 3), ("R", 4, 5)),
        ("mixed_d19_XD4", 19, ("X", 0, 4), ("V", 5, 6)),
        ("mixed_d11_R_D2", 11, ("R", 0, 2), ("Q", 3, 3)),
        ("mixed_d11_R_D6", 11, ("R", 0, 6), ("Q", 3, 7)),
        ("mixed_d19_R_D5", 19, ("R", 0, 5), ("Q", 5, 7)),
    ]
    def degree(spec):
        name, k, d = spec
        s, f = base[name]
        return [s - 4 * k + 8 * d, f + 4 * k]
    for ident, page, source, target in cases:
        item = entries[ident]
        assert item["source_bidegree"] == degree(source)
        assert item["target_bidegree"] == degree(target)
        assert degree(target) == [degree(source)[0] - 1, degree(source)[1] + page]
        if "nonzero_audit" in item:
            assert item["nonzero_audit"] in evidence["nonzero_audits"]


def test_existing_named_d11_r_actually_has_x_source(evidence):
    trap, = evidence["runtime_naming_traps"]
    assert trap["parameter_id"] == "mixed_d11_R"
    assert trap["actual_source"] == "X=x^3u"
    assert trap["not_the_source"] == "R=x^2h1u"
    assert set(trap["must_not_reuse_for"]) == {"mixed_d11_R_D2", "mixed_d11_R_D6"}
    for power, row in ((2, "formal_diff_fn-mix-006_1"), (6, "formal_diff_mixed_d11_r_D6_sibling")):
        certificate = _DERIVED_EVIDENCE[row]
        assert certificate["coefficient_parameter"]["id"] == trap["parameter_id"]
        assert certificate["coefficient_parameter"]["value"] == trap["verified_value"] == 3
        assert certificate["source_survival"]["bidegree"] == [8 * power - 3, 3]
        assert certificate["source_survival"]["e2_pattern"] == "S53"
    b_rows = [row for row in FORMAL_ARROWS if row.fact_id == "FN-MIX-005"]
    assert [(row.source_stem, row.source_filtration, row.page) for row in b_rows] == [(7, 1, 5), (15, 1, 5)]


def test_degenerate_detectors_do_not_assign_units(evidence):
    detectors = {item["multiplier"]: item for item in evidence["degenerate_detectors"]}
    assert set(detectors) == {"x^2", "h1", "h2"}
    assert all(item["numeric_constraint"] is None for item in detectors.values())
    assert "d5(x^2)=0" in detectors["x^2"]["equations"]
    assert "d3(zeta^2 Ck)=2k^2U" in detectors["x^2"]["equations"]
    # Only the scalar of the stated Witt-valued d3 image is checked in F4;
    # this is not an assertion that the Witt factor 2 vanishes.
    assert ZETA2 * ZETA == ONE
    assert detectors["h1"]["result"] == "primitive-bo-boundary"
    assert "Qh2=Ch1h2=0" in detectors["h2"]["equations"]


def test_original_sources_distinguish_current_and_wrong_branches(local_sources, evidence):
    assert r"2\zetav_1^2ku_{\sigma_i+2\sigma_j}" in local_sources["formal"]
    old = local_sources["record"]
    assert "Nowweassume$a=1$" in old
    assert r"d_3(\{h_1+xv_1\}u_{\sigma_i+2\sigma_j})=0" in old
    branch = evidence["historical_branch_exclusion"]
    assert branch["explicit_assumption_line"] == 1158
    assert branch["branch_mixed_d3_C"] == "0"
    assert branch["current_mixed_d3_C"] == "2zeta kU"
    assert r"$D^2x^2$&$d$&$(14,2)$" in local_sources["dkllw"]
    assert r"x^2h_1D^nu_{\sigma_i}" in local_sources["dkllw"]
    assert r"2k^{m+1}v_1^2D^nu_{\sigma_i}" in local_sources["dkllw"]


def test_document_rows_are_adoptions_not_numeric_certificates(local_sources, evidence):
    table = local_sources["table"]
    for fragment in (
        r"$(15,3)$&$\{x^2+y^2\}h_1D^2u_{\sigma_i+2\sigma_j}$&11",
        r"$(24,2)$&$\{x+y\}h_1D^3u_{\sigma_i+2\sigma_j}$&17",
        r"$(29,3)$&$\{x+y\}h_2^2D^3u_{\sigma_i+2\sigma_j}$&19",
        r"$(39,3)$&$\{x^2+y^2\}h_1D^5u_{\sigma_i+2\sigma_j}$&19",
    ):
        assert fragment in table
    # Bh2^2D^3 has degree (29,3), i.e. XD4, not XD3=(21,3).
    assert (-1 + 2 * 3 + 3 * 8, 1 + 2 * 1) == (29, 3)
    assert (-3 + 4 * 8, 3) == (29, 3)
    assert evidence["numeric_units"] == []
