"""Source-scoped materialization of explicitly certified periodic translates.

This module intentionally does not expand visual repeats.  A caller must select
an existing class (and, optionally, an accepted differential), a documented
periodicity rule, a permitted page, and one nonzero translate.  Preview is
read-only; materialization writes distinct records with their provenance.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from .fate import class_is_live_on_page, is_accepted
from .models import ClassNode, Differential, Grade, PeriodicityRule, Project, Proposition, Workspace, new_id


D8_RULE_ID = "q8-hfpss-integer-d8-horizontal-r3"
D8_RULE_SOURCE = (
    "DKLLW24, Proposition 4.1 (local PDF p. 25; journal p. 19): D^8 is invertible in "
    "bidegree (64,0); section 6.1.2 (local PDF p. 51; journal p. 40): non-E2 HFPSS pages are "
    "(64,0)-periodic by D^8."
)


class PeriodicityOperationError(ValueError):
    """Raised when an attempted periodicity operation is out of certified scope."""


def ensure_source_backed_q8_periodicity_rules(project: Project) -> Project:
    """Install exactly one D^8 rule for the established integer Q8 branch.

    The source also discusses a (20,4) g=kD^3 period with low-filtration
    exceptions.  That exception is not encoded as an automatic operation.
    """

    integer = next((item for item in project.workspaces if item.id == "ws_integer"), None)
    if integer is None:
        return project
    if any(item.id == D8_RULE_ID for item in project.periodicity_rules):
        return project
    project.periodicity_rules.append(PeriodicityRule(
        id=D8_RULE_ID,
        name="Q8 HFPSS D^8 horizontal translate (non-E2 pages)",
        workspace_id=integer.id,
        multiplier_expression="D^8",
        grade_shift=Grade(stem=64, filtration=0),
        valid_from_page=3,
        valid_to_page="infinity",
        spectral_sequence="hfpss",
        horizontal_only=True,
        certificate_proposition_id="prop_int_D8_period",
        period_family_id="period_integer_D8",
        status="established",
        scope=(
            "Integer-graded Q8 HFPSS only. Applies on E_r for r>=3; the cited chart statement "
            "does not authorize E2 copies."
        ),
        exclusions=[
            "No E2 propagation: the source specifies D-periodicity on E2 and D^8-periodicity on other pages.",
            "No automatic g=kD^3 propagation: section 6.1.2 excludes v1-local classes in low filtration.",
            "No propagation to other workspaces without a separately scoped rule.",
        ],
        source_ref=D8_RULE_SOURCE,
    ))
    return project


def periodicity_rule_to_dict(rule: PeriodicityRule) -> dict[str, Any]:
    return asdict(rule)


def preview_periodic_translate(project: Project, workspace: Workspace, raw: Mapping[str, Any]) -> dict[str, Any]:
    """Plan one verified D^8 translate without mutating the project."""

    rule, source, page, translation, differential = _parse_operation(project, workspace, raw)
    source_plan = _plan_class_copy(workspace, rule, source, translation, page)
    target_plan = None
    differential_plan = None
    if differential:
        target = _active_live_class(workspace, differential.target_id, page, role="differential target")
        target_plan = _plan_class_copy(workspace, rule, target, translation, page)
        differential_plan = _plan_differential_copy(
            workspace, rule, differential, source_plan, target_plan, translation,
        )
    return _serialize_plan(rule, page, translation, source_plan, target_plan, differential_plan)


def materialize_periodic_translate(project: Project, workspace: Workspace, raw: Mapping[str, Any]) -> dict[str, Any]:
    """Persist the exact records planned by ``preview_periodic_translate``.

    The operation is idempotent: an existing copy from the same rule, root, and
    translation is reused; any other class or differential in the same target
    slot is rejected as a conflict.
    """

    rule, source, page, translation, differential = _parse_operation(project, workspace, raw)
    source_plan = _plan_class_copy(workspace, rule, source, translation, page)
    target_plan = None
    differential_plan = None
    if differential:
        target = _active_live_class(workspace, differential.target_id, page, role="differential target")
        target_plan = _plan_class_copy(workspace, rule, target, translation, page)
        differential_plan = _plan_differential_copy(
            workspace, rule, differential, source_plan, target_plan, translation,
        )

    certificate = _certificate(workspace, rule)
    created_classes: list[ClassNode] = []
    created_propositions: list[Proposition] = []
    for class_plan in (source_plan, target_plan):
        if class_plan is None or class_plan["action"] == "reuse":
            continue
        node = _create_class_copy(workspace, rule, class_plan, page)
        class_plan["node"] = node
        created_classes.append(node)
        proposition = _class_copy_proposition(workspace, rule, class_plan, certificate, page)
        workspace.propositions.append(proposition)
        created_propositions.append(proposition)

    created_differential: Differential | None = None
    if differential_plan:
        if differential_plan["action"] == "create":
            created_differential, proposition = _create_differential_copy(
                workspace, rule, differential, source_plan, target_plan, translation, certificate,
            )
            workspace.differentials.append(created_differential)
            workspace.propositions.append(proposition)
            created_propositions.append(proposition)
        else:
            created_differential = differential_plan["existing"]

    return {
        "operation": _serialize_plan(rule, page, translation, source_plan, target_plan, differential_plan),
        "created_class_ids": [item.id for item in created_classes],
        "reused_class_ids": [
            plan["node"].id for plan in (source_plan, target_plan)
            if plan is not None and plan["action"] == "reuse"
        ],
        "created_differential_id": created_differential.id if created_differential and differential_plan and differential_plan["action"] == "create" else None,
        "reused_differential_id": created_differential.id if created_differential and differential_plan and differential_plan["action"] == "reuse" else None,
        "created_proposition_ids": [item.id for item in created_propositions],
    }


def _parse_operation(
    project: Project, workspace: Workspace, raw: Mapping[str, Any],
) -> tuple[PeriodicityRule, ClassNode, int, int, Differential | None]:
    rule_id = _required_string(raw, "rule_id")
    rule = next((item for item in project.periodicity_rules if item.id == rule_id), None)
    if rule is None:
        raise PeriodicityOperationError(f"Unknown periodicity rule {rule_id!r}.")
    if rule.workspace_id != workspace.id or workspace.spectral_sequence != rule.spectral_sequence:
        raise PeriodicityOperationError("This source-scoped rule does not apply to the selected workspace.")
    if rule.status != "established":
        raise PeriodicityOperationError("Only established source-backed periodicity rules can materialize copies.")
    if not rule.horizontal_only or rule.grade_shift.filtration != 0 or rule.grade_shift.representation:
        raise PeriodicityOperationError("This operation only supports certified horizontal integer-stem periodicity.")
    _certificate(workspace, rule)
    page = _integer(raw.get("page"), "page")
    if page < rule.valid_from_page or not _within_upper_page_bound(page, rule.valid_to_page):
        raise PeriodicityOperationError(
            f"Rule {rule.id!r} is certified only on pages E_{rule.valid_from_page} through E_{rule.valid_to_page}."
        )
    translation = _integer(raw.get("translation"), "translation")
    if translation == 0:
        raise PeriodicityOperationError("translation must be nonzero; the anchor is not a new periodic copy.")
    source = _active_live_class(workspace, _required_string(raw, "anchor_class_id"), page, role="anchor")
    if source.periodicity_rule_id and source.periodicity_rule_id != rule.id:
        raise PeriodicityOperationError("Composing periodicity rules is not automated; use an explicit manual claim instead.")

    differential = None
    differential_id = raw.get("differential_id")
    if differential_id is not None and differential_id != "":
        if not isinstance(differential_id, str):
            raise PeriodicityOperationError("differential_id must be a string when supplied.")
        differential = next((item for item in workspace.differentials if item.id == differential_id), None)
        if differential is None:
            raise PeriodicityOperationError(f"Unknown differential {differential_id!r}.")
        if differential.source_id != source.id or differential.page != page:
            raise PeriodicityOperationError(
                "A propagated differential must start at the selected anchor and lie on the selected page."
            )
        if not is_accepted(differential.status):
            raise PeriodicityOperationError(
                "Only an accepted source differential may be propagated; record under-review patterns manually."
            )
    return rule, source, page, translation, differential


def _plan_class_copy(
    workspace: Workspace, rule: PeriodicityRule, anchor: ClassNode, translation: int, page: int,
) -> dict[str, Any]:
    root_id = anchor.periodicity_anchor_class_id or anchor.id
    root = _active_class(workspace, root_id)
    prior_translation = anchor.periodicity_translation if anchor.periodicity_rule_id == rule.id else 0
    total_translation = prior_translation + translation
    if total_translation == 0:
        raise PeriodicityOperationError("This translation returns to the root class; no distinct copy would be created.")
    shift = Grade(
        stem=rule.grade_shift.stem * total_translation,
        filtration=rule.grade_shift.filtration * total_translation,
        representation={key: value * total_translation for key, value in rule.grade_shift.representation.items()},
    )
    grade = root.grade.shifted(shift)
    same_grade = [item for item in workspace.classes if not item.archived and item.grade == grade]
    matching = next((item for item in same_grade if (
        item.periodicity_rule_id == rule.id
        and item.periodicity_anchor_class_id == root.id
        and item.periodicity_translation == total_translation
    )), None)
    if matching:
        return {"action": "reuse", "node": matching, "root": root, "translation": total_translation, "grade": grade}
    if same_grade:
        labels = ", ".join(item.label for item in same_grade)
        raise PeriodicityOperationError(
            f"A different active class already occupies the translated cell {grade.stem},{grade.filtration}: {labels}."
        )
    return {
        "action": "create", "node": None, "root": root, "translation": total_translation,
        "grade": grade, "label": _periodic_label(root.label, rule.multiplier_expression, total_translation),
        "expression": _periodic_expression(root.expression or root.label, rule.multiplier_expression, total_translation),
    }


def _plan_differential_copy(
    workspace: Workspace,
    rule: PeriodicityRule,
    anchor: Differential,
    source_plan: dict[str, Any],
    target_plan: dict[str, Any],
    translation: int,
) -> dict[str, Any]:
    source_node = source_plan["node"]
    target_node = target_plan["node"]
    if source_node and target_node:
        existing = next((item for item in workspace.differentials if (
            item.source_id == source_node.id and item.target_id == target_node.id and item.page == anchor.page
        )), None)
        if existing:
            if existing.periodicity_rule_id == rule.id and existing.anchor_differential_id == anchor.id:
                return {"action": "reuse", "existing": existing}
            raise PeriodicityOperationError("A different differential already occupies the proposed translated endpoints.")
    return {"action": "create", "existing": None, "translation": translation}


def _create_class_copy(workspace: Workspace, rule: PeriodicityRule, plan: dict[str, Any], page: int) -> ClassNode:
    root = plan["root"]
    node = ClassNode(
        id=new_id("class"),
        label=plan["label"],
        expression=plan["expression"],
        grade=Grade(plan["grade"].stem, plan["grade"].filtration, dict(plan["grade"].representation)),
        page=page,
        state="unknown",
        notes=(
            f"Distinct source-backed {rule.multiplier_expression} periodic translate of {root.label}; "
            f"translation {plan['translation']}; certified on non-E2 pages only."
        ),
        coefficient_context_id=root.coefficient_context_id,
        convention_id=root.convention_id,
        sector_id=root.sector_id,
        periodicity_rule_id=rule.id,
        periodicity_anchor_class_id=root.id,
        periodicity_translation=plan["translation"],
    )
    workspace.classes.append(node)
    return node


def _class_copy_proposition(
    workspace: Workspace, rule: PeriodicityRule, plan: dict[str, Any], certificate: Proposition, page: int,
) -> Proposition:
    node = plan["node"]
    root = plan["root"]
    source_refs = _combined_sources(rule.source_ref, certificate)
    root_propositions = [
        item for item in workspace.propositions if item.conclusion.get("class_id") == root.id
    ]
    for item in root_propositions:
        source_refs = _combined_sources(*source_refs, item)
    return Proposition(
        id=new_id("prop"), kind="periodic-class", status="derived",
        statement=f"{node.label} is the D^8 translate {plan['translation']} of {root.label} on E_{page}.",
        conclusion={
            "class_id": node.id, "periodicity_rule_id": rule.id,
            "anchor_class_id": root.id, "translation": plan["translation"], "page": page,
        },
        premise_ids=[certificate.id, *[item.id for item in root_propositions]],
        rule="D8SourceBackedPeriodicity", confidence=0.98,
        notes=(
            "Materialized as a distinct persisted record from the D^8 rule; it is not a render-only repeat "
            "and is not asserted on E2."
        ),
        source_ref=rule.source_ref, source_refs=source_refs,
        convention_id=root.convention_id,
        hypotheses=[
            "The selected integer-graded Q8 HFPSS is within the source-scoped rule.",
            f"The chart page is E_{page}, hence non-E2.",
            "D^8 is the stated invertible (64,0) periodicity class.",
        ],
        verification_checks=["source-certificate", "workspace-scope", "non-E2-page", "horizontal-shift", "distinct-cell"],
    )


def _create_differential_copy(
    workspace: Workspace,
    rule: PeriodicityRule,
    anchor: Differential,
    source_plan: dict[str, Any],
    target_plan: dict[str, Any],
    translation: int,
    certificate: Proposition,
) -> tuple[Differential, Proposition]:
    source, target = source_plan["node"], target_plan["node"]
    anchor_prop = _find_proposition(workspace, anchor.proposition_id)
    source_refs = _combined_sources(rule.source_ref, certificate, anchor_prop)
    proposition = Proposition(
        id=new_id("prop"), kind="differential", status="derived",
        statement=f"D^8-periodic translate: d_{anchor.page}({source.label}) = {target.label}",
        conclusion={
            "source_id": source.id, "target_id": target.id, "page": anchor.page,
            "periodicity_rule_id": rule.id, "anchor_differential_id": anchor.id, "translation": translation,
        },
        premise_ids=[item for item in [certificate.id, anchor.proposition_id] if item],
        rule="D8PeriodicityLeibniz", confidence=0.97,
        notes="Derived from an accepted source differential using the certified D^8 permanent periodicity class.",
        source_ref=rule.source_ref, source_refs=source_refs,
        convention_id=source.convention_id,
        hypotheses=[
            "The source differential is accepted and lies on the selected non-E2 page.",
            "D^8 is an invertible permanent cycle in bidegree (64,0).",
            "The periodicity identification commutes with the spectral-sequence differential.",
        ],
        verification_checks=["source-certificate", "accepted-anchor-differential", "same-page", "horizontal-shift", "bidegree", "distinct-differential"],
    )
    differential = Differential(
        id=new_id("diff"), source_id=source.id, target_id=target.id, page=anchor.page,
        status="derived", proposition_id=proposition.id,
        period_family_id=rule.period_family_id or None,
        period_translation=[translation], anchor_differential_id=anchor.id,
        period_notes=(
            f"Distinct D^8 translate under {rule.id}; source-backed for non-E2 HFPSS pages."
        ),
        periodicity_rule_id=rule.id,
    )
    return differential, proposition


def _serialize_plan(
    rule: PeriodicityRule,
    page: int,
    translation: int,
    source_plan: dict[str, Any],
    target_plan: dict[str, Any] | None,
    differential_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "rule": periodicity_rule_to_dict(rule), "page": page, "translation": translation,
        "class_copies": [
            _serialize_class_plan(item) for item in (source_plan, target_plan) if item is not None
        ],
        "differential_copy": (
            {"action": differential_plan["action"], "id": differential_plan["existing"].id if differential_plan.get("existing") else None}
            if differential_plan else None
        ),
        "persisted": False,
        "limitation": (
            "Only this source-backed D^8 non-E2 horizontal rule is automatic. It does not authorize E2, g=kD^3, "
            "cross-workspace, or render-only propagation."
        ),
    }


def _serialize_class_plan(plan: dict[str, Any]) -> dict[str, Any]:
    node = plan["node"]
    return {
        "action": plan["action"], "id": node.id if node else None,
        "label": node.label if node else plan["label"],
        "expression": node.expression if node else plan["expression"],
        "grade": asdict(node.grade if node else plan["grade"]),
        "anchor_class_id": plan["root"].id, "translation": plan["translation"],
    }


def _certificate(workspace: Workspace, rule: PeriodicityRule) -> Proposition:
    certificate = _find_proposition(workspace, rule.certificate_proposition_id)
    if certificate is None or not is_accepted(certificate.status):
        raise PeriodicityOperationError("The periodicity rule has no accepted certificate proposition in this workspace.")
    return certificate


def _active_live_class(workspace: Workspace, class_id: str, page: int, *, role: str) -> ClassNode:
    node = _active_class(workspace, class_id)
    if node.page > page:
        raise PeriodicityOperationError(f"The {role} class first appears on E_{node.page}, not E_{page}.")
    if not class_is_live_on_page(workspace, node.id, page):
        raise PeriodicityOperationError(f"The {role} class is not live on E_{page}.")
    return node


def _active_class(workspace: Workspace, class_id: str) -> ClassNode:
    node = next((item for item in workspace.classes if item.id == class_id), None)
    if node is None:
        raise PeriodicityOperationError(f"Unknown class {class_id!r} in workspace {workspace.id!r}.")
    if node.archived:
        raise PeriodicityOperationError(f"Class {class_id!r} is archived and cannot be translated.")
    return node


def _find_proposition(workspace: Workspace, proposition_id: str) -> Proposition | None:
    return next((item for item in workspace.propositions if item.id == proposition_id), None)


def _combined_sources(*items: Any) -> list[str]:
    values: list[str] = []
    for item in items:
        if isinstance(item, Proposition):
            values.extend(item.source_refs)
            if item.source_ref:
                values.append(item.source_ref)
        elif isinstance(item, str) and item:
            values.append(item)
    return list(dict.fromkeys(values))


def _periodic_label(root: str, multiplier: str, translation: int) -> str:
    exponent = "" if translation == 1 else f"^{{{translation}}}"
    return f"({root}){multiplier}{exponent}"


def _periodic_expression(root: str, multiplier: str, translation: int) -> str:
    exponent = "" if translation == 1 else f"^{{{translation}}}"
    return f"({root})\\cdot {multiplier}{exponent}"


def _required_string(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PeriodicityOperationError(f"{key} must be a nonempty string.")
    return value.strip()


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PeriodicityOperationError(f"{name} must be an integer.")
    return value


def _within_upper_page_bound(page: int, upper: int | str) -> bool:
    return not isinstance(upper, int) or page <= upper
