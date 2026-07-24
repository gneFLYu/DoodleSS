"""Safe algebra labels with no separate semantic-name field.

The label is the algebra expression.  This module recognizes a deliberately
small commutative-monomial subset of LaTeX without evaluating source text.
It never calls ``eval``, ``sympify``, or ``parse_expr``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Iterable

from .models import ClassNode


MAX_LABEL_LENGTH = 512
MAX_LABEL_FACTORS = 128
MAX_LABEL_EXPONENT = 4096


class AlgebraLabelError(ValueError):
    """Raised when a label is outside the safe monomial grammar."""


@dataclass(frozen=True)
class BasicAlgebraGenerator:
    """A basic generator registered by its displayed algebra label."""

    label: str
    kind: str = "generator"  # generator | unit


@dataclass(frozen=True)
class AlgebraLabelFactor:
    label: str
    power: int = 1


@dataclass(frozen=True)
class ParsedAlgebraLabel:
    coefficient: int
    factors: tuple[AlgebraLabelFactor, ...]
    registered_generators: tuple[BasicAlgebraGenerator, ...]
    label: str

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "coefficient": self.coefficient,
            "factors": [asdict(item) for item in self.factors],
            "registered_generators": [asdict(item) for item in self.registered_generators],
        }


def parse_algebra_label(
    label: str,
    *,
    unit_labels: Iterable[str] = (),
) -> ParsedAlgebraLabel:
    """Parse ``coefficient * letter-units * powers`` from a class label.

    Accepted layout separators are ``*``, ``\\cdot``, whitespace, and legacy
    ``\\,``.  Canonical output uses juxtaposition and omits coefficient one.
    Addition, equality, function calls, and arbitrary LaTeX commands are not
    part of this first-phase grammar.
    """

    if not isinstance(label, str) or not label.strip():
        raise AlgebraLabelError("label must be a nonempty string.")
    if len(label) > MAX_LABEL_LENGTH:
        raise AlgebraLabelError(f"label exceeds the {MAX_LABEL_LENGTH}-character limit.")
    text = "".join(label.replace(r"\,", "").split())
    if not text:
        raise AlgebraLabelError("label must contain an algebra expression.")
    units = {str(item).strip() for item in unit_labels if str(item).strip()}

    index = 0
    coefficient = 1
    has_prefix = False
    if text[index].isdigit():
        end = index
        while end < len(text) and text[end].isdigit():
            end += 1
        coefficient = int(text[index:end])
        if coefficient == 0:
            raise AlgebraLabelError("A class label cannot have zero coefficient.")
        index = end
        has_prefix = True

    ordered_labels: list[str] = []
    powers: dict[str, int] = {}
    separator_pending = False
    while index < len(text):
        if text.startswith(r"\cdot", index):
            if not has_prefix or separator_pending:
                raise AlgebraLabelError("A multiplication separator must occur between factors.")
            index += len(r"\cdot")
            separator_pending = True
            continue
        if text[index] == "*":
            if not has_prefix or separator_pending:
                raise AlgebraLabelError("A multiplication separator must occur between factors.")
            index += 1
            separator_pending = True
            continue
        atom, index = _parse_atom(text, index)
        has_prefix = True
        separator_pending = False
        power = 1
        if index < len(text) and text[index] == "^":
            power, index = _parse_exponent(text, index + 1)
        if abs(power) > MAX_LABEL_EXPONENT:
            raise AlgebraLabelError(
                f"Power of {atom!r} exceeds the absolute limit {MAX_LABEL_EXPONENT}."
            )
        if power < 0 and atom not in units:
            raise AlgebraLabelError(f"Negative power of {atom!r} requires an explicitly registered unit.")
        if atom not in powers:
            ordered_labels.append(atom)
            powers[atom] = 0
        powers[atom] += power
        if len(ordered_labels) > MAX_LABEL_FACTORS:
            raise AlgebraLabelError(f"label contains more than {MAX_LABEL_FACTORS} basic generators.")
    if separator_pending:
        raise AlgebraLabelError("A label cannot end with a multiplication separator.")

    factors = tuple(
        AlgebraLabelFactor(atom, powers[atom])
        for atom in ordered_labels
        if powers[atom]
    )
    for factor in factors:
        if factor.power < 0 and factor.label not in units:
            raise AlgebraLabelError(
                f"Collected negative power of {factor.label!r} requires an explicitly registered unit."
            )
    registered = tuple(
        BasicAlgebraGenerator(atom, "unit" if atom in units else "generator")
        for atom in ordered_labels
        if powers[atom]
    )
    canonical = _format_label(coefficient, factors)
    return ParsedAlgebraLabel(coefficient, factors, registered, canonical)


def multiply_algebra_labels(
    *labels: str,
    unit_labels: Iterable[str] = (),
) -> ParsedAlgebraLabel:
    """Multiply parsed labels and return one canonical label expression."""

    units = {str(item).strip() for item in unit_labels if str(item).strip()}
    parsed = [parse_algebra_label(item, unit_labels=units) for item in labels]
    coefficient = 1
    order: list[str] = []
    powers: dict[str, int] = {}
    for item in parsed:
        coefficient *= item.coefficient
        for factor in item.factors:
            if factor.label not in powers:
                order.append(factor.label)
                powers[factor.label] = 0
            powers[factor.label] += factor.power
    factors = tuple(AlgebraLabelFactor(atom, powers[atom]) for atom in order if powers[atom])
    registered = tuple(
        BasicAlgebraGenerator(atom, "unit" if atom in units else "generator")
        for atom in order
        if powers[atom]
    )
    return ParsedAlgebraLabel(coefficient, factors, registered, _format_label(coefficient, factors))


def multiply_label_by_period(
    base_label: str,
    period_label: str,
    translation: int,
) -> ParsedAlgebraLabel:
    """Multiply a label by a positive integral power of a period cycle."""

    if isinstance(translation, bool) or not isinstance(translation, int) or translation <= 0:
        raise AlgebraLabelError("Virtual period translation must be a positive integer.")
    base = parse_algebra_label(base_label)
    period = parse_algebra_label(period_label)
    if period.coefficient != 1:
        raise AlgebraLabelError("A virtual period label must have coefficient one.")
    coefficient = base.coefficient
    order = [item.label for item in base.factors]
    powers = {item.label: item.power for item in base.factors}
    for factor in period.factors:
        if factor.label not in powers:
            order.append(factor.label)
            powers[factor.label] = 0
        powers[factor.label] += factor.power * translation
    factors = tuple(AlgebraLabelFactor(atom, powers[atom]) for atom in order if powers[atom])
    registered = tuple(BasicAlgebraGenerator(atom) for atom in order if powers[atom])
    return ParsedAlgebraLabel(coefficient, factors, registered, _format_label(coefficient, factors))


def prepare_class_label_edit(node: ClassNode, label: str, *, target_page: int) -> ClassNode:
    """Return a page-specific class edit with label as the sole expression.

    ``expression`` is retained only as a legacy serialization alias and is set
    equal to ``label``.  The edit explicitly keeps the requested E_r page; it
    never resets the record to E2.
    """

    if isinstance(target_page, bool) or not isinstance(target_page, int) or target_page < 2:
        raise AlgebraLabelError("target_page must be an integer at least 2.")
    canonical = parse_algebra_label(label).label
    return replace(node, label=canonical, expression=canonical, page=target_page)


def _parse_atom(text: str, index: int) -> tuple[str, int]:
    start = index
    if index >= len(text):
        raise AlgebraLabelError("Expected a basic algebra generator.")
    if text[index].isalpha() and text[index].isascii():
        index += 1
    elif text[index] == "\\":
        index += 1
        command_start = index
        while index < len(text) and text[index].isalpha() and text[index].isascii():
            index += 1
        if index == command_start:
            raise AlgebraLabelError("Invalid LaTeX command in label.")
        if index < len(text) and text[index] == "{":
            _, index = _parse_braced(text, index)
    else:
        raise AlgebraLabelError(
            f"Unsupported character {text[index]!r}; only structured monomial labels are accepted."
        )
    if index < len(text) and text[index] == "_":
        index += 1
        if index >= len(text):
            raise AlgebraLabelError("A subscript must contain a symbol.")
        if text[index] == "{":
            content, index = _parse_braced(text, index)
            if not content:
                raise AlgebraLabelError("A subscript cannot be empty.")
            _validate_subscript(content)
        else:
            # Standard TeX gives an unbraced subscript exactly one token.
            # Keeping that boundary is essential for labels such as
            # ``v_1h_1D``: they register v_1, h_1, and D separately.
            if not text[index].isalnum():
                raise AlgebraLabelError("A subscript must contain letters or digits.")
            index += 1
    return text[start:index], index


def _parse_exponent(text: str, index: int) -> tuple[int, int]:
    if index >= len(text):
        raise AlgebraLabelError("An exponent is required after '^'.")
    if text[index] == "{":
        content, index = _parse_braced(text, index)
    else:
        start = index
        if text[index] in "+-":
            index += 1
        while index < len(text) and text[index].isdigit():
            index += 1
        content = text[start:index]
    if not content or content in {"+", "-"}:
        raise AlgebraLabelError("Exponents must be explicit integers.")
    try:
        return int(content), index
    except ValueError as error:
        raise AlgebraLabelError("Exponents must be explicit integers.") from error


def _parse_braced(text: str, index: int) -> tuple[str, int]:
    if text[index] != "{":
        raise AlgebraLabelError("Internal braced-expression parser error.")
    depth = 1
    cursor = index + 1
    while cursor < len(text) and depth:
        if text[cursor] == "{":
            depth += 1
        elif text[cursor] == "}":
            depth -= 1
        cursor += 1
    if depth:
        raise AlgebraLabelError("Unclosed LaTeX brace in label.")
    return text[index + 1:cursor - 1], cursor


def _validate_subscript(content: str) -> None:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_\\")
    if any(character not in allowed for character in content):
        raise AlgebraLabelError("Subscripts may contain only letters, digits, underscores, and LaTeX command names.")


def _format_label(coefficient: int, factors: tuple[AlgebraLabelFactor, ...]) -> str:
    pieces: list[str] = []
    if coefficient != 1 or not factors:
        pieces.append(str(coefficient))
    for factor in factors:
        pieces.append(factor.label if factor.power == 1 else f"{factor.label}^{{{factor.power}}}")
    return "".join(pieces) or "1"
