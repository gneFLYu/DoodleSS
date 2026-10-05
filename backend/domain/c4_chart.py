"""Finite views of completed C4 coefficient modules, never fictitious F4 ranks."""
from __future__ import annotations

from dataclasses import asdict
from copy import deepcopy
from functools import lru_cache

from . import c4_integer
from .c4_reference import CONTEXT, CONVENTION


C4_PERIOD = {
    "generator": r"\Delta_1^4", "stem": 32, "filtration": 0,
    "delta_exponent": 4, "permanent": True, "domain": "integer",
    "page_min": 2, "page_max": 14,
    "source_ref": "BBHS20, Remark 5.2 and Props. 5.21, 5.24, 5.27-5.28",
    "scope": "Within each independently computed C4 slice; no vertical period is asserted",
}
C4_FORWARD_FAMILY = {
    "generator": r"\bar\kappa=\varpi^2\Delta_1", "stem": 20, "filtration": 4,
    "domain": "nonnegative", "invertible": False, "page_min": 2, "page_max": 14,
    "source_ref": "BBHS20, Remark 5.22; Props. 5.21, 5.24, 5.27-5.28",
    "scope": "Connected nonzero products on the selected page, not a vertical period isomorphism",
}


def _engine(sector):
    if sector == "integer":
        return c4_integer
    if sector == "1-minus-sigma":
        from . import c4_shifted
        return c4_shifted
    raise ValueError("Choose the integer or 1-minus-sigma C4 slice")


def _kappa_predecessor(term, engine):
    """The unique possible monomial predecessor, before checking its page.

    The filtration-zero exceptions use the actual E2 ring:
    kappa-bar*1 = varpi^2*Delta and kappa-bar*T2 = eta^2*varpi*Delta^2.
    Dividing coordinates alone would miss both identifications.
    """
    family, q, d = term.family, term.q, term.d
    if family == "varpi" and q == 2:
        family, q, d = "one", 0, d-1
    elif family == "eta2" and q == 1:
        family, q, d = "T2", 0, d-2
    elif q >= 2:
        q, d = q-2, d-1
    else:
        return None
    return engine.Term(family, q, d, term.mu, term.two)


def _kappa_product(term, engine):
    factors = {"varpi": term.q+2, "delta": term.d+1, "mu": term.mu, "two": term.two}
    if term.family not in ("one", "varpi"):
        name, exponent = {"T2": ("t2", 1), "eta2": ("eta", 2)}.get(term.family, (term.family, 1))
        factors[name] = exponent
    return engine.normalize_monomial(**factors)


@lru_cache(maxsize=100_000)
def c4_orbit_key(family, q, d, page=2, mu=0, two=0, sector="integer"):
    """Key an exact coefficient representative, not a whole Witt glyph.

    Equivalence means horizontal Delta_1^4 translates and connected nonzero
    forward kappa-bar products. A nonexisting predecessor stops reduction;
    it is never resurrected by formally inverting kappa-bar. Mu exponents,
    absolute 2-valuations, the page, and the two RO slices remain distinct.
    None means this precise representative does not exist on the page.
    """
    engine = _engine(sector)
    term = engine.Term(family, q, d, mu, two)
    if not engine.is_live(term, page):
        return None
    while (previous := _kappa_predecessor(term, engine)) is not None:
        if not engine.is_live(previous, page) or _kappa_product(previous, engine) != term:
            break
        term = previous
    return f"c4:{sector}:E{page}:{term.family}:q{term.q}:d{term.d % 4}:mu{mu}:two{two}"


def _coefficient_family_keys(cell, branch, sector, page):
    # Match the existing finite-tower ports and the three visible levels of
    # an unbounded Witt tower. This is not a finite-rank assertion.
    upper = branch["two_max"]
    if upper is None:
        upper = branch["two_min"]+2
    return {f"{two}:0": c4_orbit_key(cell["family"], cell["q"], cell["d"], page,
                                    branch["mu_min"], two, sector)
            for two in range(branch["two_min"], upper+1)}


def build_c4_window(sector="integer", *, page=2, stem_min=-8, stem_max=40,
                    filtration_min=0, filtration_max=20, include_records=True):
    engine = _engine(sector)
    window = dict(page=page, stem_min=stem_min, stem_max=stem_max,
                  filtration_min=filtration_min, filtration_max=filtration_max)
    cells = list(engine.cells_in_window(**window))
    by_cell = {(cell["family"], cell["q"], cell["d"]): cell for cell in cells}
    visible = set(by_cell)
    nodes, arrows, claims, records, relation_records = {}, [], [], [], []
    representation = {"1": 1, "sigma": -1} if sector != "integer" else {}

    def get_cell(term):
        key = (term["family"], term["q"], term["d"])
        if key not in by_cell:
            by_cell[key] = engine.module_descriptor(*key, page)
        return by_cell[key]

    def node_for(cell, branch):
        identifier = f"c4_{sector}_{cell['family']}_q{cell['q']}_d{cell['d']}_mu{branch['mu_min']}"
        if identifier not in nodes:
            endpoint_only = (cell["family"], cell["q"], cell["d"]) not in visible
            nodes[identifier] = {
                "id": identifier, "label": branch["representative_tex"],
                "expression": branch["representative_tex"],
                "grade": {"stem": cell["stem"], "filtration": cell["filtration"],
                          "representation": dict(representation)},
                "page": page, "state": "unknown", "period_stem": 0, "period_filtration": 0,
                "coefficient_context_id": CONTEXT, "convention_id": CONVENTION,
                "notes": ("A completed coefficient branch, not an independent F4 basis vector. "
                          "The label is its lowest surviving representative. "
                          "Constant and positive-mu branches retain their common W(k)[[mu]] module structure."),
                "style": {
                    "glyph": "square" if branch["two_max"] is None else "dot",
                    "last_page": page, "window_endpoint_only": endpoint_only,
                    "c4_coefficient_branch": branch,
                    "c4_module_key": [cell["family"], cell["q"], cell["d"]],
                    "c4_periodic_family_keys": _coefficient_family_keys(cell, branch, sector, page),
                    "c4_periodic_family_mu_exponent": branch["mu_min"],
                    "c4_scalar_ports_are_not_module_basis": True,
                    "c4_two_tower": {
                        "two_min": branch["two_min"], "two_max": branch["two_max"],
                        "unbounded": branch["two_max"] is None, "multiplier": "2",
                        "semantics": "successive coefficient multiples, not independent residue-field basis vectors",
                    },
                    "reference_coefficient_module": branch["coefficient_description"]
                        + (" with completed positive-mu tail" if branch["completed_mu_tail"] else " constant branch"),
                    "source_ref": engine.SOURCE,
                },
            }
        return nodes[identifier]

    def endpoint(term):
        cell = get_cell(term)
        for branch in cell["branches"]:
            if (branch["mu_min"] <= term["mu"]
                    and (branch["mu_max"] is None or term["mu"] <= branch["mu_max"])
                    and branch["two_min"] <= term["two"]
                    and (branch["two_max"] is None or term["two"] <= branch["two_max"])):
                return node_for(cell, branch), branch
        raise ArithmeticError("C4 arrow endpoint has no surviving coefficient branch")

    for cell in cells:
        for branch in cell["branches"]:
            node_for(cell, branch)
    for cell in cells:
        components = engine.differential_components(cell["family"], cell["q"], cell["d"], page)
        for component in components:
            source, source_branch = endpoint(component["source"])
            target, target_branch = endpoint(component["target"])
            if (target["grade"]["stem"] - source["grade"]["stem"],
                    target["grade"]["filtration"] - source["grade"]["filtration"]) != (-1, page):
                raise ArithmeticError("C4 differential has incorrect bidegree")
            identifier = f"{source['id']}_d{page}"
            mu_power = component["target"]["mu"] - target_branch["mu_min"]
            # Powers of 2 select actual finite coefficient ports. Only the
            # residual mu multiplication is an edge label in that drawing.
            coefficient_tex = "1" if not mu_power else r"\mu" if mu_power == 1 else rf"\mu^{{{mu_power}}}"
            equation = rf"d_{{{page}}}({component['source_tex']})={component['target_tex']}"
            claim = {
                "id": identifier + "_claim", "kind": "differential", "status": "established",
                "statement": equation, "source_ref": engine.SOURCE, "source_refs": [engine.SOURCE],
                "rule": "BBHS equations, module linearity, and global coefficient ideal quotient",
                "convention_id": CONVENTION,
                "conclusion": {
                    "source_id": source["id"], "target_id": target["id"], "page": page,
                    "proof_category": "module structure / source differential",
                    "c4_source_two": component["source"]["two"],
                    "c4_target_two": component["target"]["two"],
                    "c4_source_mu": component["source"]["mu"],
                    "c4_target_mu": component["target"]["mu"],
                    "source_term": component["source"], "target_term": component["target"],
                    "coefficient_map": component["coefficient_map"],
                    "scope": "completed coefficient branch map, not a finite F4 linear map",
                },
            }
            arrow = {
                "id": identifier, "source_id": source["id"], "target_id": target["id"],
                "page": page, "status": "established", "proposition_id": claim["id"],
                "period_stem": 0, "period_filtration": 0,
                "unperiodic_reason": "explicit-completed-C4-window",
                "display_coefficient": {"kind": "c4-coefficient", "resolved": True,
                                        "latex": coefficient_tex, "mu_exponent": mu_power},
            }
            arrows.append(arrow)
            claims.append(claim)
            if include_records:
                records.append({**component, "target_in_window": not target["style"]["window_endpoint_only"]})

    # Coefficient ports are not additional independent module generators.
    # Nonetheless eta/nu and multiplication by 2 must land on the actual
    # coefficient representative rather than the centre of its glyph.
    for cell in cells:
        for branch in cell["branches"]:
            lower, upper = branch["two_min"], branch["two_max"]
            # An unbounded Witt branch gets a symbolic 2-tower map; do not
            # pretend that a finite sampled list exhausts its coefficients.
            valuations = range(lower, upper + 1) if upper is not None else (lower,)
            for valuation in valuations:
                term = engine.Term(cell["family"], cell["q"], cell["d"], branch["mu_min"], valuation)
                for multiplier in ("eta", "nu", "2"):
                    product = engine.multiply(term, multiplier, page)
                    if product is None:
                        continue
                    source, source_branch = endpoint(asdict(term))
                    target, target_branch = endpoint(asdict(product))
                    expected = {"eta": (1, 1), "nu": (3, 1), "2": (0, 0)}[multiplier]
                    degree = (target["grade"]["stem"] - source["grade"]["stem"],
                              target["grade"]["filtration"] - source["grade"]["filtration"])
                    if degree != expected:
                        raise ArithmeticError("C4 multiplication relation has incorrect bidegree")
                    mu_power = product.mu - target_branch["mu_min"]
                    coefficient_tex = "1" if not mu_power else r"\mu" if mu_power == 1 else rf"\mu^{{{mu_power}}}"
                    multiplier_tex = {"eta": r"\eta", "nu": r"\nu", "2": "2"}[multiplier]
                    identifier = f"{source['id']}_{multiplier}_two{valuation}"
                    symbolic_tower = multiplier == "2" and upper is None
                    conclusion = {
                        "source_id": source["id"], "target_id": target["id"], "page": page,
                        "last_page": page, "source_term": asdict(term), "target_term": asdict(product),
                        "c4_source_two": term.two, "c4_target_two": product.two,
                        "c4_source_mu": term.mu, "c4_target_mu": product.mu,
                        "c4_unbounded_two_tower": symbolic_tower,
                        "c4_completed_mu_tail": branch["completed_mu_tail"],
                        "c4_multiplier": multiplier,
                        "chart_connection": {"kind": "two" if multiplier == "2" else multiplier,
                                             "multiplier": multiplier_tex},
                        "display_coefficient": {"kind": "c4-coefficient", "resolved": True,
                                                "latex": coefficient_tex, "mu_exponent": mu_power},
                        "scope": "associated-graded multiplication only; not a hidden extension",
                    }
                    claims.append({
                        "id": identifier, "kind": "relation", "status": "established",
                        "statement": rf"{multiplier_tex}\cdot\{{{term.tex()}\}}={product.tex()}",
                        "conclusion": conclusion,
                        "rule": "BBHS E2 multiplication followed by the exact current-page coefficient quotient",
                        "source_ref": engine.SOURCE, "source_refs": [engine.SOURCE],
                        "convention_id": CONVENTION,
                    })
                    if include_records:
                        relation_records.append({
                            "id": identifier, "multiplier": multiplier, "page": page,
                            "source": asdict(term), "target": asdict(product),
                            "source_tex": term.tex(), "target_tex": product.tex(),
                            "unbounded_two_tower": symbolic_tower,
                            "completed_mu_tail": branch["completed_mu_tail"],
                            "target_in_window": not target["style"]["window_endpoint_only"],
                        })
    result = {
        "sector": sector, "spectral_sequence": "hfpss", "group": "C4", "window": window,
        "source_refs": [engine.SOURCE], "differential_degree": [-1, page],
        "periodicity": dict(C4_PERIOD),
        "coverage": ("Exact C4/C4 associated-graded page in the stated bidegree window. "
                     "Completed coefficient branches and all their powers are retained symbolically; "
                     "kernel/image membership includes arrows outside the window. "
                     "This does not compute hidden extensions or the full Mackey functor."),
        "warnings": [
            "Constant and positive-mu glyphs describe coefficient branches, not an F4 basis or independent W(k)[[mu]] generators.",
            "An arrow into a finite coefficient tower selects its actual power-of-two port; mu on an arrow is a coefficient-ring factor, not an F4 unit.",
            "Square glyphs stand for unbounded Witt branches; no finite list of their doubles is asserted complete.",
        ],
        "chart": {"classes": list(nodes.values()), "differentials": arrows, "propositions": claims,
                  "periodic_family_transport": {"horizontal": dict(C4_PERIOD),
                                                "forward": dict(C4_FORWARD_FAMILY),
                                                "coefficient_scope": "Exact mu exponent and absolute 2 valuation; positive-mu glyphs use their lowest symbolic-tail representative"}},
    }
    if include_records:
        result.update(cells=cells, differentials=records, relations=relation_records)
    return result


def build_c4_periodic_chart(sector="integer", *, page=2, filtration_min=0,
                            filtration_max=20, include_records=False):
    """One 0..31 seed strip with exact seam offsets and lazy filtration.

    Nodes are canonicalized by the permanent Delta_1^4 unit only. A target
    on the other side of the strip retains its physical displacement in
    c4_target_period_offset, measured relative to its source copy. No
    varpi/kappa/epsilon multiplication is treated as an invertible period.
    """
    engine = _engine(sector)
    result = build_c4_window(sector, page=page, stem_min=0, stem_max=31,
                             filtration_min=filtration_min, filtration_max=filtration_max,
                             include_records=include_records)
    chart = result["chart"]
    original = {node["id"]: node for node in chart["classes"]}
    remap, exponents, canonical = {}, {}, {}
    for node in chart["classes"]:
        power = node["grade"]["stem"] // 32
        family, q, d = node["style"]["c4_module_key"]
        canonical_d = d - 4 * power
        branch = node["style"]["c4_coefficient_branch"]
        identifier = f"c4_{sector}_{family}_q{q}_d{canonical_d}_mu{branch['mu_min']}"
        remap[node["id"]], exponents[node["id"]] = identifier, power
        if identifier in canonical:
            if not node["style"]["window_endpoint_only"]:
                canonical[identifier]["style"]["window_endpoint_only"] = False
            continue
        seed = deepcopy(node)
        seed["id"] = identifier
        seed["grade"]["stem"] -= 32 * power
        seed["period_stem"] = 32
        seed["style"]["c4_module_key"][2] = canonical_d
        canonical_branch = seed["style"]["c4_coefficient_branch"]
        canonical_branch["representative"]["d"] = canonical_d
        term = engine.Term(**canonical_branch["representative"])
        canonical_branch["representative_tex"] = term.tex()
        seed["label"] = seed["expression"] = term.tex()
        seed["style"]["c4_period_delta_exponent"] = 4
        seed["style"]["c4_period_generator"] = r"\Delta_1^4"
        canonical[identifier] = seed

    for claim in chart["propositions"]:
        conclusion = claim["conclusion"]
        source_id, target_id = conclusion["source_id"], conclusion["target_id"]
        conclusion["source_id"], conclusion["target_id"] = remap[source_id], remap[target_id]
        conclusion["c4_target_period_offset"] = exponents[target_id] - exponents[source_id]
        conclusion["period_stem"] = 32
        conclusion["period_filtration"] = 0
        # These are the exact physical grades of the seed equation, useful
        # for audit/export. The rendered target copy adds the seam offset.
        conclusion["c4_seed_source_grade"] = original[source_id]["grade"]
        conclusion["c4_seed_target_grade"] = original[target_id]["grade"]
    for arrow in chart["differentials"]:
        arrow["source_id"], arrow["target_id"] = remap[arrow["source_id"]], remap[arrow["target_id"]]
        arrow["period_stem"] = 32
        arrow["unperiodic_reason"] = ""
        arrow["period_notes"] = "Permanent Delta_1^4 period; target seam offset is in the differential claim"
    chart["classes"] = list(canonical.values())
    chart["periodicity"] = dict(C4_PERIOD)
    result["periodicity"] = dict(C4_PERIOD)
    result["mode"] = "horizontal-periodic-seed-strip"
    result["coverage"] = (
        "Exact C4/C4 associated-graded page, represented by one 32-stem seed strip. "
        "Permanent Delta_1^4 translates cover all integer stems; filtration is loaded lazily. "
        "Coefficient ideals, eta/nu/2 products and seam-crossing endpoints are exact. "
        "No vertical period, hidden extensions, or full Mackey functor is asserted."
    )
    return result
