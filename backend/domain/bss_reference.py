"""Source-scoped 2-Bockstein equation catalogs, not a complete page engine.

The third grading (h0 filtration) is stored independently of group
cohomology. In the (t-s,s) projection d_r has degree (-1,1); in the
(t-s,p) projection it has degree (-1,r). Neither projection reindexes pages.
The catalog deliberately does not manufacture an HFPSS quotient or infer
permanence in the HFPSS from survival in the auxiliary Bockstein sequence.
"""
from __future__ import annotations

from copy import deepcopy

from .models import ClassNode, Differential, Grade, Proposition, Workspace


BEA_SOURCE = "Beaudry17b, Appendix A (by H.-W. Henn), Theorems A.14, A.20 and A.22; PDF pp. 57, 61-63"
BAUER_INTEGER = "Bauer08, Section 7, printed pp. 28-29 (PDF pp. 18-19); integral 2-Bockstein equations and Equation 7.13"
DKLLW_E1 = "DKLLW24, Section 3.1, Lemma 3.1 and Proposition 3.2; journal PDF pp. 18-20"
DKLLW_INTEGER = "DKLLW24, Table 1 and Theorem 3.3; journal PDF pp. 20-21"
DKLLW_SIGMA = "DKLLW24, Section 3.2, Propositions 3.6, 3.8 and Table 4; journal PDF pp. 22-23"
CONTEXT = "q8-bss-f4-h0"
CONVENTION = "q8-2bss-adams-h0-v1"

# These are DKLLW-normalized x and y, not the homonymous Appendix A classes.
E1_RELATIONS = [
    r"v_1h_2=0", r"v_1^2x=0", r"v_1y=0", r"h_1h_2=0",
    r"h_2x=v_1h_1x", r"h_1y=v_1x^2", r"xy=0", r"Dy^2=h_2^2",
    r"Dh_1^2x=h_2^3", r"Dx^3=h_2^2y", r"h_1^4=v_1^4k",
]
E1_ADDITIVE_BASIS = [
    {"labels": ["1", r"h_1", r"h_1^2", r"h_1^3"],
     "v1_exponents": "all nonnegative integers", "v1_annihilator": None},
    {"labels": ["x", r"xh_1", "x^2", r"x^2h_1"],
     "v1_exponents": [0, 1], "v1_annihilator": 2},
    {"labels": [r"h_2", "y", r"h_2^2", r"yh_2", r"h_2^3", "x^3"],
     "v1_exponents": [0], "v1_annihilator": 1},
]
NOTATION = [
    {"symbol": r"v_1", "stem": 2, "filtration": 0, "meaning": "C3-invariant; Appendix A v1"},
    {"symbol": "D", "stem": 8, "filtration": 0, "meaning": r"Q8 invariant; omega(D)=zeta^2 D; D is invertible in this auxiliary sequence"},
    {"symbol": r"\Delta", "stem": 24, "filtration": 0, "meaning": r"Delta=D^3; C3-invariant, unlike D; not the degree-eight C4 Delta1"},
    {"symbol": "j", "stem": 0, "filtration": 0, "meaning": r"Q8 completion parameter j=v1^4 D^(-1), also of Bockstein filtration 0. The Appendix A G24 parameter is j^3=v1^12 Delta^(-1), not this j."},
    {"symbol": "k", "stem": -4, "filtration": 4, "meaning": "C3-invariant cohomological period; use only nonnegative k powers in group cohomology"},
    {"symbol": r"h_1", "stem": 1, "filtration": 1, "meaning": "Appendix A eta; C3-invariant"},
    {"symbol": r"h_2", "stem": 3, "filtration": 1, "meaning": "Appendix A nu; C3-invariant"},
    {"symbol": "x", "stem": -1, "filtration": 1, "meaning": "DKLLW x=D^(-1) x_Bea; omega(x)=zeta x"},
    {"symbol": "y", "stem": -1, "filtration": 1, "meaning": "DKLLW y=D^(-2) y_Bea; omega(y)=zeta^2 y"},
    {"symbol": r"h_0", "stem": 0, "filtration": 0, "meaning": "Detects 2; independent Bockstein filtration 1, not an ordinary scalar 2 in F4"},
]


def _power_h0(level: int, expression: str) -> str:
    if not level:
        return expression
    return (r"h_0" if level == 1 else rf"h_0^{{{level}}}") + expression


def _base(sigma: bool) -> Workspace:
    scope = "(*-sigma_i)" if sigma else "integer"
    identifier = "ws_q8_bss_sigma" if sigma else "ws_q8_bss_integer"
    notation = deepcopy(NOTATION)
    if sigma:
        notation.append({"symbol": r"u_{\sigma_i}", "stem": 0, "filtration": 0,
                         "meaning": "Actual RO degree 1-sigma_i; dimension-adjusted plotted stem 0. It orients the mod-2 module only."})
    warnings = [
        "Finite equation catalog and selected associated-graded survivors, NOT a computed full E_r page. Multiplicative/h0 translates are stated but not exhaustively drawn.",
        "Every d_r raises group-cohomology filtration by 1 and Bockstein filtration by r; projected arrows have degree (-1,1).",
        "h0^n records a filtration layer detecting 2^n. It is not zero merely because the residue field has characteristic 2.",
        "E4 below displays selected 2-BSS E-infinity classes; their survival says nothing about later HFPSS differentials.",
        "Nodes depicting sums are exact vectors in E1, not extra independent basis generators; the catalog must not be used to count ranks.",
        "D periodicity here does not assert that D is a permanent cycle of the Q8 HFPSS. Hidden extensions are assertions about the abutment, not E1 identities.",
        "The E1 multiplication authority is Beaudry17b, Appendix A by H.-W. Henn. Its Theorems A.14/A.20 describe mod-2 cohomology, not the later integral Bockstein differentials or an RO-graded sigma computation.",
        "Bauer08 p. 28 prints d4(y h2^2)=8g, whereas the current h0-adic convention and DKLLW Table 1 use d3. This source-numbering discrepancy is retained explicitly; the chart has not changed its d3 or h0-filtration conventions.",
    ]
    if sigma:
        warnings.extend([
            "Table 5 prints v1^2 u_sigma_i at (0,2); its degree is (4,0) in the dimension-adjusted chart. The diagram uses (4,0).",
            "Table 6 contains the nonhomogeneous printed relation {h1+xv1}u_sigma_i h1^3-v1^2u_sigma_i. It is not installed as an algebra relation.",
            "Lemma 3.9's intermediate 2^(-1) displays contain inconsistent factors of 2. Its stated hidden-extension conclusions are recorded separately.",
            "Higher differentials on general twisted representatives require quotient-consistent module calculations; the five Table 4 rows alone are not a full page algorithm.",
            "The sigma twist and its d2 are published in DKLLW, not undetermined differentials or theorems proved in Beaudry's Appendix A. The twist's identification with {x+y} is additional RO/coefficient-module input.",
        ])
    else:
        warnings.append("Table 2's listed generators do not exhaust the filtration-zero v1-local families: v1^6 at (12,0), for example, is used explicitly in Proposition 4.8. Do not discard these classes.")
    review = {
        "title": f"Q8 {scope} 2-Bockstein source review",
        "scope": "2-BSS computing integral group cohomology, then completion gives the Q8 HFPSS E2 term",
        "coverage": "Source catalog of the printed differential-generator rows (Tables 1 or 4), with selected abutment generators. The chart computes j-completed E1-E4 modules on demand, with explicit cohomology/h0 display bounds and no finite v1 cutoff. The legacy finite-v1 window API is retained separately.",
        "source_refs": [BEA_SOURCE, BAUER_INTEGER, DKLLW_E1, DKLLW_SIGMA if sigma else DKLLW_INTEGER],
        "source_roles": [
            {"source_ref": BEA_SOURCE, "role": "primary-E1-algebra",
             "scope": "Additive basis, multiplication, Adams grading, and Galois-invariant normalization; Appendix A is by H.-W. Henn."},
            {"source_ref": BAUER_INTEGER, "role": "primary-integer-Bockstein-formulas",
             "scope": "Integer differential equations and hidden h2 extension; the printed d4 versus the chart's d3 discrepancy is recorded in warnings."},
            {"source_ref": DKLLW_E1, "role": "notation-and-Q8-comparison",
             "scope": "Restriction/eigenspace comparison and the normalized x,y notation, not the primary multiplication authority."},
            {"source_ref": DKLLW_SIGMA if sigma else DKLLW_INTEGER,
             "role": "published-twisted-Bockstein-results" if sigma else "secondary-page-convention",
             "scope": "Published sigma twist, d2 and abutment; source attribution does not claim a new proof or an independent derivation from Beaudry." if sigma
                      else "Integer row numbering and selected associated-graded descriptions, checked against the primary algebra and equations."},
        ],
        "provenance_note": "Beaudry/Henn is the authority for relations. A correct source equation or a source-based calculation is not an independent proof of every later-page or RO-graded claim.",
        "notation": notation,
        "relations": list(E1_RELATIONS),
        "periods": [
            r"$D$: degree $(8,0)$, with $D^{-1}$ allowed; $\Delta=D^3$: degree $(24,0)$ and $C_3$-invariant.",
            r"$j=v_1^4D^{-1}$: degree $(0,0,0)$, retained as $\mathbb F_4[[j]]$ coefficients, not as a geometric translation. The ideals $(j)$ and $(j^3)$ define the same completion topology.",
            r"$k$: degree $(-4,4)$, only nonnegative powers in $H^*(Q_8,-)$; invert $k$ only in the Tate comparison.",
            r"$h_0$: degree $(0,0)$ on the chart, $+1$ in the separate Bockstein filtration; an infinite tower before taking differentials.",
        ],
        "warnings": warnings,
        "e1_algebra": r"F4[v_1,D^{+/-1},k,h_1,h_2,x,y,h_0]/(E1 relations)" + (r" {u_sigma_i}" if sigma else ""),
        "e1_additive_basis": deepcopy(E1_ADDITIVE_BASIS),
        "basis_coefficient_ring": "F4[D^{+/-1}, k, h0]; k and h0 exponents nonnegative; apply the stated v1 exponent ranges",
        "completed_coefficient_ring": "F4[[j]], j=v1^4 D^(-1); keep h0, k and D gradings separately",
        "completion_provenance": {
            "source_ref": "Beaudry17b, Appendix A by H.-W. Henn, Lemma A.21 and Theorem A.22 (PDF p. 62)",
            "status": "derived-from-published-algebra",
            "scope": "The Q8 parameter and module display are a deduction, not a quotation of the G24 theorem. With Delta=D^3, the published parameter v1^12/Delta is j^3; j-adic and j^3-adic completions agree. Complete the finite module presentations and their j-linear page maps.",
            "glyph_rule": "Circle-dot means a free formal-series module on its displayed representative; a dot means a j-annihilated residue module. A differential may leave a j-divisible kernel with a different displayed representative.",
        },
        "notation_dictionary": [
            r"eta_Bea=h1, nu_Bea=h2, x_Bea=D x_DKLLW, y_Bea=D^2 y_DKLLW, Delta_Bea=D^3.",
            r"Original Bea x and y have degrees (7,1) and (15,1); normalized DKLLW x and y both have degree (-1,1).",
            r"Original G24 classes are C3-invariant. Q8 cohomology is the sum of eigenspaces with generators 1,D,D^2 and eigenvalues 1,zeta^2,zeta.",
            r"Bauer a1=v1, x_Bauer=D x, y_Bauer=D^2 y, d_Bauer=D^2 x^2, g_Bauer=kD^3; Bauer's printed final integral row is indexed d4.",
        ],
        "differential_degree": {"stem": -1, "filtration": 1, "bockstein_filtration": "r"},
        "differential_rules": [
            r"d1(v1)=h0 h1, d1(x)=h0 y^2, d1(y)=h0 x^2; d1(D)=d1(k)=d1(h1)=d1(h2)=d1(h0)=0.",
            (r"d1(a u_sigma_i)=d1(a)u_sigma_i+h0 a{x+y}u_sigma_i; d2(xh1^2u_sigma_i)=h0^2 k v1^2u_sigma_i."
             if sigma else r"On the appropriate quotient pages: d2(v1^2)=h0^2h2; d3(yh2^2)=h0^3kD. Extend using the multiplicative structure, not HFPSS page rules."),
        ],
    }
    return Workspace(
        id=identifier, name=f"Q8 2-BSS · {'*-i' if sigma else '*'}", group="Q8",
        theory="Integral group cohomology", characteristic=2, grading_label=scope,
        spectral_sequence="2-bss", page=1,
        summary="Auxiliary 2-BSS with j-completed E1-E4 module charts; h0 detects 2. This is not the homotopy fixed point spectral sequence.",
        settings={
            "source_reference": True, "page_min": 1, "page_max": 4, "page_limit": 4,
            "reference_kind": "2-bss-equation-catalog", "complete_page_model": False,
            "coefficient_context_id": CONTEXT, "convention_id": CONVENTION,
            "grid": {"stem_min": -6, "stem_max": 28, "filtration_min": 0, "filtration_max": 6},
            "rendering": {"buffer_cells": 2, "base_cell": 42, "periodicity": []},
            "literature_review": review,
        },
    )


def _node(workspace: Workspace, key: str, label: str, stem: int, filtration: int,
          *, level: int = 0, page: int = 1, last_page: int = 4, role: str,
          source: str, notes: str = "", combination: bool = False) -> ClassNode:
    node = ClassNode(
        id=f"{workspace.id}_{key}", label=label, expression=label,
        grade=Grade(stem, filtration, {"sigma_i": -1} if workspace.id.endswith("sigma") else {}),
        page=page, state="unknown", notes=notes, coefficient_context_id=CONTEXT,
        convention_id=CONVENTION,
        style={"last_page": last_page, "bockstein_filtration": level,
               "bss_catalog_role": role, "source_ref": source,
               "coefficient_order": 2, "chart_occurrence_only": True,
               "dependent_combination": combination, "source_reference": True},
    )
    workspace.classes.append(node)
    return node


def _arrow(workspace: Workspace, key: str, source_label: str, target_expression: str,
           stem: int, filtration: int, page: int, source_ref: str,
           *, family: str = "", combination: bool = False) -> None:
    source_node = _node(workspace, f"{key}_source", source_label, stem, filtration,
                        last_page=page, role="differential-source", source=source_ref)
    target_node = _node(workspace, f"{key}_target", _power_h0(page, target_expression),
                        stem-1, filtration+1, level=page, last_page=page,
                        role="differential-target", source=source_ref, combination=combination)
    proposition_id = f"{workspace.id}_{key}_claim"
    equation = rf"d_{{{page}}}({source_label})={target_node.label}"
    workspace.propositions.append(Proposition(
        id=proposition_id, kind="differential", statement=equation, status="established",
        conclusion={"datum_type": "differential", "spectral_sequence": "2-bss", "page": page,
                    "source_id": source_node.id, "target_id": target_node.id,
                    "source_bockstein_filtration": 0, "target_bockstein_filtration": page,
                    "family_formula": family or equation, "scope": "source equation, not full page rank"},
        rule="published 2-Bockstein differential", source_ref=source_ref, source_refs=[source_ref],
        convention_id=CONVENTION, notes="h0 detects 2. Bockstein filtration is independent of cohomological filtration.",
    ))
    workspace.differentials.append(Differential(
        id=f"{workspace.id}_{key}", source_id=source_node.id, target_id=target_node.id,
        page=page, status="established", proposition_id=proposition_id,
        unperiodic_reason="finite-source-equation-catalog",
        period_notes="Multiplicative families are recorded in the source claim; no unverified chart copies are inferred.",
    ))


def _survivor(workspace: Workspace, key: str, expression: str, stem: int, filtration: int,
              levels: int | None, source: str, *, from_page: int = 4) -> None:
    # Four levels of an infinite h0 tower are a declared finite display window.
    for level in range(4 if levels is None else levels):
        _node(workspace, f"survivor_{key}_h0_{level}", _power_h0(level, expression), stem, filtration,
              level=level, page=from_page, role="selected-Einfinity-layer", source=source,
              notes=("Unbounded h0 tower; only levels 0 through 3 are displayed." if levels is None
                     else f"Selected associated-graded h0 layer {level} of {levels}; this is not HFPSS permanence."),
              combination=(r"\{" in expression))
    workspace.propositions.append(Proposition(
        id=f"{workspace.id}_survivor_{key}_claim", kind="permanent-cycle",
        statement=expression + (" is torsion-free in the 2-BSS abutment." if levels is None
                                else f" has 2-primary order 2^{levels} in the 2-BSS abutment."),
        status="established", rule="published 2-BSS abutment",
        conclusion={"spectral_sequence": "2-bss", "role": "HFPSS-E2-input", "expression": expression,
                    "two_primary_exponent": levels, "not_hfpss_permanence": True},
        source_ref=source, source_refs=[source], convention_id=CONVENTION,
    ))


def _extension(workspace: Workspace, key: str, equation: str, source: str) -> None:
    workspace.propositions.append(Proposition(
        id=f"{workspace.id}_{key}", kind="extension", statement=equation, status="established",
        conclusion={"spectral_sequence": "2-bss", "scope": "abutment hidden extension", "formula": equation},
        rule="published hidden extension", source_ref=source, source_refs=[source], convention_id=CONVENTION,
    ))
    workspace.settings["literature_review"].setdefault("hidden_extensions", []).append(equation)


def create_bss_reference_workspaces() -> list[Workspace]:
    """Create fresh source catalogs; callers install them add-only by stable id."""
    integer, sigma = _base(False), _base(True)
    for args in [
        ("d1_v1", r"v_1", r"h_1", 2, 0, 1),
        ("d1_Dx", r"xD", r"h_2^2", 7, 1, 1),
        ("d1_x", "x", "y^2", -1, 1, 1),
        ("d1_y", "y", "x^2", -1, 1, 1),
        ("d2_v1_squared", r"v_1^2", r"h_2", 4, 0, 2),
        ("d3_yh2_squared", r"yh_2^2", "kD", 5, 3, 3),
    ]:
        _arrow(integer, *args, BAUER_INTEGER + "; " + DKLLW_INTEGER,
               family=(r"d_1(v_1^{2n+1})=h_0v_1^{2n}h_1, n>=0; the plotted seed is n=0."
                       if args[0] == "d1_v1" else ""))
    for key, expression, stem, filtration, levels in [
        ("k", "k", -4, 4, 3), ("x_squared", "x^2", -2, 2, 1),
        ("y_squared", "y^2", -2, 2, 1), ("xh1", r"xh_1", 0, 2, 1),
        ("h1", r"h_1", 1, 1, 1), ("h2", r"h_2", 3, 1, 2),
        ("v1_squared_h1", r"h_1v_1^2", 5, 1, 1),
        ("D", "D", 8, 0, None), ("v1_fourth", r"v_1^4", 8, 0, None),
    ]:
        _survivor(integer, key, expression, stem, filtration, levels,
                  "DKLLW24, Theorem 3.3 and Table 2; journal PDF pp. 20-21")
    _extension(integer, "hidden_h2", r"h_2\cdot x^2h_2=4kD",
               "Bauer08, Equation 7.13, printed p. 29 (PDF p. 19); normalized by x_Bauer=Dx and g_Bauer=kD^3; DKLLW24 Remark 3.5 is the secondary comparison")

    u = r"u_{\sigma_i}"
    for args in [
        ("d1_u", u, r"\{x+y\}"+u, 0, 0, 1),
        ("d1_xu", "x"+u, r"\{x^2+y^2\}"+u, -1, 1, 1),
        ("d1_v1u", r"v_1"+u, r"\{h_1+xv_1\}"+u, 2, 0, 1),
        ("d1_h2u", r"h_2"+u, r"\{x+y\}h_2"+u, 3, 1, 1),
        ("d2_xh1_squared_u", r"xh_1^2"+u, r"v_1^2k"+u, 1, 3, 2),
    ]:
        _arrow(sigma, *args, DKLLW_SIGMA, combination=(args[-1] == 1))
    for key, expression, stem, filtration, levels in [
        ("xy_squared", r"\{x^2+y^2\}"+u, -2, 2, 1),
        ("xy", r"\{x+y\}"+u, -1, 1, 1),
        ("h1_xv1", r"\{h_1+xv_1\}"+u, 1, 1, 1),
        ("v1_squared_u", r"v_1^2"+u, 4, 0, None),
        ("kv1_squared_u", r"v_1^2k"+u, 0, 4, 2),
    ]:
        _survivor(sigma, key, expression, stem, filtration, levels,
                  "DKLLW24, Proposition 3.8, Theorem 3.10 and Tables 5-6; journal PDF pp. 22-24; Table 5 degree corrected using Proposition 3.2")
    _extension(sigma, "hidden_h1", r"h_1\cdot x^2h_1k^mD^nu_{\sigma_i}=2v_1^2k^{m+1}D^nu_{\sigma_i},\quad m\geq0,\ n\in\mathbb Z",
               "DKLLW24, Lemma 3.9; journal PDF pp. 22-23")
    _extension(sigma, "hidden_h2", r"h_2\cdot x^3k^mD^nu_{\sigma_i}=2v_1^2k^{m+1}D^nu_{\sigma_i},\quad m\geq0,\ n\in\mathbb Z",
               "DKLLW24, Lemma 3.9; journal PDF pp. 22-23")
    return [integer, sigma]


# Readable compatibility alias for consumers which call these chart builders.
build_bss_reference_workspaces = create_bss_reference_workspaces
