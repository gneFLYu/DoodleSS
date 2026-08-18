"""Exact finite-field linear algebra for spectral-sequence cells.

The first registered field is F4.  The registry boundary is intentional: a
Witt or 2-adic coefficient context must never be reduced to F4 implicitly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence, TypeVar

from .algebra import F4Element


class CellLinearAlgebraError(ValueError):
    pass


Scalar = TypeVar("Scalar")


class FiniteFieldArithmetic(Protocol[Scalar]):
    name: str

    def parse(self, value: object) -> Scalar: ...
    def zero(self) -> Scalar: ...
    def one(self) -> Scalar: ...
    def canonical(self, value: Scalar) -> str: ...
    def inverse(self, value: Scalar) -> Scalar: ...


@dataclass(frozen=True)
class F4Arithmetic:
    name: str = "F4"

    def parse(self, value: object) -> F4Element:
        try:
            return F4Element.parse(value)  # type: ignore[arg-type]
        except (TypeError, ValueError) as error:
            raise CellLinearAlgebraError(str(error)) from error

    def zero(self) -> F4Element:
        return F4Element.zero()

    def one(self) -> F4Element:
        return F4Element.one()

    def canonical(self, value: F4Element) -> str:
        return str(value)

    def inverse(self, value: F4Element) -> F4Element:
        try:
            return value.inverse()
        except ZeroDivisionError as error:
            raise CellLinearAlgebraError(str(error)) from error


FIELD_REGISTRY: dict[str, FiniteFieldArithmetic] = {"F4": F4Arithmetic()}


def field_arithmetic(name: str) -> FiniteFieldArithmetic:
    try:
        return FIELD_REGISTRY[name]
    except KeyError as error:
        raise CellLinearAlgebraError(
            f"No exact finite-field arithmetic is registered for {name!r}."
        ) from error


def _field(field_name: str = "F4") -> F4Arithmetic:
    field = field_arithmetic(field_name)
    if not isinstance(field, F4Arithmetic):
        raise CellLinearAlgebraError(f"The {field_name!r} adapter is not available in this build.")
    return field


def canonical_scalar(value: object, field_name: str = "F4") -> str:
    field = _field(field_name)
    return field.canonical(field.parse(value))


def parse_vector(values: Sequence[object], dimension: int | None = None, field_name: str = "F4") -> list[F4Element]:
    if dimension is not None and len(values) != dimension:
        raise CellLinearAlgebraError(f"Expected {dimension} coordinates, received {len(values)}.")
    field = _field(field_name)
    return [field.parse(value) for value in values]


def canonical_vector(values: Sequence[object], dimension: int | None = None, field_name: str = "F4") -> list[str]:
    field = _field(field_name)
    return [field.canonical(value) for value in parse_vector(values, dimension, field_name)]


def canonical_matrix(
    values: Sequence[Sequence[object]],
    rows: int,
    columns: int,
    field_name: str = "F4",
) -> list[list[str]]:
    if len(values) != rows:
        raise CellLinearAlgebraError(f"Expected {rows} matrix rows, received {len(values)}.")
    return [canonical_vector(row, columns, field_name) for row in values]


def projective_normal_form(values: Sequence[object], field_name: str = "F4") -> list[str]:
    field = _field(field_name)
    vector = parse_vector(values, field_name=field_name)
    first = next((value for value in vector if value != field.zero()), None)
    if first is None:
        raise CellLinearAlgebraError("The zero vector has no projective direction.")
    scale = field.inverse(first)
    return [field.canonical(scale * value) for value in vector]


def _parse_matrix(values: Sequence[Sequence[object]], field_name: str = "F4") -> list[list[F4Element]]:
    if not values:
        return []
    columns = len(values[0])
    if any(len(row) != columns for row in values):
        raise CellLinearAlgebraError("Matrix rows must have equal length.")
    return [parse_vector(row, columns, field_name) for row in values]


def rref(values: Sequence[Sequence[object]], field_name: str = "F4") -> tuple[list[list[str]], list[int]]:
    field = _field(field_name)
    matrix = _parse_matrix(values, field_name)
    if not matrix:
        return [], []
    rows, columns = len(matrix), len(matrix[0])
    pivot_columns: list[int] = []
    pivot_row = 0
    for column in range(columns):
        selected = next((row for row in range(pivot_row, rows) if matrix[row][column] != field.zero()), None)
        if selected is None:
            continue
        matrix[pivot_row], matrix[selected] = matrix[selected], matrix[pivot_row]
        inverse = field.inverse(matrix[pivot_row][column])
        matrix[pivot_row] = [inverse * value for value in matrix[pivot_row]]
        for row in range(rows):
            if row == pivot_row or matrix[row][column] == field.zero():
                continue
            factor = matrix[row][column]
            matrix[row] = [left - factor * right for left, right in zip(matrix[row], matrix[pivot_row])]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == rows:
            break
    return [[field.canonical(value) for value in row] for row in matrix], pivot_columns


def matrix_rank(values: Sequence[Sequence[object]], field_name: str = "F4") -> int:
    return len(rref(values, field_name)[1])


def matrix_vector_product(
    matrix_values: Sequence[Sequence[object]],
    vector_values: Sequence[object],
    field_name: str = "F4",
) -> list[str]:
    field = _field(field_name)
    matrix = _parse_matrix(matrix_values, field_name)
    columns = len(matrix[0]) if matrix else len(vector_values)
    vector = parse_vector(vector_values, columns, field_name)
    result = []
    for row in matrix:
        total = field.zero()
        for left, right in zip(row, vector):
            total = total + left * right
        result.append(field.canonical(total))
    return result


def matrix_product(
    left_values: Sequence[Sequence[object]],
    right_values: Sequence[Sequence[object]],
    field_name: str = "F4",
) -> list[list[str]]:
    field = _field(field_name)
    left = _parse_matrix(left_values, field_name)
    right = _parse_matrix(right_values, field_name)
    if not left:
        return []
    inner = len(left[0])
    if len(right) != inner:
        raise CellLinearAlgebraError("Matrix dimensions do not compose.")
    columns = len(right[0]) if right else 0
    output: list[list[str]] = []
    for row in left:
        output_row: list[str] = []
        for column in range(columns):
            total = field.zero()
            for index in range(inner):
                total = total + row[index] * right[index][column]
            output_row.append(field.canonical(total))
        output.append(output_row)
    return output


def nullspace(values: Sequence[Sequence[object]], columns: int | None = None, field_name: str = "F4") -> list[list[str]]:
    field = _field(field_name)
    if not values:
        dimension = int(columns or 0)
        return [
            [field.canonical(field.one() if row == column else field.zero()) for row in range(dimension)]
            for column in range(dimension)
        ]
    reduced_strings, pivots = rref(values, field_name)
    reduced = _parse_matrix(reduced_strings, field_name)
    dimension = len(reduced[0])
    free_columns = [column for column in range(dimension) if column not in pivots]
    basis: list[list[str]] = []
    for free in free_columns:
        vector = [field.zero() for _ in range(dimension)]
        vector[free] = field.one()
        for row, pivot in enumerate(pivots):
            vector[pivot] = -reduced[row][free]
        basis.append([field.canonical(value) for value in vector])
    return basis


def column_space(values: Sequence[Sequence[object]], field_name: str = "F4") -> list[list[str]]:
    field = _field(field_name)
    matrix = _parse_matrix(values, field_name)
    if not matrix:
        return []
    _, pivots = rref(values, field_name)
    return [
        [field.canonical(matrix[row][column]) for row in range(len(matrix))]
        for column in pivots
    ]


def _vectors_as_rows(vectors: Sequence[Sequence[object]], field_name: str = "F4") -> list[list[str]]:
    return [canonical_vector(vector, field_name=field_name) for vector in vectors]


def in_span(vector: Sequence[object], basis: Sequence[Sequence[object]], field_name: str = "F4") -> bool:
    rows = _vectors_as_rows(basis, field_name)
    canonical = canonical_vector(vector, field_name=field_name)
    return matrix_rank(rows, field_name) == matrix_rank([*rows, canonical], field_name)


def quotient_basis(
    kernel_basis: Sequence[Sequence[object]],
    image_basis: Sequence[Sequence[object]],
    field_name: str = "F4",
) -> list[list[str]]:
    kernel = _vectors_as_rows(kernel_basis, field_name)
    image = _vectors_as_rows(image_basis, field_name)
    if kernel:
        dimension = len(kernel[0])
    elif image:
        dimension = len(image[0])
    else:
        return []
    if any(len(vector) != dimension for vector in [*kernel, *image]):
        raise CellLinearAlgebraError("Kernel and image vectors must have the same ambient dimension.")
    if any(not in_span(vector, kernel, field_name) for vector in image):
        raise CellLinearAlgebraError("The incoming image is not contained in the outgoing kernel (d_r^2 != 0).")
    span = list(image)
    quotient: list[list[str]] = []
    rank = matrix_rank(span, field_name)
    for vector in kernel:
        next_rank = matrix_rank([*span, vector], field_name)
        if next_rank > rank:
            quotient.append(vector)
            span.append(vector)
            rank = next_rank
    return quotient


def validate_display_basis(vectors: Sequence[Sequence[object]], dimension: int, field_name: str = "F4") -> list[list[str]]:
    if not vectors:
        return []
    if len(vectors) != dimension:
        raise CellLinearAlgebraError(f"A display basis for rank {dimension} must contain {dimension} vectors.")
    canonical = [canonical_vector(vector, dimension, field_name) for vector in vectors]
    if matrix_rank(canonical, field_name) != dimension:
        raise CellLinearAlgebraError("The display-basis coordinate matrix must be invertible.")
    return canonical


def transition_data(
    dimension: int,
    outgoing_matrix: Sequence[Sequence[object]] | None,
    incoming_matrix: Sequence[Sequence[object]] | None,
    field_name: str = "F4",
) -> dict:
    """Compute ker(outgoing)/im(incoming), returning original-basis vectors."""
    if outgoing_matrix is None or incoming_matrix is None:
        missing = []
        if outgoing_matrix is None:
            missing.append("outgoing complete map")
        if incoming_matrix is None:
            missing.append("incoming complete map")
        return {"status": "underdetermined", "obligations": missing}
    try:
        kernel = nullspace(outgoing_matrix, columns=dimension, field_name=field_name)
        image = column_space(incoming_matrix, field_name=field_name)
        quotient = quotient_basis(kernel, image, field_name)
    except CellLinearAlgebraError as error:
        return {"status": "inconsistent", "error": str(error), "kernel_basis": locals().get("kernel", [])}
    return {
        "status": "complete",
        "kernel_basis": kernel,
        "image_basis": image,
        "quotient_basis": quotient,
        "ambient_rank": dimension,
        "kernel_rank": len(kernel),
        "image_rank": len(image),
        "quotient_rank": len(quotient),
        "obligations": [],
    }
