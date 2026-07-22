from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InteractionContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.markup = (ROOT / "backend" / "templates" / "index.html").read_text(encoding="utf-8")
        cls.script = (ROOT / "backend" / "static" / "app.js").read_text(encoding="utf-8")
        cls.layout = (ROOT / "backend" / "static" / "cell-layout.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "backend" / "static" / "style.css").read_text(encoding="utf-8")

    def test_undo_redo_buttons_and_hotkeys_are_wired(self):
        self.assertIn('id="undo-action"', self.markup)
        self.assertIn('id="redo-action"', self.markup)
        self.assertIn("Ctrl+Z", self.markup)
        self.assertIn("Ctrl+Y", self.markup)
        self.assertIn('event.code === "KeyZ"', self.script)
        self.assertIn('event.code === "KeyY"', self.script)
        self.assertIn('changeHistory("undo")', self.script)
        self.assertIn('changeHistory("redo")', self.script)
        self.assertIn('api("/api/history")', self.script)

    def test_tool_hotkeys_do_not_dereference_a_missing_dialog(self):
        self.assertIn('const dialog = document.querySelector("dialog[open]")', self.script)
        self.assertIn("if (dialog?.open)", self.script)
        self.assertNotIn("if (dialog.open)", self.script)
        for code, tool in {
            "KeyV": "inspect",
            "KeyG": "class",
            "KeyD": "differential",
            "KeyR": "relation",
            "KeyX": "delete",
            "KeyN": "rename",
        }.items():
            self.assertIn(f'{code}: "{tool}"', self.script)
        self.assertIn('event.code === "KeyE"', self.script)
        self.assertIn("isTypingTarget(event.target)", self.script)
        self.assertIn("isTypingTarget(document.activeElement)", self.script)
        self.assertIn("event.isComposing", self.script)
        self.assertIn("event.repeat", self.script)
        self.assertIn('event.code === "Numpad0"', self.script)

    def test_delete_has_no_confirmation_and_uses_delete_cursor(self):
        self.assertNotIn("confirm(`Archive", self.script)
        self.assertIn('data-tool="delete"', self.markup)
        self.assertIn('url("delete-cursor.svg")', self.styles)
        self.assertTrue((ROOT / "backend" / "static" / "delete-cursor.svg").exists())
        self.assertNotIn('#chart[data-tool="delete"] { cursor: crosshair; }', self.styles)

    def test_select_mode_supports_left_button_canvas_drag(self):
        self.assertIn('state.tool === "inspect" && event.button === 0', self.script)
        self.assertIn("event.button === 0 && event.altKey", self.script)
        self.assertIn('state.drag.moved = true', self.script)
        self.assertIn('state.view.panX += event.clientX - state.drag.x', self.script)
        self.assertIn('#chart[data-tool="inspect"] { cursor: grab; }', self.styles)
        self.assertIn("drag the canvas with the left mouse button", self.script)

    def test_select_mode_highlights_points_and_shows_full_class_inspector(self):
        self.assertIn('event.target.closest("[data-point]")', self.script)
        self.assertIn("state.selectedClassId === record.item.id", self.script)
        self.assertIn("class-inspector-details", self.script)
        self.assertIn("Chart claims", self.script)
        self.assertIn("Provenance", self.script)
        self.assertIn('const fate = fateFor(ws, node.id) || {', self.script)
        self.assertIn('data-periodic-copy="true"', self.script)
        self.assertIn('node.dataset.periodicCopy && state.tool !== "inspect"', self.script)
        self.assertIn('event.button === 0 && state.tool === "inspect" && event.target.closest("[data-point]")', self.script)
        self.assertIn(".class-instance:hover .class-point", self.styles)
        self.assertIn(".class-point.selected", self.styles)

    def test_same_cell_instances_use_fate_only_adaptive_packing(self):
        self.assertIn("cell-layout.js", self.markup)
        self.assertLess(self.markup.index("cell-layout.js"), self.markup.index("app.js"))
        self.assertIn("HFPSSCellLayout.packInstances", self.script)
        self.assertIn("baseYOffset: 0.16", self.script)
        self.assertIn('return visualStateFor(ws, item) === "permanent" ? "square" : "circle"', self.script)
        self.assertIn("Never infer torsion", self.script)
        self.assertIn('data-class-instance=', self.script)
        self.assertIn('class="class-hit-target"', self.script)
        self.assertIn('role="button" tabindex="0"', self.script)
        self.assertIn("instancePoints.get(classInstanceKey", self.script)
        self.assertIn("packInstances", self.layout)
        self.assertIn("baseYOffset", self.layout)
        self.assertIn(".class-point.square", self.styles)

    def test_manual_connections_have_visible_lines_and_pointer_preview(self):
        self.assertIn("function visibleRelations", self.script)
        self.assertIn('proposition.kind !== "relation"', self.script)
        self.assertIn('class="relation-line ${relationVisualState(relation)}"', self.script)
        self.assertIn('id="connection-preview"', self.script)
        self.assertIn("state.connectionPointer", self.script)
        self.assertIn('preview.setAttribute("x2", state.connectionPointer.x)', self.script)
        self.assertIn(".relation-line", self.styles)
        self.assertIn(".connection-preview.differential", self.styles)

    def test_generator_dialog_has_live_safe_math_preview(self):
        self.assertIn('id="class-label-preview"', self.markup)
        self.assertIn("function renderClassLabelPreview", self.script)
        self.assertIn('addEventListener("input", renderClassLabelPreview)', self.script)
        self.assertIn("throwOnError: false", self.script)
        self.assertIn("trust: false", self.script)
        self.assertIn(".class-label-preview", self.styles)

    def test_project_json_import_requires_preview_and_explicit_apply(self):
        self.assertIn('id="export-json"', self.markup)
        self.assertIn('id="import-json"', self.markup)
        self.assertIn('id="import-json-file"', self.markup)
        self.assertIn('id="import-project-dialog"', self.markup)
        self.assertIn('id="apply-project-import" disabled', self.markup)
        self.assertIn('window.location.assign("/api/project/export")', self.script)
        self.assertIn('api("/api/project/import/preview"', self.script)
        self.assertIn('api("/api/project/import/apply"', self.script)
        self.assertIn("preview_sha256: preview.preview_sha256", self.script)
        self.assertIn("expected_revision: preview.current_revision", self.script)
        self.assertIn("applyButton.disabled = false", self.script)
        self.assertNotIn("if (file) applyProjectImport", self.script)
        self.assertIn("Review warnings", self.script)
        self.assertIn(".import-project-summary", self.styles)

    def test_workspace_selector_separates_charts_atlas_and_support_spaces(self):
        self.assertIn('id="support-workspace-select"', self.markup)
        self.assertIn('id="open-support-workspace"', self.markup)
        self.assertIn("function isReferenceSupportWorkspace", self.script)
        self.assertIn("function isEmptyAtlasWorkspace", self.script)
        self.assertIn("item.classes.length === 0", self.script)
        self.assertIn("function ordinaryWorkspaces", self.script)
        self.assertIn("state.workspaceId = defaultWorkspaceId()", self.script)
        self.assertIn("renderWorkspaceNavigation(ws)", self.script)
        self.assertIn(".support-workspace-control", self.styles)

    def test_selected_class_exposes_read_only_differential_candidate_control(self):
        self.assertIn('id="find-differential-candidates"', self.script)
        self.assertIn("Find compatible d<sub>", self.script)
        self.assertIn("/differential-candidates", self.script)
        self.assertIn("review-only · not saved", self.script)
        self.assertIn("never persisted or accepted automatically", self.script)
        self.assertNotIn("data-accept-candidate", self.script)

    def test_e2_dialog_requires_an_explicit_source_locator(self):
        self.assertIn('id="e2-presentation-dialog"', self.markup)
        self.assertIn('source_ref: ""', self.script)
        self.assertIn("/api/v2/e2-presentations/preview", self.script)
        self.assertIn("Materialize explicit data", self.markup)

    def test_persistent_periodicity_tool_guides_source_backed_d8_materialization(self):
        self.assertIn('id="periodicity-tool"', self.markup)
        self.assertIn("D<sup>8</sup> periodicity", self.markup)
        self.assertIn("function renderPersistentPeriodicityTool", self.script)
        self.assertIn("renderPersistentPeriodicityTool()", self.script)
        self.assertIn('id="preview-periodicity"', self.script)
        self.assertIn('id="materialize-periodicity"', self.script)
        self.assertIn("/periodicity/preview", self.script)
        self.assertIn("/periodicity/materialize", self.script)
        self.assertIn("Preview this exact D^8 translation before materializing it", self.script)
        self.assertIn("integer Q8 HFPSS", self.script)
        self.assertIn("shift (64,0)", self.script)
        self.assertIn("Select an anchor class", self.script)
        self.assertIn("E2 copies", self.script)
        self.assertIn("g=kD<sup>3</sup>", self.script)
        self.assertIn(".periodicity-tool-section", self.styles)

    def test_clear_current_canvas_is_confirmed_safe_and_undoable(self):
        self.assertIn('id="clear-current-canvas"', self.markup)
        self.assertIn("function clearCurrentCanvas", self.script)
        self.assertIn("window.confirm", self.script)
        self.assertIn("Class records, differentials, relations, propositions, provenance, and fate history remain stored", self.script)
        self.assertIn("Use Undo to restore the entire canvas in one step", self.script)
        self.assertIn("/clear-canvas", self.script)
        self.assertIn('{ method: "POST" }', self.script)
        self.assertIn('addEventListener("click", clearCurrentCanvas)', self.script)
        self.assertNotIn("irreversible", self.script.lower())

    def test_toolbar_controls_wrap_instead_of_forcing_horizontal_overflow(self):
        self.assertIn("flex-wrap: wrap", self.styles)
        self.assertIn("overflow-wrap: anywhere", self.styles)
        self.assertNotIn("min-width: 720px", self.styles)
        self.assertIn("--toolbar-height", self.styles)
        self.assertIn("syncLayoutHeight", self.script)

    def test_chart_key_explains_every_dot_and_arrow_state(self):
        self.assertIn('class="panel-section chart-key"', self.markup)
        for label in ("Green", "Gray", "Rose", "Purple", "Solid charcoal arrow", "Amber dashed arrow"):
            self.assertIn(label, self.markup)
        self.assertIn("do not encode algebraic order", self.markup)
        self.assertIn("function differentialVisualState", self.script)
        self.assertIn('["derived", "reviewed", "established", "proven"]', self.script)
        self.assertIn(".dot.target", self.styles)
        self.assertIn(".key-line.provisional", self.styles)

    def test_javascript_remains_syntactically_valid(self):
        try:
            completed = subprocess.run(
                ["node", "--check", str(ROOT / "backend" / "static" / "app.js")],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except FileNotFoundError:
            self.skipTest("Node.js is not installed in this environment.")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        layout_completed = subprocess.run(
            ["node", "--check", str(ROOT / "backend" / "static" / "cell-layout.js")],
            capture_output=True,
            text=True,
            timeout=20,
        )
        self.assertEqual(layout_completed.returncode, 0, layout_completed.stderr)


if __name__ == "__main__":
    unittest.main()
