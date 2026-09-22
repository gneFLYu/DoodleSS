"""Immutable differential events and derived class lifecycles."""
from __future__ import annotations

import re
from math import gcd

from .models import (
    ClassFate,
    DifferentialEvent,
    Project,
    Proposition,
    Workspace,
)


ACCEPTED_STATUSES = frozenset({
    "derived", "reviewed", "established", "proven",
    "admitted", "admitted-pattern", "verified-pattern", "verified", "source-verified",
})
REJECTED_STATUSES = frozenset({"rejected", "superseded"})


def is_accepted(status: str) -> bool:
    return status in ACCEPTED_STATUSES


def workspace_sequence_kind(workspace: Workspace) -> str:
    if workspace.spectral_sequence in {"hfpss", "tate"}:
        return workspace.spectral_sequence
    searchable = f"{workspace.id} {workspace.name} {workspace.grading_label}".lower()
    return "tate" if "tate" in searchable else "hfpss"


def _matching_proposition(workspace: Workspace, differential) -> Proposition | None:
    for proposition in workspace.propositions:
        conclusion = proposition.conclusion
        if (
            proposition.kind == "differential"
            and conclusion.get("source_id") == differential.source_id
            and conclusion.get("target_id") == differential.target_id
            and int(conclusion.get("page", -1)) == differential.page
        ):
            return proposition
    return None


def ensure_differential_propositions(workspace: Workspace) -> None:
    """Give every differential exactly one auditable assertion link.

    Legacy arrows are linked to their matching imported proposition.  If the
    old file has no such proposition, a visibly source-scoped migration claim
    is created rather than treating the arrow as an unrecorded theorem.
    """
    by_id = {item.id: item for item in workspace.propositions}
    for differential in workspace.differentials:
        proposition = by_id.get(differential.proposition_id)
        if proposition is None:
            proposition = _matching_proposition(workspace, differential)
        if proposition is None:
            proposition = Proposition(
                id=f"prop_for_{differential.id}",
                kind="differential",
                statement=(
                    f"Imported d_{differential.page}: "
                    f"{differential.source_id} -> {differential.target_id}"
                ),
                status=differential.status,
                conclusion={
                    "source_id": differential.source_id,
                    "target_id": differential.target_id,
                    "page": differential.page,
                },
                rule="LegacyMigration",
                confidence=0.5,
                notes="Generated only to preserve the provenance boundary of a legacy arrow.",
                source_ref="Legacy project differential record",
                source_refs=["Legacy project differential record"],
            )
            workspace.propositions.append(proposition)
            by_id[proposition.id] = proposition
        differential.proposition_id = proposition.id


def sync_differential_events(workspace: Workspace) -> None:
    """Materialize missing event records without deleting imported history."""
    ensure_differential_propositions(workspace)
    classes = {item.id: item for item in workspace.classes}
    propositions = {item.id: item for item in workspace.propositions}
    existing = {item.id for item in workspace.differential_events}
    sequence = workspace_sequence_kind(workspace)

    for differential in workspace.differentials:
        source = classes.get(differential.source_id)
        target = classes.get(differential.target_id)
        if not source or not target:
            continue
        proposition = propositions.get(differential.proposition_id)
        source_refs = []
        if proposition:
            source_refs = list(proposition.source_refs)
            if proposition.source_ref and proposition.source_ref not in source_refs:
                source_refs.append(proposition.source_ref)
        source_in_hfpss = source.grade.filtration >= 0
        comparison_status = "transports_to_hfpss"
        if sequence == "tate" and not source_in_hfpss:
            comparison_status = "tate_only_negative_source"

        for role, node, counterpart in (
            ("supports", source, target),
            ("receives", target, source),
        ):
            event_id = f"event_{differential.id}_{role}"
            if event_id in existing:
                if getattr(differential, "required_admitted_premises", False) is True:
                    for event in workspace.differential_events:
                        if event.id == event_id:
                            # Enrich existing audit provenance, never erase it.
                            event.required_admitted_premises = True
                continue
            workspace.differential_events.append(
                DifferentialEvent(
                    id=event_id,
                    spectral_sequence=sequence,
                    page=differential.page,
                    role=role,
                    class_id=node.id,
                    counterpart_class_id=counterpart.id,
                    differential_claim_id=differential.id,
                    source_filtration=source.grade.filtration,
                    target_filtration=target.grade.filtration,
                    source_exists_in_hfpss=source_in_hfpss,
                    comparison_status=comparison_status,
                    proposition_id=differential.proposition_id,
                    source_refs=source_refs,
                    status=differential.status,
                    required_admitted_premises=getattr(differential, "required_admitted_premises", False),
                )
            )
            existing.add(event_id)


def _coefficient_scalar(value: object) -> int:
    """Parse the frontend's F4 encoding, not ordinary integer reduction mod 2."""
    if type(value) in (int, float) and value in (0, 1, 2, 3):
        return int(value)
    if isinstance(value, str):
        name = value.strip().lower().replace("\\zeta", "zeta").replace("ζ", "zeta")
        name = re.sub(r"\^\{2\}|\^2|²", "2", name)
        name = re.sub(r"\s", "", name)
        names = {"0": 0, "1": 1, "2": 2, "3": 3, "z": 2, "zeta": 2,
                 "z2": 3, "zeta2": 3, "1+zeta": 3, "zeta+1": 3}
        if name in names:
            return names[name]
    raise ValueError("Invalid F4 scalar")


def _raw_parameter_record(workspace: Workspace, ident: str) -> dict:
    """Read a shared source-field unit, without evaluating or following links."""
    declarations = [claim.conclusion.get("coefficient_parameter") for claim in workspace.propositions]
    declarations = [spec for spec in declarations if isinstance(spec, dict) and spec.get("id") == ident]
    assignments = workspace.settings.get("coefficient_assignments", {})
    assignments = assignments if isinstance(assignments, dict) else {}
    values, invalid = set(), False
    for spec in declarations:
        for value in (spec.get("value"), assignments.get(ident)):
            if value is None:
                continue
            try:
                scalar = _coefficient_scalar(value)
                if not scalar:
                    raise ValueError("A source parameter must be an F4 unit")
                values.add(scalar)
            except ValueError:
                invalid = True
    return {"declarations": declarations, "values": values, "invalid": invalid,
            "domains": [spec["domain"] for spec in declarations if isinstance(spec.get("domain"), list)]}


def _source_parameter_constraint_conflict(workspace: Workspace, page: int) -> bool:
    """Check the existing finite coefficient constraints, without recursive fate queries."""
    claims = {item.id: item for item in workspace.propositions}
    matrices = {item.id: item for item in workspace.differential_maps}
    active_parameters, active_facts, active_fact_pages, constraints = set(), set(), set(), {}
    for arrow in workspace.differentials:
        if not is_accepted(arrow.status):
            continue
        if arrow.linear_map_id:
            matrix = matrices.get(arrow.linear_map_id)
            if matrix is None or matrix.archived or not is_accepted(matrix.status):
                continue
        claim = claims.get(arrow.proposition_id)
        metadata = claim.conclusion if claim else {}
        spec = metadata.get("coefficient_parameter")
        if isinstance(spec, dict) and isinstance(spec.get("id"), str):
            active_parameters.add(spec["id"])
        if metadata.get("fact_id"):
            active_facts.add(metadata["fact_id"])
            active_fact_pages.add((metadata["fact_id"], arrow.page))
        for constraint in metadata.get("coefficient_constraints", []):
            if isinstance(constraint, dict) and constraint.get("id"):
                constraints[constraint["id"]] = constraint
    for constraint in constraints.values():
        ids, constraint_page = constraint.get("parameter_ids"), constraint.get("page")
        if (constraint.get("kind") != "equal-nonzero-parameters" or not isinstance(ids, list)
                or type(constraint_page) is not int or constraint_page > page
                or not all(isinstance(ident, str) and ident in active_parameters for ident in ids)
                or not all(fact in active_facts for fact in constraint.get("required_facts", []))
                or not all(isinstance(item, dict) and (item.get("fact_id"), item.get("page")) in active_fact_pages
                           for item in constraint.get("required_differentials", []))):
            continue
        records = [_raw_parameter_record(workspace, ident) for ident in ids]
        if not records or any(len(record["values"]) != 1 for record in records):
            continue
        values = {next(iter(record["values"])) for record in records}
        normalization = constraint.get("normalization_value")
        if (len(values) > 1 or ("normalization_value" in constraint
                              and (type(normalization) not in (int, float)
                                   or any(value != normalization for value in values)))):
            return True
    return False


def _linked_source_parameter(workspace: Workspace, ident: str, declarations: list[dict],
                             *, project: Project | None = None) -> dict:
    """Resolve one explicit link to a raw unit, never a source's transformed coefficient.

    The result is computed from the supplied live project on every query. An
    isolated workspace cannot resolve a cross-workspace link. Nested links and
    locally overridden linked units are deliberately unsupported.
    """
    def failure(reason):
        return {"resolved": False, "id": ident, "reason": "linked coefficient " + reason}

    bindings = []
    for spec in declarations:
        binding = spec.get("source_parameter")
        if not isinstance(binding, dict):
            return failure("declarations have mismatched source bindings")
        if (not all(isinstance(binding.get(key), str) and binding[key]
                    for key in ("workspace_id", "parameter_id", "differential_id"))
                or type(binding.get("page")) not in (int, float)
                or binding["page"] < 2
                or (type(binding["page"]) is float and not binding["page"].is_integer())):
            return failure("source binding is invalid")
        if binding["parameter_id"] != ident:
            return failure("parameter id does not match its source binding")
        bindings.append(tuple(binding[key] for key in ("workspace_id", "parameter_id", "differential_id", "page")))
    if not bindings or any(binding != bindings[0] for binding in bindings):
        return failure("declarations have mismatched source bindings")
    assignments = workspace.settings.get("coefficient_assignments", {})
    assignments = assignments if isinstance(assignments, dict) else {}
    if assignments.get(ident) is not None or any(spec.get("value") is not None for spec in declarations):
        return failure("cannot have a local assignment")
    if project is None:
        return failure("requires project context")
    workspace_id, source_id, differential_id, page = bindings[0]
    sources = [item for item in project.workspaces if item.id == workspace_id]
    if len(sources) != 1:
        return failure("source workspace is missing or ambiguous")
    source = sources[0]
    arrows = [item for item in source.differentials if item.id == differential_id]
    if len(arrows) != 1:
        return failure("source differential is missing or ambiguous")
    arrow = arrows[0]
    if arrow.page != page:
        return failure("source differential page does not match")
    if not is_accepted(arrow.status):
        return failure("source differential is not accepted")
    if arrow.linear_map_id:
        matrices = [item for item in source.differential_maps if item.id == arrow.linear_map_id]
        if len(matrices) != 1 or matrices[0].archived or not is_accepted(matrices[0].status):
            return failure("source linear map is not accepted")
    claims = [item for item in source.propositions if item.id == arrow.proposition_id]
    spec = claims[0].conclusion.get("coefficient_parameter") if len(claims) == 1 else None
    if not isinstance(spec, dict) or spec.get("id") != source_id:
        return failure("source differential parameter does not match")
    if not is_accepted(claims[0].status):
        return failure("source proposition is not accepted")
    record = _raw_parameter_record(source, source_id)
    if any("source_parameter" in item for item in record["declarations"]):
        return failure("nested source bindings are unsupported")
    if record["invalid"]:
        return failure("source assignment is invalid")
    if len(record["values"]) > 1:
        return failure("source assignments conflict")
    if not record["values"]:
        return failure("source parameter is unresolved")
    value = next(iter(record["values"]))
    if any(not any(type(item) in (int, float) and item == value for item in domain)
           for domain in record["domains"]):
        return failure("source assignment is outside its domain")
    if _source_parameter_constraint_conflict(source, page):
        return failure("source coefficient constraints conflict")
    return {"resolved": True, "id": ident, "value": value}


def _cycle_premises_accepted(workspace: Workspace, claim: Proposition, project: Project | None = None) -> bool:
    """Resolve local premises unless an explicit workspace locator qualifies the ID."""
    if (claim.premise_ids is None or claim.premise_ids == []) and not claim.conclusion.get("external_premises"):
        if "external_premises" in claim.conclusion and claim.conclusion["external_premises"] != []:
            return False
        return True  # Preserve legacy certificates with no declared premises.
    scopes = list(project.workspaces) if project is not None else []
    if not any(owner is workspace for owner in scopes):
        scopes.append(workspace)
    records_by_scope, visiting, admitted = {}, set(), {}

    def records(owner):
        key = id(owner)
        if key not in records_by_scope:
            values = {}
            for item in owner.propositions:
                values[item.id] = None if item.id in values else item
            records_by_scope[key] = values
        return records_by_scope[key]

    def visit(owner, proof):
        if (proof is None or not isinstance(proof.id, str) or not proof.id.strip()
                or records(owner).get(proof.id) is not proof or not is_accepted(proof.status)
                or proof.kind == "tombstone"):
            return False
        key = (id(owner), proof.id)
        if key in visiting:
            return False
        if key in admitted:
            return admitted[key]
        premises = proof.premise_ids if proof.premise_ids is not None else []
        external = proof.conclusion.get("external_premises", [])
        if not isinstance(premises, list) or not isinstance(external, list):
            return False
        locators = {}
        for locator in external:
            if not isinstance(locator, dict):
                return False
            scope_id, proof_id = locator.get("workspace_id"), locator.get("proposition_id")
            if (not isinstance(scope_id, str) or not scope_id.strip()
                    or not isinstance(proof_id, str) or not proof_id.strip()
                    or proof_id not in premises or proof_id in locators):
                return False
            locators[proof_id] = scope_id

        def resolve(ident):
            if not isinstance(ident, str) or not ident.strip():
                return False
            target_owner = owner
            if ident in locators:
                matches = [candidate for candidate in scopes if candidate.id == locators[ident]]
                if len(matches) != 1:
                    return False
                target_owner = matches[0]
            return visit(target_owner, records(target_owner).get(ident))

        visiting.add(key)
        result = all(resolve(ident) for ident in premises)
        visiting.remove(key)
        admitted[key] = result
        return result

    return visit(workspace, claim)


def _cycle_claim_covers(workspace: Workspace, claim: Proposition, node, page: int, project: Project | None = None) -> bool:
    """Match a zero-outgoing certificate, never a certificate of nonzero survival.

    A forward g multiple inherits d_r=0, but may be an incoming boundary.
    Compare the transported endpoint's actual vector, not source-basis metadata.
    This scalar guard does not attempt general linear-subspace containment.
    """
    if claim.kind not in {"permanent-cycle", "zero-differential"} or not is_accepted(claim.status):
        return False
    if not _cycle_premises_accepted(workspace, claim, project):
        return False
    data = claim.conclusion
    start = data.get("page", 2)
    if page < start or (claim.kind == "zero-differential" and page != start):
        return False
    source_id = data.get("source_id", data.get("class_id"))
    source = next((c for c in workspace.classes if c.id == source_id), None)
    if source is None or source.archived or node is None or node.archived:
        return False
    if node.grade.representation != source.grade.representation:
        return False
    try:
        source_two, target_two = (int(c.style.get("two_valuation", 0)) for c in (source, node))
        source_j, target_j = (int(c.style.get("j_order", 0)) > 0 for c in (source, node))
    except (TypeError, ValueError):
        return False
    if target_two < source_two or (source_j and not target_j):
        return False
    constraint = data.get("cycle_constraint")
    scope = data.get("coefficient_scope") or (
        constraint.get("coefficient_scope") if isinstance(constraint, dict) else None)
    if scope == "exact-port":
        if target_two != source_two or target_j != source_j:
            return False
    elif scope != "all-multiples" and (scope or constraint or claim.kind == "permanent-cycle"):
        if target_j != source_j:
            return False
    # Explicit scopes apply even to same-ID endpoint copies. With neither
    # scope nor constraint, a legacy zero map retains its module closure.
    def vector(item):
        return item.style.get("e2_components") or (
            {item.style["e2_pattern"]: 1} if item.style.get("e2_pattern") else {})
    try:
        a = {k: _coefficient_scalar(v) for k, v in vector(source).items() if _coefficient_scalar(v)}
        b = {k: _coefficient_scalar(v) for k, v in vector(node).items() if _coefficient_scalar(v)}
    except ValueError:
        return False
    product = ((0, 0, 0, 0), (0, 1, 2, 3), (0, 2, 3, 1), (0, 3, 1, 2))
    if source.id != node.id and (not a or set(a) != set(b)
            or not any(all(b[k] == product[u][a[k]] for k in a) for u in (1, 2, 3))):
        return False
    stem = node.grade.stem - source.grade.stem
    filtration = node.grade.filtration - source.grade.filtration
    forward = data.get("forward_period", {})
    if filtration:
        step = forward.get("filtration", 0)
        if not step or filtration < 0 or filtration % step:
            return False
        stem -= filtration // step * forward.get("stem", 0)
    period = data.get("period_stem", 0)
    return stem == 0 or bool(period and stem % period == 0)


def _requires_admitted_premises(differential, claim) -> bool:
    """Only explicitly opted-in ordinary rows change their legacy admission."""
    return (getattr(differential, "required_admitted_premises", False) is not False
            or bool(claim is not None and isinstance(claim.conclusion, dict)
                    and "required_admitted_premises" in claim.conclusion))


def _required_differential_premises_accepted(workspace: Workspace, differential,
                                          *, project: Project | None = None) -> bool:
    proofs = [item for item in workspace.propositions if item.id == differential.proposition_id]
    claim = proofs[0] if len(proofs) == 1 else None
    if (not _requires_admitted_premises(differential, claim)
            and not any(_requires_admitted_premises(differential, item) for item in proofs)):
        return True
    # The row retains the opt-in when its proof is removed. Neither a missing
    # mirror nor a truthy non-boolean flag may restore legacy admission.
    return bool(getattr(differential, "required_admitted_premises", False) is True
                and claim is not None and isinstance(claim.conclusion, dict)
                and claim.conclusion.get("required_admitted_premises") is True
                and claim.kind == "differential" and is_accepted(claim.status)
                and isinstance(claim.premise_ids, list) and bool(claim.premise_ids)
                and _cycle_premises_accepted(workspace, claim, project))


class _EventEligibility(dict[str, bool]):
    """Event guards plus the live rows that genuinely contradict a cycle."""

    def __init__(self):
        super().__init__()
        self.cycle_conflict_ids: set[str] = set()


def _isolated_rank_one_unit(workspace: Workspace, differential, *, project: Project | None = None) -> bool:
    """Qualify an unknown unit's kernel/image, never resolve its scalar.

    This deliberately handles only the native finite patterns used by the
    certified mixed d17/d19. It is not a matrix solver or a survival certificate.
    Periodic incidence uses a superset of allowed translates: treating the
    g lattice bilaterally here can only refuse an unsafe admission, never
    infer inverse-g survival or create an event at a translated class.
    """
    claims = {item.id: item for item in workspace.propositions}
    classes = {item.id: item for item in workspace.classes}
    claim = claims.get(differential.proposition_id)
    if (not is_accepted(differential.status) or differential.linear_map_id
            or claim is None or not is_accepted(claim.status) or claim.kind != "differential"
            or not _required_differential_premises_accepted(workspace, differential, project=project)
            or sum(item.id == differential.id for item in workspace.differentials) != 1
            or sum(item.id == claim.id for item in workspace.propositions) != 1):
        return False
    data = claim.conclusion
    certificate, spec = data.get("rank_one_unit_certificate"), data.get("coefficient_parameter")
    if (not isinstance(certificate, dict) or certificate.get("status") != "verified"
            or certificate.get("kind") != "isolated-finite-F4-isomorphism"
            or type(certificate.get("page")) is not int or certificate["page"] != differential.page
            or certificate.get("coefficient_scope") != "exact-port"
            or data.get("coefficient_scope") != "exact-port" or data.get("zero")
            or data.get("source_id") != differential.source_id
            or data.get("target_id") != differential.target_id or data.get("page") != differential.page
            or "coefficient_condition" in data or not isinstance(spec, dict)):
        return False
    ident, domain = spec.get("id"), spec.get("domain")
    if (not isinstance(ident, str) or not ident or "value" not in spec or spec["value"] is not None
            or type(spec.get("frobenius_power")) is not int or spec["frobenius_power"] not in (0, 1)
            or not isinstance(domain, list) or not domain
            or any(type(value) is not int or value not in (1, 2, 3) for value in domain)
            or any(key in spec for key in ("affine_offset", "target_component", "source_parameter",
                                          "inverse_parameter_id"))):
        return False
    record = _raw_parameter_record(workspace, ident)
    if record["invalid"] or record["values"] or len(record["declarations"]) != 1:
        return False
    for other in workspace.propositions:
        metadata = other.conclusion
        parameter = metadata.get("coefficient_parameter")
        condition = metadata.get("coefficient_condition")
        constraints = metadata.get("coefficient_constraints", [])
        if (isinstance(parameter, dict) and parameter.get("inverse_parameter_id") == ident
                or isinstance(condition, dict) and condition.get("parameter_id") == ident
                or not isinstance(constraints, list)
                or any(not isinstance(item, dict) or not isinstance(item.get("parameter_ids", []), list)
                       or ident in item.get("parameter_ids", [])
                       for item in constraints)):
            return False

    def native(node, pattern):
        style = node.style if node else {}
        base = {"S02": (0, 2), "S53": (5, 3), "S73": (7, 3)}.get(pattern)
        if (node is None or base is None or type(node.grade.stem) is not int
                or type(node.grade.filtration) is not int or node.grade.filtration < base[1]
                or (node.grade.filtration - base[1]) % 4
                or (node.grade.stem - base[0] - 5 * (node.grade.filtration - base[1])) % 8):
            return False
        return bool(node and not node.archived and node.page <= differential.page
                    and pattern in {"S02", "S53", "S73"} and style.get("e2_pattern") == pattern
                    and "e2_components" not in style and "e2_basis_patterns" not in style
                    and not node.cell_id and not node.coordinates
                    and all(type(style.get(key, 0)) is int and style.get(key, 0) == 0
                            for key in ("two_valuation", "j_order")))

    source, target = classes.get(differential.source_id), classes.get(differential.target_id)
    if not native(source, certificate.get("source_pattern")) or not native(target, certificate.get("target_pattern")):
        return False
    if (source.grade.representation != target.grade.representation
            or target.grade.stem != source.grade.stem - 1
            or target.grade.filtration != source.grade.filtration + differential.page):
        return False

    def periods(arrow):
        # Overapproximate D8/g incidence even for a currently finite seed.
        generators = [(64, 0), (20, 4)]
        for stem, filtration in [(arrow.period_stem, arrow.period_filtration)]:
            if type(stem) is not int or type(filtration) is not int:
                return None
            if stem or filtration:
                generators.append((stem, filtration))
        if arrow.period_family_id:
            family = next((item for item in project.period_families if item.id == arrow.period_family_id), None) if project else None
            if family is None:
                return None  # An unavailable family may contain another shift.
            for generator in family.generators:
                grade = generator.grade_shift
                if grade.representation or type(grade.stem) is not int or type(grade.filtration) is not int:
                    return None
                generators.append((grade.stem, grade.filtration))
        if arrow.manual_periodicity_id or arrow.periodicity_rule_id:
            return None
        return generators

    def intersects(left, right, generators):
        if left.grade.representation != right.grade.representation:
            return False
        delta = (right.grade.stem - left.grade.stem, right.grade.filtration - left.grade.filtration)
        if any(type(value) is not int for value in delta):
            return True
        determinant = lambda a, b: a[0] * b[1] - a[1] * b[0]
        index = 0
        for a in generators:
            for b in generators:
                index = gcd(index, abs(determinant(a, b)))
        return all(determinant(delta, generator) % index == 0 for generator in generators)

    def patterns(node):
        components = node.style.get("e2_components")
        if components is not None:
            if not isinstance(components, dict):
                return None
            try:
                return {key for key, value in components.items() if _coefficient_scalar(value)}
            except ValueError:
                return None
        return {node.style["e2_pattern"]} if node.style.get("e2_pattern") else None

    generators = periods(differential)
    if generators is None:
        return False
    for other in workspace.differentials:
        if other.id == differential.id or other.page > differential.page or other.status in REJECTED_STATUSES:
            continue
        other_claim = claims.get(other.proposition_id)
        # A prior accepted map touching an endpoint invalidates scalar-event
        # survival. This narrow path must not remove the late target anyway.
        if other.page < differential.page and (not is_accepted(other.status)
                or other_claim is None or not is_accepted(other_claim.status)):
            continue
        if other_claim and other_claim.conclusion.get("zero"):
            continue
        endpoints = [classes.get(other.source_id), classes.get(other.target_id)]
        if any(node is None for node in endpoints) or other.linear_map_id:
            return False
        if any(node.archived for node in endpoints):
            continue
        other_generators = periods(other)
        if other_generators is None:
            return False
        for node in endpoints:
            basis = patterns(node)
            for endpoint in (source, target):
                if (basis is None or endpoint.style["e2_pattern"] in basis) and intersects(
                        endpoint, node, generators + other_generators):
                    return False
    # A vector class/cell can couple native ports without an explicit second
    # scalar arrow. Refuse this case instead of guessing its diagonal kernel.
    for node in workspace.classes:
        if node.archived or node.page > differential.page or node.id in {source.id, target.id}:
            continue
        if not (node.cell_id or node.coordinates or "e2_components" in node.style
                or "e2_basis_patterns" in node.style):
            continue
        basis = patterns(node)
        for endpoint in (source, target):
            if (basis is None or endpoint.style["e2_pattern"] in basis) and intersects(endpoint, node, generators):
                return False
    return True


def _parameterized_event_eligibility(workspace: Workspace, *, project: Project | None = None) -> dict[str, bool]:
    """Recheck live coefficients without rewriting immutable event evidence.

    Match page-algebra.js: declarations sharing an id share one source-field
    unit; add the affine offset BEFORE Frobenius. Constraint prerequisites use
    accepted differential rows (and accepted, nonarchived matrices), including
    the exact required fact/page. This is only a conservative scalar guard, not
    a replacement for vector kernels or a proof of any reviewed differential.
    Zero-outgoing contradictions also block unparameterized events on that
    page and afterwards; immutable imported history remains untouched.
    """
    claims = {item.id: item for item in workspace.propositions}
    differentials = {item.id: item for item in workspace.differentials}
    matrices = {item.id: item for item in workspace.differential_maps}
    classes = {item.id: item for item in workspace.classes}
    assignments = workspace.settings.get("coefficient_assignments", {})
    if not isinstance(assignments, dict):
        assignments = {}
    parameters: dict[str, set[int]] = {}
    parameter_domains: dict[str, list[list]] = {}
    invalid = set()
    for claim in claims.values():
        spec = claim.conclusion.get("coefficient_parameter")
        if not isinstance(spec, dict) or not isinstance(spec.get("id"), str) or not spec["id"]:
            continue
        ident = spec["id"]
        values = parameters.setdefault(ident, set())
        if isinstance(spec.get("domain"), list):
            parameter_domains.setdefault(ident, []).append(spec["domain"])
        for value in (spec.get("value"), assignments.get(ident)):
            if value is None:
                continue
            try:
                scalar = _coefficient_scalar(value)
                if scalar == 0:
                    raise ValueError("Base parameter is a nonzero unit")
                values.add(scalar)
            except ValueError:
                invalid.add(ident)
    declarations_by_id: dict[str, list[dict]] = {}
    for claim in claims.values():
        spec = claim.conclusion.get("coefficient_parameter")
        if isinstance(spec, dict) and isinstance(spec.get("id"), str) and spec["id"]:
            declarations_by_id.setdefault(spec["id"], []).append(spec)
    for ident, declarations in declarations_by_id.items():
        if not any("source_parameter" in spec for spec in declarations):
            continue
        linked = _linked_source_parameter(workspace, ident, declarations, project=project)
        parameters[ident] = {linked["value"]} if linked["resolved"] else set()
        if not linked["resolved"]:
            invalid.add(ident)

    def coefficient(spec):
        if not isinstance(spec, dict):
            return None
        ident = spec.get("id")
        if not isinstance(ident, str) or ident in invalid:
            return None
        values = parameters.get(ident, set())
        if len(values) != 1:
            return None
        value = next(iter(values))
        domain = spec.get("domain")
        if isinstance(domain, list) and not any(type(x) in (int, float) and x == value for x in domain):
            return None
        power = spec.get("frobenius_power")
        if type(power) not in (int, float) or power not in (0, 1):
            return None
        try:
            value ^= _coefficient_scalar(spec.get("affine_offset", 0) if spec.get("affine_offset") is not None else 0)
        except ValueError:
            return None
        if "inverse_parameter_id" in spec:
            denominator_id = spec["inverse_parameter_id"]
            if not isinstance(denominator_id, str) or not denominator_id or denominator_id in invalid:
                return None
            denominators = parameters.get(denominator_id, set())
            if len(denominators) != 1:
                return None
            denominator = next(iter(denominators))
            if any(not any(type(item) in (int, float) and item == denominator for item in domain)
                   for domain in parameter_domains.get(denominator_id, [])):
                return None
            product = ((0, 0, 0, 0), (0, 1, 2, 3), (0, 2, 3, 1), (0, 3, 1, 2))
            value = product[value][{1: 1, 2: 3, 3: 2}[denominator]]
        return {0: 0, 1: 1, 2: 3, 3: 2}[value] if power else value

    def condition(metadata):
        if "coefficient_condition" not in metadata:
            return True
        predicate = metadata["coefficient_condition"]
        if not isinstance(predicate, dict):
            return None
        ident, expected = predicate.get("parameter_id"), predicate.get("equals")
        if (not isinstance(ident, str) or not ident or ident in invalid
                or type(expected) not in (int, float) or expected not in (1, 2, 3)
                or predicate.get("otherwise") != "zero-euler-image"):
            return None
        values = parameters.get(ident, set())
        if len(values) != 1:
            return None
        value = next(iter(values))
        if any(not any(type(item) in (int, float) and item == value for item in domain)
               for domain in parameter_domains.get(ident, [])):
            return None
        return value == expected

    def effective_coefficient(metadata):
        nonzero = condition(metadata)
        if nonzero is None:
            return None
        if not nonzero:
            return 0  # A zero Euler image needs no choice of its unused unit.
        if "coefficient_parameter" not in metadata:
            return 1
        return coefficient(metadata["coefficient_parameter"])

    def accepted(diff):
        if (not is_accepted(diff.status)
                or not _required_differential_premises_accepted(workspace, diff, project=project)):
            return False
        if not diff.linear_map_id:
            return True
        matrix = matrices.get(diff.linear_map_id)
        return matrix is not None and not matrix.archived and is_accepted(matrix.status)

    def component_valid(spec, diff):
        if not isinstance(spec, dict) or "target_component" not in spec:
            return True
        target = classes.get(diff.target_id)
        style = target.style if target else {}
        basis = style.get("e2_basis_patterns", list(style.get("e2_components", {})))
        return isinstance(spec["target_component"], str) and spec["target_component"] in basis

    active_parameters, active_facts, active_fact_pages = set(), set(), set()
    constraints, blocked_pages, cycle_blocked_pages = {}, [], []
    result = _EventEligibility()
    unit_invariant_ids = {
        diff.id for diff in differentials.values()
        if diff.proposition_id in claims and effective_coefficient(claims[diff.proposition_id].conclusion) is None
        and _isolated_rank_one_unit(workspace, diff, project=project)
    }
    for diff in differentials.values():
        if not accepted(diff):
            continue
        claim = claims.get(diff.proposition_id)
        metadata = claim.conclusion if claim else {}
        spec = metadata.get("coefficient_parameter")
        if spec is not None or "coefficient_condition" in metadata:
            if isinstance(spec, dict) and isinstance(spec.get("id"), str):
                active_parameters.add(spec["id"])
            scalar = effective_coefficient(metadata)
            if ((scalar is None and diff.id not in unit_invariant_ids)
                    or (scalar is not None and scalar != 0 and not component_valid(spec, diff))):
                blocked_pages.append(diff.page)
        if metadata.get("fact_id"):
            active_facts.add(metadata["fact_id"])
            active_fact_pages.add((metadata["fact_id"], diff.page))
        for constraint in metadata.get("coefficient_constraints", []):
            if isinstance(constraint, dict) and constraint.get("id"):
                constraints[constraint["id"]] = constraint
        scalar = effective_coefficient(metadata)
        nonzero = (scalar is not None and scalar != 0 and component_valid(spec, diff)) or diff.id in unit_invariant_ids
        if (scalar == 0 and isinstance(spec, dict) and spec.get("target_component")
                and component_valid(spec, diff) and condition(metadata) is True):
            target = classes.get(diff.target_id)
            try:
                nonzero = bool(target and any(
                    _coefficient_scalar(v) for k, v in target.style.get("e2_components", {}).items()
                    if k != spec["target_component"]))
            except ValueError:
                nonzero = False
        if nonzero and not metadata.get("zero") and any(
            _cycle_claim_covers(workspace, cycle, classes.get(diff.source_id), diff.page, project)
            for cycle in claims.values()
        ):
            cycle_blocked_pages.append(diff.page)
            result.cycle_conflict_ids.add(diff.id)
    for constraint in constraints.values():
        ids = constraint.get("parameter_ids")
        if constraint.get("kind") != "equal-nonzero-parameters" or not isinstance(ids, list):
            continue
        if not all(ident in active_parameters for ident in ids):
            continue
        if not all(ident in active_facts for ident in constraint.get("required_facts", [])):
            continue
        if not all((item.get("fact_id"), item.get("page")) in active_fact_pages
                   for item in constraint.get("required_differentials", [])):
            continue
        values = [parameters.get(ident, set()) for ident in ids]
        if not values or not all(len(value) == 1 for value in values):
            continue
        scalars = {next(iter(value)) for value in values}
        normalization = constraint.get("normalization_value")
        if (len(scalars) > 1 or ("normalization_value" in constraint
                               and (type(normalization) not in (int, float)
                                    or any(value != normalization for value in scalars)))):
            page = constraint.get("page")
            if type(page) is int:
                blocked_pages.append(page)
    blocked_from = min(blocked_pages) if blocked_pages else None
    cycle_blocked_from = min(cycle_blocked_pages) if cycle_blocked_pages else None
    for event in workspace.differential_events:
        # A genuine inconsistent page cannot determine any later fate. An
        # unresolved coefficient alone leaves independent legacy evidence intact.
        if cycle_blocked_from is not None and event.page >= cycle_blocked_from:
            result[event.id] = False
            continue
        diff = differentials.get(event.differential_claim_id)
        claim = claims.get(diff.proposition_id if diff else event.proposition_id)
        historical_claim = claims.get(event.proposition_id)
        metadata = claim.conclusion if claim else {}
        spec = metadata.get("coefficient_parameter")
        historical_spec = historical_claim.conclusion.get("coefficient_parameter") if historical_claim else None
        event_mirror = getattr(event, "required_admitted_premises", False)
        event_proof_guarded = event_mirror is not False
        if event_proof_guarded and (event_mirror is not True or diff is None
                or getattr(diff, "required_admitted_premises", False) is not True or not accepted(diff)):
            result[event.id] = False
            continue
        proof_guarded = event_proof_guarded or _requires_admitted_premises(diff, claim) or any(
            _requires_admitted_premises(None, item) for item in workspace.propositions
            if item.id == (diff.proposition_id if diff else event.proposition_id))
        historical_proof_guarded = _requires_admitted_premises(None, historical_claim)
        if (proof_guarded or historical_proof_guarded) and (diff is None or not accepted(diff)):
            result[event.id] = False
            continue
        guarded = proof_guarded or spec is not None or "coefficient_condition" in metadata
        historical_guarded = historical_spec is not None or (
            historical_claim is not None and "coefficient_condition" in historical_claim.conclusion) or historical_proof_guarded
        if not guarded and not historical_guarded:
            continue
        scalar = effective_coefficient(metadata) if guarded else None
        component = spec.get("target_component") if isinstance(spec, dict) else None
        unit_invariant = diff is not None and diff.id in unit_invariant_ids
        relative_nonzero = (scalar is not None and scalar != 0) or unit_invariant
        same_target_line = True
        if isinstance(spec, dict) and "target_component" in spec and condition(metadata) is True:
            target = classes.get(diff.target_id) if diff else None
            components = target.style.get("e2_components", {}) if target else {}
            basis = target.style.get("e2_basis_patterns", list(components)) if target else []
            if not isinstance(component, str) or component not in basis:
                scalar = None
            else:
                try:
                    values = {key: _coefficient_scalar(value) for key, value in components.items()}
                except ValueError:
                    scalar = None
                    values = {}
                # The recorded class still denotes the printed vector. If
                # P+bQ is killed, P+Q is not a boundary when b differs from 1.
                others = any(value for key, value in values.items() if key != component)
                relative_nonzero = bool(others or (scalar and values.get(component)))
                same_target_line = scalar == 1 or not values.get(component) or (not others and bool(scalar))
        endpoint_ids = ((diff.source_id, diff.target_id) if diff and event.role == "supports"
                        else (diff.target_id, diff.source_id) if diff and event.role == "receives"
                        else None)
        matches = (diff and event.page == diff.page and event.proposition_id == diff.proposition_id
                   and endpoint_ids == (event.class_id, event.counterpart_class_id))
        result[event.id] = bool(matches and accepted(diff) and (scalar is not None or unit_invariant) and relative_nonzero
                                and (event.role != "receives" or same_target_line)
                                and (blocked_from is None or event.page < blocked_from))
    return result


def derive_class_fate(workspace: Workspace, class_id: str, *, project: Project | None = None,
                      _coefficient_guard=None) -> ClassFate:
    node = next(item for item in workspace.classes if item.id == class_id)
    events = [item for item in workspace.differential_events if item.class_id == class_id]
    hfpss_outgoing = [item.id for item in events if item.spectral_sequence == "hfpss" and item.role == "supports"]
    hfpss_incoming = [item.id for item in events if item.spectral_sequence == "hfpss" and item.role == "receives"]
    tate_outgoing = [item.id for item in events if item.spectral_sequence == "tate" and item.role == "supports"]
    tate_incoming = [item.id for item in events if item.spectral_sequence == "tate" and item.role == "receives"]
    coefficient_guard = (_parameterized_event_eligibility(workspace, project=project)
                         if _coefficient_guard is None else _coefficient_guard)

    accepted_deaths = sorted(
        (
            item for item in events
            if item.spectral_sequence == "hfpss"
            and item.comparison_status != "tate_only_negative_source"
            and coefficient_guard.get(item.id, is_accepted(item.status))
        ),
        key=lambda item: (item.page, 0 if item.role == "supports" else 1, item.id),
    )
    permanent_claims = [
        proposition for proposition in workspace.propositions
        if proposition.kind == "permanent-cycle"
        and _cycle_claim_covers(workspace, proposition, node, 10**9, project)
    ]
    cycle_conflict_ids = getattr(coefficient_guard, "cycle_conflict_ids", set())
    contradicted_cycles = any(
        arrow.id in cycle_conflict_ids and arrow.source_id == class_id
        for arrow in workspace.differentials)

    first_death = accepted_deaths[0] if accepted_deaths else None
    first_hfpss_death = None
    conclusion = "unresolved"
    conclusion_page: int | str | None = None
    last_live_page: int | str = "unknown"
    justification_ids: list[str] = []

    if first_death:
        first_hfpss_death = {
            "page": first_death.page,
            "role": first_death.role,
            "claim_id": first_death.differential_claim_id,
        }
        last_live_page = first_death.page
        conclusion_page = first_death.page
        conclusion = "supports_differential" if first_death.role == "supports" else "is_hit"
        justification_ids.append(first_death.proposition_id)

    if permanent_claims:
        justification_ids.extend(item.id for item in permanent_claims)
        if contradicted_cycles or (first_death and first_death.role == "supports"):
            conclusion = "unresolved"
        elif not first_death:
            conclusion = "permanent_cycle"
            conclusion_page = "infinity"
            # Permanent cycles may still be hit. Only filtration zero rules
            # out incoming HFPSS differentials without an extra certificate.
            last_live_page = "infinity" if node.grade.filtration == 0 else "unknown"

    return ClassFate(
        class_id=class_id,
        appears_from_page=node.page,
        hfpss_outgoing_events=hfpss_outgoing,
        hfpss_incoming_events=hfpss_incoming,
        tate_outgoing_events=tate_outgoing,
        tate_incoming_events=tate_incoming,
        first_hfpss_death=first_hfpss_death,
        last_hfpss_live_page=last_live_page,
        conclusion=conclusion,
        conclusion_page=conclusion_page,
        justification_ids=list(dict.fromkeys(item for item in justification_ids if item)),
    )


def sync_workspace_fates(workspace: Workspace, *, project: Project | None = None) -> None:
    """Refresh fates; cross-workspace coefficients require an explicit project."""
    sync_differential_events(workspace)
    coefficient_guard = _parameterized_event_eligibility(workspace, project=project)
    workspace.fates = [derive_class_fate(workspace, item.id, project=project, _coefficient_guard=coefficient_guard)
                       for item in workspace.classes]
    # Retain this private cache provenance if the last certificate is removed
    # between syncs; otherwise the formerly blocked deaths would stay masked.
    workspace._fate_has_cycle_certificates = any(
        item.kind in {"permanent-cycle", "zero-differential"}
        for item in workspace.propositions)
    workspace._fate_has_required_premises = any(
        _requires_admitted_premises(item, None) for item in workspace.differentials
    ) or any(_requires_admitted_premises(None, item) for item in workspace.propositions)


def sync_project_fates(project: Project) -> Project:
    for workspace in project.workspaces:
        sync_workspace_fates(workspace, project=project)
    return project


def class_is_live_on_page(workspace: Workspace, class_id: str, page: int, *, project: Project | None = None) -> bool:
    """Query current death; linked coefficients without project context stay unresolved."""
    fate = next((item for item in workspace.fates if item.class_id == class_id), None)
    # Assignments and affine/Frobenius declarations may change between syncs.
    # A cached fate must not keep killing a class after c+1 becomes zero.
    if (fate is None or getattr(workspace, "_fate_has_cycle_certificates", False)
            or getattr(workspace, "_fate_has_required_premises", False)
            or any(getattr(item, "required_admitted_premises", False) is not False
                   for item in workspace.differential_events)
            or any(_requires_admitted_premises(item, None) for item in workspace.differentials) or any(
        item.conclusion.get("coefficient_parameter") is not None
        or "coefficient_condition" in item.conclusion
        or item.kind in {"permanent-cycle", "zero-differential"}
        or _requires_admitted_premises(None, item)
        for item in workspace.propositions
    )):
        fate = derive_class_fate(workspace, class_id, project=project)
    death = fate.first_hfpss_death
    return death is None or int(death["page"]) >= page
