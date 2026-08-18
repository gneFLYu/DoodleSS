"""Idempotent migrations for persisted HFPSS Studio projects."""
from __future__ import annotations

from .models import (
    CellBasisVector, CellVectorSpace, CoefficientContext, DifferentialMap, Grade,
    NamedVector, PeriodFamily, PeriodGenerator, Project, Proposition,
    SCHEMA_VERSION, SymbolDefinition,
)
from .dkllw_fact_chain import ensure_dkllw_fact_chain
from .reu_fact_chain import ensure_reu_fact_chain
from .fate import sync_project_fates
from .actions import ensure_c3_action
from .grading import ensure_q8_atlas
from .manual_periodicity import (
    format_multiplicative_latex,
    normalize_multiplicative_expression,
)
from .periods import migrate_legacy_period_families
from .periodicity import ensure_source_backed_q8_periodicity_rules


def ensure_foundations(project: Project) -> Project:
    """Install coefficient and symbol contexts without changing user claims."""
    project.schema_version = SCHEMA_VERSION

    contexts = {item.id: item for item in project.coefficient_contexts}
    contexts.setdefault(
        "q8-residue-f4",
        CoefficientContext(
            id="q8-residue-f4",
            residue_field="F4",
            coefficient_ring="F4",
            bockstein_stage="residue / 2-BSS input",
            scalar_mode="residue",
            source_ref="DKLLW24, Q8 2-Bockstein input",
        ),
    )
    contexts.setdefault(
        "q8-witt-f4",
        CoefficientContext(
            id="q8-witt-f4",
            residue_field="F4",
            coefficient_ring="W(F4)[[u_1]][u^{+-1}]",
            bockstein_stage=None,
            scalar_mode="2_adic",
            source_ref="Height-2 Morava E-theory coefficient presentation",
        ),
    )
    project.coefficient_contexts = list(contexts.values())

    symbols = {item.id: item for item in project.symbol_definitions}
    symbols.setdefault(
        "symbol-u1",
        SymbolDefinition(
            id="symbol-u1",
            symbol="u_1",
            aliases=["deformation parameter"],
            grade=Grade(),
            coefficient_context_id="q8-witt-f4",
            normalization="Formal power-series parameter in the deformation ring.",
            source_ref="DKLLW24 coefficient conventions",
        ),
    )
    symbols.setdefault(
        "symbol-v1",
        SymbolDefinition(
            id="symbol-v1",
            symbol="v_1",
            aliases=["v1"],
            grade=Grade(stem=2),
            coefficient_context_id="q8-witt-f4",
            normalization="Chart symbol; do not silently identify with u_1.",
            source_ref="Workspace chart convention",
        ),
    )
    project.symbol_definitions = list(symbols.values())

    for workspace in project.workspaces:
        searchable = f"{workspace.id} {workspace.name} {workspace.grading_label}".lower()
        if "tate" in searchable:
            workspace.spectral_sequence = "tate"
        # Migration v3 corrects the old DLS22-era default (25) to the sharp
        # Q8 result in DKLLW24.  Explicit user-selected values are preserved.
        old_source = str(workspace.settings.get("vanishing_line_source", ""))
        is_q8_hfpss = workspace.spectral_sequence == "hfpss" and "c4" not in searchable
        if is_q8_hfpss and workspace.settings.get("vanishing_line") == 25 and (
            not old_source or "DKLLW24 / DLS22" in old_source
        ):
            workspace.settings["vanishing_line"] = 23
            workspace.settings["vanishing_line_source"] = (
                "DKLLW24, Theorem 4.8 (Q8 HFPSS for E2; strong vanishing line at filtration 23)"
            )
        if not is_q8_hfpss and workspace.settings.get("vanishing_line") in {23, 25} and (
            not old_source or "DKLLW24 / DLS22" in old_source or "Theorem 4.8 (Q8 HFPSS" in old_source
        ):
            workspace.settings["vanishing_line"] = 0
            workspace.settings["vanishing_line_source"] = "No source-scoped vanishing-line certificate has been selected."
        workspace.settings.setdefault("vanishing_line", 0)
        workspace.settings.setdefault(
            "vanishing_line_source",
            "No source-scoped vanishing-line certificate has been selected.",
        )
        for node in workspace.classes:
            if node.manual_periodicity_id:
                node.label = format_multiplicative_latex(node.label)
                node.expression = normalize_multiplicative_expression(node.expression)
            node.expression = node.expression or node.label
            node.coefficient_context_id = node.coefficient_context_id or "q8-witt-f4"
            node.convention_id = node.convention_id or "q8-thesis-plotted-v1"
        for proposition in workspace.propositions:
            if proposition.source_ref and not proposition.source_refs:
                proposition.source_refs = [proposition.source_ref]
    return project


def ensure_f4_high_rank_cell_sample(project: Project) -> Project:
    """Install the formal-notes d5 whose target is a genuine vector sum."""
    workspace = next((item for item in project.workspaces if item.id == "ws_3sigma_i"), None)
    if workspace is None:
        return project
    classes = {item.id: item for item in workspace.classes}
    source_node = classes.get("three_sum_source")
    target_node = classes.get("three_sum_target")
    if source_node is None or target_node is None:
        return project
    source_ref = "REU Projects/Note/formal_notes.tex:749-760"
    cells = {item.id: item for item in workspace.cells}
    if "cell_three_sum_source" not in cells:
        workspace.cells.append(CellVectorSpace(
            id="cell_three_sum_source",
            grade=source_node.grade,
            page=source_node.page,
            coefficient_context_id="q8-residue-f4",
            basis=[CellBasisVector("basis_three_sum_source", source_node.label, source_node.expression or source_node.label)],
            display_basis=[NamedVector("display_three_sum_source", source_node.label, ["1"], source_node.expression or source_node.label)],
            status="source-verified",
            source_ref=source_ref,
            source_refs=[source_ref],
        ))
    if "cell_three_sum_target" not in cells:
        label_a = "\\{yh_2+xh_1v_1\\}kDu_{3\\sigma_i}"
        label_b = "\\{h_1+xv_1\\}h_1kDu_{3\\sigma_i}"
        workspace.cells.append(CellVectorSpace(
            id="cell_three_sum_target",
            grade=target_node.grade,
            page=target_node.page,
            coefficient_context_id="q8-residue-f4",
            basis=[
                CellBasisVector("basis_three_sum_A", label_a, label_a),
                CellBasisVector("basis_three_sum_B", label_b, label_b),
            ],
            display_basis=[
                NamedVector("display_three_sum_A", "A", ["1", "0"], label_a),
                NamedVector("display_three_sum_B", "B", ["0", "1"], label_b),
            ],
            named_vectors=[NamedVector(
                "vector_three_sum_target", target_node.label, ["1", "1"], target_node.expression or target_node.label,
            )],
            status="source-verified",
            source_ref=source_ref,
            source_refs=[source_ref],
        ))
    source_node.cell_id = "cell_three_sum_source"
    source_node.coordinates = ["1"]
    source_node.coefficient_context_id = "q8-residue-f4"
    target_node.cell_id = "cell_three_sum_target"
    target_node.coordinates = ["1", "1"]
    target_node.coefficient_context_id = "q8-residue-f4"
    maps = {item.id: item for item in workspace.differential_maps}
    if "linear_diff_three_d5_sum" not in maps:
        proposition = next((item for item in workspace.propositions if item.id == "prop_three_d5_sum"), None)
        workspace.differential_maps.append(DifferentialMap(
            id="linear_diff_three_d5_sum",
            source_cell_id="cell_three_sum_source",
            target_cell_id="cell_three_sum_target",
            page=5,
            matrix=[["1"], ["1"]],
            coverage="complete",
            status=proposition.status if proposition else "candidate",
            proposition_id=proposition.id if proposition else "",
            source_ref=source_ref,
            source_refs=[source_ref],
            notes="The target is the line A+B, not either basis vector separately.",
        ))
    differential = next((item for item in workspace.differentials if item.id == "diff_three_d5_sum"), None)
    if differential:
        differential.linear_map_id = "linear_diff_three_d5_sum"
    return project


def ensure_dkllw_f4_argument_audit(project: Project) -> Project:
    """Install the reviewed coefficient-sensitive backbone of DKLLW24.

    These are deliberately narrow source facts, not an automatic assertion
    that every argument in the paper has been formally verified.
    """
    if project.id != "hfpss_studio":
        return project
    integer = next((item for item in project.workspaces if item.id == "ws_integer"), None)
    if not integer:
        return project
    known = {item.id for item in integer.propositions}
    reviewed_at = "2026-08-02"

    def add(proposition: Proposition) -> None:
        if proposition.id not in known:
            integer.propositions.append(proposition)
            known.add(proposition.id)

    add(Proposition(
        id="prop_dkllw_coeff_witt",
        kind="coefficient-foundation",
        statement=r"The coefficient ring is W(F_4)[[u_1]][u^{\pm1}], not F_4 alone.",
        status="established",
        conclusion={"coefficient_context_id": "q8-witt-f4", "scope": "Morava E_2 coefficients"},
        rule="SourceAudit",
        notes="F_4 is the residue field; 2-adic and integral formulas live over its Witt vectors.",
        source_ref="DKLLW24 arXiv v3, main.tex lines 631-649",
        source_refs=["DKLLW24 arXiv v3, main.tex lines 631-649"],
        hypotheses=["coefficient-context:q8-witt-f4"],
        verification_checks=["Match the coefficient ring and the definition of D in the source."],
        reviewer="Codex source audit",
        reviewed_at=reviewed_at,
    ))
    add(Proposition(
        id="prop_dkllw_bss_f4_to_witt",
        kind="coefficient-lift",
        statement=r"The 2-BSS starts over F_4 and reconstructs the W(F_4)-cohomology with its 2-power extensions.",
        status="established",
        conclusion={"source_context_id": "q8-residue-f4", "target_context_id": "q8-witt-f4"},
        premise_ids=["prop_dkllw_coeff_witt"],
        rule="2-Bockstein",
        notes="This is why coefficients such as 2, 4, and 8 must not be reduced to characteristic two in later HFPSS arguments.",
        source_ref="DKLLW24 arXiv v3, main.tex lines 887-892 and 965-1040",
        source_refs=["DKLLW24 arXiv v3, main.tex lines 887-892 and 965-1040"],
        hypotheses=["coefficient-context:q8-residue-f4", "coefficient-context:q8-witt-f4"],
        verification_checks=["Check the E1 and abutment rings.", "Check the displayed 2-, 4-, and 8-torsion Bocksteins."],
        reviewer="Codex source audit",
        reviewed_at=reviewed_at,
    ))
    add(Proposition(
        id="prop_dkllw_c3_f4_eigenspaces",
        kind="coefficient-decomposition",
        statement=r"The rank-three 1,D,D^2 decomposition uses the three F_4-valued C_3 eigencharacters.",
        status="established",
        conclusion={"basis": ["1", "D", "D^2"], "eigenvalues": ["1", "zeta^2", "zeta"]},
        premise_ids=["prop_dkllw_coeff_witt"],
        rule="C3EigenspaceDecomposition",
        notes="The argument genuinely needs F_4 (and zeta); it is not a scalar-free F_2 argument. Source line 918 has a typographical omission, but the surrounding eigenvalue statement is unambiguous.",
        source_ref="DKLLW24 arXiv v3, main.tex lines 898-919",
        source_refs=["DKLLW24 arXiv v3, main.tex lines 898-919"],
        hypotheses=["coefficient-context:q8-residue-f4"],
        verification_checks=["Verify omega(D)=zeta^2 D.", "Verify that all three C3 eigenvalues split over F_4."],
        reviewer="Codex source audit",
        reviewed_at=reviewed_at,
    ))
    add(Proposition(
        id="prop_dkllw_galois_base_change",
        kind="comparison",
        statement=r"The cited Galois comparison is W(F_4)-base change for the integer-graded HFPSS when F/F_0 maps isomorphically to Gal(F_4/F_2).",
        status="established",
        conclusion={"scope": "integer-graded HFPSS", "scalar_behavior": "Galois-semilinear before base change"},
        premise_ids=["prop_dkllw_coeff_witt"],
        rule="GaloisBaseChange",
        notes="This comparison preserves differential patterns; by itself it is not a pagewise isomorphism for every mixed RO(Q8) grading.",
        source_ref="DKLLW24 arXiv v3, main.tex lines 619-629",
        source_refs=["DKLLW24 arXiv v3, main.tex lines 619-629"],
        hypotheses=["coefficient-context:q8-witt-f4"],
        verification_checks=["Check the hypothesis F/F0 -> Gal.", "Keep the displayed pi_* grading distinct from a general RO(Q8) grading."],
        reviewer="Codex source audit",
        reviewed_at=reviewed_at,
    ))
    add(Proposition(
        id="prop_dkllw_unit_ambiguity",
        kind="normalization-guard",
        statement=r"Restriction-based class identifications are only determined up to a unit in W(F_4).",
        status="established",
        conclusion={"precision": "up-to-W(F4)-unit", "does_not_determine": "canonical nonzero scalar"},
        premise_ids=["prop_dkllw_coeff_witt"],
        rule="SourceConvention",
        notes="Existence, non-vanishing, and one-dimensional target arguments survive; an exact normalized coefficient requires an additional choice or computation.",
        source_ref="DKLLW24 arXiv v3, main.tex lines 1573-1579",
        source_refs=["DKLLW24 arXiv v3, main.tex lines 1573-1579"],
        hypotheses=["coefficient-context:q8-witt-f4"],
        verification_checks=["Do not turn an up-to-unit restriction into an exact equality in downstream propositions."],
        reviewer="Codex source audit",
        reviewed_at=reviewed_at,
    ))
    add(Proposition(
        id="prop_dkllw_extended_scope",
        kind="topological-scope-guard",
        statement=r"Q_8 and G_24 lie in the small stabilizer; SD_16 and G_48 use the extended Galois action.",
        status="established",
        conclusion={"small": ["Q8", "G24"], "extended": ["SD16", "G48"]},
        premise_ids=["prop_dkllw_galois_base_change"],
        rule="GroupScope",
        notes="Inside the small stabilizer, the visible quotient symmetry is C3, not an unconditional topological S3 action on every RO(Q8)-graded tower.",
        source_ref="DKLLW24 arXiv v3, main.tex lines 616 and 631-633",
        source_refs=["DKLLW24 arXiv v3, main.tex lines 616 and 631-633"],
        hypotheses=["coefficient-context:q8-witt-f4"],
        verification_checks=["Separate small and extended Morava stabilizer groups."],
        reviewer="Codex source audit",
        reviewed_at=reviewed_at,
    ))
    add(Proposition(
        id="prop_dkllw_mixed_ro_guard",
        kind="topological-scope-guard",
        statement=r"DKLLW24 does not establish a Galois reflection identifying arbitrary mixed RO(Q_8)-graded HFPSS towers.",
        status="established",
        conclusion={"unsupported_transport": "2 sigma_i + sigma_j <-> sigma_i + 2 sigma_j"},
        premise_ids=["prop_dkllw_galois_base_change", "prop_dkllw_extended_scope"],
        rule="ScopeAudit",
        notes="The paper computes the integer and single-sigma_i gradings; a mixed-grading normalizer action needs a separate genuine tower construction.",
        source_ref="DKLLW24 arXiv v3, main.tex lines 255-286 and 1935-1936",
        source_refs=["DKLLW24 arXiv v3, main.tex lines 255-286 and 1935-1936"],
        hypotheses=["coefficient-context:q8-witt-f4"],
        verification_checks=["Do not infer a mixed-RO pagewise isomorphism from the integer-graded Galois base-change lemma."],
        reviewer="Codex source audit",
        reviewed_at=reviewed_at,
    ))
    add(Proposition(
        id="prop_dkllw_f4_audit_conclusion",
        kind="audit-conclusion",
        statement=r"Qualified yes: DKLLW24 respects F_4/W(F_4) for its module and differential patterns, but exact units and arbitrary mixed-RO Galois transport are outside those arguments.",
        status="established",
        conclusion={"verdict": "qualified-yes", "exact_unit_coefficients": False, "mixed_ro_s3_transport": False},
        premise_ids=[
            "prop_dkllw_bss_f4_to_witt",
            "prop_dkllw_c3_f4_eigenspaces",
            "prop_dkllw_unit_ambiguity",
            "prop_dkllw_extended_scope",
            "prop_dkllw_mixed_ro_guard",
        ],
        rule="CoefficientAndScopeAudit",
        notes="Read displayed formulas as normalized representatives whenever the proof supplies only an up-to-unit restriction.",
        source_ref="DKLLW24 coefficient audit, 2026-08-02",
        source_refs=[
            "DKLLW24 arXiv v3, main.tex lines 619-649",
            "DKLLW24 arXiv v3, main.tex lines 887-919",
            "DKLLW24 arXiv v3, main.tex lines 1573-1579",
            "DKLLW24 arXiv v3, main.tex lines 1935-1936",
        ],
        hypotheses=["coefficient-context:q8-residue-f4", "coefficient-context:q8-witt-f4"],
        verification_checks=["All cited premises are admitted.", "No exact unit or mixed-RO S3 claim is smuggled into the conclusion."],
        reviewer="Codex source audit",
        reviewed_at=reviewed_at,
    ))
    return project


def migrate_dkl24_q8_corrections(project: Project) -> Project:
    """Correct only the demonstrably stale DKLLW24 seed records.

    The predicates intentionally match the old generated identifiers and
    coordinates, so this never rewrites a user-created class with the same
    mathematical label.
    """
    integer = next((item for item in project.workspaces if item.id == "ws_integer"), None)
    tate = next((item for item in project.workspaces if item.id == "ws_tate"), None)
    if integer:
        nodes = {item.id: item for item in integer.classes}
        if nodes.get("int_D") and nodes["int_D"].state == "permanent":
            nodes["int_D"].state = "unknown"
            nodes["int_D"].notes = "Supports the established d5; it is not a permanent cycle."
        if nodes.get("int_D2") and nodes["int_D2"].state == "permanent":
            nodes["int_D2"].state = "unknown"
        if "int_D8" not in nodes and "int_D" in nodes:
            integer.classes.append(type(nodes["int_D"])(
                id="int_D8", label="D^8", grade=Grade(stem=64, filtration=0),
                state="permanent", notes="The 64-periodicity class is invertible and permanent.",
            ))
        propositions = {item.id: item for item in integer.propositions}
        if "int_D8" in {item.id for item in integer.classes} and "prop_int_D8_period" not in propositions:
            integer.propositions.append(Proposition(
                id="prop_int_D8_period", kind="permanent-cycle",
                statement="D^8 is an invertible permanent cycle giving 64-periodicity",
                status="established", conclusion={"class_id": "int_D8"},
                rule="DKLLW24 Proposition 4.1", confidence=0.98,
                notes="The period is source-scoped to the Q8 HFPSS for E2.",
                source_ref="DKLLW24, Proposition 4.1 (PDF p. 19)",
                source_refs=["DKLLW24, Proposition 4.1 (PDF p. 19)"],
            ))
        d8_certificate = next((item for item in integer.propositions if item.id == "prop_int_D8_period"), None)
        if d8_certificate:
            d8_certificate.source_ref = "DKLLW24, Proposition 4.1 (local PDF p. 25; journal p. 19)"
            d8_certificate.source_refs = [d8_certificate.source_ref]
            d8_certificate.notes = "D^8 is source-certified as the invertible (64,0) periodicity class."
    if tate:
        g = next((item for item in tate.classes if item.id == "tate_g"), None)
        if g and g.grade.stem == 24 and g.grade.filtration == 0:
            g.label, g.expression = "g=kD^3", "g=kD^3"
            g.grade = Grade(stem=20, filtration=4, representation=g.grade.representation)
            g.notes = "Distinguished class g in the Q8 HFPSS (DKLLW24, Table 7)."

    sigma = next((item for item in project.workspaces if item.id == "ws_sigma_i"), None)
    if sigma:
        legacy = next((item for item in sigma.classes if item.id == "sig_xplusy"), None)
        imported = next((item for item in sigma.classes if item.id == "e2_sigma_xplusy_usigma_i"), None)
        if legacy and legacy.grade.stem == 0 and legacy.grade.filtration == 1:
            legacy.grade = Grade(stem=-1, filtration=1, representation=legacy.grade.representation)
            legacy.notes = "DKLLW24 Table 5 source-backed E2 coordinate."
        if legacy and imported:
            old_id, replacement_id = imported.id, legacy.id
            for proposition in sigma.propositions:
                for key, value in proposition.conclusion.items():
                    if value == old_id:
                        proposition.conclusion[key] = replacement_id
            for differential in sigma.differentials:
                if differential.source_id == old_id:
                    differential.source_id = replacement_id
                if differential.target_id == old_id:
                    differential.target_id = replacement_id
            for event in sigma.differential_events:
                if event.class_id == old_id:
                    event.class_id = replacement_id
                if event.counterpart_class_id == old_id:
                    event.counterpart_class_id = replacement_id
            for fate in sigma.fates:
                if fate.class_id == old_id:
                    fate.class_id = replacement_id
            for product in project.cross_graded_products:
                if product.left_workspace_id == sigma.id and product.left_class_id == old_id:
                    product.left_class_id = replacement_id
                if product.right_workspace_id == sigma.id and product.right_class_id == old_id:
                    product.right_class_id = replacement_id
            sigma.classes = [item for item in sigma.classes if item.id != old_id]

    known = {item.id for item in project.period_families}
    if integer and "period_integer_D8" not in known:
        project.period_families.extend([
            PeriodFamily(
                id="period_integer_D_E2", name="E2 D-period", workspace_id="ws_integer", rank=1,
                generators=[PeriodGenerator(Grade(stem=8, filtration=0), "D")], valid_from_page=2,
                valid_to_page=2, status="established", source_ref="DKLLW24, §6.1.2 (PDF p. 40)",
            ),
            PeriodFamily(
                id="period_integer_D8", name="D^8 64-period", workspace_id="ws_integer", rank=1,
                generators=[PeriodGenerator(Grade(stem=64, filtration=0), "D^8")], valid_from_page=2,
                valid_to_page="infinity", certificate_proposition_id="prop_int_D8_period",
                supporting_proposition_ids=["prop_int_D8_period"], status="established",
                source_ref="DKLLW24, Proposition 4.1 and §6.1.2 (PDF pp. 19, 40)",
            ),
            PeriodFamily(
                id="period_integer_g", name="g=kD^3 (20,4)-period", workspace_id="ws_integer", rank=1,
                generators=[PeriodGenerator(Grade(stem=20, filtration=4), "g=kD^3")], valid_from_page=2,
                valid_to_page="infinity", status="established",
                source_ref="DKLLW24, Table 7 and §6.1.2 (PDF pp. 18, 40); excludes low-filtration v1-local classes",
            ),
        ])
    for family in project.period_families:
        if family.id == "period_integer_D8":
            # DKLLW24 §6.1.2 distinguishes E2 (D-periodic) from the other
            # HFPSS pages (D^8-periodic).  The materialization rule below
            # enforces this same r>=3 boundary.
            family.valid_from_page = 3
            family.source_ref = "DKLLW24, Proposition 4.1 (local PDF p. 25; journal p. 19) and section 6.1.2 (local PDF p. 51; journal p. 40)"
        if family.id == "period_integer_g":
            family.source_ref = "DKLLW24, Table 7 and §6.1.2 (PDF p. 40); excludes low-filtration v1-local classes"

    if sigma and "period_sigma_D8" not in known:
        project.period_families.extend([
            PeriodFamily("period_sigma_D_E2", "(*-sigma_i) E2 D-period", "ws_sigma_i", 1, [PeriodGenerator(Grade(stem=8), "D")], 2, 2, status="established", source_ref="DKLLW24, §6.1.2 (PDF p. 40)"),
            PeriodFamily("period_sigma_D8", "(*-sigma_i) D^8 64-period", "ws_sigma_i", 1, [PeriodGenerator(Grade(stem=64), "D^8")], 3, "infinity", status="established", source_ref="DKLLW24, section 6.1.2 (local PDF p. 51; journal p. 40)"),
            PeriodFamily("period_sigma_g", "(*-sigma_i) g=kD^3 (20,4)-period", "ws_sigma_i", 1, [PeriodGenerator(Grade(stem=20, filtration=4), "g=kD^3")], 2, "infinity", status="established", source_ref="DKLLW24, §6.1.2 (PDF p. 40); excludes low-filtration v1-local classes"),
        ])
    return project


def migrate_project(project: Project) -> Project:
    ensure_foundations(project)
    ensure_f4_high_rank_cell_sample(project)
    ensure_dkllw_f4_argument_audit(project)
    ensure_dkllw_fact_chain(project)
    ensure_reu_fact_chain(project)
    ensure_q8_atlas(project)
    ensure_c3_action(project)
    migrate_dkl24_q8_corrections(project)
    ensure_source_backed_q8_periodicity_rules(project)
    ensure_q8_atlas(project)
    migrate_legacy_period_families(project)
    sync_project_fates(project)
    return project
