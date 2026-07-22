"""Explicit finite E2 presentations and a conservative integral rewriter.

This module does *not* compute group cohomology or discover differentials.
It accepts a finite presentation explicitly supplied by a researcher, verifies
that its chosen monic orientation terminates and passes the pairwise critical
pair test, and then evaluates polynomials exactly over the integers.  A
presentation may materialize its explicitly listed generators as E2 dots; it
never materializes arbitrary monomials or inferred differentials.
"""
from __future__ import annotations

from dataclasses import asdict
from itertools import combinations
from typing import Any, Mapping

from .models import (
    ClassNode,
    CoefficientContext,
    E2Presentation,
    E2PresentationGenerator,
    E2PresentationRelation,
    E2PresentationTerm,
    Grade,
    Project,
    Proposition,
    Workspace,
    new_id,
)


Monomial = tuple[tuple[str, int], ...]
Polynomial = dict[Monomial, int]
INTEGER_PRESENTATION_CONTEXT = "formal-integer-presentation"


class PresentationValidationError(ValueError):
    """Raised when explicit data cannot define a safe finite rewriter."""


def presentation_from_input(raw: Mapping[str, Any], *, presentation_id: str | None = None) -> E2Presentation:
    """Parse and validate the JSON-safe finite-presentation contract.

    Relations must be monic, oriented rules.  Rejecting a non-monic relation
    prevents accidental division in an integral coefficient context.
    """

    workspace_id = _required_string(raw, "workspace_id")
    name = _required_string(raw, "name")
    source_ref = _required_string(raw, "source_ref")
    coefficient_context_id = str(raw.get("coefficient_context_id", INTEGER_PRESENTATION_CONTEXT))
    coefficient_domain = str(raw.get("coefficient_domain", "integers"))
    if coefficient_context_id != INTEGER_PRESENTATION_CONTEXT or coefficient_domain != "integers":
        raise PresentationValidationError(
            "This finite rewriter supports only coefficient_domain='integers' with "
            "coefficient_context_id='formal-integer-presentation'. F4 and Witt coefficients require a scalar algebra that is not implemented."
        )
    raw_generators = raw.get("generators")
    raw_relations = raw.get("relations", [])
    if not isinstance(raw_generators, list) or not raw_generators:
        raise PresentationValidationError("A finite E2 presentation requires a nonempty generators array.")
    if not isinstance(raw_relations, list):
        raise PresentationValidationError("relations must be an array.")

    generators: list[E2PresentationGenerator] = []
    generator_ids: set[str] = set()
    for item in raw_generators:
        if not isinstance(item, Mapping):
            raise PresentationValidationError("Each generator must be an object.")
        ident = _required_string(item, "id")
        if ident in generator_ids:
            raise PresentationValidationError(f"Duplicate generator id {ident!r}.")
        generator_ids.add(ident)
        label = _required_string(item, "label")
        grade = _grade_from_input(item.get("grade"))
        expression = str(item.get("expression", label)).strip() or label
        generators.append(E2PresentationGenerator(
            id=ident,
            label=label,
            grade=grade,
            expression=expression,
            coefficient_context_id=_generator_context(item, coefficient_context_id),
        ))

    relations: list[E2PresentationRelation] = []
    relation_ids: set[str] = set()
    for item in raw_relations:
        if not isinstance(item, Mapping):
            raise PresentationValidationError("Each relation must be an object.")
        ident = _required_string(item, "id")
        if ident in relation_ids:
            raise PresentationValidationError(f"Duplicate relation id {ident!r}.")
        relation_ids.add(ident)
        lhs = _term_from_input(item.get("lhs"), generator_ids, context=f"relation {ident} lhs")
        if lhs.coefficient != 1 or not lhs.factors:
            raise PresentationValidationError(
                f"Relation {ident!r} must have a nonzero monic lhs; non-monic integral relations are not safely rewritable."
            )
        raw_rhs = item.get("rhs", [])
        if not isinstance(raw_rhs, list):
            raise PresentationValidationError(f"Relation {ident!r} rhs must be an array of terms.")
        rhs = [_term_from_input(term, generator_ids, context=f"relation {ident} rhs") for term in raw_rhs]
        relations.append(E2PresentationRelation(
            id=ident,
            lhs=lhs,
            rhs=rhs,
            source_ref=str(item.get("source_ref", source_ref)).strip() or source_ref,
            notes=str(item.get("notes", "")),
        ))

    presentation = E2Presentation(
        id=str(raw.get("id") or presentation_id or new_id("e2presentation")),
        workspace_id=workspace_id,
        name=name,
        generators=generators,
        relations=relations,
        source_ref=source_ref,
        scope=str(raw.get("scope", "Explicit user-supplied finite E2 presentation.")).strip()
            or "Explicit user-supplied finite E2 presentation.",
        status=str(raw.get("status", "user-input")),
        convention_id=str(raw.get("convention_id", "q8-thesis-plotted-v1")),
        coefficient_context_id=coefficient_context_id,
        coefficient_domain=coefficient_domain,
    )
    presentation.validation = validate_presentation(presentation)
    return presentation


def validate_presentation(presentation: E2Presentation) -> dict[str, Any]:
    """Prove the supplied orientation is terminating and pairwise confluent.

    The proof obligation is intentionally modest: every right-hand monomial
    must decrease in a fixed degree-lex order and every critical pair must have
    the same normal form.  Inputs failing either condition are rejected rather
    than evaluated using an arbitrary rule priority.
    """

    if (
        presentation.coefficient_context_id != INTEGER_PRESENTATION_CONTEXT
        or presentation.coefficient_domain != "integers"
    ):
        raise PresentationValidationError(
            "F4 and Witt coefficient presentations cannot be evaluated without their scalar algebra; "
            "only the formal-integer presentation context is supported."
        )
    order = [item.id for item in presentation.generators]
    if len(set(order)) != len(order):
        raise PresentationValidationError("Generator ids must be unique.")
    known = set(order)
    generator_by_id = {item.id: item for item in presentation.generators}
    lhs_seen: dict[Monomial, str] = {}
    rules: list[tuple[E2PresentationRelation, Monomial, Polynomial]] = []
    for relation in presentation.relations:
        lhs = _term_to_monomial(relation.lhs, known)
        if relation.lhs.coefficient != 1 or not lhs:
            raise PresentationValidationError(f"Relation {relation.id!r} does not have a monic nonconstant lhs.")
        if lhs in lhs_seen:
            raise PresentationValidationError(
                f"Relations {lhs_seen[lhs]!r} and {relation.id!r} have the same lhs; choose one explicit orientation."
            )
        lhs_seen[lhs] = relation.id
        rhs = _polynomial_from_terms(relation.rhs, known)
        lhs_grade = _monomial_grade(lhs, generator_by_id)
        for monomial in rhs:
            if _monomial_grade(monomial, generator_by_id) != lhs_grade:
                raise PresentationValidationError(
                    f"Relation {relation.id!r} is not homogeneous in the supplied E2 grade."
                )
            if not _strictly_smaller(monomial, lhs, order):
                raise PresentationValidationError(
                    f"Relation {relation.id!r} is not decreasing in degree-lex order; no terminating rewrite proof is available."
                )
        rules.append((relation, lhs, rhs))

    critical_pairs_checked = 0
    for left, right in combinations(rules, 2):
        _, lhs_left, rhs_left = left
        _, lhs_right, rhs_right = right
        lcm = _lcm(lhs_left, lhs_right)
        after_left = _multiply_polynomial(rhs_left, _quotient(lcm, lhs_left))
        after_right = _multiply_polynomial(rhs_right, _quotient(lcm, lhs_right))
        normal_left = _normal_form(after_left, rules, order)
        normal_right = _normal_form(after_right, rules, order)
        critical_pairs_checked += 1
        if normal_left != normal_right:
            raise PresentationValidationError(
                f"Critical pair {left[0].id!r}/{right[0].id!r} is unresolved; add relations or choose another orientation."
            )

    return {
        "coefficient_domain": "integers",
        "monomial_order": "degree-lex in explicit generator order",
        "terminating": True,
        "confluent": True,
        "critical_pairs_checked": critical_pairs_checked,
        "automatic_differentials": False,
        "automatic_group_cohomology": False,
    }


def normal_form_from_input(presentation: E2Presentation, raw_polynomial: Any) -> dict[str, Any]:
    """Evaluate an explicit polynomial in the verified presentation."""

    if isinstance(raw_polynomial, Mapping):
        raw_terms = raw_polynomial.get("terms")
    else:
        raw_terms = raw_polynomial
    if not isinstance(raw_terms, list):
        raise PresentationValidationError("polynomial must be an object with a terms array.")
    known = {item.id for item in presentation.generators}
    polynomial = _polynomial_from_terms(
        [_term_from_input(item, known, context="polynomial") for item in raw_terms],
        known,
    )
    order = [item.id for item in presentation.generators]
    rules = [
        (relation, _term_to_monomial(relation.lhs, known), _polynomial_from_terms(relation.rhs, known))
        for relation in presentation.relations
    ]
    normal = _normal_form(polynomial, rules, order)
    return {
        "input": _polynomial_to_dict(polynomial, order),
        "normal_form": _polynomial_to_dict(normal, order),
        "validation": dict(presentation.validation),
        "warning": "Exact rewriting in the supplied finite presentation only; this is not group-cohomology or differential discovery.",
    }


def materialize_explicit_presentation(project: Project, presentation: E2Presentation) -> dict[str, list[str]]:
    """Persist the explicit generator dots and relation claims, but no consequences."""

    if any(item.id == presentation.id for item in project.e2_presentations):
        raise PresentationValidationError(f"An E2 presentation named {presentation.id!r} is already stored.")
    workspace = next((item for item in project.workspaces if item.id == presentation.workspace_id), None)
    if workspace is None:
        raise PresentationValidationError(f"Unknown workspace {presentation.workspace_id!r}.")
    if presentation.coefficient_context_id != INTEGER_PRESENTATION_CONTEXT or presentation.coefficient_domain != "integers":
        raise PresentationValidationError(
            "Only the explicit formal-integer presentation context can be materialized by this evaluator."
        )
    if not any(item.id == INTEGER_PRESENTATION_CONTEXT for item in project.coefficient_contexts):
        project.coefficient_contexts.append(CoefficientContext(
            id=INTEGER_PRESENTATION_CONTEXT,
            residue_field="not-modeled",
            coefficient_ring="Z (finite-presentation rewrite evaluator only)",
            scalar_mode="formal",
            source_ref="Explicit finite E2 presentation input; no F4/Witt scalar algebra is implemented.",
        ))
    result = {"created_classes": [], "reused_classes": [], "created_propositions": []}
    existing = {
        (item.expression, item.grade.stem, item.grade.filtration, _normalise_representation(item.grade.representation)): item
        for item in workspace.classes
        if not item.archived
    }
    for generator in presentation.generators:
        key = (
            generator.expression,
            generator.grade.stem,
            generator.grade.filtration,
            _normalise_representation(generator.grade.representation),
        )
        node = existing.get(key)
        if node is None:
            node = ClassNode(
                id=new_id("class"),
                label=generator.label,
                expression=generator.expression,
                grade=Grade(generator.grade.stem, generator.grade.filtration, dict(generator.grade.representation)),
                page=2,
                state="unknown",
                notes=(
                    f"Explicit generator from finite E2 presentation {presentation.name!r}. "
                    "No group-cohomology, differential, or permanence claim is implied."
                ),
                coefficient_context_id=generator.coefficient_context_id,
                convention_id=presentation.convention_id,
            )
            workspace.classes.append(node)
            existing[key] = node
            result["created_classes"].append(node.id)
        else:
            result["reused_classes"].append(node.id)
        presentation.derived_class_ids[generator.id] = node.id
        proposition = Proposition(
            id=new_id("prop"),
            kind="presentation-generator",
            statement=(
                f"Explicit E2-presentation generator {generator.label} is placed at "
                f"({generator.grade.stem}, {generator.grade.filtration})."
            ),
            status="user-input",
            conclusion={"class_id": node.id, "presentation_id": presentation.id, "generator_id": generator.id},
            rule="ExplicitFinitePresentation",
            confidence=1.0,
            notes="Placement is explicit user input, not a derived cohomology calculation.",
            source_ref=presentation.source_ref,
            source_refs=[presentation.source_ref],
            convention_id=presentation.convention_id,
            verification_checks=["explicit-grade", "presentation-validation"],
        )
        workspace.propositions.append(proposition)
        result["created_propositions"].append(proposition.id)

    for relation in presentation.relations:
        proposition = Proposition(
            id=new_id("prop"),
            kind="presentation-relation",
            statement=_relation_text(relation, presentation.generators),
            status="user-input",
            conclusion={"presentation_id": presentation.id, "relation_id": relation.id},
            rule="ExactRelationRewrite",
            confidence=1.0,
            notes="Validated as an oriented finite rewrite rule; not promoted to an arbitrary spectral-sequence theorem.",
            source_ref=relation.source_ref or presentation.source_ref,
            source_refs=[relation.source_ref or presentation.source_ref],
            convention_id=presentation.convention_id,
            verification_checks=["monic", "terminating", "critical-pairs"],
        )
        workspace.propositions.append(proposition)
        result["created_propositions"].append(proposition.id)

    project.e2_presentations.append(presentation)
    return result


def presentation_to_dict(presentation: E2Presentation) -> dict[str, Any]:
    return asdict(presentation)


def _required_string(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PresentationValidationError(f"{key} must be a nonempty string.")
    return value.strip()


def _generator_context(raw: Mapping[str, Any], presentation_context: str) -> str:
    context = str(raw.get("coefficient_context_id", presentation_context))
    if context != presentation_context:
        raise PresentationValidationError(
            "All presentation generators must use the presentation's formal-integer coefficient context."
        )
    return context


def _grade_from_input(raw: Any) -> Grade:
    if not isinstance(raw, Mapping):
        raise PresentationValidationError("Each generator requires a grade object.")
    stem = raw.get("stem", 0)
    filtration = raw.get("filtration", 0)
    representation = raw.get("representation", {})
    if isinstance(stem, bool) or not isinstance(stem, int):
        raise PresentationValidationError("grade.stem must be an integer.")
    if isinstance(filtration, bool) or not isinstance(filtration, int):
        raise PresentationValidationError("grade.filtration must be an integer.")
    if not isinstance(representation, Mapping):
        raise PresentationValidationError("grade.representation must be an object.")
    normalized: dict[str, int] = {}
    for key, value in representation.items():
        if not isinstance(key, str) or not key:
            raise PresentationValidationError("Representation keys must be nonempty strings.")
        if isinstance(value, bool) or not isinstance(value, int):
            raise PresentationValidationError("Representation coefficients must be integers.")
        if value:
            normalized[key] = value
    return Grade(stem, filtration, normalized)


def _term_from_input(raw: Any, known: set[str], *, context: str) -> E2PresentationTerm:
    if not isinstance(raw, Mapping):
        raise PresentationValidationError(f"{context} must be an object with coefficient and factors.")
    coefficient = raw.get("coefficient", 1)
    factors = raw.get("factors", {})
    if isinstance(coefficient, bool) or not isinstance(coefficient, int) or coefficient == 0:
        raise PresentationValidationError(f"{context} coefficient must be a nonzero integer.")
    if not isinstance(factors, Mapping):
        raise PresentationValidationError(f"{context} factors must be an object.")
    normalized: dict[str, int] = {}
    for identifier, exponent in factors.items():
        if identifier not in known:
            raise PresentationValidationError(f"{context} refers to unknown generator {identifier!r}.")
        if isinstance(exponent, bool) or not isinstance(exponent, int) or exponent <= 0:
            raise PresentationValidationError(f"{context} exponents must be positive integers.")
        normalized[str(identifier)] = exponent
    return E2PresentationTerm(coefficient=coefficient, factors=dict(sorted(normalized.items())))


def _term_to_monomial(term: E2PresentationTerm, known: set[str]) -> Monomial:
    if any(identifier not in known for identifier in term.factors):
        raise PresentationValidationError("Stored presentation refers to an unknown generator.")
    return tuple(sorted((identifier, exponent) for identifier, exponent in term.factors.items() if exponent))


def _polynomial_from_terms(terms: list[E2PresentationTerm], known: set[str]) -> Polynomial:
    output: Polynomial = {}
    for term in terms:
        monomial = _term_to_monomial(term, known)
        output[monomial] = output.get(monomial, 0) + term.coefficient
        if output[monomial] == 0:
            del output[monomial]
    return output


def _normal_form(polynomial: Polynomial, rules: list[tuple[E2PresentationRelation, Monomial, Polynomial]], order: list[str]) -> Polynomial:
    output = dict(polynomial)
    max_steps = 20_000
    for _ in range(max_steps):
        reduced = False
        for monomial in sorted(output, key=lambda item: _monomial_key(item, order), reverse=True):
            coefficient = output[monomial]
            for _, lhs, rhs in rules:
                if not _divides(lhs, monomial):
                    continue
                del output[monomial]
                multiplier = _quotient(monomial, lhs)
                for right_monomial, right_coefficient in _multiply_polynomial(rhs, multiplier).items():
                    output[right_monomial] = output.get(right_monomial, 0) + coefficient * right_coefficient
                    if output[right_monomial] == 0:
                        del output[right_monomial]
                reduced = True
                break
            if reduced:
                break
        if not reduced:
            return output
    raise PresentationValidationError("Rewrite exceeded 20,000 steps; the presentation is not safely evaluable.")


def _divides(left: Monomial, right: Monomial) -> bool:
    right_dict = dict(right)
    return all(right_dict.get(identifier, 0) >= exponent for identifier, exponent in left)


def _quotient(numerator: Monomial, denominator: Monomial) -> Monomial:
    result = dict(numerator)
    for identifier, exponent in denominator:
        result[identifier] = result.get(identifier, 0) - exponent
        if result[identifier] == 0:
            del result[identifier]
    return tuple(sorted(result.items()))


def _lcm(left: Monomial, right: Monomial) -> Monomial:
    result = dict(left)
    for identifier, exponent in right:
        result[identifier] = max(result.get(identifier, 0), exponent)
    return tuple(sorted(result.items()))


def _multiply_polynomial(polynomial: Polynomial, multiplier: Monomial) -> Polynomial:
    output: Polynomial = {}
    for monomial, coefficient in polynomial.items():
        factors = dict(monomial)
        for identifier, exponent in multiplier:
            factors[identifier] = factors.get(identifier, 0) + exponent
        product = tuple(sorted(factors.items()))
        output[product] = output.get(product, 0) + coefficient
    return {monomial: coefficient for monomial, coefficient in output.items() if coefficient}


def _monomial_key(monomial: Monomial, order: list[str]) -> tuple[int, tuple[int, ...]]:
    factors = dict(monomial)
    return sum(factors.values()), tuple(factors.get(identifier, 0) for identifier in order)


def _strictly_smaller(candidate: Monomial, reference: Monomial, order: list[str]) -> bool:
    return _monomial_key(candidate, order) < _monomial_key(reference, order)


def _monomial_grade(monomial: Monomial, generators: Mapping[str, E2PresentationGenerator]) -> Grade:
    representation: dict[str, int] = {}
    stem = filtration = 0
    for identifier, exponent in monomial:
        generator = generators[identifier]
        stem += generator.grade.stem * exponent
        filtration += generator.grade.filtration * exponent
        for coordinate, value in generator.grade.representation.items():
            representation[coordinate] = representation.get(coordinate, 0) + value * exponent
            if representation[coordinate] == 0:
                del representation[coordinate]
    return Grade(stem=stem, filtration=filtration, representation=representation)


def _polynomial_to_dict(polynomial: Polynomial, order: list[str]) -> list[dict[str, Any]]:
    return [
        {"coefficient": coefficient, "factors": dict(monomial)}
        for monomial, coefficient in sorted(polynomial.items(), key=lambda item: _monomial_key(item[0], order), reverse=True)
    ]


def _normalise_representation(representation: Mapping[str, int]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((str(key), int(value)) for key, value in representation.items() if int(value)))


def _relation_text(relation: E2PresentationRelation, generators: list[E2PresentationGenerator]) -> str:
    labels = {item.id: item.label for item in generators}
    return f"{_term_text(relation.lhs, labels)} = {_polynomial_text(relation.rhs, labels)}"


def _polynomial_text(terms: list[E2PresentationTerm], labels: dict[str, str]) -> str:
    return " + ".join(_term_text(term, labels) for term in terms) if terms else "0"


def _term_text(term: E2PresentationTerm, labels: dict[str, str]) -> str:
    pieces: list[str] = []
    if term.coefficient != 1 or not term.factors:
        pieces.append(str(term.coefficient))
    for identifier, exponent in term.factors.items():
        label = labels.get(identifier, identifier)
        pieces.append(label if exponent == 1 else f"{label}^{exponent}")
    return " ".join(pieces)
