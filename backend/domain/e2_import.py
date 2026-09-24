"""Conservative, source-scoped import support for the Q8 HFPSS ``E2`` page.

The hand-drawn DoodleSS JSON format records presentation coordinates but has no
machine-readable statement of its workspace, grading convention, or source.
It is useful evidence for a reviewer, not an authority from which to create
classes.  This module consequently has two deliberately separate paths:

* :func:`review_legacy_e2_payload` only reports which legacy points *happen*
  to agree with the small, cited DKLLW24 catalogue.  It does not mutate a
  project.
* :func:`materialize_verified_e2_records` creates the chart-verified finite
  fundamental domain below.  It enumerates every occupied bidegree instead of
  asking the browser to reconstruct the page from algebra generators.

The catalogue uses eight consecutive D-residues (a 64-stem fundamental domain)
and filtration 0 through 3.  The chart renderer applies the independent
``g=kD^3`` shift (20,4).  Thus the orientable and nonorientable Thom patterns
have 88 and 96 explicit bidegree representatives respectively, and no runtime
algebraic closure is required.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Mapping

from .models import ClassNode, Grade, Project, Proposition, Workspace


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
E2_CHART_SOURCE = (
    "DKLLW24, Figures 4-5 and Tables 10-11 (integer and (*-sigma_i) E2 charts; "
    "multiplication-line key), journal PDF pp. 50-52"
)

WORKSPACE_IDS = {
    "integer": "ws_integer",
    "sigma_i": "ws_sigma_i",
}
E2_LOCALIZED_SCOPE = (
    "D-localized Q8-HFPSS E2 representative in an explicitly enumerated D^8 by kD^3 "
    "fundamental domain. The source table is a 2-BSS E∞ presentation; DKLLW24 §3.2 "
    "identifies it with HFPSS(E2)."
)

_PERIODIC_EDGE_MOTIFS = {
    "integer": (
        ("I00", "I11", "h1"), ("I00", "I31", "h2"),
        ("I40", "I51", "h1"), ("I11", "I22H", "h1"),
        ("I31", "I62Y", "h2"), ("I51", "I62V", "h1"),
        ("I02", "I13", "h1"),
        ("I22H", "I33", "h1"), ("I62X", "I73", "h1"),
        ("I62Y", "I13", "h2"), ("I62X", "I13X", "h2"),
        ("I62V", "I73V", "h1"),
    ),
    "sigma_i": (
        ("S00", "S11", "h1"),
        ("S40", "S51", "h1"),
        ("S51", "S62", "h1"),
        ("S71", "S02", "h1"), ("S71", "S22Y", "h2"),
        ("S11", "S22H", "h1"), ("S02", "S13", "h1"),
        ("S22H", "S33", "h1"), ("S22Y", "S53", "h2"),
        ("S62", "S73", "h1"), ("S62", "S13", "h2"),
    ),
}


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
    glyph: str = "dot"
    pattern_key: str = ""
    d_power: int = 0
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


def _power(symbol: str, exponent: int) -> str:
    if exponent == 0:
        return ""
    if exponent == 1:
        return symbol
    return f"{symbol}^{{{exponent}}}"


def _product(base: str, symbol: str, exponent: int) -> str:
    return f"{base}{_power(symbol, exponent)}" if exponent else base


def _power_id(exponent: int) -> str:
    return f"m{-exponent}" if exponent < 0 else f"p{exponent}"


def _render_d_label(template: str, *, d: int, dp1: int, dm1: int) -> str:
    result = template
    for token, exponent in (("@dm1@", dm1), ("@dp1@", dp1), ("@d@", d)):
        result = result.replace(f"D^{{{token}}}", _power("D", exponent))
    return result or "1"


def _enumerated_pattern(
    workspace_key: str,
    source_ref: str,
    representation: dict[str, int],
    motifs: tuple[tuple[int, int, str, str, str], ...],
) -> tuple[VerifiedE2Class, ...]:
    records: list[VerifiedE2Class] = []
    historical_ids = {
        ("integer", "I11", 0): "e2_integer_h1",
        ("integer", "I31", 0): "e2_integer_h2",
        ("integer", "I51", 0): "e2_integer_v12h1",
        ("integer", "I02", 0): "e2_integer_xh1",
        ("integer", "I62X", -1): "e2_integer_x2",
        ("sigma_i", "S11", 0): "e2_sigma_h1plusxv1_usigma_i",
        ("sigma_i", "S40", 0): "e2_sigma_v12_usigma_i",
        ("sigma_i", "S62", -1): "e2_sigma_x2plusy2_usigma_i",
    }
    # Eight consecutive residues are deliberately materialized. D^8, rather
    # than a fragile D/D^2/D^4 page period, is the permanent horizontal period.
    for d_power in range(-3, 5):
        for stem_residue, filtration, pattern_key, label_template, glyph in motifs:
            stem = stem_residue + 8 * d_power
            label = _render_d_label(
                label_template, d=d_power, dp1=d_power + 1, dm1=d_power - 1,
            )
            record_id = historical_ids.get(
                (workspace_key, pattern_key, d_power),
                f"e2_{workspace_key}_cell_{pattern_key}_s{stem_residue}_f{filtration}_d{_power_id(d_power)}",
            )
            records.append(VerifiedE2Class(
                id=record_id,
                workspace_key=workspace_key,
                label=label,
                stem=stem,
                filtration=filtration,
                representation=dict(representation),
                source_ref=source_ref,
                glyph=glyph,
                pattern_key=pattern_key,
                d_power=d_power,
            ))
    return tuple(records)


def verified_e2_classes(workspace_key: str | None = None) -> tuple[VerifiedE2Class, ...]:
    """Return the two fully enumerated DKLLW24 E2 chart patterns.

    These are occupied bidegrees in a ``D^8`` by ``g=kD^3`` fundamental
    domain, not merely multiplicative/module generators.  Labels describe a
    convenient presentation of the cell; ``glyph`` records its completed
    coefficient pattern independently of its spectral-sequence fate.
    """

    integer_motifs = (
        (0, 0, "I00", r"D^{@d@}", "witt-j-series"),
        (4, 0, "I40", r"v_1^6D^{@dm1@}", "j-positive-series"),
        (1, 1, "I11", r"h_1D^{@d@}", "j-series"),
        (3, 1, "I31", r"h_2D^{@d@}", "dot"),
        (5, 1, "I51", r"v_1^2h_1D^{@d@}", "j-series"),
        (0, 2, "I02", r"xh_1D^{@d@}", "dot"),
        # Each algebra class gets its own column.  A comma-brace label looks
        # like one basis vector or one linear combination and loses the
        # multiplicity visible in the published chart.
        (2, 2, "I22H", r"h_1^2D^{@d@}", "j-series"),
        (6, 2, "I62X", r"x^2D^{@dp1@}", "dot"),
        (6, 2, "I62Y", r"y^2D^{@dp1@}", "dot"),
        (6, 2, "I62V", r"v_1^2h_1^2D^{@d@}", "j-series"),
        (1, 3, "I13", r"xh_1^2D^{@d@}", "dot"),
        (1, 3, "I13X", r"x^2h_2D^{@d@}", "dot"),
        (3, 3, "I33", r"h_1^3D^{@d@}", "j-series"),
        (7, 3, "I73", r"x^2h_1D^{@dp1@}", "dot"),
        (7, 3, "I73V", r"v_1^2h_1^3D^{@d@}", "j-series"),
    )
    sigma_motifs = (
        # These twelve occupied cells are read directly from DKLLW24 Figure 7
        # (sigma E2), not inferred from the four module generators alone.
        (0, 0, "S00", r"v_1^4D^{@dm1@}u_{\sigma_i}", "witt-j-series"),
        (4, 0, "S40", r"v_1^2D^{@d@}u_{\sigma_i}", "witt-j-series"),
        (1, 1, "S11", r"(h_1+xv_1)D^{@d@}u_{\sigma_i}", "j-series"),
        (5, 1, "S51", r"v_1^2h_1D^{@d@}u_{\sigma_i}", "j-series"),
        # a_sigma_i is exactly the (x+y)u_sigma_i cell; use the semantic
        # Euler-class name so Thom transport keeps a_sigma_j/a_sigma_k visible
        # without creating a second dot in the same cell.
        (7, 1, "S71", r"a_{\sigma_i}D^{@dp1@}", "dot"),
        (0, 2, "S02", r"(x+y)h_1D^{@d@}u_{\sigma_i}", "dot"),
        (2, 2, "S22Y", r"(yh_2+xh_1v_1)D^{@d@}u_{\sigma_i}", "dot"),
        (2, 2, "S22H", r"(h_1^2+xh_1v_1)D^{@d@}u_{\sigma_i}", "j-series"),
        (6, 2, "S62", r"(x^2+y^2)D^{@dp1@}u_{\sigma_i}", "dot"),
        (6, 2, "S62V", r"v_1^2h_1^2D^{@d@}u_{\sigma_i}", "j-series"),
        (1, 3, "S13", r"(x+y)h_1^2D^{@d@}u_{\sigma_i}", "dot"),
        (3, 3, "S33", r"h_1^3D^{@d@}u_{\sigma_i}", "j-series"),
        (5, 3, "S53", r"x^3D^{@dp1@}u_{\sigma_i}", "dot"),
        (7, 3, "S73", r"x^2h_1D^{@dp1@}u_{\sigma_i}", "dot"),
        (7, 3, "S73V", r"v_1^2h_1^3D^{@d@}u_{\sigma_i}", "j-series"),
    )
    records = (
        *_enumerated_pattern("integer", INTEGER_TABLE_SOURCE, {}, integer_motifs),
        *_enumerated_pattern("sigma_i", SIGMA_TABLE_SOURCE, {"sigma_i": -1}, sigma_motifs),
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
    # Table-generator names remain valid audit aliases even though the chart
    # catalogue is now cell-based.  They resolve to the one enumerated cell
    # that contains the generator; they never create a second dot.
    generator_aliases = {
        "integer": {
            (-4, 4, "k"): ("I00", -24, 0),
            (-2, 2, "x^2"): ("I62X", -2, 2),
            (-2, 2, "y^2"): ("I62Y", -2, 2),
            (0, 2, "xh_1"): ("I02", 0, 2),
            (1, 1, "h_1"): ("I11", 1, 1),
            (3, 1, "h_2"): ("I31", 3, 1),
            (5, 1, "v_1^2h_1"): ("I51", 5, 1),
            (8, 0, "D"): ("I00", 8, 0),
            (8, 0, "v_1^4"): ("I00", 8, 0),
        },
        "sigma_i": {
            (-2, 2, r"\{x^2+y^2\}u_{\sigma_i}"): ("S62", -2, 2),
            (-2, 2, r"(x^2+y^2)u_{\sigma_i}"): ("S62", -2, 2),
            (-1, 1, r"\{x+y\}u_{\sigma_i}"): ("S71", -1, 1),
            (-1, 1, r"(x+y)u_{\sigma_i}"): ("S71", -1, 1),
            (1, 1, r"\{h_1+xv_1\}u_{\sigma_i}"): ("S11", 1, 1),
            (1, 1, r"(h_1+xv_1)u_{\sigma_i}"): ("S11", 1, 1),
            (4, 0, r"v_1^2u_{\sigma_i}"): ("S40", 4, 0),
        },
    }[workspace_key]
    by_pattern_grade = {
        (record.pattern_key, record.stem, record.filtration): record
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
        normalized_label = _normalise_label(point.label)
        record = index.get((point.stem, point.filtration, normalized_label))
        if record is None:
            alias_target = generator_aliases.get((point.stem, point.filtration, normalized_label))
            if alias_target is not None:
                record = by_pattern_grade.get(alias_target)
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

    rendering = workspace.settings.setdefault("rendering", {})
    # D is a valid E2 period, but all eight D-residues are already explicit in
    # this catalogue. Rendering by D again would stack eight copies of every
    # cell. Preserve D as mathematical metadata and render the enumerated
    # horizontal domain only by its permanent D^8 period.
    rendering["enumerated_horizontal_period"] = 64
    rendering["enumerated_e2_pattern"] = workspace_key

    catalogue = verified_e2_classes(workspace_key)
    desired_class_ids = {item.id for item in catalogue}
    stale_prefix = f"e2_{workspace_key}_"
    stale_class_ids = {
        item.id for item in workspace.classes
        if item.id.startswith(stale_prefix) and item.id not in desired_class_ids
    }
    if stale_class_ids:
        reason = (
            "Retired generated E2 motif after source-schema correction. "
            "Original class ID and user claims are retained; this is not a spectral-sequence death."
        )
        for item in workspace.classes:
            if item.id in stale_class_ids and not item.archived:
                item.archived = True
                item.archived_reason = reason
        for item in workspace.propositions:
            references_stale = any(item.conclusion.get(field) in stale_class_ids
                                   for field in ("class_id", "source_id", "target_id"))
            if (references_stale and item.id.startswith("source_e2_")
                    and item.rule.startswith("DKLLW24 E2")):
                item.status = "superseded"
                item.conclusion["source_schema_retirement"] = reason

    result = {
        "added_classes": [], "existing_classes": [], "removed_classes": [], "restored_classes": [],
        "archived_classes": sorted(stale_class_ids),
        "added_propositions": [], "existing_propositions": [],
    }
    existing_classes = {
        (item.label, item.grade.stem, item.grade.filtration, _normalise_representation(item.grade.representation)): item
        for item in workspace.classes if item.id not in stale_class_ids
    }
    existing_classes_by_id = {item.id: item for item in workspace.classes}
    existing_propositions = {item.id for item in workspace.propositions}
    nodes_by_record_id: dict[str, ClassNode] = {}
    for record in catalogue:
        key = (record.label, record.stem, record.filtration, _normalise_representation(record.representation))
        node = existing_classes.get(key)
        if node is None:
            node = existing_classes_by_id.get(record.id)
            if node is not None:
                node.label = record.label
                node.expression = record.label
                node.grade = Grade(record.stem, record.filtration, dict(record.representation))
        if (
            node is None and workspace_key == "sigma_i" and record.pattern_key == "S71"
            and record.stem == -1 and record.filtration == 1
        ):
            node = next((item for item in workspace.classes if item.id == "sig_a"), None)
            if node is not None:
                node.expression = record.label
                node.notes = (
                    r"The Euler class is this Table-5 cell: "
                    r"a_{\sigma_i}=\{x+y\}u_{\sigma_i}. It is one class, not two stacked dots."
                )
        if node is None:
            series_style = _series_style(record)
            node = ClassNode(
                id=record.id,
                label=record.label,
                expression=record.label,
                grade=Grade(record.stem, record.filtration, dict(record.representation)),
                page=2,
                state="unknown",
                notes=(
                    f"Source-verified enumerated E2 cell ({record.pattern_key}). {record.scope} "
                    "Its glyph records the completed j-series type, not its page fate."
                ),
                style={
                    "dkllw_glyph": record.glyph,
                    "module_pattern": record.glyph,
                    "e2_pattern": record.pattern_key,
                    "e2_d_power": record.d_power,
                    "multiplicative_unit": (
                        workspace_key == "integer"
                        and record.pattern_key == "I00"
                        and record.d_power == 0
                    ),
                    **series_style,
                },
            )
            workspace.classes.append(node)
            existing_classes[key] = node
            existing_classes_by_id[node.id] = node
            result["added_classes"].append(node.id)
        else:
            result["existing_classes"].append(node.id)
            node.style.update({
                "dkllw_glyph": record.glyph,
                "module_pattern": record.glyph,
                "e2_pattern": record.pattern_key,
                "e2_d_power": record.d_power,
                "multiplicative_unit": (
                    workspace_key == "integer"
                    and record.pattern_key == "I00"
                    and record.d_power == 0
                ),
                **_series_style(record),
            })
        if _restore_source_audit_archive(node, record.source_ref):
            result["restored_classes"].append(node.id)
        nodes_by_record_id[record.id] = node

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
            proposition = next(item for item in workspace.propositions if item.id == proposition_id)
            proposition.statement = (
                f"The D-localized Q8-HFPSS E2 representative {record.label} occurs at "
                f"({record.stem}, {record.filtration})."
            )
            proposition.conclusion.update({
                "class_id": node.id,
                "grade": {"stem": record.stem, "filtration": record.filtration, "representation": record.representation},
                "scope": record.scope,
            })
            proposition.source_ref = record.source_ref
            proposition.source_refs = [record.source_ref]

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

    records_by_pattern_and_grade = {
        (record.pattern_key, record.stem, record.filtration): record
        for record in catalogue
    }
    shifts = {"h1": (1, 1, "h_1"), "h2": (3, 1, "h_2")}
    desired_edge_ids: set[str] = set()
    for source_record in catalogue:
        for source_pattern, target_pattern, kind in _PERIODIC_EDGE_MOTIFS[workspace_key]:
            if source_record.pattern_key != source_pattern:
                continue
            stem_shift, filtration_shift, multiplier = shifts[kind]
            target_record = records_by_pattern_and_grade.get((
                target_pattern,
                source_record.stem + stem_shift,
                source_record.filtration + filtration_shift,
            ))
            if target_record is None:
                continue
            proposition_id = f"source_e2_edge_{source_record.id}_{kind}"
            desired_edge_ids.add(proposition_id)
            if proposition_id in existing_propositions:
                proposition = next(item for item in workspace.propositions if item.id == proposition_id)
                _refresh_e2_edge(proposition, nodes_by_record_id[source_record.id],
                                 nodes_by_record_id[target_record.id], multiplier)
                result["existing_propositions"].append(proposition_id)
                continue
            workspace.propositions.append(Proposition(
                id=proposition_id,
                kind="relation",
                statement=(
                    f"{multiplier} multiplication: {source_record.label} to {target_record.label}"
                ),
                status="established",
                conclusion={
                    "source_id": nodes_by_record_id[source_record.id].id,
                    "target_id": nodes_by_record_id[target_record.id].id,
                    "page": 2,
                    "chart_connection": {
                        "kind": kind,
                        "multiplier": multiplier,
                        "hidden_extension": False,
                        "status": "source-chart",
                    },
                    "period_scope": ["D^8", "kD^3"],
                },
                rule="DKLLW24 E2 chart enumeration",
                confidence=1.0,
                notes="An explicitly enumerated chart edge; the renderer applies the same period lattice as its endpoints.",
                source_ref=E2_CHART_SOURCE,
                source_refs=[E2_CHART_SOURCE],
            ))
            existing_propositions.add(proposition_id)
            result["added_propositions"].append(proposition_id)
    result["superseded_propositions"] = _retire_obsolete_e2_edges(
        workspace, desired_edge_ids, "DKLLW24 E2 chart enumeration"
    )
    return result


def _restore_source_audit_archive(node: ClassNode, source_ref: str) -> bool:
    # Only the old missing-source quarantine is discharged by an exact cited
    # catalogue match. Manual archives and retired, incorrect motifs stay so.
    reason = "Archived during source audit: active local display point had no source locator or notes."
    if not node.archived or node.archived_reason != reason:
        return False
    node.style["source_audit_restoration"] = {"archived_reason": reason, "source_ref": source_ref}
    node.archived = False
    node.archived_reason = ""
    return True


def _refresh_e2_edge(proposition: Proposition, source: ClassNode, target: ClassNode, multiplier: str) -> None:
    # Endpoint IDs can change when a generated motif is retired or an exact
    # existing class is reused. Refresh only our own source-backed edges.
    if proposition.kind != "relation" or proposition.rule not in {
        "DKLLW24 E2 chart enumeration", "ThomIsomorphism + DKLLW24 E2 chart",
    }:
        return
    if (proposition.conclusion.get("source_id"), proposition.conclusion.get("target_id")) != (source.id, target.id):
        proposition.conclusion.setdefault("source_schema_rebinding", {
            "previous_source_id": proposition.conclusion.get("source_id"),
            "previous_target_id": proposition.conclusion.get("target_id"),
            "previous_status": proposition.status,
        })
    proposition.statement = f"{multiplier} multiplication: {source.label} to {target.label}"
    proposition.conclusion.update({"source_id": source.id, "target_id": target.id})
    proposition.conclusion.setdefault("chart_connection", {}).update({
        "kind": multiplier.replace("_", ""), "multiplier": multiplier, "hidden_extension": False,
    })
    retirement = proposition.conclusion.pop("source_schema_retirement", None)
    if retirement and proposition.status == "superseded":
        proposition.status = "established"


def _retire_obsolete_e2_edges(workspace: Workspace, desired_ids: set[str], rule: str) -> list[str]:
    """Retain old generated edges as provenance, not as active products.

    Schema changes can replace an edge ID even when both endpoint classes
    survive (the old S71 -> S40 edge is one example). Endpoint retirement
    alone therefore cannot determine which generated edges are current.
    Ownership requires both the generator's namespace and its exact rule;
    manual relations and independently documented extensions are untouched.
    """

    retired: list[str] = []
    for proposition in workspace.propositions:
        if (proposition.kind != "relation" or proposition.rule != rule
                or not proposition.id.startswith("source_e2_edge_")
                or proposition.id in desired_ids):
            continue
        if proposition.status == "superseded":
            continue
        proposition.conclusion.setdefault("source_schema_retirement_previous_status", proposition.status)
        proposition.conclusion["source_schema_retirement"] = (
            "Retired obsolete generated E2 multiplication edge after source-schema correction. "
            "Its ID is absent from the current cited motif catalogue; original endpoints and "
            "claim are retained for review. This is not a spectral-sequence differential."
        )
        proposition.status = "superseded"
        retired.append(proposition.id)
    return retired


def _series_style(record: VerifiedE2Class) -> dict[str, Any]:
    """Attach the non-constant lower bound of a completed ``j``-series.

    A hollow circle is not one fixed copy of ``j k[[j]]`` along the whole
    chart.  In the chosen D^8 fundamental domain the bottom of its h1 tower
    rises by one j-grading every four stems.  D^8 starts the same object orbit
    again, while a forward g-translate is allowed to change the displayed
    lower order.  The browser evaluates this rule lazily for every visible
    occurrence, so no infinite tower is eagerly materialized.
    """

    if record.glyph != "j-positive-series":
        return {}
    return {
        "series_parameter": "j=v_1^4D^{-1}",
        "series_kind": "h1-truncated-j-adic",
        "series_base_order": 1,
        "series_origin_stem": -20,
        "series_stem_step": 4,
        "series_bottom_loss_per_step": 1,
        "series_object_period_stem": 64,
        "series_rule": "the h_1-tower loses one bottom j-grading every four stems",
    }


def _thom_suffix(a: int, b: int) -> str:
    terms: list[str] = []
    if a:
        terms.append(r"\sigma_i" if a == 1 else rf"{a}\sigma_i")
    if b:
        terms.append(r"\sigma_j" if b == 1 else rf"{b}\sigma_j")
    return "+".join(terms)


def _transported_label(label: str, pattern_key: str, a: int, b: int) -> str:
    """Name a Thom-transported chart cell without claiming a new relation."""

    if (a, b) == (0, 0):
        return label
    suffix = _thom_suffix(a, b)
    if pattern_key == "sigma_i":
        return (
            label.replace(r"u_{\sigma_i}", rf"u_{{{suffix}}}")
            .replace(r"a_{\sigma_i}", rf"a_{{{suffix}}}")
            .replace(r"\Theta_i", rf"\Theta_{{{suffix}}}")
            .replace(r"\mathcal M_{i;", rf"\mathcal M_{{{suffix};")
        )
    if label == "1":
        return rf"u_{{{suffix}}}"
    return rf"\left({label}\right)u_{{{suffix}}}"


def materialize_all_q8_thom_e2_patterns(project: Project) -> Project:
    """Enumerate the two Thom E2 patterns in all sixteen stored sectors.

    A sum of sign representations is orientable exactly when both independent
    determinant characters occur evenly.  Hence sectors with even ``a`` and
    even ``b`` use the integer pattern; the other twelve use the single-sign
    pattern.  This is a chart transport only: it neither copies later-page
    differentials nor identifies mixed sectors under an unsupported S3 action.
    """

    if project.id != "hfpss_studio":
        return project
    workspaces = {item.id: item for item in project.workspaces}
    for sector in project.grading_sectors:
        workspace = workspaces.get(sector.workspace_id)
        if workspace is None:
            continue
        pattern_key = "integer" if sector.a % 2 == 0 and sector.b % 2 == 0 else "sigma_i"
        if (sector.a, sector.b) == (0, 0):
            materialize_verified_e2_records(workspace, "integer")
            continue
        if (sector.a, sector.b) == (1, 0):
            materialize_verified_e2_records(workspace, "sigma_i")
            continue

        rendering = workspace.settings.setdefault("rendering", {})
        rendering["enumerated_horizontal_period"] = 64
        rendering["enumerated_e2_pattern"] = pattern_key
        rendering["thom_sector"] = sector.id
        workspace.settings["e2_thom_pattern"] = (
            "orientable" if pattern_key == "integer" else "nonorientable"
        )
        representation = {key: value for key, value in {
            "sigma_i": -sector.a,
            "sigma_j": -sector.b,
        }.items() if value}
        prefix = f"e2_thom_a{sector.a}_b{sector.b}_"
        base_catalogue = verified_e2_classes(pattern_key)
        desired_transported_ids = {f"{prefix}{record.id}" for record in base_catalogue}
        stale_transported_ids = {
            item.id for item in workspace.classes
            if item.id.startswith(prefix) and item.id not in desired_transported_ids
        }
        if stale_transported_ids:
            reason = (
                "Retired generated Thom E2 motif after source-schema correction. "
                "Original class ID, claims and differentials are retained; this is not a spectral-sequence death."
            )
            for item in workspace.classes:
                if item.id in stale_transported_ids and not item.archived:
                    item.archived = True
                    item.archived_reason = reason
            for item in workspace.propositions:
                references_stale = any(item.conclusion.get(field) in stale_transported_ids
                                       for field in ("class_id", "source_id", "target_id"))
                if (references_stale and item.id.startswith("source_e2_")
                        and item.rule.startswith("ThomIsomorphism")):
                    item.status = "superseded"
                    item.conclusion["source_schema_retirement"] = reason
        existing = {
            (item.label, item.grade.stem, item.grade.filtration): item
            for item in workspace.classes if item.id not in stale_transported_ids
        }
        existing_by_id = {item.id: item for item in workspace.classes}
        nodes: dict[tuple[str, int, int], ClassNode] = {}
        proposition_ids = {item.id for item in workspace.propositions}

        desired_edge_ids: set[str] = set()
        for record in base_catalogue:
            label = _transported_label(record.label, pattern_key, sector.a, sector.b)
            key = (label, record.stem, record.filtration)
            node = existing.get(key)
            transported_id = f"{prefix}{record.id}"
            if node is None:
                node = existing_by_id.get(transported_id)
                if node is not None:
                    node.label = label
                    node.expression = label
                    node.grade = Grade(record.stem, record.filtration, dict(representation))
            if node is None:
                node = ClassNode(
                    id=transported_id,
                    label=label,
                    expression=label,
                    grade=Grade(record.stem, record.filtration, dict(representation)),
                    page=2,
                    notes=(
                        f"Thom-transported {workspace.settings['e2_thom_pattern']} E2 cell "
                        f"({record.pattern_key}) in {sector.display_label}. The transport copies "
                        "the E2 pattern only; later differentials remain sector-specific."
                    ),
                    style={
                        "dkllw_glyph": record.glyph,
                        "module_pattern": record.glyph,
                        "e2_pattern": record.pattern_key,
                        "e2_d_power": record.d_power,
                        "thom_pattern": workspace.settings["e2_thom_pattern"],
                        **_series_style(record),
                    },
                )
                workspace.classes.append(node)
                existing[key] = node
                existing_by_id[node.id] = node
            else:
                node.style.update({
                    "dkllw_glyph": record.glyph,
                    "module_pattern": record.glyph,
                    "e2_pattern": record.pattern_key,
                    "e2_d_power": record.d_power,
                    "thom_pattern": workspace.settings["e2_thom_pattern"],
                    **_series_style(record),
                })
            _restore_source_audit_archive(node, record.source_ref)
            nodes[(record.pattern_key, record.stem, record.filtration)] = node
            proposition_id = f"source_{node.id}"
            if proposition_id not in proposition_ids:
                workspace.propositions.append(Proposition(
                    id=proposition_id,
                    kind="source",
                    statement=(
                        f"Thom transport places {label} at ({record.stem}, {record.filtration}) "
                        f"in {sector.display_label}."
                    ),
                    status="established",
                    conclusion={"class_id": node.id, "thom_pattern": workspace.settings["e2_thom_pattern"]},
                    rule="ThomIsomorphism + DKLLW24 E2 pattern",
                    confidence=1.0,
                    notes="Only the E2 additive/chart pattern is transported.",
                    source_ref=record.source_ref,
                    source_refs=[record.source_ref],
                ))
                proposition_ids.add(proposition_id)

        shifts = {"h1": (1, 1, "h_1"), "h2": (3, 1, "h_2")}
        for record in base_catalogue:
            for source_pattern, target_pattern, kind in _PERIODIC_EDGE_MOTIFS[pattern_key]:
                if record.pattern_key != source_pattern:
                    continue
                ds, df, multiplier = shifts[kind]
                source_node = nodes.get((source_pattern, record.stem, record.filtration))
                target_node = nodes.get((target_pattern, record.stem + ds, record.filtration + df))
                if source_node is None or target_node is None:
                    continue
                proposition_id = f"source_e2_edge_{source_node.id}_{kind}"
                desired_edge_ids.add(proposition_id)
                if proposition_id in proposition_ids:
                    proposition = next(item for item in workspace.propositions if item.id == proposition_id)
                    _refresh_e2_edge(proposition, source_node, target_node, multiplier)
                    continue
                workspace.propositions.append(Proposition(
                    id=proposition_id,
                    kind="relation",
                    statement=f"{multiplier} multiplication: {source_node.label} to {target_node.label}",
                    status="established",
                    conclusion={
                        "source_id": source_node.id,
                        "target_id": target_node.id,
                        "page": 2,
                        "chart_connection": {
                            "kind": kind, "multiplier": multiplier, "hidden_extension": False,
                            "status": "thom-transported",
                        },
                        "period_scope": ["D^8", "kD^3"],
                    },
                    rule="ThomIsomorphism + DKLLW24 E2 chart",
                    confidence=1.0,
                    notes="Multiplication line transported with the E2 Thom pattern.",
                    source_ref=E2_CHART_SOURCE,
                    source_refs=[E2_CHART_SOURCE],
                ))
                proposition_ids.add(proposition_id)
        _retire_obsolete_e2_edges(workspace, desired_edge_ids, "ThomIsomorphism + DKLLW24 E2 chart")
    return project


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
