"""Safe full-project JSON import preparation and structural validation.

The Studio export format is the serialized ``Project`` object.  Legacy chart
JSON from the standalone sseq page has ``generators`` and ``connections`` but
does not carry Studio workspace, evidence, or grading semantics, so it is
recognized and rejected rather than guessed at.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .fate import is_accepted
from .migrations import migrate_project
from .models import Project, project_from_dict, project_to_dict
from .periods import fill_legacy_period_pairs


class ProjectImportValidationError(ValueError):
    """Raised when a candidate full-project replacement is unsafe to apply."""


def prepare_project_import(raw: Any) -> tuple[Project, dict[str, Any]]:
    """Parse, migrate, and validate a full Studio project without persisting it."""

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
