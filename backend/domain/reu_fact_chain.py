"""Audited dependencies from the current REU/Overleaf research notes."""

from __future__ import annotations

from .models import Project, Proposition


REVIEWED_AT = "2026-08-11"
COEFFICIENTS = ["coefficient-context:q8-witt-f4"]


def ensure_reu_fact_chain(project: Project) -> Project:
    """Add corrected REU facts without admitting unresolved units or aliases."""
    if project.id != "hfpss_studio":
        return project
    workspaces = {item.id: item for item in project.workspaces}
    required = {"ws_integer", "ws_2sigma_i", "ws_sigma_i_2sigma_j"}
    if not required.issubset(workspaces):
        return project
    known = {
        proposition.id
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
        if ident in known:
            return
        source_ref = source_refs[0] if source_refs else ""
        workspaces[workspace_id].propositions.append(Proposition(
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
            reviewed_at=REVIEWED_AT,
        ))
        known.add(ident)

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
        "normalization-obligation",
        r"The selected Thom generator satisfies psi(u_{2sigma_i})=u_{2sigma_i} exactly.",
        {"normalization": "psi-fixed Thom generator", "precision": "exact"},
        ["prop_reu_psi_representations"],
        "ChooseAndVerifyThomGenerator",
        ["REU coefficientpuzzle.tex lines 39-43"],
        "Fixing the representation does not automatically fix a selected generator without a unit; this remains a review obligation.",
        status="under-review",
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
        },
        [
            "prop_reu_d3_nonzero_line",
            "prop_reu_galois_generators",
            "prop_reu_thom_normalization",
        ],
        "FilteredNaturalityAndFrobeniusFixedUnit",
        ["REU Note/record/coefficientpuzzle.tex lines 15-58"],
        "The equation c=c^2 is valid, but the exact Thom normalization is not yet admitted.",
        status="under-review",
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
        r"The corrected d11 family on the (x^2+y^2)D^(2,6) anchors is 32-periodic up to the restriction unit.",
        {
            "datum_type": "differential",
            "spectral_sequence": "Q8-HFPSS",
            "page": 11,
            "scope": "*-2sigma_i",
            "period_pattern": 32,
            "precision": "up-to-W(F4)-unit",
        },
        ["prop_reu_a2sigma_pc", "prop_chain_q8_d11"],
        "CorrectedRestrictionAndPeriodSibling",
        [
            "REU formal_notes.tex lines 450-470",
            "REU Note/record/note.tex Dec. correction, lines 1248-1255",
        ],
        "Does not use the rejected restriction lemma at formal_notes.tex lines 435-446.",
        status="verified",
    )
    add(
        "prop_reu_d9_corrected_pattern",
        "differential",
        r"The corrected d9(h2 D^2 u)=h1^2 k^2 D^3 u family is 32-periodic up to a unit.",
        {
            "datum_type": "differential",
            "spectral_sequence": "Q8-HFPSS",
            "page": 9,
            "scope": "*-2sigma_i",
            "period_pattern": 32,
            "precision": "up-to-W(F4)-unit",
        },
        ["prop_reu_d11_corrected_pattern", "prop_chain_q8_d23"],
        "CorrectionVanishingAndDegree",
        [
            "REU formal_notes.tex lines 520-526",
            "REU Note/record/note.tex lines 1232-1238",
        ],
        "Supersedes the old d9 on (10,2), which the correction declares a 21-cycle.",
        status="verified",
    )
    add(
        "prop_reu_d7_corrected_pattern",
        "differential",
        r"The corrected d7(h1 D u)=2 k^2 D^2 u family and its sibling form a 16-pattern.",
        {
            "datum_type": "differential",
            "spectral_sequence": "Q8-HFPSS",
            "page": 7,
            "scope": "*-2sigma_i",
            "period_pattern": 16,
        },
        ["prop_reu_d5_a2sigma", "prop_chain_c4_hidden_2"],
        "TransferBoundAndPermanentCycleExclusion",
        [
            "REU formal_notes.tex lines 508-518",
            "REU Note/record/note.tex lines 1232-1238",
        ],
        "The dated correction explicitly retains the (9,1) d7.",
    )
    add(
        "prop_reu_mixed_sector_guard",
        "transport-guard",
        r"C3 and the registered periods do not identify sigma_i+2sigma_j with 2sigma_i+sigma_j.",
        {"unsupported_transport": "sigma_i+2sigma_j <-> 2sigma_i+sigma_j"},
        ["prop_dkllw_mixed_ro_guard"],
        "OrbitAndPeriodAudit",
        [
            "REU Note/record/note.tex lines 1081-1087 and 1344-1348",
            "REU formal_notes.tex lines 925-932",
        ],
        "Leibniz coefficients can cancel in one mixed sector and not the other.",
        workspace_id="ws_sigma_i_2sigma_j",
    )
    add(
        "prop_reu_mixed_formulas_review",
        "mixed-differential-family",
        r"The exact mixed-sector formulas in formal_notes.tex lines 811-920 are admitted.",
        {"scope": "*-sigma_i-2sigma_j", "verdict": "review-only"},
        ["prop_reu_d3_unit", "prop_reu_mixed_sector_guard"],
        "CorrectedAliasLeibniz",
        ["REU formal_notes.tex lines 811-920"],
        "Several proofs contain TBD premises, zeta-sensitive aliases, or an invalid use of D^4 as a Q8 period identity.",
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

