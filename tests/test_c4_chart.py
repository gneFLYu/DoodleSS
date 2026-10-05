"""Audit the C4 coefficient-module adapter, independently of glyph geometry.

In particular, W/4 and its ideal 2W/4 must not be interpreted as the same
rank-one F4 vector, and a completed mu tail is not a list of sampled powers.
"""
from dataclasses import replace
from itertools import product

import pytest

from backend.domain import c4_integer, c4_shifted
from backend.domain.c4_chart import build_c4_window
from backend.domain.c4_reference import CONTEXT, CONVENTION
from backend.domain.models import ClassNode, Differential, Grade, Proposition


ENGINES = {"integer": c4_integer, "1-minus-sigma": c4_shifted}


def _nodes(payload):
    return {node["id"]: node for node in payload["chart"]["classes"]}


def _branch_node(payload, family, q=0, d=0, mu=0):
    return next(node for node in payload["chart"]["classes"]
                if node["style"]["c4_module_key"] == [family, q, d]
                and node["style"]["c4_coefficient_branch"]["mu_min"] == mu)


def _contains(branch, term):
    return (branch["mu_min"] <= term.mu
            and (branch["mu_max"] is None or term.mu <= branch["mu_max"])
            and branch["two_min"] <= term.two
            and (branch["two_max"] is None or term.two <= branch["two_max"]))


@pytest.mark.parametrize("sector", ENGINES)
@pytest.mark.parametrize("page", range(2, 15))
def test_chart_models_and_each_exact_arrow_endpoint(sector, page):
    engine = ENGINES[sector]
    payload = build_c4_window(sector, page=page)
    chart = payload["chart"]
    nodes = _nodes(payload)
    claims = {claim["id"]: claim for claim in chart["propositions"]}
    assert len(nodes) == len(chart["classes"])
    assert len(claims) == len(chart["propositions"])
    assert len({arrow["id"] for arrow in chart["differentials"]}) == len(chart["differentials"])
    assert len(chart["differentials"]) == len(payload["differentials"]) == sum(c["kind"] == "differential" for c in claims.values())
    assert payload["differential_degree"] == [-1, page]
    assert payload["source_refs"]
    for node in nodes.values():
        ClassNode(**{**node, "grade": Grade(**node["grade"])})
        assert node["page"] == node["style"]["last_page"] == page
        assert node["coefficient_context_id"] == CONTEXT
        assert node["convention_id"] == CONVENTION
        assert node["style"]["c4_scalar_ports_are_not_module_basis"] is True
        branch = node["style"]["c4_coefficient_branch"]
        representative = engine.Term(**branch["representative"])
        assert engine.is_live(representative, page)
        assert node["label"] == representative.tex()
        assert node["grade"]["stem"] == representative.stem
        assert node["grade"]["filtration"] == representative.filtration
        assert node["grade"]["representation"] == ({"1": 1, "sigma": -1} if sector != "integer" else {})
        assert node["style"]["glyph"] == ("square" if branch["two_max"] is None else "dot")
        assert "e2_pattern" not in node["style"]
        assert "bockstein_filtration" not in node["style"]
        assert node["period_stem"] == node["period_filtration"] == 0
    for arrow, record in zip(chart["differentials"], payload["differentials"]):
        Differential(**arrow)
        claim = claims[arrow["proposition_id"]]
        Proposition(**claim)
        source, target = (nodes[arrow[key]] for key in ("source_id", "target_id"))
        source_term, target_term = (engine.Term(**record[key]) for key in ("source", "target"))
        assert engine.differential(source_term, page) == target_term
        assert (target_term.stem - source_term.stem, target_term.filtration - source_term.filtration) == (-1, page)
        assert _contains(source["style"]["c4_coefficient_branch"], source_term)
        assert _contains(target["style"]["c4_coefficient_branch"], target_term)
        conclusion = claim["conclusion"]
        assert conclusion["source_id"] == source["id"]
        assert conclusion["target_id"] == target["id"]
        assert conclusion["c4_source_two"] == source_term.two
        assert conclusion["c4_target_two"] == target_term.two
        assert conclusion["c4_source_mu"] == source_term.mu
        assert conclusion["c4_target_mu"] == target_term.mu
        assert record["target_in_window"] is not target["style"]["window_endpoint_only"]
        target_mu_base = target["style"]["c4_coefficient_branch"]["mu_min"]
        assert arrow["display_coefficient"]["mu_exponent"] == target_term.mu - target_mu_base
        assert arrow["display_coefficient"]["kind"] == "c4-coefficient"


def test_witt_branch_ids_are_stable_while_the_kernel_generator_changes():
    payloads = [build_c4_window(page=page, stem_min=8, stem_max=8, filtration_max=0)
                for page in (5, 6, 8, 14)]
    constant = [_branch_node(payload, "one", d=1) for payload in payloads]
    tails = [_branch_node(payload, "one", d=1, mu=1) for payload in payloads]
    assert len({node["id"] for node in constant}) == len({node["id"] for node in tails}) == 1
    assert [node["label"] for node in constant] == [r"\Delta_1", r"2 \Delta_1", r"4 \Delta_1", r"4 \Delta_1"]
    assert [node["style"]["c4_coefficient_branch"]["two_min"] for node in constant] == [0, 1, 2, 2]
    assert all(node["label"] == r"\mu \Delta_1" for node in tails)
    assert all(node["style"]["c4_coefficient_branch"]["two_max"] is None for node in constant + tails)
    assert all(node["style"]["c4_scalar_ports_are_not_module_basis"] for node in constant + tails)
    # E6 is the ideal (2, mu), not the ideal (2) and not two independent
    # completed-module generators. E8 changes it to (4, mu).
    for payload in payloads[1:]:
        cell, = payload["cells"]
        assert cell["base_ring"] == "W(k)[[mu]]"
        assert len(cell["branches"]) == 2
        assert cell["branches"][1]["completed_mu_tail"]
        assert cell["branches"][1]["mu_max"] is None


def test_d3_mu_edge_is_relative_to_the_target_branch_not_the_raw_shift():
    payload = build_c4_window(page=3, stem_min=4, stem_max=4, filtration_max=0)
    records = payload["differentials"]
    arrows = payload["chart"]["differentials"]
    assert len(records) == 2
    assert [record["mu_exponent_shift"] for record in records] == [1, 1]
    assert [arrow["display_coefficient"]["latex"] for arrow in arrows] == ["1", r"\mu"]
    assert [arrow["display_coefficient"]["mu_exponent"] for arrow in arrows] == [0, 1]
    assert arrows[0]["target_id"] == arrows[1]["target_id"]
    target = _nodes(payload)[arrows[0]["target_id"]]
    assert target["label"] == r"\mu \varsigma \varpi \Delta_1^{-1}"
    assert target["style"]["window_endpoint_only"]
    # Both constant and completed-tail source maps have kernel 2W.
    after = build_c4_window(page=4, stem_min=4, stem_max=4, filtration_max=0)
    assert [branch["two_min"] for branch in after["cells"][0]["branches"]] == [1, 1]
    assert [node["label"] for node in after["chart"]["classes"]] == [r"2 T_2", r"2 \mu T_2"]


def test_d3_witt_four_torsion_kernel_is_two_w_over_four_not_an_f4_rank():
    before = build_c4_window(page=3, stem_min=6, stem_max=6, filtration_min=2, filtration_max=2)
    constant = _branch_node(before, "varpi", q=1)
    tail = _branch_node(before, "varpi", q=1, mu=1)
    assert constant["style"]["c4_coefficient_branch"]["two_max"] == 1
    assert tail["style"]["c4_coefficient_branch"]["two_max"] == 0
    after = build_c4_window(page=4, stem_min=6, stem_max=6, filtration_min=2, filtration_max=2)
    survivor, = after["chart"]["classes"]
    branch = survivor["style"]["c4_coefficient_branch"]
    assert survivor["id"] == constant["id"]
    assert survivor["label"] == r"2 \varpi"
    assert (branch["mu_min"], branch["mu_max"], branch["two_min"], branch["two_max"]) == (0, 0, 1, 1)
    assert branch["coefficient_description"] == "2^1W(k)/2^2"
    assert not branch["completed_mu_tail"]
    # 2mu*varpi=0 already on E2; the remaining 2varpi cannot be extended
    # to an invented completed F4[[mu]] tail.
    assert not c4_integer.e2_nonzero(c4_integer.Term("varpi", q=1, mu=1, two=1))


@pytest.mark.parametrize("page,source,target_two,target_two_min", [
    (5, c4_integer.Term("nu", q=1), 1, 0),
    (7, c4_integer.Term("one", d=1, two=1), 0, 0),
    (11, c4_integer.Term("varsigma", q=1), 1, 1),
    (13, c4_integer.Term("varpi", q=1, d=3, two=1), 0, 0),
])
def test_coefficient_ports_retain_absolute_two_valuation(page, source, target_two, target_two_min):
    payload = build_c4_window(page=page, stem_min=source.stem, stem_max=source.stem,
                              filtration_min=source.filtration, filtration_max=source.filtration)
    record, = payload["differentials"]
    arrow, = payload["chart"]["differentials"]
    claim, = [claim for claim in payload["chart"]["propositions"] if claim["kind"] == "differential"]
    target_node = _nodes(payload)[arrow["target_id"]]
    assert record["source"] == source.__dict__
    assert claim["conclusion"]["c4_source_two"] == source.two
    assert claim["conclusion"]["c4_target_two"] == target_two
    assert target_node["style"]["c4_coefficient_branch"]["two_min"] == target_two_min
    assert arrow["display_coefficient"]["latex"] == "1"
    # The factor 2 is a coefficient port, not both a port and an edge label.
    if page == 5:
        assert target_node["label"] == r"\varpi^{4} \Delta_1^{-2}"
        assert target_node["style"]["c4_coefficient_branch"]["two_max"] == 1
    if page == 11:
        assert target_node["label"] == r"2 \varpi^{7} \Delta_1^{-4}"


@pytest.mark.parametrize("sector", ENGINES)
@pytest.mark.parametrize("page", c4_integer.DIFFERENTIAL_PAGES)
def test_component_maps_are_witt_and_mu_linear_not_f4_rank_maps(sector, page):
    engine = ENGINES[sector]
    payload = build_c4_window(sector, page=page, stem_min=-40, stem_max=72, filtration_max=32)
    assert payload["differentials"]
    for record in payload["differentials"]:
        source, target = (engine.Term(**record[key]) for key in ("source", "target"))
        # All printed nonzero component maps reduce coefficients modulo 2:
        # their images must have order 2 even when the target cell began as W/4.
        assert not engine.is_live(replace(target, two=target.two + 1), page)
        assert engine.differential(replace(source, two=source.two + 1), page) is None
        assert record["kernel_two_min"] == source.two + 1
        # Mu is a permanent coefficient, not an invertible F4 scalar. If it
        # annihilates a target, the corresponding source multiple maps to zero.
        for exponent in (1, 2, 9):
            multiplied_source = replace(source, mu=source.mu + exponent)
            multiplied_target = replace(target, mu=target.mu + exponent)
            expected = multiplied_target if engine.is_live(multiplied_target, page) else None
            if not engine.is_live(multiplied_source, page):
                assert expected is None
            assert engine.differential(multiplied_source, page) == expected


def _permanent_product(engine, term, varpi, delta):
    """Multiply by a literal permanent monomial; do not invert it."""
    if term is None:
        return None
    factors = {"varpi": term.q + varpi, "delta": term.d + delta,
               "mu": term.mu, "two": term.two}
    if term.family not in ("one", "varpi"):
        key, power = {"T2": ("t2", 1), "eta2": ("eta", 2)}.get(term.family, (term.family, 1))
        factors[key] = power
    return engine.normalize_monomial(**factors)


@pytest.mark.parametrize("sector", ENGINES)
@pytest.mark.parametrize("page", c4_integer.DIFFERENTIAL_PAGES)
@pytest.mark.parametrize("varpi,delta", [(2, 1), (4, -2)])
def test_permanent_kappa_bar_and_epsilon_products_commute_even_at_low_q(sector, page, varpi, delta):
    """These permanent classes are NOT units, so test maps and annihilation.

This detects missing downward-forced maps invisible to an upward-only seed
test: for example d11(varsigma*Delta*p) at q=0. A nonzero product arrow cannot
be assigned to a permanent source merely because q=0 was absent from a seed.
"""
    engine = ENGINES[sector]
    for family in engine.FAMILIES:
        qs = (0,) if family in ("one", "T2") else range(1 if family == "varpi" else 0, 6)
        for q, d, mu, two in product(qs, range(4), range(2), range(2)):
            source = engine.Term(family, q, d, mu, two)
            if not engine.is_live(source, page):
                continue
            source_product = _permanent_product(engine, source, varpi, delta)
            target = engine.differential(source, page)
            target_product = _permanent_product(engine, target, varpi, delta)
            if target_product is not None and not engine.is_live(target_product, page):
                target_product = None
            actual = engine.differential(source_product, page) if source_product is not None else None
            assert actual == target_product, (sector, source, page, varpi, delta)


@pytest.mark.parametrize("page,source,target", [
    (11, c4_shifted.Term("varsigma", d=1), c4_shifted.Term("varpi", q=6, d=-3, two=1)),
    (13, c4_shifted.Term("nu", d=2), c4_shifted.Term("varpi", q=7, d=-3)),
    (13, c4_shifted.Term("one", d=4, two=1), c4_shifted.Term("nu", q=6, d=-1)),
])
def test_shifted_low_q_forced_arrows_materialize_without_false_unit_cancellation(page, source, target):
    # Multiplication by kappa_bar is injective on each specific order-two
    # target line here, even though it is not injective on the whole page.
    product_target = _permanent_product(c4_shifted, target, 2, 1)
    assert c4_shifted.is_live(target, page)
    assert c4_shifted.is_live(product_target, page)
    assert not c4_shifted.is_live(replace(target, two=target.two + 1), page)
    assert not c4_shifted.is_live(replace(product_target, two=product_target.two + 1), page)
    assert c4_shifted.differential(source, page) == target
    payload = build_c4_window("1-minus-sigma", page=page, stem_min=source.stem, stem_max=source.stem,
                              filtration_min=source.filtration, filtration_max=source.filtration)
    record, = payload["differentials"]
    assert record["source"] == source.__dict__
    assert record["target"] == target.__dict__
    assert record["target_in_window"] is False
    after = build_c4_window("1-minus-sigma", page=page + 1, stem_min=source.stem, stem_max=source.stem,
                            filtration_min=source.filtration, filtration_max=source.filtration)
    visible = [node for node in after["chart"]["classes"] if not node["style"]["window_endpoint_only"]]
    if source.family == "one":
        assert [node["label"] for node in visible] == [r"4 \Delta_1^{4} \mathfrak p", r"2 \mu \Delta_1^{4} \mathfrak p"]
    elif source.family == "varsigma":
        assert [node["label"] for node in visible] == [r"\mu \varsigma \Delta_1 \mathfrak p"]
    else:
        assert visible == []


def test_off_window_target_is_retained_and_does_not_make_the_source_permanent():
    source = c4_integer.Term("varpi", q=7, d=-2, two=1)
    payload = build_c4_window(page=13, stem_min=26, stem_max=26, filtration_min=14, filtration_max=14)
    record, = payload["differentials"]
    arrow, = payload["chart"]["differentials"]
    nodes = _nodes(payload)
    assert record["source"] == source.__dict__
    assert record["target"] == c4_integer.Term("nu", q=13, d=-7).__dict__
    assert record["target_in_window"] is False
    assert not nodes[arrow["source_id"]]["style"]["window_endpoint_only"]
    assert nodes[arrow["target_id"]]["style"]["window_endpoint_only"]
    after = build_c4_window(page=14, stem_min=26, stem_max=26, filtration_min=14, filtration_max=14)
    assert after["cells"] == []
    assert after["chart"]["classes"] == []
    # Conversely, an in-window target still disappears when its source was
    # not rendered in that target-only viewport.
    target_before = build_c4_window(page=13, stem_min=25, stem_max=25, filtration_min=27, filtration_max=27)
    assert target_before["chart"]["classes"]
    assert not target_before["chart"]["differentials"]
    target_after = build_c4_window(page=14, stem_min=25, stem_max=25, filtration_min=27, filtration_max=27)
    assert target_after["chart"]["classes"] == []


@pytest.mark.parametrize("sector", ENGINES)
def test_chart_only_payload_preserves_geometry_and_claims_without_raw_records(sector):
    full = build_c4_window(sector, page=3)
    compact = build_c4_window(sector, page=3, include_records=False)
    assert "cells" not in compact and "differentials" not in compact
    assert compact["chart"] == full["chart"]
    assert compact["window"] == full["window"]
    assert compact["coverage"] == full["coverage"]
    assert "hidden extensions" in compact["coverage"]
    assert "Mackey" in compact["coverage"]


@pytest.mark.parametrize("arguments", [
    {"sector": "sigma"}, {"sector": "Q8"}, {"page": 1}, {"page": 15},
    {"page": True}, {"page": 3.0}, {"stem_min": 2, "stem_max": 1},
    {"filtration_min": -1}, {"filtration_min": 4, "filtration_max": 3},
    {"stem_min": 0.5}, {"filtration_max": True},
    {"stem_min": -1000, "stem_max": 1000, "filtration_max": 1000},
])
def test_invalid_chart_requests_raise_value_error(arguments):
    with pytest.raises(ValueError):
        build_c4_window(**arguments)
