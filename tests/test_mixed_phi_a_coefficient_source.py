"""Source audit for c=zeta^2; this file does NOT admit a production mixed map.

The finite products use the real F4 arithmetic and action implementation.
The small polynomial reducer uses only the cited mod-2 relations; actual E5
ports separately check that the relevant images have no extra Witt/j layer.
The Tate/Thom existence statement remains a mathematical source premise, not
something a chart test can establish. Local TeX checks skip on machines which
do not have the research-source mirror; runtime/algebra checks still execute.
"""
from dataclasses import asdict
from itertools import product
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.actions import expanded_action_basis, normalized_scalar_ratio
from domain.algebra import F4Element
from domain.migrations import migrate_project
from domain.seed import demo_project


MIXED = "ws_sigma_i_2sigma_j"
THREE = "ws_3sigma_i"
ONE, ZETA, ZETA2 = F4Element.elements()[1:]
ZERO = F4Element.zero()
UNIT = dict(enumerate(F4Element.elements()))
SOURCE_ROOT = ROOT.parents[1]
SOURCE_PATHS = {
    "formal": SOURCE_ROOT / "REU Projects/Note/formal_notes.tex",
    "record": SOURCE_ROOT / "REU Projects/Note/record/note.tex",
    "table": SOURCE_ROOT / "REU Projects/table_Q8.tex",
    "dkllw": SOURCE_ROOT / "arXiv-2209.01830v3/main.tex",
}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


@pytest.fixture(scope="module")
def sources():
    missing = [str(path) for path in SOURCE_PATHS.values() if not path.is_file()]
    if missing:
        pytest.skip("Local mathematical source mirror is unavailable: " + "; ".join(missing))
    return {name: path.read_text(encoding="utf-8") for name, path in SOURCE_PATHS.items()}


def compact(text):
    return re.sub(r"\s+", "", text)


def monomial(**powers):
    return tuple(sorted((name, exponent) for name, exponent in powers.items() if exponent))


def term(coefficient=ONE, **powers):
    return {monomial(**powers): coefficient}


def add(*polynomials):
    result = {}
    for polynomial in polynomials:
        for key, scalar in polynomial.items():
            result[key] = result.get(key, ZERO) + scalar
    return {key: scalar for key, scalar in result.items() if scalar != ZERO}


def multiply(left, right):
    """Raw distributive product; no relation or desired answer is built in."""
    terms = []
    for first, a in left.items():
        for second, b in right.items():
            powers = dict(first)
            for atom, exponent in second:
                powers[atom] = powers.get(atom, 0) + exponent
            terms.append({monomial(**powers): a * b})
    return add(*terms)


def reduce_mod2(polynomial):
    """DKLLW main.tex:943: xy=0 and v1*x^2=y*h1, nothing else."""
    result = []
    for key, scalar in polynomial.items():
        powers = dict(key)
        if powers.get("x", 0) and powers.get("y", 0):
            continue
        while powers.get("x", 0) >= 2 and powers.get("v1", 0):
            powers["x"] -= 2
            powers["v1"] -= 1
            powers["y"] = powers.get("y", 0) + 1
            powers["h1"] = powers.get("h1", 0) + 1
        if powers.get("x", 0) and powers.get("y", 0):
            continue
        result.append({monomial(**powers): scalar})
    return add(*result)


def action_unit(atom, power):
    result = expanded_action_basis(atom, power)
    assert result["status"] == "exact" and not result["unknown_atoms"]
    return UNIT[result["unit"]]


def finite_products():
    # Euler a_j is the omega image of B_i; the source uses omega^2.
    a_j = add(term(action_unit("x", 1), x=1), term(action_unit("y", 1), y=1))
    b_k = add(term(action_unit("x", 2), x=1), term(action_unit("y", 2), y=1))
    q_k = add(term(action_unit("h_1", 2) ** 2, h1=2),
              term(action_unit("x", 2) * action_unit("h_1", 2) * action_unit("v_1", 2),
                   x=1, h1=1, v1=1))
    return reduce_mod2(multiply(a_j, b_k)), reduce_mod2(multiply(a_j, q_k))


def test_omega_squared_weights_match_the_local_convention(sources):
    # Read the independent source convention, not another copy of the action dictionary.
    matches = re.findall(r"\\omega_\*\((D|x|y)\)\s*=\s*\\zeta(?:\^(\d+))?", sources["record"])
    weights = {atom: int(power or 1) for atom, power in matches}
    assert set(weights) == {"D", "x", "y"}
    for atom, weight in weights.items():
        assert action_unit(atom, 2) == ZETA ** (2 * weight)
    assert action_unit("k", 2) == action_unit("h_1", 2) == action_unit("h_2", 2) == ONE
    assert action_unit("v_1", 2) == ONE
    assert action_unit("D", 2) == ZETA


def test_products_are_computed_with_f4_and_only_source_relations(sources):
    source = compact(sources["dkllw"])
    assert r"$h_1y-v_1x^2,$&$xy,$" in source
    image_b, image_q = finite_products()
    assert image_b == add(term(x=2), term(y=2))
    assert image_q == add(term(ZETA, x=1, h1=2), term(ZETA, y=1, h1=2))
    # Omitting the v1*x^2 relation does not accidentally yield the answer.
    a_j = add(term(ZETA, x=1), term(ZETA2, y=1))
    q_k = add(term(h1=2), term(ZETA2, x=1, h1=1, v1=1))
    assert multiply(a_j, q_k) != image_q


def test_local_notes_supply_pure_b_d5_and_the_odd_leibniz_cross_check(sources):
    formal = compact(sources["formal"])
    assert r"d_5(\{x+y\}u_{3\sigma_i})=\{h_1+xv_1\}h_1ku_{3\sigma_i}" in formal
    assert r"d_5(D)=kDh_2" in formal
    assert r"d_5(\{x+y\}Du_{3\sigma_i})=\{yh_2+xh_1v_1\}kDu_{3\sigma_i}+\{h_1+xv_1\}h_1kDu_{3\sigma_i}" in formal
    # The coefficient-one argument also has an actual nonzero detector,
    # not just a statement that the differential is nonzero.
    assert r"x^3D^{2}u_{3\sigma_i}" in formal
    assert r"2v_1^2k^{2}D^{2}" in formal
    assert "theclass$x^2$is$5$-cycle" in formal
    assert "hidden$h_2$extension" in compact(sources["dkllw"])


def test_even_d_translation_uses_two_torsion_not_a_five_cycle(sources):
    dkllw = compact(sources["dkllw"])
    assert r"d_5(D^2)=2D^{-1}gh_2" in dkllw
    assert r"$(-1,1)$&$\{x+y\}\usig$&$\mathbbZ/2$" in dkllw
    # Retain the integer 2 before tensoring with B's actual order-two line.
    # The target coefficient is NOT zero in the ambient Witt context.
    d5_d2_witt_coefficient = 2
    assert d5_d2_witt_coefficient != 0
    assert d5_d2_witt_coefficient % 2 == 0  # (2 k D^2 h2) B = 0, since 2B=0.


def ah2_product():
    # x^2*h2=v1*x^2*h1=y*h1^2; y^2*h2=D^-1*h2^3=x*h1^2.
    return add(reduce_mod2(term(v1=1, x=2, h1=1)), term(x=1, h1=2))


def test_ah2_product_uses_the_integer_relations_instead_of_a_guessed_unit(sources):
    dkllw = compact(sources["dkllw"])
    for relation in (r"h_2x-v_1h_1x", r"h_1y-v_1x^2", r"Dy^2-h_2^2", r"h_1^2Dx-h_2^3"):
        assert relation in dkllw
    assert ah2_product() == add(term(x=1, h1=2), term(y=1, h1=2))


def test_phi_degree_uses_genuine_norm_units_and_the_actual_inverse(sources):
    source = compact(sources["dkllw"])
    assert "normfunctorissymmetricmonoidal" in source
    assert r"1+\sigma_i+\sigma_j+\sigma_k+\mathbb{H}" in source
    assert r"4-4\sigma_i,4-4\sigma_j$and$4-4\sigma_k" in source
    assert r"u_{4\sigma_k}(g^{-1}a_{\H})" in compact(sources["formal"])
    # RO coordinates: 1, sigma_i, sigma_j, sigma_k, H; H has dimension 4.
    norm, u4k, g_inverse, a_h = (1, 1, 1, 1, 1), (4, 0, 0, -4, 0), (-20, 0, 0, 0, 0), (0, 0, 0, 0, -1)
    phi = tuple(sum(entries) for entries in zip(norm, u4k, g_inverse, a_h))
    assert sum(a * b for a, b in zip(phi, (1, 1, 1, 1, 4))) == -16
    # F adds Phi^-1 and a_j. This gives shift (+15,+1), not D^4 periodicity.
    pure_three_k, a_j = (0, 0, 0, -3, 0), (0, 0, -1, 0, 0)
    image = tuple(s - p + e for s, p, e in zip(pure_three_k, phi, a_j))
    assert image == (15, -1, -2, 0, 0)
    assert (-1 + 15, 1 + 1) == (14, 2)
    assert (-2 + 15, 6 + 1) == (13, 7)


@pytest.fixture(scope="module")
def runtime(project):
    snapshot = json.dumps(asdict(project), sort_keys=True)
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""return {settingsAfter: ws.settings, sourceEdges: edges
      .filter(e => ['FN-3I-005','FN-3I-006'].includes(e.diff.label))
      .map(e => {const pair=algebra.endpoints(e.diff); return {
        id:e.diff.id,fact:e.diff.label,source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
        sourceLive:algebra.live(pair.source,e.sourceGrade),
        targetLive:algebra.live(pair.target,e.targetGrade),
        targetComponents:pair.target.style.e2_components || {[pair.target.style.e2_pattern]:1}
      };}), page, points: points.length"""
    probes = [("S71", -1, 1), ("S22H", -2, 6), ("S62", 14, 2),
              ("S62V", 14, 2), ("S13", 13, 7), ("S13", 1, 3),
              ("S40", -4, 8)]
    payload = {"project": asdict(project), "workspaces": [THREE, MIXED],
               "pages": [2, 3, 5], "vectorAudit": True,
               "bounds": {"stemMin": -4, "stemMax": 18, "filtrationMin": 0, "filtrationMax": 12},
               "probes": [dict(pattern=p, stem=s, filtration=f) for p, s, f in probes]}
    completed = subprocess.run(["node", "-e", harness.replace(marker, diagnostics)],
                               cwd=ROOT, input=json.dumps(payload), text=True, encoding="utf-8",
                               capture_output=True, check=True, timeout=120)
    assert json.dumps(asdict(project), sort_keys=True) == snapshot
    result = {row["id"]: {page["page"]: page for page in row["pages"]}
              for row in json.loads(completed.stdout)}
    for workspace in (THREE, MIXED):
        expected = next(w.settings for w in project.workspaces if w.id == workspace)
        for page in result[workspace].values():
            assert page["settingsAfter"] == expected
            assert not page["conflicts"] and page["blockedFromPage"] is None
    return result


def ports(runtime, workspace, page, pattern, stem, filtration):
    return set(next(p["ports"] for p in runtime[workspace][page]["probes"]
                    if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))


def test_pure_source_is_an_actual_live_coefficient_one_d5_not_a_hypothesis(project, runtime):
    workspace = next(w for w in project.workspaces if w.id == THREE)
    row = next(d for d in workspace.differentials if d.id == "diff_three_d5_xyD2")
    claim = next(p for p in workspace.propositions if p.id == row.proposition_id)
    assert row.label == "FN-3I-005" and row.status == claim.status == "verified"
    assert row.period_stem == 16 and not claim.conclusion["period_is_invertible"]
    edge = next(e for e in runtime[THREE][5]["sourceEdges"]
                if e["fact"] == "FN-3I-005" and (e["source"]["stem"], e["source"]["filtration"]) == (-1, 1))
    assert (edge["target"]["stem"], edge["target"]["filtration"]) == (-2, 6)
    assert edge["admitted"] and edge["sourceLive"] and edge["targetLive"]
    assert edge["coefficient"]["resolved"] and edge["coefficient"]["value"] == 1
    assert edge["targetComponents"] == {"S22H": 1}
    assert ports(runtime, THREE, 5, "S71", -1, 1) == {"0:0"}
    assert ports(runtime, THREE, 5, "S22H", -2, 6) == {"0:0"}
    # x^2(kQ)=2Uk^2 is a nonzero direction, so an unknown F4 unit cannot
    # be silently normalized: its coefficient is detected by x^2.
    assert "1:0" in ports(runtime, THREE, 5, "S40", -4, 8)
    assert [unit for unit in (ONE, ZETA, ZETA2) if unit * ONE == ONE] == [ONE]
    odd = next(e for e in runtime[THREE][5]["sourceEdges"]
               if e["fact"] == "FN-3I-006" and (e["source"]["stem"], e["source"]["filtration"]) == (7, 1))
    assert odd["admitted"] and odd["sourceLive"] and odd["targetLive"]
    assert odd["targetComponents"] == {"S22Y": 1, "S22H": 1}


def test_mixed_e5_source_and_target_are_finite_but_e2_cell_is_not(runtime):
    assert ports(runtime, MIXED, 5, "S62", 14, 2) == {"0:0"}
    assert ports(runtime, MIXED, 5, "S13", 13, 7) == {"0:0"}
    assert ports(runtime, MIXED, 5, "S13", 1, 3) == {"0:0"}
    # Do not mistake the A direction for the whole E2 cell: its separate
    # S62V bo-series direction exists on E2 and is a primitive d3 source.
    assert ports(runtime, MIXED, 2, "S62V", 14, 2)
    assert not ports(runtime, MIXED, 5, "S62V", 14, 2)


@pytest.mark.parametrize("alpha", (ONE, ZETA, ZETA2))
def test_common_thom_series_unit_cancels_on_actual_finite_lines(runtime, alpha):
    source_ports = ports(runtime, MIXED, 5, "S62", 14, 2)
    target_ports = ports(runtime, MIXED, 5, "S13", 13, 7)
    image_b, image_q = finite_products()
    source_base = image_b[monomial(x=2)]
    target_base = image_q[monomial(x=1, h1=2)] * action_unit("k", 2)
    # Arbitrary coefficients in the first three positive-j layers contribute
    # zero on both actual finite lines. This is the quotient by (j), not a
    # truncation declaration for all the other series in the same chart.
    for tail in product(F4Element.elements(), repeat=3):
        series = (alpha, *tail)
        s = add(*(term(a * source_base) for n, a in enumerate(series) if f"0:{n}" in source_ports))
        t = add(*(term(a * target_base) for n, a in enumerate(series) if f"0:{n}" in target_ports))
        assert t[()] * s[()].inverse() == ZETA
    assert normalized_scalar_ratio(next(k for k, v in UNIT.items() if v == alpha),
                                   next(k for k, v in UNIT.items() if v == alpha * ZETA)) == 2


def test_odd_and_even_transport_agree_with_the_affine_leibniz_rule(project):
    image_b, image_q = finite_products()
    even = image_q[monomial(x=1, h1=2)]
    # P=h2*B; Ah2=T follows from xy=0, xh2=v1*xh1,
    # yh1=v1*x^2, Dy^2=h2^2, and Dx*h1^2=h2^3 (main.tex:943-949).
    p_image = image_b[monomial(x=2)] * ah2_product()[monomial(x=1, h1=2)]
    odd = even + p_image
    assert (odd, even) == (ZETA2, ZETA)
    workspace = next(w for w in project.workspaces if w.id == MIXED)
    claim = next(p for p in workspace.propositions if p.conclusion.get("fact_id") == "DER-MIX-D5-A-EVEN")
    offset = claim.conclusion["coefficient_parameter"]["affine_offset"]
    assert even == odd + UNIT[offset]
    assert [c for c in (ONE, ZETA, ZETA2) if c + UNIT[offset] == even] == [ZETA2]
    # omega^2(D^n) is present at BOTH endpoints; it cancels even for odd n.
    for n in range(-2, 7):
        weight = action_unit("D", 2) ** n
        target = even if n % 2 == 0 else odd
        assert weight * target * weight.inverse() == target
    # In the odd cross-check the numerator BEFORE dividing by the source
    # unit is 1, not zeta^2: F(kD(P+Q))=alpha*T*k*D^3.
    assert action_unit("D", 2) * odd == ONE
    assert ONE * action_unit("D", 2).inverse() == ZETA2


def test_printed_table_coefficients_are_reversed_historical_provenance(sources):
    odd = next(line for line in sources["table"].splitlines()
               if "$(6,2)$" in line and r"u_{\sigma_i+2\sigma_j}" in line)
    even = next(line for line in sources["table"].splitlines()
                if "$(14,2)$" in line and r"u_{\sigma_i+2\sigma_j}" in line)
    assert r"$\zeta\{x+y\}" in odd and r"$\zeta^2\{x+y\}" in even
    image_b, image_q = finite_products()
    assert image_q[monomial(x=1, h1=2)] != ZETA2
    assert image_q[monomial(x=1, h1=2)] + image_b[monomial(x=2)] != ZETA


def test_source_audit_does_not_fix_c_or_promote_production_rows(project):
    mixed_images = [w for w in project.workspaces if w.id == MIXED or
                    w.settings.get("atlas_transport", {}).get("source_workspace_id") == MIXED]
    assert len(mixed_images) == 6
    for workspace in mixed_images:
        assert "mixed_d5_A" not in workspace.settings.get("coefficient_assignments", {})
        declarations = [p.conclusion["coefficient_parameter"] for p in workspace.propositions
                        if p.conclusion.get("coefficient_parameter", {}).get("id") == "mixed_d5_A"]
        assert declarations and all(item.get("value") is None for item in declarations)
        rows = [d for d in workspace.differentials
                if d.label in {"FN-MIX-002", "FN-MIX-003", "DER-MIX-D5-A-EVEN"}]
        assert len(rows) == 3 and all(d.status == "review" for d in rows)


def test_new_audit_json_matches_computation_without_claiming_runtime_admission(project):
    path = ROOT / "backend/data/review/mixed_phi_a_coefficient.v1.json"
    evidence = json.loads(path.read_text(encoding="utf-8"))
    image_b, image_q = finite_products()
    even = image_q[monomial(x=1, h1=2)]
    odd = even + image_b[monomial(x=2)]
    assert UNIT[evidence["coefficient_value"]] == odd
    assert UNIT[evidence["even_coefficient_value"]] == even
    assert evidence["coefficient_parameter_id"] == "mixed_d5_A"
    assert evidence["runtime_admission"] is False
    assert evidence["integration_requirements"]["not_yet_integrated"] is True
    pure = next(w for w in project.workspaces if w.id == THREE)
    source = evidence["source_differential"]
    row = next(d for d in pure.differentials if d.id == source["differential_id"])
    assert source["fact_id"] == row.label == "FN-3I-005"
    assert source["page"] == row.page == 5
    assert evidence["transport"]["common_Thom_unit"]["chosen_value"] is None
    assert evidence["historical_comparison"]["rows"] == [
        {"line": 511, "D_power": 1, "printed_coefficient": "zeta", "current_convention_coefficient": str(odd)},
        {"line": 512, "D_power": 2, "printed_coefficient": "zeta^2", "current_convention_coefficient": str(even)},
    ]
