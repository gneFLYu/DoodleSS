"""D-strip aliases preserve page algebra, seams, and independent filtrations."""
from dataclasses import replace
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain import bss_integer, bss_sigma
from domain.bss_chart import _identifier, integer_label_tex
from domain.bss_multiplication import chart_operators, multiply
from domain.bss_periodic import build_bss_periodic_window
from domain.models import ClassNode, Differential, Proposition


def engine_and_class(sector):
    return ((bss_integer, bss_integer.BSSMonomial) if sector == "integer" else
            (bss_sigma, bss_sigma.SigmaMonomial))


def node_map(payload):
    return {node["id"]: node for node in payload["chart"]["classes"]}


def terms_for(node, cls):
    style = node["style"]
    return tuple(cls(**item) for item in style.get("bss_combination_monomials", [style.get("bss_monomial")]))


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
@pytest.mark.parametrize("projection", ["cohomology", "bockstein"])
def test_periodic_models_degrees_and_true_products(sector, page, projection):
    payload = build_bss_periodic_window(sector, page, filtration_max=4,
                                        v1_max=4, h0_max=2, projection=projection)
    engine, cls = engine_and_class(sector)
    nodes = node_map(payload)
    assert len(nodes) == len(payload["chart"]["classes"])
    assert payload["window"]["stem_min"] == 0 and payload["window"]["stem_max"] == 7
    assert payload["window"]["filtration_max"] == 4
    assert payload["projection"] == projection
    assert payload["projected_differential_degree"] == [-1, 1 if projection == "cohomology" else page]
    assert payload["periodicity"] == payload["chart"]["periodicity"]
    assert payload["periodicity"]["domain"] == "integer"
    assert payload["coverage_details"]["periodic_family_transport"]["forward"]["invertible"] is False
    assert "omitted, not zero" in payload["coverage"]
    assert "classes" not in payload and "differentials" not in payload
    json.dumps(payload)
    for node in nodes.values():
        ClassNode(**node)
        assert 0 <= node["grade"]["stem"] <= 7
        assert node["period_stem"] == 8 and node["period_filtration"] == 0
        assert node["style"]["chart_occurrence_only"] is False
        terms = terms_for(node, cls)
        assert all(engine.is_live(term, page) for term in terms)
        assert len({term.tridegree for term in terms}) == 1
        assert terms[0].tridegree == tuple(node["style"]["bss_seed_tridegree"])
        assert node["style"]["bss_cohomological_filtration"] == terms[0].bidegree[1]
        assert node["grade"]["filtration"] == (terms[0].bidegree[1] if projection == "cohomology" else terms[0].h0)
        for item in node["style"].get("bss_combination_terms", []):
            assert item["class_id"] in nodes
    claims = {claim["id"]: claim for claim in payload["chart"]["propositions"]}
    assert len(claims) == len(payload["chart"]["propositions"])
    for claim in claims.values():
        Proposition(**claim)
        con = claim["conclusion"]
        source, target = nodes[con["source_id"]], nodes[con["target_id"]]
        source_term = cls(**con["source_term"])
        target_terms = tuple(cls(**item) for item in con["target_terms"])
        assert source_term == terms_for(source, cls)[0]
        assert target_terms == tuple(replace(term, D=term.D+con["bss_target_period_offset"])
                                     for term in terms_for(target, cls))
        degree = [target["grade"]["stem"] + 8*con["bss_target_period_offset"] - source["grade"]["stem"],
                  target["grade"]["filtration"] - source["grade"]["filtration"]]
        assert degree == con["projected_degree"]
        assert tuple(b-a for a, b in zip(source_term.tridegree, target_terms[0].tridegree)) == tuple(con["tridegree"])
        if claim["kind"] == "differential":
            assert engine.differential(source_term, page) == target_terms[0]
            assert not engine.is_live(target_terms[0], page+1)
        else:
            operator = con["chart_connection"]["kind"]
            if operator == "two":
                operator = "h0"
            assert multiply(source_term, operator, page, sector) == target_terms
    for arrow in payload["chart"]["differentials"]:
        Differential(**arrow)
        assert arrow["proposition_id"] in claims
        assert arrow["source_id"] in nodes and arrow["target_id"] in nodes
        assert arrow["period_stem"] == 8 and not arrow["unperiodic_reason"]


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_no_horizontal_relation_is_lost_at_strip_seams(sector, page):
    payload = build_bss_periodic_window(sector, page, filtration_max=8, v1_max=8, h0_max=2)
    engine, cls = engine_and_class(sector)
    nodes = node_map(payload)
    relation_keys = {(claim["conclusion"]["source_id"], claim["conclusion"]["chart_connection"]["kind"])
                     for claim in payload["chart"]["propositions"] if claim["kind"] == "relation"}
    saw_seam = False
    for node in nodes.values():
        if not node["style"].get("bss_in_window"):
            continue
        term = cls(**node["style"]["bss_monomial"])
        for operator in chart_operators(page):
            products = multiply(term, operator, page, sector)
            if not products or not all(item.bidegree[1] <= 8 and item.v1 <= 8 and item.h0 <= 2 for item in products):
                continue
            kind = "two" if operator == "h0" else operator
            assert (node["id"], kind) in relation_keys
            saw_seam |= not 0 <= products[0].bidegree[0] <= 7
    assert saw_seam


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_projection_and_cap_changes_do_not_change_algebraic_ids(sector):
    options = dict(sector=sector, page=1, filtration_max=4, v1_max=4, h0_max=2)
    first = build_bss_periodic_window(**options, include_records=True)
    second = build_bss_periodic_window(**options, projection="bockstein", include_records=True)
    assert first["classes"] == second["classes"]  # Raw grading remains (stem,s).
    left, right = node_map(first), node_map(second)
    assert left.keys() == right.keys()
    for identifier, node in left.items():
        assert node["label"] == right[identifier]["label"]
        assert node["style"]["bss_periodic_family_key"] == right[identifier]["style"]["bss_periodic_family_key"]
    larger = build_bss_periodic_window(sector, page=1, filtration_max=12, v1_max=8, h0_max=5)
    assert set(left) <= node_map(larger).keys()
    assert len({record["id"] for record in first["classes"]}) == len(first["classes"])


@pytest.mark.parametrize("sector,page,basis,v1,h0", [
    ("integer", 2, "1", 4, 1), ("sigma", 2, "1", 4, 1),
    ("integer", 4, "1", 0, 3), ("sigma", 3, "1", 2, 2),
])
def test_k_does_not_fabricate_killed_successors(sector, page, basis, v1, h0):
    engine, cls = engine_and_class(sector)
    source = cls(basis, v1=v1, h0=h0)
    assert engine.is_live(source, page)
    assert not engine.is_live(replace(source, k=1), page)
    payload = build_bss_periodic_window(sector, page, filtration_max=8, v1_max=v1, h0_max=h0)
    source = replace(source, D=-(source.bidegree[0] // 8))
    node = node_map(payload)[_identifier(sector, source)]
    assert node["style"]["bss_k_forward_nonzero"] is False
    assert node["style"]["bss_k_predecessor_exists"] is False
    family = node["style"]["bss_periodic_family_key"]
    assert all(other["style"].get("bss_monomial", {}).get("k", 0) == 0
               for other in payload["chart"]["classes"]
               if other["style"]["bss_periodic_family_key"] == family)


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_family_preserves_v1_h0_and_only_connects_true_k_products(sector):
    engine, cls = engine_and_class(sector)
    payload = build_bss_periodic_window(sector, page=1, filtration_max=12, v1_max=4, h0_max=2)
    nodes = node_map(payload)
    source = cls("h1", v1=2, h0=1)
    canonical_source = replace(source, D=-(source.bidegree[0] // 8))
    source_node = nodes[_identifier(sector, canonical_source)]
    for k in range(3):
        target = replace(source, k=k)
        target = replace(target, D=-(target.bidegree[0] // 8))
        target_node = nodes[_identifier(sector, target)]
        assert source_node["style"]["bss_periodic_family_key"] == target_node["style"]["bss_periodic_family_key"]
        assert target_node["style"]["bss_family_k_min"] == 0
        assert target_node["style"]["bss_k_predecessor_exists"] == (k > 0)
    for field in ("v1", "h0"):
        changed = replace(source, **{field: 0})
        changed = replace(changed, D=-(changed.bidegree[0] // 8))
        assert nodes[_identifier(sector, changed)]["style"]["bss_periodic_family_key"] != source_node["style"]["bss_periodic_family_key"]


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_arbitrary_D_translations_commute_with_every_seed_differential(sector):
    engine, cls = engine_and_class(sector)
    for page in (1, 2, 3):
        payload = build_bss_periodic_window(sector, page, filtration_max=4, v1_max=6, h0_max=1,
                                            include_records=True)
        for arrow in payload["differentials"]:
            source = cls(**{key: arrow["source"][key] for key in ("basis", "v1", "k", "D", "h0")})
            target = cls(**{key: arrow["target"][key] for key in ("basis", "v1", "k", "D", "h0")})
            for shift in (-101, -1, 0, 1, 103):
                assert engine.differential(replace(source, D=source.D+shift), page) == replace(target, D=target.D+shift)


def test_boundary_targets_remain_explicit_and_raw_target_is_physical_equation():
    payload = build_bss_periodic_window("sigma", page=1, filtration_max=0, v1_max=0, h0_max=0,
                                        include_records=True)
    assert len(payload["classes"]) == 1
    arrow, = payload["differentials"]
    assert arrow["source"]["label"] == r"u_{\sigma_i}"
    assert arrow["target"]["label"] == r"h_0\{x+y\}u_{\sigma_i}"
    assert arrow["target"]["grade"]["stem"] == -1
    assert arrow["bss_target_period_offset"] == -1
    target = node_map(payload)[arrow["target_id"]]
    assert target["grade"]["stem"] == 7
    assert target["label"] == r"h_0\{x+y\}Du_{\sigma_i}"
    assert target["style"]["bss_boundary"] == "outgoing_target"
    assert not target["style"]["bss_in_window"]


@pytest.mark.parametrize("kwargs", [
    {"projection": "adams"}, {"projection": None}, {"include_records": "no"},
    {"page": 0}, {"page": 5}, {"sector": "C4"}, {"filtration_min": -1},
    {"filtration_min": 4, "filtration_max": 3}, {"h0_max": -1}, {"v1_max": 1.2},
    {"limit": 0}, {"limit": True}, {"limit": 1},
])
def test_invalid_periodic_inputs_and_size_guard(kwargs):
    options = dict(sector="integer")
    options.update(kwargs)
    with pytest.raises(ValueError):
        build_bss_periodic_window(**options)
