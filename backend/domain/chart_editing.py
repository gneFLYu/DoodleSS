"""Exact, candidate-only chart edits at displayed coefficient occurrences."""
from copy import deepcopy
from .models import ClassNode, Grade, Differential, Proposition, new_id


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer.")
    return value


def prepare_endpoint(workspace, payload, page):
    if not isinstance(payload, dict):
        raise ValueError("Select a source and a target point first.")
    classes = {node.id: node for node in workspace.classes if not node.archived}
    base = classes.get(payload.get("classId"))
    grade = payload.get("grade", {})
    if not isinstance(grade, dict):
        raise ValueError("Endpoint grade must be an object.")
    stem = _integer(grade.get("stem"), "Stem")
    filtration = _integer(grade.get("filtration"), "Filtration")
    if filtration < 0:
        raise ValueError("Filtration must be nonnegative.")
    label = str(payload.get("label", "")).strip()
    if not label:
        raise ValueError("An endpoint label is required.")
    two = _integer(payload.get("two", 0), "2-adic level")
    j = _integer(payload.get("j", 0), "j-adic level")
    if two < 0 or two > 3 or j not in (0, 1):
        raise ValueError("Invalid coefficient port.")
    style = deepcopy(base.style) if base else {}
    terms = payload.get("terms")
    if terms is not None and not isinstance(terms, list):
        raise ValueError("Vector terms must be a list.")
    if terms:
        known = {node.style.get("e2_pattern") for node in classes.values() if node.style.get("e2_pattern")}
        components = {}
        ports = set()
        for term in terms:
            if not isinstance(term, dict):
                raise ValueError("Each vector term must be an object.")
            pattern = term.get("pattern")
            coefficient = _integer(term.get("coefficient"), "F4 coefficient")
            if not isinstance(pattern, str) or pattern not in known or coefficient not in (1, 2, 3):
                raise ValueError("The displayed vector must use known basis patterns and F4 coefficients.")
            ports.add((_integer(term.get("two", 0), "2-adic level"),
                       _integer(term.get("j", 0), "j-adic level")))
            components[pattern] = components.get(pattern, 0) ^ coefficient
        if len(ports) != 1:
            raise ValueError("This vector mixes coefficient levels; use an explicit matrix record.")
        two, j = next(iter(ports))
        if not 0 <= two <= 3 or j not in (0, 1):
            raise ValueError("Invalid vector coefficient port.")
        components = {key: value for key, value in components.items() if value}
        if not components:
            raise ValueError("A zero vector is not a differential endpoint.")
        style = {"e2_components": components}
        if len(components) == 1 and next(iter(components.values())) == 1:
            style["e2_pattern"] = next(iter(components))
    elif base is None:
        raise ValueError("The selected class is no longer available. Reload the chart.")
    if (base and not terms and base.grade.stem == stem and base.grade.filtration == filtration
            and int(base.style.get("two_valuation", 0)) == two
            and bool(base.style.get("j_order", 0)) == bool(j)
            and base.label == label):
        return base, False
    representation = deepcopy(base.grade.representation if base else
                               next(iter(classes.values())).grade.representation if classes else {})
    style.update(two_valuation=two, j_order=j, chart_occurrence_only=True)
    for key in ("multiplicative_unit", "computed_quotient"):
        style.pop(key, None)
    node = ClassNode(id=new_id("chart_endpoint"), label=label, expression=label,
                     grade=Grade(stem, filtration, representation), page=page, style=style,
                     coefficient_context_id=base.coefficient_context_id if base else "q8-residue-f4",
                     sector_id=base.sector_id if base else None,
                     notes="Explicit displayed occurrence selected for a manual candidate; not a new proved generator.")
    return node, True


def prepare_connection(workspace, payload):
    """Validate without mutation; the caller checkpoints once before applying."""
    page = _integer(payload.get("page"), "Page")
    if page < 2:
        raise ValueError("A differential page must be E2 or later.")
    kind = payload.get("kind")
    if kind not in ("differential", "relation"):
        raise ValueError("Connection must be a differential or relation.")
    source, add_source = prepare_endpoint(workspace, payload.get("source"), page)
    target, add_target = prepare_endpoint(workspace, payload.get("target"), page)
    if source.grade.representation != target.grade.representation:
        raise ValueError("Both endpoints must be in the same representation grading.")
    if kind == "differential" and (target.grade.stem != source.grade.stem - 1
                                  or target.grade.filtration != source.grade.filtration + page):
        raise ValueError(f"d_{page} must map (stem, filtration) to (stem - 1, filtration + {page}).")
    conclusion = {"source_id": source.id, "target_id": target.id, "page": page,
                  "coefficient_scope": "exact-port", "chart_occurrence_only": True,
                  "selected_occurrences": {"source": payload["source"], "target": payload["target"]}}
    statement = (f"d_{page}({source.label}) = {target.label}" if kind == "differential"
                 else f"Relation: {source.label} to {target.label}")
    proposition = Proposition(id=new_id("prop"), kind=kind, statement=statement,
                              status="candidate", conclusion=conclusion, rule="manual",
                              confidence=0.5, source_ref=payload.get("source_ref", ""),
                              notes="Selected exact coefficient ports; no periodic family or proof is inferred.")
    differential = Differential(id=new_id("diff"), source_id=source.id, target_id=target.id,
                                page=page, status="candidate", proposition_id=proposition.id,
                                unperiodic_reason="manual-chart-occurrence") if kind == "differential" else None
    nodes = ([source] if add_source else []) + ([target] if add_target else [])
    return nodes, proposition, differential
