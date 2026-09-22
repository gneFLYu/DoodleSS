"""Independent degree and page-quotient checks for published descendants."""
import re

from backend.domain.published_differentials import PUBLISHED_ARROWS
from backend.domain.published_products import (
    SURVIVAL_WITNESSES,
    derived_published_arrows,
)


def monomial_grade(label):
    """Source-table degrees, deliberately independent of chart motif lookup."""
    degrees = {
        "D": (8, 0), "g": (20, 4), "k": (-4, 4),
        "v_1": (2, 0), "h_1": (1, 1), "h_2": (3, 1),
        "x": (-1, 1), "y": (-1, 1), "c": (8, 2), "d": (14, 2),
    }
    value = label.replace(r"u_{\sigma_i}", "")
    # The sigma Bh2 representative is a named homogeneous sum, not a
    # comma-list of independent generators. Check both summands independently.
    if "(" in value:
        match = re.fullmatch(r"\(([^()]+)\)(.*)", value)
        assert match is not None
        summands, suffix = match.groups()
        results = {monomial_grade(term + suffix) for term in summands.split("+")}
        assert len(results) == 1
        return results.pop()
    value = re.sub(r"^\d+", "", value)
    tokens = list(re.finditer(r"(v_1|h_1|h_2|D|g|k|x|y|c|d)(?:\^(?:\{(-?\d+)\}|(-?\d+)))?", value))
    assert "".join(token.group(0) for token in tokens) == value
    stem = filtration = 0
    for token in tokens:
        power = int(token.group(2) or token.group(3) or 1)
        ds, df = degrees[token.group(1)]
        stem += power * ds
        filtration += power * df
    return stem, filtration


def test_every_derived_formula_has_its_declared_bidegree_and_valid_table_origin():
    for descendant in derived_published_arrows():
        arrow = descendant.arrow
        assert monomial_grade(arrow.source_label) == (arrow.source_stem, arrow.source_filtration)
        assert monomial_grade(arrow.target_label) == (arrow.target_stem, arrow.target_filtration)
        assert (arrow.target_stem - arrow.source_stem, arrow.target_filtration - arrow.source_filtration) == (-1, arrow.page)
        source_rows = [item for item in PUBLISHED_ARROWS if item.workspace_id == arrow.workspace_id]
        origin = source_rows[descendant.origin_row - 1]
        assert origin.page == arrow.page


def test_d5_derivative_of_d_squared_retains_the_order_four_target():
    rows = {item.key: item for item in derived_published_arrows()}
    row = rows["integer_d5_D2"]
    # h2 has order 4: the derivative coefficient 2 is nonzero, while 4 is zero.
    assert 2 % 4 != 0 and 4 % 4 == 0
    assert row.arrow.target_label == r"2D^{-1}gh_2"
    assert row.target_two_valuation == 1
    assert row.period_stem == 32
    assert row.source_j_component == "constant"


def test_d3_h1_descendants_hit_tails_not_constants_that_support_d23():
    rows = derived_published_arrows()
    integer = [item for item in rows if item.arrow.workspace_id == "ws_integer" and item.arrow.page == 3]
    assert {item.arrow.source_filtration for item in integer} == {1, 2, 3}
    assert all(item.target_j_component == "tail" and item.target_j_order == 1 for item in integer)
    assert all(item.source_j_component == "full" for item in integer)


def test_d23_source_product_has_a_d5_boundary_as_its_candidate_d9_target():
    rows = {item.key: item for item in derived_published_arrows()}
    witness = next(item for item in SURVIVAL_WITNESSES if item["class"] == r"D^2h_1^2")
    earlier = rows["integer_d5_h2sq"]
    # Multiply Dh2^2 -> D^-2 g h2^3 by g D^-2. This is a legal forward
    # g and inverse D^2 pattern translate of this particular differential.
    ds, df = monomial_grade(r"D^{-2}g")
    assert (earlier.arrow.source_stem + ds, earlier.arrow.source_filtration + df) == monomial_grade(witness["earlier_boundary_source"])
    assert (earlier.arrow.target_stem + ds, earlier.arrow.target_filtration + df) == monomial_grade(witness["target_reduction"])
    assert witness["earlier_boundary_page"] < witness["page"]
    assert any(item.source_label == witness["class"] and item.page == 23 for item in PUBLISHED_ARROWS)
    assert not any(item.arrow.source_label == witness["class"] and item.arrow.page == 9 for item in rows.values())


def test_d11_h1_products_are_distinct_from_the_odd_d_exponent_table_rows():
    descendants = [item.arrow for item in derived_published_arrows() if item.arrow.page == 11]
    assert {item.source_stem for item in descendants} == {31, 63}
    direct = {item.source_stem for item in PUBLISHED_ARROWS if item.workspace_id == "ws_integer" and item.page == 11}
    assert not direct.intersection(item.source_stem for item in descendants)


def test_odd_d9_h1_products_are_not_confused_with_the_d_squared_zero_product():
    products = [item for item in derived_published_arrows() if item.arrow.page == 9 and item.arrow.workspace_id == "ws_integer"]
    assert {item.arrow.source_label for item in products} == {r"Dh_1^2", r"D^5h_1^2"}
    # After reducing h2^3 = D*xh1^2, target D residues are even. The
    # d5(Dh2^2) family removes odd xh1^2 residues only, so these remain nonzero.
    for item in products:
        stem_after_removing_g = item.arrow.target_stem - 2 * 20
        d_residue = (stem_after_removing_g - 1) // 8
        assert d_residue % 2 == 0


def test_d7_four_d_cubed_covers_a_different_residue_from_four_d():
    product = next(item for item in derived_published_arrows() if item.key == "integer_d7_4D3")
    row = next(item for item in PUBLISHED_ARROWS if item.source_label == "4D")
    assert (product.arrow.source_stem - row.source_stem) % 32 == 16
    assert product.source_two_valuation == 2
    assert product.arrow.target_stem == 23
    assert product.target_j_component == "constant"


def test_sigma_products_cover_the_other_nonzero_finite_residues():
    rows = {item.key: item for item in derived_published_arrows()}
    h2_product = rows["sigma_d5_Bh2D"]
    assert h2_product.source_pattern == "S22Y"
    assert h2_product.target_pattern == "S53"
    assert h2_product.period_stem == 16
    for exponent in (2, 6):
        row = rows[f"sigma_d9_Bh1D{exponent}"]
        assert row.source_pattern == "S02"
        assert row.target_pattern == "S73"
        # Tables9 rows7/8 have source D^1/D^5, not these D^2/D^6 residues.
        direct_sources = {
            item.source_stem for item in PUBLISHED_ARROWS
            if item.workspace_id == "ws_sigma_i" and item.page == 9
            and item.source_label.startswith("(x+y)h_1D")
        }
        assert row.arrow.source_stem not in direct_sources
