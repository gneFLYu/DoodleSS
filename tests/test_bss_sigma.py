"""Twisted d1 basis changes and quotient-compatible sigma 2-BSS d2."""
from dataclasses import replace
from itertools import product
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain.bss_integer import BASIS_GRADES as RAW_BASIS_GRADES, BSSMonomial
from domain.bss_sigma import (
    BASIS_SPECS, SigmaMonomial, differential, differential_e1_vector,
    enumerate_window, from_integer_basis, is_live, raw_twisted_d1,
    reduce_e1_vector, to_integer_basis,
)


def samples(v1_max=8, k_max=2, D_max=2, h0_max=4):
    for basis, spec in BASIS_SPECS.items():
        maximum = v1_max if spec.max_v1 is None else min(v1_max, spec.max_v1)
        for v1, k, D, h0 in product(range(maximum+1), range(k_max+1), range(-D_max, D_max+1), range(h0_max+1)):
            yield SigmaMonomial(basis, v1, k, D, h0)


def raw_samples():
    for basis in RAW_BASIS_GRADES:
        max_v1 = 6 if basis in ("1", "h1", "h1^2", "h1^3") else 1 if basis in ("x", "xh1", "x^2", "x^2h1") else 0
        for v1, k, D, h0 in product(range(max_v1+1), [0, 2], [-3, 0, 4], [0, 3]):
            yield BSSMonomial(basis, v1, k, D, h0)


def xor_raw(terms):
    result = set()
    for term in terms:
        result.symmetric_difference_update([term])
    return result


def test_basis_change_is_invertible_both_directions_and_degree_preserving():
    for node in samples(v1_max=6, k_max=1, D_max=1, h0_max=1):
        raw = to_integer_basis(node)
        assert raw and all(term.tridegree == node.tridegree for term in raw)
        assert from_integer_basis(raw) == (node,)
    for raw in raw_samples():
        adapted = from_integer_basis([raw])
        assert adapted and all(term.tridegree == raw.tridegree for term in adapted)
        assert xor_raw(term for node in adapted for term in to_integer_basis(node)) == {raw}


def test_adapted_d1_equals_raw_twisted_derivation_and_squares_zero():
    for node in samples(v1_max=6, k_max=1, D_max=1, h0_max=1):
        raw = to_integer_basis(node)
        independent_image = from_integer_basis(raw_twisted_d1(raw))
        target = differential(node, 1)
        assert independent_image == (() if target is None else (target,)), node
        assert raw_twisted_d1(raw_twisted_d1(raw)) == ()


def test_all_printed_table4_d1_equations_in_raw_coordinates():
    rows = [
        (BSSMonomial("1"), "{x+y}"),
        (BSSMonomial("x"), "{x^2+y^2}"),
        (BSSMonomial("1", v1=1), "{h1+v1x}"),
        (BSSMonomial("h2"), "{v1xh1+yh2}"),
    ]
    for raw, expression in rows:
        assert differential_e1_vector([raw], 1) == (SigmaMonomial(expression, h0=1),)


@pytest.mark.parametrize("page", [1, 2])
def test_degrees_square_zero_and_endpoint_lifetimes(page):
    count = 0
    for node in samples():
        target = differential(node, page)
        if target is None:
            continue
        count += 1
        assert is_live(node, page) and is_live(target, page)
        assert tuple(b-a for a, b in zip(node.tridegree, target.tridegree)) == (-1, 1, page)
        assert differential(target, page) is None
        assert not is_live(node, page+1) and not is_live(target, page+1)
    assert count > 0


def test_d2_agrees_on_the_two_monomial_representatives_and_their_sum():
    for k, D, h0 in product([0, 3], [-7, 0, 12], [0, 1, 5]):
        # xh1^2 = D^-1 h2^3, while v1*x^2*h1 has a different h0^0
        # class but the same positive-h0 class in the d1 quotient.
        raw_left = BSSMonomial("h2^3", k=k, D=D-1, h0=h0)
        raw_right = BSSMonomial("x^2h1", v1=1, k=k, D=D, h0=h0)
        target = SigmaMonomial("1", v1=2, k=k+1, D=D, h0=h0+2)
        assert differential_e1_vector([raw_left], 2) == (target,)
        assert differential_e1_vector([raw_right], 2) == (target,)
        assert differential_e1_vector([raw_left, raw_right], 2) == ()
        if h0:
            assert reduce_e1_vector([raw_left], 2) == reduce_e1_vector([raw_right], 2)
            assert reduce_e1_vector([raw_left, raw_right], 2) == ()
        else:
            assert reduce_e1_vector([raw_left], 2) != reduce_e1_vector([raw_right], 2)
            assert reduce_e1_vector([raw_left, raw_right], 3) == (SigmaMonomial("{xh1^2+v1x^2h1}", k=k, D=D),)


def test_projection_does_not_silently_drop_noncycles():
    with pytest.raises(ValueError, match="not an E2 cycle"):
        reduce_e1_vector([BSSMonomial("1")], 2)
    with pytest.raises(ValueError, match="not an E3 cycle"):
        reduce_e1_vector([BSSMonomial("h2^3", D=-1)], 3)
    assert reduce_e1_vector([BSSMonomial("h2^3", D=-1), BSSMonomial("h2^3", D=-1)], 3) == ()


def test_h0_layers_and_torsion_free_v1_squared_orientation_degree():
    for D in [-10, 0, 37]:
        node = SigmaMonomial("1", v1=2, D=D)
        assert node.bidegree == (4+8*D, 0)
        for h0 in [0, 1, 2, 99]:
            assert is_live(replace(node, h0=h0), 3)
        for k in [1, 2, 7]:
            assert [is_live(replace(node, k=k, h0=h0), 3) for h0 in range(4)] == [True, True, False, False]
    for v1 in [4, 6, 8, 1000]:
        assert is_live(SigmaMonomial("1", v1=v1, h0=999), 3)
        assert differential(SigmaMonomial("1", v1=v1), 2) is None
        assert is_live(SigmaMonomial("1", v1=v1, k=1), 3)
        assert not is_live(SigmaMonomial("1", v1=v1, k=1, h0=1), 2)


def test_next_page_is_exact_coordinate_kernel_mod_image():
    outer = list(samples(v1_max=11, k_max=4, D_max=3, h0_max=6))
    inner = list(samples(v1_max=8, k_max=3, D_max=2, h0_max=4))
    for page in [1, 2]:
        outgoing = {source for source in outer if differential(source, page) is not None}
        incoming = {differential(source, page) for source in outgoing}
        # Distinct nonzero columns have distinct targets, justifying the
        # coordinate-space kernel and quotient used by is_live.
        assert len(incoming) == len(outgoing)
        for node in inner:
            assert is_live(node, page+1) == (is_live(node, page) and node not in outgoing and node not in incoming)
    for node in inner:
        assert is_live(node, 3) == is_live(node, 4) == is_live(node, 100)
        assert differential(node, 3) is None


def test_D_k_h0_linearity_and_symbolic_unbounded_exponents():
    for page in [1, 2]:
        for node in samples(v1_max=4, k_max=0, D_max=0, h0_max=0):
            target = differential(node, page)
            if target is not None:
                moved = replace(node, k=node.k+10**5, D=node.D-10**8, h0=node.h0+10**4)
                expected = replace(target, k=target.k+10**5, D=target.D-10**8, h0=target.h0+10**4)
                assert differential(moved, page) == expected


def test_full_explicit_tex_labels_use_braces_and_simplify_v1_torsion():
    for name, spec in BASIS_SPECS.items():
        label = SigmaMonomial(name).label_tex
        assert label.endswith(r"u_{\sigma_i}")
        if "+" in name:
            assert r"\{" in label and r"\}" in label
    assert SigmaMonomial("{h1^2+v1xh1}", v1=2, k=3, D=-4).label_tex == r"h_1^2v_1^{2}k^{3}D^{-4}u_{\sigma_i}"
    assert SigmaMonomial("1", v1=2).label_tex == r"v_1^{2}u_{\sigma_i}"


def test_bounded_enumeration_and_off_window_fates():
    for page in [1, 2, 3, 4]:
        nodes = enumerate_window(-7, 11, 1, 8, page=page, v1_max=6, h0_max=3)
        assert nodes and len(nodes) == len(set(nodes))
        for node in nodes:
            stem, filtration = node.bidegree
            assert -7 <= stem <= 11 and 1 <= filtration <= 8
            assert node.v1 <= 6 and node.h0 <= 3 and is_live(node, page)
    # u_sigma_i lies outside this window; h0{x+y}u is still a boundary.
    boundary = SigmaMonomial("{x+y}", h0=1)
    assert boundary in enumerate_window(-1, -1, 1, 1, page=1, v1_max=0, h0_max=1)
    assert boundary not in enumerate_window(-1, -1, 1, 1, page=2, v1_max=0, h0_max=1)
    # The source lies in filtration3 outside this single filtration4 cell.
    late_boundary = SigmaMonomial("1", v1=2, k=1, h0=2)
    assert late_boundary in enumerate_window(0, 0, 4, 4, page=2, v1_max=2, h0_max=2)
    assert late_boundary not in enumerate_window(0, 0, 4, 4, page=3, v1_max=2, h0_max=2)
    # A tiny h0 cap cannot save a source whose target was not enumerated.
    assert SigmaMonomial("xh1^2") not in enumerate_window(1, 1, 3, 3, page=3, v1_max=0, h0_max=0)


@pytest.mark.parametrize("kwargs", [
    {"basis": "A"}, {"basis": []}, {"basis": "x", "v1": 1},
    {"basis": "xh1", "v1": 2}, {"basis": "1", "v1": -1},
    {"basis": "1", "k": -1}, {"basis": "1", "D": 1.5},
    {"basis": "1", "h0": True}, {"basis": "1", "h0": -1},
])
def test_invalid_canonical_monomials(kwargs):
    with pytest.raises(ValueError):
        SigmaMonomial(**kwargs)


@pytest.mark.parametrize("page", [0, -1, True, "2", 1.1])
def test_invalid_pages(page):
    with pytest.raises(ValueError):
        is_live(SigmaMonomial("1"), page)
    with pytest.raises(ValueError):
        differential(SigmaMonomial("1"), page)
    with pytest.raises(ValueError):
        reduce_e1_vector([], page)


@pytest.mark.parametrize("kwargs", [
    {"stem_min": 9, "stem_max": 8}, {"filtration_min": -1},
    {"filtration_min": 5, "filtration_max": 4}, {"v1_max": -1},
    {"h0_max": 1.2}, {"page": 0}, {"limit": 0},
])
def test_invalid_windows(kwargs):
    options = dict(stem_min=-4, stem_max=8, filtration_min=0, filtration_max=4, page=1, v1_max=4, h0_max=3)
    options.update(kwargs)
    with pytest.raises(ValueError):
        enumerate_window(**options)


def test_enumeration_limit():
    with pytest.raises(ValueError, match="materialization limit"):
        enumerate_window(-4, 8, 0, 4, page=1, v1_max=4, h0_max=3, limit=1)
