from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from threading import Lock
from dataclasses import asdict

from flask import Flask, jsonify, render_template, request

from domain.fate import class_is_live_on_page, sync_workspace_fates, workspace_sequence_kind
from domain.actions import c3_transport_preview
from domain.candidate_enumeration import (
    CandidateEnumerationError,
    enumerate_comparison_transport_candidates,
    enumerate_differential_candidates,
)
from domain.e2_presentation import (
    PresentationValidationError,
    materialize_explicit_presentation,
    normal_form_from_input,
    presentation_from_input,
    presentation_to_dict,
)
from domain.migrations import migrate_project
from domain.logic_graph import build_logic_graph
from domain.history import history_status, record_edit, redo_edit, undo_edit
from domain.manual_periodicity import (
    ManualPeriodicityError,
    add_manual_rule,
    delete_manual_rule,
    list_manual_rules,
    materialize_batch_preview,
    materialize_manual_periodicity,
    prepare_manual_rule,
    preview_all_rules_to_box,
    preview_differentials_only,
    preview_manual_periodicity,
)
from domain.models import ClassNode, Differential, Grade, Project, Proposition, Workspace, new_id, project_from_dict, project_to_dict
from domain.project_io import ProjectImportValidationError, import_digest, prepare_project_import
from domain.periods import LEGACY_DIFFERENTIAL_PERIODS
from domain.periodicity import (
    PeriodicityOperationError,
    materialize_periodic_translate,
    periodicity_rule_to_dict,
    preview_periodic_translate,
)
from domain.products import create_cross_graded_product, preview_cross_graded_product, product_to_dict
from domain.proof_engine import comparison_suggestions, leibniz_suggestions, vanishing_line_suggestions
from domain.seed import demo_project
from domain.tex_renderer import render_article_tex, render_chart_tex

ROOT = Path(__file__).resolve().parent
SEED_DATA_PATH = ROOT / "data" / "project.json"


def _project_data_path() -> tuple[Path, str]:
    """Choose a writable project file for local and Vercel execution.

    Vercel Functions ship the repository as a read-only deployment bundle.  A
    serverless instance therefore starts from the checked-in seed in ``/tmp``;
    edits remain available while that instance is warm, but are intentionally
    not presented as durable shared storage.
    """
    configured_path = os.environ.get("HFPSS_DATA_PATH")
    if configured_path:
        return Path(configured_path).expanduser(), "configured"
    if os.environ.get("VERCEL"):
        transient_path = Path(tempfile.gettempdir()) / "hfpss-studio" / "project.json"
        if not transient_path.exists():
            transient_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SEED_DATA_PATH, transient_path)
        return transient_path, "vercel-ephemeral"
    return SEED_DATA_PATH, "local"


DATA_PATH, PROJECT_STORAGE_MODE = _project_data_path()
LOCK = Lock()
# The Vercel build copies these local Flask assets to public/static for its
# CDN.  Keeping Flask's normal static folder preserves run-latest.ps1 exactly.
app = Flask(__name__)
APP_VERSION = "2026.07.22-manual-periodicity"

# Compatibility map for project.json files created before periodicity was
# attached to individual differential families.  It is intentionally limited
# to periods stated in the local notes and only fills missing values.
def migrate_legacy_periods(project: Project) -> Project:
    """Fill documented family periods in pre-family-period project data."""
    for workspace in project.workspaces:
        for differential in workspace.differentials:
            period = LEGACY_DIFFERENTIAL_PERIODS.get(differential.id)
            if period and not differential.period_stem and not differential.period_filtration:
                differential.period_stem, differential.period_filtration = period
    return migrate_project(project)


def load_project() -> Project:
    if not DATA_PATH.exists():
        return migrate_legacy_periods(demo_project())
    return migrate_legacy_periods(project_from_dict(json.loads(DATA_PATH.read_text(encoding="utf-8"))))


def save_project(project: Project) -> None:
    DATA_PATH.parent.mkdir(exist_ok=True)
    project.revision += 1
    temporary_path = DATA_PATH.with_name(f"{DATA_PATH.name}.tmp")
    try:
        temporary_path.write_text(
            json.dumps(project_to_dict(project), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # ``replace`` is atomic within the data directory, so a completed
        # checkpoint cannot be paired with a half-written replacement file.
        temporary_path.replace(DATA_PATH)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def history_key() -> str:
    return str(DATA_PATH.resolve())


def checkpoint(project: Project, label: str) -> None:
    record_edit(history_key(), project, label)


def find_workspace(project: Project, workspace_id: str) -> Workspace:
    workspace = next((item for item in project.workspaces if item.id == workspace_id), None)
    if not workspace:
        raise KeyError(f"Unknown workspace: {workspace_id}")
    return workspace


def body_integer(body: dict, key: str, default: int) -> int:
    """Parse a JSON integer while preserving an explicit numeric zero."""
    value = body[key] if key in body else default
    if isinstance(value, bool):
        raise ValueError(f"{key} must be an integer.")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"{key} must be an integer.")
    return int(value)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/project")
def get_project():
    return jsonify(project_to_dict(load_project()))


@app.get("/api/project/export")
def export_project():
    """Download the complete Studio project JSON, not a chart-only snapshot."""
    project = load_project()
    response = app.response_class(
        json.dumps(project_to_dict(project), ensure_ascii=False, indent=2),
        mimetype="application/json",
    )
    response.headers["Content-Disposition"] = (
        f'attachment; filename="hfpss-studio-project-v{project.schema_version}-r{project.revision}.json"'
    )
    return response


def _import_status_policy() -> str:
    return (
        "Imported proposition and differential statuses are preserved only as cited assertions from the file. "
        "This endpoint neither proves nor independently verifies mathematical claims; derived fate/event caches are rebuilt."
    )


@app.post("/api/project/import/preview")
def preview_project_import():
    """Parse/migrate/validate a full replacement project without writing it."""
    try:
        raw = request.get_json(force=True)
        candidate, metadata = prepare_project_import(raw)
        current = load_project()
        return jsonify({
            "valid": True,
            "preview_sha256": import_digest(candidate),
            "current_revision": current.revision,
            "would_revision": current.revision + 1,
            "project": project_to_dict(candidate),
            "import": metadata,
            "mathematical_status_policy": _import_status_policy(),
        })
    except ProjectImportValidationError as error:
        return jsonify({"valid": False, "error": str(error)}), 422
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        return jsonify({"valid": False, "error": f"Malformed import request: {error}"}), 422


@app.post("/api/project/import/apply")
def apply_project_import():
    """Atomically replace a project only after its exact preview was reviewed."""
    try:
        body = request.get_json(force=True)
        if not isinstance(body, dict) or set(("project", "preview_sha256", "expected_revision")) - set(body):
            raise ProjectImportValidationError(
                "Apply requires an object with project, preview_sha256, and expected_revision from a successful preview."
            )
        if not isinstance(body["preview_sha256"], str) or not body["preview_sha256"]:
            raise ProjectImportValidationError("preview_sha256 must be the nonempty value returned by preview.")
        if isinstance(body["expected_revision"], bool) or not isinstance(body["expected_revision"], int):
            raise ProjectImportValidationError("expected_revision must be the integer current_revision returned by preview.")
        with LOCK:
            current = load_project()
            if body["expected_revision"] != current.revision:
                return jsonify({
                    "error": "The project changed after preview; preview the import again before applying it.",
                    "current_revision": current.revision,
                }), 409
            candidate, metadata = prepare_project_import(body["project"])
            if body["preview_sha256"] != import_digest(candidate):
                return jsonify({
                    "error": "The proposed project differs from the reviewed preview; preview it again before applying.",
                    "current_revision": current.revision,
                }), 409
            # Project revision records local replacement history, not a number
            # supplied by an external file.  The old state remains undoable.
            candidate.revision = current.revision
            checkpoint(current, "Import and replace validated project JSON")
            save_project(candidate)
        return jsonify({
            "project": project_to_dict(candidate),
            "revision": candidate.revision,
            "import": metadata,
            "mathematical_status_policy": _import_status_policy(),
            **history_status(history_key()),
        }), 201
    except ProjectImportValidationError as error:
        return jsonify({"error": str(error)}), 422
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        return jsonify({"error": f"Malformed import request: {error}"}), 422


@app.get("/api/health")
def health():
    project = load_project()
    return jsonify({
        "application": "HFPSS Studio",
        "version": APP_VERSION,
        "revision": project.revision,
        "storage": PROJECT_STORAGE_MODE,
    })


@app.get("/api/history")
def get_history_status():
    return jsonify(history_status(history_key()))


@app.post("/api/history/undo")
def undo_history():
    with LOCK:
        current = load_project()
        result = undo_edit(history_key(), current)
        if result is None:
            return jsonify({"error": "Nothing to undo.", **history_status(history_key())}), 409
        restored, label = result
        restored = migrate_legacy_periods(restored)
        save_project(restored)
    return jsonify({"project": project_to_dict(restored), "action": label, **history_status(history_key())})


@app.post("/api/history/redo")
def redo_history():
    with LOCK:
        current = load_project()
        result = redo_edit(history_key(), current)
        if result is None:
            return jsonify({"error": "Nothing to redo.", **history_status(history_key())}), 409
        restored, label = result
        restored = migrate_legacy_periods(restored)
        save_project(restored)
    return jsonify({"project": project_to_dict(restored), "action": label, **history_status(history_key())})


@app.get("/api/v2/grading-sectors")
def grading_sectors():
    project = load_project()
    return jsonify({"schema_version": project.schema_version, "sectors": [asdict(item) for item in project.grading_sectors]})


@app.get("/api/v2/logic-graph")
def logic_graph():
    return jsonify(build_logic_graph(load_project()))


@app.get("/api/v2/period-families")
def period_families():
    project = load_project()
    return jsonify({"period_families": [asdict(item) for item in project.period_families]})


@app.get("/api/v2/periodicity-rules")
def periodicity_rules():
    """Return source-scoped periodicity operations, not render-only repeats."""
    project = load_project()
    return jsonify({"periodicity_rules": [periodicity_rule_to_dict(item) for item in project.periodicity_rules]})


@app.get("/api/v2/render/workspaces/<workspace_id>/<kind>.tex")
def render_tex(workspace_id: str, kind: str):
    """Return a deterministic, provenance-preserving TeX snapshot.

    Supported kinds are ``chart`` (a standalone custom-TikZ chart) and
    ``article`` (a compact review-safe report containing that chart).
    """
    project = load_project()
    workspace = find_workspace(project, workspace_id)
    try:
        page = int(request.args.get("page", workspace.page))
    except ValueError:
        return jsonify({"error": "page must be an integer."}), 400
    if page < 2:
        return jsonify({"error": "page must be at least 2."}), 400
    if kind == "chart":
        tex = render_chart_tex(project, workspace, page)
    elif kind == "article":
        tex = render_article_tex(project, workspace, page)
    else:
        return jsonify({"error": "kind must be chart or article."}), 404
    response = app.response_class(tex, mimetype="application/x-tex")
    response.headers["Content-Disposition"] = f'attachment; filename="{workspace.id}-E{page}-{kind}.tex"'
    return response


@app.get("/api/v2/workspaces/<workspace_id>/fates")
def workspace_fates(workspace_id: str):
    project = load_project()
    workspace = find_workspace(project, workspace_id)
    return jsonify({
        "workspace_id": workspace.id,
        "fates": [asdict(item) for item in workspace.fates],
        "events": [asdict(item) for item in workspace.differential_events],
    })


@app.get("/api/v2/e2-presentations")
def list_e2_presentations():
    """List explicit finite presentations already materialized in this project."""
    project = load_project()
    return jsonify({
        "presentations": [presentation_to_dict(item) for item in project.e2_presentations],
        "limitation": (
            "Presentations are explicit user input rewritten over formal integers only; "
            "this endpoint does not compute group cohomology or discover differentials."
        ),
    })


@app.post("/api/v2/e2-presentations/preview")
def preview_e2_presentation():
    """Validate (and optionally evaluate) an unpersisted explicit presentation."""
    try:
        body = request.get_json(force=True)
        presentation = presentation_from_input(body)
        find_workspace(load_project(), presentation.workspace_id)
        output = {"presentation": presentation_to_dict(presentation), "persisted": False}
        if "polynomial" in body:
            output["evaluation"] = normal_form_from_input(presentation, body["polynomial"])
        return jsonify(output)
    except (KeyError, TypeError, ValueError, PresentationValidationError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/v2/e2-presentations")
def materialize_e2_presentation():
    """Store only the explicitly supplied generator dots and relation claims."""
    try:
        body = request.get_json(force=True)
        with LOCK:
            project = load_project()
            presentation = presentation_from_input(body)
            workspace = find_workspace(project, presentation.workspace_id)
            checkpoint(project, f"Materialize explicit E2 presentation {presentation.name}")
            result = materialize_explicit_presentation(project, presentation)
            sync_workspace_fates(workspace)
            save_project(project)
        return jsonify({
            "presentation": presentation_to_dict(presentation),
            "materialization": result,
            "revision": project.revision,
            "limitation": (
                "Only explicit generators and cited relations were stored. No monomial dots, group-cohomology "
                "calculation, permanent-cycle claim, or differential was inferred."
            ),
        }), 201
    except (KeyError, TypeError, ValueError, PresentationValidationError) as error:
        return jsonify({"error": str(error)}), 400


@app.get("/api/v2/products")
def cross_graded_products():
    project = load_project()
    return jsonify({"products": [product_to_dict(item) for item in project.cross_graded_products]})


def _product_arguments(body: dict) -> dict:
    return {
        "left_sector_id": body["left_sector_id"],
        "left_class_id": body["left_class_id"],
        "right_sector_id": body["right_sector_id"],
        "right_class_id": body["right_class_id"],
        "page": int(body.get("page", 2)),
    }


@app.post("/api/v2/products/preview")
def preview_product():
    try:
        project = load_project()
        preview = preview_cross_graded_product(project, **_product_arguments(request.get_json(force=True)))
    except (KeyError, TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"preview": preview})


@app.post("/api/v2/products")
def create_product():
    try:
        with LOCK:
            project = load_project()
            arguments = _product_arguments(request.get_json(force=True))
            preview_cross_graded_product(project, **arguments)
            checkpoint(project, "Add cross-graded product")
            product = create_cross_graded_product(project, **arguments)
            save_project(project)
    except (KeyError, TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"product": product_to_dict(product), "revision": project.revision}), 201


@app.get("/api/v2/c3-actions")
def c3_actions():
    project = load_project()
    return jsonify({"actions": [asdict(item) for item in project.c3_actions]})


@app.get("/api/v2/c3-actions/omega/orbit/<sector_id>")
def c3_orbit_preview(sector_id: str):
    try:
        return jsonify(c3_transport_preview(load_project(), sector_id))
    except ValueError as error:
        return jsonify({"error": str(error)}), 404


@app.get("/api/proof-tree")
def project_proof_tree():
    """Return the proposition graph across all grading workspaces."""
    project = load_project()
    nodes = [
        {
            "id": prop.id,
            "label": prop.statement,
            "status": prop.status,
            "rule": prop.rule,
            "workspace_id": workspace.id,
            "workspace_name": workspace.name,
            "source_ref": prop.source_ref,
        }
        for workspace in project.workspaces
        for prop in workspace.propositions
    ]
    edges = [
        {"source": premise, "target": prop.id}
        for workspace in project.workspaces
        for prop in workspace.propositions
        for premise in prop.premise_ids
    ]
    return jsonify({"nodes": nodes, "edges": edges})


@app.post("/api/project/reset-demo")
def reset_demo():
    with LOCK:
        current = load_project()
        checkpoint(current, "Reset demo project")
        project = migrate_legacy_periods(demo_project())
        save_project(project)
    return jsonify(project_to_dict(project))


@app.post("/api/workspaces")
def create_workspace():
    body = request.get_json(force=True)
    with LOCK:
        project = load_project()
        workspace = Workspace(id=new_id("ws"), name=body.get("name", "Untitled workspace"), group=body.get("group", "Q8"), theory=body.get("theory", "E_2"), characteristic=int(body.get("characteristic", 2)), grading_label=body.get("grading_label", "integer"), spectral_sequence=body.get("spectral_sequence", "hfpss"))
        checkpoint(project, f"Add workspace {workspace.name}")
        project.workspaces.append(workspace)
        save_project(project)
    return jsonify({"workspace": workspace.__dict__, "revision": project.revision}), 201


@app.patch("/api/workspaces/<workspace_id>/settings")
def update_workspace_settings(workspace_id: str):
    """Persist safe display settings without exposing arbitrary workspace mutation."""
    body = request.get_json(force=True)
    with LOCK:
        project = load_project(); workspace = find_workspace(project, workspace_id)
        if "page_limit" in body:
            page_limit = int(body["page_limit"])
            if page_limit < 25 or page_limit > 500:
                return jsonify({"error": "page_limit must be between 25 and 500."}), 400
            checkpoint(project, f"Set {workspace.name} page limit to {page_limit}")
            workspace.settings["page_limit"] = page_limit
        save_project(project)
    return jsonify({"settings": workspace.settings, "revision": project.revision})


@app.post("/api/workspaces/<workspace_id>/classes")
def create_class(workspace_id: str):
    body = request.get_json(force=True)
    if not isinstance(body, dict):
        return jsonify({"error": "Class input must be a JSON object."}), 400
    label = str(body.get("label", "")).strip()
    if not label:
        return jsonify({"error": "A class label is required."}), 400
    try:
        stem = body_integer(body, "stem", 0)
        filtration = body_integer(body, "filtration", 0)
        period_stem = body_integer(body, "period_stem", 0)
        period_filtration = body_integer(body, "period_filtration", 0)
        page = body_integer(body, "page", 2)
    except (TypeError, ValueError):
        return jsonify({"error": "Stem, filtration, page, and periods must be integers."}), 400
    representation = body.get("representation", {})
    if not isinstance(representation, dict) or any(
        not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, int)
        for key, value in representation.items()
    ):
        return jsonify({"error": "Representation must map strings to integer coefficients."}), 400
    with LOCK:
        project = load_project(); workspace = find_workspace(project, workspace_id)
        if filtration < 0 and workspace_sequence_kind(workspace) != "tate":
            return jsonify({"error": "Negative filtration is available only in a TateSS workspace."}), 400
        if page < 2:
            return jsonify({"error": "A class must first appear on page E2 or later."}), 400
        node = ClassNode(
            id=new_id("class"),
            label=label,
            expression=str(body.get("expression", label)),
            grade=Grade(stem, filtration, representation),
            page=page if "page" in body else workspace.page,
            state=body.get("state", "unknown"),
            notes=body.get("notes", ""),
            period_stem=period_stem,
            period_filtration=period_filtration,
            coefficient_context_id=body.get("coefficient_context_id", "q8-witt-f4"),
            convention_id=body.get("convention_id", "q8-thesis-plotted-v1"),
            sector_id=body.get("sector_id"),
        )
        checkpoint(project, f"Add class {node.label}")
        workspace.classes.append(node); save_project(project)
    return jsonify({"class": asdict(node), "revision": project.revision}), 201


@app.patch("/api/workspaces/<workspace_id>/classes/<class_id>")
def update_class(workspace_id: str, class_id: str):
    """Rename a class without changing its grade or proof history."""
    body = request.get_json(force=True)
    label = str(body.get("label", "")).strip()
    if not label:
        return jsonify({"error": "A class label is required."}), 400
    with LOCK:
        project = load_project(); workspace = find_workspace(project, workspace_id)
        node = next((item for item in workspace.classes if item.id == class_id), None)
        if not node:
            return jsonify({"error": "Unknown class."}), 404
        checkpoint(project, f"Rename class {node.label} to {label}")
        node.label = label
        save_project(project)
    return jsonify({"class": asdict(node), "revision": project.revision})


@app.delete("/api/workspaces/<workspace_id>/classes/<class_id>")
def delete_class(workspace_id: str, class_id: str):
    """Archive a class without erasing its mathematical history."""
    with LOCK:
        project = load_project(); workspace = find_workspace(project, workspace_id)
        if not any(item.id == class_id for item in workspace.classes):
            return jsonify({"error": "Unknown class."}), 404
        node = next(item for item in workspace.classes if item.id == class_id)
        checkpoint(project, f"Archive class {node.label}")
        node.archived = True
        node.archived_reason = "Archived by a local user action. Historical claims are retained."
        workspace.propositions.append(Proposition(
            id=new_id("prop"),
            kind="tombstone",
            statement=f"Archive the chart display of {node.label} without deleting its proof history.",
            status="established",
            conclusion={"class_id": class_id, "archived": True},
            rule="UserArchive",
            source_ref="Local workspace edit",
            source_refs=["Local workspace edit"],
        ))
        sync_workspace_fates(workspace)
        save_project(project)
    return jsonify({"deleted": class_id, "revision": project.revision})


@app.post("/api/workspaces/<workspace_id>/clear-canvas")
def clear_workspace_canvas(workspace_id: str):
    """Archive every active dot in one workspace without deleting its history.

    The operation intentionally affects display/lifecycle state only.  It does
    not remove classes, arrows, propositions, provenance, or past events, and
    one checkpoint restores the entire pre-clear workspace through undo.
    """
    try:
        with LOCK:
            project = load_project()
            workspace = find_workspace(project, workspace_id)
            active_nodes = [node for node in workspace.classes if not node.archived]
            if not active_nodes:
                return jsonify({
                    "workspace_id": workspace.id,
                    "archived_count": 0,
                    "archived_class_ids": [],
                    "changed": False,
                    "revision": project.revision,
                    "message": "The workspace canvas is already empty; no records were changed.",
                    **history_status(history_key()),
                })

            label = f"Clear current canvas in {workspace.name} (archive {len(active_nodes)} classes)"
            checkpoint(project, label)
            reason = (
                "Archived by Clear current canvas. The class, its differential records, "
                "propositions, and provenance remain in the project and can be restored by undo."
            )
            for node in active_nodes:
                node.archived = True
                node.archived_reason = reason
            sync_workspace_fates(workspace)
            save_project(project)

        return jsonify({
            "workspace_id": workspace.id,
            "archived_count": len(active_nodes),
            "archived_class_ids": [node.id for node in active_nodes],
            "changed": True,
            "revision": project.revision,
            "message": "Active dots were archived; no mathematical records were physically deleted.",
            **history_status(history_key()),
        })
    except KeyError as error:
        return jsonify({"error": str(error)}), 404


@app.post("/api/workspaces/<workspace_id>/differentials")
def create_differential(workspace_id: str):
    body = request.get_json(force=True)
    with LOCK:
        project = load_project(); workspace = find_workspace(project, workspace_id)
        source_id, target_id, page = body["source_id"], body["target_id"], int(body.get("page", workspace.page))
        classes = {node.id: node for node in workspace.classes}
        if source_id not in classes or target_id not in classes:
            return jsonify({"error": "Both endpoints must be classes in this workspace."}), 400
        if page < 2:
            return jsonify({"error": "A differential page must be at least 2."}), 400
        source, target = classes[source_id], classes[target_id]
        if target.grade.stem != source.grade.stem - 1 or target.grade.filtration != source.grade.filtration + page:
            return jsonify({"error": f"Under q8-thesis-plotted-v1, d_{page} must shift (stem, filtration) by (-1, +{page})."}), 400
        if target.grade.representation != source.grade.representation:
            return jsonify({"error": "Under q8-thesis-plotted-v1, a differential must preserve the representation coordinate."}), 400
        if not class_is_live_on_page(workspace, source_id, page) or not class_is_live_on_page(workspace, target_id, page):
            return jsonify({"error": "Both endpoints must be live on the claimed page."}), 400
        status = body.get("status", "candidate")
        source_refs = body.get("source_refs", [])
        source_ref = body.get("source_ref", "")
        if status in {"derived", "reviewed", "established", "proven"} and not (source_ref or source_refs):
            return jsonify({"error": "An accepted differential requires a source locator."}), 400
        proposition = Proposition(
            id=new_id("prop"),
            kind="differential",
            statement=f"d_{page}({source.label}) = {target.label}",
            status=status,
            conclusion={"source_id": source_id, "target_id": target_id, "page": page},
            rule=body.get("rule", "manual"),
            confidence=float(body.get("confidence", 0.5)),
            notes=body.get("notes", ""),
            source_ref=source_ref,
            source_refs=source_refs or ([source_ref] if source_ref else []),
            hypotheses=body.get("hypotheses", []),
            verification_checks=["structure", "bidegree", "page-liveness", "evidence"],
        )
        differential = Differential(
            id=new_id("diff"),
            source_id=source_id,
            target_id=target_id,
            page=page,
            status=status,
            label=body.get("label", ""),
            period_stem=int(body.get("period_stem", 0)),
            period_filtration=int(body.get("period_filtration", 0)),
            proposition_id=proposition.id,
        )
        checkpoint(project, f"Add differential d_{page}({source.label}) = {target.label}")
        workspace.differentials.append(differential)
        workspace.propositions.append(proposition)
        sync_workspace_fates(workspace)
        save_project(project)
    return jsonify({"differential": differential.__dict__, "revision": project.revision}), 201


@app.post("/api/v2/workspaces/<workspace_id>/differential-candidates")
def differential_candidates(workspace_id: str):
    """Enumerate structural candidates without storing or accepting an arrow."""
    try:
        body = request.get_json(force=True)
        if not isinstance(body, dict):
            raise CandidateEnumerationError("The request body must be an object.")
        source_id = body.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            raise CandidateEnumerationError("source_id must be a nonempty string.")
        project = load_project()
        workspace = find_workspace(project, workspace_id)
        raw_page = body.get("page", workspace.page)
        if isinstance(raw_page, bool):
            raise CandidateEnumerationError("page must be an integer at least 2.")
        page = int(raw_page)
        candidates = enumerate_differential_candidates(workspace, source_id, page)
        comparison_candidates = []
        comparison_id = body.get("comparison_id")
        if comparison_id is not None:
            if not isinstance(comparison_id, str) or not comparison_id:
                raise CandidateEnumerationError("comparison_id must be a nonempty string when supplied.")
            comparison_candidates = enumerate_comparison_transport_candidates(
                project, workspace, source_id, page, comparison_id,
            )
        return jsonify({
            "workspace_id": workspace.id,
            "source_id": source_id,
            "page": page,
            "candidates": [asdict(item) for item in candidates],
            "comparison_candidates": [asdict(item) for item in comparison_candidates],
            "persisted": False,
            "limitation": (
                "These are bidegree/liveness-compatible review candidates only. The service never creates or "
                "accepts a differential from enumeration; comparison candidates also require map-hypothesis review."
            ),
        })
    except (KeyError, TypeError, ValueError, CandidateEnumerationError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/v2/workspaces/<workspace_id>/periodicity/preview")
def preview_periodicity_translate(workspace_id: str):
    """Preview one source-backed periodic copy without changing the project."""
    try:
        project = load_project()
        workspace = find_workspace(project, workspace_id)
        return jsonify(preview_periodic_translate(project, workspace, request.get_json(force=True)))
    except (KeyError, TypeError, ValueError, PeriodicityOperationError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/v2/workspaces/<workspace_id>/periodicity/materialize")
def materialize_periodicity_translate(workspace_id: str):
    """Persist exactly the periodic class/differential records approved by the caller."""
    try:
        body = request.get_json(force=True)
        with LOCK:
            project = load_project()
            workspace = find_workspace(project, workspace_id)
            checkpoint(project, "Materialize source-backed periodic translate")
            result = materialize_periodic_translate(project, workspace, body)
            sync_workspace_fates(workspace)
            save_project(project)
        return jsonify({**result, "persisted": True, "revision": project.revision}), 201
    except (KeyError, TypeError, ValueError, PeriodicityOperationError) as error:
        return jsonify({"error": str(error)}), 400


@app.get("/api/v2/workspaces/<workspace_id>/manual-periodicities")
def list_manual_periodicities(workspace_id: str):
    """List persisted manual patterns without implying that they are theorems."""
    project = load_project()
    find_workspace(project, workspace_id)
    return jsonify({
        "manual_periodicities": [
            asdict(item) for item in project.manual_periodicities if item.workspace_id == workspace_id
        ],
        "limitation": (
            "Manual patterns are user-entered, manual-unverified records. They neither prove periodicity nor "
            "authorize automatic propagation or differential acceptance."
        ),
    })


@app.post("/api/v2/workspaces/<workspace_id>/manual-periodicity/preview")
def preview_manual_periodicity_operation(workspace_id: str):
    """Validate explicit manual copies without changing the project."""
    try:
        project = load_project()
        workspace = find_workspace(project, workspace_id)
        return jsonify(preview_manual_periodicity(workspace, request.get_json(force=True)))
    except (KeyError, TypeError, ValueError, ManualPeriodicityError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/v2/workspaces/<workspace_id>/manual-periodicity/materialize")
def materialize_manual_periodicity_operation(workspace_id: str):
    """Persist exact user-entered candidate copies in one undoable transaction."""
    try:
        body = request.get_json(force=True)
        with LOCK:
            project = load_project()
            workspace = find_workspace(project, workspace_id)
            preview = preview_manual_periodicity(workspace, body)
            if preview["conflicts"]:
                raise ManualPeriodicityError("Resolve preview conflicts before materializing manual drawing copies.")
            changing = any(item["action"] == "create" for item in preview["cycle_copies"] + preview["differential_copies"])
            if not changing:
                return jsonify({
                    **preview,
                    "persisted": True,
                    "changed": False,
                    "revision": project.revision,
                    **history_status(history_key()),
                })
            checkpoint(project, "Materialize manual-unverified periodicity copies")
            result = materialize_manual_periodicity(project, workspace, body)
            sync_workspace_fates(workspace)
            save_project(project)
        return jsonify({
            **result,
            "persisted": True,
            "revision": project.revision,
            **history_status(history_key()),
        }), 201
    except (KeyError, TypeError, ValueError, ManualPeriodicityError) as error:
        return jsonify({"error": str(error)}), 400


@app.get("/api/v2/workspaces/<workspace_id>/drawing-periodicity/rules")
def get_drawing_periodicity_rules(workspace_id: str):
    try:
        project = load_project()
        workspace = find_workspace(project, workspace_id)
        return jsonify({"rules": list_manual_rules(project, workspace), "status": "manual-unverified"})
    except KeyError as error:
        return jsonify({"error": str(error)}), 404


@app.post("/api/v2/workspaces/<workspace_id>/drawing-periodicity/rules")
def create_drawing_periodicity_rule(workspace_id: str):
    try:
        with LOCK:
            project = load_project()
            workspace = find_workspace(project, workspace_id)
            body = request.get_json(force=True)
            prepared = prepare_manual_rule(project, workspace, body)
            checkpoint(project, f"Add manual periodicity rule {prepared.name}")
            rule = add_manual_rule(project, workspace, body, prepared_rule=prepared)
            save_project(project)
        return jsonify({"rule": rule, "revision": project.revision, **history_status(history_key())}), 201
    except (KeyError, TypeError, ValueError, ManualPeriodicityError) as error:
        return jsonify({"error": str(error)}), 400


@app.delete("/api/v2/workspaces/<workspace_id>/drawing-periodicity/rules/<rule_id>")
def remove_drawing_periodicity_rule(workspace_id: str, rule_id: str):
    try:
        with LOCK:
            project = load_project()
            workspace = find_workspace(project, workspace_id)
            rule = next((item for item in project.manual_periodicity_rules if (
                item.id == rule_id and item.workspace_id == workspace.id
            )), None)
            if rule is None:
                return jsonify({"error": "Unknown manual periodicity rule."}), 404
            if rule.archived:
                return jsonify({
                    "deleted": {"id": rule.id, "archived": True}, "changed": False,
                    "revision": project.revision, **history_status(history_key()),
                })
            checkpoint(project, f"Delete manual periodicity rule {rule.name}")
            removed = delete_manual_rule(project, workspace, rule_id)
            save_project(project)
        return jsonify({"deleted": removed, "revision": project.revision, **history_status(history_key())})
    except (KeyError, TypeError, ValueError, ManualPeriodicityError) as error:
        return jsonify({"error": str(error)}), 400


def _drawing_batch_response(workspace_id: str, mode: str, apply: bool):
    body = request.get_json(force=True)
    preview_function = preview_all_rules_to_box if mode == "all-rules-box" else preview_differentials_only
    try:
        if not apply:
            project = load_project()
            workspace = find_workspace(project, workspace_id)
            return jsonify(preview_function(project, workspace, body))
        with LOCK:
            project = load_project()
            workspace = find_workspace(project, workspace_id)
            preview = preview_function(project, workspace, body)
            summary = preview["summary"]
            if preview["conflicts"]:
                raise ManualPeriodicityError("Resolve preview conflicts before applying manual drawing periodicity.")
            changing = bool(
                summary["cycles_to_create"]
                or summary["differentials_to_create"]
                or summary["relations_to_create"]
            )
            if not changing:
                return jsonify({**preview, "changed": False, "revision": project.revision, **history_status(history_key())})
            label = "Apply all manual periodicity rules to box" if mode == "all-rules-box" else "Apply manual periodicity to differentials only"
            checkpoint(project, label)
            result = materialize_batch_preview(project, workspace, preview)
            sync_workspace_fates(workspace)
            save_project(project)
        return jsonify({**result, "preview_summary": summary, "revision": project.revision, **history_status(history_key())}), 201
    except (KeyError, TypeError, ValueError, ManualPeriodicityError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/v2/workspaces/<workspace_id>/drawing-periodicity/box/preview")
def preview_drawing_periodicity_box(workspace_id: str):
    return _drawing_batch_response(workspace_id, "all-rules-box", False)


@app.post("/api/v2/workspaces/<workspace_id>/drawing-periodicity/box/apply")
def apply_drawing_periodicity_box(workspace_id: str):
    return _drawing_batch_response(workspace_id, "all-rules-box", True)


@app.post("/api/v2/workspaces/<workspace_id>/drawing-periodicity/differentials/preview")
def preview_drawing_periodicity_differentials(workspace_id: str):
    return _drawing_batch_response(workspace_id, "differentials-only", False)


@app.post("/api/v2/workspaces/<workspace_id>/drawing-periodicity/differentials/apply")
def apply_drawing_periodicity_differentials(workspace_id: str):
    return _drawing_batch_response(workspace_id, "differentials-only", True)


@app.post("/api/workspaces/<workspace_id>/suggestions")
def suggest(workspace_id: str):
    body = request.get_json(silent=True) or {}
    project = load_project(); workspace = find_workspace(project, workspace_id)
    rules = body.get("rules", ["LeibnizRule", "VanishingLine"])
    suggestions: list[Proposition] = []
    if "LeibnizRule" in rules:
        suggestions.extend(leibniz_suggestions(workspace))
    if "VanishingLine" in rules:
        suggestions.extend(vanishing_line_suggestions(workspace))
    comparison_id = body.get("comparison_id")
    if comparison_id:
        comparison = next((item for item in project.comparisons if item.id == comparison_id), None)
        if comparison:
            source = find_workspace(project, comparison.source_workspace_id)
            target = find_workspace(project, comparison.target_workspace_id)
            if target.id == workspace.id:
                suggestions.extend(comparison_suggestions(source, target, comparison.mode, comparison.grade_shift))
    return jsonify({"suggestions": [item.__dict__ for item in suggestions]})


@app.post("/api/workspaces/<workspace_id>/propositions")
def save_proposition(workspace_id: str):
    body = request.get_json(force=True)
    with LOCK:
        project = load_project(); workspace = find_workspace(project, workspace_id)
        proposition = Proposition(
            id=body.get("id", new_id("prop")),
            kind=body.get("kind", "relation"),
            statement=body["statement"],
            status=body.get("status", "suggested"),
            conclusion=body.get("conclusion", {}),
            premise_ids=body.get("premise_ids", []),
            rule=body.get("rule", "manual"),
            confidence=float(body.get("confidence", 1)),
            notes=body.get("notes", ""),
            source_ref=body.get("source_ref", ""),
            source_refs=body.get("source_refs", []),
            convention_id=body.get("convention_id", "q8-thesis-plotted-v1"),
            hypotheses=body.get("hypotheses", []),
            verification_checks=body.get("verification_checks", []),
        )
        action_kind = "relation" if proposition.kind == "relation" else proposition.kind
        checkpoint(project, f"Add {action_kind}: {proposition.statement}")
        workspace.propositions.append(proposition); save_project(project)
    return jsonify({"proposition": proposition.__dict__, "revision": project.revision}), 201


@app.get("/api/workspaces/<workspace_id>/proof-tree")
def proof_tree(workspace_id: str):
    project = load_project(); workspace = find_workspace(project, workspace_id)
    nodes = [{"id": prop.id, "label": prop.statement, "status": prop.status, "rule": prop.rule} for prop in workspace.propositions]
    edges = [{"source": premise, "target": prop.id} for prop in workspace.propositions for premise in prop.premise_ids]
    return jsonify({"nodes": nodes, "edges": edges})


@app.errorhandler(KeyError)
def missing(error):
    return jsonify({"error": str(error)}), 404


if __name__ == "__main__":
    app.run(debug=True, port=5078)
