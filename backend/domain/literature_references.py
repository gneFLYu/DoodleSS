"""Install independent, source-scoped review workspaces without replacing user data."""
from __future__ import annotations

from .models import CoefficientContext, Project


def ensure_literature_references(project: Project) -> Project:
    # Local imports keep model-only consumers independent of chart builders.
    from .bss_reference import create_bss_reference_workspaces
    from .c4_reference import create_c4_reference_workspaces

    known = {workspace.id for workspace in project.workspaces}
    additions = []
    if not {"ws_c4_bbhs_integer", "ws_c4_bbhs_1_minus_sigma"} <= known:
        additions.extend(create_c4_reference_workspaces())
    if not {"ws_q8_bss_integer", "ws_q8_bss_sigma"} <= known:
        additions.extend(create_bss_reference_workspaces())
    for workspace in additions:
        if workspace.id not in known:
            workspace.settings.setdefault("vanishing_line", 0)
            workspace.settings.setdefault("vanishing_line_source", "No source-scoped vanishing-line certificate has been selected.")
            for proposition in workspace.propositions:
                if proposition.source_ref and not proposition.source_refs:
                    proposition.source_refs = [proposition.source_ref]
            project.workspaces.append(workspace)
            known.add(workspace.id)
    contexts = {context.id for context in project.coefficient_contexts}
    for context in (
        CoefficientContext("c4-bbhs-witt-k", residue_field="k", coefficient_ring="W(k)[[mu]]", scalar_mode="formal",
                           source_ref="BBHS20, Proposition 5.10"),
        CoefficientContext("q8-bss-f4-h0", coefficient_ring="F4[h0]", scalar_mode="residue",
                           bockstein_stage="E1 with independent h0 filtration", source_ref="DKLLW24, Section 3; h0 detects 2"),
    ):
        if context.id not in contexts:
            project.coefficient_contexts.append(context)
    return project
