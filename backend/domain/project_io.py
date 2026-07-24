"""Safe full-project and legacy sseq ver15.3 JSON import preparation."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any, Mapping

from .fate import is_accepted, sync_workspace_fates
from .migrations import migrate_project
from .models import (
    ClassNode,
    CoefficientContext,
    Differential,
    Grade,
    ManualPeriodicityRule,
    Project,
    Proposition,
    Workspace,
    project_from_dict,
    project_to_dict,
)
from .periods import fill_legacy_period_pairs


class ProjectImportValidationError(ValueError):
    """Raised when a candidate full-project replacement is unsafe to apply."""


def prepare_project_import(
    raw: Any,
    *,
    base_project: Project | None = None,
    legacy_source_name: str = "",
    legacy_workspace_name: str = "",
    legacy_target_workspace_id: str = "",
    legacy_target_page: int | None = None,
) -> tuple[Project, dict[str, Any]]:
    """Prepare either a full Studio replacement or an additive legacy canvas.

    Legacy conversion needs ``base_project`` because its only safe meaning is
    to append a new workspace.  The returned object is nevertheless a complete
    Studio project, so the ordinary reviewed Apply endpoint can use its stable
    digest and revision guard without a second mutation protocol.
    """

    if is_legacy_v153_canvas(raw):
        if base_project is None:
            raise ProjectImportValidationError(
                "Legacy sseq ver15.3 conversion requires the current Studio project so it can append a workspace."
            )
        return _prepare_legacy_v153_import(
            raw,
            base_project,
            source_name=legacy_source_name,
            workspace_name=legacy_workspace_name,
            target_workspace_id=legacy_target_workspace_id,
            target_page=legacy_target_page,
        )

    _validate_raw_envelope(raw)
    source_schema = raw.get("schema_version", 1)
    if isinstance(source_schema, bool) or not isinstance(source_schema, int) or source_schema < 1:
        raise ProjectImportValidationError("schema_version must be a positive integer when supplied.")
    from .models import SCHEMA_VERSION
    if source_schema > SCHEMA_VERSION:
        raise ProjectImportValidationError(
            f"This file uses future schema version {source_schema}; this Studio supports through {SCHEMA_VERSION}."
        )
    _validate_raw_claim_provenance(raw)
    try:
        candidate = project_from_dict(deepcopy(raw))
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise ProjectImportValidationError(f"Malformed Studio project JSON: {error}") from error

    # Fates and events are caches derived from the primary class/differential
    # records.  Never import a stale cache as mathematical evidence.
    for workspace in candidate.workspaces:
        workspace.fates = []
        workspace.differential_events = []
    fill_legacy_period_pairs(candidate)
    migrate_project(candidate)
    _validate_project_references(candidate)
    return candidate, {
        "source_schema_version": source_schema,
        "schema_version": candidate.schema_version,
        "migration_applied": source_schema != candidate.schema_version,
        "derived_caches_rebuilt": True,
        "summary": project_summary(candidate),
    }


def is_legacy_v153_canvas(raw: Any) -> bool:
    """Recognize the exact saveState shape without confusing Studio exports."""

    return (
        isinstance(raw, Mapping)
        and "workspaces" not in raw
        and "generators" in raw
        and "connections" in raw
    )


def _legacy_integer(value: Any, scope: str, *, default: int | None = None) -> int:
    if value is None and default is not None:
        return default
    if isinstance(value, bool):
        raise ProjectImportValidationError(f"{scope} must be an integer.")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise ProjectImportValidationError(f"{scope} must be an integer.")


def _legacy_offset(value: Any, scope: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ProjectImportValidationError(f"{scope} must be a finite number.")
    return float(value)


def _legacy_text(value: Any, scope: str, *, fallback: str = "") -> str:
    if value is None and fallback:
        return fallback
    if not isinstance(value, str):
        raise ProjectImportValidationError(f"{scope} must be a string.")
    result = value.strip()
    if not result:
        if fallback:
            return fallback
        raise ProjectImportValidationError(f"{scope} must be nonempty.")
    if len(result) > 5000:
        raise ProjectImportValidationError(f"{scope} is too long to import safely.")
    return result


def _mapped_legacy_id(workspace_id: str, kind: str, index: int, legacy_id: str) -> str:
    suffix = hashlib.sha256(legacy_id.encode("utf-8")).hexdigest()[:12]
    return f"{workspace_id}_{kind}_{index}_{suffix}"


def _unique_workspace_id(project: Project, fingerprint: str) -> str:
    stem = f"legacy_v153_{fingerprint[:12]}"
    known = {item.id for item in project.workspaces}
    candidate = stem
    suffix = 2
    while candidate in known:
        candidate = f"{stem}_{suffix}"
        suffix += 1
    return candidate


def _prepare_legacy_v153_import(
    raw: Mapping[str, Any],
    base_project: Project,
    *,
    source_name: str,
    workspace_name: str,
    target_workspace_id: str = "",
    target_page: int | None = None,
) -> tuple[Project, dict[str, Any]]:
    generators = raw.get("generators")
    connections = raw.get("connections")
    rules = raw.get("periodicityRules", [])
    if not isinstance(generators, list) or not isinstance(connections, list):
        raise ProjectImportValidationError("Legacy generators and connections must both be arrays.")
    if not isinstance(rules, list):
        raise ProjectImportValidationError("Legacy periodicityRules must be an array when supplied.")
    if not generators:
        raise ProjectImportValidationError("A legacy canvas must contain at least one generator.")
    if len(generators) > 100000 or len(connections) > 200000 or len(rules) > 1000:
        raise ProjectImportValidationError("The legacy canvas exceeds the safe conversion size limit.")

    try:
        canonical = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as error:
        raise ProjectImportValidationError(f"Legacy canvas is not valid JSON data: {error}") from error
    fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    source_name = _legacy_text(source_name, "legacy source_name", fallback="uploaded legacy sseq ver15.3 JSON")
    target_workspace = next(
        (item for item in base_project.workspaces if item.id == target_workspace_id),
        None,
    ) if target_workspace_id else None
    if target_workspace_id and target_workspace is None:
        raise ProjectImportValidationError("The selected legacy target workspace does not exist.")
    if target_page is not None and (isinstance(target_page, bool) or not isinstance(target_page, int) or target_page < 2):
        raise ProjectImportValidationError("The selected legacy target page must be an integer at least 2.")
    workspace_name = _legacy_text(
        workspace_name,
        "legacy workspace_name",
        fallback=target_workspace.name if target_workspace else f"Imported legacy canvas — {source_name}",
    )
    source_ref = f"Legacy sseq ver15.3 JSON import: {source_name}; candidate data requiring review."

    candidate = deepcopy(base_project)
    workspace_id = target_workspace.id if target_workspace else _unique_workspace_id(candidate, fingerprint)
    context_id = "legacy-v153-unclassified"
    if not any(item.id == context_id for item in candidate.coefficient_contexts):
        candidate.coefficient_contexts.append(CoefficientContext(
            id=context_id,
            residue_field="unspecified",
            coefficient_ring="unspecified",
            scalar_mode="formal",
            source_ref="Legacy chart import; coefficient context was not encoded in the file.",
        ))

    warnings: list[dict[str, Any]] = []
    known_top = {"generators", "connections", "periodicityRules"}
    unknown_top = sorted(str(key) for key in raw if key not in known_top)
    if unknown_top:
        warnings.append({
            "code": "unknown-top-level-fields",
            "message": "Unknown top-level fields were not interpreted.",
            "fields": unknown_top,
        })

    generator_fields = {"id", "p", "q", "name", "xOffset", "yOffset", "isBaseGenerator", "page"}
    unknown_generator_fields: set[str] = set()
    classes: list[ClassNode] = []
    propositions: list[Proposition] = []
    id_map: dict[str, str] = {}
    pages: list[int] = []
    stems: list[int] = []
    filtrations: list[int] = []
    for index, item in enumerate(generators):
        scope = f"generators[{index}]"
        if not isinstance(item, Mapping):
            raise ProjectImportValidationError(f"{scope} must be an object.")
        unknown_generator_fields.update(str(key) for key in item if key not in generator_fields)
        legacy_id = _legacy_text(item.get("id"), f"{scope}.id")
        if legacy_id in id_map:
            raise ProjectImportValidationError(f"Duplicate legacy generator id {legacy_id!r} is ambiguous.")
        stem = _legacy_integer(item.get("p"), f"{scope}.p")
        filtration = _legacy_integer(item.get("q"), f"{scope}.q")
        if filtration < 0:
            raise ProjectImportValidationError(
                f"{scope}.q is negative; this legacy upload path preserves upper-half-plane canvases only."
            )
        page = target_page if target_page is not None else _legacy_integer(item.get("page"), f"{scope}.page", default=2)
        if page < 2:
            raise ProjectImportValidationError(f"{scope}.page must be at least 2.")
        label = _legacy_text(item.get("name"), f"{scope}.name", fallback=f"unnamed_{index + 1}")
        x_offset = _legacy_offset(item.get("xOffset", 0), f"{scope}.xOffset")
        y_offset = _legacy_offset(item.get("yOffset", 0), f"{scope}.yOffset")
        is_base = item.get("isBaseGenerator", True)
        if not isinstance(is_base, bool):
            raise ProjectImportValidationError(f"{scope}.isBaseGenerator must be boolean.")
        class_id = _mapped_legacy_id(workspace_id, "class", index, legacy_id)
        id_map[legacy_id] = class_id
        note = (
            f"Imported from legacy generator {legacy_id}; original offsets "
            f"({x_offset:g},{y_offset:g}), isBaseGenerator={str(is_base).lower()}. "
            "Offsets are preserved as metadata; Studio adaptive packing controls display."
        )
        node = ClassNode(
            id=class_id,
            label=label,
            expression=label,
            grade=Grade(stem=stem, filtration=filtration),
            page=page,
            state="unknown",
            notes=note,
            style={
                "legacy_import": True,
                "module_pattern": "dot",
                "legacy_original_id": legacy_id,
                "legacy_x_offset": x_offset,
                "legacy_y_offset": y_offset,
                "legacy_is_base_generator": is_base,
            },
            coefficient_context_id=context_id,
            convention_id="legacy-v153-pq",
        )
        classes.append(node)
        propositions.append(Proposition(
            id=_mapped_legacy_id(workspace_id, "class_prop", index, legacy_id),
            kind="legacy-imported-class",
            statement=f"Legacy chart contains a dot labelled {label} at ({stem},{filtration}) from E{page}.",
            status="candidate",
            conclusion={"class_id": class_id, "legacy_generator_id": legacy_id},
            rule="LegacyV153Import",
            confidence=0.0,
            notes=note,
            source_ref=source_ref,
            source_refs=[source_ref],
            convention_id="legacy-v153-pq",
            hypotheses=["The legacy file does not certify the algebraic identity or coefficient context of this dot."],
        ))
        pages.append(page)
        stems.append(stem)
        filtrations.append(filtration)
    if unknown_generator_fields:
        warnings.append({
            "code": "unknown-generator-fields",
            "message": "Unknown generator fields were not interpreted.",
            "fields": sorted(unknown_generator_fields),
        })

    connection_fields = {"id", "fromId", "toId", "type", "isPeriodic", "page"}
    unknown_connection_fields: set[str] = set()
    connection_ids: set[str] = set()
    differentials: list[Differential] = []
    relation_count = 0
    anomalous_differential_ids: list[str] = []
    periodic_connection_count = 0
    classes_by_id = {item.id: item for item in classes}
    for index, item in enumerate(connections):
        scope = f"connections[{index}]"
        if not isinstance(item, Mapping):
            raise ProjectImportValidationError(f"{scope} must be an object.")
        unknown_connection_fields.update(str(key) for key in item if key not in connection_fields)
        legacy_id = _legacy_text(item.get("id"), f"{scope}.id")
        if legacy_id in connection_ids:
            raise ProjectImportValidationError(f"Duplicate legacy connection id {legacy_id!r} is ambiguous.")
        connection_ids.add(legacy_id)
        from_id = _legacy_text(item.get("fromId"), f"{scope}.fromId")
        to_id = _legacy_text(item.get("toId"), f"{scope}.toId")
        if from_id not in id_map or to_id not in id_map:
            raise ProjectImportValidationError(
                f"Legacy connection {legacy_id!r} has a dangling endpoint; no partial connection was imported."
            )
        connection_type = _legacy_text(item.get("type"), f"{scope}.type").lower()
        if connection_type not in {"differential", "relation"}:
            raise ProjectImportValidationError(
                f"Legacy connection {legacy_id!r} has unknown type {connection_type!r}."
            )
        page = target_page if target_page is not None else _legacy_integer(item.get("page"), f"{scope}.page", default=2)
        if page < 2:
            raise ProjectImportValidationError(f"{scope}.page must be at least 2.")
        is_periodic = item.get("isPeriodic", False)
        if not isinstance(is_periodic, bool):
            raise ProjectImportValidationError(f"{scope}.isPeriodic must be boolean.")
        if is_periodic:
            periodic_connection_count += 1
        source_id = id_map[from_id]
        target_id = id_map[to_id]
        source = classes_by_id[source_id]
        target = classes_by_id[target_id]
        connection_note = (
            f"Imported legacy {connection_type} {legacy_id}; isPeriodic={str(is_periodic).lower()}. "
            "The visual flag is metadata, not a periodicity theorem."
        )
        proposition_id = _mapped_legacy_id(workspace_id, "connection_prop", index, legacy_id)
        conclusion = {
            "source_id": source_id,
            "target_id": target_id,
            "page": page,
            "legacy_connection_id": legacy_id,
            "legacy_is_periodic": is_periodic,
        }
        if connection_type == "relation":
            relation_count += 1
            propositions.append(Proposition(
                id=proposition_id,
                kind="relation",
                statement=f"Legacy chart relation candidate: {source.label} — {target.label} on E{page}.",
                status="candidate",
                conclusion=conclusion,
                rule="LegacyV153Import",
                confidence=0.0,
                notes=connection_note,
                source_ref=source_ref,
                source_refs=[source_ref],
                convention_id="legacy-v153-pq",
                hypotheses=["A legacy visual relation does not by itself certify an algebraic equality."],
            ))
            continue

        is_valid_bidegree = (
            target.grade.stem == source.grade.stem - 1
            and target.grade.filtration == source.grade.filtration + page
            and target.grade.representation == source.grade.representation
        )
        if not is_valid_bidegree:
            anomalous_differential_ids.append(legacy_id)
            propositions.append(Proposition(
                id=proposition_id,
                kind="legacy-differential-anomaly",
                statement=(
                    f"Legacy line marked d_{page}: {source.label} — {target.label}; "
                    "its endpoints do not satisfy the Studio d_r bidegree convention."
                ),
                status="candidate",
                conclusion={**conclusion, "preserved_as_differential_record": False},
                rule="LegacyV153Import",
                confidence=0.0,
                notes=connection_note,
                source_ref=source_ref,
                source_refs=[source_ref],
                convention_id="legacy-v153-pq",
                hypotheses=["This anomalous visual line requires manual classification before it can become a differential."],
            ))
            continue

        propositions.append(Proposition(
            id=proposition_id,
            kind="differential",
            statement=f"Legacy chart differential candidate: d_{page}({source.label}) = {target.label}.",
            status="candidate",
            conclusion=conclusion,
            rule="LegacyV153Import",
            confidence=0.0,
            notes=connection_note,
            source_ref=source_ref,
            source_refs=[source_ref],
            convention_id="legacy-v153-pq",
            hypotheses=["The legacy arrow does not certify that this differential is nonzero or accepted."],
        ))
        differentials.append(Differential(
            id=_mapped_legacy_id(workspace_id, "diff", index, legacy_id),
            source_id=source_id,
            target_id=target_id,
            page=page,
            status="candidate",
            label=f"d_{page} (legacy candidate)",
            proposition_id=proposition_id,
            period_notes="Legacy isPeriodic flag retained only in the linked candidate proposition.",
            unperiodic_reason="No source-backed period certificate was encoded in the legacy file.",
        ))
    if unknown_connection_fields:
        warnings.append({
            "code": "unknown-connection-fields",
            "message": "Unknown connection fields were not interpreted.",
            "fields": sorted(unknown_connection_fields),
        })
    if anomalous_differential_ids:
        warnings.append({
            "code": "differential-bidegree-anomalies",
            "message": (
                "Legacy lines marked differential but violating the Studio d_r bidegree convention were retained "
                "as candidate anomaly propositions, not Differential records."
            ),
            "count": len(anomalous_differential_ids),
            "legacy_connection_ids": anomalous_differential_ids[:20],
        })

    rule_fields = {"id", "name", "p", "q"}
    unknown_rule_fields: set[str] = set()
    created_rule_count = 0
    skipped_zero_rules: list[str] = []
    for index, item in enumerate(rules):
        scope = f"periodicityRules[{index}]"
        if not isinstance(item, Mapping):
            raise ProjectImportValidationError(f"{scope} must be an object.")
        unknown_rule_fields.update(str(key) for key in item if key not in rule_fields)
        legacy_id = _legacy_text(item.get("id"), f"{scope}.id")
        name = _legacy_text(item.get("name"), f"{scope}.name", fallback=f"legacy period {index + 1}")
        stem = _legacy_integer(item.get("p"), f"{scope}.p")
        filtration = _legacy_integer(item.get("q"), f"{scope}.q")
        if stem == 0 and filtration == 0:
            skipped_zero_rules.append(legacy_id)
            continue
        candidate.manual_periodicity_rules.append(ManualPeriodicityRule(
            id=_mapped_legacy_id(workspace_id, "manual_rule", index, legacy_id),
            workspace_id=workspace_id,
            name=name,
            period_vector=Grade(stem=stem, filtration=filtration),
            basis="Imported legacy drawing-period vector; no mathematical certificate was encoded.",
            source_ref=source_ref,
            status="manual-unverified",
        ))
        created_rule_count += 1
    if skipped_zero_rules:
        warnings.append({
            "code": "zero-period-rules-skipped",
            "message": "Legacy (0,0) periodicity rules cannot become canonical manual rules and were skipped.",
            "legacy_rule_ids": skipped_zero_rules[:20],
            "count": len(skipped_zero_rules),
        })
    if unknown_rule_fields:
        warnings.append({
            "code": "unknown-periodicity-rule-fields",
            "message": "Unknown periodicity-rule fields were not interpreted.",
            "fields": sorted(unknown_rule_fields),
        })

    workspace = Workspace(
        id=workspace_id,
        name=workspace_name,
        group="unclassified legacy import",
        theory="unspecified",
        characteristic=2,
        grading_label="legacy p/q mapped to stem/filtration; representation component unspecified",
        spectral_sequence="legacy-unclassified",
        page=target_page or 2,
        representation_basis=[],
        classes=classes,
        differentials=differentials,
        propositions=propositions,
        summary=(
            "Additive import from sseq ver15.3 JSON. Every dot remains distinct; connections and period vectors "
            "are review candidates, not established mathematics."
        ),
    )
    workspace.settings.update({
        "page_limit": max(25, *(pages or [2])),
        "grid": {
            "stem_min": min(stems) if stems else 0,
            "stem_max": max(stems) if stems else 0,
            "filtration_min": 0,
            "filtration_max": max(filtrations) if filtrations else 0,
        },
        "legacy_import": {
            "format": "sseq-ver15.3",
            "source_name": source_name,
            "sha256": fingerprint,
            "p_q_mapping": "p -> stem, q -> filtration",
            "offset_policy": "preserved in class style/notes; adaptive packing renders the cell",
            "mathematical_status": "candidate/manual-unverified",
        },
    })
    operation = "append-workspace"
    if target_workspace is not None:
        operation = "merge-current-page"
        replaced_page = target_page or target_workspace.page
        imported_class_ids = {item.id for item in classes}
        imported_differential_ids = {item.id for item in differentials}
        imported_proposition_ids = {item.id for item in propositions}
        preserved_classes = [
            item for item in target_workspace.classes if item.id not in imported_class_ids
        ]
        preserved_differentials = [
            item for item in target_workspace.differentials
            if item.id not in imported_differential_ids
        ]
        preserved_propositions = [
            item for item in target_workspace.propositions
            if item.id not in imported_proposition_ids
        ]
        workspace.group = target_workspace.group
        workspace.theory = target_workspace.theory
        workspace.characteristic = target_workspace.characteristic
        workspace.grading_label = target_workspace.grading_label
        workspace.spectral_sequence = target_workspace.spectral_sequence
        workspace.representation_basis = list(target_workspace.representation_basis)
        workspace.summary = target_workspace.summary
        workspace.settings = deepcopy(target_workspace.settings)
        workspace.settings["legacy_import"] = {
            "format": "sseq-ver15.3",
            "source_name": source_name,
            "sha256": fingerprint,
            "target_page": replaced_page,
            "operation": operation,
            "p_q_mapping": "p -> stem, q -> filtration",
            "offset_policy": "preserved in class style/notes; adaptive packing renders the cell",
            "mathematical_status": "candidate/manual-unverified",
        }
        workspace.classes = preserved_classes + classes
        workspace.differentials = preserved_differentials + differentials
        workspace.propositions = preserved_propositions + propositions
        candidate.workspaces[candidate.workspaces.index(next(
            item for item in candidate.workspaces if item.id == target_workspace.id
        ))] = workspace
        # The conversion loop added the new imported rules to the deep-copied
        # project. Replace only prior rules from a legacy JSON import; retain
        # source-backed and user-entered rules for this workspace.
        imported_rules = [
            item for item in candidate.manual_periodicity_rules
            if item.workspace_id == workspace_id and item.source_ref == source_ref
        ]
        nonlegacy_rules = [
            item for item in base_project.manual_periodicity_rules
            if not (
                item.workspace_id == workspace_id
                and item.source_ref.startswith("Legacy sseq ver15.3 JSON import:")
            )
        ]
        candidate.manual_periodicity_rules = nonlegacy_rules + imported_rules
    else:
        candidate.workspaces.append(workspace)
    sync_workspace_fates(workspace)
    _validate_project_references(candidate)
    return candidate, {
        "format": "legacy-sseq-ver15.3",
        "operation": operation,
        "imported_workspace_id": workspace_id,
        "workspace_id": workspace_id,
        "workspace_name": workspace_name,
        "target_page": target_page,
        "source_name": source_name,
        "schema_version": candidate.schema_version,
        "migration_applied": True,
        "derived_caches_rebuilt": True,
        "warnings": warnings,
        "legacy_summary": {
            "generators_received": len(generators),
            "classes_created": len(classes),
            "connections_received": len(connections),
            "connection_propositions_created": len(connections),
            "relations_created": relation_count,
            "differentials_created": len(differentials),
            "differential_anomalies": len(anomalous_differential_ids),
            "periodic_visual_connections": periodic_connection_count,
            "periodicity_rules_received": len(rules),
            "manual_periodicity_rules_created": created_rule_count,
        },
        "summary": project_summary(candidate),
    }


def project_summary(project: Project) -> dict[str, int]:
    return {
        "workspaces": len(project.workspaces),
        "classes": sum(len(item.classes) for item in project.workspaces),
        "differentials": sum(len(item.differentials) for item in project.workspaces),
        "propositions": sum(len(item.propositions) for item in project.workspaces),
        "comparisons": len(project.comparisons),
        "periodicity_rules": len(project.periodicity_rules),
        "manual_periodicities": len(project.manual_periodicities),
        "manual_periodicity_rules": len(project.manual_periodicity_rules),
    }


def _validate_raw_envelope(raw: Any) -> None:
    if not isinstance(raw, Mapping):
        raise ProjectImportValidationError("A Studio import must be a JSON object.")
    if "workspaces" not in raw and {"generators", "connections"}.issubset(raw):
        raise ProjectImportValidationError(
            "This is a legacy sseq ver15.3 canvas file (generators/connections), not a full HFPSS Studio project. "
            "It lacks workspace, grading, and provenance semantics and cannot be imported automatically."
        )
    for key in ("id", "name"):
        if not isinstance(raw.get(key), str) or not raw[key].strip():
            raise ProjectImportValidationError(f"Full Studio project JSON requires a nonempty top-level {key!r}.")
    if not isinstance(raw.get("workspaces"), list) or not raw["workspaces"]:
        raise ProjectImportValidationError("Full Studio project JSON requires a nonempty workspaces array.")
    _require_list_fields(raw, "project", (
        "workspaces", "comparisons", "coefficient_contexts", "symbol_definitions", "period_families",
        "grading_sectors", "representation_relations", "cross_graded_products", "c3_actions",
        "e2_presentations", "periodicity_rules", "manual_periodicities", "manual_periodicity_rules",
    ))
    for index, workspace in enumerate(raw["workspaces"]):
        if not isinstance(workspace, Mapping):
            raise ProjectImportValidationError(f"workspaces[{index}] must be an object.")
        for key in ("id", "name"):
            if not isinstance(workspace.get(key), str) or not workspace[key].strip():
                raise ProjectImportValidationError(f"workspaces[{index}] requires a nonempty {key!r}.")
        _require_list_fields(workspace, f"workspaces[{index}]", (
            "classes", "differentials", "differential_events", "fates", "propositions",
        ))
        for field in ("classes", "differentials", "propositions"):
            for item_index, item in enumerate(workspace.get(field, [])):
                if not isinstance(item, Mapping):
                    raise ProjectImportValidationError(f"workspaces[{index}].{field}[{item_index}] must be an object.")


def _require_list_fields(raw: Mapping[str, Any], scope: str, keys: tuple[str, ...]) -> None:
    for key in keys:
        if key in raw and not isinstance(raw[key], list):
            raise ProjectImportValidationError(f"{scope}.{key} must be an array when supplied.")


def _validate_raw_claim_provenance(raw: Mapping[str, Any]) -> None:
    """Reject uncited imported assertions before migration can synthesize caches."""

    accepted_statuses = {"derived", "reviewed", "established", "proven"}
    for workspace in raw["workspaces"]:
        propositions = workspace.get("propositions", [])
        by_endpoint = {}
        for item in propositions:
            if not isinstance(item, Mapping) or item.get("kind") != "differential":
                continue
            conclusion = item.get("conclusion")
            if not isinstance(conclusion, Mapping):
                continue
            by_endpoint[(conclusion.get("source_id"), conclusion.get("target_id"), conclusion.get("page"))] = item
        for item in propositions:
            if not isinstance(item, Mapping) or item.get("status") not in accepted_statuses:
                continue
            if not _has_source_locator(item):
                raise ProjectImportValidationError(
                    f"Accepted imported proposition {item.get('id', '<unnamed>')!r} requires a source locator "
                    "(source_ref or source_refs)."
                )
        for differential in workspace.get("differentials", []):
            if not isinstance(differential, Mapping) or differential.get("status") not in accepted_statuses:
                continue
            endpoint = (differential.get("source_id"), differential.get("target_id"), differential.get("page"))
            proposition = by_endpoint.get(endpoint)
            if proposition is None or not _has_source_locator(proposition):
                raise ProjectImportValidationError(
                    "An accepted imported differential requires a matching cited differential proposition; "
                    "the importer will not promote a bare arrow."
                )


def _has_source_locator(proposition: Mapping[str, Any]) -> bool:
    if isinstance(proposition.get("source_ref"), str) and proposition["source_ref"].strip():
        return True
    refs = proposition.get("source_refs", [])
    return isinstance(refs, list) and any(isinstance(item, str) and item.strip() for item in refs)


def _validate_project_references(project: Project) -> None:
    _unique((item.id for item in project.workspaces), "workspace")
    workspace_ids = {item.id for item in project.workspaces}
    all_proposition_ids: list[str] = []
    all_differential_ids: list[str] = []
    for workspace in project.workspaces:
        _unique((item.id for item in workspace.classes), f"class in workspace {workspace.id}")
        _unique((item.id for item in workspace.propositions), f"proposition in workspace {workspace.id}")
        _unique((item.id for item in workspace.differentials), f"differential in workspace {workspace.id}")
        class_ids = {item.id for item in workspace.classes}
        proposition_ids = {item.id for item in workspace.propositions}
        all_proposition_ids.extend(proposition_ids)
        all_differential_ids.extend(item.id for item in workspace.differentials)
        for node in workspace.classes:
            _validate_grade(node.grade, f"class {node.id}")
            if not isinstance(node.page, int) or node.page < 2:
                raise ProjectImportValidationError(f"Class {node.id!r} must first appear on an integer page at least 2.")
            if workspace.spectral_sequence != "tate" and node.grade.filtration < 0:
                raise ProjectImportValidationError(f"HFPSS class {node.id!r} cannot have negative filtration.")
        for differential in workspace.differentials:
            if differential.source_id not in class_ids or differential.target_id not in class_ids:
                raise ProjectImportValidationError(f"Differential {differential.id!r} has an endpoint absent from its workspace.")
            source = next(item for item in workspace.classes if item.id == differential.source_id)
            target = next(item for item in workspace.classes if item.id == differential.target_id)
            if not isinstance(differential.page, int) or differential.page < 2:
                raise ProjectImportValidationError(f"Differential {differential.id!r} has an invalid page.")
            if (
                target.grade.stem != source.grade.stem - 1
                or target.grade.filtration != source.grade.filtration + differential.page
                or target.grade.representation != source.grade.representation
            ):
                raise ProjectImportValidationError(f"Differential {differential.id!r} violates the Studio d_r bidegree convention.")
            if differential.proposition_id and differential.proposition_id not in proposition_ids:
                raise ProjectImportValidationError(f"Differential {differential.id!r} refers to a missing local proposition.")
        for proposition in workspace.propositions:
            for key in ("class_id", "source_id", "target_id", "anchor_class_id"):
                value = proposition.conclusion.get(key)
                if value and value not in class_ids:
                    raise ProjectImportValidationError(
                        f"Proposition {proposition.id!r} refers to missing class {value!r} through {key}."
                    )
            if is_accepted(proposition.status) and not (proposition.source_ref or proposition.source_refs):
                raise ProjectImportValidationError(f"Accepted proposition {proposition.id!r} has no source locator.")
        for event in workspace.differential_events:
            if event.class_id not in class_ids:
                raise ProjectImportValidationError(f"Differential event {event.id!r} refers to a missing class.")
        for fate in workspace.fates:
            if fate.class_id not in class_ids:
                raise ProjectImportValidationError(f"Class fate refers to missing class {fate.class_id!r}.")

    _unique(all_proposition_ids, "project-wide proposition")
    _unique(all_differential_ids, "project-wide differential")
    all_proposition_id_set = set(all_proposition_ids)
    manual_ids = [item.id for item in project.manual_periodicities]
    _unique(manual_ids, "manual periodicity")
    manual_by_id = {item.id: item for item in project.manual_periodicities}
    manual_rule_ids = [item.id for item in project.manual_periodicity_rules]
    _unique(manual_rule_ids, "manual periodicity rule")
    manual_rules_by_id = {item.id: item for item in project.manual_periodicity_rules}
    workspaces_by_id = {item.id: item for item in project.workspaces}
    for rule in project.manual_periodicity_rules:
        if rule.workspace_id not in workspace_ids:
            raise ProjectImportValidationError(f"Manual periodicity rule {rule.id!r} refers to a missing workspace.")
        if rule.status != "manual-unverified":
            raise ProjectImportValidationError(f"Manual periodicity rule {rule.id!r} must remain manual-unverified.")
        if not rule.name.strip() or not rule.basis.strip():
            raise ProjectImportValidationError(f"Manual periodicity rule {rule.id!r} requires a name and manual basis.")
        _validate_nonzero_grade(rule.period_vector, f"manual periodicity rule {rule.id}")
    for manual in project.manual_periodicities:
        if manual.workspace_id not in workspace_ids:
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} refers to a missing workspace.")
        workspace = workspaces_by_id[manual.workspace_id]
        class_ids = {item.id for item in workspace.classes}
        differential_ids = {item.id for item in workspace.differentials}
        if manual.status != "manual-unverified" or manual.mode not in {"anchor", "box", "differentials-only"}:
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} has an invalid status or mode.")
        if not isinstance(manual.page, int) or manual.page < 2 or not manual.basis.strip():
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} requires an E2+ page and manual basis.")
        if manual.mode == "anchor" and manual.anchor_class_id not in class_ids:
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} has a missing anchor class.")
        if manual.anchor_differential_id and manual.anchor_differential_id not in differential_ids:
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} has a missing anchor differential.")
        if any(rule_id not in manual_rules_by_id for rule_id in manual.rule_ids):
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} refers to a missing manual rule.")
        if any(manual_rules_by_id[rule_id].workspace_id != manual.workspace_id for rule_id in manual.rule_ids):
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} refers to a rule in another workspace.")
        if manual.mode == "box" and not manual.rule_ids:
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} requires at least one named rule for box mode.")
        if manual.mode != "box":
            _validate_nonzero_grade(manual.period_vector, f"manual periodicity {manual.id}")
        if isinstance(manual.translation_limit, bool) or not isinstance(manual.translation_limit, int) or manual.translation_limit < 0:
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} has an invalid translation limit.")
        if manual.mode == "anchor" and (not manual.translations or any(
            isinstance(value, bool) or not isinstance(value, int) or value == 0 for value in manual.translations
        )):
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} has invalid translations.")
        if any(item not in class_ids for item in manual.created_class_ids) or any(item not in differential_ids for item in manual.created_differential_ids):
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} refers to a missing generated copy.")
        if any(item not in all_proposition_id_set for item in manual.created_proposition_ids):
            raise ProjectImportValidationError(f"Manual periodicity {manual.id!r} refers to a missing generated proposition.")
    for workspace in project.workspaces:
        class_ids = {item.id for item in workspace.classes}
        differential_ids = {item.id for item in workspace.differentials}
        for node in workspace.classes:
            if not node.manual_periodicity_id:
                continue
            manual = manual_by_id.get(node.manual_periodicity_id)
            if manual is None or manual.workspace_id != workspace.id:
                raise ProjectImportValidationError(f"Class {node.id!r} refers to a missing manual periodicity declaration.")
            if node.manual_periodicity_anchor_class_id not in class_ids:
                raise ProjectImportValidationError(f"Class {node.id!r} has a missing manual periodicity anchor.")
            if any(isinstance(value, bool) or not isinstance(value, int) for value in node.manual_periodicity_exponents):
                raise ProjectImportValidationError(f"Class {node.id!r} has invalid manual periodicity exponents.")
        for differential in workspace.differentials:
            if not differential.manual_periodicity_id:
                continue
            manual = manual_by_id.get(differential.manual_periodicity_id)
            if manual is None or manual.workspace_id != workspace.id or differential.anchor_differential_id not in differential_ids:
                raise ProjectImportValidationError(f"Differential {differential.id!r} has an invalid manual periodicity reference.")
            if any(isinstance(value, bool) or not isinstance(value, int) for value in differential.manual_periodicity_exponents):
                raise ProjectImportValidationError(f"Differential {differential.id!r} has invalid manual periodicity exponents.")
        for proposition in workspace.propositions:
            for premise in proposition.premise_ids:
                if premise not in all_proposition_id_set:
                    raise ProjectImportValidationError(f"Proposition {proposition.id!r} has missing premise {premise!r}.")
    for comparison in project.comparisons:
        if comparison.source_workspace_id not in workspace_ids or comparison.target_workspace_id not in workspace_ids:
            raise ProjectImportValidationError(f"Comparison {comparison.id!r} refers to a missing workspace.")
        _validate_grade(comparison.grade_shift, f"comparison {comparison.id}")
    for family in project.period_families:
        if family.workspace_id not in workspace_ids:
            raise ProjectImportValidationError(f"Period family {family.id!r} refers to a missing workspace.")
        if family.certificate_proposition_id and family.certificate_proposition_id not in all_proposition_id_set:
            raise ProjectImportValidationError(f"Period family {family.id!r} has a missing certificate proposition.")
    for rule in project.periodicity_rules:
        if rule.workspace_id not in workspace_ids:
            raise ProjectImportValidationError(f"Periodicity rule {rule.id!r} refers to a missing workspace.")
        if rule.certificate_proposition_id and rule.certificate_proposition_id not in all_proposition_id_set:
            raise ProjectImportValidationError(f"Periodicity rule {rule.id!r} has a missing certificate proposition.")
        _validate_grade(rule.grade_shift, f"periodicity rule {rule.id}")


def _validate_grade(grade, scope: str) -> None:
    if isinstance(grade.stem, bool) or not isinstance(grade.stem, int):
        raise ProjectImportValidationError(f"{scope} has a non-integer stem.")
    if isinstance(grade.filtration, bool) or not isinstance(grade.filtration, int):
        raise ProjectImportValidationError(f"{scope} has a non-integer filtration.")
    if not isinstance(grade.representation, dict) or any(
        not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, int)
        for key, value in grade.representation.items()
    ):
        raise ProjectImportValidationError(f"{scope} has an invalid representation grade.")


def _validate_nonzero_grade(grade, scope: str) -> None:
    _validate_grade(grade, scope)
    if grade.stem == 0 and grade.filtration == 0 and not any(grade.representation.values()):
        raise ProjectImportValidationError(f"{scope} has a zero period vector.")


def _unique(values, kind: str) -> None:
    values = list(values)
    if any(not isinstance(value, str) or not value for value in values):
        raise ProjectImportValidationError(f"Every {kind} id must be a nonempty string.")
    if len(values) != len(set(values)):
        raise ProjectImportValidationError(f"Duplicate {kind} ids are not safe to import.")


def import_digest(project: Project) -> str:
    """Return a stable digest for the post-migration preview that must be applied."""

    import hashlib
    import json
    canonical = json.dumps(project_to_dict(project), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
