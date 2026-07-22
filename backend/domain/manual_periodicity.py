"""Manual chart-periodicity previews and transactional materialization.

These operations deliberately create candidate drawing records.  They do not
assert that the supplied vector is a mathematically certified period.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from typing import Any

from .fate import class_is_live_on_page, workspace_sequence_kind
from .models import (
    ClassNode,
    Differential,
    Grade,
    ManualPeriodicity,
    ManualPeriodicityRule,
    Project,
    Proposition,
    Workspace,
    new_id,
)


class ManualPeriodicityError(ValueError):
    """Raised when a drawing-periodicity request is unsafe or inconsistent."""


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ManualPeriodicityError(f"{name} must be an integer.")
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ManualPeriodicityError(f"{name} must be an integer.") from error
    if isinstance(value, float) and not value.is_integer():
        raise ManualPeriodicityError(f"{name} must be an integer.")
    return result


def _normalize_request(workspace: Workspace, payload: dict[str, Any]) -> dict[str, Any]:
    classes = {item.id: item for item in workspace.classes}
    differentials = {item.id: item for item in workspace.differentials}
    anchor_id = str(payload.get("anchor_class_id", ""))
    anchor = classes.get(anchor_id)
    if anchor is None or anchor.archived:
        raise ManualPeriodicityError("Select a live, non-archived anchor class.")

    page = _integer(payload.get("page", workspace.page), "page")
    if page < 2 or not class_is_live_on_page(workspace, anchor.id, page):
        raise ManualPeriodicityError(f"The anchor class is not live on E{page}.")

    stem = _integer(payload.get("period_stem"), "period_stem")
    filtration = _integer(payload.get("period_filtration"), "period_filtration")
    if stem == 0 and filtration == 0:
        raise ManualPeriodicityError("The drawing period vector cannot be (0,0).")

    start = _integer(payload.get("translation_start", 1), "translation_start")
    end = _integer(payload.get("translation_end", 3), "translation_end")
    if start > end:
        raise ManualPeriodicityError("translation_start must not exceed translation_end.")
    translations = [value for value in range(start, end + 1) if value != 0]
    if not translations:
        raise ManualPeriodicityError("The translation range must contain at least one nonzero integer.")
    if len(translations) > 64 or min(translations) < -64 or max(translations) > 64:
        raise ManualPeriodicityError("A preview may contain at most 64 translations, each between -64 and 64.")

    include_cycles = bool(payload.get("include_cycles", True))
    include_differential = bool(payload.get("include_differential", False))
    if not include_cycles and not include_differential:
        raise ManualPeriodicityError("Choose cycles, a differential, or both.")

    differential_id = str(payload.get("differential_id", ""))
    differential = differentials.get(differential_id) if differential_id else None
    if include_differential:
        if differential is None:
            raise ManualPeriodicityError("Choose a current-page differential to copy.")
        if differential.page != page:
            raise ManualPeriodicityError(f"The selected differential is not drawn on E{page}.")
        if anchor.id not in {differential.source_id, differential.target_id}:
            raise ManualPeriodicityError("The selected differential must be incident to the anchor class.")
        if not all(class_is_live_on_page(workspace, class_id, page) for class_id in (differential.source_id, differential.target_id)):
            raise ManualPeriodicityError(f"Both differential endpoints must be live on E{page}.")

    cycle_label = str(payload.get("cycle_label", "P")).strip()
    if not cycle_label or len(cycle_label) > 120:
        raise ManualPeriodicityError("The cycle multiplier label must contain 1 to 120 characters.")

    fingerprint = "|".join([
        workspace.id, anchor.id, differential_id, str(page), str(stem), str(filtration), cycle_label,
    ])
    manual_id = f"manual-period-{sha256(fingerprint.encode('utf-8')).hexdigest()[:16]}"
    return {
        "anchor": anchor,
        "differential": differential,
        "page": page,
        "period": Grade(stem, filtration, {}),
        "translations": translations,
        "translation_start": start,
        "translation_end": end,
        "include_cycles": include_cycles,
        "include_differential": include_differential,
        "cycle_label": cycle_label,
        "manual_id": manual_id,
    }


def _copy_label(base: ClassNode, cycle_label: str, translation: int) -> str:
    factor = cycle_label if translation == 1 else f"{cycle_label}^{{{translation}}}"
    return f"{base.label}\\,{factor}"


def _copy_expression(base: ClassNode, cycle_label: str, translation: int) -> str:
    return f"({base.expression or base.label})*({cycle_label})^({translation})"


def _translated_grade(base: ClassNode, period: Grade, translation: int) -> Grade:
    return Grade(
        base.grade.stem + translation * period.stem,
        base.grade.filtration + translation * period.filtration,
        dict(base.grade.representation),
    )


def _existing_copy(workspace: Workspace, manual_id: str, base_id: str, translation: int) -> ClassNode | None:
    return next((item for item in workspace.classes if (
        item.manual_periodicity_id == manual_id
        and item.manual_periodicity_anchor_class_id == base_id
        and item.manual_periodicity_translation == translation
    )), None)


def preview_manual_periodicity(workspace: Workspace, payload: dict[str, Any]) -> dict[str, Any]:
    request_data = _normalize_request(workspace, payload)
    anchor = request_data["anchor"]
    differential = request_data["differential"]
    period = request_data["period"]
    translations = request_data["translations"]
    manual_id = request_data["manual_id"]
    by_id = {item.id: item for item in workspace.classes}

    base_nodes: list[ClassNode] = []
    if request_data["include_cycles"]:
        base_nodes.append(anchor)
    if request_data["include_differential"] and differential:
        for class_id in (differential.source_id, differential.target_id):
            node = by_id[class_id]
            if node.id not in {item.id for item in base_nodes}:
                base_nodes.append(node)

    cycle_copies: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    plans: dict[tuple[str, int], dict[str, Any]] = {}
    for base in base_nodes:
        for translation in translations:
            grade = _translated_grade(base, period, translation)
            if grade.filtration < 0 and workspace_sequence_kind(workspace) != "tate":
                skipped.append({
                    "kind": "cycle", "base_class_id": base.id, "translation": translation,
                    "reason": "negative filtration is outside this HFPSS canvas",
                })
                continue
            existing = _existing_copy(workspace, manual_id, base.id, translation)
            action = "create"
            existing_id = None
            if existing:
                action = "archived-conflict" if existing.archived else "reuse"
                existing_id = existing.id
            plan = {
                "kind": "cycle",
                "base_class_id": base.id,
                "base_label": base.label,
                "translation": translation,
                "label": _copy_label(base, request_data["cycle_label"], translation),
                "expression": _copy_expression(base, request_data["cycle_label"], translation),
                "grade": asdict(grade),
                "action": action,
                "class_id": existing_id,
                "required_for_differential": bool(differential and base.id in {differential.source_id, differential.target_id}),
            }
            cycle_copies.append(plan)
            plans[(base.id, translation)] = plan

    differential_copies: list[dict[str, Any]] = []
    if request_data["include_differential"] and differential:
        for translation in translations:
            source_plan = plans.get((differential.source_id, translation))
            target_plan = plans.get((differential.target_id, translation))
            if not source_plan or not target_plan:
                skipped.append({
                    "kind": "differential", "anchor_differential_id": differential.id,
                    "translation": translation, "reason": "a translated endpoint is outside the HFPSS canvas",
                })
                continue
            if "archived-conflict" in {source_plan["action"], target_plan["action"]}:
                differential_copies.append({
                    "kind": "differential", "anchor_differential_id": differential.id,
                    "translation": translation, "page": differential.page,
                    "source_plan": [differential.source_id, translation],
                    "target_plan": [differential.target_id, translation],
                    "action": "blocked-by-archived-endpoint", "differential_id": None,
                })
                continue
            existing = None
            if source_plan["class_id"] and target_plan["class_id"]:
                existing = next((item for item in workspace.differentials if (
                    item.manual_periodicity_id == manual_id
                    and item.anchor_differential_id == differential.id
                    and item.source_id == source_plan["class_id"]
                    and item.target_id == target_plan["class_id"]
                    and item.page == differential.page
                )), None)
            differential_copies.append({
                "kind": "differential", "anchor_differential_id": differential.id,
                "translation": translation, "page": differential.page,
                "source_plan": [differential.source_id, translation],
                "target_plan": [differential.target_id, translation],
                "action": "reuse" if existing else "create",
                "differential_id": existing.id if existing else None,
            })

    conflicts = [item for item in cycle_copies if item["action"] == "archived-conflict"]
    conflicts.extend(item for item in differential_copies if item["action"].startswith("blocked"))
    return {
        "operation": "manual-drawing-periodicity",
        "status": "manual-unverified",
        "warning": "Drawing preview only: this vector is not a certified spectral-sequence period.",
        "manual_periodicity_id": manual_id,
        "workspace_id": workspace.id,
        "page": request_data["page"],
        "anchor_class_id": anchor.id,
        "anchor_differential_id": differential.id if differential else "",
        "cycle_label": request_data["cycle_label"],
        "period_vector": asdict(period),
        "translations": translations,
        "include_cycles": request_data["include_cycles"],
        "include_differential": request_data["include_differential"],
        "cycle_copies": cycle_copies,
        "differential_copies": differential_copies,
        "skipped": skipped,
        "conflicts": conflicts,
        "summary": {
            "translations": len(translations),
            "cycles_to_create": sum(item["action"] == "create" for item in cycle_copies),
            "cycles_to_reuse": sum(item["action"] == "reuse" for item in cycle_copies),
            "differentials_to_create": sum(item["action"] == "create" for item in differential_copies),
            "differentials_to_reuse": sum(item["action"] == "reuse" for item in differential_copies),
            "skipped": len(skipped),
            "conflicts": len(conflicts),
        },
    }


def materialize_manual_periodicity(project: Project, workspace: Workspace, payload: dict[str, Any]) -> dict[str, Any]:
    preview = preview_manual_periodicity(workspace, payload)
    if preview["conflicts"]:
        raise ManualPeriodicityError(
            "A prior manual-period copy is archived. Undo its deletion or choose another vector/anchor before materializing."
        )

    request_data = _normalize_request(workspace, payload)
    manual_id = request_data["manual_id"]
    anchor = request_data["anchor"]
    base_differential = request_data["differential"]
    existing_record = next((item for item in project.manual_periodicities if item.id == manual_id), None)
    record = existing_record or ManualPeriodicity(
        id=manual_id,
        workspace_id=workspace.id,
        anchor_class_id=anchor.id,
        anchor_differential_id=base_differential.id if base_differential else "",
        cycle_label=request_data["cycle_label"],
        period_vector=request_data["period"],
        page=request_data["page"],
        translations=[],
        basis="Selected class and optional incident differential on the displayed page.",
        source_ref="Local manual drawing operation; no mathematical certificate supplied.",
        status="manual-unverified",
    )

    by_id = {item.id: item for item in workspace.classes}
    resolved: dict[tuple[str, int], ClassNode] = {}
    created_class_ids: list[str] = []
    created_proposition_ids: list[str] = []
    for plan in preview["cycle_copies"]:
        key = (plan["base_class_id"], plan["translation"])
        if plan["action"] == "reuse":
            resolved[key] = by_id[plan["class_id"]]
            continue
        base = by_id[plan["base_class_id"]]
        node = ClassNode(
            id=new_id("class"),
            label=plan["label"],
            expression=plan["expression"],
            grade=Grade(**plan["grade"]),
            page=request_data["page"],
            state="unknown",
            notes=(
                f"Manual drawing-period copy of {base.id} by translation {plan['translation']} "
                f"of ({request_data['period'].stem},{request_data['period'].filtration}); not certified."
            ),
            style={**base.style, "manual_periodicity": True},
            coefficient_context_id=base.coefficient_context_id,
            convention_id=base.convention_id,
            sector_id=base.sector_id,
            manual_periodicity_id=manual_id,
            manual_periodicity_anchor_class_id=base.id,
            manual_periodicity_translation=plan["translation"],
            manual_periodicity_exponents=[plan["translation"]],
        )
        workspace.classes.append(node)
        by_id[node.id] = node
        resolved[key] = node
        created_class_ids.append(node.id)
        proposition = Proposition(
            id=new_id("prop"),
            kind="manual-periodicity-drawing",
            statement=f"Draw {node.label} as a manual translation of {base.label}; no period theorem is asserted.",
            status="candidate",
            conclusion={
                "class_id": node.id, "anchor_class_id": base.id,
                "manual_periodicity_id": manual_id, "translation": plan["translation"],
            },
            rule="ManualDrawingPeriodicity",
            confidence=0.0,
            notes="Created from an explicitly user-entered drawing vector.",
            source_ref="Local manual drawing operation; no mathematical certificate supplied.",
            source_refs=["Local manual drawing operation; no mathematical certificate supplied."],
            convention_id=base.convention_id,
            hypotheses=["The entered vector is a drawing instruction only and remains unverified."],
        )
        workspace.propositions.append(proposition)
        created_proposition_ids.append(proposition.id)

    created_differential_ids: list[str] = []
    for plan in preview["differential_copies"]:
        if plan["action"] == "reuse":
            continue
        source = resolved[tuple(plan["source_plan"])]
        target = resolved[tuple(plan["target_plan"])]
        proposition = Proposition(
            id=new_id("prop"),
            kind="differential",
            statement=(
                f"Manual drawing candidate: d_{plan['page']}({source.label}) = {target.label}; "
                "translation does not certify nonzero behavior."
            ),
            status="candidate",
            conclusion={
                "source_id": source.id, "target_id": target.id, "page": plan["page"],
                "manual_periodicity_id": manual_id, "translation": plan["translation"],
            },
            rule="ManualDrawingPeriodicity",
            confidence=0.0,
            notes="Copied from a displayed arrow using a user-entered vector; requires independent review.",
            source_ref="Local manual drawing operation; no mathematical certificate supplied.",
            source_refs=["Local manual drawing operation; no mathematical certificate supplied."],
            convention_id=source.convention_id,
            hypotheses=["The base arrow and entered vector do not by themselves prove this differential."],
        )
        differential = Differential(
            id=new_id("diff"),
            source_id=source.id,
            target_id=target.id,
            page=plan["page"],
            status="candidate",
            label=f"d_{plan['page']} (manual periodic drawing)",
            proposition_id=proposition.id,
            anchor_differential_id=base_differential.id if base_differential else None,
            period_notes="Manual drawing-period copy; no certificate supplied.",
            unperiodic_reason="Not eligible for certified propagation until separately reviewed.",
            manual_periodicity_id=manual_id,
            manual_periodicity_translation=plan["translation"],
            manual_periodicity_exponents=[plan["translation"]],
        )
        workspace.propositions.append(proposition)
        workspace.differentials.append(differential)
        created_proposition_ids.append(proposition.id)
        created_differential_ids.append(differential.id)

    all_class_ids = [item["class_id"] for item in preview["cycle_copies"] if item["class_id"]]
    all_class_ids.extend(created_class_ids)
    all_differential_ids = [item["differential_id"] for item in preview["differential_copies"] if item["differential_id"]]
    all_differential_ids.extend(created_differential_ids)
    record.translations = sorted(set(record.translations + preview["translations"]))
    record.created_class_ids = list(dict.fromkeys(record.created_class_ids + all_class_ids))
    record.created_differential_ids = list(dict.fromkeys(record.created_differential_ids + all_differential_ids))
    record.created_proposition_ids = list(dict.fromkeys(record.created_proposition_ids + created_proposition_ids))
    if existing_record is None:
        project.manual_periodicities.append(record)

    return {
        "manual_periodicity": asdict(record),
        "created_class_ids": created_class_ids,
        "created_differential_ids": created_differential_ids,
        "created_proposition_ids": created_proposition_ids,
        "reused_class_count": preview["summary"]["cycles_to_reuse"],
        "reused_differential_count": preview["summary"]["differentials_to_reuse"],
        "skipped": preview["skipped"],
    }


# ---------------------------------------------------------------------------
# ver15.3-compatible batch drawing periodicity

LEGACY_TRANSLATION_LIMIT = 20


def _rule_payload(rule: ManualPeriodicityRule) -> dict[str, Any]:
    return {
        "id": rule.id, "name": rule.name,
        "p": rule.period_vector.stem, "q": rule.period_vector.filtration,
        "status": rule.status, "basis": rule.basis, "source_ref": rule.source_ref,
        "archived": rule.archived,
    }


def list_manual_rules(project: Project, workspace: Workspace, *, include_archived: bool = False) -> list[dict[str, Any]]:
    return [
        _rule_payload(item)
        for item in project.manual_periodicity_rules
        if item.workspace_id == workspace.id and (include_archived or not item.archived)
    ]


def prepare_manual_rule(project: Project, workspace: Workspace, payload: dict[str, Any]) -> ManualPeriodicityRule:
    """Validate a named drawing rule without changing project state.

    Routes call this before recording a history checkpoint.  Keeping this
    operation pure is important: a rejected ``POST`` must not manufacture an
    empty Undo entry.
    """
    if not isinstance(payload, dict):
        raise ManualPeriodicityError("A manual rule request must be an object.")
    name = str(payload.get("name", "")).strip()
    stem = _integer(payload.get("p"), "p")
    filtration = _integer(payload.get("q"), "q")
    if not name:
        raise ManualPeriodicityError("Rule must have a name.")
    if stem == 0 and filtration == 0:
        raise ManualPeriodicityError("Periodicity of (0,0) is not allowed.")
    basis = str(payload.get("basis", "Local manual drawing rule; no mathematical certificate supplied.")).strip()
    source_ref = str(payload.get("source_ref", "")).strip()
    if not basis:
        raise ManualPeriodicityError("A manual rule requires a nonempty basis describing why it is being drawn.")
    duplicate = next((item for item in project.manual_periodicity_rules if (
        item.workspace_id == workspace.id and not item.archived and item.name == name
        and item.period_vector == Grade(stem, filtration, {})
    )), None)
    if duplicate:
        raise ManualPeriodicityError("An active manual rule with this name and vector already exists.")
    return ManualPeriodicityRule(
        id=new_id("manual_rule"), workspace_id=workspace.id, name=name,
        period_vector=Grade(stem, filtration, {}), basis=basis, source_ref=source_ref,
        status="manual-unverified",
    )


def add_manual_rule(
    project: Project,
    workspace: Workspace,
    payload: dict[str, Any],
    *,
    prepared_rule: ManualPeriodicityRule | None = None,
) -> dict[str, Any]:
    """Append a rule which has already passed (or now passes) validation."""
    rule = prepared_rule or prepare_manual_rule(project, workspace, payload)
    if rule.workspace_id != workspace.id:
        raise ManualPeriodicityError("The prepared manual rule belongs to another workspace.")
    project.manual_periodicity_rules.append(rule)
    return _rule_payload(rule)


def delete_manual_rule(project: Project, workspace: Workspace, rule_id: str) -> dict[str, Any]:
    rule = next((item for item in project.manual_periodicity_rules if (
        item.id == rule_id and item.workspace_id == workspace.id
    )), None)
    if rule is None:
        raise ManualPeriodicityError("Unknown manual periodicity rule.")
    if not rule.archived:
        rule.archived = True
        rule.archived_reason = "Archived by local user action; existing manual copies remain auditable."
    return _rule_payload(rule)


def _location_key(grade: Grade) -> str:
    representation = json.dumps(grade.representation, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{grade.stem}:{grade.filtration}:{representation}"


def _rule_factor(rules: list[dict[str, Any]], exponents: list[int]) -> str:
    factors = []
    for rule, exponent in zip(rules, exponents):
        if exponent == 0:
            continue
        factors.append(rule["name"] if exponent == 1 else f"{rule['name']}^{{{exponent}}}")
    return "\\,".join(factors) or "1"


def _compound_translations(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Enumerate exponent vectors, without collapsing linearly dependent rules.

    Two named rules may produce the same total grade shift.  They remain
    distinct drawing orbits because their labels and algebraic expressions can
    carry different meanings.  Deduplicating merely by location loses dots.
    """
    states: list[tuple[int, int, list[int]]] = [(0, 0, [])]
    for rule in rules:
        next_states: list[tuple[int, int, list[int]]] = []
        for stem, filtration, exponents in states:
            for exponent in range(-LEGACY_TRANSLATION_LIMIT, LEGACY_TRANSLATION_LIMIT + 1):
                next_states.append((
                    stem + exponent * rule["p"],
                    filtration + exponent * rule["q"],
                    [*exponents, exponent],
                ))
                if len(next_states) > 25000:
                    raise ManualPeriodicityError(
                        "These rules generate more than 25,000 exponent vectors. Reduce the rule list before previewing."
                    )
        states = next_states
    return [
        {"stem": stem, "filtration": filtration, "exponents": exponents}
        for stem, filtration, exponents in states
        if stem != 0 or filtration != 0
    ]


def _active_classes(workspace: Workspace, page: int) -> list[ClassNode]:
    return sorted(
        [
            item for item in workspace.classes
            if not item.archived
            and not item.manual_periodicity_id
            and item.page <= page
            and class_is_live_on_page(workspace, item.id, page)
        ],
        key=lambda item: item.id,
    )


def _current_connections(workspace: Workspace, page: int, live_ids: set[str]) -> list[dict[str, Any]]:
    connections = [
        {
            "kind": "differential", "id": item.id, "source_id": item.source_id,
            "target_id": item.target_id, "page": item.page,
        }
        for item in workspace.differentials
        if item.page == page and item.source_id in live_ids and item.target_id in live_ids
    ]
    connections.extend({
        "kind": "relation", "id": item.id, "source_id": item.conclusion.get("source_id"),
        "target_id": item.conclusion.get("target_id"), "page": page,
    } for item in workspace.propositions if (
        item.kind == "relation"
        and int(item.conclusion.get("page", 2)) == page
        and item.conclusion.get("source_id") in live_ids
        and item.conclusion.get("target_id") in live_ids
    ))
    return connections


def _batch_id(
    workspace: Workspace, page: int, mode: str, rules: list[dict[str, Any]], scope: dict[str, Any] | None = None,
) -> str:
    source = json.dumps({
        "workspace": workspace.id, "page": page, "mode": mode,
        "rules": [{key: rule[key] for key in ("id", "name", "p", "q") if key in rule} for rule in rules],
        "scope": scope or {},
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"manual-period-{sha256(source.encode('utf-8')).hexdigest()[:16]}"


def _batch_builder(
    workspace: Workspace,
    page: int,
    mode: str,
    rules: list[dict[str, Any]],
    scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active = _active_classes(workspace, page)
    active_by_id = {item.id: item for item in active}
    manual_id = _batch_id(workspace, page, mode, rules, scope)
    plans_by_orbit: dict[str, dict[str, Any]] = {}
    cycle_plans: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    def ensure_cycle(base: ClassNode, shift: dict[str, Any]) -> dict[str, Any] | None:
        grade = Grade(
            base.grade.stem + shift["stem"],
            base.grade.filtration + shift["filtration"],
            dict(base.grade.representation),
        )
        if grade.filtration < 0 and workspace_sequence_kind(workspace) != "tate":
            return None
        exponents = list(shift["exponents"])
        orbit_key = json.dumps([manual_id, base.id, exponents], separators=(",", ":"))
        if orbit_key in plans_by_orbit:
            return plans_by_orbit[orbit_key]
        existing = next((item for item in workspace.classes if (
            item.manual_periodicity_id == manual_id
            and item.manual_periodicity_anchor_class_id == base.id
            and item.manual_periodicity_exponents == exponents
        )), None)
        factor = _rule_factor(rules, shift["exponents"])
        plan = {
            "kind": "cycle", "plan_key": orbit_key, "base_class_id": base.id,
            "label": f"{base.label}\\,{factor}",
            "expression": f"({base.expression or base.label})*({factor})",
            "grade": asdict(grade), "exponents": exponents,
            "action": "archived-conflict" if existing and existing.archived else "reuse" if existing else "create",
            "class_id": existing.id if existing else None,
        }
        plans_by_orbit[orbit_key] = plan
        cycle_plans.append(plan)
        return plan

    return {
        "active": active, "active_by_id": active_by_id,
        "manual_id": manual_id, "plans_by_orbit": plans_by_orbit,
        "cycles": cycle_plans, "endpoint_plans": {}, "skipped": skipped, "ensure_cycle": ensure_cycle,
    }


def _visible_classes_at(workspace: Workspace, page: int, grade: Grade) -> list[ClassNode]:
    """All visible dots at a grade, including deliberate manual copies."""
    key = _location_key(grade)
    return [
        item for item in workspace.classes
        if not item.archived and item.page <= page
        and class_is_live_on_page(workspace, item.id, page)
        and _location_key(item.grade) == key
    ]


def _existing_endpoint_plan(builder: dict[str, Any], node: ClassNode) -> dict[str, Any]:
    key = f"existing:{node.id}"
    existing = builder["endpoint_plans"].get(key)
    if existing:
        return existing
    plan = {
        "kind": "existing-endpoint", "plan_key": key, "base_class_id": node.id,
        "label": node.label, "expression": node.expression, "grade": asdict(node.grade),
        "exponents": [], "action": "reuse", "class_id": node.id,
    }
    builder["endpoint_plans"][key] = plan
    return plan


def _connection_action(
    workspace: Workspace,
    kind: str,
    source_id: str,
    target_id: str,
    page: int,
    manual_id: str,
    anchor_connection_id: str,
    exponents: list[int],
) -> tuple[str, str | None, str | None]:
    """Return create/reuse/conflict without folding unrelated arrows together."""
    if kind == "differential":
        candidates = [item for item in workspace.differentials if (
            item.source_id == source_id and item.target_id == target_id and item.page == page
        )]
        exact = next((item for item in candidates if (
            item.manual_periodicity_id == manual_id
            and item.anchor_differential_id == anchor_connection_id
            and item.manual_periodicity_exponents == exponents
        )), None)
    else:
        candidates = [item for item in workspace.propositions if (
            item.kind == "relation"
            and item.conclusion.get("source_id") == source_id
            and item.conclusion.get("target_id") == target_id
            and int(item.conclusion.get("page", 2)) == page
        )]
        exact = next((item for item in candidates if (
            item.conclusion.get("manual_periodicity_id") == manual_id
            and item.conclusion.get("anchor_connection_id") == anchor_connection_id
            and item.conclusion.get("manual_periodicity_exponents") == exponents
        )), None)
    if exact:
        return "reuse", exact.id, None
    if candidates:
        return (
            "conflict", None,
            "An unrelated existing connection has these endpoints; review it instead of merging drawing records.",
        )
    return "create", None, None


def _application_metadata(payload: dict[str, Any]) -> tuple[str, str]:
    basis = str(payload.get("basis", "Manual drawing operation; no mathematical certificate supplied.")).strip()
    source_ref = str(payload.get("source_ref", "Local manual drawing operation; no mathematical certificate supplied.")).strip()
    if not basis:
        raise ManualPeriodicityError("A manual drawing application requires a nonempty basis.")
    return basis, source_ref


def preview_all_rules_to_box(project: Project, workspace: Workspace, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ManualPeriodicityError("A box request must be an object.")
    page = _integer(payload.get("page", workspace.page), "page")
    if page < 2:
        raise ManualPeriodicityError("page must be at least 2.")
    rules = list_manual_rules(project, workspace)
    if not rules:
        raise ManualPeriodicityError("Define at least one manual periodicity rule first.")
    bounds = {
        "p_min": _integer(payload.get("p_min"), "p_min"),
        "p_max": _integer(payload.get("p_max"), "p_max"),
        "q_min": _integer(payload.get("q_min"), "q_min"),
        "q_max": _integer(payload.get("q_max"), "q_max"),
    }
    if bounds["p_min"] > bounds["p_max"] or bounds["q_min"] > bounds["q_max"]:
        raise ManualPeriodicityError("Invalid coordinate bounds.")
    if (bounds["p_max"] - bounds["p_min"] + 1) * (bounds["q_max"] - bounds["q_min"] + 1) > 50000:
        raise ManualPeriodicityError("The drawing box may contain at most 50,000 cells.")
    basis, source_ref = _application_metadata(payload)
    shifts = _compound_translations(rules)
    builder = _batch_builder(workspace, page, "box", rules, {"bounds": bounds, "limit": LEGACY_TRANSLATION_LIMIT})
    in_box = lambda grade: (
        bounds["p_min"] <= grade.stem <= bounds["p_max"]
        and bounds["q_min"] <= grade.filtration <= bounds["q_max"]
    )

    for base in builder["active"]:
        for shift in shifts:
            grade = Grade(
                base.grade.stem + shift["stem"], base.grade.filtration + shift["filtration"],
                dict(base.grade.representation),
            )
            if in_box(grade):
                builder["ensure_cycle"](base, shift)

    connections: list[dict[str, Any]] = []
    live_ids = set(builder["active_by_id"])
    for base_connection in _current_connections(workspace, page, live_ids):
        source_base = builder["active_by_id"][base_connection["source_id"]]
        target_base = builder["active_by_id"][base_connection["target_id"]]
        for shift in shifts:
            source_grade = Grade(
                source_base.grade.stem + shift["stem"], source_base.grade.filtration + shift["filtration"],
                dict(source_base.grade.representation),
            )
            target_grade = Grade(
                target_base.grade.stem + shift["stem"], target_base.grade.filtration + shift["filtration"],
                dict(target_base.grade.representation),
            )
            if not (in_box(source_grade) or in_box(target_grade)):
                continue
            source_plan = builder["ensure_cycle"](source_base, shift)
            target_plan = builder["ensure_cycle"](target_base, shift)
            if not source_plan or not target_plan:
                builder["skipped"].append({
                    "kind": base_connection["kind"], "base_connection_id": base_connection["id"],
                    "exponents": shift["exponents"], "reason": "translated endpoint has negative filtration",
                })
                continue
            action = "create"
            connection_id = None
            conflict_reason = None
            if source_plan["class_id"] and target_plan["class_id"]:
                action, connection_id, conflict_reason = _connection_action(
                    workspace, base_connection["kind"], source_plan["class_id"], target_plan["class_id"], page,
                    builder["manual_id"], base_connection["id"], list(shift["exponents"]),
                )
            connections.append({
                "kind": base_connection["kind"], "base_connection_id": base_connection["id"],
                "source_plan_key": source_plan["plan_key"], "target_plan_key": target_plan["plan_key"],
                "source_grade": source_plan["grade"], "target_grade": target_plan["grade"],
                "page": page, "exponents": list(shift["exponents"]),
                "action": action, "connection_id": connection_id, "conflict_reason": conflict_reason,
            })

    return _finish_batch_preview(
        workspace, page, "box", rules, builder, connections, bounds,
        "All named rules are compounded as manual drawing instructions; no period theorem is asserted.",
        basis, source_ref,
    )


def preview_differentials_only(project: Project, workspace: Workspace, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ManualPeriodicityError("A differential-only request must be an object.")
    page = _integer(payload.get("page", workspace.page), "page")
    if page < 2:
        raise ManualPeriodicityError("page must be at least 2.")
    stem = _integer(payload.get("p"), "p")
    filtration = _integer(payload.get("q"), "q")
    if stem == 0 and filtration == 0:
        raise ManualPeriodicityError("Periodicity of (0,0) is not allowed.")
    rules = [{"id": "differential-only-vector", "name": f"({stem},{filtration})", "p": stem, "q": filtration}]
    basis, source_ref = _application_metadata(payload)
    builder = _batch_builder(
        workspace, page, "differentials-only", rules,
        {"p": stem, "q": filtration, "limit": LEGACY_TRANSLATION_LIMIT},
    )
    live_ids = set(builder["active_by_id"])
    connections: list[dict[str, Any]] = []
    seen_connections: set[tuple[str, str, str, int]] = set()
    base_differentials = [item for item in workspace.differentials if (
        item.page == page and item.source_id in live_ids and item.target_id in live_ids
    )]
    for base in base_differentials:
        source_base = builder["active_by_id"][base.source_id]
        target_base = builder["active_by_id"][base.target_id]
        for translation in range(-LEGACY_TRANSLATION_LIMIT, LEGACY_TRANSLATION_LIMIT + 1):
            if translation == 0:
                continue
            shift = {"stem": translation * stem, "filtration": translation * filtration, "exponents": [translation]}
            source_grade = _translated_grade(source_base, Grade(stem, filtration, {}), translation)
            target_grade = _translated_grade(target_base, Grade(stem, filtration, {}), translation)
            existing_sources = _visible_classes_at(workspace, page, source_grade)
            existing_targets = _visible_classes_at(workspace, page, target_grade)
            if not existing_sources and not existing_targets:
                builder["skipped"].append({
                    "kind": "differential", "base_connection_id": base.id,
                    "translation": translation, "reason": "both translated endpoints are absent",
                })
                continue
            if len(existing_sources) > 1 or len(existing_targets) > 1:
                connections.append({
                    "kind": "differential", "base_connection_id": base.id,
                    "page": page, "translation": translation, "exponents": [translation],
                    "action": "conflict", "connection_id": None,
                    "conflict_reason": "A translated endpoint has multiple visible dots; choose an explicit anchor operation.",
                    "endpoint_case": "ambiguous-existing-endpoint",
                })
                continue
            source_plan = (_existing_endpoint_plan(builder, existing_sources[0]) if existing_sources
                           else builder["ensure_cycle"](source_base, shift))
            target_plan = (_existing_endpoint_plan(builder, existing_targets[0]) if existing_targets
                           else builder["ensure_cycle"](target_base, shift))
            if not source_plan or not target_plan:
                builder["skipped"].append({
                    "kind": "differential", "base_connection_id": base.id,
                    "translation": translation, "reason": "translated endpoint has negative filtration",
                })
                continue
            identity = (base.id, source_plan["plan_key"], target_plan["plan_key"], page)
            if identity in seen_connections:
                continue
            seen_connections.add(identity)
            source_id = source_plan.get("class_id")
            target_id = target_plan.get("class_id")
            action = "create"
            connection_id = None
            conflict_reason = None
            if source_id and target_id:
                action, connection_id, conflict_reason = _connection_action(
                    workspace, "differential", source_id, target_id, page,
                    builder["manual_id"], base.id, [translation],
                )
            connections.append({
                "kind": "differential", "base_connection_id": base.id,
                "source_plan_key": source_plan["plan_key"], "target_plan_key": target_plan["plan_key"],
                "source_grade": source_plan["grade"], "target_grade": target_plan["grade"],
                "page": page, "translation": translation, "exponents": [translation],
                "action": action, "connection_id": connection_id, "conflict_reason": conflict_reason,
                "endpoint_case": (
                    "both-exist" if existing_sources and existing_targets
                    else "create-missing-target" if existing_sources
                    else "create-missing-source"
                ),
            })
    return _finish_batch_preview(
        workspace, page, "differentials-only", rules, builder, connections, {},
        "Both endpoints absent is skipped; exactly one absent endpoint is created; both present are connected.",
        basis, source_ref,
    )


def _finish_batch_preview(
    workspace: Workspace,
    page: int,
    mode: str,
    rules: list[dict[str, Any]],
    builder: dict[str, Any],
    connections: list[dict[str, Any]],
    bounds: dict[str, int],
    behavior: str,
    basis: str,
    source_ref: str,
) -> dict[str, Any]:
    cycles = builder["cycles"]
    endpoint_plans = list(builder["endpoint_plans"].values())
    conflicts = [item for item in cycles if item["action"] == "archived-conflict"]
    conflicts.extend(item for item in connections if item["action"] == "conflict")
    return {
        "operation": "manual-drawing-periodicity", "mode": mode,
        "status": "manual-unverified", "workspace_id": workspace.id, "page": page,
        "manual_periodicity_id": builder["manual_id"], "rules": rules, "bounds": bounds,
        "basis": basis, "source_ref": source_ref,
        "warning": "Preview only. These are distinguishable drawing candidates, not certified periodicity.",
        "behavior": behavior, "cycle_copies": cycles, "existing_endpoint_copies": endpoint_plans,
        "connection_copies": connections, "conflicts": conflicts,
        "skipped": builder["skipped"],
        "summary": {
            "cycles_to_create": sum(item["action"] == "create" for item in cycles),
            "cycles_to_reuse": sum(item["action"] == "reuse" for item in cycles),
            "existing_endpoints": len(endpoint_plans),
            "differentials_to_create": sum(item["kind"] == "differential" and item["action"] == "create" for item in connections),
            "relations_to_create": sum(item["kind"] == "relation" and item["action"] == "create" for item in connections),
            "connections_to_reuse": sum(item["action"] == "reuse" for item in connections),
            "skipped": len(builder["skipped"]), "conflicts": len(conflicts),
        },
    }


def materialize_batch_preview(project: Project, workspace: Workspace, preview: dict[str, Any]) -> dict[str, Any]:
    if preview.get("workspace_id") != workspace.id:
        raise ManualPeriodicityError("The preview belongs to another workspace.")
    if preview.get("conflicts"):
        raise ManualPeriodicityError("Resolve preview conflicts before materializing manual drawing copies.")
    manual_id = preview["manual_periodicity_id"]
    by_id = {item.id: item for item in workspace.classes}
    resolved: dict[str, ClassNode] = {}
    created_classes: list[str] = []
    created_differentials: list[str] = []
    created_relations: list[str] = []
    created_propositions: list[str] = []
    for plan in preview.get("existing_endpoint_copies", []):
        node = by_id.get(plan.get("class_id"))
        if node is None or node.archived:
            raise ManualPeriodicityError("A preview endpoint no longer exists; preview again before materializing.")
        resolved[plan["plan_key"]] = node
    for plan in preview["cycle_copies"]:
        if plan["action"] == "reuse":
            node = by_id.get(plan["class_id"])
            if node is None or node.archived:
                raise ManualPeriodicityError("A preview copy no longer exists; preview again before materializing.")
            resolved[plan["plan_key"]] = node
            continue
        if plan["action"] != "create":
            raise ManualPeriodicityError("The preview contains a blocked class copy.")
        base = by_id[plan["base_class_id"]]
        exponents = list(plan.get("exponents", []))
        node = ClassNode(
            id=new_id("class"), label=plan["label"], expression=plan["expression"],
            grade=Grade(**plan["grade"]), page=preview["page"], state="unknown",
            notes="Manual ver15.3-style drawing-period copy; no mathematical certificate supplied.",
            style={**base.style, "manual_periodicity": True},
            coefficient_context_id=base.coefficient_context_id, convention_id=base.convention_id,
            sector_id=base.sector_id, manual_periodicity_id=manual_id,
            manual_periodicity_anchor_class_id=base.id,
            manual_periodicity_translation=exponents[0] if len(exponents) == 1 else 0,
            manual_periodicity_exponents=exponents,
        )
        workspace.classes.append(node)
        by_id[node.id] = node
        resolved[plan["plan_key"]] = node
        created_classes.append(node.id)
        proposition = Proposition(
            id=new_id("prop"), kind="manual-periodicity-drawing",
            statement=f"Draw {node.label} as a manual periodic copy; no period theorem is asserted.",
            status="candidate",
            conclusion={
                "class_id": node.id, "anchor_class_id": base.id,
                "manual_periodicity_id": manual_id,
                "manual_periodicity_exponents": exponents,
            },
            rule="ManualDrawingPeriodicity", confidence=0.0,
            notes="Generated by the ver15.3-compatible manual drawing tool.",
            source_ref="Local manual drawing operation; no mathematical certificate supplied.",
            source_refs=["Local manual drawing operation; no mathematical certificate supplied."],
            convention_id=base.convention_id,
        )
        workspace.propositions.append(proposition)
        created_propositions.append(proposition.id)

    for plan in preview["connection_copies"]:
        if plan["action"] == "reuse":
            continue
        if plan["action"] != "create":
            raise ManualPeriodicityError("The preview contains a conflicting connection.")
        source = resolved[plan["source_plan_key"]]
        target = resolved[plan["target_plan_key"]]
        exponents = list(plan.get("exponents", []))
        if plan["kind"] == "differential":
            proposition = Proposition(
                id=new_id("prop"), kind="differential",
                statement=f"Manual drawing candidate: d_{plan['page']}({source.label}) = {target.label}.",
                status="candidate",
                conclusion={
                    "source_id": source.id, "target_id": target.id, "page": plan["page"],
                    "manual_periodicity_id": manual_id, "anchor_connection_id": plan["base_connection_id"],
                    "manual_periodicity_exponents": exponents,
                },
                rule="ManualDrawingPeriodicity", confidence=0.0,
                notes="Copied as a drawing candidate; nonzero behavior is not certified.",
                source_ref="Local manual drawing operation; no mathematical certificate supplied.",
                source_refs=["Local manual drawing operation; no mathematical certificate supplied."],
                convention_id=source.convention_id,
            )
            differential = Differential(
                id=new_id("diff"), source_id=source.id, target_id=target.id, page=plan["page"],
                status="candidate", label=f"d_{plan['page']} (manual periodic drawing)",
                proposition_id=proposition.id, anchor_differential_id=plan["base_connection_id"],
                period_notes="Manual drawing-period copy; no certificate supplied.",
                unperiodic_reason="This manual copy is not a certified period propagation.",
                manual_periodicity_id=manual_id,
                manual_periodicity_translation=exponents[0] if len(exponents) == 1 else 0,
                manual_periodicity_exponents=exponents,
            )
            workspace.propositions.append(proposition)
            workspace.differentials.append(differential)
            created_propositions.append(proposition.id)
            created_differentials.append(differential.id)
        else:
            relation = Proposition(
                id=new_id("prop"), kind="relation",
                statement=f"Manual periodic drawing relation: {source.label} ~ {target.label}.",
                status="candidate",
                conclusion={
                    "source_id": source.id, "target_id": target.id, "page": plan["page"],
                    "manual_periodicity_id": manual_id, "anchor_connection_id": plan["base_connection_id"],
                    "manual_periodicity_exponents": exponents,
                },
                rule="ManualDrawingPeriodicity", confidence=0.0,
                notes="Copied as a drawing relation; no algebraic equality is certified.",
                source_ref="Local manual drawing operation; no mathematical certificate supplied.",
                source_refs=["Local manual drawing operation; no mathematical certificate supplied."],
                convention_id=source.convention_id,
            )
            workspace.propositions.append(relation)
            created_relations.append(relation.id)

    changed = bool(created_classes or created_differentials or created_relations)
    if changed:
        record = next((item for item in project.manual_periodicities if item.id == manual_id), None)
        if record is None:
            first_rule = preview["rules"][0]
            is_box = preview["mode"] == "box"
            record = ManualPeriodicity(
                id=manual_id, workspace_id=workspace.id, anchor_class_id="",
                mode=preview["mode"],
                rule_ids=[item["id"] for item in preview["rules"] if item["id"] != "differential-only-vector"],
                cycle_label=first_rule["name"],
                period_vector=Grade() if is_box else Grade(first_rule["p"], first_rule["q"], {}),
                page=preview["page"], status="manual-unverified",
                basis=preview["basis"], source_ref=preview["source_ref"],
                bounds=dict(preview.get("bounds", {})),
                translation_limit=LEGACY_TRANSLATION_LIMIT,
            )
            project.manual_periodicities.append(record)
        record.created_class_ids = list(dict.fromkeys(record.created_class_ids + created_classes))
        record.created_differential_ids = list(dict.fromkeys(record.created_differential_ids + created_differentials))
        record.created_proposition_ids = list(dict.fromkeys(record.created_proposition_ids + created_propositions))
    return {
        "changed": changed, "manual_periodicity_id": manual_id,
        "created_class_ids": created_classes, "created_differential_ids": created_differentials,
        "created_relation_proposition_ids": created_relations,
        "created_proposition_ids": created_propositions, "skipped": preview["skipped"],
    }
