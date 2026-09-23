"""Register the independently audited mixed c coefficient without assigning it.

The registry records installation, not admission: current proof records and
their actual differential premises are checked by the raw resolver each time.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .models import Project, Proposition


PARAMETER_ID = "mixed_d5_A"
WORKSPACE_ID = "ws_sigma_i_2sigma_j"
PROOF_ID = "coefficient_proof_mixed_d5_A"
BINDING = {"workspace_id": WORKSPACE_ID, "parameter_id": PARAMETER_ID, "proposition_id": PROOF_ID}
SOURCE_WORKSPACE_ID = "ws_3sigma_i"
SOURCE_PROPOSITION_ID = "formal_prop_fn-3i-005_1"
SOURCE_DIFFERENTIAL_ID = "diff_three_d5_xyD2"
SOURCE_REF = "backend/data/review/mixed_phi_a_coefficient.v1.json"
_CONSUMERS = {"formal_prop_fn-mix-002_1", "formal_prop_fn-mix-003_1", "formal_prop_der-mix-d5-a-even_1"}
_MARKER = "coefficient_proof_registry"


def _owners(project, ident):
    return [workspace for workspace in project.workspaces if workspace.id == ident]


def _restore_in_place(current, selected, saved):
    """Restore protected records without moving unchanged rows to the end."""
    remaining = iter(deepcopy(saved))
    output = []
    for item in current:
        if not selected(item):
            output.append(item)
        else:
            replacement = next(remaining, None)
            if replacement is not None:
                output.append(replacement)
    output.extend(remaining)
    return output


def capture_coefficient_proof_inputs(project: Project):
    """Protect this installed proof's edited inputs from source migrations.

    Absence is significant after installation. Initial demo construction has
    no marker, so the ordinary formal chart can bootstrap its source records.
    """
    installed = project.research_brief.get(_MARKER, {}).get(PARAMETER_ID)
    if not isinstance(installed, dict):
        return None
    snapshot = {"source": None, "consumers": {}}
    sources = _owners(project, SOURCE_WORKSPACE_ID)
    if len(sources) == 1:
        source = sources[0]
        class_ids = set(installed.get("source_class_ids", []))
        matrix_ids = set(installed.get("source_matrix_ids", []))
        rows = [row for row in source.differentials if row.id == SOURCE_DIFFERENTIAL_ID]
        class_ids.update(ident for row in rows for ident in (row.source_id, row.target_id))
        matrix_ids.update(row.linear_map_id for row in rows if row.linear_map_id)
        snapshot["source"] = {
            "rows": deepcopy(rows),
            "claims": deepcopy([p for p in source.propositions if p.id == SOURCE_PROPOSITION_ID]),
            "class_ids": class_ids, "classes": deepcopy([c for c in source.classes if c.id in class_ids]),
            "matrix_ids": matrix_ids, "matrices": deepcopy([m for m in source.differential_maps if m.id in matrix_ids]),
        }
    owners = _owners(project, WORKSPACE_ID)
    if len(owners) == 1:
        for claim in owners[0].propositions:
            if claim.id not in _CONSUMERS:
                continue
            snapshot["consumers"].setdefault(claim.id, []).append({
                "fields": {key: deepcopy(claim.conclusion[key]) for key in
                           ("coefficient_parameter", "coefficient_proof_registration", "admission_status")
                           if key in claim.conclusion},
                "status": claim.status,
                "rows": deepcopy([row for row in owners[0].differentials if row.proposition_id == claim.id]),
            })
    return snapshot


def restore_coefficient_proof_inputs(project: Project, snapshot) -> None:
    if snapshot is None:
        return
    sources = _owners(project, SOURCE_WORKSPACE_ID)
    saved = snapshot["source"]
    if len(sources) == 1 and saved is not None:
        source = sources[0]
        source.differentials = _restore_in_place(source.differentials, lambda r: r.id == SOURCE_DIFFERENTIAL_ID, saved["rows"])
        source.propositions = _restore_in_place(source.propositions, lambda p: p.id == SOURCE_PROPOSITION_ID, saved["claims"])
        source.classes = _restore_in_place(source.classes, lambda c: c.id in saved["class_ids"], saved["classes"])
        source.differential_maps = _restore_in_place(source.differential_maps, lambda m: m.id in saved["matrix_ids"], saved["matrices"])
    owners = _owners(project, WORKSPACE_ID)
    if len(owners) == 1:
        for ident, saved_claims in snapshot["consumers"].items():
            claims = [p for p in owners[0].propositions if p.id == ident]
            # Preserve every duplicate declaration, instead of repairing the
            # final record while silently discarding the ambiguity.
            if len(claims) == len(saved_claims):
                for claim, saved_claim in zip(claims, saved_claims):
                    for key in ("coefficient_parameter", "coefficient_proof_registration", "admission_status"):
                        claim.conclusion.pop(key, None)
                    claim.conclusion.update(deepcopy(saved_claim["fields"]))
                    claim.status = saved_claim["status"]
                owners[0].differentials = _restore_in_place(
                    owners[0].differentials, lambda row: row.proposition_id == ident, saved_claims[0]["rows"])


def ensure_coefficient_proofs(project: Project) -> Project:
    if project.id != "hfpss_studio":
        return project
    owners = _owners(project, WORKSPACE_ID)
    if len(owners) != 1:
        return project
    workspace = owners[0]
    registry = project.research_brief.setdefault(_MARKER, {})
    if not isinstance(registry, dict):
        return project
    installing = PARAMETER_ID not in registry
    if installing:
        audit = json.loads((Path(__file__).resolve().parents[1] / "data/review/mixed_phi_a_coefficient.v1.json").read_text(encoding="utf-8"))
        rows = [row for source in _owners(project, SOURCE_WORKSPACE_ID)
                for row in source.differentials if row.id == SOURCE_DIFFERENTIAL_ID]
        registry[PARAMETER_ID] = {
            "version": 1, "binding": deepcopy(BINDING),
            "source_class_ids": list(dict.fromkeys(ident for row in rows for ident in (row.source_id, row.target_id))),
            "source_matrix_ids": [row.linear_map_id for row in rows if row.linear_map_id],
        }
        local = [
            ("thom", "The common Thom unit cancels on the two specified finite directions.", "transport"),
            ("products", "The explicit Euler products have scalars 1 and zeta in the stated source basis.", "finite_products"),
            ("comparison", "The (13,7) HFPSS target injects into Tate and has no earlier d3 source.", "transport"),
            ("leibniz", "The 16-stem A differential pattern follows from 2A=0 and Leibniz, not an invertible D2 cycle.", "period_scope"),
        ]
        premise_ids = [SOURCE_PROPOSITION_ID]
        for suffix, statement, key in local:
            ident = f"coefficient_premise_mixed_d5_A_{suffix}"
            premise_ids.append(ident)
            if any(p.id == ident for p in workspace.propositions):
                continue
            workspace.propositions.append(Proposition(
                id=ident, kind="source-lemma", statement=statement, status="source-verified",
                conclusion={"admission_status": "source-verified", "source_audit_id": audit["id"],
                            "source_scope": key, "source_evidence": deepcopy(audit[key])},
                rule="independently audited finite naturality premise", source_ref=SOURCE_REF,
                source_refs=[SOURCE_REF, *audit["source_refs"]],
            ))
        if not any(p.id == PROOF_ID for p in workspace.propositions):
            workspace.propositions.append(Proposition(
                id=PROOF_ID, kind="coefficient-proof", statement=r"c+1=\zeta,\qquad c=\zeta^2",
                status="source-verified", premise_ids=premise_ids,
                conclusion={"parameter_id": PARAMETER_ID, "coefficient_value": audit["coefficient_value"],
                            "admission_status": "source-verified", "source_audit_id": audit["id"],
                            "external_premises": [{"workspace_id": SOURCE_WORKSPACE_ID,
                                                   "proposition_id": SOURCE_PROPOSITION_ID}],
                            "source_evidence": deepcopy(audit["deduction"]),
                            "historical_comparison": deepcopy(audit["historical_comparison"])},
                rule="qualified source differential, Thom cancellation, products and Tate injection",
                source_ref=SOURCE_REF, source_refs=[SOURCE_REF, *audit["source_refs"]],
            ))
    # No setdefault recreates an installed root or premise after withdrawal.
    # The marker only requires a binding; it never grants proof admission.
    for ident in _CONSUMERS:
        claims = [claim for claim in workspace.propositions if claim.id == ident]
        if len(claims) != 1:
            continue
        claim = claims[0]
        spec = claim.conclusion.get("coefficient_parameter")
        if not isinstance(spec, dict) or spec.get("id") != PARAMETER_ID:
            continue
        prior = spec.get("document_baseline")
        if isinstance(prior, dict) and prior.get("profile") == "mixed-document-baseline-v1":
            spec["value"] = prior.get("original_value")
            spec.pop("document_baseline", None)
        if installing:
            spec.setdefault("proof_binding", deepcopy(BINDING))
            claim.conclusion["coefficient_proof_registration"] = {"parameter_id": PARAMETER_ID, "binding": deepcopy(BINDING)}
        claim.conclusion.pop("document_baseline", None)
        claim.conclusion.setdefault("coefficient_proof_history", {
            "source_status": claim.conclusion.get("source_status"),
            "source_blockers": deepcopy(claim.conclusion.get("source_blockers", [])),
        })
        claim.conclusion.update({"source_status": "proof-bound-coefficient", "source_blockers": [],
                                 "machine_verification_pending": [], "required_admitted_premises": True})
        if installing:
            claim.conclusion["admission_status"] = "source-verified"
            claim.status = "source-verified"
        if isinstance(claim.premise_ids, list) and PROOF_ID not in claim.premise_ids:
            claim.premise_ids.append(PROOF_ID)
        for row in workspace.differentials:
            if row.proposition_id == ident:
                if installing:
                    row.status = "source-verified"
                row.required_admitted_premises = True
    return project
