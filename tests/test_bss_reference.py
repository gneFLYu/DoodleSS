"""The auxiliary Bockstein catalogs retain a third grading and source scope."""
from dataclasses import asdict
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from domain.bss_reference import E1_ADDITIVE_BASIS, E1_RELATIONS, create_bss_reference_workspaces


@pytest.fixture
def catalogs():
    return create_bss_reference_workspaces()


def test_stable_separate_workspaces_and_fresh_factories(catalogs):
    assert [w.id for w in catalogs] == ["ws_q8_bss_integer", "ws_q8_bss_sigma"]
    assert [len(w.differentials) for w in catalogs] == [6, 5]
    assert [asdict(w) for w in catalogs] == [asdict(w) for w in create_bss_reference_workspaces()]
    catalogs[0].settings["literature_review"]["notation"][0]["stem"] = 999
    assert create_bss_reference_workspaces()[0].settings["literature_review"]["notation"][0]["stem"] == 2


@pytest.mark.parametrize("index", [0, 1])
def test_catalog_scope_and_page_range(catalogs, index):
    ws = catalogs[index]
    assert ws.spectral_sequence == "2-bss" and ws.page == 1
    assert ws.settings["page_min"] == 1 and ws.settings["page_max"] == 4
    assert ws.settings["source_reference"] is True
    assert ws.settings["complete_page_model"] is False
    review = ws.settings["literature_review"]
    for field in ["title", "scope", "coverage", "source_refs", "notation", "relations", "periods", "warnings"]:
        assert review[field]
    assert "NOT a computed full" in review["warnings"][0]
    assert review["differential_degree"] == {"stem": -1, "filtration": 1, "bockstein_filtration": "r"}
    assert all(text.count("$") >= 2 and text.count("$") % 2 == 0 for text in review["periods"])


@pytest.mark.parametrize("index", [0, 1])
def test_each_arrow_has_bockstein_not_hfpss_degree(catalogs, index):
    ws = catalogs[index]
    nodes = {n.id: n for n in ws.classes}
    claims = {p.id: p for p in ws.propositions}
    assert len(nodes) == len(ws.classes)
    assert len(claims) == len(ws.propositions)
    for differential in ws.differentials:
        source, target = nodes[differential.source_id], nodes[differential.target_id]
        assert target.grade.stem-source.grade.stem == -1
        assert target.grade.filtration-source.grade.filtration == 1
        assert target.style["bockstein_filtration"]-source.style["bockstein_filtration"] == differential.page
        assert source.page == target.page == 1
        assert source.style["last_page"] == target.style["last_page"] == differential.page
        assert target.label.startswith("h_0")
        assert claims[differential.proposition_id].conclusion["spectral_sequence"] == "2-bss"
        assert source.period_stem == target.period_stem == differential.period_stem == 0


def test_beaudry_symbol_dictionary_and_c3_invariant_delta(catalogs):
    review = catalogs[0].settings["literature_review"]
    symbols = {x["symbol"]: x for x in review["notation"]}
    assert (symbols[r"\Delta"]["stem"], symbols[r"\Delta"]["filtration"]) == (24, 0)
    assert symbols["D"]["stem"] == 8
    assert "C3-invariant" in symbols[r"\Delta"]["meaning"]
    assert "zeta^2" in symbols["D"]["meaning"]
    assert "D^(-1) x_Bea" in symbols["x"]["meaning"]
    assert "D^(-2) y_Bea" in symbols["y"]["meaning"]
    assert "independent Bockstein filtration 1" in symbols[r"h_0"]["meaning"]


def test_complete_e1_presentation_and_additive_basis():
    assert len(E1_RELATIONS) == 11
    assert E1_RELATIONS[-1] == r"h_1^4=v_1^4k"
    assert [len(group["labels"]) for group in E1_ADDITIVE_BASIS] == [4, 4, 6]
    assert E1_ADDITIVE_BASIS[0]["v1_annihilator"] is None
    assert E1_ADDITIVE_BASIS[1]["v1_exponents"] == [0, 1]
    assert E1_ADDITIVE_BASIS[2]["v1_exponents"] == [0]


def test_integer_all_printed_families_and_selected_survivor_layers(catalogs):
    ws = catalogs[0]
    differential_claims = [p for p in ws.propositions if p.kind == "differential"]
    assert any("2n+1" in p.conclusion["family_formula"] for p in differential_claims)
    k = [c for c in ws.classes if c.id.startswith(ws.id+"_survivor_k_h0_")]
    assert [c.style["bockstein_filtration"] for c in k] == [0, 1, 2]
    assert all(c.page == 4 for c in k)
    h2 = [c for c in ws.classes if c.id.startswith(ws.id+"_survivor_h2_h0_")]
    assert len(h2) == 2
    assert any(p.kind == "extension" and "4kD" in p.statement for p in ws.propositions)
    assert any("v1^6" in warning for warning in ws.settings["literature_review"]["warnings"])


def test_sigma_sums_and_printed_degree_error_are_not_lost(catalogs):
    ws = catalogs[1]
    assert all(c.grade.representation == {"sigma_i": -1} for c in ws.classes)
    v1 = next(c for c in ws.classes if c.id.endswith("survivor_v1_squared_u_h0_0"))
    assert (v1.grade.stem, v1.grade.filtration) == (4, 0)
    sums = [c for c in ws.classes if c.style["dependent_combination"]]
    assert sums and all(r"\{" in c.label and r"\}" in c.label for c in sums)
    assert len([p for p in ws.propositions if p.kind == "extension"]) == 2
    assert any("nonhomogeneous" in warning for warning in ws.settings["literature_review"]["warnings"])
    for claim in ws.propositions:
        if claim.kind == "permanent-cycle":
            assert claim.conclusion["not_hfpss_permanence"] is True
