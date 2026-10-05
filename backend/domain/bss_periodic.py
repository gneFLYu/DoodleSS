"""Exact D-periodic views of the auxiliary Q8 2-Bockstein sequence.

Only D is inverted: its degree is (8,0,0) in (stem,s,h0). The k action
has degree (-4,4,0) and is used only for connected, nonzero page products.
In particular, a filtration-zero class can have zero k product. Neither
k nor h0 is a global invertible period. These are associated-graded BSS
pages, not the Q8 HFPSS or its hidden-extension algebra.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json

from . import bss_integer, bss_sigma
from .bss_chart import (_coordinates, _identifier, _power_tex, build_bss_window,
                        integer_label_tex)
from .bss_multiplication import multiply


BSS_PERIOD = {
    "generator": "D", "stem": 8, "filtration": 0, "h0_filtration": 0,
    "D_exponent": 1, "permanent": True, "domain": "integer",
    "page_min": 1, "page_max": 4,
    "source_ref": "Beaudry/Henn Appendix A.14, A.20-A.22 (invert Delta); "
                  "Q8 normalization Delta=D^3, DKLLW Lemma 3.1 and Section 3",
    "scope": "Invertible D action within each auxiliary 2-BSS sector; not an HFPSS period",
}
BSS_FORWARD_FAMILY = {
    "generator": "k", "stem": -4, "filtration": 4, "h0_filtration": 0,
    "domain": "nonnegative", "invertible": False, "page_min": 1, "page_max": 4,
    "source_ref": "Beaudry/Henn Appendix A.14(a); current-page kernel/image quotient",
    "scope": "Connected nonzero k products only; an absent predecessor or zero product stops the family",
}


def _hash(prefix, value):
    encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return prefix + sha256(encoded).hexdigest()


def _vector_identifier(sector, terms, *, tower=False):
    if len(terms) == 1:
        return _identifier(sector, terms[0], tower=tower)
    coordinates = [term.as_tuple()[:-1] if tower else term.as_tuple() for term in terms]
    prefix = "bss_combination_tower_" if tower else "bss_combination_"
    return _hash(prefix, [sector, coordinates])


def _shift(terms, exponent):
    return tuple(replace(term, D=term.D+exponent) for term in terms)


def _label(sector, terms):
    if len(terms) == 1:
        return integer_label_tex(terms[0]) if sector == "integer" else terms[0].label_tex
    raw = bss_sigma._xor(term for item in terms for term in
                         ((item,) if sector == "integer" else bss_sigma.to_integer_basis(item)))
    common = {name: min(getattr(term, name) for term in raw) for name in ("h0", "v1", "k", "D")}
    summands = [integer_label_tex(replace(term, **{name: getattr(term, name)-value
                for name, value in common.items()})) for term in raw]
    base = summands[0] if len(summands) == 1 else r"\{" + "+".join(summands) + r"\}"
    return (_power_tex("h_0", common["h0"]) + ("" if base == "1" else base)
            + _power_tex("v_1", common["v1"]) + _power_tex("k", common["k"])
            + _power_tex("D", common["D"])
            + (r"u_{\sigma_i}" if sector == "sigma" else "")) or "1"


def _family(sector, engine, terms, page):
    """Do not formally divide by k through a missing class or a zero map."""
    initial = terms
    while all(term.k > 0 for term in terms):
        previous = tuple(replace(term, k=term.k-1) for term in terms)
        if not all(engine.is_live(term, page) for term in previous):
            break
        image = bss_sigma._xor(result for term in previous for result in multiply(term, "k", page, sector))
        if image != terms:
            break
        terms = previous
    origin = _shift(terms, -(terms[0].bidegree[0] // 8))
    forward = bss_sigma._xor(result for term in initial for result in multiply(term, "k", page, sector))
    return {
        "bss_periodic_family_key": _hash("bss_family_", [sector, page, [term.as_tuple() for term in origin]]),
        "bss_family_k_min": min(term.k for term in terms),
        "bss_k_exponent": min(term.k for term in initial),
        "bss_k_predecessor_exists": terms != initial,
        "bss_k_forward_nonzero": bool(forward),
    }


def build_bss_periodic_window(sector: str, page: int = 1,
                              filtration_min: int = 0, filtration_max: int = 8,
                              v1_max: int = 8, h0_max: int = 3, *,
                              include_records: bool = False, limit: int = 10_000,
                              projection: str = "cohomology") -> dict:
    """Return the canonical 0..7 strip, with exact seam-crossing arrows.

    Input filtration bounds always mean group-cohomological s. Projection
    changes only chart coordinates: ``cohomology`` plots (stem,s), whereas
    ``bockstein`` plots (stem,h0). It does not reindex pages or forget s.
    IDs, full monomials, and the 2-BSS tridegree are projection-independent.

    Horizontal padding is only an implementation detail: short products
    range from x/y (-1 stem) to v1^4 (+8 stems). This completes every
    horizontal seam without increasing the stated v1/h0/s display caps.
    Incoming/outgoing differential boundary completion is inherited from
    the exact nonperiodic adapter, even when it exceeds those caps.
    """
    if projection not in ("cohomology", "bockstein"):
        raise ValueError("projection must be 'cohomology' or 'bockstein'")
    if not isinstance(include_records, bool):
        raise ValueError("include_records must be boolean")
    # Validate the public limit before scaling the private padded window.
    bss_integer._integer(limit, "limit", minimum=1)
    result = build_bss_window(sector, page=page, stem_min=-1, stem_max=15,
        filtration_min=filtration_min, filtration_max=filtration_max,
        v1_max=v1_max, h0_max=h0_max, include_records=False, limit=3*limit)
    sector = result["sector"]
    engine = bss_integer if sector == "integer" else bss_sigma
    cls = bss_integer.BSSMonomial if sector == "integer" else bss_sigma.SigmaMonomial
    chart = result["chart"]
    original = {node["id"]: node for node in chart["classes"]}
    original_terms = {}
    for identifier, node in original.items():
        if not node["style"].get("bss_combination"):
            original_terms[identifier] = (cls(**node["style"]["bss_monomial"]),)
    for identifier, node in original.items():
        if node["style"].get("bss_combination"):
            original_terms[identifier] = bss_sigma._xor(
                term for item in node["style"]["bss_combination_terms"]
                for term in original_terms[item["class_id"]])

    remap, powers, canonical, canonical_terms = {}, {}, {}, {}

    def in_window(term):
        return (filtration_min <= term.bidegree[1] <= filtration_max
                and term.v1 <= v1_max and term.h0 <= h0_max)

    def projected_grade(term):
        return {"stem": term.bidegree[0],
                "filtration": term.bidegree[1] if projection == "cohomology" else term.h0,
                "representation": {"sigma_i": -1} if sector == "sigma" else {}}

    for old_id, node in original.items():
        power = node["grade"]["stem"] // 8
        terms = _shift(original_terms[old_id], -power)
        identifier = _vector_identifier(sector, terms)
        remap[old_id], powers[old_id] = identifier, power
        if identifier in canonical:
            continue
        seed = deepcopy(node)
        seed.update(id=identifier, label=_label(sector, terms), expression=_label(sector, terms),
                    grade=projected_grade(terms[0]), period_stem=8, period_filtration=0)
        style = seed["style"]
        style.update(chart_occurrence_only=False, bss_period_generator="D",
                     bss_period_D_exponent=1, bss_projection=projection,
                     bss_cohomological_filtration=terms[0].bidegree[1],
                     bss_seed_tridegree=list(terms[0].tridegree),
                     bss_tower_key=_vector_identifier(sector, terms, tower=True))
        style.update(_family(sector, engine, terms, page))
        if style.get("bss_combination"):
            style["bss_combination_terms"] = [{"class_id": _identifier(sector, term), "coefficient": "1"}
                                              for term in terms]
            style["bss_combination_monomials"] = [_coordinates(term) for term in terms]
        else:
            style.update(bss_monomial=_coordinates(terms[0]), bss_engine_id=identifier,
                         bss_in_window=in_window(terms[0]))
            style["bss_excluded_by"] = [reason for reason in style["bss_excluded_by"] if reason != "stem_bounds"]
            if in_window(terms[0]):
                style["bss_boundary"] = ""
                seed["notes"] = f"Exact 2-BSS E{page}; h0 level {terms[0].h0}. D-periodic seed."
            if "bss_representative_terms" in style:
                # The compact source adapter supplies actual raw E1 coordinates.
                for item in style["bss_representative_terms"]:
                    item["D"] -= power
        canonical[identifier], canonical_terms[identifier] = seed, terms

    basis_count = sum(bool(node["style"].get("bss_in_window")) for node in canonical.values())
    if basis_count > limit:
        raise ValueError("2-BSS periodic window exceeds the requested materialization limit")

    claims, arrows = {}, {}
    for old_claim in chart["propositions"]:
        old_con = old_claim["conclusion"]
        old_source, old_target = old_con["source_id"], old_con["target_id"]
        source_id, target_id = remap[old_source], remap[old_target]
        # Translate the WHOLE equation to the source seed, not each side
        # separately: the target can lie in the adjacent physical strip.
        source_terms = canonical_terms[source_id]
        target_terms = _shift(original_terms[old_target], -powers[old_source])
        offset = powers[old_target] - powers[old_source]
        identifier = source_id + old_claim["id"][len(old_source):]
        if identifier in claims:
            continue
        claim = deepcopy(old_claim)
        con = claim["conclusion"]
        tridegree = con.get("differential_degree", con.get("degree"))
        projected_degree = [tridegree[0], tridegree[1 if projection == "cohomology" else 2]]
        con.update(source_id=source_id, target_id=target_id, chart_occurrence_only=False,
                   bss_target_period_offset=offset, period_stem=8, period_filtration=0,
                   tridegree=list(tridegree), projected_degree=projected_degree,
                   bss_seed_source_grade=projected_grade(source_terms[0]),
                   bss_seed_target_grade=projected_grade(target_terms[0]),
                   source_cohomological_filtration=source_terms[0].bidegree[1],
                   target_cohomological_filtration=target_terms[0].bidegree[1],
                   source_term=_coordinates(source_terms[0]),
                   target_terms=[_coordinates(term) for term in target_terms])
        if len(target_terms) == 1:
            con["target_term"] = _coordinates(target_terms[0])
        if "target_coordinates" in con:
            for item in con["target_coordinates"]:
                item["class_id"] = remap[item["class_id"]]
                item["bss_period_offset"] = offset
        target_label = _label(sector, target_terms)
        if claim["kind"] == "differential":
            operator = rf"d_{{{page}}}"
            con["target_in_window"] = in_window(target_terms[0])
        else:
            operator = con["multiplier"]
        claim.update(id=identifier,
                     statement=rf"{operator}\!\left({_label(sector, source_terms)}\right)={target_label}")
        claims[identifier] = claim

    for old_arrow in chart["differentials"]:
        source_id, target_id = remap[old_arrow["source_id"]], remap[old_arrow["target_id"]]
        identifier = f"{source_id}_d{page}"
        if identifier in arrows:
            continue
        arrow = deepcopy(old_arrow)
        arrow.update(id=identifier, source_id=source_id, target_id=target_id,
                     proposition_id=identifier+"_claim", period_stem=8,
                     period_filtration=0, unperiodic_reason="",
                     period_notes="Invertible D period; exact target seam offset is in the differential claim")
        arrows[identifier] = arrow

    warnings = [warning for warning in result["warnings"] if not warning.startswith("Different h0")]
    warnings += [
        "D is the only invertible display period. k-family highlighting follows nonzero page products and does not invert k.",
        "Projection changes only chart coordinates, never page numbering, the engine's tridegree, or the meaning of the cohomological s bounds.",
        ("Distinct h0 layers project to the same (stem,s) cell." if projection == "cohomology" else
         "Distinct group-cohomology s degrees can project to the same (stem,h0) cell; they remain separate basis vectors."),
    ]
    chart.update(classes=list(canonical.values()), differentials=list(arrows.values()),
                 propositions=list(claims.values()), periodicity=dict(BSS_PERIOD), warnings=warnings)
    result.update(mode="horizontal-periodic-seed-strip", projection=projection,
                  periodicity=dict(BSS_PERIOD), warnings=warnings,
                  projected_differential_degree=[-1, 1 if projection == "cohomology" else page])
    result["window"].update(stem_min=0, stem_max=7)
    result["coverage"] = (
        "Exact auxiliary 2-BSS additive page in one D-periodic 8-stem seed strip. "
        "D translates cover all integer stems; the stated group-cohomology s and inclusive extra-v1/h0 bounds "
        "limit only materialization. Higher powers are omitted, not zero. Horizontal differential and "
        "multiplication seams retain their exact endpoints; immediate differential boundaries beyond the "
        "caps remain visible. k products are not global isomorphisms. No full cell rank, hidden-extension "
        "algebra, or HFPSS permanence is asserted."
    )
    result["coverage_details"].update(
        displayed_class_count=basis_count,
        boundary_class_count=sum(bool(node["style"].get("bss_boundary")) for node in canonical.values()),
        relation_count=sum(claim["kind"] == "relation" for claim in claims.values()),
        combination_count=sum(bool(node["style"].get("bss_combination")) for node in canonical.values()),
        nonzero_outgoing_count=len(arrows),
        outside_target_count=sum(not claims[arrow["proposition_id"]]["conclusion"]["target_in_window"]
                                 for arrow in arrows.values()),
        periodic_family_transport={"horizontal": dict(BSS_PERIOD), "forward": dict(BSS_FORWARD_FAMILY)})
    if include_records:
        def record(terms, identifier):
            term = terms[0]
            return {"id": identifier, **_coordinates(term), "label": _label(sector, terms),
                    "label_tex": _label(sector, terms),
                    "grade": {**projected_grade(term), "filtration": term.bidegree[1]},
                    "cohomological_filtration": term.bidegree[1], "bockstein_filtration": term.h0,
                    "in_window": in_window(term)}

        result["classes"] = [record(canonical_terms[node["id"]], node["id"])
                             for node in canonical.values() if node["style"].get("bss_in_window")]
        result["differentials"] = []
        for arrow in arrows.values():
            con = claims[arrow["proposition_id"]]["conclusion"]
            source = record((cls(**con["source_term"]),), arrow["source_id"])
            target = record((cls(**con["target_term"]),), arrow["target_id"])
            result["differentials"].append({**arrow, "source": source, "target": target,
                "target_in_window": target["in_window"],
                "bss_target_period_offset": con["bss_target_period_offset"],
                "scope": "Exact source-seed equation; target ID aliases its D-periodic representative"})
    return result
