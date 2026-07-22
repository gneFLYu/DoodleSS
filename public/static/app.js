const state = {
  project: null,
  logicGraph: { nodes: [], edges: [] },
  history: { undo_depth: 0, redo_depth: 0, undo_label: null, redo_label: null },
  workspaceId: null,
  selectedClassId: null,
  tool: "inspect",
  connectionStart: null,
  suggestions: [],
  candidateResults: null,
  periodicityPreview: null,
  drawingPeriodicityPreview: null,
  importPreview: null,
  drag: null,
  suppressClick: false,
  connectionPointer: null,
  view: { zoom: 1, panX: 0, panY: 0 },
};

const $ = (selector) => document.querySelector(selector);
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function workspace() {
  return state.project?.workspaces.find((item) => item.id === state.workspaceId);
}

function isReferenceSupportWorkspace(item) {
  return item.spectral_sequence !== "hfpss"
    || item.group !== "Q8"
    || item.id === "ws_H"
    || /reference|support/i.test(`${item.name} ${item.grading_label}`);
}

function isEmptyAtlasWorkspace(item) {
  return (state.project?.grading_sectors || []).some((sector) => sector.workspace_id === item.id)
    && item.classes.length === 0;
}

function ordinaryWorkspaces() {
  return (state.project?.workspaces || []).filter((item) => !isReferenceSupportWorkspace(item) && !isEmptyAtlasWorkspace(item));
}

function defaultWorkspaceId() {
  return ordinaryWorkspaces()[0]?.id || state.project?.workspaces[0]?.id || null;
}

function renderWorkspaceNavigation(ws) {
  const selector = $("#workspace-select");
  const ordinary = ordinaryWorkspaces();
  const currentIsOrdinary = ordinary.some((item) => item.id === ws.id);
  selector.innerHTML = `${currentIsOrdinary ? "" : `<option value="${ws.id}">[${isReferenceSupportWorkspace(ws) ? "reference" : "atlas"}] ${escapeHtml(ws.name)}</option>`}${ordinary.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("")}`;
  selector.value = ws.id;

  const support = state.project.workspaces.filter(isReferenceSupportWorkspace);
  const supportSelector = $("#support-workspace-select");
  supportSelector.innerHTML = support.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("");
  $("#open-support-workspace").disabled = !support.length;
}

function pageLimit(ws = workspace()) {
  const inferred = Math.max(2, ...ws.differentials.map((item) => item.page + 1));
  return Math.max(25, inferred, Number(ws.settings.known_page_max || 0), Number(ws.settings.page_limit || 0));
}

function liveClassesAt(ws, page = ws.page) {
  const fates = new Map((ws.fates || []).map((item) => [item.class_id, item]));
  return ws.classes.filter((item) => {
    if (item.archived || item.page > page) return false;
    const death = fates.get(item.id)?.first_hfpss_death;
    return !death || Number(death.page) >= page;
  });
}

function visualState(value) {
  return ["permanent", "killed", "target"].includes(value) ? value : "unknown";
}

function fateFor(ws, classId) {
  return (ws.fates || []).find((item) => item.class_id === classId);
}

function visualStateFor(ws, item) {
  const conclusion = fateFor(ws, item.id)?.conclusion;
  if (conclusion === "permanent_cycle") return "permanent";
  if (conclusion === "supports_differential") return "killed";
  if (conclusion === "is_hit") return "target";
  return "unknown";
}

function glyphShapeFor(ws, item) {
  // Shape remains a fate/proof-status display. Never infer torsion, tower
  // level, or coefficient algebra from a label or coefficient context.
  return visualStateFor(ws, item) === "permanent" ? "square" : "circle";
}

function differentialVisualState(differential) {
  return ["derived", "reviewed", "established", "proven"].includes(differential.status) ? "accepted" : "under-review";
}

function relationVisualState(proposition) {
  return ["derived", "reviewed", "established", "proven"].includes(proposition.status) ? "accepted" : "under-review";
}

function escapeHtml(value) {
  const node = document.createElement("span");
  node.textContent = value ?? "";
  return node.innerHTML;
}

function toast(message) {
  const target = $("#toast");
  target.textContent = message;
  target.classList.add("show");
  window.clearTimeout(toast.timeout);
  toast.timeout = window.setTimeout(() => target.classList.remove("show"), 2600);
}

function gradeText(grade) {
  const representation = Object.entries(grade.representation || {})
    .filter(([, coefficient]) => coefficient)
    .map(([name, coefficient]) => `${coefficient < 0 ? "-" : "+"}${Math.abs(coefficient) === 1 ? "" : Math.abs(coefficient)}${name}`)
    .join(" ");
  return `(${grade.stem}, ${grade.filtration})${representation ? ` ${representation}` : ""}`;
}

function allPropositions() {
  return state.project.workspaces.flatMap((ws) => ws.propositions.map((prop) => ({ ...prop, workspaceName: ws.name })));
}

async function loadProject() {
  const [project, logicGraph, history] = await Promise.all([api("/api/project"), api("/api/v2/logic-graph"), api("/api/history")]);
  state.project = project;
  state.logicGraph = logicGraph;
  state.history = history;
  if (!state.project.workspaces.some((item) => item.id === state.workspaceId)) state.workspaceId = defaultWorkspaceId();
  render();
}

function toolHint() {
  const hints = {
    inspect: "Select a class, or drag the canvas with the left mouse button to pan blank space. Middle-drag or Alt+left-drag pans in any tool.",
    class: "Click an empty feasible cell to add a generator.",
    differential: "Click a source class, preview the arrow, then click its target.",
    relation: "Click two classes to draw and record a candidate relation in the proposition tree.",
    delete: "Click a class to archive its chart display while retaining proof history.",
    rename: "Click a class to rename it.",
  };
  return hints[state.tool] || hints.inspect;
}

function renderPageSelector() {
  const select = $("#page-select");
  const ws = workspace();
  const current = ws.page;
  const maximum = pageLimit(ws);
  select.innerHTML = Array.from({ length: maximum - 1 }, (_, index) => {
    const page = index + 2;
    return `<option value="${page}">E${page}</option>`;
  }).join("") + `<option value="__add_page">+ Add E${maximum + 1}</option>`;
  select.value = current;
  $("#page-previous").disabled = current <= 2;
  $("#page-next").disabled = false;
}

function render() {
  const ws = workspace();
  if (!ws) return;
  ws.page = clamp(Number(ws.page) || 2, 2, pageLimit(ws));
  const visibleClasses = liveClassesAt(ws);
  renderWorkspaceNavigation(ws);
  renderPageSelector();
  renderHistoryControls();
  $("#chart").dataset.tool = state.tool;

  $("#workspace-title").textContent = ws.name;
  $("#workspace-meta").textContent = `${ws.group} · ${ws.theory} · characteristic ${ws.characteristic} · ${ws.grading_label}`;
  $("#workspace-summary").textContent = ws.summary || "No research summary has been recorded for this workspace.";
  $("#page-label").textContent = `E${ws.page}`;
  $("#chart-caption").textContent = `${ws.grading_label} · E${ws.page}`;
  const documentedLimit = Number(ws.settings.known_page_max || 0);
  $("#page-status").textContent = documentedLimit && ws.page >= documentedLimit
    ? `E${documentedLimit} is the latest documented page; later pages are available for workspace additions.`
    : `Showing E${ws.page}; d${ws.page} is drawn only on this page.`;
  $("#vanishing-line").value = ws.settings.vanishing_line || 0;
  $("#class-count").textContent = visibleClasses.length;
  $("#tool-hint").textContent = toolHint();
  document.querySelectorAll("[data-tool]").forEach((button) => button.classList.toggle("active", button.dataset.tool === state.tool));
  $("#class-list").innerHTML = visibleClasses.map((item) => `<button class="class-row ${state.selectedClassId === item.id ? "active" : ""}" data-class="${item.id}"><span><i class="badge ${visualStateFor(ws, item)}"></i>${escapeHtml(item.label)}</span><span class="coords">${item.grade.stem}, ${item.grade.filtration}</span></button>`).join("") || '<p class="empty">No surviving classes on this page.</p>';
  document.querySelectorAll("[data-class]").forEach((button) => button.addEventListener("click", () => onClassClick(button.dataset.class)));
  renderComparisons();
  renderGradingAtlas();
  renderFateInspector();
  renderDrawingPeriodicityTool();
  renderPersistentPeriodicityTool();
  renderProofTree();
  renderProductControls();
  renderSuggestions();
  constrainView();
  renderChart();
  syncLayoutHeight();
}

function syncLayoutHeight() {
  const toolbar = document.querySelector(".legacy-toolbar");
  if (toolbar) document.documentElement.style.setProperty("--toolbar-height", `${toolbar.offsetHeight}px`);
}

function renderHistoryControls() {
  const undo = $("#undo-action");
  const redo = $("#redo-action");
  undo.disabled = !state.history.undo_depth;
  redo.disabled = !state.history.redo_depth;
  undo.title = state.history.undo_label ? `Undo: ${state.history.undo_label} (Ctrl+Z)` : "Nothing to undo (Ctrl+Z)";
  redo.title = state.history.redo_label ? `Redo: ${state.history.redo_label} (Ctrl+Y)` : "Nothing to redo (Ctrl+Y)";
}

async function changeHistory(direction) {
  if (!state.history[`${direction}_depth`]) return;
  try {
    const result = await api(`/api/history/${direction}`, { method: "POST" });
    state.selectedClassId = null;
    state.connectionStart = null;
    state.drawingPeriodicityPreview = null;
    await loadProject();
    toast(`${direction === "undo" ? "Undid" : "Redid"}: ${result.action}`);
  } catch (error) { toast(error.message); }
}

function atlasSector(sectorId) {
  return (state.project.grading_sectors || []).find((item) => item.id === sectorId);
}

function renderGradingAtlas() {
  const root = $("#grading-atlas");
  const sectors = state.project.grading_sectors || [];
  root.innerHTML = sectors.map((sector) => {
    const active = sector.workspace_id === state.workspaceId ? "active" : "";
    const count = sector.class_ids?.length || 0;
    return `<button type="button" class="atlas-cell ${active} ${escapeHtml(sector.status)}" data-sector="${sector.id}" title="${escapeHtml(sector.display_label)} · ${escapeHtml(sector.status)}"><strong>S<sub>${sector.a},${sector.b}</sub></strong><span>${count ? `${count} classes` : "not computed"}</span></button>`;
  }).join("");
  root.querySelectorAll("[data-sector]").forEach((button) => button.addEventListener("click", () => selectAtlasSector(button.dataset.sector)));
}

async function selectAtlasSector(sectorId) {
  const sector = atlasSector(sectorId);
  if (!sector) return;
  state.workspaceId = sector.workspace_id;
  state.selectedClassId = null;
  state.connectionStart = null;
  state.view = { zoom: 1, panX: 0, panY: 0 };
  render();
  try {
    const preview = await api(`/api/v2/c3-actions/omega/orbit/${sectorId}`);
    const targets = preview.orbit.map((item) => item.result_sector_id || item.normalization_status).join(" → ");
    $("#c3-summary").textContent = `ω orbit: ${targets}. ${preview.warning}`;
  } catch (error) {
    $("#c3-summary").textContent = error.message;
  }
}

function renderFateInspector() {
  const ws = workspace();
  const node = ws.classes.find((item) => item.id === state.selectedClassId);
  if (!node) {
    $("#fate-status").textContent = "none";
    $("#fate-inspector").innerHTML = '<p class="empty">Select a class to inspect its two-track fate record.</p>';
    return;
  }
  const fate = fateFor(ws, node.id) || {
    conclusion: "unresolved", hfpss_outgoing_events: [], hfpss_incoming_events: [],
    tate_outgoing_events: [], tate_incoming_events: [], first_hfpss_death: null,
  };
  const events = new Map((ws.differential_events || []).map((item) => [item.id, item]));
  const eventMarkup = (ids, track) => ids.map((id) => {
    const event = events.get(id);
    if (!event) return "";
    const qualifier = event.comparison_status === "tate_only_negative_source" ? " · Tate-only negative source" : "";
    return `<li><strong>${event.role} d${event.page}</strong><span>${escapeHtml(event.status)}${escapeHtml(qualifier)}</span></li>`;
  }).join("") || `<li class="empty">No ${track} events.</li>`;
  const representation = Object.entries(node.grade.representation || {})
    .filter(([, coefficient]) => coefficient)
    .map(([name, coefficient]) => `${coefficient > 0 ? "+" : ""}${coefficient}${name}`)
    .join(" ") || "integer-graded";
  const relatedDifferentials = ws.differentials.filter((item) => item.source_id === node.id || item.target_id === node.id);
  const differentialMarkup = relatedDifferentials.map((item) => {
    const role = item.source_id === node.id ? "supports" : "receives";
    const period = item.period_family_id
      ? `${item.period_family_id} (${item.period_stem},${item.period_filtration})`
      : "no period family";
    return `<li><strong>${role} d${item.page}</strong><span>${escapeHtml(item.status)} · ${escapeHtml(period)}</span></li>`;
  }).join("") || '<li class="empty">No chart differential claims.</li>';
  const sourcePropositions = ws.propositions.filter((item) => (
    item.conclusion?.class_id === node.id
    || relatedDifferentials.some((differential) => differential.proposition_id === item.id)
  ));
  const provenanceMarkup = sourcePropositions.map((item) => {
    const source = item.source_refs?.join("; ") || item.source_ref || "source locator required";
    return `<li><strong>${escapeHtml(item.id)}</strong><span>${escapeHtml(item.status)} · ${escapeHtml(source)}</span></li>`;
  }).join("") || '<li class="empty">No direct proposition record.</li>';
  const candidateData = state.candidateResults
    && state.candidateResults.sourceId === node.id
    && state.candidateResults.page === ws.page
    ? state.candidateResults.data
    : null;
  const candidateMarkup = candidateData
    ? renderCandidateResults(candidateData)
    : '<p class="empty">No compatibility query has been run for this class on this page.</p>';
  $("#fate-status").textContent = fate.conclusion.replaceAll("_", " ");
  $("#fate-inspector").innerHTML = `
    <strong>${escapeHtml(node.label)}</strong>
    <dl class="class-inspector-details"><dt>Grade</dt><dd>${escapeHtml(gradeText(node.grade))}</dd><dt>Representation</dt><dd>${escapeHtml(representation)}</dd><dt>Display state</dt><dd>${escapeHtml(visualStateFor(ws, node))}</dd><dt>Convention</dt><dd>${escapeHtml(node.convention_id || "unspecified")}</dd><dt>Coefficient context</dt><dd>${escapeHtml(node.coefficient_context_id || "unspecified")}</dd></dl>
    <div class="fate-track hfpss"><span>HFPSS</span><ul>${eventMarkup([...(fate.hfpss_outgoing_events || []), ...(fate.hfpss_incoming_events || [])], "HFPSS")}</ul></div>
    <div class="fate-track tate"><span>TateSS</span><ul>${eventMarkup([...(fate.tate_outgoing_events || []), ...(fate.tate_incoming_events || [])], "TateSS")}</ul></div>
    <div class="fate-track claims"><span>Chart claims</span><ul>${differentialMarkup}</ul></div>
    <div class="fate-track provenance"><span>Provenance</span><ul>${provenanceMarkup}</ul></div>
    <div class="fate-track candidates"><span>Compatibility</span><button type="button" class="text-button" id="find-differential-candidates">Find compatible d<sub>${ws.page}</sub> candidates</button>${candidateMarkup}</div>
    <p class="fate-summary">${fate.first_hfpss_death ? `Lives through E${fate.last_hfpss_live_page}; absent on E${Number(fate.last_hfpss_live_page) + 1}.` : fate.conclusion === "permanent_cycle" ? "HFPSS permanent cycle with explicit justification." : "HFPSS fate remains unresolved."}</p>`;
  $("#find-differential-candidates").addEventListener("click", () => findDifferentialCandidates(node.id));
}

function drawingPeriodicityRules(ws = workspace()) {
  const canonical = (state.project?.manual_periodicity_rules || []).filter((rule) => (
    rule.workspace_id === ws?.id && !rule.archived
  ));
  return canonical.length ? canonical.map((rule) => ({
    ...rule,
    p: rule.p ?? rule.period_vector?.stem,
    q: rule.q ?? rule.period_vector?.filtration,
  })) : (ws?.settings?.manual_periodicity_rules || []);
}

function drawingPeriodicityPath(suffix) {
  return `/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/drawing-periodicity/${suffix}`;
}

function drawingPeriodicityPayload(mode) {
  if (mode === "box") {
    return {
      page: workspace().page,
      p_min: Number($("#drawing-period-p-min").value),
      p_max: Number($("#drawing-period-p-max").value),
      q_min: Number($("#drawing-period-q-min").value),
      q_max: Number($("#drawing-period-q-max").value),
    };
  }
  return {
    page: workspace().page,
    p: Number($("#drawing-diff-period-p").value),
    q: Number($("#drawing-diff-period-q").value),
  };
}

function drawingPreviewCycles(data) {
  return data?.cycle_copies || data?.class_copies || [];
}

function drawingPreviewConnections(data) {
  return data?.connection_copies || [
    ...(data?.differential_copies || []),
    ...(data?.relation_copies || []),
  ];
}

function drawingPreviewSummaryMarkup(data) {
  if (!data) return "Preview has not been run.";
  const summary = data.summary || {};
  const cycles = drawingPreviewCycles(data);
  const connections = drawingPreviewConnections(data);
  const cycleCreates = Number(summary.cycles_to_create ?? summary.classes_to_create ?? cycles.filter((item) => item.action === "create").length);
  const cycleReuses = Number(summary.cycles_to_reuse ?? cycles.filter((item) => item.action === "reuse").length);
  const differentialCreates = Number(summary.differentials_to_create ?? connections.filter((item) => item.kind === "differential" && item.action === "create").length);
  const relationCreates = Number(summary.relations_to_create ?? connections.filter((item) => item.kind === "relation" && item.action === "create").length);
  const connectionReuses = Number(summary.connections_to_reuse ?? connections.filter((item) => item.action === "reuse").length);
  const existingEndpoints = Number(summary.existing_endpoints ?? data.existing_endpoint_copies?.length ?? 0);
  const skipped = Number(summary.skipped ?? data.skipped?.length ?? 0);
  const conflicts = Number(summary.conflicts ?? data.conflicts?.length ?? 0);
  return `<strong>Preview only · manual-unverified</strong><ul><li>${cycleCreates} cycle(s) to create · ${cycleReuses} to reuse</li><li>${differentialCreates} differential arrow(s) to create</li><li>${relationCreates} relation connection(s) to create</li><li>${connectionReuses} connection(s) to reuse · ${existingEndpoints} existing endpoint(s)</li><li>${skipped} skipped translation(s)</li><li>${conflicts} conflict(s)</li></ul><span>${escapeHtml(data.behavior || data.warning || "No mathematical periodicity claim is created by preview.")}</span>`;
}

function renderDrawingPeriodicityTool() {
  const rulesRoot = $("#drawing-periodicity-rules-list");
  const rules = drawingPeriodicityRules();
  rulesRoot.innerHTML = rules.length ? rules.map((rule) => `
    <div class="drawing-periodicity-rule">
      <span><strong>${escapeHtml(rule.name)}</strong> (${Number(rule.p)}, ${Number(rule.q)})</span>
      <button type="button" class="rule-item-delete" data-delete-drawing-rule="${escapeHtml(rule.id)}" title="Delete rule" aria-label="Delete periodicity rule ${escapeHtml(rule.name)}">×</button>
    </div>`).join("") : '<p class="empty">No rules defined.</p>';
  rulesRoot.querySelectorAll("[data-delete-drawing-rule]").forEach((button) => {
    button.addEventListener("click", () => deleteDrawingPeriodicityRule(button.dataset.deleteDrawingRule));
  });

  const preview = state.drawingPeriodicityPreview;
  const current = preview && preview.workspaceId === state.workspaceId && preview.page === workspace().page ? preview : null;
  $("#drawing-period-box-preview").innerHTML = current?.mode === "box"
    ? drawingPreviewSummaryMarkup(current.data)
    : "Preview has not been run.";
  $("#drawing-diff-period-preview").innerHTML = current?.mode === "differentials"
    ? drawingPreviewSummaryMarkup(current.data)
    : "Preview has not been run.";
  const blocked = Boolean(current?.data?.conflicts?.length);
  $("#apply-drawing-period-box").disabled = current?.mode !== "box" || blocked;
  $("#apply-drawing-diff-period").disabled = current?.mode !== "differentials" || blocked;
}

async function addDrawingPeriodicityRule() {
  const button = $("#add-drawing-period-rule");
  const payload = {
    name: $("#drawing-period-name").value.trim(),
    p: Number($("#drawing-period-p").value),
    q: Number($("#drawing-period-q").value),
  };
  button.disabled = true;
  try {
    await api(drawingPeriodicityPath("rules"), { method: "POST", body: JSON.stringify(payload) });
    state.drawingPeriodicityPreview = null;
    await loadProject();
    toast(`Added manual periodicity rule ${payload.name} (${payload.p},${payload.q}).`);
  } catch (error) { toast(error.message); } finally { button.disabled = false; }
}

async function deleteDrawingPeriodicityRule(ruleId) {
  try {
    await api(drawingPeriodicityPath(`rules/${encodeURIComponent(ruleId)}`), { method: "DELETE" });
    state.drawingPeriodicityPreview = null;
    await loadProject();
    toast("Manual periodicity rule deleted; generated records were retained.");
  } catch (error) { toast(error.message); }
}

async function previewDrawingPeriodicity(mode) {
  const button = mode === "box" ? $("#preview-drawing-period-box") : $("#preview-drawing-diff-period");
  const suffix = mode === "box" ? "box/preview" : "differentials/preview";
  button.disabled = true;
  try {
    const payload = drawingPeriodicityPayload(mode);
    const data = await api(drawingPeriodicityPath(suffix), { method: "POST", body: JSON.stringify(payload) });
    state.drawingPeriodicityPreview = { mode, payload, data, workspaceId: state.workspaceId, page: workspace().page };
    renderDrawingPeriodicityTool();
    renderChart();
    toast("Manual periodicity preview ready; no project record changed.");
  } catch (error) {
    state.drawingPeriodicityPreview = null;
    renderDrawingPeriodicityTool();
    renderChart();
    toast(error.message);
  } finally { button.disabled = false; }
}

async function applyDrawingPeriodicity(mode) {
  const preview = state.drawingPeriodicityPreview;
  if (!preview || preview.mode !== mode || preview.workspaceId !== state.workspaceId || preview.page !== workspace().page) {
    return toast("Preview this exact drawing-periodicity operation before applying it.");
  }
  const payload = drawingPeriodicityPayload(mode);
  if (JSON.stringify(payload) !== JSON.stringify(preview.payload)) {
    return toast("The vector or bounds changed; preview the exact operation again.");
  }
  const button = mode === "box" ? $("#apply-drawing-period-box") : $("#apply-drawing-diff-period");
  const suffix = mode === "box" ? "box/apply" : "differentials/apply";
  button.disabled = true;
  try {
    const result = await api(drawingPeriodicityPath(suffix), { method: "POST", body: JSON.stringify(payload) });
    state.drawingPeriodicityPreview = null;
    await loadProject();
    const created = (result.created_class_ids?.length || 0) + (result.created_differential_ids?.length || 0) + (result.created_relation_proposition_ids?.length || 0);
    toast(result.changed === false ? "Every requested drawing record already exists." : `Applied ${created} manual drawing record(s) in one undoable edit.`);
  } catch (error) { toast(error.message); } finally { if (button) button.disabled = false; }
}

function d8RuleFor(ws) {
  return (state.project.periodicity_rules || []).find((item) => (
    item.workspace_id === ws.id && item.id === "q8-hfpss-integer-d8-horizontal-r3" && item.status === "established"
  ));
}

function outgoingAcceptedDifferentials(ws, node) {
  const accepted = new Set(["derived", "reviewed", "established", "proven"]);
  return ws.differentials.filter((item) => item.source_id === node.id && item.page === ws.page && accepted.has(item.status));
}

function periodicityPreviewMarkup(node, page) {
  const preview = state.periodicityPreview;
  if (!preview || preview.anchorClassId !== node.id || preview.page !== page) {
    return '<p class="empty">Preview a distinct persisted copy before materializing it.</p>';
  }
  const copies = preview.data.class_copies || [];
  const labels = copies.map((item) => `${item.action}: ${item.label} at (${item.grade.stem}, ${item.grade.filtration})`).join("; ");
  const differential = preview.data.differential_copy ? ` Differential: ${preview.data.differential_copy.action}.` : "";
  return `<p class="periodicity-preview">Preview only — ${escapeHtml(labels)}.${escapeHtml(differential)} No chart record has changed.</p>`;
}

function renderPeriodicityControl(ws, node) {
  const rule = d8RuleFor(ws);
  if (!rule) {
    return '<p class="periodicity-scope"><strong>Scope:</strong> integer Q8 HFPSS · E3+ · D<sup>8</sup> · shift (64,0)</p><p class="hint">Unavailable in this workspace. No source-backed automatic D<sup>8</sup> rule applies here; E2, g=kD<sup>3</sup>, Tate, C4, and other gradings remain disabled.</p><div class="periodicity-actions"><button type="button" disabled>Preview D<sup>8</sup> copy</button><button type="button" class="primary" disabled>Materialize distinct copy</button></div>';
  }
  if (ws.page < Number(rule.valid_from_page)) {
    return `<p class="periodicity-scope"><strong>Scope:</strong> integer Q8 HFPSS · E${rule.valid_from_page}+ · ${escapeHtml(rule.multiplier_expression)} · shift (${rule.grade_shift.stem},${rule.grade_shift.filtration})</p><p class="hint">Disabled on E${ws.page}. This certificate begins on E${rule.valid_from_page}; E2 copies and g=kD<sup>3</sup> remain manual.</p><div class="periodicity-actions"><button type="button" disabled>Preview D<sup>8</sup> copy</button><button type="button" class="primary" disabled>Materialize distinct copy</button></div>`;
  }
  if (!node) {
    return `<p class="periodicity-scope"><strong>Scope:</strong> integer Q8 HFPSS · E${rule.valid_from_page}+ · ${escapeHtml(rule.multiplier_expression)} · shift (${rule.grade_shift.stem},${rule.grade_shift.filtration})</p><p class="hint">Select an anchor class on the chart or in “Classes on this page”, then Preview. Materialize stays disabled until that exact preview succeeds.</p><div class="periodicity-actions"><button type="button" disabled>Preview D<sup>8</sup> copy</button><button type="button" class="primary" disabled>Materialize distinct copy</button></div><p class="hint">Source: ${escapeHtml(rule.source_ref || "source locator required")}</p>`;
  }
  const differentials = outgoingAcceptedDifferentials(ws, node);
  const preview = state.periodicityPreview;
  const ready = preview && preview.anchorClassId === node.id && preview.page === ws.page;
  const selectedDifferential = ready ? preview.payload.differential_id || "" : "";
  const options = `<option value="" ${selectedDifferential ? "" : "selected"}>Class only</option>` + differentials.map((item) => `<option value="${escapeHtml(item.id)}" ${selectedDifferential === item.id ? "selected" : ""}>Propagate accepted d${item.page}</option>`).join("");
  const translation = ready ? preview.payload.translation : 1;
  return `<p class="periodicity-scope"><strong>Scope:</strong> integer Q8 HFPSS · E${rule.valid_from_page}+ · ${escapeHtml(rule.multiplier_expression)} · shift (${rule.grade_shift.stem},${rule.grade_shift.filtration})</p>
    <p class="hint">Anchor: <strong>${escapeHtml(node.label)}</strong> at ${escapeHtml(gradeText(node.grade))}. Preview is read-only; materialization creates distinct stored records, never visual repeats.</p>
    <label class="periodicity-field">Translation<input id="periodicity-translation" type="number" step="1" value="${translation}" aria-label="D8 translation"></label>
    <label class="periodicity-field">Accepted arrow<select id="periodicity-differential" aria-label="Accepted differential to translate">${options}</select></label>
    <div class="periodicity-actions"><button type="button" id="preview-periodicity">Preview D<sup>8</sup> copy</button><button type="button" id="materialize-periodicity" class="primary" ${ready ? "" : "disabled"}>Materialize distinct copy</button></div>
    ${periodicityPreviewMarkup(node, ws.page)}
    <p class="hint">Source: ${escapeHtml(rule.source_ref || "source locator required")}. Manual only: g=kD<sup>3</sup>, E2, other workspaces, under-review arrows, and composite period rules.</p>`;
}

function renderPersistentPeriodicityTool() {
  const ws = workspace();
  const node = ws?.classes.find((item) => item.id === state.selectedClassId) || null;
  $("#periodicity-tool").innerHTML = renderPeriodicityControl(ws, node);
  const rule = ws && d8RuleFor(ws);
  if (!node || !rule || ws.page < Number(rule.valid_from_page)) return;
  $("#preview-periodicity").addEventListener("click", () => previewPeriodicityTranslate(node.id));
  $("#materialize-periodicity").addEventListener("click", () => materializePeriodicityTranslate(node.id));
}

function periodicityRequest(anchorClassId) {
  const translation = Number($("#periodicity-translation").value);
  if (!Number.isInteger(translation) || translation === 0) throw new Error("Translation must be a nonzero integer.");
  const rule = d8RuleFor(workspace());
  const differentialId = $("#periodicity-differential").value;
  return {
    rule_id: rule.id,
    anchor_class_id: anchorClassId,
    page: workspace().page,
    translation,
    ...(differentialId ? { differential_id: differentialId } : {}),
  };
}

async function previewPeriodicityTranslate(anchorClassId) {
  const button = $("#preview-periodicity");
  button.disabled = true;
  try {
    const payload = periodicityRequest(anchorClassId);
    const data = await api(`/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/periodicity/preview`, {
      method: "POST", body: JSON.stringify(payload),
    });
    state.periodicityPreview = { anchorClassId, page: workspace().page, payload, data };
    renderPersistentPeriodicityTool();
    toast("D^8 translation previewed; no chart record changed.");
  } catch (error) {
    state.periodicityPreview = null;
    state.drawingPeriodicityPreview = null;
    toast(error.message);
  } finally {
    if ($("#preview-periodicity")) $("#preview-periodicity").disabled = false;
  }
}

async function materializePeriodicityTranslate(anchorClassId) {
  const preview = state.periodicityPreview;
  if (!preview || preview.anchorClassId !== anchorClassId || preview.page !== workspace().page) {
    return toast("Preview this exact D^8 translation before materializing it.");
  }
  let payload;
  try {
    payload = periodicityRequest(anchorClassId);
  } catch (error) { return toast(error.message); }
  if (JSON.stringify(payload) !== JSON.stringify(preview.payload)) {
    return toast("Translation or arrow selection changed; preview the exact operation again.");
  }
  const button = $("#materialize-periodicity");
  button.disabled = true;
  try {
    const data = await api(`/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/periodicity/materialize`, {
      method: "POST", body: JSON.stringify(payload),
    });
    state.periodicityPreview = null;
    await loadProject();
    const copies = data.created_class_ids.length;
    toast(`Materialized ${copies} distinct D^8 class copy/copies${data.created_differential_id ? " and one derived arrow" : ""}.`);
  } catch (error) { toast(error.message); }
}

function renderCandidateResults(data) {
  const direct = data.candidates || [];
  const transported = data.comparison_candidates || [];
  const candidateList = (items, label) => items.length
    ? `<div class="candidate-result-group"><strong>${label}</strong><ul>${items.map((item) => `<li><strong>${escapeHtml(item.statement)}</strong><span>review-only · not saved</span></li>`).join("")}</ul></div>`
    : "";
  if (!direct.length && !transported.length) {
    return '<p class="empty">No live, representation-preserving target with the displayed d<sub>r</sub> bidegree.</p>';
  }
  return `<div class="candidate-results">${candidateList(direct, "Bidegree/liveness candidates")}${candidateList(transported, "Comparison transport candidates")}<p class="hint">These results are never persisted or accepted automatically. Review the listed hypotheses before creating any claim.</p></div>`;
}

async function findDifferentialCandidates(sourceId) {
  const ws = workspace();
  const button = $("#find-differential-candidates");
  button.disabled = true;
  try {
    const comparison = state.project.comparisons.find((item) => item.id === $("#comparison-select").value);
    const payload = { source_id: sourceId, page: ws.page };
    if (comparison?.target_workspace_id === ws.id) payload.comparison_id = comparison.id;
    const data = await api(`/api/v2/workspaces/${encodeURIComponent(ws.id)}/differential-candidates`, {
      method: "POST", body: JSON.stringify(payload),
    });
    state.candidateResults = { sourceId, page: ws.page, data };
    renderFateInspector();
    const total = (data.candidates || []).length + (data.comparison_candidates || []).length;
    toast(`${total} review-only compatible candidate(s) found; none saved.`);
  } catch (error) {
    toast(error.message);
  } finally {
    if ($("#find-differential-candidates")) $("#find-differential-candidates").disabled = false;
  }
}

function renderComparisons() {
  const ws = workspace();
  const select = $("#comparison-select");
  const comparisons = state.project.comparisons.filter((item) => item.source_workspace_id === ws.id || item.target_workspace_id === ws.id);
  select.innerHTML = '<option value="">No comparison selected</option>' + comparisons.map((item) => `<option value="${item.id}">${escapeHtml(item.name)} · ${item.mode}</option>`).join("");
  showComparisonNote();
}

function showComparisonNote() {
  const comparison = state.project.comparisons.find((item) => item.id === $("#comparison-select").value);
  $("#comparison-note").textContent = comparison
    ? `${comparison.mode}: ${comparison.notes || "No notes supplied."}${comparison.source_ref ? ` Source: ${comparison.source_ref}.` : ""}`
    : "Choose a translation, restriction, transfer, norm, or Tate comparison.";
}

function renderProofTree() {
  const ws = workspace();
  const propositions = $("#proof-scope").value === "project" ? allPropositions() : ws.propositions.map((item) => ({ ...item, workspaceName: ws.name }));
  const lookup = new Map(allPropositions().map((item) => [item.id, item.statement]));
  $("#proposition-count").textContent = propositions.length;
  $("#proof-tree").innerHTML = propositions.map((item) => `<article class="proof-node ${escapeHtml(item.status)}"><strong>${escapeHtml(item.statement)}</strong><small>${escapeHtml(item.workspaceName)} · ${escapeHtml(item.rule)} · ${escapeHtml(item.status)} · ${(item.confidence * 100).toFixed(0)}%</small>${item.source_ref ? `<div class="source-ref">${escapeHtml(item.source_ref)}</div>` : ""}${item.premise_ids?.length ? `<div class="parents">depends on: ${item.premise_ids.map((id) => escapeHtml(lookup.get(id) || id)).join("; ")}</div>` : ""}</article>`).join("") || '<p class="empty">No propositions in this workspace.</p>';
  renderLogicGraph();
}

function renderLogicGraph() {
  const graph = state.logicGraph || { nodes: [], edges: [] };
  const projectScope = $("#proof-scope").value === "project";
  let visibleIds = new Set(graph.nodes.filter((item) => projectScope || item.workspace_id === state.workspaceId).map((item) => item.id));
  if (!projectScope) {
    const localIds = new Set(visibleIds);
    for (const edge of graph.edges) {
      if (localIds.has(edge.source) || localIds.has(edge.target)) {
        visibleIds.add(edge.source);
        visibleIds.add(edge.target);
      }
    }
  }
  const allVisible = graph.nodes.filter((item) => visibleIds.has(item.id));
  const nodes = allVisible.slice(0, projectScope ? 70 : 90);
  visibleIds = new Set(nodes.map((item) => item.id));
  const edges = graph.edges.filter((item) => visibleIds.has(item.source) && visibleIds.has(item.target));
  const columnFor = (kind) => {
    if (["source-reference", "c3-action"].includes(kind)) return 0;
    if (kind === "proposition") return 1;
    if (["differential-claim", "differential-event", "cross-graded-product"].includes(kind)) return 2;
    return 3;
  };
  const columns = [[], [], [], []];
  nodes.forEach((item) => columns[columnFor(item.kind)].push(item));
  const positions = new Map();
  columns.forEach((column, x) => column.forEach((item, y) => positions.set(item.id, { x: 18 + x * 150, y: 18 + y * 54 })));
  const height = Math.max(180, ...columns.map((column) => column.length * 54 + 28));
  const svg = $("#logic-graph");
  svg.setAttribute("viewBox", `0 0 590 ${height}`);
  let markup = '<defs><marker id="logic-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z"/></marker></defs>';
  for (const edge of edges) {
    const from = positions.get(edge.source);
    const to = positions.get(edge.target);
    markup += `<path class="logic-edge ${escapeHtml(edge.kind)}" d="M${from.x + 118},${from.y + 16} C${from.x + 135},${from.y + 16} ${to.x - 17},${to.y + 16} ${to.x},${to.y + 16}"><title>${escapeHtml(edge.kind)}</title></path>`;
  }
  for (const item of nodes) {
    const point = positions.get(item.id);
    const label = item.label.length > 23 ? `${item.label.slice(0, 22)}…` : item.label;
    markup += `<g class="logic-node ${escapeHtml(item.kind)}" data-logic-node="${escapeHtml(item.id)}" transform="translate(${point.x} ${point.y})"><rect width="118" height="33" rx="5"/><text x="7" y="13">${escapeHtml(item.kind)}</text><text class="logic-label" x="7" y="26">${escapeHtml(label)}</text><title>${escapeHtml(item.label)}</title></g>`;
  }
  svg.innerHTML = markup || '<text x="12" y="24">No graph nodes.</text>';
  svg.querySelectorAll("[data-logic-node]").forEach((node) => node.addEventListener("click", () => {
    const item = graph.nodes.find((candidate) => candidate.id === node.dataset.logicNode);
    $("#logic-node-detail").textContent = `${item.kind} · ${item.status || "no status"} · ${item.label}`;
  }));
  $("#logic-node-detail").textContent = allVisible.length > nodes.length
    ? `Showing ${nodes.length} of ${allVisible.length} typed nodes. Select a node for details.`
    : `${nodes.length} typed nodes · ${edges.length} visible evidence edges.`;
}

function renderSuggestions() {
  const root = $("#suggestion-list");
  if (!state.suggestions.length) {
    root.innerHTML = '<p class="empty">Run a rule to look for transparent, reviewable candidates.</p>';
    return;
  }
  root.innerHTML = state.suggestions.map((item, index) => `<article class="suggestion"><strong>${escapeHtml(item.statement)}</strong><span class="suggestion-meta">${escapeHtml(item.rule)} · ${(item.confidence * 100).toFixed(0)}%</span><p>${escapeHtml(item.notes || "Review the premises before accepting.")}</p><button data-accept="${index}" class="primary">Add to proof tree</button></article>`).join("");
  document.querySelectorAll("[data-accept]").forEach((button) => button.addEventListener("click", () => acceptSuggestion(Number(button.dataset.accept))));
}

async function acceptSuggestion(index) {
  const item = state.suggestions[index];
  if (!item) return;
  await api(`/api/workspaces/${state.workspaceId}/propositions`, { method: "POST", body: JSON.stringify({ ...item, status: "candidate" }) });
  state.suggestions.splice(index, 1);
  await loadProject();
  toast("Candidate added to the evidence graph.");
}

function classesForSector(sectorId) {
  const sector = atlasSector(sectorId);
  const ws = sector && state.project.workspaces.find((item) => item.id === sector.workspace_id);
  return (ws?.classes || []).filter((item) => !item.archived);
}

function fillProductClassSelect(sectorSelector, classSelector, preferred) {
  const classes = classesForSector($(sectorSelector).value);
  $(classSelector).innerHTML = classes.length
    ? classes.map((item) => `<option value="${item.id}">${escapeHtml(item.label)}</option>`).join("")
    : '<option value="">No computed classes</option>';
  if (classes.some((item) => item.id === preferred)) $(classSelector).value = preferred;
}

function renderProductControls() {
  const sectors = state.project.grading_sectors || [];
  const leftSector = $("#product-left-sector").value || sectors.find((item) => item.id === "q8-ro-a1-b0")?.id || sectors[0]?.id;
  const rightSector = $("#product-right-sector").value || sectors.find((item) => item.id === "q8-ro-a0-b2")?.id || sectors[0]?.id;
  const leftClass = $("#product-left-class").value;
  const rightClass = $("#product-right-class").value;
  const options = sectors.map((item) => `<option value="${item.id}">S(${item.a},${item.b}) · ${escapeHtml(item.status)}</option>`).join("");
  $("#product-left-sector").innerHTML = options;
  $("#product-right-sector").innerHTML = options;
  $("#product-left-sector").value = leftSector;
  $("#product-right-sector").value = rightSector;
  fillProductClassSelect("#product-left-sector", "#product-left-class", leftClass);
  fillProductClassSelect("#product-right-sector", "#product-right-class", rightClass);
  $("#product-page").value = workspace().page;
}

function productPayload() {
  return {
    left_sector_id: $("#product-left-sector").value,
    left_class_id: $("#product-left-class").value,
    right_sector_id: $("#product-right-sector").value,
    right_class_id: $("#product-right-class").value,
    page: Number($("#product-page").value),
  };
}

async function previewProduct() {
  try {
    const { preview } = await api("/api/v2/products/preview", { method: "POST", body: JSON.stringify(productPayload()) });
    $("#product-preview").innerHTML = `<strong>${escapeHtml(preview.resulting_expression)}</strong><br>lands in ${escapeHtml(preview.result_sector_id || "unknown")} · ${escapeHtml(preview.normalization_status)}${preview.normalization_path.length ? `<br>path: ${preview.normalization_path.map(escapeHtml).join(" → ")}` : ""}`;
    return preview;
  } catch (error) {
    $("#product-preview").textContent = error.message;
    return null;
  }
}

function dimensions() {
  const rect = $("#chart").getBoundingClientRect();
  return { width: Math.max(rect.width, 100), height: Math.max(rect.height, 100) };
}

function chartMetrics() {
  const grid = workspace().settings.grid || {};
  const { width, height } = dimensions();
  const margin = { left: 48, right: 24, top: 22, bottom: 36 };
  const baseCell = workspace().settings.rendering?.base_cell ?? 28;
  // The viewport bounds, not a finite grid, determine how much of the
  // upper half-plane is drawn at the current scale.
  const cell = clamp(baseCell * state.view.zoom, 1.5, 320);
  const baseAxisY = height - margin.bottom;
  const minimumAxisY = Math.max(margin.top + cell, height * 0.55);
  return {
    grid,
    width,
    height,
    margin,
    cell,
    baseAxisY,
    axisX: width / 2 + state.view.panX,
    axisY: baseAxisY + state.view.panY,
    minimumAxisY,
  };
}

function pointFor(grade, m = chartMetrics()) {
  return { x: m.axisX + (grade.stem + 0.5) * m.cell, y: m.axisY - (grade.filtration + 0.5) * m.cell };
}

function gradeFloatAt(x, y, m = chartMetrics()) {
  return { stem: (x - m.axisX) / m.cell - 0.5, filtration: (m.axisY - y) / m.cell - 0.5 };
}

function gradeAt(x, y) {
  const m = chartMetrics();
  return { stem: Math.floor((x - m.axisX) / m.cell), filtration: Math.floor((m.axisY - y) / m.cell) };
}

function generatorGradeAtChartPoint(localX, localY, metrics, minimumFiltration = 0, allowNegative = false) {
  if (!allowNegative && localY > metrics.axisY) return null;
  const grade = {
    stem: Math.floor((localX - metrics.axisX) / metrics.cell),
    filtration: Math.floor((metrics.axisY - localY) / metrics.cell),
  };
  return grade.filtration < minimumFiltration ? null : grade;
}

function viewportBounds(m, buffer = 0) {
  const start = gradeFloatAt(0, m.height, m);
  const end = gradeFloatAt(m.width, 0, m);
  return {
    stemMin: Math.floor(Math.min(start.stem, end.stem)) - buffer,
    stemMax: Math.ceil(Math.max(start.stem, end.stem)) + buffer,
    filtrationMin: Math.max(0, Math.floor(Math.min(start.filtration, end.filtration)) - buffer),
    filtrationMax: Math.max(0, Math.ceil(Math.max(start.filtration, end.filtration)) + buffer),
  };
}

function inBounds(grade, bounds) {
  return grade.stem >= bounds.stemMin && grade.stem <= bounds.stemMax && grade.filtration >= bounds.filtrationMin && grade.filtration <= bounds.filtrationMax;
}

function shiftRange(grade, period, bounds) {
  let low = Number.NEGATIVE_INFINITY;
  let high = Number.POSITIVE_INFINITY;
  let constrained = false;
  for (const [coordinate, delta, min, max] of [[grade.stem, period.stem, bounds.stemMin, bounds.stemMax], [grade.filtration, period.filtration, bounds.filtrationMin, bounds.filtrationMax]]) {
    if (!delta) {
      if (coordinate < min || coordinate > max) return [];
      continue;
    }
    constrained = true;
    const a = (min - coordinate) / delta;
    const b = (max - coordinate) / delta;
    low = Math.max(low, Math.ceil(Math.min(a, b)));
    high = Math.min(high, Math.floor(Math.max(a, b)));
  }
  if (!constrained) return [0];
  return low > high ? [] : Array.from({ length: high - low + 1 }, (_, index) => low + index);
}

function normalizedPeriod(stem, filtration) {
  const result = { stem: Number(stem) || 0, filtration: Number(filtration) || 0 };
  return result.stem || result.filtration ? result : null;
}

function usablePeriodFamily(differential) {
  if (!differential.period_family_id) return null;
  const family = (state.project.period_families || []).find((item) => item.id === differential.period_family_id);
  return family && ["reviewed", "established"].includes(family.status) ? family : null;
}

function periodsForClassOnPage(ws, item) {
  const periods = [];
  const add = (period) => {
    if (!period || periods.some((known) => known.stem === period.stem && known.filtration === period.filtration)) return;
    periods.push(period);
  };
  // Periodic copies require a reviewed/established PeriodFamily certificate.
  for (const differential of ws.differentials) {
    if (differential.page !== ws.page) continue;
    if (differential.source_id !== item.id && differential.target_id !== item.id) continue;
    if (!usablePeriodFamily(differential)) continue;
    add(normalizedPeriod(differential.period_stem, differential.period_filtration));
  }
  return periods;
}

function periodicClassInstances(ws, bounds) {
  const rendered = [];
  const seen = new Set();
  for (const item of liveClassesAt(ws)) {
    const periods = periodsForClassOnPage(ws, item);
    const copies = [{ grade: item.grade, shift: 0, periodic: false }];
    for (const period of periods) {
      for (const shift of shiftRange(item.grade, period, bounds)) {
        if (shift === 0) continue;
        copies.push({
          grade: { ...item.grade, stem: item.grade.stem + shift * period.stem, filtration: item.grade.filtration + shift * period.filtration },
          shift,
          periodic: true,
        });
      }
    }
    for (const copy of copies) {
      const key = `${item.id}:${copy.grade.stem}:${copy.grade.filtration}`;
      if (seen.has(key) || !inBounds(copy.grade, bounds)) continue;
      seen.add(key);
      rendered.push({ item, instanceKey: key, ...copy });
    }
  }
  return rendered;
}

function drawingPreviewCycleKey(cycle, index) {
  return String(cycle.plan_key || `unkeyed-preview:${index}:${cycle.grade?.stem}:${cycle.grade?.filtration}`);
}

function drawingPeriodicityPreviewInstances(bounds) {
  const preview = state.drawingPeriodicityPreview;
  if (!preview || preview.workspaceId !== state.workspaceId || preview.page !== workspace().page) return [];
  return drawingPreviewCycles(preview.data).flatMap((cycle, index) => {
    if (!cycle.grade || !inBounds(cycle.grade, bounds) || cycle.action === "reuse") return [];
    const planKey = drawingPreviewCycleKey(cycle, index);
    return [{
      preview: true,
      planKey,
      cycle,
      key: `manual-preview:${planKey}`,
      instanceKey: `manual-preview:${planKey}`,
      cellKey: `${cycle.grade.stem}:${cycle.grade.filtration}`,
      grade: cycle.grade,
      label: cycle.label || "",
      shape: "circle",
      size: 5.5,
    }];
  });
}

function packedClassInstances(ws, bounds, metrics, extraInstances = []) {
  const instances = periodicClassInstances(ws, bounds).map((record) => ({
    ...record,
    key: record.instanceKey,
    cellKey: `${record.grade.stem}:${record.grade.filtration}`,
    label: record.item.label,
    shape: glyphShapeFor(ws, record.item),
    size: record.periodic ? 4.2 : 5.5,
  }));
  return window.HFPSSCellLayout.packInstances([...instances, ...extraInstances], metrics.cell, { baseYOffset: 0.16 });
}

function packedPoint(record, metrics) {
  const base = pointFor(record.grade, metrics);
  return { x: base.x + record.dx, y: base.y + record.dy };
}

function classInstanceKey(classId, grade) {
  return `${classId}:${grade.stem}:${grade.filtration}`;
}

function classGlyphMarkup(record, point, classNames) {
  if (record.shape === "square") {
    return `<rect class="class-point square ${classNames}" x="${point.x - record.size}" y="${point.y - record.size}" width="${2 * record.size}" height="${2 * record.size}" rx="${Math.min(1.2, record.size * 0.2)}"/>`;
  }
  return `<circle class="class-point circle ${classNames}" cx="${point.x}" cy="${point.y}" r="${record.size}"/>`;
}

function classLabelMarkup(record, point, metrics, visible) {
  if (record.periodic || !inBounds(record.grade, visible)) return "";
  const base = pointFor(record.grade, metrics);
  const labelStep = Math.max(13, record.baseYOffset * metrics.cell);
  const labelCenterY = base.y + (record.packIndex - (record.packCount - 1) / 2) * labelStep;
  const labelX = base.x + Math.max(9, Math.min(18, metrics.cell * 0.45));
  return `<foreignObject class="label-host" x="${labelX}" y="${labelCenterY - 9}" width="180" height="18"><div xmlns="http://www.w3.org/1999/xhtml" class="latex-label" data-latex="${escapeHtml(record.item.label)}"></div></foreignObject>`;
}

function periodicDifferentials(ws, bounds) {
  const byId = new Map(ws.classes.map((item) => [item.id, item]));
  const liveIds = new Set(liveClassesAt(ws).map((item) => item.id));
  const results = [];
  for (const diff of ws.differentials.filter((item) => item.page === ws.page)) {
    const source = byId.get(diff.source_id);
    const target = byId.get(diff.target_id);
    if (!source || !target || !liveIds.has(source.id) || !liveIds.has(target.id)) continue;
    const period = usablePeriodFamily(diff) && (diff.period_stem || diff.period_filtration)
      ? { stem: diff.period_stem || 0, filtration: diff.period_filtration || 0 }
      : null;
    const shifts = period ? shiftRange(source.grade, period, bounds) : [0];
    for (const shift of shifts) {
      const sourceGrade = { ...source.grade, stem: source.grade.stem + shift * (period?.stem || 0), filtration: source.grade.filtration + shift * (period?.filtration || 0) };
      const targetGrade = { ...target.grade, stem: target.grade.stem + shift * (period?.stem || 0), filtration: target.grade.filtration + shift * (period?.filtration || 0) };
      if (inBounds(sourceGrade, bounds) || inBounds(targetGrade, bounds)) results.push({ diff, sourceGrade, targetGrade, periodic: shift !== 0 });
    }
  }
  return results;
}

function visibleRelations(ws, liveIds) {
  return ws.propositions.filter((proposition) => {
    if (proposition.kind !== "relation") return false;
    const sourceId = proposition.conclusion?.source_id;
    const targetId = proposition.conclusion?.target_id;
    const page = Number(proposition.conclusion?.page || 2);
    return sourceId && targetId && page <= ws.page && liveIds.has(sourceId) && liveIds.has(targetId);
  });
}

function constrainView() {
  if (!workspace()) return;
  state.view.zoom = clamp(state.view.zoom, 0.055, 16);
  const m = chartMetrics();
  // The only camera guard: never move the x-axis into the upper half.
  // Horizontal panning and movement toward arbitrarily high filtration remain free.
  state.view.panY = Math.max(state.view.panY, m.minimumAxisY - m.baseAxisY);
}

function renderMathInChart() {
  if (!window.katex) return;
  document.querySelectorAll(".latex-label[data-latex]").forEach((node) => katex.render(node.dataset.latex, node, { throwOnError: false, displayMode: false, trust: false }));
}

function drawingPeriodicityPreviewSvg(metrics, bounds, packedPreviewInstances, instancePoints, layer = "all") {
  const preview = state.drawingPeriodicityPreview;
  if (!preview || preview.workspaceId !== state.workspaceId || preview.page !== workspace().page) return "";
  const cycles = drawingPreviewCycles(preview.data);
  const plans = new Map([
    ...cycles,
    ...(preview.data?.existing_endpoint_copies || []),
  ].filter((plan) => plan.plan_key).map((plan) => [String(plan.plan_key), plan]));
  const packedByPlanKey = new Map(packedPreviewInstances.map((record) => [record.planKey, record]));
  const previewPoints = new Map(packedPreviewInstances.map((record) => [record.planKey, packedPoint(record, metrics)]));
  const endpointPoint = (planKey, fallbackGrade) => {
    const key = planKey == null ? "" : String(planKey);
    if (previewPoints.has(key)) return previewPoints.get(key);
    const plan = plans.get(key);
    if (plan?.class_id && plan.grade) {
      const persisted = instancePoints.get(classInstanceKey(plan.class_id, plan.grade));
      if (persisted) return persisted;
    }
    const grade = plan?.grade || fallbackGrade;
    return grade ? pointFor(grade, metrics) : null;
  };
  let markup = "";
  if (layer !== "cycles") {
    for (const connection of drawingPreviewConnections(preview.data)) {
      const sourceGrade = connection.source_grade || connection.source?.grade || connection.from_grade;
      const targetGrade = connection.target_grade || connection.target?.grade || connection.to_grade;
      if (!sourceGrade || !targetGrade || (!inBounds(sourceGrade, bounds) && !inBounds(targetGrade, bounds))) continue;
      const from = endpointPoint(connection.source_plan_key, sourceGrade);
      const to = endpointPoint(connection.target_plan_key, targetGrade);
      if (!from || !to) continue;
      const kind = connection.kind === "relation" ? "relation" : "differential";
      markup += `<line class="manual-period-preview connection ${kind}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"><title>${escapeHtml(connection.action || "preview")} ${kind}</title></line>`;
    }
  }
  if (layer !== "connections") {
    cycles.forEach((cycle, index) => {
      if (!cycle.grade || !inBounds(cycle.grade, bounds)) return;
      const planKey = drawingPreviewCycleKey(cycle, index);
      const point = endpointPoint(planKey, cycle.grade);
      if (!point) return;
      const packed = packedByPlanKey.get(planKey);
      const radius = packed?.size || clamp(metrics.cell * 0.2, 3.5, 7);
      markup += `<circle class="manual-period-preview cycle ${cycle.action === "reuse" ? "reuse" : "create"}" cx="${point.x}" cy="${point.y}" r="${radius}"><title>${escapeHtml(cycle.action || "preview")}: ${escapeHtml(cycle.label || "cycle")} at ${escapeHtml(gradeText(cycle.grade))}</title></circle>`;
    });
  }
  return markup;
}

function renderChart() {
  if (!workspace()) return;
  const ws = workspace();
  const svg = $("#chart");
  const m = chartMetrics();
  const buffer = ws.settings.rendering?.buffer_cells ?? 6;
  const visible = viewportBounds(m);
  const buffered = viewportBounds(m, buffer);
  $("#zoom-readout").textContent = `${Math.round(state.view.zoom * 100)}%`;
  $("#viewport-readout").textContent = `Upper half-plane · buffer: ${buffer} cells`;
  svg.setAttribute("viewBox", `0 0 ${m.width} ${m.height}`);

  let markup = '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#1f2937" /></marker><marker id="manual-preview-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#0891b2" /></marker></defs>';
  markup += `<rect class="plot-bg" x="0" y="0" width="${m.width}" height="${m.height}"/>`;
  const gridX = m.axisX + buffered.stemMin * m.cell;
  const gridY = m.axisY - (buffered.filtrationMax + 1) * m.cell;
  const gridWidth = (buffered.stemMax - buffered.stemMin + 1) * m.cell;
  const gridHeight = (buffered.filtrationMax - buffered.filtrationMin + 1) * m.cell;
  markup += `<rect class="feasible-bg" x="${gridX}" y="${gridY}" width="${gridWidth}" height="${gridHeight}"/>`;

  for (let stem = buffered.stemMin; stem <= buffered.stemMax + 1; stem += 1) {
    const x = m.axisX + stem * m.cell;
    markup += `<line class="${stem === 0 ? "axis" : "grid-line"}" x1="${x}" y1="${gridY}" x2="${x}" y2="${gridY + gridHeight}"/>`;
  }
  for (let filtration = buffered.filtrationMin; filtration <= buffered.filtrationMax + 1; filtration += 1) {
    const y = m.axisY - filtration * m.cell;
    markup += `<line class="${filtration === 0 ? "axis" : "grid-line"}" x1="${gridX}" y1="${y}" x2="${gridX + gridWidth}" y2="${y}"/>`;
  }
  const labelStep = Math.max(4, Math.ceil(44 / m.cell));
  if (m.axisY <= m.height) {
    for (let stem = buffered.stemMin; stem <= buffered.stemMax; stem += 1) {
      if (stem % labelStep) continue;
      const point = pointFor({ stem, filtration: 0 }, m);
      markup += `<text class="axis-text" x="${point.x}" y="${m.axisY + 19}">${stem}</text>`;
    }
  }
  for (let filtration = buffered.filtrationMin; filtration <= buffered.filtrationMax; filtration += 1) {
    if (filtration % labelStep) continue;
    const point = pointFor({ stem: buffered.stemMin, filtration }, m);
    markup += `<text class="axis-text y-axis-label" x="${gridX - 13}" y="${point.y + 3}">${filtration}</text>`;
  }

  const previewInstances = drawingPeriodicityPreviewInstances(buffered);
  const allPackedInstances = packedClassInstances(ws, buffered, m, previewInstances);
  const packedInstances = allPackedInstances.filter((record) => !record.preview);
  const packedPreviewInstances = allPackedInstances.filter((record) => record.preview);
  const instancePoints = new Map(packedInstances.map((record) => [record.instanceKey, packedPoint(record, m)]));
  const classesById = new Map(ws.classes.map((item) => [item.id, item]));
  const liveIds = new Set(liveClassesAt(ws).map((item) => item.id));
  markup += drawingPeriodicityPreviewSvg(m, buffered, packedPreviewInstances, instancePoints, "connections");
  for (const relation of visibleRelations(ws, liveIds)) {
    const source = classesById.get(relation.conclusion.source_id);
    const target = classesById.get(relation.conclusion.target_id);
    if (!source || !target) continue;
    const from = instancePoints.get(classInstanceKey(source.id, source.grade)) || pointFor(source.grade, m);
    const to = instancePoints.get(classInstanceKey(target.id, target.grade)) || pointFor(target.grade, m);
    const manualDrawing = relation.conclusion?.manual_periodicity_id ? "manual-drawing-periodic" : "";
    markup += `<line class="relation-line ${relationVisualState(relation)} ${manualDrawing}" data-relation="${escapeHtml(relation.id)}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"><title>${escapeHtml(relation.statement)}</title></line>`;
  }
  for (const item of periodicDifferentials(ws, buffered)) {
    const from = instancePoints.get(classInstanceKey(item.diff.source_id, item.sourceGrade)) || pointFor(item.sourceGrade, m);
    const to = instancePoints.get(classInstanceKey(item.diff.target_id, item.targetGrade)) || pointFor(item.targetGrade, m);
    const manualDrawing = item.diff.manual_periodicity_id ? "manual-drawing-periodic" : "";
    markup += `<line class="differential ${item.periodic ? "periodic" : ""} ${differentialVisualState(item.diff)} ${manualDrawing}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"/>`;
  }
  if (state.connectionStart && ["differential", "relation"].includes(state.tool)) {
    const source = classesById.get(state.connectionStart);
    const from = source && (instancePoints.get(classInstanceKey(source.id, source.grade)) || pointFor(source.grade, m));
    if (from) {
      const to = state.connectionPointer || from;
      markup += `<line id="connection-preview" class="connection-preview ${state.tool}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"/>`;
    }
  }
  for (const record of packedInstances) {
    const point = packedPoint(record, m);
    const selected = state.connectionStart === record.item.id || state.selectedClassId === record.item.id ? "selected" : "";
    const manualDrawing = record.item.manual_periodicity_id ? "manual-drawing-periodic" : "";
    const classes = `${visualStateFor(ws, record.item)} ${selected} ${record.periodic ? "periodic" : ""} ${manualDrawing}`;
    const label = classLabelMarkup(record, point, m, visible);
    const periodicAttribute = record.periodic ? ' data-periodic-copy="true"' : "";
    const aria = `${record.item.label} at ${gradeText(record.grade)}${record.periodic ? ", certified render copy" : ""}${manualDrawing ? ", manual periodic drawing record" : ""}`;
    markup += `<g class="class-instance" data-point="${record.item.id}" data-class-instance="${escapeHtml(record.instanceKey)}"${periodicAttribute} role="button" tabindex="0" aria-label="${escapeHtml(aria)}"><circle class="class-hit-target" cx="${point.x}" cy="${point.y}" r="${record.hitRadius}"/>${classGlyphMarkup(record, point, classes)}${label}</g>`;
  }
  markup += drawingPeriodicityPreviewSvg(m, buffered, packedPreviewInstances, instancePoints, "cycles");
  svg.innerHTML = markup;
  renderMathInChart();
  const activateClassInstance = (node, event) => {
    event.stopPropagation();
    if (state.suppressClick) {
      state.suppressClick = false;
      return;
    }
    if (node.dataset.periodicCopy && state.tool !== "inspect") return;
    onClassClick(node.dataset.point);
  };
  document.querySelectorAll("[data-point]").forEach((node) => {
    node.addEventListener("click", (event) => activateClassInstance(node, event));
    node.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      activateClassInstance(node, event);
    });
  });
}

function setPage(page) {
  workspace().page = clamp(Number(page), 2, pageLimit());
  state.connectionStart = null;
  state.candidateResults = null;
  state.periodicityPreview = null;
  state.drawingPeriodicityPreview = null;
  state.connectionPointer = null;
  render();
}

async function extendPageLimit() {
  const ws = workspace();
  const next = pageLimit(ws) + 1;
  try {
    const data = await api(`/api/workspaces/${ws.id}/settings`, { method: "PATCH", body: JSON.stringify({ page_limit: next }) });
    ws.settings = data.settings;
    state.history = await api("/api/history");
    renderHistoryControls();
    setPage(next);
    toast(`Added E${next} to this workspace.`);
  } catch (error) {
    toast(error.message);
    renderPageSelector();
  }
}

function setTool(tool) {
  state.tool = tool;
  state.connectionStart = null;
  state.connectionPointer = null;
  render();
}

async function onClassClick(id) {
  const item = workspace().classes.find((point) => point.id === id);
  if (!item) return;
  if (state.tool === "differential" || state.tool === "relation") {
    if (!state.connectionStart) {
      state.connectionStart = id;
      state.connectionPointer = null;
      toast(`Source: ${item.label}. Click the ${state.tool === "relation" ? "related" : "target"} class.`);
      renderChart();
    } else if (state.connectionStart === id) {
      state.connectionStart = null;
      state.connectionPointer = null;
      renderChart();
    } else if (state.tool === "differential") {
      await createDifferential(state.connectionStart, id);
    } else {
      await createRelation(state.connectionStart, id);
    }
    return;
  }
  if (state.tool === "delete") {
    try {
      await api(`/api/workspaces/${state.workspaceId}/classes/${id}`, { method: "DELETE" });
      await loadProject();
      state.selectedClassId = null;
      toast("Class archived; proof history retained.");
    } catch (error) { toast(error.message); }
    return;
  }
  if (state.tool === "rename") {
    const label = prompt("Class label (KaTeX accepted)", item.label);
    if (!label?.trim()) return;
    try {
      await api(`/api/workspaces/${state.workspaceId}/classes/${id}`, { method: "PATCH", body: JSON.stringify({ label }) });
      await loadProject();
      toast("Class renamed.");
    } catch (error) { toast(error.message); }
    return;
  }
  state.selectedClassId = item.id;
  state.candidateResults = null;
  state.periodicityPreview = null;
  renderFateInspector();
  renderPersistentPeriodicityTool();
  renderChart();
  toast(`${item.label} at ${gradeText(item.grade)} · ${fateFor(workspace(), item.id)?.conclusion || "unresolved"}`);
}

async function clearCurrentCanvas() {
  const ws = workspace();
  const activeCount = ws.classes.filter((item) => !item.archived).length;
  if (!activeCount) return toast("The current workspace canvas is already empty.");
  const confirmed = window.confirm(
    `Clear current canvas in “${ws.name}”?\n\nThis archives all ${activeCount} active dots in this workspace. Class records, differentials, relations, propositions, provenance, and fate history remain stored. Use Undo to restore the entire canvas in one step.`,
  );
  if (!confirmed) return;

  const button = $("#clear-current-canvas");
  button.disabled = true;
  try {
    const result = await api(`/api/workspaces/${encodeURIComponent(ws.id)}/clear-canvas`, { method: "POST" });
    state.selectedClassId = null;
    state.connectionStart = null;
    state.connectionPointer = null;
    state.candidateResults = null;
    state.periodicityPreview = null;
    state.drawingPeriodicityPreview = null;
    await loadProject();
    toast(result.changed
      ? `Archived ${result.archived_count} active dot${result.archived_count === 1 ? "" : "s"}; mathematical records were preserved. Use Undo to restore them.`
      : result.message);
  } catch (error) {
    toast(error.message);
  } finally {
    if ($("#clear-current-canvas")) $("#clear-current-canvas").disabled = false;
  }
}

async function createDifferential(source_id, target_id) {
  try {
    await api(`/api/workspaces/${state.workspaceId}/differentials`, { method: "POST", body: JSON.stringify({ source_id, target_id, page: workspace().page }) });
    state.connectionStart = null;
    state.connectionPointer = null;
    await loadProject();
    toast("Differential added with a provenance proposition.");
  } catch (error) { toast(error.message); }
}

async function createRelation(sourceId, targetId) {
  const source = workspace().classes.find((item) => item.id === sourceId);
  const target = workspace().classes.find((item) => item.id === targetId);
  try {
    await api(`/api/workspaces/${state.workspaceId}/propositions`, { method: "POST", body: JSON.stringify({ kind: "relation", statement: `Relation: ${source.label} ~ ${target.label}`, status: "candidate", conclusion: { source_id: sourceId, target_id: targetId, page: workspace().page }, rule: "manual", confidence: 0.5, notes: "Added from the chart relation tool; evidence remains to be supplied." }) });
    state.connectionStart = null;
    state.connectionPointer = null;
    await loadProject();
    toast("Relation recorded in the proposition tree.");
  } catch (error) { toast(error.message); }
}

function openClassDialog(stem, filtration) {
  const dialog = $("#class-dialog");
  dialog.querySelector("[name=stem]").value = stem;
  dialog.querySelector("[name=filtration]").value = filtration;
  dialog.showModal();
  renderClassLabelPreview();
  dialog.querySelector("[name=label]").focus();
}

function renderClassLabelPreview() {
  const input = $("#class-form [name=label]");
  const preview = $("#class-label-preview");
  if (!input || !preview) return;
  if (!window.katex) {
    preview.textContent = input.value || " ";
    return;
  }
  katex.render(input.value || " ", preview, { throwOnError: false, displayMode: false, trust: false });
}

function e2PresentationTemplate() {
  return {
    workspace_id: state.workspaceId,
    name: "Untitled explicit E2 presentation",
    source_ref: "",
    scope: "Explicit finite presentation supplied by a researcher.",
    convention_id: "q8-thesis-plotted-v1",
    coefficient_context_id: "formal-integer-presentation",
    coefficient_domain: "integers",
    generators: [
      { id: "x", label: "x", expression: "x", grade: { stem: 1, filtration: 1, representation: {} } },
      { id: "y", label: "y", expression: "y", grade: { stem: 2, filtration: 2, representation: {} } },
    ],
    relations: [
      { id: "x-square", lhs: { coefficient: 1, factors: { x: 2 } }, rhs: [{ coefficient: 1, factors: { y: 1 } }], source_ref: "" },
    ],
    polynomial: { terms: [{ coefficient: 1, factors: { x: 2 } }] },
  };
}

function showE2PresentationResult(value) {
  $("#e2-presentation-result").textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function e2PresentationPayload() {
  const raw = $("#e2-presentation-json").value;
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch (error) {
    throw new Error(`Invalid JSON: ${error.message}`);
  }
  if (!payload || Array.isArray(payload) || typeof payload !== "object") throw new Error("Presentation JSON must be an object.");
  payload.workspace_id = state.workspaceId;
  return payload;
}

function openE2PresentationDialog() {
  const dialog = $("#e2-presentation-dialog");
  $("#e2-presentation-json").value = JSON.stringify(e2PresentationTemplate(), null, 2);
  showE2PresentationResult("Choose Preview to validate without changing the project.");
  dialog.showModal();
  $("#e2-presentation-json").focus();
}

async function previewE2Presentation() {
  const button = $("#preview-e2-presentation");
  button.disabled = true;
  try {
    const data = await api("/api/v2/e2-presentations/preview", { method: "POST", body: JSON.stringify(e2PresentationPayload()) });
    showE2PresentationResult({
      persisted: data.persisted,
      validation: data.presentation.validation,
      normal_form: data.evaluation?.normal_form,
      limitation: "No dots, cohomology calculation, or differential was created by preview.",
    });
    toast("Explicit presentation validated without saving.");
  } catch (error) {
    showE2PresentationResult(`Preview failed: ${error.message}`);
    toast(error.message);
  } finally { button.disabled = false; }
}

async function materializeE2Presentation(event) {
  event.preventDefault();
  const button = $("#materialize-e2-presentation");
  button.disabled = true;
  try {
    const data = await api("/api/v2/e2-presentations", { method: "POST", body: JSON.stringify(e2PresentationPayload()) });
    $("#e2-presentation-dialog").close();
    await loadProject();
    toast(`Stored ${data.materialization.created_classes.length} explicit generator dot(s); no differential was inferred.`);
  } catch (error) {
    showE2PresentationResult(`Materialization failed: ${error.message}`);
    toast(error.message);
  } finally { button.disabled = false; }
}

async function runRules() {
  try {
    workspace().settings.vanishing_line = Number($("#vanishing-line").value);
    const data = await api(`/api/workspaces/${state.workspaceId}/suggestions`, { method: "POST", body: JSON.stringify({ rules: ["LeibnizRule", "VanishingLine"] }) });
    state.suggestions = data.suggestions;
    renderSuggestions();
    toast(`${state.suggestions.length} candidate(s) found.`);
  } catch (error) { toast(error.message); }
}

function renderProjectImportPreview(preview, fileName) {
  const target = $("#import-project-summary");
  const summary = preview.import?.summary || {};
  const counts = ["workspaces", "classes", "differentials", "propositions", "comparisons", "periodicity_rules"]
    .map((key) => `<li><strong>${escapeHtml(key.replaceAll("_", " "))}</strong>: ${Number(summary[key] || 0)}</li>`)
    .join("");
  const warnings = [
    preview.mathematical_status_policy,
    preview.import?.derived_caches_rebuilt ? "Derived fate and differential-event caches will be rebuilt from primary records." : "",
    preview.import?.migration_applied ? `Schema migration will be applied: v${preview.import.source_schema_version} to v${preview.import.schema_version}.` : "No schema migration is required.",
  ].filter(Boolean);
  target.innerHTML = `<p><strong>${escapeHtml(fileName)}</strong></p><p>Project: <strong>${escapeHtml(preview.project.name)}</strong> · revision ${preview.current_revision} → ${preview.would_revision}</p><ul class="import-counts">${counts}</ul><h3>Review warnings</h3><ul>${warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>`;
}

async function previewProjectImport(file) {
  const dialog = $("#import-project-dialog");
  const applyButton = $("#apply-project-import");
  state.importPreview = null;
  applyButton.disabled = true;
  $("#import-project-summary").textContent = `Reading ${file.name}...`;
  if (!dialog.open) dialog.showModal();
  try {
    const text = await file.text();
    const project = JSON.parse(text);
    const preview = await api("/api/project/import/preview", { method: "POST", body: JSON.stringify(project) });
    state.importPreview = preview;
    renderProjectImportPreview(preview, file.name);
    applyButton.disabled = false;
    toast("Import preview ready; review it before applying.");
  } catch (error) {
    $("#import-project-summary").innerHTML = `<p class="import-error"><strong>Preview failed.</strong> ${escapeHtml(error.message)}</p><p>The saved project was not changed.</p>`;
    toast(error.message);
  }
}

async function applyProjectImport() {
  const preview = state.importPreview;
  if (!preview) return;
  const button = $("#apply-project-import");
  button.disabled = true;
  try {
    const result = await api("/api/project/import/apply", {
      method: "POST",
      body: JSON.stringify({
        project: preview.project,
        preview_sha256: preview.preview_sha256,
        expected_revision: preview.current_revision,
      }),
    });
    $("#import-project-dialog").close("applied");
    state.importPreview = null;
    state.workspaceId = null;
    state.selectedClassId = null;
    state.view = { zoom: 1, panX: 0, panY: 0 };
    await loadProject();
    toast(`Imported reviewed project revision ${result.revision}.`);
  } catch (error) {
    $("#import-project-summary").insertAdjacentHTML("beforeend", `<p class="import-error">Apply failed: ${escapeHtml(error.message)} Preview again before retrying if the project changed.</p>`);
    toast(error.message);
  }
}

function resetView() {
  state.view = { zoom: 1, panX: 0, panY: 0 };
  constrainView();
  renderChart();
}

function onWheel(event) {
  if (!workspace()) return;
  event.preventDefault();
  const rect = event.currentTarget.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const before = gradeFloatAt(x, y);
  state.view.zoom = clamp(state.view.zoom * (event.deltaY < 0 ? 1.11 : 0.9), 0.055, 16);
  const after = pointFor(before);
  state.view.panX += x - after.x;
  state.view.panY += y - after.y;
  constrainView();
  renderChart();
}

function isTypingTarget(target) {
  return target instanceof Element && (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) || target.isContentEditable);
}

function handleHotkey(event) {
  const dialog = document.querySelector("dialog[open]");
  if (dialog?.open) {
    if (event.code === "Escape") {
      event.preventDefault();
      dialog.close("cancel");
    }
    return;
  }
  const commandKey = event.ctrlKey || event.metaKey;
  const typing = isTypingTarget(event.target) || isTypingTarget(document.activeElement);
  if (!event.defaultPrevented && !event.isComposing && commandKey && !event.altKey && !typing) {
    if (event.code === "KeyZ" && !event.shiftKey) {
      event.preventDefault();
      changeHistory("undo");
      return;
    }
    if (event.code === "KeyY" || (event.code === "KeyZ" && event.shiftKey)) {
      event.preventDefault();
      changeHistory("redo");
      return;
    }
  }
  if (event.defaultPrevented || event.isComposing || event.repeat || commandKey || event.altKey || typing) return;

  const toolKeys = { KeyV: "inspect", KeyG: "class", KeyD: "differential", KeyR: "relation", KeyX: "delete", KeyN: "rename" };
  if (toolKeys[event.code]) {
    event.preventDefault();
    setTool(toolKeys[event.code]);
    return;
  }
  if (event.code === "KeyE") { event.preventDefault(); runRules(); return; }
  if (event.code === "BracketLeft") { event.preventDefault(); setPage(workspace().page - 1); return; }
  if (event.code === "BracketRight") { event.preventDefault(); setPage(workspace().page + 1); return; }
  if (event.code === "Digit0" || event.code === "Numpad0") { event.preventDefault(); resetView(); return; }
  if (event.code === "Escape") {
    event.preventDefault();
    state.connectionStart = null;
    setTool("inspect");
  }
}

function bindEvents() {
  $("#workspace-select").addEventListener("change", (event) => {
    state.workspaceId = event.target.value;
    state.selectedClassId = null;
    state.suggestions = [];
    state.candidateResults = null;
    state.periodicityPreview = null;
    state.drawingPeriodicityPreview = null;
    state.view = { zoom: 1, panX: 0, panY: 0 };
    state.connectionStart = null;
    render();
  });
  $("#open-support-workspace").addEventListener("click", () => {
    const workspaceId = $("#support-workspace-select").value;
    if (!workspaceId) return;
    state.workspaceId = workspaceId;
    state.selectedClassId = null;
    state.suggestions = [];
    state.candidateResults = null;
    state.periodicityPreview = null;
    state.drawingPeriodicityPreview = null;
    state.view = { zoom: 1, panX: 0, panY: 0 };
    state.connectionStart = null;
    render();
  });
  $("#page-select").addEventListener("change", (event) => {
    if (event.target.value === "__add_page") extendPageLimit();
    else setPage(event.target.value);
  });
  $("#page-previous").addEventListener("click", () => setPage(workspace().page - 1));
  $("#page-next").addEventListener("click", () => {
    if (workspace().page >= pageLimit()) extendPageLimit();
    else setPage(workspace().page + 1);
  });
  $("#reset-view").addEventListener("click", resetView);
  $("#export-json").addEventListener("click", () => window.location.assign("/api/project/export"));
  $("#import-json").addEventListener("click", () => $("#import-json-file").click());
  $("#import-json-file").addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) previewProjectImport(file);
  });
  $("#apply-project-import").addEventListener("click", applyProjectImport);
  $("#cancel-project-import").addEventListener("click", () => {
    state.importPreview = null;
    $("#import-project-dialog").close("cancel");
  });
  $("#export-chart").addEventListener("click", () => downloadTex("chart"));
  $("#export-article").addEventListener("click", () => downloadTex("article"));
  $("#clear-current-canvas").addEventListener("click", clearCurrentCanvas);
  $("#undo-action").addEventListener("click", () => changeHistory("undo"));
  $("#redo-action").addEventListener("click", () => changeHistory("redo"));
  $("#proof-scope").addEventListener("change", renderProofTree);
  $("#comparison-select").addEventListener("change", showComparisonNote);
  document.querySelectorAll("[data-tool]").forEach((button) => button.addEventListener("click", () => setTool(button.dataset.tool)));
  $("#add-drawing-period-rule").addEventListener("click", addDrawingPeriodicityRule);
  $("#preview-drawing-period-box").addEventListener("click", () => previewDrawingPeriodicity("box"));
  $("#apply-drawing-period-box").addEventListener("click", () => applyDrawingPeriodicity("box"));
  $("#preview-drawing-diff-period").addEventListener("click", () => previewDrawingPeriodicity("differentials"));
  $("#apply-drawing-diff-period").addEventListener("click", () => applyDrawingPeriodicity("differentials"));
  [
    "#drawing-period-name", "#drawing-period-p", "#drawing-period-q",
    "#drawing-period-p-min", "#drawing-period-p-max", "#drawing-period-q-min", "#drawing-period-q-max",
    "#drawing-diff-period-p", "#drawing-diff-period-q",
  ].forEach((selector) => $(selector).addEventListener("input", () => {
    if (!state.drawingPeriodicityPreview) return;
    state.drawingPeriodicityPreview = null;
    renderDrawingPeriodicityTool();
    renderChart();
  }));
  $("#product-left-sector").addEventListener("change", () => fillProductClassSelect("#product-left-sector", "#product-left-class"));
  $("#product-right-sector").addEventListener("change", () => fillProductClassSelect("#product-right-sector", "#product-right-class"));
  $("#preview-product").addEventListener("click", previewProduct);
  $("#product-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const preview = await previewProduct();
    if (!preview) return;
    try {
      await api("/api/v2/products", { method: "POST", body: JSON.stringify(productPayload()) });
      await loadProject();
      toast("Cross-graded product candidate stored with its normalization evidence.");
    } catch (error) { toast(error.message); }
  });

  const chart = $("#chart");
  chart.addEventListener("click", (event) => {
    if (state.suppressClick) {
      state.suppressClick = false;
      return;
    }
    if (state.tool !== "class" || state.drag) return;
    const rect = chart.getBoundingClientRect();
    const localX = event.clientX - rect.left;
    const localY = event.clientY - rect.top;
    const m = chartMetrics();
    const minimumFiltration = workspace().spectral_sequence === "tate"
      ? Number(workspace().settings.grid?.filtration_min ?? -64)
      : 0;
    // Feasibility is determined by the cell boundary at the x-axis. A
    // center-shifted fractional grade is negative in the lower half of the
    // filtration-zero cell and must not be used as a click guard.
    const grade = generatorGradeAtChartPoint(
      localX, localY, m, minimumFiltration, workspace().spectral_sequence === "tate",
    );
    if (!grade) return;
    openClassDialog(grade.stem, grade.filtration);
  });
  chart.addEventListener("wheel", onWheel, { passive: false });
  chart.addEventListener("pointerdown", (event) => {
    const altDrag = event.button === 0 && event.altKey;
    if (!altDrag && event.button === 0 && state.tool === "inspect" && event.target.closest("[data-point]")) return;
    const selectDrag = state.tool === "inspect" && event.button === 0;
    const middleDrag = event.button === 1;
    if (!selectDrag && !middleDrag && !altDrag) return;
    event.preventDefault();
    state.drag = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, startX: event.clientX, startY: event.clientY, moved: false };
    chart.setPointerCapture(event.pointerId);
    chart.classList.add("panning");
  });
  chart.addEventListener("pointermove", (event) => {
    if (!state.drag || event.pointerId !== state.drag.pointerId) {
      if (state.connectionStart && ["differential", "relation"].includes(state.tool)) {
        const rect = chart.getBoundingClientRect();
        state.connectionPointer = { x: event.clientX - rect.left, y: event.clientY - rect.top };
        const preview = $("#connection-preview");
        if (preview) {
          preview.setAttribute("x2", state.connectionPointer.x);
          preview.setAttribute("y2", state.connectionPointer.y);
        }
      }
      return;
    }
    if (Math.abs(event.clientX - state.drag.startX) > 2 || Math.abs(event.clientY - state.drag.startY) > 2) state.drag.moved = true;
    state.view.panX += event.clientX - state.drag.x;
    state.view.panY += event.clientY - state.drag.y;
    state.drag.x = event.clientX;
    state.drag.y = event.clientY;
    constrainView();
    renderChart();
  });
  const stopDrag = (event) => {
    if (!state.drag || event.pointerId !== state.drag.pointerId) return;
    const moved = state.drag.moved;
    state.drag = null;
    chart.classList.remove("panning");
    if (moved) {
      state.suppressClick = true;
      requestAnimationFrame(() => { state.suppressClick = false; });
    }
  };
  chart.addEventListener("pointerup", stopDrag);
  chart.addEventListener("pointercancel", stopDrag);

  $("#class-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    if (!formElement.checkValidity()) {
      formElement.reportValidity();
      return;
    }
    const form = new FormData(formElement);
    const submit = $("#save-class");
    submit.disabled = true;
    try {
      const sector = (state.project.grading_sectors || []).find((item) => item.workspace_id === state.workspaceId);
      await api(`/api/workspaces/${state.workspaceId}/classes`, { method: "POST", body: JSON.stringify({ label: form.get("label"), expression: form.get("expression"), stem: Number(form.get("stem")), filtration: Number(form.get("filtration")), state: "unknown", page: workspace().page, representation: sector?.normal_form || {}, sector_id: sector?.id || null }) });
      $("#class-dialog").close();
      await loadProject();
      toast("Class added.");
    } catch (error) { toast(error.message); } finally { submit.disabled = false; }
  });
  $("#class-form [name=label]").addEventListener("input", renderClassLabelPreview);
  $("#cancel-class").addEventListener("click", () => $("#class-dialog").close("cancel"));
  $("#open-e2-presentation").addEventListener("click", openE2PresentationDialog);
  $("#preview-e2-presentation").addEventListener("click", previewE2Presentation);
  $("#e2-presentation-form").addEventListener("submit", materializeE2Presentation);
  $("#cancel-e2-presentation").addEventListener("click", () => $("#e2-presentation-dialog").close("cancel"));
  $("#run-rules").addEventListener("click", runRules);
  $("#run-comparison").addEventListener("click", async () => {
    const comparison_id = $("#comparison-select").value;
    if (!comparison_id) return toast("Choose a comparison first.");
    try {
      const data = await api(`/api/workspaces/${state.workspaceId}/suggestions`, { method: "POST", body: JSON.stringify({ rules: [], comparison_id }) });
      state.suggestions = data.suggestions;
      renderSuggestions();
      toast(`${state.suggestions.length} transported candidate(s) found.`);
    } catch (error) { toast(error.message); }
  });
  $("#clear-suggestions").addEventListener("click", () => { state.suggestions = []; renderSuggestions(); });
  $("#new-workspace").addEventListener("click", async () => {
    const name = prompt("Workspace name", "New RO(Q8) workspace");
    if (!name) return;
    await api("/api/workspaces", { method: "POST", body: JSON.stringify({ name, grading_label: "custom RO(Q8)" }) });
    await loadProject();
    state.workspaceId = state.project.workspaces.at(-1).id;
    state.view = { zoom: 1, panX: 0, panY: 0 };
    render();
  });
  $("#reset-demo").addEventListener("click", async () => {
    if (!confirm("Replace the saved local project with the illustrative research demo?")) return;
    await api("/api/project/reset-demo", { method: "POST" });
    state.workspaceId = null;
    state.suggestions = [];
    state.candidateResults = null;
    state.periodicityPreview = null;
    state.drawingPeriodicityPreview = null;
    state.view = { zoom: 1, panX: 0, panY: 0 };
    await loadProject();
    toast("Illustrative research demo restored.");
  });
  document.addEventListener("keydown", handleHotkey, true);
  window.addEventListener("resize", () => { syncLayoutHeight(); constrainView(); renderChart(); });
}

function downloadTex(kind) {
  if (!state.workspaceId) return;
  const page = workspace().page;
  window.location.assign(`/api/v2/render/workspaces/${encodeURIComponent(state.workspaceId)}/${kind}.tex?page=${encodeURIComponent(page)}`);
}

bindEvents();
loadProject().catch((error) => {
  document.body.innerHTML = `<pre>Unable to load HFPSS Studio: ${escapeHtml(error.message)}</pre>`;
});
