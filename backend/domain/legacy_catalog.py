"""Read-only catalog for the 21 research sseq ver15.3 canvases."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from .models import ClassFate, ClassNode, Differential, Grade, Proposition, Workspace
from .project_io import ProjectImportValidationError, _legacy_integer, _legacy_offset, _legacy_text


SOURCE_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "legacy_catalog"


# Only exact source coordinates stated in formal_notes.tex are linked.  Any
# other visual edge keeps file-level provenance and remains a review claim.
EVIDENCE_BY_SECTOR: dict[str, dict[tuple[int, int, int], tuple[str, str, str]]] = {
    "2sigma_i": {
        (3, 0, 0): ("prop:d3 u2sig", r"d_3(u_{2\sigma_i})=x^2h_1u_{2\sigma_i}", "reviewed"),
        (3, 12, 0): ("cor:d3 v1u2sig", r"d_3(v_1^6u_{2\sigma_i})=h_1^3Du_{2\sigma_i}", "reviewed"),
        (5, 6, 2): ("prop:d5-1 u2sig", r"d_5(\{x^2+y^2\}Du_{2\sigma_i})=k\{x^2+y^2\}h_2Du_{2\sigma_i}", "reviewed"),
        (5, 11, 1): ("prop:d5-2 u2sig", r"d_5(h_2Du_{2\sigma_i})=kh_2^2Du_{2\sigma_i}", "review"),
        (5, 8, 0): ("prop:d5-3", r"d_5(2Du_{2\sigma_i})=2kh_2Du_{2\sigma_i}", "review"),
        (11, 14, 2): ("prop: d11 2sig (14,2)", r"d_{11}(\{x^2+y^2\}D^2u_{2\sigma_i})=k^3h_1D^3u_{2\sigma_i}", "review"),
        (9, 15, 5): ("cor:d9-h1ext", r"d_9(2kh_2D^2u_{2\sigma_i})=k^3h_1^2D^3u_{2\sigma_i}", "review"),
        (9, 27, 1): ("cor:d9-h1ext", r"d_9(2h_2D^3u_{2\sigma_i})=k^2h_1^2D^4u_{2\sigma_i}", "review"),
        (9, 26, 2): ("cor: d9 Leibniz", r"d_9(h_1^2D^3u_{2\sigma_i})=k^2D^3h_2^3u_{2\sigma_i}", "reviewed"),
        (7, 25, 1): ("cor: d7 2sig (25,1)", r"d_7(h_1D^3u_{2\sigma_i})=2k^2D^4u_{2\sigma_i}", "reviewed"),
        (7, 9, 1): ("prop: d7 2sig (9,1))", r"d_7(h_1Du_{2\sigma_i})=2k^2D^2u_{2\sigma_i}", "review"),
        (9, 19, 1): ("prop: d9 2sig (19,1)", r"d_9(h_2D^2u_{2\sigma_i})=h_1^2k^2D^3u_{2\sigma_i}", "review"),
        (21, 55, 5): ("prop: d21 2sig (55,5)", r"d_{21}(kh_2D^7u_{2\sigma_i})=k^6x^2D^{10}u_{2\sigma_i}", "review"),
    },
    "3sigma_i": {
        (5, 14, 10): ("formal_notes:3sigma:d5-(14,10)", r"d_5(k^2\{x^2+y^2\}D^3u_{3\sigma_i})=k^3\{x+y\}h_1^2D^3u_{3\sigma_i}", "reviewed"),
        (5, 10, 2): ("formal_notes:3sigma:d5-(10,2)", r"d_5(\{yh_2+xh_1v_1\}Du_{3\sigma_i})=kx^3D^2u_{3\sigma_i}", "reviewed"),
        (5, 7, 1): ("formal_notes:3sigma:d5-(7,1)", r"d_5(\{x+y\}Du_{3\sigma_i})=k\{yh_2+h_1^2\}Du_{3\sigma_i}", "reviewed"),
        (9, 25, 3): ("prop:3sig-d9-euler", r"d_9(\{x+y\}h_1^2D^3u_{3\sigma_i})=2v_1^2k^3D^4u_{3\sigma_i}", "reviewed"),
        (11, 30, 2): ("prop:3sig-d11-res", r"d_{11}(\{x^2+y^2\}D^4u_{3\sigma_i})=\{h_1+xv_1\}h_1k^3D^5u_{3\sigma_i}", "review"),
    },
    "sigma_i+2sigma_j": {
        (3, 4, 0): ("formal_notes:mixed:d3-(4,0)", r"d_3(v_1^2u_{\sigma_i+2\sigma_j})=h_1^3u_{\sigma_i+2\sigma_j}", "reviewed"),
        (3, 1, 1): ("formal_notes:mixed:d3-(1,1)", r"d_3(\{h_1+xv_1\}u_{\sigma_i+2\sigma_j})=2\zeta v_1^2ku_{\sigma_i+2\sigma_j}", "reviewed"),
        (5, 14, 10): ("prop:d5 i2j", r"d_5(k^2\{x^2+y^2\}D^3u_{\sigma_i+2\sigma_j})=k^3\{x+y\}h_1^2D^3u_{\sigma_i+2\sigma_j}", "review"),
        (5, 6, 2): ("cor:prop:d5 i2j", r"d_5(\{x^2+y^2\}Du_{\sigma_i+2\sigma_j})=k\{x+y\}h_1^2Du_{\sigma_i+2\sigma_j}", "review"),
        (5, 10, 2): ("formal_notes:mixed:d5-(10,2)", r"d_5(\{yh_2+xh_1v_1\}Du_{\sigma_i+2\sigma_j})=x^3kD^2u_{\sigma_i+2\sigma_j}", "review"),
        (5, 7, 1): ("formal_notes:mixed:d5-(7,1)", r"d_5(\{x+y\}Du_{\sigma_i+2\sigma_j})=k\{yh_2+h_1^2\}Du_{\sigma_i+2\sigma_j}", "review"),
        (5, 15, 1): ("formal_notes:mixed:d5-(15,1)", r"d_5(\{x+y\}D^2u_{\sigma_i+2\sigma_j})=k\{h_1^2+xh_1v_1\}D^2u_{\sigma_i+2\sigma_j}", "review"),
        (11, 13, 3): ("formal_notes:mixed:d11-(13,3)", r"d_{11}(x^3D^2u_{\sigma_i+2\sigma_j})=\{x+y\}h_1k^3D^3u_{\sigma_i+2\sigma_j}", "review"),
    },
}


@dataclass(frozen=True)
class CatalogEntry:
    id: str
    filename: str
    title: str
    sector: str
    stage: str
    authority: str
    status: str
    source: str
    evidence_ref: str


CATALOG = (
    CatalogEntry("2sigma-vor-e3", "2sigma_vorE3.json", "2sigma before E3", "2sigma_i", "pre-E3 snapshot", "record-note", "historical", "sseq ver15.3", "record/note.tex; early 2sigma computation"),
    CatalogEntry("2sigma-vor-e6", "2sigma_vorE6.json", "2sigma before E6", "2sigma_i", "pre-E6 snapshot", "record-note", "historical", "sseq ver15.3", "record/note.tex; early 2sigma computation"),
    CatalogEntry("2sigma-dec16", "2sigma_Dec16.json", "2sigma Dec 16", "2sigma_i", "2025-12-16", "record-note", "rejected", "sseq ver15.3", "record/note.tex:1236-1242; old 16-period d9 and (10,2) d9 are wrong"),
    CatalogEntry("2sigma-d5-dec15", "d_5 plus 12.15 diffs.json", "2sigma d5 plus Dec 15", "2sigma_i", "2025-12-15", "record-note", "historical", "sseq ver15.3", "record/note.tex; historical d5 stage"),
    CatalogEntry("2sigma-dec17", "2sigma_Dec17.json", "2sigma Dec 17", "2sigma_i", "2025-12-17", "record-note", "historical", "sseq ver15.3", "record/note.tex; corrected after Dec 16"),
    CatalogEntry("2sigma-dec18", "2sigma_Dec18.json", "2sigma Dec 18", "2sigma_i", "2025-12-18", "record-note", "historical", "sseq ver15.3", "record/note.tex; intermediate 2sigma stage"),
    CatalogEntry("2sigma-dec23-preview", "2sigma_Dec23_preview.json", "2sigma Dec 23 preview", "2sigma_i", "2025-12-23 preview 1", "record-note", "review", "sseq ver15.3", "record/note.tex; preview snapshot"),
    CatalogEntry("2sigma-dec23-preview2", "2sigma_Dec23_preview2.json", "2sigma Dec 23 preview 2", "2sigma_i", "2025-12-23 preview 2", "record-note", "review", "sseq ver15.3", "record/note.tex; preview snapshot"),
    CatalogEntry("2sigma-dec23", "2sigma_Dec23.json", "2sigma Dec 23", "2sigma_i", "2025-12-23", "record-note", "historical", "sseq ver15.3", "record/note.tex; intermediate 2sigma stage"),
    CatalogEntry("2sigma-dec30", "2sigma_Dec30.json", "2sigma corrected Dec 30", "2sigma_i", "2025-12-30 corrected", "formal-notes", "current", "sseq ver15.3", "formal_notes.tex:275-674; labels prop:d3 u2sig through prop:d9"),
    CatalogEntry("3sigma-feb10", "3sigma_Feb10.json", "3sigma Feb 10", "3sigma_i", "2026-02-10 base", "formal-notes", "historical", "sseq ver15.3", "formal_notes.tex:675-792; pre-higher-differential snapshot"),
    CatalogEntry("3sigma-public", "3sigma_public.json", "3sigma public", "3sigma_i", "2026-02-10 public", "formal-notes", "current", "sseq ver15.3", "formal_notes.tex:675-792; prop:d3 u3sig and prop:3sig-d9-euler"),
    CatalogEntry("3sigma-vor-einf", "3sigma_vorEinf_Feb10.json", "3sigma before Einfinity", "3sigma_i", "2026-02-10 completed draft", "formal-notes", "review", "sseq ver15.3", "formal_notes.tex:782-791 has an empty proof for prop:3sig-d11-res"),
    CatalogEntry("mixed-feb10", "2sigma i sigma j_Feb10.json", "Mixed 2sigma_i+sigma_j Feb 10", "2sigma_i+sigma_j", "2026-02-10", "record-note", "historical", "sseq ver15.3", "record/note.tex; historical mixed computation"),
    CatalogEntry("mixed-conflict-feb12", "2sigma i sigma j_conflict_Feb12.json", "Mixed conflict Feb 12", "2sigma_i+sigma_j", "2026-02-12 conflict", "record-note", "conflict", "sseq ver15.3", "formal_notes.tex:925-933 warns C3 does not identify the two mixed sectors"),
    CatalogEntry("mixed-5-3", "5.3.json", "Mixed section 5.3", "mixed", "legacy section 5.3", "record-note", "historical", "sseq ver15.3", "record/note.tex; generator/connection pages default to E2"),
    CatalogEntry("mixed-e5-prop64", "E5, prop6.4.json", "Mixed E5 proposition 6.4", "sigma_i+2sigma_j", "2026-05-02 proposition 6.4", "record-note", "review", "sseq ver15.3", "record/note.tex:1350 says only through 6.4 checked; formal_notes.tex contains red [TBD] dependencies"),
    CatalogEntry("mixed-e5-2", "E5_2.json", "Mixed E5 second draft", "sigma_i+2sigma_j", "2026-05-06", "record-note", "rejected", "sseq ver15.3", "record/note.tex:1350 says sections 6.5-6.6 do not hold"),
    CatalogEntry("mixed-new-d9d11-base", "spectral_sequence_project_newd9d11.json", "Mixed new d9/d11 base", "sigma_i+2sigma_j", "2026-06-10 base", "formal-notes", "review", "sseq ver15.3", "formal_notes.tex:795-924; several proofs depend on red [TBD] claims"),
    CatalogEntry("mixed-new-d9d11", "6.9_new_d9d11.json", "Mixed section 6.9 new d9/d11", "sigma_i+2sigma_j", "2026-06-10 section 6.9", "formal-notes", "review", "sseq ver15.3", "formal_notes.tex:795-924; unresolved red [TBD] dependencies"),
    CatalogEntry("mixed-july20", "sigma i+2sigma j July20.json", "sigma_i+2sigma_j July 20", "sigma_i+2sigma_j", "2026-07-20/24 latest canvas", "formal-notes", "review", "sseq ver15.3", "formal_notes.tex:795-924; current draft but red [TBD] dependencies remain"),
)


def _source_path(entry: CatalogEntry) -> Path:
    path = SOURCE_DIRECTORY / entry.filename
    if not path.is_file():
        raise FileNotFoundError(f"Catalog source is unavailable: {entry.filename}")
    return path


def _raw_canvas(entry: CatalogEntry) -> dict[str, Any]:
    raw = json.loads(_source_path(entry).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ProjectImportValidationError(f"{entry.filename} must contain a JSON object.")
    return raw


def _statistics(raw: dict[str, Any]) -> dict[str, Any]:
    generators = raw.get("generators")
    connections = raw.get("connections")
    rules = raw.get("periodicityRules", [])
    if not isinstance(generators, list) or not isinstance(connections, list) or not isinstance(rules, list):
        raise ProjectImportValidationError("Catalog generators, connections, and periodicityRules must be arrays.")
    generator_ids = {str(item.get("id", "")) for item in generators if isinstance(item, dict)}
    dangling = sum(
        not isinstance(item, dict) or str(item.get("fromId", "")) not in generator_ids or str(item.get("toId", "")) not in generator_ids
        for item in connections
    )
    return {
        "generators": len(generators),
        "connections": len(connections),
        "relations": sum(isinstance(item, dict) and item.get("type") == "relation" for item in connections),
        "differentials": sum(isinstance(item, dict) and item.get("type") == "differential" for item in connections),
        "periodicity_rules": len(rules),
        "dangling_connections": dangling,
        "pages": sorted({
            _legacy_integer(item.get("page"), "catalog page", default=2)
            for item in [*generators, *connections] if isinstance(item, dict)
        }),
    }


def manifest() -> list[dict[str, Any]]:
    return [{**asdict(entry), "statistics": _statistics(_raw_canvas(entry))} for entry in CATALOG]


def entry_by_id(entry_id: str) -> CatalogEntry:
    entry = next((item for item in CATALOG if item.id == entry_id), None)
    if entry is None:
        raise KeyError(entry_id)
    return entry


def _mapped_id(entry: CatalogEntry, kind: str, legacy_id: str) -> str:
    return f"catalog:{entry.id}:{kind}:{legacy_id}"


def catalog_workspace(entry_id: str) -> Workspace:
    """Map one legacy canvas without changing the saved Studio project."""

    entry = entry_by_id(entry_id)
    raw = _raw_canvas(entry)
    stats = _statistics(raw)
    if stats["dangling_connections"]:
        raise ProjectImportValidationError(f"{entry.filename} has dangling connections.")

    classes: list[ClassNode] = []
    class_ids: dict[str, str] = {}
    for index, item in enumerate(raw["generators"]):
        if not isinstance(item, dict):
            raise ProjectImportValidationError(f"generators[{index}] must be an object.")
        legacy_id = _legacy_text(item.get("id"), f"generators[{index}].id")
        if legacy_id in class_ids:
            raise ProjectImportValidationError(f"Duplicate generator id {legacy_id!r}.")
        class_id = _mapped_id(entry, "class", legacy_id)
        class_ids[legacy_id] = class_id
        label = _legacy_text(item.get("name"), f"generators[{index}].name", fallback=f"unnamed_{index + 1}")
        page = _legacy_integer(item.get("page"), f"generators[{index}].page", default=2)
        classes.append(ClassNode(
            id=class_id,
            label=label,
            expression=label,
            grade=Grade(
                stem=_legacy_integer(item.get("p"), f"generators[{index}].p"),
                filtration=_legacy_integer(item.get("q"), f"generators[{index}].q"),
            ),
            page=page,
            notes=f"Read-only catalog point from {entry.filename}; legacy id {legacy_id}.",
            style={
                "module_pattern": "dot",
                "legacy_catalog": True,
                "legacy_original_id": legacy_id,
                "legacy_x_offset": _legacy_offset(item.get("xOffset", 0), f"generators[{index}].xOffset"),
                "legacy_y_offset": _legacy_offset(item.get("yOffset", 0), f"generators[{index}].yOffset"),
                "legacy_is_base_generator": bool(item.get("isBaseGenerator", True)),
            },
            coefficient_context_id="legacy-v153-unclassified",
            convention_id="legacy-v153-pq",
        ))

    differentials: list[Differential] = []
    propositions: list[Proposition] = []
    nodes_by_id = {item.id: item for item in classes}
    fates: dict[str, ClassFate] = {item.id: ClassFate(class_id=item.id, appears_from_page=item.page) for item in classes}
    seen_connections: set[str] = set()
    for index, item in enumerate(raw["connections"]):
        if not isinstance(item, dict):
            raise ProjectImportValidationError(f"connections[{index}] must be an object.")
        legacy_id = _legacy_text(item.get("id"), f"connections[{index}].id")
        if legacy_id in seen_connections:
            raise ProjectImportValidationError(f"Duplicate connection id {legacy_id!r}.")
        seen_connections.add(legacy_id)
        kind = _legacy_text(item.get("type"), f"connections[{index}].type").lower()
        if kind not in {"relation", "differential"}:
            raise ProjectImportValidationError(f"Unknown connection type {kind!r}.")
        source_id = class_ids[_legacy_text(item.get("fromId"), f"connections[{index}].fromId")]
        target_id = class_ids[_legacy_text(item.get("toId"), f"connections[{index}].toId")]
        page = _legacy_integer(item.get("page"), f"connections[{index}].page", default=2)
        periodic = item.get("isPeriodic", False)
        if not isinstance(periodic, bool):
            raise ProjectImportValidationError(f"connections[{index}].isPeriodic must be boolean.")
        proposition_id = _mapped_id(entry, "claim", legacy_id)
        conclusion = {
            "source_id": source_id,
            "target_id": target_id,
            "page": page,
            "legacy_connection_id": legacy_id,
            "legacy_is_periodic": periodic,
            "catalog_entry_id": entry.id,
        }
        source = nodes_by_id[source_id]
        evidence = EVIDENCE_BY_SECTOR.get(entry.sector, {}).get((page, source.grade.stem, source.grade.filtration))
        evidence_label, evidence_formula, evidence_status = evidence or ("", "", "review")
        claim_status = "rejected" if entry.status == "rejected" else (
            "reviewed" if entry.status == "current" and evidence_status == "reviewed" else "candidate"
        )
        if evidence_label:
            conclusion.update({
                "formal_notes_label": evidence_label,
                "formal_notes_formula": evidence_formula,
                "evidence_status": evidence_status,
            })
        propositions.append(Proposition(
            id=proposition_id,
            kind=kind,
            statement=f"Legacy {kind} in {entry.title} on E{page}.",
            status=claim_status,
            conclusion=conclusion,
            rule="LegacyCatalog",
            confidence=0.0,
            notes=(
                f"Exact source coordinate linked to {evidence_label}; formula: {evidence_formula}."
                if evidence_label else "Visual record only; no theorem status is inferred from the JSON."
            ),
            source_ref=f"{entry.filename}; {entry.evidence_ref}{f'; {evidence_label}' if evidence_label else ''}",
            source_refs=[entry.filename, entry.evidence_ref, *([evidence_label] if evidence_label else [])],
            convention_id="legacy-v153-pq",
        ))
        if kind == "differential":
            differential_id = _mapped_id(entry, "differential", legacy_id)
            differentials.append(Differential(
                id=differential_id,
                source_id=source_id,
                target_id=target_id,
                page=page,
                status=claim_status,
                label=f"d_{page} (legacy catalog)",
                proposition_id=proposition_id,
                period_notes="Legacy isPeriodic flag retained in the linked claim only.",
                unperiodic_reason="No source-backed certificate is inferred from a visual JSON.",
            ))
            for class_id, conclusion_name in ((source_id, "supports_differential"), (target_id, "is_hit")):
                fate = fates[class_id]
                known_page = fate.first_hfpss_death and int(fate.first_hfpss_death["page"])
                if known_page is None or page < known_page:
                    fate.first_hfpss_death = {"page": page, "differential_id": differential_id, "status": "legacy-visual"}
                    fate.last_hfpss_live_page = page
                    fate.conclusion = conclusion_name
                    fate.conclusion_page = page
                    fate.justification_ids = [proposition_id]

    rules = []
    for index, item in enumerate(raw.get("periodicityRules", [])):
        if not isinstance(item, dict):
            raise ProjectImportValidationError(f"periodicityRules[{index}] must be an object.")
        rules.append({
            "id": _legacy_text(item.get("id"), f"periodicityRules[{index}].id"),
            "name": _legacy_text(item.get("name"), f"periodicityRules[{index}].name", fallback=f"period {index + 1}"),
            "p": _legacy_integer(item.get("p"), f"periodicityRules[{index}].p"),
            "q": _legacy_integer(item.get("q"), f"periodicityRules[{index}].q"),
            "status": "manual-unverified",
        })

    max_page = max(stats["pages"], default=2)
    return Workspace(
        id=f"catalog:{entry.id}",
        name=entry.title,
        grading_label=entry.sector,
        page=2,
        classes=classes,
        differentials=differentials,
        fates=list(fates.values()),
        propositions=propositions,
        summary=f"{entry.status.upper()} · {entry.filename} · {entry.evidence_ref}",
        settings={
            "vanishing_line": 0,
            "page_limit": max(25, max_page),
            "known_page_max": max_page,
            "grid": {
                "stem_min": min(item.grade.stem for item in classes),
                "stem_max": max(item.grade.stem for item in classes),
                "filtration_min": min(item.grade.filtration for item in classes),
                "filtration_max": max(item.grade.filtration for item in classes),
            },
            "rendering": {"buffer_cells": 6, "base_cell": 28, "periodicity": []},
            "read_only_catalog": True,
            "catalog_entry": {**asdict(entry), "statistics": stats, "periodicity_rules": rules},
        },
    )


def catalog_workspace_dict(entry_id: str) -> dict[str, Any]:
    return deepcopy(asdict(catalog_workspace(entry_id)))
