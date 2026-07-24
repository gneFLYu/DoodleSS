"""Idempotent migrations for persisted HFPSS Studio projects."""
from __future__ import annotations

from .models import (
    CoefficientContext, Grade, PeriodFamily, PeriodGenerator, Project,
    Proposition, SCHEMA_VERSION, SymbolDefinition,
)
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
    ensure_q8_atlas(project)
    ensure_c3_action(project)
    migrate_dkl24_q8_corrections(project)
    ensure_source_backed_q8_periodicity_rules(project)
    ensure_q8_atlas(project)
    migrate_legacy_period_families(project)
    sync_project_fates(project)
    return project
