"""Read-only audit support for the periodic fate review ledger.

The ledger is deliberately separate from the canonical Studio project.  It
groups named chart occurrences by source-certified period identities and
checks whether the recorded high-filtration obligations have enough admitted
nonzero differential rank to vanish.  Formal-power-series families are routed
to a separate fixed-differential registry instead of being approximated by a
large finite vector space.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .cell_linear_algebra import CellLinearAlgebraError, matrix_rank


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER_PATH = (
    ROOT / "data" / "review" / "formal_notes_periodic_fate_ledger.v1.json"
)

FATE_CERTIFYING_STATUSES = frozenset(
    {"admitted", "admitted-pattern", "verified-pattern"}
)
PERIOD_CLASS_RE = re.compile(
    r"^pc\.[a-z0-9-]+\.(?:d8|gd8semi|gd8)\.[a-z0-9-]+$"
)
REQUIRED_MODULE_KINDS = frozenset(
    {"finite-2-primary", "witt-2-adic", "j-adic-formal-power-series"}
)


class PeriodicFateLedgerError(ValueError):
    """Raised when a review ledger violates its declared identity contract."""


def hfpss_d8_period_class_id(
    sector: str,
    shape: str,
    *,
    coefficient: str = "one",
    k_power: int = 0,
    d_power: int = 0,
) -> str:
    """Return the genuine HFPSS D^8-orbit identifier for one occurrence."""
    return (
        f"pc.{sector}.d8."
        f"{shape}-c{coefficient}-k{k_power}-d{d_power % 8}"
    )


def tate_g_d8_period_class_id(
    sector: str,
    shape: str,
    *,
    coefficient: str = "one",
    k_power: int = 0,
    d_power: int = 0,
) -> str:
    """Return the conditional positive-filtration {g,D^8} orbit identifier.

    Since g=kD^3, the invariant of the exponent pair (k_power,d_power) is
    d_power-3*k_power modulo 8.  Calling this function does not itself certify
    that the HFPSS-to-TateSS comparison applies to the requested occurrence.
    """
    residue = (d_power - 3 * k_power) % 8
    return f"pc.{sector}.gd8.{shape}-c{coefficient}-r{residue}"


def hfpss_g_d8_semiperiod_class_id(
    sector: str,
    shape: str,
    *,
    coefficient: str = "one",
    k_power: int = 0,
    d_power: int = 0,
) -> str:
    """Return the all-family forward ``g``/invertible ``D^8`` family id.

    The residue is the same exponent invariant as in the Tate lattice because
    ``g=kD^3``.  The different ``gd8semi`` namespace matters: occurrences in
    this HFPSS family carry a concrete translation ``(s,q)`` with ``s>=0`` and
    ``q`` integral.  The id groups bo and non-bo occurrences into one periodic
    family; it does not manufacture an inverse for ``g``.
    """
    residue = (d_power - 3 * k_power) % 8
    return f"pc.{sector}.gd8semi.{shape}-c{coefficient}-r{residue}"


def load_periodic_fate_ledger(path: Path | None = None) -> dict[str, Any]:
    source = path or DEFAULT_LEDGER_PATH
    return json.loads(source.read_text(encoding="utf-8"))


def _fact_period_class_ids(fact: dict[str, Any]) -> set[str]:
    output: set[str] = set()
    for key in ("source_period_class_ids", "target_period_class_ids"):
        output.update(str(item) for item in fact.get(key, []))
    return output


def audit_periodic_fate_ledger(data: dict[str, Any]) -> dict[str, Any]:
    """Validate references and report finite-domain vanishing coverage."""
    errors: list[str] = []
    mechanisms = {
        item.get("id"): item for item in data.get("period_mechanisms", [])
    }
    facts = {item.get("id"): item for item in data.get("fact_families", [])}
    formal_series_families = {
        item.get("id"): item for item in data.get("formal_series_families", [])
    }
    module_kinds = {item.get("id") for item in data.get("module_kinds", [])}
    period_defaults = data.get("fact_family_period_defaults", {})

    if len(mechanisms) != len(data.get("period_mechanisms", [])):
        errors.append("period mechanism ids must be unique")
    if len(facts) != len(data.get("fact_families", [])):
        errors.append("fact family ids must be unique")
    if len(formal_series_families) != len(data.get("formal_series_families", [])):
        errors.append("formal-series family ids must be unique")
    for family_id, family in formal_series_families.items():
        if not family_id:
            errors.append("formal-series family id must be nonempty")
        if not family.get("fixed_differential_templates") and not family.get(
            "permanent_cycle_templates"
        ):
            errors.append(
                f"{family_id} lacks a fixed differential or permanent-cycle template"
            )
    missing_module_kinds = REQUIRED_MODULE_KINDS - module_kinds
    if missing_module_kinds:
        errors.append(
            "missing module kinds: " + ", ".join(sorted(missing_module_kinds))
        )

    for fact_id, fact in facts.items():
        same_object_period = fact.get(
            "same_object_period_id", period_defaults.get("same_object_period_id")
        )
        if same_object_period:
            mechanism = mechanisms.get(same_object_period)
            if mechanism is None:
                errors.append(
                    f"{fact_id} references unknown period mechanism "
                    f"{same_object_period}"
                )
            elif mechanism.get("semantic") != "same-object":
                errors.append(
                    f"{fact_id} uses pattern-only {same_object_period} "
                    "as a same-object period"
                )
        semiperiod_family = fact.get(
            "semiperiod_family_id", period_defaults.get("semiperiod_family_id")
        )
        if not semiperiod_family:
            errors.append(f"{fact_id} lacks an HFPSS semiperiod family")
        else:
            mechanism = mechanisms.get(semiperiod_family)
            if mechanism is None:
                errors.append(
                    f"{fact_id} references unknown semiperiod mechanism "
                    f"{semiperiod_family}"
                )
            elif mechanism.get("semantic") != "period-family":
                errors.append(
                    f"{fact_id} semiperiod {semiperiod_family} is not a "
                    "period-family mechanism"
                )
        for pattern_id in fact.get("pattern_period_ids", []):
            mechanism = mechanisms.get(pattern_id)
            if mechanism is None:
                errors.append(f"{fact_id} references unknown pattern {pattern_id}")
            elif mechanism.get("semantic") != "pattern-only":
                errors.append(f"{fact_id} pattern {pattern_id} is not pattern-only")
        for period_class_id in _fact_period_class_ids(fact):
            if not PERIOD_CLASS_RE.match(period_class_id):
                errors.append(
                    f"{fact_id} has malformed period class id {period_class_id}"
                )

    alias_ids: set[str] = set()
    for alias in data.get("conditional_comparison_classes", []):
        alias_id = str(alias.get("id", ""))
        if alias_id in alias_ids:
            errors.append(f"duplicate comparison class id {alias_id}")
        alias_ids.add(alias_id)
        if not PERIOD_CLASS_RE.match(alias_id) or ".gd8." not in alias_id:
            errors.append(f"malformed comparison class id {alias_id}")
        if not alias.get("comparison_certificate_id"):
            errors.append(f"{alias_id} lacks a comparison certificate")
        if len(alias.get("hfpss_period_class_ids", [])) < 2:
            errors.append(f"{alias_id} must join at least two D8 orbit ids")

    obligation_results: list[dict[str, Any]] = []
    for obligation in data.get("vanishing_audit", {}).get("obligations", []):
        obligation_id = str(obligation.get("id", ""))
        module_kind = str(obligation.get("module_kind", "finite-2-primary"))
        dimension = int(obligation.get("cell_dimension", 0))
        required_rank = int(obligation.get("required_killed_rank", dimension))
        killed_vectors: list[list[str]] = []
        accepted_fact_ids: list[str] = []
        unresolved_reasons: list[str] = list(
            obligation.get("unresolved_reasons", [])
        )

        if module_kind not in module_kinds:
            unresolved_reasons.append(f"unknown module kind {module_kind}")
        if module_kind == "j-adic-formal-power-series":
            family_id = str(obligation.get("fixed_differential_family_id", ""))
            family = formal_series_families.get(family_id)
            if not family_id:
                unresolved_reasons.append(
                    "formal-series obligation must name a fixed_differential_family_id"
                )
            elif family is None:
                unresolved_reasons.append(
                    f"unknown fixed differential family {family_id}"
                )
            elif family.get("status") not in FATE_CERTIFYING_STATUSES:
                unresolved_reasons.append(
                    f"{family_id} has non-certifying status {family.get('status')}"
                )
            elif family.get("vanishing_outcome") != "killed":
                unresolved_reasons.append(
                    f"{family_id} does not assert that this formal-series family is killed"
                )

            obligation_results.append(
                {
                    "id": obligation_id,
                    "period_class_id": obligation.get("period_class_id"),
                    "module_kind": module_kind,
                    "audit_mode": "fixed-differential-family",
                    "fixed_differential_family_id": family_id or None,
                    "covered": not unresolved_reasons,
                    "cell_dimension": None,
                    "required_killed_rank": None,
                    "covered_rank": None,
                    "accepted_fact_ids": [],
                    "unresolved_reasons": unresolved_reasons,
                }
            )
            continue

        if obligation.get("kind") == "fundamental-domain-enumeration":
            unresolved_reasons.append(
                "the E2 basis in this periodic fundamental domain is incomplete"
            )
        else:
            for resolution in obligation.get("resolutions", []):
                fact_id = resolution.get("fact_id")
                fact = facts.get(fact_id)
                if fact is None:
                    unresolved_reasons.append(
                        f"resolution references unknown fact {fact_id}"
                    )
                    continue
                if fact.get("status") not in FATE_CERTIFYING_STATUSES:
                    unresolved_reasons.append(
                        f"{fact_id} has non-certifying status {fact.get('status')}"
                    )
                    continue
                vectors = resolution.get("killed_vectors", [])
                if not vectors and dimension == 1 and int(
                    resolution.get("killed_rank", 0)
                ) == 1:
                    vectors = [["1"]]
                if not vectors:
                    unresolved_reasons.append(
                        f"{fact_id} lacks an explicit killed-subspace basis"
                    )
                    continue
                if any(len(vector) != dimension for vector in vectors):
                    unresolved_reasons.append(
                        f"{fact_id} killed-subspace vectors have the wrong dimension"
                    )
                    continue
                killed_vectors.extend(vectors)
                accepted_fact_ids.append(str(fact_id))

        try:
            covered_rank = matrix_rank(killed_vectors, "F4") if killed_vectors else 0
        except CellLinearAlgebraError as error:
            unresolved_reasons.append(str(error))
            covered_rank = 0
        covered = (
            dimension > 0
            and required_rank > 0
            and covered_rank >= required_rank
            and not unresolved_reasons
        )
        obligation_results.append(
            {
                "id": obligation_id,
                "period_class_id": obligation.get("period_class_id"),
                "module_kind": module_kind,
                "audit_mode": "finite-rank",
                "covered": covered,
                "cell_dimension": dimension,
                "required_killed_rank": required_rank,
                "covered_rank": covered_rank,
                "accepted_fact_ids": accepted_fact_ids,
                "unresolved_reasons": unresolved_reasons,
            }
        )

    unresolved = [item for item in obligation_results if not item["covered"]]
    return {
        "valid": not errors,
        "errors": errors,
        "status": (
            "invalid"
            if errors
            else "complete"
            if not unresolved and obligation_results
            else "underdetermined"
        ),
        "fact_family_count": len(facts),
        "period_mechanism_count": len(mechanisms),
        "module_kind_count": len(module_kinds),
        "formal_series_family_count": len(formal_series_families),
        "obligation_count": len(obligation_results),
        "finite_rank_obligation_count": sum(
            item.get("audit_mode") == "finite-rank" for item in obligation_results
        ),
        "formal_series_obligation_count": sum(
            item.get("audit_mode") == "fixed-differential-family"
            for item in obligation_results
        ),
        "covered_obligation_count": len(obligation_results) - len(unresolved),
        "unresolved_obligation_ids": [item["id"] for item in unresolved],
        "obligations": obligation_results,
    }
