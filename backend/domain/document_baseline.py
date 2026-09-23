"""Explicit, reversible-by-migration document defaults for the research service.

This profile is not part of the strict source audit.  It neither assigns user
settings nor upgrades document-adopted statements to verified theorems.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from .formal_notes_chart import _node_for
from .models import Differential, Project, Proposition


_WORKSPACE = "ws_sigma_i_2sigma_j"
_PROFILE = "mixed-document-baseline-v1"
_NOTE = "Document baseline: independently unresolved values temporarily follow the cited document; not a verification claim."
_AUDIT = "backend/data/review/mixed_pq_d21_source.v1.json"
_DEFAULTS = {
    "mixed_d5_B": (1, "REU Projects/Note/formal_notes.tex:953-970", "document-adopted"),
    "mixed_d17_VD3": (1, "REU Projects/table_Q8.tex:533", "document-adopted"),
    "mixed_d19_XD4": (1, "REU Projects/table_Q8.tex:537", "document-adopted"),
}
_ALLOW_FACTS = {"FN-MIX-005"}
_FORWARD = {"multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True}
_U = r"u_{\sigma_i+2\sigma_j}"


def _adoption(claim, source_ref):
    """Retain the first pre-profile status/source when applying repeatedly."""
    prior = claim.conclusion.get("document_baseline")
    if isinstance(prior, dict) and prior.get("profile") == _PROFILE:
        return deepcopy(prior)
    return {
        "profile": _PROFILE, "authority": "document-adopted",
        "original_status": claim.status,
        "original_source_status": claim.conclusion.get("source_status"),
        "original_source_ref": claim.source_ref,
        "source_ref": source_ref, "note": _NOTE,
    }


def _admit_existing(workspace):
    claims = {p.id: p for p in workspace.propositions}
    matrices = {m.id: m for m in workspace.differential_maps}
    cells = {c.id: c for c in workspace.cells}
    admitted = []
    for row in workspace.differentials:
        claim = claims.get(row.proposition_id)
        if claim is None or claim.conclusion.get("fact_id") not in _ALLOW_FACTS:
            continue
        adoption = _adoption(claim, claim.source_ref)
        adoption.setdefault("original_differential_status", row.status)
        matrix = matrices.get(row.linear_map_id)
        if matrix is not None:
            adoption.setdefault("original_matrix_status", matrix.status)
            matrix.status = "admitted"
            for ident in (matrix.source_cell_id, matrix.target_cell_id):
                cell = cells.get(ident)
                if cell is not None:
                    adoption.setdefault("original_cell_statuses", {}).setdefault(ident, cell.status)
                    cell.status = "admitted"
        row.status = claim.status = "admitted"
        claim.conclusion.update({"admission_status": "admitted", "source_status": "document-adopted",
                                 "document_baseline": adoption})
        admitted.append(row.id)
    return admitted


def _defaults(project):
    # Same-ID declarations must agree, including any existing transported
    # declarations.  User coefficient_assignments are deliberately untouched.
    for workspace in project.workspaces:
        for claim in workspace.propositions:
            spec = claim.conclusion.get("coefficient_parameter")
            if not isinstance(spec, dict) or spec.get("id") not in _DEFAULTS:
                continue
            if not claim.id.startswith("formal_prop_") and not claim.conclusion.get("atlas_transport"):
                # An unrelated researcher claim is not managed by this profile.
                continue
            value, source_ref, authority = _DEFAULTS[spec["id"]]
            spec = deepcopy(spec)
            spec.setdefault("document_baseline", {
                "profile": _PROFILE, "authority": authority,
                "original_value": spec.get("value"), "source_ref": source_ref,
                "note": _NOTE if authority == "document-adopted" else "Value fixed by the separate coefficient source audit.",
            })
            spec["value"] = value
            claim.conclusion["coefficient_parameter"] = spec


def _node(workspace, label, grade, pattern, *, j=0):
    node = _node_for(workspace, label, *grade)
    node.style.update({"e2_pattern": pattern, "two_valuation": 0, "j_order": j})
    node.style.pop("e2_components", None)
    return node


def _upsert_arrow(workspace, ident, fact, page, source, target, *, period=64,
                  source_ref, extra=None):
    prop_id = "formal_prop_" + fact.lower()
    claim = next((p for p in workspace.propositions if p.id == prop_id), None)
    if claim is not None and claim.conclusion.get("document_baseline", {}).get("profile") != _PROFILE:
        return None  # Do not replace a same-ID researcher record.
    statement = rf"d_{{{page}}}({source.label})={target.label}"
    data = {
        "fact_id": fact, "source_id": source.id, "target_id": target.id,
        "page": page, "admission_status": "admitted", "source_status": "document-adopted",
        "coefficient_scope": "exact-port", "period_stem": period,
        "period_kind": "same-object" if period == 64 else "repeated-differential-pattern",
        "period_is_invertible": period == 64,
        "period_multiplier": f"D^{period // 8}", "forward_period": deepcopy(_FORWARD),
        "coverage_scope": "Only the specified constant coefficient ports and their declared translates; incoming boundaries retain priority.",
        "document_baseline": {"profile": _PROFILE, "authority": "document-adopted",
                              "source_ref": source_ref, "note": _NOTE},
    }
    data.update(deepcopy(extra or {}))
    if claim is None:
        claim = Proposition(id=prop_id, kind="differential", statement=statement,
                            status="admitted", conclusion=data, rule="explicit document baseline",
                            notes=_NOTE, source_ref=source_ref, source_refs=[source_ref])
        workspace.propositions.append(claim)
    else:
        claim.status = "admitted"
        claim.statement = statement
        claim.conclusion.update(data)
    parameter = data.get("coefficient_parameter")
    if parameter:
        claim.statement = rf"d_{{{page}}}({source.label})=({parameter['expression']}){target.label}"
    row = next((d for d in workspace.differentials if d.id == ident), None)
    if row is None:
        row = Differential(id=ident, source_id=source.id, target_id=target.id, page=page,
                           status="admitted", label=fact, proposition_id=prop_id, period_stem=period,
                           period_notes=f"Document-adopted: D^{period // 8} repeated pattern and forward g=kD^3; no inverse g assumed.")
        workspace.differentials.append(row)
    elif row.proposition_id == prop_id:
        row.status = "admitted"
    return row.id


def _positive_j_zero(workspace, audit):
    fact = "DER-MIX-D21-JQ-D4-ZERO"
    ident = "formal_prop_" + fact.lower()
    source = _node(workspace, r"j(h_1^2+xh_1v_1)D^4" + _U, (34, 2), "S22H", j=1)
    data = {
        "fact_id": fact, "source_id": source.id, "source_label": source.label,
        "grade": {"stem": 34, "filtration": 2}, "e2_components": {"S22H": 1},
        "page": 21, "zero": True, "admission_status": "admitted",
        "source_status": "document-adopted", "cycle_constraint": "outgoing-only",
        "coefficient_scope": "exact-port", "j_order": 1, "source_component": "positive-j",
        "covers": "j^n QD^4 for n>=1, not the constant Q coefficient",
        "period_stem": 64, "period_kind": "same-object", "period_is_invertible": True,
        "forward_period": deepcopy(_FORWARD),
        "derivation": "Choose the actual permanent Witt lift J of j from DKLLW prop:inftybo. JY=0 in the finite order-two target. Thus d21(J^n QD4)=0 for n>=1. This does not restore incoming boundaries or assert a permanent raw polynomial v1^4/D.",
        "document_baseline": {"profile": _PROFILE, "authority": "document-adopted", "source_ref": _AUDIT, "note": _NOTE},
        "source_certificate": deepcopy(audit.get("completed_ideal", {})),
    }
    claim = next((p for p in workspace.propositions if p.id == ident), None)
    if claim is None:
        workspace.propositions.append(Proposition(
            id=ident, kind="zero-differential", statement=r"d_{21}(J^nQD^4)=0\quad(n\geq1)",
            status="admitted", conclusion=data, rule="permanent Witt lift and finite target",
            notes="Outgoing-only certificate; earlier incoming boundaries are unchanged.",
            source_ref=_AUDIT, source_refs=[_AUDIT, "DKLLW prop:inftybo, main.tex:1391-1400"],
        ))
    elif claim.conclusion.get("document_baseline", {}).get("profile") == _PROFILE:
        claim.status = "admitted"
        claim.conclusion.update(data)


def _withdraw_document_baseline(project):
    """Restore only saved profile metadata; never remove shared class nodes."""
    for workspace in project.workspaces:
        rows = {row.id: row for row in workspace.differentials}
        matrices = {matrix.id: matrix for matrix in workspace.differential_maps}
        cells = {cell.id: cell for cell in workspace.cells}
        removed_claims, removed_rows, restored_rows = set(), set(), {}
        changed = False
        for claim in workspace.propositions:
            spec = claim.conclusion.get("coefficient_parameter")
            saved = spec.get("document_baseline") if isinstance(spec, dict) else None
            if isinstance(saved, dict) and saved.get("profile") == _PROFILE:
                spec["value"] = saved.get("original_value")
                spec.pop("document_baseline", None)
                changed = True
            adopted = claim.conclusion.get("document_baseline")
            if not isinstance(adopted, dict) or adopted.get("profile") != _PROFILE:
                continue
            changed = True
            related = [row for row in rows.values() if row.proposition_id == claim.id]
            if "original_status" not in adopted:
                # Only newly created profile claims lack a pre-profile status.
                removed_claims.add(claim.id)
                removed_rows.update(row.id for row in related)
                continue
            claim.status = adopted["original_status"]
            claim.conclusion["admission_status"] = claim.status
            if adopted.get("original_source_status") is None:
                claim.conclusion.pop("source_status", None)
            else:
                claim.conclusion["source_status"] = adopted["original_source_status"]
            claim.source_ref = adopted.get("original_source_ref", claim.source_ref)
            for row in related:
                row.status = adopted.get("original_differential_status", claim.status)
                restored_rows[row.id] = row.status
                matrix = matrices.get(row.linear_map_id)
                if matrix is not None and "original_matrix_status" in adopted:
                    matrix.status = adopted["original_matrix_status"]
            for ident, status in adopted.get("original_cell_statuses", {}).items():
                if ident in cells:
                    cells[ident].status = status
            claim.conclusion.pop("document_baseline", None)
        if removed_rows:
            workspace.differentials = [row for row in workspace.differentials if row.id not in removed_rows]
        if removed_claims:
            workspace.propositions = [claim for claim in workspace.propositions if claim.id not in removed_claims]
        # These automatic event records were created from the profile rows.
        # Unrelated imported history remains untouched.
        removed_events = {f"event_{ident}_{role}" for ident in removed_rows for role in ("supports", "receives")}
        workspace.differential_events = [event for event in workspace.differential_events if event.id not in removed_events]
        for event in workspace.differential_events:
            if event.differential_claim_id in restored_rows and event.id in {
                    f"event_{event.differential_claim_id}_supports", f"event_{event.differential_claim_id}_receives"}:
                event.status = restored_rows[event.differential_claim_id]
        summary = workspace.settings.get("document_baseline")
        if isinstance(summary, dict) and summary.get("profile") == _PROFILE:
            workspace.settings.pop("document_baseline", None)
            changed = True
        if changed:
            workspace.fates = []  # Recomputed by the existing migration sync.
    return project


def apply_document_baseline(project: Project) -> Project:
    """Apply only the explicitly enabled Studio document profile, in place."""
    if project.id != "hfpss_studio":
        return project
    if project.research_brief.get("document_baseline") is not True:
        return _withdraw_document_baseline(project)
    workspace = next((w for w in project.workspaces if w.id == _WORKSPACE), None)
    if workspace is None:
        return project
    _defaults(project)
    admitted = _admit_existing(workspace)
    audit = json.loads((Path(__file__).resolve().parents[1] / "data/review/mixed_pq_d21_source.v1.json").read_text(encoding="utf-8"))
    p = _node(workspace, r"(yh_2+xh_1v_1)D^4" + _U, (34, 2), "S22Y")
    q = _node(workspace, r"(h_1^2+xh_1v_1)D^4" + _U, (34, 2), "S22H")
    y = _node(workspace, r"x^3k^5D^7" + _U, (33, 23), "S53")
    for name, fact, source, section, extra in (
        ("p", "DER-MIX-D21-P-D4-EULER", p, "euler_P_d21", {"coefficient_value": 1}),
        ("q", "DER-MIX-D21-Q-D4-B-INVERSE", q, "linked_Q_d21", {
            "coefficient_parameter": {"id": "mixed_d21_Q_numerator", "symbol": "1", "expression": "1/b",
                                      "value": 1, "domain": [1], "frobenius_power": 0,
                                      "inverse_parameter_id": "mixed_d5_B",
                                      "fixed_reason": "The P Euler coefficient is 1; use the existing relative b before atlas Frobenius."}}),
    ):
        admitted.append(_upsert_arrow(workspace, f"formal_diff_document_mixed_d21_{name}_D4", fact, 21,
                                      source, y, source_ref=_AUDIT,
                                      extra={**extra, "source_certificate": deepcopy(audit.get(section, {})),
                                             "completed_kernel": "F4{P+bQ} plus j F4[[j]] Q",
                                             "coefficient_prerequisites": {"mixed_d5_A": "nonzero and not 1", "mixed_d5_B": "nonzero"}}))
    _positive_j_zero(workspace, audit)
    for power, page, period, target_grade, target_label, fact in (
        (2, 11, 32, (14, 14), r"(h_1^2+xh_1v_1)k^3D^3", "TQ8-MIX-L0528"),
        (5, 19, 64, (38, 22), r"(h_1^2+xh_1v_1)k^5D^7", "TQ8-MIX-L0538"),
    ):
        source = _node(workspace, rf"(x^2+y^2)h_1D^{power}" + _U, (8 * power - 1, 3), "S73")
        target = _node(workspace, target_label + _U, target_grade, "S22H")
        admitted.append(_upsert_arrow(workspace, f"formal_diff_document_mixed_d{page}_r_D{power}", fact,
                                      page, source, target, period=period,
                                      source_ref=f"REU Projects/table_Q8.tex:{int(fact[-4:])}",
                                      extra={"source_history": "Document row adopted temporarily; no independent proof is claimed.",
                                             "source_pattern": "S73", "excluded_companion": "S73V",
                                             "target_pattern": "S22H"}))
    workspace.settings["document_baseline"] = {
        "profile": _PROFILE, "enabled": True, "authority": "document-adopted", "note": _NOTE,
        "parameter_defaults": {key: value[0] for key, value in _DEFAULTS.items()},
        "admitted_differential_ids": [ident for ident in admitted if ident],
        "excluded": ["Jan29 withdrawn proof branches", "source-audited contradictions"],
        "remaining_scope": "Unlisted late rows remain under their existing source/admission status; no full-convergence claim.",
    }
    return project
