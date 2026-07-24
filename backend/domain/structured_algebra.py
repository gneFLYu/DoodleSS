"""Safe structured algebra for explicit HFPSS calculations.

The public entry point in this module accepts JSON objects, never expression
text.  Generator identifiers are validated against an explicit registry before
any arithmetic begins.  SymPy is used only as a backend for expressions built
from private ``Symbol`` objects and exact Python integers; this module never
calls ``eval``, ``sympify``, or ``parse_expr`` on user data.

This is an algebra evaluator, not a group-cohomology or differential solver.
Every rewrite rule and generator grade is explicit researcher input, and the
preview result is never persisted as a mathematical claim.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping, Sequence

from .algebra import F4Element
from .models import Grade


FORMAL_INTEGER_CONTEXTS = frozenset({"formal-integer", "formal-integer-presentation"})
F4_CONTEXT = "q8-residue-f4"
WITT_CONTEXT = "q8-witt-f4"
CONTEXT_DOMAINS = {
    "formal-integer": "integers",
    "formal-integer-presentation": "integers",
    F4_CONTEXT: "F4",
    WITT_CONTEXT: "W(F4)/2-adic",
}

MAX_GENERATORS = 128
MAX_TERMS = 2_000
MAX_FACTORS = 64
MAX_RELATIONS = 128
MAX_RELATION_TERMS = 10_000
MAX_CRITICAL_PAIRS = 128
MAX_EXPONENT = 4_096
MAX_PRODUCTS = 100_000
MAX_INTERMEDIATE_TERMS = 10_000
MAX_REWRITE_STEPS = 20_000
IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,79}$")


class AlgebraValidationError(ValueError):
    """Raised when structured algebra input is unsafe or unsupported."""


Scalar = int | F4Element


@dataclass(frozen=True)
class CoefficientContextSpec:
    id: str
    domain: str
    source_ref: str

    @property
    def arithmetic_supported(self) -> bool:
        return self.domain in {"integers", "F4"}


@dataclass(frozen=True)
class StructuredGenerator:
    id: str
    label: str
    grade: Grade
    kind: str
    coefficient_context_id: str
    source_ref: str

    @property
    def invertible(self) -> bool:
        return self.kind == "unit"


@dataclass(frozen=True)
class AlgebraMonomial:
    """A canonical commutative product of registered generator powers."""

    powers: tuple[tuple[str, int], ...] = ()

    def multiply(self, other: "AlgebraMonomial", registry: "GeneratorRegistry") -> "AlgebraMonomial":
        combined = dict(self.powers)
        for identifier, exponent in other.powers:
            combined[identifier] = combined.get(identifier, 0) + exponent
            if combined[identifier] == 0:
                del combined[identifier]
        return registry.monomial_from_powers(combined)

    def grade(self, registry: "GeneratorRegistry") -> Grade:
        result = Grade()
        for identifier, exponent in self.powers:
            result = result.shifted(_scale_grade(registry[identifier].grade, exponent))
        return result


@dataclass(frozen=True)
class AlgebraTerm:
    coefficient: Scalar
    monomial: AlgebraMonomial


@dataclass(frozen=True)
class AlgebraPolynomial:
    """A collected polynomial with one term per canonical monomial."""

    terms: tuple[AlgebraTerm, ...] = ()

    @classmethod
    def from_map(
        cls,
        values: Mapping[AlgebraMonomial, Scalar],
        context: CoefficientContextSpec,
        registry: "GeneratorRegistry",
    ) -> "AlgebraPolynomial":
        nonzero = [
            AlgebraTerm(coefficient, monomial)
            for monomial, coefficient in values.items()
            if not _scalar_is_zero(coefficient, context)
        ]
        nonzero.sort(key=lambda term: registry.monomial_key(term.monomial), reverse=True)
        return cls(tuple(nonzero))

    def as_map(self) -> dict[AlgebraMonomial, Scalar]:
        return {term.monomial: term.coefficient for term in self.terms}

    def add(
        self,
        other: "AlgebraPolynomial",
        context: CoefficientContextSpec,
        registry: "GeneratorRegistry",
    ) -> "AlgebraPolynomial":
        result = self.as_map()
        for term in other.terms:
            previous = result.get(term.monomial, _scalar_zero(context))
            result[term.monomial] = _scalar_add(previous, term.coefficient, context)
        return AlgebraPolynomial.from_map(result, context, registry)

    def multiply(
        self,
        other: "AlgebraPolynomial",
        context: CoefficientContextSpec,
        registry: "GeneratorRegistry",
    ) -> "AlgebraPolynomial":
        if len(self.terms) * len(other.terms) > MAX_PRODUCTS:
            raise AlgebraValidationError(
                f"Polynomial product exceeds the {MAX_PRODUCTS:,}-term safety limit."
            )
        result: dict[AlgebraMonomial, Scalar] = {}
        for left in self.terms:
            for right in other.terms:
                monomial = left.monomial.multiply(right.monomial, registry)
                coefficient = _scalar_mul(left.coefficient, right.coefficient, context)
                previous = result.get(monomial, _scalar_zero(context))
                result[monomial] = _scalar_add(previous, coefficient, context)
                if len(result) > MAX_INTERMEDIATE_TERMS:
                    raise AlgebraValidationError(
                        f"Polynomial product exceeds the {MAX_INTERMEDIATE_TERMS:,}-term output limit."
                    )
        return AlgebraPolynomial.from_map(result, context, registry)


class GeneratorRegistry:
    """Ordered registry used for validation, grading, and monomial ordering."""

    def __init__(self, generators: Sequence[StructuredGenerator]):
        self.generators = tuple(generators)
        self._by_id = {item.id: item for item in self.generators}
        self._position = {item.id: index for index, item in enumerate(self.generators)}

    def __getitem__(self, identifier: str) -> StructuredGenerator:
        try:
            return self._by_id[identifier]
        except KeyError as error:
            raise AlgebraValidationError(f"Unknown generator {identifier!r}.") from error

    def monomial_from_powers(self, raw: Mapping[str, Any]) -> AlgebraMonomial:
        normalized: dict[str, int] = {}
        for identifier, exponent in raw.items():
            if not isinstance(identifier, str):
                raise AlgebraValidationError("Monomial generator ids must be strings.")
            generator = self[identifier]
            if isinstance(exponent, bool) or not isinstance(exponent, int):
                raise AlgebraValidationError(f"Exponent of {identifier!r} must be an integer.")
            if abs(exponent) > MAX_EXPONENT:
                raise AlgebraValidationError(
                    f"Exponent of {identifier!r} exceeds the absolute limit {MAX_EXPONENT}."
                )
            if exponent < 0 and not generator.invertible:
                raise AlgebraValidationError(
                    f"Negative exponent for {identifier!r} requires kind='unit'."
                )
            if exponent:
                normalized[identifier] = exponent
        return AlgebraMonomial(tuple(sorted(normalized.items(), key=lambda item: self._position[item[0]])))

    def monomial_key(self, monomial: AlgebraMonomial) -> tuple[int, tuple[int, ...]]:
        powers = dict(monomial.powers)
        vector = tuple(powers.get(item.id, 0) for item in self.generators)
        return sum(vector), vector


@dataclass(frozen=True)
class RewriteRule:
    id: str
    lhs: AlgebraMonomial
    rhs: AlgebraPolynomial
    source_ref: str


def preview_structured_algebra(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one explicit, structured algebra request without persistence."""

    if not isinstance(raw, Mapping):
        raise AlgebraValidationError("Algebra preview input must be a JSON object.")
    source_ref = _required_string(raw, "source_ref")
    context = _context_from_input(raw.get("coefficient_context"), source_ref)
    registry = _registry_from_input(raw.get("generators"), context, source_ref)
    operation = _required_string(raw, "operation")
    if operation not in {"canonicalize", "add", "multiply", "expand", "collect", "normal-form"}:
        raise AlgebraValidationError(
            "operation must be canonicalize, add, multiply, expand, collect, or normal-form."
        )
    if not context.arithmetic_supported:
        raise AlgebraValidationError(
            "W(F4)/2-adic arithmetic is not implemented. This request is rejected rather than "
            "using integer or F4 arithmetic; in particular, the engine never infers 2 = 0 in this context."
        )

    input_polynomials: list[AlgebraPolynomial] = []
    rules: list[RewriteRule] = []
    applied_rule_ids: set[str] = set()
    rewrite_validation: dict[str, Any] | None = None
    engine = "native-exact"

    if operation in {"canonicalize", "collect", "normal-form"}:
        polynomial = _polynomial_from_input(raw.get("polynomial"), context, registry, "polynomial")
        input_polynomials.append(polynomial)
        result = polynomial
        if operation == "normal-form":
            rules = _relations_from_input(raw.get("relations", []), context, registry, source_ref)
            rewrite_validation = _validate_rewrite_rules(rules, context, registry)
            result, applied_rule_ids = _normal_form(result, rules, context, registry)
        if context.domain == "integers" and operation in {"collect", "normal-form"}:
            result = SafeSympyIntegerAdapter(registry).collect(result)
            engine = "sympy-safe-structured"
    elif operation in {"add", "multiply"}:
        left = _polynomial_from_input(raw.get("left"), context, registry, "left")
        right = _polynomial_from_input(raw.get("right"), context, registry, "right")
        input_polynomials.extend((left, right))
        result = (
            left.add(right, context, registry)
            if operation == "add"
            else left.multiply(right, context, registry)
        )
    else:
        raw_factors = raw.get("factors")
        if not isinstance(raw_factors, list) or not raw_factors:
            raise AlgebraValidationError("expand requires a nonempty factors array of polynomials.")
        if len(raw_factors) > MAX_FACTORS:
            raise AlgebraValidationError(f"expand accepts at most {MAX_FACTORS} polynomial factors.")
        input_polynomials = [
            _polynomial_from_input(item, context, registry, f"factors[{index}]")
            for index, item in enumerate(raw_factors)
        ]
        if context.domain == "integers":
            result = SafeSympyIntegerAdapter(registry).expand(input_polynomials)
            engine = "sympy-safe-structured"
        else:
            result = _one_polynomial(context, registry)
            for factor in input_polynomials:
                result = result.multiply(factor, context, registry)

    used_generator_ids = _used_generator_ids(input_polynomials)
    used_generator_ids.update(_used_generator_ids([result]))
    relation_by_id = {item.id: item for item in rules}
    for identifier in applied_rule_ids:
        rule = relation_by_id[identifier]
        used_generator_ids.update(item for item, _ in rule.lhs.powers)
        used_generator_ids.update(_used_generator_ids([rule.rhs]))
    provenance_refs = {source_ref, context.source_ref}
    provenance_refs.update(registry[identifier].source_ref for identifier in used_generator_ids)
    provenance_refs.update(relation_by_id[identifier].source_ref for identifier in applied_rule_ids)
    response: dict[str, Any] = {
        "operation": operation,
        "coefficient_context": {
            "id": context.id,
            "domain": context.domain,
            "arithmetic_supported": True,
        },
        "result": _polynomial_to_dict(result, context, registry),
        "engine": engine,
        "persisted": False,
        "claims_created": 0,
        "status": "computed-from-explicit-input",
        "provenance": {
            "source_refs": sorted(provenance_refs),
            "generator_ids": sorted(used_generator_ids, key=lambda item: registry._position[item]),
            "relation_ids": sorted(applied_rule_ids),
        },
        "validation": {
            "structured_input_only": True,
            "untrusted_text_parsing": False,
            "registered_generators_only": True,
            "integer_exponents_only": True,
            "coefficient_context_separated": True,
        },
        "limitations": [
            "No class, relation, differential, permanence claim, or theorem is persisted.",
            "The engine does not compute group cohomology or discover arbitrary spectral-sequence differentials.",
            "W(F4)/2-adic scalar arithmetic and Macaulay2 execution are outside this phase."
        ],
    }
    if rewrite_validation is not None:
        response["rewrite_validation"] = rewrite_validation
    if engine == "sympy-safe-structured":
        response["sympy"] = {
            "version": SafeSympyIntegerAdapter.version(),
            "input_mode": "internally constructed symbols; no string parser",
        }
    return response


class SafeSympyIntegerAdapter:
    """SymPy bridge for validated integral Laurent polynomials.

    Generator ids and labels are never used as SymPy source text.  Each
    registered generator receives a private positional symbol, and conversion
    back verifies that SymPy returned only those symbols with integer powers.
    """

    def __init__(self, registry: GeneratorRegistry):
        import sympy

        self.sympy = sympy
        self.registry = registry
        self.symbols = tuple(
            sympy.Symbol(f"_hfpss_g{index}", commutative=True)
            for index, _ in enumerate(registry.generators)
        )
        self.symbol_by_id = {
            generator.id: self.symbols[index]
            for index, generator in enumerate(registry.generators)
        }
        self.id_by_symbol = {symbol: identifier for identifier, symbol in self.symbol_by_id.items()}

    @staticmethod
    def version() -> str:
        import sympy

        return str(sympy.__version__)

    def collect(self, polynomial: AlgebraPolynomial) -> AlgebraPolynomial:
        return self._from_expr(self.sympy.expand(self._to_expr(polynomial)))

    def expand(self, factors: Sequence[AlgebraPolynomial]) -> AlgebraPolynomial:
        context = CoefficientContextSpec("formal-integer", "integers", "internal")
        result = _one_polynomial(context, self.registry)
        for index, factor in enumerate(factors):
            estimated_products = len(result.terms) * len(factor.terms)
            if estimated_products > MAX_PRODUCTS:
                raise AlgebraValidationError(
                    f"expand step {index + 1} requires {estimated_products:,} term products, "
                    f"exceeding the {MAX_PRODUCTS:,}-product safety limit."
                )
            result = result.multiply(factor, context, self.registry)
            if len(result.terms) > MAX_INTERMEDIATE_TERMS:
                raise AlgebraValidationError(
                    f"expand step {index + 1} produced more than {MAX_INTERMEDIATE_TERMS:,} "
                    "intermediate terms."
                )
            # SymPy receives only the already bounded, internally constructed
            # expression for collection; it never sees the unexpanded product.
            result = self.collect(result)
            if len(result.terms) > MAX_INTERMEDIATE_TERMS:
                raise AlgebraValidationError(
                    f"SymPy collection returned more than {MAX_INTERMEDIATE_TERMS:,} terms."
                )
        return result

    def _to_expr(self, polynomial: AlgebraPolynomial):
        expression = self.sympy.Integer(0)
        for term in polynomial.terms:
            if not isinstance(term.coefficient, int) or isinstance(term.coefficient, bool):
                raise AlgebraValidationError("SymPy adapter received a non-integral coefficient.")
            product = self.sympy.Integer(term.coefficient)
            for identifier, exponent in term.monomial.powers:
                product *= self.symbol_by_id[identifier] ** exponent
            expression += product
        return expression

    def _from_expr(self, expression) -> AlgebraPolynomial:
        if expression == 0:
            return AlgebraPolynomial()
        values: dict[AlgebraMonomial, Scalar] = {}
        for term in self.sympy.Add.make_args(expression):
            coefficient, symbolic = term.as_coeff_Mul()
            if coefficient.is_Integer is not True:
                raise AlgebraValidationError("SymPy returned a non-integral coefficient.")
            powers: dict[str, int] = {}
            symbolic_powers = {} if symbolic == 1 else symbolic.as_powers_dict()
            for base, exponent in symbolic_powers.items():
                identifier = self.id_by_symbol.get(base)
                if identifier is None or exponent.is_Integer is not True:
                    raise AlgebraValidationError("SymPy returned an unregistered symbol or non-integer exponent.")
                powers[identifier] = int(exponent)
            monomial = self.registry.monomial_from_powers(powers)
            previous = values.get(monomial, 0)
            values[monomial] = int(previous) + int(coefficient)
        integer_context = CoefficientContextSpec("formal-integer", "integers", "internal")
        return AlgebraPolynomial.from_map(values, integer_context, self.registry)


def _context_from_input(raw: Any, source_ref: str) -> CoefficientContextSpec:
    if not isinstance(raw, Mapping):
        raise AlgebraValidationError("coefficient_context must be an object with id and domain.")
    identifier = _required_string(raw, "id")
    domain = _required_string(raw, "domain")
    expected = CONTEXT_DOMAINS.get(identifier)
    if expected is None:
        raise AlgebraValidationError(f"Unknown coefficient context {identifier!r}.")
    if domain != expected:
        raise AlgebraValidationError(
            f"Coefficient context {identifier!r} requires domain={expected!r}, not {domain!r}."
        )
    return CoefficientContextSpec(identifier, domain, str(raw.get("source_ref") or source_ref))


def _registry_from_input(
    raw: Any,
    context: CoefficientContextSpec,
    source_ref: str,
) -> GeneratorRegistry:
    if not isinstance(raw, list) or not raw:
        raise AlgebraValidationError("generators must be a nonempty array.")
    if len(raw) > MAX_GENERATORS:
        raise AlgebraValidationError(f"At most {MAX_GENERATORS} generators may be registered.")
    output: list[StructuredGenerator] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise AlgebraValidationError(f"generators[{index}] must be an object.")
        identifier = _required_string(item, "id")
        if not IDENTIFIER_RE.fullmatch(identifier):
            raise AlgebraValidationError(
                f"Generator id {identifier!r} must match {IDENTIFIER_RE.pattern}."
            )
        if identifier in seen:
            raise AlgebraValidationError(f"Duplicate generator id {identifier!r}.")
        seen.add(identifier)
        generator_context = str(item.get("coefficient_context_id", context.id))
        if generator_context != context.id:
            raise AlgebraValidationError(
                f"Generator {identifier!r} belongs to {generator_context!r}, not request context {context.id!r}."
            )
        kind = str(item.get("kind", "generator"))
        if kind not in {"generator", "unit"}:
            raise AlgebraValidationError(f"Generator {identifier!r} kind must be 'generator' or 'unit'.")
        output.append(StructuredGenerator(
            id=identifier,
            label=_required_string(item, "label"),
            grade=_grade_from_input(item.get("grade"), f"generator {identifier}"),
            kind=kind,
            coefficient_context_id=context.id,
            source_ref=str(item.get("source_ref") or source_ref),
        ))
    return GeneratorRegistry(output)


def _polynomial_from_input(
    raw: Any,
    context: CoefficientContextSpec,
    registry: GeneratorRegistry,
    scope: str,
) -> AlgebraPolynomial:
    if not isinstance(raw, Mapping):
        raise AlgebraValidationError(f"{scope} must be an object with a terms array.")
    raw_terms = raw.get("terms")
    if not isinstance(raw_terms, list):
        raise AlgebraValidationError(f"{scope}.terms must be an array.")
    if len(raw_terms) > MAX_TERMS:
        raise AlgebraValidationError(f"{scope} exceeds the {MAX_TERMS}-term safety limit.")
    values: dict[AlgebraMonomial, Scalar] = {}
    for index, item in enumerate(raw_terms):
        term = _term_from_input(item, context, registry, f"{scope}.terms[{index}]")
        previous = values.get(term.monomial, _scalar_zero(context))
        values[term.monomial] = _scalar_add(previous, term.coefficient, context)
    return AlgebraPolynomial.from_map(values, context, registry)


def _term_from_input(
    raw: Any,
    context: CoefficientContextSpec,
    registry: GeneratorRegistry,
    scope: str,
) -> AlgebraTerm:
    if not isinstance(raw, Mapping):
        raise AlgebraValidationError(f"{scope} must be an object.")
    coefficient = _scalar_from_input(raw.get("coefficient", 1), context, f"{scope}.coefficient")
    powers = raw.get("powers", {})
    if not isinstance(powers, Mapping):
        raise AlgebraValidationError(f"{scope}.powers must be an object.")
    return AlgebraTerm(coefficient, registry.monomial_from_powers(powers))


def _relations_from_input(
    raw: Any,
    context: CoefficientContextSpec,
    registry: GeneratorRegistry,
    default_source_ref: str,
) -> list[RewriteRule]:
    if not isinstance(raw, list):
        raise AlgebraValidationError("relations must be an array.")
    if len(raw) > MAX_RELATIONS:
        raise AlgebraValidationError(f"At most {MAX_RELATIONS} rewrite relations are allowed.")
    rules: list[RewriteRule] = []
    ids: set[str] = set()
    lhs_seen: dict[AlgebraMonomial, str] = {}
    relation_term_count = 0
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise AlgebraValidationError(f"relations[{index}] must be an object.")
        identifier = _required_string(item, "id")
        if identifier in ids:
            raise AlgebraValidationError(f"Duplicate relation id {identifier!r}.")
        ids.add(identifier)
        lhs_term = _term_from_input(item.get("lhs"), context, registry, f"relation {identifier} lhs")
        if lhs_term.coefficient != _scalar_one(context) or not lhs_term.monomial.powers:
            raise AlgebraValidationError(f"Relation {identifier!r} must have a monic nonconstant lhs.")
        if _has_negative_power(lhs_term.monomial):
            raise AlgebraValidationError(f"Relation {identifier!r} lhs cannot contain negative powers.")
        if lhs_term.monomial in lhs_seen:
            raise AlgebraValidationError(
                f"Relations {lhs_seen[lhs_term.monomial]!r} and {identifier!r} have the same lhs."
            )
        lhs_seen[lhs_term.monomial] = identifier
        rhs = _polynomial_from_input(item.get("rhs"), context, registry, f"relation {identifier} rhs")
        relation_term_count += len(rhs.terms)
        if relation_term_count > MAX_RELATION_TERMS:
            raise AlgebraValidationError(
                f"Relation right-hand sides exceed the {MAX_RELATION_TERMS:,}-term aggregate limit."
            )
        if any(_has_negative_power(term.monomial) for term in rhs.terms):
            raise AlgebraValidationError(f"Relation {identifier!r} rhs cannot contain negative powers.")
        rules.append(RewriteRule(
            id=identifier,
            lhs=lhs_term.monomial,
            rhs=rhs,
            source_ref=str(item.get("source_ref") or default_source_ref),
        ))
    return rules


def _validate_rewrite_rules(
    rules: Sequence[RewriteRule],
    context: CoefficientContextSpec,
    registry: GeneratorRegistry,
) -> dict[str, Any]:
    critical_pair_count = len(rules) * (len(rules) - 1) // 2
    if critical_pair_count > MAX_CRITICAL_PAIRS:
        raise AlgebraValidationError(
            f"This rule set requires {critical_pair_count:,} critical-pair checks, exceeding the "
            f"{MAX_CRITICAL_PAIRS:,}-pair safety limit."
        )
    for rule in rules:
        lhs_grade = rule.lhs.grade(registry)
        for term in rule.rhs.terms:
            if term.monomial.grade(registry) != lhs_grade:
                raise AlgebraValidationError(f"Relation {rule.id!r} is not homogeneous in the supplied RO grade.")
            if registry.monomial_key(term.monomial) >= registry.monomial_key(rule.lhs):
                raise AlgebraValidationError(
                    f"Relation {rule.id!r} is not decreasing in degree-lex generator order."
                )
    critical_pairs = 0
    for left_index, left in enumerate(rules):
        for right in rules[left_index + 1:]:
            lcm = _lcm(left.lhs, right.lhs, registry)
            left_start = _multiply_by_monomial(
                left.rhs, _quotient(lcm, left.lhs, registry), context, registry
            )
            right_start = _multiply_by_monomial(
                right.rhs, _quotient(lcm, right.lhs, registry), context, registry
            )
            left_normal, _ = _normal_form(left_start, rules, context, registry)
            right_normal, _ = _normal_form(right_start, rules, context, registry)
            critical_pairs += 1
            if left_normal != right_normal:
                raise AlgebraValidationError(
                    f"Critical pair {left.id!r}/{right.id!r} is unresolved."
                )
    return {
        "monomial_order": "degree-lex in registered generator order",
        "terminating": True,
        "confluent": True,
        "critical_pairs_checked": critical_pairs,
        "rules_are_explicit_input": True,
    }


def _normal_form(
    polynomial: AlgebraPolynomial,
    rules: Sequence[RewriteRule],
    context: CoefficientContextSpec,
    registry: GeneratorRegistry,
) -> tuple[AlgebraPolynomial, set[str]]:
    output = polynomial.as_map()
    applied: set[str] = set()
    for _ in range(MAX_REWRITE_STEPS):
        reduced = False
        ordered = sorted(output, key=registry.monomial_key, reverse=True)
        for monomial in ordered:
            coefficient = output[monomial]
            for rule in rules:
                if not _divides(rule.lhs, monomial):
                    continue
                del output[monomial]
                multiplier = _quotient(monomial, rule.lhs, registry)
                replacement = _multiply_by_monomial(rule.rhs, multiplier, context, registry)
                for replacement_term in replacement.terms:
                    scaled = _scalar_mul(coefficient, replacement_term.coefficient, context)
                    previous = output.get(replacement_term.monomial, _scalar_zero(context))
                    output[replacement_term.monomial] = _scalar_add(previous, scaled, context)
                    if _scalar_is_zero(output[replacement_term.monomial], context):
                        del output[replacement_term.monomial]
                    if len(output) > MAX_INTERMEDIATE_TERMS:
                        raise AlgebraValidationError(
                            f"Rewrite produced more than {MAX_INTERMEDIATE_TERMS:,} intermediate terms."
                        )
                applied.add(rule.id)
                reduced = True
                break
            if reduced:
                break
        if not reduced:
            return AlgebraPolynomial.from_map(output, context, registry), applied
    raise AlgebraValidationError(
        f"Rewrite exceeded {MAX_REWRITE_STEPS:,} steps; the rules are not safely evaluable."
    )


def _multiply_by_monomial(
    polynomial: AlgebraPolynomial,
    multiplier: AlgebraMonomial,
    context: CoefficientContextSpec,
    registry: GeneratorRegistry,
) -> AlgebraPolynomial:
    values: dict[AlgebraMonomial, Scalar] = {}
    for term in polynomial.terms:
        product = term.monomial.multiply(multiplier, registry)
        previous = values.get(product, _scalar_zero(context))
        values[product] = _scalar_add(previous, term.coefficient, context)
    return AlgebraPolynomial.from_map(values, context, registry)


def _divides(left: AlgebraMonomial, right: AlgebraMonomial) -> bool:
    right_powers = dict(right.powers)
    return all(right_powers.get(identifier, 0) >= exponent for identifier, exponent in left.powers)


def _quotient(
    numerator: AlgebraMonomial,
    denominator: AlgebraMonomial,
    registry: GeneratorRegistry,
) -> AlgebraMonomial:
    powers = dict(numerator.powers)
    for identifier, exponent in denominator.powers:
        powers[identifier] = powers.get(identifier, 0) - exponent
        if powers[identifier] == 0:
            del powers[identifier]
    return registry.monomial_from_powers(powers)


def _lcm(
    left: AlgebraMonomial,
    right: AlgebraMonomial,
    registry: GeneratorRegistry,
) -> AlgebraMonomial:
    powers = dict(left.powers)
    for identifier, exponent in right.powers:
        powers[identifier] = max(powers.get(identifier, 0), exponent)
    return registry.monomial_from_powers(powers)


def _one_polynomial(
    context: CoefficientContextSpec,
    registry: GeneratorRegistry,
) -> AlgebraPolynomial:
    return AlgebraPolynomial.from_map({AlgebraMonomial(): _scalar_one(context)}, context, registry)


def _scalar_from_input(raw: Any, context: CoefficientContextSpec, scope: str) -> Scalar:
    if context.domain == "integers":
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise AlgebraValidationError(f"{scope} must be an integer in the formal-integer context.")
        return raw
    if context.domain == "F4":
        if not isinstance(raw, Mapping) or set(raw) != {"a", "b"}:
            raise AlgebraValidationError(f"{scope} must be exactly {{'a': bit, 'b': bit}} in F4.")
        a, b = raw["a"], raw["b"]
        if isinstance(a, bool) or isinstance(b, bool) or a not in (0, 1) or b not in (0, 1):
            raise AlgebraValidationError(f"{scope} F4 coordinates must be integer bits.")
        return F4Element(a, b)
    raise AlgebraValidationError("Unsupported coefficient arithmetic context.")


def _scalar_zero(context: CoefficientContextSpec) -> Scalar:
    return 0 if context.domain == "integers" else F4Element.zero()


def _scalar_one(context: CoefficientContextSpec) -> Scalar:
    return 1 if context.domain == "integers" else F4Element.one()


def _scalar_add(left: Scalar, right: Scalar, context: CoefficientContextSpec) -> Scalar:
    if context.domain == "integers":
        if not isinstance(left, int) or isinstance(left, bool) or not isinstance(right, int) or isinstance(right, bool):
            raise AlgebraValidationError("Mixed coefficient contexts are not allowed.")
        return left + right
    if not isinstance(left, F4Element) or not isinstance(right, F4Element):
        raise AlgebraValidationError("Mixed coefficient contexts are not allowed.")
    return left + right


def _scalar_mul(left: Scalar, right: Scalar, context: CoefficientContextSpec) -> Scalar:
    if context.domain == "integers":
        if not isinstance(left, int) or isinstance(left, bool) or not isinstance(right, int) or isinstance(right, bool):
            raise AlgebraValidationError("Mixed coefficient contexts are not allowed.")
        return left * right
    if not isinstance(left, F4Element) or not isinstance(right, F4Element):
        raise AlgebraValidationError("Mixed coefficient contexts are not allowed.")
    return left * right


def _scalar_is_zero(value: Scalar, context: CoefficientContextSpec) -> bool:
    return value == _scalar_zero(context)


def _serialize_scalar(value: Scalar, context: CoefficientContextSpec) -> int | dict[str, int]:
    if context.domain == "integers":
        return int(value)
    if not isinstance(value, F4Element):
        raise AlgebraValidationError("Internal F4 coefficient mismatch.")
    return value.to_dict()


def _polynomial_to_dict(
    polynomial: AlgebraPolynomial,
    context: CoefficientContextSpec,
    registry: GeneratorRegistry,
) -> dict[str, Any]:
    terms = [
        {
            "coefficient": _serialize_scalar(term.coefficient, context),
            "powers": dict(term.monomial.powers),
            "grade": _grade_to_dict(term.monomial.grade(registry)),
        }
        for term in polynomial.terms
    ]
    grades = {(_grade_key(term.monomial.grade(registry))) for term in polynomial.terms}
    homogeneous = len(grades) <= 1
    common_grade = terms[0]["grade"] if terms and homogeneous else None
    return {
        "terms": terms,
        "term_count": len(terms),
        "homogeneous": homogeneous,
        "grade": common_grade,
    }


def _used_generator_ids(polynomials: Iterable[AlgebraPolynomial]) -> set[str]:
    return {
        identifier
        for polynomial in polynomials
        for term in polynomial.terms
        for identifier, _ in term.monomial.powers
    }


def _grade_from_input(raw: Any, scope: str) -> Grade:
    if not isinstance(raw, Mapping):
        raise AlgebraValidationError(f"{scope}.grade must be an object.")
    stem = raw.get("stem", 0)
    filtration = raw.get("filtration", 0)
    representation = raw.get("representation", {})
    if isinstance(stem, bool) or not isinstance(stem, int):
        raise AlgebraValidationError(f"{scope}.grade.stem must be an integer.")
    if isinstance(filtration, bool) or not isinstance(filtration, int):
        raise AlgebraValidationError(f"{scope}.grade.filtration must be an integer.")
    if not isinstance(representation, Mapping):
        raise AlgebraValidationError(f"{scope}.grade.representation must be an object.")
    normalized: dict[str, int] = {}
    for identifier, coefficient in representation.items():
        if not isinstance(identifier, str) or not identifier:
            raise AlgebraValidationError("Representation coordinates must be nonempty strings.")
        if isinstance(coefficient, bool) or not isinstance(coefficient, int):
            raise AlgebraValidationError("Representation coefficients must be integers.")
        if coefficient:
            normalized[identifier] = coefficient
    return Grade(stem, filtration, dict(sorted(normalized.items())))


def _scale_grade(grade: Grade, exponent: int) -> Grade:
    return Grade(
        grade.stem * exponent,
        grade.filtration * exponent,
        {identifier: coefficient * exponent for identifier, coefficient in grade.representation.items() if coefficient * exponent},
    )


def _grade_to_dict(grade: Grade) -> dict[str, Any]:
    return {
        "stem": grade.stem,
        "filtration": grade.filtration,
        "representation": dict(sorted(grade.representation.items())),
    }


def _grade_key(grade: Grade) -> tuple[int, int, tuple[tuple[str, int], ...]]:
    return grade.stem, grade.filtration, tuple(sorted(grade.representation.items()))


def _has_negative_power(monomial: AlgebraMonomial) -> bool:
    return any(exponent < 0 for _, exponent in monomial.powers)


def _required_string(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AlgebraValidationError(f"{key} must be a nonempty string.")
    return value.strip()
