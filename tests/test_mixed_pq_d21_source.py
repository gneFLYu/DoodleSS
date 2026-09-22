"""Independent source audit, not production admission, for the mixed P/Q d21.

E2 incidence comes from the production fundamental-domain catalogue, not the
new JSON. F4 kernels use the actual linear-algebra implementation. The late
mixed quotient is inspected only under explicitly labelled c/b hypotheses in
deep copies; no proposed d21 is inserted. Permanent lifts and naturality are
source premises, distinguished from machine-checkable degrees and products.
"""
from copy import deepcopy
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
from domain.algebra import F4Element
from domain.cell_linear_algebra import in_span, matrix_rank, matrix_vector_product, nullspace
from domain.e2_import import verified_e2_classes
from domain.migrations import migrate_project
from domain.seed import demo_project
from test_mixed_phi_a_coefficient_source import action_unit, add, finite_products, monomial, multiply, reduce_mod2, term


MIXED, TWO = "ws_sigma_i_2sigma_j", "ws_2sigma_i"
ROW = "formal_diff_two_d21_h2_low_derived"
AUDIT = ROOT / "backend/data/review/mixed_pq_d21_source.v1.json"
ONE, ZETA, ZETA2 = F4Element.elements()[1:]
ZERO = F4Element.zero()
TARGETS = {"Y": (33, 23), "gY": (53, 27)}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


@pytest.fixture(scope="module")
def evidence():
    return json.loads(AUDIT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sources():
    paths = {
        "dkllw": ROOT.parents[1] / "arXiv-2209.01830v3/main.tex",
        "formal": ROOT.parents[1] / "REU Projects/Note/formal_notes.tex",
        "table": ROOT.parents[1] / "REU Projects/table_Q8.tex",
    }
    missing = [str(p) for p in paths.values() if not p.is_file()]
    if missing:
        pytest.skip("Local research-source mirror unavailable: " + "; ".join(missing))
    return {name: re.sub(r"\s+", "", path.read_text(encoding="utf-8"))
            for name, path in paths.items()}


def e2_candidates(stem, filtration):
    """Exhaust all stored residues and integer D8/forward-g translations."""
    result = []
    for record in verified_e2_classes("sigma_i"):
        difference = filtration - record.filtration
        if difference < 0 or difference % 4:
            continue
        g = difference // 4
        horizontal = stem - record.stem - 20 * g
        if horizontal % 64:
            continue
        result.append({"pattern": record.pattern_key, "bidegree": [stem, filtration],
                       "g_exponent": g, "D8_exponent": horizontal // 64,
                       "representative": record.label})
    assert len({item["pattern"] for item in result}) == len(result)
    return result


def incoming_inventory(target):
    stem, filtration = target
    return {r: e2_candidates(stem + 1, filtration - r) for r in range(2, filtration + 1)}


def label_degree(label):
    match = re.fullmatch(r"(Uh1\^2|Uh1|P|Q|A|X|C|T)(k(?:\^(\d+))?)?(D(?:\^(-?\d+))?)?", label)
    assert match, label
    base = {"P": (2, 2), "Q": (2, 2), "A": (-2, 2), "X": (-3, 3),
            "C": (1, 1), "T": (1, 3), "Uh1": (5, 1), "Uh1^2": (6, 2)}[match[1]]
    k = int(match[3] or 1) if match[2] else 0
    d = int(match[5] or 1) if match[4] else 0
    return (base[0] - 4 * k + 8 * d, base[1] + 4 * k)


@pytest.mark.parametrize("name", TARGETS)
def test_all_earlier_incoming_bidegrees_are_enumerated_from_actual_e2(name, evidence):
    stem, filtration = TARGETS[name]
    assert {item["pattern"] for item in e2_candidates(stem, filtration)} == {"S53"}
    actual = incoming_inventory((stem, filtration))
    # This pattern is independently generated, rather than copied from JSON.
    expected_nonempty = {5, 9, 13, 17, 21} | ({25} if name == "gY" else set())
    assert {r for r, cells in actual.items() if cells} == expected_nonempty
    assert all(not actual[r] for r in range(2, filtration + 1, 2))
    ledger = {item["page"]: item for item in evidence["incoming_inventories"][name]}
    assert set(ledger) == set(range(3, filtration + 1, 2))
    for page, item in ledger.items():
        assert item["source_bidegree"] == [stem + 1, filtration - page]
        expected = {(cell["pattern"], tuple(cell["bidegree"])) for cell in actual[page]}
        recorded = {(cell["pattern"], tuple(cell["bidegree"])) for cell in item["e2_candidates"]}
        assert recorded == expected
        assert all(label_degree(cell["label"]) == tuple(item["source_bidegree"])
                   for cell in item["e2_candidates"])
    assert {cell["pattern"] for cell in actual[21]} == {"S22Y", "S22H"}
    # The g shift changes filtration as well as stem; never treat it as D4.
    assert TARGETS["gY"] == (TARGETS["Y"][0] + 20, TARGETS["Y"][1] + 4)


def test_source_survival_inventory_uses_actual_target_degrees_and_patterns(evidence):
    assert not e2_candidates(35, 0)  # Only possible nonnegative incoming source.
    for source in ("P", "Q"):
        entries = evidence["source_survival"][source]["outgoing_inventory"]
        assert {entry["page"] for entry in entries} == set(range(3, 21, 2))
        for entry in entries:
            target = (33, 2 + entry["page"])
            assert tuple(entry["target_bidegree"]) == target
            # The mixed target often exists even when pure-preimage
            # naturality proves zero. Do not infer zero from missing dots.
            actual = e2_candidates(*target)
            assert len(actual) == 1
            if "target_pattern" in entry:
                assert entry["target_pattern"] == actual[0]["pattern"]
                assert label_degree(entry["target_label"]) == target


def test_e21_audit_does_not_assert_later_e2_sources_are_empty():
    assert e2_candidates(54, 27 - 25)  # An E2 candidate exists for d25 into gY.
    assert not e2_candidates(54, 27 - 27)
    # The E21 claim only needs r<21; later E2 candidates are not asserted
    # absent. This audit does not use a strong line to force the d21.


def test_local_sources_supply_pure_two_sigma_d21_and_its_product_detector(project, sources):
    workspace = next(w for w in project.workspaces if w.id == TWO)
    row = next(d for d in workspace.differentials if d.id == ROW)
    claim = next(p for p in workspace.propositions if p.id == row.proposition_id)
    nodes = {n.id: n for n in workspace.classes}
    source, target = nodes[row.source_id], nodes[row.target_id]
    assert row.status == claim.status == "verified" and row.label == "FN-2I-019"
    assert row.page == 21 and row.period_stem == 64
    assert (source.grade.stem, source.grade.filtration) == (35, 1)
    assert (target.grade.stem, target.grade.filtration) == (34, 22)
    assert target.style["e2_components"] == {"I62X": 1, "I62Y": 1}
    assert "Multiplication by permanent g" in claim.conclusion["derivation"]
    assert r"h_2kD^{7}u_{2\sigma_i}" in sources["formal"]
    assert r"\{x^2+y^2\}k^{6}D^{10}u_{2\sigma_i}" in sources["formal"]
    assert (35 + 20, 1 + 4, 34 + 20, 22 + 4) == (55, 5, 54, 26)
    assert r"$(35,1)$" in sources["table"] and r"h_2D^4u_{2\sigma_i}" in sources["table"]


def test_omega_euler_coefficients_cancel_without_normalizing_the_mixed_basis(sources):
    # a_i*omega(A_i): the mod-2 mixed-module relation x^3u=y^3u is
    # B*x^2=B*y^2 together with xy=0, not an equality of integer monomials.
    assert r"\{x+y\}\usig\cdotx^2-\{x+y\}\usig\cdoty^2" in sources["dkllw"]
    a_i = add(term(x=1), term(y=1))
    omega_a = add(term(action_unit("x", 1) ** 2, x=2),
                  term(action_unit("y", 1) ** 2, y=2))
    image = reduce_mod2(multiply(a_i, omega_a))
    assert set(image) == {monomial(x=3), monomial(y=3)}
    euler_scalar = image[monomial(x=3)] + image[monomial(y=3)]
    source_scalar = action_unit("h_2", 1) * action_unit("D", 1) ** 4
    target_scalar = euler_scalar * action_unit("k", 1) ** 5 * action_unit("D", 1) ** 7
    assert euler_scalar == ONE
    assert source_scalar == target_scalar == ZETA2
    assert target_scalar * source_scalar.inverse() == ONE


@pytest.mark.parametrize("b", (ONE, ZETA, ZETA2))
def test_actual_f4_matrix_has_kernel_p_plus_bq_for_every_nonzero_b(b):
    matrix = [["1", str(b.inverse())]]
    assert matrix_rank(matrix) == 1
    kernel = nullspace(matrix)
    assert len(kernel) == 1
    assert in_span(["1", str(b)], kernel)
    zero_vectors = {tuple(str(v) for v in vector)
                    for vector in product(F4Element.elements(), repeat=2)
                    if matrix_vector_product(matrix, [str(v) for v in vector]) == ["0"]}
    expected = {(str(t), str(t * b)) for t in F4Element.elements()}
    assert zero_vectors == expected and len(zero_vectors) == 4
    assert matrix_vector_product(matrix, ["1", "0"]) == ["1"]
    assert matrix_vector_product(matrix, ["0", "1"]) == [str(b.inverse())]


@pytest.mark.parametrize("b", (ONE, ZETA, ZETA2))
def test_matrix_preserves_every_tested_positive_j_direction(b):
    # The source premise JY=0 handles the whole completed ideal. These exact
    # finite matrices audit arbitrary prefixes, not a truncation of that ideal.
    for tail_length in range(1, 5):
        matrix = [["1", str(b.inverse()), *(["0"] * tail_length)]]
        kernel = nullspace(matrix)
        expected = [["1", str(b), *(["0"] * tail_length)]]
        expected.extend([["0"] * (n + 2) + ["1"] + ["0"] * (tail_length - n - 1)
                         for n in range(tail_length)])
        assert matrix_rank(matrix) == 1 and len(kernel) == tail_length + 1
        assert matrix_rank(expected) == tail_length + 1
        assert all(in_span(vector, kernel) for vector in expected)


def test_permanent_witt_lift_j_comes_from_the_proposition_not_the_plot_key(sources):
    dkllw = sources["dkllw"]
    start = dkllw.index(r"\begin{prop}\label{prop:inftybo}")
    end = dkllw.index(r"\end{proof}", start)
    proof = dkllw[start:end]
    assert r"D^mv_1^{4l}" in proof and "survivetothe$E_{\\infty}$-page" in proof
    assert r"d_3(D^{m+3}g^{-1}v_1^{4l-2}h_1^{n+4})=D^mv_1^{4l}h_1^{n+3}" in proof
    # m=-1,l=1,n=-3 in the proposition's Tate formula:
    m, ell, n = -1, 1, -3
    assert (m + 3, 4 * ell - 2, n + 4, m, 4 * ell, n + 3) == (2, 2, 1, -1, 4, 0)
    # Degrees of D^2 g^-1 v1^2 h1 -> v1^4 D^-1 are (1,-3)->(0,0).
    assert (16 - 20 + 4 + 1, -4 + 1) == (1, -3)
    assert (8 - 8, 0) == (0, 0)
    assert r"\begin{lem}\label{lem:tateisorange}" in dkllw
    assert r"\begin{met}\label{met:Tatemethod}" in dkllw
    # The actual order-two module relation makes jX=0, since X=x^2B.
    assert r"\{x+y\}\usig\cdotv_1^4" in dkllw
    assert reduce_mod2(multiply(add(term(x=1), term(y=1)), term(x=2))) == term(x=3)
    assert r"$(-1,1)$&$\{x+y\}\usig$&$\mathbbZ/2$" in dkllw


def run_chart(payload):
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    extra = r"""return {sourceD21: edges.filter(e=>e.diff.id===input.sourceId).map(e=>{
        const pair=algebra.endpoints(e.diff); return {source:e.sourceGrade,target:e.targetGrade,
          admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
          sourceLive:algebra.live(pair.source,e.sourceGrade),targetLive:algebra.live(pair.target,e.targetGrade)};
      }), settingsAfter:ws.settings, page, points: points.length"""
    completed = subprocess.run(["node", "-e", harness.replace(marker, extra)], cwd=ROOT,
                               input=json.dumps(payload), capture_output=True, text=True,
                               encoding="utf-8", check=True, timeout=180)
    return {row["id"]: {page["page"]: page for page in row["pages"]}
            for row in json.loads(completed.stdout)}


@pytest.fixture(scope="module")
def pure_runtime(project):
    return run_chart({"project": asdict(project), "workspaces": [TWO], "pages": [21],
                      "sourceId": ROW, "vectorAudit": True,
                      "bounds": {"stemMin": 30, "stemMax": 58, "filtrationMin": 0, "filtrationMax": 29}})


def test_pure_source_is_actually_applied_on_e21_with_a_nonzero_target(pure_runtime):
    page = pure_runtime[TWO][21]
    assert not page["conflicts"] and page["blockedFromPage"] is None
    edge = next(e for e in page["sourceD21"] if e["source"]["stem"] == 35)
    assert edge["source"]["filtration"] == 1
    assert (edge["target"]["stem"], edge["target"]["filtration"]) == (34, 22)
    assert edge["admitted"] and edge["sourceLive"] and edge["targetLive"]
    assert edge["coefficient"]["resolved"] and edge["coefficient"]["value"] == 1


@pytest.fixture(scope="module")
def hypothesis_runtime(project):
    original = asdict(project)
    before = json.dumps(original, sort_keys=True)
    image_b, image_q = finite_products()
    c = image_q[monomial(x=1, h1=2)] + image_b[monomial(x=2)]
    assert c == ZETA2  # independently derived source audit; no production assignment
    field_codes = {value: index for index, value in enumerate(F4Element.elements())}
    results = {}
    for b in (ONE, ZETA, ZETA2):
        hypothetical = deepcopy(original)
        workspace = next(w for w in hypothetical["workspaces"] if w["id"] == MIXED)
        workspace["settings"].setdefault("coefficient_assignments", {}).update(
            mixed_d5_A=field_codes[c], mixed_d5_B=field_codes[b])
        claims = {p["id"]: p for p in workspace["propositions"]}
        matrices = {m["id"]: m for m in workspace["differential_maps"]}
        assumed = [d for d in workspace["differentials"] if d["page"] == 5
                   and d["label"] in {"FN-MIX-002", "FN-MIX-003", "DER-MIX-D5-A-EVEN", "FN-MIX-005"}]
        assert len(assumed) == 5
        for row in assumed:
            row["status"] = "admitted"
            claim = claims[row["proposition_id"]]
            claim["status"] = "admitted"
            claim["conclusion"]["test_hypothesis"] = True
            if row["linear_map_id"]:
                matrices[row["linear_map_id"]]["status"] = "admitted"
        assert all(p["conclusion"].get("test_hypothesis") for p in workspace["propositions"]
                   if p["conclusion"].get("fact_id") in {"FN-MIX-002", "FN-MIX-003"})
        # The proposed d21 has not been manufactured in this copied chart.
        assert {d["id"] for d in workspace["differentials"]} == {
            d["id"] for w in original["workspaces"] if w["id"] == MIXED for d in w["differentials"]}
        payload = {"project": hypothetical, "workspaces": [MIXED], "pages": [2, 6, 21],
                   "vectorAudit": True,
                   "bounds": {"stemMin": 30, "stemMax": 58, "filtrationMin": 0, "filtrationMax": 29},
                   "probes": [dict(pattern=p, stem=s, filtration=f) for p, s, f in (
                       ("S53", 33, 23), ("S53", 53, 27), ("S22Y", 34, 2), ("S22H", 34, 2),
                       ("S62", 34, 6), ("S62V", 34, 6), ("S62", 34, 14), ("S62V", 34, 14))],
                   "vectorProbes": [{"components": {"S22Y": 1, "S22H": field_codes[b]},
                                     "stem": s, "filtration": f} for s, f in ((34, 2), (54, 6))]}
        results[str(b)] = run_chart(payload)[MIXED]
        for page in results[str(b)].values():
            assert page["settingsAfter"] == workspace["settings"]
    assert json.dumps(original, sort_keys=True) == before
    assert json.dumps(asdict(project), sort_keys=True) == before
    return results


def get_ports(page, pattern, stem, filtration):
    return set(next(p["ports"] for p in page["probes"]
                    if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))


@pytest.mark.parametrize("b", ("1", "zeta", "zeta^2"))
def test_conditional_e21_endpoints_survive_and_j_target_direction_is_zero(hypothesis_runtime, b):
    pages = hypothesis_runtime[b]
    assert all(not p["conflicts"] and p["blockedFromPage"] is None for p in pages.values())
    for s, f in TARGETS.values():
        assert get_ports(pages[2], "S53", s, f) == {"0:0"}
        assert get_ports(pages[21], "S53", s, f) == {"0:0"}
    assert get_ports(pages[21], "S22Y", 34, 2) == {"0:0"}
    assert {"0:0", "0:1"} <= get_ports(pages[21], "S22H", 34, 2)
    for page in (6, 21):
        low, high = pages[page]["vectorProbes"]
        assert low["live"]  # P+bQ is a genuine low direction before d21.
        assert not high["live"]  # g(P+bQ)D4=d5(BD7), not gP=gQ=0.
    for f in (6, 14):
        assert not get_ports(pages[6], "S62", 34, f)
        assert not get_ports(pages[6], "S62V", 34, f)


def test_audit_is_not_runtime_admission_and_keeps_completed_tail_separate(evidence, project):
    assert evidence["runtime_admission"] is False
    assert evidence["workspace_id"] == MIXED
    for name, target in TARGETS.items():
        assert evidence["targets"][name]["bidegree"] == list(target)
        assert evidence["targets"][name]["pattern"] == "S53"
        assert evidence["targets"][name]["finite_port"] == "0:0"
    workspace = next(w for w in project.workspaces if w.id == MIXED)
    assert "mixed_d5_A" not in workspace.settings.get("coefficient_assignments", {})
    assert "mixed_d5_B" not in workspace.settings.get("coefficient_assignments", {})
    assert not any(p.conclusion.get("fact_id") == evidence["id"] for p in workspace.propositions)
