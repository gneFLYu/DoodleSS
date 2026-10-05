"""C4 family highlighting distinguishes units from nonzero forward products."""
from dataclasses import asdict, replace
from itertools import product

import pytest

from backend.domain import c4_integer, c4_shifted
from backend.domain.c4_chart import build_c4_periodic_chart, c4_orbit_key


ENGINES = {"integer": c4_integer, "1-minus-sigma": c4_shifted}


def key(term, page=2, sector="integer"):
    return c4_orbit_key(**asdict(term), page=page, sector=sector)


def times_kappa(term, engine):
    # Independent statement of the E2 product from BBHS Props. 5.10, 5.22.
    factors = {"varpi": term.q+2, "delta": term.d+1, "mu": term.mu, "two": term.two}
    for family, symbol, power in [("T2", "t2", 1), ("eta", "eta", 1), ("eta2", "eta", 2),
                                   ("nu", "nu", 1), ("varsigma", "varsigma", 1)]:
        if term.family == family:
            factors[symbol] = power
    return engine.normalize_monomial(**factors)


@pytest.mark.parametrize("sector", ENGINES)
@pytest.mark.parametrize("page", range(2, 15))
def test_keys_respect_horizontal_units_and_actual_nonzero_forward_products(sector, page):
    engine = ENGINES[sector]
    checks = 0
    for family, q, d, mu, two in product(engine.FAMILIES, range(9), range(4), range(3), range(3)):
        if family in ("one", "T2") and q or family == "varpi" and not q:
            continue
        term = engine.Term(family, q, d, mu, two)
        family_key = key(term, page, sector)
        if not engine.is_live(term, page):
            assert family_key is None
            continue
        assert isinstance(family_key, str)
        for power in (-3, -1, 1, 4):
            assert key(replace(term, d=d+4*power), page, sector) == family_key
        target = times_kappa(term, engine)
        if target is not None and engine.is_live(target, page):
            assert (target.stem-term.stem, target.filtration-term.filtration) == (20, 4)
            assert key(target, page, sector) == family_key
        elif target is not None:
            assert key(target, page, sector) is None
        checks += 1
    assert checks > 20


@pytest.mark.parametrize("sector", ENGINES)
def test_filtration_zero_identifications_are_true_ring_products_not_q_parity(sector):
    engine = ENGINES[sector]
    assert key(engine.Term("one"), sector=sector) == key(engine.Term("varpi", 2, 1), sector=sector)
    assert key(engine.Term("T2"), sector=sector) == key(engine.Term("eta2", 1, 2), sector=sector)
    # Different Δ residues or odd/even chains do not become the same family.
    assert key(engine.Term("one"), sector=sector) != key(engine.Term("varpi", 1, 1), sector=sector)
    assert key(engine.Term("eta", 0, 0), sector=sector) != key(engine.Term("eta", 0, 1), sector=sector)
    assert key(engine.Term("eta", 0, 0), sector=sector) != key(engine.Term("eta", 1, 0), sector=sector)


def test_coefficients_sector_and_page_are_never_collapsed():
    term = c4_integer.Term("one")
    keys = {key(replace(term, mu=mu, two=two), page, sector)
            for mu, two, page, sector in product(range(3), range(5), [2, 3], ENGINES)}
    assert len(keys) == 3*5*2*2
    assert None not in keys
    # In particular the two constant W/4 ports and the mu-tail are different.
    terms = [c4_integer.Term("varpi", 2, 1, mu=0, two=0),
             c4_integer.Term("varpi", 2, 1, mu=0, two=1),
             c4_integer.Term("varpi", 2, 1, mu=1, two=0)]
    assert len({key(term) for term in terms}) == 3


def test_forward_action_does_not_assert_an_inverse_or_resurrect_zero_coefficients():
    assert key(c4_integer.Term("one", two=2)) is not None
    assert key(c4_integer.Term("varpi", 2, 1, two=2)) is None  # 4*kappa-bar=0 already on E2.
    assert key(c4_integer.Term("one", mu=1), page=4) is not None
    assert key(c4_integer.Term("varpi", 2, 1, mu=1), page=4) is None  # mu*kappa-bar is a d3 boundary.
    assert key(c4_shifted.Term("T2"), page=4, sector="1-minus-sigma") is not None
    assert key(c4_shifted.Term("eta2", 1, 2), page=4, sector="1-minus-sigma") is None


def test_reduction_stops_at_absent_predecessor_even_if_a_formal_lower_anchor_exists(monkeypatch):
    # Guard the algorithm independently of the current finite catalogue of maps:
    # a future certified quotient may cut a chain. No formal division is allowed.
    c4_orbit_key.cache_clear()
    original = c4_integer.is_live
    missing = c4_integer.Term("varpi", 2, 1)
    monkeypatch.setattr(c4_integer, "is_live", lambda term, page: term != missing and original(term, page))
    try:
        assert key(c4_integer.Term("varpi", 4, 2)) != key(c4_integer.Term("one"))
        assert key(c4_integer.Term("varpi", 4, 2)) == key(c4_integer.Term("varpi", 6, 3))
    finally:
        c4_orbit_key.cache_clear()


@pytest.mark.parametrize("sector", ENGINES)
@pytest.mark.parametrize("page", [2, 4, 6, 8, 12, 14])
def test_chart_exports_exact_displayed_port_keys_and_honest_transport_metadata(sector, page):
    engine = ENGINES[sector]
    payload = build_c4_periodic_chart(sector, page=page, filtration_max=12)
    transport = payload["chart"]["periodic_family_transport"]
    assert transport["horizontal"]["stem"] == 32
    assert transport["forward"]["stem"] == 20 and transport["forward"]["filtration"] == 4
    assert transport["forward"]["domain"] == "nonnegative"
    assert transport["forward"]["invertible"] is False
    for node in payload["chart"]["classes"]:
        style, branch = node["style"], node["style"]["c4_coefficient_branch"]
        representative = engine.Term(**branch["representative"])
        upper = branch["two_max"] if branch["two_max"] is not None else branch["two_min"]+2
        expected = {f"{two}:0": key(replace(representative, two=two), page, sector)
                    for two in range(branch["two_min"], upper+1)}
        assert style["c4_periodic_family_keys"] == expected
        assert all(expected.values())
        assert style["c4_periodic_family_mu_exponent"] == branch["mu_min"]
        assert len(set(expected.values())) == len(expected)
