"""Source-review slices of the height-two C4 HFPSS from BBHS20.

This is deliberately not fed into the Q8 page-quotient engine.  It contains the
full E2 module motif in a finite window, together with the published generating
differential equations.  A later-page display is a source snapshot, not a claim
to have computed its kernel/image quotient.  HHR's K_[2] slice sequence and the
height-four HSWX computation are not substituted for this HFPSS.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import ClassNode, Differential, Grade, Proposition, Workspace


BBHS = "[BBHS20f] Invertible K(2)-local E-modules in C_4-spectra.pdf"
HHR = "[HHR17f] HHR on C_4 analog publish .pdf"
HSWX = "[HSWX]THE SLICE SPECTRAL SEQUENCE OF A C4-EQUIVARIANT_1811.07960v3.pdf"
CONVENTION = "c4-bbhs-stem-filtration-v1"
CONTEXT = "c4-bbhs-witt-k"
INTEGER_ID = "ws_c4_bbhs_integer"
SHIFTED_ID = "ws_c4_bbhs_1_minus_sigma"

RING_RELATIONS = [
    r"2\eta=2\nu=2\varsigma=4\varpi=0",
    r"T_2^2=\Delta_1\{(\mu-2)^2+4\}",
    r"\Delta_1\eta^2=T_2\varpi=\varsigma^2",
    r"T_2\varsigma=\mu\Delta_1\eta",
    r"T_2\eta=\mu\varsigma",
    r"\varsigma\eta=\mu\varpi",
    r"\nu^2=2\varpi",
    r"\mu\nu=\eta\nu=T_2\nu=\varsigma\nu=0",
]


@dataclass(frozen=True)
class Monomial:
    """A literal published monomial; no unproved simplification is performed."""

    eta: int = 0
    nu: int = 0
    varsigma: int = 0
    varpi: int = 0
    t2: int = 0
    delta: int = 0
    p: int = 0
    coefficient: int = 1
    mu: int = 0

    @property
    def filtration(self) -> int:
        return self.eta + self.nu + self.varsigma + 2 * self.varpi

    @property
    def integer_stem(self) -> int:
        # p has actual RO degree -3-sigma.  In the 1-sigma slice its
        # integer coordinate is -4; this is not the dimension grading.
        return (self.eta + 3 * self.nu + 5 * self.varsigma + 6 * self.varpi
                + 4 * self.t2 + 8 * self.delta - 4 * self.p)

    def grade(self) -> Grade:
        representation = {"1": self.p, "sigma": -self.p} if self.p else {}
        return Grade(self.integer_stem, self.filtration, representation)

    def tex(self) -> str:
        pieces = [str(self.coefficient)] if self.coefficient != 1 else []
        for symbol, exponent in (
            (r"\mu", self.mu), (r"T_2", self.t2), (r"\eta", self.eta),
            (r"\nu", self.nu), (r"\varsigma", self.varsigma),
            (r"\varpi", self.varpi), (r"\Delta_1", self.delta), (r"\mathfrak p", self.p),
        ):
            if exponent:
                pieces.append(symbol if exponent == 1 else f"{symbol}^{{{exponent}}}")
        return " ".join(pieces) or "1"


@dataclass(frozen=True)
class DifferentialSeed:
    key: str
    page: int
    source: Monomial
    target: Monomial
    citation: str
    proof: str
    delta_period: int
    linear_over: tuple[str, ...]


def c4_differential_seeds(shifted: bool = False) -> tuple[DifferentialSeed, ...]:
    """Exactly the nonzero C4/C4 generators of BBHS20 Props. 5.21--5.28."""
    m = Monomial
    d3 = (r"\mu", r"\eta", r"\nu", r"\Delta_1^{\pm1}", r"\varpi^2")
    d5 = (r"\mu", r"\eta", r"\nu", r"\bar\kappa", r"\Delta_1^{\pm2}")
    late = (r"\mu", r"\eta", r"\nu", r"\bar\kappa", r"\epsilon", r"\Delta_1^{\pm4}")
    refs = {
        3: f"{BBHS}, Proposition 5.21, pp. 3456-3457 (arXiv v2 pp. 27-28)",
        5: f"{BBHS}, Proposition 5.24, p. 3464 (arXiv v2 p. 32)",
        7: f"{BBHS}, Proposition 5.27, pp. 3465-3466 (arXiv v2 pp. 35-36)",
        11: f"{BBHS}, Proposition 5.28, pp. 3466-3467 (arXiv v2 p. 36)",
        13: f"{BBHS}, Proposition 5.28, pp. 3466-3467 (arXiv v2 p. 36)",
    }
    proofs = {
        3: "Naturality from HHR17 Table 3: d3(u_lambda)=eta*a_lambda; BBHS Remark 5.12 dictionary.",
        5: "HHR17 Table 3, BBHS Remark 5.12, and the gold relation nu^2=2*varpi.",
        7: "HHR17 Theorem 14.3; in the shifted slice also BBHS Corollary 5.26.",
        11: "HHR17 Theorem 14.2(iv); shifted formula by the permanent class varpi*Delta_1^2*p.",
        13: "HHR17 Theorem 14.4; shifted formulas by BBHS Corollary 5.26.",
    }
    if shifted:
        rows = [
            ("d3-delta-p", 3, m(delta=1, p=1), m(eta=1, varpi=1, p=1)),
            ("d3-varpi-varsigma-p", 3, m(varpi=1, varsigma=1, p=1), m(eta=1, varsigma=1, varpi=2, delta=-1, p=1)),
            ("d5-delta-nu-p", 5, m(delta=1, nu=1, p=1), m(coefficient=2, delta=-1, varpi=3, p=1)),
            ("d5-delta-varpi-p", 5, m(delta=1, varpi=1, p=1), m(nu=1, delta=-1, varpi=3, p=1)),
            ("d7-two-delta3-varpi-p", 7, m(coefficient=2, delta=3, varpi=1, p=1), m(varsigma=1, varpi=4, p=1)),
            ("d7-varpi-p", 7, m(varpi=1, p=1), m(varsigma=1, varpi=4, delta=-3, p=1)),
            ("d11-varsigma-varpi2-delta2-p", 11, m(varsigma=1, varpi=2, delta=2, p=1), m(nu=2, varpi=7, delta=-2, p=1)),
            ("d13-delta3-nu-varpi2-p", 13, m(delta=3, nu=1, varpi=2, p=1), m(delta=-2, varpi=9, p=1)),
            ("d13-delta5-nu2-varpi-p", 13, m(delta=5, nu=2, varpi=1, p=1), m(nu=1, varpi=8, p=1)),
        ]
    else:
        rows = [
            ("d3-t2", 3, m(t2=1), m(eta=3)),
            ("d3-varpi", 3, m(varpi=1), m(eta=1, varpi=2, delta=-1)),
            ("d3-varsigma", 3, m(varsigma=1), m(eta=1, varsigma=1, varpi=1, delta=-1)),
            ("d5-delta", 5, m(delta=1), m(nu=1, delta=-1, varpi=2)),
            ("d5-nu-varpi", 5, m(nu=1, varpi=1), m(coefficient=2, delta=-2, varpi=4)),
            ("d7-two-delta", 7, m(coefficient=2, delta=1), m(varsigma=1, varpi=3, delta=-2)),
            ("d7-delta2", 7, m(delta=2), m(varsigma=1, varpi=3, delta=-1)),
            ("d11-varsigma-varpi", 11, m(varsigma=1, varpi=1), m(coefficient=2, delta=-4, varpi=7)),
            ("d13-delta-nu-varpi", 13, m(delta=1, nu=1, varpi=1), m(delta=-4, varpi=8)),
            ("d13-delta3-nu2", 13, m(delta=3, nu=2), m(delta=-2, nu=1, varpi=7)),
        ]
    return tuple(DifferentialSeed(key, page, source, target, refs[page], proofs[page],
                                 1 if page == 3 else 2 if page == 5 else 4,
                                 d3 if page == 3 else d5 if page == 5 else late)
                 for key, page, source, target in rows)


def _e2_motif(stem_min: int, stem_max: int, filtration_max: int, shifted: bool):
    """Module generators, not one point per coefficient of a power series."""
    p = int(shifted)
    for filtration in range(filtration_max + 1):
        if filtration == 0:
            families = [(dict(), "W(k)[[mu]]", "square"), (dict(t2=1), "W(k)[[mu]]", "square")]
        elif filtration % 2:
            q = (filtration - 1) // 2
            families = [
                (dict(eta=1, varpi=q), "k[[mu]]", "dot"),
                (dict(nu=1, varpi=q), "k; mu=0", "dot"),
                (dict(varsigma=1, varpi=q), "k[[mu]]", "dot"),
            ]
        else:
            q = filtration // 2
            families = [
                (dict(varpi=q), "W(k)[[mu]]/(4,2*mu)", "circle"),
                (dict(eta=2, varpi=q-1), "k[[mu]]", "dot"),
            ]
        for factors, module, glyph in families:
            zero = Monomial(**factors, p=p)
            first = (stem_min - zero.integer_stem + 7) // 8
            last = (stem_max - zero.integer_stem) // 8
            for delta in range(first, last + 1):
                yield Monomial(**factors, delta=delta, p=p), module, glyph


def _metadata(shifted: bool, stem_min: int, stem_max: int, filtration_max: int) -> dict:
    return {
        "source_reference": True,
        "page_min": 2, "page_max": 14, "page_limit": 14,
        "grid": {"stem_min": -8, "stem_max": 40, "filtration_min": 0, "filtration_max": 20},
        "rendering": {"buffer_cells": 6, "base_cell": 28, "periodicity": []},
        "reference_snapshot": "E2 modules plus literal published differential generators; not a later-page quotient",
        "reference_window": {"stem_min": stem_min, "stem_max": stem_max, "filtration_min": 0, "filtration_max": filtration_max},
        "reference_sector": {"1": 1, "sigma": -1} if shifted else {},
        "coefficient_context": {"id": CONTEXT, "coefficient_ring": "W(k)[[mu]]", "scalar_mode": "formal", "residue_field": "k"},
        "literature_review": {
            "title": "C4 Morava E2 HFPSS: " + ("1-sigma slice" if shifted else "integer slice"),
            "scope": "Height-two Lubin-Tate theory; C4/C4 level, RO(C4)=Z{1,sigma,lambda}. Coordinates are (t-s,s) relative to the displayed slice.",
            "coverage": f"Source catalog: complete finite-window E2 module motif (stems {stem_min} to {stem_max}, filtration 0 to {filtration_max}) and published generating d3,d5,d7,d11,d13 equations for this slice. This stored catalog is not a higher-page quotient. Computed E2-E14 coefficient-module views are loaded separately on demand.",
            "source_refs": [
                f"{BBHS}, Table 5.1, Props. 5.9-5.10, 5.21, 5.24, 5.27-5.28; Remarks 4.9, 5.13, 5.23",
                f"{HHR}, Table 3 (pp. 421-423), Theorems 11.13, 14.2-14.4: slice input through BBHS comparison",
                f"{HSWX}, Section 3 reviews the height-two slice input; main Theorems 1.1-1.3 concern height FOUR, not this HFPSS",
            ],
            "notation": [
                {"symbol": r"\mu", "stem": 0, "filtration": 0, "meaning": "C4-fixed deformation parameter; coefficients are completed in (2,mu), not a finite F4 vector space"},
                {"symbol": r"T_2", "stem": 4, "filtration": 0, "meaning": "r_{1,0}^2+r_{1,1}^2"},
                {"symbol": r"\Delta_1", "stem": 8, "filtration": 0, "meaning": "(r_{1,0}r_{1,1})^2; BBHS/HHR Delta_1. NOT Beaudry's degree-24 Delta"},
                {"symbol": r"\eta", "stem": 1, "filtration": 1, "meaning": "Hopf eta, the h_1 notation counterpart; exact restriction/normalization must be checked separately"},
                {"symbol": r"\nu", "stem": 3, "filtration": 1, "meaning": "Hopf nu, the h_2 notation counterpart; 2nu=0 on E2, nu^2=2varpi"},
                {"symbol": r"\varsigma", "stem": 5, "filtration": 1, "meaning": "BBHS varsigma; not the F4 third root of unity zeta"},
                {"symbol": r"\varpi", "stem": 6, "filtration": 2, "meaning": "4-torsion group-cohomology generator, with 2mu*varpi=0"},
                {"symbol": r"\mathfrak p", "stem": -4, "filtration": 0, "meaning": "(dbar_1*u_lambda)^(-1), actual RO degree -3-sigma; coordinate -4 in the 1-sigma slice. An E2 unit, NOT a permanent cycle"},
            ],
            "relations": list(RING_RELATIONS),
            "periods": [
                r"$E_2$: $\Delta_1^{\pm1}$ gives $(8,0)$; positive-filtration $\varpi$ multiplication gives $(6,2)$ for $s\geq1$ (BBHS Remark 5.13).",
                r"$d_3$ is $\Delta_1$-linear; $d_5$ is $\Delta_1^2$-linear; $d_7,d_{11},d_{13}$ are $\Delta_1^4$-linear. These ranges must not be merged.",
                r"$\Delta_1^4$ is a permanent unit and gives integer period 32 (BBHS Remark 5.2).",
                r"RO periods: $1+\sigma+\lambda$; $16-8\lambda$; $4-4\sigma$; $10-2\sigma-4\lambda$ (BBHS Props. 4.4-4.7, 5.25).",
                r"RO quotient is $\mathbf Z/32\{1\}\oplus\mathbf Z/2\{7+\sigma\}$; every slice reduces to the integer or $1-\sigma$ slice, with a stem shift (BBHS Remark 4.9).",
                r"$\bar\kappa=\varpi^2\Delta_1$, $\epsilon=\varpi^4\Delta_1^{-2}$, $\kappa=2\varpi\Delta_1$ are permanent cycles, not invertible periods (BBHS Remark 5.22).",
            ],
            "warnings": [
                "This is not the Q8 spectral sequence and does not use its E2 pattern, coefficient quotient, vanishing line, or differential list.",
                "The finite drawing represents completed coefficient MODULES; a dot labelled k[[mu]] is not a single residue-field vector. Repeated seed aliases are not independent basis elements.",
                "The stored catalog contains generating equations only. Use the computed window for module translates and higher-page quotients; a missing catalog arrow is not a zero-differential assertion.",
                "HHR's slice d5(u_{2sigma}) has zero target in this HFPSS; d5(u_{2sigma})=0 and u_{2sigma} instead supports d7 (BBHS Remark 5.23).",
                "HSWX's main spectral sequence has height 4 and period 384; neither its late differentials nor that period belongs to the height-2 C4 workspace.",
                "No equality between C4 Delta_1 (8,0), Q8 D (8,0), and C3-invariant Delta (24,0) is inferred from notation or degree alone.",
            ],
        },
    }


def _workspace(shifted: bool, stem_min: int, stem_max: int, filtration_max: int) -> Workspace:
    ident = SHIFTED_ID if shifted else INTEGER_ID
    ws = Workspace(
        id=ident, name="C4 Morava E2 HFPSS · " + ("*+1−σ" if shifted else "*"),
        group="C4", theory="E_2", grading_label="1-sigma" if shifted else "integer",
        representation_basis=["1", "sigma", "lambda"],
        summary="BBHS20 source-review workspace: completed coefficient modules and published differential equations, with computed E2-E14 views loaded on demand.",
        settings=_metadata(shifted, stem_min, stem_max, filtration_max),
    )
    by_monomial: dict[Monomial, ClassNode] = {}
    source = f"{BBHS}, Proposition 5.10 and Remark 5.13 (arXiv v2 pp. 20-21)"

    def add(monomial: Monomial, module: str = "literal equation endpoint", glyph: str = "dot", *, page: int | None = None) -> ClassNode:
        if monomial in by_monomial:
            node = by_monomial[monomial]
            if page is not None:
                node.style.setdefault("reference_equation_pages", []).append(page)
            return node
        node = ClassNode(
            id=f"{ident}_class_{len(ws.classes):04d}", label=monomial.tex(), expression=monomial.tex(),
            grade=monomial.grade(), page=2, coefficient_context_id=CONTEXT, convention_id=CONVENTION,
            notes=f"{module}. {source}. A source E2 module / equation representative, not a computed later-page quotient.",
            style={"glyph": glyph, "source_ref": source, "reference_coefficient_module": module,
                   "reference_role": "e2_module" if page is None else "differential_seed_alias",
                   "reference_equation_pages": [] if page is None else [page],
                   "reference_monomial": dict(monomial.__dict__)},
        )
        ws.classes.append(node)
        by_monomial[monomial] = node
        return node

    for monomial, module, glyph in _e2_motif(stem_min, stem_max, filtration_max, shifted):
        add(monomial, module, glyph)

    for seed in c4_differential_seeds(shifted):
        source_node = add(seed.source, page=seed.page)
        target_node = add(seed.target, page=seed.page)
        prop_id = f"{ident}_{seed.key}_source"
        statement = rf"d_{{{seed.page}}}({seed.source.tex()})={seed.target.tex()}"
        ws.propositions.append(Proposition(
            id=prop_id, kind="differential", status="source-verified", statement=statement,
            rule="published-equation", source_ref=seed.citation, source_refs=[seed.citation],
            convention_id=CONVENTION, notes=seed.proof,
            conclusion={"source_id": source_node.id, "target_id": target_node.id, "page": seed.page,
                        "reference_only": True, "equation_tex": statement,
                        "linear_over": list(seed.linear_over), "delta_period_power": seed.delta_period,
                        "module_closure_materialized": False, "proof_category": seed.proof},
            verification_checks=["Literal source formula visually checked", "stem decreases by 1", "filtration increases by r", "RO sector unchanged"],
        ))
        ws.differentials.append(Differential(
            id=f"{ident}_{seed.key}", source_id=source_node.id, target_id=target_node.id,
            page=seed.page, status="source-verified", label=rf"d_{{{seed.page}}}", proposition_id=prop_id,
            unperiodic_reason="source-review seeds only; full module closure is not materialized",
            period_notes=rf"Published family is \Delta_1^{{{seed.delta_period}}}-linear; formal module multipliers in proposition metadata. Do not infer a universal period.",
        ))

    for index, relation in enumerate(RING_RELATIONS):
        ws.propositions.append(Proposition(
            id=f"{ident}_ring_{index}", kind="relation", statement=relation, status="source-verified",
            rule="published-E2-ring", source_ref=source, source_refs=[source], convention_id=CONVENTION,
            conclusion={"reference_only": True, "equation_tex": relation, "valid_page": 2},
        ))
    # Record known zero statements independently; a missing arrow is not used as evidence.
    zero = Monomial(mu=1, varpi=1, delta=3, p=1) if shifted else Monomial(mu=1, delta=1)
    ws.propositions.append(Proposition(
        id=f"{ident}_d7_zero", kind="zero_differential", statement=rf"d_7({zero.tex()})=0",
        status="source-verified", rule="published-equation", source_ref=f"{BBHS}, Proposition 5.27",
        convention_id=CONVENTION,
        conclusion={"reference_only": True, "page": 7, "equation_tex": rf"d_7({zero.tex()})=0"},
        notes="Explicit zero in Proposition 5.27; not inferred from absence of a chart edge.",
    ))
    return ws


def create_c4_reference_workspaces(*, stem_min: int = -32, stem_max: int = 64,
                                   filtration_max: int = 20) -> list[Workspace]:
    """Build fresh C4 review slices without modifying the historical ws_c4_j."""
    if any(isinstance(value, bool) or not isinstance(value, int)
           for value in (stem_min, stem_max, filtration_max)):
        raise ValueError("Reference chart bounds must be integers")
    if stem_min > stem_max or filtration_max < 0:
        raise ValueError("Reference chart requires ordered stems and nonnegative filtration")
    return [_workspace(False, stem_min, stem_max, filtration_max),
            _workspace(True, stem_min, stem_max, filtration_max)]
