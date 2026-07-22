"""Read-only differential candidate enumeration.

The functions in this module only report endpoints that obey the chart's
declared differential bidegree and are live on the requested page.  They do
not establish that a differential exists, mutate a workspace, or promote a
candidate to an accepted proposition.
"""
from __future__ import annotations

from typing import Iterable

from .fate import class_is_live_on_page, is_accepted
from .models import ClassNode, Comparison, Project, Proposition, Workspace, new_id


class CandidateEnumerationError(ValueError):
    """Raised when a read-only candidate query has invalid explicit input."""


def enumerate_differential_candidates(
    workspace: Workspace, source_id: str, page: int,
) -> list[Proposition]:
    """Return unpersisted targets compatible with ``d_page`` from ``source_id``.

    Compatibility is deliberately structural only: the expected bidegree is
    ``(-1, +page)`` in (stem, filtration), the representation coordinate is
    preserved, and both nodes must exist and be live on the requested page.
    No evidence is supplied for a nonzero differential.
    """

    source = _active_class(workspace, source_id)
    _validate_page(page)
    _validate_live(workspace, source, page, role="source")
    claimed = _claimed_endpoint_keys(workspace)

    result: list[Proposition] = []
    for target in _live_active_classes(workspace, page):
        if target.id == source.id:
            continue
        if not _has_differential_bidegree(source, target, page):
            continue
        if (source.id, target.id, page) in claimed:
            continue
        result.append(_bidegree_candidate(source, target, page))
    return result


def enumerate_comparison_transport_candidates(
    project: Project,
    target_workspace: Workspace,
    target_source_id: str,
    page: int,
    comparison_id: str,
) -> list[Proposition]:
    """Return unpersisted map-transport candidates from an accepted source arrow.

    The selected source is in the *target* workspace.  A candidate is returned
    only when an existing Comparison maps an already accepted source-workspace
    differential to that selected node and to an existing live target endpoint.
    The response records the comparison and source differential as hypotheses;
    it makes no assertion that the map transport theorem actually applies.
    """

    _validate_page(page)
    target_source = _active_class(target_workspace, target_source_id)
    _validate_live(target_workspace, target_source, page, role="selected target-workspace source")
    comparison = next((item for item in project.comparisons if item.id == comparison_id), None)
    if comparison is None:
        raise CandidateEnumerationError(f"Unknown comparison {comparison_id!r}.")
    if comparison.target_workspace_id != target_workspace.id:
        raise CandidateEnumerationError(
            f"Comparison {comparison.id!r} does not target workspace {target_workspace.id!r}."
        )
    source_workspace = next(
        (item for item in project.workspaces if item.id == comparison.source_workspace_id), None
    )
    if source_workspace is None:
        raise CandidateEnumerationError(
            f"Comparison {comparison.id!r} refers to an unavailable source workspace."
        )

    claimed = _claimed_endpoint_keys(target_workspace)
    output: list[Proposition] = []
    for differential in source_workspace.differentials:
        if differential.page != page or not is_accepted(differential.status):
            continue
        source = _find_class(source_workspace, differential.source_id)
        target = _find_class(source_workspace, differential.target_id)
        if not source or not target or source.archived or target.archived:
            continue
        if not class_is_live_on_page(source_workspace, source.id, page):
            continue
        if not class_is_live_on_page(source_workspace, target.id, page):
            continue
        if source.grade.shifted(comparison.grade_shift) != target_source.grade:
            continue
        transported_target_grade = target.grade.shifted(comparison.grade_shift)
        for target_node in _live_active_classes(target_workspace, page):
            if target_node.grade != transported_target_grade:
                continue
            if not _has_differential_bidegree(target_source, target_node, page):
                # A comparison must still preserve the declared d_r bidegree.
                continue
            if (target_source.id, target_node.id, page) in claimed:
                continue
            output.append(_comparison_candidate(
                comparison, source_workspace, _find_proposition(source_workspace, differential.proposition_id),
                target_source, target_node, page,
            ))
    return output


def _active_class(workspace: Workspace, class_id: str) -> ClassNode:
    node = _find_class(workspace, class_id)
    if node is None:
        raise CandidateEnumerationError(f"Unknown class {class_id!r} in workspace {workspace.id!r}.")
    if node.archived:
        raise CandidateEnumerationError(f"Class {class_id!r} is archived and cannot be enumerated.")
    return node


def _find_class(workspace: Workspace, class_id: str) -> ClassNode | None:
    return next((item for item in workspace.classes if item.id == class_id), None)


def _find_proposition(workspace: Workspace, proposition_id: str) -> Proposition | None:
    return next((item for item in workspace.propositions if item.id == proposition_id), None)


def _validate_page(page: int) -> None:
    if isinstance(page, bool) or not isinstance(page, int) or page < 2:
        raise CandidateEnumerationError("A differential page must be an integer at least 2.")


def _validate_live(workspace: Workspace, node: ClassNode, page: int, *, role: str) -> None:
    if node.page > page:
        raise CandidateEnumerationError(
            f"The {role} class {node.id!r} first appears on E_{node.page}, not E_{page}."
        )
    if not class_is_live_on_page(workspace, node.id, page):
        raise CandidateEnumerationError(f"The {role} class {node.id!r} is not live on E_{page}.")


def _live_active_classes(workspace: Workspace, page: int) -> Iterable[ClassNode]:
    for node in workspace.classes:
        if node.archived or node.page > page:
            continue
        if class_is_live_on_page(workspace, node.id, page):
            yield node


def _has_differential_bidegree(source: ClassNode, target: ClassNode, page: int) -> bool:
    return (
        target.grade.stem == source.grade.stem - 1
        and target.grade.filtration == source.grade.filtration + page
        and target.grade.representation == source.grade.representation
    )


def _claimed_endpoint_keys(workspace: Workspace) -> set[tuple[str, str, int]]:
    return {
        (item.source_id, item.target_id, item.page)
        for item in workspace.differentials
    }


def _bidegree_candidate(source: ClassNode, target: ClassNode, page: int) -> Proposition:
    return Proposition(
        id=new_id("candidate"),
        kind="differential",
        statement=f"Candidate only: d_{page}({source.label}) = {target.label}",
        status="candidate",
        conclusion={"source_id": source.id, "target_id": target.id, "page": page},
        rule="BidegreeAndLiveness",
        confidence=0.0,
        notes=(
            "Enumerated from bidegree and page liveness only. It is not a claimed "
            "or accepted differential and is not stored by this endpoint."
        ),
        hypotheses=[
            f"The selected source and target are classes on E_{page}.",
            f"The chart convention gives d_{page} bidegree (-1, +{page}).",
            "The representation coordinate is preserved by this chart convention.",
            "Independent mathematical evidence is still required to claim a nonzero differential.",
        ],
        verification_checks=[
            "source-exists", "target-exists", "page-liveness", "bidegree", "representation", "no-automatic-claim",
        ],
    )


def _comparison_candidate(
    comparison: Comparison,
    source_workspace: Workspace,
    source_proposition: Proposition | None,
    target_source: ClassNode,
    target: ClassNode,
    page: int,
) -> Proposition:
    source_refs = [item for item in [comparison.source_ref] if item]
    if source_proposition:
        source_refs.extend(source_proposition.source_refs)
        if source_proposition.source_ref:
            source_refs.append(source_proposition.source_ref)
    source_refs = list(dict.fromkeys(item for item in source_refs if item))
    return Proposition(
        id=new_id("candidate"),
        kind="differential",
        statement=f"{comparison.mode.title()} transport candidate only: d_{page}({target_source.label}) = {target.label}",
        status="candidate",
        conclusion={"source_id": target_source.id, "target_id": target.id, "page": page},
        premise_ids=[source_proposition.id] if source_proposition else [],
        rule="ComparisonTransportCandidate",
        confidence=0.0,
        notes=(
            f"Transported structurally from an accepted differential in {source_workspace.name!r} "
            f"through comparison {comparison.name!r}. This is an unpersisted review candidate, "
            "not a theorem that the comparison applies."
        ),
        source_ref=comparison.source_ref or (source_proposition.source_ref if source_proposition else ""),
        source_refs=source_refs,
        hypotheses=[
            f"Comparison {comparison.id!r} is defined and applies with its recorded grade shift.",
            "The accepted source-workspace differential is within the comparison's valid scope.",
            f"Both transported endpoints are live on E_{page} and preserve the d_r bidegree.",
            "Independent comparison-map hypotheses and a source locator must be reviewed before claiming this arrow.",
        ],
        verification_checks=[
            "comparison-record", "accepted-source-differential", "grade-translation", "page-liveness", "bidegree", "representation", "no-automatic-claim",
        ],
    )
