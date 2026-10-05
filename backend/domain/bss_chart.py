"""Read-only materialization of exact auxiliary 2-BSS display windows.

Chart nodes are projections of distinct trigraded basis vectors. Their h0
levels and full engine coordinates are retained rather than collapsed to
a Witt glyph or interpreted by the Q8 HFPSS page engine. Immediate
out-of-window differential sources and targets are visible boundary
context, never invisible arrow ends or extra in-window rank.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from hashlib import sha256
import json

from . import bss_integer, bss_sigma
from .bss_multiplication import (SOURCE_REF as PRODUCT_SOURCE, OPERATOR_TEX,
                                 OPERATOR_MONOMIAL, chart_operators, multiply,
                                 differential_preimages)
from .bss_reference import CONTEXT, CONVENTION
from .models import ClassNode, Differential, Grade, Proposition


_INTEGER_TEX = {
    "1": "1", "h1": r"h_1", "h1^2": r"h_1^2", "h1^3": r"h_1^3",
    "x": "x", "xh1": r"xh_1", "x^2": "x^2", "x^2h1": r"x^2h_1",
    "h2": r"h_2", "y": "y", "h2^2": r"h_2^2", "yh2": r"yh_2",
    "h2^3": r"h_2^3", "x^3": "x^3",
}
_SECTORS = {
    "integer": "integer", "sigma": "sigma",
    "ws_q8_bss_integer": "integer", "ws_q8_bss_sigma": "sigma",
}


def _power_tex(symbol: str, exponent: int) -> str:
    return "" if exponent == 0 else symbol if exponent == 1 else rf"{symbol}^{{{exponent}}}"


def integer_label_tex(monomial: bss_integer.BSSMonomial) -> str:
    """Canonical collected powers; h0 remains a formal Bockstein coordinate."""
    base = "" if monomial.basis == "1" else _INTEGER_TEX[monomial.basis]
    return (_power_tex("h_0", monomial.h0) + base + _power_tex("v_1", monomial.v1)
            + _power_tex("k", monomial.k) + _power_tex("D", monomial.D)) or "1"


def _coordinates(monomial) -> dict:
    return {"basis": monomial.basis, "v1": monomial.v1, "k": monomial.k,
            "D": monomial.D, "h0": monomial.h0}


def _identifier(sector: str, monomial, *, tower: bool = False) -> str:
    coordinates = monomial.as_tuple()[:-1] if tower else monomial.as_tuple()
    # Hash only the immutable algebraic identity, never the page, bounds,
    # display rank, or label formatting. The full digest avoids short hashes.
    encoded = json.dumps([sector, *coordinates], separators=(",", ":"), ensure_ascii=True)
    return f"bss_{sector}_{'tower_' if tower else ''}{sha256(encoded.encode('ascii')).hexdigest()}"


def build_bss_window(sector: str, page: int = 1, stem_min: int = -8, stem_max: int = 32,
                     filtration_min: int = 0, filtration_max: int = 8,
                     v1_max: int = 8, h0_max: int = 3, *, limit: int = 10_000,
                     include_records: bool = True) -> dict:
    """Return raw records and ordinary serializable chart model dictionaries.

    ``classes`` retains the raw-coordinate list for API consumers unless
    ``include_records=False``. ``chart`` supplies compact model dicts to
    existing SVG consumers. Every chart arrow has both endpoint nodes;
    off-window endpoints are visible, explicitly marked boundary context.

    Enumeration caps are inclusive and are always reported in ``window``.
    They limit display materialization, never global kernel/image membership.
    """
    if not isinstance(sector, str) or sector not in _SECTORS:
        raise ValueError("sector must be 'integer' or 'sigma'")
    if not isinstance(include_records, bool):
        raise ValueError("include_records must be boolean")
    sector = _SECTORS[sector]
    if isinstance(page, bool) or not isinstance(page, int) or not 1 <= page <= 4:
        raise ValueError("The 2-BSS chart accepts pages E1 through E4")
    engine = bss_integer if sector == "integer" else bss_sigma
    window = {"page": page, "stem_min": stem_min, "stem_max": stem_max,
              "filtration_min": filtration_min, "filtration_max": filtration_max,
              "v1_max": v1_max, "h0_max": h0_max}
    monomials = engine.enumerate_window(**window, limit=limit)
    visible = set(monomials)
    workspace_id = f"ws_q8_bss_{sector}"
    source_refs = list(engine.SOURCE_REFS)
    representation = {"sigma_i": -1} if sector == "sigma" else {}

    def excluded_by(monomial) -> list[str]:
        stem, filtration = monomial.bidegree
        reasons = []
        if not stem_min <= stem <= stem_max:
            reasons.append("stem_bounds")
        if not filtration_min <= filtration <= filtration_max:
            reasons.append("filtration_bounds")
        if monomial.v1 > v1_max:
            reasons.append("v1_cap")
        if monomial.h0 > h0_max:
            reasons.append("h0_cap")
        return reasons

    def label(monomial) -> str:
        return integer_label_tex(monomial) if sector == "integer" else monomial.label_tex

    def raw_terms(monomial, *, full: bool = True) -> list[dict]:
        terms = (monomial,) if sector == "integer" else bss_sigma.to_integer_basis(monomial)
        if not full:
            return [{**_coordinates(term), "coefficient": "1"} for term in terms]
        return [{**_coordinates(term), "coefficient": "1",
                 "label_tex": integer_label_tex(term) + (r"u_{\sigma_i}" if sector == "sigma" else ""),
                 "grade": {"stem": term.bidegree[0], "filtration": term.bidegree[1],
                           "representation": dict(representation)}} for term in terms]

    def record(monomial) -> dict:
        stem, filtration, h0 = monomial.tridegree
        return {"id": _identifier(sector, monomial), **_coordinates(monomial),
                "label": label(monomial), "label_tex": label(monomial),
                "grade": {"stem": stem, "filtration": filtration, "representation": dict(representation)},
                "bockstein_filtration": h0,
                "in_window": monomial in visible, "excluded_by": excluded_by(monomial),
                "representative_terms": raw_terms(monomial, full=include_records)}

    records = [record(monomial) for monomial in monomials] if include_records else []
    record_by_id = {item["id"]: item for item in records}
    chart_nodes: dict[str, dict] = {}
    chart_differentials = []
    chart_propositions = []
    differential_records = []
    outside_target_count = 0

    def compact_model(model) -> dict:
        # Missing optional dataclass fields retain their standard defaults.
        # Keep all required fields and nonempty semantic values, including 0.
        return {key: value for key, value in asdict(model).items()
                if value is not None and value != "" and value != [] and value != {}
                and value is not False}

    def ensure_node(monomial, boundary_role: str = "outgoing_target") -> dict:
        identifier = _identifier(sector, monomial)
        if identifier in chart_nodes:
            return chart_nodes[identifier]
        item = record_by_id.get(identifier) or record(monomial)
        record_by_id[identifier] = item
        node = ClassNode(
            id=identifier, label=item["label"], expression=item["label"],
            grade=Grade(monomial.bidegree[0], monomial.bidegree[1], dict(representation)),
            page=page, state="unknown", coefficient_context_id=CONTEXT, convention_id=CONVENTION,
            notes=(f"Exact 2-BSS E{page}; h0 level {monomial.h0}."
                   + (" Boundary context outside the requested caps; not part of the in-window count."
                      if monomial not in visible else "")),
            style={
                "glyph": "dot", "last_page": page, "bockstein_filtration": monomial.h0,
                "source_reference": True, "source_ref": "Exact 2-BSS engine; see workspace source review",
                "window_endpoint_only": False,
                "bss_boundary": boundary_role if monomial not in visible else "",
                "bss_in_window": monomial in visible, "bss_excluded_by": item["excluded_by"],
                "bss_engine": f"q8-2bss-{sector}-v1", "bss_engine_id": identifier,
                "bss_monomial": _coordinates(monomial),
                "bss_tower_key": _identifier(sector, monomial, tower=True),
                "bss_representative_terms": item["representative_terms"],
                "coefficient_order": 2, "chart_occurrence_only": True,
                "bss_exact_additive_basis": True,
            },
        )
        if not include_records:
            terms = node.style["bss_representative_terms"]
            if len(terms) == 1 and {key: terms[0][key] for key in _coordinates(monomial)} == _coordinates(monomial):
                del node.style["bss_representative_terms"]
        chart_nodes[identifier] = compact_model(node)
        return chart_nodes[identifier]

    for monomial in monomials:
        ensure_node(monomial)
    # Complete every differential incident to a requested node. This is a
    # finite one-step boundary completion, not a larger guessed algebra cap.
    incident_sources = set(monomials)
    for target in monomials:
        incident_sources.update(differential_preimages(target, page, sector))
    for monomial in sorted(incident_sources, key=lambda item: item.as_tuple()):
        target = engine.differential(monomial, page)
        if target is None:
            continue
        source_node, target_node = ensure_node(monomial, "incoming_source"), ensure_node(target)
        # These invariants are independent of the requested bounds and caps.
        if not engine.is_live(target, page):
            raise AssertionError("A nonzero Bockstein target must exist on the source page")
        if tuple(b-a for a, b in zip(monomial.tridegree, target.tridegree)) != (-1, 1, page):
            raise AssertionError("Invalid 2-BSS tridegree")
        differential_id = f"{source_node['id']}_d{page}"
        proposition_id = f"{differential_id}_claim"
        equation = rf"d_{{{page}}}\!\left({source_node['label']}\right)={target_node['label']}"
        locator = ("Bauer08, Section 7; Beaudry17b Section 4.1 for beta(v1)=eta; "
                   "current h0-adic indexing (DKLLW Table 1 is a comparison, not primary authority)"
                   if sector == "integer" else
                   "Published twisted-module differential, DKLLW24 "
                   f"Proposition {'3.6' if page == 1 else '3.8'}; "
                   "not independently attributed to Beaudry's untwisted algebra")
        proposition = Proposition(
            id=proposition_id, kind="differential", statement=equation, status="established",
            conclusion={"datum_type": "differential", "spectral_sequence": "2-bss", "page": page,
                        "source_id": source_node["id"], "target_id": target_node["id"],
                        "source_bockstein_filtration": monomial.h0,
                        "target_bockstein_filtration": target.h0,
                        "differential_degree": [-1, 1, page],
                        "target_in_window": target in visible,
                        "scope": "exact auxiliary 2-BSS additive page; not an HFPSS differential"},
            rule="2-BSS additive kernel/image computation",
            source_refs=[locator],
            convention_id=CONVENTION,
        )
        arrow = Differential(
            id=differential_id, source_id=source_node["id"], target_id=target_node["id"],
            page=page, status="established", proposition_id=proposition_id,
            unperiodic_reason="exact-2-bss-window",
        )
        chart_propositions.append(compact_model(proposition))
        chart_differentials.append(compact_model(arrow))
        outside_target_count += target not in visible
        if include_records:
            differential_records.append({
                "id": differential_id, "source": record_by_id[source_node["id"]],
                "target": record_by_id[target_node["id"]], "page": page,
                "source_id": source_node["id"], "target_id": target_node["id"],
                "target_in_window": target in visible, "target_excluded_by": excluded_by(target),
                "proposition_id": proposition_id,
            })

    # Multi-coordinate products get an exact named-vector endpoint (Sigma),
    # never a fan of falsely independent lines to individual summands.
    def combination_node(terms: tuple) -> dict:
        if len(terms) == 1:
            return ensure_node(terms[0])
        raw = bss_sigma._xor(term for item in terms for term in
                             ((item,) if sector == "integer" else bss_sigma.to_integer_basis(item)))
        common = {name: min(getattr(item, name) for item in raw) for name in ("h0", "v1", "k", "D")}
        summands = [integer_label_tex(replace(item, **{name: getattr(item, name)-value
                    for name, value in common.items()})) for item in raw]
        base = summands[0] if len(summands) == 1 else r"\{" + "+".join(summands) + r"\}"
        combined_label = (_power_tex("h_0", common["h0"]) + ("" if base == "1" else base)
                          + _power_tex("v_1", common["v1"]) + _power_tex("k", common["k"])
                          + _power_tex("D", common["D"]) + (r"u_{\sigma_i}" if sector == "sigma" else "")) or "1"
        identifier = "bss_combination_" + sha256(json.dumps(
            [sector, [item.as_tuple() for item in terms]], separators=(",", ":")).encode()).hexdigest()
        tower_key = "bss_combination_tower_" + sha256(json.dumps(
            [sector, [item.as_tuple()[:-1] for item in terms]], separators=(",", ":")).encode()).hexdigest()
        if identifier not in chart_nodes:
            grade = Grade(*terms[0].bidegree, dict(representation))
            node = ClassNode(id=identifier, label=combined_label, expression=combined_label,
                grade=grade, page=page, coefficient_context_id=CONTEXT, convention_id=CONVENTION,
                notes="Exact dependent vector in the displayed basis; not an additional basis generator.",
                style={"glyph": "dot", "last_page": page, "bss_combination": True,
                       "bss_in_window": False, "chart_occurrence_only": True,
                       "bockstein_filtration": terms[0].h0,
                       "bss_tower_key": tower_key, "source_reference": True,
                       "bss_combination_terms": [{"class_id": _identifier(sector, term), "coefficient": "1"}
                                                 for term in terms]})
            chart_nodes[identifier] = compact_model(node)
        return chart_nodes[identifier]

    relation_count = 0
    # Do not recursively extend the caps for multiplication. Include boundary
    # tower layers only where their true target is already materialized.
    relation_sources = tuple(record_by_id[node_id] for node_id in chart_nodes)
    for source_record in relation_sources:
        cls = bss_integer.BSSMonomial if sector == "integer" else bss_sigma.SigmaMonomial
        monomial = cls(**{key: source_record[key] for key in ("basis", "v1", "k", "D", "h0")})
        source_node = chart_nodes[source_record["id"]]
        for operator in chart_operators(page):
            terms = multiply(monomial, operator, page, sector)
            if not terms or any(_identifier(sector, term) not in chart_nodes for term in terms):
                continue
            target_node = combination_node(terms)
            equation = rf"{OPERATOR_TEX[operator]}\!\left({source_node['label']}\right)={target_node['label']}"
            identifier = f"{source_node['id']}_product_{operator.replace('^', '_')}_E{page}"
            chart_propositions.append(compact_model(Proposition(
                id=identifier, kind="relation", statement=equation, status="established",
                source_ref=PRODUCT_SOURCE, source_refs=[PRODUCT_SOURCE],
                rule="Beaudry/Henn E1 multiplication followed by current-page kernel/image reduction",
                conclusion={"source_id": source_node["id"], "target_id": target_node["id"],
                    "page": page, "spectral_sequence": "2-bss", "chart_occurrence_only": True,
                    "multiplier": OPERATOR_TEX[operator],
                    "degree": list(OPERATOR_MONOMIAL[operator].tridegree),
                    "source_bockstein_filtration": monomial.h0,
                    "target_bockstein_filtration": terms[0].h0,
                    "chart_connection": {"kind": "two" if operator == "h0" else operator,
                                         "multiplier": OPERATOR_TEX[operator]},
                    "target_coordinates": [{"class_id": _identifier(sector, term), "coefficient": "1"}
                                           for term in terms],
                    "scope": "associated-graded page product; no hidden extension"},
                convention_id=CONVENTION)))
            relation_count += 1

    coverage = (
        "Exact additive 2-BSS page restricted to the displayed bidegree window and explicit inclusive v1/h0 caps. "
        "Higher powers are omitted, not zero. Kernel/image membership is decided globally, including predecessors "
        "outside the window. Every differential incident to an in-window basis class includes visible boundary "
        "source/target context; boundary nodes are not included in the in-window count. "
        "Short lines are Beaudry/Henn page products; Sigma marks a dependent vector, not an extra basis class. "
        "This is neither the hidden-extension algebra nor an HFPSS page."
    )
    warnings = [
        "Different h0 layers can project to the same (stem, cohomological filtration); their engine IDs and h0 levels remain distinct.",
        "Boundary completion includes immediate differential predecessors/successors, not all powers or a complete finite subcomplex.",
        "h0,h1,h2 multiplication is shown, together with v1,x,y on E1, v1^2 on E2, and v1^4 thereafter. Normalized x,y have degree (-1,1); products to other excluded classes remain clipped.",
    ]
    if sector == "sigma":
        warnings.append("Sigma basis labels are actual adapted E1 vectors. The extra-v1 cap does not erase v1 powers already present inside a named sum.")
    boundary_count = sum(bool(node["style"].get("bss_boundary")) for node in chart_nodes.values())
    result = {
        "workspace_id": workspace_id, "sector": sector, "spectral_sequence": "2-bss", "page": page,
        "convention": "(stem, group-cohomology filtration, h0 filtration)",
        "convention_id": CONVENTION, "coefficient_context_id": CONTEXT,
        "differential_degree": [-1, 1, page], "window": window,
        "source_refs": [PRODUCT_SOURCE, *source_refs], "coverage": coverage, "warnings": warnings,
        "coverage_details": {
            "exact_additive_page": True, "global_fate": True, "full_cell_rank_claim": False,
            "complete_hidden_extension_algebra": False, "hfpss_permanence_claim": False,
            "displayed_class_count": len(monomials), "endpoint_only_class_count": 0,
            "boundary_class_count": boundary_count, "relation_count": relation_count,
            "combination_count": sum(bool(node["style"].get("bss_combination")) for node in chart_nodes.values()),
            "nonzero_outgoing_count": len(chart_differentials),
            "outside_target_count": outside_target_count,
            "caps_are_inclusive": True, "v1_cap_is_extra_exponent": sector == "sigma",
            "verified": ["Tridegree (-1,+1,+r)", "Both endpoints exist on Er",
                         "Global quotient fate independent of window bounds"],
        },
        "chart": {"classes": list(chart_nodes.values()), "differentials": chart_differentials,
                  "propositions": chart_propositions, "warnings": warnings},
    }
    if include_records:
        result.update(classes=records, differentials=differential_records)
    return result
