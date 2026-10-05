"""Exact integer auxiliary Bockstein pages; no viewport-dependent inference."""
from dataclasses import replace
from itertools import product
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain.bss_integer import (
    BASIS_GRADES, FREE_BASES, V1_LENGTH_TWO_BASES, BSSMonomial,
    differential, enumerate_window, is_live, iter_window,
)


def samples(v1_max=8, k_max=2, D_max=2, h0_max=4):
    for basis in BASIS_GRADES:
        max_v1 = v1_max if basis in FREE_BASES else 1 if basis in V1_LENGTH_TWO_BASES else 0
        for v1, k, D, h0 in product(range(max_v1+1), range(k_max+1), range(-D_max, D_max+1), range(h0_max+1)):
            yield BSSMonomial(basis, v1, k, D, h0)


@pytest.mark.parametrize("kwargs", [
    {"basis": "unknown"}, {"basis": []}, {"basis": "x", "v1": 2},
    {"basis": "h2", "v1": 1}, {"basis": "1", "v1": -1},
    {"basis": "1", "k": -1}, {"basis": "1", "h0": -1},
    {"basis": "1", "D": 1.5}, {"basis": "1", "k": True},
    {"basis": "1", "h0": "1"},
])
def test_canonical_tuple_validation(kwargs):
    with pytest.raises(ValueError):
        BSSMonomial(**kwargs)


@pytest.mark.parametrize("page", [0, -1, True, "2", 2.5])
def test_invalid_pages(page):
    with pytest.raises(ValueError):
        is_live(BSSMonomial("1"), page)
    with pytest.raises(ValueError):
        differential(BSSMonomial("1"), page)


def test_exact_d1_basis_columns():
    rows = [
        (BSSMonomial("1", v1=3), BSSMonomial("h1", v1=2, h0=1)),
        (BSSMonomial("h1", v1=1), BSSMonomial("h1^2", h0=1)),
        (BSSMonomial("h1^2", v1=5), BSSMonomial("h1^3", v1=4, h0=1)),
        (BSSMonomial("h1^3", v1=3), BSSMonomial("1", v1=6, k=1, h0=1)),
        (BSSMonomial("x"), BSSMonomial("h2^2", D=-1, h0=1)),
        (BSSMonomial("x", v1=1), BSSMonomial("xh1", h0=1)),
        (BSSMonomial("xh1", v1=1), BSSMonomial("h2^3", D=-1, h0=1)),
        (BSSMonomial("x^2", v1=1), BSSMonomial("x^2h1", h0=1)),
        (BSSMonomial("y"), BSSMonomial("x^2", h0=1)),
        (BSSMonomial("yh2"), BSSMonomial("x^2h1", v1=1, h0=1)),
    ]
    for source, target in rows:
        assert differential(source, 1) == target
    # Every remaining column in this finite set is a declared zero.
    declared = {source for source, _ in rows}
    assert differential(BSSMonomial("1", v1=2), 1) is None
    assert differential(BSSMonomial("x^2h1", v1=1), 1) is None
    assert len(declared) == len(rows)


@pytest.mark.parametrize("page", [1, 2, 3])
def test_bidegrees_square_zero_and_endpoint_liveness(page):
    count = 0
    for source in samples():
        target = differential(source, page)
        if target is None:
            continue
        count += 1
        assert is_live(source, page) and is_live(target, page)
        assert tuple(b-a for a, b in zip(source.tridegree, target.tridegree)) == (-1, 1, page)
        assert differential(target, page) is None
        assert not is_live(source, page+1)
        assert not is_live(target, page+1)
    assert count > 0


@pytest.mark.parametrize("page", [1, 2, 3])
def test_maps_are_D_k_h0_linear(page):
    for source in samples(v1_max=4, k_max=0, D_max=0, h0_max=0):
        target = differential(source, page)
        if target is None:
            continue
        for shift_D, shift_k, shift_h0 in [(-13, 9, 27), (8, 1, 0), (0, 0, 42)]:
            moved = replace(source, D=source.D+shift_D, k=source.k+shift_k, h0=source.h0+shift_h0)
            expected = replace(target, D=target.D+shift_D, k=target.k+shift_k, h0=target.h0+shift_h0)
            assert differential(moved, page) == expected


def test_d2_exact_v1_squared_not_higher_v1_families():
    for k, D, h0 in product(range(4), range(-2, 3), range(5)):
        assert differential(BSSMonomial("1", v1=2, k=k, D=D, h0=h0), 2) == BSSMonomial("h2", k=k, D=D, h0=h0+2)
    for v1 in [4, 6, 8, 10, 1000]:
        for h0 in [0, 1, 20]:
            node = BSSMonomial("1", v1=v1, h0=h0)
            assert is_live(node, 4)
            assert differential(node, 2) is None
    assert is_live(BSSMonomial("h1", v1=2), 4)


def test_d3_normalization_matches_printed_yh2_squared_row():
    # y*h2^2 = D*x^3 by the E1 relation, hence Table 1 has source (5,3).
    source = BSSMonomial("x^3", D=1)
    assert source.bidegree == (5, 3)
    assert differential(source, 3) == BSSMonomial("1", k=1, D=1, h0=3)
    assert differential(source, 2) is None


def test_h0_torsion_and_early_incoming_layers():
    for D, k in product([-100, 0, 100], range(1, 5)):
        assert [is_live(BSSMonomial("1", k=k, D=D, h0=h0), 4) for h0 in range(5)] == [True, True, True, False, False]
        assert [is_live(BSSMonomial("h2", k=k, D=D, h0=h0), 4) for h0 in range(4)] == [True, True, False, False]
        assert [is_live(BSSMonomial("1", v1=6, k=k, D=D, h0=h0), 2) for h0 in range(3)] == [True, False, False]
        assert [is_live(BSSMonomial("h1", v1=2, k=k, D=D, h0=h0), 2) for h0 in range(3)] == [True, False, False]


def test_next_page_is_exact_coordinate_kernel_mod_image():
    # Oversized source coverage includes all predecessors of the inner audit
    # sample, including negative D shifts, v1+1 and the high-filtration wrap.
    outer = list(samples(v1_max=11, k_max=4, D_max=3, h0_max=6))
    inner = list(samples(v1_max=8, k_max=3, D_max=2, h0_max=4))
    for page in [1, 2, 3]:
        outgoing = {source for source in outer if differential(source, page) is not None}
        incoming = {differential(source, page) for source in outgoing}
        for monomial in inner:
            expected = is_live(monomial, page) and monomial not in outgoing and monomial not in incoming
            assert is_live(monomial, page+1) == expected, (page, monomial)


def test_no_window_dependent_fates_or_h0_cap_artifacts():
    # The source v1 lies outside this single-cell window, but h0*h1 is
    # nevertheless a d1 boundary and must not appear on E2.
    boundary = BSSMonomial("h1", h0=1)
    assert boundary in enumerate_window(1, 1, 1, 1, page=1, v1_max=0, h0_max=1)
    assert boundary not in enumerate_window(1, 1, 1, 1, page=2, v1_max=0, h0_max=1)
    # Here x^3 is outside the requested filtration window.
    late_boundary = BSSMonomial("1", k=1, h0=3)
    assert late_boundary in enumerate_window(-4, -4, 4, 4, page=3, v1_max=0, h0_max=3)
    assert late_boundary not in enumerate_window(-4, -4, 4, 4, page=4, v1_max=0, h0_max=3)
    # A source remains absent even when its target h0 level exceeds the cap.
    assert BSSMonomial("1", v1=2) not in enumerate_window(4, 4, 0, 0, page=3, v1_max=2, h0_max=0)


def test_enumeration_bounds_caps_and_no_duplicate_tuples():
    for page in [1, 2, 3, 4]:
        nodes = enumerate_window(-7, 13, 2, 7, page=page, v1_max=5, h0_max=2)
        assert nodes and len(nodes) == len(set(nodes))
        for node in nodes:
            stem, filtration = node.bidegree
            assert -7 <= stem <= 13 and 2 <= filtration <= 7
            assert node.v1 <= 5 and node.h0 <= 2 and is_live(node, page)
        assert nodes == list(iter_window(-7, 13, 2, 7, page=page, v1_max=5, h0_max=2))
    # Finite bidegree bounds alone do not bound v1, because D is invertible.
    assert BSSMonomial("1", v1=100, D=-25) in enumerate_window(0, 0, 0, 0, page=4, v1_max=100, h0_max=0)


@pytest.mark.parametrize("kwargs", [
    {"stem_min": 3, "stem_max": 2}, {"filtration_min": -1},
    {"filtration_min": 3, "filtration_max": 2}, {"v1_max": -1},
    {"h0_max": 1.5}, {"page": 0}, {"stem_max": True}, {"limit": 0},
])
def test_invalid_window_requests(kwargs):
    options = dict(stem_min=-4, stem_max=8, filtration_min=0, filtration_max=4, page=1, v1_max=4, h0_max=3)
    options.update(kwargs)
    with pytest.raises(ValueError):
        enumerate_window(**options)


def test_materialization_limit_and_symbolic_large_exponents():
    with pytest.raises(ValueError, match="materialization limit"):
        enumerate_window(-4, 8, 0, 4, page=1, v1_max=4, h0_max=3, limit=1)
    node = BSSMonomial("x^3", k=10**9, D=-(10**12), h0=10**8)
    assert differential(node, 3) == BSSMonomial("1", k=10**9+1, D=-(10**12), h0=10**8+3)
    assert not is_live(node, 4)
    assert is_live(BSSMonomial("1", v1=6, h0=10**12), 100)
    assert differential(BSSMonomial("1", v1=6), 100) is None
