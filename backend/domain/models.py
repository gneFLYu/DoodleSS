"""Domain objects for a proof-aware RO(G)-graded spectral-sequence workspace."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, TypeVar
from uuid import uuid4


SCHEMA_VERSION = 6


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


@dataclass
class Grade:
    stem: int = 0
    filtration: int = 0
    representation: dict[str, int] = field(default_factory=dict)

    def shifted(self, other: "Grade") -> "Grade":
        representation = dict(self.representation)
        for key, value in other.representation.items():
            representation[key] = representation.get(key, 0) + value
            if representation[key] == 0:
                del representation[key]
        return Grade(self.stem + other.stem, self.filtration + other.filtration, representation)


@dataclass
class CoefficientContext:
    id: str
    residue_field: str = "F4"
    coefficient_ring: str = "W(F4)"
    bockstein_stage: str | None = None
    scalar_mode: str = "2_adic"  # residue | 2_adic | formal
    source_ref: str = ""


@dataclass
class ScalarValue:
    coefficient_context_id: str
    field_part: dict[str, int] | None = None
    two_adic_valuation: int | None = None
    presentation: str = "unknown"  # exact | quotient | unknown


@dataclass
class SymbolDefinition:
    id: str
    symbol: str
    grade: Grade = field(default_factory=Grade)
    aliases: list[str] = field(default_factory=list)
    coefficient_context_id: str = "q8-witt-f4"
    normalization: str = ""
    source_ref: str = ""


@dataclass
class ClassNode:
    id: str
    label: str
    grade: Grade
    page: int = 2
    state: str = "unknown"  # legacy display cache; ClassFate is authoritative
    notes: str = ""
    style: dict[str, Any] = field(default_factory=dict)
    period_stem: int = 0
    period_filtration: int = 0
    expression: str = ""
    coefficient_context_id: str = "q8-witt-f4"
    convention_id: str = "q8-thesis-plotted-v1"
    sector_id: str | None = None
    archived: bool = False
    archived_reason: str = ""
    periodicity_rule_id: str | None = None
    periodicity_anchor_class_id: str | None = None
    periodicity_translation: int = 0
    manual_periodicity_id: str | None = None
    manual_periodicity_anchor_class_id: str | None = None
    manual_periodicity_translation: int = 0
    manual_periodicity_exponents: list[int] = field(default_factory=list)


@dataclass
class Differential:
    id: str
    source_id: str
    target_id: str
    page: int
    status: str = "claimed"
    label: str = ""
    period_stem: int = 0
    period_filtration: int = 0
    proposition_id: str = ""
    period_family_id: str | None = None
    period_translation: list[int] = field(default_factory=list)
    anchor_differential_id: str | None = None
    period_notes: str = ""
    unperiodic_reason: str = ""
    periodicity_rule_id: str | None = None
    manual_periodicity_id: str | None = None
    manual_periodicity_translation: int = 0
    manual_periodicity_exponents: list[int] = field(default_factory=list)


@dataclass
class DifferentialEvent:
    id: str
    spectral_sequence: str  # hfpss | tate
    page: int
    role: str  # supports | receives
    class_id: str
    counterpart_class_id: str
    differential_claim_id: str
    source_filtration: int
    target_filtration: int
    source_exists_in_hfpss: bool | None = True
    comparison_status: str = "transports_to_hfpss"
    proposition_id: str = ""
    source_refs: list[str] = field(default_factory=list)
    status: str = "claimed"


@dataclass
class ClassFate:
    class_id: str
    appears_from_page: int = 2
    hfpss_outgoing_events: list[str] = field(default_factory=list)
    hfpss_incoming_events: list[str] = field(default_factory=list)
    tate_outgoing_events: list[str] = field(default_factory=list)
    tate_incoming_events: list[str] = field(default_factory=list)
    first_hfpss_death: dict[str, Any] | None = None
    last_hfpss_live_page: int | str = "unknown"
    conclusion: str = "unresolved"
    conclusion_page: int | str | None = None
    justification_ids: list[str] = field(default_factory=list)


@dataclass
class Proposition:
    id: str
    kind: str
    statement: str
    status: str = "claimed"
    conclusion: dict[str, Any] = field(default_factory=dict)
    premise_ids: list[str] = field(default_factory=list)
    rule: str = "manual"
    confidence: float = 1.0
    notes: str = ""
    source_ref: str = ""
    source_refs: list[str] = field(default_factory=list)
    convention_id: str = "q8-thesis-plotted-v1"
    hypotheses: list[str] = field(default_factory=list)
    verification_checks: list[str] = field(default_factory=list)
    reviewer: str = ""
    reviewed_at: str | None = None
    supersedes_id: str | None = None


def default_workspace_settings() -> dict[str, Any]:
    return {
        "vanishing_line": 0,
        "vanishing_line_source": "No source-scoped vanishing-line certificate has been selected.",
        "page_limit": 25,
        "grid": {"stem_min": -8, "stem_max": 32, "filtration_min": 0, "filtration_max": 28},
        "rendering": {"buffer_cells": 6, "base_cell": 28, "periodicity": []},
    }


@dataclass
class Workspace:
    id: str
    name: str
    group: str = "Q8"
    theory: str = "E_2"
    characteristic: int = 2
    grading_label: str = "integer"
    spectral_sequence: str = "hfpss"  # hfpss | tate
    page: int = 2
    representation_basis: list[str] = field(default_factory=lambda: ["1", "sigma_i", "sigma_j", "sigma_k", "H"])
    classes: list[ClassNode] = field(default_factory=list)
    differentials: list[Differential] = field(default_factory=list)
    differential_events: list[DifferentialEvent] = field(default_factory=list)
    fates: list[ClassFate] = field(default_factory=list)
    propositions: list[Proposition] = field(default_factory=list)
    summary: str = ""
    settings: dict[str, Any] = field(default_factory=default_workspace_settings)


@dataclass
class Comparison:
    id: str
    source_workspace_id: str
    target_workspace_id: str
    name: str
    grade_shift: Grade = field(default_factory=Grade)
    mode: str = "translation"
    notes: str = ""
    source_ref: str = ""


@dataclass
class PeriodGenerator:
    grade_shift: Grade
    multiplier_expr: str
    inverse_required: bool = False
    relation_id: str | None = None


@dataclass
class PeriodFamily:
    id: str
    name: str
    workspace_id: str
    rank: int
    generators: list[PeriodGenerator] = field(default_factory=list)
    valid_from_page: int = 2
    valid_to_page: int | str = "infinity"
    certificate_proposition_id: str = ""
    supporting_proposition_ids: list[str] = field(default_factory=list)
    status: str = "under-review"
    source_ref: str = ""


@dataclass
class PeriodicityRule:
    """A source-scoped operation that may create audited periodic translates.

    A rule is deliberately separate from a PeriodFamily: the latter records a
    mathematical period, while this object records the exact page range and
    workspace in which the application is permitted to materialize new chart
    records.
    """

    id: str
    name: str
    workspace_id: str
    multiplier_expression: str
    grade_shift: Grade
    valid_from_page: int = 2
    valid_to_page: int | str = "infinity"
    spectral_sequence: str = "hfpss"
    horizontal_only: bool = False
    certificate_proposition_id: str = ""
    period_family_id: str = ""
    status: str = "under-review"
    scope: str = ""
    exclusions: list[str] = field(default_factory=list)
    source_ref: str = ""


@dataclass
class ManualPeriodicity:
    """A user-entered periodicity pattern, deliberately not a theorem claim.

    Unlike ``PeriodicityRule``, this record never authorizes automatic
    propagation.  It identifies exactly the manual copies created from a
    supplied vector and remains ``manual-unverified`` until a separate,
    source-backed argument is recorded.
    """

    id: str
    workspace_id: str
    anchor_class_id: str = ""
    anchor_differential_id: str = ""
    mode: str = "anchor"  # anchor | box | differentials-only
    rule_ids: list[str] = field(default_factory=list)
    bounds: dict[str, int] = field(default_factory=dict)
    translation_limit: int = 0
    cycle_label: str = "P"
    period_vector: Grade = field(default_factory=Grade)
    page: int = 2
    translations: list[int] = field(default_factory=list)
    basis: str = ""
    source_ref: str = ""
    status: str = "manual-unverified"
    created_class_ids: list[str] = field(default_factory=list)
    created_differential_ids: list[str] = field(default_factory=list)
    created_proposition_ids: list[str] = field(default_factory=list)


@dataclass
class ManualPeriodicityRule:
    """A named user-defined period vector for manual batch applications."""

    id: str
    workspace_id: str
    name: str
    period_vector: Grade
    basis: str
    source_ref: str = ""
    status: str = "manual-unverified"
    archived: bool = False
    archived_reason: str = ""


@dataclass
class E2PresentationGenerator:
    """An explicitly supplied generator in a finite E2 presentation."""

    id: str
    label: str
    grade: Grade
    expression: str = ""
    coefficient_context_id: str = "formal-integer-presentation"


@dataclass
class E2PresentationTerm:
    """An integral coefficient times a commutative monomial."""

    coefficient: int = 1
    factors: dict[str, int] = field(default_factory=dict)


@dataclass
class E2PresentationRelation:
    """A monic oriented relation ``lhs = rhs`` used by the safe rewriter."""

    id: str
    lhs: E2PresentationTerm
    rhs: list[E2PresentationTerm] = field(default_factory=list)
    source_ref: str = ""
    notes: str = ""


@dataclass
class E2Presentation:
    """A finite, explicit presentation; never an inferred group-cohomology result."""

    id: str
    workspace_id: str
    name: str
    generators: list[E2PresentationGenerator] = field(default_factory=list)
    relations: list[E2PresentationRelation] = field(default_factory=list)
    source_ref: str = ""
    scope: str = "Explicit user-supplied finite E2 presentation."
    status: str = "user-input"
    convention_id: str = "q8-thesis-plotted-v1"
    coefficient_context_id: str = "formal-integer-presentation"
    coefficient_domain: str = "integers"
    derived_class_ids: dict[str, str] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)


@dataclass
class GradingSector:
    id: str
    a: int
    b: int
    normal_form: dict[str, int]
    display_label: str
    period_reduction_context_id: str
    workspace_id: str
    status: str = "not-computed"
    c3_orbit_id: str = ""
    c3_position: int = 0
    symmetry_status: str = "distinct"
    class_ids: list[str] = field(default_factory=list)
    products_in: list[str] = field(default_factory=list)
    products_out: list[str] = field(default_factory=list)


@dataclass
class RepresentationRelation:
    id: str
    name: str
    relation_vector: dict[str, int]
    certificate_proposition_id: str = ""
    status: str = "under-review"
    source_refs: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class CrossGradedProduct:
    id: str
    left_workspace_id: str
    left_class_id: str
    right_workspace_id: str
    right_class_id: str
    page: int
    left_sector_id: str
    right_sector_id: str
    raw_representation_sum: dict[str, int]
    result_sector_id: str
    result_stem: int
    result_filtration: int
    normalization_path: list[str] = field(default_factory=list)
    resulting_expression: str = ""
    coefficient_context_id: str = "q8-witt-f4"
    leibniz_sign_convention_id: str = "q8-thesis-plotted-v1"
    proposition_id: str = ""
    status: str = "candidate"


@dataclass
class C3Action:
    id: str = "q8-c3-omega"
    name: str = "omega"
    representation_cycle: list[str] = field(default_factory=lambda: ["sigma_i", "sigma_j", "sigma_k"])
    symbol_images: dict[str, str] = field(default_factory=lambda: {
        "D": "zeta^2 D",
        "x": "zeta x",
        "y": "zeta^2 y",
    })
    coefficient_automorphism: str = "identity-until-source-certified"
    status: str = "under-review"
    source_ref: str = "Project notes; coefficient convention requires review"


@dataclass
class Project:
    id: str
    name: str
    workspaces: list[Workspace] = field(default_factory=list)
    comparisons: list[Comparison] = field(default_factory=list)
    research_brief: dict[str, Any] = field(default_factory=dict)
    revision: int = 0
    schema_version: int = SCHEMA_VERSION
    coefficient_contexts: list[CoefficientContext] = field(default_factory=list)
    symbol_definitions: list[SymbolDefinition] = field(default_factory=list)
    period_families: list[PeriodFamily] = field(default_factory=list)
    grading_sectors: list[GradingSector] = field(default_factory=list)
    representation_relations: list[RepresentationRelation] = field(default_factory=list)
    cross_graded_products: list[CrossGradedProduct] = field(default_factory=list)
    c3_actions: list[C3Action] = field(default_factory=list)
    e2_presentations: list[E2Presentation] = field(default_factory=list)
    periodicity_rules: list[PeriodicityRule] = field(default_factory=list)
    manual_periodicities: list[ManualPeriodicity] = field(default_factory=list)
    manual_periodicity_rules: list[ManualPeriodicityRule] = field(default_factory=list)


T = TypeVar("T")


def _known_kwargs(model: type[T], raw: dict[str, Any]) -> dict[str, Any]:
    names = {item.name for item in fields(model)}
    return {key: value for key, value in raw.items() if key in names}


def _coerce_grade(data: dict[str, Any] | Grade | None) -> Grade:
    if isinstance(data, Grade):
        return data
    return Grade(**(data or {}))


def _coerce_proposition(raw: dict[str, Any]) -> Proposition:
    values = _known_kwargs(Proposition, raw)
    source_ref = str(values.get("source_ref", ""))
    if not values.get("source_refs") and source_ref:
        values["source_refs"] = [source_ref]
    return Proposition(**values)


def project_to_dict(project: Project) -> dict[str, Any]:
    return asdict(project)


def project_from_dict(data: dict[str, Any]) -> Project:
    workspaces: list[Workspace] = []
    for raw_workspace in data.get("workspaces", []):
        classes = [
            ClassNode(**{
                **_known_kwargs(ClassNode, raw),
                "grade": _coerce_grade(raw.get("grade")),
                "expression": raw.get("expression") or raw.get("label", ""),
            })
            for raw in raw_workspace.get("classes", [])
        ]
        differentials = [Differential(**_known_kwargs(Differential, raw)) for raw in raw_workspace.get("differentials", [])]
        propositions = [_coerce_proposition(raw) for raw in raw_workspace.get("propositions", [])]
        events = [DifferentialEvent(**_known_kwargs(DifferentialEvent, raw)) for raw in raw_workspace.get("differential_events", [])]
        fates = [ClassFate(**_known_kwargs(ClassFate, raw)) for raw in raw_workspace.get("fates", [])]
        workspace_values = _known_kwargs(Workspace, raw_workspace)
        workspace_values.update({
            "classes": classes,
            "differentials": differentials,
            "propositions": propositions,
            "differential_events": events,
            "fates": fates,
        })
        workspaces.append(Workspace(**workspace_values))

    comparisons = [
        Comparison(**{
            **_known_kwargs(Comparison, raw),
            "grade_shift": _coerce_grade(raw.get("grade_shift")),
        })
        for raw in data.get("comparisons", [])
    ]
    contexts = [CoefficientContext(**_known_kwargs(CoefficientContext, raw)) for raw in data.get("coefficient_contexts", [])]
    symbols = [
        SymbolDefinition(**{
            **_known_kwargs(SymbolDefinition, raw),
            "grade": _coerce_grade(raw.get("grade")),
        })
        for raw in data.get("symbol_definitions", [])
    ]
    period_families = []
    for raw in data.get("period_families", []):
        generators = [
            PeriodGenerator(**{
                **_known_kwargs(PeriodGenerator, item),
                "grade_shift": _coerce_grade(item.get("grade_shift")),
            })
            for item in raw.get("generators", [])
        ]
        period_families.append(PeriodFamily(**{**_known_kwargs(PeriodFamily, raw), "generators": generators}))

    periodicity_rules = [
        PeriodicityRule(**{
            **_known_kwargs(PeriodicityRule, raw),
            "grade_shift": _coerce_grade(raw.get("grade_shift")),
        })
        for raw in data.get("periodicity_rules", [])
    ]

    manual_periodicity_rules = [
        ManualPeriodicityRule(**{
            **_known_kwargs(ManualPeriodicityRule, raw),
            "period_vector": _coerce_grade(raw.get("period_vector")),
        })
        for raw in data.get("manual_periodicity_rules", [])
    ]
    known_manual_rule_ids = {item.id for item in manual_periodicity_rules}
    # Read-only migration of the first beta draft, which stored named manual
    # rules inside workspace settings.  The canonical representation is now
    # project.manual_periodicity_rules; remove the duplicated settings copy.
    for workspace in workspaces:
        legacy_rules = workspace.settings.pop("manual_periodicity_rules", [])
        if not isinstance(legacy_rules, list):
            continue
        for raw_rule in legacy_rules:
            if not isinstance(raw_rule, dict):
                continue
            rule_id = str(raw_rule.get("id") or new_id("manual_rule"))
            if rule_id in known_manual_rule_ids:
                continue
            manual_periodicity_rules.append(ManualPeriodicityRule(
                id=rule_id,
                workspace_id=workspace.id,
                name=str(raw_rule.get("name") or "manual period").strip() or "manual period",
                period_vector=Grade(
                    stem=int(raw_rule.get("p", 0)),
                    filtration=int(raw_rule.get("q", 0)),
                ),
                basis="Migrated local manual drawing rule; no mathematical certificate supplied.",
                source_ref="Local manual drawing operation; no mathematical certificate supplied.",
                status="manual-unverified",
            ))
            known_manual_rule_ids.add(rule_id)

    manual_periodicities = []
    for raw in data.get("manual_periodicities", []):
        values = _known_kwargs(ManualPeriodicity, raw)
        legacy_kind = str(raw.get("operation_kind", ""))
        if "mode" not in raw:
            values["mode"] = {
                "all-rules-box": "box",
                "differentials-only": "differentials-only",
            }.get(legacy_kind, "anchor")
        if "rule_ids" not in raw:
            vectors = raw.get("rule_vectors", [])
            if legacy_kind == "differentials-only":
                # The old differential-only endpoint carried an ephemeral
                # vector, not a named user rule.
                values["rule_ids"] = []
            elif isinstance(vectors, list):
                legacy_rule_ids: list[str] = []
                for index, vector in enumerate(vectors):
                    if not isinstance(vector, dict):
                        continue
                    rule_id = str(vector.get("id") or f"legacy_manual_rule_{raw.get('id', 'operation')}_{index}")
                    legacy_rule_ids.append(rule_id)
                    if rule_id in known_manual_rule_ids:
                        continue
                    manual_periodicity_rules.append(ManualPeriodicityRule(
                        id=rule_id,
                        workspace_id=str(raw.get("workspace_id", "")),
                        name=str(vector.get("name") or f"manual period {index + 1}").strip() or f"manual period {index + 1}",
                        period_vector=Grade(
                            stem=int(vector.get("p", 0)),
                            filtration=int(vector.get("q", 0)),
                        ),
                        basis="Migrated local manual drawing rule; no mathematical certificate supplied.",
                        source_ref="Local manual drawing operation; no mathematical certificate supplied.",
                        status="manual-unverified",
                    ))
                    known_manual_rule_ids.add(rule_id)
                values["rule_ids"] = legacy_rule_ids
        if values.get("mode") == "differentials-only" and "period_vector" not in raw:
            vectors = raw.get("rule_vectors", [])
            if isinstance(vectors, list) and vectors and isinstance(vectors[0], dict):
                values["period_vector"] = Grade(int(vectors[0].get("p", 0)), int(vectors[0].get("q", 0)))
        values["period_vector"] = _coerce_grade(values.get("period_vector", raw.get("period_vector")))
        manual_periodicities.append(ManualPeriodicity(**values))

    e2_presentations = []
    for raw in data.get("e2_presentations", []):
        generators = [
            E2PresentationGenerator(**{
                **_known_kwargs(E2PresentationGenerator, item),
                "grade": _coerce_grade(item.get("grade")),
                "expression": item.get("expression") or item.get("label", ""),
            })
            for item in raw.get("generators", [])
        ]
        relations = []
        for item in raw.get("relations", []):
            lhs = E2PresentationTerm(**_known_kwargs(E2PresentationTerm, item.get("lhs", {})))
            rhs = [E2PresentationTerm(**_known_kwargs(E2PresentationTerm, term)) for term in item.get("rhs", [])]
            relations.append(E2PresentationRelation(**{
                **_known_kwargs(E2PresentationRelation, item),
                "lhs": lhs,
                "rhs": rhs,
            }))
        e2_presentations.append(E2Presentation(**{
            **_known_kwargs(E2Presentation, raw),
            "generators": generators,
            "relations": relations,
        }))

    return Project(
        id=data.get("id", new_id("project")),
        name=data.get("name", "Untitled spectral-sequence project"),
        workspaces=workspaces,
        comparisons=comparisons,
        research_brief=dict(data.get("research_brief", {})),
        revision=int(data.get("revision", 0)),
        schema_version=int(data.get("schema_version", 1)),
        coefficient_contexts=contexts,
        symbol_definitions=symbols,
        period_families=period_families,
        grading_sectors=[GradingSector(**_known_kwargs(GradingSector, raw)) for raw in data.get("grading_sectors", [])],
        representation_relations=[RepresentationRelation(**_known_kwargs(RepresentationRelation, raw)) for raw in data.get("representation_relations", [])],
        cross_graded_products=[CrossGradedProduct(**_known_kwargs(CrossGradedProduct, raw)) for raw in data.get("cross_graded_products", [])],
        c3_actions=[C3Action(**_known_kwargs(C3Action, raw)) for raw in data.get("c3_actions", [])],
        e2_presentations=e2_presentations,
        periodicity_rules=periodicity_rules,
        manual_periodicities=manual_periodicities,
        manual_periodicity_rules=manual_periodicity_rules,
    )
