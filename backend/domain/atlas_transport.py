"""All-page atlas transport in explicitly transported bases.

The five computed sectors cover the sixteen tiles under omega, semilinear
psi, and the declared Picard periods. Thom isomorphism by itself only gives
an E2 pattern; this module transports the entire filtered chart instead.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import re

from .actions import (apply_s3_representation, expanded_action_basis, frobenius_scalar,
                      normalized_scalar_ratio)
from .grading import EXISTING_WORKSPACE_BY_SECTOR, normalize_to_q8_sector
from .models import Project
from .periods import migrate_legacy_period_families


SOURCE_REPRESENTATIONS = {
    workspace_id: {key: value for key, value in {"sigma_i": -a, "sigma_j": -b}.items() if value}
    for (a, b), workspace_id in EXISTING_WORKSPACE_BY_SECTOR.items()
}


def q8_atlas_transport_plan(project: Project) -> dict[str, dict]:
    """Find all six S3 images, retaining each integer/Picard shift.

    The action is omega^power psi^reflected. Reduced chart stems obey
    (a,b,c;s) -> (a-c mod4,b-c mod4;s-16c). In particular S11 comes
    from 3sigma_k at +16, and S33 comes from sigma_k at -16.
    """
    plans: dict[str, dict] = {}
    for source_id, representation in SOURCE_REPRESENTATIONS.items():
        for reflected in (False, True):
            for power in range(3):
                raw = apply_s3_representation(representation, power, reflected)
                reduction = normalize_to_q8_sector(project, raw)
                if reduction.sector_id is None:
                    continue
                stem_shift = (reduction.stem_shift + 32) % 64 - 32
                plan = {
                    "source_workspace_id": source_id,
                    "source_representation": representation,
                    "raw_representation": raw,
                    "sector_id": reduction.sector_id,
                    "omega_power": power,
                    "reflected": reflected,
                    "action": (f"omega^{power}" if power else "identity") + (" psi" if reflected else ""),
                    "stem_shift": stem_shift,
                    "unreduced_stem_shift": reduction.stem_shift,
                    "d8_adjustment": (stem_shift - reduction.stem_shift) // 64,
                    "normalization": asdict(reduction),
                    "coefficient_action": "Frobenius" if reflected else "F4-linear",
                    "basis_convention": "Runtime uses transported source coordinates; labels use explicit expanded, path-induced Thom bases with separate scalar conversion.",
                    "source_refs": [
                        "DKLLW24 Corollaries 2.22-2.23 and Proposition 4.1",
                        "formal_notes.tex H-page remark, lines 1016-1022",
                        "Note/record/coefficientpuzzle.tex, psi representation action and Frobenius",
                    ],
                }
                old = plans.get(reduction.sector_id)
                # Prefer a published Picard path to the exceptional declared
                # period and prefer a cyclic map to a semilinear one.
                score = (reduction.status != "exact", reflected, power)
                if old is None or score < old["_score"]:
                    plan["_score"] = score
                    plans[reduction.sector_id] = plan
    for plan in plans.values():
        plan.pop("_score")
    return plans


def _replace_references(value, ids):
    if isinstance(value, str):
        return ids.get(value, value)
    if isinstance(value, list):
        return [_replace_references(item, ids) for item in value]
    if isinstance(value, dict):
        return {key: _replace_references(item, ids) for key, item in value.items()}
    return value


def _transport_coefficient_parameter(parameter: dict, reflected: bool) -> dict:
    """Conjugate a parameter reference, never its shared source assignment.

    The parameter id denotes one scalar across every atlas image. A reflected
    occurrence evaluates that scalar after Frobenius; creating a new id or
    squaring its stored value would lose that dependency or conjugate twice.
    Witt levels and all other metadata remain outside this operation.
    """
    image = deepcopy(parameter)
    power = image.get("frobenius_power")
    if type(power) is not int or power not in (0, 1):
        raise ValueError("Coefficient parameter frobenius_power must be 0 or 1.")
    if reflected:
        image["frobenius_power"] = 1 - power
    return image


def _thom_label(representation: dict) -> str:
    terms = []
    for axis in ("i", "j", "k"):
        exponent = -representation.get("sigma_" + axis, 0)
        if exponent:
            terms.append((str(exponent) if exponent != 1 else "") + r"\sigma_" + axis)
    return "u_{" + "+".join(terms) + "}" if terms else "1"


def _picard_display_basis(plan: dict, representation: dict) -> dict:
    """Name the chosen target basis without inventing an external Thom unit."""
    multiplicities = plan["normalization"]["relation_multiplicities"]
    factors = [
        (r"N_{C_4}^{Q_8}(\bar d)", -multiplicities.get("q8-rel-norm-h", 0)),
        (r"(g^{-1}a_{\mathbb H})", multiplicities.get("q8-rel-twenty-h", 0)),
        (r"u_{4\sigma_i}", multiplicities.get("q8-rel-four-sigma-i", 0)),
        (r"u_{4\sigma_j}", multiplicities.get("q8-rel-four-sigma-j", 0)),
        ("D", 8 * plan["d8_adjustment"]),
    ]
    factors = [(label, power) for label, power in factors if power]
    multiplier = "".join(label if power == 1 else "(" + label + ")^{" + str(power) + "}"
                         for label, power in factors) or "1"
    return {
        "target_thom": _thom_label(representation), "picard_multiplier": multiplier,
        "picard_factors": [{"expression": label, "exponent": power} for label, power in factors],
        "definition": "u_target^(path) := D^(-stem_shift/8) * Picard_multiplier * action(u_source)",
        "display_D_exponent": plan["stem_shift"] // 8,
        "external_thom_unit": None,
        "external_thom_normalization": "not asserted; target Thom notation denotes this explicitly chosen path-induced basis",
        "status": plan["normalization"]["status"],
        "obligations": deepcopy(plan["normalization"]["obligations"]),
        "source_refs": deepcopy(plan["source_refs"]),
        "D_shift_is_permanent_period": False,
    }


_NO_COEFFICIENT_CONDITION = object()


def atlas_display_coefficient(source_basis: dict, target_basis: dict,
                              parameter: dict | None = None, *,
                              coefficient_condition=_NO_COEFFICIENT_CONDITION,
                              matrix_endpoint: bool = False) -> dict:
    """Display c'=sigma(c)*beta/alpha without changing the runtime basis.

    A linked or unspecified parameter remains symbolic. The parameter's
    existing Frobenius flag is evaluated once; no atlas reflection is applied
    a second time here. A vector-component parameter is not a scalar map.
    Conditions and effective matrix endpoints need the actual runtime's
    shared parameter registry and vector image, not just two label units.
    """
    source_unit, target_unit = source_basis.get("unit"), target_basis.get("unit")
    ratio = normalized_scalar_ratio(source_unit, target_unit)
    result = {
        "basis": "unscaled expanded endpoint generators",
        "runtime_basis": "transported source basis (unchanged)",
        "formula": "normalized = transported_coefficient * target_unit / source_unit",
        "source_unit": source_unit, "target_unit": target_unit, "basis_ratio": ratio,
        "transported_parameter": deepcopy(parameter),
        "transported_value": None, "value": None, "resolved": False,
        "requires_runtime": True,
        "frobenius_applied_to_parameter_once": True,
    }
    if coefficient_condition is not _NO_COEFFICIENT_CONDITION:
        # Even an explicit null is an invalid condition in the runtime, not
        # absence of a condition. Preserve it for inspection and validation.
        result["coefficient_condition"] = deepcopy(coefficient_condition)
    if matrix_endpoint:
        result["basis_ratio"] = None
        result["endpoint_basis_status"] = "requires-effective-matrix-image"
        result["reason"] = "Stored labels do not certify the effective matrix endpoints; resolve the vector image and full basis transform first."
        return result
    if coefficient_condition is not _NO_COEFFICIENT_CONDITION:
        result["reason"] = "Evaluate the coefficient condition in the shared runtime registry before recording a scalar or zero map."
        return result
    if ratio is None:
        result["reason"] = "An endpoint expansion has no certified scalar normalization."
        return result
    if parameter is not None and (not isinstance(parameter, dict)
                                  or not isinstance(parameter.get("id"), str) or not parameter["id"]):
        result["reason"] = "The coefficient parameter has no valid stable identity."
        return result
    if parameter and any(key in parameter for key in ("target_component", "source_parameter", "inverse_parameter_id")):
        result["reason"] = "Resolve the linked, quotient or vector-component parameter in the runtime; do not treat it as a fixed scalar."
        return result
    value = parameter.get("value") if parameter is not None else 1
    if type(value) is not int or value not in (0, 1, 2, 3):
        result["reason"] = "The source parameter is unresolved; basis_ratio alone does not fix the differential."
        return result
    if parameter and isinstance(parameter.get("domain"), list) and value not in parameter["domain"]:
        result["reason"] = "The fixed coefficient is outside its declared domain."
        return result
    offset = parameter.get("affine_offset", 0) if parameter else 0
    if type(offset) is not int or offset not in (0, 1, 2, 3):
        result["reason"] = "Invalid affine residue-field coefficient."
        return result
    value ^= offset
    reflected = parameter.get("frobenius_power") if parameter is not None else 0
    if type(reflected) is not int or reflected not in (0, 1):
        result["reason"] = "Invalid parameter Frobenius power."
        return result
    transported = {0: 0, 1: 1, 2: 3, 3: 2}[value] if reflected else value
    # The three nonzero codes are consecutive exponents of zeta.
    normalized = 0 if transported == 0 else 1 + ((transported - 1) + (ratio - 1)) % 3
    result.update(transported_value=transported, value=normalized, resolved=True, requires_runtime=False)
    return result


def ensure_q8_atlas_transports(project: Project) -> Project:
    if project.id != "hfpss_studio":
        return project
    # Issue source row certificates before cloning. Otherwise pass one has no
    # source certificates to copy, while pass two adds a second, differently
    # named certificate for every image of the same differential.
    migrate_legacy_period_families(project)
    workspaces = {item.id: item for item in project.workspaces}
    plans = q8_atlas_transport_plan(project)
    for sector in project.grading_sectors:
        target = workspaces.get(sector.workspace_id)
        plan = plans.get(sector.id)
        if target is None or plan is None:
            continue
        if target.id in SOURCE_REPRESENTATIONS:
            target.settings["atlas_representative"] = True
            continue
        source = workspaces.get(plan["source_workspace_id"])
        if source is None:
            continue
        prefix = f"atlas_{sector.id}_"
        power, reflected, shift = plan["omega_power"], plan["reflected"], plan["stem_shift"]
        representation = {key: value for key, value in sector.normal_form.items() if value}
        display_thom = _picard_display_basis(plan, representation)
        plan["display_thom_basis"] = deepcopy(display_thom)
        class_bases = {}
        collections = ("classes", "cells", "differential_maps", "differentials", "propositions")
        ids = {item.id: prefix + item.id for key in collections for item in getattr(source, key)}
        for differential in source.differentials:
            if differential.period_stem or differential.period_filtration:
                image_id = ids[differential.id]
                ids[f"prop_period_{differential.id}"] = f"prop_period_{image_id}"
                if differential.period_family_id:
                    ids[differential.period_family_id] = f"period_{image_id}"
        # Basis/named-vector ids may be referenced by display selectors.
        for cell in source.cells:
            ids.update({item.id: prefix + item.id for item in cell.basis + cell.display_basis + cell.named_vectors})

        def display_basis(text):
            basis = expanded_action_basis(text, power, reflected,
                                          target_thom=display_thom["target_thom"], stem_shift=shift)
            basis["thom_provenance"] = deepcopy(display_thom)
            return basis

        def label(text):
            return display_basis(text)["expanded_expression"]

        # Retire only generated E2-only placeholders. They remain archived as
        # provenance; this is a replacement of a model, not a page death.
        obsolete_prefix = f"e2_thom_a{sector.a}_b{sector.b}_"
        obsolete_ids = set()
        for node in target.classes:
            if node.id.startswith(obsolete_prefix):
                node.archived = True
                node.archived_reason = "E2-only placeholder replaced by explicit all-page atlas transport."
                obsolete_ids.add(node.id)
        for key in collections:
            old_records = {item.id: item for item in getattr(target, key)}
            cloned_ids = {ids[item.id] for item in getattr(source, key)}
            previous = [item for item in getattr(target, key)
                        if not item.id.startswith(prefix) and item.id not in cloned_ids]
            if key == "propositions":
                # Explicit expanded image labels can match the E2 importer's
                # Thom labels on a later migration. Its newly generated claims
                # about these managed images duplicate the all-page source
                # claims cloned below. Do not discard similarly named manual
                # claims or claims referring only to independent placeholders.
                previous = [item for item in previous if not (
                    item.id.startswith((f"source_{prefix}", f"source_e2_edge_{prefix}"))
                    and item.rule.startswith("ThomIsomorphism")
                    and any(isinstance(item.conclusion.get(field), str)
                            and item.conclusion[field].startswith(prefix)
                            for field in ("class_id", "source_id", "target_id"))
                )]
                for item in previous:
                    references_obsolete = any(item.conclusion.get(field) in obsolete_ids
                                              for field in ("class_id", "source_id", "target_id"))
                    if (references_obsolete and item.id.startswith("source_e2_")
                            and item.rule.startswith(("DKLLW24 E2", "ThomIsomorphism"))):
                        item.status = "superseded"
                        item.conclusion["source_schema_retirement"] = (
                            "E2-only placeholder replaced by an explicit all-page atlas transport. "
                            "Original claim retained for review; this is not a spectral-sequence death."
                        )
            clones = deepcopy(getattr(source, key))
            for item in clones:
                source_item_id = item.id
                item.id = ids[item.id]
                old = old_records.get(item.id)
                if (old is not None and getattr(old, "archived", False)
                        and old.archived_reason.startswith(("Archived by", "Archived with endpoint cell"))):
                    # A researcher may hide an image without hiding its source.
                    # Rebuilding the transported model must not undo that action.
                    item.archived = True
                    item.archived_reason = old.archived_reason
                if key in {"classes", "cells"}:
                    item.grade.stem += shift
                    item.grade.representation = dict(representation)
                if key == "classes":
                    original_expression = item.expression or item.label
                    display_expression = original_expression
                    # The E2 Thom importer historically renamed the sigma
                    # Euler alias a_sigma_i to a_V, even for dim(V)>1. Its
                    # certified filtration-one S71 column is B*u_V, NOT the
                    # higher-filtration Euler class a_V. Repair only this
                    # generated display alias, never an arbitrary user's a_V.
                    alias_correction = None
                    if source_item_id.startswith("e2_thom_") and item.style.get("e2_pattern") == "S71":
                        display_expression = re.sub(r"a_\{([^{}]+)\}", r"(x+y)u_{\1}", original_expression)
                        if display_expression != original_expression:
                            alias_correction = {
                                "source_expression": original_expression, "expanded_expression": display_expression,
                                "reason": "S71 is the filtration-one Thom column (x+y)u_V, not Euler a_V.",
                                "source_ref": "DKLLW24 Table 6 and the explicit S71 E2 pattern",
                            }
                    basis = display_basis(display_expression)
                    basis["source_expression"] = original_expression
                    if alias_correction:
                        basis["source_alias_correction"] = alias_correction
                    class_bases[source_item_id] = basis
                    item.label = basis["expanded_expression"]
                    item.expression = basis["expanded_expression"]
                    item.sector_id = sector.id
                    item.cell_id = ids.get(item.cell_id, item.cell_id)
                    item.style = _replace_references(item.style, ids)
                    if reflected and item.style.get("e2_components"):
                        # These are residue-field coordinates in the transported
                        # pattern basis, just like node.coordinates (integer
                        # encoding 0,1,2,3 means 0,1,zeta,zeta^2). Do not
                        # conjugate unrelated Witt/2-adic presentation metadata.
                        item.style["e2_components"] = {
                            pattern: ({0: 0, 1: 1, 2: 3, 3: 2}[value]
                                      if isinstance(value, int) else frobenius_scalar(value))
                            for pattern, value in item.style["e2_components"].items()
                        }
                    item.style["atlas_transport"] = {
                        "source_workspace_id": source.id, "source_class_id": source_item_id,
                        "omega_power": power, "reflected": reflected, "stem_shift": shift,
                    }
                    item.style["atlas_display_basis"] = basis
                    if reflected and item.coordinates:
                        item.coordinates = [frobenius_scalar(value) for value in item.coordinates]
                    # User-created period records belong to the source; an
                    # atlas image is not a second manual-period declaration.
                    item.manual_periodicity_id = None
                    item.manual_periodicity_anchor_class_id = None
                    item.periodicity_anchor_class_id = ids.get(item.periodicity_anchor_class_id, item.periodicity_anchor_class_id)
                elif key == "cells":
                    for vector in item.basis + item.named_vectors + item.display_basis:
                        vector.id = ids[vector.id]
                        vector.label = label(vector.label)
                        vector.expression = label(vector.expression) if vector.expression else ""
                        if reflected and hasattr(vector, "coordinates"):
                            vector.coordinates = [frobenius_scalar(value) for value in vector.coordinates]
                elif key == "differential_maps":
                    item.source_cell_id = ids.get(item.source_cell_id, item.source_cell_id)
                    item.target_cell_id = ids.get(item.target_cell_id, item.target_cell_id)
                    item.proposition_id = ids.get(item.proposition_id, item.proposition_id)
                    if reflected:
                        item.matrix = [[frobenius_scalar(value) for value in row] for row in item.matrix]
                elif key == "differentials":
                    item.source_id = ids[item.source_id]
                    item.target_id = ids[item.target_id]
                    item.proposition_id = ids.get(item.proposition_id, item.proposition_id)
                    item.linear_map_id = ids.get(item.linear_map_id, item.linear_map_id)
                    item.anchor_differential_id = ids.get(item.anchor_differential_id, item.anchor_differential_id)
                    item.manual_periodicity_id = None
                    item.period_family_id = ids.get(item.period_family_id, item.period_family_id)
                    item.period_notes += f" Transported by {plan['action']}, stem shift {shift}; coefficients in the transported basis."
                elif key == "propositions":
                    # Parameter ids are global identities, not chart-local
                    # references. Preserve them even if one happens to match
                    # a class or proposition id in the source workspace.
                    parameter = item.conclusion.get("coefficient_parameter")
                    condition = item.conclusion.get("coefficient_condition")
                    external = deepcopy(item.conclusion.get("external_premises"))
                    qualified_ids = {
                        locator["proposition_id"] for locator in external
                        if isinstance(locator, dict) and isinstance(locator.get("proposition_id"), str)
                    } if isinstance(external, list) else set()
                    item.conclusion = _replace_references(item.conclusion, ids)
                    if "external_premises" in item.conclusion:
                        # A qualified proof points to that original workspace,
                        # not a same-name local proof in this atlas image.
                        # Preserve malformed locators too, for fail-closed admission.
                        item.conclusion["external_premises"] = external
                    if condition is not None:
                        # Equality is stated in the shared source field, not
                        # in the transported basis. Neither rename its global
                        # parameter id nor conjugate its predicate twice.
                        item.conclusion["coefficient_condition"] = deepcopy(condition)
                    if isinstance(parameter, dict):
                        try:
                            image_parameter = _transport_coefficient_parameter(parameter, reflected)
                        except ValueError as error:
                            # Imported user metadata must not make every
                            # project read fail. Retain the invalid parameter
                            # verbatim; the algebra can report and block it.
                            item.conclusion["coefficient_parameter"] = deepcopy(parameter)
                            item.conclusion["coefficient_transport_error"] = str(error)
                        else:
                            item.conclusion["coefficient_parameter"] = image_parameter
                            item.conclusion.pop("coefficient_transport_error", None)
                    for grade_key in ("grade", "source_grade", "target_grade"):
                        grade = item.conclusion.get(grade_key)
                        if isinstance(grade, dict) and "stem" in grade:
                            grade["stem"] += shift
                            if "representation" in grade:
                                grade["representation"] = dict(representation)
                    item.conclusion["atlas_transport"] = {**plan, "source_proposition_id": source_item_id}
                    item.premise_ids = [ident if ident in qualified_ids else ids.get(ident, ident)
                                        for ident in item.premise_ids]
                    item.supersedes_id = ids.get(item.supersedes_id, item.supersedes_id)
                    item.statement = f"[{plan['action']}; stem {shift:+d}] {item.statement}"
                    item.rule = "FilteredAtlasTransport: " + item.rule
                    # Relations are expressed between transported endpoints,
                    # so their incidence and d_r degree remain unchanged.
            setattr(target, key, previous + clones)
        # Runtime maps, matrices and e2_components remain in transported
        # coordinates. The following is presentation-only beta/alpha data.
        # Do not conjugate a parameter's stored value and its flag together.
        source_rows = {row.id: row for row in source.differentials}
        image_rows = {row.id: row for row in target.differentials}
        target_claims = {claim.id: claim for claim in target.propositions}
        for row_id, row in source_rows.items():
            claim = target_claims.get(ids.get(row.proposition_id))
            if claim is None:
                continue
            source_basis = class_bases.get(row.source_id, {})
            target_basis = class_bases.get(row.target_id, {})
            claim.conclusion["atlas_display_coefficient"] = atlas_display_coefficient(
                source_basis, target_basis, claim.conclusion.get("coefficient_parameter"),
                coefficient_condition=claim.conclusion.get("coefficient_condition", _NO_COEFFICIENT_CONDITION),
                matrix_endpoint=bool(row.linear_map_id))
            image_rows[ids[row_id]].display_coefficient = deepcopy(claim.conclusion["atlas_display_coefficient"])
        target.differential_events = [item for item in target.differential_events if not item.differential_claim_id.startswith(prefix)]
        target.fates = [item for item in target.fates if not item.class_id.startswith(prefix)]
        for setting in ("rendering", "convergence", "known_page_max", "published_page_schedule", "e2_thom_pattern", "coefficient_assignments"):
            if setting in source.settings:
                target.settings[setting] = deepcopy(source.settings[setting])
            elif setting == "coefficient_assignments":
                # Clearing a source assignment must also clear its generated
                # images. The occurrence's Frobenius flag handles conjugation.
                target.settings.pop(setting, None)
        target.settings["atlas_transport"] = deepcopy(plan)
        target.summary = (
            f"All-page image of {source.name} under {plan['action']}, stem shift {shift:+d}. "
            "Labels denote the transported basis; source claim status and coefficient conjugation are retained."
        )
    # Complete the image-side period records as part of this operation so a
    # direct refresh and the normal full migration have the same contract.
    migrate_legacy_period_families(project)
    return project
