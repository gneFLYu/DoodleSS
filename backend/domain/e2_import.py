"""Conservative, source-scoped import support for the Q8 HFPSS ``E2`` page.

The hand-drawn DoodleSS JSON format records presentation coordinates but has no
machine-readable statement of its workspace, grading convention, or source.
It is useful evidence for a reviewer, not an authority from which to create
classes.  This module consequently has two deliberately separate paths:

* :func:`review_legacy_e2_payload` only reports which legacy points *happen*
  to agree with the small, cited DKLLW24 catalogue.  It does not mutate a
  project.
* :func:`materialize_verified_e2_records` creates the finite set of
  source-backed representatives below.  It does not expand ``D``-periods or
  copy arbitrary legacy points.

The catalogue is D-localized.  It is not a claim that the listed finite set is
the unlocalized E2 page, nor a claim that the classes are permanent cycles.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Mapping

from .models import ClassNode, Grade, Proposition, Workspace


DKLLW_E2_IDENTIFICATION = (
    "DKLLW24, §3.2, final paragraph (PDF p. 19): by Lemma 2.12, the Q8-HFPSS(E2) "
    "page follows from Theorems 3.3 and 3.10."
)
INTEGER_TABLE_SOURCE = (
    "DKLLW24, Theorem 3.3 and Table 2 (integer-graded 2-BSS E∞ page, PDF p. 16); "
    + DKLLW_E2_IDENTIFICATION
)
SIGMA_TABLE_SOURCE = (
    "DKLLW24, Theorem 3.10 and Table 5 ((* - sigma_i)-graded 2-BSS E∞ page, PDF p. 18); "
    + DKLLW_E2_IDENTIFICATION
)
INTEGER_RELATION_SOURCE = (
    "DKLLW24, Table 3 (integer-graded relations, PDF p. 16); " + DKLLW_E2_IDENTIFICATION
)
SIGMA_RELATION_SOURCE = (
    "DKLLW24, Table 6 ((* - sigma_i)-graded relations, PDF p. 19); " + DKLLW_E2_IDENTIFICATION
)

WORKSPACE_IDS = {
    "integer": "ws_integer",
    "sigma_i": "ws_sigma_i",
}
E2_LOCALIZED_SCOPE = (
    "D-localized Q8-HFPSS E2 representative.  The source table is a 2-BSS E∞ presentation; "
    "DKLLW24 §3.2 identifies it with HFPSS(E2).  No D-periodic copies are imported."
)


@dataclass(frozen=True)
class VerifiedE2Class:
    """One explicitly listed, source-backed E2 representative."""

    id: str
    workspace_key: str
    label: str
    stem: int
    filtration: int
    representation: dict[str, int]
    source_ref: str
    scope: str = E2_LOCALIZED_SCOPE
    review_status: str = "source-verified"


@dataclass(frozen=True)
class VerifiedE2Relation:
    """A raw, cited relation retained until the algebra engine has an AST parser."""

    id: str
    workspace_key: str
    expression: str
    source_ref: str
    scope: str = E2_LOCALIZED_SCOPE
    review_status: str = "source-verified"


@dataclass(frozen=True)
class LegacyPoint:
    ordinal: int
    legacy_id: str
    label: str
    stem: int
    filtration: int
    page: int | None


@dataclass(frozen=True)
class LegacyPayloadIssue:
    ordinal: int
    reason: str


@dataclass(frozen=True)
class LegacyPointReview:
    point: LegacyPoint
    status: str
    reason: str
    verified_record_id: str | None = None


@dataclass
class E2ImportPlan:
    """A review artefact; constructing one never adds dots to a workspace."""

    workspace_key: str
    verified_catalogue: list[VerifiedE2Class] = field(default_factory=list)
    point_reviews: list[LegacyPointReview] = field(default_factory=list)
    payload_issues: list[LegacyPayloadIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verified_e2_classes(workspace_key: str | None = None) -> tuple[VerifiedE2Class, ...]:
    """Return only the finite representatives explicitly present in DKLLW24.

    The integer data are the multiplicative generators in Table 2.  The
    shifted data are the module generators in Table 5.  Both are restricted
    to the D-localized setting stated in §3 of the paper.
    """

    records = (
        VerifiedE2Class("e2_integer_k", "integer", "k", -4, 4, {}, INTEGER_TABLE_SOURCE),
        VerifiedE2Class("e2_integer_x2", "integer", "x^2", -2, 2, {}, INTEGER_TABLE_SOURCE),
        VerifiedE2Class("e2_integer_y2", "integer", "y^2", -2, 2, {}, INTEGER_TABLE_SOURCE),
        VerifiedE2Class("e2_integer_xh1", "integer", "xh_1", 0, 2, {}, INTEGER_TABLE_SOURCE),
        VerifiedE2Class("e2_integer_h1", "integer", "h_1", 1, 1, {}, INTEGER_TABLE_SOURCE),
        VerifiedE2Class("e2_integer_h2", "integer", "h_2", 3, 1, {}, INTEGER_TABLE_SOURCE),
        VerifiedE2Class("e2_integer_v12h1", "integer", "v_1^2h_1", 5, 1, {}, INTEGER_TABLE_SOURCE),
        VerifiedE2Class("e2_integer_D", "integer", "D", 8, 0, {}, INTEGER_TABLE_SOURCE),
        VerifiedE2Class("e2_integer_v14", "integer", "v_1^4", 8, 0, {}, INTEGER_TABLE_SOURCE),
        VerifiedE2Class(
            "e2_sigma_x2plusy2_usigma_i", "sigma_i", "\\{x^2+y^2\\}u_{\\sigma_i}", -2, 2,
            {"sigma_i": -1}, SIGMA_TABLE_SOURCE,
        ),
        VerifiedE2Class(
            "e2_sigma_xplusy_usigma_i", "sigma_i", "\\{x+y\\}u_{\\sigma_i}", -1, 1,
            {"sigma_i": -1}, SIGMA_TABLE_SOURCE,
        ),
        VerifiedE2Class(
            "e2_sigma_h1plusxv1_usigma_i", "sigma_i", "\\{h_1+xv_1\\}u_{\\sigma_i}", 1, 1,
            {"sigma_i": -1}, SIGMA_TABLE_SOURCE,
        ),
        VerifiedE2Class(
            "e2_sigma_v12_usigma_i", "sigma_i", "v_1^2u_{\\sigma_i}", 0, 2,
            {"sigma_i": -1}, SIGMA_TABLE_SOURCE,
        ),
    )
    if workspace_key is None:
        return records
    _validate_workspace_key(workspace_key)
    return tuple(record for record in records if record.workspace_key == workspace_key)


def verified_e2_relations(workspace_key: str | None = None) -> tuple[VerifiedE2Relation, ...]:
    """Return a small, executable-model-independent subset of the cited relations.

    The backend does not yet parse presentation relations into algebra ASTs, so
    these are retained as source propositions rather than silently treated as
    rewrite rules.  Each expression below is printed in Table 3 or Table 6.
    """

    records = (
        VerifiedE2Relation("e2_rel_integer_v14h2", "integer", "v_1^4h_2 = 0", INTEGER_RELATION_SOURCE),
        VerifiedE2Relation("e2_rel_integer_h1h2", "integer", "h_1h_2 = 0", INTEGER_RELATION_SOURCE),
        VerifiedE2Relation("e2_rel_integer_Dy2", "integer", "Dy^2 = h_2^2", INTEGER_RELATION_SOURCE),
        VerifiedE2Relation("e2_rel_integer_h14", "integer", "h_1^4 = v_1^4k", INTEGER_RELATION_SOURCE),
        VerifiedE2Relation("e2_rel_integer_h22x2", "integer", "h_2^2x^2 = 4kD", INTEGER_RELATION_SOURCE),
        VerifiedE2Relation("e2_rel_sigma_v12uh2", "sigma_i", "v_1^2u_{\\sigma_i}h_2 = 0", SIGMA_RELATION_SOURCE),
        VerifiedE2Relation("e2_rel_sigma_4v12uk", "sigma_i", "4v_1^2u_{\\sigma_i}k = 0", SIGMA_RELATION_SOURCE),
    )
    if workspace_key is None:
        return records
    _validate_workspace_key(workspace_key)
    return tuple(record for record in records if record.workspace_key == workspace_key)


def parse_legacy_generators(payload: Mapping[str, Any]) -> tuple[list[LegacyPoint], list[LegacyPayloadIssue]]:
    """Parse DoodleSS generators without attaching mathematical meaning to them."""

    raw_generators = payload.get("generators")
    if not isinstance(raw_generators, list):
        raise ValueError("A DoodleSS import payload must contain a 'generators' array.")

    points: list[LegacyPoint] = []
    issues: list[LegacyPayloadIssue] = []
    for ordinal, raw in enumerate(raw_generators):
        if not isinstance(raw, Mapping):
            issues.append(LegacyPayloadIssue(ordinal, "Generator is not an object."))
            continue
        label = raw.get("name")
        stem = raw.get("p")
        filtration = raw.get("q")
        if not isinstance(label, str) or not label.strip():
            issues.append(LegacyPayloadIssue(ordinal, "Generator has no nonempty string 'name'."))
            continue
        if isinstance(stem, bool) or not isinstance(stem, int):
            issues.append(LegacyPayloadIssue(ordinal, "Generator has no integer 'p' coordinate."))
            continue
        if isinstance(filtration, bool) or not isinstance(filtration, int):
            issues.append(LegacyPayloadIssue(ordinal, "Generator has no integer 'q' coordinate."))
            continue
        raw_page = raw.get("page")
        page = raw_page if isinstance(raw_page, int) and not isinstance(raw_page, bool) else None
        if raw_page is not None and page is None:
            issues.append(LegacyPayloadIssue(ordinal, "Generator has a non-integer page; it will require stage review."))
        points.append(LegacyPoint(
            ordinal=ordinal,
            legacy_id=str(raw.get("id", "")),
            label=label,
            stem=stem,
            filtration=filtration,
            page=page,
        ))
    return points, issues


def review_legacy_e2_payload(payload: Mapping[str, Any], workspace_key: str) -> E2ImportPlan:
    """Compare a legacy file with the cited catalogue without importing it.

    A legacy point is marked ``source-match`` only when its page is explicitly
    2 and its label and coordinates agree exactly (up to whitespace) with a
    verified DKLLW24 record.  Files with no per-generator page are not treated
    as E2 data merely because their filename suggests it.
    """

    _validate_workspace_key(workspace_key)
    points, issues = parse_legacy_generators(payload)
    catalogue = list(verified_e2_classes(workspace_key))
    index = {
        (record.stem, record.filtration, _normalise_label(record.label)): record
        for record in catalogue
    }
    reviews: list[LegacyPointReview] = []
    for point in points:
        if point.page is None:
            reviews.append(LegacyPointReview(
                point, "needs-stage-attestation",
                "The legacy JSON does not explicitly place this point on E2; no dot is eligible for import.",
            ))
            continue
        if point.page != 2:
            reviews.append(LegacyPointReview(
                point, "out-of-scope",
                f"The legacy point is marked E{point.page}, not E2.",
            ))
            continue
        record = index.get((point.stem, point.filtration, _normalise_label(point.label)))
        if record is None:
            reviews.append(LegacyPointReview(
                point, "needs-manual-review",
                "No exact DKLLW24 catalogue match.  Legacy JSON has no workspace, RO-grading, or source locator metadata.",
            ))
            continue
        reviews.append(LegacyPointReview(
            point, "source-match",
            "Coordinates and label agree with the cited finite DKLLW24 E2 catalogue; review still does not import periodic copies.",
            record.id,
        ))
    return E2ImportPlan(workspace_key, catalogue, reviews, issues)


def materialize_verified_e2_records(workspace: Workspace, workspace_key: str) -> dict[str, list[str]]:
    """Opt in to the cited catalogue, without using a legacy file's extra dots.

    The return value lists added or already-present class and proposition IDs,
    making a command-line import auditable and idempotent.
    """

    _validate_workspace_key(workspace_key)
    expected_workspace_id = WORKSPACE_IDS[workspace_key]
    if workspace.id != expected_workspace_id:
        raise ValueError(
            f"Verified {workspace_key} E2 records may only be materialized in {expected_workspace_id}, "
            f"not {workspace.id}."
        )

    result = {"added_classes": [], "existing_classes": [], "added_propositions": [], "existing_propositions": []}
    existing_classes = {
        (item.label, item.grade.stem, item.grade.filtration, _normalise_representation(item.grade.representation)): item
        for item in workspace.classes
    }
    existing_propositions = {item.id for item in workspace.propositions}
    for record in verified_e2_classes(workspace_key):
        key = (record.label, record.stem, record.filtration, _normalise_representation(record.representation))
        node = existing_classes.get(key)
        if node is None:
            node = ClassNode(
                id=record.id,
                label=record.label,
                expression=record.label,
                grade=Grade(record.stem, record.filtration, dict(record.representation)),
                page=2,
                state="unknown",
                notes=f"Source-verified E2 import. {record.scope}",
            )
            workspace.classes.append(node)
            existing_classes[key] = node
            result["added_classes"].append(node.id)
        else:
            result["existing_classes"].append(node.id)

        proposition_id = f"source_{record.id}"
        if proposition_id not in existing_propositions:
            workspace.propositions.append(Proposition(
                id=proposition_id,
                kind="source",
                statement=(
                    f"The D-localized Q8-HFPSS E2 representative {record.label} occurs at "
                    f"({record.stem}, {record.filtration})."
                ),
                status="established",
                conclusion={
                    "class_id": node.id,
                    "grade": {"stem": record.stem, "filtration": record.filtration, "representation": record.representation},
                    "scope": record.scope,
                },
                rule="DKLLW24 E2 source import",
                confidence=1.0,
                notes="The E2 source record does not assert survival beyond E2.",
                source_ref=record.source_ref,
                source_refs=[record.source_ref],
            ))
            existing_propositions.add(proposition_id)
            result["added_propositions"].append(proposition_id)
        else:
            result["existing_propositions"].append(proposition_id)

    for relation in verified_e2_relations(workspace_key):
        proposition_id = f"source_{relation.id}"
        if proposition_id in existing_propositions:
            result["existing_propositions"].append(proposition_id)
            continue
        workspace.propositions.append(Proposition(
            id=proposition_id,
            kind="relation",
            statement=relation.expression,
            status="established",
            conclusion={"relation": relation.expression, "scope": relation.scope},
            rule="DKLLW24 E2 source import",
            confidence=1.0,
            notes="Stored as a cited presentation relation; it is not yet an automatic algebra rewrite rule.",
            source_ref=relation.source_ref,
            source_refs=[relation.source_ref],
        ))
        existing_propositions.add(proposition_id)
        result["added_propositions"].append(proposition_id)
    return result


def materialize_verified_e2_records_for_project(project: Any, workspace_key: str) -> dict[str, list[str]]:
    """Convenience wrapper used by the opt-in CLI; deliberately no legacy input."""

    _validate_workspace_key(workspace_key)
    workspace = next((item for item in project.workspaces if item.id == WORKSPACE_IDS[workspace_key]), None)
    if workspace is None:
        raise ValueError(f"Project has no {WORKSPACE_IDS[workspace_key]} workspace.")
    return materialize_verified_e2_records(workspace, workspace_key)


def _normalise_label(label: str) -> str:
    return re.sub(r"\s+", "", label)


def _normalise_representation(representation: Mapping[str, int]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((str(key), int(value)) for key, value in representation.items() if int(value)))


def _validate_workspace_key(workspace_key: str) -> None:
    if workspace_key not in WORKSPACE_IDS:
        supported = ", ".join(sorted(WORKSPACE_IDS))
        raise ValueError(f"Unsupported E2 catalogue {workspace_key!r}; supported values are {supported}.")
