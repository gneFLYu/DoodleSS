"""Read-only audit for differentials that are not yet admitted.

This module deliberately does not change a project or promote a source proof.
It cross-checks the formal chart against the periodic fate ledger and records
the exact open premise for every ``review`` or ``source-proved`` fact.  A
separate status mismatch is reported as a warning because the governing
record intentionally keeps source status and admission status distinct.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from .formal_notes_chart import (
    DERIVED_FORMAL_ARROWS,
    FORMAL_ARROWS,
    _MACHINE_VERIFICATION_PENDING,
    _SOURCE_BLOCKERS,
    _SOURCE_CONFLICTS,
)
from .periodic_fate_ledger import FATE_CERTIFYING_STATUSES, load_periodic_fate_ledger
from .fate import resolve_raw_coefficient_parameter
from .models import Project


UNDECIDED_STATUSES = frozenset({"review", "source-proved"})
REJECTED_STATUSES = frozenset({"rejected", "superseded"})


def _arrow_record(arrow: Any) -> dict[str, Any]:
    delta = (
        arrow.target_stem - arrow.source_stem,
        arrow.target_filtration - arrow.source_filtration,
    )
    return {
        "fact_id": arrow.fact_id,
        "workspace_id": arrow.workspace_id,
        "page": arrow.page,
        "source": {
            "label": arrow.source_label,
            "bidegree": [arrow.source_stem, arrow.source_filtration],
        },
        "target": {
            "label": arrow.target_label,
            "bidegree": [arrow.target_stem, arrow.target_filtration],
        },
        "delta": list(delta),
        "expected_delta": [-1, arrow.page],
        "status": arrow.status,
        "source_ref": arrow.source_ref,
        "period_stem": arrow.period_stem,
        "degree_valid": delta == (-1, arrow.page),
    }


def audit_undecided_differentials(
    ledger: dict[str, Any] | None = None,
    *, project: Project | None = None, workspace_id: str | None = None,
) -> dict[str, Any]:
    """Return a machine-checkable inventory of unresolved differential facts.

    ``valid`` means that the inventory is structurally complete: every
    unresolved ledger fact has a chart occurrence, every occurrence has a
    source locator, and every arrow has the differential bidegree shift
    ``(-1, r)``.  It does *not* mean that the unresolved facts are proved.
    """
    data = ledger or load_periodic_fate_ledger()
    facts = {
        str(item.get("id")): item
        for item in data.get("fact_families", [])
        if item.get("id")
    }
    arrows = tuple(FORMAL_ARROWS) + tuple(DERIVED_FORMAL_ARROWS)
    by_fact: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for arrow in arrows:
        if workspace_id is None or arrow.workspace_id == workspace_id:
            by_fact[arrow.fact_id].append(_arrow_record(arrow))

    errors: list[str] = []
    warnings: list[str] = []
    obligations: list[dict[str, Any]] = []
    unresolved_fact_ids = [
        fact_id
        for fact_id, fact in facts.items()
        if fact.get("status") in UNDECIDED_STATUSES
        and "differential" in str(fact.get("kind", ""))
    ]

    for fact_id in sorted(unresolved_fact_ids):
        fact = facts[fact_id]
        occurrences = by_fact.get(fact_id, [])
        if workspace_id is not None and not occurrences:
            continue
        if not occurrences:
            errors.append(f"{fact_id} has no formal-chart occurrence")
        if any(not occurrence["source_ref"] for occurrence in occurrences):
            errors.append(f"{fact_id} has an occurrence without source_ref")
        if any(not occurrence["degree_valid"] for occurrence in occurrences):
            errors.append(f"{fact_id} has an invalid differential bidegree")

        chart_statuses = sorted({occurrence["status"] for occurrence in occurrences})
        if chart_statuses and fact.get("status") not in chart_statuses:
            warnings.append(
                f"{fact_id} ledger status {fact.get('status')} differs from "
                f"formal-chart status {','.join(chart_statuses)}"
            )

        missing_premises: list[str] = []
        if fact_id in _SOURCE_BLOCKERS:
            missing_premises.append(_SOURCE_BLOCKERS[fact_id])
        if fact_id in _MACHINE_VERIFICATION_PENDING:
            missing_premises.append(_MACHINE_VERIFICATION_PENDING[fact_id])
        conflicts = _SOURCE_CONFLICTS.get(fact_id)
        if conflicts:
            missing_premises.append(
                "source conflict remains open: " + str(conflicts.get("kind", "unspecified"))
            )
        if not missing_premises:
            missing_premises.append(
                "ledger marks this fact unresolved without a registered blocker"
            )

        obligations.append(
            {
                "fact_id": fact_id,
                "ledger_status": fact.get("status"),
                "runtime_admission": fact.get("runtime_admission"),
                "occurrences": occurrences,
                "missing_premises": missing_premises,
                "scope": "historical-ledger; current coefficient resolution is reported separately",
            }
        )

    # A non-unresolved chart occurrence must not silently disappear from the
    # ledger when it claims a status that the ledger treats as certifying.
    primary_fact_ids = {arrow.fact_id for arrow in FORMAL_ARROWS
                        if workspace_id is None or arrow.workspace_id == workspace_id}
    for fact_id in sorted(primary_fact_ids):
        occurrences = by_fact[fact_id]
        if fact_id not in facts and any(
            occurrence["status"] in FATE_CERTIFYING_STATUSES
            for occurrence in occurrences
        ):
            errors.append(f"{fact_id} has a certifying chart occurrence but no ledger fact")

    coefficient_evidence = _coefficient_evidence(project, workspace_id)
    return {
        "valid": not errors,
        "status": "underdetermined" if obligations else "resolved",
        "fact_count": len(facts),
        "unresolved_fact_count": len(obligations),
        "errors": errors,
        "warnings": warnings,
        "obligations": obligations,
        "workspace_filter": workspace_id,
        "coefficient_evidence": coefficient_evidence,
    }


def _coefficient_evidence(project: Project | None, workspace_id: str | None) -> dict[str, Any]:
    """Separate a historical printed unit, a current assignment and a proof."""
    directory = Path(__file__).resolve().parents[1] / "data" / "review"
    c_audit = json.loads((directory / "mixed_phi_a_coefficient.v1.json").read_text(encoding="utf-8"))
    remaining = json.loads((directory / "mixed_remaining_units.v1.json").read_text(encoding="utf-8"))
    result = {
        "source_coefficient_audit": {"id": c_audit["id"], "parameter_id": c_audit["coefficient_parameter_id"],
                                     "source_value": c_audit["coefficient_value"], "status": c_audit["status"],
                                     "historical_comparison": c_audit["historical_comparison"]},
        "remaining_numeric_units": remaining["parameters"],
        "remaining_numeric_unit_count": len(remaining["parameters"]),
        "derived_constraints": remaining["derived_constraints"],
        "runtime_project_inspected": project is not None, "runtime_workspaces": [],
        "note": "Source-audit values and document defaults do not grant runtime admission. Runtime proof bindings are resolved against the supplied live project without migration or mutation.",
    }
    if project is None:
        return result
    parameter_ids = [c_audit["coefficient_parameter_id"], *[p["parameter_id"] for p in remaining["parameters"]]]
    sources = {p["parameter_id"]: p for p in remaining["parameters"]}
    for workspace in project.workspaces:
        if workspace_id is not None and workspace.id != workspace_id:
            continue
        has_c = any(isinstance(p.conclusion.get(key), dict)
                    and p.conclusion[key].get("id" if key == "coefficient_parameter" else "parameter_id") == parameter_ids[0]
                    for p in workspace.propositions for key in ("coefficient_parameter", "coefficient_proof_registration"))
        has_c = has_c or workspace.settings.get("atlas_transport", {}).get("source_workspace_id") == c_audit["workspace_id"]
        if workspace_id is None and workspace.id != c_audit["workspace_id"] and not has_c:
            continue
        records = []
        for ident in parameter_ids:
            resolved = resolve_raw_coefficient_parameter(workspace, ident, project=project)
            declarations = [p for p in workspace.propositions
                            if isinstance(p.conclusion.get("coefficient_parameter"), dict)
                            and p.conclusion["coefficient_parameter"].get("id") == ident]
            record = {"parameter_id": ident, "resolution": resolved,
                      "declaration_count": len(declarations),
                      "numeric_proof_status": "proved-current" if resolved.get("proof_bound") and resolved["resolved"]
                      else "unresolved-proof" if resolved.get("proof_bound") else "not-numerically-proved"}
            if ident in sources:
                evidence = sources[ident]
                record.update({"source_numeric_status": evidence["numeric_status"],
                               "document_default": evidence["document_default"],
                               "source_D_residue_mod_8": evidence.get("source_D_residue_mod_8"),
                               "source_gap": evidence["gap"],
                               "runtime_row_ids": [row.id for row in workspace.differentials
                                                   if any(row.id.endswith(legacy) for legacy in evidence["runtime_rows"])]})
                if not declarations and record["runtime_row_ids"]:
                    record["runtime_scope_warning"] = "Document row exists without an independent raw parameter declaration; a printed unit or shared period32 row is not a proof of these separate units."
            records.append(record)
        result["runtime_workspaces"].append({"workspace_id": workspace.id, "parameters": records})
    return result
