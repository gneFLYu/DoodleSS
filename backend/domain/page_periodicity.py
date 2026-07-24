"""Page-aware, virtual period cycles and legacy-materialization retirement.

Page periods are user-declared mathematical input.  They are represented by a
compact record and review-only virtual instances; this module never creates a
``ClassNode``, ``Differential``, or ``Proposition`` for a periodic translate.

The retirement helpers are deliberately explicit and ownership-based.  They
only remove IDs listed by a selected legacy ``ManualPeriodicity`` record and
whose record-level owner points back to that same operation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Iterable

from .algebra_labels import (
    AlgebraLabelError,
    multiply_label_by_period,
    parse_algebra_label,
)
from .fate import REJECTED_STATUSES, class_is_live_on_page, sync_workspace_fates
from .models import (
    Grade,
    ManualPeriodicity,
    PagePeriodCycle,
    Project,
    Workspace,
    new_id,
)


class PagePeriodicityError(ValueError):
    """Raised when a page-period or retirement request is unsafe."""


@dataclass(frozen=True)
class PagePeriodStatus:
    cycle_id: str
    page: int
    eligible: bool
    reason: str
    blocking_differential_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "blocking_differential_ids": list(self.blocking_differential_ids),
        }


def prepare_page_period_cycle(
    project: Project,
    workspace_id: str,
    payload: dict[str, Any],
) -> PagePeriodCycle:
    """Validate a compact period-cycle declaration without mutating a project.

    The displayed ``label`` is the only algebra expression.  A deprecated
    ``expression`` field is rejected rather than silently diverging from it.
    """

    if not isinstance(payload, dict):
        raise PagePeriodicityError("page-period payload must be a JSON object.")
    if "expression" in payload:
        raise PagePeriodicityError(
            "Use label as the algebra expression; a separate expression field is not supported."
        )
    workspace = _workspace(project, workspace_id)
    page = _page(payload.get("page"), field="page")
    cycle_class_id = _optional_string(payload.get("cycle_class_id", ""))
    label = payload.get("label")
    raw_grade = payload.get("grade")
    selected = None
    if cycle_class_id:
        selected = next(
            (item for item in workspace.classes if item.id == cycle_class_id),
            None,
        )
        if selected is None or selected.archived:
            raise PagePeriodicityError("cycle_class_id must select an active class.")
        if selected.page > page or not class_is_live_on_page(workspace, selected.id, page):
            raise PagePeriodicityError(
                f"The selected cycle is not live on E_{page}."
            )
        if label is None:
            label = selected.label
        if raw_grade is None:
            grade = selected.grade
        else:
            grade = _grade(raw_grade)
            if grade != selected.grade:
                raise PagePeriodicityError(
                    "An explicit period grade must equal the selected cycle grade."
                )
    else:
        if raw_grade is None:
            raise PagePeriodicityError(
                "An explicit period cycle requires grade or cycle_class_id."
            )
        grade = _grade(raw_grade)

    try:
        canonical_label = parse_algebra_label(str(label or "")).label
    except AlgebraLabelError as error:
        raise PagePeriodicityError(str(error)) from error
    if canonical_label == "1" or grade == Grade():
        raise PagePeriodicityError(
            "A page period must be a nonconstant cycle with a nonzero grade."
        )
    basis = _required_string(payload.get("basis"), "basis")
    source_ref = _required_string(payload.get("source_ref"), "source_ref")
    status = str(payload.get("status", "candidate")).strip().lower()
    if status not in {"candidate", "reviewed", "established", "proven"}:
        raise PagePeriodicityError(
            "status must be candidate, reviewed, established, or proven."
        )
    identifier = _optional_string(payload.get("id")) or new_id("page_period")
    return PagePeriodCycle(
        id=identifier,
        workspace_id=workspace.id,
        label=canonical_label,
        grade=grade,
        declared_page=page,
        cycle_class_id=cycle_class_id,
        invertible=bool(payload.get("invertible", False)),
        basis=basis,
        source_ref=source_ref,
        status=status,
        virtual=True,
    )


def register_page_period_cycle(project: Project, cycle: PagePeriodCycle) -> PagePeriodCycle:
    """Append one validated compact cycle; no chart records are generated."""

    if any(item.id == cycle.id for item in project.page_period_cycles):
        raise PagePeriodicityError(f"page-period cycle {cycle.id!r} already exists.")
    _workspace(project, cycle.workspace_id)
    project.page_period_cycles.append(cycle)
    return cycle


def page_period_status(
    project: Project,
    cycle_id: str,
    page: int,
) -> PagePeriodStatus:
    """Return whether the cycle may act as a period on exactly ``E_page``.

    A declaration on E_r is automatically available on E_2 through E_r.  To
    cross E_s -> E_(s+1), the selected cycle must have no non-rejected incoming
    or outgoing d_s.  Candidate/claimed arrows block automatic propagation:
    absence of a certified arrow is not treated as a theorem.
    """

    target_page = _page(page, field="page")
    cycle = _cycle(project, cycle_id)
    workspace = _workspace(project, cycle.workspace_id)
    if target_page <= cycle.declared_page:
        return PagePeriodStatus(
            cycle.id,
            target_page,
            True,
            f"Declared on E_{cycle.declared_page}; a period there acts on all earlier pages.",
        )
    if not cycle.cycle_class_id:
        return PagePeriodStatus(
            cycle.id,
            target_page,
            False,
            "An explicit unlinked cycle cannot be propagated beyond its declared page.",
        )
    selected = next(
        (
            item
            for item in workspace.classes
            if item.id == cycle.cycle_class_id and not item.archived
        ),
        None,
    )
    if selected is None:
        return PagePeriodStatus(
            cycle.id,
            target_page,
            False,
            "The selected period-cycle class is missing or archived.",
        )
    for transition_page in range(cycle.declared_page, target_page):
        blockers = tuple(
            item.id
            for item in workspace.differentials
            if item.page == transition_page
            and item.status not in REJECTED_STATUSES
            and cycle.cycle_class_id in {item.source_id, item.target_id}
        )
        if blockers:
            return PagePeriodStatus(
                cycle.id,
                target_page,
                False,
                (
                    f"The cycle is hit by or supports a non-rejected d_{transition_page}; "
                    f"it cannot automatically pass to E_{transition_page + 1}."
                ),
                blockers,
            )
        if not class_is_live_on_page(
            workspace,
            cycle.cycle_class_id,
            transition_page + 1,
        ):
            return PagePeriodStatus(
                cycle.id,
                target_page,
                False,
                f"The selected cycle is not live on E_{transition_page + 1}.",
            )
    return PagePeriodStatus(
        cycle.id,
        target_page,
        True,
        (
            f"No non-rejected incoming or outgoing differential blocks the "
            f"selected cycle through E_{target_page}."
        ),
    )


def plan_virtual_period_instances(
    project: Project,
    cycle_id: str,
    *,
    page: int,
    base_class_ids: Iterable[str],
    translations: Iterable[int],
) -> dict[str, Any]:
    """Return review-only period multiples without persisting chart records."""

    target_page = _page(page, field="page")
    cycle = _cycle(project, cycle_id)
    status = page_period_status(project, cycle.id, target_page)
    if not status.eligible:
        raise PagePeriodicityError(status.reason)
    workspace = _workspace(project, cycle.workspace_id)
    base_ids = _unique_strings(base_class_ids, "base_class_ids")
    shifts = _positive_translations(translations)
    classes = {item.id: item for item in workspace.classes}
    instances: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for class_id in base_ids:
        node = classes.get(class_id)
        if node is None:
            raise PagePeriodicityError(f"Unknown base class {class_id!r}.")
        if node.archived:
            skipped.append({"class_id": class_id, "reason": "archived"})
            continue
        if node.manual_periodicity_id:
            skipped.append(
                {
                    "class_id": class_id,
                    "reason": "legacy-manual-periodicity-derived",
                }
            )
            continue
        if node.page > target_page or not class_is_live_on_page(
            workspace,
            node.id,
            target_page,
        ):
            skipped.append(
                {"class_id": class_id, "reason": f"not-live-on-E_{target_page}"}
            )
            continue
        for translation in shifts:
            try:
                label = multiply_label_by_period(
                    node.label,
                    cycle.label,
                    translation,
                )
            except AlgebraLabelError as error:
                raise PagePeriodicityError(str(error)) from error
            grade = node.grade
            for _ in range(translation):
                grade = grade.shifted(cycle.grade)
            instances.append(
                {
                    "kind": "virtual-period-instance",
                    "persisted": False,
                    "page_period_cycle_id": cycle.id,
                    "base_class_id": node.id,
                    "translation": translation,
                    "label": label.label,
                    "registered_generators": [
                        asdict(item) for item in label.registered_generators
                    ],
                    "grade": asdict(grade),
                    "page": target_page,
                    "provenance": {
                        "basis": cycle.basis,
                        "source_ref": cycle.source_ref,
                        "status": cycle.status,
                    },
                }
            )
    return {
        "cycle": asdict(cycle),
        "page_status": status.to_dict(),
        "instances": instances,
        "skipped": skipped,
        "persisted": False,
        "created_class_ids": [],
        "created_differential_ids": [],
        "created_proposition_ids": [],
    }


def preview_manual_periodicity_retirement(
    project: Project,
    manual_periodicity_ids: Iterable[str],
) -> dict[str, Any]:
    """Audit exact legacy generated IDs without mutating ``project``."""

    requested = _unique_strings(
        manual_periodicity_ids,
        "manual_periodicity_ids",
    )
    records = {item.id: item for item in project.manual_periodicities}
    unknown = [item for item in requested if item not in records]
    if unknown:
        raise PagePeriodicityError(
            f"Unknown manual-periodicity records: {', '.join(unknown)}."
        )
    selected = [records[item] for item in requested]
    workspaces = {item.id: item for item in project.workspaces}
    conflicts: list[dict[str, str]] = []
    eligible_classes: set[str] = set()
    eligible_differentials: set[str] = set()
    eligible_propositions: set[str] = set()
    missing = {"classes": [], "differentials": [], "propositions": []}
    record_summaries: dict[str, dict[str, Any]] = {}

    for record in selected:
        record_class_ids: list[str] = []
        record_differential_ids: list[str] = []
        record_proposition_ids: list[str] = []
        record_missing = {"classes": 0, "differentials": 0, "propositions": 0}
        record_active_classes = 0
        record_archived_classes = 0
        workspace = workspaces.get(record.workspace_id)
        if workspace is None:
            conflicts.append(
                {
                    "record_id": record.id,
                    "reason": "workspace-missing",
                    "object_id": record.workspace_id,
                }
            )
            record_summaries[record.id] = {
                "workspace_id": record.workspace_id,
                "counts": {
                    "classes": 0,
                    "active_classes": 0,
                    "archived_classes": 0,
                    "differentials": 0,
                    "propositions": 0,
                },
                "missing_counts": record_missing,
            }
            continue
        classes = {item.id: item for item in workspace.classes}
        differentials = {item.id: item for item in workspace.differentials}
        propositions = {item.id: item for item in workspace.propositions}
        for class_id in record.created_class_ids:
            node = classes.get(class_id)
            if node is None:
                missing["classes"].append(class_id)
                record_missing["classes"] += 1
            elif node.manual_periodicity_id != record.id:
                conflicts.append(
                    {
                        "record_id": record.id,
                        "object_id": class_id,
                        "reason": "class-owner-mismatch",
                    }
                )
            else:
                eligible_classes.add(class_id)
                record_class_ids.append(class_id)
                if node.archived:
                    record_archived_classes += 1
                else:
                    record_active_classes += 1
        for differential_id in record.created_differential_ids:
            differential = differentials.get(differential_id)
            if differential is None:
                missing["differentials"].append(differential_id)
                record_missing["differentials"] += 1
            elif differential.manual_periodicity_id != record.id:
                conflicts.append(
                    {
                        "record_id": record.id,
                        "object_id": differential_id,
                        "reason": "differential-owner-mismatch",
                    }
                )
            else:
                eligible_differentials.add(differential_id)
                record_differential_ids.append(differential_id)
        for proposition_id in record.created_proposition_ids:
            proposition = propositions.get(proposition_id)
            if proposition is None:
                missing["propositions"].append(proposition_id)
                record_missing["propositions"] += 1
            elif proposition.conclusion.get("manual_periodicity_id") != record.id:
                conflicts.append(
                    {
                        "record_id": record.id,
                        "object_id": proposition_id,
                        "reason": "proposition-owner-mismatch",
                    }
                )
            else:
                eligible_propositions.add(proposition_id)
                record_proposition_ids.append(proposition_id)
        if record.anchor_class_id in record_class_ids:
            conflicts.append(
                {
                    "record_id": record.id,
                    "object_id": record.anchor_class_id,
                    "reason": "record-anchor-is-generated",
                }
            )
        if record.anchor_differential_id in record_differential_ids:
            conflicts.append(
                {
                    "record_id": record.id,
                    "object_id": record.anchor_differential_id,
                    "reason": "record-anchor-is-generated",
                }
            )
        record_summaries[record.id] = {
            "workspace_id": record.workspace_id,
            "counts": {
                "classes": len(record_class_ids),
                "active_classes": record_active_classes,
                "archived_classes": record_archived_classes,
                "differentials": len(record_differential_ids),
                "propositions": len(record_proposition_ids),
            },
            "missing_counts": record_missing,
        }

    conflicts.extend(
        _external_reference_conflicts(
            project,
            selected_ids=set(requested),
            class_ids=eligible_classes,
            differential_ids=eligible_differentials,
            proposition_ids=eligible_propositions,
        )
    )
    normalized_missing = {
        key: sorted(set(value)) for key, value in missing.items()
    }
    already_retired = sorted(
        record.id
        for record in selected
        if record.storage_mode == "retired-compact"
        and not record.created_class_ids
        and not record.created_differential_ids
        and not record.created_proposition_ids
    )
    identity = {
        "manual_periodicity_ids": requested,
        "class_ids": sorted(eligible_classes),
        "differential_ids": sorted(eligible_differentials),
        "proposition_ids": sorted(eligible_propositions),
        "record_summaries": record_summaries,
        "missing": normalized_missing,
        "conflicts": conflicts,
    }
    digest = sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "operation": "retire-legacy-manual-periodicity",
        "manual_periodicity_ids": requested,
        "eligible": {
            "class_ids": sorted(eligible_classes),
            "differential_ids": sorted(eligible_differentials),
            "proposition_ids": sorted(eligible_propositions),
        },
        "counts": {
            "classes": len(eligible_classes),
            "active_classes": sum(
                item["counts"]["active_classes"]
                for item in record_summaries.values()
            ),
            "archived_classes": sum(
                item["counts"]["archived_classes"]
                for item in record_summaries.values()
            ),
            "differentials": len(eligible_differentials),
            "propositions": len(eligible_propositions),
        },
        "records": record_summaries,
        "missing": normalized_missing,
        "conflicts": conflicts,
        "can_apply": not conflicts,
        "already_retired": already_retired,
        "would_change": len(already_retired) != len(selected),
        "digest": digest,
        "persisted": False,
    }


def apply_manual_periodicity_retirement(
    project: Project,
    preview: dict[str, Any],
) -> dict[str, Any]:
    """Apply an unchanged retirement preview as one caller-owned transaction.

    Routes must checkpoint once before calling this function.  A fresh preview
    is recomputed and its digest must match, preventing stale or hand-edited
    ownership lists from deleting records.
    """

    if not isinstance(preview, dict):
        raise PagePeriodicityError("retirement preview must be an object.")
    requested = preview.get("manual_periodicity_ids", [])
    current = preview_manual_periodicity_retirement(project, requested)
    if current["digest"] != preview.get("digest"):
        raise PagePeriodicityError(
            "Retirement preview is stale; review the generated-ID ownership again."
        )
    if current["conflicts"]:
        raise PagePeriodicityError(
            "Retirement has external references or ownership conflicts and cannot be applied."
        )
    if not current["would_change"]:
        return {
            **current,
            "persisted": False,
            "affected_workspace_ids": [],
        }
    class_ids = set(current["eligible"]["class_ids"])
    differential_ids = set(current["eligible"]["differential_ids"])
    proposition_ids = set(current["eligible"]["proposition_ids"])
    affected_workspaces: set[str] = set()
    for workspace in project.workspaces:
        before = (
            len(workspace.classes),
            len(workspace.differentials),
            len(workspace.propositions),
        )
        workspace.classes = [
            item for item in workspace.classes if item.id not in class_ids
        ]
        workspace.differentials = [
            item
            for item in workspace.differentials
            if item.id not in differential_ids
        ]
        workspace.propositions = [
            item
            for item in workspace.propositions
            if item.id not in proposition_ids
        ]
        workspace.differential_events = [
            item
            for item in workspace.differential_events
            if item.class_id not in class_ids
            and item.counterpart_class_id not in class_ids
            and item.differential_claim_id not in differential_ids
            and item.proposition_id not in proposition_ids
        ]
        after = (
            len(workspace.classes),
            len(workspace.differentials),
            len(workspace.propositions),
        )
        if before != after:
            affected_workspaces.add(workspace.id)
            sync_workspace_fates(workspace)
    for sector in project.grading_sectors:
        sector.class_ids = [
            item for item in sector.class_ids if item not in class_ids
        ]

    now = datetime.now(timezone.utc).isoformat()
    selected = set(current["manual_periodicity_ids"])
    for record in project.manual_periodicities:
        if record.id not in selected:
            continue
        if record.id in current["already_retired"]:
            continue
        record.storage_mode = "retired-compact"
        record_summary = current["records"][record.id]
        record.retirement_summary = {
            "retired_at": now,
            "digest": current["digest"],
            "counts": dict(record_summary["counts"]),
            "missing_counts": dict(record_summary["missing_counts"]),
            "policy": "exact-created-id-and-record-owner",
        }
        record.created_class_ids = []
        record.created_differential_ids = []
        record.created_proposition_ids = []
    return {
        **current,
        "persisted": True,
        "affected_workspace_ids": sorted(affected_workspaces),
    }


def _external_reference_conflicts(
    project: Project,
    *,
    selected_ids: set[str],
    class_ids: set[str],
    differential_ids: set[str],
    proposition_ids: set[str],
) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []

    def add(kind: str, object_id: str, target_id: str) -> None:
        conflicts.append(
            {
                "reason": "external-reference",
                "object_kind": kind,
                "object_id": object_id,
                "target_id": target_id,
            }
        )

    for workspace in project.workspaces:
        for node in workspace.classes:
            if node.id in class_ids:
                continue
            for target in (
                node.periodicity_anchor_class_id,
                node.manual_periodicity_anchor_class_id,
            ):
                if target in class_ids:
                    add("class", node.id, str(target))
        for differential in workspace.differentials:
            if differential.id in differential_ids:
                continue
            for target in (
                differential.source_id,
                differential.target_id,
                differential.anchor_differential_id,
                differential.proposition_id,
            ):
                if target in class_ids or target in differential_ids or target in proposition_ids:
                    add("differential", differential.id, str(target))
        for proposition in workspace.propositions:
            if proposition.id in proposition_ids:
                continue
            referenced = set(_string_values(proposition.conclusion))
            referenced.update(proposition.premise_ids)
            if proposition.supersedes_id:
                referenced.add(proposition.supersedes_id)
            for target in referenced & (
                class_ids | differential_ids | proposition_ids
            ):
                add("proposition", proposition.id, target)
    for record in project.manual_periodicities:
        if record.id in selected_ids:
            continue
        for target in (
            record.anchor_class_id,
            record.anchor_differential_id,
            *record.created_class_ids,
            *record.created_differential_ids,
            *record.created_proposition_ids,
        ):
            if target in class_ids or target in differential_ids or target in proposition_ids:
                add("manual-periodicity", record.id, target)
    for cycle in project.page_period_cycles:
        if cycle.cycle_class_id in class_ids:
            add("page-period-cycle", cycle.id, cycle.cycle_class_id)
    for product in project.cross_graded_products:
        for target in (product.left_class_id, product.right_class_id):
            if target in class_ids:
                add("cross-graded-product", product.id, target)
        if product.proposition_id in proposition_ids:
            add("cross-graded-product", product.id, product.proposition_id)
    for presentation in project.e2_presentations:
        for target in presentation.derived_class_ids.values():
            if target in class_ids:
                add("e2-presentation", presentation.id, target)
    for family in project.period_families:
        for target in (
            family.certificate_proposition_id,
            *family.supporting_proposition_ids,
        ):
            if target in proposition_ids:
                add("period-family", family.id, target)
    for rule in project.periodicity_rules:
        if rule.certificate_proposition_id in proposition_ids:
            add("periodicity-rule", rule.id, rule.certificate_proposition_id)
    for relation in project.representation_relations:
        if relation.certificate_proposition_id in proposition_ids:
            add(
                "representation-relation",
                relation.id,
                relation.certificate_proposition_id,
            )
    return conflicts


def _string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_values(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _string_values(item)


def _workspace(project: Project, workspace_id: str) -> Workspace:
    workspace = next(
        (item for item in project.workspaces if item.id == workspace_id),
        None,
    )
    if workspace is None:
        raise PagePeriodicityError(f"Unknown workspace {workspace_id!r}.")
    return workspace


def _cycle(project: Project, cycle_id: str) -> PagePeriodCycle:
    cycle = next(
        (item for item in project.page_period_cycles if item.id == cycle_id),
        None,
    )
    if cycle is None:
        raise PagePeriodicityError(f"Unknown page-period cycle {cycle_id!r}.")
    return cycle


def _grade(raw: Any) -> Grade:
    if not isinstance(raw, dict):
        raise PagePeriodicityError("grade must be an object.")
    representation = raw.get("representation", {})
    if not isinstance(representation, dict):
        raise PagePeriodicityError("grade.representation must be an object.")
    try:
        stem = raw.get("stem")
        filtration = raw.get("filtration")
        if isinstance(stem, bool) or isinstance(filtration, bool):
            raise TypeError
        if not isinstance(stem, int) or not isinstance(filtration, int):
            raise TypeError
        normalized = {}
        for key, value in representation.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError
            if value:
                normalized[str(key)] = value
    except (TypeError, ValueError) as error:
        raise PagePeriodicityError(
            "grade stem, filtration, and representation coefficients must be integers."
        ) from error
    return Grade(stem, filtration, normalized)


def _page(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        raise PagePeriodicityError(f"{field} must be an integer at least 2.")
    return value


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PagePeriodicityError(f"{field} must be a nonempty string.")
    return value.strip()


def _optional_string(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise PagePeriodicityError("identifier fields must be strings.")
    return value.strip()


def _unique_strings(values: Iterable[str], field: str) -> list[str]:
    if isinstance(values, (str, bytes)) or values is None:
        raise PagePeriodicityError(f"{field} must be a list of identifiers.")
    result: list[str] = []
    for raw in values:
        if not isinstance(raw, str) or not raw.strip():
            raise PagePeriodicityError(
                f"{field} must contain nonempty string identifiers."
            )
        value = raw.strip()
        if value not in result:
            result.append(value)
    if not result:
        raise PagePeriodicityError(f"{field} must not be empty.")
    return result


def _positive_translations(values: Iterable[int]) -> list[int]:
    if isinstance(values, (str, bytes)) or values is None:
        raise PagePeriodicityError("translations must be a list of positive integers.")
    result: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise PagePeriodicityError(
                "translations must contain positive integers."
            )
        if value > 4096:
            raise PagePeriodicityError("translation exceeds the limit 4096.")
        if value not in result:
            result.append(value)
    if not result:
        raise PagePeriodicityError("translations must not be empty.")
    return result
