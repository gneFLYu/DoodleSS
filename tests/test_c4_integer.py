"""Independent family/liveness checks for the exact integer C4 page engine."""
from itertools import product

import pytest

from backend.domain.c4_integer import (
    DIFFERENTIAL_PAGES, Term, cells_in_window, differential, differential_components,
    e2_nonzero, incoming, is_live, module_descriptor, normalize_monomial, reduce_ro_degree,
)
from backend.domain.c4_reference import c4_differential_seeds


def test_every_literal_integer_bbhs_seed_normalizes_to_exact_live_arrow():
    for seed in c4_differential_seeds(False):
        def normalize(value):
            factors = value.__dict__.copy()
            assert factors.pop("p") == 0
            coefficient = factors.pop("coefficient")
            assert coefficient in (1, 2)
            return normalize_monomial(**factors, two=coefficient - 1)
        source, target = normalize(seed.source), normalize(seed.target)
        assert source is not None and target is not None
        assert is_live(source, seed.page) and is_live(target, seed.page)
        assert differential(source, seed.page) == target
        assert source in incoming(target, seed.page)
        assert not is_live(source, seed.page + 1)
        assert not is_live(target, seed.page + 1)


def test_ring_normalization_preserves_torsion_and_does_not_fake_polynomial():
    assert normalize_monomial(eta=3) == Term("varsigma", 1, -1, mu=1)
    assert normalize_monomial(eta=1, varsigma=1) == Term("varpi", 1, mu=1)
    assert normalize_monomial(nu=2) == Term("varpi", 1, two=1)
    assert normalize_monomial(t2=1, varpi=2) == Term("eta2", 1, 1)
    assert normalize_monomial(nu=3) is None
    assert normalize_monomial(nu=1, mu=1) is None
    assert normalize_monomial(varpi=1, mu=1, two=1) is None
    with pytest.raises(ValueError, match="additive Witt polynomial"):
        normalize_monomial(t2=2)


def test_delta_witt_kernel_has_mu_branch_not_just_a_doubled_point():
    assert is_live(Term("one", d=1), 5)
    assert not is_live(Term("one", d=1), 6)
    assert is_live(Term("one", d=1, two=1), 6)
    assert is_live(Term("one", d=1, mu=1), 6)
    assert not is_live(Term("one", d=1, two=1), 8)
    assert is_live(Term("one", d=1, two=2), 8)
    assert is_live(Term("one", d=1, mu=1), 14)
    descriptor = module_descriptor("one", 0, 1, 14)
    assert [(b["mu_min"], b["mu_max"], b["two_min"], b["two_max"])
            for b in descriptor["branches"]] == [(0, 0, 2, None), (1, None, 0, None)]
    assert descriptor["scalar_ports_are_not_module_basis"] is True


def test_d3_completed_tail_map_is_not_a_single_f4_arrow():
    components = differential_components("T2", 0, 0, 3)
    assert len(components) == 2
    assert components[0]["target"] == dict(family="varsigma", q=1, d=-1, mu=1, two=0)
    assert components[1]["source_branch"]["completed_mu_tail"] is True
    assert components[1]["mu_exponent_shift"] == 1
    assert components[1]["source_branch"]["mu_max"] is None
    assert components[0]["kernel_two_min"] == 1


def test_outgoing_differential_survives_source_clipping_but_not_page_change():
    source = Term("varpi", 7, -2, two=1)
    target = Term("nu", 13, -7)
    assert (source.stem, source.filtration) == (26, 14)
    assert (target.stem, target.filtration) == (25, 27)
    assert differential(source, 13) == target
    assert incoming(target, 13) == (source,)
    before = list(cells_in_window(page=13, stem_min=26, stem_max=26, filtration_min=14, filtration_max=14))
    after = list(cells_in_window(page=14, stem_min=26, stem_max=26, filtration_min=14, filtration_max=14))
    assert len(before) == 1 and after == []


def expected_e14(term):
    f, q, d, n, a = term.family, term.q, term.d, term.mu, term.two
    if not e2_nonzero(term):
        return False
    if f == "one":
        return n > 0 or a >= (0 if d % 4 == 0 else 1 if d % 4 == 2 else 2)
    if f == "T2":
        return a >= 1
    if f in ("eta", "eta2"):
        return q == 0 and a == 0
    if n:
        return False
    if f == "varsigma":
        return q == 1 and d % 4 != 0 and a == 0
    if f == "nu":
        return a == 0 and ((q == 0 and d % 2 == 0) or
                           (q == 1 and d % 4 == 3) or
                           (q == 3 and d % 4 == 0) or
                           (q == 5 and d % 4 == 1))
    if f == "varpi":
        if q == 1:
            return a == 1 and d % 4 != 3
        if q == 2:
            return (d % 4 == 1 and a <= 1) or (d % 4 == 3 and a == 1)
        return (q == 3 and d % 4 == 2 and a == 1 or
                q == 4 and d % 4 == 2 and a == 0 or
                q == 5 and d % 4 == 3 and a == 1 or
                q == 6 and d % 4 == 3 and a == 0)
    return False


def terms():
    for family in ("one", "T2", "eta", "nu", "varsigma", "varpi", "eta2"):
        qs = (0,) if family in ("one", "T2") else range(1 if family == "varpi" else 0, 10)
        for q, d, n, a in product(qs, range(-5, 6), range(3), range(4)):
            yield Term(family, q, d, n, a)


def test_e14_matches_independent_complete_family_checklist():
    for term in terms():
        assert is_live(term, 14) == expected_e14(term), term


def test_every_live_map_has_correct_degree_zero_square_and_reverse_source():
    for term in terms():
        for page in DIFFERENTIAL_PAGES:
            target = differential(term, page)
            if target is None:
                continue
            assert is_live(target, page)
            assert (target.stem, target.filtration) == (term.stem - 1, term.filtration + page)
            assert differential(target, page) is None
            assert term in incoming(target, page)
            assert not is_live(term, page + 1)
            assert not is_live(target, page + 1)


def test_delta4_period_is_global_but_delta_is_not():
    for term in terms():
        shifted = Term(term.family, term.q, term.d + 4, term.mu, term.two)
        for page in (2, 4, 6, 8, 12, 14):
            assert is_live(term, page) == is_live(shifted, page)
    assert is_live(Term("one"), 6)
    assert not is_live(Term("one", d=1), 6)
    assert is_live(Term("one", d=2), 6)
    assert not is_live(Term("one", d=2), 8)


def test_positive_mu_tail_is_exact_not_a_finite_truncation():
    for f in ("one", "T2", "eta", "nu", "varsigma", "varpi", "eta2"):
        for d, a, page in product(range(4), range(3), (2, 4, 6, 8, 12, 14)):
            q = 1 if f == "varpi" else 0
            expected = is_live(Term(f, q, d, 1, a), page)
            assert all(is_live(Term(f, q, d, n, a), page) == expected for n in (2, 7, 100))


def test_e14_high_filtration_empty_and_characteristic_positions_present():
    assert list(cells_in_window(page=14, stem_min=-50, stem_max=50, filtration_min=13, filtration_max=40)) == []
    cells = list(cells_in_window(page=14, stem_min=0, stem_max=31, filtration_min=8, filtration_max=12))
    assert {(c["stem"], c["filtration"]) for c in cells} == {(8, 8), (22, 10), (9, 11), (28, 12)}


def test_ro_reduction_certificates_are_exact_equalities():
    for alpha, beta, gamma in product(range(-4, 5), repeat=3):
        cert = reduce_ro_degree(alpha, beta, gamma)
        reconstructed = cert["representative"].copy()
        for unit in cert["permanent_unit_powers"]:
            reconstructed = [x + unit["exponent"] * y for x, y in zip(reconstructed, unit["degree"])]
        assert reconstructed == [alpha, beta, gamma]
        assert 0 <= cert["stem_shift"] < 32
    assert reduce_ro_degree(1, -1, 0)["stem_shift"] == 0
    assert reduce_ro_degree(1, -1, 0)["sector"] == 1
    assert reduce_ro_degree(2, -2, 0)["stem_shift"] == 16
    for degree in ((1, 1, 1), (16, 0, -8), (4, -4, 0), (10, -2, -4)):
        cert = reduce_ro_degree(*degree)
        assert cert["stem_shift"] == cert["sector"] == 0


@pytest.mark.parametrize("page", (1, 15, True, 3.5))
def test_unsupported_pages_rejected(page):
    with pytest.raises(ValueError):
        is_live(Term("one"), page)


def test_invalid_terms_and_windows_rejected():
    with pytest.raises(ValueError):
        Term("varpi", 0)
    with pytest.raises(ValueError):
        Term("one", q=1)
    with pytest.raises(ValueError):
        Term("one", mu=-1)
    with pytest.raises(ValueError):
        list(cells_in_window(page=2, stem_min=3, stem_max=2))
