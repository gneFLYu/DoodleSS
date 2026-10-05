"""Independent Beaudry A.14 product tests for the auxiliary 2-BSS.

The oracle below is the short product table of A.14, transported by
x_Bea=D*x, y_Bea=D**2*y and Delta=D**3. It does not call the implementation's
raw reducer. Higher-page products use the previously independently audited
additive quotient; hidden extensions are deliberately not used.
"""
from dataclasses import replace
from itertools import product
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain import bss_integer as integer
from domain import bss_sigma as sigma
from domain.bss_multiplication import multiply


# Each tuple is (basis, extra v1, extra k, extra D); omitted entries are zero.
PRODUCTS = {
    "h1": {"1": ("h1", 0, 0, 0), "h1": ("h1^2", 0, 0, 0),
           "h1^2": ("h1^3", 0, 0, 0), "h1^3": ("1", 4, 1, 0),
           "x": ("xh1", 0, 0, 0), "xh1": ("h2^3", 0, 0, -1),
           "x^2": ("x^2h1", 0, 0, 0), "y": ("x^2", 1, 0, 0)},
    "h2": {"1": ("h2", 0, 0, 0), "x": ("xh1", 1, 0, 0),
           "x^2": ("x^2h1", 1, 0, 0), "h2": ("h2^2", 0, 0, 0),
           "y": ("yh2", 0, 0, 0), "h2^2": ("h2^3", 0, 0, 0),
           "yh2": ("x^3", 0, 0, 1)},
    "x": {"1": ("x", 0, 0, 0), "h1": ("xh1", 0, 0, 0),
          "h1^2": ("h2^3", 0, 0, -1), "x": ("x^2", 0, 0, 0),
          "xh1": ("x^2h1", 0, 0, 0), "x^2": ("x^3", 0, 0, 0),
          "h2": ("xh1", 1, 0, 0)},
    "y": {"1": ("y", 0, 0, 0), "h1": ("x^2", 1, 0, 0),
          "h1^2": ("x^2h1", 1, 0, 0), "h2": ("yh2", 0, 0, 0),
          "y": ("h2^2", 0, 0, -1), "h2^2": ("x^3", 0, 0, 1),
          "yh2": ("h2^3", 0, 0, -1)},
}
OPERATOR_DEGREES = {"h0": (0, 0, 1), "h1": (1, 1, 0), "h2": (3, 1, 0),
                    "v1": (2, 0, 0), "v1^2": (4, 0, 0), "v1^4": (8, 0, 0),
                    "x": (-1, 1, 0), "y": (-1, 1, 0), "k": (-4, 4, 0),
                    "D": (8, 0, 0), "D^-1": (-8, 0, 0)}


def xor(terms):
    remaining = set()
    for term in terms:
        remaining.symmetric_difference_update((term,))
    return tuple(sorted(remaining, key=lambda term: term.as_tuple()))


def raw_product(term, operator):
    """A.14(a-d), applied before any Bockstein quotient."""
    if operator in {"h0", "k", "D", "D^-1"}:
        key = "D" if operator == "D^-1" else operator
        return (replace(term, **{key: getattr(term, key) + (-1 if operator == "D^-1" else 1)}),)
    if operator.startswith("v1"):
        spec = (term.basis, {"v1": 1, "v1^2": 2, "v1^4": 4}[operator], 0, 0)
    else:
        spec = PRODUCTS[operator].get(term.basis)
        if spec is None:
            return ()
    basis, v1, k, D = spec
    v1 += term.v1
    if basis in integer.V1_LENGTH_TWO_BASES and v1 >= 2:
        return ()
    if basis in integer.V1_LENGTH_ONE_BASES and v1 >= 1:
        return ()
    return (integer.BSSMonomial(basis, v1=v1, k=term.k+k, D=term.D+D, h0=term.h0),)


def expected_product(term, operator, page, sector):
    raw = sigma.to_integer_basis(term) if sector == "sigma" else (term,)
    result = xor(target for source in raw for target in raw_product(source, operator))
    if sector == "sigma":
        return sigma.reduce_e1_vector(result, page)
    for previous_page in range(1, min(page, 4)):
        assert all(integer.differential(target, previous_page) is None for target in result)
        result = tuple(target for target in result if integer.is_live(target, previous_page+1))
    return result


def basis_terms(sector, maximum=8):
    if sector == "integer":
        for basis in integer.BASIS_GRADES:
            top = maximum if basis in integer.FREE_BASES else 1 if basis in integer.V1_LENGTH_TWO_BASES else 0
            for v1 in range(top+1):
                yield integer.BSSMonomial(basis, v1=v1)
    else:
        for basis, spec in sigma.BASIS_SPECS.items():
            for v1 in range((maximum if spec.max_v1 is None else spec.max_v1)+1):
                yield sigma.SigmaMonomial(basis, v1=v1)


def operators_on_page(page):
    operators = ["h0", "h1", "h2", "v1^4", "k", "D", "D^-1"]
    if page <= 2:
        operators.append("v1^2")
    if page == 1:
        operators += ["v1", "x", "y"]
    return operators


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_full_beaudry_product_matrix_and_homogeneous_tridegrees(sector, page):
    engine = integer if sector == "integer" else sigma
    cases = 0
    for seed, k, D, h0 in product(basis_terms(sector), [0, 1, 3], [-2, 0, 3], [0, 1, 3]):
        term = replace(seed, k=k, D=D, h0=h0)
        if not engine.is_live(term, page):
            continue
        for operator in operators_on_page(page):
            result = multiply(term, operator, page, sector=sector)
            assert isinstance(result, tuple)
            assert result == expected_product(term, operator, page, sector), (term, operator, page)
            assert len(set(result)) == len(result)
            for target in result:
                assert engine.is_live(target, page)
                assert tuple(b-a for a, b in zip(term.tridegree, target.tridegree)) == OPERATOR_DEGREES[operator]
            cases += 1
    assert cases > 100


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page,operator", [(2, "v1"), (3, "v1^2"), (4, "v1^2"), (2, "x"), (2, "y")])
def test_absent_multiplier_rejected_instead_of_interpreted_as_zero(sector, page, operator):
    term = integer.BSSMonomial("1") if sector == "integer" else sigma.SigmaMonomial("1", v1=4)
    with pytest.raises(ValueError):
        multiply(term, operator, page, sector=sector)


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_current_page_outgoing_multiplier_is_a_valid_algebra_operation(sector):
    term = integer.BSSMonomial("1") if sector == "integer" else sigma.SigmaMonomial("1")
    assert multiply(term, "v1", 1, sector=sector) == (replace(term, v1=1),)
    if sector == "sigma":
        term = replace(term, v1=2)
    assert multiply(term, "v1^2", 2, sector=sector) == (replace(term, v1=term.v1+2),)


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_absent_source_rejected(sector):
    term = integer.BSSMonomial("x") if sector == "integer" else sigma.SigmaMonomial("1")
    with pytest.raises(ValueError):
        multiply(term, "h1", 2, sector=sector)


@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_sigma_cycle_combinations_and_no_hidden_extensions(page):
    term = sigma.SigmaMonomial
    for basis, operator, expected in [
        ("{h1+v1x}", "h1", "{h1^2+v1xh1}"),
        ("{x+y}", "h2", "{v1xh1+yh2}"),
        ("{x^2+y^2}", "h2", "{xh1^2+v1x^2h1}"),
        ("{xh1+v1x^2}", "h1", "{xh1^2+v1x^2h1}"),
    ]:
        assert multiply(term(basis), operator, page, sector="sigma") == (term(expected),)
    # These become hidden extensions only in the abutment, not on E_r.
    assert multiply(term("x^2h1"), "h1", page, sector="sigma") == ()
    assert multiply(term("x^3"), "h2", page, sector="sigma") == ()


@pytest.mark.parametrize("basis,expected", [
    ("x", ("h1", "{h1+v1x}")),
    ("x^2", ("xh1", "{xh1+v1x^2}")),
    ("x^2h1", ("xh1^2", "{xh1^2+v1x^2h1}")),
])
def test_sigma_product_can_be_a_genuine_sum_of_adapted_basis_vectors(basis, expected):
    assert multiply(sigma.SigmaMonomial(basis), "v1", 1, sector="sigma") == xor(
        sigma.SigmaMonomial(name) for name in expected)


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_products_by_permanent_h0_h1_h2_k_D_commute_with_differential(sector, page):
    engine = integer if sector == "integer" else sigma
    for term in basis_terms(sector):
        if not engine.is_live(term, page):
            continue
        for operator in ["h0", "h1", "h2", "k", "D", "D^-1"]:
            lhs = xor(target for value in multiply(term, operator, page, sector=sector)
                      if (target := engine.differential(value, page)) is not None)
            image = engine.differential(term, page)
            rhs = multiply(image, operator, page, sector=sector) if image is not None else ()
            assert lhs == rhs, (sector, page, term, operator)


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_v1_leibniz_correction_is_not_silently_treated_as_a_chain_map(sector):
    engine = integer if sector == "integer" else sigma
    for term in basis_terms(sector):
        lhs = xor(target for value in multiply(term, "v1", 1, sector=sector)
                  if (target := engine.differential(value, 1)) is not None)
        image = engine.differential(term, 1)
        first = multiply(image, "v1", 1, sector=sector) if image is not None else ()
        correction = tuple(target for value in multiply(term, "h1", 1, sector=sector)
                           for target in multiply(value, "h0", 1, sector=sector))
        assert lhs == xor((*first, *correction)), term


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_E2_v1_squared_leibniz_rule_uses_h0_squared_h2(sector):
    engine = integer if sector == "integer" else sigma
    for term in basis_terms(sector):
        if not engine.is_live(term, 2):
            continue
        lhs = xor(target for value in multiply(term, "v1^2", 2, sector=sector)
                  if (target := engine.differential(value, 2)) is not None)
        image = engine.differential(term, 2)
        first = multiply(image, "v1^2", 2, sector=sector) if image is not None else ()
        correction = tuple(replace(value, h0=value.h0+2)
                           for value in multiply(term, "h2", 2, sector=sector)
                           if engine.is_live(replace(value, h0=value.h0+2), 2))
        assert lhs == xor((*first, *correction)), term


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_associated_graded_operator_relations_hold_on_every_surviving_class(sector, page):
    engine = integer if sector == "integer" else sigma

    def word(term, operators):
        result = (term,)
        for operator in operators:
            result = xor(target for value in result for target in multiply(value, operator, page, sector=sector))
        return result

    for term in basis_terms(sector):
        if not engine.is_live(term, page):
            continue
        assert word(term, ["h1"] * 4) == word(term, ["v1^4", "k"])
        assert word(term, ["h1", "h2"]) == word(term, ["h2", "h1"]) == ()
        assert word(term, ["D", "D^-1"]) == (term,)
        for operator in operators_on_page(page):
            assert word(term, ["h0", operator]) == word(term, [operator, "h0"])
        if page <= 2:
            assert word(term, ["v1^2"] * 2) == word(term, ["v1^4"])
        if page == 1:
            assert word(term, ["v1"] * 2) == word(term, ["v1^2"])


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_multiplication_has_no_hidden_v1_h0_or_viewport_caps(sector):
    cls = integer.BSSMonomial if sector == "integer" else sigma.SigmaMonomial
    term = cls("1", v1=1_000_000, k=0, D=-250_000, h0=1000)
    assert multiply(term, "v1^4", 4, sector=sector) == (replace(term, v1=1_000_004),)
    assert multiply(term, "h0", 4, sector=sector) == (replace(term, h0=1001),)
    assert multiply(term, "D^-1", 4, sector=sector) == (replace(term, D=-250_001),)
