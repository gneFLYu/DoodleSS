"""Source equations and honest scope for the BBHS C4 review workspaces."""
from dataclasses import asdict

import pytest

from backend.domain.c4_reference import (
    CONTEXT, INTEGER_ID, SHIFTED_ID, Monomial, c4_differential_seeds,
    create_c4_reference_workspaces,
)


@pytest.fixture(scope="module")
def workspaces():
    return create_c4_reference_workspaces()


def test_new_workspaces_do_not_overwrite_historical_support_workspace(workspaces):
    assert [w.id for w in workspaces] == [INTEGER_ID, SHIFTED_ID]
    assert all(w.id != "ws_c4_j" for w in workspaces)
    assert all(w.group == "C4" and w.theory == "E_2" for w in workspaces)
    assert all(w.representation_basis == ["1", "sigma", "lambda"] for w in workspaces)


@pytest.mark.parametrize("shifted,count", [(False, 10), (True, 9)])
def test_published_seed_count_and_every_bidegree(shifted, count):
    seeds = c4_differential_seeds(shifted)
    assert len(seeds) == count
    assert {seed.page for seed in seeds} == {3, 5, 7, 11, 13}
    for seed in seeds:
        assert seed.target.integer_stem == seed.source.integer_stem - 1
        assert seed.target.filtration == seed.source.filtration + seed.page
        assert seed.target.grade().representation == seed.source.grade().representation
        assert "Proposition 5." in seed.citation


def test_delta_eight_is_not_beaudry_delta_twentyfour(workspaces):
    assert Monomial(delta=1).grade().stem == 8
    assert Monomial(delta=4).grade().stem == 32
    for ws in workspaces:
        notation = {item["symbol"]: item for item in ws.settings["literature_review"]["notation"]}
        assert notation[r"\Delta_1"]["stem"] == 8
        assert "degree-24" in notation[r"\Delta_1"]["meaning"]
        assert "not the F4" in notation[r"\varsigma"]["meaning"]


def test_shifted_integer_coordinate_is_not_ro_dimension():
    grade = Monomial(p=1).grade()
    assert grade.stem == -4
    assert grade.representation == {"1": 1, "sigma": -1}
    # -4 + (1-sigma) = -3-sigma.
    assert grade.stem + grade.representation["1"] == -3
    assert Monomial(delta=1, p=1).grade().stem == 4


def test_e2_module_motif_not_artificial_f4_vector_space(workspaces):
    integer = workspaces[0]
    nodes = {node.label: node for node in integer.classes}
    assert nodes["1"].style["reference_coefficient_module"] == "W(k)[[mu]]"
    assert nodes[r"\nu"].style["reference_coefficient_module"] == "k; mu=0"
    assert nodes[r"\eta"].style["reference_coefficient_module"] == "k[[mu]]"
    assert nodes[r"\varpi"].style["reference_coefficient_module"] == "W(k)[[mu]]/(4,2*mu)"
    assert all(node.coefficient_context_id == CONTEXT for node in integer.classes)
    assert all("e2_pattern" not in node.style for node in integer.classes)


def test_e2_family_counts_each_internal_degree_modulo_eight():
    ws = create_c4_reference_workspaces(stem_min=0, stem_max=7, filtration_max=6)[0]
    motif = [node for node in ws.classes if node.style["reference_role"] == "e2_module"]
    for s in range(7):
        in_degree = [node for node in motif if node.grade.filtration == s]
        assert len(in_degree) == (3 if s % 2 else 2)
        assert {((node.grade.stem + s) % 8) for node in in_degree} == ({2, 4, 6} if s % 2 else {0, 4})


def test_literal_two_coefficient_endpoints_preserved(workspaces):
    integer = workspaces[0]
    nodes = {node.id: node for node in integer.classes}
    d7 = next(d for d in integer.differentials if d.id.endswith("d7-two-delta"))
    assert nodes[d7.source_id].label == r"2 \Delta_1"
    d11 = next(d for d in integer.differentials if d.page == 11)
    assert nodes[d11.target_id].label == r"2 \varpi^{7} \Delta_1^{-4}"
    assert nodes[d7.source_id].style["reference_role"] == "differential_seed_alias"


def test_page_scoped_linearity_not_universal_delta_period(workspaces):
    for ws in workspaces:
        assert ws.settings["rendering"]["periodicity"] == []
        for prop in ws.propositions:
            if prop.kind != "differential":
                continue
            page = prop.conclusion["page"]
            assert prop.conclusion["delta_period_power"] == (1 if page == 3 else 2 if page == 5 else 4)
            assert prop.conclusion["module_closure_materialized"] is False
        assert all(d.period_stem == 0 and d.period_filtration == 0 for d in ws.differentials)


def test_limitations_and_height_distinction_remain_user_visible(workspaces):
    for ws in workspaces:
        metadata = ws.settings["literature_review"]
        assert ws.settings["source_reference"] is True
        assert "computed E2-E14 views loaded on demand" in ws.summary
        assert "stored catalog is not a higher-page quotient" in metadata["coverage"]
        warning = " ".join(metadata["warnings"])
        assert "height 4" in warning and "384" in warning
        assert "d5(u_{2sigma})=0" in warning
        assert "not a zero-differential assertion" in warning
        assert not ws.fates and not ws.differential_events
        assert "Q8" not in str([asdict(node.grade) for node in ws.classes])


@pytest.mark.parametrize("kwargs", [dict(stem_min=1, stem_max=0), dict(filtration_max=-1), dict(stem_min=True), dict(stem_max=2.0)])
def test_invalid_windows_rejected(kwargs):
    with pytest.raises(ValueError):
        create_c4_reference_workspaces(**kwargs)
