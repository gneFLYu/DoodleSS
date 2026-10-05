"""Exact j-adically completed auxiliary 2-BSS module charts.

Here j=v1^4 D^-1 has tridegree (0,0,0).  Beaudry/Henn A.14 gives four
v1-free families and ten v1-torsion families.  Splitting the free families
by v1 exponent modulo four gives free F4[[j]] modules; every torsion
family is killed by j.  The page predicates involve only parity, the
exceptions v1=0,2, and the cutoff v1>=4.  Consequently each surviving
residue family is an entire j-tail, a length-one j-torsion module, or zero.
This classification is symbolic, not an inference from a finite v1 cap.

The sigma d1-adapted basis is NOT a j-module basis: j*{h1+v1*x}=j*h1.
E1 therefore uses the raw Beaudry basis.  On E2 and later the free
residue-zero h1 generator is {h1+v1*x}; its positive j powers absorb the
ordinary h1 tail.  No extra independent generator is introduced for it.

Completion is flat for these finitely generated F4[j] pieces.  This
adapter changes their coefficient presentation, not the underlying
documented differentials.  It retains the auxiliary associated grading,
not hidden extensions or HFPSS permanence.  The user's j is not silently
identified with a paper's classical j: j^3=v1^12 Delta^-1, Delta=D^3;
the two adic filtrations have cofinal ideals.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from . import bss_integer as integer, bss_sigma as sigma
from .bss_chart import _coordinates, _SECTORS
from .bss_multiplication import (multiply, chart_operators,
                                 OPERATOR_TEX, OPERATOR_MONOMIAL, SOURCE_REF)
from .bss_periodic import BSS_PERIOD, BSS_FORWARD_FAMILY, _hash, _label, _family, _shift
from .bss_reference import CONTEXT, CONVENTION


J_COMPLETION = {
    "generator": "j", "expression_tex": r"j=v_1^4D^{-1}",
    "coefficient_ring": "F4[[j]]", "tridegree": [0, 0, 0],
    "permanent": True, "page_min": 1, "page_max": 4,
    "source_ref": "Beaudry/Henn A.14, A.20-A.22; exact auxiliary page quotients",
    "normalization": r"j^3=v_1^{12}\Delta^{-1},\quad\Delta=D^3",
    "scope": "Formal power series, not a finite v1 truncation or an inverted j action",
}
_A = "{h1+v1x}"
_B = "{h1^2+v1xh1}"


def _j_tex(power):
    return "1" if power == 0 else "j" if power == 1 else rf"j^{{{power}}}"


@dataclass(frozen=True, slots=True)
class CompletedModule:
    """A canonical 0..7-stem coefficient module, at fixed s and h0.

    ``D`` is the exponent before the j_min shift.  ``lift(0)`` is the
    actual displayed generator, already multiplied by j^j_min.  Positive
    powers are relative to that generator, never absolute valuations.
    """
    sector: str
    page: int
    basis: str
    residue: int
    k: int
    h0: int
    D: int
    kind: str
    j_min: int
    length: int | None
    raw: bool

    @property
    def id(self):
        return _hash("bss_j_", [self.sector, self.raw, self.basis, self.residue,
                               self.k, self.h0, self.D])

    @property
    def tridegree(self):
        return self.lift()[0].tridegree

    def lift(self, power=0):
        integer._integer(power, "j power", minimum=0)
        if self.length is not None and power >= self.length:
            return ()
        n = self.j_min + power
        v1 = self.residue + 4*n
        D = self.D-n
        if self.raw:
            raw = integer.BSSMonomial(self.basis, v1=v1, k=self.k, D=D, h0=self.h0)
            return (raw,) if self.sector == "integer" else sigma.from_integer_basis((raw,))
        basis = self.basis
        if basis == "h1" and self.residue == 0 and n == 0:
            basis = _A
        return (sigma.SigmaMonomial(basis, v1=v1, k=self.k, D=D, h0=self.h0),)

    def descriptor(self):
        return {"kind": self.kind, "j_min": self.j_min, "length": self.length,
                "coefficient_ring": "F4[[j]]", "annihilator": "0" if self.kind == "free" else "j",
                "representative_tex": _label(self.sector, self.lift()),
                "basis": self.basis, "v1_residue": self.residue,
                "D_before_j_min": self.D, "raw_basis": self.raw,
                "classification": "exact residue/parity and v1=0,2,>=4 page predicates"}


@lru_cache(maxsize=65536)
def completed_module(sector, page, basis, residue=0, k=0, h0=0):
    """Return a full symbolic coefficient module, or None if it is zero.

    Sigma E1 accepts raw integer basis names. Sigma E2+ accepts its
    adapted names, with {h1+v1x} canonically aliased to h1 residue zero.
    """
    if sector not in ("integer", "sigma"):
        raise ValueError("Unknown 2-BSS sector")
    integer._integer(page, "page", minimum=1)
    if page > 4:
        raise ValueError("Completed chart accepts E1 through E4")
    for name, value in (("residue", residue), ("k", k), ("h0", h0)):
        integer._integer(value, name, minimum=0)
    raw = sector == "integer" or page == 1
    if not raw and basis == _A:
        if residue:
            raise ValueError("The adapted sum has no separate v1 residue")
        basis = "h1"
    specs = integer.BASIS_GRADES if raw else sigma.BASIS_SPECS
    if basis not in specs:
        raise ValueError("Unknown module basis")
    free = basis in (integer.FREE_BASES if raw else sigma.FREE_BASES)
    maximum = (3 if free else 1 if basis in integer.V1_LENGTH_TWO_BASES else 0) if raw else (
        3 if free else sigma.BASIS_SPECS[basis].max_v1)
    if residue > maximum:
        raise ValueError("Residue exceeds this algebraic family")
    stem = specs[basis][0] if raw else specs[basis].stem
    D = -((stem+2*residue-4*k)//8)
    lower, upper = 0, None if free else 0
    if page >= 2 and free:
        if residue % 2:
            return None
        if basis == "1":
            if sector == "sigma" and residue == 0:
                lower = 1
            if sector == "integer" and page >= 3 and residue == 2:
                lower = 1
            if k > 0 and h0 > 0:
                upper = 0
            if sector == "integer" and page >= 4 and residue == 0 and k > 0 and h0 >= 3:
                lower = 1
            if sector == "sigma" and page >= 3 and residue == 2 and k > 0 and h0 >= 2:
                lower = 1
        elif h0 > 0:
            return None
    if upper is not None and lower > upper:
        return None
    module = CompletedModule(sector, page, basis, residue, k, h0, D,
                             "free" if upper is None else "torsion", lower,
                             None if upper is None else upper-lower+1, raw)
    engine = integer if sector == "integer" else sigma
    if not all(engine.is_live(term, page) for term in module.lift()):
        # Finite families use the same exact page predicate, not a v1 sample.
        if not free:
            return None
        raise AssertionError("Symbolic free-family classification disagrees with exact page")
    return module


def iter_modules(sector, page, filtration_min=0, filtration_max=8, h0_max=3):
    """Finite set of complete j modules in a D strip, with no v1 cap."""
    raw = sector == "integer" or page == 1
    specs = integer.BASIS_GRADES if raw else sigma.BASIS_SPECS
    for basis, spec in specs.items():
        if not raw and basis == _A:
            continue  # this is the free h1 residue-zero generator, not extra rank
        s = spec[1] if raw else spec.filtration
        free = basis in (integer.FREE_BASES if raw else sigma.FREE_BASES)
        max_r = (3 if free else 1 if basis in integer.V1_LENGTH_TWO_BASES else 0) if raw else (
            3 if free else spec.max_v1)
        for k in range(max(0, -((s-filtration_min)//4)), (filtration_max-s)//4+1):
            for residue in range(max_r+1):
                for h0 in range(h0_max+1):
                    module = completed_module(sector, page, basis, residue, k, h0)
                    if module is not None:
                        yield module


def resolve_vector(terms, sector, page):
    """Exact completed coordinates (module, relative j power, D translate).

    Coordinates of equal module, j power and translate cancel in F2.  The
    source formulas have F2 coefficients and extend F4[[j]]-linearly.
    """
    terms = sigma._xor(terms)
    if sector == "sigma" and page == 1:
        terms = sigma._xor(raw for term in terms for raw in sigma.to_integer_basis(term))
    result = set()
    for term in terms:
        basis = "h1" if sector == "sigma" and page >= 2 and term.basis == _A else term.basis
        raw = sector == "integer" or page == 1
        free = basis in (integer.FREE_BASES if raw else sigma.FREE_BASES)
        n, residue = divmod(term.v1, 4) if free else (0, term.v1)
        module = completed_module(sector, page, basis, residue, term.k, term.h0)
        if module is None or n < module.j_min or (module.length is not None and n >= module.j_min+module.length):
            raise ValueError("Vector contains a coordinate absent from the completed page")
        coordinate = (module, n-module.j_min, term.D+n-module.D)
        if coordinate in result:
            result.remove(coordinate)
        else:
            result.add(coordinate)
    return tuple(sorted(result, key=lambda item: (item[0].id, item[1], item[2])))


def expand_coordinates(coordinates):
    return sigma._xor(term for module, power, offset in coordinates
                      for term in _shift(module.lift(power), offset))


def _map(module, operator=None):
    engine = integer if module.sector == "integer" else sigma
    if operator is None:
        return sigma._xor(target for term in module.lift()
                          if (target := engine.differential(term, module.page)) is not None)
    return sigma._xor(target for term in module.lift()
                      for target in multiply(term, operator, module.page, module.sector))


def build_bss_completed_chart(sector, page=1, filtration_min=0, filtration_max=8,
                              h0_max=3, *, projection="cohomology",
                              include_records=False, limit=10_000):
    """Exact completed page in one D-periodic strip; s/h0 are display bounds."""
    if sector not in _SECTORS:
        raise ValueError("sector must be 'integer' or 'sigma'")
    sector = _SECTORS[sector]
    integer._integer(page, "page", minimum=1)
    if page > 4:
        raise ValueError("Completed chart accepts E1 through E4")
    for name, value in (("filtration_min", filtration_min), ("filtration_max", filtration_max),
                        ("h0_max", h0_max), ("limit", limit)):
        integer._integer(value, name, minimum=1 if name == "limit" else 0)
    if filtration_min > filtration_max:
        raise ValueError("Filtration bounds are reversed")
    if projection not in ("cohomology", "bockstein"):
        raise ValueError("Unknown projection")
    if not isinstance(include_records, bool):
        raise ValueError("include_records must be boolean")
    engine = integer if sector == "integer" else sigma
    representation = {"sigma_i": -1} if sector == "sigma" else {}
    visible = set(iter_modules(sector, page, filtration_min, filtration_max, h0_max))
    if len(visible) > limit:
        raise ValueError("Completed 2-BSS chart exceeds materialization limit")
    nodes, modules, claims, arrows = {}, {}, {}, {}

    def grade(term):
        return {"stem": term.bidegree[0], "filtration": term.bidegree[1] if projection == "cohomology" else term.h0,
                "representation": dict(representation)}

    def ensure(module, boundary="outgoing_target"):
        if module.id in nodes:
            return nodes[module.id]
        terms = module.lift()
        term = terms[0]
        label = _label(sector, terms)
        within = module in visible
        style = {"glyph": "j-series" if module.kind == "free" else "dot", "last_page": page,
                 "bss_j_module": module.descriptor(), "bss_j_completed": True,
                 "bss_engine": f"q8-2bss-{sector}-j-completed-v1", "bss_engine_id": module.id,
                 "bss_monomial": _coordinates(term),
                 "bss_representative_monomials": [_coordinates(item) for item in terms],
                 "bss_in_window": within, "bss_boundary": "" if within else boundary,
                 "bss_excluded_by": ([] if filtration_min <= term.bidegree[1] <= filtration_max else ["filtration_bounds"])
                    + ([] if term.h0 <= h0_max else ["h0_cap"]),
                 "window_endpoint_only": False, "chart_occurrence_only": False,
                 "bss_period_generator": "D", "bss_period_D_exponent": 1,
                 "bss_projection": projection, "bss_cohomological_filtration": term.bidegree[1],
                 "bss_seed_tridegree": list(term.tridegree), "bockstein_filtration": term.h0,
                 "bss_tower_key": _hash("bss_j_tower_", [sector, module.raw, module.basis, module.residue, module.k, module.D]),
                 "source_reference": True, "coefficient_order": 2,
                 "bss_exact_additive_basis": True}
        style.update(_family(sector, engine, terms, page))
        node = {"id": module.id, "label": label, "expression": label, "grade": grade(term),
                "page": page, "state": "unknown", "period_stem": 8, "period_filtration": 0,
                "coefficient_context_id": CONTEXT, "convention_id": CONVENTION, "style": style,
                "notes": "Exact completed auxiliary 2-BSS module; h0 is a separate associated grading."}
        nodes[module.id], modules[module.id] = node, module
        return node

    for module in sorted(visible, key=lambda item: item.id):
        ensure(module)
    # Every d_r raises s by exactly one and h0 by r. All possible incoming
    # sources outside this s window therefore lie in its single preceding
    # row, with h0 <= cap-r. Enumerate that finite set of complete modules
    # and inspect their WHOLE images. Inverting individual adapted columns
    # would miss raw sigma sources whose images involve cancelling basis
    # coordinates (for example d1(x*v1*u) and d1(y*u)). No v1 cap is needed.
    incident = set(visible)
    if filtration_min > 0 and h0_max >= page:
        for source in iter_modules(sector, page, filtration_min-1, filtration_min-1, h0_max-page):
            image = _map(source)
            if image and any(module in visible for module, _, _ in resolve_vector(image, sector, page)):
                incident.add(source)

    def target_node(coordinates, terms):
        for module, _, _ in coordinates:
            ensure(module)
        if len(coordinates) == 1:
            module, power, offset = coordinates[0]
            return nodes[module.id], offset, power
        offsets = {offset for _, _, offset in coordinates}
        if len(offsets) != 1:
            raise AssertionError("Homogeneous vector has inconsistent D strips")
        offset = next(iter(offsets))
        seed_terms = _shift(terms, -offset)
        identifier = _hash("bss_j_combination_", [(module.id, power) for module, power, _ in coordinates])
        if identifier not in nodes:
            label = _label(sector, seed_terms)
            nodes[identifier] = {"id": identifier, "label": label, "expression": label,
                "grade": grade(seed_terms[0]), "page": page, "period_stem": 8, "period_filtration": 0,
                "coefficient_context_id": CONTEXT, "convention_id": CONVENTION,
                "notes": "Dependent completed-module vector, not an additional module generator.",
                "style": {"glyph": "dot", "last_page": page, "bss_combination": True,
                    "bss_j_completed": True, "bss_in_window": False, "chart_occurrence_only": False,
                    "bss_period_generator": "D", "bss_period_D_exponent": 1,
                    "bss_seed_tridegree": list(seed_terms[0].tridegree),
                    "bss_cohomological_filtration": seed_terms[0].bidegree[1],
                    "bockstein_filtration": seed_terms[0].h0, "bss_projection": projection,
                    "bss_combination_terms": [{"class_id": module.id, "coefficient": _j_tex(power),
                        "j_power": power, "bss_period_offset": 0} for module, power, _ in coordinates],
                    "bss_combination_monomials": [_coordinates(term) for term in seed_terms]}}
        return nodes[identifier], offset, 0

    def add_map(source, terms, operator=None):
        if not terms:
            return
        coordinates = resolve_vector(terms, sector, page)
        if not coordinates:
            return
        source_node = ensure(source, "incoming_source")
        target, offset, power = target_node(coordinates, terms)
        differential = operator is None
        degree = [-1, 1, page] if differential else list(OPERATOR_MONOMIAL[operator].tridegree)
        actual_degree = [b-a for a, b in zip(source.tridegree, terms[0].tridegree)]
        if actual_degree != degree:
            raise AssertionError("Completed map changes the exact tridegree")
        identifier = source.id + (f"_d{page}" if differential else f"_product_{operator.replace('^','_')}_E{page}")
        claim_id = identifier+"_claim" if differential else identifier
        coefficient = _j_tex(power) if len(coordinates) == 1 else r"\Sigma"
        con = {"source_id": source.id, "target_id": target["id"], "page": page,
            "spectral_sequence": "2-bss", "chart_occurrence_only": False,
            "period_stem": 8, "period_filtration": 0, "bss_target_period_offset": offset,
            "bss_j_source_power": 0, "bss_j_target_power": power,
            "bss_j_coefficient_tex": coefficient,
            "bss_j_target_label_tex": _label(sector, terms),
            "target_coordinates": [{"class_id": module.id, "coefficient": _j_tex(p),
                                     "j_power": p, "bss_period_offset": off} for module, p, off in coordinates],
            "source_term": _coordinates(source.lift()[0]),
            "source_terms": [_coordinates(term) for term in source.lift()],
            "target_terms": [_coordinates(term) for term in terms],
            "bss_seed_source_grade": grade(source.lift()[0]), "bss_seed_target_grade": grade(terms[0]),
            "source_cohomological_filtration": source.tridegree[1],
            "target_cohomological_filtration": terms[0].bidegree[1],
            "source_bockstein_filtration": source.h0, "target_bockstein_filtration": terms[0].h0,
            "tridegree": degree, "projected_degree": [degree[0], degree[1 if projection == "cohomology" else 2]],
            "target_in_window": all(module in visible for module, _, _ in coordinates),
            "scope": "Exact F4[[j]]-linear associated-graded page map; no hidden extension"}
        if len(terms) == 1:
            con["target_term"] = _coordinates(terms[0])
        optex = rf"d_{{{page}}}" if differential else OPERATOR_TEX[operator]
        if differential:
            con.update(datum_type="differential", differential_degree=degree)
            arrows[identifier] = {"id": identifier, "source_id": source.id, "target_id": target["id"],
                "page": page, "status": "established", "proposition_id": claim_id,
                "period_stem": 8, "period_filtration": 0}
        else:
            con.update(degree=degree, multiplier=optex,
                chart_connection={"kind": "two" if operator == "h0" else operator, "multiplier": optex})
        claims[claim_id] = {"id": claim_id, "kind": "differential" if differential else "relation",
            "statement": rf"{optex}\!\left({source_node['label']}\right)={_label(sector, terms)}",
            "status": "established", "conclusion": con,
            "source_refs": list(engine.SOURCE_REFS) if differential else [SOURCE_REF],
            "rule": "Exact j-linear completion of the documented auxiliary page",
            "convention_id": CONVENTION}

    for source in sorted(incident, key=lambda item: item.id):
        terms = _map(source)
        # Incoming completion may find a source whose full vector has
        # several coordinates; retain the actual whole equation.
        if terms:
            add_map(source, terms)
    relation_sources = tuple(modules.values())
    for source in relation_sources:
        for operator in chart_operators(page):
            terms = _map(source, operator)
            if not terms:
                continue
            coordinates = resolve_vector(terms, sector, page)
            if all(module.id in nodes for module, _, _ in coordinates):
                add_map(source, terms, operator)
    warnings = ["Circle-dot denotes one free F4[[j]] module, not one F4 vector or a finite v1 sample.",
        "A dot denotes F4[[j]]/(j); j is not inverted. Edge j powers are relative to the displayed generator.",
        "h0 and group-cohomology s are distinct gradings; the projection does not identify their classes.",
        "Only D is an invertible chart period; connected nonzero k products stop at zero or absent predecessors.",
        "Immediate differential boundary context can exceed the requested s/h0 bounds; it adds no in-window rank."]
    if sector == "sigma":
        warnings.append("The sigma twist and d2 are published RO-graded results (DKLLW Propositions 3.6/3.8), not undetermined differentials or consequences of Beaudry/Henn's untwisted algebra alone.")
    result = {"workspace_id": f"ws_q8_bss_{sector}", "sector": sector, "page": page,
        "spectral_sequence": "2-bss", "mode": "j-completed-periodic-seed-strip", "projection": projection,
        "coefficient_context_id": CONTEXT, "convention_id": CONVENTION,
        "convention": "(stem, group-cohomology filtration, h0 filtration)",
        "differential_degree": [-1, 1, page], "projected_differential_degree": [-1, 1 if projection == "cohomology" else page],
        "window": {"page": page, "stem_min": 0, "stem_max": 7,
                   "filtration_min": filtration_min, "filtration_max": filtration_max, "h0_max": h0_max},
        "periodicity": dict(BSS_PERIOD), "j_completion": dict(J_COMPLETION),
        "source_refs": [SOURCE_REF, *engine.SOURCE_REFS], "warnings": warnings,
        "coverage": "Exact j-adically completed auxiliary 2-BSS modules in a D-periodic strip. All nonnegative j powers are represented symbolically, without a v1 cap. Only s/h0 materialization is bounded. No hidden-extension algebra or HFPSS permanence is asserted.",
        "coverage_details": {"exact_additive_page": True, "global_fate": True,
            "j_adically_complete": True, "v1_truncated": False, "full_cell_rank_claim": False,
            "complete_hidden_extension_algebra": False, "hfpss_permanence_claim": False,
            "displayed_class_count": len(visible), "module_generator_count": len(visible),
            "free_module_count": sum(module.kind == "free" for module in visible),
            "torsion_module_count": sum(module.kind == "torsion" for module in visible),
            "boundary_class_count": len(modules)-len(visible),
            "combination_count": len(nodes)-len(modules),
            "relation_count": sum(item["kind"] == "relation" for item in claims.values()),
            "nonzero_outgoing_count": len(arrows),
            "periodic_family_transport": {"horizontal": dict(BSS_PERIOD), "forward": dict(BSS_FORWARD_FAMILY)}},
        "chart": {"classes": list(nodes.values()), "differentials": list(arrows.values()),
                  "propositions": list(claims.values()), "periodicity": dict(BSS_PERIOD),
                  "j_completion": dict(J_COMPLETION), "warnings": warnings}}
    if include_records:
        result["classes"] = [nodes[module.id] for module in sorted(visible, key=lambda item: item.id)]
        result["differentials"] = list(arrows.values())
    return result
