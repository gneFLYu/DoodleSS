"""Exact C4 multiplication ports and lazy horizontal periodic seed charts."""
from dataclasses import replace

import pytest

from backend.domain import c4_integer, c4_shifted
from backend.domain.c4_chart import build_c4_periodic_chart, build_c4_window
from backend.domain.models import ClassNode, Differential, Grade, Proposition


ENGINES = {"integer": c4_integer, "1-minus-sigma": c4_shifted}


def _relations(payload):
    return [claim for claim in payload["chart"]["propositions"] if claim["kind"] == "relation"]


@pytest.mark.parametrize("sector", ENGINES)
@pytest.mark.parametrize("page", (2, 3, 4, 5, 7, 11, 13, 14))
def test_periodic_nodes_and_all_endpoint_equations_are_exact(sector, page):
    engine = ENGINES[sector]
    payload = build_c4_periodic_chart(sector, page=page, filtration_max=16)
    chart = payload["chart"]
    nodes = {node["id"]: node for node in chart["classes"]}
    assert len(nodes) == len(chart["classes"])
    assert chart["periodicity"]["stem"] == 32
    assert chart["periodicity"]["filtration"] == 0
    assert chart["periodicity"]["generator"] == r"\Delta_1^4"
    assert chart["periodicity"]["permanent"]
    assert "vertical period" in payload["coverage"]
    for node in nodes.values():
        ClassNode(**{**node, "grade": Grade(**node["grade"])})
        assert 0 <= node["grade"]["stem"] <= 31
        assert node["period_stem"] == 32 and node["period_filtration"] == 0
        term = engine.Term(**node["style"]["c4_coefficient_branch"]["representative"])
        assert node["label"] == term.tex()
        assert term.stem == node["grade"]["stem"]
        assert engine.is_live(term, page)
    for arrow in chart["differentials"]:
        Differential(**arrow)
        assert arrow["period_stem"] == 32
    for claim in chart["propositions"]:
        Proposition(**claim)
        conclusion = claim["conclusion"]
        source_node, target_node = (nodes[conclusion[key]] for key in ("source_id", "target_id"))
        offset = conclusion["c4_target_period_offset"]
        source = engine.Term(**conclusion["source_term"])
        target = engine.Term(**conclusion["target_term"])
        assert target_node["grade"]["stem"] + 32 * offset - source_node["grade"]["stem"] == target.stem - source.stem
        assert target_node["grade"]["filtration"] - source_node["grade"]["filtration"] == target.filtration - source.filtration
        for exponent in (-3, -1, 0, 1, 4):
            source_copy = replace(source, d=source.d + 4 * exponent)
            target_copy = replace(target, d=target.d + 4 * exponent)
            assert engine.is_live(source_copy, page)
            assert engine.is_live(target_copy, page)
            actual = (engine.differential(source_copy, page) if claim["kind"] == "differential"
                      else engine.multiply(source_copy, conclusion["c4_multiplier"], page))
            assert actual == target_copy


def test_differential_crossing_left_seam_keeps_minus_one_degree():
    payload = build_c4_periodic_chart(page=5, filtration_min=8, filtration_max=8)
    claim = next(c for c in payload["chart"]["propositions"] if c["kind"] == "differential"
                 and c["conclusion"]["source_term"] == dict(family="varpi", q=4, d=-3, mu=0, two=0))
    nodes = {n["id"]: n for n in payload["chart"]["classes"]}
    conclusion = claim["conclusion"]
    assert nodes[conclusion["source_id"]]["grade"]["stem"] == 0
    assert nodes[conclusion["target_id"]]["grade"]["stem"] == 31
    assert conclusion["c4_target_period_offset"] == -1
    assert conclusion["c4_seed_target_grade"]["stem"] == -1
    assert nodes[conclusion["target_id"]]["style"]["window_endpoint_only"]


def test_eta_and_nu_right_seams_use_the_next_period_copy():
    payload = build_c4_periodic_chart(page=2, filtration_max=8)
    cases = (
        ("eta", dict(family="varsigma", q=3, d=1, mu=0, two=0)),
        ("nu", dict(family="nu", q=3, d=1, mu=0, two=0)),
    )
    nodes = {n["id"]: n for n in payload["chart"]["classes"]}
    for multiplier, source in cases:
        claim = next(c for c in _relations(payload) if c["conclusion"]["source_term"] == source
                     and c["conclusion"]["c4_multiplier"] == multiplier)
        conclusion = claim["conclusion"]
        assert nodes[conclusion["target_id"]]["grade"]["stem"] == 0
        assert conclusion["c4_target_period_offset"] == 1
        assert conclusion["c4_seed_target_grade"]["stem"] == 32


def test_shifted_completed_eta_tower_has_real_mu_coefficients():
    payload = build_c4_window("1-minus-sigma", page=14, stem_min=0, stem_max=2, filtration_max=2)
    relations = _relations(payload)
    first = next(c for c in relations if c["conclusion"]["source_term"] == dict(family="T2", q=0, d=0, mu=0, two=0)
                 and c["conclusion"]["c4_multiplier"] == "eta")
    assert first["conclusion"]["target_term"] == dict(family="varsigma", q=0, d=0, mu=1, two=0)
    assert first["conclusion"]["display_coefficient"]["latex"] == "1"
    second = next(c for c in relations if c["conclusion"]["source_term"] == first["conclusion"]["target_term"]
                  and c["conclusion"]["c4_multiplier"] == "eta")
    assert second["conclusion"]["target_term"] == dict(family="varpi", q=1, d=0, mu=2, two=0)
    assert second["conclusion"]["display_coefficient"]["latex"] == r"\mu"
    assert c4_shifted.multiply(c4_shifted.Term("varpi", 1, mu=2), "eta", 14) is None
    assert first["conclusion"]["c4_completed_mu_tail"] is False
    assert second["conclusion"]["c4_completed_mu_tail"] is True


def test_nu_square_selects_double_port_not_centre_or_double_edge_coefficient():
    payload = build_c4_window(page=2, stem_min=3, stem_max=3, filtration_min=1, filtration_max=1)
    claim = next(c for c in _relations(payload) if c["conclusion"]["c4_multiplier"] == "nu")
    conclusion = claim["conclusion"]
    assert conclusion["source_term"] == dict(family="nu", q=0, d=0, mu=0, two=0)
    assert conclusion["target_term"] == dict(family="varpi", q=1, d=0, mu=0, two=1)
    assert conclusion["c4_source_two"] == 0 and conclusion["c4_target_two"] == 1
    assert conclusion["display_coefficient"]["latex"] == "1"


def test_two_towers_distinguish_witt_tail_and_finite_four_torsion():
    payload = build_c4_window(page=2, stem_min=0, stem_max=6, filtration_max=2)
    nodes = {n["id"]: n for n in payload["chart"]["classes"]}
    two_relations = [c for c in _relations(payload) if c["conclusion"]["c4_multiplier"] == "2"]
    witt = next(c for c in two_relations if c["conclusion"]["source_term"] == dict(family="one", q=0, d=0, mu=0, two=0))
    finite = next(c for c in two_relations if c["conclusion"]["source_term"] == dict(family="varpi", q=1, d=0, mu=0, two=0))
    assert witt["conclusion"]["c4_unbounded_two_tower"]
    assert not finite["conclusion"]["c4_unbounded_two_tower"]
    assert witt["conclusion"]["source_id"] == witt["conclusion"]["target_id"]
    assert nodes[witt["conclusion"]["source_id"]]["style"]["c4_two_tower"]["two_max"] is None
    assert nodes[finite["conclusion"]["source_id"]]["style"]["c4_two_tower"]["two_max"] == 1
    assert not any(c["conclusion"]["source_term"] == dict(family="varpi", q=1, d=0, mu=0, two=1)
                   for c in two_relations)


def test_eta_products_use_page_quotients_and_never_infer_hidden_extensions():
    assert c4_integer.multiply(c4_integer.Term("eta2"), "eta", 2) == c4_integer.Term("varsigma", 1, -1, mu=1)
    assert c4_integer.multiply(c4_integer.Term("eta2"), "eta", 4) is None
    assert c4_integer.multiply(c4_integer.Term("nu"), "eta", 2) is None
    assert c4_shifted.multiply(c4_shifted.Term("eta"), "eta", 4) is None
    with pytest.raises(ValueError):
        c4_integer.multiply(c4_integer.Term("one"), "Delta")
    with pytest.raises(ValueError):
        c4_shifted.multiply(c4_shifted.Term("one"), "k")


def test_lazy_filtration_has_no_absolute_sixty_four_cutoff():
    high = build_c4_periodic_chart(page=2, filtration_min=128, filtration_max=140)
    assert high["chart"]["classes"]
    assert all(n["grade"]["filtration"] >= 128 for n in high["chart"]["classes"])
    assert not build_c4_periodic_chart(page=14, filtration_min=128, filtration_max=140)["chart"]["classes"]


def test_finite_window_core_equals_canonical_classes_and_copies_without_duplicates():
    periodic = build_c4_periodic_chart(page=3, filtration_min=0, filtration_max=6)
    canonical = {(tuple(n["style"]["c4_module_key"]), n["style"]["c4_coefficient_branch"]["mu_min"]): n
                 for n in periodic["chart"]["classes"]}
    finite = build_c4_window(page=3, stem_min=-67, stem_max=70, filtration_max=6)
    for node in finite["chart"]["classes"]:
        if node["style"]["window_endpoint_only"]:
            continue
        family, q, d = node["style"]["c4_module_key"]
        power = node["grade"]["stem"] // 32
        key = ((family, q, d - 4 * power), node["style"]["c4_coefficient_branch"]["mu_min"])
        seed = canonical[key]
        assert seed["grade"]["stem"] + 32 * power == node["grade"]["stem"]
        assert seed["style"]["c4_coefficient_branch"]["two_min"] == node["style"]["c4_coefficient_branch"]["two_min"]
    assert len(canonical) == len(periodic["chart"]["classes"])
