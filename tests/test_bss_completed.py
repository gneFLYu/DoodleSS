"""Independent algebraic checks of the symbolic j-completion adapter."""
from dataclasses import replace

import pytest

from backend.domain import bss_integer as integer, bss_sigma as sigma
from backend.domain.bss_completed import (
    completed_module, iter_modules, resolve_vector, expand_coordinates,
    build_bss_completed_chart, J_COMPLETION,
)
from backend.domain.bss_multiplication import multiply, chart_operators


def j_product(terms, page, sector):
    return sigma._xor(replace(result, D=result.D-1) for term in terms
                      for result in multiply(term, "v1^4", page, sector))


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_every_live_coordinate_has_exact_module_coordinate(sector, page):
    engine = integer if sector == "integer" else sigma
    for term in engine.iter_window(-16, 16, 0, 12, page=page, v1_max=17, h0_max=4):
        coordinates = resolve_vector((term,), sector, page)
        assert expand_coordinates(coordinates) == (term,)
        for module, power, _ in coordinates:
            assert module.tridegree[0] in range(8)
            assert power >= 0
            assert module.kind == "free" or power == 0


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_classification_is_exact_j_action_not_v1_sampling(sector, page):
    engine = integer if sector == "integer" else sigma
    for module in iter_modules(sector, page, 0, 12, 4):
        assert j_product(module.lift(), page, sector) == module.lift(1)
        for n in (0, 1, 2, 100_000):
            terms = module.lift(n)
            assert all(engine.is_live(term, page) for term in terms)
            if module.kind == "free":
                assert terms
                assert resolve_vector(terms, sector, page) == ((module, n, 0),)
                assert j_product(terms, page, sector) == module.lift(n+1)
            else:
                assert bool(terms) == (n == 0)


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_maps_are_j_linear_including_free_to_torsion(sector, page):
    engine = integer if sector == "integer" else sigma
    for module in iter_modules(sector, page, 0, 8, 3):
        for operation in (None, *chart_operators(page)):
            def image(terms):
                if operation is None:
                    return sigma._xor(target for term in terms
                        if (target := engine.differential(term, page)) is not None)
                return sigma._xor(target for term in terms
                    for target in multiply(term, operation, page, sector))
            mapped = image(module.lift())
            assert image(module.lift(1)) == j_product(mapped, page, sector)
            assert expand_coordinates(resolve_vector(mapped, sector, page)) == mapped
            if module.kind == "torsion":
                assert not j_product(mapped, page, sector)


def test_sigma_adapted_A_is_not_torsion_or_extra_rank():
    A = sigma.SigmaMonomial("{h1+v1x}")
    E1 = resolve_vector((A,), "sigma", 1)
    assert len(E1) == 2
    assert {module.kind for module, _, _ in E1} == {"free", "torsion"}
    assert j_product((A,), 1, "sigma") == (sigma.SigmaMonomial("h1", v1=4, D=-1),)
    E2 = resolve_vector((A,), "sigma", 2)
    assert len(E2) == 1
    module, power, offset = E2[0]
    assert module.kind == "free" and power == offset == 0
    assert module.lift(1) == (sigma.SigmaMonomial("h1", v1=4, D=-1),)
    assert sum(m.basis == "h1" and m.residue == 0 and m.k == m.h0 == 0
               for m in iter_modules("sigma", 2)) == 1


def test_integer_d2_kills_only_constant_not_whole_free_module():
    before = completed_module("integer", 2, "1", 2)
    after = completed_module("integer", 3, "1", 2)
    assert before.kind == after.kind == "free"
    assert before.j_min == 0 and after.j_min == 1
    assert after.lift() == (integer.BSSMonomial("1", v1=6, D=-1),)
    assert integer.differential(before.lift()[0], 2) == integer.BSSMonomial("h2", h0=2)
    assert integer.differential(before.lift(1)[0], 2) is None
    with pytest.raises(ValueError):
        resolve_vector(before.lift(), "integer", 3)


def test_sigma_d1_leaves_scalar_j_tail_and_positive_h0_k_quotient():
    module = completed_module("sigma", 2, "1", 0)
    assert module.kind == "free" and module.j_min == 1
    assert module.lift() == (sigma.SigmaMonomial("1", v1=4, D=-1),)
    assert completed_module("sigma", 2, "1", 0, k=1, h0=1) is None
    point = completed_module("sigma", 2, "1", 2, k=1, h0=2)
    assert point.kind == "torsion" and point.length == 1
    assert completed_module("sigma", 3, "1", 2, k=1, h0=2) is None


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_chart_has_complete_endpoints_exact_coefficients_and_no_v1_cap(sector, page):
    result = build_bss_completed_chart(sector, page, filtration_max=8, h0_max=0)
    assert "v1_max" not in result["window"]
    assert result["j_completion"]["tridegree"] == [0, 0, 0]
    chart = result["chart"]
    nodes = {node["id"]: node for node in chart["classes"]}
    assert all(0 <= node["grade"]["stem"] <= 7 for node in nodes.values())
    engine = integer if sector == "integer" else sigma
    cls = integer.BSSMonomial if sector == "integer" else sigma.SigmaMonomial
    for claim in chart["propositions"]:
        con = claim["conclusion"]
        assert con["source_id"] in nodes and con["target_id"] in nodes
        assert con["bss_j_source_power"] == 0
        assert con["bss_j_target_power"] >= 0
        source = tuple(cls(**term) for term in con["source_terms"])
        targets = tuple(cls(**term) for term in con["target_terms"])
        if claim["kind"] == "differential":
            actual = sigma._xor(target for term in source
                if (target := engine.differential(term, page)) is not None)
            assert actual == targets
        coordinates = resolve_vector(targets, sector, page)
        assert [(module.id, power, offset) for module, power, offset in coordinates] == [
            (item["class_id"], item["j_power"], item["bss_period_offset"])
            for item in con["target_coordinates"]]
        for module, _, _ in coordinates:
            assert module.id in nodes
    independent = [node for node in nodes.values() if "bss_j_module" in node["style"]]
    assert sum(node["style"]["bss_in_window"] for node in independent) == result["coverage_details"]["module_generator_count"]


def test_nonunit_incoming_j_image_is_preserved():
    result = build_bss_completed_chart("integer", 1, filtration_min=4, filtration_max=4, h0_max=1)
    nodes = {n["id"]: n for n in result["chart"]["classes"]}
    claims = [c for c in result["chart"]["propositions"] if c["kind"] == "differential"]
    # d1(v1*h1^3)=h0*v1^4*k = j*(h0*k*D); target lowest generator is not itself a boundary.
    match = [c for c in claims if c["conclusion"]["source_term"]["basis"] == "h1^3"
             and c["conclusion"]["source_term"]["v1"] == 1]
    assert match
    for claim in match:
        con = claim["conclusion"]
        assert con["bss_j_target_power"] == 1
        assert con["bss_j_coefficient_tex"] == "j"
        assert nodes[con["source_id"]]["style"]["bss_boundary"] == "incoming_source"


def test_sigma_raw_d1_vector_target_keeps_exact_sum():
    result = build_bss_completed_chart("sigma", 1, filtration_max=4, h0_max=1)
    scalar = completed_module("sigma", 1, "1", 0)
    claim = next(c for c in result["chart"]["propositions"] if c["id"] == scalar.id+"_d1_claim")
    con = claim["conclusion"]
    assert len(con["target_coordinates"]) == 2
    assert con["bss_j_coefficient_tex"] == r"\Sigma"
    nodes = {n["id"]: n for n in result["chart"]["classes"]}
    assert nodes[con["target_id"]]["style"]["bss_combination"]
    assert "bss_j_module" not in nodes[con["target_id"]]["style"]
    assert nodes[con["target_id"]]["style"]["bss_period_generator"] == "D"
    assert nodes[con["target_id"]]["style"]["bss_period_D_exponent"] == 1


@pytest.mark.parametrize("basis,residue", [("x", 1), ("y", 0)])
def test_sigma_narrow_row_keeps_incoming_raw_sum_sources(basis, residue):
    result = build_bss_completed_chart("sigma", 1, filtration_min=2, filtration_max=2, h0_max=1)
    source = completed_module("sigma", 1, basis, residue)
    claim = next(c for c in result["chart"]["propositions"] if c["id"] == source.id+"_d1_claim")
    con = claim["conclusion"]
    nodes = {node["id"]: node for node in result["chart"]["classes"]}
    assert nodes[source.id]["style"]["bss_boundary"] == "incoming_source"
    assert con["target_in_window"]
    assert len(con["target_coordinates"]) == 2
    raw_source = sigma._xor(raw for term in source.lift() for raw in sigma.to_integer_basis(term))
    raw_target = sigma._xor(raw for data in con["target_terms"]
        for raw in sigma.to_integer_basis(sigma.SigmaMonomial(**data)))
    assert sigma.raw_twisted_d1(raw_source) == raw_target


@pytest.mark.parametrize("sector", ["integer", "sigma"])
@pytest.mark.parametrize("page", [1, 2, 3])
@pytest.mark.parametrize("h0_max", [0, 1, 3])
def test_all_narrow_rows_include_exactly_incident_differential_columns(sector, page, h0_max):
    engine = integer if sector == "integer" else sigma
    columns = []
    for source in iter_modules(sector, page, 0, 9, h0_max):
        if sector == "sigma" and page == 1:
            # Independent raw twist, not the adapted one-column lookup.
            raw = sigma._xor(item for term in source.lift() for item in sigma.to_integer_basis(term))
            target = sigma.from_integer_basis(sigma.raw_twisted_d1(raw))
        else:
            target = sigma._xor(result for term in source.lift()
                if (result := engine.differential(term, page)) is not None)
        if target:
            columns.append((source.id, source.tridegree, target[0].tridegree))
    for row in range(9):
        expected = {identifier for identifier, source_grade, target_grade in columns
                    if source_grade[1] == row or (target_grade[1] == row and target_grade[2] <= h0_max)}
        result = build_bss_completed_chart(sector, page, filtration_min=row, filtration_max=row, h0_max=h0_max)
        actual = {arrow["source_id"] for arrow in result["chart"]["differentials"]}
        assert actual == expected, (sector, page, h0_max, row)


@pytest.mark.parametrize("sector", ["integer", "sigma"])
def test_projection_changes_no_module_or_map_identity(sector):
    a = build_bss_completed_chart(sector, 1, filtration_max=4, projection="cohomology")
    b = build_bss_completed_chart(sector, 1, filtration_max=4, projection="bockstein")
    assert {n["id"] for n in a["chart"]["classes"]} == {n["id"] for n in b["chart"]["classes"]}
    assert {c["id"] for c in a["chart"]["propositions"]} == {c["id"] for c in b["chart"]["propositions"]}
    assert all(n["grade"]["filtration"] == n["style"]["bockstein_filtration"] for n in b["chart"]["classes"])


@pytest.mark.parametrize("kwargs", [{"page": 0}, {"page": 5}, {"h0_max": -1},
    {"filtration_min": 3, "filtration_max": 2}, {"projection": "invalid"},
    {"include_records": 1}, {"page": True}, {"limit": 1}])
def test_validation(kwargs):
    with pytest.raises(ValueError):
        build_bss_completed_chart("integer", **kwargs)


def test_completion_normalization_distinguishes_classical_invariant():
    assert J_COMPLETION["expression_tex"] == r"j=v_1^4D^{-1}"
    assert "j^3" in J_COMPLETION["normalization"]
