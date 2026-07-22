"""Immutable differential events and derived class lifecycles."""
from __future__ import annotations

from .models import (
    ClassFate,
    DifferentialEvent,
    Project,
    Proposition,
    Workspace,
)


ACCEPTED_STATUSES = frozenset({"derived", "reviewed", "established", "proven"})
REJECTED_STATUSES = frozenset({"rejected", "superseded"})


def is_accepted(status: str) -> bool:
    return status in ACCEPTED_STATUSES


def workspace_sequence_kind(workspace: Workspace) -> str:
    if workspace.spectral_sequence in {"hfpss", "tate"}:
        return workspace.spectral_sequence
    searchable = f"{workspace.id} {workspace.name} {workspace.grading_label}".lower()
    return "tate" if "tate" in searchable else "hfpss"


def _matching_proposition(workspace: Workspace, differential) -> Proposition | None:
    for proposition in workspace.propositions:
        conclusion = proposition.conclusion
        if (
            proposition.kind == "differential"
            and conclusion.get("source_id") == differential.source_id
            and conclusion.get("target_id") == differential.target_id
            and int(conclusion.get("page", -1)) == differential.page
        ):
            return proposition
    return None


def ensure_differential_propositions(workspace: Workspace) -> None:
    """Give every differential exactly one auditable assertion link.

    Legacy arrows are linked to their matching imported proposition.  If the
    old file has no such proposition, a visibly source-scoped migration claim
    is created rather than treating the arrow as an unrecorded theorem.
    """
    by_id = {item.id: item for item in workspace.propositions}
    for differential in workspace.differentials:
        proposition = by_id.get(differential.proposition_id)
        if proposition is None:
            proposition = _matching_proposition(workspace, differential)
        if proposition is None:
            proposition = Proposition(
                id=f"prop_for_{differential.id}",
                kind="differential",
                statement=(
                    f"Imported d_{differential.page}: "
                    f"{differential.source_id} -> {differential.target_id}"
                ),
                status=differential.status,
                conclusion={
                    "source_id": differential.source_id,
                    "target_id": differential.target_id,
                    "page": differential.page,
                },
                rule="LegacyMigration",
                confidence=0.5,
                notes="Generated only to preserve the provenance boundary of a legacy arrow.",
                source_ref="Legacy project differential record",
                source_refs=["Legacy project differential record"],
            )
            workspace.propositions.append(proposition)
            by_id[proposition.id] = proposition
        differential.proposition_id = proposition.id


def sync_differential_events(workspace: Workspace) -> None:
    """Materialize missing event records without deleting imported history."""
    ensure_differential_propositions(workspace)
    classes = {item.id: item for item in workspace.classes}
    propositions = {item.id: item for item in workspace.propositions}
    existing = {item.id for item in workspace.differential_events}
    sequence = workspace_sequence_kind(workspace)

    for differential in workspace.differentials:
        source = classes.get(differential.source_id)
        target = classes.get(differential.target_id)
        if not source or not target:
            continue
        proposition = propositions.get(differential.proposition_id)
        source_refs = []
        if proposition:
            source_refs = list(proposition.source_refs)
            if proposition.source_ref and proposition.source_ref not in source_refs:
                source_refs.append(proposition.source_ref)
        source_in_hfpss = source.grade.filtration >= 0
        comparison_status = "transports_to_hfpss"
        if sequence == "tate" and not source_in_hfpss:
            comparison_status = "tate_only_negative_source"

        for role, node, counterpart in (
            ("supports", source, target),
            ("receives", target, source),
        ):
            event_id = f"event_{differential.id}_{role}"
            if event_id in existing:
                continue
            workspace.differential_events.append(
                DifferentialEvent(
                    id=event_id,
                    spectral_sequence=sequence,
                    page=differential.page,
                    role=role,
                    class_id=node.id,
                    counterpart_class_id=counterpart.id,
                    differential_claim_id=differential.id,
                    source_filtration=source.grade.filtration,
                    target_filtration=target.grade.filtration,
                    source_exists_in_hfpss=source_in_hfpss,
                    comparison_status=comparison_status,
                    proposition_id=differential.proposition_id,
                    source_refs=source_refs,
                    status=differential.status,
                )
            )
            existing.add(event_id)


def derive_class_fate(workspace: Workspace, class_id: str) -> ClassFate:
    node = next(item for item in workspace.classes if item.id == class_id)
    events = [item for item in workspace.differential_events if item.class_id == class_id]
    hfpss_outgoing = [item.id for item in events if item.spectral_sequence == "hfpss" and item.role == "supports"]
    hfpss_incoming = [item.id for item in events if item.spectral_sequence == "hfpss" and item.role == "receives"]
    tate_outgoing = [item.id for item in events if item.spectral_sequence == "tate" and item.role == "supports"]
    tate_incoming = [item.id for item in events if item.spectral_sequence == "tate" and item.role == "receives"]

    accepted_deaths = sorted(
        (
            item for item in events
            if item.spectral_sequence == "hfpss"
            and item.comparison_status != "tate_only_negative_source"
            and is_accepted(item.status)
        ),
        key=lambda item: (item.page, 0 if item.role == "supports" else 1, item.id),
    )
    permanent_claims = [
        proposition for proposition in workspace.propositions
        if proposition.kind == "permanent-cycle"
        and proposition.conclusion.get("class_id") == class_id
        and is_accepted(proposition.status)
    ]

    first_death = accepted_deaths[0] if accepted_deaths else None
    first_hfpss_death = None
    conclusion = "unresolved"
    conclusion_page: int | str | None = None
    last_live_page: int | str = "unknown"
    justification_ids: list[str] = []

    if first_death:
        first_hfpss_death = {
            "page": first_death.page,
            "role": first_death.role,
            "claim_id": first_death.differential_claim_id,
        }
        last_live_page = first_death.page
        conclusion_page = first_death.page
        conclusion = "supports_differential" if first_death.role == "supports" else "is_hit"
        justification_ids.append(first_death.proposition_id)

    if permanent_claims:
        justification_ids.extend(item.id for item in permanent_claims)
        if first_death:
            # Preserve contradictory accepted evidence for review; never let a
            # stale permanent badge overwrite an accepted differential.
            conclusion = "unresolved"
        else:
            conclusion = "permanent_cycle"
            conclusion_page = "infinity"
            last_live_page = "infinity"

    return ClassFate(
        class_id=class_id,
        appears_from_page=node.page,
        hfpss_outgoing_events=hfpss_outgoing,
        hfpss_incoming_events=hfpss_incoming,
        tate_outgoing_events=tate_outgoing,
        tate_incoming_events=tate_incoming,
        first_hfpss_death=first_hfpss_death,
        last_hfpss_live_page=last_live_page,
        conclusion=conclusion,
        conclusion_page=conclusion_page,
        justification_ids=list(dict.fromkeys(item for item in justification_ids if item)),
    )


def sync_workspace_fates(workspace: Workspace) -> None:
    sync_differential_events(workspace)
    workspace.fates = [derive_class_fate(workspace, item.id) for item in workspace.classes]


def sync_project_fates(project: Project) -> Project:
    for workspace in project.workspaces:
        sync_workspace_fates(workspace)
    return project


def class_is_live_on_page(workspace: Workspace, class_id: str, page: int) -> bool:
    fate = next((item for item in workspace.fates if item.class_id == class_id), None)
    if fate is None:
        fate = derive_class_fate(workspace, class_id)
    death = fate.first_hfpss_death
    return death is None or int(death["page"]) >= page
