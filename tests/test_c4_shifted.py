"""Checks for the independent, p-twisted C4 1-sigma page engine."""
from dataclasses import asdict
from itertools import product

import pytest

from backend.domain import c4_integer
from backend.domain.c4_reference import c4_differential_seeds
from backend.domain.c4_shifted import (
    DIFFERENTIAL_PAGES, FAMILIES, Term, cells_in_window, differential,
    differential_components, e2_nonzero, incoming, is_live, module_descriptor,
    normalize_monomial,
)


def terms():
    for family in FAMILIES:
        qs = (0,) if family in ("one", "T2") else range(1 if family == "varpi" else 0, 11)
        for q, d, n, a in product(qs, range(-5, 6), range(3), range(4)):
            yield Term(family, q, d, n, a)


def test_all_nine_literal_shifted_bbhs_differentials():
    seeds = c4_differential_seeds(True)
    assert len(seeds) == 9
    for seed in seeds:
        def normalize(value):
            factors = value.__dict__.copy()
            assert factors.pop("p") == 1
            coefficient = factors.pop("coefficient")
            return normalize_monomial(**factors, two=coefficient - 1)
        source, target = normalize(seed.source), normalize(seed.target)
        assert source is not None and target is not None
        assert is_live(source, seed.page) and is_live(target, seed.page)
        assert differential(source, seed.page) == target
        assert source in incoming(target, seed.page)
        assert not is_live(source, seed.page + 1)
        assert not is_live(target, seed.page + 1)
        assert (source.stem, source.filtration) == (seed.source.integer_stem, seed.source.filtration)


def test_p_is_not_a_permanent_unit_and_d3_parities_are_reversed():
    assert differential(Term("one"), 3) == Term("eta", 1, -1)
    assert not is_live(Term("one"), 4)
    assert is_live(Term("one", two=1), 13)
    assert is_live(Term("one", two=2), 14)
    assert differential(Term("T2"), 3) is None
    assert is_live(Term("T2"), 14)
    assert not c4_integer.is_live(c4_integer.Term("T2"), 4)
    assert differential(Term("varpi", 1), 3) is None
    assert differential(Term("varpi", 2), 3) == Term("eta", 3, -1)
    for q, d, n in product(range(8), range(4), range(2)):
        assert not is_live(Term("eta", q, d, n), 4)
        assert not is_live(Term("eta2", q, d, n), 4)


def test_e4_completed_ideals_and_shifted_low_filtration_permanents():
    one = module_descriptor("one", 0, 0, 14)
    assert one["stem"] == -4 and one["filtration"] == 0
    assert one["label"] == r"\mathfrak p"
    assert [(b["mu_min"], b["two_min"], b["two_max"]) for b in one["branches"]] == [(0, 2, None), (1, 1, None)]
    assert all(r"\mathfrak p" in b["representative_tex"] for b in one["branches"])
    for d in range(-4, 5):
        assert is_live(Term("T2", d=d), 14)
        assert is_live(Term("varsigma", d=d, mu=12), 14)
        assert is_live(Term("nu", d=4 * d), 14)
        assert not is_live(Term("nu", d=2 * d + 1), 6)
    # The paper's permanent nu*p does not make every Delta*nu*p permanent.
    assert differential(Term("nu", d=1), 5) == Term("varpi", 3, -1, two=1)


def test_completed_tail_maps_and_literal_zero_d7_mu_seed():
    components = differential_components("one", 0, 1, 3)
    assert len(components) == 2
    assert components[0]["source_tex"] == r"\Delta_1 \mathfrak p"
    assert components[1]["source_branch"]["completed_mu_tail"]
    assert components[1]["source_branch"]["mu_max"] is None
    assert components[1]["mu_exponent_shift"] == 0
    for n in (1, 2, 7, 100):
        source = Term("varpi", 1, 3, mu=n)
        assert is_live(source, 7) and differential(source, 7) is None
        assert is_live(source, 14)


def test_d7_leibniz_adds_the_second_odd_residue_not_only_the_printed_seed():
    for d in (1, 3, 5, 7, -1):
        assert differential(Term("varpi", 1, d, two=1), 7) == Term("varsigma", 4, d - 3)
    # varpi*Delta^2*p, unlike p, is permanent (Corollary 5.26).
    assert all(is_live(Term("varpi", 1, 2), r) for r in range(2, 15))
    assert differential(Term("varpi", 1), 7) == Term("varsigma", 4, -3)


def test_three_low_q_maps_are_forced_by_nonzero_printed_kappa_bar_products():
    def kappa_bar(term):
        family = "varpi" if term.family == "one" else term.family
        return Term(family, term.q + 2, term.d + 1, term.mu, term.two)
    for page, source, target in (
        (11, Term("varsigma", d=1), Term("varpi", 6, -3, two=1)),
        (13, Term("nu", d=2), Term("varpi", 7, -3)),
        (13, Term("one", d=4, two=1), Term("nu", 6, -1)),
    ):
        assert differential(source, page) == target
        assert differential(kappa_bar(source), page) == kappa_bar(target)
        assert is_live(target, page) and is_live(kappa_bar(target), page)
        # Each target is exactly one k-line at this page, and multiplication
        # carries its nonzero generator to the printed nonzero target.
        for t in (target, kappa_bar(target)):
            descriptor = module_descriptor(t.family, t.q, t.d, page)
            branch = descriptor["branches"][0]
            assert branch["mu_max"] == 0
            assert branch["two_min"] == branch["two_max"] == t.two
        assert not is_live(source, page + 1)
        assert not is_live(target, page + 1)
    # The last kernel is (4,2mu)p, not all of 2W[[mu]]p.
    assert not is_live(Term("one", two=1), 14)
    assert is_live(Term("one", two=2), 14)
    assert is_live(Term("one", mu=1, two=1), 14)


def test_image_of_permanent_varpi_delta2_p_commutes_with_integer_maps():
    """The permanent comparison is multiplication, never invertible p."""
    def multiply_w(term):
        if term.family == "one":
            result = Term("varpi", 1, term.d + 2, term.mu, term.two)
        elif term.family == "T2":
            result = Term("eta2", 0, term.d + 3, term.mu, term.two)
        else:
            result = Term(term.family, term.q + 1, term.d + 2, term.mu, term.two)
        return result if e2_nonzero(result) else None
    for shifted_term in terms():
        term = c4_integer.Term(**asdict(shifted_term))
        image = multiply_w(term)
        for page in DIFFERENTIAL_PAGES:
            if not c4_integer.is_live(term, page) or image is None or not is_live(image, page):
                continue
            target = c4_integer.differential(term, page)
            target_image = multiply_w(target) if target is not None else None
            if target_image is not None and not is_live(target_image, page):
                target_image = None
            assert differential(image, page) == target_image, (term, page)


def expected_e14(term):
    """Additive survivors after the five successive kernel/image steps."""
    f, q, d, n, a = term.family, term.q, term.d, term.mu, term.two
    if not e2_nonzero(term):
        return False
    if f == "one":
        return a >= (2 if n == 0 and d % 4 == 0 else 1)
    if f == "T2":
        return True
    if f == "varsigma" and q == 0:
        return a == 0 and (n > 0 or d % 4 != 1)
    if f == "varpi" and q == 1 and n:
        return a == 0
    if n:
        return False
    if f == "nu":
        return a == 0 and ((q == 0 and d % 4 == 0) or
                           (q == 1 and d % 2 == 0) or
                           (q == 2 and d % 4 == 1) or
                           (q == 4 and d % 4 == 2))
    if f == "varsigma":
        return q == 2 and d % 4 != 2 and a == 0
    if f == "varpi":
        if q == 1:
            return (d % 4 == 0 and a == 1) or (d % 4 == 2 and a <= 1)
        if q == 2:
            return d % 4 != 1 and a == 1
        return (q == 3 and d % 4 == 3 and a == 0 or
                q == 4 and d % 4 == 0 and a == 1 or
                q == 5 and d % 4 == 0 and a == 0)
    return False


def test_e14_matches_complete_shifted_family_checklist():
    for term in terms():
        assert is_live(term, 14) == expected_e14(term), term


def test_every_live_arrow_degree_reverse_index_and_square_zero():
    for term in terms():
        for page in DIFFERENTIAL_PAGES:
            target = differential(term, page)
            if target is None:
                continue
            assert (target.stem, target.filtration) == (term.stem - 1, term.filtration + page)
            assert differential(target, page) is None
            assert term in incoming(target, page)
            assert not is_live(term, page + 1)
            assert not is_live(target, page + 1)


def test_out_of_window_target_does_not_resurrect_source():
    source = Term("varpi", 8, 0, two=1)
    target = Term("nu", 14, -5)
    assert (source.stem, source.filtration) == (44, 16)
    assert (target.stem, target.filtration) == (43, 29)
    assert differential(source, 13) == target
    before = list(cells_in_window(page=13, stem_min=44, stem_max=44, filtration_min=16, filtration_max=16))
    after = list(cells_in_window(page=14, stem_min=44, stem_max=44, filtration_min=16, filtration_max=16))
    assert len(before) == 1 and not after


def test_delta4_is_a_period_but_does_not_identify_integer_and_shifted_pages():
    for term in terms():
        shifted = Term(term.family, term.q, term.d + 4, term.mu, term.two)
        for page in (2, 4, 6, 8, 12, 14):
            assert is_live(term, page) == is_live(shifted, page)
    assert not is_live(Term("varpi", 1), 8)
    assert is_live(Term("varpi", 1, 2), 8)
    assert is_live(Term("varpi", 1, 2), 14)
    assert not c4_integer.is_live(c4_integer.Term("varpi", 1, 2), 14)


def test_e14_matches_bbhs_figure_5_14_top_filtration_ten():
    assert list(cells_in_window(page=14, stem_min=-40, stem_max=40, filtration_min=11, filtration_max=40)) == []
    top = list(cells_in_window(page=14, stem_min=0, stem_max=31, filtration_min=9, filtration_max=10))
    assert {(c["stem"], c["filtration"]) for c in top} == {(7, 9), (26, 10)}


@pytest.mark.parametrize("page", (1, 15, True, 3.5))
def test_rejects_unsupported_pages(page):
    with pytest.raises(ValueError):
        is_live(Term("one"), page)


def test_rejects_invalid_window_and_preserves_shift_in_normalization():
    with pytest.raises(ValueError):
        list(cells_in_window(page=2, stem_min=0, stem_max=4, filtration_min=-1))
    assert normalize_monomial(nu=2) == Term("varpi", 1, two=1)
    assert normalize_monomial(nu=2).tex() == r"2 \varpi \mathfrak p"
    assert normalize_monomial(nu=2).stem == 2
