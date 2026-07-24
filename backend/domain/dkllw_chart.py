"""Explicit DKLLW24 chart-key semantics.

These helpers annotate user-supplied chart objects.  They do not infer a
module type from a class fate, a generic UI color, or the presence of a line,
and they never certify that a particular multiplication or extension exists.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .models import ClassNode, Grade


DKLLW24_CHART_KEY_SOURCE = (
    "DKLLW24, section 6.1, Tables 10-11, journal PDF p. 50"
)
DKLLW24_TWO_ADIC_SOURCE = (
    "DKLLW24, Remark 6.1 after Table 11, journal PDF pp. 50-51"
)


class ChartSemanticError(ValueError):
    """Raised when an annotation contradicts the selected DKLLW chart key."""


@dataclass(frozen=True)
class ChartClassSemantic:
    glyph: str
    algebra_type: str
    legend_source_ref: str = DKLLW24_CHART_KEY_SOURCE
    status: str = "source-legend"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ChartConnectionSemantic:
    kind: str
    multiplier: str
    hidden_extension: bool
    target_shift: Grade
    spectral_sequence: str
    claim_source_ref: str
    legend_source_ref: str = DKLLW24_CHART_KEY_SOURCE
    status: str = "candidate"

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


# The browser uses geometry rather than the historical blue/red palette for
# the two completed-local-module glyphs.  Palette aliases remain available to
# a legacy importer, but a generic class state/fate is never consulted.
_CLASS_GLYPHS = {
    "dot": "k",
    "fat-dot": r"k[\![j]\!]",
    "circle": r"k[\![j]\!]\{j\}",
    "square": r"\mathbb W(k)",
}
_LEGACY_CLASS_ALIASES = {
    "blue-dot": "fat-dot",
    "red-dot": "circle",
}

_CONNECTIONS = {
    "vertical-two": ("2", Grade(0, 0), False),
    "h1": ("h_1", Grade(1, 1), False),
    "h2": ("h_2", Grade(3, 1), False),
    "hidden-extension": ("unspecified", Grade(0, 0), True),
}


def class_semantic_from_glyph(glyph: str) -> ChartClassSemantic:
    """Return the module type named by one explicit DKLLW class glyph."""

    normalized = str(glyph).strip().lower().replace("_", "-").replace(" ", "-")
    normalized = _LEGACY_CLASS_ALIASES.get(normalized, normalized)
    algebra_type = _CLASS_GLYPHS.get(normalized)
    if algebra_type is None:
        raise ChartSemanticError(
            "glyph must be dot, fat-dot, circle, or square; color/state/fate is not an algebra type."
        )
    return ChartClassSemantic(normalized, algebra_type)


def annotate_class_glyph(node: ClassNode, glyph: str) -> dict:
    """Return a non-mutating, explicit class-glyph annotation."""

    semantic = class_semantic_from_glyph(glyph)
    return {
        "class_id": node.id,
        **semantic.to_dict(),
        "inference_inputs": ["explicit-glyph"],
        "ignored_inputs": ["class.state", "class.archived", "fate", "generic-color"],
    }


def annotate_connection(
    *,
    kind: str,
    source_grade: Grade,
    target_grade: Grade,
    spectral_sequence: str,
    claim_source_ref: str,
) -> ChartConnectionSemantic:
    """Validate a user-supplied multiplication/extension against Table 10.

    ``claim_source_ref`` is mandatory because Table 10 explains notation; it
    does not prove that the specific connection selected by the user exists.
    """

    normalized = str(kind).strip().lower().replace("_", "-")
    if normalized not in _CONNECTIONS:
        raise ChartSemanticError(
            "connection kind must be vertical-two, h1, h2, or hidden-extension."
        )
    if not isinstance(claim_source_ref, str) or not claim_source_ref.strip():
        raise ChartSemanticError(
            "A source locator for this specific candidate connection is required."
        )
    sequence = str(spectral_sequence).strip().lower()
    multiplier, expected, hidden = _CONNECTIONS[normalized]
    actual = _grade_difference(source_grade, target_grade)
    if normalized == "vertical-two":
        if actual != Grade():
            raise ChartSemanticError(
                "DKLLW vertical 2-multiplication connects two presentations in the same bidegree."
            )
    elif normalized in {"h1", "h2"}:
        if actual != expected:
            raise ChartSemanticError(
                f"{normalized} multiplication requires grade shift "
                f"({expected.stem},{expected.filtration})."
            )
    elif sequence not in {"2bss", "2-bss", "bockstein"}:
        raise ChartSemanticError(
            "The dashed hidden-extension key is restricted to the 2-Bockstein spectral sequence."
        )
    result_shift = actual if hidden else expected
    return ChartConnectionSemantic(
        kind=normalized,
        multiplier=multiplier,
        hidden_extension=hidden,
        target_shift=result_shift,
        spectral_sequence=sequence,
        claim_source_ref=claim_source_ref.strip(),
    )


def _grade_difference(source: Grade, target: Grade) -> Grade:
    keys = set(source.representation) | set(target.representation)
    representation = {
        key: target.representation.get(key, 0) - source.representation.get(key, 0)
        for key in keys
    }
    return Grade(
        target.stem - source.stem,
        target.filtration - source.filtration,
        {key: value for key, value in representation.items() if value},
    )
