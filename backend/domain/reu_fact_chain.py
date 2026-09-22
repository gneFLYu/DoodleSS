"""Audited dependencies from the current REU/Overleaf research notes."""

from __future__ import annotations

from .models import Project, Proposition


REVIEWED_AT = "2026-08-11"
COEFFICIENTS = ["coefficient-context:q8-witt-f4"]
# Only these old managed conclusions were superseded by the researcher's
# explicit choice. Do not turn this into a generic overwrite of research facts.
_NORMALIZATION_REFRESH = {
    "prop_reu_thom_normalization": (
        "Fixing the representation does not automatically fix a selected generator without a unit; this remains a review obligation."
    ),
    "prop_reu_d3_unit": (
        "The equation c=c^2 is valid, but the exact Thom normalization is not yet admitted."
    ),
}
_VERIFIED_PATTERN_REFRESH = {
    "prop_reu_d11_corrected_pattern": (
        "Does not use the rejected restriction lemma at formal_notes.tex lines 435-446."
    ),
    "prop_reu_d9_corrected_pattern": (
        "Supersedes the old d9 on (10,2), which the correction declares a 21-cycle."
    ),
    "prop_reu_d7_corrected_pattern": (
        "The dated correction explicitly retains the (9,1) d7."
    ),
}
_MANAGED_REFRESH_NOTES = {**_NORMALIZATION_REFRESH, **_VERIFIED_PATTERN_REFRESH}
_MIXED_SUMMARY_REFRESH = {
    "prop_reu_mixed_sector_guard": {
        "statement": "C3 and the registered periods do not identify sigma_i+2sigma_j with 2sigma_i+sigma_j.",
        "notes": "Leibniz coefficients can cancel in one mixed sector and not the other.",
    },
    "prop_reu_mixed_formulas_review": {
        "statement": "The exact mixed-sector formulas in formal_notes.tex lines 811-920 are admitted.",
        "notes": "Several proofs contain TBD premises, zeta-sensitive aliases, or an invalid use of D^4 as a Q8 period identity.",
    },
}
_SUPERSEDED_PATTERN_PREMISES = {
    "prop_reu_d11_corrected_pattern": {"prop_reu_a2sigma_pc", "prop_chain_q8_d11"},
    "prop_reu_d9_corrected_pattern": {"prop_reu_d11_corrected_pattern", "prop_chain_q8_d23"},
    "prop_reu_d7_corrected_pattern": {"prop_reu_d5_a2sigma", "prop_chain_c4_hidden_2"},
}
_EXACT_PURE_NORMALIZATION = {
    "id": "pure-sigma-i-galois-fixed", "value": 1, "field": "F4",
    "preserves_witt_layers": True,
    "derivation": "The chosen psi-fixed source and target give c=c^2, hence nonzero c=1.",
}


def ensure_reu_fact_chain(project: Project) -> Project:
    """Add corrected REU facts without admitting unresolved units or aliases."""
    if project.id != "hfpss_studio":
        return project
    workspaces = {item.id: item for item in project.workspaces}
    required = {"ws_integer", "ws_2sigma_i", "ws_sigma_i_2sigma_j"}
    if not required.issubset(workspaces):
        return project
    known = {
        proposition.id: proposition
        for workspace in project.workspaces
        for proposition in workspace.propositions
    }

    def add(
        ident: str,
        kind: str,
        statement: str,
        conclusion: dict,
        premises: list[str],
        rule: str,
        source_refs: list[str],
        notes: str,
        *,
        workspace_id: str = "ws_2sigma_i",
        status: str = "established",
        hypotheses: list[str] | None = None,
    ) -> None:
        existing = known.get(ident)
        mixed_refresh = _MIXED_SUMMARY_REFRESH.get(ident)
        refresh_legacy_mixed = bool(existing is not None and mixed_refresh
                                    and existing.statement == mixed_refresh["statement"])
        if existing is not None and ident not in _MANAGED_REFRESH_NOTES and not refresh_legacy_mixed:
            return
        source_ref = source_refs[0] if source_refs else ""
        proposition = Proposition(
            id=ident,
            kind=kind,
            statement=statement,
            status=status,
            conclusion=conclusion,
            premise_ids=premises,
            rule=rule,
            notes=notes,
            source_ref=source_ref,
            source_refs=source_refs,
            hypotheses=COEFFICIENTS if hypotheses is None else hypotheses,
            verification_checks=[
                "Check every cited source locator and correction override.",
                "Do not promote an up-to-unit pattern to an exact normalized formula.",
                "Keep D^8 as the Q8-HFPSS period identity; repeated D^4 siblings are distinct anchors.",
            ],
            reviewer="Codex REU source-chain audit",
            reviewed_at="2026-09-21" if ident in _MANAGED_REFRESH_NOTES or mixed_refresh else REVIEWED_AT,
        )
        if existing is None:
            workspaces[workspace_id].propositions.append(proposition)
            known[ident] = proposition
            return
        # Refresh saved projects as well as fresh seeds. Preserve additional
        # research fields, premises and references; remove only exact obsolete
        # managed premises/boilerplate superseded by independent certificates.
        for field in ("kind", "statement", "status", "rule", "reviewer", "reviewed_at"):
            setattr(existing, field, getattr(proposition, field))
        existing.conclusion.update(proposition.conclusion)
        if refresh_legacy_mixed and ident == "prop_reu_mixed_sector_guard":
            old_guard = existing.conclusion.get("unsupported_transport")
            if old_guard == "sigma_i+2sigma_j <-> 2sigma_i+sigma_j":
                existing.conclusion["historical_c3_only_guard"] = existing.conclusion.pop("unsupported_transport")
        for field in ("premise_ids", "hypotheses", "verification_checks"):
            retained = getattr(existing, field)
            if field == "premise_ids":
                obsolete = _SUPERSEDED_PATTERN_PREMISES.get(ident, set())
                retained = [value for value in retained if value not in obsolete]
            setattr(existing, field, list(dict.fromkeys(
                [*getattr(proposition, field), *retained]
            )))
        existing.source_refs = list(dict.fromkeys([
            *proposition.source_refs, *existing.source_refs,
            *([existing.source_ref] if existing.source_ref else []),
        ]))
        existing.source_ref = proposition.source_ref
        remaining_notes = existing.notes
        old_note = _MANAGED_REFRESH_NOTES.get(ident, (mixed_refresh or {}).get("notes", ""))
        for managed_note in (old_note, proposition.notes):
            remaining_notes = remaining_notes.replace(managed_note, "").strip()
        existing.notes = proposition.notes + ("\n\n" + remaining_notes if remaining_notes else "")

    add(
        "prop_reu_topological_galois",
        "topological-action",
        r"The extended stabilizer acts topologically on Morava E_2; Frobenius is semilinear, not an F_4-linear element of the small stabilizer.",
        {"scope": "extended Morava stabilizer", "scalar_action": "a -> a^2"},
        ["prop_dkllw_extended_scope"],
        "Goerss-Hopkins-Miller/extended-stabilizer action",
        ["Beaudry 2017, pp. 4, 10-12; Goerss-Hopkins-Miller realization"],
        "This supplies filtered topological naturality, but not exact mixed-RO aliases by itself.",
        workspace_id="ws_integer",
    )
    add(
        "prop_reu_psi_q8",
        "normalizer-action",
        r"For Beaudry's Q_8 embedding, Frobenius sends (i,j,k) to (-i,-k,-j).",
        {"group_action": {"i": "-i", "j": "-k", "k": "-j"}},
        ["prop_reu_topological_galois"],
        "ExplicitFrobeniusSubstitution",
        ["Beaudry 2017, explicit supersingular-curve automorphisms, pp. 10-12"],
        "The central signs are essential at group level, although they vanish on one-dimensional quotient representations.",
        workspace_id="ws_integer",
    )
    add(
        "prop_reu_psi_representations",
        "representation-transport",
        r"Frobenius fixes sigma_i and swaps sigma_j with sigma_k.",
        {"representation_action": {"sigma_i": "sigma_i", "sigma_j": "sigma_k", "sigma_k": "sigma_j"}},
        ["prop_reu_psi_q8"],
        "PassToOneDimensionalQuotients",
        ["REU coefficientpuzzle.tex lines 29-40, corrected by Beaudry's central signs"],
        "The central element acts trivially on these one-dimensional representations.",
        workspace_id="ws_integer",
    )
    add(
        "prop_reu_galois_generators",
        "coefficient-action",
        r"The named classes x and h1 are Galois invariant while F_4 scalars transform by a -> a^2.",
        {"fixed_classes": ["x", "h1"], "scalar_action": "Frobenius"},
        ["prop_reu_topological_galois", "prop_chain_q8_hurewicz_pc"],
        "SourceIdentification",
        ["Beaudry 2017, p. 61; DKLLW24 identification h1=eta"],
        "This records class invariance separately from the action on an orientation generator.",
        workspace_id="ws_integer",
    )
    add(
        "prop_reu_thom_normalization",
        "normalization-choice",
        r"The selected Thom generator satisfies psi(u_{2sigma_i})=u_{2sigma_i} exactly.",
        {"normalization": "psi-fixed Thom generator", "precision": "exact",
         "scope": "chosen pure *-n sigma_i bases", "preserves_witt_layers": True},
        ["prop_reu_psi_representations"],
        "ChooseAndVerifyThomGenerator",
        ["Researcher declaration: chosen psi-fixed pure *-n sigma_i generators and Thom classes",
         "REU coefficientpuzzle.tex lines 39-43"],
        "The researcher has fixed this normalization. It is a choice of psi-fixed pure-sector generators, not an inference from representation invariance alone. Witt factors 2 and 4 and mixed-sector coefficients are not normalized away.",
        status="verified",
    )
    add(
        "prop_reu_a2sigma_pc",
        "permanent-cycle",
        r"(x^2+y^2)u_{2sigma_i}=a_{sigma_i}^2 is the surviving permanent-cycle alias.",
        {"datum_type": "permanent-cycle", "spectral_sequence": "Q8-HFPSS", "cycle": "(x^2+y^2)u_{2sigma_i}"},
        ["prop_chain_q8_usigma_pc"],
        "MultiplicativityAndCorrection",
        [
            "REU formal_notes.tex lines 280, 299-304",
            "REU Note/record/note.tex Dec. 30 correction, lines 1262-1268",
        ],
        "Supersedes the stale x^2u_{2sigma_i} alias.",
    )
    add(
        "prop_reu_d3_nonzero_line",
        "differential",
        r"d3(u_{2sigma_i})=c x^2 h1 u_{2sigma_i} for a nonzero c in F_4.",
        {
            "datum_type": "differential",
            "spectral_sequence": "Q8-HFPSS",
            "page": 3,
            "scope": "*-2sigma_i",
            "formula": "d3(u_{2sigma_i})=c x^2 h1 u_{2sigma_i}",
            "precision": "nonzero-F4-unit",
        },
        ["prop_reu_a2sigma_pc", "prop_chain_c4_d3"],
        "RestrictionDegreeAndPermanentCycleExclusion",
        [
            "REU formal_notes.tex lines 283-305",
            "REU Drawing/2Sigma_E3.tex lines 340-357 (coordinate corroboration only)",
        ],
        "The differential line is verified; its exact F4 unit is not fixed by this proposition.",
        status="verified",
    )
    add(
        "prop_reu_d3_unit",
        "differential",
        r"d3(u_{2sigma_i})=x^2 h1 u_{2sigma_i} with exact coefficient one.",
        {
            "datum_type": "differential",
            "spectral_sequence": "Q8-HFPSS",
            "page": 3,
            "scope": "*-2sigma_i",
            "formula": "d3(u_{2sigma_i})=x^2 h1 u_{2sigma_i}",
            "precision": "exact-after-normalization",
            "coefficient_normalization": {
                "id": "pure-sigma-i-galois-fixed", "value": 1, "field": "F4",
                "derivation": "psi-fixed source and nonzero target imply c=c^2; c in F4* implies c=1",
                "preserves_witt_layers": True,
            },
        },
        [
            "prop_reu_d3_nonzero_line",
            "prop_reu_galois_generators",
            "prop_reu_thom_normalization",
        ],
        "FilteredNaturalityAndFrobeniusFixedUnit",
        ["REU Note/record/coefficientpuzzle.tex lines 15-58"],
        "Naturality and the chosen psi-fixed source and target give c=c^2, hence the nonzero F4 scalar is 1. This does not set a Witt coefficient or a power series equal to 1, and does not fix a coefficient in a mixed sector moved by psi.",
        status="verified",
    )
    add(
        "prop_reu_d5_a2sigma",
        "differential",
        r"The corrected (x^2+y^2)D and (x^2+y^2)D^2 d5 families follow by Leibniz.",
        {
            "datum_type": "differential",
            "spectral_sequence": "Q8-HFPSS",
            "page": 5,
            "scope": "*-2sigma_i",
            "period_pattern": 16,
        },
        ["prop_reu_a2sigma_pc", "prop_chain_q8_d5_D"],
        "Leibniz",
        ["REU formal_notes.tex lines 334-353"],
        "This is a repeated differential pattern, not an HFPSS same-object declaration.",
    )
    add(
        "prop_reu_d11_corrected_pattern",
        "differential",
        r"The verified d11 family on (x^2+y^2)D^(2,6)u has exact nonzero F_4 coefficient 1 in the chosen psi-fixed basis.",
        {
            "datum_type": "differential",
            "spectral_sequence": "Q8-HFPSS",
            "page": 11,
            "scope": "*-2sigma_i",
            "period_pattern": 32,
            "precision": "exact-after-normalization",
            "coefficient_normalization": dict(_EXACT_PURE_NORMALIZATION),
            "period_kind": "repeated-differential-pattern",
            "period_is_invertible": False,
        },
        ["formal_prop_fn-2i-009_1"],
        "VerifiedRestrictionCertificateAndGaloisNormalization",
        [
            "REU formal_notes.tex lines 450-470",
            "REU Note/record/note.tex Dec. correction, lines 1248-1255",
        ],
        "The canonical FN009 certificate proves the two D2/D6 blocks separately by C4 restriction and earlier-target exclusion. Their common 32-stem pattern is not permanence of Q8 D4; use D8 for invertible repetition. The rejected restriction lemma is not a premise.",
        status="verified",
    )
    add(
        "prop_reu_d9_corrected_pattern",
        "differential",
        r"The verified d9(h2 D^(2,6)u)=h1^2 k^2 D^(3,7)u has exact F_4 coefficient 1; the source's two-multiple survives.",
        {
            "datum_type": "differential",
            "spectral_sequence": "Q8-HFPSS",
            "page": 9,
            "scope": "*-2sigma_i",
            "period_pattern": 32,
            "precision": "exact-after-normalization",
            "coefficient_normalization": dict(_EXACT_PURE_NORMALIZATION),
            "period_kind": "repeated-differential-pattern",
            "period_is_invertible": False,
        },
        ["formal_prop_fn-2i-016_1"],
        "VerifiedD11ProductBoundaryAndEarlierSourceExclusion",
        [
            "REU formal_notes.tex lines 520-526",
            "REU Note/record/note.tex lines 1232-1238",
        ],
        "The canonical FN016 certificate forces the target to be zero already on E11 using D^-1h1 multiplication of FN009. Earlier incoming-source exclusion forces d9, without a d23 or vanishing-line premise. At low filtration the W/4 source retains its two-layer; the nonzero F4 scalar is 1.",
        status="verified",
    )
    add(
        "prop_reu_d7_corrected_pattern",
        "differential",
        r"The verified d7(h1 D^(1,3)u)=2 k^2 D^(2,4)u branches form a common 16-stem pattern with exact F_4 unit 1.",
        {
            "datum_type": "differential",
            "spectral_sequence": "Q8-HFPSS",
            "page": 7,
            "scope": "*-2sigma_i",
            "period_pattern": 16,
            "precision": "exact-after-normalization",
            "coefficient_normalization": dict(_EXACT_PURE_NORMALIZATION),
            "period_kind": "repeated-differential-pattern",
            "period_is_invertible": False,
        },
        ["formal_prop_fn-2i-014_1", "formal_prop_fn-2i-012_1"],
        "VerifiedTransferAndD9ProductCertificates",
        [
            "REU formal_notes.tex lines 496-499,508-518",
            "REU Note/record/note.tex lines 1232-1238",
        ],
        "FN014 and FN012 independently certify the H1/H5 and H3/H7 blocks and the exact two-layer E7 targets. Combining these branches gives a repeated 16-stem pattern, not an invertible D2. Retain the positive-j source ideals; the Witt factor 2 is not normalized away.",
        status="verified",
    )
    add(
        "prop_reu_mixed_sector_guard",
        "transport-guard",
        r"C3 alone does not interchange the two mixed sectors; omega psi gives a semilinear isomorphism from sigma_i+2sigma_j to 2sigma_i+sigma_j.",
        {"c3_only_transport": False, "scope": "extended-stabilizer filtered towers",
         "semilinear_transport": {
             "source": "sigma_i+2sigma_j", "target": "2sigma_i+sigma_j",
             "action": "omega psi", "omega_power": 1, "reflected": True, "stem_shift": 0,
             "scalar_action": "a -> a^2", "basis_convention": "transported source coordinates",
             "display_conversion": "Expand endpoint eigenunits separately; the arrow coefficient uses the target/source unit ratio.",
         }},
        ["prop_reu_topological_galois", "prop_reu_psi_representations", "prop_reu_galois_generators"],
        "SemilinearNormalizerTransport",
        [
            "REU Note/record/note.tex lines 1081-1087 and 1344-1348",
            "REU formal_notes.tex lines 997-1003 (historical C3-only warning)",
            "Researcher-specified extended Galois action; backend/domain/actions.py and atlas_transport.py",
        ],
        "Apply psi first, fixing sigma_i and interchanging sigma_j,sigma_k, then omega. Frobenius preserves zero sums: a genuine transported differential cannot vanish in only one of the two sectors. Copying untransformed basis coefficients is not this semilinear map. This does not determine the unresolved source parameters c or b.",
        workspace_id="ws_sigma_i_2sigma_j",
    )
    add(
        "prop_reu_mixed_formulas_review",
        "mixed-differential-family",
        r"Mixed-sector formulas are reviewed individually: the verified d3, P d5, Q zero-d5 and d11 coexist with unresolved relative d5 coefficients and late claims.",
        {"scope": "*-sigma_i-2sigma_j", "verdict": "review-only",
         "independent_facts": ["FN-MIX-001", "FN-MIX-004", "FN-MIX-005-Q-zero", "FN-MIX-006"],
         "unresolved_parameters": ["mixed_d5_A", "mixed_d5_B"],
         "no_blanket_admission": True},
        ["prop_reu_d3_unit", "prop_reu_mixed_sector_guard"],
        "CorrectedAliasLeibniz",
        ["REU formal_notes.tex lines 881-991", "Canonical independent certificates in backend/domain/formal_notes_chart.py"],
        "Use each canonical claim's certificate and current admission status. The nonzero-b repair does not assign b; the corrected d11 coefficient is zeta^2. A printed D4 repeat does not identify pages by a permanent D4 unit, and no late historical row is admitted by this summary.",
        workspace_id="ws_sigma_i_2sigma_j",
        status="under-review",
    )
    add(
        "prop_reu_rejected_high_filtration_branch",
        "rejected-claim",
        r"The commented high-filtration perfect-matching branch may support admitted descendants.",
        {"verdict": "rejected", "blocked_source_lines": "formal_notes.tex 579-673"},
        [],
        "ExplicitSourceRejection",
        ["REU formal_notes.tex lines 579-673"],
        "The source opens the comment with 'Seems to be wrong' and ends by requesting proofreading.",
        status="rejected",
    )
    add(
        "prop_reu_period_relations",
        "representation-periods",
        r"The ten norm-derived rows are the registered period relation matrix in RO(Q_8).",
        {
            "relation_matrix": [
                [1, 1, 1, 1, 1],
                [4, 4, -4, -4, 0], [4, -4, 4, -4, 0], [4, -4, -4, 4, 0],
                [10, 10, -2, -2, -4], [10, -2, 10, -2, -4], [10, -2, -2, 10, -4],
                [16, 16, 0, 0, -8], [16, 0, 16, 0, -8], [16, 0, 0, 16, -8],
            ],
            "basis": ["1", "sigma_i", "sigma_j", "sigma_k", "H"],
        },
        ["prop_chain_c4_periodic_pc"],
        "NormPeriodRelations",
        [
            "DKLLW24 main.tex lines 831-866, Corollary 2.22",
            "REU charts.tex lines 127-145",
        ],
        "The matrix, not a prose exercise, is the input to Smith normal form.",
        workspace_id="ws_integer",
    )
    add(
        "prop_reu_period_snf",
        "exact-algebra",
        r"The period relation matrix has Smith diagonal (1,2,4,4,64).",
        {"smith_diagonal": [1, 2, 4, 4, 64]},
        ["prop_reu_period_relations"],
        "SmithNormalForm",
        ["Exact integer recomputation from REU charts.tex lines 127-145, 2026-08-11"],
        "The unit diagonal contributes no quotient summand.",
        workspace_id="ws_integer",
        status="verified",
        hypotheses=[],
    )
    add(
        "prop_reu_period_quotient",
        "representation-periods",
        r"RO(Q_8)/P is Z/64 + Z/4 + Z/4 + Z/2.",
        {"quotient_invariants": [64, 4, 4, 2]},
        ["prop_reu_period_snf"],
        "ReadSmithInvariants",
        [
            "REU formal_notes.tex line 243",
            "REU charts.tex lines 127-146",
        ],
        "This is the audited finite grading quotient.",
        workspace_id="ws_integer",
        hypotheses=[],
    )
    add(
        "prop_reu_bad_period_exercise",
        "rejected-claim",
        r"The main.tex exercise quotient Z/64 + Z/8 + Z/8 + Z/4 is correct.",
        {"verdict": "rejected", "contradicted_by": "prop_reu_period_snf"},
        ["prop_reu_period_snf"],
        "ExactAlgebraContradiction",
        ["REU main.tex lines 104-110"],
        "The exact Smith diagonal is (1,2,4,4,64), not one producing 8,8,4.",
        workspace_id="ws_integer",
        status="rejected",
        hypotheses=[],
    )
    return project
