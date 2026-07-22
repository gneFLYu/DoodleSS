"""A provenance-preserving seed distilled from the local REU Projects archive.

This is intentionally a navigable research index, not a claim that the draft
notes constitute a completed proof.  Every statement is labelled with its
status and the file that supplied it, so later corrections can be recorded
without deleting the mathematical history.
"""
from __future__ import annotations

from .models import (
    ClassNode, Comparison, Differential, Grade, PeriodFamily, PeriodGenerator,
    Project, Proposition, Workspace,
)
from .e2_import import materialize_verified_e2_records_for_project


ARCHIVE = "REU Projects archive: Note/formal_notes.tex, final report.tex, and main.md"
FORMAL = "Note/formal_notes.tex"
REPORT = "Final Presentation/final report.tex"
LOG = "main.md working log"


def _workspace(
    ident: str,
    name: str,
    grading: str,
    summary: str,
    *,
    line: int = 23,
    stem_min: int = -8,
    stem_max: int = 32,
    filt_max: int = 28,
) -> Workspace:
    return Workspace(
        id=ident,
        name=name,
        grading_label=grading,
        summary=summary,
        settings={
            "vanishing_line": line,
            "page_limit": 25,
            "grid": {"stem_min": stem_min, "stem_max": stem_max, "filtration_min": 0, "filtration_max": filt_max},
            "rendering": {
                "buffer_cells": 6,
                "base_cell": 28,
                "minimum_zoom": 0.72,
                # A universal D-period is deliberately not declared here.
                # D is only a 3-cycle, so later-page families use the
                # individually documented periods on their differentials.
                "periodicity": [],
            },
            "research_source": ARCHIVE,
            "vanishing_line_source": "DKLLW24, Theorem 4.8 (Q8 HFPSS for E2; strong vanishing line at filtration 23)",
        },
    )


def _node(
    ident: str,
    label: str,
    stem: int,
    filtration: int,
    representation: dict[str, int] | None = None,
    *,
    state: str = "unknown",
    notes: str = "",
) -> ClassNode:
    return ClassNode(
        id=ident,
        label=label,
        grade=Grade(stem, filtration, representation or {}),
        state=state,
        notes=notes,
    )


def _diff(
    ident: str,
    source: str,
    target: str,
    page: int,
    status: str = "derived",
    *,
    period_stem: int = 0,
    period_filtration: int = 0,
) -> Differential:
    return Differential(
        id=ident,
        source_id=source,
        target_id=target,
        page=page,
        status=status,
        period_stem=period_stem,
        period_filtration=period_filtration,
    )


def _prop(
    ident: str,
    statement: str,
    *,
    kind: str = "differential",
    status: str = "derived",
    conclusion: dict | None = None,
    premise_ids: list[str] | None = None,
    rule: str = "manual",
    confidence: float = 0.75,
    notes: str = "",
    source_ref: str = FORMAL,
) -> Proposition:
    return Proposition(
        id=ident,
        kind=kind,
        statement=statement,
        status=status,
        conclusion=conclusion or {},
        premise_ids=premise_ids or [],
        rule=rule,
        confidence=confidence,
        notes=notes,
        source_ref=source_ref,
    )


def research_project() -> Project:
    """Create the local-first research workspace represented by the Overleaf zip."""
    integer = _workspace(
        "ws_integer",
        "Q8 HFPSS — integer graded",
        "integer",
        "Reference workspace for the integer-graded calculation used to transport differentials to RO(Q8) shifts.",
    )
    integer.classes = [
        _node("int_D", "D", 8, 0, state="unknown", notes="Supports the established d5; it is not a permanent cycle."),
        _node("int_h2D", "kh_2D", 7, 5, state="target"),
        _node("int_D2", "D^2", 16, 0, state="unknown"),
        _node("int_h2D2", "2kh_2D^2", 15, 5, state="target"),
        _node("int_Dinvh1", "D^{-1}h_1", -8, 1, state="unknown", notes="The working log uses its integer-page d_23 as a constraint."),
        _node("int_D8", "D^8", 64, 0, state="permanent", notes="The 64-periodicity class is invertible and permanent."),
    ]
    integer.differentials = [
        _diff("diff_int_d5_D", "int_D", "int_h2D", 5, "established"),
        _diff("diff_int_d5_D2", "int_D2", "int_h2D2", 5, "established"),
    ]
    integer.propositions = [
        _prop(
            "prop_int_d5_D",
            "d_5(D) = kh_2D",
            status="established",
            conclusion={"source_id": "int_D", "target_id": "int_h2D", "page": 5},
            confidence=0.95,
            notes="Recorded as integer-graded input and cited in the REU formal notes.",
            source_ref="DKLLW24, Corollary 4.15 (as cited in Note/formal_notes.tex)",
        ),
        _prop(
            "prop_int_D8_period",
            "D^8 is an invertible permanent cycle giving 64-periodicity",
            kind="permanent-cycle",
            status="established",
            conclusion={"class_id": "int_D8"},
            confidence=0.98,
            notes="The period is source-scoped to the Q8 HFPSS for E2.",
            source_ref="DKLLW24, Proposition 4.1 (PDF p. 19)",
        ),
        _prop(
            "prop_int_d5_D2",
            "d_5(D^2) = 2kh_2D^2",
            status="established",
            conclusion={"source_id": "int_D2", "target_id": "int_h2D2", "page": 5},
            confidence=0.95,
            notes="Integer-graded input used by the shifted computations.",
            source_ref="DKLLW24, Corollary 4.15 (as cited in Note/formal_notes.tex)",
        ),
    ]

    sigma = _workspace(
        "ws_sigma_i",
        "Q8 HFPSS — (* − σᵢ)",
        "*-sigma_i",
        "Known shifted comparison page.  Euler-class multiplication and its extensions feed the 2σᵢ and 3σᵢ workspaces.",
    )
    sigma.classes = [
        _node("sig_a", "a_{\\sigma_i}", -1, 1, {"sigma_i": -1}, state="permanent", notes="Euler class treated as a permanent cycle in the formal notes."),
        _node("sig_xplusy", "\\{x+y\\}u_{\\sigma_i}", -1, 1, {"sigma_i": -1}, state="unknown", notes="DKLLW24 Table 5 source-backed E2 coordinate."),
        _node("sig_x3", "x^3D^4u_{\\sigma_i}", 32, 3, {"sigma_i": -1}, state="unknown", notes="Used in a non-transfer argument."),
    ]
    sigma.propositions = [
        _prop(
            "prop_sig_euler",
            "a_{\\sigma_i} is a permanent cycle",
            kind="permanent-cycle",
            status="established",
            conclusion={"class_id": "sig_a"},
            confidence=0.92,
            notes="Used as a multiplier in the shifted HFPSS arguments.",
            source_ref=FORMAL,
        ),
    ]

    two_sigma = _workspace(
        "ws_2sigma_i",
        "Q8 HFPSS — (* − 2σᵢ)",
        "*-2sigma_i",
        "Most developed shifted page in the archive: d3, d5, and higher differential families with restriction, transfer, and vanishing-line evidence.",
        filt_max=30,
    )
    two_sigma.classes = [
        _node("two_u", "u_{2\\sigma_i}", 0, 0, {"sigma_i": -2}, state="killed"),
        _node("two_x2h1u", "x^2h_1u_{2\\sigma_i}", -1, 3, {"sigma_i": -2}, state="target"),
        _node("two_a2", "\\{x^2+y^2\\}u_{2\\sigma_i}", 0, 2, {"sigma_i": -2}, state="permanent", notes="Identified with a_{2σᵢ} in the notes."),
        _node("two_D", "Du_{2\\sigma_i}", 8, 0, {"sigma_i": -2}, state="unknown"),
        _node("two_2D", "2Du_{2\\sigma_i}", 8, 0, {"sigma_i": -2}, state="killed"),
        _node("two_h2D", "h_2Du_{2\\sigma_i}", 11, 1, {"sigma_i": -2}, state="killed"),
        _node("two_kh2sqD", "kh_2^2Du_{2\\sigma_i}", 10, 6, {"sigma_i": -2}, state="target"),
        _node("two_2kh2D", "2kh_2Du_{2\\sigma_i}", 7, 5, {"sigma_i": -2}, state="target"),
        _node("two_xh1u", "xh_1u_{2\\sigma_i}", 7, 1, {"sigma_i": -2}, state="killed"),
        _node("two_kh1cubedu", "kh_1^3u_{2\\sigma_i}", 6, 6, {"sigma_i": -2}, state="target"),
        _node("two_a2D2", "\\{x^2+y^2\\}D^2u_{2\\sigma_i}", 14, 2, {"sigma_i": -2}, state="killed"),
        _node("two_k3h1D3", "k^3h_1D^3u_{2\\sigma_i}", 13, 13, {"sigma_i": -2}, state="target"),
        _node("two_k2h1sqD3", "k^2h_1^2D^3u_{2\\sigma_i}", 18, 10, {"sigma_i": -2}, state="killed"),
        _node("two_k4xh1sqD4", "k^4xh_1^2D^4u_{2\\sigma_i}", 17, 19, {"sigma_i": -2}, state="target"),
        _node("two_2h2D3", "2h_2D^3u_{2\\sigma_i}", 27, 1, {"sigma_i": -2}, state="killed"),
        _node("two_d13target", "d_{13}\\text{-target}", 26, 14, {"sigma_i": -2}, state="target", notes="Target label is intentionally generic until imported chart coordinates are normalized."),
    ]
    two_sigma.differentials = [
        _diff("diff_two_d3_u", "two_u", "two_x2h1u", 3, period_stem=8),
        _diff("diff_two_d5_h2D", "two_h2D", "two_kh2sqD", 5, period_stem=16),
        _diff("diff_two_d5_2D", "two_2D", "two_2kh2D", 5, period_stem=16),
        _diff("diff_two_d5_xh1", "two_xh1u", "two_kh1cubedu", 5, period_stem=8),
        _diff("diff_two_d9", "two_k2h1sqD3", "two_k4xh1sqD4", 9, period_stem=32),
        _diff("diff_two_d11", "two_a2D2", "two_k3h1D3", 11, period_stem=32),
        _diff("diff_two_d13", "two_2h2D3", "two_d13target", 13, period_stem=32),
    ]
    two_sigma.propositions = [
        _prop("prop_two_a2_pc", "\\{x^2+y^2\\}u_{2\\sigma_i} = a_{2\\sigma_i} is a permanent cycle", kind="permanent-cycle", status="derived", conclusion={"class_id": "two_a2"}, rule="EulerClass", confidence=0.84, notes="The formal notes use this to force the d3 on u_{2σᵢ}.", source_ref=FORMAL),
        _prop("prop_two_d3_u", "d_3(u_{2\\sigma_i}) = x^2h_1u_{2\\sigma_i}", conclusion={"source_id": "two_u", "target_id": "two_x2h1u", "page": 3}, premise_ids=["prop_two_a2_pc"], rule="Restriction + LeibnizRule", confidence=0.84, notes="The draft rules out the possible d5 values using C4 restriction and the permanent Euler class; stated with 8-periodicity.", source_ref=FORMAL),
        _prop("prop_two_d5_h2D", "d_5(h_2Du_{2\\sigma_i}) = kh_2^2Du_{2\\sigma_i}", conclusion={"source_id": "two_h2D", "target_id": "two_kh2sqD", "page": 5}, premise_ids=["prop_int_d5_D"], rule="Restriction", confidence=0.78, notes="Derived by restricting to C4⟨i⟩ and importing the indicated C4 differential; the draft records 16-periodicity.", source_ref=FORMAL),
        _prop("prop_two_d5_2D", "d_5(2Du_{2\\sigma_i}) = 2kh_2Du_{2\\sigma_i}", conclusion={"source_id": "two_2D", "target_id": "two_2kh2D", "page": 5}, rule="Transfer", confidence=0.78, notes="Transferred from the recorded C4 d5 on Δ₁.", source_ref=FORMAL),
        _prop("prop_two_d5_xh1", "d_5(xh_1u_{2\\sigma_i}) = kh_1^3u_{2\\sigma_i}", conclusion={"source_id": "two_xh1u", "target_id": "two_kh1cubedu", "page": 5}, rule="Transfer", confidence=0.76, notes="Uses two C4 transfers and the absence of a compatible surviving target.", source_ref=FORMAL),
        _prop("prop_two_d9", "d_9(k^2h_1^2D^3u_{2\\sigma_i}) = k^4xh_1^2D^4u_{2\\sigma_i}", conclusion={"source_id": "two_k2h1sqD3", "target_id": "two_k4xh1sqD4", "page": 9}, rule="Transfer + VanishingLine", confidence=0.67, notes="The source is selected because the target is a C4 transfer that must die by length at most 13.  Preserve this as a reviewable draft claim.", source_ref=FORMAL),
        _prop("prop_two_d11", "d_{11}(\\{x^2+y^2\\}D^2u_{2\\sigma_i}) = k^3h_1D^3u_{2\\sigma_i}", conclusion={"source_id": "two_a2D2", "target_id": "two_k3h1D3", "page": 11}, rule="Restriction", confidence=0.7, notes="The notes use C4 periodicity and eliminate the other target because it is already a d9 target.", source_ref=FORMAL),
        _prop("prop_two_d13", "2h_2D^3u_{2\\sigma_i} supports a d_{13}", conclusion={"source_id": "two_2h2D3", "target_id": "two_d13target", "page": 13}, rule="Restriction + Transfer", confidence=0.62, notes="Keep the target under review until the source chart is imported with fixed coordinates.", source_ref=FORMAL),
    ]

    three_sigma = _workspace(
        "ws_3sigma_i",
        "Q8 HFPSS — (* − 3σᵢ)",
        "*-3sigma_i",
        "Built from the 2σᵢ page by Euler-class multiplication; the working log flags this page for continued consistency checks.",
        filt_max=30,
    )
    # Keep the selector label ASCII-safe on Windows while TeX labels remain
    # rendered by KaTeX in the chart itself.
    three_sigma.name = "Q8 HFPSS - (*-3sigma_i)"
    three_sigma.summary = "Documented *-3sigma_i calculation through E12: one 8-periodic d3 family, five 16-periodic d5 families, and under-review 32-periodic d9/d11 families from the working log. E12 is not asserted to be E-infinity."
    # The formal notes determine d3/d5. The working log adds d9/d11 but
    # leaves the final d19/d23 alternative open; E12 is never E-infinity.
    three_sigma.settings["known_page_max"] = 12
    three_sigma.classes = [
        _node("three_v1sq", "v_1^2u_{3\\sigma_i}", 4, 0, {"sigma_i": -3}, state="killed"),
        _node("three_h1cubed", "h_1^3u_{3\\sigma_i}", 3, 3, {"sigma_i": -3}, state="target"),
        _node("three_combo", "\\{h_1+xv_1\\}u_{3\\sigma_i}", 1, 1, {"sigma_i": -3}, state="unknown"),
        _node("three_k2a2D3", "k^2\\{x^2+y^2\\}D^3u_{3\\sigma_i}", 14, 10, {"sigma_i": -3}, state="killed"),
        _node("three_k3xh1sqD3", "k^3\\{x+y\\}h_1^2D^3u_{3\\sigma_i}", 13, 15, {"sigma_i": -3}, state="target"),
        _node("three_yh2_source", "\\{yh_2+xh_1v_1\\}Du_{3\\sigma_i}", 10, 2, {"sigma_i": -3}, state="killed"),
        _node("three_kx3_target", "kx^3D^2u_{3\\sigma_i}", 9, 7, {"sigma_i": -3}, state="target"),
        _node("three_x3_source", "x^3D^2u_{3\\sigma_i}", 13, 3, {"sigma_i": -3}, state="killed"),
        _node("three_2v1_target", "2v_1^2k^2D^2u_{3\\sigma_i}", 12, 8, {"sigma_i": -3}, state="target"),
        _node("three_xyD2_source", "\\{x+y\\}D^2u_{3\\sigma_i}", 15, 1, {"sigma_i": -3}, state="killed"),
        _node("three_h1xv1_target", "\\{h_1+xv_1\\}h_1kD^2u_{3\\sigma_i}", 14, 6, {"sigma_i": -3}, state="target"),
        _node("three_sum_source", "\\{x+y\\}Du_{3\\sigma_i}", 7, 1, {"sigma_i": -3}, state="killed"),
        _node("three_sum_target", "k\\{yh_2+h_1^2\\}Du_{3\\sigma_i}", 6, 6, {"sigma_i": -3}, state="target"),
        _node("three_d9_25_source", "\\{x+y\\}h_1^2D^3u_{3\\sigma_i}", 25, 3, {"sigma_i": -3}, state="killed"),
        _node("three_d9_25_target", "2v_1^2k^3D^4u_{3\\sigma_i}", 24, 12, {"sigma_i": -3}, state="target"),
        _node("three_d11_30_source", "\\{x^2+y^2\\}D^4u_{3\\sigma_i}", 30, 2, {"sigma_i": -3}, state="killed"),
        _node("three_d11_30_target", "\\{h_1+xv_1\\}k^3D^5u_{3\\sigma_i}", 29, 13, {"sigma_i": -3}, state="target"),
        _node("three_d9_17_source", "D^2\\{h_1+xv_1\\}u_{3\\sigma_i}", 17, 1, {"sigma_i": -3}, state="killed"),
        _node("three_d9_17_target", "k^2D^3\\{x+y\\}h_1u_{3\\sigma_i}", 16, 10, {"sigma_i": -3}, state="target"),
        _node("three_d9_18_source", "D^2h_1\\{h_1+xv_1\\}u_{3\\sigma_i}", 18, 2, {"sigma_i": -3}, state="killed"),
        _node("three_d9_18_target", "k^2D^3\\{x+y\\}h_1^2u_{3\\sigma_i}", 17, 11, {"sigma_i": -3}, state="target"),
        _node("three_d9_32_source", "\\{x+y\\}h_1D^4u_{3\\sigma_i}", 32, 2, {"sigma_i": -3}, state="killed"),
        _node("three_d9_32_target", "x^2h_1k^2D^5u_{3\\sigma_i}", 31, 11, {"sigma_i": -3}, state="target"),
        _node("three_d9_25b_source", "\\{h_1+xv_1\\}D^3u_{3\\sigma_i}", 25, 1, {"sigma_i": -3}, state="killed"),
        _node("three_d9_25b_target", "\\{x+y\\}h_1k^2D^4u_{3\\sigma_i}", 24, 10, {"sigma_i": -3}, state="target"),
    ]
    three_sigma.differentials = [
        _diff("diff_three_d3", "three_v1sq", "three_h1cubed", 3, period_stem=8),
        _diff("diff_three_d5_main", "three_k2a2D3", "three_k3xh1sqD3", 5, period_stem=16),
        _diff("diff_three_d5_yh2", "three_yh2_source", "three_kx3_target", 5, period_stem=16),
        _diff("diff_three_d5_x3", "three_x3_source", "three_2v1_target", 5, period_stem=16),
        _diff("diff_three_d5_xyD2", "three_xyD2_source", "three_h1xv1_target", 5, period_stem=16),
        _diff("diff_three_d5_sum", "three_sum_source", "three_sum_target", 5, period_stem=16),
        _diff("diff_three_d9_25", "three_d9_25_source", "three_d9_25_target", 9, "under-review", period_stem=32),
        _diff("diff_three_d11_30", "three_d11_30_source", "three_d11_30_target", 11, "under-review", period_stem=32),
        _diff("diff_three_d9_17", "three_d9_17_source", "three_d9_17_target", 9, "under-review", period_stem=32),
        _diff("diff_three_d9_18", "three_d9_18_source", "three_d9_18_target", 9, "under-review", period_stem=32),
        _diff("diff_three_d9_32", "three_d9_32_source", "three_d9_32_target", 9, "under-review", period_stem=32),
        _diff("diff_three_d9_25b", "three_d9_25b_source", "three_d9_25b_target", 9, "under-review", period_stem=32),
    ]
    three_sigma.propositions = [
        _prop("prop_three_d3", "d_3(v_1^2u_{3\\sigma_i}) = h_1^3u_{3\\sigma_i}", conclusion={"source_id": "three_v1sq", "target_id": "three_h1cubed", "page": 3}, premise_ids=["prop_two_d3_u", "prop_sig_euler"], rule="LeibnizRule", confidence=0.77, notes="Computed by multiplying the 2σᵢ d3 with the σᵢ orientation class; stated with 8-periodicity.", source_ref=FORMAL),
        _prop("prop_three_d5_main", "k^2\\{x^2+y^2\\}D^3u_{3\\sigma_i} supports a d_5", conclusion={"source_id": "three_k2a2D3", "target_id": "three_k3xh1sqD3", "page": 5}, premise_ids=["prop_two_d9"], rule="LeibnizRule", confidence=0.66, notes="The formal notes force the shorter d5 because a transported d9 target must vanish by E9.", source_ref=FORMAL),
        _prop("prop_three_d5_yh2", "d_5(\\{yh_2+xh_1v_1\\}Du_{3\\sigma_i}) = kx^3D^2u_{3\\sigma_i}", conclusion={"source_id": "three_yh2_source", "target_id": "three_kx3_target", "page": 5}, premise_ids=["prop_two_d5_h2D"], rule="LeibnizRule + h2Extension", confidence=0.8, notes="The target coordinate is determined by the d5 bidegree from the supplied source coordinate.", source_ref=FORMAL),
        _prop("prop_three_d5_x3", "d_5(x^3D^2u_{3\\sigma_i}) = 2v_1^2k^2D^2u_{3\\sigma_i}", conclusion={"source_id": "three_x3_source", "target_id": "three_2v1_target", "page": 5}, premise_ids=["prop_three_d5_yh2"], rule="h2Extension", confidence=0.75, notes="The source is stated at (13,3); the target coordinate follows the d5 bidegree.", source_ref=FORMAL),
        _prop("prop_three_d5_xyD2", "d_5(\\{x+y\\}D^2u_{3\\sigma_i}) = \\{h_1+xv_1\\}h_1kD^2u_{3\\sigma_i}", conclusion={"source_id": "three_xyD2_source", "target_id": "three_h1xv1_target", "page": 5}, premise_ids=["prop_three_d5_x3"], rule="Degree + LeibnizRule", confidence=0.75, notes="The source and target coordinates are explicitly supplied in the formal notes.", source_ref=FORMAL),
        _prop("prop_three_d5_sum", "d_5(\\{x+y\\}Du_{3\\sigma_i}) = k\\{yh_2+h_1^2\\}Du_{3\\sigma_i}", conclusion={"source_id": "three_sum_source", "target_id": "three_sum_target", "page": 5}, rule="LeibnizRule", confidence=0.68, notes="The working log explicitly says this differential must kill the sum rather than either summand alone.", source_ref=FORMAL),
        _prop("prop_three_review", "The *−3σᵢ higher-differential pattern remains under review", kind="relation", status="under-review", rule="ResearchLog", confidence=0.4, notes="The working log records corrected d9 periodicity and asks for continued consistency checks.", source_ref=LOG),
        _prop("prop_three_d9_25", "d_9(\\{x+y\\}h_1^2D^3u_{3\\sigma_i}) = 2v_1^2k^3D^4u_{3\\sigma_i}", status="under-review", conclusion={"source_id": "three_d9_25_source", "target_id": "three_d9_25_target", "page": 9}, rule="h1Extension", confidence=0.55, notes="32-periodic working-log proposition; import is intentionally under review.", source_ref=LOG),
        _prop("prop_three_d11_30", "d_{11}(\\{x^2+y^2\\}D^4u_{3\\sigma_i}) = \\{h_1+xv_1\\}k^3D^5u_{3\\sigma_i}", status="under-review", conclusion={"source_id": "three_d11_30_source", "target_id": "three_d11_30_target", "page": 11}, rule="Restriction + Degree", confidence=0.5, notes="Working-log proposition; its proof is not part of the later formal-notes subsection.", source_ref=LOG),
        _prop("prop_three_d9_17", "d_9(D^2\\{h_1+xv_1\\}u_{3\\sigma_i}) = k^2D^3\\{x+y\\}h_1u_{3\\sigma_i}", status="under-review", conclusion={"source_id": "three_d9_17_source", "target_id": "three_d9_17_target", "page": 9}, rule="LeibnizRule", confidence=0.5, notes="First 32-periodic d9 in the working log.", source_ref=LOG),
        _prop("prop_three_d9_18", "d_9(D^2h_1\\{h_1+xv_1\\}u_{3\\sigma_i}) = k^2D^3\\{x+y\\}h_1^2u_{3\\sigma_i}", status="under-review", conclusion={"source_id": "three_d9_18_source", "target_id": "three_d9_18_target", "page": 9}, rule="LeibnizRule", confidence=0.5, notes="Second 32-periodic d9 in the working log.", source_ref=LOG),
        _prop("prop_three_d9_32", "d_9(\\{x+y\\}h_1D^4u_{3\\sigma_i}) = x^2h_1k^2D^5u_{3\\sigma_i}", status="under-review", conclusion={"source_id": "three_d9_32_source", "target_id": "three_d9_32_target", "page": 9}, rule="LeibnizRule", confidence=0.48, notes="32-periodic working-log proposition.", source_ref=LOG),
        _prop("prop_three_d9_25b", "d_9(\\{h_1+xv_1\\}D^3u_{3\\sigma_i}) = \\{x+y\\}h_1k^2D^4u_{3\\sigma_i}", status="under-review", conclusion={"source_id": "three_d9_25b_source", "target_id": "three_d9_25b_target", "page": 9}, rule="LeibnizRule", confidence=0.48, notes="32-periodic working-log proposition.", source_ref=LOG),
    ]

    mixed = _workspace(
        "ws_sigma_i_2sigma_j",
        "Q8 HFPSS — (* − σᵢ − 2σⱼ)",
        "*-sigma_i-2sigma_j",
        "Mixed grading requiring the C3 action on coefficients; use this workspace to track formulas that must be rechecked after changing the σⱼ orientation convention.",
    )
    mixed.classes = [
        _node("mixed_v1sq", "v_1^2u_{\\sigma_i+2\\sigma_j}", 4, 0, {"sigma_i": -1, "sigma_j": -2}, state="killed"),
        _node("mixed_h1", "h_1^2u_{\\sigma_i+2\\sigma_j}", 3, 3, {"sigma_i": -1, "sigma_j": -2}, state="target"),
        _node("mixed_combo", "\\{h_1+xv_1\\}u_{\\sigma_i+2\\sigma_j}", 1, 1, {"sigma_i": -1, "sigma_j": -2}, state="unknown"),
    ]
    mixed.differentials = [_diff("diff_mixed_d3", "mixed_v1sq", "mixed_h1", 3, "under-review")]
    mixed.propositions = [
        _prop("prop_mixed_d3", "d_3(v_1^2u_{\\sigma_i+2\\sigma_j}) = h_1^2u_{\\sigma_i+2\\sigma_j}", status="under-review", conclusion={"source_id": "mixed_v1sq", "target_id": "mixed_h1", "page": 3}, rule="LeibnizRule + C3Action", confidence=0.42, notes="The formal draft contains this formula, while the working log warns that the C3 action can change ζ-coefficients. Do not promote without rechecking the convention.", source_ref=f"{FORMAL}; {LOG}"),
        _prop("prop_mixed_c3", "Mixed-page formulas require an explicit C3-action coefficient check", kind="relation", status="under-review", rule="C3Action", confidence=0.35, notes="The log specifically flags Sections 6.5–6.6 as invalid and requires the corrected σⱼ orientation convention.", source_ref=LOG),
    ]

    c4 = _workspace(
        "ws_c4_j",
        "C4⟨j⟩ HFPSS — restriction reference",
        "C4 reference",
        "Reference chart for imported C4 differentials and transfer targets. It is not a replacement for a full C4 calculation.",
        line=0,
    )
    c4.group = "C4"
    c4.classes = [
        _node("c4_h2", "\\bar{\\mathfrak d}_1^3u_{3\\lambda}u_{2\\sigma}a_{\\sigma}", 11, 1, state="killed"),
        _node("c4_target", "C_4\\text{-}d_5\\text{ target}", 10, 6, state="target"),
        _node("c4_delta", "\\Delta_1", 8, 0, state="killed"),
        _node("c4_delta_target", "\\bar{\\mathfrak d}_1^3u_{\\lambda}uu_{2\\sigma}a_{2\\lambda}a_{\\sigma}", 7, 5, state="target"),
    ]
    c4.differentials = [_diff("diff_c4_d5_h2", "c4_h2", "c4_target", 5, "established"), _diff("diff_c4_d5_delta", "c4_delta", "c4_delta_target", 5, "established")]
    c4.propositions = [
        _prop("prop_c4_d5_h2", "The recorded C4 restriction supports the d_5 used for h_2Du_{2σᵢ}", status="established", conclusion={"source_id": "c4_h2", "target_id": "c4_target", "page": 5}, rule="C4Input", confidence=0.88, notes="Imported reference used by the Q8 restriction argument.", source_ref=FORMAL),
        _prop("prop_c4_d5_delta", "d_5(Δ_1) gives the transfer input for d_5(2Du_{2σᵢ})", status="established", conclusion={"source_id": "c4_delta", "target_id": "c4_delta_target", "page": 5}, rule="C4Input", confidence=0.88, notes="Imported reference used by the Q8 transfer argument.", source_ref=FORMAL),
    ]

    tate = _workspace(
        "ws_tate",
        "Q8 TateSS — comparison reference",
        "Q8 TateSS",
        "A minimal TateSS reference workspace. The formal notes use invertibility of k in TateSS to organize the H-shift periodicity.",
        line=0,
    )
    tate.classes = [_node("tate_k", "k", 0, 0, state="permanent", notes="Treated as invertible in the recorded Q8 TateSS argument."), _node("tate_g", "g=kD^3", 20, 4, state="permanent", notes="Distinguished class g in the Q8 HFPSS.")]
    tate.propositions = [_prop("prop_tate_k", "k is invertible in the Q8 TateSS comparison", kind="comparison", status="derived", conclusion={"class_id": "tate_k"}, rule="TateComparison", confidence=0.7, notes="This is used as a periodicity device in the H-shift argument.", source_ref=FORMAL)]

    h_shift = _workspace(
        "ws_H",
        "Q8 HFPSS — (* − ℍ)",
        "*-H",
        "The ℍ-shift is organized by the 20+ℍ period and the norm period 1+σᵢ+σⱼ+σₖ+ℍ rather than by a separate hand-drawn page.",
    )
    h_shift.classes = [
        _node("H_a", "a_{\\mathbb H}", -4, 1, {"H": -1}, state="permanent", notes="Euler class."),
        _node("H_period", "(kD^3)^{-1}a_{\\mathbb H}", -20, 1, {"H": -1}, state="permanent", notes="Recorded 20+ℍ periodicity generator."),
    ]
    h_shift.propositions = [
        _prop("prop_H_a", "a_{\\mathbb H} is a permanent Euler class", kind="permanent-cycle", status="established", conclusion={"class_id": "H_a"}, rule="EulerClass", confidence=0.92, source_ref=FORMAL),
        _prop("prop_H_period", "(kD^3)^{-1}a_{\\mathbb H} gives the 20+ℍ periodicity", kind="comparison", status="derived", conclusion={"class_id": "H_period"}, premise_ids=["prop_H_a", "prop_tate_k"], rule="TateComparison + EulerClass", confidence=0.74, notes="Use only as a comparison/periodicity rule; it does not silently transport every differential.", source_ref=FORMAL),
    ]

    comparisons = [
        Comparison("cmp_integer_2sigma", integer.id, two_sigma.id, "Orientable 2σᵢ translation", Grade(representation={"sigma_i": -2}), "orientation", "Multiply by u_{2σᵢ}; review the chosen coordinate convention before accepting a transported arrow.", FORMAL),
        Comparison("cmp_2sigma_3sigma", two_sigma.id, three_sigma.id, "Euler multiplication by a_{σᵢ}", Grade(representation={"sigma_i": -1}), "Euler multiplication", "Use the permanent Euler class to relate 2σᵢ and 3σᵢ families.", FORMAL),
        Comparison("cmp_c4_restrict_2sigma", c4.id, two_sigma.id, "C4⟨j⟩ restriction evidence", Grade(), "restriction", "Imported C4 differential constrains the Q8 source or target by naturality.", FORMAL),
        Comparison("cmp_c4_transfer_2sigma", c4.id, two_sigma.id, "C4⟨i⟩ transfer evidence", Grade(), "transfer", "Transferred C4 classes provide Q8 targets and differential obligations.", FORMAL),
        Comparison("cmp_tate_H", tate.id, h_shift.id, "TateSS → H-shift periodicity", Grade(representation={"H": -1}, stem=-20), "tate-comparison", "Use invertibility in TateSS together with the H Euler class to organize periodicity.", FORMAL),
    ]

    project = Project(
        id="hfpss_studio",
        name="RO(Q8)-graded HFPSS for Morava E2",
        workspaces=[integer, sigma, two_sigma, three_sigma, mixed, c4, tate, h_shift],
        comparisons=comparisons,
        research_brief={
            "source": "Local REU_Projects (1).zip",
            "scope": "RO(Q8)-graded HFPSS for height-2 Morava E-theory",
            "reduction": "RO(Q8)/~ ≅ Z/64 ⊕ Z/4 ⊕ Z/4 ⊕ Z/2; nine representative grading cases up to symmetry.",
            "status_policy": "Statements imported from drafts remain derived or under-review unless the archive explicitly treats them as established input.",
        },
    )
    project.research_brief["reduction"] = (
        "All 16 (* - a sigma_i - b sigma_j), 0<=a,b<=3, are stored; "
        "C3 transport does not quotient by an i/j transposition."
    )
    project.period_families = [
        PeriodFamily(
            id="period_integer_D_E2", name="E2 D-period", workspace_id=integer.id, rank=1,
            generators=[PeriodGenerator(Grade(stem=8, filtration=0), "D")],
            valid_from_page=2, valid_to_page=2, status="established",
            source_ref="DKLLW24, \u00a76.1.2 (PDF p. 40)",
        ),
        PeriodFamily(
            id="period_integer_D8", name="D^8 64-period", workspace_id=integer.id, rank=1,
            generators=[PeriodGenerator(Grade(stem=64, filtration=0), "D^8")],
            valid_from_page=3, valid_to_page="infinity", certificate_proposition_id="prop_int_D8_period",
            supporting_proposition_ids=["prop_int_D8_period"], status="established",
            source_ref="DKLLW24, Proposition 4.1 (local PDF p. 25; journal p. 19) and section 6.1.2 (local PDF p. 51; journal p. 40)",
        ),
        PeriodFamily(
            id="period_integer_g", name="g=kD^3 (20,4)-period", workspace_id=integer.id, rank=1,
            generators=[PeriodGenerator(Grade(stem=20, filtration=4), "g=kD^3")],
            valid_from_page=2, valid_to_page="infinity", status="established",
            source_ref="DKLLW24, Table 7 and \u00a76.1.2 (PDF pp. 18, 40); excludes low-filtration v1-local classes",
        ),
    ]
    for family in project.period_families:
        if family.id == "period_integer_g":
            family.source_ref = "DKLLW24, Table 7 and §6.1.2 (PDF p. 40); excludes low-filtration v1-local classes"
    project.period_families.extend([
        PeriodFamily("period_sigma_D_E2", "(*-sigma_i) E2 D-period", sigma.id, 1, [PeriodGenerator(Grade(stem=8), "D")], 2, 2, status="established", source_ref="DKLLW24, §6.1.2 (PDF p. 40)"),
        PeriodFamily("period_sigma_D8", "(*-sigma_i) D^8 64-period", sigma.id, 1, [PeriodGenerator(Grade(stem=64), "D^8")], 2, "infinity", status="established", source_ref="DKLLW24, §6.1.2 (PDF p. 40)"),
        PeriodFamily("period_sigma_g", "(*-sigma_i) g=kD^3 (20,4)-period", sigma.id, 1, [PeriodGenerator(Grade(stem=20, filtration=4), "g=kD^3")], 2, "infinity", status="established", source_ref="DKLLW24, §6.1.2 (PDF p. 40); excludes low-filtration v1-local classes"),
    ])
    # The shipped research workspace deliberately includes the small,
    # D-localized, source-backed E2 catalogue.  Arbitrary persisted projects
    # are never changed merely by loading a migration.
    materialize_verified_e2_records_for_project(project, "integer")
    materialize_verified_e2_records_for_project(project, "sigma_i")
    return project


# Kept as the public factory name used by the Flask app.
def demo_project() -> Project:
    return research_project()
