(function exposeWorkspaceNavigation(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.HFPSSWorkspaceNavigation = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createWorkspaceNavigation() {
  "use strict";

  const MAIN_FAMILIES = ["q8-hfpss", "c4-hfpss", "q8-2-bss"];
  const LABELS = {"q8-hfpss": "Q8 HFPSS", "c4-hfpss": "C4 HFPSS", "q8-2-bss": "Q8 2-BSS"};
  const INTEGER_IDS = {"q8-hfpss": "ws_integer", "c4-hfpss": "ws_c4_bbhs_integer", "q8-2-bss": "ws_q8_bss_integer"};
  const escape = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");

  function familyId(workspace) {
    if (!workspace) return null;
    const group = String(workspace.group || "Other"), sequence = String(workspace.spectral_sequence || "unspecified").toLowerCase();
    if (group === "Q8" && sequence === "hfpss") return "q8-hfpss";
    if (group === "C4" && sequence === "hfpss") return "c4-hfpss";
    if (group === "Q8" && sequence === "2-bss") return "q8-2-bss";
    return `family:${encodeURIComponent(group)}:${encodeURIComponent(sequence)}`;
  }

  function defaultWorkspaceId(project, id) {
    const members = (project?.workspaces || []).filter(item => familyId(item) === id);
    const integerSector = id === "q8-hfpss" && (project?.grading_sectors || [])
      .find(sector => Number(sector.a) === 0 && Number(sector.b) === 0)?.workspace_id;
    return members.find(item => item.id === INTEGER_IDS[id])?.id
      || members.find(item => item.id === integerSector)?.id
      || members.find(item => /^(integer(?:[- ]graded)?|\*)$/i.test(item.grading_label || ""))?.id
      || members[0]?.id || null;
  }

  function families(project) {
    const grouped = new Map();
    for (const item of project?.workspaces || []) {
      const id = familyId(item);
      if (!grouped.has(id)) grouped.set(id, {id, label: LABELS[id] || `${item.group || "Other"} ${String(item.spectral_sequence || "sequence").toUpperCase()}`, workspaceIds: []});
      grouped.get(id).workspaceIds.push(item.id);
    }
    const order = id => MAIN_FAMILIES.includes(id) ? MAIN_FAMILIES.indexOf(id) : MAIN_FAMILIES.length;
    return [...grouped.values()].sort((left, right) => order(left.id) - order(right.id))
      .map(item => ({...item, defaultWorkspaceId: defaultWorkspaceId(project, item.id)}));
  }

  function renderSelector(selector, project, workspace) {
    const choices = families(project);
    selector.innerHTML = choices.map(item => `<option value="${escape(item.id)}">${escape(item.label)}</option>`).join("");
    selector.value = familyId(workspace) || choices[0]?.id || "";
    selector.disabled = !choices.length;
    return choices;
  }

  function workspaceEntry(item, active, label, detail) {
    return {kind: "workspace", workspaceId: item.id, label: label || item.name || item.id,
      detail: detail || item.grading_label || "stored workspace", active: item.id === active,
      ariaLabel: `${label || item.name || item.id}: ${item.name || item.id}`, disabled: false};
  }

  function atlas(project, workspace) {
    const id = familyId(workspace), members = (project?.workspaces || []).filter(item => familyId(item) === id);
    const active = workspace?.id;
    const model = {familyId: id, eyebrow: "GRADING SLICES", title: "Stored workspaces", summary: "", entries: [], additionalEntries: []};
    if (id === "q8-hfpss") {
      model.eyebrow = "RO(Q8) ATLAS";
      model.entries = (project?.grading_sectors || []).map(sector => {
        const target = members.find(item => item.id === sector.workspace_id), transport = target?.settings?.atlas_transport;
        const independent = target?.settings?.atlas_representative === true && !transport;
        const count = sector.class_ids?.length || 0;
        const detail = transport ? `${transport.action || "transport"} · ${Number(transport.stem_shift) >= 0 ? "+" : ""}${Number(transport.stem_shift) || 0}`
          : count ? `${count} anchors` : "not computed";
        return {kind: "sector", workspaceId: sector.workspace_id, sectorId: sector.id, a: sector.a, b: sector.b,
          label: `S(${sector.a},${sector.b})`, detail, status: sector.status, independent, active: active === sector.workspace_id,
          ariaLabel: `${sector.display_label || `Q8 sector ${sector.a}, ${sector.b}`} · ${detail}${independent ? " · Independently computed representative (not a proof-status assertion)" : ""}`, disabled: !target};
      });
      model.title = `${model.entries.length} stored representatives`;
      model.summary = `Tinted tiles: ${model.entries.filter(entry => entry.independent).length} independently computed representatives. Blue outline: selected sector. Independent marks the computation origin, not proof status.`;
    } else if (id === "c4-hfpss") {
      model.eyebrow = "RO(C4) ATLAS";
      for (const [workspaceId, label, detail] of [["ws_c4_bbhs_integer", "*", "integer slice"],
        ["ws_c4_bbhs_1_minus_sigma", "* + 1 − σ", "1 − σ slice"]]) {
        const item = members.find(member => member.id === workspaceId);
        if (item) model.entries.push(workspaceEntry(item, active, label, detail));
      }
      model.title = `${model.entries.length} independent slices`;
      model.summary = "Permanent Δ₁⁴ gives 32-stem periodicity within each slice. Certified RO(C4) reduction chooses a slice and an integer shift; it does not identify the two slices.";
      model.reduction = {integerPeriod: 32, quotient: "Z/32{1} ⊕ Z/2{7+σ}", slices: ["integer", "1-sigma"],
        source: "BBHS RO(C4) periodicity lattice", independentSlices: true,
        warning: "1−σ is not the order-two generator: 2(1−σ)=16 modulo periods."};
    } else if (id === "q8-2-bss") {
      model.eyebrow = "Q8 2-BSS SLICES";
      for (const [workspaceId, label, detail] of [["ws_q8_bss_integer", "*", "integer slice"],
        ["ws_q8_bss_sigma", "* − σᵢ", "σᵢ slice"]]) {
        const item = members.find(member => member.id === workspaceId);
        if (item) model.entries.push(workspaceEntry(item, active, label, detail));
      }
      model.title = `${model.entries.length} computed slices`;
      model.summary = "Integer and σᵢ slices of the 2-BSS. Group-cohomology s and Bockstein p are separate gradings; the vertical-coordinate control selects the projection. These are not HFPSS pages.";
    }
    if (!model.entries.length) {
      model.entries = members.map(item => workspaceEntry(item, active));
      model.title = `${model.entries.length} stored workspaces`;
    }
    const listed = new Set(model.entries.map(item => item.workspaceId));
    model.additionalEntries = members.filter(item => !listed.has(item.id)).map(item => workspaceEntry(item, active));
    return model;
  }

  function atlasMarkup(model, additionalOpen = false) {
    const button = (entry, index) => `<button type="button" class="atlas-cell ${entry.active ? "active" : ""} ${entry.independent ? "independent-representative" : ""}" data-navigation-index="${index}" data-atlas-workspace="${escape(entry.workspaceId)}"${entry.sectorId ? ` data-sector="${escape(entry.sectorId)}"` : ""} aria-pressed="${Boolean(entry.active)}" aria-label="${escape(entry.ariaLabel)}" title="${escape(entry.ariaLabel)}"${entry.disabled ? " disabled" : ""}><strong>${entry.kind === "sector" ? `S<sub>${escape(entry.a)},${escape(entry.b)}</sub>` : escape(entry.label)}</strong><span>${escape(entry.detail)}</span>${entry.independent ? '<small class="atlas-origin-badge">Independent</small>' : ""}</button>`;
    return model.entries.map(button).join("") + (model.additionalEntries.length
      ? `<details class="atlas-additional"${additionalOpen || model.additionalEntries.some(item => item.active) ? " open" : ""}><summary>Other stored workspaces (${model.additionalEntries.length})</summary><div class="atlas-additional-list">${model.additionalEntries.map((entry, index) => button(entry, index + model.entries.length)).join("")}</div></details>` : "");
  }

  function renderAtlas(root, model, onSelect) {
    const wasOpen = Boolean(root.querySelector(".atlas-additional")?.open);
    root.dataset.familyId = model.familyId || "";
    root.setAttribute("aria-label", `${model.eyebrow}: ${model.title}`);
    root.innerHTML = atlasMarkup(model, wasOpen);
    const entries = [...model.entries, ...model.additionalEntries];
    root.querySelectorAll("[data-navigation-index]").forEach(button => {
      button.addEventListener("click", () => onSelect(entries[Number(button.dataset.navigationIndex)]));
    });
  }

  return {familyId, families, defaultWorkspaceId, renderSelector, atlas, atlasMarkup, renderAtlas};
});
