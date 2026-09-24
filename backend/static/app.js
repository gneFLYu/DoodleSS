const state = {
  project: null,
  savedProject: null,
  catalogEntries: [],
  catalogMode: false,
  logicGraph: { nodes: [], edges: [] },
  periodicFateLedger: null,
  history: { undo_depth: 0, redo_depth: 0, undo_label: null, redo_label: null },
  workspaceId: null,
  activeAtlasSectorId: null,
  pageByWorkspace: new Map(),
  selectedClassId: null,
  selectedOccurrence: null,
  selectedQuotientInstance: null,
  classFilter: "",
  selectedCellId: null,
  lastVectorResult: null,
  tool: "inspect",
  connectionStart: null,
  suggestions: [],
  candidateResults: null,
  periodicityPreview: null,
  drawingPeriodicityPreview: null,
  importPreview: null,
  importSource: null,
  drag: null,
  suppressClick: false,
  connectionPointer: null,
  pendingRenameId: null,
  pendingRelation: null,
  view: { zoom: 1, panX: 0, panY: 0 },
};

const $ = (selector) => document.querySelector(selector);
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
const PAGE_MODE = document.body.dataset.page || "researching";
let chartRenderFrame = 0;
let pageRenderFrame = 0;
let pageRenderRequest = null;
let chartPagePresentation = null;
let projectLoadSequence = 0;
let historyLoadSequence = 0;
let catalogManifestRequest = null;

const CURRENT_CATALOG_BY_SECTOR = {
  "q8-ro-a2-b0": "2sigma-dec30",
  "q8-ro-a3-b0": "3sigma-public",
  "q8-ro-a1-b2": "mixed-july20",
};

function scheduleChartRender() {
  if (chartRenderFrame) return;
  chartRenderFrame = requestAnimationFrame(() => {
    chartRenderFrame = 0;
    renderChart();
  });
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const responseText = await response.text();
  let data = {};
  try { data = responseText ? JSON.parse(responseText) : {}; }
  catch (_error) {
    if (!response.ok) throw new Error(`Request failed (${response.status}). The server rejected or could not process the payload.`);
    throw new Error("The server returned an unreadable response.");
  }
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function workspace() {
  return state.project?.workspaces.find((item) => item.id === state.workspaceId);
}

function readOnlyCatalog(ws = workspace()) {
  return Boolean(state.catalogMode && ws?.settings?.read_only_catalog);
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
  if (readOnlyCatalog(ws)) {
    selector.innerHTML = `<option value="${ws.id}">[read-only archive] ${escapeHtml(ws.name)}</option>`;
    selector.value = ws.id;
    selector.disabled = true;
    $("#support-workspace-select").innerHTML = "";
    $("#open-support-workspace").disabled = true;
    return;
  }
  selector.disabled = false;
  const ordinary = ordinaryWorkspaces();
  const currentIsOrdinary = ordinary.some((item) => item.id === ws.id);
  const option = item => `<option value="${item.id}">${escapeHtml(workspaceDisplayName(item))}</option>`;
  const computed = ordinary.filter(item => !item.settings?.atlas_transport);
  const transported = ordinary.filter(item => item.settings?.atlas_transport);
  selector.innerHTML = `${currentIsOrdinary ? "" : option(ws)}<optgroup label="Computed representatives">${computed.map(option).join("")}</optgroup>${transported.length ? `<optgroup label="Isomorphic atlas pages">${transported.map(option).join("")}</optgroup>` : ""}`;
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
    // A coefficient port can die while its cell retains a kernel or j-tail.
    // The occurrence algebra below resolves those subquotients separately.
    if ((item.style?.e2_pattern || item.style?.e2_components) && window.HFPSSPageAlgebra) return true;
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
  // DKLLW class glyphs describe the coefficient/module pattern. They are
  // independent of the page-fate color supplied by visualStateFor().
  const raw = item.style?.module_pattern
    || item.style?.dkllw_glyph
    || item.style?.glyph
    || "dot";
  const normalized = String(raw).trim().toLowerCase().replaceAll("_", "-").replaceAll(" ", "-");
  if (["fat-dot", "blue-dot"].includes(normalized)) return "fat-dot";
  if (["circle", "red-dot"].includes(normalized)) return "circle";
  if (normalized === "square") return "square";
  if (normalized === "j-series") return "j-series";
  if (normalized === "j-positive-series") return "j-positive-series";
  if (normalized === "witt-j-series") return "witt-j-series";
  if (normalized === "dot") return "dot";
  return "unknown";
}

function differentialVisualState(differential) {
  return ["derived", "reviewed", "established", "proven", "admitted", "admitted-pattern", "verified-pattern", "verified", "source-verified"].includes(differential.status) ? "accepted" : "under-review";
}

function relationVisualState(proposition) {
  return ["derived", "reviewed", "established", "proven", "verified", "source-verified"].includes(proposition.status) ? "accepted" : "under-review";
}

function escapeHtml(value) {
  const node = document.createElement("span");
  node.textContent = value ?? "";
  return node.innerHTML;
}

function mathMarkup(value) {
  const source = String(value ?? "");
  if (window.katex?.renderToString) {
    try { return window.katex.renderToString(source, {throwOnError: false, trust: false, displayMode: false}); }
    catch (_) { /* Keep source labels readable when a renderer is unavailable. */ }
  }
  // Retain the source for hydration if the optional renderer arrives later.
  return `<span data-math-source="${encodeURIComponent(source)}">${escapeHtml(source)}</span>`;
}

function hydrateMathLabels() {
  if (!window.katex?.renderToString) return;
  document.querySelectorAll("[data-math-source]").forEach(node => {
    node.outerHTML = mathMarkup(decodeURIComponent(node.dataset.mathSource));
  });
  if (PAGE_MODE === "researching" && workspace()) renderMathInChart();
  syncLayoutHeight();
}

function mathTextMarkup(value) {
  const source = String(value ?? "");
  const pieces = source.split(/(\\\([\s\S]*?\\\)|\\\[[\s\S]*?\\\]|\$[^$]+\$)/g);
  return pieces.map(piece => {
    if (piece.startsWith("\\(") || piece.startsWith("\\[")) return mathMarkup(piece.slice(2, -2));
    if (piece.startsWith("$") && piece.endsWith("$")) return mathMarkup(piece.slice(1, -1));
    // Entire formula statements are common in the proposition ledger.
    if (/^(?:d_\{?\d|\\(?:omega|psi|zeta)|[a-zA-Z]_\{)/.test(piece) && !/\b(?:is|the|with|from)\b/.test(piece)) return mathMarkup(piece);
    return escapeHtml(piece);
  }).join("");
}

function compactSectorLabel(value) {
  const sector = typeof value === "string" ? atlasSector(value) : value;
  if (!sector) return String(value || "*").replace(/^q8-ro-a(\d+)-b(\d+)$/, (_, a, b) => compactSectorLabel({a: Number(a), b: Number(b)}));
  return `*${Number(sector.a) ? `-${Number(sector.a) === 1 ? "" : sector.a}i` : ""}${Number(sector.b) ? `-${Number(sector.b) === 1 ? "" : sector.b}j` : ""}`;
}

function workspaceDisplayName(ws) {
  const sector = (state.project?.grading_sectors || []).find(item => item.workspace_id === ws.id);
  return sector ? `Q8 HFPSS · ${compactSectorLabel(sector)}` : ws.name;
}

function e2OrientationPattern(ws) {
  const pattern = ws?.settings?.rendering?.enumerated_e2_pattern;
  if (pattern === "integer") return "oriented";
  if (pattern === "sigma_i") return "non-oriented";
  return "unspecified";
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
  const sequence = ++projectLoadSequence;
  const previousWorkspaceId = state.workspaceId;
  const previousPage = previousWorkspaceId
    ? (state.pageByWorkspace.get(previousWorkspaceId) ?? workspace()?.page)
    : null;
  const project = await api("/api/project");
  if (sequence !== projectLoadSequence) return;
  state.project = project;
  state.catalogMode = false;
  state.savedProject = null;
  state.history = {undo_depth: 0, redo_depth: 0};
  if (!state.project.workspaces.some((item) => item.id === state.workspaceId)) state.workspaceId = defaultWorkspaceId();
  if (previousWorkspaceId === state.workspaceId && previousPage != null) {
    workspace().page = clamp(Number(previousPage) || 2, 2, pageLimit(workspace()));
    state.pageByWorkspace.set(state.workspaceId, workspace().page);
  } else if (workspace()) {
    const remembered = state.pageByWorkspace.get(state.workspaceId);
    workspace().page = clamp(Number(remembered ?? workspace().page) || 2, 2, pageLimit(workspace()));
    state.pageByWorkspace.set(state.workspaceId, workspace().page);
  }
  refreshSelectedOccurrence();
  render();
  // History is not needed to paint or inspect the chart. A failed/stale
  // history request must neither blank the chart nor enable obsolete Undo.
  void refreshHistory(project, sequence);
}

async function refreshHistory(project, sequence) {
  const historySequence = ++historyLoadSequence;
  try {
    const history = await api("/api/history");
    if (sequence !== projectLoadSequence || historySequence !== historyLoadSequence || state.project !== project) return;
    state.history = history;
    renderHistoryControls();
  } catch (error) {
    if (sequence === projectLoadSequence && historySequence === historyLoadSequence && state.project === project) {
      toast(`Chart loaded; history unavailable: ${error.message}`);
    }
  }
}

function refreshSelectedOccurrence() {
  const selected = state.selectedOccurrence;
  if (!selected) return;
  const ws = workspace();
  if (!ws || selected.workspaceId !== ws.id || selected.page !== ws.page
      || selected.classId !== state.selectedClassId) {
    state.selectedOccurrence = null;
    return;
  }
  const {stem, filtration} = selected.grade;
  const record = periodicClassInstances(ws, {
    stemMin: stem, stemMax: stem, filtrationMin: filtration, filtrationMax: filtration,
  }).find(item => item.item.id === selected.classId);
  state.selectedOccurrence = record ? {...selected, instanceKey: record.instanceKey,
    grade: {...record.grade}, label: periodicDisplayLabel(record)} : null;
}

async function loadLegacyCatalogManifest() {
  // The archive is optional and collapsed on startup. Share concurrent opens
  // and retain the loaded manifest, but allow a failed request to be retried.
  if (!catalogManifestRequest) catalogManifestRequest = api("/api/v2/legacy-catalog").catch(error => {
    catalogManifestRequest = null;
    throw error;
  });
  const data = await catalogManifestRequest;
  if (state.catalogEntries === data.entries) return;
  state.catalogEntries = data.entries || [];
  const selector = $("#legacy-catalog-select");
  selector.innerHTML = state.catalogEntries.map((entry) => (
    `<option value="${escapeHtml(entry.id)}">[${escapeHtml(entry.status)}] ${escapeHtml(entry.title)}</option>`
  )).join("");
  $("#open-legacy-catalog").disabled = !state.catalogEntries.length;
  if (state.project) renderGradingAtlas();
}

function catalogProject(project, ws) {
  return {
    ...project,
    workspaces: [ws],
    comparisons: [],
    page_period_cycles: [],
    drawing_periodicity_rules: [],
    manual_periodicities: [],
    manual_periodicity_rules: [],
    products: [],
  };
}

async function openLegacyCatalog() {
  await loadLegacyCatalogManifest();
  const entryId = $("#legacy-catalog-select").value;
  if (!entryId) return;
  return openLegacyCatalogEntry(entryId);
}

async function openLegacyCatalogEntry(entryId) {
  const button = $("#open-legacy-catalog");
  button.disabled = true;
  try {
    const data = await api(`/api/v2/legacy-catalog/${encodeURIComponent(entryId)}`);
    if (!state.catalogMode) state.savedProject = state.project;
    state.catalogMode = true;
    state.project = catalogProject(state.savedProject, data.workspace);
    state.workspaceId = data.workspace.id;
    state.selectedClassId = null;
    state.classFilter = "";
    state.tool = "inspect";
    state.connectionStart = null;
    state.view = { zoom: 1, panX: 0, panY: 0 };
    render();
    fitViewToData();
    toast(`Opened ${data.workspace.name} as a read-only research chart.`);
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
  }
}


async function closeLegacyCatalog() {
  state.activeAtlasSectorId = null;
  await loadProject();
  toast("Returned to the saved Studio project.");
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
  }).join("") + (readOnlyCatalog(ws) ? "" : `<option value="__add_page">+ Add E${maximum + 1}</option>`);
  select.value = current;
  $("#page-previous").disabled = current <= 2;
  $("#page-next").disabled = readOnlyCatalog(ws) && current >= maximum;
}

function renderLegacyCatalogState(ws) {
  const entry = ws.settings.catalog_entry;
  const active = readOnlyCatalog(ws) && entry;
  document.body.classList.toggle("catalog-mode", Boolean(active));
  $("#close-legacy-catalog").hidden = !active;
  $("#legacy-catalog-summary").hidden = !active;
  if (active) {
    $("#legacy-catalog-select").value = entry.id;
    const stats = entry.statistics;
    $("#legacy-catalog-summary").innerHTML = `<strong>${escapeHtml(entry.status)} · ${escapeHtml(entry.authority)}</strong><span>${stats.generators} generators · ${stats.connections} connections · ${stats.differentials} differentials · ${stats.periodicity_rules} drawing-period rules</span><span>${escapeHtml(entry.filename)}</span><span>${escapeHtml(entry.evidence_ref)}</span><em>Read-only visual record; unlinked edges are not admitted as theorems.</em>`;
  }
  const blockedIds = [
    "export-json", "export-legacy-json", "import-json", "new-workspace", "export-chart", "export-article",
    "clear-current-canvas", "reset-demo", "run-rules", "open-cell-editor", "open-matrix-editor",
  ];
  blockedIds.forEach((id) => { const node = $(`#${id}`); if (node) node.disabled = Boolean(active); });
  document.querySelectorAll('[data-tool]:not([data-tool="inspect"])').forEach((button) => { button.disabled = Boolean(active); });
}

function pageStatusText(ws, algebra = null) {
  const conflicts = algebra?.conflicts || [];
  if (conflicts.length) {
    const count = new Set(conflicts.map(item => JSON.stringify([item.page, item.block || item.id, item.reason]))).size;
    return `E${ws.page}: partial / unknown quotient — ${count} unresolved map conditions. ${conflicts[0].reason || "Incomplete differential data"}. Potential representatives are provisional; a complete quotient is not claimed.`;
  }
  const documentedLimit = Number(ws.settings.known_page_max || 0);
  const claims = new Map((ws.propositions || []).map(claim => [claim.id, claim]));
  const verifiedPages = (ws.differentials || []).filter(diff => {
    const claim = claims.get(diff.proposition_id), conclusion = claim?.conclusion;
    return diff.status === "verified" && claim?.status === "verified"
      && conclusion?.admission_status === "verified"
      && conclusion.verification_certificate?.status === "verified"
      && Number.isInteger(diff.page) && diff.page >= 2
      && (!algebra?.canApply || algebra.canApply(diff));
  }).map(diff => diff.page);
  const latestVerified = Math.max(0, ...verifiedPages);
  const convergence = ws.settings.convergence || {};
  return convergence.status === "published-complete" && ws.page >= Number(convergence.stable_from_page || 0)
    ? `DKLLW Tables 8–9 conclude E${convergence.stable_from_page} = E∞ with filtration ≥ ${ws.settings.vanishing_line} empty. This chart applies the table maps and their documented products; no filtration clipping is used.`
    : convergence.status === "published-complete"
      ? `DKLLW table equations and documented product families; showing E${ws.page}. The current d${ws.page} is drawn before taking its quotient.`
      : documentedLimit && latestVerified + 1 > documentedLimit && ws.page >= documentedLimit
        ? `Showing E${ws.page}; verified differential families are recorded through d${latestVerified}. This is not a complete-page or convergence claim.`
      : documentedLimit && ws.page >= documentedLimit
        ? `E${documentedLimit} is the latest documented page; later pages are available for workspace additions.`
        : `Showing E${ws.page}; d${ws.page} is drawn only on this page.`;
}

function render() {
  const ws = workspace();
  if (!ws) return;
  ws.page = clamp(Number(ws.page) || 2, 2, pageLimit(ws));
  beginChartPageRender(ws);
  const visibleClasses = liveClassesAt(ws);
  renderWorkspaceNavigation(ws);
  renderPageSelector();
  renderHistoryControls();
  renderLegacyCatalogState(ws);
  $("#chart").dataset.tool = state.tool;

  $("#workspace-title").textContent = workspaceDisplayName(ws);
  $("#workspace-meta").textContent = `${ws.group} · ${ws.theory} · characteristic ${ws.characteristic} · ${ws.grading_label} · ${e2OrientationPattern(ws)} E2 pattern`;
  $("#workspace-summary").textContent = ws.summary || "No research summary has been recorded for this workspace.";
  $("#page-label").textContent = `E${ws.page}`;
  if ($("#vanishing-line")) $("#vanishing-line").value = ws.settings.vanishing_line || 0;
  renderClassList(ws, visibleClasses);
  $("#tool-hint").textContent = toolHint();
  document.querySelectorAll("[data-tool]").forEach((button) => button.classList.toggle("active", button.dataset.tool === state.tool));
  renderComparisons();
  renderGradingAtlas();
  renderAtlasPath(ws);
  renderFateInspector();
  renderCellInspector();
  renderPagePeriodTool();
  renderDrawingPeriodicityTool();
  renderPersistentPeriodicityTool();
  renderProductControls();
  renderSuggestions();
  constrainView();
  renderChart();
  syncLayoutHeight();
}

function renderClassList(ws = workspace(), visibleClasses = liveClassesAt(ws)) {
  const query = String(state.classFilter || "").trim().toLowerCase();
  const matching = query ? visibleClasses.filter((item) => {
    const coordinates = `${item.grade.stem},${item.grade.filtration}`;
    return `${item.label} ${item.expression || ""} ${coordinates}`.toLowerCase().includes(query);
  }) : visibleClasses;
  const limit = 250;
  const listed = matching.slice(0, limit);
  $("#class-count").textContent = matching.length === visibleClasses.length
    ? `${visibleClasses.length}${matching.length > limit ? ` · first ${limit}` : ""}`
    : `${matching.length}/${visibleClasses.length}${matching.length > limit ? ` · first ${limit}` : ""}`;
  $("#class-list").innerHTML = listed.map((item) => `<button class="class-row ${state.selectedClassId === item.id ? "active" : ""}" data-class="${item.id}"><span><i class="badge ${visualStateFor(ws, item)}"></i><span class="class-formula">${mathMarkup(item.label)}</span></span><span class="coords">${item.grade.stem}, ${item.grade.filtration}</span></button>`).join("") || '<p class="empty">No matching surviving classes on this page.</p>';
  $("#class-list").querySelectorAll("[data-class]").forEach((button) => button.addEventListener("click", () => onClassClick(button.dataset.class)));
}

function syncLayoutHeight() {
  const modeBar = document.querySelector(".mode-bar");
  const toolbar = document.querySelector(".legacy-toolbar");
  const height = (modeBar?.offsetHeight || 0) + (toolbar?.offsetHeight || 0);
  document.documentElement.style.setProperty("--toolbar-height", `${height}px`);
}

function renderHistoryControls() {
  const undo = $("#undo-action");
  const redo = $("#redo-action");
  undo.disabled = readOnlyCatalog() || !state.history.undo_depth;
  redo.disabled = readOnlyCatalog() || !state.history.redo_depth;
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

function renderAtlasPath(ws) {
  const root = $("#c3-summary");
  if (!root) return;
  const plan = ws.settings?.atlas_transport;
  if (!plan) { root.textContent = ws.settings?.atlas_representative ? "Independent computation · ω: i → j → k → i; ψ: j ↔ k, ζ ↔ ζ²." : ""; return; }
  const source = (state.project.grading_sectors || []).find(s => s.workspace_id === plan.source_workspace_id);
  const action = `${plan.omega_power ? (plan.omega_power === 1 ? "ω" : "ω²") : ""}${plan.reflected ? "ψ" : ""}` || "identity";
  const shift = Number(plan.stem_shift) || 0;
  root.textContent = `${compactSectorLabel(source)} → ${compactSectorLabel(plan.sector_id)} via ${action}${shift ? `, Picard stem ${shift > 0 ? "+" : ""}${shift}` : ""}. Actions compose right to left. ψ: j ↔ k, ζ ↔ ζ².`;
  root.title = (plan.normalization?.obligations || []).join(" ");
}

function renderGradingAtlas() {
  const root = $("#grading-atlas");
  const sectors = state.project.grading_sectors || [];
  root.innerHTML = sectors.map((sector) => {
    const active = sector.workspace_id === state.workspaceId ? "active" : "";
    const count = sector.class_ids?.length || 0;
    const catalog = state.catalogEntries.find((entry) => entry.id === CURRENT_CATALOG_BY_SECTOR[sector.id]);
    const transportInfo = state.project.workspaces.find(w => w.id === sector.workspace_id)?.settings.atlas_transport;
    const transport = transportInfo ? `${transportInfo.action} · ${Number(transportInfo.stem_shift) >= 0 ? "+" : ""}${transportInfo.stem_shift}` : "";
    const detail = transport || (count ? `${count} anchors` : "not computed");
    const archiveHint = catalog ? ` · ${catalog.status} legacy source chart remains in the archive selector` : "";
    return `<button type="button" class="atlas-cell ${active} ${escapeHtml(sector.status)}" data-sector="${sector.id}" title="${escapeHtml(sector.display_label)} · ${escapeHtml(transport || sector.status)}${escapeHtml(archiveHint)}"><strong>S<sub>${sector.a},${sector.b}</sub></strong><span>${escapeHtml(detail)}</span></button>`;
  }).join("");
  root.querySelectorAll("[data-sector]").forEach((button) => button.addEventListener("click", () => selectAtlasSector(button.dataset.sector)));
}

async function selectAtlasSector(sectorId) {
  const sector = atlasSector(sectorId);
  if (!sector) return;
  state.activeAtlasSectorId = sectorId;
  {
    if (state.catalogMode) {
      state.project = state.savedProject;
      state.savedProject = null;
      state.catalogMode = false;
    }
    state.workspaceId = sector.workspace_id;
    state.selectedClassId = null;
    state.connectionStart = null;
    state.view = { zoom: 1, panX: 0, panY: 0 };
    render();
  }
  try {
    const preview = await api(`/api/v2/c3-actions/omega/orbit/${sectorId}`);
    const targets = preview.orbit.map((item) => item.result_sector_id ? compactSectorLabel(item.result_sector_id) : item.display_label).join(" → ");
    const period = preview.periodic_transport
      ? ` Picard transport: stem ${preview.periodic_transport.stem_shift}, ${preview.periodic_transport.relation}.`
      : "";
    renderAtlasPath(workspace());
    $("#c3-summary").title = `ω orbit: ${targets}.${period} ${$("#c3-summary").title}`;
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
  const selected = state.selectedOccurrence;
  const occurrence = selected?.workspaceId === ws.id && selected.page === ws.page && selected.classId === node.id ? selected : null;
  $("#fate-status").textContent = fate.conclusion.replaceAll("_", " ");
  $("#fate-inspector").innerHTML = `
    <strong>${mathMarkup(occurrence?.label || node.label)}</strong>
    ${occurrence ? `<p class="selected-bidegree">Selected occurrence: (${occurrence.grade.stem}, ${occurrence.grade.filtration}) · E${ws.page}</p>` : ""}
    ${node.style?.atlas_display_basis ? `<dl class="class-inspector-details"><dt>Family anchor: unscaled basis</dt><dd>${mathMarkup(node.style.atlas_display_basis.expression)}</dd><dt>Family anchor: transported element</dt><dd>${mathMarkup(node.style.atlas_display_basis.expanded_expression)}</dd><dt>Thom basis</dt><dd>${escapeHtml(node.style.atlas_display_basis.thom_provenance?.external_thom_normalization || node.style.atlas_display_basis.thom_basis)}</dd></dl>` : ""}
    <dl class="class-inspector-details"><dt>Grade</dt><dd>${escapeHtml(gradeText(occurrence?.grade || node.grade))}</dd><dt>Representation</dt><dd>${escapeHtml(representation)}</dd><dt>Display state</dt><dd>${escapeHtml(visualStateFor(ws, node))}</dd><dt>Convention</dt><dd>${escapeHtml(node.convention_id || "unspecified")}</dd><dt>Coefficient context</dt><dd>${escapeHtml(node.coefficient_context_id || "unspecified")}</dd></dl>
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
  if (!rulesRoot) return;
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
    if (mode === "box") {
      state.drawingPeriodicityPreview = {
        ...preview,
        virtual: true,
      };
      renderDrawingPeriodicityTool();
      renderChart();
      toast("Live periodicity view active for this page and viewport; no dots were materialized.");
      return;
    }
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

function pagePeriodEligible(ws, cycle, page = ws.page) {
  if (page <= Number(cycle.declared_page)) return true;
  if (!cycle.cycle_class_id) return false;
  const rejected = new Set(["rejected", "disproven", "invalid"]);
  for (let transition = Number(cycle.declared_page); transition < page; transition += 1) {
    if (ws.differentials.some((item) => (
      item.page === transition
      && !rejected.has(item.status)
      && [item.source_id, item.target_id].includes(cycle.cycle_class_id)
    ))) return false;
  }
  return liveClassesAt(ws, page).some((item) => item.id === cycle.cycle_class_id);
}

function detectedAlgebraGenerators(ws) {
  const ignored = new Set(["cdot", "frac", "left", "right", "mathbb", "mathrm", "operatorname"]);
  const names = new Set();
  liveClassesAt(ws).forEach((item) => {
    (item.label.match(/\\[A-Za-z]+|[A-Za-z]+(?:_[A-Za-z0-9]+)?/g) || []).forEach((token) => {
      const name = token.replace(/^\\/, "");
      if (!ignored.has(name)) names.add(name);
    });
  });
  return [...names].sort((left, right) => left.localeCompare(right));
}

function explicitCells(ws = workspace()) {
  return (ws?.cells || []).filter((item) => !item.archived);
}

function activeDifferentialMaps(ws = workspace()) {
  return (ws?.differential_maps || []).filter((item) => !item.archived);
}

function selectedCell() {
  return explicitCells().find((item) => item.id === state.selectedCellId) || null;
}

function vectorText(vector) {
  return `[${(vector || []).join(":")}]`;
}

function matrixText(matrix) {
  if (!matrix?.length) return "zero codomain";
  return matrix.map((row) => `[${row.join(", ")}]`).join("; ");
}

function renderCellInspector() {
  const ws = workspace();
  const cells = explicitCells(ws);
  const select = $("#cell-select");
  if (!select) return;
  if (!cells.some((item) => item.id === state.selectedCellId)) state.selectedCellId = cells[0]?.id || null;
  select.innerHTML = '<option value="">No explicit cell selected</option>' + cells.map((cell) => (
    `<option value="${escapeHtml(cell.id)}">rank ${cell.basis.length} · ${escapeHtml(gradeText(cell.grade))}</option>`
  )).join("");
  select.value = state.selectedCellId || "";
  const cell = selectedCell();
  const inspector = $("#cell-inspector");
  const mapSelect = $("#cell-vector-map");
  if (!cell) {
    $("#cell-status").textContent = "none";
    inspector.innerHTML = '<p class="empty">Select or create an explicit F4 cell. Legacy classes remain independent rank-one adapters.</p>';
    mapSelect.innerHTML = '<option value="">Choose a map</option>';
    return;
  }
  $("#cell-status").textContent = `rank ${cell.basis.length}`;
  const maps = activeDifferentialMaps(ws).filter((item) => item.source_cell_id === cell.id || item.target_cell_id === cell.id);
  const basis = cell.basis.map((item, index) => `<li><strong>e${index + 1}</strong> ${mathMarkup(item.label)}</li>`).join("");
  const display = (cell.display_basis || []).map((item) => `<li><strong>${mathMarkup(item.label)}</strong> ${escapeHtml(vectorText(item.coordinates))}</li>`).join("") || '<li class="empty">computational basis is displayed</li>';
  const named = (cell.named_vectors || []).map((item) => `<li><strong>${mathMarkup(item.label)}</strong> ${escapeHtml(vectorText(item.coordinates))}</li>`).join("") || '<li class="empty">no pinned combination ports</li>';
  const mapMarkup = maps.map((item) => {
    const direction = item.source_cell_id === cell.id ? "out" : "in";
    return `<li><button type="button" class="text-button" data-edit-map="${escapeHtml(item.id)}">${direction} d${item.page}</button><span>${escapeHtml(item.status)} · ${escapeHtml(item.coverage)} · ${escapeHtml(matrixText(item.matrix))}</span></li>`;
  }).join("") || '<li class="empty">no stored matrices at this cell</li>';
  inspector.innerHTML = `<div class="cell-grade"><strong>${escapeHtml(gradeText(cell.grade))}</strong><span>${escapeHtml(cell.coefficient_context_id)} · ${escapeHtml(cell.status)}</span></div><div class="cell-inspector-grid"><div><h3>Computational basis</h3><ul>${basis}</ul></div><div><h3>Display basis</h3><ul>${display}</ul></div><div><h3>Named vectors</h3><ul>${named}</ul></div></div><h3>Differential matrices</h3><ul class="cell-map-list">${mapMarkup}</ul><p class="source-ref">${escapeHtml(cell.source_ref || "No source locator recorded.")}</p>`;
  inspector.querySelectorAll("[data-edit-map]").forEach((button) => button.addEventListener("click", () => openMatrixDialog(button.dataset.editMap)));
  const outgoing = activeDifferentialMaps(ws).filter((item) => item.source_cell_id === cell.id);
  mapSelect.innerHTML = '<option value="">Choose a map</option>' + outgoing.map((item) => `<option value="${escapeHtml(item.id)}">d${item.page} · ${escapeHtml(item.status)} · ${escapeHtml(item.coverage)}</option>`).join("");
}

function parseJsonField(value, fallback = []) {
  const text = String(value || "").trim();
  if (!text) return fallback;
  const parsed = JSON.parse(text);
  if (!Array.isArray(parsed)) throw new Error("Expected a JSON list.");
  return parsed;
}

function openCellDialog(cellId = null) {
  if (readOnlyCatalog()) return toast("Archived research charts are read-only.");
  const cell = explicitCells().find((item) => item.id === cellId) || null;
  const form = $("#cell-form");
  form.reset();
  form.elements.cell_id.value = cell?.id || "";
  form.elements.stem.value = cell?.grade?.stem ?? 0;
  form.elements.filtration.value = cell?.grade?.filtration ?? 0;
  form.elements.page.value = cell?.page ?? workspace().page;
  form.elements.coefficient_context_id.value = cell?.coefficient_context_id || "q8-residue-f4";
  form.elements.basis.value = cell?.basis?.map((item) => item.label).join("\n") || "a\nb";
  form.elements.display_basis.value = cell?.display_basis?.length ? JSON.stringify(cell.display_basis.map(({ label, coordinates, expression, pinned }) => ({ label, coordinates, expression, pinned })), null, 2) : "";
  form.elements.named_vectors.value = cell?.named_vectors?.length ? JSON.stringify(cell.named_vectors.map(({ label, coordinates, expression, pinned }) => ({ label, coordinates, expression, pinned })), null, 2) : "";
  form.elements.status.value = cell?.status || "candidate";
  form.elements.source_ref.value = cell?.source_ref || "";
  $("#archive-cell").hidden = !cell;
  $("#cell-form-result").textContent = "F4 validation runs on the server before saving.";
  $("#cell-dialog").showModal();
}

function cellPayload(form) {
  const basis = String(form.elements.basis.value || "").split(/\r?\n/).map((label) => label.trim()).filter(Boolean).map((label) => ({ label, expression: label }));
  return {
    grade: { stem: Number(form.elements.stem.value), filtration: Number(form.elements.filtration.value), representation: {} },
    page: Number(form.elements.page.value),
    coefficient_context_id: form.elements.coefficient_context_id.value,
    basis,
    display_basis: parseJsonField(form.elements.display_basis.value),
    named_vectors: parseJsonField(form.elements.named_vectors.value),
    status: form.elements.status.value,
    source_ref: form.elements.source_ref.value.trim(),
  };
}

async function saveCell(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const id = form.elements.cell_id.value;
    const data = await api(id ? `/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/cells/${encodeURIComponent(id)}` : `/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/cells`, {
      method: id ? "PATCH" : "POST", body: JSON.stringify(cellPayload(form)),
    });
    state.selectedCellId = data.cell.id;
    $("#cell-dialog").close();
    await loadProject();
    toast(`Saved rank-${data.cell.basis.length} F4 cell.`);
  } catch (error) {
    $("#cell-form-result").textContent = error.message;
  }
}

function matrixOptions(selected = "", allowZero = true) {
  return `${allowZero ? '<option value="">0 (zero cell)</option>' : ""}` + explicitCells().map((cell) => `<option value="${escapeHtml(cell.id)}" ${cell.id === selected ? "selected" : ""}>rank ${cell.basis.length} · ${escapeHtml(gradeText(cell.grade))}</option>`).join("");
}

function openMatrixDialog(mapId = null) {
  if (readOnlyCatalog()) return toast("Archived research charts are read-only.");
  const item = activeDifferentialMaps().find((record) => record.id === mapId) || null;
  const form = $("#matrix-form");
  form.reset();
  form.elements.map_id.value = item?.id || "";
  form.elements.source_cell_id.innerHTML = matrixOptions(item?.source_cell_id || state.selectedCellId || "");
  form.elements.target_cell_id.innerHTML = matrixOptions(item?.target_cell_id || "");
  form.elements.source_cell_id.value = item?.source_cell_id || state.selectedCellId || "";
  form.elements.target_cell_id.value = item?.target_cell_id || "";
  form.elements.page.value = item?.page || workspace().page;
  form.elements.coverage.value = item?.coverage || "complete";
  form.elements.status.value = item?.status || "candidate";
  form.elements.source_ref.value = item?.source_ref || "";
  form.elements.notes.value = item?.notes || "";
  form.elements.matrix.value = item?.matrix?.map((row) => row.join(", ")).join("\n") || "";
  $("#archive-matrix").hidden = !item;
  $("#matrix-form-result").textContent = "Candidate matrices can be previewed but do not change the canonical page.";
  $("#matrix-dialog").showModal();
}

function parseMatrix(text, targetRank, sourceRank) {
  const trimmed = String(text || "").trim();
  if (!targetRank) return [];
  if (!sourceRank && !trimmed) return Array.from({ length: targetRank }, () => []);
  return trimmed.split(/\r?\n/).filter((line) => line.trim()).map((line) => line.split(/[ ,]+/).filter(Boolean));
}

async function saveMatrix(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const id = form.elements.map_id.value;
    const sourceId = form.elements.source_cell_id.value || null;
    const targetId = form.elements.target_cell_id.value || null;
    const source = explicitCells().find((item) => item.id === sourceId);
    const target = explicitCells().find((item) => item.id === targetId);
    const payload = {
      source_cell_id: sourceId, target_cell_id: targetId,
      page: Number(form.elements.page.value), coverage: form.elements.coverage.value,
      status: form.elements.status.value, source_ref: form.elements.source_ref.value.trim(),
      notes: form.elements.notes.value,
      matrix: parseMatrix(form.elements.matrix.value, target?.basis.length || 0, source?.basis.length || 0),
      coefficient_context_id: source?.coefficient_context_id || target?.coefficient_context_id || "q8-residue-f4",
    };
    const data = await api(id ? `/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/differential-maps/${encodeURIComponent(id)}` : `/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/differential-maps`, {
      method: id ? "PATCH" : "POST", body: JSON.stringify(payload),
    });
    $("#matrix-dialog").close();
    await loadProject();
    toast(`Saved d${data.differential_map.page} matrix; ${data.image_ports.filter((port) => !port.zero).length} nonzero image port(s).`);
  } catch (error) {
    $("#matrix-form-result").textContent = error.message;
  }
}

function coordinatesInput() {
  return String($("#cell-vector-coordinates").value || "").split(/[ ,]+/).filter(Boolean);
}

async function evaluateCellVector() {
  const cell = selectedCell();
  const mapId = $("#cell-vector-map").value;
  if (!cell || !mapId) return toast("Choose a cell and one of its outgoing maps.");
  try {
    const data = await api(`/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/cells/${encodeURIComponent(cell.id)}/vector-image`, {
      method: "POST", body: JSON.stringify({ map_id: mapId, coordinates: coordinatesInput() }),
    });
    state.lastVectorResult = data.result;
    $("#cell-vector-result").textContent = data.result.zero
      ? `${vectorText(data.result.coordinates)} maps to 0.`
      : `${vectorText(data.result.coordinates)} maps to ${vectorText(data.result.image_coordinates)} · port ${vectorText(data.result.image_projective_coordinates)}.`;
  } catch (error) { $("#cell-vector-result").textContent = error.message; }
}

async function pinCellVector() {
  const cell = selectedCell();
  if (!cell) return toast("Choose a cell first.");
  const coordinates = state.lastVectorResult?.cell_id === cell.id ? state.lastVectorResult.coordinates : coordinatesInput();
  if (!coordinates.length) return toast("Enter coordinates or evaluate a vector first.");
  const label = window.prompt("Label for this named vector", vectorText(coordinates));
  if (!label) return;
  try {
    await api(`/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/cells/${encodeURIComponent(cell.id)}`, {
      method: "PATCH", body: JSON.stringify({ named_vectors: [...(cell.named_vectors || []).map(({ label: oldLabel, coordinates: oldCoordinates, expression, pinned }) => ({ label: oldLabel, coordinates: oldCoordinates, expression, pinned })), { label, coordinates, expression: label, pinned: true }] }),
    });
    await loadProject();
    toast("Pinned an exact projective combination port.");
  } catch (error) { $("#cell-vector-result").textContent = error.message; }
}

async function previewCellTransition() {
  const cell = selectedCell();
  if (!cell) return toast("Choose a cell first.");
  const maps = activeDifferentialMaps();
  const incoming = maps.find((item) => item.target_cell_id === cell.id && item.page === workspace().page);
  const selectedOutgoing = $("#cell-vector-map").value;
  const outgoing = maps.find((item) => item.id === selectedOutgoing) || maps.find((item) => item.source_cell_id === cell.id && item.page === workspace().page);
  try {
    const data = await api(`/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/page-transitions/preview`, {
      method: "POST", body: JSON.stringify({
        cell_id: cell.id, page: workspace().page,
        incoming_map_id: incoming?.id || null, outgoing_map_id: outgoing?.id || null,
        incoming_zero: $("#transition-incoming-zero").checked,
        outgoing_zero: $("#transition-outgoing-zero").checked,
      }),
    });
    const result = data.transition;
    $("#cell-transition-result").innerHTML = result.status === "complete"
      ? `<strong>E${result.page + 1} rank ${result.quotient_rank}</strong><span>ker: ${escapeHtml(JSON.stringify(result.kernel_basis))}</span><span>image: ${escapeHtml(JSON.stringify(result.image_basis))}</span><span>quotient basis: ${escapeHtml(JSON.stringify(result.quotient_basis))}</span><em>${result.canonical ? "canonical admitted maps" : "research preview; not persisted"}</em>`
      : `<strong>${escapeHtml(result.status)}</strong><span>${escapeHtml((result.obligations || result.errors || [result.error]).filter(Boolean).join("; "))}</span>`;
  } catch (error) { $("#cell-transition-result").textContent = error.message; }
}

function renderPagePeriodTool() {
  const ws = workspace();
  const root = $("#page-period-tool");
  if (!ws || !root) return;
  const selected = ws.classes.find((item) => item.id === state.selectedClassId && !item.archived);
  const cycles = (state.project.page_period_cycles || []).filter((item) => item.workspace_id === ws.id);
  const generatorNames = detectedAlgebraGenerators(ws);
  root.innerHTML = `
    <p class="hint"><strong>Detected basic generators:</strong> ${escapeHtml(generatorNames.join(", ") || "none on this page")}</p>
    <label>Cycle label (= algebra expression)<input id="page-period-label" value="${escapeHtml(selected?.label || "")}" placeholder="D"></label>
    <div class="periodicity-coordinate-row">
      <label>Stem<input id="page-period-stem" type="number" value="${Number(selected?.grade.stem || 0)}"></label>
      <label>Filtration<input id="page-period-filtration" type="number" value="${Number(selected?.grade.filtration || 0)}"></label>
    </div>
    <label>Basis / mathematical role<input id="page-period-basis" value="${selected ? `Selected live class ${escapeHtml(selected.label)} on E${ws.page}` : ""}" placeholder="Why this cycle is used as a period"></label>
    <label>Source locator<input id="page-period-source" placeholder="Paper/notes theorem or explicit user declaration"></label>
    <button type="button" id="register-page-period" class="wide primary">Register virtual period on E${ws.page}</button>
    <div class="drawing-periodicity-rules">${cycles.map((cycle) => {
      const eligible = pagePeriodEligible(ws, cycle, ws.page);
      return `<div class="drawing-periodicity-rule"><span><strong>${escapeHtml(cycle.label)}</strong> (${cycle.grade.stem},${cycle.grade.filtration}) · declared E${cycle.declared_page} · ${eligible ? `acts on E${ws.page}` : `blocked before E${ws.page}`}</span></div>`;
    }).join("") || '<p class="empty">No compact page-period cycle has been registered.</p>'}</div>`;
  $("#register-page-period").addEventListener("click", registerPagePeriodCycle);
}

async function registerPagePeriodCycle() {
  const ws = workspace();
  const selected = ws.classes.find((item) => item.id === state.selectedClassId && !item.archived);
  const payload = {
    page: ws.page,
    label: $("#page-period-label").value,
    basis: $("#page-period-basis").value,
    source_ref: $("#page-period-source").value,
    status: "candidate",
    ...(selected
      ? { cycle_class_id: selected.id }
      : { grade: {
        stem: Number($("#page-period-stem").value),
        filtration: Number($("#page-period-filtration").value),
        representation: {},
      } }),
  };
  try {
    await api(`/api/v2/workspaces/${encodeURIComponent(ws.id)}/page-periods`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    await loadProject();
    toast(`Registered ${payload.label} as a compact virtual period on E${payload.page}.`);
  } catch (error) { toast(error.message); }
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
    ? `<div class="candidate-result-group"><strong>${label}</strong><ul>${items.map((item) => `<li><strong>${mathTextMarkup(item.statement)}</strong><span>review-only · not saved</span></li>`).join("")}</ul></div>`
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
  const all = $("#proof-scope").value === "project" ? allPropositions() : ws.propositions.map((item) => ({ ...item, workspaceName: ws.name }));
  const graphPropositions = new Map((state.logicGraph?.nodes || []).filter((item) => item.kind === "proposition").map((item) => [item.record_id, item]));
  const admissionFilter = $("#proof-admission").value;
  const propositions = all.filter((item) => {
    const admitted = graphPropositions.get(item.id)?.admitted === true;
    return admissionFilter === "all" || (admissionFilter === "admitted" ? admitted : !admitted);
  });
  const lookup = new Map(allPropositions().map((item) => [item.id, item.statement]));
  $("#proposition-count").textContent = propositions.length;
  $("#proof-tree").innerHTML = propositions.map((item) => {
    const graphItem = graphPropositions.get(item.id) || {};
    const admission = graphItem.admitted ? `admitted · depth ${graphItem.dependency_depth ?? 0}` : `review queue${graphItem.blocked_by?.length ? ` · blocked by ${graphItem.blocked_by.join(", ")}` : ""}`;
    const sourceAudit = window.HFPSSTableLedger?.claimAuditMarkup(item) || "";
    return `<article class="proof-node ${escapeHtml(item.status)}"><strong>${mathTextMarkup(item.statement)}</strong><small>${escapeHtml(item.workspaceName)} · ${escapeHtml(item.rule)} · ${escapeHtml(item.status)} · ${escapeHtml(admission)} · ${(item.confidence * 100).toFixed(0)}%</small>${item.source_ref ? `<div class="source-ref">${escapeHtml(item.source_ref)}</div>` : ""}${sourceAudit}${item.premise_ids?.length ? `<div class="parents">depends on: ${item.premise_ids.map((id) => mathTextMarkup(lookup.get(id) || id)).join("; ")}</div>` : ""}</article>`;
  }).join("") || '<p class="empty">No propositions match this fact-admission filter.</p>';
  renderLogicGraph();
}

function renderLogicGraph() {
  const graph = state.logicGraph || { nodes: [], edges: [] };
  const projectScope = $("#proof-scope").value === "project";
  const admissionFilter = $("#proof-admission").value;
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
  if (admissionFilter !== "all") {
    const matchingPropositions = new Set(graph.nodes.filter((item) => (
      item.kind === "proposition"
      && visibleIds.has(item.id)
      && (admissionFilter === "admitted" ? item.admitted : !item.admitted)
    )).map((item) => item.id));
    const contextualIds = new Set(matchingPropositions);
    for (const edge of graph.edges) {
      if (matchingPropositions.has(edge.source)) contextualIds.add(edge.target);
      if (matchingPropositions.has(edge.target)) contextualIds.add(edge.source);
    }
    visibleIds = new Set([...visibleIds].filter((ident) => contextualIds.has(ident)));
  }
  const allVisible = graph.nodes.filter((item) => visibleIds.has(item.id));
  const nodes = allVisible.slice(0, projectScope ? 70 : 90);
  visibleIds = new Set(nodes.map((item) => item.id));
  const edges = graph.edges.filter((item) => visibleIds.has(item.source) && visibleIds.has(item.target));
  const columnFor = (kind) => {
    if (["source-reference", "coefficient-context", "c3-action"].includes(kind)) return 0;
    if (kind === "proposition") return 1;
    if (["cell-vector-space", "differential-map", "differential-claim", "differential-event", "cross-graded-product"].includes(kind)) return 2;
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
    const admissionClass = item.kind === "proposition" ? (item.admitted ? " admitted" : " review-queue") : "";
    const depth = item.dependency_depth == null ? "" : ` · d${item.dependency_depth}`;
    markup += `<g class="logic-node ${escapeHtml(item.kind)}${admissionClass}" data-logic-node="${escapeHtml(item.id)}" transform="translate(${point.x} ${point.y})"><rect width="118" height="33" rx="5"/><text x="7" y="13">${escapeHtml(item.kind)}${escapeHtml(depth)}</text><text class="logic-label" x="7" y="26">${escapeHtml(label)}</text><title>${escapeHtml(item.label)}</title></g>`;
  }
  svg.innerHTML = markup || '<text x="12" y="24">No graph nodes.</text>';
  svg.querySelectorAll("[data-logic-node]").forEach((node) => node.addEventListener("click", () => {
    const item = graph.nodes.find((candidate) => candidate.id === node.dataset.logicNode);
    const admission = item.kind === "proposition"
      ? ` · ${item.admitted ? `admitted at depth ${item.dependency_depth ?? 0}` : `review queue${item.blocked_by?.length ? ` (blocked by ${item.blocked_by.join(", ")})` : ""}`}`
      : "";
    const coefficients = item.coefficient_context_ids?.length ? ` · coefficients: ${item.coefficient_context_ids.join(", ")}` : "";
    const datum = item.conclusion?.datum_type ? ` · ${item.conclusion.datum_type} in ${item.conclusion.spectral_sequence || "unspecified tower"}` : "";
    const period = item.conclusion?.period_identity ? ` · period: ${item.conclusion.period_identity}` : "";
    const implies = item.implies_ids?.length ? ` · implies: ${item.implies_ids.join(", ")}` : "";
    const basis = item.computational_basis?.length ? ` · basis: ${item.computational_basis.join(", ")}` : "";
    const matrix = item.matrix ? ` · matrix: ${matrixText(item.matrix)} · ${item.coverage || "unknown coverage"}` : "";
    const sourceRefs = item.source_refs?.length ? ` · source: ${item.source_refs.join("; ")}` : "";
    $("#logic-node-detail").textContent = `${item.kind} · ${item.status || "no status"}${admission}${coefficients}${datum}${period}${basis}${matrix}${sourceRefs}${implies} · ${item.label}`;
  }));
  $("#logic-node-detail").textContent = allVisible.length > nodes.length
    ? `Showing ${nodes.length} of ${allVisible.length} typed nodes. Select a node for details.`
    : `${nodes.length} typed nodes · ${edges.length} visible evidence edges.`;
}

function renderPeriodicFateAudit() {
  const payload = state.periodicFateLedger || {};
  const audit = payload.audit || {};
  const ledger = payload.ledger || {};
  const status = audit.status || "unavailable";
  const statusNode = $("#periodic-fate-audit-status");
  statusNode.textContent = status;
  statusNode.dataset.status = status;

  const metrics = [
    ["Fact families", audit.fact_family_count],
    ["Period mechanisms", audit.period_mechanism_count],
    ["Module kinds", audit.module_kind_count],
    ["Finite obligations", audit.finite_rank_obligation_count],
    ["Covered", audit.covered_obligation_count],
    ["Formal-series families", audit.formal_series_family_count],
  ];
  $("#periodic-fate-audit-metrics").innerHTML = metrics.map(([label, value]) => (
    `<div><strong>${Number(value || 0)}</strong><span>${escapeHtml(label)}</span></div>`
  )).join("");

  const formalPolicy = ledger.formal_series_policy || {};
  $("#formal-series-audit-note").textContent = formalPolicy.storage_rule
    ? `Formal series are separate from finite-rank audit. ${formalPolicy.storage_rule}`
    : "Formal-series families are handled separately from finite-rank obligations.";

  const unresolved = (audit.obligations || []).filter((item) => !item.covered);
  $("#periodic-fate-obligations").innerHTML = unresolved.length
    ? `<h3>${unresolved.length} unresolved obligations</h3>${unresolved.map((item) => {
      const reasons = (item.unresolved_reasons || []).length
        ? item.unresolved_reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")
        : "<li>No resolution has been recorded.</li>";
      const representative = item.period_class_id || item.id;
      return `<article class="audit-obligation"><strong>${escapeHtml(item.id)}</strong><span>${escapeHtml(representative)}</span><ul>${reasons}</ul></article>`;
    }).join("")}`
    : '<p class="empty">All recorded high-filtration obligations are covered.</p>';
}

async function loadReviewPage() {
  const [project, logicGraph, periodicFateLedger] = await Promise.all([
    api("/api/project"),
    api("/api/v2/logic-graph"),
    api("/api/v2/review/periodic-fate-ledger"),
  ]);
  state.project = project;
  state.logicGraph = logicGraph;
  state.periodicFateLedger = periodicFateLedger;
  if (!project.workspaces.some((item) => item.id === state.workspaceId)) state.workspaceId = defaultWorkspaceId();
  const selector = $("#review-workspace-select");
  selector.innerHTML = project.workspaces.map((item) => (
    `<option value="${escapeHtml(item.id)}">${escapeHtml(workspaceDisplayName(item))}</option>`
  )).join("");
  selector.value = state.workspaceId;
  const admission = logicGraph.admission || {};
  $("#review-admission-summary").innerHTML = (
    `<strong>${Number(admission.admitted || 0)} admitted</strong>`
    + `<span>${Number(admission.review_queue || 0)} in review</span>`
    + `<small>${escapeHtml(admission.policy || "Premise-complete facts enter the admitted DAG.")}</small>`
  );
  renderPeriodicFateAudit();
  renderProofTree();
  syncLayoutHeight();
}

function bindReviewEvents() {
  $("#review-workspace-select").addEventListener("change", (event) => {
    state.workspaceId = event.target.value;
    renderProofTree();
  });
  $("#proof-scope").addEventListener("change", renderProofTree);
  $("#proof-admission").addEventListener("change", renderProofTree);
  window.addEventListener("resize", syncLayoutHeight);
}

function renderSuggestions() {
  const root = $("#suggestion-list");
  if (!state.suggestions.length) {
    root.innerHTML = '<p class="empty">Run a rule to look for transparent, reviewable candidates.</p>';
    return;
  }
  root.innerHTML = state.suggestions.map((item, index) => `<article class="suggestion"><strong>${mathTextMarkup(item.statement)}</strong><span class="suggestion-meta">${escapeHtml(item.rule)} · ${(item.confidence * 100).toFixed(0)}%</span><p>${mathTextMarkup(item.notes || "Review the premises before accepting.")}</p><button data-accept="${index}" class="primary">Add to proof tree</button></article>`).join("");
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

function segmentIntersectsBounds(source, target, bounds) {
  let entry = 0, exit = 1;
  for (const [coordinate, minimum, maximum] of [["stem", bounds.stemMin, bounds.stemMax], ["filtration", bounds.filtrationMin, bounds.filtrationMax]]) {
    const delta = target[coordinate] - source[coordinate];
    if (!delta) {
      if (source[coordinate] < minimum || source[coordinate] > maximum) return false;
      continue;
    }
    const first = (minimum - source[coordinate]) / delta;
    const last = (maximum - source[coordinate]) / delta;
    entry = Math.max(entry, Math.min(first, last));
    exit = Math.min(exit, Math.max(first, last));
    if (entry > exit) return false;
  }
  return true;
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
  return family && ["reviewed", "established", "verified", "under-review"].includes(family.status) ? family : null;
}

function pageWithinPeriodFamily(page, family) {
  const upper = family.valid_to_page;
  return page >= Number(family.valid_from_page || 2) && (typeof upper !== "number" || page <= upper);
}

function workspaceRenderPeriods(ws) {
  const enumeratedHorizontal = Number(ws.settings.rendering?.enumerated_horizontal_period || 0);
  const periods = (ws.settings.rendering?.period_lattice || []).map((item) => ({
    stem: Number(item.stem) || 0,
    filtration: Number(item.filtration) || 0,
    domain: item.exponent_domain === "integer" ? "integer" : "nonnegative",
    id: item.id,
  }));
  for (const family of state.project.period_families || []) {
    if (family.workspace_id !== ws.id || !["reviewed", "established"].includes(family.status) || !pageWithinPeriodFamily(ws.page, family)) continue;
    for (const generator of family.generators || []) {
      const label = String(generator.multiplier_expr || "");
      periods.push({
        stem: Number(generator.grade_shift?.stem) || 0,
        filtration: Number(generator.grade_shift?.filtration) || 0,
        domain: /^D(?:\^\d+)?$/.test(label) ? "integer" : "nonnegative",
        id: family.id,
      });
    }
  }
  const distinct = new Map();
  for (const period of periods) {
    if (!period.stem && !period.filtration) continue;
    distinct.set(`${period.stem}:${period.filtration}:${period.domain}`, period);
  }
  return [...distinct.values()].filter((period) => (
    !enumeratedHorizontal
    || period.filtration !== 0
    || period.domain !== "integer"
    || Math.abs(period.stem) >= enumeratedHorizontal
  ));
}

function latticeCopies(grade, periods, bounds) {
  const horizontal = periods
    .filter((item) => item.filtration === 0 && item.domain === "integer" && item.stem)
    .sort((left, right) => Math.abs(left.stem) - Math.abs(right.stem))[0];
  const forward = periods.filter((item) => item.domain !== "integer" && item.filtration > 0);
  const verticalPeriod = forward[0];
  const copies = [];
  const sMax = verticalPeriod
    ? Math.max(0, Math.floor((bounds.filtrationMax - grade.filtration) / verticalPeriod.filtration))
    : 0;
  for (let s = 0; s <= sMax; s += 1) {
    const base = {
      stem: grade.stem + s * (verticalPeriod?.stem || 0),
      filtration: grade.filtration + s * (verticalPeriod?.filtration || 0),
    };
    const qValues = horizontal ? shiftRange(base, horizontal, bounds) : [0];
    for (const q of qValues) {
      const shifted = {
        ...grade,
        stem: base.stem + q * (horizontal?.stem || 0),
        filtration: base.filtration,
      };
      if (inBounds(shifted, bounds)) copies.push({
        grade: shifted,
        shift: `${s}:${q}`,
        verticalExponent: s,
        horizontalExponent: q,
        horizontalStem: horizontal?.stem || 0,
        periodic: s !== 0 || q !== 0,
      });
    }
  }
  return copies.length ? copies : (inBounds(grade, bounds) ? [{ grade, shift: "0:0", periodic: false }] : []);
}

function pageHorizontalDifferentialPeriod(ws, page = ws.page) {
  const schedule = ws.settings.rendering?.page_horizontal_periods || [];
  const match = schedule.find((item) => (
    page >= Number(item.from_page || 2)
    && (item.to_page == null || page <= Number(item.to_page))
  ));
  return match?.stem ? {
    stem: Number(match.stem), filtration: 0, domain: "integer", label: match.label,
  } : null;
}

function latexPower(symbol, exponent) {
  if (!exponent) return "";
  if (exponent === 1) return symbol;
  return `${symbol}^{${exponent}}`;
}

function shiftDExponent(label, delta) {
  return shiftPeriodFactor(label, "D", delta);
}

function shiftKExponent(label, delta) {
  return shiftPeriodFactor(label, "k", delta);
}

function shiftPeriodFactor(label, symbol, delta) {
  if (!delta) return label;
  const clean = String(label || "").split("=")[0].trim();
  if (clean === "0") return "0";
  const factor = latexPower(symbol, delta);
  if (clean === "1") return factor || "1";
  const matches = [];
  let depth = 0, sum = false;
  for (let index = 0; index < clean.length;) {
    const char = clean[index];
    if (char === "\\") {
      const command = clean.slice(index).match(/^\\[A-Za-z]+/);
      if (command) { index += command[0].length; continue; }
      if (clean[index + 1] === "{") depth++;
      if (clean[index + 1] === "}") depth--;
      index += 2;
      continue;
    }
    if ("({[".includes(char)) depth++;
    else if (")}]".includes(char)) depth--;
    else if (depth === 0 && char === "^") {
      const exponent = clean.slice(index).match(/^\^(?:\{[^}]*\}|[+-]?\d+|[A-Za-z])/);
      if (exponent) { index += exponent[0].length; continue; }
    } else if (depth === 0 && (char === "+" || (char === "-" && index > 0))) sum = true;
    else if (depth === 0 && char === symbol && clean[index - 1] !== "_") {
      const match = clean.slice(index + 1).match(/^(?:\^\{(-?\d+)\}|\^(-?\d+))/);
      const length = 1 + (match?.[0].length || 0);
      if (!["^", "_"].includes(clean[index + length])) {
        matches.push({index, length, exponent: Number(match?.[1] ?? match?.[2] ?? 1)});
        index += length;
        continue;
      }
    }
    index++;
  }
  // Preserve a whole sum (or an unfamiliar grouping) as an exact product.
  // Replacing only its first D/k would change the represented element.
  if (sum || depth !== 0) return `${factor}\\left(${clean}\\right)`;
  if (matches.length) {
    let result = clean;
    const power = delta + matches.reduce((total, match) => total + match.exponent, 0);
    for (let n = matches.length - 1; n >= 0; n--) {
      const match = matches[n];
      result = result.slice(0, match.index) + (n === 0 ? latexPower(symbol, power) : "")
        + result.slice(match.index + match.length);
    }
    return result || "1";
  }
  if (symbol === "k") {
    const scalar = clean.match(/^([+-]?\d+)(.*)$/);
    return scalar ? `${scalar[1]}${factor}${scalar[2]}` : `${factor}${clean}`;
  }
  const thomIndex = clean.indexOf("u_{");
  return thomIndex >= 0
    ? `${clean.slice(0, thomIndex)}${factor}${clean.slice(thomIndex)}`
    : `${clean}${factor}`;
}

function periodicDisplayLabel(record) {
  if (record.presentationLabel) return record.presentationLabel;
  const survivingLabel = (label) => {
    // Name the lowest surviving CONSTANT 2-adic layer, including a Witt
    // tower. Positive-j ideals have independent fates and do not lower this
    // representative's coefficient. The compressed 3:0 tail starts at 8W.
    // Already scaled endpoint aliases include their own two-valuation.
    const style = record.item.style || {};
    if (record.readOnlyRepresentative || record.uncertain || !style.e2_pattern
        || !Array.isArray(record.modulePorts)) return label;
    const constants = record.modulePorts.flatMap(port => {
      const match = String(port).match(/^([0-3]):0$/);
      return match ? [Number(match[1])] : [];
    });
    const originalTwo = Number(style.two_valuation || 0);
    const delta = constants.length ? Math.min(...constants) - originalTwo : 0;
    if (!Number.isInteger(originalTwo) || originalTwo < 0 || delta <= 0) return label;
    const factor = 2 ** delta;
    const clean = String(label).trim();
    if (clean === "0") return "0";
    // Do not apply a coefficient to just the first summand. Exponent signs
    // are not additive signs, and these labels are presentation only.
    const withoutPowers = clean.replace(/\^(?:\{[+-]?\d+\}|[+-]?\d+)/g, "").replace(/^[+-]/, "");
    if (/[+-]/.test(withoutPowers)) return `${factor}\\left(${clean}\\right)`;
    const unit = clean.match(/^(\{\\zeta(?:\^\{?2\}?)?\}|\\zeta(?:\^\{?2\}?)?)/)?.[0] || "";
    const scalar = clean.slice(unit.length).match(/^([+-]?)(\d*)(.*)$/);
    const value = factor * Number(scalar[2] || 1) * (scalar[1] === "-" ? -1 : 1);
    return `${value}${unit}${scalar[3]}`;
  };
  if (!record.periodic) return survivingLabel(record.item.label);
  const kPower = Number(record.verticalExponent || 0);
  const horizontalDPower = Number(record.horizontalExponent || 0) * Number(record.horizontalStem || 0) / 8;
  const dShift = 3 * kPower + horizontalDPower;
  const basis = record.item.style?.atlas_display_basis;
  const label = basis?.status === "exact" ? basis.expression : record.item.label;
  const shifted = shiftKExponent(shiftDExponent(label, dShift), kPower);
  if (basis?.status !== "exact" || ![1, 2, 3].includes(basis.unit)) return survivingLabel(shifted);
  const omega = Number(record.item.style.atlas_transport?.omega_power || 0);
  const exponent = ((2 * omega * dShift) % 3 + 3) % 3;
  const unit = f4DisplayMultiply(basis.unit, [1, 2, 3][exponent]);
  return survivingLabel(`${unit === 1 ? "" : `{${f4DisplayLatex(unit)}}`}${shifted}`);
}

function f4DisplayMultiply(a, b) {
  return [[0, 0, 0, 0], [0, 1, 2, 3], [0, 2, 3, 1], [0, 3, 1, 2]][a]?.[b] ?? null;
}

function f4DisplayLatex(unit) {
  return unit === 2 ? "\\zeta" : unit === 3 ? "\\zeta^{2}" : unit === 0 ? "0" : "";
}

function periodsForClassOnPage(ws, item) {
  const periods = [...workspaceRenderPeriods(ws)];
  const add = (period) => {
    if (!period || periods.some((known) => known.stem === period.stem && known.filtration === period.filtration)) return;
    periods.push(period);
  };
  // Periodic copies require a reviewed/established PeriodFamily certificate.
  for (const differential of ws.differentials) {
    if (differential.page !== ws.page) continue;
    if (differential.source_id !== item.id && differential.target_id !== item.id) continue;
    if (!usablePeriodFamily(differential)) continue;
    const period = normalizedPeriod(differential.period_stem, differential.period_filtration);
    if (period) add({ ...period, domain: "integer" });
  }
  for (const cycle of state.project.page_period_cycles || []) {
    if (cycle.workspace_id !== ws.id || !pagePeriodEligible(ws, cycle, ws.page)) continue;
    const period = normalizedPeriod(cycle.grade?.stem, cycle.grade?.filtration);
    if (period) add({ ...period, cycleId: cycle.id, domain: cycle.invertible ? "integer" : "nonnegative" });
  }
  return periods;
}

function periodsForDifferential(ws, differential) {
  const periods = [...workspaceRenderPeriods(ws)].filter(p => p.filtration !== 0 || !differential.period_stem);
  // Repetition belongs to a row: d7(D^4) has period 64, not 32.
  if (differential.period_stem || differential.period_filtration) {
    periods.push({
      stem: differential.period_stem || 0,
      filtration: differential.period_filtration || 0,
      domain: "integer",
    });
  }
  else {
    const pagePeriod = pageHorizontalDifferentialPeriod(ws, differential.page);
    if (pagePeriod) periods.push(pagePeriod);
  }
  return periods;
}

function e2OccurrenceKey(item, grade) {
  const pattern = item?.style?.e2_pattern || (item?.style?.e2_components ? JSON.stringify(item.style.e2_components) : "");
  if (!pattern) return "";
  // Coefficient levels in one Witt square share a visual cell, but not a
  // spectral-sequence fate.  For example d5(D) must not kill the 4D port
  // which supports a Table 8 d7 on the next page.
  const coefficientPort = `${Number(item.style.two_valuation || 0)}:${Number(item.style.j_order || 0) > 0 ? 1 : 0}`;
  return `${pattern}:${coefficientPort}:${grade.stem}:${grade.filtration}`;
}

function pageAlgebra(ws, bounds) {
  if (!ws.settings.rendering?.enumerated_e2_pattern || !window.HFPSSPageAlgebra) return null;
  return window.HFPSSPageAlgebra.compute(ws, bounds, {
    coefficientWorkspaces: state.project.workspaces,
    copies: latticeCopies, classPeriods: periodsForClassOnPage,
    diffPeriods: periodsForDifferential,
    accepted: (diff) => differentialVisualState(diff) === "accepted",
    periodSignature: JSON.stringify([
      (state.project.period_families || []).filter(p => p.workspace_id === ws.id),
      (state.project.page_period_cycles || []).filter(p => p.workspace_id === ws.id),
    ]),
  });
}

function e2DisplaySlot(item, grade) {
  const pattern = item?.style?.e2_pattern;
  return pattern ? `${pattern}:${grade.stem}:${grade.filtration}` : "";
}

function deadE2OccurrenceKeys(ws, bounds, page = ws.page) {
  const keys = new Set();
  const algebra = pageAlgebra(page === ws.page ? ws : {...ws, page}, bounds);
  if (!algebra) return keys;
  for (const item of ws.classes) {
    for (const copy of latticeCopies(item.grade, periodsForClassOnPage(ws, item), bounds)) {
      if (!algebra.live(item, copy.grade)) keys.add(e2OccurrenceKey(item, copy.grade));
    }
  }
  return keys;
}

function periodicClassInstances(ws, bounds, presentation = null, algebra = pageAlgebra(ws, bounds)) {
  const rendered = [];
  const seen = new Set();
  const occupiedSlots = new Set();
  for (const item of liveClassesAt(ws).filter((node) => !node.cell_id || node.style?.e2_pattern || node.style?.e2_components)) {
    const periods = periodsForClassOnPage(ws, item);
    const copies = latticeCopies(item.grade, periods, bounds);
    for (const copy of copies) {
      const modulePorts = (presentation || algebra)?.ports(item, copy.grade);
      if (modulePorts && !modulePorts.size) continue;
      const displayLabel = periodicDisplayLabel({item, ...copy,
        modulePorts: modulePorts ? [...modulePorts] : null, uncertain: algebra?.blockedFromPage != null});
      const algebraSlots = (presentation || algebra)?.displaySlots(item, copy.grade) || [];
      const algebraSlot = algebraSlots.join("|") || e2DisplaySlot(item, copy.grade) || `${displayLabel}:${glyphShapeFor(ws, item)}`;
      const key = `${algebraSlot}:${copy.grade.stem}:${copy.grade.filtration}`;
      if (seen.has(key) || !inBounds(copy.grade, bounds)) continue;
      seen.add(key);
      for (const slot of algebraSlots) occupiedSlots.add(slot);
      const displayLine = presentation?.endpoint(item, copy.grade);
      const displayedName = displayLine?.adapted && !Number(item.style?.two_valuation || 0)
        && !String(item.coefficient_context_id || "").toLowerCase().includes("witt")
        ? window.HFPSSDisplayBasis?.combineLabels([{coefficient: 1, label: displayLabel}], {coefficientContext: "F4"}) : null;
      rendered.push({
        item,
        ...(displayedName?.supported ? {presentationLabel: displayedName.label} : {}),
        algebraSlots,
        modulePorts: modulePorts ? [...modulePorts] : null,
        uncertain: algebra?.blockedFromPage != null,
        displayBasisPriority: Number(Boolean(displayLine?.adapted
          && displayLine.entries?.length === 1 && Object.keys(item.style?.e2_components || {}).length > 1)),
        instanceKey: key,
        occurrenceState: visualStateFor(ws, item),
        ...copy,
      });
    }
  }
  // Different named vectors may share only a j/2 tail, so comparing entire
  // slot sets does not deduplicate them. Allocate each displayed direction
  // once, preferring the adapted differential target over its complement.
  rendered.splice(0, rendered.length, ...uniqueClassDisplaySlots(rendered));
  occupiedSlots.clear();
  for (const record of rendered) for (const slot of record.algebraSlots) occupiedSlots.add(slot);
  // A quotient basis can be a combination absent from the saved drawing.
  // These viewport-only objects have their own namespace and never replace
  // (or mutate) the researcher's original generators.
  const patterns = new Map();
  for (const item of ws.classes) {
    const pattern = item.style?.e2_pattern;
    if (!pattern || item.archived || Number(item.style.two_valuation || 0) || Number(item.style.j_order || 0)) continue;
    if (!patterns.has(pattern)) patterns.set(pattern, []);
    patterns.get(pattern).push(item);
  }
  for (const representative of (presentation || algebra)?.representatives?.(bounds) || []) {
    if (occupiedSlots.has(representative.slot) || !inBounds(representative.grade, bounds)) continue;
    const label = quotientRepresentativeLabel(ws, representative, patterns);
    const instanceKey = `computed-quotient:${ws.id}:E${ws.page}:${representative.slot}`;
    const positiveJ = representative.terms.length > 0 && representative.terms.every(term => Number(term.j) > 0);
    const grade = {...representative.grade, representation: {...(ws.classes.find(item => !item.archived)?.grade.representation || {})}};
    rendered.push({
      item: {id: instanceKey, label, expression: label, grade, page: ws.page,
        style: {computed_quotient: true, glyph: positiveJ ? "j-positive-series" : "dot"}},
      grade, instanceKey, algebraSlots: [representative.slot], modulePorts: null,
      readOnlyRepresentative: true, uncertain: Boolean(representative.uncertain),
      representativeTerms: representative.terms, displayBasis: representative.displayBasis,
      periodic: false, occurrenceState: "unknown",
    });
    occupiedSlots.add(representative.slot);
  }
  return rendered;
}

function uniqueClassDisplaySlots(records) {
  const occupied = new Set(), allocated = new Map();
  const priority = record => Number(record.displayBasisPriority || 0);
  const ordered = [...records].sort((a, b) => priority(b) - priority(a)
    || (b.algebraSlots?.length || 0) - (a.algebraSlots?.length || 0)
    || String(a.instanceKey).localeCompare(String(b.instanceKey)));
  for (const record of ordered) {
    const slots = record.algebraSlots || [];
    if (!slots.length) { allocated.set(record, record); continue; }
    const indices = slots.map((slot, index) => occupied.has(slot) ? -1 : index).filter(index => index >= 0);
    if (!indices.length) continue;
    for (const index of indices) occupied.add(slots[index]);
    if (indices.length === slots.length) { allocated.set(record, record); continue; }
    const algebraSlots = indices.map(index => slots[index]);
    const sharedModulePorts = (record.modulePorts || []).filter((_, index) => !indices.includes(index));
    allocated.set(record, {...record, algebraSlots, sharedModulePorts,
      modulePorts: record.modulePorts ? indices.map(index => record.modulePorts[index]) : null,
      instanceKey: `${algebraSlots.join("|")}:${record.grade.stem}:${record.grade.filtration}`});
  }
  return records.flatMap(record => allocated.has(record) ? [allocated.get(record)] : []);
}

function quotientRepresentativeLabel(ws, representative, patterns) {
  const grade = representative.grade;
  const bounds = {stemMin: grade.stem, stemMax: grade.stem, filtrationMin: grade.filtration, filtrationMax: grade.filtration};
  const collected = [];
  let residueFieldLabels = true;
  const fallback = representative.terms.filter(term => term.coefficient).map(term => {
    let basisLabel = `\\operatorname{${String(term.pattern).replace(/[^a-zA-Z0-9_-]/g, "")}}`;
    for (const item of patterns.get(term.pattern) || []) {
      const copy = latticeCopies(item.grade, periodsForClassOnPage(ws, item), bounds)[0];
      if (!copy) continue;
      basisLabel = periodicDisplayLabel({item, ...copy});
      if (String(item.coefficient_context_id || "").toLowerCase().includes("witt")
          || item.style?.multiplicative_unit || item.style?.dkllw_glyph === "witt-j-series") residueFieldLabels = false;
      break;
    }
    const coefficient = Number(term.coefficient) === 2 ? "\\zeta" : Number(term.coefficient) === 3 ? "\\zeta^{2}" : "";
    const two = Number(term.two) ? String(2 ** Number(term.two)) : "";
    const j = Number(term.j) ? latexPower("j", Number(term.j)) : "";
    const factor = `${two}${coefficient}${j}`;
    collected.push({coefficient: term.coefficient, label: `${two}${j}(${basisLabel})`});
    return factor ? `${factor}\\left(${basisLabel}\\right)` : basisLabel;
  }).join("+") || "0";
  // Only the explicitly F4 quotient is collected here. Unsupported syntax
  // and integer/Witt levels retain their original, unguessed expression.
  const simplified = residueFieldLabels
    ? window.HFPSSDisplayBasis?.combineLabels(collected, {coefficientContext: "F4"}) : null;
  return simplified?.supported ? simplified.label : fallback;
}

function inspectQuotientRepresentative(record) {
  state.selectedClassId = null;
  state.selectedOccurrence = null;
  state.selectedQuotientInstance = record.instanceKey;
  renderFateInspector();
  const description = record.uncertain ? "Potential representative; outgoing map incomplete" : "Computed quotient representative";
  const basis = record.displayBasis ? ` Display coordinates in the computed quotient basis: [${record.displayBasis.row.map(f4DisplayLatex).join(", ")}].` : "";
  toast(`${description}: ${record.item.label}.${basis} Read-only viewport result; no saved class was changed.`);
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

function packedClassInstances(ws, bounds, metrics, extraInstances = [], presentation = null, algebra = undefined) {
  const instances = periodicClassInstances(ws, bounds, presentation, algebra).map((record) => ({
    ...record,
    key: record.instanceKey,
    cellKey: `${record.grade.stem}:${record.grade.filtration}`,
    label: record.item.label,
    shape: quotientGlyph(record) || glyphShapeFor(ws, record.item),
    size: clamp(metrics.cell * 0.105, 0.55, 7),
  }));
  if (ws.settings?.read_only_catalog) {
    return [...instances, ...extraInstances].map((record, index) => ({
      ...record,
      dx: Number(record.item?.style?.legacy_x_offset || 0) * metrics.cell,
      dy: -Number(record.item?.style?.legacy_y_offset || 0) * metrics.cell,
      size: record.size,
      hitRadius: clamp(metrics.cell * 0.28, 5, 9),
      baseYOffset: 0,
      packIndex: index,
      packCount: 1,
    }));
  }
  const envelope = instances.some(record => record.shape === "finite-two-tower") ? 2.4 : 1.35;
  return window.HFPSSCellLayout.packInstances([...instances, ...extraInstances], metrics.cell, {
    baseYOffset: 0.16, uniformSize: true, glyphEnvelope: envelope,
  });
}

function quotientGlyph(record) {
  if (!record.modulePorts) return null;
  const ports = record.modulePorts;
  const constant = ports.some(p => p.endsWith(":0"));
  const series = ports.some(p => p.endsWith(":1"));
  const witt = ports.some(p => Number(p.split(":")[0]) === 3);
  if (witt) return "witt-j-series";
  // Positive-filtration Z/4 or Z/8 is a finite 2-tower, not W(F4).
  if (new Set(ports.map(p => p.split(":")[0])).size > 1) return "finite-two-tower";
  if (constant && series) return "j-series";
  if (series) return "j-positive-series";
  return "dot";
}

function quotientDescription(record) {
  if (!record.modulePorts) return "";
  const components = record.modulePorts.map(port => {
    const [two, j] = port.split(":").map(Number);
    const scalar = two === 0 ? "" : two === 3 ? "8W · " : `${2 ** two} · `;
    return `${scalar}${j ? "positive-j ideal" : "constant component"}`;
  });
  const shared = record.sharedModulePorts?.length
    ? ` Shared coefficient ports [${record.sharedModulePorts.join(", ")}] are represented by other displayed basis points, not zero.` : "";
  return `${record.uncertain ? "Provisional (quotient unresolved)" : "Displayed coefficient components"}: ${components.join("; ")}. The label names the lowest displayed constant representative when present; positive-j ideals are listed separately and are not rescaled by that label.${shared}`;
}

function packedPoint(record, metrics) {
  const base = pointFor(record.grade, metrics);
  return { x: base.x + record.dx, y: base.y + record.dy };
}

function classInstanceKey(classId, grade) {
  return `${classId}:${grade.stem}:${grade.filtration}`;
}

function classGlyphMarkup(record, point, classNames) {
  if (record.readOnlyRepresentative && record.uncertain) {
    return `<circle class="class-point ${classNames}" style="--point-color:#d97706;fill:white;stroke:#d97706" cx="${point.x}" cy="${point.y}" r="${record.size * 0.72}"/>`;
  }
  if (record.shape === "finite-two-tower") {
    const levels = [...new Set(record.modulePorts.map(port => Number(port.split(":")[0])))].sort((a,b) => a-b);
    const step = record.size * 1.6;
    const ys = levels.map((level, index) => point.y + ((levels.length - 1) / 2 - index) * step);
    return `<g class="class-point finite-two-tower ${classNames}"><line x1="${point.x}" y1="${ys[0]}" x2="${point.x}" y2="${ys[ys.length - 1]}"/>${ys.map(y => `<circle cx="${point.x}" cy="${y}" r="${record.size * 0.72}"/>`).join("")}</g>`;
  }
  if (record.shape === "witt-j-series") {
    const outer = record.size * 1.18;
    const inner = record.size * 0.68;
    return `<g class="class-point witt-j-series ${classNames}"><rect x="${point.x - outer}" y="${point.y - outer}" width="${2 * outer}" height="${2 * outer}" rx="1.2"/><rect class="series-inner" x="${point.x - inner}" y="${point.y - inner}" width="${2 * inner}" height="${2 * inner}" rx="0.8"/></g>`;
  }
  if (record.shape === "j-positive-series") {
    return `<g class="class-point j-positive-series ${classNames}"><circle cx="${point.x}" cy="${point.y}" r="${record.size * 0.92}"/><circle class="series-hole" cx="${point.x}" cy="${point.y}" r="${record.size * 0.4}"/></g>`;
  }
  if (record.shape === "j-series") {
    return `<g class="class-point j-series ${classNames}"><circle cx="${point.x}" cy="${point.y}" r="${record.size * 1.3}"/><circle class="series-core" cx="${point.x}" cy="${point.y}" r="${record.size * 0.42}"/></g>`;
  }
  if (record.shape === "square") {
    return `<rect class="class-point square ${classNames}" x="${point.x - record.size}" y="${point.y - record.size}" width="${2 * record.size}" height="${2 * record.size}" rx="${Math.min(1.2, record.size * 0.2)}"/>`;
  }
  if (record.shape === "circle") {
    return `<circle class="class-point circle ${classNames}" cx="${point.x}" cy="${point.y}" r="${record.size}"/>`;
  }
  if (record.shape === "fat-dot") {
    return `<circle class="class-point fat-dot ${classNames}" cx="${point.x}" cy="${point.y}" r="${record.size * 1.28}"/>`;
  }
  if (record.shape === "unknown") {
    const size = record.size * 0.82;
    return `<path class="class-point unknown-glyph ${classNames}" d="M ${point.x} ${point.y - size} L ${point.x + size} ${point.y} L ${point.x} ${point.y + size} L ${point.x - size} ${point.y} Z"/>`;
  }
  return `<circle class="class-point dot-glyph ${classNames}" cx="${point.x}" cy="${point.y}" r="${record.size * 0.72}"/>`;
}

function seriesTruncation(record) {
  const style = record.item?.style || {};
  if (record.shape !== "j-positive-series" || style.series_kind !== "h1-truncated-j-adic") return null;
  const origin = Number(style.series_origin_stem ?? record.grade.stem);
  const period = Math.max(1, Number(style.series_object_period_stem || 64));
  const step = Math.max(1, Number(style.series_stem_step || 4));
  const loss = Math.max(0, Number(style.series_bottom_loss_per_step || 1));
  const base = Math.max(0, Number(style.series_base_order || 1));
  const residue = ((Number(record.grade.stem) - origin) % period + period) % period;
  const order = base + Math.floor(residue / step) * loss;
  return {
    order,
    text: `j^${order} F4[[j]] · h1-tower bottom rises by one j-grading every ${step} stems`,
  };
}

function classLabelMarkup(record, point, metrics, visible) {
  const persistentUnit = Boolean(record.item.style?.multiplicative_unit) && !record.periodic;
  const selectedQuotient = record.readOnlyRepresentative && record.instanceKey === state.selectedQuotientInstance;
  const selected = state.selectedOccurrence;
  const currentSelection = selected?.workspaceId === state.workspaceId && selected.page === workspace().page && selected.classId === state.selectedClassId;
  const exact = currentSelection && selected.instanceKey === record.instanceKey;
  const selectedAnchor = !currentSelection && !record.periodic && record.item.id === state.selectedClassId;
  if ((!exact && !selectedAnchor && !persistentUnit && !selectedQuotient) || !inBounds(record.grade, visible)) return "";
  const labelGap = Math.max(9, Math.min(18, metrics.cell * 0.45));
  const labelX = point.x + labelGap;
  const name = periodicDisplayLabel(record);
  const degree = exact || selectedAnchor || selectedQuotient ? `<small class="selected-bidegree">(${record.grade.stem}, ${record.grade.filtration})</small>` : "";
  return `<foreignObject class="label-host${exact ? " selected-occurrence-label" : ""}" data-label-point-x="${point.x}" data-label-point-y="${point.y}" data-label-gap="${labelGap}" x="${labelX}" y="${point.y - 10}" width="280" height="38"><div xmlns="http://www.w3.org/1999/xhtml" class="selected-class-label"><span class="latex-label" data-latex="${escapeHtml(name)}"></span>${degree}</div></foreignObject>`;
}

function periodicDifferentials(ws, bounds, candidateDiagnostics = null, algebra = pageAlgebra(ws, bounds)) {
  const byId = new Map(ws.classes.map((item) => [item.id, item]));
  const liveIds = new Set(liveClassesAt(ws).map((item) => item.id));
  const results = [];
  const seen = new Set();
  for (const diff of ws.differentials.filter((item) => item.page === ws.page)) {
    if (algebra?.isZero(diff)) continue;
    const source = algebra?.endpoints(diff).source || byId.get(diff.source_id);
    const target = algebra?.endpoints(diff).target || byId.get(diff.target_id);
    if (diff.linear_map_id && !(source?.style?.e2_pattern || source?.style?.e2_components)) continue;
    if (!source || !target || !liveIds.has(source.id) || !liveIds.has(target.id)) continue;
    const periods = periodsForDifferential(ws, diff);
    const stemDelta = target.grade.stem - source.grade.stem;
    const filtrationDelta = target.grade.filtration - source.grade.filtration;
    // The source of a visible d_r can lie r rows below the viewport (and
    // one column to its right). Search the swept source box, not just the
    // visible points; the exact segment test below also handles crossings
    // for which neither endpoint is visible. Keep the real endpoint grades.
    const sourceBounds = {
      stemMin: bounds.stemMin - Math.max(0, stemDelta),
      stemMax: bounds.stemMax - Math.min(0, stemDelta),
      filtrationMin: bounds.filtrationMin - Math.max(0, filtrationDelta),
      filtrationMax: bounds.filtrationMax - Math.min(0, filtrationDelta),
    };
    for (const copy of latticeCopies(source.grade, periods, sourceBounds)) {
      const sourceGrade = copy.grade;
      const targetGrade = {
        ...target.grade,
        stem: sourceGrade.stem + stemDelta,
        filtration: sourceGrade.filtration + filtrationDelta,
      };
      let candidate = null;
      if (algebra) {
        const typedSource = source.style?.e2_pattern || source.style?.e2_components;
        const typedTarget = target.style?.e2_pattern || target.style?.e2_components;
        if (typedSource && typedTarget) {
          if (algebra.candidateState) {
            candidate = algebra.candidateState(diff, sourceGrade, targetGrade);
            if (candidate.status !== "possible") {
              if (candidateDiagnostics && segmentIntersectsBounds(sourceGrade, targetGrade, bounds)) {
                candidateDiagnostics.push({id: diff.id, status: candidate.status,
                  sourceGrade, targetGrade, reasons: candidate.reasons});
              }
              continue;
            }
          } else if (!algebra.maps(source, target, sourceGrade, targetGrade).length) continue;
        } else {
          // A manual endpoint must not bypass the other endpoint's quotient.
          // Self-maps test every remaining 2/j layer, not just the constant.
          if (typedSource && !algebra.maps(source, source, sourceGrade, sourceGrade).length) continue;
          if (typedTarget && !algebra.maps(target, target, targetGrade, targetGrade).length) continue;
        }
      }
      // Keep one edge for every source-table row.  Different coefficient
      // ports or basis classes can occupy the same bidegree, so coordinate-
      // only deduplication silently erased genuine differential families.
      const key = `${diff.id}:${sourceGrade.stem}:${sourceGrade.filtration}:${targetGrade.stem}:${targetGrade.filtration}`;
      if (segmentIntersectsBounds(sourceGrade, targetGrade, bounds) && !seen.has(key)) {
        seen.add(key);
        const unitInvariant = Boolean(algebra?.unitInvariant?.(diff));
        const renderedDiff = algebra && (!algebra.canApply(diff) || (candidate?.conditional && !unitInvariant))
          ? {...diff, status: "review"} : diff;
        // Anchor a conditional vector in a genuinely surviving branch,
        // never in the placeholder P+Q. This does not assign its coefficient.
        const pair = candidate?.variants?.[0];
        results.push({ diff: renderedDiff, sourceNode: pair?.source || source,
          targetNode: pair?.target || target, sourceGrade, targetGrade, periodic: copy.periodic,
          ...(candidate ? {candidate} : {}), unitInvariant });
      }
    }
  }
  return results;
}

function visibleRelations(ws, liveIds) {
  return ws.propositions.filter((proposition) => {
    if (proposition.kind !== "relation") return false;
    if (proposition.status === "superseded" || proposition.conclusion?.source_schema_retirement) return false;
    const sourceId = proposition.conclusion?.source_id;
    const targetId = proposition.conclusion?.target_id;
    const page = Number(proposition.conclusion?.page || 2);
    return sourceId && targetId && page <= ws.page && liveIds.has(sourceId) && liveIds.has(targetId);
  });
}

function periodicRelations(ws, liveIds, bounds, algebra = pageAlgebra(ws, bounds)) {
  const classes = new Map(ws.classes.map((item) => [item.id, item]));
  const periods = workspaceRenderPeriods(ws);
  const results = [];
  for (const proposition of visibleRelations(ws, liveIds)) {
    const source = classes.get(proposition.conclusion.source_id);
    const target = classes.get(proposition.conclusion.target_id);
    if (!source || !target) continue;
    const stemDelta = target.grade.stem - source.grade.stem;
    const filtrationDelta = target.grade.filtration - source.grade.filtration;
    for (const copy of latticeCopies(source.grade, periods, bounds)) {
      const targetGrade = {
        ...target.grade,
        stem: copy.grade.stem + stemDelta,
        filtration: copy.grade.filtration + filtrationDelta,
      };
      if (algebra && source.style?.e2_pattern && target.style?.e2_pattern
          && !algebra.maps(source, target, copy.grade, targetGrade).length) continue;
      if (inBounds(copy.grade, bounds) || inBounds(targetGrade, bounds)) {
        results.push({ proposition, source, target, sourceGrade: copy.grade, targetGrade, periodic: copy.periodic });
      }
    }
  }
  return results;
}

function constrainView() {
  if (!workspace()) return;
  state.view.zoom = clamp(state.view.zoom, 0.18, 16);
  const m = chartMetrics();
  // The only camera guard: never move the x-axis into the upper half.
  // Horizontal panning and movement toward arbitrarily high filtration remain free.
  state.view.panY = Math.max(state.view.panY, m.minimumAxisY - m.baseAxisY);
}

function fitClassLabelsToViewport(svg, metrics) {
  const {width, height} = metrics;
  if (!(width > 0 && height > 0)) return;
  const padding = Math.min(4, width / 4, height / 4);
  for (const host of svg.querySelectorAll(".label-host[data-label-point-x]")) {
    const label = host.querySelector(".selected-class-label");
    if (!label) continue;
    // Measure the actual typeset name and bidegree, not a fixed 280px box.
    label.style.width = "max-content";
    label.style.transform = "";
    // Layout sizes inside foreignObject use viewBox units; a screen-space
    // getBoundingClientRect() would also include the outer SVG/CSS scale.
    const naturalWidth = label.offsetWidth, naturalHeight = label.offsetHeight;
    if (!(naturalWidth > 0 && naturalHeight > 0)) continue;
    const scale = Math.min(1, (width - 2 * padding) / naturalWidth, (height - 2 * padding) / naturalHeight);
    const labelWidth = naturalWidth * scale, labelHeight = naturalHeight * scale;
    const pointX = Number(host.dataset.labelPointX), pointY = Number(host.dataset.labelPointY);
    const gap = Number(host.dataset.labelGap);
    const right = pointX + gap, left = pointX - gap - labelWidth;
    const preferredX = right + labelWidth <= width - padding ? right : left;
    const x = Math.max(padding, Math.min(width - padding - labelWidth, preferredX));
    const y = Math.max(padding, Math.min(height - padding - labelHeight, pointY - 10));
    host.setAttribute("x", x);
    host.setAttribute("y", y);
    host.setAttribute("width", labelWidth);
    host.setAttribute("height", labelHeight);
    label.style.transformOrigin = "top left";
    label.style.transform = scale < 1 ? `scale(${scale})` : "";
  }
}

function renderMathInChart(metrics = chartMetrics()) {
  const svg = $("#chart");
  svg.querySelectorAll(".latex-label[data-latex]").forEach((node) => {
    if (window.katex) katex.render(node.dataset.latex, node, { throwOnError: false, displayMode: false, trust: false });
    else node.textContent = node.dataset.latex;
  });
  fitClassLabelsToViewport(svg, metrics);
}

function replaceSvgMarkup(svg, markup) {
  const scratch = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  scratch.innerHTML = markup;
  const fragment = document.createDocumentFragment();
  while (scratch.firstChild) fragment.appendChild(scratch.firstChild);
  svg.replaceChildren(fragment);
}

function beginChartPageRender(ws) {
  const svg = $("#chart");
  const baselineNote = $("#document-baseline-note");
  if (baselineNote) {
    const documentBaseline = state.project?.research_brief?.document_baseline === true;
    baselineNote.hidden = !documentBaseline;
    baselineNote.textContent = documentBaseline
      ? "Document baseline: unresolved items follow the documented chart; verified corrections are retained, but this does not represent independent verification of every claim."
      : "";
  }
  const sector = (state.project.grading_sectors || []).find(item => item.workspace_id === ws.id);
  chartPagePresentation = {workspaceId: ws.id, page: ws.page,
    caption: `${sector ? compactSectorLabel(sector) : ws.grading_label} · E${ws.page}`,
    status: pageStatusText(ws)};
  svg.dataset.requestedPage = String(ws.page);
  svg.dataset.requestedWorkspace = ws.id;
  svg.setAttribute("aria-busy", "true");
  delete svg.dataset.renderError;
  const previous = svg.dataset.renderedPage;
  const retained = previous
    ? `chart still ${svg.dataset.renderedWorkspace === ws.id ? "" : "previous workspace "}E${previous}`
    : "chart not yet rendered";
  const pending = `Rendering E${ws.page}; ${retained}`;
  $("#chart-caption").textContent = pending;
  $("#page-status").textContent = pending;
}

function updateChartPageStatus(ws, text, append = false) {
  if (chartPagePresentation?.workspaceId === ws.id && chartPagePresentation.page === ws.page) {
    chartPagePresentation.status = append ? `${chartPagePresentation.status} ${text}` : text;
    return;
  }
  // A same-page pan can update status immediately; a different page must
  // not describe the old SVG as the new quotient before it is committed.
  const svg = $("#chart");
  if (svg.dataset.renderedWorkspace !== ws.id || svg.dataset.renderedPage !== String(ws.page)) {
    beginChartPageRender(ws);
    updateChartPageStatus(ws, text, append);
    return;
  }
  const status = $("#page-status");
  status.textContent = append ? `${status.textContent} ${text}` : text;
}

function markChartPageCommitted(svg, ws) {
  svg.dataset.renderedPage = String(ws.page);
  svg.dataset.renderedWorkspace = ws.id;
  svg.setAttribute("aria-busy", "false");
  delete svg.dataset.requestedPage;
  delete svg.dataset.requestedWorkspace;
  delete svg.dataset.renderError;
  if (chartPagePresentation?.workspaceId === ws.id && chartPagePresentation.page === ws.page) {
    $("#chart-caption").textContent = chartPagePresentation.caption;
    $("#page-status").textContent = chartPagePresentation.status;
    chartPagePresentation = null;
  }
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

function standardBasisCoordinates(rank, index) {
  return Array.from({ length: rank }, (_, position) => position === index ? "1" : "0");
}

function cellPortRecords(ws, cell) {
  const ports = new Map();
  const add = (label, coordinates, projectiveCoordinates = coordinates, kind = "named") => {
    if (!projectiveCoordinates?.length || projectiveCoordinates.every((value) => value === "0")) return;
    const key = projectiveCoordinates.join(":");
    if (!ports.has(key)) ports.set(key, { key, label, coordinates, projectiveCoordinates, kind });
  };
  cell.basis.forEach((item, index) => {
    const coordinates = standardBasisCoordinates(cell.basis.length, index);
    add(item.label, coordinates, coordinates, "basis");
  });
  (cell.display_basis || []).forEach((item) => add(item.label, item.coordinates, item.projective_coordinates, "display"));
  (cell.named_vectors || []).forEach((item) => add(item.label, item.coordinates, item.projective_coordinates, "named"));
  activeDifferentialMaps(ws).filter((item) => item.target_cell_id === cell.id).forEach((item) => {
    (item.image_ports || []).filter((port) => !port.zero).forEach((port) => add(
      vectorText(port.projective_coordinates), port.coordinates, port.projective_coordinates, "image",
    ));
  });
  return [...ports.values()];
}

function cellChartLayout(ws, metrics, bounds) {
  const positions = new Map();
  const enumeratedCells = new Set(ws.classes.filter(n => n.style?.e2_pattern || n.style?.e2_components).map(n => n.cell_id).filter(Boolean));
  for (const cell of explicitCells(ws).filter((item) => !enumeratedCells.has(item.id) && item.page <= ws.page && inBounds(item.grade, bounds))) {
    const center = pointFor(cell.grade, metrics);
    const ports = cellPortRecords(ws, cell);
    const width = Math.max(48, ports.length * 15 + 12);
    const byKey = new Map();
    ports.forEach((port, index) => {
      const x = center.x + (index - (ports.length - 1) / 2) * 15;
      byKey.set(port.key, { ...port, x, y: center.y });
    });
    positions.set(cell.id, { cell, center, width, ports, byKey });
  }
  return positions;
}

function cellMapSvg(ws, layout) {
  let markup = "";
  for (const item of activeDifferentialMaps(ws).filter((record) => record.page === ws.page)) {
    const source = item.source_cell_id ? layout.get(item.source_cell_id) : null;
    const target = item.target_cell_id ? layout.get(item.target_cell_id) : null;
    if (!source) continue;
    for (const port of item.image_ports || []) {
      const sourceKey = standardBasisCoordinates(source.cell.basis.length, source.cell.basis.findIndex((basis) => basis.id === port.source_basis_id)).join(":");
      const from = source.byKey.get(sourceKey) || source.center;
      if (port.zero || !target) {
        markup += `<text class="linear-zero-label" x="${from.x + 5}" y="${from.y - 13}">0</text>`;
        continue;
      }
      const to = target.byKey.get((port.projective_coordinates || []).join(":")) || target.center;
      const admitted = ["established", "verified", "source-verified"].includes(item.status) ? "accepted" : "under-review";
      markup += `<line class="differential linear-map ${admitted}" data-linear-map="${escapeHtml(item.id)}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"><title>d_${item.page}(${escapeHtml(port.source_label)}) = ${escapeHtml(vectorText(port.coordinates))} · ${escapeHtml(item.status)}${item.coverage === "complete" ? " · complete" : " · partial"}</title></line>`;
    }
  }
  return markup;
}

function cellGlyphSvg(layout) {
  let markup = "";
  for (const { cell, center, width, ports, byKey } of layout.values()) {
    const selected = state.selectedCellId === cell.id ? "selected" : "";
    markup += `<g class="vector-cell ${selected}" data-cell="${escapeHtml(cell.id)}" role="button" tabindex="0" aria-label="rank ${cell.basis.length} F4 cell at ${escapeHtml(gradeText(cell.grade))}"><rect class="vector-cell-hull" x="${center.x - width / 2}" y="${center.y - 12}" width="${width}" height="24" rx="10"/><text class="vector-cell-rank" x="${center.x - width / 2 + 4}" y="${center.y - 16}">F4^${cell.basis.length}</text>`;
    for (const port of ports) {
      const point = byKey.get(port.key);
      markup += `<circle class="combination-port ${escapeHtml(port.kind)}" cx="${point.x}" cy="${point.y}" r="4"><title>${escapeHtml(port.label)} · ${escapeHtml(vectorText(port.coordinates))} · projective ${escapeHtml(vectorText(port.projectiveCoordinates))}</title></circle>`;
    }
    markup += `<foreignObject class="label-host cell-label-host" x="${center.x + width / 2 + 5}" y="${center.y - 9}" width="190" height="20"><div xmlns="http://www.w3.org/1999/xhtml" class="latex-label" data-latex="${escapeHtml(cell.named_vectors?.[0]?.label || cell.basis[0]?.label || cell.id)}"></div></foreignObject></g>`;
  }
  return markup;
}

// Coalesce certified aliases only at the SVG boundary. The algebra and
// periodicDifferentials retain every source-table row and its provenance.
function differentialRenderGroups(ws, occurrences, algebra) {
  const claims = new Map(ws.propositions.map(claim => [claim.id, claim]));
  const canonical = value => Array.isArray(value) ? value.map(canonical)
    : value && typeof value === "object"
      ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
  const endpoint = node => {
    const style = node?.style || {};
    const components = style.e2_components && Object.keys(style.e2_components).length
      ? style.e2_components : style.e2_pattern ? {[style.e2_pattern]: 1} : null;
    const two = Number(style.two_valuation || 0), j = Number(style.j_order || 0);
    if (!components || !Number.isFinite(two) || !Number.isFinite(j)) return null;
    return {components, two, j, coefficientContext: node.coefficient_context_id || null,
      convention: node.convention_id || null};
  };
  const groups = [], byKey = new Map(), metadata = new Map();
  for (const item of occurrences) {
    const claim = claims.get(item.diff.proposition_id), conclusion = claim?.conclusion;
    const certificate = conclusion?.verification_certificate;
    const alias = {id: item.diff.id, propositionId: item.diff.proposition_id,
      label: item.diff.label || `d${item.diff.page}`, statement: claim?.statement,
      status: item.diff.status, periodNotes: item.diff.period_notes || "single table anchor",
      proof: certificate?.method, sourceRefs: [...new Set([
        ...(claim?.source_refs || []), claim?.source_ref, ...(certificate?.source_refs || []),
        conclusion?.period_source_ref,
      ].filter(Boolean))]};
    const source = endpoint(item.sourceNode), target = endpoint(item.targetNode);
    const coefficient = algebra?.coefficientState(item.diff);
    const fact = conclusion?.fact_id;
    const certified = typeof fact === "string" && fact.trim()
      && item.diff.status === "verified" && claim?.status === "verified"
      && conclusion.admission_status === "verified" && certificate?.status === "verified"
      && !item.diff.manual_periodicity_id
      && algebra?.canApply(item.diff) && coefficient?.resolved && coefficient.value !== undefined
      && source && target;
    // Equal geometry alone is never evidence of equal maps. In particular
    // distinguish vectors, exact Witt/j ports, coefficient state and fact.
    const key = certified ? JSON.stringify(canonical([fact, item.diff.page,
      item.diff.status, coefficient, source, target, item.sourceGrade, item.targetGrade])) : null;
    const existing = key && byKey.get(key);
    if (existing) {
      existing.renderAliases.push(alias);
    } else {
      const group = {...item, renderAliases: [alias]};
      groups.push(group);
      // A resolved scalar's parameter ID is provenance, not its map value.
      // Component parameters and conditional equations are not scalar aliases.
      const equation = source && target && coefficient?.resolved
        && [1, 2, 3].includes(coefficient.value) && coefficient.component === undefined
        && !coefficient.zeroEulerImage && !item.candidate?.conditional
        && !item.diff.manual_periodicity_id
        ? JSON.stringify(canonical([item.diff.page, coefficient.value,
          source, target, item.sourceGrade, item.targetGrade])) : null;
      metadata.set(group, {certified, claim, fact, equation});
      if (key) byKey.set(key, group);
    }
  }
  // A new proof can explicitly name a historical equation as a display alias.
  // This never changes admission or drops the historical row from the algebra.
  // Require one unambiguous certified owner and identical exact occurrence maps;
  // equal targets alone (for example P and Q mapping to T) do not suffice.
  const owners = new Map();
  for (const group of groups) {
    const data = metadata.get(group);
    if (!data.certified || !data.equation) continue;
    for (const alias of data.claim.conclusion.render_equation_aliases || []) {
      if (alias.scope !== "same-equation-only" || alias.status !== "review"
          || alias.page !== group.diff.page || typeof alias.fact_id !== "string") continue;
      const key = JSON.stringify([alias.fact_id, data.equation]);
      if (!owners.has(key)) owners.set(key, new Set());
      owners.get(key).add(group);
    }
  }
  return groups.filter(group => {
    const data = metadata.get(group);
    if (group.diff.status !== "review" || data.claim?.status !== "review"
        || data.claim.conclusion?.admission_status !== "review" || !data.equation) return true;
    const matches = owners.get(JSON.stringify([data.fact, data.equation]));
    if (matches?.size !== 1) return true;
    const owner = [...matches][0];
    owner.renderAliases.push(...group.renderAliases.map(alias => ({...alias, historicalEquation: true})));
    return false;
  });
}

function differentialRenderTitle(item) {
  const provenance = item.renderAliases.map((alias, index) => (index
    ? alias.historicalEquation ? " | Historical equation alias (proof remains under review): "
      : " | Same certified map; alternate source: " : "") + [
    alias.label, alias.statement, alias.status, alias.periodNotes,
    `Source row: ${alias.id}`, alias.propositionId && `Claim: ${alias.propositionId}`,
    alias.proof, alias.sourceRefs.length && `Sources: ${alias.sourceRefs.join("; ")}`,
  ].filter(Boolean).join(" · ")).join("");
  if (item.unitInvariant) return `${provenance} · Verified nonzero rank-one map; exact F4 unit unassigned. Kernel and image are independent of this isolated scalar.`;
  if (!item.candidate?.conditional) return provenance;
  const values = [...new Set(item.candidate.variants.map(v => v.coefficient.value))]
    .map(value => value === 1 ? "1" : f4DisplayLatex(value)).join(", ");
  return `${provenance} · Conditional candidate: surviving coefficient values ${values}; no parameter has been assigned.`;
}

function differentialCandidateSummary(diagnostics) {
  const count = status => new Set(diagnostics.filter(d => d.status === status).map(d => d.id)).size;
  const contradicted = count("contradicted"), unknown = count("unknown");
  const families = count => `${count} candidate ${count === 1 ? "family has" : "families have"}`;
  return [contradicted ? `${families(contradicted)} occurrences excluded by certified zero-outgoing maps; their sources and historical records are retained.` : "",
    unknown ? `${families(unknown)} unresolved endpoint/coefficient data here; no coefficient-1 substitution is used.` : ""].filter(Boolean).join(" ");
}

function differentialDisplayCoefficient(ws, diff, algebra) {
  const metadata = (ws.propositions || []).find(p => p.id === diff.proposition_id)?.conclusion || {};
  const parameter = metadata.coefficient_parameter;
  const display = metadata.atlas_display_coefficient || (Object.keys(diff.display_coefficient || {}).length ? diff.display_coefficient : null);
  const coefficient = algebra?.coefficientState(diff);
  // A factor on one summand of P+bQ is not an overall scalar on the arrow.
  if (parameter?.target_component !== undefined || coefficient?.component !== undefined) return null;
  if (display && ![1, 2, 3].includes(display.basis_ratio)) return null;
  if (!coefficient?.resolved && algebra?.unitInvariant?.(diff)) {
    const symbol = parameter.symbol;
    const conjugate = parameter.frobenius_power === 1 ? `(${symbol})^2` : symbol;
    const scalar = f4DisplayLatex(display?.basis_ratio ?? 1);
    return {value: null, latex: `${scalar}${conjugate}`, nonzeroUnit: true,
      basis: display ? "unscaled expanded generators" : "recorded generators"};
  }
  const value = coefficient?.resolved ? coefficient.value
    : !parameter?.proof_binding && !metadata.coefficient_proof_registration && display?.resolved ? display.value : null;
  if (![1, 2, 3].includes(value)) return null;
  const normalized = coefficient?.resolved ? f4DisplayMultiply(value, display?.basis_ratio ?? 1) : value;
  return {value: normalized, latex: f4DisplayLatex(normalized),
    basis: display ? "unscaled expanded generators" : "recorded generators",
    sourceUnit: display?.source_unit ?? 1, targetUnit: display?.target_unit ?? 1};
}

function differentialCoefficientMarkup(ws, item, algebra, from, to) {
  const metadata = (ws.propositions || []).find(p => p.id === item.diff.proposition_id)?.conclusion || {};
  if (item.displayBasisCoefficient !== undefined) {
    const value = item.displayBasisCoefficient;
    if (value === 1) return "";
    return `<foreignObject class="differential-coefficient" data-coefficient-for="${escapeHtml(item.diff.id)}" data-coefficient="${value}" x="${(from.x + to.x) / 2}" y="${(from.y + to.y) / 2}" width="1" height="1"><div xmlns="http://www.w3.org/1999/xhtml" class="latex-label" data-latex="${f4DisplayLatex(value)}" title="Coefficient in the displayed basis; the stored equation is unchanged."></div></foreignObject>`;
  }
  // Relative coefficients belong to the target expression, not a scalar badge.
  // Keep P+bQ distinct from an overall b(P+Q); the target and record retain it.
  if (metadata.coefficient_parameter?.target_component !== undefined
      || algebra?.coefficientState(item.diff)?.component !== undefined) return "";
  const coefficient = differentialDisplayCoefficient(ws, item.diff, algebra);
  if (coefficient?.value === 1) return "";
  const declared = metadata.coefficient_parameter || metadata.atlas_display_coefficient || item.diff.display_coefficient;
  if (!coefficient && (!declared || !Object.keys(declared).length)) return "";
  const latex = coefficient?.latex || "?";
  const x = (from.x + to.x) / 2, y = (from.y + to.y) / 2;
  const title = coefficient?.nonzeroUnit
    ? `A verified nonzero F4 unit relative to ${coefficient.basis}. Its exact value is unassigned; only the isolated one-dimensional kernel and image are unit-independent.`
    : coefficient ? `Coefficient relative to ${coefficient.basis}; point labels retain transported units.`
    : "A normalized scalar is not determined here; this does not mean coefficient 1.";
  return `<foreignObject class="differential-coefficient" data-coefficient-for="${escapeHtml(item.diff.id)}" data-coefficient="${coefficient?.nonzeroUnit ? "nonzero-unit" : coefficient?.value ?? "unresolved"}" x="${x}" y="${y}" width="1" height="1"><div xmlns="http://www.w3.org/1999/xhtml" class="latex-label" data-latex="${latex}" title="${title}"></div></foreignObject>`;
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

  const algebra = pageAlgebra(ws, buffered);
  const candidateDiagnostics = [];
  const differentialOccurrences = periodicDifferentials(ws, buffered, candidateDiagnostics, algebra);
  const presentation = window.HFPSSChartPresentation?.create(algebra, differentialOccurrences, buffered);
  const previewInstances = drawingPeriodicityPreviewInstances(buffered);
  const allPackedInstances = packedClassInstances(ws, buffered, m, previewInstances, presentation, algebra);
  const packedInstances = allPackedInstances.filter((record) => !record.preview);
  window.renderPublishedTableLedger?.(ws, undefined, algebra);
  updateChartPageStatus(ws, pageStatusText(ws, algebra));
  const packedPreviewInstances = allPackedInstances.filter((record) => record.preview);
  const instancePoints = new Map(packedInstances.map((record) => [record.instanceKey, packedPoint(record, m)]));
  for (const record of packedInstances) {
    instancePoints.set(classInstanceKey(record.item.id, record.grade), packedPoint(record, m));
    const slot = e2DisplaySlot(record.item, record.grade);
    if (slot) instancePoints.set(slot, packedPoint(record, m));
    for (const slot of record.algebraSlots || (presentation || algebra)?.displaySlots(record.item, record.grade) || []) instancePoints.set(slot, packedPoint(record, m));
  }
  const classesById = new Map(ws.classes.map((item) => [item.id, item]));
  const combinationPorts = new Map(), patternLabels = new Map();
  for (const node of ws.classes) {
    const pattern = node.style?.e2_pattern;
    if (!pattern || node.archived || node.style.two_valuation || node.style.j_order) continue;
    if (!patternLabels.has(pattern)) patternLabels.set(pattern, []);
    patternLabels.get(pattern).push(node);
  }
  const endpointPoint = (id, grade, effectiveNode, branch) => {
    const node = effectiveNode || classesById.get(id);
    const display = presentation?.endpoint(node, grade, branch?.two || 0, branch?.j || 0);
    if (display?.live) {
      if (display.entries.length === 1) {
        const point = instancePoints.get(display.entries[0].slot);
        if (point) return {...point, basisEndpoint: display};
      } else if (display.entries.length > 1) {
        // A remaining dependent direction is an exact named combination,
        // not an extra basis dot and not the unweighted centre of its terms.
        if (!combinationPorts.has(display.key)) {
          const center = pointFor(grade, m);
          const siblings = [...combinationPorts.values()].filter(p => p.grade.stem === grade.stem && p.grade.filtration === grade.filtration).length;
          combinationPorts.set(display.key, {x: center.x + m.cell * (0.18 - 0.12 * (siblings % 3)),
            y: center.y + m.cell * (0.3 - 0.14 * Math.floor(siblings / 3)), grade,
            label: quotientRepresentativeLabel(ws, {grade, terms: display.terms}, patternLabels), basisEndpoint: display});
        }
        return combinationPorts.get(display.key);
      }
    }
    const vectorPoints = (algebra?.endpointSlots(node, grade) || []).map(slot => instancePoints.get(slot)).filter(Boolean);
    if (vectorPoints.length) return {x: vectorPoints.reduce((sum, p) => sum + p.x, 0) / vectorPoints.length,
      y: vectorPoints.reduce((sum, p) => sum + p.y, 0) / vectorPoints.length};
    return instancePoints.get(classInstanceKey(id, grade)) || instancePoints.get(e2DisplaySlot(node, grade)) || pointFor(grade, m);
  };
  const liveIds = new Set(liveClassesAt(ws).map((item) => item.id));
  const vectorCellLayout = cellChartLayout(ws, m, buffered);
  markup += cellMapSvg(ws, vectorCellLayout);
  markup += drawingPeriodicityPreviewSvg(m, buffered, packedPreviewInstances, instancePoints, "connections");
  for (const item of periodicRelations(ws, liveIds, buffered, algebra)) {
    const relation = item.proposition;
    const source = item.source;
    const target = item.target;
    const branch = presentation && algebra.maps(source, target, item.sourceGrade, item.targetGrade)[0];
    const from = endpointPoint(source.id, item.sourceGrade, source, branch);
    const to = endpointPoint(target.id, item.targetGrade, target, branch);
    const manualDrawing = relation.conclusion?.manual_periodicity_id ? "manual-drawing-periodic" : "";
    const chartConnection = relation.conclusion?.chart_connection;
    const chartClass = chartConnection?.kind ? `dkllw-${chartConnection.kind}` : "";
    markup += `<line class="relation-line ${relationVisualState(relation)} ${manualDrawing} ${chartClass} ${item.periodic ? "periodic" : ""}" data-relation="${escapeHtml(relation.id)}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"><title>${escapeHtml(chartConnection ? `${chartConnection.multiplier} multiplication · ${relation.statement}` : relation.statement)}</title></line>`;
    if (from.basisEndpoint?.adapted || to.basisEndpoint?.adapted) {
      const unit = point => point.basisEndpoint?.entries.length === 1 ? point.basisEndpoint.entries[0].coefficient : 1;
      const value = f4DisplayMultiply(unit(to), f4DisplayMultiply(unit(from), unit(from)));
      markup += differentialCoefficientMarkup(ws, {diff: {id: relation.id}, displayBasisCoefficient: value}, null, from, to);
    }
  }
  const candidateSummary = differentialCandidateSummary(candidateDiagnostics);
  if (candidateSummary) updateChartPageStatus(ws, candidateSummary, true);
  for (const item of differentialRenderGroups(ws, differentialOccurrences, algebra)) {
    // Use one actual common surviving 2/j branch at both ends. The constant
    // term may already be a boundary while its positive-j tail still maps.
    const branch = presentation && algebra.maps(item.sourceNode, item.targetNode, item.sourceGrade, item.targetGrade)
      .find(value => window.HFPSSPageAlgebra.allowsConstraintBranch(item.diff, value.two || 0, value.j || 0));
    const from = endpointPoint(item.diff.source_id, item.sourceGrade, item.sourceNode, branch);
    const to = endpointPoint(item.diff.target_id, item.targetGrade, item.targetNode, branch);
    const coefficient = algebra?.coefficientState(item.diff);
    if ((from.basisEndpoint?.adapted || to.basisEndpoint?.adapted) && coefficient?.resolved) {
      const unit = point => point.basisEndpoint?.entries.length === 1 ? point.basisEndpoint.entries[0].coefficient : 1;
      const targetUnit = to.basisEndpoint ? unit(to) : coefficient.component === undefined ? coefficient.value : 1;
      item.displayBasisCoefficient = f4DisplayMultiply(targetUnit, f4DisplayMultiply(unit(from), unit(from)));
    }
    const manualDrawing = item.diff.manual_periodicity_id ? "manual-drawing-periodic" : "";
    // escapeHtml is a text-node escape; JSON quotes also need attribute escaping.
    const aliasIds = escapeHtml(JSON.stringify(item.renderAliases.map(alias => alias.id))).replaceAll('"', "&quot;");
    markup += `<line class="differential ${item.periodic ? "periodic" : ""} ${differentialVisualState(item.diff)} ${manualDrawing}" data-differential="${escapeHtml(item.diff.id)}" data-differential-aliases="${aliasIds}" data-pattern-period="${Number(item.diff.period_stem || 0)}" x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"><title>${escapeHtml(differentialRenderTitle(item))}</title></line>`;
    markup += differentialCoefficientMarkup(ws, item, algebra, from, to);
  }
  for (const [key, point] of combinationPorts) {
    const coordinates = point.basisEndpoint.coordinates.map(f4DisplayLatex).join(", ");
    markup += `<g class="combination-endpoint" data-combination-endpoint="${escapeHtml(key)}" role="button" tabindex="0" aria-label="Combination, not an extra basis generator: ${escapeHtml(point.label)} at ${gradeText(point.grade)}"><title>${escapeHtml(point.label)} · (${point.grade.stem}, ${point.grade.filtration}) · displayed-basis coordinates [${coordinates}] · not an extra basis generator</title><text x="${point.x}" y="${point.y}" text-anchor="middle" dominant-baseline="central" font-size="${clamp(m.cell * 0.19, 7, 12)}" paint-order="stroke" stroke="white" stroke-width="3" fill="#334155">Σ</text></g>`;
    if (state.selectedCombinationKey === key) markup += `<foreignObject class="label-host" x="${point.x + 10}" y="${point.y - 12}" width="280" height="42"><div xmlns="http://www.w3.org/1999/xhtml" class="selected-class-label"><span class="latex-label" data-latex="${escapeHtml(point.label)}"></span><small class="selected-bidegree">(${point.grade.stem}, ${point.grade.filtration}) · [${coordinates}]</small></div></foreignObject>`;
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
    const selected = state.connectionStart === record.item.id || state.selectedClassId === record.item.id || state.selectedQuotientInstance === record.instanceKey ? "selected" : "";
    const manualDrawing = record.item.manual_periodicity_id ? "manual-drawing-periodic" : "";
    const classes = `${record.occurrenceState || visualStateFor(ws, record.item)} ${selected} ${record.periodic ? "periodic" : ""} ${manualDrawing}`;
    const label = classLabelMarkup(record, point, m, visible);
    const periodicAttribute = record.periodic ? ' data-periodic-copy="true"' : "";
    const truncation = seriesTruncation(record);
    const seriesText = truncation ? `, ${truncation.text}` : "";
    const displayLabel = periodicDisplayLabel(record);
    const representativeText = record.readOnlyRepresentative ? (record.uncertain ? " · Potential representative; outgoing map incomplete · read-only" : record.displayBasis?.adapted ? " · Adapted display basis · read-only" : " · Computed quotient representative · read-only") : "";
    const aria = `${displayLabel} at ${gradeText(record.grade)}${record.periodic ? ", virtual period copy" : ""}${manualDrawing ? ", manual periodic drawing record" : ""}${seriesText}${representativeText}`;
    const unitPeriodText = record.item.style?.multiplicative_unit && !record.periodic
      ? " · W(F4)[[j]] 2-adic unit tower; virtual copies use forward g and D^8"
      : "";
    const tooltip = `${displayLabel} · ${gradeText(record.grade)}${record.periodic ? ` · ${record.item.label} translated by the shared D^m/g lattice` : ""}${unitPeriodText}${truncation ? ` · ${truncation.text}` : ""}${record.modulePorts ? ` · ${quotientDescription(record)}` : ""}${representativeText}`;
    const seriesAttribute = truncation ? ` data-series-bottom-order="${truncation.order}"` : "";
    const readOnlyAttribute = record.readOnlyRepresentative ? ' data-readonly-representative="true"' : "";
    markup += `<g class="class-instance" data-point="${escapeHtml(record.item.id)}" data-class-instance="${escapeHtml(record.instanceKey)}"${periodicAttribute}${seriesAttribute}${readOnlyAttribute} role="button" tabindex="0" aria-label="${escapeHtml(aria)}"><title>${escapeHtml(tooltip)}</title><circle class="class-hit-target" cx="${point.x}" cy="${point.y}" r="${record.hitRadius}"/>${classGlyphMarkup(record, point, classes)}${label}</g>`;
  }
  markup += cellGlyphSvg(vectorCellLayout);
  markup += drawingPeriodicityPreviewSvg(m, buffered, packedPreviewInstances, instancePoints, "cycles");
  replaceSvgMarkup(svg, markup);
  markChartPageCommitted(svg, ws);
  renderMathInChart(m);
  const activateClassInstance = (node, event) => {
    event.stopPropagation();
    if (state.suppressClick) {
      state.suppressClick = false;
      return;
    }
    if (node.dataset.readonlyRepresentative) {
      const record = packedInstances.find(item => item.instanceKey === node.dataset.classInstance);
      if (record) { inspectQuotientRepresentative(record); renderChart(); }
      return;
    }
    if (node.dataset.periodicCopy && state.tool !== "inspect") return;
    const occurrence = packedInstances.find(item => item.instanceKey === node.dataset.classInstance);
    onClassClick(node.dataset.point, occurrence);
  };
  svg.onclick = (event) => {
    const combination = event.target.closest?.("[data-combination-endpoint]");
    if (combination) {
      event.stopPropagation();
      const record = combinationPorts.get(combination.dataset.combinationEndpoint);
      if (record) {
        state.selectedCombinationKey = combination.dataset.combinationEndpoint;
        toast(`${record.label} at (${record.grade.stem}, ${record.grade.filtration}); displayed-basis coordinates [${record.basisEndpoint.coordinates.map(f4DisplayLatex).join(", ")}]. Not an extra basis generator; saved data unchanged.`);
        renderChart();
      }
      return;
    }
    const cellNode = event.target.closest?.("[data-cell]");
    if (cellNode) {
      event.stopPropagation();
      state.selectedCellId = cellNode.dataset.cell;
      state.selectedClassId = null;
      renderCellInspector();
      renderChart();
      return;
    }
    const node = event.target.closest?.("[data-point]");
    if (node) activateClassInstance(node, event);
  };
  svg.onkeydown = (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const combination = event.target.closest?.("[data-combination-endpoint]");
    if (combination) { event.preventDefault(); svg.onclick(event); return; }
    const cellNode = event.target.closest?.("[data-cell]");
    if (cellNode) {
      event.preventDefault();
      state.selectedCellId = cellNode.dataset.cell;
      state.selectedClassId = null;
      renderCellInspector();
      renderChart();
      return;
    }
    const node = event.target.closest?.("[data-point]");
    if (!node) return;
    event.preventDefault();
    activateClassInstance(node, event);
  };
}

function schedulePageRender() {
  const ws = workspace();
  const svg = $("#chart");
  pageRenderRequest = {workspaceId: ws.id, page: ws.page};
  beginChartPageRender(ws);
  if (pageRenderFrame) return;
  pageRenderFrame = requestAnimationFrame(() => {
    pageRenderFrame = 0;
    const requested = pageRenderRequest;
    pageRenderRequest = null;
    const current = workspace();
    // A synchronous workspace render may already have replaced this request.
    if (!requested || current?.id !== requested.workspaceId || current.page !== requested.page) return;
    try {
      render();
    } catch (error) {
      if (workspace()?.id !== requested.workspaceId || workspace().page !== requested.page) return;
      const message = error?.message || String(error);
      svg.dataset.renderError = message;
      svg.setAttribute("aria-busy", "false");
      const committed = svg.dataset.renderedWorkspace === requested.workspaceId
        && svg.dataset.renderedPage === String(requested.page);
      const status = $("#page-status");
      if (status) status.textContent = committed
        ? `E${requested.page} chart updated, but page controls failed: ${message}`
        : `Unable to render E${requested.page}; the previous chart is retained. ${message}`;
      if (!committed) {
        const caption = $("#chart-caption");
        if (caption) caption.textContent = `Previous chart retained · E${requested.page} not rendered`;
      }
    }
  });
}

function setPage(page) {
  workspace().page = clamp(Number(page), 2, pageLimit());
  state.pageByWorkspace.set(state.workspaceId, workspace().page);
  state.connectionStart = null;
  state.candidateResults = null;
  state.periodicityPreview = null;
  state.drawingPeriodicityPreview = null;
  state.connectionPointer = null;
  schedulePageRender();
}

async function extendPageLimit() {
  const ws = workspace();
  if (readOnlyCatalog(ws)) return toast("Archived research charts are read-only.");
  const next = pageLimit(ws) + 1;
  try {
    const data = await api(`/api/workspaces/${ws.id}/settings`, { method: "PATCH", body: JSON.stringify({ page_limit: next }) });
    ws.settings = data.settings;
    await refreshHistory(state.project, projectLoadSequence);
    setPage(next);
    toast(`Added E${next} to this workspace.`);
  } catch (error) {
    toast(error.message);
    renderPageSelector();
  }
}

function setTool(tool) {
  if (readOnlyCatalog() && tool !== "inspect") return toast("Archived research charts are read-only.");
  state.tool = tool;
  state.connectionStart = null;
  state.connectionPointer = null;
  render();
}

async function onClassClick(id, occurrence = null) {
  const item = workspace().classes.find((point) => point.id === id);
  if (!item) return;
  state.selectedQuotientInstance = null;
  state.selectedOccurrence = occurrence && state.tool === "inspect"
    ? {workspaceId: state.workspaceId, page: workspace().page, classId: id, instanceKey: occurrence.instanceKey,
      grade: {...occurrence.grade}, label: periodicDisplayLabel(occurrence)} : null;
  if (readOnlyCatalog() && state.tool !== "inspect") state.tool = "inspect";
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
    state.pendingRenameId = id;
    $("#rename-form [name=label]").value = item.label;
    $("#rename-dialog").showModal();
    $("#rename-form [name=label]").focus();
    return;
  }
  state.selectedClassId = item.id;
  state.candidateResults = null;
  state.periodicityPreview = null;
  renderFateInspector();
  renderPersistentPeriodicityTool();
  renderChart();
  const selected = state.selectedOccurrence;
  toast(`${selected?.label || item.label} at ${gradeText(selected?.grade || item.grade)} · ${fateFor(workspace(), item.id)?.conclusion || "unresolved"}`);
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
  state.pendingRelation = { sourceId, targetId };
  $("#relation-endpoints").innerHTML = `${mathMarkup(source.label)} → ${mathMarkup(target.label)} on E${Number(workspace().page)}`;
  $("#relation-form [name=chart_connection_kind]").value = (
    source.grade.stem === target.grade.stem && source.grade.filtration === target.grade.filtration
      ? "vertical-two" : ""
  );
  $("#relation-form [name=source_ref]").value = "";
  $("#relation-dialog").showModal();
}

async function savePendingRelation(event) {
  event.preventDefault();
  const pending = state.pendingRelation;
  if (!pending) return;
  const source = workspace().classes.find((item) => item.id === pending.sourceId);
  const target = workspace().classes.find((item) => item.id === pending.targetId);
  const form = new FormData(event.currentTarget);
  const chartConnectionKind = String(form.get("chart_connection_kind") || "");
  const sourceRef = String(form.get("source_ref") || "");
  try {
    await api(`/api/workspaces/${state.workspaceId}/propositions`, { method: "POST", body: JSON.stringify({ kind: "relation", statement: chartConnectionKind ? `${chartConnectionKind} multiplication: ${source.label} to ${target.label}` : `Relation: ${source.label} ~ ${target.label}`, status: "candidate", conclusion: { source_id: pending.sourceId, target_id: pending.targetId, page: workspace().page }, chart_connection_kind: chartConnectionKind, source_ref: sourceRef, rule: "manual", confidence: 0.5, notes: "Added from the chart relation tool; evidence remains to be supplied." }) });
    $("#relation-dialog").close();
    state.pendingRelation = null;
    state.connectionStart = null;
    state.connectionPointer = null;
    await loadProject();
    toast("Relation recorded in the proposition tree.");
  } catch (error) { toast(error.message); }
}

async function savePendingRename(event) {
  event.preventDefault();
  const id = state.pendingRenameId;
  const label = String(new FormData(event.currentTarget).get("label") || "").trim();
  if (!id || !label) return;
  try {
    await api(`/api/workspaces/${state.workspaceId}/classes/${id}`, { method: "PATCH", body: JSON.stringify({ label }) });
    $("#rename-dialog").close();
    state.pendingRenameId = null;
    await loadProject();
    toast("Class renamed.");
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
  const generatorPreview = $("#class-generator-preview");
  if (!input || !preview) return;
  const ignoredLatexCommands = new Set(["cdot", "frac", "left", "right", "mathbb", "mathrm", "operatorname"]);
  const generators = [...new Set((input.value.match(/\\[A-Za-z]+|[A-Za-z]+(?:_[A-Za-z0-9]+)?/g) || [])
    .map((token) => token.replace(/^\\/, ""))
    .filter((token) => !ignoredLatexCommands.has(token)))];
  if (generatorPreview) {
    generatorPreview.textContent = generators.length
      ? `Basic generators: ${generators.join(", ")}`
      : "Basic generators: none detected";
  }
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
    if ($("#vanishing-line")) workspace().settings.vanishing_line = Number($("#vanishing-line").value);
    const data = await api(`/api/workspaces/${state.workspaceId}/suggestions`, { method: "POST", body: JSON.stringify({ rules: ["LeibnizRule", "VanishingLine"] }) });
    state.suggestions = data.suggestions;
    renderSuggestions();
    toast(`${state.suggestions.length} candidate(s) found.`);
  } catch (error) { toast(error.message); }
}

function renderProjectImportPreview(preview, fileName) {
  const target = $("#import-project-summary");
  const metadata = preview.import || {};
  const isLegacy = metadata.format === "legacy-sseq-ver15.3";
  const summary = metadata.summary || {};
  const legacy = metadata.legacy_summary || {};
  const counts = isLegacy
    ? [
      ["generators received", legacy.generators_received],
      ["classes created", legacy.classes_created],
      ["connections received", legacy.connections_received],
      ["relations created", legacy.relations_created],
      ["differentials created", legacy.differentials_created],
      ["periodicity rules received", legacy.periodicity_rules_received],
      ["manual-unverified rules created", legacy.manual_periodicity_rules_created],
    ].map(([label, count]) => `<li><strong>${escapeHtml(label)}</strong>: ${Number(count || 0)}</li>`).join("")
    : ["workspaces", "classes", "differentials", "propositions", "comparisons", "periodicity_rules"]
      .map((key) => `<li><strong>${escapeHtml(key.replaceAll("_", " "))}</strong>: ${Number(summary[key] || 0)}</li>`)
      .join("");
  const structuredWarnings = (metadata.warnings || []).map((warning) => {
    if (typeof warning === "string") return `<li>${escapeHtml(warning)}</li>`;
    const count = warning.count == null ? "" : ` (${Number(warning.count)})`;
    return `<li><strong>${escapeHtml(warning.code || "legacy-warning")}${escapeHtml(count)}</strong>: ${escapeHtml(warning.message || "Review this converted record.")}</li>`;
  });
  const policyWarnings = [
    preview.mathematical_status_policy,
    metadata.derived_caches_rebuilt ? "Derived fate and differential-event caches will be rebuilt from primary records." : "",
    !isLegacy && metadata.migration_applied ? `Schema migration will be applied: v${metadata.source_schema_version} to v${metadata.schema_version}.` : "",
    !isLegacy && !metadata.migration_applied ? "No schema migration is required." : "",
  ].filter(Boolean).map((warning) => `<li>${escapeHtml(warning)}</li>`);
  const operation = isLegacy
    ? `<p class="import-operation replace"><strong>Import into the current E${Number(metadata.target_page || workspace().page)} canvas in place.</strong> This legacy sseq ver15.3 canvas will be merged into <strong>${escapeHtml(workspace().name)}</strong>; no temporary workspace will be created and existing proof history is retained.</p><p>Legacy glyph semantics are deliberately forgotten as ordinary dots. Stored offsets remain metadata; connections and period rules remain candidate/manual-unverified.</p>`
    : `<p class="import-operation replace"><strong>Replace project.</strong> Applying this reviewed Studio JSON will replace the current project with <strong>${escapeHtml(preview.project.name)}</strong>.</p>`;
  $("#apply-project-import").textContent = isLegacy ? "Import into current page" : "Apply reviewed import";
  target.innerHTML = `<p><strong>${escapeHtml(fileName)}</strong></p>${operation}<p>Revision ${preview.current_revision} → ${preview.would_revision}</p><ul class="import-counts">${counts}</ul><h3>Review warnings</h3><ul>${[...structuredWarnings, ...policyWarnings].join("") || "<li>No warnings reported.</li>"}</ul>`;
}

async function previewProjectImport(file) {
  const dialog = $("#import-project-dialog");
  const applyButton = $("#apply-project-import");
  state.importPreview = null;
  state.importSource = null;
  applyButton.disabled = true;
  $("#import-project-summary").textContent = `Reading ${file.name}...`;
  if (!dialog.open) dialog.showModal();
  try {
    const text = await file.text();
    const project = JSON.parse(text);
    const previewPath = `/api/project/import/preview?source_name=${encodeURIComponent(file.name)}&target_workspace_id=${encodeURIComponent(state.workspaceId)}&target_page=${encodeURIComponent(workspace().page)}`;
    const preview = await api(previewPath, { method: "POST", body: JSON.stringify(project) });
    state.importPreview = preview;
    if (preview.import?.format === "legacy-sseq-ver15.3") {
      state.importSource = {
        legacyCanvas: project,
        sourceName: file.name,
        workspaceName: preview.import?.workspace_name || "",
        targetWorkspaceId: state.workspaceId,
        targetPage: workspace().page,
      };
    }
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
  const previewWorkspaceId = preview.import?.imported_workspace_id || preview.import?.workspace_id || null;
  const isLegacy = preview.import?.format === "legacy-sseq-ver15.3";
  const idleLabel = isLegacy ? "Import into current page" : "Apply reviewed import";
  button.disabled = true;
  button.textContent = "Applying...";
  $("#import-project-summary").insertAdjacentHTML(
    "beforeend",
    '<p id="import-apply-status" class="hint" aria-live="polite">Applying the reviewed import...</p>',
  );
  try {
    if (isLegacy && !state.importSource?.legacyCanvas) {
      throw new Error("The original legacy JSON is no longer available. Choose the file and Preview it again.");
    }
    const commonApply = {
      preview_sha256: preview.preview_sha256,
      expected_revision: preview.current_revision,
      imported_workspace_id: previewWorkspaceId,
    };
    const applyPayload = isLegacy
      ? {
        ...commonApply,
        legacy_canvas: state.importSource.legacyCanvas,
        source_name: state.importSource.sourceName,
        workspace_name: state.importSource.workspaceName,
        target_workspace_id: state.importSource.targetWorkspaceId,
        target_page: state.importSource.targetPage,
      }
      : { ...commonApply, project: preview.project };
    await new Promise((resolve) => requestAnimationFrame(resolve));
    const result = await api("/api/project/import/apply", {
      method: "POST",
      body: JSON.stringify(applyPayload),
    });
    const importedWorkspaceId = result.imported_workspace_id
      || result.import?.imported_workspace_id
      || result.import?.workspace_id
      || previewWorkspaceId;
    $("#import-project-dialog").close("applied");
    state.importPreview = null;
    state.importSource = null;
    state.workspaceId = importedWorkspaceId || null;
    state.selectedClassId = null;
    state.connectionStart = null;
    state.suggestions = [];
    state.candidateResults = null;
    state.periodicityPreview = null;
    state.drawingPeriodicityPreview = null;
    state.view = { zoom: 1, panX: 0, panY: 0 };
    await loadProject();
    toast(isLegacy && importedWorkspaceId
      ? `Imported reviewed legacy canvas into ${workspace()?.name || importedWorkspaceId} on E${workspace()?.page || state.importSource?.targetPage}.`
      : `Imported reviewed project revision ${result.revision}.`);
  } catch (error) {
    $("#import-apply-status")?.remove();
    $("#import-project-summary").insertAdjacentHTML("beforeend", `<p class="import-error">Apply failed: ${escapeHtml(error.message)} Preview again before retrying if the project changed.</p>`);
    button.disabled = false;
    button.textContent = idleLabel;
    toast(error.message);
  }
}

function resetView() {
  fitViewToData();
}

function fitViewToData() {
  const ws = workspace();
  if (!ws) return;
  const nodes = liveClassesAt(ws).filter((item) => !item.archived);
  if (!nodes.length) {
    state.view = { zoom: 1, panX: 0, panY: 0 };
    renderChart();
    return;
  }
  const stems = nodes.map((item) => Number(item.grade.stem));
  const filtrations = nodes.map((item) => Number(item.grade.filtration));
  const stemMin = Math.min(...stems);
  const stemMax = Math.max(...stems);
  const filtrationMax = Math.max(0, ...filtrations);
  const { width, height } = dimensions();
  const baseCell = Number(ws.settings.rendering?.base_cell || 28);
  const horizontalZoom = (width - 76) / (Math.max(1, stemMax - stemMin + 3) * baseCell);
  const verticalZoom = (height - 64) / (Math.max(1, filtrationMax + 2) * baseCell);
  const zoom = clamp(Math.min(horizontalZoom, verticalZoom, 1.25), 0.18, 16);
  const cell = baseCell * zoom;
  state.view = {
    zoom,
    panX: -((stemMin + stemMax) / 2 + 0.5) * cell,
    panY: 0,
  };
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
  state.view.zoom = clamp(state.view.zoom * (event.deltaY < 0 ? 1.11 : 0.9), 0.18, 16);
  const after = pointFor(before);
  state.view.panX += x - after.x;
  state.view.panY += y - after.y;
  constrainView();
  scheduleChartRender();
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
  $("#legacy-catalog-reference").addEventListener("toggle", (event) => {
    if (event.currentTarget.open) void loadLegacyCatalogManifest().catch(error => toast(error.message));
  });
  $("#open-legacy-catalog").addEventListener("click", () => {
    void openLegacyCatalog().catch(error => toast(error.message));
  });
  $("#close-legacy-catalog").addEventListener("click", closeLegacyCatalog);
  $("#workspace-select").addEventListener("change", (event) => {
    state.workspaceId = event.target.value;
    state.selectedClassId = null;
    state.classFilter = "";
    $("#class-filter").value = "";
    state.suggestions = [];
    state.candidateResults = null;
    state.periodicityPreview = null;
    state.drawingPeriodicityPreview = null;
    state.view = { zoom: 1, panX: 0, panY: 0 };
    state.connectionStart = null;
    render();
  });
  $("#class-filter").addEventListener("input", (event) => {
    state.classFilter = event.target.value;
    renderClassList();
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
  $("#export-legacy-json").addEventListener("click", () => {
    window.location.assign(`/api/workspaces/${encodeURIComponent(state.workspaceId)}/legacy-export?page=${encodeURIComponent(workspace().page)}`);
  });
  $("#import-json").addEventListener("click", () => $("#import-json-file").click());
  $("#import-json-file").addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) previewProjectImport(file);
  });
  $("#apply-project-import").addEventListener("click", applyProjectImport);
  $("#cancel-project-import").addEventListener("click", () => {
    state.importPreview = null;
    state.importSource = null;
    $("#import-project-dialog").close("cancel");
  });
  $("#export-chart").addEventListener("click", () => downloadTex("chart"));
  $("#export-article").addEventListener("click", () => downloadTex("article"));
  $("#clear-current-canvas").addEventListener("click", clearCurrentCanvas);
  $("#undo-action").addEventListener("click", () => changeHistory("undo"));
  $("#redo-action").addEventListener("click", () => changeHistory("redo"));
  $("#comparison-select").addEventListener("change", showComparisonNote);
  document.querySelectorAll("[data-tool]").forEach((button) => button.addEventListener("click", () => setTool(button.dataset.tool)));
  $("#add-drawing-period-rule")?.addEventListener("click", addDrawingPeriodicityRule);
  $("#preview-drawing-period-box")?.addEventListener("click", () => previewDrawingPeriodicity("box"));
  $("#apply-drawing-period-box")?.addEventListener("click", () => applyDrawingPeriodicity("box"));
  $("#preview-drawing-diff-period")?.addEventListener("click", () => previewDrawingPeriodicity("differentials"));
  $("#apply-drawing-diff-period")?.addEventListener("click", () => applyDrawingPeriodicity("differentials"));
  [
    "#drawing-period-name", "#drawing-period-p", "#drawing-period-q",
    "#drawing-period-p-min", "#drawing-period-p-max", "#drawing-period-q-min", "#drawing-period-q-max",
    "#drawing-diff-period-p", "#drawing-diff-period-q",
  ].forEach((selector) => $(selector)?.addEventListener("input", () => {
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
    if (state.tool !== "class" || state.drag || event.target.closest?.("[data-readonly-representative]")) return;
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
    scheduleChartRender();
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
      const label = String(form.get("label") || "").trim();
      await api(`/api/workspaces/${state.workspaceId}/classes`, { method: "POST", body: JSON.stringify({ label, expression: label, glyph: form.get("glyph"), stem: Number(form.get("stem")), filtration: Number(form.get("filtration")), state: "unknown", page: workspace().page, representation: sector?.normal_form || {}, sector_id: sector?.id || null }) });
      $("#class-dialog").close();
      await loadProject();
      toast("Class added.");
    } catch (error) { toast(error.message); } finally { submit.disabled = false; }
  });
  $("#class-form [name=label]").addEventListener("input", renderClassLabelPreview);
  $("#cancel-class").addEventListener("click", () => $("#class-dialog").close("cancel"));
  $("#open-cell-editor").addEventListener("click", () => openCellDialog());
  $("#new-cell-from-panel").addEventListener("click", () => openCellDialog());
  $("#edit-selected-cell").addEventListener("click", () => state.selectedCellId ? openCellDialog(state.selectedCellId) : openCellDialog());
  $("#cell-select").addEventListener("change", (event) => {
    state.selectedCellId = event.target.value || null;
    state.lastVectorResult = null;
    renderCellInspector();
    renderChart();
  });
  $("#cell-form").addEventListener("submit", saveCell);
  $("#cancel-cell").addEventListener("click", () => $("#cell-dialog").close("cancel"));
  $("#archive-cell").addEventListener("click", async () => {
    const id = $("#cell-form").elements.cell_id.value;
    if (!id || !window.confirm("Archive this cell and all incident matrix records? Proof history will be retained.")) return;
    try {
      await api(`/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/cells/${encodeURIComponent(id)}`, { method: "DELETE" });
      $("#cell-dialog").close();
      state.selectedCellId = null;
      await loadProject();
      toast("Cell and incident matrix displays archived; history retained.");
    } catch (error) { $("#cell-form-result").textContent = error.message; }
  });
  $("#open-matrix-editor").addEventListener("click", () => openMatrixDialog());
  $("#matrix-form").addEventListener("submit", saveMatrix);
  $("#cancel-matrix").addEventListener("click", () => $("#matrix-dialog").close("cancel"));
  $("#archive-matrix").addEventListener("click", async () => {
    const id = $("#matrix-form").elements.map_id.value;
    if (!id || !window.confirm("Archive this matrix while retaining its proposition and provenance?")) return;
    try {
      await api(`/api/v2/workspaces/${encodeURIComponent(state.workspaceId)}/differential-maps/${encodeURIComponent(id)}`, { method: "DELETE" });
      $("#matrix-dialog").close();
      await loadProject();
      toast("Differential matrix archived; proposition retained.");
    } catch (error) { $("#matrix-form-result").textContent = error.message; }
  });
  $("#evaluate-cell-vector").addEventListener("click", evaluateCellVector);
  $("#pin-cell-vector").addEventListener("click", pinCellVector);
  $("#preview-cell-transition").addEventListener("click", previewCellTransition);
  $("#rename-form").addEventListener("submit", savePendingRename);
  $("#cancel-rename").addEventListener("click", () => {
    state.pendingRenameId = null;
    $("#rename-dialog").close("cancel");
  });
  $("#relation-form").addEventListener("submit", savePendingRelation);
  $("#cancel-relation").addEventListener("click", () => {
    state.pendingRelation = null;
    state.connectionStart = null;
    $("#relation-dialog").close("cancel");
    renderChart();
  });
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
  window.addEventListener("resize", () => { syncLayoutHeight(); constrainView(); scheduleChartRender(); });
}

function downloadTex(kind) {
  if (!state.workspaceId) return;
  const page = workspace().page;
  window.location.assign(`/api/v2/render/workspaces/${encodeURIComponent(state.workspaceId)}/${kind}.tex?page=${encodeURIComponent(page)}`);
}

if (PAGE_MODE === "reviewing") bindReviewEvents();
else bindEvents();
window.addEventListener("math-renderer-ready", hydrateMathLabels);

(PAGE_MODE === "reviewing" ? loadReviewPage() : loadProject()).catch((error) => {
  document.body.innerHTML = `<pre>Unable to load HFPSS Studio: ${escapeHtml(error.message)}</pre>`;
});
