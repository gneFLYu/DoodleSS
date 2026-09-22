"""Materialize every active nonzero differential declared in formal_notes.

The source/admission status comes from RECORD.md and the machine ledger in
``backend/data/review``.  Review and source-proved arrows are intentionally
drawn (amber/dashed in the browser) but are never promoted to canonical page
transitions.  The commented ``Seems to be wrong`` block is not represented.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re

from .models import (
    CellBasisVector, CellVectorSpace, ClassNode, Differential, DifferentialMap,
    Grade, NamedVector, Project, Proposition, Workspace,
)
from .periodic_fate_ledger import load_periodic_fate_ledger
from .published_differentials import (
    _normalise_label, _published_e2_pattern, endpoint_component_style,
)


@dataclass(frozen=True)
class FormalArrow:
    fact_id: str
    workspace_id: str
    source_label: str
    source_stem: int
    source_filtration: int
    target_label: str
    target_stem: int
    target_filtration: int
    page: int
    status: str
    source_ref: str
    period_stem: int = 0
    differential_id: str = ""


def _a(
    fact_id: str,
    workspace_id: str,
    source_label: str,
    source: tuple[int, int],
    target_label: str,
    target: tuple[int, int],
    page: int,
    status: str,
    source_ref: str,
    period_stem: int = 0,
    differential_id: str = "",
) -> FormalArrow:
    return FormalArrow(
        fact_id, workspace_id, source_label, *source, target_label, *target,
        page, status, source_ref, period_stem, differential_id,
    )


FORMAL_ARROWS: tuple[FormalArrow, ...] = (
    # (* - 2 sigma_i)
    _a("FN-2I-001", "ws_2sigma_i", r"u_{2\sigma_i}", (0, 0), r"x^2h_1u_{2\sigma_i}", (-1, 3), 3, "verified-pattern", "formal_notes.tex:283-320", 8, "diff_two_d3_u"),
    _a("FN-2I-002", "ws_2sigma_i", r"v_1^6u_{2\sigma_i}", (12, 0), r"h_1^3Du_{2\sigma_i}", (11, 3), 3, "source-proved", "formal_notes.tex:308-320", 8),
    _a("FN-2I-002", "ws_2sigma_i", r"h_1v_1^6u_{2\sigma_i}", (13, 1), r"h_1^4Du_{2\sigma_i}", (12, 4), 3, "source-proved", "formal_notes.tex:308-320", 8),
    _a("FN-2I-003", "ws_2sigma_i", r"\{x^2+y^2\}Du_{2\sigma_i}", (6, 2), r"k\{x^2+y^2\}h_2Du_{2\sigma_i}", (5, 7), 5, "admitted", "formal_notes.tex:334-353", 16),
    _a("FN-2I-004", "ws_2sigma_i", r"h_2Du_{2\sigma_i}", (11, 1), r"kh_2^2Du_{2\sigma_i}", (10, 6), 5, "verified-pattern", "formal_notes.tex:357-379", 16, "diff_two_d5_h2D"),
    _a("FN-2I-005", "ws_2sigma_i", r"2Du_{2\sigma_i}", (8, 0), r"2kh_2Du_{2\sigma_i}", (7, 5), 5, "verified", "formal_notes.tex:382-399; transfer from ker(sigma_i)=C4<i>", 16, "diff_two_d5_2D"),
    _a("FN-2I-006", "ws_2sigma_i", r"xh_1u_{2\sigma_i}", (0, 2), r"kh_1^3u_{2\sigma_i}", (-1, 7), 5, "verified", "formal_notes.tex:401-420; repaired E2 coefficient-sequence/transfer proof", 8, "diff_two_d5_xh1"),
    _a("FN-2I-009", "ws_2sigma_i", r"\{x^2+y^2\}D^2u_{2\sigma_i}", (14, 2), r"k^3h_1D^3u_{2\sigma_i}", (13, 13), 11, "verified", "formal_notes.tex:450-470; BBHS20 Propositions 5.25 and 5.28", 32, "diff_two_d11"),
    _a("FN-2I-010", "ws_2sigma_i", r"2kh_2D^2u_{2\sigma_i}", (15, 5), r"k^3h_1^2D^3u_{2\sigma_i}", (14, 14), 9, "verified", "formal_notes.tex:472-482; FN-2I-009 and finite incoming-source exclusion", 32),
    _a("FN-2I-010", "ws_2sigma_i", r"2h_2D^3u_{2\sigma_i}", (27, 1), r"k^2h_1^2D^4u_{2\sigma_i}", (26, 10), 9, "verified", "formal_notes.tex:472-482; Tate translate of the D6 block", 32),
    _a("FN-2I-011", "ws_2sigma_i", r"h_1^2D^3u_{2\sigma_i}", (26, 2), r"k^2D^3h_2^3u_{2\sigma_i}", (25, 11), 9, "verified", "formal_notes.tex:487-494; Tate H2/H6 cycles and Table 8", 32, "diff_two_d9"),
    _a("FN-2I-012", "ws_2sigma_i", r"h_1D^3u_{2\sigma_i}", (25, 1), r"2k^2D^4u_{2\sigma_i}", (24, 8), 7, "verified", "formal_notes.tex:496-499; FN006/FN011 and the exact E7 target quotient", 32),
    _a("FN-2I-013", "ws_2sigma_i", r"h_1D^4u_{2\sigma_i}", (33, 1), r"4k^2D^5u_{2\sigma_i}", (32, 8), 7, "verified", "formal_notes.tex:501-506; DKLLW24 main:1694-1702 and the exact E7 target quotient", 32),
    _a("FN-2I-014", "ws_2sigma_i", r"h_1Du_{2\sigma_i}", (9, 1), r"2k^2D^2u_{2\sigma_i}", (8, 8), 7, "verified", "formal_notes.tex:508-516; repaired C4<i> transfer and E2 Euler kernel", 32),
    _a("FN-2I-016", "ws_2sigma_i", r"h_2D^2u_{2\sigma_i}", (19, 1), r"h_1^2k^2D^3u_{2\sigma_i}", (18, 10), 9, "verified", "formal_notes.tex:520-526; FN009 zero-product obstruction before E11", 32),
    _a("FN-2I-017", "ws_2sigma_i", r"2h_2Du_{2\sigma_i}", (11, 1), r"k^2h_1^2D^2u_{2\sigma_i}", (10, 10), 9, "verified", "formal_notes.tex:529-536; repaired Table 8 d23 product obstruction before E23", 32),
    _a("FN-2I-018", "ws_2sigma_i", r"\{x^2+y^2\}D^4u_{2\sigma_i}", (30, 2), r"h_2^3k^3D^4u_{2\sigma_i}", (29, 15), 13, "verified", "formal_notes.tex:540-555; Table 9 Euler image and actual target quotient", differential_id="diff_two_d13"),
    _a("FN-2I-019", "ws_2sigma_i", r"h_2kD^7u_{2\sigma_i}", (55, 5), r"\{x^2+y^2\}k^6D^{10}u_{2\sigma_i}", (54, 26), 21, "verified", "formal_notes.tex:558-563; table_Q8.tex:407; repaired Table 8 d23 product proof"),
    _a("FN-2I-020", "ws_2sigma_i", r"h_2^3D^{-1}u_{2\sigma_i}", (1, 3), r"4k^6D^3u_{2\sigma_i}", (0, 24), 21, "verified", "formal_notes.tex:565-570; table_Q8.tex:408; finite rank-one E21 quotient"),
    _a("FN-2I-021", "ws_2sigma_i", r"4k^2D^3u_{2\sigma_i}", (16, 8), r"h_2k^7D^5u_{2\sigma_i}", (15, 29), 21, "verified", "formal_notes.tex:572-577; table_Q8.tex:409; repaired Table 8 d23 product proof"),

    # (* - 3 sigma_i)
    _a("FN-3I-001", "ws_3sigma_i", r"v_1^2u_{3\sigma_i}", (4, 0), r"h_1^3u_{3\sigma_i}", (3, 3), 3, "verified", "formal_notes.tex:678-700", 8, "diff_three_d3"),
    _a("FN-3I-002", "ws_3sigma_i", r"k^2\{x^2+y^2\}D^3u_{3\sigma_i}", (14, 10), r"k^3\{x+y\}h_1^2D^3u_{3\sigma_i}", (13, 15), 5, "verified", "formal_notes.tex:707-718; FN010 Euler image and finite incoming-source exclusion", 16, "diff_three_d5_main"),
    _a("FN-3I-003", "ws_3sigma_i", r"\{yh_2+xh_1v_1\}Du_{3\sigma_i}", (10, 2), r"kx^3D^2u_{3\sigma_i}", (9, 7), 5, "verified", "formal_notes.tex:730-742", 16, "diff_three_d5_yh2"),
    _a("FN-3I-004", "ws_3sigma_i", r"x^3D^2u_{3\sigma_i}", (13, 3), r"2v_1^2k^2D^2u_{3\sigma_i}", (12, 8), 5, "verified", "formal_notes.tex:744-746", 16, "diff_three_d5_x3"),
    _a("FN-3I-005", "ws_3sigma_i", r"\{x+y\}D^2u_{3\sigma_i}", (15, 1), r"\{h_1+xv_1\}h_1kD^2u_{3\sigma_i}", (14, 6), 5, "verified", "formal_notes.tex:748-753", 16, "diff_three_d5_xyD2"),
    _a("FN-3I-006", "ws_3sigma_i", r"\{x+y\}Du_{3\sigma_i}", (7, 1), r"k\{yh_2+h_1^2\}Du_{3\sigma_i}", (6, 6), 5, "verified", "formal_notes.tex:755-762", 16, "diff_three_d5_sum"),
    _a("FN-3I-007", "ws_3sigma_i", r"\{x+y\}h_1^2D^3u_{3\sigma_i}", (25, 3), r"2v_1^2k^3D^4u_{3\sigma_i}", (24, 12), 9, "verified", "formal_notes.tex:764-775; verified FN-2I-011 Euler image and finite target survival", 64, "diff_three_d9_25"),
    _a("FN-3I-008", "ws_3sigma_i", r"\{x+y\}h_1D^3u_{3\sigma_i}", (24, 2), r"x^2h_1k^2D^4u_{3\sigma_i}", (23, 11), 9, "verified", "formal_notes.tex:777-780; FN007 and actual hidden h1 multiplication", 64, "diff_three_d9_25b"),
    _a("FN-3I-009", "ws_3sigma_i", r"\{x^2+y^2\}D^4u_{3\sigma_i}", (30, 2), r"\{h_1+xv_1\}k^3D^5u_{3\sigma_i}", (29, 13), 11, "verified", "formal_notes.tex:782-796; BBHS20 Proposition 5.28 and finite E11 quotient", 32, "diff_three_d11_30"),
    _a("FN-3I-009", "ws_3sigma_i", r"x^2h_1D^4u_{3\sigma_i}", (31, 3), r"\{h_1+xv_1\}h_1k^3D^5u_{3\sigma_i}", (30, 14), 11, "verified", "formal_notes.tex:782-796; BBHS20 Proposition 5.28 and finite E11 quotient", 32),
    _a("FN-3I-010", "ws_3sigma_i", r"\{x^2+y^2\}D^2u_{3\sigma_i}", (14, 2), r"\{h_1+xv_1\}k^5D^4u_{3\sigma_i}", (13, 21), 19, "source-proved", "formal_notes.tex:849-860", 32),
    _a("FN-3I-010", "ws_3sigma_i", r"2v_1^2Du_{3\sigma_i}", (12, 0), r"x^2h_1k^5D^4u_{3\sigma_i}", (11, 23), 23, "source-proved", "formal_notes.tex:799-845", 32),

    # (* - sigma_i - 2 sigma_j)
    _a("FN-MIX-001", "ws_sigma_i_2sigma_j", r"v_1^2u_{\sigma_i+2\sigma_j}", (4, 0), r"h_1^3u_{\sigma_i+2\sigma_j}", (3, 3), 3, "verified", "formal_notes.tex:881-901; DKLLW24 Corollary 4.15 (D is a 3-cycle)", 8, "diff_mixed_d3"),
    # The endpoint is the unscaled Witt two-layer. Its nontrivial F4 unit
    # is recorded separately below, so the actual map (not only its label)
    # is zeta times this endpoint and psi conjugates it exactly once.
    _a("FN-MIX-001", "ws_sigma_i_2sigma_j", r"\{h_1+xv_1\}u_{\sigma_i+2\sigma_j}", (1, 1), r"2v_1^2ku_{\sigma_i+2\sigma_j}", (0, 4), 3, "verified", "formal_notes.tex:881-901; DKLLW24 Corollary 4.15 (D is a 3-cycle)", 8),
    _a("FN-MIX-002", "ws_sigma_i_2sigma_j", r"\{x^2+y^2\}k^2D^3u_{\sigma_i+2\sigma_j}", (14, 10), r"\{x+y\}h_1^2k^3D^3u_{\sigma_i+2\sigma_j}", (13, 15), 5, "review", "formal_notes.tex:903-916", 16),
    _a("FN-MIX-003", "ws_sigma_i_2sigma_j", r"\{x^2+y^2\}Du_{\sigma_i+2\sigma_j}", (6, 2), r"\{x+y\}h_1^2kDu_{\sigma_i+2\sigma_j}", (5, 7), 5, "review", "formal_notes.tex:918-932", 16),
    _a("FN-MIX-004", "ws_sigma_i_2sigma_j", r"\{yh_2+xh_1v_1\}Du_{\sigma_i+2\sigma_j}", (10, 2), r"x^3kD^2u_{\sigma_i+2\sigma_j}", (9, 7), 5, "verified", "formal_notes.tex:934-951", 16),
    _a("FN-MIX-005", "ws_sigma_i_2sigma_j", r"\{x+y\}Du_{\sigma_i+2\sigma_j}", (7, 1), r"\{yh_2+h_1^2\}kDu_{\sigma_i+2\sigma_j}", (6, 6), 5, "review", "formal_notes.tex:953-970", 16),
    _a("FN-MIX-005", "ws_sigma_i_2sigma_j", r"\{x+y\}D^2u_{\sigma_i+2\sigma_j}", (15, 1), r"\{h_1^2+xh_1v_1\}kD^2u_{\sigma_i+2\sigma_j}", (14, 6), 5, "review", "formal_notes.tex:953-970", 16),
    _a("FN-MIX-006", "ws_sigma_i_2sigma_j", r"x^3D^2u_{\sigma_i+2\sigma_j}", (13, 3), r"\{x+y\}h_1k^3D^3u_{\sigma_i+2\sigma_j}", (12, 14), 11, "verified", "formal_notes.tex:972-991; table_Q8.tex:527 (coefficient corrected by omega/Euler)", 64),
)


DERIVED_FORMAL_ARROWS: tuple[FormalArrow, ...] = (
    # The odd and even A blocks are linked by Leibniz, not by an
    # independently chosen unit. The even coefficient c+1 can be zero.
    _a("DER-MIX-D5-A-EVEN", "ws_sigma_i_2sigma_j", r"\{x^2+y^2\}D^2u_{\sigma_i+2\sigma_j}", (14, 2),
       r"\{x+y\}h_1^2kD^2u_{\sigma_i+2\sigma_j}", (13, 7), 5, "review",
       "formal_notes.tex:903-932; DKLLW24 Tables 6 and 8; Leibniz with d5(D)=kh2D",
       16, "formal_diff_mixed_d5_a_D2_leibniz_derived"),
    _a("FN-MIX-006", "ws_sigma_i_2sigma_j", r"x^3D^6u_{\sigma_i+2\sigma_j}", (45, 3),
       r"\{x+y\}h_1k^3D^7u_{\sigma_i+2\sigma_j}", (44, 14), 11, "verified",
       "formal_notes.tex:450-470,972-991; table_Q8.tex:527; independently transported D6 block with corrected coefficient",
       64, "formal_diff_mixed_d11_r_D6_sibling"),
    # Independently apply the integer d3 to the Thom module. Table 3 gives
    # x^2(v1^2 h1)=0, so the extra term a*d3(u) vanishes for these sources.
    # This does NOT use FN-2I-002's printed, missing-j target.
    _a("FN-2I-001", "ws_2sigma_i", r"v_1^6u_{2\sigma_i}", (12, 0),
       r"v_1^4h_1^3u_{2\sigma_i}", (11, 3), 3, "verified-pattern",
       "DKLLW24 Table 8 row 1, Proposition 4.10, Table 3; formal_notes.tex:283-305",
       8, "formal_diff_two_d3_v6_derived"),
    # h2 is permanent and h2^2 = y^2 D.  This is a consequence of FN-2I-004,
    # not a forty-first formula printed in formal_notes.
    _a("FN-2I-004", "ws_2sigma_i", r"y^2D^2u_{2\sigma_i}", (14, 2),
       r"kh_2^3Du_{2\sigma_i}", (13, 7), 5, "verified-pattern",
       "formal_notes.tex:280,357-379; h2 multiplication of FN-2I-004",
       16, "formal_diff_two_d5_y2_derived"),
    _a("FN-2I-003", "ws_2sigma_i", r"\{x^2+y^2\}h_2Du_{2\sigma_i}", (9, 3),
       r"4k^2D^2u_{2\sigma_i}", (8, 8), 5, "admitted",
       "formal_notes.tex:334-353; DKLLW24 Remark rmk:h2ext and Tables 2/3; h2 multiplication",
       16, "formal_diff_two_d5_h2_sum_derived"),
    _a("FN-2I-021", "ws_2sigma_i", r"4ku_{2\sigma_i}", (-4, 4),
       r"h_2k^6D^2u_{2\sigma_i}", (-5, 25), 21, "verified",
       "formal_notes.tex:572-577; DKLLW24 Lemma 2.6 and Tate method (main.tex:488-510)",
       64, "formal_diff_two_d21_tate_positive_derived"),
    _a("FN-2I-019", "ws_2sigma_i", r"h_2D^4u_{2\sigma_i}", (35, 1),
       r"\{x^2+y^2\}k^5D^7u_{2\sigma_i}", (34, 22), 21, "verified",
       "table_Q8.tex:407; formal_notes.tex:558-563; finite source audit and g detection",
       64, "formal_diff_two_d21_h2_low_derived"),
    _a("FN-2I-021", "ws_2sigma_i", r"4D^5u_{2\sigma_i}", (40, 0),
       r"h_2k^5D^7u_{2\sigma_i}", (39, 21), 21, "verified",
       "table_Q8.tex:409; formal_notes.tex:572-577; finite filtration-zero audit and g^2 detection",
       64, "formal_diff_two_d21_four_f0_derived"),
    # The printed low-filtration corollary is commented out. This separate
    # record is an independent Tate derivation of the active high-filtration
    # FN-3I-002 row, never a reclassification of the commented source text.
    _a("FN-3I-002", "ws_3sigma_i", r"\{x^2+y^2\}Du_{3\sigma_i}", (6, 2),
       r"\{x+y\}h_1^2kDu_{3\sigma_i}", (5, 7), 5, "verified",
       "formal_notes.tex:707-718; DKLLW24 Lemma 2.6 and Tate method (main.tex:488-510)",
       16, "formal_diff_three_d5_tate_positive_derived"),
    # This D5 block has a separate Table 8/Leibniz proof. It does not admit
    # the withdrawn D1 equation, nor its claimed 32-stem period.
    _a("DER-3I-LEIBNIZ-W5-D23", "ws_3sigma_i", r"2v_1^2D^5u_{3\sigma_i}", (44, 0),
       r"x^2h_1k^5D^8u_{3\sigma_i}", (43, 23), 23, "verified",
       "DKLLW24 Table 8 row 22; main.tex:1095-1111,1914-1915; independent finite D5-block audit",
       64, "formal_diff_three_d23_u_D5_forced"),
    _a("DER-3I-EULER-CD1-D11", "ws_3sigma_i", r"(h_1+xv_1)Du_{3\sigma_i}", (9, 1),
       r"2v_1^2k^3D^2u_{3\sigma_i}", (8, 12), 11, "verified",
       "DKLLW24 Table 9 d13; main.tex:1094-1111,2365-2369; Euler square and complete finite incoming audit",
       64, "formal_diff_three_d11_c_D1_euler_forced"),
    _a("DER-3I-EULER-AD2-D19", "ws_3sigma_i", r"(x^2+y^2)D^2u_{3\sigma_i}", (14, 2),
       r"(h_1+xv_1)k^5D^4u_{3\sigma_i}", (13, 21), 19, "verified",
       "BBHS20 Table 4 p3470; DKLLW24 Table 8, Corollary 2.22 and strong vanishing theorem; independent Euler-cofiber proof",
       64, "formal_diff_three_d19_a_D2_euler_forced"),
) + tuple(
    _a(fact_id, workspace_id,
       rf"v_1^2{'h_1' if power == 1 else f'h_1^{power}'}u_{{{thom}}}",
       (4 + power, power), rf"h_1^{power + 3}u_{{{thom}}}", (3 + power, 3 + power),
        3, "verified-pattern" if key == "two" else "verified",
       f"{source_ref}; h1^{power} multiplication; DKLLW24 Tables 3 and 6",
       8, f"formal_diff_{key}_d3_h1_{power}_derived")
    for workspace_id, fact_id, key, thom, source_ref in (
        ("ws_2sigma_i", "FN-2I-001", "two", r"2\sigma_i", "DKLLW24 Corollary 4.11; formal_notes.tex:283-305"),
        ("ws_3sigma_i", "FN-3I-001", "three", r"3\sigma_i", "formal_notes.tex:678-705"),
        ("ws_sigma_i_2sigma_j", "FN-MIX-001", "mixed", r"\sigma_i+2\sigma_j", "formal_notes.tex:881-901"),
    )
    for power in (1, 2, 3)
) + tuple(
    _a(f"DER-3I-D9-{column.upper()}", "ws_3sigma_i", source, grade,
       target, (grade[0] - 1, grade[1] + 9), 9, "verified", reference,
       64, f"formal_diff_three_d9_{column}_D{power}_derived")
    for power in (2, 6)
    for column, source, grade, target, reference in (
        ("p", rf"\{{yh_2+xh_1v_1\}}D^{power}u_{{3\sigma_i}}", (8 * power + 2, 2),
         rf"\{{x+y\}}h_1^2k^2D^{power + 1}u_{{3\sigma_i}}",
         "formal_notes.tex:520-526,730-741; multiplication by the permanent Euler class a_sigma_i"),
        ("q", rf"\{{h_1+xv_1\}}h_1D^{power}u_{{3\sigma_i}}", (8 * power + 2, 2),
         rf"\{{x+y\}}h_1^2k^2D^{power + 1}u_{{3\sigma_i}}",
         "formal_notes.tex:755-762; FN016 Euler image, FN002 even-A zero and finite target g-injection"),
        ("c", rf"\{{h_1+xv_1\}}D^{power}u_{{3\sigma_i}}", (8 * power + 1, 1),
         rf"\{{x+y\}}h_1k^2D^{power + 1}u_{{3\sigma_i}}",
         "formal_notes.tex:678-705; Table 6; empty/primitive-boundary targets and h1 lift of the verified Q differential"),
    )
) + tuple(
    _a("DER-3I-EULER-D9-B", "ws_3sigma_i",
       rf"\{{x+y\}}h_1D^{power}u_{{3\sigma_i}}", (8 * power, 2),
       rf"x^2h_1k^2D^{power + 1}u_{{3\sigma_i}}", (8 * power - 1, 11),
       9, "verified",
       "formal_notes.tex:764-780; DKLLW24 main.tex:1094-1111,1694-1702; D^-1 h1 detection",
       64, f"formal_diff_three_d9_b_D{power}_euler_derived")
    for power in (4, 8)
) + tuple(
    _a("DER-3I-EULER-D9-C", "ws_3sigma_i",
       rf"\{{h_1+xv_1\}}D^{power}u_{{3\sigma_i}}", (8 * power + 1, 1),
       rf"\{{x+y\}}h_1k^2D^{power + 1}u_{{3\sigma_i}}", (8 * power, 10),
       9, "verified",
       "formal_notes.tex:678-705; DKLLW24 Table 8 rows 12-13, Tables 3 and 6, u_4sigma periodicity (main.tex:869-878)",
       64, f"formal_diff_three_d9_c_D{power}_euler_derived")
    for power in (3, 7)
) + (
    _a("FN-3I-007", "ws_3sigma_i", r"\{x+y\}h_1^2D^7u_{3\sigma_i}", (57, 3),
       r"2v_1^2k^3D^8u_{3\sigma_i}", (56, 12), 9, "verified",
       "formal_notes.tex:764-775; Note/record/note.tex:1343-1345 (32-pattern sibling)",
       64, "formal_diff_three_d9_t_D7_sibling"),
    _a("FN-3I-008", "ws_3sigma_i", r"\{x+y\}h_1D^7u_{3\sigma_i}", (56, 2),
       r"x^2h_1k^2D^8u_{3\sigma_i}", (55, 11), 9, "verified",
       "formal_notes.tex:777-780; Note/record/note.tex:1343-1345 (32-pattern sibling)",
       64, "formal_diff_three_d9_b_D7_sibling"),
) + tuple(
    # These Euler images are nonzero only on the c=1 branch. They are not
    # additional printed formal-notes rows or unconditional source deaths.
    _a(f"DER-MIX-D9-P-D{power}", "ws_sigma_i_2sigma_j",
       rf"\{{yh_2+xh_1v_1\}}D^{power}u_{{\sigma_i+2\sigma_j}}", (8 * power + 2, 2),
       rf"\{{x+y\}}h_1^2k^2D^{power + 1}u_{{\sigma_i+2\sigma_j}}", (8 * power + 1, 11),
       9, "review", "formal_notes.tex:520-526,881-932; DKLLW24 Lemma 5.2 and Table 6; omega and Euler multiplication",
       64, f"formal_diff_mixed_d9_p_D{power}_euler_derived")
    for power in (2, 6)
) + tuple(
    _a(f"DER-MIX-D9-Q-D{power}", "ws_sigma_i_2sigma_j",
       rf"\{{h_1^2+xh_1v_1\}}D^{power}u_{{\sigma_i+2\sigma_j}}", (8 * power + 2, 2),
       rf"\{{x+y\}}h_1^2k^2D^{power + 1}u_{{\sigma_i+2\sigma_j}}", (8 * power + 1, 11),
       9, "review", "formal_notes.tex:520-526,881-932,953-970; DKLLW24 Tables 3 and 6; finite g-target injection",
       64, f"formal_diff_mixed_d9_q_D{power}_derived")
    for power in (2, 6)
) + tuple(
    _a(f"DER-MIX-PHI-D9-D{power}", "ws_sigma_i_2sigma_j",
       rf"\{{x+y\}}h_1" + (rf"D^{power}" if power else "") + r"u_{\sigma_i+2\sigma_j}", (8 * power, 2),
       rf"x^2h_1k^2D^{power + 1}u_{{\sigma_i+2\sigma_j}}", (8 * power - 1, 11),
       9, "verified",
       "formal_notes.tex:875,881-901; Note/record/note.tex:762-779 (corrected transport); " +
       ("independently verified DER-3I-D9-C; " if power % 2 == 0 else "independently verified DER-3I-EULER-D9-C; ") +
       "Lemma 2.6, main.tex:488-524,833-878; table_Q8.tex:520-521 (formula comparison)",
       64, f"formal_diff_mixed_phi_d9_D{power}")
    for power in (0, 1, 4, 5)
) + (
    # The local summary prints coefficient 1. The independent finite-source
    # argument establishes a nonzero F4 unit, not that normalization.
    _a("DER-MIX-D17-V-D3", "ws_sigma_i_2sigma_j",
       r"\{x+y\}h_1D^3u_{\sigma_i+2\sigma_j}", (24, 2),
       r"x^2h_1k^4D^5u_{\sigma_i+2\sigma_j}", (23, 19), 17, "verified",
       "table_Q8.tex:533; DKLLW24 main.tex:1311-1315,1914,2328; finite incoming/outgoing exclusion and Euler cycles",
       64, "formal_diff_mixed_d17_v_D3_forced"),
)

_THREE_D3_CERTIFICATE = {
    "status": "verified",
    "source_refs": ["formal_notes.tex:283-305,678-700",
                    "DKLLW24 main.tex:1094-1111,1941-1956,2045-2058,2782-2784,2868"],
    "premises": ["FN-2I-001", "DKLLW24 Table 9 rows 1-2",
                 "psi-fixed pure sigma_i generators and Thom classes"],
    "actual_products": {
        "U*x^2": "0: H^2(Q8,pi_4 E tensor sigma_i)=W/2 + W/2, so reduction is injective",
        "C*x^2": "A*h1=R: H^3(Q8,pi_2 E tensor sigma_i) is killed by 2, so reduction is injective",
        "R*h1": "2kU (actual hidden h1 extension, not the associated-graded zero)",
        "4kU": "0",
    },
    "derivation": (
        "Let U=v1^2 u_sigma, C=(h1+xv1)u_sigma, A=(x^2+y^2)u_sigma, R=x^2h1u_sigma. "
        "Leibniz with d3(u_2sigma)=x^2h1u_2sigma gives d3(Uu_2sigma)=h1^3u_3sigma "
        "and d3(Cu_2sigma)=2kUu_2sigma +/- 2kUu_2sigma=0. The latter summand has order 2. "
        "The chosen psi-fixed basis fixes the nonzero F4 units to 1, not the Witt factors 2 or 4. "
        "Permanent h1 supplies the three displayed h1 products; d3(D)=0 gives their 8-stem translates."
    ),
    "scope": (
        "Only these d3 equations and h1 products are verified; no Jan29 premise. "
        "This does not certify completeness of all d3 rows, a later d5, or permanence of C. "
        "The filtration-zero kernel contains 2W{v1^2u_3sigma}; it is not a 2-torsion group."
    ),
}

_TWO_D7_CERTIFICATE = {
    "status": "verified", "method": "d9 product contradiction and exact Witt target quotient",
    "source_refs": ["formal_notes.tex:334-420,487-506",
                    "DKLLW24 main.tex:1694-1702; Table 3; Table 8"],
    "premises": ["FN-2I-001", "FN-2I-003", "FN-2I-005", "FN-2I-006", "FN-2I-011",
                 "DKLLW24 D^-1 h1 is a 13-cycle",
                 "psi-fixed pure sigma_i generators and Thom classes"],
    "target_quotients": {
        "FN-2I-012": {
            "bidegree": [24, 8], "pattern": "I00", "two_valuation": 1, "j_order": 0,
            "prior_d5": "d5((x^2+y^2)h2D^3u)=4k^2D^4u removes the four-layer",
        },
        "FN-2I-013": {
            "bidegree": [32, 8], "pattern": "I00", "two_valuation": 2, "j_order": 0,
            "prior_d5": "d5(2k^2D^5u)=2k^3h2D^5u removes the two-layer from cycles",
        },
    },
    "derivation": (
        "Write Hm=h1D^m u_2sigma_i. H3,H4 have no incoming by filtration, their d3 is zero, "
        "and their d5 target cells are empty. If either were a 7-cycle it would also be a "
        "9-cycle: its potential d9 target is xh1k^2D^(4,5)u, a FN006 d5 source already "
        "absent from E6. Then h1*H3=(D^-1*h1)*H4 would be a 9-cycle, contradicting "
        "FN011's nonzero d9. The integer factor D^-1*h1 is already a 13-cycle by "
        "DKLLW main:1694-1702; no final d23 is used. The exact E7 target of H3 has only "
        "the two-layer: FN003 multiplied by h2 hit the four-layer on E5. The H4 target "
        "has only the four-layer: FN005's g^2 and 16-pattern translate made its "
        "two-layer a d5 source. In both cells primitive d3 already removed the odd "
        "layer and positive-j terms. Nonzero therefore determines the stated distinct "
        "Witt target layers, with F4 unit 1 in the chosen psi-fixed basis. Repeat the "
        "same argument separately for H7,H8 using FN011's D7 block, then translate "
        "by the permanent D8 and forward g."
    ),
    "scope": (
        "Only the constant I11 source layer is killed; its positive-j ideal remains. "
        "Both target cells become zero on E8, not a surviving opposite Witt layer. "
        "The 32-stem agreement is a repeated differential pattern, not permanence "
        "of D4. Coordinates refer to the source workspace. No Jan29 or vanishing-line premise."
    ),
}

_VERIFIED_FORMAL_CERTIFICATES = {
    "FN-2I-012": _TWO_D7_CERTIFICATE,
    "FN-2I-013": _TWO_D7_CERTIFICATE,
    "FN-2I-014": {
        "status": "verified", "method": "C4 d13 transfer and E2 Euler-kernel exclusion",
        "source_refs": ["formal_notes.tex:334-420,508-516 (subgroup and source repaired)",
                        "BBHS20 Remark 5.12 and Proposition 5.28; pp.3466-3467",
                        "DKLLW24 main.tex:488-524,1094-1118,2831-2839,2913-2917"],
        "premises": ["FN-2I-001", "FN-2I-003", "FN-2I-004", "FN-2I-005",
                     "DER-2I-TATE-AH2-D2-cycle", "DER-2I-TATE-AH2-D6-cycle",
                     "BBHS20 d13(Delta nu varpi)=Delta^-4 varpi^8",
                     "psi-fixed pure sigma_i generators and Thom classes"],
        "transfer_certificate": {
            "subgroup": "C4<i>=ker(sigma_i)", "exactness_page": 2,
            "restriction": "res(D)=Delta, res(g)=Delta varpi^2",
            "source_bidegree": [17, 3], "target_bidegree": [16, 16],
            "target_trace": "tr(res(k^4 D^4 u))=2k^4 D^4 u at E2",
            "euler_kernel": "(x^2+y^2)h2 D^2 u",
            "excluded_direction": "a_sigma_i*(h2^3 D u)=2kv1^2 D^2 u_3sigma_i != 0",
        },
        "derivation": (
            "Write u=u_2sigma_i, A=x^2+y^2 and e=a_sigma_i. The C4 d13 source "
            "Delta*nu*varpi transfers at E2 into ker(e), which is the single line "
            "P=Ah2D^2u: eP=0, whereas e(h2^3Du)=2kv1^2D^2u_3sigma is nonzero "
            "by the actual hidden h2 product and its W/4 constant layer. FN003 gives "
            "a negative-source Tate d5 onto P, hence its HFPSS outgoing maps are zero. "
            "Naturality therefore makes the E13 image of Z=2k^4D^4u zero. This uses "
            "the E2 trace identity only, not survival of k^4D^4u or Euler exactness "
            "on arbitrary Er. Z is the transfer of a class surviving to the C4 d13 "
            "page, so while nonzero it cannot disappear by an earlier outgoing map. "
            "In its E7 quotient primitive d3 removed the odd layer and j-tail, and "
            "FN003*h2 removed the four-layer; only two1 remains. The d9 incoming "
            "cell is empty and the d11 candidate I51 already supported d3. Thus "
            "d7(h1k^2D^3u)=Z. Multiplication by g^-2D8 in Tate gives the low H5 "
            "block. Repeat the C4 proof using its permanent Delta^4, with the "
            "independent Ah2D6 cycle certificate, to obtain the high +32 block "
            "and hence the low H1 block. Both endpoints after translation have "
            "positive filtration, so Tate differential correspondence applies."
        ),
        "scope": (
            "The I11 constant supports d7 to the I00 two1 constant; retain its j-tail. "
            "The two 32-separated blocks repeat under Q8 D8, not an invertible Q8 D4. "
            "A Tate cycle certificate constrains outgoing maps only, never incoming. "
            "No every-source-is-transfer assertion, FN017, Jan29 or vanishing-line premise."
        ),
    },
    "FN-2I-016": {
        "status": "verified", "method": "d11 product boundary and finite incoming-source exclusion",
        "source_refs": ["formal_notes.tex:283-305,334-420,450-470,520-526",
                        "DKLLW24 main.tex:633-642,937-949,1036-1039,1373-1387,1694-1702",
                        "DKLLW24 main.tex:488-510,1236-1246,1336-1342"],
        "premises": ["FN-2I-001", "FN-2I-004", "FN-2I-005", "FN-2I-006", "FN-2I-009",
                     "DKLLW24 primitive d3 and D^-1 h1 is a 13-cycle",
                     "permanent g and D8; Tate differential correspondence",
                     "psi-fixed pure sigma_i generators and Thom classes"],
        "actual_products": {
            "A*h1": "x^2h1: y^2h1=0; reduction is injective in the 2-torsion H3 group",
            "x^2*v1^2h1": "0 in actual cohomology, so the extra Thom term vanishes",
        },
        "derivation": (
            "Write u=u_2sigma_i, A=x^2+y^2 and m=2,6. FN009 gives "
            "d11(Ak^3D^(m+5)u)=h1k^6D^(m+6)u: use its D6 block times g^3D^-8 "
            "for m=2, and its D2 block times g^3 for m=6. Multiply by the published "
            "13-cycle D^-1h1. The product source is Ah1k^3D^(m+4)u="
            "d3(k^3D^(m+4)u), hence zero on E11. Thus T=h1^2k^6D^(m+5)u is "
            "already zero on E11. Before then T is a product of cycles, so cannot "
            "support an outgoing differential. Incoming d3 removes jT, not its "
            "constant; the d5 source cell is empty; the d7 candidate "
            "h1^3k^4D^(m+4)u is already an FN006 d5 boundary. The remaining incoming "
            "is d9 from Y=h2k^4D^(m+4)u. This source is a cycle through E9; its only "
            "possible incoming d3 source is an FN006 d5 source, hence a 3-cycle. "
            "Its double is the FN005 boundary d5(2k^3D^(m+4)u)=2Y: explicitly use "
            "g^3D^-8*(2D^5u) for m=2 and g^3*(2Du) for m=6, not bare D parity. "
            "Therefore the nonzero constant lines support d9(Y)=T. Translate by "
            "g^-4D8 in Tate; both resulting endpoints have positive filtration, "
            "so Lemma 2.6 gives d9(h2D^m u)=h1^2k^2D^(m+1)u in HFPSS."
        ),
        "scope": (
            "Two independently proved D2/D6 blocks repeat by permanent D8, giving "
            "a common 32-stem differential pattern, not a permanent D4. The low W/4 "
            "source retains its two-multiple after d9: its corresponding d5 source "
            "has negative filtration. Only the constant target remains after d3. "
            "No FN002, FN010-014, FN017, vanishing-line or Jan29 premise. "
            "No inverse g cancellation in HFPSS; no admission of mixed Euler images."
        ),
    },
    "FN-2I-006": {
        "status": "verified", "method": "coefficient Euler sequence and transfer naturality",
        "source_refs": ["formal_notes.tex:401-420 (subgroup labels repaired)",
                        "DKLLW24 main.tex:451-477,520-524,976-977",
                        "BBHS20 Remark 4.3, Propositions 5.10,5.21,5.25,5.27; pp.3441,3449,3456-3457,3465-3466"],
        "premises": ["FN-2I-001", "FN-2I-005", "BBHS20 C4 d7 and permanent RO unit",
                     "psi-fixed pure sigma_i generators and Thom classes"],
        "coefficient_sequence": "0 -> M tensor sigma_j -> Ind_C4<j>^Q8 Res(M) -> M -> 0, at E2 only",
        "transfer_subgroups": {"nonkernel": "C4<j>", "kernel": "C4<i>"},
        "c4_period": {"class": "P=Delta^2/u_2sigma=delta^4(u_lambda^4 u_2sigma)",
                      "degree": "14+2sigma", "permanent_unit": True},
        "c4_target_quotient": "F4[[mu]]{t} / (mu*t) = F4{t} by E4; d3(P^-1 T2 varpi^2)=mu*t",
        "derivation": (
            "Write u=u_2sigma_i and T=kh1^3u. Its a_sigma_j product lies in "
            "H8(Q8;pi6 E tensor sigma_j)=0: the central -1 acts negatively on the "
            "2-torsion-free coefficient module, so invariants vanish, and four-periodic "
            "Tate cohomology identifies this group with Tate H0. The coefficient Euler "
            "sequence at E2 therefore gives a transfer preimage from C4<j>. BBHS gives "
            "d7(u_2sigma)=t=P^-1(varsigma varpi^3 Delta^-1); after d3 removes mu*t, "
            "the preimage cell at E7 is one F4 line. If T survived E7, transfer(t)=alpha*T "
            "with alpha nonzero. The normalized Thom restriction gives transfer_C4<j>(u_2sigma)=2u "
            "exactly, while 2u=transfer_C4<i>(1) has zero outgoing. Naturality would give "
            "0=d7(2u)=alpha*T, a contradiction. Early-page source exclusion leaves only "
            "d5(xh1u)=T. Since (xh1)h2=0, Leibniz gives every 8-stem translate."
        ),
        "normalization": "Nonzero follows from transfer; the nonzero F4 unit is 1 separately by the chosen psi-fixed basis.",
        "scope": (
            "Corrects the exchanged i,j in formal_notes:411-413. Exactness is used only at E2, "
            "never im(transfer)=ker(Euler) on arbitrary Er. The period is a repeated "
            "differential pattern, not permanence of D; no vanishing-line assumption."
        ),
    },
    "FN-2I-009": {
        "status": "verified", "method": "C4 restriction and finite earlier-target exclusion",
        "source_refs": ["formal_notes.tex:283-305,334-399,450-470",
                        "BBHS20 Propositions 5.25 and 5.28; pp.3465-3467",
                        "DKLLW24 main.tex:488-510,710-722,2915-2917"],
        "premises": ["FN-2I-001", "FN-2I-003", "FN-2I-004", "FN-2I-005",
                     "BBHS20 d13(Delta^3 nu^2)=Delta^-2 nu varpi^7"],
        "restriction_certificate": {
            "subgroup": "C4<j>", "A": "A=(x^2+y^2)u_2sigma_i=a_sigma_i^2",
            "permanent_unit": "P=Delta^2/u_2sigma, degree 14+2sigma",
            "identity": "res(AD^2)=a_sigma^2 Delta^2=P^-1 Delta^3 nu^2",
            "second_block": "res(AD^6)=Delta^4 res(AD^2); Delta^4 is a C4 permanent unit",
        },
        "derivation": (
            "The nonzero C4 d13 implies AD^2 and AD^6 cannot be hit before E13. Their "
            "d3,d5 are zero by the earlier Euler/Leibniz equations. The potential d7 "
            "targets (13,9),(45,9) are I51 directions already removed by primitive d3; "
            "the d9 targets (13,11),(45,11) are empty. In the d13 target at (13,15) "
            "and its +32 sibling, d5 identifies C=I13X with E=I13 rather than killing "
            "both. The remaining line is represented by h2^3 k^3 D^2 u, whose restriction "
            "is zero since nu^3=0. It cannot realize the nonzero C4 d13. Thus the only "
            "remaining outgoing possibility is the asserted nonzero d11. The source "
            "is the sum I62X+I62Y, never either summand on its own."
        ),
        "scope": (
            "The two D2/D6 blocks repeat under Q8 D8. Their 32-stem coincidence does "
            "not make Q8 D4 permanent. Independent of FN006, later vanishing and Jan29."
        ),
    },
    "FN-2I-010": {
        "status": "verified", "method": "d11 product obstruction and finite incoming-source exclusion",
        "source_refs": ["formal_notes.tex:472-482", "DKLLW24 Table 8 rows 6-7; Lemma 2.6"],
        "premises": ["FN-2I-001", "FN-2I-003", "FN-2I-004", "FN-2I-005", "FN-2I-009",
                     "DER-2I-TATE-H2-cycle", "DER-2I-TATE-H6-cycle",
                     "DER-2I-TATE-JD2-cycle", "DER-2I-TATE-JD6-cycle"],
        "derivation": (
            "h1*AD^2=x^2h1D^2u=d3(D^2u), so multiplying FN009 by h1 makes "
            "B=k^3h1^2D^3u zero on E11. B was a cycle, so must be hit earlier. "
            "d3 hits its positive-j tail, not B; the incoming d5 cell (15,9) is empty. "
            "The d7 candidate kh1^3D^2u=H2*(kh1^2) is a 7-cycle, since H2 is a "
            "Tate-certified cycle and kh1^2=(gD^-8)(D^5h1)h1, with D^5h1 a Table 8 "
            "d9 source. The only remaining incoming is d9 from 2kh2D^2u at (15,5); "
            "the odd two-layer of this cell was already killed by FN004 d5. Its own "
            "incoming d5 from (16,0) is zero: FN005 covers 2D^2u and the negative-source "
            "Tate d3 certifies the whole positive-j ideal jD^2u. The D6 block is identical "
            "using H6. Translate that D6 block by g^-1 in Tate to obtain the low-filtration "
            "row 2h2D^3u -> k^2h1^2D^4u; the other low block uses D2 and g^-1 D8."
        ),
        "scope": "Only the two_valuation=1 source and constant target. No inverse g in HFPSS and no permanent Q8 D4 assumption.",
    },
    "FN-2I-011": {
        "status": "verified", "method": "Tate-certified H2/H6 multiplication and nonzero quotient target",
        "source_refs": ["formal_notes.tex:487-494", "DKLLW24 Table 8 rows 6-7; Lemma 2.6"],
        "premises": ["FN-2I-001", "FN-2I-003", "FN-2I-004", "FN-2I-009",
                     "DER-2I-TATE-H2-cycle", "DER-2I-TATE-H6-cycle"],
        "derivation": (
            "Multiply Table 8 d9(Dh1)=k^2D^2xh1 by H2=h1D^2u or H6=h1D^6u. "
            "This gives d9(h1^2D^(3,7)u)=k^2h2^3D^(3,7)u. The product source has "
            "no earlier outgoing and no incoming by filtration/parity. The product "
            "target is a cycle; incoming d3,d7 source cells are empty, while d5 only "
            "kills I13X+I13. Thus the common I13=I13X quotient is nonzero at E9. "
            "j annihilates this finite target: the positive-j source tail is not killed."
        ),
        "scope": "Two D3/D7 blocks modulo D8; a single rank-one quotient target, not two separate dots. No hidden-extension or later-vanishing premise.",
    },
    "FN-MIX-004": {
        "status": "verified", "method": "omega-transported Euler product and target survival",
        "source_refs": ["formal_notes.tex:357-379,934-951", "Note/record/note.tex:713,725",
                        "DKLLW24 main.tex:915,1094-1123,1179-1190,1972-1976,2868"],
        "premises": ["FN-2I-004", "FN-MIX-001", "DKLLW24 Lemma 5.2"],
        "derivation": (
            "omega fixes h2,k and scales D by zeta^2. Both sides of FN-2I-004 scale equally, "
            "so d5(h2*D*u_2sigma_j)=k*h2^2*D*u_2sigma_j has coefficient 1. Multiply by the "
            "permanent Euler class E=a_sigma_i, writing H=h2*u_2sigma_j, P=E*H and R=x^3*u. "
            "The actual product P*h2=R*D gives d5(PD)=kRD^2. P's H^2 group is W/2 + W/2 "
            "and R has a single finite two-torsion line, so this product has no hidden two-layer correction. "
            "d3(H)=zeta^2*x^2*h1*h2*u=0; hence P and R=P*h2*D^-1 are 3-cycles. "
            "The source (10,2) has no incoming d3 and the target (9,7) has empty incoming cell (10,4). "
            "The target's outgoing cell (8,10) is NOT empty: its cycle property follows from the product. "
            "Leibniz with d5(D)=kDh2 gives d5(P)=0; 2P=0 gives d5(PD^(2l))=0 and "
            "d5(PD^(2l+1))=kRD^(2l+2). This is a 16-stem pattern, not permanence of D^2."
        ),
        "scope": (
            "This certificate establishes only the P direction and its even-D zero. "
            "Q's zero d5 is separately certified by DER-MIX-D5-B-NONZERO and FN-MIX-005-Q-zero; "
            "mixed C supports d3, so the pure-three-sigma empty-target argument is not its proof. "
            "Forward multiplication by permanent g is allowed, not inverse g in HFPSS or bare k. "
            "Atlas images use explicitly transported bases; conjugating the unit 1 leaves it fixed. "
            "No pure-sector normalization is imposed on other mixed coefficients."
        ),
    },
    "FN-2I-005": {
        "status": "verified", "method": "kernel-subgroup transfer and Leibniz",
        "source_refs": ["DKLLW24 main.tex:520,1021,1384-1389,1451-1453", "formal_notes.tex:382-399"],
        "derivation": (
            "For H=ker(sigma_i)=C4<i>, V=2-2sigma_i restricts to zero and the coset acts "
            "on its orientation by det(-I_2)=+1. Thus tr_H^Q8(1) has E2 representative "
            "2u_2sigma and no outgoing differential. Leibniz gives d5(2D^m u)=2m*k*h2*D^m u; "
            "4h2=0 gives the even-D zero and 16-stem repetition. The odd-D target's nonzero "
            "W/4 two-layer survives d3: its only possible source xh1Du has d3=0 since "
            "x^2*xh1=0 in the actual 2-torsion H^4(Q8,pi_2 E)."
        ),
        "scope": "Uses the kernel subgroup C4<i>, not the interchanged subgroups in formal_notes:411-414; does not admit FN-2I-006.",
    },
    "FN-MIX-001": {
        "status": "verified", "method": "omega-transported Thom differential and actual hidden product",
        "source_refs": ["formal_notes.tex:881-901", "DKLLW24 main.tex:638-647,937-949,1094-1111,1183-1185,2868"],
        "derivation": (
            "omega(x)=zeta*x and omega(h1)=h1, so d3(u_2sigma_j)=zeta^2*x^2*h1*u_2sigma_j. "
            "With U=v1^2u and C=(h1+xv1)u, actual products U*x^2=0 and C*x^2*h1=2kU give "
            "d3(U)=h1^3u and d3(C)=2(1+zeta^2)kU=2zeta*kU. The last equality is in W/4: "
            "1+zeta^2=-zeta and 4kU=0. j*(2kU)=0, so only C's constant layer supports this map. "
            "Permanent h1 gives the three displayed U*h1 products; D is a 3-cycle, giving 8-stem repetition."
        ),
        "scope": "Keep the Witt two-layer and the nontrivial F4 unit separately. psi conjugates zeta; this mixed sector is not pure sigma_i. omega(j)=zeta*j; atlas coordinates use explicitly transported bases.",
    },
}
_VERIFIED_FORMAL_CERTIFICATES["FN-2I-017"] = {
    "status": "verified", "method": "Published d23 product boundary and finite incoming-source exclusion",
    "source_refs": ["formal_notes.tex:334-420,450-536 (finite exclusion repaired)",
                    "DKLLW24 main.tex:488-510,1373-1387,1744-1753,1914-1915"],
    "premises": ["FN-2I-001", "FN-2I-003", "FN-2I-004", "FN-2I-005", "FN-2I-006",
                 "FN-2I-009", "FN-2I-011", "FN-2I-013", "FN-2I-014", "FN-2I-016",
                 "DKLLW24 Table 8 row 22", "permanent g and D8; Tate differential correspondence",
                 "psi-fixed pure sigma_i generators and Thom classes"],
    "cycle_audit": {
        "class": "X_p=h1^2 D^p u_2sigma, independently for p=4,8",
        "incoming": "filtration 2 excludes r>=3; d2 is excluded by parity",
        "outgoing": {
            "3,7": "h1 times FN013 H_p; d7 is 4h1 k^2 D^(p+1)u=0",
            "5,13,21": "empty E2 target cell",
            "9": "H_(p-2)*(D^2h1) hits only I13, already an FN004 h2-product boundary",
            "11,19": "I51 targets already supported primitive d3",
            "15": "I11 target is an FN009 d11 boundary",
            "17": "FN003 kills I13X+I13 and FN011 kills I13; both directions are now zero",
            "23": "I11 constant supported FN014 d7; its positive-j tail was a primitive d3 image",
        },
    },
    "target_cutoff": {"zero_on_page": 23, "not_a_vanishing_line": True,
                      "bidegrees": [[26, 26], [58, 26]], "e2_pattern": "I22H"},
    "derivation": (
        "Put u=u_2sigma and work separately with p=4,8. The finite cycle audit proves "
        "X_p=h1^2D^pu survives through E23 and d23(X_p)=0. Its early factorization "
        "h1*H_p is used only through E7; after H_p dies, use the independent H2/H6 "
        "factorization for d9, not a dead source. FN006 times g^-1 gives a Tate d5 "
        "(8p-4,-2)->(8p-5,3) onto Z_p=h1^3D^(p-1)u, so Z_p has zero outgoing maps "
        "in HFPSS, without deleting it there or forbidding incoming maps. Multiply "
        "the published d23(D^-1h1)=g^6D^-16 by X_p. Since (D^-1h1)X_p=Z_p, Leibniz "
        "forces T_p=h1^2k^6D^(p+2)u=0 on E23 itself. Before that page T_p is the "
        "product of X_p with the permanent integer g^6D^-16, so cannot disappear by "
        "an outgoing map. Enumerate only incoming r<23: primitive d3 hits jT_p, "
        "not its constant; r5,13,21 source cells are empty; r7,15 I33 sources are "
        "FN006 d5 boundaries; r11,19 I73/I73V sources are respectively Thom d3 "
        "boundaries and primitive d3 sources. The r17 I31 odd constant is an FN016 "
        "d9 source and its double an FN005 d5 image. Thus only the r9 source "
        "2h2 k^4 D^(p+1)u can hit T_p. Its odd layer supported FN004 d5, while "
        "the double survives: its possible d5 preimage is g^3D^-8*(2D^p u), "
        "whose d5 is zero for p=4,8. Tate multiplication by g^-4D8 returns the two "
        "equations to source filtrations 1 and target filtrations 10."
    ),
    "scope": (
        "The cutoff is zero on E23, not E24; a surviving potential d23 incoming source "
        "does not obstruct this argument. Preserve the I31 two1 source and I22H constant "
        "target: earlier d5/d3 already removed the other layers. Treat the two 32-separated "
        "blocks independently and repeat by D8, never by an invertible high-page D4. "
        "No Jan29 or imposed vanishing-line premise is used."
    ),
}

_VERIFIED_FORMAL_CERTIFICATES["FN-2I-018"] = {
    "status": "verified", "method": "Euler image and actual-product target quotient",
    "source_refs": ["formal_notes.tex:334-379,450-470,540-555",
                    "DKLLW24 main.tex:488-510,943-949,1037,1694-1702,2460-2461"],
    "premises": ["FN-2I-001", "FN-2I-003", "FN-2I-004", "FN-2I-009",
                 "DER-2I-TATE-H2-cycle", "DKLLW24 Table 9 row 19",
                 "DKLLW24 Table 8 row 22 pre-d23 cycle",
                 "psi-fixed pure sigma_i generators and Thom classes"],
    "actual_products": {
        "e*e": "(x^2+y^2)u_2sigma; H2(Q8,W) is killed by 2",
        "e*C": "xh1u_2sigma; central -1 kills 2H2(Q8,pi_2 E), so reduction mod 2 is injective",
        "e*(C*h1)": "xh1^2u_2sigma=h2^3 D^-1 u_2sigma in the actual finite 2-torsion cell",
    },
    "target_quotient": {
        "bidegree": [29, 15], "components": {"I13": 1},
        "basis": ["K=h2^3 k^3 D^4 u", "L=x^2 h2 k^3 D^5 u"],
        "earlier_image": {"I13": 1, "I13X": 1},
        "rank_before_d13": 1, "K_nonzero": True,
    },
    "derivation": (
        "Let e=a_sigma_i, C=(h1+xv1)u_sigma and u=u_2sigma. The actual products are "
        "e^2=(x^2+y^2)u and eC=xh1u. For the latter, the central element -1 acts by -1 "
        "on pi_2 E but trivially on group cohomology, so 2H2=0 and reduction mod 2 is "
        "injective. Then (x+y)(h1+xv1)=xh1 follows from h1y=v1x^2 and xy=0. "
        "Multiply the published Table 9 d13(eD4)=k3(C h1)D5 by e. The source "
        "AD4u at (30,2) is nonzero on E13: Euler naturality prevents early outgoing maps, "
        "and its filtration excludes early incoming maps. The target is K=h2^3 k3D4u. "
        "At (29,15) its earlier d3,d7,d11 incoming cells are empty. The d5 source "
        "has lost its bo direction to primitive d3; FN003/FN004 give precisely the "
        "line K+L, L=x^2h2 k3D5u, not both independent directions. This is FN003's "
        "D7 block times g^2 D^-8. The remaining d9 candidate is "
        "h1^2 kD4u=g*(h1D2u)*(D^-1h1); its factors are 9-cycles by the independent "
        "H2 Tate certificate and the published integer row. Its positive-j tail was "
        "already a d3 boundary. Thus K is nonzero in the rank-one E13 quotient, "
        "and the Euler-image d13 is genuinely nonzero with F4 unit 1."
    ),
    "scope": (
        "Repeat only by permanent D8 (64 stems) and forward g; use Tate comparison "
        "when certifying nonzero g-translates. Never cancel g in HFPSS or regard D4 "
        "as permanent. No Jan29, FN017, high two-sigma differential or imposed "
        "vanishing-line premise is needed."
    ),
}

_TWO_D21_SCOPE = (
    "Repeat only by permanent D8 and forward g=kD3. No D4 unit, imposed vanishing line, "
    "Jan29 argument or deletion of a whole multicolumn cell. A class forced zero ON E23 "
    "must be hit before d23; the published d23 is not itself the incoming arrow. "
    "Pure psi-fixed F4 units are 1; the Witt coefficient-four layer remains two=2."
)
_TWO_D21_PREMISES = [f"FN-2I-{n:03}" for n in (1, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 16, 17, 18)] + [
    "DKLLW24 Table 8 row 22: d23(D^-1 h1)=D^-16 g6",
    "permanent e=a_sigma_i, h1, h2, g and D8; Tate differential correspondence",
    "psi-fixed pure sigma_i generators and Thom classes",
]
_VERIFIED_FORMAL_CERTIFICATES["FN-2I-019"] = {
    "status": "verified", "method": "Published d23 product and finite E21 quotient",
    "source_refs": ["formal_notes.tex:558-563", "table_Q8.tex:407",
                    "DKLLW24 main.tex:488-510,1236-1250,1336-1342,1914"],
    "premises": _TWO_D21_PREMISES[:],
    "target_cutoff": {"zero_on_page": 23, "bidegree": [54, 26], "not_a_vanishing_line": True},
    "target_quotient": {"components": {"I62X": 1, "I62Y": 1}, "rank_before_d21": 1,
                        "kind": "kernel of earlier d5, not quotient identifying X and Y"},
    "derivation": (
        "Let u=u_2sigma and A=x2+y2. Multiply published d23(h1D7)=k6D10 by e2=Au. "
        "Its source Ah1D7u=x2h1D7u is d3(D7u), hence zero; its target Ak6D10u is "
        "therefore zero on E23. It has no outgoing differential, being a product of permanent "
        "e2,g6,D^-8. Enumerate incoming r<23 at (55,26-r): r3 has a 3-cycle I33; "
        "r5 the even h2 block has zero d5; r7,15 I73/I73V have already died; r9,17 "
        "are empty; r11,19 I33 are FN006 images; r13 has odd FN004 and even FN010 "
        "sources already dead. Only r21 remains. Its I31 two-layer was FN005's image; "
        "its odd constant survives. At the target primitive d3 killed I62V, and d5 has "
        "equal nonzero values on I62X and I62Y, leaving exactly A=X+Y. Thus the forced "
        "d21 is rank one onto this kernel line, not two independent arrows."
    ),
    "table_comparison": {"source": "table_Q8.tex:407", "table_period_stem": 64,
                         "table_representative": "h2D4u -> Ak5D7u",
                         "relation_to_formal": "multiply both sides by permanent g"},
    "scope": _TWO_D21_SCOPE,
}
_VERIFIED_FORMAL_CERTIFICATES["FN-2I-021"] = {
    "status": "verified", "method": "Published d23 product and finite E21 quotient",
    "source_refs": ["formal_notes.tex:572-577", "table_Q8.tex:409",
                    "DKLLW24 main.tex:488-510,1236-1250,1336-1342,1914"],
    "premises": _TWO_D21_PREMISES[:],
    "cycle_audit": {
        "class": "H=h2u", "through_page": 23, "permanent_asserted": False,
        "outgoing": {"3,7,11,15,19,23": "empty target cells", "5": "FN004 and Leibniz",
                     "9": "target constant is FN011 d9 source, j-tail already d3-dead; d9 squared",
                     "13": "entire I62 target already d5-dead", "17": "FN010 d9 image",
                     "21": "remaining A target already FN018 d13 source"},
    },
    "target_cutoff": {"zero_on_page": 23, "bidegree": [15, 29], "not_a_vanishing_line": True},
    "derivation": (
        "The independent finite target audit makes H=h2u a cycle through d23, without "
        "assuming it permanent. Multiply d23(D^-1h1)=k6D2 by gH. The left product "
        "is zero since h1h2=0, so T=h2k7D5u is zero on E23. It cannot disappear "
        "outgoing before that page. Its even layer is already an FN005 d5 image. "
        "Incoming r3 has the FN006 d5 source I02, a 3-cycle; r5 hits only the even "
        "layer; r7,15 are empty; r11,19 I02 sources have died by d5; r9,17 I40 died by primitive "
        "d3. In the r13 I00 cell the odd/j layers died by d3, the four-layer by FN003*h2 "
        "d5 and the two-layer by FN014 d7. The only earlier incoming map is therefore "
        "d21 from 4k2D3u. Its odd/j and two-layers died by d3 and FN005 d5 respectively, "
        "leaving precisely the four constant. Tate translation by g^-1 gives the "
        "additional positive-filtration seed 4ku -> h2k6D2u, not inverse-g HFPSS periodicity."
    ),
    "table_comparison": {"source": "table_Q8.tex:409", "table_period_stem": 64,
                         "table_representative": "4D5u -> h2k5D7u",
                         "relation_to_formal": "multiply by g2 D^-8; independently audited filtration-zero source"},
    "scope": _TWO_D21_SCOPE,
}
_VERIFIED_FORMAL_CERTIFICATES["FN-2I-020"] = {
    "status": "verified", "method": "Published d23 product and finite E21 quotient",
    "source_refs": ["formal_notes.tex:565-570", "table_Q8.tex:408,416",
                    "DKLLW24 main.tex:488-510,1914,2324-2338; Tables 3 and 6"],
    "premises": _TWO_D21_PREMISES[:] + ["FN-2I-019", "DKLLW24 permanent Q_sigma D3"],
    "cycle_audit": {
        "class": "F=4Du", "through_page": 23, "permanent_asserted": False,
        "outgoing": {"3,5": "Leibniz and 4h2=0", "7,15,23": "FN006 d5 images",
                     "9,17": "empty targets", "11,19": "I73/I73V already d3-dead",
                     "13": "FN004 odd and FN017 even layers already dead",
                     "21": "FN005 kills target double; remaining odd is FN019 d21 source; d21 squared"},
    },
    "target_cutoff": {"zero_on_page": 23, "bidegree": [20, 28], "not_a_vanishing_line": True},
    "low_quotient": {"bidegree": [1, 3], "basis": ["I13X", "I13"],
                     "matrix": [[1, 1]], "kernel": {"I13X": 1, "I13": 1}, "rank_after_d21": 1},
    "derivation": (
        "F=4Du is a cycle through d23 by finite target exclusion, not by the table's "
        "unproved permanent-cycle list. Multiply published d23(D^-1h1)=k6D2 by gF. "
        "The source 4gh1u=0 forces 4k7D6u=0 on E23. At (20,28) only the four constant "
        "remains after d3 and FN005 d5. Incoming r3 hits only j; r5 is zero on the even "
        "Ah2 direction and on h2-cube by h2^4=0; r7 is the independent H6 Tate cycle; "
        "r9,17 empty; r11,19,23 I51 already supported d3; r15 H3 supported FN012 d7. "
        "At r13 the Ah2 direction already supported d5; the other direction is the "
        "actual Euler image e(Q_sigma D3)g3D^-8, hence has zero outgoing map. The "
        "identity eQ_sigma=h2^3D^-1u is exact, not merely associated graded: reduction "
        "mod 2 is injective in this exponent-two cell, and its product reduces to xh1^2u. "
        "Only r21 remains. At the high source (21,7), earlier d5 killed X+Y, leaving "
        "[X]=[Y]; Tate translation down by g gives the claimed low arrow. At (1,3) "
        "X=x2h2u and Y=h2^3D^-1u are independent and X+Y=e2h2 is permanent. Thus "
        "d21(X)=d21(Y)=4k6D3u and the low kernel X+Y survives, rather than deleting "
        "both columns."
    ),
    "table_comparison": {"source": "table_Q8.tex:408", "table_period_stem": 64,
                         "table_representative": "y2h2u -> 4k6D3u",
                         "relation_to_formal": "identical by D y2=h2^2"},
    "scope": _TWO_D21_SCOPE,
}

_THREE_D5_CERTIFICATE = {
    "status": "verified", "method": "Euler product, actual hidden h2 product, and d5 squared",
    "source_refs": ["formal_notes.tex:357-378,730-762", "DKLLW24 main.tex:1094-1123,1179-1190,1336-1342,1451-1453"],
    "derivation": (
        "Write B=(x+y)u, C=(h1+xv1)u, P=h2B, Q=h1C, U=v1^2u. Euler multiplication of "
        "FN-2I-004 gives d5(PD)=kx^3D^2u; h2 multiplication and the actual hidden product "
        "x^3u*h2=2kU give d5(x^3D^2u)=2Uk^2D^2. The target survives d3 because C is a 3-cycle. "
        "The cells for d5(C) at (0,6) and Ch2 at (4,2) are empty, so every D-translate of Q has d5=0. "
        "Leibniz gives d5(P)=0, with 16-stem repetition. At (14,6), d5 is nonzero on the P direction "
        "and zero on Q; x^2B=x^3u and d5^2=0 therefore give d5(BD^2)=kD^2Q. Finally "
        "d5(BD)=kD(P+Q). The positive-j Q targets were already d3(Uh1^3D) and d3(Uh1^3), respectively."
    ),
    "scope": "The P+Q image has rank one, leaving P=Q in the quotient. Preserve the Witt two-layer. No FN-3I-002, Jan29 or imposed vanishing-line premise is used; this does not admit later d9/d11 claims.",
}
for _fact in ("FN-3I-003", "FN-3I-004", "FN-3I-005", "FN-3I-006"):
    _VERIFIED_FORMAL_CERTIFICATES[_fact] = _THREE_D5_CERTIFICATE

_VERIFIED_FORMAL_CERTIFICATES["FN-3I-002"] = {
    "status": "verified", "method": "Euler image and finite incoming-source exclusion",
    "source_refs": ["formal_notes.tex:472-482,678-728",
                    "DKLLW24 main.tex:488-510,1150-1198,1336-1342,1451-1453,1972-1976"],
    "premises": ["FN-2I-010", "FN-3I-001", "permanent Euler multiplication",
                 "unoriented E2 cell enumeration", "DKLLW24 Table 8 row 2",
                 "DKLLW24 Lemma 2.6", "psi-fixed pure sigma_i generators and Thom classes"],
    "derivation": (
        "Write e=a_sigma_i, A=(x^2+y^2)u_3sigma, B=(x+y)u_3sigma, P=h2B, U=v1^2u_3sigma. "
        "For m=2,6, multiply the independently verified FN010 equation by e. Its source "
        "is 2kPD^m=0 already on E2 since 2B=0, while its target is T=k^3 B h1^2 D^(m+1). "
        "T has no outgoing differential before E9, being the Euler image of an E9 class, "
        "and the image equation forces T=0 on E9 itself. T is initially a nonzero finite F4 line. "
        "The d3 and d7 incoming source cells (8m-2,12) and (8m-2,8) are empty. "
        "Even-page sources are empty by E2 parity. The only possible incoming page is d5: "
        "at (8m-2,10) the independent S62V direction Uh1^2 k^2 D^m has already supported "
        "FN3I001's h1^2 d3 product. Thus the S62 constant A k^2 D^(m+1) must survive "
        "to E5 and hit T nontrivially. Pure Galois normalization fixes this nonzero F4 unit to 1. "
        "Tate multiplication by g^-2 D^4 moves the m=2,6 equations to (6,2)->(5,7) "
        "and (38,2)->(37,7). Here D^4 is only an invertible 5-cycle: "
        "d5(D^4)=4kh2D^4=0, not a permanent unit. Multiplication by D^2 has extra "
        "term 2kAh2D^2=0 since 2A=0, yielding the 16-stem differential pattern."
    ),
    "target_cutoff": {"zero_on_page": 9, "not_a_vanishing_line": True,
                      "bidegrees": [[13, 15], [45, 15]], "e2_pattern": "S13"},
    "incoming_exclusion": {"d3": "empty E2 cell", "d7": "empty E2 cell",
                           "d5_S62V": "earlier FN-3I-001 h1^2 d3 source",
                           "d5_S62": "unique remaining constant direction"},
    "scope": (
        "Only this d5 family and its positive-filtration Tate translates are verified. "
        "The handwritten Jan29 proof and all later three-sigma claims are unnecessary. "
        "Do not infer that all E5 survivors are 2-torsion, identify P and Q before quotienting, "
        "or turn D^2/D^4 into permanent periods. Formal line 715 omits h2: the source is kPD^2."
    ),
}

_THREE_ODD_D9_CERTIFICATE = {
    "status": "verified", "method": "Euler products, finite target survival and h1 detection",
    "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
    "source_refs": ["formal_notes.tex:487-494,678-780",
                    "DKLLW24 main.tex:868-878,1094-1111,1694-1702; Table 8 rows 12-13"],
    "premises": ["FN-2I-011", "FN-3I-001", "FN-3I-003", "FN-3I-005", "FN-3I-006",
                 "DKLLW24 hidden h1 multiplication", "psi-fixed pure sigma_i basis"],
    "no_withdrawn_premise": True,
    "D_blocks": [3, 7], "same_object_period": "D^8", "forward_g_only": True,
    "derivation": (
        "Write a=(x+y)u, B=a*h1, T=a*h1^2, C=(h1+xv1)u, R=x^2*h1*u, U=v1^2*u. "
        "For m=3,7 separately, permanent Euler multiplication of verified FN-2I-011 gives "
        "d9(TD^m)=W=2U*k^3*D^(m+1), using the actual hidden product h1*R=2kU. "
        "This is the constant Witt two-layer S40: its odd and positive-j layers died by d3. "
        "Incoming d3 to W has finite source C*k^2*D^(m+1), a 3-cycle. Incoming d5 has "
        "source x^3*k*D^(m+1), the FN003 d5 image, so its outgoing d5 is zero by d5^2=0. "
        "Incoming d7 has source U*h1*k*D^m, already a primitive d3 source. Thus W is nonzero on E9. "
        "B*D^p for p=3,4,7,8 has empty d3 target; its d5 target is a primitive d3 boundary; "
        "its d7 target a*k^2*D^(p+1) is an FN005 or FN006 d5 source. Filtration two forbids "
        "earlier incoming maps. Since h1*B=T and h1*(R*k^2*D^(m+1))=W, the m=3,7 B rows "
        "are forced and their finite targets survive. For p=m+1 use the published 13-cycle "
        "L=D^-1*h1: L*(B*D^p)=T*D^m and L*(R*k^2*D^(p+1))=W. This independently forces "
        "the p=4,8 B rows without Ck permanence, a later d11 or a Jan29 premise. "
        "Same-cell S73V is a primitive d3 source, not the finite R target. "
        "D4 siblings are proved separately; only D8 is used as an invertible period."
    ),
    "target_ports": {"FN-3I-007": {"pattern": "S40", "two_valuation": 1, "j_order": 0},
                     "FN-3I-008": {"pattern": "S73", "two_valuation": 0, "j_order": 0}},
    "incoming_exclusion": {"d3": "C is a verified 3-cycle",
                           "d5": "entire finite source is an FN003 d5 image; d5 squared is zero",
                           "d7": "primitive d3 source already absent"},
}
for _fact in ("FN-3I-007", "FN-3I-008"):
    _VERIFIED_FORMAL_CERTIFICATES[_fact] = _THREE_ODD_D9_CERTIFICATE

_VERIFIED_FORMAL_CERTIFICATES["FN-3I-009"] = {
    "status": "verified", "method": "C4 restriction detection and finite E11 quotient",
    "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
    "source_refs": ["formal_notes.tex:782-796", "BBHS20 Proposition 5.28, pp.3465-3466",
                    "DKLLW24 main.tex:721,1573,1817,2235,2883"],
    "premises": ["FN-3I-001", "FN-3I-002", "FN-3I-003", "FN-3I-005", "FN-3I-006",
                 "DER-3I-D5-A-EVEN", "BBHS20 Proposition 5.28", "psi-fixed pure sigma_i basis"],
    "no_withdrawn_premise": True,
    "D_blocks": [4, 8], "paired_pattern_stem": 32, "same_object_period": "D^8",
    "restriction": {
        "subgroup": "C4<i>=ker(sigma_i)",
        "source": "A D^p, p=4,8", "image": "unit*Delta_1^(p-1)*nu^2",
        "unit": "constant permanent Witt unit; no unproved normalization of res(D) is required",
        "detector": "d13(Delta_1^3*nu^2)=Delta_1^-2*nu*varpi^7 != 0",
        "second_block": "published Delta_1^4-linearity, not Q8 D^4 permanence",
    },
    "derivation": (
        "Set A=(x^2+y^2)u, R=x^2*h1*u, C=(h1+xv1)u, P=(yh2+xh1v1)u, Q=C*h1, T=(x+y)h1^2u. "
        "DKLLW main2235 restricts A_sigma*D^3 to dbar^6*u_6lambda*u_4sigma*a_2sigma "
        "=Delta_1^2*nu^2 (main721 and BBHS p3465). Restriction of D is Delta_1 up to a "
        "constant permanent Witt unit, and u_2sigma_i restricts to 1 on the kernel subgroup. "
        "Hence A*D^p restricts to a unit times Delta_1^(p-1)*nu^2 for p=4,8. "
        "BBHS Proposition5.28 detects a nonzero d13 on both images, independently by Delta_1^4-linearity. "
        "A*D^p has no early incoming at filtration2. Its d3 is zero and even-A d5 is zero. "
        "Its d7 target U*h1*k^2*D^p is a primitive d3 source; its d9 target "
        "x^3*k^2*D^(p+1) is an FN003 d5 image; its d13 target T*k^3*D^(p+1) is an FN002 "
        "d5 image. Parity excludes even lengths, so restriction forces the remaining d11 "
        "to the constant C*k^3*D^(p+1) line. Positive-j C died by primitive d3; the other "
        "incoming d3 direction A*k^2*D^(p+1) is a 3-cycle, incoming d5/d9 cells are empty, "
        "and incoming d7 P*k*D^p,Q*k*D^p died by FN003/FN005 respectively. "
        "Multiplication by permanent h1 gives R*D^p -> Q*k^3*D^(p+1). At this second target "
        "primitive d3 removes positive-j Q, and FN006 removes only P+Q, leaving [P]=[Q] nonzero. "
        "Incoming d7 is an earlier d3 boundary and incoming d9 is empty. The nonzero product "
        "therefore also detects survival of the R source, without guessing its filtration-zero "
        "incoming map. Neither an odd-three-sigma d9 nor a Jan29/later differential is a premise."
    ),
    "target_quotient": {"first": "finite S11 constant only",
                        "second": "span(P,Q)/span(P+Q); positive-j Q already removed by d3",
                        "do_not_kill_whole_initial_cell": True},
}

_VERIFIED_FORMAL_CERTIFICATES["FN-MIX-006"] = {
    "status": "verified", "method": "omega-Euler product and finite E11 target survival",
    "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
    "source_refs": ["formal_notes.tex:450-470,496-499,881-901,934-951,972-991",
                    "DKLLW24 main.tex:915,937-949,1094-1111,1179-1190; Lemma 2.6",
                    "table_Q8.tex:527 (printed coefficient corrected)"],
    "premises": ["FN-2I-009", "FN-2I-012", "FN-MIX-001", "FN-MIX-004",
                 "permanent a_sigma_i", "psi-fixed pure sigma_i basis", "DKLLW24 Lemma 2.6"],
    "D_blocks": [2, 6], "paired_pattern_stem": 32, "same_object_period": "D^8",
    "derivation": (
        "Write E=a_sigma_i, A_j=x^2+zeta^2*y^2, B=(x+y)u_mix, R=x^3u_mix, "
        "U=v1^2u_mix, C=(h1+xv1)u_mix and P=(yh2+xh1v1)u_mix. "
        "Independently for p=2,6, omega of verified FN009 scales both A_j D^p "
        "and h1 k^3 D^(p+1) by zeta^(2p+2). The common Thom factor also cancels, "
        "so the rotated premise has coefficient 1. The actual Euler product "
        "E*A_j=zeta*R follows from x^3=y^3, xy=0 and 1+zeta^2=zeta in its "
        "finite order-two cell. Thus d11(RD^p)=zeta^2*B*h1*k^3*D^(p+1), "
        "not the printed unit 1. Its source is the nonzero Euler image of an "
        "11-cycle; incoming d2,d3 sources are empty and larger lengths have "
        "negative filtration. The finite S02 target is an outgoing cycle as "
        "the corresponding Euler image. Earlier incoming r3 has R*k^2*D^(p+1), "
        "a 3-cycle because P*h2=R*D and P is the Euler image of h2u_2sigma_j. "
        "Incoming r5 has U*h1*k^2*D^p, an injective primitive d3 source. "
        "Incoming r7 has B*h1^2*k*D^p. Use FN012 on h1*k*D^p (the D7 or D3 "
        "block times permanent g and an appropriate D8 translate), then multiply "
        "by E*h1: its factor 2 makes the target zero. This does not require a "
        "choice of c or b. Incoming r9 has C*k*D^p; its constant supports mixed "
        "d3 and its positive-j ideal is the image d3(U*h1^2*D^(p-1))=j*C*k*D^p. "
        "Parity excludes even incoming lengths. Therefore the S02 target is "
        "nonzero on E11. The Phi d9 targets occupy different D8 residue blocks. "
        "The two seeds give nonzero Tate differentials in positive filtration; "
        "permanent g and D8 unit transport there followed by Lemma 2.6 supplies "
        "forward-g HFPSS translates. No unrestricted HFPSS g cancellation, "
        "D4 unit, mixed coefficient assignment or late vanishing assertion is used."
    ),
}

_DERIVED_EVIDENCE = {
    "formal_diff_three_d5_tate_positive_derived": {
        "evidence_kind": "Tate-comparison-derived",
        "derived_from": ["FN-3I-002", "DKLLW24 Lemma 2.6", "DKLLW24 Tate method"],
        "derivation": (
            "In TateSS multiply the active FN-3I-002 equation by g^-2 D^4. "
            "The shift is (-8,-8), giving source (6,2) and target (5,7). "
            "g is permanent and invertible in TateSS; D^4 is a 5-cycle because "
            "d5(D^4)=4kD^4h2=0 (4h2=0), not because D^4 is permanent. "
            "Both endpoint filtrations are strictly positive, so the "
            "Tate/HFPSS differential comparison supplies this independently verified seed. "
            "The commented low-filtration corollary is not used as a proved premise."
        ),
        "comparison_source_filtration": 2,
        "comparison_target_filtration": 7,
        "comparison_translation": {"g_exponent": -2, "D_exponent": 4, "spectral_sequence": "tate"},
    },
    "formal_diff_two_d5_h2_sum_derived": {
        "evidence_kind": "Leibniz-derived",
        "derived_from": ["FN-2I-003", "DKLLW24 Tables 2 and 3",
                         "DKLLW24 Remark rmk:h2ext", "DKLLW24 C3 eigenspaces"],
        "derivation": (
            "Multiply FN-2I-003 by permanent h2. The actual hidden h2 extension "
            "in Remark rmk:h2ext gives x^2 h2^2=4kD; the associated-graded table "
            "alone is not the justification for an actual product. For y^2 h2^2, "
            "the graded zero and additive order restrict a hidden correction to the "
            "4kD line. Since D*y^2=h2^2, omega(D)=zeta^2*D and h2,k are fixed, "
            "y^2 h2^2 has weight zeta, whereas 4kD has weight zeta^2. Their "
            "difference is a Witt unit, so the correction is zero. Thus "
            "d5((x^2+y^2)h2 D u)=4k^2D^2u. "
            "Only the coefficient-four layer of I00 is the image, not the whole cell."
        ),
        "actual_product_certificate": {
            "status": "verified", "coefficient_ring": "W(F4)",
            "source_refs": ["DKLLW24 main.tex:913-918,970-983,1008-1039"],
            "nonzero_product": "x^2 h2^2=4kD", "zero_product": "y^2 h2^2=0",
            "possible_hidden_line": "4kD",
            "omega_weight_exponents": {"y^2 h2^2": 1, "4kD": 2},
            "weight_difference_mod_2": 1,
            "scope": "Actual E2 products; not a general lifting of associated-graded zero relations.",
        },
        "target_two_valuation": 2,
    },
    "formal_diff_two_d21_tate_positive_derived": {
        "evidence_kind": "Tate-comparison-derived",
        "derived_from": ["FN-2I-021", "DKLLW24 Lemma 2.6", "DKLLW24 Tate method"],
        "derivation": (
            "In TateSS multiply FN-2I-021 by the invertible permanent g^-1, g=kD^3. "
            "This gives d21(4k u)=h2 k^6 D^2 u at (-4,4)->(-5,25). "
            "Both endpoints have strictly positive filtration, so the stated "
            "Tate/HFPSS differential correspondence supplies this HFPSS seed. "
            "Only forward g translates are used after lifting; no negative-filtration "
            "HFPSS classes or global inverse-g period are introduced."
        ),
        "comparison_source_filtration": 4,
        "comparison_target_filtration": 25,
        "comparison_translation": {"multiplier": "g", "exponent": -1, "spectral_sequence": "tate"},
    },
    "formal_diff_two_d21_h2_low_derived": {
        "evidence_kind": "Finite-source-audit-and-product-detection",
        "derived_from": ["FN-2I-019", "FN-2I-004", "FN-2I-010", "FN-2I-011", "table_Q8.tex:407"],
        "derivation": (
            "H D4u at (35,1) has no earlier incoming map. Its d3,d5 are zero; r7,11,15,19 "
            "targets are empty; r9 target constant supports FN011 d9 and its j-tail died d3, "
            "so d9 squared excludes this map; r13 target is wholly d5-dead; r17 target is "
            "FN010's d9 image. Multiplication by permanent g detects FN019, forcing this "
            "nonzero low d21 onto the finite A line. The low I31 double is retained: unlike "
            "its forward-g image it is not an FN005 boundary. Only the odd constant maps."
        ),
        "source_two_valuation": 0, "target_components": {"I62X": 1, "I62Y": 1},
    },
    "formal_diff_two_d21_four_f0_derived": {
        "evidence_kind": "Finite-source-audit-and-product-detection",
        "derived_from": ["FN-2I-021", "FN-2I-004", "FN-2I-006", "FN-2I-017", "table_Q8.tex:409"],
        "derivation": (
            "S=4D5u has no incoming differential. d3,d5 vanish by the torsion of their targets; "
            "r7,15 target I33 is an FN006 d5 image; r11,19 I73 and its bo companion died d3; "
            "r9,17 target cells are empty; r13 Hk3D6 has odd layer FN004 d5-dead and double "
            "FN017 d9-dead. Thus S survives to E21. Its product g2*S is the D8 translate "
            "of FN021, which forces d21(S) nonzero by naturality. At the target (39,21) "
            "FN005 removed the double, leaving precisely the odd constant. This is a direct "
            "filtration-zero HFPSS argument, not cancellation of g or a blanket Tate lift. "
            "Only source two=2,j=0 maps; higher Witt layers and positive-j terms are not deleted."
        ),
        "source_two_valuation": 2, "target_two_valuation": 0,
        "filtration_zero_audit": True,
    },
    "formal_diff_two_d3_v6_derived": {
        "evidence_kind": "Leibniz-derived",
        "derived_from": ["DKLLW24 Table 8 row 1", "DKLLW24 Table 3", "FN-2I-001"],
        "derivation": (
            "d3(v1^6 u)=v1^4 h1^3 u+v1^6 d3(u). "
            "Table 3 gives x^2(v1^2 h1)=0, so the second term is zero "
            "even with an unspecified unit in d3(u). The target is "
            "j D h1^3 u, not the constant D h1^3 u printed in FN-2I-002."
        ),
        "source_component": "full",
        "target_component": "positive-j",
    },
    "formal_diff_two_d5_y2_derived": {
        "evidence_kind": "Leibniz-derived",
        "derived_from": ["FN-2I-004"],
        "derivation": "h2 is permanent: d5(h2*(h2 D u)) = h2*(k h2^2 D u); h2^2 = y^2 D.",
    },
}

_DERIVED_ENDPOINT_STYLES: dict[str, tuple[dict, dict]] = {
    "diff_three_d11_30": (
        {"e2_pattern": "S62", "j_order": 0, "two_valuation": 0},
        {"e2_pattern": "S11", "j_order": 0, "two_valuation": 0},
    ),
    "formal_diff_fn-3i-009_2": (
        {"e2_pattern": "S73", "j_order": 0, "two_valuation": 0},
        {"e2_pattern": "S22H", "j_order": 0, "two_valuation": 0},
    ),
    "formal_diff_two_d3_v6_derived": (
        {"e2_pattern": "I40", "j_order": 0, "two_valuation": 0},
        {"e2_pattern": "I33", "j_order": 1, "two_valuation": 0},
    ),
}
for _power, _ident in ((2, "formal_diff_fn-mix-006_1"), (6, "formal_diff_mixed_d11_r_D6_sibling")):
    _DERIVED_ENDPOINT_STYLES[_ident] = (
        {"e2_pattern": "S53", "two_valuation": 0, "j_order": 0},
        {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0},
    )
    _DERIVED_EVIDENCE[_ident] = {
        "evidence_kind": "corrected-omega-Euler-d11",
        "source_status": "independently-verified", "source_blockers": [],
        "withdrawn_dependencies": [], "machine_verification_pending": [],
        "derived_from": _VERIFIED_FORMAL_CERTIFICATES["FN-MIX-006"]["premises"][:],
        "derivation": _VERIFIED_FORMAL_CERTIFICATES["FN-MIX-006"]["derivation"],
        "paired_pattern_stem": 32,
        "coefficient_parameter": {
            "id": "mixed_d11_R", "symbol": r"\zeta^2", "value": 3, "domain": [3],
            "frobenius_power": 0, "fixed_reason": "verified omega-Euler source product",
        },
        "printed_source_formula": {
            "coefficient": 1, "status": "review-corrected",
            "source_ref": "formal_notes.tex:972-991; table_Q8.tex:527",
            "statement": r"d_{11}(x^3D^2u_{\sigma_i+2\sigma_j})=(x+y)h_1k^3D^3u_{\sigma_i+2\sigma_j}",
        },
        "coefficient_correction": {
            "status": "verified", "source_product_unit": 2, "rotated_premise_unit": 1,
            "normalized_target_unit": 3, "source_basis": "mixed source workspace before atlas Frobenius",
            "identity": "a_sigma_i*(x^2+zeta^2*y^2)=zeta*x^3*u_sigma_i",
            "equation": "d11(zeta*R D^p)=B h1 k^3 D^(p+1); hence d11(R D^p)=zeta^2*B h1 k^3 D^(p+1)",
        },
        "source_survival": {
            "status": "verified", "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
            "bidegree": [8 * _power - 3, 3], "e2_pattern": "S53",
            "cycle_premise": "Nonzero Euler image of the omega-transported verified FN-2I-009 11-cycle.",
            "incoming": "d2,d3 source cells empty; r>3 has negative source filtration.",
        },
        "target_survival": {
            "status": "verified", "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
            "bidegree": [8 * _power - 4, 14], "e2_pattern": "S02",
            "nonzero_condition": "independent of mixed_d5_A and mixed_d5_B",
            "cycle_premise": "Euler image of the verified FN-2I-009 E11 target.",
            "incoming": [
                {"page": 3, "source_bidegree": [8 * _power - 3, 11], "e2_pattern": "S53",
                 "reason": "R*k^2*D^(p+1) has d3=0 by P*h2=R*D and FN-MIX-004's Euler product."},
                {"page": 5, "source_bidegree": [8 * _power - 3, 9], "e2_pattern": "S51",
                 "reason": "U*h1*k^2*D^p is an injective primitive d3 source, not an empty E2 cell."},
                {"page": 7, "source_bidegree": [8 * _power - 3, 7], "e2_pattern": "S13",
                 "reason": "Multiply omega(FN-2I-012 on h1*k*D^p) by a_sigma_i*h1; 2h1=0, independently of c,b."},
                {"page": 9, "source_bidegree": [8 * _power - 3, 5], "e2_pattern": "S11",
                 "reason": "The constant supports d3(C)=2*zeta*U*k. Positive-j terms are d3(U*h1^2*D^(p-1))=j*C*k*D^p boundaries."},
            ],
            "forward_g": "Transport the nonzero Tate differential by g^q D^(8m), q>=0, then use positive-filtration comparison.",
        },
    }

for _power, _source_power in ((0, 6), (1, 7), (4, 2), (5, 3)):
    _ident = f"formal_diff_mixed_phi_d9_D{_power}"
    _even_source = _source_power % 2 == 0
    _source_fact = "DER-3I-D9-C" if _even_source else "DER-3I-EULER-D9-C"
    _parameter_id = f"three_sigma_d9_{'D' if _even_source else 'CD'}{_source_power}"
    _parameter_symbol = rf"\lambda_{{{_source_power}}}" if _even_source else rf"\nu_{{{_source_power}}}"
    _parameter_name = f"{'lambda' if _even_source else 'nu'}_{_source_power}"
    _source_differential = f"formal_diff_three_d9_c_D{_source_power}_{'derived' if _even_source else 'euler_derived'}"
    _DERIVED_ENDPOINT_STYLES[_ident] = (
        {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0},
        {"e2_pattern": "S73", "two_valuation": 0, "j_order": 0},
    )
    _DERIVED_EVIDENCE[_ident] = {
        "evidence_kind": "corrected-Phi-Euler-transport",
        "source_status": "independently-verified",
        "derived_from": [_source_fact,
                         "FN-3I-001", "FN-MIX-001",
                         "DKLLW24 Lemma 2.6", "formal_notes.tex:875", "Note/record/note.tex:762-779"]
                        + ([] if _even_source else ["DKLLW24 Table 8 rows 12-13"]),
        "coefficient_parameter": {
            "id": _parameter_id, "symbol": _parameter_symbol,
            "domain": [1, 2, 3], "value": None, "frobenius_power": 0,
            "source_parameter": {
                "workspace_id": "ws_3sigma_i", "parameter_id": _parameter_id,
                "differential_id": _source_differential, "page": 9,
            },
        },
        "coefficient_constraint": (
            f"This is the same {_parameter_name} as the ws_3sigma_i C D^{_source_power} map, "
            "not a mixed-local parameter or assignment. omega^2 supplies one zeta factor and "
            "a_sigma_j*C_k=zeta*B*h1 cancels it. A common invertible Thom coefficient cancels "
            "on the two finite j-annihilated lines. Resolve the source workspace's admitted "
            "premise and its coefficient constraints before using this linked map."
        ),
        "derivation": (
            "Write B=(x+y)u_mix, R=x^2*h1*u_mix, C_k=(h1+zeta^2*x*v1)u_3sigma_k, "
            "and B_k=(zeta^2*x+zeta*y)u_3sigma_k. "
            f"omega^2 of d9(C D^{_source_power})={_parameter_name} B*h1*k^2*D^{_source_power + 1} "
            f"gives d9(C_k D^{_source_power})=zeta*{_parameter_name} B_k*h1*k^2*D^{_source_power + 1}. "
            "Phi=N_C4^Q8(dbar)*u_4sigma_k*g^-1*a_H is a permanent invertible Tate class: "
            "the norm and u_4sigma_k are genuine permanent units, a_H is inverted in TateSS, "
            "and g=kD^3 is a permanent Tate unit. Phi has (stem,filtration)=(-16,0). "
            "Its inverse adds 16 to stem and preserves filtration; its E2 Thom expression "
            "is a common invertible scalar times D^2. Multiply the transported equation by "
            "permanent a_sigma_j=(zeta*x+zeta^2*y)u_sigma_j. The exact finite E2 products are "
            "a_sigma_j*C_k=zeta*B*h1 and a_sigma_j*B_k*h1=R: use xy=0 and yh1=v1*x^2. "
            "There is no higher 2-layer in either finite target cell, and j annihilates both "
            "products, so the common Thom unit cancels; no norm coefficient is chosen. "
            + ("Finally multiply by permanent D^-8. " if _power < 2 else "No final D translation is needed. ")
            + "All transported endpoints have positive filtration, so Lemma 2.6 and the Tate "
            "method return an HFPSS differential once its finite target survives. The target "
            "certificate below excludes every earlier incoming map independently of c and b. "
            "D^4 is not used as a 9-cycle; this is not an assertion that g is invertible on "
            "the whole HFPSS. This does not justify the historical d11 corollary. "
            + ("The source even C row is independently verified by the FN016 Euler image, "
               "the even-A d5 zero, finite target survival and its h1 lift. "
               "No Ck permanence, Jan29 argument or later three-sigma differential is used."
               if _even_source else
               "The source odd C row is independently detected by a_sigma_i and published "
               f"Table 8 row {12 if _source_power == 3 else 13}. Its source survives through "
               "E9 and its finite target is nonzero under the Euler detector. The relative "
               "omega^2 scalar is zeta for every D exponent, not just even exponents. "
               "No Ck permanence, Jan29 argument or later three-sigma differential is used.")
        ),
        "transport_certificate": {
            "status": "verified",
            "source_workspace_id": "ws_3sigma_i", "source_differential_id": _source_differential,
            "source_power": _source_power, "action": "omega^2",
            "phi_stem_shift": -16, "phi_filtration_shift": 0,
            "applied_inverse": True, "euler_multiplier": "a_sigma_j",
            "final_D_exponent": -8 if _power < 2 else 0,
            "comparison": "permanent-unit Tate transport with positive-filtration endpoints",
            "admission": "Verified source map and permanent-unit comparison; retain live source-parameter admission checks.",
        },
        "source_survival": {
            "status": "verified",
            "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
            "bidegree": [8 * _power, 2], "e2_pattern": "S02",
            "d3_target": {"bidegree": [8 * _power - 1, 5], "reason": "empty-E2-cell"},
            "d5_target": {"bidegree": [8 * _power - 1, 7],
                          "reason": "h1^3*k*D^m*u=d3(U*k*D^m); FN-MIX-001"},
            "d7_zero": "Image of the linked C_k D^n 9-cycle under permanent Phi^-1 and a_sigma_j.",
            "incoming": "No r>=3 incoming source at filtration 2-r; the d2 source is an empty E2 cell.",
        },
        "target_survival": {
            "status": "verified",
            "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
            "bidegree": [8 * _power - 1, 11], "e2_pattern": "S73",
            "nonzero_condition": "independent of mixed_d5_A and mixed_d5_B",
            "cycle_premise": "Permanent Phi/Euler image of the linked 3sigma E9 target.",
            "other_e2_direction": "S73V=U*h1^3*k^2*D^m supports the primitive d3 to h1^6*k^2*D^m; it is not the finite R line.",
            "incoming": [
                {"page": 3, "source_bidegree": [8 * _power, 8], "e2_pattern": "S00",
                 "reason": "v1^4*k^2*D^m*u has zero d3: it is the entire primitive image d3(U*h1*k*D^m), including local j_order=0, so d3^2=0. No bo permanence assertion is needed."},
                {"page": 5, "source_bidegree": [8 * _power, 6], "reason": "empty-E2-cell"},
                {"page": 7, "source_bidegree": [8 * _power, 4],
                 "e2_pattern": "S40",
                 "reason": "The odd U*k*D^m layer supports d3 to h1^3*k*D^m; its remaining even layer 2U*k*D^m is d3(CD^m)=2*zeta*U*k*D^m. The entire slot is zero on E4; FN-MIX-001."},
            ],
            "forward_g": "The same E2 support and d3-boundary exclusions hold after each nonnegative g translation.",
        },
        "historical_corrections": [
            {"source_ref": "Note/record/note.tex:765", "printed": "R k^7 D^9 at (43,17)",
             "corrected": "R k^7 D^9 at (43,31)"},
            {"source_ref": "Note/record/note.tex:771", "printed": "B_k h1 k^7 D^5 -> B_k h1 k^5 D^5",
             "problem": "This shifts (+8,-8), not Phi's (-16,0); the displayed equality is not used."},
        ],
        "source_blockers": [],
        "related_period_table": {
            "source_ref": f"REU Projects/table_Q8.tex:{521 if _even_source else 520}",
            "sector": "sigma_i+2sigma_j", "status": "independently-compared", "column": "Period",
            "printed_period_stem": 32,
            "interpretation": "Two separately verified D8 families reproduce the printed 32-stem pattern; D4 is not used as a permanent unit.",
            "authority": "Formula comparison only. Admission uses the linked pure source and finite Phi/Euler target proof.",
        },
    }
    _metadata = _DERIVED_EVIDENCE[_ident]
    _metadata.update({
        "withdrawn_dependencies": [], "machine_verification_pending": [],
        "verification_certificate": {
            "status": "verified", "method": "Permanent Phi transport and finite Euler target survival",
            "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
            "source_refs": ["DKLLW24 main.tex:488-524,833-878", "formal_notes.tex:875,881-901"],
            "premises": [_source_fact, "FN-MIX-001", "DKLLW24 Lemma 2.6",
                         "permanent norm, u_4sigma_k, g and Tate Euler a_H units"],
            "derivation": _metadata["derivation"],
            "source_survival": deepcopy(_metadata["source_survival"]),
            "target_survival": deepcopy(_metadata["target_survival"]),
        },
    })

for _power, _table_row in ((3, 12), (7, 13)):
    _ident = f"formal_diff_three_d9_c_D{_power}_euler_derived"
    _DERIVED_ENDPOINT_STYLES[_ident] = (
        {"e2_pattern": "S11", "two_valuation": 0, "j_order": 0},
        {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0},
    )
    _DERIVED_EVIDENCE[_ident] = {
        "evidence_kind": "Euler-detection-derived",
        "source_status": "independently-verified",
        "derived_from": ["FN-3I-001", f"DKLLW24 Table 8 row {_table_row}",
                         "DKLLW24 Tables 3 and 6", "DKLLW24 u_4sigma periodicity"],
        "source_blockers": [], "machine_verification_pending": [], "withdrawn_dependencies": [],
        "coefficient_parameter": {
            "id": f"three_sigma_d9_CD{_power}", "symbol": rf"\nu_{{{_power}}}",
            "domain": [1, 2, 3], "value": None, "frobenius_power": 0,
        },
        "coefficient_constraint": (
            "In each block C, B=h1*(x+y)u and T=h1*B share the coefficient of FN-3I-007/008: "
            "multiply C by the integer 9-cycle xh1, using C*xh1=T and B*xh1=2Uk. "
            "The pure-sector psi-fixed basis fixes each nonzero scalar to 1 independently; no later d23 is used."
        ),
        "derivation": (
            "Set C=(h1+xv1)u_3sigma and B=(x+y)h1u_3sigma. The Euler a_sigma is permanent "
            "and u_4sigma is an invertible permanent Thom class (main.tex:869-878). "
            "The 2-BSS relations h1*y=v1*x^2 and xy=0 give "
            "a_sigma*C=xh1*u_4sigma in the associated graded. Its total E2 cell (0,2) "
            "has only that finite F4 line and no higher 2-layer, so the product is nonzero "
            "up to a unit. Likewise a_sigma*B=x^2h1*u_4sigma in the finite j-annihilated line. "
            "For m=3 and m=7 separately, a_sigma*C*D^m=c*D^(m-1)*u_4sigma. "
            "Table 8 rows 12 and 13 give its nonzero d9 target x^2h1*k^2*D^(m+1)*u_4sigma. "
            "C*D^m reaches E9: d3(C)=0 and D is a 3-cycle; its d5 target is empty, "
            "and its d7 target is a known d3 boundary. At E9 its unique finite target "
            "B*k^2*D^(m+1) maps nontrivially under a_sigma to the displayed integer target. "
            "Naturality therefore forces the displayed nonzero d9, without any vanishing-line "
            "or partial-quotient g-injectivity assumption. D^4 is not used as a 9-cycle."
        ),
        "source_survival": {"zero_d3_fact": "FN-3I-001", "d5_target": "empty-E2-cell",
                            "d7_target": "d3-boundary"},
        "detector": {"multiplier": "a_sigma_i", "target_workspace": "integer-times-u_4sigma_i",
                     "table_number": 8, "table_row": _table_row},
    }
    _DERIVED_EVIDENCE[_ident]["verification_certificate"] = {
        "status": "verified", "method": "Euler products, finite target survival and h1 detection",
        "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "D_power": _power,
        "source_refs": [f"DKLLW24 Table 8 row {_table_row}", "DKLLW24 main.tex:868-878", "formal_notes.tex:678-705"],
        "premises": ["FN-3I-001", f"DKLLW24 Table 8 row {_table_row}", "permanent u_4sigma_i",
                     "DER-3I-D5-C-zero", "DER-3I-D7-C-zero", "psi-fixed pure sigma_i basis"],
        "no_withdrawn_premise": True,
        "derivation": _DERIVED_EVIDENCE[_ident]["derivation"],
    }
_EULER_CHAIN_COEFFICIENTS = {}
for _power, _chain_rows in (
    (3, ("diff_three_d9_25", "diff_three_d9_25b")),
    (7, ("formal_diff_three_d9_t_D7_sibling", "formal_diff_three_d9_b_D7_sibling")),
):
    for _ident in _chain_rows:
        _EULER_CHAIN_COEFFICIENTS[_ident] = {
            "coefficient_parameter": {
                "id": f"three_sigma_d9_CD{_power}", "symbol": rf"\nu_{{{_power}}}",
                "domain": [1, 2, 3], "value": None, "frobenius_power": 0,
            },
            "paired_pattern_stem": 32,
            "derived_from": _THREE_ODD_D9_CERTIFICATE["premises"][:],
            "coefficient_constraint": (
                "FN007, its h1 lift FN008 and the Euler-detected C row have scalar 1 in each "
                "psi-fixed pure-sector block. The two blocks are proved separately modulo D8; "
                "no coefficient equality or nonzero map is inferred from a later d23."
            ),
        }
        _DERIVED_ENDPOINT_STYLES[_ident] = (
            {"e2_pattern": "S13" if _ident in {"diff_three_d9_25", "formal_diff_three_d9_t_D7_sibling"} else "S02",
             "two_valuation": 0, "j_order": 0},
            {"e2_pattern": "S40" if _ident in {"diff_three_d9_25", "formal_diff_three_d9_t_D7_sibling"} else "S73",
             "two_valuation": 1 if _ident in {"diff_three_d9_25", "formal_diff_three_d9_t_D7_sibling"} else 0, "j_order": 0},
        )
        if _power == 7:
            _DERIVED_EVIDENCE[_ident] = {
                "evidence_kind": "independently-verified-Euler-pattern-sibling",
                "derived_from": ["FN-3I-007" if "_t_" in _ident else "FN-3I-008"],
                "derivation": (
                    "Independently use the verified D7 block of FN-2I-011, its Euler image, "
                    "the finite Witt-two target survival and h1 detection. This is a second "
                    "D8 family, not transport by a permanent D4."
                ),
            }
for _power in (4, 8):
    _ident = f"formal_diff_three_d9_b_D{_power}_euler_derived"
    _DERIVED_ENDPOINT_STYLES[_ident] = (
        {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0},
        {"e2_pattern": "S73", "two_valuation": 0, "j_order": 0},
    )
    _DERIVED_EVIDENCE[_ident] = {
        "evidence_kind": "published-13-cycle-detection",
        "source_status": "independently-verified",
        "derived_from": ["FN-3I-007", "FN-3I-001", "FN-3I-005", "FN-3I-006",
                         "DKLLW24 D^-1 h1 13-cycle", "DKLLW24 hidden h1 multiplication"],
        "source_blockers": [], "machine_verification_pending": [], "withdrawn_dependencies": [],
        "coefficient_parameter": {
            "id": f"three_sigma_d9_BD{_power}", "symbol": rf"\mu_{{{_power}}}",
            "domain": [1, 2, 3], "value": None, "frobenius_power": 0,
        },
        "coefficient_constraint": (
            "The published L=D^-1 h1 detector forces this map independently in each block. "
            "Its nonzero pure-sector F4 coefficient is 1 in the psi-fixed basis."
        ),
        "derivation": (
            "Write B=(x+y)h1u, T=h1B, R=x^2h1u, U=v1^2u and L=D^-1*h1. "
            "DKLLW main1694-1702 proves L is a 13-cycle. B D^p reaches E9: its d3 target "
            "is empty, its d5 target is a primitive d3 boundary, and its d7 target "
            "a*k^2*D^(p+1) is an FN005/FN006 d5 source. There is no earlier incoming. "
            f"For p={_power}, L*(B D^p)=T D^(p-1) supports verified FN007. Its target W="
            "2U*k^3*D^p is nonzero on E9 by the independent finite incoming-source check. "
            "The only surviving finite target of B D^p is R*k^2*D^(p+1), whose L product "
            "is W by the actual hidden h1 multiplication. Naturality forces its nonzero d9. "
            "The same-cell S73V has already supported primitive d3. No Ck permanence, "
            "d11, Jan29 proof, high-filtration cutoff or cancellation of g is used."
        ),
        "detector": {"multiplier": "D^-1 h1", "cycle_through": 13,
                     "source_power": _power - 1, "fact_id": "FN-3I-007"},
    }
    _DERIVED_EVIDENCE[_ident]["verification_certificate"] = {
        **deepcopy(_THREE_ODD_D9_CERTIFICATE), "D_power": _power,
        "premises": _DERIVED_EVIDENCE[_ident]["derived_from"][:],
        "derivation": _DERIVED_EVIDENCE[_ident]["derivation"],
    }
_MIXED_A_PARAMETER = {
    "id": "mixed_d5_A", "symbol": "c", "domain": [1, 2, 3],
    "value": None, "frobenius_power": 0,
}
_MIXED_B_PARAMETER = {
    "id": "mixed_d5_B", "symbol": "b", "domain": [1, 2, 3],
    "value": None, "frobenius_power": 0,
}
_MIXED_B_NONZERO_CERTIFICATE = {
    "id": "DER-MIX-D5-B-NONZERO", "status": "verified",
    "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
    "parameter_id": "mixed_d5_B", "domain": [1, 2, 3], "value": None,
    "premises": ["DER-MIX-EULER-H2-cycle", "FN-MIX-001", "FN-MIX-004",
                 "FN-MIX-002 nonzero c", "DKLLW24 Table 8 d9(h1D2)", "DKLLW24 Table 6"],
    "source_refs": ["formal_notes.tex:881-901,934-970",
                    "DKLLW24 main.tex:943,949,1036-1039,1179-1187,1895"],
    "target_space": {
        "bidegree": [-2, 6], "basis": ["kP", "kQ"],
        "general_map": "k(alpha P+beta Q)", "alpha": 0,
        "completed_ideal": "d3(U h1^3 D^-1)=j kQ; all positive-j multiples are included.",
        "alpha_exclusion": (
            "P=B h2 and Q h2=0. The independent FN-MIX-004 equation and d5(D)=kDh2 "
            "give d5(P)=0, using D invertible on E5 only. Thus alpha*x^3kDu=0. "
            "This finite target at (1,7) is nonzero on E5; its d3 incoming cell (2,4) is empty."
        ),
    },
    "counterfactual": {
        "b": 0, "target_bidegree": [15, 11], "target": "W=Rk^2D^3",
        "B_survival": (
            "B=(x+y)u has filtration 1, hence no earlier incoming. Its d3/d7 targets "
            "are empty, and d5(B)=0 is the counterfactual. Its d9 finite A target "
            "supports the independently nonzero c d5; the other completed-series "
            "direction is already a primitive d3 image. Therefore d9(B)=0."
        ),
        "W_outgoing": (
            "In this branch B is a 9-cycle and xh1k^2D^3 is the integer Table 8 d9 "
            "target. Their exact product W has no earlier outgoing differential."
        ),
        "contradiction": (
            "V=B h1D^2 is the certified Euler image of h1D^2u_2sigma_j, so d9(V)=0. "
            "Leibniz and Table 8 give d9(V)=B*xh1k^2D^3=Rk^2D^3=W, "
            "nonzero by the complete earlier incoming inventory. Thus b is nonzero."
        ),
    },
    "incoming_inventory": [
        {"page": 3, "source_bidegree": [16, 8], "pattern": "S00", "disposition": "zero-outgoing",
         "reason": "The entire module is the primitive image d3(Uh1kD2)=v1^4k^2D2u; apply d3 squared zero."},
        {"page": 5, "source_bidegree": [16, 6], "disposition": "empty-E2-cell"},
        {"page": 7, "source_bidegree": [16, 4], "pattern": "S40", "disposition": "absent-after-d3",
         "reason": "The odd UkD2 layer supports primitive d3; the two-layer is d3(CD2)=2zeta UkD2. Higher two-layers vanish; all j multiples are included."},
    ],
    "even_pages": "Empty by total-degree parity.",
    "interpretation": "This proves b in F4*, not b=1. The coupled P+bQ map still requires the exact relative unit before quotienting.",
    "withdrawn_premises_used": [],
}
_DERIVED_ENDPOINT_STYLES["formal_diff_mixed_d5_a_D2_leibniz_derived"] = (
    {"e2_pattern": "S62", "two_valuation": 0, "j_order": 0},
    {"e2_pattern": "S13", "two_valuation": 0, "j_order": 0},
)
_DERIVED_EVIDENCE["formal_diff_mixed_d5_a_D2_leibniz_derived"] = {
    "evidence_kind": "coefficient-linked-Leibniz-family",
    "derived_from": ["FN-MIX-003", "DKLLW24 Table 8 row 2", "DKLLW24 Table 6"],
    "coefficient_parameter": {**_MIXED_A_PARAMETER, "affine_offset": 1, "expression": "(c+1)"},
    "coefficient_constraint": "The same c occurs in FN-MIX-002/003. The even coefficient is c+1, not an independent nonzero unit.",
    "coefficient_branches": [{"c": 1, "even": 0}, {"c": 2, "even": 3}, {"c": 3, "even": 2}],
    "derivation": (
        "Set A=(x^2+y^2)u and T=(x+y)h1^2u. Table 6 gives Ah2=T. "
        "The cell (1,3) is a finite F4 line with no higher 2-layer or positive-j tail, "
        "so this product has no hidden correction. Thus d5(AD^2)=d5(AD)D+AD*d5(D) "
        "=(c+1)TkD^2. No zero or nonzero choice of c+1 is made before c is resolved. "
        "The E2 Thom isomorphism does not transport the ordinary sigma E5 coefficient "
        "because u_2sigma_j itself supports d3."
    ),
    "source_blockers": ["The Euler annihilator proves only c is nonzero. The notes do not determine its exact value."],
}

for _power in (2, 6):
    _ident = f"formal_diff_mixed_d9_p_D{_power}_euler_derived"
    _DERIVED_ENDPOINT_STYLES[_ident] = (
        {"e2_pattern": "S22Y", "two_valuation": 0, "j_order": 0},
        {"e2_pattern": "S13", "two_valuation": 0, "j_order": 0},
    )
    _DERIVED_EVIDENCE[_ident] = {
        "evidence_kind": "conditional-Euler-image-derived",
        "source_status": "derived-review",
        "derived_from": ["FN-2I-016", "FN-MIX-001", "FN-MIX-003",
                         "DER-MIX-D5-A-EVEN", "DKLLW24 Lemma 5.2", "DKLLW24 Table 6"],
        "coefficient_parameter": {
            "id": f"mixed_d9_PD{_power}", "symbol": r"\zeta^2",
            "domain": [3], "value": 3, "frobenius_power": 0,
            "fixed_reason": "Verified FN-2I-016 has pure-sector coefficient 1; omega contributes the target/source ratio zeta^2 before exact Euler multiplication.",
        },
        "coefficient_condition": {
            "parameter_id": "mixed_d5_A", "equals": 1, "otherwise": "zero-euler-image",
            "source_ref": "formal_notes.tex:520-526,881-932; DKLLW24 Table 6; Leibniz and the finite E9 target certificate",
            "derivation": (
                "The unique finite incoming d5 has coefficient c+1. Thus c=1 leaves the "
                "E9 target nonzero, while c=zeta or zeta^2 makes it a d5 boundary. "
                "On those latter branches the Euler-image equation is zero and does not remove P D^m. "
                "Test c in the source-field assignment, without Frobenius-conjugating the condition. "
                "An unresolved c does not certify a zero or nonzero map."
            ),
        },
        "coefficient_constraint": (
            f"gamma_{_power}=zeta^2*lambda_{_power}=zeta^2: verified FN-2I-016 and the "
            "psi-fixed pure basis give lambda=1 in each independently proved m=2,6 block. "
            "The ratio of omega target/source units is zeta^(2(m+1))/zeta^(2m)=zeta^2. "
            "Exact Euler products P=a_sigma_i*h2*u_2sigma_j and T=a_sigma_i*h1^2*u_2sigma_j "
            "introduce no new scalar. This fixes gamma, not c or b; no D4 cycle is asserted."
        ),
        "paired_pattern_stem": 32,
        "conditional_statement": rf"c=1\Longrightarrow d_9(PD^{_power})=\zeta^2Tk^2D^{_power + 1}",
        "derivation": (
            "Set u=u_(sigma_i+2sigma_j), B=(x+y)u, P=B h2 and T=B h1^2. "
            "Transport the m=2 or m=6 FN-2I-016 equation to 2sigma_j by omega, then multiply "
            "by permanent a_sigma_i. omega fixes h1,h2,k and sends D to zeta^2 D, giving "
            "gamma_m=zeta^2 because the verified pure-source coefficient lambda_m is 1. "
            "This supplies an Euler-image equation, not an "
            "unconditional nonzero differential. The source reaches E9 as that Euler image "
            "and has no earlier incoming differential: r>=3 would have negative source filtration, "
            "while the d2 incoming cell is empty by E2 parity. "
            "The target is a 9-cycle as the Euler image of the FN-2I-016 target. "
            "Its d3 and d7 incoming cells are empty; its d5 incoming cell consists of "
            "A k D^(m+1) and U h1^2 k D^m, with A=(x^2+y^2)u and U=v1^2u. "
            "The U direction is a d3 source; the finite A direction has d5=(c+1) times this target. "
            "Even-page incoming sources are empty by E2 parity. Therefore the target survives "
            "precisely on the c=1 branch under these stated premises. D^4 is not used as a 9-cycle: "
            "the two independently sourced blocks each repeat by permanent D^8 and forward g=kD^3. "
            "No vanishing-line truncation or partial-runtime absence of an arrow is used as proof."
        ),
        "premise_transport_certificate": {
            "status": "verified-equation", "premise": "FN-2I-016", "action": "omega",
            "source_sector": "2sigma_i", "target_sector": "2sigma_j",
            "multiplier": "a_sigma_i", "source_ref": "formal_notes.tex:520-526; DKLLW24 Lemma 5.2",
            "pure_source_coefficient": 1, "target_source_unit_ratio": 3, "mixed_coefficient": 3,
            "exact_products": {
                "source": "a_sigma_i*h2*u_2sigma_j=P=(yh2+xh1v1)u; the base finite P summand is j-annihilated, excluding an additional Q or jQ correction.",
                "target": "a_sigma_i*h1^2*u_2sigma_j=T=(x+y)h1^2u; its cell is one finite F4 line without a higher two-layer.",
                "source_refs": ["DKLLW24 main.tex:943,1183-1189", "formal_notes.tex:939-940"],
                "thom_unit": "The same transported Thom unit appears at source and target and cancels in the ratio.",
            },
            "admission": "The source equation and exact Euler transport are verified. This does not admit the unresolved c/b hypotheses or assert a nonzero mixed target on every branch.",
        },
        "source_survival": {
            "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
            "bidegree": [8 * _power + 2, 2], "e2_pattern": "S22Y",
            "cycle_premise": "Euler image of the FN-2I-016 E9 source",
            "earlier_incoming": "r>=3: negative-filtration sources; d2: empty-E2-cell by parity",
        },
        "target_survival": {
            "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
            "bidegree": [8 * _power + 1, 11], "e2_pattern": "S13",
            "cycle_premise": "Euler image of the FN-2I-016 E9 target",
            "incoming": [
                {"page": 3, "source_bidegree": [8 * _power + 2, 8], "exclusion": "empty-E2-cell"},
                {"page": 5, "source_bidegree": [8 * _power + 2, 6],
                 "directions": [
                     {"e2_pattern": "S62", "representative": f"A k D^{_power + 1}", "target_coefficient": "c+1"},
                     {"e2_pattern": "S62V", "representative": f"U h1^2 k D^{_power}",
                      "exclusion": "d3-source", "fact_id": "FN-MIX-001"},
                 ]},
                {"page": 7, "source_bidegree": [8 * _power + 2, 4], "exclusion": "empty-E2-cell"},
            ],
            "even_pages": "empty by E2 parity", "nonzero_condition": "c=1",
        },
        "source_blockers": [
            "Unresolved c blocks the nonzero/zero decision; gamma is fixed by the verified omega/Euler equation and is not a further free parameter.",
            "When c is zeta or zeta^2 the target is already a d5 boundary; this image does not remove the source.",
        ],
    }

for _power in (2, 6):
    _ident = f"formal_diff_mixed_d9_q_D{_power}_derived"
    _p_evidence = _DERIVED_EVIDENCE[f"formal_diff_mixed_d9_p_D{_power}_euler_derived"]
    _DERIVED_ENDPOINT_STYLES[_ident] = (
        {"e2_pattern": "S22H", "two_valuation": 0, "j_order": 0},
        {"e2_pattern": "S13", "two_valuation": 0, "j_order": 0},
    )
    _DERIVED_EVIDENCE[_ident] = {
        "evidence_kind": "finite-target-injection-derived", "source_status": "derived-review",
        "derived_from": [f"DER-MIX-D9-P-D{_power}", "FN-MIX-001", "FN-MIX-005",
                         "FN-MIX-005-Q-zero", "DKLLW24 Tables 3 and 6"],
        "coefficient_parameter": {
            **deepcopy(_p_evidence["coefficient_parameter"]),
            "inverse_parameter_id": "mixed_d5_B", "expression": r"\zeta^2/b",
        },
        "coefficient_condition": deepcopy(_p_evidence["coefficient_condition"]),
        "coefficient_constraint": (
            "The Q coefficient is gamma_m/b=zeta^2/b, not a new independent unit. "
            "Form the quotient in the source field before any atlas Frobenius action. "
            "Requires the explicit nonzero-b premise of FN-MIX-005."
        ),
        "conditional_statement": rf"c=1\Longrightarrow d_9(QD^{_power})=(\zeta^2/b)Tk^2D^{_power + 1}",
        "paired_pattern_stem": 32,
        "derivation": (
            "Set B=(x+y)u, P=B h2, Q=(h1^2+xh1v1)u and T=B h1^2. "
            "For m=2 or 6, FN-MIX-005 gives g(P+bQ)D^m=d5(BD^(m+3)); "
            "hence g*(d9(PD^m)+b*d9(QD^m))=0. The sole possible target is the finite "
            "T k^2 D^(m+1) line. When c=1, multiplication by g is injective on this line: "
            "at (8m+21,15), incoming d3/d7 sources are empty, while the d5 source consists "
            "of A k^2 D^(m+4) with coefficient c+1 and a previously killed S62V direction. "
            "Thus d9(QD^m)=(gamma_m/b)T k^2 D^(m+1). For c!=1 the target is already a "
            "d5 boundary and the Euler-image equation is zero. No global inverse-g assumption, "
            "vanishing-line argument or independent unit choice is used. D^4 is not used as a 9-cycle."
        ),
        "source_survival": {
            "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
            "bidegree": [8 * _power + 2, 2], "e2_pattern": "S22H", "j_order": 0,
            "d3": "Q=C h1 and d3(C)=2*zeta*U*k, so d3(Q)=0 since 2h1=0; D is a 3-cycle.",
            "d5": "FN-MIX-005-Q-zero, using nonzero b and d5^2; Qh2=0 permits each D translate.",
            "d7_target": {
                "bidegree": [8 * _power + 1, 9], "representative": f"C k^2 D^{_power + 1}",
                "constant": "FN-MIX-001 d3 source",
                "positive_j": f"d3(U h1^2 k D^{_power})=j C k^2 D^{_power + 1}",
            },
            "earlier_incoming": "r>=3: negative-filtration sources; d2: empty-E2-cell by parity",
        },
        "target_survival": deepcopy(_p_evidence["target_survival"]),
        "g_injection_certificate": {
            "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
            "status": "review", "target_bidegree": [8 * _power + 1, 11],
            "g_target_bidegree": [8 * _power + 21, 15], "condition": "c=1",
            "incoming": [
                {"page": 3, "source_bidegree": [8 * _power + 22, 12], "exclusion": "empty-E2-cell"},
                {"page": 5, "source_bidegree": [8 * _power + 22, 10],
                 "finite_source": f"A k^2 D^{_power + 4}", "target_coefficient": "c+1",
                 "other_direction": "S62V d3-source"},
                {"page": 7, "source_bidegree": [8 * _power + 22, 8], "exclusion": "empty-E2-cell"},
            ],
            "even_pages": "empty by E2 parity", "cycle_premise": "g times the P-row Euler-image target",
        },
        "source_blockers": [
            "Conditional on the P Euler-image premises and the nonzero-b FN-MIX-005 hypothesis; no admission is implied.",
            "Only the constant S22H direction is this row's source. Positive-j directions have a separate zero certificate.",
        ],
    }

for _power in (2, 6):
    for _column, _pattern, _target_pattern in (("p", "S22Y", "S13"), ("q", "S22H", "S13"), ("c", "S11", "S02")):
        _ident = f"formal_diff_three_d9_{_column}_D{_power}_derived"
        _DERIVED_ENDPOINT_STYLES[_ident] = (
            {"e2_pattern": _pattern, "two_valuation": 0, "j_order": 0},
            {"e2_pattern": _target_pattern, "two_valuation": 0, "j_order": 0},
        )
        _DERIVED_EVIDENCE[_ident] = {
            "evidence_kind": "Euler-image-and-finite-target-injection" if _column != "c" else "h1-injective-lift-derived",
            "derived_from": ["FN-2I-016", "FN-3I-001", "FN-3I-002", "FN-3I-006",
                             "DER-3I-D5-A-EVEN", "DKLLW24 Lemma 5.2", "DKLLW24 Tables 3 and 6"],
            "source_status": "independently-verified", "source_blockers": [],
            "machine_verification_pending": [], "withdrawn_dependencies": [],
            "coefficient_parameter": {"id": f"three_sigma_d9_D{_power}", "symbol": rf"\lambda_{{{_power}}}",
                                      "domain": [1, 2, 3], "value": None, "frobenius_power": 0},
            "derivation": (
                "Set A=(x^2+y^2)u, B=(x+y)u, C=(h1+xv1)u, P=Bh2, Q=Ch1, R=Bh1, T=Bh1^2. "
                "The actual product Ah2=T lies in a finite order-two line, so the mod-2 identity "
                "has no hidden Witt correction. FN002 d5(AD)=kTD and d5(D)=kDh2 give d5(A)=0 "
                "using D invertible on E5; 2T=0 gives every even-A zero. Multiply FN016 by "
                "permanent a_sigma_i to obtain d9(PD^m)=Z=T k^2 D^(m+1). Its incoming d3/d7 "
                "sources are empty, while the sole finite d5 source g*A D^(m-2) has zero d5; "
                "the other S62V direction has already supported primitive d3. Thus Z survives. "
                "The same enumeration for gZ replaces that source by g^2*A D^(m-2), proving "
                "g is injective on this particular target line. FN006 makes g(P+Q)D^m a d5 "
                "boundary; hence d9(QD^m)=Z. First certify C survives: d3(C)=0, its d5 target "
                "is empty, and its d7 target S00 is entirely hit by primitive d3, including "
                "local j_order=0. Then Q=h1*C and h1*(Rk^2D^(m+1))=Z force C's nonzero d9. "
                "This uses no Ck permanence, Jan29 proof or later three-sigma differential. "
                "Each m is recorded separately modulo permanent D^8; D^4 is not used as a 9-cycle."
            ),
            "paired_pattern_stem": 32,
            "verification_certificate": {
                "status": "verified",
                "method": "Euler image, finite g-injection and h1 lift",
                "source_refs": ["formal_notes.tex:520-526,678-762", "DKLLW24 Tables 3 and 6; Lemma 5.2"],
                "premises": ["FN-2I-016", "FN-3I-001", "FN-3I-002", "FN-3I-006",
                             "DER-3I-D5-A-EVEN", "psi-fixed pure sigma_i basis"],
                "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
                "D_power": _power, "no_withdrawn_premise": True,
                "target_injection": "Only the specified finite E9 line; not global cancellation of g.",
                "forward_g": "Low P+Q kernel is already an FN006 boundary after multiplication by g; high j tails die by d3.",
            },
            "g_injection_certificate": {
                "status": "verified", "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
                "target_bidegree": [8 * _power + 1, 11], "g_target_bidegree": [8 * _power + 21, 15],
                "incoming_d3": "empty-E2-cell", "incoming_d7": "empty-E2-cell",
                "incoming_d5": {"source_bidegree": [8 * _power + 22, 10],
                                "finite_source": f"g^2 A D^{_power - 2}",
                                "zero_certificate": "DER-3I-D5-A-EVEN", "other_direction": "S62V d3-source"},
            },
        }
        if _column == "p":
            _DERIVED_EVIDENCE[_ident].update({
                "euler_image_certificate": {
                    "status": "verified", "equation_only": False, "target_nonzero": "verified",
                    "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
                    "premises": ["FN-2I-016", "FN-3I-002", "DER-3I-D5-A-EVEN",
                                 "DKLLW24 Lemma 5.2", "formal_notes.tex:734-739"],
                    "source_bidegree": [8 * _power + 2, 2], "target_bidegree": [8 * _power + 1, 11],
                    "statement": f"d9(PD^{_power})=[T k^2 D^{_power + 1}]_E9",
                    "source_survival": "Euler image of the FN-2I-016 E9 source; earlier incoming sources have negative filtration or an empty d2 source cell.",
                    "scope_limit": "Certifies this nonzero E9 map with the finite incoming-source enumeration. No Ck permanent-cycle or Jan29 premise is used.",
                },
                "target_survival": {
                    "status": "verified", "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
                    "bidegree": [8 * _power + 1, 11],
                    "incoming_d3": "empty-E2-cell", "incoming_d7": "empty-E2-cell",
                    "incoming_d5": {"source_bidegree": [8 * _power + 2, 6],
                                    "finite_source": f"A k D^{_power + 1}",
                                    "finite_source_identity": f"g A D^{_power - 2}",
                                    "zero_certificate": "DER-3I-D5-A-EVEN",
                                    "other_direction": "S62V, already a d3 source"},
                    "derivation": "Independently verified FN002 gives d5(AD)=kTD. Actual Ah2=T and Leibniz give the required even-A zero; S62V is a primitive d3 source.",
                },
            })
        _DERIVED_EVIDENCE[_ident]["verification_certificate"]["derivation"] = _DERIVED_EVIDENCE[_ident]["derivation"]
for _power, _source_pattern, _target_pattern in (
    (1, "I51", "I00"), (2, "I62V", "I11"), (3, "I73V", "I22H"),
):
    _derived_id = f"formal_diff_two_d3_h1_{_power}_derived"
    _DERIVED_ENDPOINT_STYLES[_derived_id] = (
        {"e2_pattern": _source_pattern, "j_order": 0, "two_valuation": 0},
        {"e2_pattern": _target_pattern, "j_order": 1, "two_valuation": 0},
    )
    _DERIVED_EVIDENCE[_derived_id] = {
        "evidence_kind": "Leibniz-derived",
        "derived_from": ["DKLLW24 Corollary 4.11", "DKLLW24 Table 3", "FN-2I-001"],
        "derivation": (
            f"d3(v1^2 h1^{_power} u)=h1^{_power + 3} u: the Thom extra term "
            "is x^2(v1^2 h1)h1^n u=0 by Table 3, independently of its unit. "
            "h1^4=k v1^4=j kD, hence the target is the positive-j ideal "
            "and its constant coefficient remains. This is independent of FN-2I-002."
        ),
        "source_component": "full",
        "target_component": "positive-j",
    }
for _key, _fact in (("three", "FN-3I-001"), ("mixed", "FN-MIX-001")):
    for _power, _source_pattern, _target_pattern in (
        (1, "S51", "S00"), (2, "S62V", "S11"), (3, "S73V", "S22H"),
    ):
        _derived_id = f"formal_diff_{_key}_d3_h1_{_power}_derived"
        _DERIVED_ENDPOINT_STYLES[_derived_id] = (
            {"e2_pattern": _source_pattern, "j_order": 0, "two_valuation": 0},
            {"e2_pattern": _target_pattern, "j_order": 0 if _power == 1 else 1, "two_valuation": 0},
        )
        _DERIVED_EVIDENCE[_derived_id] = {
            "evidence_kind": "Leibniz-derived",
            "derived_from": [_fact],
            "derivation": (
                f"Multiply d3(v1^2 u)=h1^3 u by permanent h1^{_power}. "
                "Table 3 gives h1^4=k v1^4 and v1^4 xh1=0. "
                "Thus h1^6 u=j*kD*(h1^2+xh1v1)u: at filtration 6 "
                "the positive-j ideal of S22H is a d3 boundary, not its constant line. "
                "S00 already starts with v1^4 D^-1 u, so its local target j_order is zero."
            ),
            "source_component": "full",
            "target_component": "full" if _power == 1 else "positive-j",
        }

ZERO_AND_PERMANENT_CLAIMS = (
    ("FN-2I-003-zero", "ws_2sigma_i", "zero-differential", r"d_5(\{x^2+y^2\}D^2u_{2\sigma_i})=0", (14, 2), 5, "admitted", "formal_notes.tex:334-353"),
    ("FN-2I-005-zero", "ws_2sigma_i", "zero-differential", r"d_5(2D^2u_{2\sigma_i})=0", (16, 0), 5, "verified", "formal_notes.tex:382-399; transfer and 4h2=0"),
    ("DER-2I-TRANSFER-TWO-cycle", "ws_2sigma_i", "permanent-cycle", r"2u_{2\sigma_i}\text{ supports no differential}", (0, 0), 2, "verified", "DKLLW24 main.tex:520; RO-graded transfer from ker(sigma_i)=C4<i>"),
    ("FN-3I-001-zero", "ws_3sigma_i", "zero-differential", r"d_3(\{h_1+xv_1\}u_{3\sigma_i})=0", (1, 1), 3, "verified", "formal_notes.tex:678-700"),
    ("FN-3I-010-pc", "ws_3sigma_i", "permanent-cycle", r"\{h_1+xv_1\}ku_{3\sigma_i}\text{ is permanent}", (-3, 5), 2, "source-proved", "formal_notes.tex:799-809"),
    ("DER-3I-TATE-W-cycle", "ws_3sigma_i", "permanent-cycle", r"2v_1^2Du_{3\sigma_i}\text{ supports no differential}", (12, 0), 2, "verified", "DKLLW24 Table 9; Lemma 2.6; main.tex:937-949,1094-1111,2365-2378,2751-2756"),
    ("DER-3I-EULER-XD5-cycle", "ws_3sigma_i", "permanent-cycle", r"x^3D^5u_{3\sigma_i}\text{ supports no differential}", (37, 3), 2, "verified", "BBHS20 Propositions 5.21,5.24,5.27,5.28 and Tables 4/5; DKLLW24 Table 8 and Corollary 2.23; index-two Euler cofiber"),
    ("DER-3I-EULER-CD5-cycle", "ws_3sigma_i", "permanent-cycle", r"(h_1+xv_1)D^5u_{3\sigma_i}\text{ supports no differential}", (41, 1), 2, "verified", "BBHS20 Propositions 5.21,5.24,5.27,5.28 and Tables 4/5; DKLLW24 Table 8 and Tate method; adjusted Euler preimage"),
    ("FN-2I-004-derived-zero", "ws_2sigma_i", "zero-differential", r"d_5(y^2Du_{2\sigma_i})=0", (6, 2), 5, "verified-pattern", "formal_notes.tex:280,357-379; DKLLW24 Corollary 4.15; Leibniz rule"),
    ("FN-2I-003-h2-zero", "ws_2sigma_i", "zero-differential", r"d_5(\{x^2+y^2\}h_2D^2u_{2\sigma_i})=0", (17, 3), 5, "admitted", "formal_notes.tex:334-353; h2 multiplication"),
    ("FN-2I-004-h2-square-zero", "ws_2sigma_i", "zero-differential", r"d_5(h_2^3u_{2\sigma_i})=0", (9, 3), 5, "verified-pattern", "formal_notes.tex:357-379; DKLLW24 Table 3 h2^4=0"),
    ("FN-2I-003-euler-h2-zero", "ws_2sigma_i", "zero-differential", r"d_{21}(\{x^2+y^2\}h_2u_{2\sigma_i})=0", (1, 3), 21, "admitted", "formal_notes.tex:343; DKLLW24 lemma:gPC (main.tex:1334-1342)"),
    ("FN-3I-003-even-zero", "ws_3sigma_i", "zero-differential", r"d_5(\{yh_2+xh_1v_1\}u_{3\sigma_i})=0", (2, 2), 5, "verified", "formal_notes.tex:730-742; DKLLW24 Tables 6 and 8; Leibniz rule"),
    ("FN-3I-001-Q-zero", "ws_3sigma_i", "zero-differential", r"d_5(\{h_1+xv_1\}h_1u_{3\sigma_i})=0", (2, 2), 5, "verified", "formal_notes.tex:678-705; DKLLW24 Table 6; empty target (0,6) for d5(C)"),
    ("DER-3I-D5-A-EVEN", "ws_3sigma_i", "zero-differential", r"d_5(\{x^2+y^2\}D^2u_{3\sigma_i})=0", (14, 2), 5, "verified", "FN-3I-002; actual Ah2=T and DKLLW24 d5(D)=kDh2"),
    ("DER-3I-D5-C-zero", "ws_3sigma_i", "zero-differential", r"d_5(\{h_1+xv_1\}u_{3\sigma_i})=0", (1, 1), 5, "verified", "FN-3I-001; DKLLW24 Table 6 empty target"),
    ("DER-3I-D7-C-zero", "ws_3sigma_i", "zero-differential", r"d_7(\{h_1+xv_1\}u_{3\sigma_i})=0", (1, 1), 7, "verified", "FN-3I-001; primitive d3 image is the entire S00 target"),
    ("DER-3I-D7-Q-zero", "ws_3sigma_i", "zero-differential", r"d_7(\{h_1+xv_1\}h_1u_{3\sigma_i})=0", (2, 2), 7, "verified", "DER-3I-D7-C-zero; Q=h1*C and permanent h1"),
    ("DER-3I-D7-P-EVEN", "ws_3sigma_i", "zero-differential", r"d_7(\{yh_2+xh_1v_1\}u_{3\sigma_i})=0", (2, 2), 7, "verified", "FN-2I-004; permanent Euler image and empty integer-pattern d7 target"),
    ("DER-3I-D5-B-zero", "ws_3sigma_i", "zero-differential", r"d_5(\{x+y\}h_1u_{3\sigma_i})=0", (0, 2), 5, "verified", "FN-3I-001; entire target is a primitive d3 boundary"),
    ("DER-3I-D7-B-zero", "ws_3sigma_i", "zero-differential", r"d_7(\{x+y\}h_1u_{3\sigma_i})=0", (0, 2), 7, "verified", "FN-3I-005/006; both parity blocks of the target support d5"),
    ("FN-MIX-004-even-zero", "ws_sigma_i_2sigma_j", "zero-differential", r"d_5(\{yh_2+xh_1v_1\}u_{\sigma_i+2\sigma_j})=0", (2, 2), 5, "verified", "formal_notes.tex:934-951; DKLLW24 Tables 6 and 8; Leibniz rule"),
    ("FN-MIX-005-Q-zero", "ws_sigma_i_2sigma_j", "zero-differential", r"d_5(\{h_1+xv_1\}h_1u_{\sigma_i+2\sigma_j})=0", (2, 2), 5, "verified", "DER-MIX-D5-B-NONZERO; formal_notes.tex:953-970; DKLLW24 Table 6; square-zero and finite target injection"),
) + tuple(
    (f"DER-3I-D9-J{column}-D{m}-zero", "ws_3sigma_i", "zero-differential",
     rf"d_9(j^n\{{h_1+xv_1\}}{'h_1' if column == 'Q' else ''}D^{m}u_{{3\sigma_i}})=0\quad(n\geq1)",
     (8 * m + (2 if column == "Q" else 1), 2 if column == "Q" else 1), 9, "verified",
     "FN-3I-001; primitive d3 h1-products and negative-source Tate comparison")
    for m in (2, 3, 6, 7) for column in ("C", "Q") if m % 2 == 0 or column == "C"
) + tuple(
    (f"DER-2I-TATE-H{m}-cycle", "ws_2sigma_i", "permanent-cycle",
     rf"h_1D^{m}u_{{2\sigma_i}}\text{{ supports no differential}}",
     (8 * m + 1, 1), 2, "verified", "FN-2I-009; DKLLW24 Lemma 2.6 and negative-source Tate method")
    for m in (2, 6)
) + tuple(
    (f"DER-2I-TATE-JD{m}-cycle", "ws_2sigma_i", "permanent-cycle",
     rf"j^nD^{m}u_{{2\sigma_i}}\text{{ supports no differential}}\quad(n\geq1)",
     (8 * m, 0), 2, "verified", "FN-2I-001; DKLLW24 Table 8 primitive d3 and Lemma 2.6")
    for m in (2, 6)
) + tuple(
    (f"DER-2I-TATE-AH2-D{m}-cycle", "ws_2sigma_i", "permanent-cycle",
     rf"\{{x^2+y^2\}}h_2D^{m}u_{{2\sigma_i}}\text{{ supports no differential}}",
     (8 * m + 1, 3), 2, "verified", "FN-2I-003; DKLLW24 Lemma 2.6 and negative-source Tate method")
    for m in (2, 6)
) + tuple(
    (f"DER-2I-TATE-H2CUBE-D{m}-cycle", "ws_2sigma_i", "permanent-cycle",
     rf"h_2^3D^{m}u_{{2\sigma_i}}\text{{ supports no differential}}",
     (8 * m + 9, 3), 2, "verified", "FN-2I-011; DKLLW24 Lemma 2.6 and negative-source Tate method")
    for m in (1, 5)
) + tuple(
    (f"DER-MIX-D9-JQ-D{m}-zero", "ws_sigma_i_2sigma_j", "zero-differential",
     rf"d_9(j^n\{{h_1^2+xh_1v_1\}}D^{m}u_{{\sigma_i+2\sigma_j}})=0\quad(n\geq1)",
     (8 * m + 2, 2), 9, "review",
     "formal_notes.tex:881-901; DKLLW24 Lemma 2.6, main.tex:488-509,1391-1398; Table 6")
    for m in (2, 6)
)

_ZERO_CLAIM_SOURCES = {
    "DER-2I-TRANSFER-TWO-cycle": (r"2u_{2\sigma_i}", 64, "DER-2I-TRANSFER-TWO-cycle"),
    "FN-2I-003-zero": (r"\{x^2+y^2\}D^2u_{2\sigma_i}", 16, "FN-2I-003"),
    "FN-2I-005-zero": (r"2D^2u_{2\sigma_i}", 16, "FN-2I-005"),
    "FN-3I-001-zero": (r"\{h_1+xv_1\}u_{3\sigma_i}", 8, "FN-3I-001"),
    "FN-3I-010-pc": (r"\{h_1+xv_1\}ku_{3\sigma_i}", 64, "FN-3I-010"),
    "DER-3I-TATE-W-cycle": (r"2v_1^2Du_{3\sigma_i}", 64, "DER-3I-TATE-W-cycle"),
    "DER-3I-EULER-XD5-cycle": (r"x^3D^5u_{3\sigma_i}", 64, "DER-3I-EULER-XD5-cycle"),
    "DER-3I-EULER-CD5-cycle": (r"(h_1+xv_1)D^5u_{3\sigma_i}", 64, "DER-3I-EULER-CD5-cycle"),
    "FN-2I-004-derived-zero": (r"y^2Du_{2\sigma_i}", 16, "FN-2I-004"),
    "FN-2I-003-h2-zero": (r"\{x^2+y^2\}h_2D^2u_{2\sigma_i}", 16, "FN-2I-003"),
    "FN-2I-004-h2-square-zero": (r"h_2^3u_{2\sigma_i}", 8, "FN-2I-004"),
    "FN-2I-003-euler-h2-zero": (r"\{x^2+y^2\}h_2u_{2\sigma_i}", 64, "FN-2I-003"),
    "FN-3I-003-even-zero": (r"\{yh_2+xh_1v_1\}u_{3\sigma_i}", 16, "FN-3I-003"),
    "FN-3I-001-Q-zero": (r"\{h_1+xv_1\}h_1u_{3\sigma_i}", 8, "FN-3I-001"),
    "DER-3I-D5-A-EVEN": (r"\{x^2+y^2\}D^2u_{3\sigma_i}", 16, "DER-3I-D5-A-EVEN"),
    "DER-3I-D5-C-zero": (r"\{h_1+xv_1\}u_{3\sigma_i}", 8, "DER-3I-D5-C-zero"),
    "DER-3I-D7-C-zero": (r"\{h_1+xv_1\}u_{3\sigma_i}", 8, "DER-3I-D7-C-zero"),
    "DER-3I-D7-Q-zero": (r"\{h_1+xv_1\}h_1u_{3\sigma_i}", 8, "DER-3I-D7-Q-zero"),
    "DER-3I-D7-P-EVEN": (r"\{yh_2+xh_1v_1\}u_{3\sigma_i}", 16, "DER-3I-D7-P-EVEN"),
    "DER-3I-D5-B-zero": (r"\{x+y\}h_1u_{3\sigma_i}", 8, "DER-3I-D5-B-zero"),
    "DER-3I-D7-B-zero": (r"\{x+y\}h_1u_{3\sigma_i}", 8, "DER-3I-D7-B-zero"),
    "FN-MIX-004-even-zero": (r"\{yh_2+xh_1v_1\}u_{\sigma_i+2\sigma_j}", 16, "FN-MIX-004"),
    "FN-MIX-005-Q-zero": (r"\{h_1+xv_1\}h_1u_{\sigma_i+2\sigma_j}", 8, "FN-MIX-005"),
}

_ZERO_ENDPOINT_STYLES = {
    "DER-2I-TRANSFER-TWO-cycle": {"e2_pattern": "I00", "two_valuation": 1, "j_order": 0},
    "DER-3I-TATE-W-cycle": {"e2_pattern": "S40", "two_valuation": 1, "j_order": 0},
    "DER-3I-EULER-XD5-cycle": {"e2_pattern": "S53", "two_valuation": 0, "j_order": 0},
    "DER-3I-EULER-CD5-cycle": {"e2_pattern": "S11", "two_valuation": 0, "j_order": 0},
    "DER-3I-D5-A-EVEN": {"e2_pattern": "S62", "two_valuation": 0, "j_order": 0},
    "DER-3I-D5-C-zero": {"e2_pattern": "S11", "two_valuation": 0, "j_order": 0},
    "DER-3I-D7-C-zero": {"e2_pattern": "S11", "two_valuation": 0, "j_order": 0},
    "DER-3I-D7-Q-zero": {"e2_pattern": "S22H", "two_valuation": 0, "j_order": 0},
    "DER-3I-D7-P-EVEN": {"e2_pattern": "S22Y", "two_valuation": 0, "j_order": 0},
    "DER-3I-D5-B-zero": {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0},
    "DER-3I-D7-B-zero": {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0},
}
_PHI_ZERO_EVIDENCE = {}
for _power in (0, 1, 4, 5):
    _source_fact = "DER-3I-D9-C" if _power % 2 == 0 else "DER-3I-EULER-D9-C"
    _fact = f"DER-MIX-PHI-D7-D{_power}-zero"
    _label = r"\{x+y\}h_1" + (rf"D^{_power}" if _power else "") + r"u_{\sigma_i+2\sigma_j}"
    ZERO_AND_PERMANENT_CLAIMS += ((
        _fact, "ws_sigma_i_2sigma_j", "zero-differential", rf"d_7({_label})=0",
        (8 * _power, 2), 7, "verified", f"{_source_fact}; permanent Phi inverse and a_sigma_j",
    ),)
    _ZERO_CLAIM_SOURCES[_fact] = (_label, 64, _fact)
    _ZERO_ENDPOINT_STYLES[_fact] = {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0}
    _phi_evidence = _DERIVED_EVIDENCE[f"formal_diff_mixed_phi_d9_D{_power}"]
    _PHI_ZERO_EVIDENCE[_fact] = {
        "source_status": "independently-verified", "source_blockers": [],
        "withdrawn_dependencies": [], "machine_verification_pending": [],
        "evidence_kind": "permanent-Phi-Euler-cycle-image", "cycle_constraint": "outgoing-only",
        "derived_from": [_source_fact, "FN-MIX-001", "DKLLW24 Lemma 2.6"],
        "derivation": (
            "The independently verified 3sigma C source is a 9-cycle. Its image under "
            "omega^2, permanent Phi^-1 and a_sigma_j has zero outgoing d7. "
            "This certifies only the finite S02 source at this D^8 block and forward g. "
            "It does not protect against incoming maps, use D^4 as a 7-cycle, or declare permanence."
        ),
        "verification_certificate": {
            "status": "verified", "method": "Permanent Phi/Euler image of a verified 9-cycle",
            "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j", "page": 7,
            "premises": [_source_fact, "FN-MIX-001", "DKLLW24 Lemma 2.6"],
            "transport": deepcopy(_phi_evidence["transport_certificate"]),
        },
    }
_FINITE_D9_ZERO_EVIDENCE = {}
for _power in (1, 5):
    # Separate D8 blocks: the detector rows at D4 and D8 were proved
    # independently. No use of D4 as a permanent class is implicit here.
    _row_power = _power + 3
    _pure_fact = f"DER-3I-EULER-CD{_power}-D9-zero"
    _mixed_power = _power + 2
    _mixed_fact = f"DER-MIX-PHI-BH-D{_mixed_power}-D9-zero"
    _detector_row = f"formal_diff_three_d9_b_D{_row_power}_euler_derived"
    _pure_proof = {
        "status": "verified", "method": "Square-zero on a one-dimensional finite target",
        "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "page": 9,
        "source_refs": ["formal_notes.tex:678-705,764-780",
                        "DKLLW24 main.tex:1094-1111,1150-1198,1694-1702"],
        "premises": ["FN-3I-001", "DER-3I-D5-C-zero", "DER-3I-D7-C-zero",
                     "DER-3I-EULER-D9-B", "FN-3I-007", "DKLLW24 D^-1 h1 13-cycle"],
        "detector_differential_id": _detector_row,
        "detector_verification": deepcopy(_DERIVED_EVIDENCE[_detector_row]["verification_certificate"]),
        "translation": {"g_exponent": 2, "D_exponent": -8, "forward_g_only": True},
        "source_survival": {
            "bidegree": [8 * _power + 1, 1], "pattern": "S11", "port": "0:0",
            "d3": "FN-3I-001 and the integer D 3-cycle.",
            "d5": "The target E2 cell is empty.",
            "d7": "The entire target S00 column is a primitive d3 image.",
            "incoming": "Filtration one has no incoming d_r for r>=2.",
        },
        "finite_target": {
            "bidegree": [8 * _power, 10], "pattern": "S02", "port": "0:0", "dimension": 1,
            "representative": f"(x+y)h1*k^2*D^{_power + 1}u_3sigma_i",
            "no_extra_layers": "S02 is a single order-two, j-annihilated line; no Witt layer or completed tail.",
            "nonzero_d9_target": {"bidegree": [8 * _power - 1, 19], "pattern": "S73", "port": "0:0"},
            "same_cell_S73V": "Already a primitive d3 source, not an additional finite target.",
            "R_survival": {
                "incoming_d3": "The S00 source has zero d3, being a primitive d3 image.",
                "incoming_d5": "Empty E2 source cell.",
                "outgoing_before_d7": "Product of the independently verified E9 detector-row target with permanent M.",
                "outgoing_d7": {
                    "candidate_bidegree": [8 * _power - 2, 26], "pattern": "S62", "port": "0:0",
                    "L_image_bidegree": [8 * _power - 9, 27], "L_image_pattern": "S73",
                    "reason": "L=D^-1*h1 sends the finite A target nontrivially to Rk^6D^(m+2), "
                              "which is nonzero on E7: its d3 incoming S00 source has zero d3 and "
                              "its d5 incoming cell is empty. Since LW is an E9 cycle, Leibniz "
                              "and this finite target injection force d7(W)=0.",
                },
            },
            "d7_incoming_two_layer": {
                "bidegree": [8 * _power, 12], "pattern": "S40", "port": "1:0",
                "representative": f"2U*k^3*D^{_power + 1}",
                "disposition": "Not declared absent or a d5 boundary. L=D^-1*h1 annihilates this source, "
                               "while it sends the proposed target to the nonzero finite FN007 image. "
                               "Leibniz with the published 13-cycle L excludes this incoming d7.",
            },
        },
        "W_detector": {
            "bidegree": [8 * _power - 8, 20], "pattern": "S40", "port": "1:0",
            "representative": f"2U*k^5*D^{_power + 1}",
            "incoming_inventory": [
                {"page": 3, "source_bidegree": [8 * _power - 7, 17],
                 "reason": "The finite C source has zero d3; its positive-j directions cannot map to this constant port."},
                {"page": 5, "source_bidegree": [8 * _power - 7, 15],
                 "reason": "For x^3k^3D^(m+1), the even D exponent and odd k exponent give "
                           "cancelling Leibniz terms. Its outgoing d5 is zero; no source removal is asserted."},
                {"page": 7, "source_bidegree": [8 * _power - 7, 13],
                 "reason": "The Uh1 source, including its completed tail, supports primitive d3; no second two-layer."},
            ],
            "survival": "Forward g^2 D^-8 image of the independently verified FN007 constant two-target; "
                        "the same finite incoming inventory proves it is nonzero on E9.",
        },
        "derivation": (
            "Write C=(h1+xv1)u, B=(x+y)h1u, R=x^2h1u, U=v1^2u and g=kD^3. "
            f"For m={_power}, CD^m reaches E9. Its only possible finite target is T=Bk^2D^(m+1). "
            f"The independent B D^{_row_power} d9, multiplied by permanent g^2 D^-8, gives "
            "d9(T)=Rk^4D^(m+2) nonzero. Nonvanishing can be detected with L=D^-1*h1 "
            "in the finite FN007 Witt two-target W=2Uk^5D^(m+1). The potential incoming d7 "
            "from 2Uk^3D^(m+1) to R is excluded by L, not by removing that source. "
            "Thus d9 restricted to the one-dimensional candidate target T is injective. "
            "The identity d9^2=0 forces d9(CD^m)=0. Only nonzero units are needed, no "
            "new coefficient is assigned. No Jan29 premise, global inverse g, D4 permanence "
            "or high-filtration clipping is used."
        ),
        "coefficient_scope": "exact-port", "no_withdrawn_premise": True,
    }
    for _fact, _workspace, _pattern, _grade, _label in (
        (_pure_fact, "ws_3sigma_i", "S11", (8 * _power + 1, 1),
         rf"\{{h_1+xv_1\}}D^{_power}u_{{3\sigma_i}}"),
        (_mixed_fact, "ws_sigma_i_2sigma_j", "S02", (8 * _mixed_power, 2),
         rf"\{{x+y\}}h_1D^{_mixed_power}u_{{\sigma_i+2\sigma_j}}"),
    ):
        ZERO_AND_PERMANENT_CLAIMS += ((
            _fact, _workspace, "zero-differential", rf"d_9({_label})=0", _grade, 9,
            "verified", "formal_notes.tex:678-705,764-780,875; DKLLW24 main.tex:488-510,833-878,1694-1702; independent square-zero proof",
        ),)
        _ZERO_CLAIM_SOURCES[_fact] = (_label, 64, _fact)
        _ZERO_ENDPOINT_STYLES[_fact] = {"e2_pattern": _pattern, "two_valuation": 0, "j_order": 0}
        _evidence = {
            "source_status": "independently-verified", "source_blockers": [],
            "withdrawn_dependencies": [], "machine_verification_pending": [],
            "evidence_kind": "finite-square-zero-and-Phi-Euler-transport",
            "cycle_constraint": "outgoing-only", "coefficient_scope": "exact-port",
            "derived_from": _pure_proof["premises"][:],
            "verification_certificate": deepcopy(_pure_proof),
            "derivation": _pure_proof["derivation"],
        }
        if _workspace != "ws_3sigma_i":
            _evidence["derived_from"] = [_pure_fact, "FN-MIX-001", "DKLLW24 Lemma 2.6"]
            _evidence["transport_certificate"] = {
                "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
                "source_fact_id": _pure_fact, "source_power": _power,
                "action": "omega^2", "applied_inverse": True,
                "phi": "N_C4^Q8(dbar)*u_4sigma_k*g^-1*a_H",
                "phi_RO_degree": "-15+sigma_i+sigma_j-3sigma_k",
                "phi_stem_shift": -16, "phi_filtration_shift": 0,
                "euler_multiplier": "a_sigma_j", "final_D_exponent": 0,
                "comparison": "Tate equation followed by target injection at filtration 11>=9-1.",
            }
            _evidence["derivation"] += (
                " Apply omega^2, the inverse of the actual permanent Tate unit Phi, and a_sigma_j. "
                "Their finite E2 product sends CD^m to a nonzero unit times B D^(m+2) in the mixed sector. "
                "The target comparison in filtration 11 is injective; no low-filtration Tate injectivity "
                "is assumed. Hence the mixed outgoing d9 is zero whenever its source is present. "
                "The common Thom unit and the F4 action do not change a zero equation. "
                "This does not assert permanence, survival through later pages, or absence of incoming maps."
            )
        _FINITE_D9_ZERO_EVIDENCE[_fact] = _evidence

for _power in (1, 5):
    # Two independent D8 blocks. Multiplication by Dh1 has a nonzero
    # d9 itself, so both Leibniz terms are required even though they cancel.
    _fact = f"DER-3I-LEIBNIZ-TD{_power}-D9-zero"
    _label = r"(x+y)h_1^2" + ("D" if _power == 1 else rf"D^{_power}") + r"u_{3\sigma_i}"
    _v_power = 8 if _power == 1 else 4
    _v_row = f"formal_diff_three_d9_b_D{_v_power}_euler_derived"
    _premises = ["DER-3I-EULER-D9-B", "DKLLW24 Table 8 Dh1 d9",
                 "DKLLW24 hidden h1 extension R*h1=2kU", "DKLLW24 Table 6", "permanent D8"]
    _derivation = (
        "Write T=(x+y)h1^2u, V=(x+y)h1u, R=x^2h1u and U=v1^2u in the 3sigma sector. "
        f"For m={_power}, TD^m=(VD^(m-1))(Dh1). The independently verified V D^{_v_power} "
        + ("row is translated by permanent D^-8 to V D^0. " if _power == 1 else "row supplies V D^4. ")
        + "Together with Table 8 d9(Dh1)=xh1*k^2*D^2, Leibniz gives "
        "(R*h1 + V*xh1)k^2D^(m+1). Both actual products equal 2kU, so this is "
        "4Uk^3D^(m+1)=0 by 4kU=0. The pure-sector fixed units agree; the cancellation "
        "does not follow merely from the two terms being nonzero. The finite S13 source "
        "is nonzero on E9: both factors reach E9 and its incoming d2/d3 E2 cells are empty. "
        "This certifies only outgoing d9 on its constant finite line and its D8/forward-g "
        "images whenever present. It does not assert permanence, prevent incoming maps, "
        "remove the potential S40 two-layer target, or use D4 as a permanent unit."
    )
    ZERO_AND_PERMANENT_CLAIMS += ((
        _fact, "ws_3sigma_i", "zero-differential", rf"d_9({_label})=0",
        (8 * _power + 1, 3), 9, "verified",
        "formal_notes.tex:764-780; DKLLW24 main.tex:1095-1111,1183-1190,1889; two-term Leibniz rule",
    ),)
    _ZERO_CLAIM_SOURCES[_fact] = (_label, 64, _fact)
    _ZERO_ENDPOINT_STYLES[_fact] = {"e2_pattern": "S13", "two_valuation": 0, "j_order": 0}
    _FINITE_D9_ZERO_EVIDENCE[_fact] = {
        "source_status": "independently-verified", "source_blockers": [],
        "withdrawn_dependencies": [], "machine_verification_pending": [],
        "evidence_kind": "finite-two-term-Leibniz-cancellation",
        "cycle_constraint": "outgoing-only", "coefficient_scope": "exact-port",
        "derived_from": _premises[:], "derivation": _derivation,
        "verification_certificate": {
            "status": "verified", "method": "Two equal Leibniz terms in a finite order-two line",
            "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "page": 9,
            "source_refs": ["formal_notes.tex:764-780", "DKLLW24 main.tex:1095-1111,1183-1190,1889"],
            "premises": _premises[:], "derivation": _derivation,
            "factor_differential_id": _v_row,
            "factor_verification": deepcopy(_DERIVED_EVIDENCE[_v_row]["verification_certificate"]),
            "factor_translation": {"D_exponent": -8 if _power == 1 else 0, "g_exponent": 0},
            "source_survival": {
                "bidegree": [8 * _power + 1, 3], "pattern": "S13", "port": "0:0",
                "factors": [f"V D^{_power - 1}", "D h1"],
                "incoming_d2_cell": [8 * _power + 2, 1],
                "incoming_d3_cell": [8 * _power + 2, 0],
                "incoming": "Both E2 cells are empty; larger r have negative source filtration.",
                "outgoing_before_d9": "Product of two verified E9 classes.",
            },
            "potential_target": {
                "bidegree": [8 * _power, 12], "pattern": "S40", "port": "1:0",
                "representative": f"2U k^3 D^{_power + 1}",
                "disposition": "Not an image of this zero map; no liveness or permanence is assigned.",
            },
            "Leibniz_terms": [f"2U k^3 D^{_power + 1}", f"2U k^3 D^{_power + 1}"],
            "torsion_relation": "4kU=0", "no_withdrawn_premise": True,
        },
    }

_MIXED_D17_ID = "formal_diff_mixed_d17_v_D3_forced"
_DERIVED_ENDPOINT_STYLES[_MIXED_D17_ID] = (
    {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0},
    {"e2_pattern": "S73", "two_valuation": 0, "j_order": 0},
)
_DERIVED_EVIDENCE[_MIXED_D17_ID] = {
    "evidence_kind": "finite-vanishing-line-forced",
    "source_status": "independently-verified-nonzero-unit",
    "source_blockers": [], "withdrawn_dependencies": [], "machine_verification_pending": [],
    "derived_from": ["FN-MIX-001", "FN-MIX-004", "DER-MIX-D5-B-NONZERO",
                     "DER-MIX-D9-P-D2", "DER-MIX-PHI-BH-D3-D9-zero",
                     "DER-MIX-EULER-H2-cycle", "DER-MIX-EULER-H6-cycle",
                     "DKLLW24 RO strong vanishing line", "DKLLW24 Table 8 row 24"],
    "coefficient_parameter": {
        "id": "mixed_d17_VD3", "symbol": r"\lambda_{17}",
        "domain": [1, 2, 3], "value": None, "frobenius_power": 0,
    },
    "coefficient_constraint": "lambda_17 is nonzero; the printed local-summary coefficient 1 is not established.",
    "coefficient_scope": "exact-port",
    "rank_one_unit_certificate": {
        "status": "verified", "kind": "isolated-finite-F4-isomorphism", "page": 17,
        "source_pattern": "S02", "target_pattern": "S73", "coefficient_scope": "exact-port",
    },
    "derivation": (
        "Put V=(x+y)h1u, T=Vh1, R=x^2h1u, X=x^3u. The actual product "
        "S=g^6D^-16(VD^3)=Vk^6D^5 at (16,26) is a finite order-two, j-annihilated line. "
        "The complete incoming inventory and the outgoing inventory below leave only d17. "
        "For the c=1 incoming-d15 branch the independently verified FN-2I-016 equation "
        "under omega and a_sigma_i gives d9(PD^2)=zeta^2Tk^2D^3; for c!=1 that target "
        "is already a d5 image. No actual c or b is selected. The RO strong vanishing line "
        "requires filtration 26 to be absent after d23, hence d17(S) is nonzero. "
        "Forward multiplication implies d17(VD^3)=lambda_17 Rk^4D^5 with lambda_17 in F4*. "
        "This is not cancellation of g: the multiplier g^6D^-16 is itself the integer "
        "d23(D^-1h1) target. The argument separately proves S nonzero through E17. "
        "The same low formula repeats by D^8 and forward g wherever its endpoints remain; "
        "it does not determine the separate VD^7 residue or any d19/d21."
    ),
    "verification_certificate": {
        "status": "verified", "method": "Complete finite exclusion and RO strong vanishing line",
        "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j", "page": 17,
        "source_refs": ["table_Q8.tex:533", "formal_notes.tex:450-470,520-526,881-951",
                        "DKLLW24 main.tex:1179-1198,1311-1315,1914,1972-1976,2328"],
        "low_source": {"bidegree": [24, 2], "pattern": "S02", "port": "0:0"},
        "low_target": {"bidegree": [23, 19], "pattern": "S73", "port": "0:0"},
        "translation": {"g_exponent": 6, "D_exponent": -16, "forward_g_only": True,
                        "invertible_in_HFPSS": False},
        "forward_detection": "The high source/target filtrations 26/43 are above the E17 comparison threshold 16. Their nonzero images in Tate remain nonzero under its unit g; positive-filtration comparison brings those higher translates back. Lower g exponents are detected by the high one. This is not global g-injectivity on the HFPSS.",
        "high_source": {"bidegree": [16, 26], "pattern": "S02", "port": "0:0", "dimension": 1},
        "high_target": {"bidegree": [15, 43], "pattern": "S73", "port": "0:0", "dimension": 1,
                        "other_direction": "S73V is an entire primitive d3 source; not an additional target line."},
        "incoming_inventory": [
            {"page": 3, "source_bidegree": [17, 23], "representative": "Xk^5D^5",
             "reason": "X=a_i*a_j^2 is permanent, and integer D,k are 3-cycles; hence zero outgoing d3."},
            {"page": 5, "source_bidegree": [17, 21], "representative": "Uh1k^5D^4",
             "reason": "The entire completed module supports primitive d3."},
            {"page": 7, "source_bidegree": [17, 19], "representative": "Tk^4D^4",
             "reason": "d5(Ak^3D^4)=cTk^4D^4, with independently established c nonzero."},
            {"page": 9, "source_bidegree": [17, 17], "representative": "Ck^4D^4",
             "reason": "The constant is a primitive d3 source; positive-j directions are primitive d3 images."},
            {"page": 11, "source_bidegree": [17, 15], "representative": "Xk^3D^4",
             "reason": "d5(Pk^2D^3)=Xk^3D^4."},
            {"page": 13, "source_bidegree": [17, 13], "representative": "Uh1k^3D^3",
             "reason": "The entire completed module supports primitive d3."},
            {"page": 15, "source_bidegree": [17, 11], "representative": "Tk^2D^3",
             "reason": "If c!=1, d5(AkD^3)=(c+1)Tk^2D^3 is nonzero; if c=1, the independently verified Euler equation d9(PD^2)=zeta^2Tk^2D^3 is nonzero."},
            {"page": 17, "source_bidegree": [17, 9], "representative": "Ck^2D^3",
             "reason": "The constant is a primitive d3 source; positive-j directions are primitive d3 images."},
            {"page": 19, "source_bidegree": [17, 7], "representative": "XkD^3=gX",
             "reason": "X=a_i*a_j^2 and g are permanent cycles; only zero outgoing is asserted."},
            {"page": 21, "source_bidegree": [17, 5], "representative": "Uh1kD^2",
             "reason": "The entire completed module supports primitive d3."},
            {"page": 23, "source_bidegree": [17, 3], "representative": "TD^2",
             "reason": "DER-MIX-EULER-H2-cycle times the permanent h1 has zero outgoing."},
        ],
        "outgoing_inventory": [
            {"pages": [3, 11, 19], "reason": "Empty E2 target cells by the finite bidegree enumeration."},
            {"pages": [5, 13, 21], "targets": ["h1^3k^7D^5u", "h1^3k^9D^6u", "h1^3k^11D^7u"],
             "reason": "Each entire completed target module is a primitive d3 image."},
            {"pages": [7, 15, 23], "targets": ["Bk^8D^6", "Bk^10D^7", "Bk^12D^8"],
             "reason": "Each finite B direction supports nonzero d5, using only the proved b!=0."},
            {"pages": [9], "reason": "DER-MIX-PHI-BH-D3-D9-zero multiplied by g^6D^-16."},
            {"pages": [17], "target_bidegree": [15, 43], "reason": "The unique remaining finite target S73."},
        ],
        "even_pages": "Empty by E2 total-degree parity.",
        "vanishing_line": {"filtration": 23, "empty_from_page": 24, "all_RO_gradings": True},
        "conditional_premise": {"fact_id": "DER-MIX-D9-P-D2", "condition": "c=1",
                                "coefficient": 3, "independent_of": ["b", "row533", "Jan29"]},
        "cross_check": "If VD^3 reached E23, Table 8 gives d23(TD^2)=g^6D^-16 VD^3=S, contradicting the Euler-H2 times h1 zero-outgoing certificate and the same complete incoming inventory.",
        "coefficient_result": "nonzero unit only", "no_withdrawn_premise": True,
    },
}

_THREE_W5_D23_ID = "formal_diff_three_d23_u_D5_forced"
_DERIVED_ENDPOINT_STYLES[_THREE_W5_D23_ID] = (
    {"e2_pattern": "S40", "two_valuation": 1, "j_order": 0},
    {"e2_pattern": "S73", "two_valuation": 0, "j_order": 0},
)
_DERIVED_EVIDENCE[_THREE_W5_D23_ID] = {
    "evidence_kind": "finite-exclusion-and-published-d23-Leibniz",
    "source_status": "independently-verified", "source_blockers": [],
    "withdrawn_dependencies": [], "machine_verification_pending": [],
    "D_block": 5, "coefficient_scope": "exact-port",
    # Display provenance only: do not admit the withdrawn D1/32-period claim.
    # An alias may share a line only where its exact occurrence equation agrees.
    "render_equation_aliases": [{"fact_id": "FN-3I-010", "page": 23,
                                 "status": "review", "scope": "same-equation-only"}],
    "derived_from": ["FN-3I-001", "FN-3I-002", "FN-3I-003", "FN-3I-004",
                     "FN-3I-005", "FN-3I-006", "FN-3I-008",
                     "DER-3I-D9-C", "DER-3I-LEIBNIZ-TD5-D9-zero",
                     "DER-3I-EULER-XD5-cycle", "DER-3I-EULER-CD5-cycle",
                     "DKLLW24 Table 8 row 22", "DKLLW24 Lemma 5.2"],
    "coefficient_parameter": {
        "id": "three_sigma_d23_W5", "symbol": r"\lambda_{23,5}",
        "domain": [1], "value": 1, "frobenius_power": 0,
        "fixed_reason": "pure-sigma-i-galois-fixed",
    },
    "coefficient_constraint": "The actual product equation also forces lambda=1, not merely a nonzero F4 unit.",
    "forward_period": {"multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True},
    "derivation": (
        "Write U=v1^2u, C=(h1+xv1)u, a=(x+y)u, V=ah1, T=ah1^2, "
        "X=x^3u, R=x^2h1u, P=ah2 and Q=Ch1. Put W=2UD5, Y=Rk5D8, "
        "L=D^-1h1, Z=g6D^-16W and G=gZ=g7D^-16W. The complete low outgoing "
        "inventory proves W nonzero through E23. Since g7D^-16 is permanent, "
        "G has zero outgoing for r<23; its independent complete incoming inventory "
        "proves G nonzero at (56,28) on E23. Table 8 gives d23(gL)=g7D^-16. "
        "The actual relation 2h1=0 implies (gL)W=0, hence Leibniz gives "
        "0=G+(gL)d23(W). Thus d23(W) is nonzero. Its only possible finite "
        "direction is Y; the other completed S73V direction is already a primitive "
        "d3 source. By the actual hidden product Rh1=2kU, (gL)Y=G. "
        "Writing d23(W)=lambda*Y forces (1+lambda)G=0, so lambda=1 in F4. "
        "This argument forces Y to be present on E23 without first assuming its "
        "d19 is zero. Square-zero then gives d23(Y)=0; Y is a boundary on E24, "
        "not a permanent class. Only D8 and forward g translate this equation. "
        "In particular G itself supports the translated d23 to (55,51); it is "
        "not declared an incoming image by multiplying with the noncycle gL. "
        "No January Euler claim, D4 periodicity, global cancellation of g, "
        "or imposed vanishing-line clipping is used."
    ),
    "verification_certificate": {
        "status": "verified", "method": "Complete finite exclusion and published d23 product",
        "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "page": 23,
        "source_refs": ["DKLLW24 main.tex:1095-1111,1914-1915",
                        "formal_notes.tex:678-780", "DER-3I-EULER-XD5-cycle",
                        "DER-3I-EULER-CD5-cycle", "DER-3I-LEIBNIZ-TD5-D9-zero"],
        "low_source": {"bidegree": [44, 0], "pattern": "S40", "port": "1:0",
                       "incoming": "All r>=2 have negative source filtration.",
                       "coefficient_module": "2W(F4)[[j]] before d23"},
        "low_target": {"bidegree": [43, 23], "pattern": "S73", "port": "0:0",
                       "dimension": 1, "torsion_order": 2, "j_annihilated": True,
                       "other_direction": "The entire S73V column supports primitive d3.",
                       "survival": "Forced by the nonzero Leibniz product; not assumed beforehand."},
        "low_outgoing_inventory": [
            {"page": 3, "target": "h1^3D5u", "reason": "2d3(UD5)=0; this target does exist on E3."},
            {"page": 5, "target": "akD6", "reason": "Its d5=(P+Q)k2D6 is nonzero, excluding it by square-zero."},
            {"page": 7, "target": "RkD6", "reason": "L detects this line as nonzero 2Uk2D5 on E7, whereas LW=0."},
            {"pages": [9, 17], "reason": "Empty E2 target cells."},
            {"pages": [11, 19], "targets": ["h1^3k2D6u", "h1^3k4D7u"],
             "reason": "Entire completed target columns are primitive d3 images."},
            {"page": 13, "target": "ak3D7", "reason": "Nonzero d5=Qk4D7."},
            {"page": 15, "target": "Rk3D7", "reason": "Already d9(VkD6), the forward-g FN008 image."},
            {"page": 21, "target": "ak5D8", "reason": "Nonzero d5=(P+Q)k6D8."},
            {"page": 23, "target": "Y=Rk5D8", "reason": "Only remaining finite direction."},
        ],
        "d7_detector": {
            "multiplier": "L=D^-1h1", "zero_product": "LW=0",
            "target_product": "L(RkD6)=2Uk2D5", "bidegree": [36, 8],
            "pattern": "S40", "port": "1:0",
            "incoming_d3": "CkD5 has zero d3.",
            "incoming_d5": "XD5 has zero d5 (1+5=0 mod 2), independently a certified cycle.",
            "outgoing_d5": "Its sole finite target ak3D6 has nonzero d5, so square-zero excludes it.",
            "other_ports": "Primitive d3 removes odd and positive-j directions; the finite 2-layer remains.",
        },
        "high_detection": {
            "label": "G=2Uk7D10", "bidegree": [56, 28], "pattern": "S40", "port": "1:0",
            "dimension": 1, "torsion_order": 2, "j_annihilated": True,
            "multiplier": {"g_exponent": 7, "D_exponent": -16, "permanent": True,
                           "invertible_in_HFPSS": False},
            "outgoing_before_23": "Zero by the independently established survival of W and the permanent multiplier.",
            "incoming_inventory": [
                {"page": 3, "source": "Ck6D10", "reason": "The entire C column has zero d3."},
                {"page": 5, "source": "Xk5D10", "reason": "d5 coefficient 1+10-3*5 is zero mod 2."},
                {"page": 7, "source": "Uh1k5D9", "reason": "The entire completed column supports primitive d3."},
                {"page": 9, "source": "Tk4D9", "reason": "g4D^-8 times the independently verified TD5 zero-d9."},
                {"page": 11, "source": "Ck4D9", "reason": "g4D^-8 times the independently verified CD5 cycle."},
                {"page": 13, "source": "Xk3D9", "reason": "Nonzero d5=2Uk5D9; its target is a nonzero E5 two-layer."},
                {"page": 15, "source": "Uh1k3D8", "reason": "The entire completed column supports primitive d3."},
                {"page": 17, "source": "Tk2D8", "reason": "Already d5(AkD8), with coefficient 8-3=1 mod 2."},
                {"page": 19, "source": "Ck2D8", "reason": "The constant supports verified nonzero d9=Vk4D9; the positive-j ideal was an earlier d3 image."},
                {"page": 21, "source": "XkD8", "reason": "Already d5(PD7); the XD5 cycle certificate does not restore an incoming image."},
                {"page": 23, "source": "Uh1kD7", "reason": "The entire completed column supports primitive d3."},
            ],
            "actual_d23": {"source": [56, 28], "target": [55, 51],
                           "kind": "outgoing translate of W-to-Y, not an incoming h1 closure"},
        },
        "coefficient_equation": {"zero_product": "(gL)W=0", "published": "d23(gL)=g7D^-16",
                                 "actual_product": "(gL)Y=G", "equation": "(1+lambda)G=0",
                                 "G_nonzero": True, "lambda": 1, "field": "F4"},
        "even_pages": "Empty by E2 total-degree parity in both finite inventories.",
        "surviving_source_submodule": "4W(F4)[[j]] + 2jW(F4)[[j]]; do not remove the whole square.",
        "period": {"D_power": 8, "stem": 64, "forward_g": True, "D1_block_inferred": False},
        "no_withdrawn_premise": True, "uses_vanishing_line": False,
    },
}

_THREE_W5_TARGET_ZERO_EVIDENCE = {}
for _page in (19, 23):
    _fact = f"DER-3I-W5-TARGET-D{_page}-zero"
    _label = r"x^2h_1k^5D^8u_{3\sigma_i}"
    _reason = (
        "The independently proved nonzero d23(W5)=Y forces this exact finite "
        "target direction to be present on E23, hence d19(Y)=0. This is a "
        "consequence of the complete W5 proof, not a premise of that proof."
        if _page == 19 else
        "The independently proved equation d23(W5)=Y and d23 squared zero "
        "give d23(Y)=0. Y remains the genuine incoming image and is absent "
        "on E24; a zero outgoing map does not make Y a permanent class."
    )
    ZERO_AND_PERMANENT_CLAIMS += ((
        _fact, "ws_3sigma_i", "zero-differential", rf"d_{{{_page}}}({_label})=0",
        (43, 23), _page, "verified",
        "DER-3I-LEIBNIZ-W5-D23; DKLLW24 main.tex:1095-1111,1914-1915; target survival and square-zero",
    ),)
    _ZERO_CLAIM_SOURCES[_fact] = (_label, 64, _fact)
    _ZERO_ENDPOINT_STYLES[_fact] = {"e2_pattern": "S73", "two_valuation": 0, "j_order": 0}
    _THREE_W5_TARGET_ZERO_EVIDENCE[_fact] = {
        "source_status": "independently-verified", "source_blockers": [],
        "withdrawn_dependencies": [], "machine_verification_pending": [],
        "evidence_kind": "verified-d23-target-consequence", "cycle_constraint": "outgoing-only",
        "coefficient_scope": "exact-port", "derived_from": ["DER-3I-LEIBNIZ-W5-D23"],
        "derivation": _reason + " Only D8 and nonnegative powers of g translate this zero map.",
        "verification_certificate": {
            "status": "verified", "method": "Verified target survival" if _page == 19 else "Same-page square-zero",
            "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "page": _page,
            "premises": ["DER-3I-LEIBNIZ-W5-D23"],
            "source_refs": ["DER-3I-LEIBNIZ-W5-D23", "DKLLW24 main.tex:1095-1111,1914-1915"],
            "source": {"bidegree": [43, 23], "pattern": "S73", "port": "0:0", "dimension": 1},
            "nonzero_parent_map": {"source": [44, 0], "target": [43, 23], "page": 23},
            "boundary_from_page": 24, "survival_override": False, "no_withdrawn_premise": True,
            "excluded_scope": ["D4 translates", "negative g powers", "S73V", "additional Witt or positive-j ports", "other pages"],
        },
    }

_TRANSFER_TWO_EVIDENCE = {
    "source_status": "independently-verified", "source_blockers": [], "machine_verification_pending": [],
    "evidence_kind": "RO-kernel-subgroup-transfer", "cycle_constraint": "outgoing-only",
    "coefficient_scope": "constant-two-multiples",
    "verification_certificate": _VERIFIED_FORMAL_CERTIFICATES["FN-2I-005"],
    "derivation": _VERIFIED_FORMAL_CERTIFICATES["FN-2I-005"]["derivation"],
    "transfer_certificate": {"subgroup": "C4<i>", "restriction_degree": "res(2-2sigma_i)=0",
                             "source": "1", "trace": "1+1=2", "orientation_action": 1},
}
_EULER_XD5_CYCLE_EVIDENCE = {
    "source_status": "independently-verified", "source_blockers": [],
    "machine_verification_pending": [], "withdrawn_dependencies": [],
    "evidence_kind": "Euler-cofiber-and-complete-C4-filtration",
    "cycle_constraint": "outgoing-only", "coefficient_scope": "exact-port",
    "derived_from": ["BBHS20 complete C4 HFPSS", "DKLLW24 Table 8",
                     "DKLLW24 Corollary 2.23", "FN-3I-001", "index-two representation-sphere cofiber"],
    "derivation": (
        "Put X=x^3u_3sigma_i and U=v1^2u_3sigma_i. In the integer HFPSS, "
        "4kD5=g*(4D2) is a nonzero E-infinity class: the complete Table 8 gives "
        "zero outgoing on 4D2 and g is permanent. The only possible incoming at "
        "(36,4) is d3(v1^2*h1*D4)=j*kD5 and its positive-j ideal, which does not "
        "contain the constant four-layer. The ordinary C4<i> restriction of 4kD5 "
        "is zero, since the positive-filtration C4 group here has exponent four. "
        "The complete BBHS C4 differential enumeration below proves F5 pi36=0, "
        "so this associated-graded zero is also an actual homotopy restriction zero. "
        "Multiply by the permanent filtration-zero unit u_4sigma_i. The cofiber "
        "(Q8/C4<i>)+ -> S0 -> S^sigma_i gives an actual Euler preimage in "
        "pi_(40-3sigma_i), whose chart stem is 37. An Euler product raises "
        "filtration by at least one, so a class with nonzero filtration-four image "
        "has a preimage with leading filtration at most three. At this RO degree "
        "the entire filtration-one j-series U*h1*D4 maps injectively by primitive "
        "d3 to v1^4*k*D4*u; filtrations zero and two are empty. The sole remaining "
        "low-filtration line is X*D5, which therefore detects a nonzero homotopy "
        "class. All its outgoing differentials, including d21, are zero. "
        "This is not the January Ck argument. Only permanent D8 translates and "
        "forward g images inherit the outgoing-zero constraint; g*XD5 is itself "
        "the d5(PD7) image and must not be resurrected. No d11(CD5) or d23(2UD5) "
        "value follows from this certificate."
    ),
    "verification_certificate": {
        "status": "verified", "method": "Euler cofiber and complete C4 filtration bound",
        "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "page": 2,
        "source_refs": ["BBHS20 pp.3454-3457,3464-3471; Propositions 5.21,5.24,5.27,5.28; Tables 4/5",
                        "DKLLW24 main.tex:869-878,1336-1395,1870-1917,2510",
                        "formal_notes.tex:678-705"],
        "premises": ["complete C4 HFPSS", "integer 4kD5 nonzero in E-infinity",
                     "permanent u_4sigma_i", "FN-3I-001 and its full h1/j closure",
                     "index-two representation-sphere cofiber"],
        "source_survival": {"bidegree": [37, 3], "pattern": "S53", "port": "0:0"},
        "integer_image": {
            "bidegree": [36, 4], "representative": "4kD5", "factorization": "g*(4D2)",
            "incoming_d3": {"bidegree": [37, 1], "source": "v1^2*h1*D4",
                            "image": "j*kD5", "coefficient_scope": "positive-j ideal only"},
            "later_incoming": "r>=5 has negative source filtration; even lengths have empty sources.",
            "ordinary_restriction": "zero in gr4; positive-filtration C4 coefficients have exponent four",
        },
        "C4_filtration_certificate": {
            "stem": 36, "F5_zero": True, "finite_E_infinity_filtration": 4,
            "finite_E_infinity_representative": "2*varpi^2*Delta1^3",
            "degrees": {"Delta1": [8, 0], "varpi": [6, 2], "kappa_bar": [20, 4], "epsilon": [8, 8]},
            "definitions": {"kappa_bar": "varpi^2*Delta1", "epsilon": "varpi^4*Delta1^-2"},
            "n_min": 0,
            "E2_families": [
                {"filtration": "4+8n", "basis": "b_n=epsilon^n*kappa_bar*Delta1^(2-n)",
                 "monomial": "varpi^(2+4n)*Delta1^(3-3n)", "after_d3": "W/4; positive-mu image removed"},
                {"filtration": "8+8n", "basis": "eta^2*varpi^(3+4n)*Delta1^(2-3n)",
                 "after_d3": "zero; d3 is injective on the full column"},
            ],
            "E6": {"n=0": "W/4{b0}", "n odd": "F4{2b_n}", "n even>=2": "F4{b_n mod 2}"},
            "incoming_d5_even_n": "d5(nu*varpi^(4n-1)*Delta1^(5-3n))=2b_n",
            "E8": ["2b0", "b_(2+4r), r>=0"],
            "last_d13": "d13(epsilon^(4r)*kappa_bar*Delta1^(-4r)*Delta1*nu*varpi)=b_(2+4r)",
            "permanent_multipliers": ["epsilon", "kappa_bar", "Delta1^4", "Delta1^-4"],
            "completion": "All positive filtrations enumerated; strong separated convergence gives F5 pi36=0.",
        },
        "Euler_exactness": {
            "cofiber": "(Q8/C4<i>)+ -> S0 -> S^sigma_i",
            "groups": ["pi_(40-3sigma_i)", "pi_(40-4sigma_i)", "pi_36(C4<i>)"],
            "maps": ["a_sigma_i", "restriction"],
            "thom_unit": "u_4sigma_i, degree 4-4sigma_i, filtration 0; its restriction is a unit, not necessarily 1",
            "filtration_argument": "If the preimage lay in F4, its Euler image would lie in F5, contradicting the nonzero gr4 image.",
        },
        "low_source_inventory": [
            {"filtration": 0, "disposition": "empty E2 cell"},
            {"filtration": 1, "pattern": "S51", "basis": "U*h1*D4", "coefficient_scope": "full j-series",
             "disposition": "primitive d3 injective onto the full S00 local series; not just its constant term"},
            {"filtration": 2, "disposition": "empty E2 cell"},
            {"filtration": 3, "pattern": "S53", "basis": "X*D5", "port": "0:0", "dimension": 1},
        ],
        "forward_boundary_control": {"source": "P*D7", "target": "g*X*D5=X*k*D8", "page": 5},
        "no_withdrawn_premise": True,
    },
}

_EULER_CD5_CYCLE_EVIDENCE = {
    "source_status": "independently-verified", "source_blockers": [],
    "withdrawn_dependencies": [], "machine_verification_pending": [],
    "evidence_kind": "adjusted-Euler-preimage-and-complete-C4-filtration",
    "cycle_constraint": "outgoing-only", "coefficient_scope": "all-multiples",
    "derived_from": ["DKLLW24 Table 8 D2h1 d9", "DKLLW24 Tate method",
                     "BBHS20 complete C4 stem-40 filtration", "FN-3I-001",
                     "index-two representation-sphere cofiber", "permanent u_4sigma_i"],
    "derivation": (
        "Write C=(h1+xv1)u_3sigma_i, U=v1^2u_3sigma_i, c=xh1D and g=kD3. "
        "Table 8 gives d9(D2h1)=D^-4*g^2*c. In TateSS, multiply by the permanent "
        "unit D8*g^-2: the resulting source (41,-7) maps to cD4 at (40,2). "
        "The Tate comparison proves zero HFPSS outgoing, not an incoming HFPSS "
        "map. HFPSS incoming d2 has empty source (41,0), and r>=3 has negative "
        "source filtration, so cD4 detects a nonzero element y of gr2 pi40. "
        "The complete BBHS C4 calculation gives F2 pi40=F8 pi40=F4{epsilon*Delta1^4} "
        "and F9 pi40=0. This generator is res(g^2)=kappa_bar^2. Choose an actual "
        "representative y and subtract a suitable W(F4) scalar multiple of g^2 "
        "to obtain y' with actual restriction zero and the same nonzero gr2. "
        "No value of the possible exotic restriction coefficient is assumed. "
        "Multiplying by the permanent Thom unit u_4sigma_i preserves filtration; "
        "its restriction need only be a unit. The index-two Euler cofiber lifts "
        "y'u_4sigma_i to pi_(44-3sigma_i), with leading filtration at most one. "
        "Filtration zero at stem 41 is empty; filtration one is the full "
        "F4[[j]]{CD5}, not a finite one-dimensional cell. Independently, primitive "
        "d3 in TateSS gives d3(k^-1*U*h1^2*D4)=jCD5 from (42,-2) to (41,1). "
        "Continuity and j-linearity include the whole completed positive-j ideal. "
        "The actual E2 Euler product sends CD5 to cD4*u_4sigma_i and its positive-j "
        "ideal to zero. Thus the lifted leading cycle has nonzero constant "
        "coefficient; its positive-j part is separately a cycle. Subtract that "
        "part to obtain zero outgoing on CD5, including d11. All of its completed "
        "j-series therefore consists of cycles. Only D8 translates and forward g "
        "inherit this constraint; incoming maps still take precedence. In particular "
        "g*jCD5 is a positive-filtration primitive d3 image and is not restored. "
        "This does not assert that CD1 is permanent or decide d23(2UD5)."
    ),
    "verification_certificate": {
        "status": "verified", "method": "Adjusted Euler preimage and complete C4 filtration",
        "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "page": 2,
        "source_refs": ["BBHS20 pp.3454-3457,3464-3471; Propositions 5.21,5.24,5.27,5.28; Tables 4/5",
                        "DKLLW24 main.tex:488-510,869-878,1095-1111,1336-1339,1867-1917,2510",
                        "formal_notes.tex:678-705"],
        "premises": ["complete C4 HFPSS", "integer cD4 Tate-cycle certificate",
                     "restriction of g^2 spans positive filtration in C4 pi40",
                     "permanent u_4sigma_i", "FN-3I-001 including completed j-ideals",
                     "index-two representation-sphere cofiber"],
        "source_survival": {"bidegree": [41, 1], "pattern": "S11", "ports": ["0:0", "0:1"],
                            "module": "F4[[j]]{CD5}", "incoming": "r>=2 has negative source filtration"},
        "integer_image": {
            "bidegree": [40, 2], "pattern": "I02", "representative": "cD4=xh1D5",
            "published_map": "d9(D2h1)=D^-4*g^2*c",
            "Tate_multiplier": "D8*g^-2", "Tate_source_bidegree": [41, -7],
            "Tate_source": "D10*g^-2*h1", "Tate_target": "cD4",
            "incoming_d2_cell": [41, 0], "incoming_d2_empty": True,
            "later_incoming": "r>=3 has negative source filtration",
            "interpretation": "Negative-source Tate image certifies HFPSS outgoing zero, not HFPSS removal.",
        },
        "C4_filtration_certificate": {
            "stem": 40, "F2_equals_F8": True, "F9_zero": True,
            "finite_E_infinity_filtration": 8,
            "finite_E_infinity_representative": "epsilon*Delta1^4=kappa_bar^2",
            "degrees": {"Delta1": [8, 0], "varpi": [6, 2], "kappa_bar": [20, 4], "epsilon": [8, 8]},
            "definitions": {"kappa_bar": "varpi^2*Delta1", "epsilon": "varpi^4*Delta1^-2"},
            "n_min": 0,
            "E2_families": [
                {"filtration": "8+8n", "basis": "b_n=epsilon^(n+1)*Delta1^(4-n)",
                 "monomial": "varpi^(4+4n)*Delta1^(2-3n)", "after_d3": "W/4; positive-mu image removed"},
                {"filtration": "4+8n", "basis": "eta^2*varpi^(1+4n)*Delta1^(4-3n)",
                 "after_d3": "zero; d3 injective on the full column"},
            ],
            "E6": {"n even": "F4{b_n mod 2}", "n odd": "F4{2b_n}"},
            "incoming_d5_even_n": "d5(nu*varpi^(1+4n)*Delta1^(4-3n))=2b_n",
            "basic_d7": ["d7(2Delta1)=varsigma*varpi^3*Delta1^-2",
                         "d7(Delta1^2)=varsigma*varpi^3*Delta1^-1"],
            "E8": ["b_(4r), r>=0"],
            "last_d13": "d13(epsilon^(4r-1)*Delta1^(4-4r)*Delta1*nu*varpi)=b_(4r), r>=1",
            "permanent_multipliers": ["epsilon", "kappa_bar", "Delta1^4", "Delta1^-4"],
            "completion": "All positive filtrations enumerated; strong separated convergence gives F2=F8 and F9=0.",
        },
        "restriction_adjustment": {
            "surjective_detector": "res(g^2)=kappa_bar^2=epsilon*Delta1^4",
            "coefficient_ring": "W(F4)", "coefficient_value": None,
            "operation": "y'=y-[a]*g^2 with res(y')=0",
            "filtrations": {"y": 2, "g_squared": 8},
            "leading_class_preserved": True,
            "scope": "Cancel the actual restriction using surjectivity; do not infer actual res(y)=0 from its E2 restriction.",
        },
        "Euler_exactness": {
            "cofiber": "(Q8/C4<i>)+ -> S0 -> S^sigma_i",
            "groups": ["pi_(44-3sigma_i)", "pi_(44-4sigma_i)", "pi_40(C4<i>)"],
            "maps": ["a_sigma_i", "restriction"],
            "thom_unit": "u_4sigma_i; filtration zero, restriction an unspecified unit",
            "leading_product": "a_sigma_i*CD5=cD4*u_4sigma_i",
            "positive_j_product": "j*cD4=0 in the finite I02 E2 line",
            "filtration_argument": "A preimage in F2 would have Euler image in F3, contradicting the preserved nonzero gr2.",
        },
        "low_source_inventory": [
            {"filtration": 0, "disposition": "empty E2 cell"},
            {"filtration": 1, "pattern": "S11", "basis": "CD5", "module": "F4[[j]]", "ports": ["0:0", "0:1"]},
        ],
        "positive_j_cycle": {
            "page": 3, "source_bidegree": [42, -2], "target_bidegree": [41, 1],
            "equation": "d3(k^-1*U*h1^2*D4)=jCD5",
            "relation": "h1^4=k*v1^4=j*kD; h1^5*u=v1^4*k*C",
            "coefficient_scope": "entire completed positive-j ideal",
            "interpretation": "Tate-only preimage; not an HFPSS incoming map in filtration one",
        },
        "forward_boundary_control": {
            "page": 3, "source_bidegree": [62, 2], "target_bidegree": [61, 5],
            "source": "U*h1^2*D7", "target": "g*jCD5", "target_port": "0:1",
        },
        "no_withdrawn_premise": True,
    },
}

_MIXED_VD7_CYCLE_FACT = "DER-MIX-PHI-CD5-VD7-cycle"
_MIXED_VD7_CYCLE_LABEL = r"(x+y)h_1D^7u_{\sigma_i+2\sigma_j}"
ZERO_AND_PERMANENT_CLAIMS += ((
    _MIXED_VD7_CYCLE_FACT, "ws_sigma_i_2sigma_j", "permanent-cycle",
    _MIXED_VD7_CYCLE_LABEL + r"\text{ supports no differential}", (56, 2), 2,
    "verified", "DER-3I-EULER-CD5-cycle; formal_notes.tex:875; DKLLW24 Tate comparison and norm/Thom units",
),)
_ZERO_CLAIM_SOURCES[_MIXED_VD7_CYCLE_FACT] = (_MIXED_VD7_CYCLE_LABEL, 64, _MIXED_VD7_CYCLE_FACT)
_ZERO_ENDPOINT_STYLES[_MIXED_VD7_CYCLE_FACT] = {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0}
_MIXED_VD7_CYCLE_EVIDENCE = {
    "source_status": "independently-verified", "source_blockers": [],
    "withdrawn_dependencies": [], "machine_verification_pending": [],
    "evidence_kind": "permanent-Phi-Euler-image-of-CD5-cycle",
    "cycle_constraint": "outgoing-only", "coefficient_scope": "exact-port",
    "source_fact_id": "DER-3I-EULER-CD5-cycle",
    "external_premises": [{"workspace_id": "ws_3sigma_i",
                           "proposition_id": "formal_prop_der-3i-euler-cd5-cycle"}],
    "derived_from": ["DER-3I-EULER-CD5-cycle", "FN-MIX-001", "DKLLW24 Lemma 2.6",
                     "DKLLW24 norm/Thom permanent units", "formal_notes.tex:875"],
    "derivation": (
        "Put C=(h1+xv1)u_3sigma_i and V=(x+y)h1u_mix. The independent adjusted "
        "Euler/C4 proof makes the entire completed CD5 class an outgoing cycle. "
        "In TateSS apply F=a_sigma_j*Phi^-1*omega^2, where "
        "Phi=N_C4^Q8(dbar)*u_4sigma_k*g^-1*a_H is an actual permanent unit, not "
        "an asserted HFPSS 20+H isomorphism. omega^2(D)=zeta*D and the finite "
        "E2 product a_sigma_j*C_k=zeta*V give F(CD5)=alpha*zeta^6*VD7=alpha*VD7. "
        "Here alpha is the nonzero constant of the Thom unit; jV=0 removes its "
        "higher-j terms. No value of alpha or mixed differential parameter is chosen. "
        "Thus all outgoing maps of VD7 vanish in TateSS, even if its source image "
        "has already become a Tate boundary. The HFPSS d_r target lies in "
        "filtration 2+r>=r-1, where comparison is injective. Therefore every "
        "present HFPSS VD7 has zero outgoing d_r. D8 and forward g preserve this "
        "constraint, not liveness: incoming boundaries still take precedence. "
        "This is a new all-page consequence of CD5, distinct from the older "
        "page9-only certificate. It neither copies VD3's nonzero d17 by D4 nor "
        "determines an incoming d19 without a separate finite inventory."
    ),
    "transport_certificate": {
        "source_workspace_id": "ws_3sigma_i", "source_fact_id": "DER-3I-EULER-CD5-cycle",
        "source_power": 5, "source_bidegree": [41, 1], "action": "omega^2",
        "phi": "N_C4^Q8(dbar)*u_4sigma_k*g^-1*a_H", "applied_inverse": True,
        "phi_stem_shift": -16, "phi_filtration_shift": 0,
        "euler_multiplier": "a_sigma_j", "final_D_exponent": 0,
        "target_power": 7, "target_bidegree": [56, 2],
        "coefficient": {"omega_D_exponent": 5, "euler_zeta_exponent": 1,
                        "total_zeta_exponent_mod3": 0, "Thom_unit_value": None,
                        "Thom_unit_nonzero": True, "target_j_annihilated": True},
        "comparison": "Tate transport; injectivity is required only at the HFPSS differential target.",
    },
    "verification_certificate": {
        "status": "verified", "method": "CD5 cycle, permanent Phi/Euler transport and target comparison",
        "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j", "page": 2,
        "source_refs": ["formal_notes.tex:875", "DKLLW24 main.tex:488-510,833-878",
                        "DER-3I-EULER-CD5-cycle independent complete C4/Euler certificate"],
        "premises": ["DER-3I-EULER-CD5-cycle", "permanent Tate Phi inverse",
                     "permanent a_sigma_j", "DKLLW24 Lemma 2.6"],
        "source": {"bidegree": [56, 2], "pattern": "S02", "port": "0:0",
                   "torsion_order": 2, "j_annihilated": True},
        "target_comparison": {"differential_page": "r>=2", "filtration": "r+2",
                              "injective_from": "r-1", "source_injectivity_required": False},
        "d17_control": {"source_bidegree": [56, 2], "target_bidegree": [55, 19],
                        "target_pattern": "S73", "target": "Rk^4D^9", "zero": True},
        "high_translation": {"g_exponent": 6, "D_exponent": -16,
                             "source_bidegree": [48, 26], "d17_target_bidegree": [47, 43],
                             "forward_g_only": True, "incoming_survival_asserted": False},
        "separate_D3_d17_unchanged": True, "no_withdrawn_premise": True,
    },
}

_MIXED_D19_ID = "formal_diff_mixed_d19_x_D4_forced"
DERIVED_FORMAL_ARROWS += (
    _a("DER-MIX-D19-X-D4", "ws_sigma_i_2sigma_j", r"x^3D^4u_{\sigma_i+2\sigma_j}", (29, 3),
       r"(x+y)h_1k^5D^6u_{\sigma_i+2\sigma_j}", (28, 22), 19, "verified",
       "Independent CD5/Phi cycle and complete finite incoming inventory; compare table_Q8.tex:537",
       64, _MIXED_D19_ID),
)
_DERIVED_ENDPOINT_STYLES[_MIXED_D19_ID] = (
    {"e2_pattern": "S53", "two_valuation": 0, "j_order": 0},
    {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0},
)
_DERIVED_EVIDENCE[_MIXED_D19_ID] = {
    "required_admitted_premises": True,
    "source_status": "independently-verified-nonzero-unit", "source_blockers": [],
    "withdrawn_dependencies": [], "machine_verification_pending": [],
    "evidence_kind": "Phi-cycle-and-finite-incoming-exclusion",
    "derived_from": [_MIXED_VD7_CYCLE_FACT, "FN-MIX-001", "FN-MIX-004", "FN-MIX-004-even-zero",
                     "FN-MIX-005-Q-zero", "DER-MIX-D5-B-NONZERO", "DER-MIX-D9-P-D6",
                     "DER-MIX-EULER-H6-cycle", "DKLLW24 RO strong vanishing line"],
    "coefficient_parameter": {"id": "mixed_d19_XD4", "symbol": r"\lambda_{19}",
                              "domain": [1, 2, 3], "value": None, "frobenius_power": 0},
    "coefficient_constraint": "lambda_19 is nonzero; table_Q8:537 prints 1 but does not establish that unit in the current basis.",
    "coefficient_scope": "exact-port",
    "rank_one_unit_certificate": {
        "status": "verified", "kind": "isolated-finite-F4-isomorphism", "page": 19,
        "source_pattern": "S53", "target_pattern": "S02", "coefficient_scope": "exact-port",
    },
    "derivation": (
        "Put X=x^3u, V=(x+y)h1u, T=Vh1 in the mixed sector. The actual finite product "
        "(x+y)h2^2D3u=XD4 follows from xh2^2=0 and yh2^2=Dx^3; it is not XD3. "
        "The low source XD4 at (29,3) reaches E19 by the complete outgoing inventory below. "
        "Let Y=Vk5D6 at (28,22) and H=gY=g^6D^-16(VD7)=Vk6D9 at (48,26). "
        "The independent CD5/Phi certificate makes every outgoing map of H zero. "
        "Its finite incoming inventory excludes all odd lengths through 23 except 19. "
        "In the length-15 alternative, c!=1 gives a nonzero d5 image and c=1 gives "
        "the independently verified Euler/Phi d9 image with numerator zeta^2. "
        "Thus no particular mixed c or b is assigned. The source gXD4 at (49,7) "
        "also reaches E19: its d3/d7 incoming cells are empty and its possible d5 "
        "sources PD6 and the entire QD6 family have zero d5. Its outgoing maps "
        "before 19 vanish by the low-source equations and the permanent multiplier g. "
        "The RO strong vanishing line forces H to become a boundary by E24; hence "
        "d19(gXD4) is nonzero. Leibniz forces d19(XD4)=lambda_19*Y with lambda_19 "
        "a nonzero F4 unit. Nonzero gY detects Y; no global cancellation of g is used. "
        "Only D8 and forward g repeat the result. No D4 period, historical graph matching, "
        "withdrawn Ck argument, coefficient 1 assignment, or artificial point deletion is used."
    ),
    "verification_certificate": {
        "status": "verified", "method": "CD5/Phi outgoing cycle and complete finite incoming exclusion",
        "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j", "page": 19,
        "source_refs": ["DKLLW24 main.tex:488-510,943,949,1179-1198",
                        "formal_notes.tex:875,881-970", "DER-3I-EULER-CD5-cycle independent C4/Euler proof",
                        "table_Q8.tex:537 (comparison only; historical proof and coefficient not used)"],
        "low_source": {"bidegree": [29, 3], "pattern": "S53", "port": "0:0", "dimension": 1,
                       "representative": "XD4=x^3D4u", "torsion_order": 2, "j_annihilated": True},
        "low_target": {"bidegree": [28, 22], "pattern": "S02", "port": "0:0", "dimension": 1,
                       "representative": "Vk5D6", "survival": "Detected by the nonzero high target gY, not assumed."},
        "high_source": {"bidegree": [49, 7], "pattern": "S53", "port": "0:0", "dimension": 1},
        "high_target": {"bidegree": [48, 26], "pattern": "S02", "port": "0:0", "dimension": 1,
                        "outgoing_certificate": _MIXED_VD7_CYCLE_FACT},
        "target_translation": {"g_exponent": 6, "D_exponent": -16,
                               "forward_g_only": True, "invertible_in_HFPSS": False},
        "low_source_incoming": "d2/d3 cells (30,1),(30,0) are empty; r>3 needs negative filtration.",
        "low_source_outgoing": [
            {"pages": [3], "reason": "X=a_sigma_i*a_sigma_j^2 is an Euler product, and D is a 3-cycle."},
            {"pages": [5, 13], "target_bidegrees": [[28, 8], [28, 16]],
             "reason": "The entire U slots are absent after primitive d3, including the two-layer image of d3(C)."},
            {"pages": [7, 15], "target_bidegrees": [[28, 10], [28, 18]], "reason": "Empty E2 cells."},
            {"pages": [9, 17], "target_bidegrees": [[28, 12], [28, 20]],
             "reason": "The entire S00 slots, including local constants, are primitive d3 images."},
            {"pages": [11], "target_bidegrees": [[28, 14]],
             "reason": "Vk3D5 is the nonzero Phi D4 d9 source times g3D^-8 and is absent on E11."},
        ],
        "high_source_incoming": [
            {"page": 3, "source_bidegree": [50, 4], "reason": "Empty E2 cell."},
            {"page": 5, "source_bidegree": [50, 2], "patterns": ["S22Y", "S22H"],
             "reason": "PD6 and the entire QD6 family have independently proved zero d5; positive-j is included."},
            {"page": 7, "source_bidegree": [50, 0], "reason": "Empty E2 cell."},
        ],
        "high_source_outgoing": "Forward g times the low-source zero equations; not a claim that g is injective.",
        "incoming_inventory": [
            {"page": 3, "source_bidegree": [49, 23], "representative": "Xk5D9",
             "reason": "Euler product times 3-cycles D and k: zero outgoing d3."},
            {"page": 5, "source_bidegree": [49, 21], "representative": "Uh1k5D8",
             "reason": "Entire primitive d3 source module."},
            {"page": 7, "source_bidegree": [49, 19], "representative": "Tk4D8",
             "reason": "d5(Ak3D8)=c*Tk4D8 with independently established c nonzero."},
            {"page": 9, "source_bidegree": [49, 17], "representative": "Ck4D8",
             "reason": "The constant is a primitive d3 source; the completed positive-j ideal is a primitive d3 image."},
            {"page": 11, "source_bidegree": [49, 15], "representative": "Xk3D8",
             "reason": "g2*d5(PD)=Xk3D8."},
            {"page": 13, "source_bidegree": [49, 13], "representative": "Uh1k3D7",
             "reason": "Entire primitive d3 source module."},
            {"page": 15, "source_bidegree": [49, 11], "representative": "Tk2D7",
             "reason": "c!=1: nonzero (c+1)d5 image. c=1: independently verified zeta2*d9(PD6) image."},
            {"page": 17, "source_bidegree": [49, 9], "representative": "Ck2D7",
             "reason": "The constant is a primitive d3 source; the completed positive-j ideal is a primitive d3 image."},
            {"page": 19, "source_bidegree": [49, 7], "representative": "XkD7=gXD4",
             "reason": "The unique remaining source; its full earlier incoming/outgoing inventories are above."},
            {"page": 21, "source_bidegree": [49, 5], "representative": "Uh1kD6",
             "reason": "Entire primitive d3 source module."},
            {"page": 23, "source_bidegree": [49, 3], "representative": "TD6",
             "reason": "Euler-H6 cycle multiplied by the permanent h1: zero outgoing."},
        ],
        "conditional_premise": {"fact_id": "DER-MIX-D9-P-D6", "condition": "c=1",
                                "coefficient": 3, "independent_of": ["b", "row537", "Jan29"]},
        "even_pages": "All corresponding E2 cells are empty by parity.",
        "vanishing_line": {"filtration": 23, "empty_from_page": 24, "all_RO_gradings": True},
        "forward_detection": "The low target filtration22 is in the E19 Tate comparison range. Permanent Tate g detects its forward images; nonzero differentials detect their source images. No negative-g HFPSS translation is used.",
        "coefficient_result": "nonzero unit only", "no_withdrawn_premise": True,
    },
}

_TATE_CYCLE_EVIDENCE = {
    "DER-3I-TATE-W-cycle": {
        "source_status": "independently-verified", "source_blockers": [],
        "machine_verification_pending": "",
        "evidence_kind": "Euler-product-and-negative-source-Tate-derived",
        "cycle_constraint": "outgoing-only",
        "coefficient_scope": "constant-two-multiples",
        "derived_from": ["DKLLW24 Table 9 d13 at (31,1)", "DKLLW24 Lemma 2.6",
                         "DKLLW24 hidden h1 extension", "Q8 sign Euler cube in group cohomology"],
        "derivation": (
            "Let e=a_sigma_i, C=(h1+xv1)u_sigma_i and w=2v1^2 D u_3sigma_i. "
            "The actual E2 identities are e^3=0 and e^2 C h1=2k v1^2 u_3sigma_i. "
            "Table 9 gives d13(e D^4)=k^3 C h1 D^5. Multiplication by the permanent "
            "Euler square gives Z=2v1^2 k^4 D^5 u_3sigma_i=0 already on E13. "
            "Before E13 this product of cycles has no outgoing differential. In TateSS "
            "Z=g^4 D^-8 w; this multiplier is a permanent unit, so the nonzero E2 "
            "Tate class w is hit at some q in {3,5,7,9,11} from filtration -q. "
            "No particular q or replacement differential is asserted. Comparison is "
            "injective at the target filtration r of every potential d_r(w), hence all "
            "HFPSS outgoing differentials on w vanish. In filtration zero there is no "
            "HFPSS incoming differential. Forward g multiples inherit only zero outgoing "
            "differentials and may be hit; never cancel g in HFPSS or erase its point "
            "using a negative-source Tate boundary. This proof does not use Jan.29."
        ),
        "product_certificate": {
            "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
            "euler_cube": (
                "In the sign-twisted integral resolution d2=(0,2), d3=0, so H3(Z_sigma_i)=Z/2 "
                "and reduction mod 2 is injective. A normalized Q8 bar-cochain computation "
                "makes each nontrivial F2 character cube a boundary. Thus e_Z^3=0, and its "
                "image in E2 is zero. This does not say the topological Euler class is zero."
            ),
            "hidden_product": (
                "H3(pi2 E tensor sigma_i) is killed by 2: the central element acts as -1 "
                "on pi2 E but trivially on group cohomology. Reduction is injective; "
                "xy=0, v1 y=0 and h1 y=v1 x^2 give e^2 C=x^2h1 u_3sigma_i. "
                "The actual hidden h1 multiplication then gives e^2 C h1=2k v1^2 u_3sigma_i."
            ),
            "source_ref": "DKLLW24 main.tex:937-949,1094-1111,2751-2756,2777-2784",
        },
        "comparison_certificate": {
            "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
            "status": "verified", "spectral_sequence": "tate",
            "page_upper_bound": 11, "possible_pages": [3, 5, 7, 9, 11],
            "tate_zero_by_page": 13, "source_bidegree": [13, "-q"],
            "target_bidegree": [12, 0], "target_representative": "2v1^2 D u_3sigma_i",
            "multiplier_to_positive_product": "g^4 D^-8",
            "positive_product_bidegree": [28, 16],
            "comparison_range": "E_r: surjective in f>=0, injective/isomorphic in f>=r-1",
            "interpretation": "Negative-source Tate boundary implies zero HFPSS outgoing; not an HFPSS death.",
        },
    },
}

# The Euler13 product proves an earlier boundary. Enumerating its possible
# sources determines d11 on CD1; it does not repeat on CD5 or assert that the
# low positive-j ideal is an HFPSS boundary.
_CD1_D11_FACT = "DER-3I-EULER-CD1-D11"
_CD1_D11_ROW = "formal_diff_three_d11_c_D1_euler_forced"
_DERIVED_ENDPOINT_STYLES[_CD1_D11_ROW] = (
    {"e2_pattern": "S11", "two_valuation": 0, "j_order": 0},
    {"e2_pattern": "S40", "two_valuation": 1, "j_order": 0},
)
_DERIVED_EVIDENCE[_CD1_D11_ROW] = {
    "source_status": "independently-verified", "source_blockers": [],
    "withdrawn_dependencies": [], "machine_verification_pending": [],
    "evidence_kind": "Euler13-product-and-complete-incoming-inventory",
    "coefficient_scope": "exact-port",
    "forward_period": {"multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True},
    "derived_from": ["DKLLW24 Table 9 d13", "FN-3I-001", "FN-3I-003", "FN-3I-005",
                     "DER-3I-LEIBNIZ-TD1-D9-zero", "DER-3I-EULER-CD1-D9-zero",
                     "Q8 sign Euler cube in group cohomology", "DKLLW24 hidden h1 extension"],
    "coefficient_parameter": {"id": "three_sigma_d11_CD1", "symbol": r"\lambda_{11}",
                              "value": 1, "domain": [1], "frobenius_power": 0,
                              "fixed_reason": "pure-sigma-i-galois-fixed"},
    "derivation": (
        "Write e=a_sigma_i, C=(h1+xv1)u_3sigma_i, U=v1^2u_3sigma_i, g=kD3. "
        "Table 9 gives d13(eD4)=Theta=k3 C_sigma h1 D5. The actual E2 relations "
        "e^3=0 and e^2 C_sigma h1=2kU give K=e^2 Theta=2Uk4D5=0 already on E13. "
        "Before E13 the product has zero outgoing because both factors are cycles. "
        "K's incoming sources at r=3,5,7,9,11 are respectively Ck3D5 (zero d3), "
        "Xk2D5 (d5 coefficient 1+5-6=0), Uh1k2D4 (full primitive d3 source), "
        "TkD4=gTD1 (independent zero d9), and CkD4=gCD1. Even-page cells are empty. "
        "Thus the nonzero finite E11 line K must be the d11 image of gCD1. "
        "CD1 reaches E11: d3=0, the d5 target is empty, the whole d7 target is a "
        "primitive d3 image, and d9=0 is independently proved. The sole target is "
        "W'=2Uk3D2; gW'=K proves W' nonzero without cancelling g. Leibniz forces "
        "d11(CD1)=lambda W', and psi-fixed source/target give lambda^2=lambda, "
        "hence lambda=1. The positive-j ideal has zero outgoing by the independent "
        "negative-source Tate d3(k^-1 Uh1^2)=jCD1. Only D8 and forward g translate "
        "this equation; CD5 and the withdrawn January d19/d23 are not premises."
    ),
    "verification_certificate": {
        "status": "verified", "method": "Euler13 product and complete finite incoming inventory",
        "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "page": 11,
        "premises": ["DKLLW24 Table 9 d13", "FN-3I-001", "FN-3I-003", "FN-3I-005",
                     "DER-3I-LEIBNIZ-TD1-D9-zero", "DER-3I-EULER-CD1-D9-zero",
                     "actual Euler and hidden h1 products", "psi-fixed pure sigma_i basis"],
        "source_refs": ["DKLLW24 main.tex:488-510,1094-1111,2365-2369,2460",
                        "formal_notes.tex:678-705,730-762"],
        "product_certificate": deepcopy(_TATE_CYCLE_EVIDENCE["DER-3I-TATE-W-cycle"]["product_certificate"]),
        "Euler13_equation": {"published_source": [31, 1], "published_target": [30, 14],
                             "product": "K=e^2 Theta=2Uk4D5", "bidegree": [28, 16],
                             "zero_on_page": 13, "zero_outgoing_before": 13,
                             "source_product": "e^3D4=0 on E2, not an empty cell"},
        "incoming_inventory": [
            {"page": 3, "source": "Ck3D5", "bidegree": [29, 13], "disposition": "zero d3"},
            {"page": 5, "source": "Xk2D5", "bidegree": [29, 11], "disposition": "zero d5: 1+5-6=0",
             "same_page_image": {"source": "PkD4", "bidegree": [30, 6], "fact": "FN-3I-003"}},
            {"page": 7, "source": "Uh1k2D4", "bidegree": [29, 9], "disposition": "whole primitive d3 source"},
            {"page": 9, "source": "TkD4=gTD1", "bidegree": [29, 7], "disposition": "independent zero d9"},
            {"page": 11, "source": "CkD4=gCD1", "bidegree": [29, 5], "disposition": "sole remaining source"},
        ],
        "source_survival": {"bidegree": [9, 1], "pattern": "S11", "port": "0:0",
                            "incoming": "negative filtration; even source empty",
                            "outgoing": {"3": "zero", "5": "empty target", "7": "whole primitive d3 image", "9": "independent zero"}},
        "finite_target": {"bidegree": [8, 12], "pattern": "S40", "port": "1:0", "dimension": 1,
                          "coefficient_ring": "F4{2Uk3D2}", "relation": "2j kU=0 and 4kU=0"},
        "target_detection": {"multiplier": "g", "image": [28, 16], "nonzero_on_page": 11,
                             "argument": "A zero target would have zero product; no inverse of g is used."},
        "coefficient_equation": "lambda=lambda^2 and lambda!=0 imply lambda=1; retain the Witt scalar 2",
        "kernel": "jF4[[j]]{CD1}",
        "period": {"D_power": 8, "stem": 64, "forward_g": True, "D5_block_inferred": False},
        "no_withdrawn_premise": True, "uses_vanishing_line": False,
    },
}
_AD2_D19_ROW = "formal_diff_three_d19_a_D2_euler_forced"
_DERIVED_ENDPOINT_STYLES[_AD2_D19_ROW] = (
    {"e2_pattern": "S62", "two_valuation": 0, "j_order": 0},
    {"e2_pattern": "S11", "two_valuation": 0, "j_order": 0},
)
_DERIVED_EVIDENCE[_AD2_D19_ROW] = {
    "source_status": "independently-verified", "source_blockers": [],
    "withdrawn_dependencies": [], "machine_verification_pending": [],
    "evidence_kind": "Euler-cofiber-and-complete-homotopy-filtration",
    "coefficient_scope": "exact-port",
    "forward_period": {"multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True},
    "render_equation_aliases": [{"fact_id": "FN-3I-010", "page": 19,
                                 "status": "review", "scope": "same-equation-only"}],
    "derived_from": ["FN-3I-001", "FN-3I-002", "FN-3I-003", "FN-3I-005", "FN-3I-006",
                     "DER-3I-D5-A-EVEN", "DER-3I-D9-C", "DER-3I-D9-P", "DER-3I-D9-Q",
                     "DER-3I-EULER-CD5-cycle", "BBHS20 Table 4 integer stem 13",
                     "DKLLW24 Table 8 D2h1 d9", "DKLLW24 Corollary 2.22",
                     "DKLLW24 strong vanishing theorem"],
    "coefficient_parameter": {"id": "three_sigma_d19_AD2", "symbol": r"\lambda_{19,2}",
                              "value": 1, "domain": [1], "frobenius_power": 0,
                              "fixed_reason": "pure-sigma-i-galois-fixed"},
    "derivation": (
        "Set A=(x2+y2)u, C=(h1+xv1)u, B2=Ck5D4 and g=kD3. The complete incoming "
        "inventory leaves only AD2 as a possible source of the finite constant B2 at (13,21). "
        "Its positive-j ideal is already a primitive d3 image. B2=g5D^-16 CD5 has zero "
        "outgoing by the independent CD5 certificate. If d19(AD2)=0, B2 detects a nonzero "
        "b in F21 pi_(16-3sigma_i). For H=ker(sigma_i)=C4<i>, Euler cofiber exactness "
        "gives pi13(E^hH) -> pi_(16-3sigma_i) -> pi_(16-4sigma_i). BBHS Table 4 gives "
        "the whole integer pi13(E^hC4)=0, so the last Euler map is injective. The genuine "
        "filtration-zero unit u_4sigma_i identifies its target with pi12. Its F22 is zero: "
        "the only filtration22 direction xh1k5D4 is the Table 8 d9(g3D^-8 D2h1) image, "
        "and all higher filtration vanishes by the strong theorem. Thus e*b lies in zero "
        "F22, contradicting injectivity. This forces nonzero d19; psi fixes the pure bases "
        "and normalizes its unit to 1. No leading Euler product or hidden-extension guess "
        "is required, nor the withdrawn January proof. Only D8 and forward g repeat this "
        "map. AD6 has a separate zero d19, not a D4 copy."
    ),
    "verification_certificate": {
        "status": "verified", "method": "Euler cofiber and complete homotopy filtration",
        "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "page": 19,
        "source_refs": ["BBHS20 pp3425,3438-3445,3470 Table 4 (upper integer table)",
                        "DKLLW24 main.tex:869-878,1311-1315,1895",
                        "formal_notes.tex:678-796; independent CD5 cycle certificate"],
        "euler_cofiber": {"subgroup": "ker(sigma_i)=C4<i>", "source_degree": "16-3sigma_i",
                          "target_degree": "16-4sigma_i", "restricted_degree": 13,
                          "left_group": "pi13(E^hC4)=0", "consequence": "Euler multiplication is injective"},
        "coefficient_descent": {
            "extension": "W(F4) -> W(algebraic closure of F2)", "faithfully_flat": True,
            "argument": "Finite-group cochains commute with completed unramified flat base change; the uniform strong bound gives finite separated filtration and detects zero abutment. C4 fixes Witt coefficients. This is not taking Galois homotopy fixed points.",
            "embedding": "After unramified extension the height-two formal groups agree and C4 subgroups are conjugate (BBHS p3425).",
            "scope": "Auxiliary completed base-change argument, not an extra assertion printed in BBHS Table 4.",
            "comparison_steps": [
                "Use the equivariant Lubin-Tate coefficient extension W(F4)[[u1]] -> W(algebraic closure of F2)[[u1]], with the C4 action transported by conjugacy. The small stabilizer fixes the Witt coefficients.",
                "Compute continuous C4 cochains using the invariant maximal-ideal-adic coefficient tower. At each finite level, finite products and the cochain differential commute with flat unramified scalar extension; use completed, not ordinary, tensor products on passage to the limit.",
                "The finite-level coefficient tower is Mittag-Leffler. Its completed cohomology comparison gives the natural HFPSS base-change map, and compatibility of differentials gives the page-by-page comparison.",
                "Use the uniform strong horizontal bound and separated convergence to pass from finitely many associated-graded pieces in each total degree to the abutment. Faithfulness detects a nonzero completed piece, so a zero extended pi13 implies zero pi13 over F4.",
            ],
            "forbidden_shortcuts": ["Ordinary tensor does not replace completed tensor for the power-series coefficient ring.",
                                    "Flatness alone does not exchange an unbounded homotopy-fixed-point totalization.",
                                    "This comparison is not descent by taking Galois homotopy fixed points."],
        },
        "integer_filtration": {"stem": 12, "zero_from_filtration": 22,
                               "filtration22_basis": ["xh1k5D4"],
                               "differential": {"page": 9, "source": [13, 13], "target": [12, 22],
                                                "published_source": "D2h1", "multiplier": "g3D^-8"},
                               "higher_filtration": "Zero from 23 by the strong vanishing theorem.",
                               "period_unit": "u_4sigma_i", "unit_and_inverse_filtration": 0,
                               "hidden_extensions": "The entire F22 subgroup is zero, not merely its leading associated-graded piece."},
        "source_survival": {"bidegree": [14, 2], "pattern": "S62", "port": "0:0",
                            "incoming": "d2 source empty; all later sources have negative filtration.",
                            "outgoing": {"3": "A zero, D an E3 unit", "5": "independent even-A zero",
                                         "7": "whole primitive d3 source", "9": "nonzero d5 image of PkD2",
                                         "11": "Ck3D3 supports independent d9", "13": "d5(Ak2D3)",
                                         "15": "whole primitive d3 source", "17": "Xk4D4 supports nonzero d5"}},
        "target": {"bidegree": [13, 21], "pattern": "S11", "port": "0:0", "dimension": 1,
                   "positive_j": "Primitive d3 image; not part of this d19 image.",
                   "outgoing_certificate": "B2=g5D^-16 CD5; only zero outgoing, not survival override."},
        "incoming_inventory": [
            {"page": 3, "source": [14, 18], "patterns": ["S62", "S62V"], "reason": "A zero; primitive direction maps only to positive-j B2"},
            {"page": 5, "source": [14, 16], "patterns": [], "reason": "empty"},
            {"page": 7, "source": [14, 14], "patterns": ["S22Y", "S22H"], "reason": "rank-one P/Q quotient supports independent nonzero d9"},
            {"page": 9, "source": [14, 12], "patterns": [], "reason": "empty"},
            {"page": 11, "source": [14, 10], "patterns": ["S62", "S62V"], "reason": "A supports FN002 d5; other column supports primitive d3"},
            {"page": 13, "source": [14, 8], "patterns": [], "reason": "empty"},
            {"page": 15, "source": [14, 6], "patterns": ["S22Y", "S22H"], "reason": "P supports d5; Q is d5(aD2)"},
            {"page": 17, "source": [14, 4], "patterns": [], "reason": "empty"},
            {"page": 19, "source": [14, 2], "patterns": ["S62", "S62V"], "reason": "only finite A survives; other column supports primitive d3"},
            {"page": 21, "source": [14, 0], "patterns": [], "reason": "empty; r>21 has negative source filtration"},
        ],
        "h1_product": {"source": [15, 3], "target": [14, 22], "result": "zero on E19",
                       "earlier_image": {"page": 5, "source": [15, 17], "target": [14, 22],
                                         "formula": "d5(a k4D4)=Qk5D4"}},
        "period": {"D_power": 8, "stem": 64, "forward_g": True, "D6_block_inferred": False},
        "no_withdrawn_premise": True, "uses_vanishing_line": True, "uses_clipping": False,
    },
}

_THREE_CD1_ZERO_EVIDENCE = {}
for _fact, _label, _grade, _page, _pattern, _j in (
    ("DER-3I-CD1-D11-J-zero", r"j(h_1+xv_1)Du_{3\sigma_i}", (9, 1), 11, "S11", 1),
    ("DER-3I-AD6-D19-zero", r"(x^2+y^2)D^6u_{3\sigma_i}", (46, 2), 19, "S62", 0),
):
    ZERO_AND_PERMANENT_CLAIMS += ((
        _fact, "ws_3sigma_i", "zero-differential", rf"d_{{{_page}}}({_label})=0",
        _grade, _page, "verified", "DKLLW24 Table 9; Lemma 2.6; independent CD1 d11 and finite target audit",
    ),)
    _ZERO_CLAIM_SOURCES[_fact] = (_label, 64, _fact)
    _ZERO_ENDPOINT_STYLES[_fact] = {"e2_pattern": _pattern, "two_valuation": 0, "j_order": _j}
    _THREE_CD1_ZERO_EVIDENCE[_fact] = {
        "source_status": "independently-verified", "source_blockers": [],
        "withdrawn_dependencies": [], "machine_verification_pending": [],
        "evidence_kind": "negative-source-Tate-comparison" if _j else "verified-earlier-target-differential",
        "cycle_constraint": "outgoing-only", "coefficient_scope": "exact-port",
        "source_component": "positive-j" if _j else "constant",
        "derived_from": ["FN-3I-001", "DKLLW24 Lemma 2.6"] if _j else [_CD1_D11_FACT],
        "derivation": (
            "Tate d3(k^-1 Uh1^2)=jCD1 has negative source filtration; comparison gives zero HFPSS "
            "outgoing on the full positive-j ideal. Forward g images already hit by primitive d3 remain boundaries."
            if _j else
            "The proposed d19 target Ck5D8=g5D^-8 CD1 supports the verified nonzero d11 "
            "to 2Uk8D9. Its positive-j ideal is already a primitive d3 image, so the whole target "
            "is absent from E12. Hence d19(AD6)=0; this neither clips AD6 nor decides d19(AD2)."
        ),
        "verification_certificate": {
            "status": "verified", "method": "Primitive d3 and negative-source Tate comparison" if _j else "Earlier target differential",
            "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "page": _page,
            "premises": ["FN-3I-001", "DKLLW24 Lemma 2.6"] if _j else [_CD1_D11_FACT],
            "source": {"bidegree": list(_grade), "pattern": _pattern, "port": f"0:{_j}"},
            "tate_source_bidegree": [10, -2] if _j else None,
            "tate_target_bidegree": [9, 1] if _j else None,
            "target_differential": None if _j else {"source": [45, 21], "target": [44, 32], "page": 11},
            "no_withdrawn_premise": True, "survival_override": False,
        },
    }

for _power, _source_differential in (
    (3, "diff_three_d9_25"),
    (7, "formal_diff_three_d9_t_D7_sibling"),
):
    _fact = f"DER-3I-TATE-U-D{_power}-cycle"
    _label = rf"2v_1^2D^{_power}u_{{3\sigma_i}}"
    _premises = ["FN-3I-007", "FN-2I-011", f"DER-2I-TATE-H{_power - 1}-cycle",
                 "DKLLW24 Lemma 2.6", "DKLLW24 Tate method"]
    ZERO_AND_PERMANENT_CLAIMS += ((
        _fact, "ws_3sigma_i", "permanent-cycle",
        rf"{_label}\text{{ supports no differential}}",
        (8 * _power + 4, 0), 2, "verified",
        "formal_notes.tex:487-494,764-775; DKLLW24 main.tex:488-510; independently verified FN007 D block",
    ),)
    _ZERO_CLAIM_SOURCES[_fact] = (_label, 64, _fact)
    _ZERO_ENDPOINT_STYLES[_fact] = {"e2_pattern": "S40", "two_valuation": 1, "j_order": 0}
    _TATE_CYCLE_EVIDENCE[_fact] = {
        "source_status": "independently-verified", "source_blockers": [],
        "machine_verification_pending": [], "withdrawn_dependencies": [],
        "evidence_kind": "negative-source-Tate-derived", "cycle_constraint": "outgoing-only",
        "coefficient_scope": "constant-two-multiples", "derived_from": _premises,
        "source_fact_id": "FN-3I-007", "source_differential_id": _source_differential,
        "D_block": _power,
        "derivation": (
            "Write T=(x+y)h1^2u_3sigma_i and U=v1^2u_3sigma_i. "
            f"The independently verified FN007 D{_power} block gives "
            f"d9(TD^{_power})=2Uk^3D^{_power + 1}. Its proof uses the separate "
            f"H{_power - 1} Tate cycle, Table 8 d9(Dh1), permanent Euler multiplication "
            "and finite constant Witt target survival, not a permanent D4 or a later d23. "
            "Only in TateSS multiply by the permanent unit g^-3 D8=k^-3 D^-1. "
            f"This gives d9(Tk^-3D^{_power - 1})=2UD^{_power}, at "
            f"({8 * _power + 5},-9)->({8 * _power + 4},0). Tate comparison gives "
            "zero HFPSS outgoing differentials on the constant two-layer and its additive "
            "two-multiples. Filtration zero excludes HFPSS incoming at the seed, but this "
            "does not remove its point using a negative-source Tate boundary. Forward g "
            "images only inherit zero outgoing and can receive FN007 itself: g^3 D^-8 "
            "times the seed is its positive-filtration target. Repeat each independent "
            "block by D8; do not cancel g in HFPSS or include an unrelated positive-j tail."
        ),
        "verification_certificate": {
            "status": "verified", "method": "Verified odd d9 and negative-source Tate comparison",
            "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
            "premises": _premises, "source_fact_id": "FN-3I-007",
            "source_differential_id": _source_differential, "D_block": _power,
            "source_verification": deepcopy(_THREE_ODD_D9_CERTIFICATE),
            "coefficient_scope": "constant-two-multiples",
            "source_ref": "formal_notes.tex:487-494,764-775; DKLLW24 main.tex:488-510,1094-1111,1889-1890",
        },
        "comparison_certificate": {
            "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
            "status": "verified", "spectral_sequence": "tate", "page": 9,
            "tate_zero_by_page": 10, "source_differential_id": _source_differential,
            "source_bidegree": [8 * _power + 5, -9],
            "target_bidegree": [8 * _power + 4, 0],
            "source_formula": rf"\{{x+y\}}h_1^2k^{{-3}}D^{_power - 1}u_{{3\sigma_i}}",
            "target_formula": _label,
            "translation": {"g_exponent": -3, "D_exponent": 8, "permanent_unit": True},
            "positive_source_bidegree": [8 * _power + 1, 3],
            "positive_target_bidegree": [8 * _power, 12],
            "interpretation": "Zero outgoing only; genuine forward-g HFPSS incoming maps remain allowed.",
        },
    }

for _power in (2, 6):
    _cube_power = _power - 1
    _cube_fact = f"DER-2I-TATE-H2CUBE-D{_cube_power}-cycle"
    _ZERO_CLAIM_SOURCES[_cube_fact] = (
        rf"h_2^3D^{_cube_power}u_{{2\sigma_i}}", 64, _cube_fact,
    )
    _ZERO_ENDPOINT_STYLES[_cube_fact] = {"e2_pattern": "I13", "two_valuation": 0, "j_order": 0}
    _TATE_CYCLE_EVIDENCE[_cube_fact] = {
        "source_status": "independently-verified", "source_blockers": [],
        "machine_verification_pending": [], "evidence_kind": "negative-source-Tate-derived",
        "cycle_constraint": "outgoing-only", "coefficient_scope": "constant-two-multiples",
        "derived_from": ["FN-2I-011", "DKLLW24 Lemma 2.6", "DKLLW24 Tate method"],
        "derivation": (
            f"Use FN011's independently proved D{7 if _power == 2 else 3} block, "
            f"multiplied by g^-2{' D8' if _power == 6 else ''} in Tate. It gives "
            f"d9(h1^2 k^-2 D^{_cube_power}u)=h2^3 D^{_cube_power}u, at "
            f"({8 * _power + 2},-6)->({8 * _power + 1},3). The permanent Tate unit "
            "and negative-source method certify zero HFPSS outgoing of the I13 "
            "constant only. Together with the independently certified I13X+I13 "
            "sum this determines the two-dimensional outgoing map, not merely "
            "a proper subspace. Neither certificate protects incoming images. "
            "FN011's D7 block uses H6 and Table 8, not FN014."
        ),
        "comparison_certificate": {
            "scope": "source-workspace", "source_workspace_id": "ws_2sigma_i",
            "status": "verified", "spectral_sequence": "tate", "page": 9,
            "source_bidegree": [8 * _power + 2, -6],
            "target_bidegree": [8 * _power + 1, 3],
            "translation": {"g_exponent": -2, "D_exponent": 8 if _power == 6 else 0,
                            "permanent_unit": True},
            "interpretation": "Zero outgoing of I13; no negative-filtration HFPSS arrow or immunity to incoming.",
        },
    }
    _ah_fact = f"DER-2I-TATE-AH2-D{_power}-cycle"
    _ZERO_CLAIM_SOURCES[_ah_fact] = (
        rf"\{{x^2+y^2\}}h_2D^{_power}u_{{2\sigma_i}}", 64, _ah_fact,
    )
    # Keep the parser's I13X+I13 vector. A single-pattern override would
    # incorrectly certify each summand rather than their coupled sum.
    _TATE_CYCLE_EVIDENCE[_ah_fact] = {
        "source_status": "independently-verified", "source_blockers": [],
        "machine_verification_pending": [], "evidence_kind": "negative-source-Tate-derived",
        "cycle_constraint": "outgoing-only", "coefficient_scope": "constant-two-multiples",
        "derived_from": ["FN-2I-003", "DKLLW24 Lemma 2.6", "DKLLW24 Tate method"],
        "derivation": (
            f"Translate FN003 d5(A D^{_power + 3}u)=kAh2D^{_power + 3}u by g^-1 "
            f"in Tate. This gives a source at ({8 * _power + 2},-2) and target "
            f"P=Ah2D^{_power}u at ({8 * _power + 1},3), A=x^2+y^2. The negative-source "
            "Tate method gives zero HFPSS outgoing maps of this sum, not a deletion "
            "or zero maps on each summand. Forward g images may still be hit, "
            "including by FN003 itself. This certificate is independent of FN014."
        ),
        "comparison_certificate": {
            "scope": "source-workspace", "source_workspace_id": "ws_2sigma_i",
            "status": "verified", "spectral_sequence": "tate", "page": 5,
            "source_bidegree": [8 * _power + 2, -2],
            "target_bidegree": [8 * _power + 1, 3],
            "translation": {"g_exponent": -1, "D_exponent": 0, "permanent_unit": True},
            "interpretation": "Zero outgoing of the coupled vector only; incoming maps remain allowed.",
        },
    }
    _h_fact = f"DER-2I-TATE-H{_power}-cycle"
    _ZERO_CLAIM_SOURCES[_h_fact] = (rf"h_1D^{_power}u_{{2\sigma_i}}", 64, _h_fact)
    _ZERO_ENDPOINT_STYLES[_h_fact] = {"e2_pattern": "I11", "two_valuation": 0, "j_order": 0}
    _TATE_CYCLE_EVIDENCE[_h_fact] = {
        "source_status": "independently-verified", "source_blockers": [],
        "machine_verification_pending": [], "evidence_kind": "negative-source-Tate-derived",
        "cycle_constraint": "outgoing-only", "coefficient_scope": "constant-two-multiples",
        "derived_from": ["FN-2I-009", "DKLLW24 Lemma 2.6", "DKLLW24 Tate method"],
        "derivation": (
            f"Translate FN009's D{_power} block in Tate by the permanent unit g^-3 D8. "
            f"The resulting d11 has source ({8 * _power + 2},-10) and target "
            f"H{_power}=h1D^{_power}u at ({8 * _power + 1},1). The negative-source "
            "Tate method gives zero HFPSS outgoing differentials, not an HFPSS death. "
            "Filtration one excludes incoming at the seed. Forward g multiples only "
            "inherit zero outgoing: they may be hit, in particular by FN009 itself. "
            "The other 32-stem block has a separate certificate; repetition here uses D8."
        ),
        "verification_certificate": deepcopy(_VERIFIED_FORMAL_CERTIFICATES["FN-2I-009"]),
        "comparison_certificate": {
            "scope": "source-workspace", "source_workspace_id": "ws_2sigma_i",
            "status": "verified", "spectral_sequence": "tate", "page": 11,
            "source_bidegree": [8 * _power + 2, -10], "target_bidegree": [8 * _power + 1, 1],
            "translation": {"g_exponent": -3, "D_exponent": 8, "permanent_unit": True},
            "interpretation": "Zero outgoing only; forward-g images can still be hit in HFPSS.",
        },
    }
    _j_fact = f"DER-2I-TATE-JD{_power}-cycle"
    _ZERO_CLAIM_SOURCES[_j_fact] = (rf"jD^{_power}u_{{2\sigma_i}}", 64, _j_fact)
    _ZERO_ENDPOINT_STYLES[_j_fact] = {"e2_pattern": "I00", "two_valuation": 0, "j_order": 1}
    _TATE_CYCLE_EVIDENCE[_j_fact] = {
        "source_status": "independently-verified", "source_blockers": [],
        "machine_verification_pending": [], "evidence_kind": "negative-source-Tate-derived",
        "cycle_constraint": "outgoing-only", "coefficient_scope": "constant-two-multiples",
        "source_component": "positive-j", "covers": f"j^n D^{_power}u for n>=1, with two-multiples",
        "derived_from": ["FN-2I-001", "DKLLW24 Table 8 primitive d3", "DKLLW24 Lemma 2.6",
                         "DKLLW24 Proposition inftybo (main.tex:1391-1398)"],
        "derivation": (
            f"In TateSS d3(v1^2 h1 k^-1 D^{_power - 1}u)=v1^4 D^{_power - 1}u=jD^{_power}u. "
            "This follows from the primitive h1-multiplied integer d3 and x^2v1^2h1=0, "
            "so the extra Thom term is zero. The source filtration is -3 and the target "
            "filtration zero. Tate comparison gives zero HFPSS outgoing, not a deletion. "
            "j=v1^4 D^-1 is permanent, so multiplication by j^(n-1) proves this for the "
            "whole positive-j ideal. This certificate does not constrain the constant D^m term."
        ),
        "comparison_certificate": {
            "scope": "source-workspace", "source_workspace_id": "ws_2sigma_i",
            "status": "verified", "spectral_sequence": "tate", "page": 3,
            "source_bidegree": [8 * _power + 1, -3], "target_bidegree": [8 * _power, 0],
            "interpretation": "Positive-j ideal only; negative-source Tate boundary is not an HFPSS death.",
        },
    }

for _sector, _workspace_id, _thom in (
    ("3I", "ws_3sigma_i", r"3\sigma_i"),
    ("MIX", "ws_sigma_i_2sigma_j", r"\sigma_i+2\sigma_j"),
):
    for _power in (2, 6):
        _fact = f"DER-{_sector}-EULER-H{_power}-cycle"
        _source_fact = f"DER-2I-TATE-H{_power}-cycle"
        _label = rf"\{{x+y\}}h_1D^{_power}u_{{{_thom}}}"
        _premises = [_source_fact, "FN-2I-009", "DKLLW24 Lemma 5.2", "DKLLW24 Lemma 2.6"]
        _action = "identity" if _sector == "3I" else "omega"
        ZERO_AND_PERMANENT_CLAIMS += ((
            _fact, _workspace_id, "permanent-cycle",
            rf"{_label}\text{{ supports no differential}}",
            (8 * _power, 2), 2, "verified",
            f"{_source_fact}; DKLLW24 main.tex:1972-1976; permanent Euler multiplication",
        ),)
        _ZERO_CLAIM_SOURCES[_fact] = (_label, 64, _fact)
        _ZERO_ENDPOINT_STYLES[_fact] = {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0}
        _TATE_CYCLE_EVIDENCE[_fact] = {
            "source_status": "independently-verified", "source_blockers": [],
            "machine_verification_pending": [], "withdrawn_dependencies": [],
            "evidence_kind": "permanent-Euler-cycle-image",
            "cycle_constraint": "outgoing-only", "coefficient_scope": "exact-port",
            "derived_from": _premises,
            "source_fact_id": _source_fact,
            "derivation": (
                f"The independently certified H{_power}=h1D^{_power}u_2sigma_i has zero "
                "outgoing differentials by negative-source Tate comparison. "
                + ("Apply omega to transport it to the 2sigma_j sector; a common nonzero "
                   "F4/Thom unit does not change a zero outgoing map. " if _sector == "MIX" else "")
                + f"Multiply by the permanent Euler class a_sigma_i=(x+y)u_sigma_i. "
                f"The resulting finite S02 port is (x+y)h1D^{_power}u_{_thom} "
                f"at ({8 * _power},2). This is an exact product, not a new independent generator. "
                "The filtration-two seed has no incoming odd differential; its possible d2 "
                "source has odd total degree and is zero. Forward g images inherit only "
                "zero outgoing maps and can still be boundaries. The two D blocks are "
                "certified separately and repeat by D8, never by an assumed permanent D4."
            ),
            "verification_certificate": {
                "status": "verified", "method": "Permanent Euler image of an independently certified cycle",
                "scope": "source-workspace", "source_workspace_id": _workspace_id,
                "premises": _premises,
                "source_fact_id": _source_fact,
                "source_bidegree": [8 * _power + 1, 1],
                "target_bidegree": [8 * _power, 2],
                "transport": _action,
                "euler_multiplier": "a_sigma_i=(x+y)u_sigma_i",
                "coefficient_scope": "exact-port",
                "source_ref": "DKLLW24 main.tex:1972-1976; formal_notes.tex:450-469",
            },
            "product_certificate": {
                "scope": "source-workspace", "source_workspace_id": _workspace_id,
                "source_fact_id": _source_fact, "action": _action,
                "multiplier": "a_sigma_i", "target_pattern": "S02",
                "target_bidegree": [8 * _power, 2],
                "interpretation": "Zero outgoing of the exact finite port only; incoming maps remain allowed.",
            },
        }

_POSITIVE_J_ZERO_EVIDENCE = {}
for _power in (2, 3, 6, 7):
    for _column, _pattern, _filtration in (("C", "S11", 1), ("Q", "S22H", 2)):
        if _power % 2 and _column != "C":
            continue
        _fact = f"DER-3I-D9-J{_column}-D{_power}-zero"
        _ZERO_CLAIM_SOURCES[_fact] = (
            rf"j\{{h_1+xv_1\}}{'h_1' if _column == 'Q' else ''}D^{_power}u_{{3\sigma_i}}", 64, _fact,
        )
        _ZERO_ENDPOINT_STYLES[_fact] = {"e2_pattern": _pattern, "j_order": 1, "two_valuation": 0}
        _POSITIVE_J_ZERO_EVIDENCE[_fact] = {
            "source_status": "independently-verified", "source_blockers": [], "machine_verification_pending": [],
            "evidence_kind": "Tate-negative-source-derived", "j_order": 1, "source_component": "positive-j",
            "derived_from": ["FN-3I-001", "DKLLW24 Tables 3 and 6", "DKLLW24 Lemma 2.6"],
            "covers": f"j^n {_column}D^{_power} for n>=1; page 9 only",
            "derivation": (
                f"The primitive equation gives d3(Uh1^{_filtration + 1})=j*kD*{_column}. "
                f"In TateSS multiply by g^-1 D^{_power + 2} j^(n-1), all 3-cycles. "
                f"The resulting source has filtration {_filtration - 3} and target {_filtration}. "
                "Negative-source Tate comparison gives zero HFPSS outgoing d9 of the positive-j ideal. "
                "It does not kill the low-filtration HFPSS class. Its forward-g images can be "
                "actual HFPSS d3 boundaries and must not be preserved or recreated."
            ),
            "verification_certificate": {
                "status": "verified",
                "method": "Primitive d3 and negative-source Tate comparison",
                "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "page": 9,
                "premises": ["FN-3I-001", "DKLLW24 Lemma 2.6"],
                "tate_source_bidegree": [8 * _power + _filtration + 1, _filtration - 3],
                "tate_target_bidegree": [8 * _power + _filtration, _filtration],
            },
        }
for _power in (2, 6):
    _fact = f"DER-MIX-D9-JQ-D{_power}-zero"
    _ZERO_CLAIM_SOURCES[_fact] = (
        rf"j\{{h_1^2+xh_1v_1\}}D^{_power}u_{{\sigma_i+2\sigma_j}}", 64, _fact,
    )
    _ZERO_ENDPOINT_STYLES[_fact] = {"e2_pattern": "S22H", "j_order": 1, "two_valuation": 0}
    _POSITIVE_J_ZERO_EVIDENCE[_fact] = {
        "source_status": "derived-review", "evidence_kind": "Tate-negative-source-derived",
        "derived_from": ["FN-MIX-001", "DKLLW24 Lemma 2.6", "DKLLW24 Tables 3 and 6",
                         "DKLLW24 Proposition inftybo (main.tex:1391-1398)"],
        "j_order": 1, "source_component": "positive-j", "covers": "j^n Q D^m for n>=1",
        "derivation": (
            "Write U=v1^2u and Q=(h1^2+xh1v1)u. The mixed primitive d3 and its h1^3 "
            "product give d3(Uh1^3)=h1^6u=j kD Q. In TateSS, for n>=1, "
            "d3(g^-1 D^(m+2) j^(n-1) U h1^3)=j^n QD^m. Its source has filtration -1 "
            "and the target filtration 2. Lemma 2.6 and the negative-source Tate method "
            "(main.tex:488-509) make this HFPSS positive-j class a cycle, not an HFPSS d3 boundary. "
            "This independently proves its d9 is zero without assuming the constant-Q coefficient. "
            "Alternatively j=v1^4D^-1 is permanent by main.tex:1391-1398; Table 6 gives "
            "jT=0, in a finite order-two target line with no higher 2-layer or positive-j tail. "
            "Thus the constant-Q formula also gives d9(j^n QD^m)=0. Neither argument sets d9(QD^m)=0."
        ),
        "comparison_certificate": {
            "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j",
            "status": "review", "spectral_sequence": "tate", "page": 3,
            "source_bidegree": [8 * _power + 3, -1], "target_bidegree": [8 * _power + 2, 2],
            "source_representative": f"g^-1 D^{_power + 2} j^(n-1) U h1^3",
            "target_representative": f"j^n Q D^{_power}", "n_min": 1,
            "interpretation": "HFPSS cycle from a negative-source Tate boundary; never delete the HFPSS target.",
        },
    }

_MULTIPLICATIVE_ZERO_EVIDENCE = {
    "DER-3I-D5-B-zero": (
        "For B=(x+y)h1u the potential d5 target h1^3*kD^p*u is the primitive "
        "d3(U*kD^p) image. Its entire finite line is zero on E4. The same "
        "target exclusion works for every D block and forward g, without "
        "asserting D is a 5-cycle or B is permanent."
    ),
    "DER-3I-D7-B-zero": (
        "B=(x+y)h1u has zero d3 and d5. Its d7 target (x+y)k^2D^(p+1)u "
        "is an FN005 d5 source when p+1 is even and an FN006 d5 source when "
        "p+1 is odd. Both targets have therefore disappeared on E6. This "
        "is an 8-stem outgoing-zero pattern, not an invertible D or permanent B."
    ),
    "DER-3I-D5-A-EVEN": (
        "The actual product Ah2=T is checked by mod-2 reduction into the unique finite "
        "order-two (1,3) line, with no extra Witt layer. Independently verified FN002 "
        "gives d5(AD)=kTD. Together with d5(D)=kDh2 and D invertible on E5 this gives "
        "d5(A)=0. Since 2T=0, every even D translate has d5=0. This is a page-5 zero "
        "map, not a permanent-cycle claim or a claim that D^2 is a 5-cycle."
    ),
    "DER-3I-D5-C-zero": (
        "C=(h1+xv1)u survives d3 by FN001; the potential d5 target (0,6) is empty "
        "in the unoriented E2 pattern. C*h2=0 makes the D-Leibniz term zero. "
        "The same empty-target argument holds every 8 stems and after forward g."
    ),
    "DER-3I-D7-C-zero": (
        "After its independently verified zero d3 and d5, C's d7 target (0,8) "
        "is S00. The primitive d3(Uh1*kD)=v1^4*k^2D*u hits this entire module, "
        "including S00's local j_order=0. The same calculation applies at every "
        "8-stem translate; it does not assume D is a 7-cycle."
    ),
    "DER-3I-D7-Q-zero": (
        "Q=h1*C, h1 is permanent, and C has independently verified zero d3,d5,d7. "
        "Thus d7(Q)=0 on each 8-stem block. This certifies only the outgoing map, "
        "not protection against the FN005/FN006 incoming images after forward g."
    ),
    "DER-3I-D7-P-EVEN": (
        "Set H=h2*u2sigma. Its d3 is zero since h1*h2 lies in the empty (4,2) "
        "integer E2 cell. FN004 and d5(D)=kDh2 give d5(H)=0 with D invertible "
        "on E5; every even D translate has zero extra term because 2h2^2=0. "
        "The d7 target (8m+2,8) is empty for all m, and filtration one excludes "
        "early incoming. Multiply these even-D 7-cycles by permanent a_sigma_i "
        "to obtain d7(PD^m)=0. The 16-stem repeat is a zero-map pattern, not "
        "an invertible D^2 or permanent P declaration."
    ),
    "FN-MIX-004-even-zero": (
        "P=(yh2+xh1v1)u and P*h2=x^3D u. The normalized FN-MIX-004 map "
        "d5(PD)=x^3kD^2u and Table 8 d5(D)=kDh2 give D*d5(P)=0. "
        "D is invertible on E5, so d5(P)=0; 2P=0 makes every even-D translate a 5-cycle. "
        "FN-MIX-004 has an independent omega/Euler and target-survival certificate; this is not E2 Thom transport to E5."
    ),
    "FN-MIX-005-Q-zero": (
        "Q=(h1^2+xh1v1)u has Q*h2=0 because C*h2 lies in the empty E2 cell (4,2). "
        "The repaired full-F4 target argument proves d5(BD^2)=b*kD^2*Q with b nonzero, "
        "without fixing its exact unit. "
        "Square-zero then gives kD^2*d5(Q)=0. Q's only possible d5 target is "
        "the F4 line x^3*kD*u at (1,7). Multiplication by kD^2 sends it to "
        "x^3*k^2*D^3*u at (13,11), nonzero on E5: its d3 source (14,8) is empty, "
        "and its cycle property follows from the FN-MIX-004 target and 3-cycles D,k. "
        "Thus that multiplication is injective on the candidate target and d5(Q)=0. "
        "Q*h2=0 gives all D translates by Leibniz. This is not the three-sigma "
        "empty-target proof for C, which does not survive d3 in the mixed sector."
    ),
    "FN-3I-003-even-zero": (
        "Write P=(yh2+xh1v1)u. Table 6 gives P*h2=x^3D u. "
        "FN-3I-003 and d5(D)=kDh2 have the same displayed coefficient, "
        "so d5(PD)=D*d5(P)+kx^3D^2u implies d5(P)=0 on E5. "
        "Since 2P=0, the extra term d5(D^2)*P is zero; repeat by 16 stems."
    ),
    "FN-3I-001-Q-zero": (
        "C=(h1+xv1)u survives d3 by FN-3I-001. Its d5 target (0,6) "
        "and all 8-stem translates are empty in the Table 6 E2 pattern. "
        "Thus d5(C)=0 and d5(Q)=0 for Q=h1*C. Table 6 gives C*h2=0, "
        "so the extra D-Leibniz term vanishes for every D translate. "
        "This uses the empty target, not an implication from d3(C)=0 alone."
    ),
    "FN-2I-003-h2-zero": "Multiply the stated d5((x^2+y^2)D^2u)=0 by permanent h2.",
    "FN-2I-004-h2-square-zero": (
        "Multiply the h2-u d5 by h2^2: every possible target is a multiple of h2^4=0. "
        "The extra D-Leibniz term also contains h2^4, so all D translates have zero d5."
    ),
    "FN-2I-003-euler-h2-zero": (
        "(x^2+y^2)h2u=a_sigma_i^2 h2 is a product of permanent cycles. "
        "Thus its d21 is zero. This is the line C+E, not C or E separately; "
        "combine with FN-2I-020 to compute the rank-one d21 and its kernel."
    ),
}

_DERIVED_ZERO_EVIDENCE = {
    "evidence_kind": "Leibniz-derived",
    "derived_from": ["FN-2I-004", "DKLLW24 Corollary 4.15"],
    "coefficient_constraint": (
        "Use the displayed coefficient 1 in both FN-2I-004 and d5(D)=k h2 D, "
        "as required by formal_notes.tex:358. Independent unspecified units "
        "would not justify this zero map."
    ),
    "derivation": (
        "Set H=h2 u. On E5, D is invertible and d5(D)=k h2 D. "
        "FN-2I-004 gives d5(HD)=k h2^2 D u=D*d5(H)+k h2^2 D u, "
        "so d5(H)=0 and d5(y^2 D u)=d5(h2 H)=0. "
        "This uses invertibility on E5, not permanence of D."
    ),
}


_REPRESENTATIONS = {
    "ws_2sigma_i": {"sigma_i": -2},
    "ws_3sigma_i": {"sigma_i": -3},
    "ws_sigma_i_2sigma_j": {"sigma_i": -1, "sigma_j": -2},
}

_JAN29_PROOF_SOURCES = {
    "FN-3I-010-pc": ["笔记 2026年1月29日 10_52_56.pdf, pages 1-3"],
    "FN-3I-010": [
        "笔记 2026年1月29日 10_52_56.pdf, page 3 (D^5 block)",
        "笔记 2026年1月29日 11_21_30.pdf, pages 1-3 (D block)",
    ],
}


def _apply_pure_galois_normalization(conclusion: dict, workspace_id: str) -> None:
    """Fix residue-field units, independently of admitting a differential.

    In the user's chosen pure sigma_i bases, psi fixes the generators and
    Thom classes. Equivariance forces each F4 coefficient into F2. This does
    not remove 2/Witt layers, prove a proposed arrow, or normalize a mixed
    grading after a semilinear change of basis.
    """
    if workspace_id not in {"ws_2sigma_i", "ws_3sigma_i"}:
        return
    conclusion["coefficient_normalization"] = {
        "id": "pure-sigma-i-galois-fixed", "value": 1,
        "coefficient_field": "F4", "witness": "psi",
        "basis": "Galois-fixed generators and Thom classes",
        "source_ref": "User Galois normalization declaration (2026-09-20)",
        "source_workspace_id": workspace_id, "admission_independent": True,
    }
    parameter = conclusion.get("coefficient_parameter")
    if isinstance(parameter, dict) and not parameter.get("source_parameter"):
        conclusion["coefficient_parameter"] = {
            **deepcopy(parameter), "value": 1, "domain": [1],
            "fixed_reason": "pure-sigma-i-galois-fixed",
        }
        conclusion["coefficient_constraint"] = (
            "The nonzero F4 coefficient is 1 in the chosen psi-fixed pure sigma_i basis. "
            "This is independent of Jan.29 and of any final d19/d23 claim; "
            "the differential's existence and source survival remain separate premises."
        )
    # This old compatibility argument used a disputed d23 source to infer
    # equality of units. The direct Galois normalization needs no such premise.
    constraints = conclusion.get("coefficient_constraints", [])
    if workspace_id == "ws_3sigma_i" or constraints:
        conclusion["coefficient_constraints"] = [
            item for item in constraints
            if item.get("id") != "three-sigma-d9-product-compatibility"
        ]
    withdrawn = [fact for fact in conclusion.get("derived_from", [])
                 if fact in _JAN29_PROOF_SOURCES]
    if withdrawn:
        conclusion["withdrawn_dependencies"] = withdrawn
        conclusion["source_blockers"] = list(conclusion.get("source_blockers", [])) + [
            "The Jan.29 proof is withdrawn as an authority; this derived row still "
            "needs an independent proof of " + ", ".join(withdrawn) + "."
        ]

_LEGACY_MANAGED_IDS = {
    "diff_two_d3_u", "diff_two_d5_h2D", "diff_two_d5_2D", "diff_two_d5_xh1",
    "diff_two_d9", "diff_two_d11", "diff_two_d13",
    "diff_three_d3", "diff_three_d5_main", "diff_three_d5_yh2", "diff_three_d5_x3",
    "diff_three_d5_xyD2", "diff_three_d5_sum", "diff_three_d9_25", "diff_three_d11_30",
    "diff_three_d9_17", "diff_three_d9_18", "diff_three_d9_32", "diff_three_d9_25b",
    "diff_mixed_d3",
}

_LEGACY_PROPOSITION_BY_DIFFERENTIAL = {
    "diff_two_d3_u": "prop_two_d3_u",
}


_SOURCE_BLOCKERS = {
    "FN-2I-002": (
        "Coefficient-ideal mismatch in formal_notes.tex:313-315: the cited integer "
        "formula has v1^4 h1^3 = j D h1^3, not D h1^3. Its h1 multiple "
        "has v1^4 h1^4 = j D h1^4; the printed intermediate h1^4 v1^2 "
        "also has the wrong stem. Preserve the printed claim for review; "
        "do not use it to delete the constant j coefficient."
    ),
    "FN-2I-004": "The nonzero coefficient is fixed by the chosen Galois-invariant basis; pattern admission is separate.",
    "FN-2I-006": "The proof explicitly questions its transfer/permanent-cycle premise.",
    "FN-2I-009": "The restriction lemma requires review; the pure-sector unit is fixed independently by Galois invariance.",
    "FN-2I-010": "Hidden extension and Tate cancellation depend on the reviewed d11 family.",
    "FN-2I-011": "The permanent-cycle premise uses inverse g through Tate comparison.",
    "FN-3I-007": "Depends on reviewed FN-2I-011 and a coefficient-sensitive product.",
    "FN-3I-008": "Depends on FN-3I-007 through the h1 extension.",
    "FN-3I-010-pc": (
        "The restriction proof in formal_notes.tex:808 uses C4<i>, but ker(sigma_i)=C4<i> "
        "by DKLLW24 main.tex:520. Res(a_3sigma_i)=a_3=0 on that subgroup, not the "
        "nontrivial sign Euler class a_3sigma. A repaired proof may use C4<j> or C4<k>, "
        "but its Euler-class identification and filtration must be checked there. "
        "This is a separate proof issue from the FN-3I-010 Euler-preimage exclusion; "
        "the permanent-cycle statement is retained, not declared false."
    ),
    "FN-3I-010": (
        "The Euler-preimage exclusion in formal_notes.tex:833-848 conflicts with "
        "the displayed product in lines 770-774: a_sigma_i*(x*h1^2*D^4*u_2sigma_i) "
        "is 2*v1^2*k*D^4*u_3sigma_i, the very class z being excluded. "
        "The candidate at (33,3) is not the (1,3) source of FN-2I-020; a D4 shift "
        "of that 64-period d21 is not justified. An independent exclusion or corrected "
        "lifting argument is required before using this d23 proof or its claimed "
        "vanishing consequences. Conditional runtime tests also find a cross-grading "
        "naturality conflict: d23(A)=0 while the claimed d23(a_sigma_i*A) is nonzero. "
        "The user has withdrawn the Jan.29 proof as an authority and prioritizes "
        "the earlier independent propositions; this does not select a replacement formula."
    ),
    "FN-MIX-002": "The printed red [TBD] d9 premise is now supplied by the verified omega image of FN-2I-010. The annihilator argument only forces a nonzero earlier map; it does not determine the new d5 coefficient c or reconcile table_Q8.tex:511-512 with the printed unit 1.",
    "FN-MIX-003": (
        "FN-MIX-002's nonzero premise and coefficient remain under review. "
        "The positive-filtration Tate pullback itself is covered by DKLLW24 Lemma 2.6, "
        "not an additional unproved HFPSS comparison assumption."
    ),
    "FN-MIX-004": "The red [TBD] d5 premise is the omega image of FN-2I-004, with equal source/target scaling. The Euler multiplication and the source admission are retained as explicit premises.",
    "FN-MIX-005": (
        "The H2-cycle premise and the full F4 target enumeration are now independently "
        "repaired: d5(B)=b*kQ with b nonzero. This does not select b=1. The relative "
        "unit in P+bQ remains unresolved, so the printed unit-1 formula stays review. "
        "Note/record/note.tex:1409 rejects the historical Proposition 6.5; the repair "
        "uses earlier independently supported propositions, not that historical assertion."
    ),
    "FN-MIX-006": (
        "The proof explicitly contains a red [TBD] d11 premise; D4 is only a pattern shift. "
        "Note/record/note.tex:1409 rejects historical Proposition 6.6. The factorization "
        "in formal_notes.tex:979 omits zeta: B(x^2+zeta^2 y^2)=zeta x^3, "
        "so a unit-1 premise would give a zeta^2 target, not the printed unit-1 target."
    ),
}

_SOURCE_CONFLICTS = {
    "FN-3I-010-pc": {
        "kind": "euler-restriction-uses-kernel-subgroup",
        "source_ref": "formal_notes.tex:799-809; DKLLW24 main.tex:515-520; Note/record/note.tex:638-660",
        "authority": "Preserve the source's permanent-cycle statement without admitting its invalid subgroup restriction.",
        "checked_identity": "ker(sigma_i)=C4<i>; Res_C4<i>(3sigma_i)=3; Res_C4<i>(a_3sigma_i)=a_3=0",
        "conditional_correction": (
            "Res_C4<j>(sigma_i)=Res_C4<k>(sigma_i)=sigma. A nonzero Euler detector on "
            "one of those subgroups could repair the argument, but requires its own "
            "coefficient transport and filtration certificate; do not silently rename C4<i>."
        ),
        "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i",
    },
    "FN-3I-010": {
        "kind": "euler-preimage-exclusion-conflicts-with-recorded-product",
        "source_ref": "formal_notes.tex:515,540-555,770-774,833-848; DKLLW24 main.tex:1037,1094-1123",
        "authority": "formal_notes remains primary; preserve both printed formulas without admitting the disputed exclusion",
        "checked_identity": (
            "a_sigma_i*(x*h1^2*D^4*u_2sigma_i)=x^2*h1^2*D^4*u_3sigma_i"
            "=2*v1^2*k*D^4*u_3sigma_i=z; also a_sigma_i*(x^2*h2*D^4*u_2sigma_i)"
            "=x^3*h2*D^4*u_3sigma_i=z, using the actual group-cohomology hidden h1/h2 extensions"
        ),
        "conditional_family": (
            "The candidate (33,3) maps to z at (32,4). Even under the current two-sigma "
            "hypotheses its I13 line survives to E24, whereas I13 at (1,3) dies on d21. "
            "Its only possible d23 target at (32,26) is an FN-2I-006 d5 source, already "
            "zero on E6. Thus d23(A)=0; admitting nonzero d23(z) conflicts with Euler "
            "naturality. Earlier still, g^3*A is an FN-2I-018 d13 target, but the current "
            "three-sigma hypotheses leave g^3*z nonzero on E14. These are conditional "
            "cross-grading inconsistencies, not independent topological permanence proofs."
        ),
        "conditional_correction": (
            "Resolve the earlier Euler-image mismatch before using the final convergence test. "
            "For Z=g^3*z*D^-8 at (28,16), finite incoming-source enumeration retains the "
            "d11 candidate (29,5)->(28,16) if the separate Ck permanence premise and the "
            "recorded early products/differentials hold. That premise has its own subgroup "
            "proof blocker. This does not establish the historical Option 2's full 32-period "
            "family. Its nonzero F4 unit is fixed independently by Galois normalization; "
            "no replacement map is installed."
        ),
        "scope": "source-workspace",
        "source_workspace_id": "ws_3sigma_i",
    },
    "FN-MIX-003": {
        "kind": "historical-summary-coefficient-not-admitted",
        "source_ref": "REU projects/table_Q8.tex:511-512; formal_notes.tex:903-932",
        "authority": "The local summary records a coefficient choice; it does not resolve the current proof's unit.",
        "conditional_family": "The local table prints c=zeta and c+1=zeta^2, both with Period 16.",
        "unit_parameter": "Keep the shared c unresolved; the historical table is not a coefficient assignment.",
    },
    "FN-MIX-005": {
        "kind": "mixed-F4-target-choice-not-exhaustive",
        "source_ref": "Note/record/note.tex:1409-1413; formal_notes.tex:953-970; REU projects/table_Q8.tex:514-515",
        "historical_proposition": "6.5",
        "authority": "formal_notes remains primary; preserve its TBD claim without treating it as admitted",
        "conditional_family": "d5(BD)=kD(P+bQ), d5(BD^2)=b kD^2 Q",
        "unit_parameter": "b in F4* by the independent repair; exact value not determined",
        "omitted_targets": ["P+zeta*Q", "P+zeta^2*Q"],
        "verified_subpremise": "Full F4 target enumeration and nonzero b, using the independent H2 Euler cycle and finite incoming inventory",
        "repair_certificate_id": "DER-MIX-D5-B-NONZERO",
        "unresolved": "The exact relative b among the three nonzero F4 units is still undetermined.",
        "runtime_admission": False,
    },
    "FN-MIX-006": {
        "kind": "historical-rejection-and-factorization-unit-mismatch",
        "source_ref": "Note/record/note.tex:1409-1413; formal_notes.tex:979-981; DKLLW24 Table 6",
        "historical_proposition": "6.6",
        "status": "resolved-by-independent-corrected-proof",
        "authority": "Preserve the printed coefficient 1 for review; the separate omega/Euler proof verifies coefficient zeta^2.",
        "checked_identity": "B*x^2=B*y^2=x^3; 1+zeta^2=zeta",
        "conditional_correction": "The target coefficient is lambda*zeta^2; verified omega(FN-2I-009) fixes lambda=1, giving zeta^2.",
        "unit_parameter": "mixed_d11_R is fixed to zeta^2 by the actual Euler product; atlas psi squares it once.",
    },
}

_REPRESENTATION_WARNINGS = {
    "FN-3I-003": "The printed ref prop:2sig d5-2 resolves by its displayed formula to prop:d5-2 u2sig (FN-2I-004).",
    "FN-3I-004": "The printed target omits u_{3sigma_i}; the subsection and bidegree supply this Thom factor.",
    "FN-3I-006": "The image is the single line P+Q, not both columns. The positive-j Q ideal is already a d3 boundary here.",
}

_MACHINE_VERIFICATION_PENDING = {
    "FN-2I-002": (
        "Resolve the printed coefficient ideal before admission. The independently "
        "derived primitive d3(v1^2 h1 u)=h1^4 u is not the printed source "
        "h1 v1^6 u and must have a separate derivation record."
    ),
    "FN-2I-019": "Independently check the source proof's vanishing and unique-source enumeration after all earlier quotients.",
    "FN-2I-020": "Independently check the source proof's earlier quotients and unique-source enumeration.",
    "FN-2I-021": "Independently check the source proof's unique-source enumeration.",
    "FN-3I-005": "Check the same-page kernel/image using FN-3I-003 and FN-3I-004.",
    "FN-3I-006": "Check the prior positive-j d3 image and the one-dimensional d5 image in the current quotient.",
    "FN-3I-009": "Independently check the supplied corrected-restriction proof and prior differential exclusions.",
    "FN-3I-010-pc": (
        "Repair the kernel-subgroup restriction and verify that the cited C4 class really "
        "detects a_3sigma in filtration five. The cofiber argument for FN-3I-010 still "
        "uses the kernel C4<i>; these two subgroup roles must not be conflated."
    ),
    "FN-3I-010": (
        "Resolve the explicit Euler-preimage conflict before certifying the d23 argument "
        "and the asserted d19 vanishing premise; test the earlier d13 Euler image and the "
        "d23 naturality square across workspaces, not just their separate quotients. The separately recorded Euler permanent "
        "cycle FN-3I-010-pc has a distinct restriction-proof issue. Its Jan.29 proof is also "
        "withdrawn as an authority; the statement is retained for independent review, not declared false."
    ),
}


def _source_metadata(fact_id: str) -> dict:
    """Separate a source's open proof issue from editorial or software work."""
    metadata = {
        "source_status": "active-proof-with-review" if fact_id in _SOURCE_BLOCKERS else "active-proof",
        "source_blockers": [_SOURCE_BLOCKERS[fact_id]] if fact_id in _SOURCE_BLOCKERS else [],
        "source_conflicts": [dict(_SOURCE_CONFLICTS[fact_id])] if fact_id in _SOURCE_CONFLICTS else [],
        "representation_warning": _REPRESENTATION_WARNINGS.get(fact_id, ""),
        "machine_verification_pending": (
            [_MACHINE_VERIFICATION_PENDING[fact_id]] if fact_id in _MACHINE_VERIFICATION_PENDING else []
        ),
    }
    if fact_id in _JAN29_PROOF_SOURCES:
        metadata.update({
            "source_status": "withdrawn-proof",
            "printed_source_status": "source-proved",
            "source_artifacts": _JAN29_PROOF_SOURCES[fact_id][:],
            "authority_decision": (
                "User withdrew the Jan.29 handwritten proof as an authority; "
                "use earlier independently supported propositions. Preserve the "
                "formula for review, without asserting its negation or a replacement."
            ),
        })
    # These really have a printed Period column, unlike DKLLW Tables 8/9.
    # Keep the local summary identifiable without adopting its equations or
    # treating every displayed short repeat as a permanent D-power.
    period_table = next((value for prefix, value in {
        "FN-2I-": ("2sigma_i", "350-410", "Its caption explicitly says Need Correction!"),
        "FN-3I-": ("3sigma_i", "419-478", "Check each row against the current formal notes."),
        "FN-MIX-": ("sigma_i+2sigma_j", "485-544", "Its coefficient choices and high-page candidates are not automatically admitted."),
    }.items() if fact_id.startswith(prefix)), None)
    if period_table:
        sector, lines, caveat = period_table
        metadata["related_period_table"] = {
            "source_ref": f"REU projects/table_Q8.tex:{lines}",
            "sector": sector,
            "status": "historical-review",
            "column": "Period",
            "interpretation": "Stem displacement of the stated differential family, not a claim that the corresponding bare D-power is a permanent unit.",
            "authority": "This local summary does not override formal_notes.tex or its proof caveats. " + caveat,
        }
    if fact_id in {"FN-MIX-002", "FN-MIX-003"}:
        metadata["coefficient_parameter"] = dict(_MIXED_A_PARAMETER)
        metadata["coefficient_constraint"] = (
            "FN-MIX-002 and its positive-filtration pullback FN-MIX-003 share c in F4*. "
            "The even D block has coefficient c+1. Nonzero does not mean c=1."
        )
    if fact_id in {"FN-MIX-002", "FN-MIX-004"}:
        metadata["premise_transport_certificate"] = {
            "action": "omega", "source_sector": "2sigma_i", "target_sector": "2sigma_j",
            "premise": "FN-2I-010" if fact_id == "FN-MIX-002" else "FN-2I-004",
            "source_ref": "formal_notes.tex:476-478; DKLLW24 omega(D)=zeta^2 D" if fact_id == "FN-MIX-002"
                          else "formal_notes.tex:357-379; DKLLW24 omega(D)=zeta^2 D",
            "status": "verified",
            "derivation": (
                "omega fixes h1,h2,k and sends D to zeta^2 D. "
                + ("Thus d9(2zeta*k*h2*D^2*u_2sigma_j)=lambda*k^3*h1^2*D^3*u_2sigma_j "
                   "is the verified FN-2I-010 image, not FN-2I-016 or twice that different row. "
                   "Multiplication by permanent a_sigma_i annihilates its source. "
                   "This forces a nonzero earlier d5 but does not equate its coefficient c with lambda."
                   if fact_id == "FN-MIX-002" else
                   "Both source h2*D*u and target k*h2^2*D*u scale by zeta^2, "
                   "so the normalized coefficient remains 1. Multiplication by permanent a_sigma_i "
                   "gives P*D -> x^3*k*D^2, P=(yh2+xh1v1)u. Also P*h2=x^3*D "
                   "makes d5(P*D^2)=0 by Leibniz.")
            ),
        }
    if fact_id == "FN-MIX-005":
        metadata["nonzero_parameter_certificate"] = deepcopy(_MIXED_B_NONZERO_CERTIFICATE)
        metadata["verified_cycle_subpremise"] = {
            "status": "verified", "scope": "H2 outgoing-cycle premise only; not the mixed d5 coefficient",
            "source_workspace_id": "ws_2sigma_i", "source_fact_id": "DER-2I-TATE-H2-cycle",
            "source_ref": "formal_notes.tex:450-470,965; DKLLW24 Lemma 2.6 and Tate method",
            "action": "omega", "target_sector": "2sigma_j",
            "derivation": (
                "The negative-source Tate d11 obtained from verified FN-2I-009 by g^-3 D8 "
                "has target h1D2u_2sigma_i at (17,1). Thus this HFPSS target has zero "
                "outgoing maps, and filtration one excludes incoming at the seed. omega "
                "maps it to a nonzero scalar times h1D2u_2sigma_j. This repairs the "
                "cycle subpremise; the separate nonzero_parameter_certificate repairs the full F4 target choice."
            ),
            "runtime_admission": False,
        }
    if fact_id == "FN-MIX-003":
        metadata["comparison_certificate"] = {
            "status": "verified-comparison-conditional-on-premise",
            "scope": "source-workspace-comparison",
            "source_workspace_id": "ws_sigma_i_2sigma_j",
            "premise": "FN-MIX-002",
            "source_ref": "DKLLW24 Lemma 2.6 and Tate method; main.tex:488-510",
            "translation": {"g_exponent": -2, "D_exponent": 4, "spectral_sequence": "tate"},
            "source_bidegree": [6, 2], "target_bidegree": [5, 7],
            "derivation": (
                "Translate the FN-MIX-002 row (14,10)->(13,15) by g^-2 D^4, "
                "of bidegree (-8,-8), in TateSS. D^4 is a 5-cycle since "
                "d5(D^4)=4kD^4h2=0 and 4h2=0; it is not a permanent period. "
                "The translated endpoints have positive filtration, so Lemma 2.6 "
                "gives the HFPSS differential with the same still-unresolved coefficient. "
                "This does not promote FN-MIX-002 or the printed unit-1 normalization."
            ),
        }
    return metadata

_PERIOD_SOURCES = {
    "FN-3I-007": "Note/record/note.tex:589-598,1343-1345 (corrected 32-pattern; not the rejected 16-pattern)",
    "FN-3I-008": "Note/record/note.tex:589-598,1343-1345 (corrected 32-pattern; not the rejected 16-pattern)",
    "FN-3I-009": "Note/record/note.tex:1343-1345 (Jan. 13 corrected 32-pattern)",
}
for _fact in ("FN-MIX-002", "FN-MIX-003", "FN-MIX-004", "FN-MIX-005", "DER-MIX-D5-A-EVEN"):
    _PERIOD_SOURCES[_fact] = (
        "DKLLW24 Table 8 row 2 and Proposition 4.17 proof; "
        "Note/record/note.tex:725: d5(D^2)=2kD^2h2 and each listed source is 2-torsion, "
        "so the extra Leibniz term vanishes. This conditional 16-pattern does not make D^2 permanent."
    )
_PERIOD_SOURCES["FN-MIX-004"] = (
    "formal_notes.tex:357-379,934-951; DKLLW24 Table 8 row 2. "
    "The omega/Euler proof and 2P=0 give a verified 16-stem differential pattern by Leibniz, "
    "not a claim that D^2 is permanent."
)


def _occurrence_style(workspace: Workspace, label: str, stem: int, filtration: int) -> dict:
    """Retain the vector or 2-adic level named by a formal differential.

    A coefficient-2 source may survive d3 even when its coefficient-1 parent
    does not.  Likewise, killing A+B never kills both summands of a cell.
    """
    value = _normalise_label(label)
    style = {"formal_notes_occurrence": True, **endpoint_component_style(label)}
    if workspace.settings.get("rendering", {}).get("enumerated_e2_pattern") == "integer" and "x^2+y^2" in value:
        # formal_notes:277-280 changes the integer basis (x^2,y^2) to
        # (x^2+y^2,y^2).  The first vector is not either original column.
        components = {"I62X": 1, "I62Y": 1}
        if "h_2" in value:
            components = {"I13X": 1, "I13": 1}  # y^2 h2 = h2^3 D^-1
        style.update({"e2_components": components, "named_vector_port": True})
        return style
    if "yh_2+h_1^2" in value:
        style["e2_components"] = {"S22Y": 1, "S22H": 1}
        style["named_vector_port"] = True
        return style
    style["e2_pattern"] = _published_e2_pattern(workspace, label, filtration)
    scalar = re.match(r"^([24])(?!\^)", value)
    if scalar:
        parent = next((item for item in workspace.classes if (
            item.grade.stem == stem and item.grade.filtration == filtration
            and not item.style.get("coefficient_port")
            and item.style.get("e2_pattern") == style["e2_pattern"]
        )), None)
        style.update({
            "coefficient_port": True,
            "coefficient_parent_id": parent.id if parent else "",
            "witt_scalar_level": label,
            "two_adic_valuation": 1 if scalar.group(1) == "2" else 2,
            "two_valuation": 1 if scalar.group(1) == "2" else 2,
        })
        if filtration % 4 == 0:
            style["dkllw_glyph"] = "witt-j-series"
    return style


def _node_for(workspace: Workspace, label: str, stem: int, filtration: int) -> ClassNode:
    style = _occurrence_style(workspace, label, stem, filtration)
    node = next((item for item in workspace.classes if (
        _normalise_label(item.label) == _normalise_label(label)
        and item.grade.stem == stem and item.grade.filtration == filtration
        and not (item.archived and "source-schema correction" in item.archived_reason)
    )), None)
    if node is not None:
        node.style.update(style)
        if style.get("e2_components"):
            node.style.pop("e2_pattern", None)
        return node
    safe_index = sum(1 for item in workspace.classes if item.id.startswith("formal_class_"))
    node = ClassNode(
        id=f"formal_class_{workspace.id}_{safe_index}",
        label=label,
        expression=label,
        grade=Grade(stem, filtration, dict(_REPRESENTATIONS[workspace.id])),
        page=2,
        state="unknown",
        notes="Class occurrence required by an active formal_notes differential claim.",
        style=style,
        period_stem=64,
    )
    workspace.classes.append(node)
    return node


def _ensure_sum_map(workspace: Workspace, source: ClassNode, target: ClassNode,
                    arrow: FormalArrow, proposition_id: str, status: str) -> str | None:
    if target.style.get("e2_components") != {"S22Y": 1, "S22H": 1}:
        return None
    prefix = "three_sum" if workspace.id == "ws_3sigma_i" else "mixed_sum"
    suffix = r"3\sigma_i" if workspace.id == "ws_3sigma_i" else r"\sigma_i+2\sigma_j"
    labels = [rf"\{{yh_2+xh_1v_1\}}kDu_{{{suffix}}}", rf"\{{h_1+xv_1\}}h_1kDu_{{{suffix}}}"]
    target.style["e2_basis_patterns"] = ["S22Y", "S22H"]
    cell_ids = [f"cell_{prefix}_source", f"cell_{prefix}_target"]
    for node, cell_id, basis_labels in (
        (source, cell_ids[0], [source.label]), (target, cell_ids[1], labels),
    ):
        cell = next((item for item in workspace.cells if item.id == cell_id), None)
        if cell is None:
            cell = CellVectorSpace(id=cell_id, grade=node.grade, page=2)
            workspace.cells.append(cell)
        cell.grade = node.grade
        cell.basis = [CellBasisVector(f"{cell_id}_{i}", text, text) for i, text in enumerate(basis_labels)]
        cell.display_basis = [
            NamedVector(f"{cell_id}_display_{i}", text,
                        ["1" if i == j else "0" for j in range(len(basis_labels))], text)
            for i, text in enumerate(basis_labels)
        ]
        cell.status = status
        cell.source_ref = arrow.source_ref
        cell.source_refs = [arrow.source_ref]
        node.cell_id = cell.id
        node.coordinates = ["1"] * len(basis_labels)
        node.coefficient_context_id = "q8-residue-f4"
        if len(basis_labels) == 2:
            vector_id = "vector_three_sum_target" if prefix == "three_sum" else "vector_mixed_sum_target"
            cell.named_vectors = [NamedVector(vector_id, node.label, ["1", "1"], node.label)]
    map_id = "linear_diff_three_d5_sum" if prefix == "three_sum" else "linear_diff_mixed_d5_sum"
    linear = next((item for item in workspace.differential_maps if item.id == map_id), None)
    if linear is None:
        linear = DifferentialMap(map_id, cell_ids[0], cell_ids[1], arrow.page)
        workspace.differential_maps.append(linear)
    linear.source_cell_id, linear.target_cell_id = cell_ids
    linear.page = arrow.page
    linear.matrix = [["1"], ["1"]]
    linear.coverage = "complete"
    linear.status = status
    linear.proposition_id = proposition_id
    linear.source_ref = arrow.source_ref
    linear.source_refs = [arrow.source_ref]
    linear.notes = "The image has rank one: only A+B is a boundary. The complementary quotient is retained."
    return map_id


def _reconcile_original_demo_aliases(project: Project) -> None:
    """Map only unchanged seed snapshots into E2, or retire invalid drawings.

    The whitelist is the original 52 nodes in the five computation sectors
    of seed.research_project, not an ID-prefix ownership guess. A researcher
    who changes a label or any part of its grade owns that edited node.
    Retirement preserves IDs, claims, arrows and fate history; it is a schema
    correction and never a spectral-sequence death.
    """
    snapshots = {
        "ws_integer": ("", {}, (
            ("int_D", "D", 8, 0),
            ("int_h2D", "kh_2D", 7, 5),
            ("int_D2", "D^2", 16, 0),
            ("int_h2D2", "2kh_2D^2", 15, 5),
            ("int_Dinvh1", "D^{-1}h_1", -8, 1),
            ("int_D8", "D^8", 64, 0),
        )),
        "ws_sigma_i": (r"u_{\sigma_i}", {"sigma_i": -1}, (
            ("sig_a", r"a_{\sigma_i}", -1, 1),
            ("sig_x3", "x^3D^4", 32, 3),
        )),
        "ws_2sigma_i": (r"u_{2\sigma_i}", {"sigma_i": -2}, (
            ("two_u", "", 0, 0),
            ("two_x2h1u", "x^2h_1", -1, 3),
            ("two_a2", r"\{x^2+y^2\}", 0, 2),
            ("two_D", "D", 8, 0),
            ("two_2D", "2D", 8, 0),
            ("two_h2D", "h_2D", 11, 1),
            ("two_kh2sqD", "kh_2^2D", 10, 6),
            ("two_2kh2D", "2kh_2D", 7, 5),
            ("two_xh1u", "xh_1", 7, 1),
            ("two_kh1cubedu", "kh_1^3", 6, 6),
            ("two_a2D2", r"\{x^2+y^2\}D^2", 14, 2),
            ("two_k3h1D3", "k^3h_1D^3", 13, 13),
            ("two_k2h1sqD3", "k^2h_1^2D^3", 18, 10),
            ("two_k4xh1sqD4", "k^4xh_1^2D^4", 17, 19),
            ("two_2h2D3", "2h_2D^3", 27, 1),
            ("two_d13target", r"d_{13}\text{-target}", 26, 14),
        )),
        "ws_3sigma_i": (r"u_{3\sigma_i}", {"sigma_i": -3}, (
            ("three_v1sq", "v_1^2", 4, 0),
            ("three_h1cubed", "h_1^3", 3, 3),
            ("three_combo", r"\{h_1+xv_1\}", 1, 1),
            ("three_k2a2D3", r"k^2\{x^2+y^2\}D^3", 14, 10),
            ("three_k3xh1sqD3", r"k^3\{x+y\}h_1^2D^3", 13, 15),
            ("three_yh2_source", r"\{yh_2+xh_1v_1\}D", 10, 2),
            ("three_kx3_target", "kx^3D^2", 9, 7),
            ("three_x3_source", "x^3D^2", 13, 3),
            ("three_2v1_target", "2v_1^2k^2D^2", 12, 8),
            ("three_xyD2_source", r"\{x+y\}D^2", 15, 1),
            ("three_h1xv1_target", r"\{h_1+xv_1\}h_1kD^2", 14, 6),
            ("three_sum_source", r"\{x+y\}D", 7, 1),
            ("three_sum_target", r"k\{yh_2+h_1^2\}D", 6, 6),
            ("three_d9_25_source", r"\{x+y\}h_1^2D^3", 25, 3),
            ("three_d9_25_target", "2v_1^2k^3D^4", 24, 12),
            ("three_d11_30_source", r"\{x^2+y^2\}D^4", 30, 2),
            ("three_d11_30_target", r"\{h_1+xv_1\}k^3D^5", 29, 13),
            ("three_d9_17_source", r"D^2\{h_1+xv_1\}", 17, 1),
            ("three_d9_17_target", r"k^2D^3\{x+y\}h_1", 16, 10),
            ("three_d9_18_source", r"D^2h_1\{h_1+xv_1\}", 18, 2),
            ("three_d9_18_target", r"k^2D^3\{x+y\}h_1^2", 17, 11),
            ("three_d9_32_source", r"\{x+y\}h_1D^4", 32, 2),
            ("three_d9_32_target", "x^2h_1k^2D^5", 31, 11),
            ("three_d9_25b_source", r"\{h_1+xv_1\}D^3", 25, 1),
            ("three_d9_25b_target", r"\{x+y\}h_1k^2D^4", 24, 10),
        )),
        "ws_sigma_i_2sigma_j": (r"u_{\sigma_i+2\sigma_j}", {"sigma_i": -1, "sigma_j": -2}, (
            ("mixed_v1sq", "v_1^2", 4, 0),
            ("mixed_h1", "h_1^2", 3, 3),
            ("mixed_combo", r"\{h_1+xv_1\}", 1, 1),
        )),
    }
    corrected_grades = {
        "int_Dinvh1": (-7, 1), "sig_x3": (29, 3),
        "two_a2": (-2, 2), "two_xh1u": (0, 2),
        "two_kh1cubedu": (-1, 7), "mixed_h1": (2, 2),
    }
    for workspace in project.workspaces:
        if workspace.id not in snapshots:
            continue
        suffix, representation, rows = snapshots[workspace.id]
        nodes = {node.id: node for node in workspace.classes}
        for ident, monomial, stem, filtration in rows:
            label = monomial + (suffix if ident not in {"sig_a", "two_d13target"} else "")
            node = nodes.get(ident)
            if node is None or (node.label, node.grade.stem, node.grade.filtration, node.grade.representation) != (
                label, stem, filtration, representation
            ):
                continue
            snapshot = {"id": ident, "label": label, "grade": {
                "stem": stem, "filtration": filtration, "representation": dict(representation),
            }}
            metadata = {"source_ref": "backend/domain/seed.py:research_project", "original": snapshot}
            if ident in corrected_grades or ident == "two_d13target":
                corrected = corrected_grades.get(ident)
                explanation = (
                    f"Its displayed formula has bidegree {corrected}, not {(stem, filtration)}."
                    if corrected else "The generic d13 target is not an identified algebraic class."
                )
                reason = (
                    "Retired original demo after source-schema correction. " + explanation
                    + " Original ID and all research claims are retained; this is not a spectral-sequence death."
                )
                # A user archive is a separate action, so do not overwrite it.
                if not node.archived or node.archived_reason == "Superseded by the complete DKLLW24 published-table import.":
                    node.archived = True
                    node.archived_reason = reason
                metadata.update({"action": "retired-invalid-coordinate" if corrected else "retired-placeholder",
                                 "reason": reason, "mathematical_bidegree": list(corrected) if corrected else None})
            else:
                style = _occurrence_style(workspace, label, stem, filtration)
                node.style.update(style)
                if style.get("e2_components"):
                    node.style.pop("e2_pattern", None)
                metadata.update({"action": "mapped-E2-alias", "reason":
                    "The unchanged seed formula has this bidegree; use the same coefficient-sensitive E2 quotient as its catalogue alias."})
            node.style["original_demo_reconciliation"] = metadata


def ensure_formal_notes_chart(project: Project) -> Project:
    """Synchronize the active formal-notes arrows into the three new sectors."""

    if project.id != "hfpss_studio":
        return project
    workspaces = {item.id: item for item in project.workspaces}
    admission = {item["id"]: item for item in load_periodic_fate_ledger()["fact_families"]}
    for workspace_id in _REPRESENTATIONS:
        workspace = workspaces.get(workspace_id)
        if workspace is None:
            continue
        if workspace_id == "ws_2sigma_i" and workspace.summary == (
            "Most developed shifted page in the archive: d3, d5, and higher differential families "
            "with restriction, transfer, and vanishing-line evidence."
        ):
            workspace.summary = (
                "Source-verified d3 through d21, including all three 64-periodic d21 families "
                "and their low representatives in table_Q8.tex. Earlier quotients retain exact "
                "Witt layers and the low Euler-product kernel; no imposed vanishing-line clipping."
            )
        if workspace_id == "ws_3sigma_i" and workspace.summary in {(
            "Documented *-3sigma_i calculation through E12: one 8-periodic d3 family, "
            "five 16-periodic d5 families, and under-review 32-periodic d9/d11 families "
            "from the working log. E12 is not asserted to be E-infinity."
        ), (
                "Verified d3/d5 patterns and two independently proved D2/D6 blocks of "
                "P/Q/C d9 maps. Each d9 block repeats by permanent D8 and forward g; "
                "D4 is not an E9 unit. Other d9 and higher claims remain under review; "
                "no E-infinity page is asserted."
        ), (
                "Verified d3/d5, separately proved D8 blocks of d9, and restriction-detected d11 "
                "with the actual P/Q target quotient. Short paired patterns are not permanent "
                "D4 units. A separately proved D5-block d23 retains the Witt/j kernel. "
                "The withdrawn-proof D1 d23 and d19 claims remain review; E-infinity is not asserted."
        ), (
                "Verified d3/d5 and separate D8 blocks of d9/d11. The Euler13-forced CD1 d11 "
                "retains its positive-j kernel; CD5 is a separate outgoing cycle. The D5-block "
                "d23 retains the Witt/j kernel. AD6 has zero d19 because its proposed target "
                "already supports d11; AD2 d19 remains unresolved. Historical D1 d23/d19 rows "
                "remain review, not a permanent D4 family. E-infinity is not asserted."
        )}:
            workspace.summary = (
                "Verified d3/d5 and separate D8 blocks of d9/d11. The Euler13-forced CD1 d11 "
                "retains its positive-j kernel; CD5 is a separate outgoing cycle. The D5-block "
                "d23 retains the Witt/j kernel. The independent Euler-cofiber and complete C4 "
                "homotopy calculation force AD2 d19; AD6 has zero d19 because its proposed "
                "target already supports d11. Historical D1 d23/d19 rows "
                "remain review, not a permanent D4 family. E-infinity is not asserted."
            )
        removed = {
            item.id for item in workspace.differentials
            if item.id in _LEGACY_MANAGED_IDS or item.id.startswith("formal_diff_")
        }
        workspace.differentials = [item for item in workspace.differentials if item.id not in removed]
        workspace.differential_events = [
            item for item in workspace.differential_events
            if item.differential_claim_id not in removed
            and not item.differential_claim_id.startswith("formal_diff_")
        ]

    occurrence: dict[str, int] = {}
    for arrow in FORMAL_ARROWS + DERIVED_FORMAL_ARROWS:
        workspace = workspaces.get(arrow.workspace_id)
        if workspace is None:
            continue
        source = _node_for(workspace, arrow.source_label, arrow.source_stem, arrow.source_filtration)
        target = _node_for(workspace, arrow.target_label, arrow.target_stem, arrow.target_filtration)
        status = ("review" if arrow.fact_id in _JAN29_PROOF_SOURCES else
                  admission.get(arrow.fact_id, {}).get("status", arrow.status))
        occurrence[arrow.fact_id] = occurrence.get(arrow.fact_id, 0) + 1
        suffix = occurrence[arrow.fact_id]
        differential_id = arrow.differential_id or f"formal_diff_{arrow.fact_id.lower()}_{suffix}"
        if differential_id in _DERIVED_ENDPOINT_STYLES:
            source_style, target_style = _DERIVED_ENDPOINT_STYLES[differential_id]
            source.style.update(source_style)
            target.style.update(target_style)
        proposition_id = _LEGACY_PROPOSITION_BY_DIFFERENTIAL.get(
            differential_id, f"formal_prop_{arrow.fact_id.lower()}_{suffix}"
        )
        proposition = next((item for item in workspace.propositions if item.id == proposition_id), None)
        statement = rf"d_{{{arrow.page}}}({arrow.source_label})={arrow.target_label}"
        period = arrow.period_stem or 64
        period_source = _PERIOD_SOURCES.get(arrow.fact_id, arrow.source_ref)
        source_refs = list(dict.fromkeys([arrow.source_ref, period_source]))
        if arrow.fact_id in _SOURCE_CONFLICTS:
            source_refs.append(_SOURCE_CONFLICTS[arrow.fact_id]["source_ref"])
        conclusion = {
            "source_id": source.id, "target_id": target.id, "page": arrow.page,
            "fact_id": arrow.fact_id, "admission_status": status,
            **_source_metadata(arrow.fact_id),
            "period_stem": period,
            "period_kind": "same-object" if period == 64 else "repeated-differential-pattern",
            "period_is_invertible": period == 64,
            "period_multiplier": "D" if period == 8 else f"D^{period // 8}",
            "period_source_ref": period_source,
            "coverage_scope": "active source formula and its declared translates; not a full page quotient certificate",
        }
        conclusion.update(_DERIVED_EVIDENCE.get(differential_id, {}))
        conclusion.update(_EULER_CHAIN_COEFFICIENTS.get(differential_id, {}))
        if arrow.fact_id in _VERIFIED_FORMAL_CERTIFICATES:
            certificate = _VERIFIED_FORMAL_CERTIFICATES[arrow.fact_id]
            conclusion.update({"verification_certificate": deepcopy(certificate),
                               "source_status": "independently-verified", "source_blockers": [],
                               "machine_verification_pending": []})
            if arrow.fact_id in {"FN-3I-007", "FN-3I-008", "FN-3I-009"}:
                conclusion.update({"withdrawn_dependencies": [], "derivation": certificate["derivation"]})
                conclusion.setdefault("derived_from", certificate["premises"][:])
        if arrow.fact_id == "FN-MIX-001" and arrow.source_stem == arrow.source_filtration == 1:
            conclusion["coefficient_parameter"] = {
                "id": "mixed_d3_C", "symbol": r"\zeta", "value": 2, "domain": [2],
                "frobenius_power": 0, "fixed_reason": "omega-Thom-Leibniz in the Witt two-layer",
            }
        if arrow.fact_id == "FN-3I-001":
            conclusion["d3_product_certificate"] = deepcopy(_THREE_D3_CERTIFICATE)
            conclusion["source_status"] = "independently-verified"
            if differential_id == "diff_three_d3":
                conclusion["derivation"] = _THREE_D3_CERTIFICATE["derivation"]
        if arrow.fact_id == "FN-MIX-005":
            conclusion["coefficient_parameter"] = dict(_MIXED_B_PARAMETER)
            if arrow.source_stem == 7:
                conclusion["coefficient_parameter"]["target_component"] = "S22H"
            conclusion["coefficient_constraint"] = (
                "The same relative unit b appears in P+bQ and bQ; it does not scale both columns. "
                "b in F4* is independently proved, but its exact value is not an admitted unit-1 normalization."
            )
        _apply_pure_galois_normalization(conclusion, workspace.id)
        parameter = conclusion.get("coefficient_parameter")
        if parameter:
            conclusion["unparameterized_statement"] = statement
            coefficient_tex = parameter.get("expression", parameter["symbol"])
            if parameter.get("target_component"):
                statement = rf"d_5({arrow.source_label})=kD(P+bQ),\quad P=(yh_2+xh_1v_1)u_{{\sigma_i+2\sigma_j}},\quad Q=(h_1^2+xh_1v_1)u_{{\sigma_i+2\sigma_j}}"
            elif parameter.get("value") != 1:
                statement = rf"d_{{{arrow.page}}}({arrow.source_label})={coefficient_tex}{arrow.target_label}"
        if conclusion.get("conditional_statement"):
            # An Euler image can already be zero in the target quotient.
            # Keep the condition in the visible formula, not just metadata.
            statement = conclusion["conditional_statement"]
        rule = (_DERIVED_EVIDENCE[differential_id]["evidence_kind"] + " from formal_notes"
                if differential_id in _DERIVED_EVIDENCE else "formal_notes active proposition")
        if proposition is None:
            proposition = Proposition(
                id=proposition_id,
                kind="differential",
                statement=statement,
                status=status,
                conclusion=conclusion,
                rule=rule,
                confidence=1.0 if status in {"admitted", "admitted-pattern"} else 0.6,
                notes=(
                    "Rendered from the active proposition ledger. Review/source-proved status is visualized "
                    "but does not enter canonical page-transition reasoning."
                ),
                source_ref=arrow.source_ref,
                source_refs=source_refs,
            )
            workspace.propositions.append(proposition)
        else:
            proposition.statement = statement
            proposition.status = status
            if (arrow.fact_id == "DER-3I-EULER-D9-B"
                    and proposition.conclusion.get("evidence_kind") == "Euler-annihilator-cutoff-derived"):
                # Retire this managed former proof, not unrelated user metadata.
                for stale_key in ("cutoff", "comparison_translation", "comparison_source_filtration",
                                  "comparison_target_filtration"):
                    proposition.conclusion.pop(stale_key, None)
            if arrow.fact_id in {"DER-3I-D9-P", "DER-3I-D9-Q", "DER-3I-D9-C"}:
                # Remove the managed obsolete conditional text without
                # dropping unrelated researcher annotations.
                proposition.conclusion.pop("conditional_statement", None)
            proposition.conclusion.update(conclusion)
            proposition.source_ref = arrow.source_ref
            proposition.source_refs = source_refs
            proposition.rule = rule
        if differential_id == _MIXED_D19_ID:
            # This derived map must be withdrawn when its outgoing-cycle
            # premise (including the external CD5 proof) is not admitted.
            proposition.premise_ids = list(dict.fromkeys([
                *proposition.premise_ids,
                f"formal_prop_{_MIXED_VD7_CYCLE_FACT.lower()}",
            ]))
        linear_map_id = _ensure_sum_map(workspace, source, target, arrow, proposition_id, status)
        workspace.differentials.append(Differential(
            id=differential_id,
            source_id=source.id,
            target_id=target.id,
            page=arrow.page,
            status=status,
            label=arrow.fact_id,
            period_stem=period,
            proposition_id=proposition_id,
            period_notes=(
                f"{arrow.fact_id}: {period}-stem {conclusion['period_multiplier']} "
                + ("permanent translation, together with forward g=kD^3."
                   if period == 64 else "repeated differential pattern; not an invertible permanent class.")
                + ((" Nonzero F4 coefficient is fixed to 1 by the Galois-invariant basis; admission is separate."
                    if parameter.get("fixed_reason") == "pure-sigma-i-galois-fixed" else
                    f" Relative F4 coefficient {parameter['symbol']} on {parameter['target_component']} only ({parameter['id']}); other target columns are unchanged."
                    if parameter.get("target_component") else
                    f" F4 coefficient {parameter['symbol']} is linked to the source workspace ({parameter['id']}); the source's coefficient and admission checks determine this map, not a mixed-local assignment."
                    if parameter.get("source_parameter") else
                    f" Source-basis F4 coefficient {parameter['symbol']} ({parameter['id']}) is fixed by {parameter.get('fixed_reason', 'the verified coefficient declaration')}; atlas Frobenius is applied when evaluating the map."
                    if parameter.get("value") is not None else
                    f" Target has F4 coefficient {parameter.get('expression', parameter['symbol'])} ({parameter['id']}); "
                    + ("the expression may be zero; " if "affine_offset" in parameter else "exact unit not fixed; ")
                    + ("only an isolated finite rank-one kernel and image may be computed without assigning this unit."
                       if conclusion.get("rank_one_unit_certificate") else "resolve the linked parameter before quotienting."))
                   if parameter else "")
            ),
            linear_map_id=linear_map_id,
            required_admitted_premises=conclusion.get("required_admitted_premises") is True,
        ))

    for claim_id, workspace_id, kind, statement, grade, page, status, source_ref in ZERO_AND_PERMANENT_CLAIMS:
        workspace = workspaces.get(workspace_id)
        if workspace is None:
            continue
        source_label, period, parent_fact = _ZERO_CLAIM_SOURCES[claim_id]
        source = _node_for(workspace, source_label, *grade)
        if claim_id in _ZERO_ENDPOINT_STYLES:
            source.style.update(_ZERO_ENDPOINT_STYLES[claim_id])
            source.style.pop("e2_components", None)
        # The later d5-zero has its own empty-target/product proof, not the d3 proof.
        status = (status if claim_id in {"FN-3I-001-Q-zero", "FN-MIX-005-Q-zero"} else
                  "review" if claim_id in _JAN29_PROOF_SOURCES else
                  admission.get(parent_fact, {}).get("status", status))
        proposition_id = f"formal_prop_{claim_id.lower()}"
        conclusion = {
            "grade": {"stem": grade[0], "filtration": grade[1]},
            "source_id": source.id,
            "source_label": source.label,
            "e2_components": source.style.get("e2_components") or {source.style["e2_pattern"]: 1},
            "page": page,
            "zero": kind == "zero-differential",
            "fact_id": claim_id,
            "origin_fact_id": parent_fact,
            "admission_status": status,
            # The Euler detector has its own restriction proof (799-809).
            # It must not inherit the later d23 proof's preimage-exclusion
            # conflict merely because the old ledger grouped them together.
            **_source_metadata(claim_id if claim_id == "FN-3I-010-pc" else parent_fact),
            "period_stem": period,
            "period_kind": "same-object" if period == 64 else "repeated-differential-pattern",
            "period_is_invertible": period == 64,
            "forward_period": {"multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True},
        }
        premise_ids = []
        derived = claim_id == "FN-2I-004-derived-zero"
        if derived:
            conclusion.update(_DERIVED_ZERO_EVIDENCE)
        elif claim_id in _MULTIPLICATIVE_ZERO_EVIDENCE:
            derived = True
            conclusion.update({"evidence_kind": "Leibniz-derived", "derived_from": [parent_fact],
                                "derivation": _MULTIPLICATIVE_ZERO_EVIDENCE[claim_id]})
        if claim_id in {"DER-3I-D5-A-EVEN", "DER-3I-D5-C-zero", "DER-3I-D7-C-zero", "DER-3I-D7-Q-zero", "DER-3I-D7-P-EVEN",
                        "DER-3I-D5-B-zero", "DER-3I-D7-B-zero"}:
            zero_premises = (["FN-2I-004", "DKLLW24 Lemma 5.2", "DKLLW24 Table 3"]
                             if claim_id == "DER-3I-D7-P-EVEN" else
                             ["FN-3I-001", "FN-3I-005", "FN-3I-006"]
                             if claim_id in {"DER-3I-D5-B-zero", "DER-3I-D7-B-zero"} else
                             ["FN-3I-002", "FN-3I-001", "DKLLW24 Tables 3 and 6"])
            conclusion.update({
                "source_status": "independently-verified", "source_blockers": [], "machine_verification_pending": [],
                "derived_from": zero_premises,
                "verification_certificate": {
                    "status": "verified",
                    "method": "Actual E2 product and finite target enumeration",
                    "scope": "source-workspace", "source_workspace_id": "ws_3sigma_i", "page": page,
                    "premises": zero_premises,
                    "derivation": _MULTIPLICATIVE_ZERO_EVIDENCE[claim_id],
                },
            })
        if claim_id in _POSITIVE_J_ZERO_EVIDENCE:
            derived = True
            conclusion.update(_POSITIVE_J_ZERO_EVIDENCE[claim_id])
        if claim_id in _PHI_ZERO_EVIDENCE:
            derived = True
            conclusion.update(deepcopy(_PHI_ZERO_EVIDENCE[claim_id]))
        if claim_id in _FINITE_D9_ZERO_EVIDENCE:
            derived = True
            conclusion.update(deepcopy(_FINITE_D9_ZERO_EVIDENCE[claim_id]))
        if claim_id in _THREE_W5_TARGET_ZERO_EVIDENCE:
            derived = True
            conclusion.update(deepcopy(_THREE_W5_TARGET_ZERO_EVIDENCE[claim_id]))
            premise_ids = ["formal_prop_der-3i-leibniz-w5-d23_1"]
        if claim_id in _THREE_CD1_ZERO_EVIDENCE:
            derived = True
            conclusion.update(deepcopy(_THREE_CD1_ZERO_EVIDENCE[claim_id]))
            if claim_id == "DER-3I-AD6-D19-zero":
                premise_ids = ["formal_prop_der-3i-euler-cd1-d11_1"]
        if claim_id in _TATE_CYCLE_EVIDENCE:
            derived = True
            conclusion.update(deepcopy(_TATE_CYCLE_EVIDENCE[claim_id]))
        if claim_id == "DER-3I-EULER-XD5-cycle":
            derived = True
            conclusion.update(deepcopy(_EULER_XD5_CYCLE_EVIDENCE))
        if claim_id == "DER-3I-EULER-CD5-cycle":
            derived = True
            conclusion.update(deepcopy(_EULER_CD5_CYCLE_EVIDENCE))
        if claim_id == _MIXED_VD7_CYCLE_FACT:
            derived = True
            conclusion.update(deepcopy(_MIXED_VD7_CYCLE_EVIDENCE))
            premise_ids = ["formal_prop_der-3i-euler-cd5-cycle"]
        if claim_id == "DER-2I-TRANSFER-TWO-cycle":
            derived = True
            conclusion.update(deepcopy(_TRANSFER_TWO_EVIDENCE))
        verification_fact = ("FN-3I-003" if claim_id == "FN-3I-001-Q-zero" else parent_fact)
        if verification_fact in _VERIFIED_FORMAL_CERTIFICATES:
            conclusion.update({"verification_certificate": deepcopy(_VERIFIED_FORMAL_CERTIFICATES[verification_fact]),
                               "source_status": "independently-verified", "source_blockers": [],
                               "machine_verification_pending": []})
        if claim_id == "FN-3I-001-zero":
            derived = True
            conclusion["d3_product_certificate"] = deepcopy(_THREE_D3_CERTIFICATE)
            conclusion["derivation"] = _THREE_D3_CERTIFICATE["derivation"]
            conclusion["source_status"] = "independently-verified"
        if claim_id == "FN-3I-003-even-zero":
            conclusion["coefficient_constraint"] = (
                "The chosen Galois-fixed basis gives relative coefficient 1 in "
                "FN-3I-003 and d5(D). Their cancellation is not an unresolved "
                "F4 choice; admission of the source differential is separate."
            )
        if claim_id == "FN-MIX-005-Q-zero":
            conclusion["coefficient_constraint"] = (
                "The independently repaired nonzero b premise and finite target injection prove this zero map. "
                "Its exact unit is unnecessary; no coefficient assignment or admission of the P+bQ arrow is made."
            )
            conclusion["derived_from"] = ["DER-MIX-D5-B-NONZERO", "FN-MIX-004", "FN-MIX-005", "DKLLW24 Table 6"]
            conclusion.update({
                "source_status": "independently-verified", "source_blockers": [],
                "printed_claim_conflicts": conclusion.get("source_conflicts", []),
                "source_conflicts": [], "machine_verification_pending": [],
                "verification_certificate": {
                    "status": "verified", "method": "Nonzero parameter, square-zero and finite target injection",
                    "scope": "source-workspace", "source_workspace_id": "ws_sigma_i_2sigma_j", "page": 5,
                    "premises": conclusion["derived_from"][:],
                    "nonzero_parameter_certificate": deepcopy(_MIXED_B_NONZERO_CERTIFICATE),
                    "target_injection": {
                        "source_bidegree": [1, 7], "target_bidegree": [13, 11],
                        "source": "x^3kDu", "target": "x^3k^2D^3u", "multiplier": "kD^2",
                        "empty_d3_incoming_cells": [[2, 4], [14, 8]],
                        "scope": "The one-dimensional E5 candidate target, not global injectivity of k.",
                    },
                    "Leibniz_term": "d5(kD2)Q=k2D2h2Q=0; kD2 need not be a 5-cycle.",
                    "closure": "All integer D powers since Qh2=0, all positive j powers and forward g.",
                    "positive_j_layers": (
                        "At filtration 2 the positive-j Q tail remains: its Tate d3 preimage has filtration -1. "
                        "For g^q j^n QD^m with q,n>=1 the primitive HFPSS d3 preimage has filtration 4q-1."
                    ),
                    "derivation": _MULTIPLICATIVE_ZERO_EVIDENCE[claim_id],
                },
            })
        _apply_pure_galois_normalization(conclusion, workspace.id)
        claim_rule = ("Adjusted Euler preimage and complete C4 filtration" if claim_id == "DER-3I-EULER-CD5-cycle"
                      else "Euler cofiber and complete C4 filtration bound" if claim_id == "DER-3I-EULER-XD5-cycle"
                      else "Euler/Tate cycle certificate from DKLLW24" if claim_id in _TATE_CYCLE_EVIDENCE
                      else "RO kernel-subgroup transfer" if claim_id == "DER-2I-TRANSFER-TWO-cycle"
                      else "Leibniz-derived from formal_notes" if derived
                      else "formal_notes active proposition")
        proposition = next((item for item in workspace.propositions if item.id == proposition_id), None)
        if proposition is not None:
            proposition.status = status
            proposition.conclusion.update(conclusion)
            proposition.rule = claim_rule
            if premise_ids:
                proposition.premise_ids = list(dict.fromkeys([*proposition.premise_ids, *premise_ids]))
            continue
        workspace.propositions.append(Proposition(
            id=proposition_id,
            kind=kind,
            statement=statement,
            status=status,
            conclusion=conclusion,
            premise_ids=premise_ids,
            rule=claim_rule,
            confidence=1.0 if status == "admitted" else 0.6,
            notes="A zero differential is cycle metadata, not a fake arrow to a zero node.",
            source_ref=source_ref,
            source_refs=[source_ref],
        ))
    _reconcile_original_demo_aliases(project)
    return project


def formal_arrow_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for arrow in FORMAL_ARROWS:
        counts[arrow.workspace_id] = counts.get(arrow.workspace_id, 0) + 1
    return counts
