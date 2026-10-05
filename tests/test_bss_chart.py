"""Materialized Bockstein windows retain trigrading and exact excluded targets."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain.bss_chart import build_bss_window, integer_label_tex
from domain.bss_integer import BSSMonomial
from domain.models import ClassNode, Differential, Proposition


def coordinates(record):
    return record["basis"], record["v1"], record["k"], record["D"], record["h0"]


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_standard_chart_models_and_raw_payload(sector, page):
    payload = build_bss_window(sector, page=page, stem_min=-8, stem_max=16, filtration_max=8, v1_max=6, h0_max=3)
    assert payload["sector"] == sector and payload["workspace_id"] == f"ws_q8_bss_{sector}"
    assert payload["spectral_sequence"] == "2-bss"
    assert "records" not in payload
    assert payload["differential_degree"] == [-1, 1, page]
    assert payload["coverage_details"]["global_fate"] is True
    assert payload["coverage_details"]["full_cell_rank_claim"] is False
    assert "omitted, not zero" in payload["coverage"]
    json.dumps(payload)  # No dataclass or symbolic object leaks into the API.
    chart = payload["chart"]
    nodes = {node["id"]: node for node in chart["classes"]}
    claims = {claim["id"]: claim for claim in chart["propositions"]}
    assert len(nodes) == len(chart["classes"])
    raw = {item["id"]: item for item in payload["classes"]}
    for node in nodes.values():
        assert node["page"] == node["style"]["last_page"] == page
        assert isinstance(node["style"]["bockstein_filtration"], int)
        assert "e2_pattern" not in node["style"]
        assert not node["period_stem"] and not node["period_filtration"]
        assert node["coefficient_context_id"] == "q8-bss-f4-h0"
        assert set(node) <= set(ClassNode.__dataclass_fields__)
        ClassNode(**node)  # Omitted fields are optional model defaults.
        assert not node["style"].get("window_endpoint_only")
        if node["id"] not in raw:
            assert node["style"].get("bss_boundary") or node["style"].get("bss_combination")
    assert len(chart["differentials"]) == len(payload["differentials"])
    for arrow in chart["differentials"]:
        assert set(arrow) <= set(Differential.__dataclass_fields__)
        Differential(**arrow)
        source, target = nodes[arrow["source_id"]], nodes[arrow["target_id"]]
        assert source["id"] in raw or target["id"] in raw
        assert (target["grade"]["stem"]-source["grade"]["stem"],
                target["grade"]["filtration"]-source["grade"]["filtration"],
                target["style"]["bockstein_filtration"]-source["style"]["bockstein_filtration"]) == (-1, 1, page)
        assert set(claims[arrow["proposition_id"]]) <= set(Proposition.__dataclass_fields__)
        Proposition(**claims[arrow["proposition_id"]])
        assert claims[arrow["proposition_id"]]["conclusion"]["spectral_sequence"] == "2-bss"


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_identities_stable_across_pages_bounds_and_caps(sector):
    first = build_bss_window(sector, page=1, stem_min=-8, stem_max=16, filtration_max=8, v1_max=6, h0_max=3)
    later = build_bss_window(sector, page=4, stem_min=-4, stem_max=12, filtration_max=4, v1_max=8, h0_max=5)
    ids = {coordinates(record): record["id"] for record in first["classes"]}
    common = [record for record in later["classes"] if coordinates(record) in ids]
    assert common
    assert all(record["id"] == ids[coordinates(record)] for record in common)
    # The same coordinates in the other sector must never collide.
    other = build_bss_window("sigma" if sector == "integer" else "integer", page=1)
    assert not set(ids.values()).intersection(record["id"] for record in other["classes"])


def test_projected_h0_tower_has_distinct_nodes_but_common_tower_key():
    payload = build_bss_window("integer", page=4, stem_min=0, stem_max=0, filtration_max=0, v1_max=0, h0_max=4)
    nodes = payload["chart"]["classes"]
    assert len(nodes) == 5
    assert len({node["id"] for node in nodes}) == 5
    assert len({node["style"]["bss_tower_key"] for node in nodes}) == 1
    assert {node["style"]["bockstein_filtration"] for node in nodes} == set(range(5))
    assert {node["label"] for node in nodes} == {"1", "h_0", "h_0^{2}", "h_0^{3}", "h_0^{4}"}


@pytest.mark.parametrize("sector,source_basis,source_v1,source_stem,source_filtration,page", [
    ("integer", "1", 2, 4, 0, 2),
    ("integer", "x^3", 0, -3, 3, 3),
    ("sigma", "xh1^2", 0, 1, 3, 2),
])
def test_outside_target_is_reported_and_retained_as_endpoint(sector, source_basis, source_v1, source_stem, source_filtration, page):
    payload = build_bss_window(sector, page=page, stem_min=source_stem, stem_max=source_stem,
                               filtration_min=source_filtration, filtration_max=source_filtration,
                               v1_max=source_v1, h0_max=0)
    arrow = next(item for item in payload["differentials"]
                 if coordinates(item["source"]) == (source_basis, source_v1, 0, 0, 0))
    assert arrow["target_in_window"] is False
    assert {"stem_bounds", "filtration_bounds", "h0_cap"} <= set(arrow["target_excluded_by"])
    nodes = {node["id"]: node for node in payload["chart"]["classes"]}
    assert nodes[arrow["target_id"]]["style"]["bss_boundary"] == "outgoing_target"
    assert not nodes[arrow["target_id"]]["style"].get("window_endpoint_only")
    assert not any(node["id"] == arrow["target_id"] for node in payload["classes"])
    assert arrow["target"]["bockstein_filtration"] == page


def test_endpoint_only_identifier_matches_a_larger_window_visible_node():
    small = build_bss_window("integer", page=2, stem_min=4, stem_max=4, filtration_max=0, v1_max=2, h0_max=0)
    arrow = next(item for item in small["differentials"] if coordinates(item["source"]) == ("1", 2, 0, 0, 0))
    large = build_bss_window("integer", page=2, stem_min=3, stem_max=4, filtration_max=1, v1_max=2, h0_max=2)
    node = next(item for item in large["chart"]["classes"] if item["id"] == arrow["target_id"])
    assert not node["style"]["window_endpoint_only"]


def test_sigma_vectors_not_mechanical_name_sums_and_no_false_E3_sources():
    payload = build_bss_window("sigma", page=2, stem_min=1, stem_max=1, filtration_min=3, filtration_max=3, v1_max=0, h0_max=1)
    survivor = next(item for item in payload["classes"] if item["basis"] == "{xh1^2+v1x^2h1}")
    assert survivor["label"] == r"\{xh_1^2+x^2h_1v_1\}u_{\sigma_i}"
    assert len(survivor["representative_terms"]) == 2
    assert {term["basis"] for term in survivor["representative_terms"]} == {"h2^3", "x^2h1"}
    assert all(term["grade"] == survivor["grade"] for term in survivor["representative_terms"])
    assert not any(item["source_id"] == survivor["id"] for item in payload["differentials"])
    later = build_bss_window("sigma", page=3, stem_min=1, stem_max=1, filtration_min=3, filtration_max=3, v1_max=0, h0_max=0)
    assert not later["differentials"]
    assert any(item["id"] == survivor["id"] for item in later["classes"])
    assert all(item["basis"] != "xh1^2" for item in later["classes"])


def test_labels_collect_powers_and_keep_formal_h0():
    assert integer_label_tex(BSSMonomial("h1", v1=6, k=2, D=-3, h0=4)) == r"h_0^{4}h_1v_1^{6}k^{2}D^{-3}"
    assert integer_label_tex(BSSMonomial("1")) == "1"
    assert integer_label_tex(BSSMonomial("1", h0=1)) == "h_0"
    payload = build_bss_window("sigma", page=1, stem_min=0, stem_max=12, filtration_max=4, v1_max=6, h0_max=3)
    for record in payload["classes"]:
        assert record["label"] == record["label_tex"]
        if record["h0"]:
            assert record["label"].startswith("h_0")
        assert "(" not in record["label"]


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_chart_only_format_omits_duplicate_records_but_preserves_math(sector):
    options = dict(sector=sector, page=1, stem_min=-4, stem_max=8, filtration_max=4, v1_max=4, h0_max=2)
    full = build_bss_window(**options)
    compact = build_bss_window(**options, include_records=False)
    assert "classes" not in compact and "records" not in compact and "differentials" not in compact
    assert compact["coverage_details"] == full["coverage_details"]
    assert compact["chart"]["differentials"] == full["chart"]["differentials"]
    assert compact["chart"]["propositions"] == full["chart"]["propositions"]
    # Shared multiplication claims are now part of both formats. The compact
    # response still removes raw duplicate records, without deleting evidence.
    assert len(json.dumps(compact)) < len(json.dumps(full)) * 0.85
    originals = {node["id"]: node for node in full["chart"]["classes"]}
    for node in compact["chart"]["classes"]:
        original = originals[node["id"]]
        assert (node["label"], node["grade"], node["page"]) == (original["label"], original["grade"], original["page"])
        assert node["style"]["bockstein_filtration"] == original["style"]["bockstein_filtration"]
        assert node["style"].get("window_endpoint_only") == original["style"].get("window_endpoint_only")
        if node["style"].get("bss_combination"):
            assert node["style"]["bss_combination_terms"] == original["style"]["bss_combination_terms"]
            continue
        assert node["style"]["source_ref"] == "Exact 2-BSS engine; see workspace source review"
        if "+" in node["style"]["bss_monomial"]["basis"] and "+" in node["label"]:
            terms = node["style"]["bss_representative_terms"]
            assert len(terms) == 2
            assert all(set(term) == {"basis", "v1", "k", "D", "h0", "coefficient"} for term in terms)
    if sector == "integer":
        assert all("bss_representative_terms" not in node["style"] for node in compact["chart"]["classes"])


def test_off_window_predecessors_still_determine_page_membership():
    early = build_bss_window("integer", page=1, stem_min=1, stem_max=1, filtration_min=1, filtration_max=1, v1_max=0, h0_max=1)
    later = build_bss_window("integer", page=2, stem_min=1, stem_max=1, filtration_min=1, filtration_max=1, v1_max=0, h0_max=1)
    assert any(coordinates(record) == ("h1", 0, 0, 0, 1) for record in early["classes"])
    assert all(coordinates(record) != ("h1", 0, 0, 0, 1) for record in later["classes"])
    arrow = next(item for item in early["differentials"] if coordinates(item["source"]) == ("1", 1, 0, 0, 0))
    node = next(node for node in early["chart"]["classes"] if node["id"] == arrow["source_id"])
    assert node["style"]["bss_boundary"] == "incoming_source"
    assert not node["style"]["window_endpoint_only"]


def test_annotated_sigma_e2_has_three_real_target_layers():
    payload = build_bss_window("sigma", page=2, stem_min=-8, stem_max=24,
                               filtration_max=6, v1_max=4, h0_max=2)
    nodes = {node["id"]: node for node in payload["chart"]["classes"]}
    family = [arrow for arrow in payload["differentials"]
              if coordinates(arrow["source"])[:4] == ("xh1^2", 0, 0, 0)]
    assert len(family) == 3
    assert {arrow["target"]["h0"] for arrow in family} == {2, 3, 4}
    for arrow in family:
        target = nodes[arrow["target_id"]]
        assert not target["style"]["window_endpoint_only"]
        assert target["grade"]["stem"] == 0 and target["grade"]["filtration"] == 4
    assert sum(bool(nodes[arrow["target_id"]]["style"]["bss_boundary"]) for arrow in family) == 2


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_beaudry_relations_have_exact_page_degrees_and_real_endpoints(sector, page):
    payload = build_bss_window(sector, page=page, stem_min=-4, stem_max=12,
                               filtration_max=6, v1_max=4, h0_max=2)
    nodes = {node["id"]: node for node in payload["chart"]["classes"]}
    relations = [claim for claim in payload["chart"]["propositions"] if claim["kind"] == "relation"]
    assert relations and len(relations) == payload["coverage_details"]["relation_count"]
    for claim in relations:
        assert "Beaudry" in claim["source_ref"] and "A.14" in claim["source_ref"]
        assert "DKLLW" not in claim["source_ref"]
        con = claim["conclusion"]
        source, target = nodes[con["source_id"]], nodes[con["target_id"]]
        assert [target["grade"]["stem"] - source["grade"]["stem"],
                target["grade"]["filtration"] - source["grade"]["filtration"],
                target["style"]["bockstein_filtration"] - source["style"]["bockstein_filtration"]] == con["degree"]
        if target["style"].get("bss_combination"):
            assert len(con["target_coordinates"]) > 1
            assert all(term["class_id"] in nodes for term in con["target_coordinates"])
    h0_lines = [claim for claim in relations if claim["conclusion"]["multiplier"] == r"h_0"]
    assert h0_lines and all(claim["conclusion"]["degree"] == [0, 0, 1] for claim in h0_lines)


@pytest.mark.parametrize("kwargs", [
    {"sector": "C4"}, {"sector": None}, {"page": 0}, {"page": 5}, {"page": True},
    {"stem_min": 4, "stem_max": 3}, {"filtration_min": -1},
    {"h0_max": 1.2}, {"v1_max": -1}, {"limit": 0}, {"include_records": "false"},
])
def test_invalid_adapter_arguments(kwargs):
    options = {"sector": "integer", "page": 1}
    options.update(kwargs)
    with pytest.raises(ValueError):
        build_bss_window(**options)


def test_workspace_aliases_and_materialization_guard():
    assert build_bss_window("ws_q8_bss_integer", stem_min=0, stem_max=0, filtration_max=0, v1_max=0, h0_max=0)["sector"] == "integer"
    assert build_bss_window("ws_q8_bss_sigma", stem_min=0, stem_max=0, filtration_max=0, v1_max=0, h0_max=0)["sector"] == "sigma"
    with pytest.raises(ValueError, match="materialization limit"):
        build_bss_window("integer", limit=1)
