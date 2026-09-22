"""Finite, source-checked Leibniz descendants of DKLLW24 Tables 8 and 9.

The tables list generating differentials, not every arrow in a fundamental
domain.  These additional rows are consequences of the equations immediately
before the tables and of the relations in Tables 3/6.  In particular a dead
factor is *not* a reason to delete its products: the Leibniz target must be
reduced in the current page first.

Only nonzero descendants with a checked reduction are admitted below.  The
``j_component`` fields describe submodules, not additional isolated points.
``tail`` means positive powers of j relative to the named E2 motif.
"""
from __future__ import annotations

from dataclasses import dataclass

from .published_differentials import PublishedArrow


@dataclass(frozen=True)
class DerivedPublishedArrow:
    key: str
    arrow: PublishedArrow
    origin_table: int
    origin_row: int
    derivation: str
    period_stem: int
    source_pattern: str
    target_pattern: str
    source_j_component: str = "constant"
    target_j_component: str = "constant"
    source_j_order: int = 0
    target_j_order: int = 0
    source_two_valuation: int = 0
    target_two_valuation: int = 0
    target_reduction: str = ""


def _derived(
    key: str,
    workspace: str,
    source_label: str,
    source: tuple[int, int],
    target_label: str,
    page: int,
    *,
    table: int,
    row: int,
    derivation: str,
    period: int,
    source_pattern: str,
    target_pattern: str,
    source_component: str = "constant",
    target_component: str = "constant",
    source_j: int = 0,
    target_j: int = 0,
    source_two: int = 0,
    target_two: int = 0,
    reduction: str = "",
) -> DerivedPublishedArrow:
    return DerivedPublishedArrow(
        key=key,
        arrow=PublishedArrow(
            workspace_id=workspace,
            source_label=source_label,
            source_stem=source[0],
            source_filtration=source[1],
            target_label=target_label,
            target_stem=source[0] - 1,
            target_filtration=source[1] + page,
            page=page,
            source_ref=f"DKLLW24 Table {table}, row {row}; {derivation}",
        ),
        origin_table=table,
        origin_row=row,
        derivation=derivation,
        period_stem=period,
        source_pattern=source_pattern,
        target_pattern=target_pattern,
        source_j_component=source_component,
        target_j_component=target_component,
        source_j_order=source_j,
        target_j_order=target_j,
        source_two_valuation=source_two,
        target_two_valuation=target_two,
        target_reduction=reduction,
    )


def derived_published_arrows() -> tuple[DerivedPublishedArrow, ...]:
    """Return the checked finite descendants modulo their stated patterns."""
    rows: list[DerivedPublishedArrow] = []

    # main.tex 1373--1389: the corollary and its displayed complete d3 family.
    # h1^4 = v1^4 k = j D^-2 g, so these targets are tails, not entire cells.
    for power, source_pattern, target_pattern in (
        (1, "I51", "I00"),
        (2, "I62V", "I11"),
        (3, "I73V", "I22H"),
    ):
        h_source = "h_1" if power == 1 else f"h_1^{power}"
        h_remainder = "" if power == 1 else ("h_1" if power == 2 else "h_1^2")
        rows.append(_derived(
            f"integer_d3_h1_{power}", "ws_integer",
            rf"v_1^2{h_source}", (4 + power, power),
            rf"h_1^{power + 3}", 3,
            table=8, row=1,
            derivation="Corollary cor:d3 and displayed d3 family, main.tex 1373-1389",
            period=8, source_pattern=source_pattern, target_pattern=target_pattern,
            source_component="full", target_component="tail", target_j=1,
            reduction=rf"jD^{{-2}}g{h_remainder}",
        ))

    # The corresponding explicit sigma family is main.tex 1954--1961.
    # S00 itself already starts with v1^4 D^-1 u, unlike integer I00.
    for power, source_pattern, target_pattern in (
        (1, "S51", "S00"),
        (2, "S62V", "S11"),
        (3, "S73V", "S22H"),
    ):
        h_source = "h_1" if power == 1 else f"h_1^{power}"
        rows.append(_derived(
            f"sigma_d3_h1_{power}", "ws_sigma_i",
            rf"v_1^2{h_source}u_{{\sigma_i}}", (4 + power, power),
            rf"h_1^{power + 3}u_{{\sigma_i}}", 3,
            table=9, row=2,
            derivation="Displayed sigma d3 family, main.tex 1954-1961",
            period=8, source_pattern=source_pattern, target_pattern=target_pattern,
            source_component="full",
            target_component="full" if power == 1 else "tail",
            target_j=0 if power == 1 else 1,
            reduction=(r"kv_1^4u_{\sigma_i}" if power == 1 else
                       rf"jD^{{-2}}g h_1^{power - 1}u_{{\sigma_i}}"),
        ))

    # h2 has order four. Thus d5(D^2) is NONZERO; d5(D^4)=0.
    # The d7 proof explicitly uses this differential (main.tex 1510).
    rows.append(_derived(
        "integer_d5_D2", "ws_integer", "D^2", (16, 0),
        r"2D^{-1}gh_2", 5,
        table=8, row=2,
        derivation="Leibniz rule d(D^2)=2D d(D); prop:d7one proof, main.tex 1510",
        period=32, source_pattern="I00", target_pattern="I31", target_two=1,
    ))

    # h2, h2^2, d and dh2 are d5 cycles. The nonzero products of the
    # Table-8 d5 target reduce by h2^2=Dy^2 and dh2^2=4g.
    for key, source_label, source, target_label, source_pattern, target_pattern, target_two, reduction in (
        ("h2", r"Dh_2", (11, 1), r"D^{-2}gh_2^2", "I31", "I62Y", 0, r"D^{-1}gy^2"),
        ("h2sq", r"Dh_2^2", (14, 2), r"D^{-2}gh_2^3", "I62Y", "I13", 0, r"D^{-1}gxh_1^2"),
        ("d", "Dd", (22, 2), r"D^{-2}gdh_2", "I62X", "I13X", 0, r"gx^2h_2"),
        ("dh2", r"Ddh_2", (25, 3), r"4D^{-2}g^2", "I13X", "I00", 2, r"4D^{-2}g^2"),
    ):
        rows.append(_derived(
            f"integer_d5_{key}", "ws_integer", source_label, source, target_label, 5,
            table=8, row=2,
            derivation="Leibniz rule; Table 3 and hidden extension dh2^2=4g, main.tex 1457-1476",
            period=16, source_pattern=source_pattern, target_pattern=target_pattern,
            target_two=target_two, reduction=reduction,
        ))

    # The proof of prop:d7one applies to the odd D^3 residue too:
    # d5(D^3)=3g h2 and the same hidden 2 extension force the target g h1^3
    # to be hit from 4D^3. This residue is not a D^4 translate of 4D.
    # On the order-two target the coefficient 3 is the coefficient 1.
    rows.append(_derived(
        "integer_d7_4D3", "ws_integer", r"4D^3", (24, 0), r"gh_1^3", 7,
        table=8, row=3,
        derivation=(
            "The prop:d7one hidden-2-extension argument applied to "
            "d5(D^3)=3g h2; main.tex 1503-1510"
        ),
        period=32, source_pattern="I00", target_pattern="I33", source_two=2,
    ))

    # Unlike the D^2 h1^2 product below, these h1 products have nonzero
    # targets on E9. Their xh1^2 residues are even, whereas d5(Dh2^2)
    # removed the odd residues. These are genuine additional d9 arrows.
    for exponent, row, source_stem, target_label, reduction in (
        (1, 6, 10, r"D^{-5}g^2h_2^3", r"D^{-4}g^2xh_1^2"),
        (5, 7, 42, r"D^{-1}g^2h_2^3", r"g^2xh_1^2"),
    ):
        d_label = "D" if exponent == 1 else f"D^{exponent}"
        rows.append(_derived(
            f"integer_d9_D{exponent}h1sq", "ws_integer",
            rf"{d_label}h_1^2", (source_stem, 2), target_label, 9,
            table=8, row=row,
            derivation="Multiply Table 8 row by permanent h1; ch1=h2^3 (Table 3)",
            period=64, source_pattern="I22H", target_pattern="I13",
            reduction=reduction,
        ))

    # h1 is permanent. Its product with rows 14/15 is not one of rows16/17:
    # the latter have odd D exponents, so omitting these misses two families.
    for exponent, row, source_stem, target_label in (
        (2, 14, 31, r"D^{-4}g^3h_1^2"),
        (6, 15, 63, r"g^3h_1^2"),
    ):
        rows.append(_derived(
            f"integer_d11_D{exponent}dh1", "ws_integer",
            rf"D^{exponent}dh_1", (source_stem, 3), target_label, 11,
            table=8, row=row,
            derivation="Explicit corollary after prop:d11, main.tex 1663-1670; multiply by permanent h1",
            period=64, source_pattern="I73", target_pattern="I22H",
        ))

    # Multiply the first sigma d5 by h2.  With B=(x+y)u one has
    # B*h2=(yh2+xh1v1)u and B*h2^2=D*x^3u: x*h2^2=0 while
    # y*h2^2=D*x^3 in the mod-2 presentation (main.tex 940--950).
    rows.append(_derived(
        "sigma_d5_Bh2D", "ws_sigma_i",
        r"(yh_2+xh_1v_1)Du_{\sigma_i}", (10, 2),
        r"kx^3D^2u_{\sigma_i}", 5,
        table=9, row=3,
        derivation="Multiply Table 9 row 3 by permanent h2; B*h2^2=D*x^3u, main.tex 940-950",
        period=16, source_pattern="S22Y", target_pattern="S53",
    ))

    # A*h1=x^2*h1*u because y^2*h1=0 (Tables 3 and 6).
    # These target residues differ from those of Table9 rows7/8, and
    # therefore do not follow merely by drawing those rows periodically.
    for exponent, row, source_stem in ((2, 9, 16), (6, 10, 48)):
        rows.append(_derived(
            f"sigma_d9_Bh1D{exponent}", "ws_sigma_i",
            rf"(x+y)h_1D^{exponent}u_{{\sigma_i}}", (source_stem, 2),
            rf"k^2x^2h_1D^{exponent + 1}u_{{\sigma_i}}", 9,
            table=9, row=row,
            derivation="Multiply Table 9 row by permanent h1; (x^2+y^2)u*h1=x^2h1u, Tables 3/6",
            period=64, source_pattern="S02", target_pattern="S73",
        ))
    return tuple(rows)


# Checked vanishing reductions are recorded as witnesses rather than arrows.
# They protect against the invalid rule 'a dead factor has only dead products'.
SURVIVAL_WITNESSES = (
    {
        "class": r"D^2h_1^2",
        "page": 9,
        "candidate_target": r"D^{-4}g^2ch_1",
        "target_reduction": r"D^{-4}g^2h_2^3",
        "earlier_boundary_source": r"D^{-1}gh_2^2",
        "earlier_boundary_page": 5,
        "explanation": "The Leibniz target is already zero on E9; Table 8 gives this source d23, not d9.",
    },
    {
        "class": r"D^5h_1^3",
        "page": 9,
        "candidate_target": r"D^{-1}g^2ch_1^2",
        "target_reduction": "0",
        "earlier_boundary_source": "",
        "earlier_boundary_page": 0,
        "explanation": "Table 3 has xh1*h1^2=0, hence c*h1^2=0; the Table-8 d23 source survives d9.",
    },
)
