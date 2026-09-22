"""Read-only audit for differentials that are not yet admitted.

This module deliberately does not change a project or promote a source proof.
It cross-checks the formal chart against the periodic fate ledger and records
the exact open premise for every ``review`` or ``source-proved`` fact.  A
separate status mismatch is reported as a warning because the governing
record intentionally keeps source status and admission status distinct.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .formal_notes_chart import (
    DERIVED_FORMAL_ARROWS,
    FORMAL_ARROWS,
    _MACHINE_VERIFICATION_PENDING,
    _SOURCE_BLOCKERS,
    _SOURCE_CONFLICTS,
)
from .periodic_fate_ledger import FATE_CERTIFYING_STATUSES, load_periodic_fate_ledger


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
            }
        )

    # A non-unresolved chart occurrence must not silently disappear from the
    # ledger when it claims a status that the ledger treats as certifying.
    primary_fact_ids = {arrow.fact_id for arrow in FORMAL_ARROWS}
    for fact_id in sorted(primary_fact_ids):
        occurrences = by_fact[fact_id]
        if fact_id not in facts and any(
            occurrence["status"] in FATE_CERTIFYING_STATUSES
            for occurrence in occurrences
        ):
            errors.append(f"{fact_id} has a certifying chart occurrence but no ledger fact")

    return {
        "valid": not errors,
        "status": "underdetermined" if obligations else "resolved",
        "fact_count": len(facts),
        "unresolved_fact_count": len(obligations),
        "errors": errors,
        "warnings": warnings,
        "obligations": obligations,
    }
