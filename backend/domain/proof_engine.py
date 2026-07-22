"""Transparent, deliberately conservative proposition suggestions.

The engine never silently changes a claimed theorem: it emits suggestions with
complete provenance that a mathematician can inspect and accept or reject.
"""
from __future__ import annotations

from typing import Iterable

from .models import ClassNode, Grade, Proposition, Workspace, new_id
from .fate import is_accepted


def _statement_diff(source: ClassNode, target: ClassNode, page: int) -> str:
    return f"d_{page}({source.label}) = {target.label}"


def _find_class(workspace: Workspace, class_id: str) -> ClassNode | None:
    return next((item for item in workspace.classes if item.id == class_id), None)


def _differential_propositions(workspace: Workspace) -> Iterable[Proposition]:
    for proposition in workspace.propositions:
        if proposition.kind == "differential" and is_accepted(proposition.status):
            yield proposition


def leibniz_suggestions(workspace: Workspace) -> list[Proposition]:
    """Suggest d_r(xz)=d_r(x)z for permanent multipliers already drawn."""
    suggestions: list[Proposition] = []
    permanent_ids = {fate.class_id for fate in workspace.fates if fate.conclusion == "permanent_cycle"}
    permanent = [node for node in workspace.classes if node.id in permanent_ids]
    for proposition in _differential_propositions(workspace):
        conclusion = proposition.conclusion
        source = _find_class(workspace, conclusion.get("source_id", ""))
        target = _find_class(workspace, conclusion.get("target_id", ""))
        if not source or not target:
            continue
        for multiplier in permanent:
            if multiplier.id in (source.id, target.id):
                continue
            # The unit produces the original differential, not a new deduction.
            if multiplier.grade == Grade():
                continue
            candidate_source_grade = source.grade.shifted(multiplier.grade)
            candidate_target_grade = target.grade.shifted(multiplier.grade)
            existing_source = next((node for node in workspace.classes if node.grade == candidate_source_grade), None)
            existing_target = next((node for node in workspace.classes if node.grade == candidate_target_grade), None)
            if not existing_source or not existing_target:
                continue
            statement = f"Leibniz candidate: d_{conclusion.get('page', workspace.page)}({existing_source.label}) = {existing_target.label}"
            if any(item.statement == statement for item in workspace.propositions):
                continue
            suggestions.append(Proposition(
                id=new_id("prop"), kind="differential", statement=statement, status="suggested",
                conclusion={"source_id": existing_source.id, "target_id": existing_target.id, "page": conclusion.get("page", workspace.page)},
                premise_ids=[proposition.id], rule="LeibnizRule", confidence=0.72,
                notes=f"Multiply {_statement_diff(source, target, conclusion.get('page', workspace.page))} by the permanent cycle {multiplier.label}.",
            ))
    return suggestions


def vanishing_line_suggestions(workspace: Workspace) -> list[Proposition]:
    line = int(workspace.settings.get("vanishing_line", 0))
    if line <= 0:
        return []
    output: list[Proposition] = []
    for node in workspace.classes:
        if node.grade.filtration < line or node.state not in {"unknown", "permanent"}:
            continue
        statement = f"Vanishing-line obligation: {node.label} in filtration {node.grade.filtration} must be hit or support a differential."
        if any(item.statement == statement for item in workspace.propositions):
            continue
        output.append(Proposition(
            id=new_id("prop"), kind="relation", statement=statement, status="suggested",
            conclusion={"class_id": node.id, "filtration": node.grade.filtration, "line": line}, rule="VanishingLine", confidence=0.93,
            notes="This is an obligation, not a chosen differential. Supply a compatible source/target before accepting it as a concrete claim.",
        ))
    return output


def comparison_suggestions(source: Workspace, target: Workspace, mode: str, shift: Grade) -> list[Proposition]:
    output: list[Proposition] = []
    for differential in source.differentials:
        if not is_accepted(differential.status):
            continue
        from_node, to_node = _find_class(source, differential.source_id), _find_class(source, differential.target_id)
        if not from_node or not to_node:
            continue
        source_grade, target_grade = from_node.grade.shifted(shift), to_node.grade.shifted(shift)
        translated_from = next((node for node in target.classes if node.grade == source_grade), None)
        translated_to = next((node for node in target.classes if node.grade == target_grade), None)
        if not translated_from or not translated_to:
            continue
        statement = f"{mode.title()} candidate: d_{differential.page}({translated_from.label}) = {translated_to.label}"
        if any(item.statement == statement for item in target.propositions):
            continue
        output.append(Proposition(
            id=new_id("prop"), kind="differential", statement=statement, status="suggested",
            conclusion={"source_id": translated_from.id, "target_id": translated_to.id, "page": differential.page},
            rule=mode, confidence=0.6 if mode in {"restriction", "transfer", "norm"} else 0.85,
            notes=f"Transported from {source.name}; verify the comparison hypotheses and grading convention.",
        ))
    return output
