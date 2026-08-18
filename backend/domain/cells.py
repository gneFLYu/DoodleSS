"""Coefficient-aware cell records, matrix validation, and page transitions."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from .cell_linear_algebra import (
    CellLinearAlgebraError,
    canonical_matrix,
    canonical_vector,
    field_arithmetic,
    matrix_vector_product,
    matrix_product,
    projective_normal_form,
    transition_data,
    validate_display_basis,
)
from .logic_graph import admitted_proposition_ids
from .models import (
    CellBasisVector,
    CellVectorSpace,
    ClassNode,
    DifferentialMap,
    Grade,
    NamedVector,
    Project,
    Workspace,
    new_id,
)


LEGACY_CELL_PREFIX = "legacy-cell:"
ADMITTED_STATUSES = frozenset({"established", "verified", "source-verified"})


def coefficient_field(project: Project, coefficient_context_id: str) -> str:
    context = next((item for item in project.coefficient_contexts if item.id == coefficient_context_id), None)
    if context is None:
        raise CellLinearAlgebraError(f"Unknown coefficient context: {coefficient_context_id}.")
    if context.scalar_mode != "residue" or context.coefficient_ring != context.residue_field:
        raise CellLinearAlgebraError(
            f"Cell linear algebra requires an exact residue-field context; {context.coefficient_ring} "
            "will not be reduced modulo 2 implicitly."
        )
    field_arithmetic(context.residue_field)
    return context.residue_field


def _grade(raw: Any, fallback: Grade | None = None) -> Grade:
    if isinstance(raw, Grade):
        return raw
    if raw is None and fallback is not None:
        return fallback
    if not isinstance(raw, dict):
        raise CellLinearAlgebraError("A cell grade must be a JSON object.")
    representation = raw.get("representation", {})
    if not isinstance(representation, dict) or any(
        not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, int)
        for key, value in representation.items()
    ):
        raise CellLinearAlgebraError("Representation coordinates must map strings to integers.")
    try:
        return Grade(int(raw.get("stem", 0)), int(raw.get("filtration", 0)), dict(representation))
    except (TypeError, ValueError) as error:
        raise CellLinearAlgebraError("Stem and filtration must be integers.") from error


def _basis(raw: Any, existing: list[CellBasisVector] | None = None) -> list[CellBasisVector]:
    if raw is None and existing is not None:
        return existing
    if not isinstance(raw, list) or not raw:
        raise CellLinearAlgebraError("A cell needs a nonempty ordered computational basis.")
    if len(raw) > 64:
        raise CellLinearAlgebraError("A cell basis may contain at most 64 vectors.")
    output: list[CellBasisVector] = []
    for index, item in enumerate(raw):
        if isinstance(item, str):
            label, ident, expression = item.strip(), new_id("basis"), item.strip()
        elif isinstance(item, dict):
            label = str(item.get("label", "")).strip()
            ident = str(item.get("id") or new_id("basis"))
            expression = str(item.get("expression") or label)
        else:
            raise CellLinearAlgebraError("Each basis vector must be a label or JSON object.")
        if not label:
            raise CellLinearAlgebraError(f"Basis vector {index + 1} needs a label.")
        output.append(CellBasisVector(ident, label, expression))
    if len({item.id for item in output}) != len(output):
        raise CellLinearAlgebraError("Basis-vector IDs must be unique inside a cell.")
    return output


def _named_vectors(raw: Any, rank: int, field_name: str, *, require_basis: bool = False) -> list[NamedVector]:
    if raw in (None, []):
        return []
    if not isinstance(raw, list):
        raise CellLinearAlgebraError("Named vectors must be a JSON list.")
    output: list[NamedVector] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise CellLinearAlgebraError("Each named vector must be a JSON object.")
        label = str(item.get("label", "")).strip()
        if not label:
            raise CellLinearAlgebraError(f"Named vector {index + 1} needs a label.")
        coordinates = canonical_vector(item.get("coordinates", []), rank, field_name)
        if not any(value != "0" for value in coordinates):
            raise CellLinearAlgebraError("The zero vector cannot be a named projective port.")
        output.append(NamedVector(
            id=str(item.get("id") or new_id("vector")),
            label=label,
            coordinates=coordinates,
            expression=str(item.get("expression") or label),
            pinned=bool(item.get("pinned", True)),
        ))
    if require_basis:
        canonical = validate_display_basis([item.coordinates for item in output], rank, field_name)
        for item, coordinates in zip(output, canonical):
            item.coordinates = coordinates
    return output


def cell_from_payload(project: Project, payload: dict[str, Any], existing: CellVectorSpace | None = None) -> CellVectorSpace:
    if not isinstance(payload, dict):
        raise CellLinearAlgebraError("Cell input must be a JSON object.")
    context_id = str(payload.get("coefficient_context_id", existing.coefficient_context_id if existing else "q8-residue-f4"))
    field_name = coefficient_field(project, context_id)
    basis = _basis(payload.get("basis"), existing.basis if existing else None)
    display_raw = payload.get("display_basis", [asdict(item) for item in existing.display_basis] if existing else [])
    named_raw = payload.get("named_vectors", [asdict(item) for item in existing.named_vectors] if existing else [])
    display_basis = _named_vectors(display_raw, len(basis), field_name, require_basis=True)
    named_vectors = _named_vectors(named_raw, len(basis), field_name)
    try:
        page = int(payload.get("page", existing.page if existing else 2))
    except (TypeError, ValueError) as error:
        raise CellLinearAlgebraError("Cell page must be an integer.") from error
    if page < 2:
        raise CellLinearAlgebraError("A cell must first appear on E2 or later.")
    status = str(payload.get("status", existing.status if existing else "candidate"))
    source_ref = str(payload.get("source_ref", existing.source_ref if existing else "")).strip()
    source_refs = payload.get("source_refs", existing.source_refs if existing else [])
    if not isinstance(source_refs, list) or any(not isinstance(item, str) for item in source_refs):
        raise CellLinearAlgebraError("source_refs must be a list of strings.")
    if status in ADMITTED_STATUSES and not (source_ref or source_refs):
        raise CellLinearAlgebraError("An accepted cell definition requires a source locator.")
    return CellVectorSpace(
        id=existing.id if existing else str(payload.get("id") or new_id("cell")),
        grade=_grade(payload.get("grade"), existing.grade if existing else None),
        page=page,
        coefficient_context_id=context_id,
        basis=basis,
        display_basis=display_basis,
        named_vectors=named_vectors,
        status=status,
        source_ref=source_ref,
        source_refs=list(source_refs) or ([source_ref] if source_ref else []),
        convention_id=str(payload.get("convention_id", existing.convention_id if existing else "q8-thesis-plotted-v1")),
        archived=existing.archived if existing else False,
        archived_reason=existing.archived_reason if existing else "",
    )


def legacy_cell(node: ClassNode) -> CellVectorSpace:
    return CellVectorSpace(
        id=f"{LEGACY_CELL_PREFIX}{node.id}",
        grade=node.grade,
        page=node.page,
        coefficient_context_id=node.coefficient_context_id,
        basis=[CellBasisVector(f"legacy-basis:{node.id}", node.label, node.expression or node.label)],
        display_basis=[NamedVector(f"legacy-display:{node.id}", node.label, ["1"], node.expression or node.label)],
        named_vectors=[],
        status="legacy-adapter",
        source_ref="Legacy rank-one ClassNode adapter",
    )


def effective_cell(workspace: Workspace, cell_id: str) -> CellVectorSpace | None:
    explicit = next((item for item in workspace.cells if item.id == cell_id and not item.archived), None)
    if explicit:
        return explicit
    if cell_id.startswith(LEGACY_CELL_PREFIX):
        class_id = cell_id.removeprefix(LEGACY_CELL_PREFIX)
        node = next((item for item in workspace.classes if item.id == class_id and not item.archived and not item.cell_id), None)
        if node:
            return legacy_cell(node)
    return None


def effective_cells(workspace: Workspace) -> list[CellVectorSpace]:
    return [item for item in workspace.cells if not item.archived] + [
        legacy_cell(node) for node in workspace.classes if not node.archived and not node.cell_id
    ]


def _cell_rank(cell: CellVectorSpace | None) -> int:
    return len(cell.basis) if cell else 0


def _canonical_map_matrix(
    payload: dict[str, Any], source_rank: int, target_rank: int, field_name: str
) -> list[list[str]]:
    raw = payload.get("matrix", [])
    if not isinstance(raw, list):
        raise CellLinearAlgebraError("A differential matrix must be a JSON list of rows.")
    return canonical_matrix(raw, target_rank, source_rank, field_name)


def _map_is_admitted(project: Project, item: DifferentialMap) -> bool:
    return (
        not item.archived
        and item.coverage == "complete"
        and item.status in ADMITTED_STATUSES
        and item.proposition_id in admitted_proposition_ids(project)
    )


def _matrix_is_zero(matrix: Iterable[Iterable[str]]) -> bool:
    return all(value == "0" for row in matrix for value in row)


def validate_differential_map(
    project: Project,
    workspace: Workspace,
    payload: dict[str, Any],
    existing: DifferentialMap | None = None,
) -> DifferentialMap:
    if not isinstance(payload, dict):
        raise CellLinearAlgebraError("Differential-map input must be a JSON object.")
    source_id = payload.get("source_cell_id", existing.source_cell_id if existing else None)
    target_id = payload.get("target_cell_id", existing.target_cell_id if existing else None)
    source_id = str(source_id) if source_id not in (None, "") else None
    target_id = str(target_id) if target_id not in (None, "") else None
    if source_id is None and target_id is None:
        raise CellLinearAlgebraError("A differential map needs a source or target cell.")
    source = effective_cell(workspace, source_id) if source_id else None
    target = effective_cell(workspace, target_id) if target_id else None
    if source_id and source is None:
        raise CellLinearAlgebraError(f"Unknown source cell: {source_id}.")
    if target_id and target is None:
        raise CellLinearAlgebraError(f"Unknown target cell: {target_id}.")
    contexts = {item.coefficient_context_id for item in (source, target) if item}
    if len(contexts) != 1:
        raise CellLinearAlgebraError("Source and target cells must use the same coefficient context.")
    field_name = coefficient_field(project, next(iter(contexts)))
    try:
        page = int(payload.get("page", existing.page if existing else workspace.page))
    except (TypeError, ValueError) as error:
        raise CellLinearAlgebraError("Differential page must be an integer.") from error
    if page < 2:
        raise CellLinearAlgebraError("Differential page must be at least E2.")
    if source and target:
        if target.grade.stem != source.grade.stem - 1 or target.grade.filtration != source.grade.filtration + page:
            raise CellLinearAlgebraError(f"Under q8-thesis-plotted-v1, d_{page} shifts (stem, filtration) by (-1, +{page}).")
        if target.grade.representation != source.grade.representation:
            raise CellLinearAlgebraError("A differential must preserve the representation coordinate.")
    matrix = _canonical_map_matrix(payload, _cell_rank(source), _cell_rank(target), field_name)
    coverage = str(payload.get("coverage", existing.coverage if existing else "partial"))
    if coverage not in {"partial", "complete"}:
        raise CellLinearAlgebraError("coverage must be partial or complete.")
    status = str(payload.get("status", existing.status if existing else "candidate"))
    proposition_id = str(payload.get("proposition_id", existing.proposition_id if existing else ""))
    source_ref = str(payload.get("source_ref", existing.source_ref if existing else "")).strip()
    source_refs = payload.get("source_refs", existing.source_refs if existing else [])
    if not isinstance(source_refs, list) or any(not isinstance(item, str) for item in source_refs):
        raise CellLinearAlgebraError("source_refs must be a list of strings.")
    propositions = {item.id for item in workspace.propositions}
    if status in ADMITTED_STATUSES:
        if not (source_ref or source_refs):
            raise CellLinearAlgebraError("An accepted differential map requires a source locator.")
        if not proposition_id or proposition_id not in propositions:
            raise CellLinearAlgebraError("An accepted differential map requires a proposition in this workspace.")
    candidate = DifferentialMap(
        id=existing.id if existing else str(payload.get("id") or new_id("linear_map")),
        source_cell_id=source_id,
        target_cell_id=target_id,
        page=page,
        matrix=matrix,
        coverage=coverage,
        status=status,
        proposition_id=proposition_id,
        source_ref=source_ref,
        source_refs=list(source_refs) or ([source_ref] if source_ref else []),
        notes=str(payload.get("notes", existing.notes if existing else "")),
        archived=existing.archived if existing else False,
        archived_reason=existing.archived_reason if existing else "",
    )
    if status in ADMITTED_STATUSES and coverage == "complete":
        for item in workspace.differential_maps:
            if item.id == candidate.id or not _map_is_admitted(project, item) or item.page != page:
                continue
            if item.source_cell_id == source_id and item.target_cell_id == target_id and item.matrix != matrix:
                raise CellLinearAlgebraError("A conflicting admitted complete map already exists for this cell pair and page.")
        _validate_d_squared(project, workspace, candidate)
    return candidate


def _validate_d_squared(project: Project, workspace: Workspace, candidate: DifferentialMap) -> None:
    maps = [item for item in workspace.differential_maps if _map_is_admitted(project, item) and item.page == candidate.page and item.id != candidate.id]
    for previous in maps:
        if previous.target_cell_id == candidate.source_cell_id and previous.source_cell_id and candidate.target_cell_id:
            if not _matrix_is_zero(matrix_product(candidate.matrix, previous.matrix)):
                raise CellLinearAlgebraError("The admitted composition through the source cell is nonzero (d_r^2 != 0).")
    for following in maps:
        if candidate.target_cell_id == following.source_cell_id and candidate.source_cell_id and following.target_cell_id:
            if not _matrix_is_zero(matrix_product(following.matrix, candidate.matrix)):
                raise CellLinearAlgebraError("The admitted composition through the target cell is nonzero (d_r^2 != 0).")


def map_image_ports(workspace: Workspace, item: DifferentialMap) -> list[dict[str, Any]]:
    source = effective_cell(workspace, item.source_cell_id) if item.source_cell_id else None
    target = effective_cell(workspace, item.target_cell_id) if item.target_cell_id else None
    if source is None:
        return []
    ports = []
    for column, basis in enumerate(source.basis):
        coordinates = [row[column] for row in item.matrix] if target else []
        if not coordinates or all(value == "0" for value in coordinates):
            ports.append({"source_basis_id": basis.id, "source_label": basis.label, "zero": True, "coordinates": coordinates})
        else:
            ports.append({
                "source_basis_id": basis.id,
                "source_label": basis.label,
                "zero": False,
                "coordinates": coordinates,
                "projective_coordinates": projective_normal_form(coordinates),
            })
    return ports


def vector_image(
    project: Project, workspace: Workspace, cell_id: str, map_id: str, coordinates: list[object]
) -> dict[str, Any]:
    cell = effective_cell(workspace, cell_id)
    item = next((record for record in workspace.differential_maps if record.id == map_id and not record.archived), None)
    if cell is None:
        raise CellLinearAlgebraError(f"Unknown cell: {cell_id}.")
    if item is None or item.source_cell_id != cell_id:
        raise CellLinearAlgebraError("Choose an active differential map with this source cell.")
    field_name = coefficient_field(project, cell.coefficient_context_id)
    canonical = canonical_vector(coordinates, len(cell.basis), field_name)
    image = matrix_vector_product(item.matrix, canonical, field_name) if item.target_cell_id else []
    zero = not image or all(value == "0" for value in image)
    return {
        "cell_id": cell_id,
        "map_id": map_id,
        "coordinates": canonical,
        "projective_coordinates": projective_normal_form(canonical, field_name) if any(value != "0" for value in canonical) else None,
        "image_coordinates": image,
        "image_projective_coordinates": None if zero else projective_normal_form(image, field_name),
        "zero": zero,
        "persisted": False,
    }


def _select_map(
    project: Project,
    workspace: Workspace,
    page: int,
    *,
    source_cell_id: str | None = None,
    target_cell_id: str | None = None,
    selected_id: str | None = None,
) -> tuple[DifferentialMap | None, list[str]]:
    if selected_id:
        selected = next((item for item in workspace.differential_maps if item.id == selected_id and not item.archived), None)
        if selected is None:
            return None, [f"Unknown selected map: {selected_id}"]
        if selected.page != page or (source_cell_id is not None and selected.source_cell_id != source_cell_id) or (target_cell_id is not None and selected.target_cell_id != target_cell_id):
            return None, [f"Selected map {selected_id} does not have the required page or endpoint."]
        if selected.coverage != "complete":
            return None, [f"Selected map {selected_id} is partial."]
        return selected, []
    matches = [
        item for item in workspace.differential_maps
        if item.page == page and _map_is_admitted(project, item)
        and (source_cell_id is None or item.source_cell_id == source_cell_id)
        and (target_cell_id is None or item.target_cell_id == target_cell_id)
    ]
    if len(matches) > 1:
        return None, ["Multiple admitted complete maps match this endpoint."]
    return (matches[0], []) if matches else (None, [])


def page_transition(
    project: Project,
    workspace: Workspace,
    cell_id: str,
    page: int,
    *,
    incoming_map_id: str | None = None,
    outgoing_map_id: str | None = None,
    incoming_zero: bool = False,
    outgoing_zero: bool = False,
) -> dict[str, Any]:
    cell = effective_cell(workspace, cell_id)
    if cell is None:
        raise CellLinearAlgebraError(f"Unknown cell: {cell_id}.")
    field_name = coefficient_field(project, cell.coefficient_context_id)
    outgoing, outgoing_errors = _select_map(
        project, workspace, page, source_cell_id=cell_id, selected_id=outgoing_map_id
    )
    incoming, incoming_errors = _select_map(
        project, workspace, page, target_cell_id=cell_id, selected_id=incoming_map_id
    )
    if outgoing_errors or incoming_errors:
        return {"status": "inconsistent", "errors": [*outgoing_errors, *incoming_errors], "cell_id": cell_id, "page": page}
    outgoing_matrix = outgoing.matrix if outgoing else ([] if outgoing_zero else None)
    incoming_matrix = incoming.matrix if incoming else ([[] for _ in range(len(cell.basis))] if incoming_zero else None)
    result = transition_data(len(cell.basis), outgoing_matrix, incoming_matrix, field_name)
    return {
        **result,
        "cell_id": cell_id,
        "page": page,
        "coefficient_context_id": cell.coefficient_context_id,
        "field": field_name,
        "computational_basis": [asdict(item) for item in cell.basis],
        "incoming_map_id": incoming.id if incoming else None,
        "outgoing_map_id": outgoing.id if outgoing else None,
        "canonical": not any((incoming_map_id, outgoing_map_id, incoming_zero, outgoing_zero)),
    }
