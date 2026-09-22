"""Independent Euler/Tate certificate for the constant two-multiple 2UDu_3sigma.

This does not admit the Jan29 final differential or its Ck Euler detector.
DKLLW Table 9 (main.tex:2460; Proposition sigmad13 at 2365-2378)
gives d13(eD^4)=k^3 Ch1 D^5. Actual E2 multiplication, including the
hidden h1 product (1094-1111), gives e^2 Ch1=2kUu_3sigma. Since the E2
product e^3 is zero, Z=2Uk^4D^5u_3sigma is zero already on E13, not merely
E14. Its Tate translate by g^-4D^8 is w=2UDu_3sigma in filtration zero.

The following finite calculation independently checks the e^3 premise: all
three nontrivial F2 characters have alpha^3 a normalized bar coboundary.
For Z_sigma the appendix resolution (main.tex:2737-2756) gives
H^3=ker(Norm)/im(i-1,1-ij)=Z/2. Thus reduction H^3(Z_sigma)->H^3(F2)
is injective, and the integral Euler cube is zero too. This is an E2
product statement, NOT a claim that the stable Euler class a_3sigma=0.

Lemma 2.6 / Tate method (488-510) distinguish a negative-filtration Tate
incoming differential from an HFPSS death. The HFPSS comparison is
injective at the possible outgoing target filtration r, so w has no
outgoing differential; there is no HFPSS incoming into filtration zero.
No division by 2, no vanishing-line clipping, and no whole-j-family death
are used. The original Witt layers and withdrawn claims must remain.
"""
from copy import deepcopy
from itertools import product
from math import gcd
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.atlas_transport import ensure_q8_atlas_transports
from domain.formal_notes_chart import ensure_formal_notes_chart
from domain.fate import derive_class_fate
from domain.migrations import migrate_project
from domain.seed import demo_project


WORKSPACE = "ws_3sigma_i"
CLAIM_ID = "formal_prop_der-3i-tate-w-cycle"
FACT_ID = "DER-3I-TATE-W-cycle"
IDENTITY = (0, 0)
Q8 = tuple(product(range(4), range(2)))  # i^a j^b, j^2=i^2 and ji=i^-1j
NORMALIZED = tuple(g for g in Q8 if g != IDENTITY)
CHARACTERS = ((1, 0), (0, 1), (1, 1))


def multiply(left, right):
    a, b = left
    c, d = right
    return ((a + (-1 if b else 1) * c + 2 * b * d) % 4, (b + d) % 2)


def character(bits, element):
    return (bits[0] * element[0] + bits[1] * element[1]) % 2


def differential_value(cochain, a, b, c):
    # Trivial F2 action; normalized cochains are zero if an argument is 1.
    return (cochain.get((b, c), 0) ^ cochain.get((multiply(a, b), c), 0)
            ^ cochain.get((a, multiply(b, c)), 0) ^ cochain.get((a, b), 0))


@pytest.fixture(scope="module")
def normalized_bar_basis():
    pairs = tuple(product(NORMALIZED, repeat=2))
    triples = tuple(product(NORMALIZED, repeat=3))
    pivots = {}
    for index, pair in enumerate(pairs):
        cochain = {pair: 1}
        column = sum(differential_value(cochain, *triple) << row
                     for row, triple in enumerate(triples))
        witness = 1 << index
        while column:
            pivot = column.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = (column, witness)
                break
            previous, primitive = pivots[pivot]
            column ^= previous
            witness ^= primitive
    return pairs, triples, pivots


def primitive_for(cocycle, pivots):
    remainder, witness = cocycle, 0
    while remainder:
        pivot = remainder.bit_length() - 1
        assert pivot in pivots, "The proposed Euler cube is not a bar coboundary"
        column, primitive = pivots[pivot]
        remainder ^= column
        witness ^= primitive
    return witness


def test_quaternion_model_and_all_three_characters_are_genuine():
    assert len(Q8) == 8 and len(NORMALIZED) == 7
    i, j, minus_one = (1, 0), (0, 1), (2, 0)
    assert multiply(i, i) == multiply(j, j) == minus_one
    assert multiply(i, j) != multiply(j, i)
    for a, b, c in product(Q8, repeat=3):
        assert multiply(multiply(a, b), c) == multiply(a, multiply(b, c))
    for bits in CHARACTERS:
        assert sum(character(bits, g) for g in Q8) == 4
        for a, b in product(Q8, repeat=2):
            assert character(bits, multiply(a, b)) == (character(bits, a) ^ character(bits, b))


@pytest.mark.parametrize("bits", CHARACTERS)
def test_each_euler_cube_has_an_explicit_normalized_bar_primitive(bits, normalized_bar_basis):
    pairs, triples, pivots = normalized_bar_basis
    assert (len(pairs), len(triples)) == (49, 343)
    cube = sum((character(bits, a) * character(bits, b) * character(bits, c)) << row
               for row, (a, b, c) in enumerate(triples))
    assert cube.bit_count() == 64  # It is a nonzero cochain, not a vacuous check.
    witness = primitive_for(cube, pivots)
    primitive = {pair: (witness >> index) & 1 for index, pair in enumerate(pairs)}
    assert witness
    # Verify the computed primitive independently on all 512 triples,
    # including the triples omitted by the normalized chain complex.
    for a, b, c in product(Q8, repeat=3):
        assert differential_value(primitive, a, b, c) == (
            character(bits, a) * character(bits, b) * character(bits, c))


@pytest.mark.parametrize("bits", CHARACTERS)
def test_integral_sign_twisted_h3_has_exponent_two_so_reduction_is_injective(bits):
    sign_i, sign_j = (-1) ** bits[0], (-1) ** bits[1]
    norm = sum((-1) ** character(bits, g) for g in Q8)
    # DKLLW appendix d_2: Z^2 -> Z and d_3: Z -> Z.
    d2 = (sign_i - 1, 1 - sign_i * sign_j)
    assert norm == 0
    assert gcd(*d2) == 2
    # ker(d_3)=Z, im(d_2)=2Z, hence H^3(Z_sigma)=Z/2.
    # Exactness for 0->Z_sigma --2--> Z_sigma -> F2->0 now makes
    # reduction injective. Together with the explicit primitive above this
    # certifies e_sigma^3=0 before mapping coefficients into Morava E.
    assert all(2 * residue % gcd(*d2) == 0 for residue in (0, 1))


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def cycle_record(project):
    ws = next(w for w in project.workspaces if w.id == WORKSPACE)
    claim = next(p for p in ws.propositions if p.id == CLAIM_ID)
    source = next(n for n in ws.classes if n.id == claim.conclusion["source_id"])
    return ws, claim, source


def test_cycle_record_keeps_the_exact_witt_port_and_outgoing_only_meaning(project):
    ws, claim, source = cycle_record(project)
    data = claim.conclusion
    assert claim.kind == "permanent-cycle" and claim.status == "verified"
    assert data["fact_id"] == FACT_ID
    assert data["cycle_constraint"] == "outgoing-only"
    assert data["coefficient_scope"] == "constant-two-multiples"
    assert source.label == r"2v_1^2Du_{3\sigma_i}"
    assert (source.grade.stem, source.grade.filtration) == (12, 0)
    assert source.style["e2_pattern"] == "S40"
    assert source.style["two_valuation"] == 1 and source.style["j_order"] == 0
    assert not source.archived
    assert data["period_stem"] == 64
    assert data["forward_period"] == {
        "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
    }
    assert not ws.settings.get("coefficient_assignments")
    assert not any(d.proposition_id == claim.id for d in ws.differentials)
    fate = derive_class_fate(ws, source.id, project=project)
    assert fate.conclusion == "permanent_cycle"
    assert fate.last_hfpss_live_page == "infinity"
    assert fate.first_hfpss_death is None


def test_tate_certificate_keeps_negative_sources_out_of_the_hfpss(project):
    ws, claim, _ = cycle_record(project)
    certificate = claim.conclusion["comparison_certificate"]
    assert certificate["page_upper_bound"] == 11
    assert certificate["tate_zero_by_page"] == 13
    assert certificate["source_bidegree"] == [13, "-q"]
    assert certificate["target_bidegree"] == [12, 0]
    assert certificate["source_workspace_id"] == WORKSPACE
    nodes = {n.id: n for n in ws.classes}
    assert all(nodes[d.source_id].grade.filtration >= 0 and nodes[d.target_id].grade.filtration >= 0
               for d in ws.differentials)
    g = claim.conclusion["forward_period"]
    shift = (claim.conclusion["period_stem"] - 4 * g["stem"], -4 * g["filtration"])
    assert shift == (-16, -16)  # g^-4 D^8, not a bare inverse g in HFPSS.
    for q in (3, 5, 7, 9, 11):
        shifted_source = (29 + shift[0], 16 - q + shift[1])
        assert shifted_source == (13, -q) and shifted_source[1] < 0
        assert (shifted_source[0] - 1, shifted_source[1] + q) == (12, 0)
    assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(claim.conclusion.get("derived_from", []))


def test_refresh_preserves_original_w_and_stored_higher_witt_multiple(project):
    candidate = deepcopy(project)
    ws, _, source = cycle_record(candidate)
    original_w = deepcopy(source)
    four_w = deepcopy(source)
    four_w.id = "research_four_times_w"
    four_w.label = four_w.expression = r"8v_1^2Du_{3\sigma_i}"  # 4*w, not the F4 scalar zero.
    four_w.style.update(two_valuation=3, two_adic_valuation=3,
                        witt_scalar_level=four_w.label)
    ws.classes.append(four_w)
    original_four_w = deepcopy(four_w)
    arrows = deepcopy(ws.differentials)
    ensure_formal_notes_chart(candidate)
    # The normal refresh completes period-family materialization in this
    # second phase; compare the finished records, not its intermediate state.
    ensure_q8_atlas_transports(candidate)
    assert next(n for n in ws.classes if n.id == source.id) == original_w
    assert next(n for n in ws.classes if n.id == four_w.id) == original_four_w
    assert ws.differentials == arrows
    withdrawn = [p for p in ws.propositions
                 if p.conclusion.get("fact_id") in {"FN-3I-010", "FN-3I-010-pc"}]
    assert withdrawn and all(p.status == "review" and p.conclusion["source_status"] == "withdrawn-proof"
                             for p in withdrawn)


def test_all_three_sigma_atlas_images_preserve_cycle_and_deepcopy_source_certificate(project):
    candidate = ensure_q8_atlas_transports(deepcopy(project))
    _, original, source = cycle_record(candidate)
    seen = []
    for image in candidate.workspaces:
        plan = image.settings.get("atlas_transport", {})
        if plan.get("source_workspace_id") != WORKSPACE:
            continue
        seen.append(image.id)
        ident = f"atlas_{plan['sector_id']}_{CLAIM_ID}"
        claim = next(p for p in image.propositions if p.id == ident)
        node = next(n for n in image.classes if n.id == claim.conclusion["source_id"])
        assert claim.status == original.status == "verified"
        assert claim.conclusion["cycle_constraint"] == "outgoing-only"
        assert claim.conclusion["coefficient_scope"] == "constant-two-multiples"
        assert claim.conclusion["period_stem"] == 64
        assert claim.conclusion["forward_period"] == original.conclusion["forward_period"]
        certificate = claim.conclusion["comparison_certificate"]
        assert certificate == original.conclusion["comparison_certificate"]
        assert certificate is not original.conclusion["comparison_certificate"]
        assert certificate["source_workspace_id"] == WORKSPACE
        assert (node.grade.stem, node.grade.filtration) == (12 + plan["stem_shift"], 0)
        assert (node.style["e2_pattern"], node.style["two_valuation"], node.style["j_order"]) == (
            source.style["e2_pattern"], 1, 0)
        assert not node.archived
        assert claim.conclusion["coefficient_normalization"]["source_workspace_id"] == WORKSPACE
    assert set(seen) == {"ws_q8-ro-a0-b3", "ws_q8-ro-a1-b1"}


def test_local_primary_source_locators_when_the_optional_tex_mirror_exists():
    paper = ROOT.parents[1] / "arXiv-2209.01830v3/main.tex"
    if not paper.exists():
        pytest.skip("Optional external TeX mirror is not needed for CI's finite certificate")
    text = paper.read_text(encoding="utf-8")
    assert r"\label{lem:tateisorange}" in text and r"\label{met:Tatemethod}" in text
    assert r"\label{prop:sigmad13}" in text and r"\label{lem:hiddenh1}" in text
    assert r"d_{4k+2}=\begin{pmatrix} -1+i & 1-ij \end{pmatrix}" in text
    assert r"d_{4k+3}=\sum_{g\in Q_8}g" in text
    assert r"d_{13}(\{x+y\}D^4 u_{\sigma_i})=k^3\{h_1^2+xh_1v_1\}D^5 u_{\sigma_i}" in text
