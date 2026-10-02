/* A viewport export, not a dump of stored anchors. All page algebra and
 * periodic occurrences come from the same runtime that draws the chart.
 * Palette: REU Projects/Final Presentation/Figures/Drawing/
 * 2Sigma_corrected_E11above.tex, first chart. Layout follows SSdraw/texRender.py.
 */
(function (root) {
  "use strict";
  const palette = Object.freeze({1: "truemagenta", 2: "darkcyan", 3: "red", 4: "darkgreen",
    5: "darkgreen", 6: "orange", 7: "blue", 9: "violet", 11: "brown", 13: "truemagenta",
    17: "red!50!pink", 19: "teal!80!black", 21: "green!40!orange", 23: "orange"});
  const f4Latex = value => value === 2 ? "\\zeta" : value === 3 ? "\\zeta^{2}" : "";
  const integer = (value, name) => {
    if ((typeof value !== "number" && (typeof value !== "string" || !/^[+-]?\d+$/.test(value.trim())))
        || !Number.isSafeInteger(Number(value))) throw new Error(`${name} must be an integer.`);
    return Number(value);
  };
  function validateOptions(input) {
    const pageStart = integer(input.pageStart, "Starting page"), pageEnd = integer(input.pageEnd, "Ending page");
    if (pageStart <= 0 || pageEnd <= 0) throw new Error("Page numbers must be positive integers.");
    if (pageStart > pageEnd) throw new Error("Starting page must not exceed ending page.");
    const b = input.bounds || {};
    const bounds = Object.fromEntries(["stemMin", "stemMax", "filtrationMin", "filtrationMax"]
      .map(key => [key, integer(b[key], key)]));
    if (bounds.filtrationMin < 0) throw new Error("The lower filtration must be nonnegative.");
    if (bounds.stemMin > bounds.stemMax || bounds.filtrationMin > bounds.filtrationMax)
      throw new Error("Each view-range minimum must not exceed its maximum.");
    const cells = (bounds.stemMax - bounds.stemMin + 1) * (bounds.filtrationMax - bounds.filtrationMin + 1);
    if (!Number.isSafeInteger(cells) || cells > 250000)
      throw new Error("The export window exceeds 250,000 bidegrees. Choose a smaller view range.");
    return {pageStart, pageEnd, bounds, labels: Boolean(input.labels)};
  }
  const inBounds = (grade, b) => grade.stem >= b.stemMin && grade.stem <= b.stemMax
    && grade.filtration >= b.filtrationMin && grade.filtration <= b.filtrationMax;
  const finitePoint = p => p && Number.isFinite(p.x) && Number.isFinite(p.y);
  const number = n => String(Number(Number(n).toFixed(5)));
  const point = p => `(${number(p.x)},${number(p.y)})`;
  const provenance = (record, value) => `% HFPSS-STUDIO ${JSON.stringify({record, ...value})
    .replace(/[\u007f-\uffff]/g, char => `\\u${char.charCodeAt(0).toString(16).padStart(4, "0")}`)}`;

  /** Build geometry once at E_start. Later arrows are expressed in that same
   * basis, never on freshly packed E_r dots. No workspace/page is mutated. */
  function buildSnapshot(workspace, input, runtime) {
    const options = validateOptions(input), b = options.bounds;
    const pages = [...new Set([options.pageStart, ...(workspace.differentials || [])
      .map(d => d.page).filter(r => r >= options.pageStart && r <= options.pageEnd)])].sort((a, c) => a - c);
    const maxR = Math.max(3, ...pages.filter(r => (workspace.differentials || []).some(d => d.page === r)));
    const padded = {stemMin: b.stemMin - 4, stemMax: b.stemMax + 4,
      filtrationMin: Math.max(0, b.filtrationMin - maxR), filtrationMax: b.filtrationMax + maxR};
    // Fixed logical pixels make packing independent of the user's current zoom.
    const metrics = {cell: 40, axisX: 0, axisY: 0, width: 1200, height: 800};
    const toTex = p => ({x: p.x / metrics.cell - 0.5, y: -p.y / metrics.cell - 0.5});
    const base = {...workspace, page: options.pageStart};
    const algebra = runtime.pageAlgebra(base, padded);
    const baseOccurrences = runtime.periodicDifferentials(base, b, null, algebra);
    const presentation = root.HFPSSChartPresentation?.create(algebra, baseOccurrences, padded);
    const records = runtime.packedClassInstances(base, padded, metrics, [], presentation, algebra);
    const byId = new Map(workspace.classes.map(node => [node.id, node]));
    const slots = new Map(), instanceRecords = new Map(), patterns = new Map();
    const portPoint = (record, port = null) => runtime.coefficientPortPoint
      ? runtime.coefficientPortPoint(record, metrics, port) : runtime.packedPoint(record, metrics);
    for (const record of records) {
      const key = runtime.classInstanceKey(record.item.id, record.grade);
      instanceRecords.set(key, record);
      const p = portPoint(record);
      slots.set(key, p);
      const slot = runtime.e2DisplaySlot(record.item, record.grade);
      if (slot) slots.set(slot, p);
      if (slot) for (const port of record.modulePorts || [])
        slots.set(`${slot}:port:${port}`, portPoint(record, port));
      (record.algebraSlots || (presentation || algebra)?.displaySlots?.(record.item, record.grade) || [])
        .forEach((value, i) => slots.set(value, portPoint(record, record.modulePorts?.[i])));
    }
    for (const node of workspace.classes) {
      const pattern = node.style?.e2_pattern;
      if (!pattern || node.archived || node.style.two_valuation || node.style.j_order) continue;
      if (!patterns.has(pattern)) patterns.set(pattern, []);
      patterns.get(pattern).push(node);
    }
    const combinations = new Map();
    function endpoint(id, grade, effectiveNode, branch = {}) {
      const node = effectiveNode || byId.get(id);
      const display = presentation?.endpoint(node, grade, branch.two || 0, branch.j || 0);
      if (display?.live && display.entries.length === 1 && slots.has(display.entries[0].slot))
        return {...slots.get(display.entries[0].slot), basisEndpoint: display};
      if (display?.live && display.entries.length > 1) {
        if (!combinations.has(display.key)) {
          const center = runtime.pointFor(grade, metrics);
          const siblings = [...combinations.values()].filter(p => p.grade.stem === grade.stem
            && p.grade.filtration === grade.filtration).length;
          combinations.set(display.key, {x: center.x + metrics.cell * (0.18 - 0.12 * (siblings % 3)),
            y: center.y + metrics.cell * (0.3 - 0.14 * Math.floor(siblings / 3)), grade,
            label: runtime.quotientRepresentativeLabel(base, {grade, terms: display.terms}, patterns),
            basisEndpoint: display});
        }
        return combinations.get(display.key);
      }
      const port = `${Number(node?.style?.two_valuation || 0) + Number(branch.two || 0)}:${Number(node?.style?.j_order || 0) + Number(branch.j || 0) > 0 ? 1 : 0}`;
      const exactPort = slots.get(`${runtime.e2DisplaySlot(node, grade)}:port:${port}`);
      if (exactPort) return exactPort;
      const record = instanceRecords.get(runtime.classInstanceKey(id, grade));
      if (record) {
        return portPoint(record, port);
      }
      const vectorSlots = algebra?.endpointSlots?.(node, grade) || [];
      if (vectorSlots.length === 1 && slots.has(vectorSlots[0])) return slots.get(vectorSlots[0]);
      // Missing geometry outside the clipped region is harmless. A missing
      // in-view vector must not be disguised as the average of several dots.
      if (!inBounds(grade, b)) return runtime.pointFor(grade, metrics);
      const fallback = slots.get(runtime.e2DisplaySlot(node, grade));
      if (fallback && vectorSlots.length <= 1) return fallback;
      throw new Error(`No exact lower-page endpoint for ${node?.label || id} at (${grade.stem}, ${grade.filtration}). Export a shorter page range.`);
    }
    const nodes = records.filter(record => inBounds(record.grade, b)).map(record => {
      const center = runtime.packedPoint(record, metrics), tex = toTex(center);
      const glyphs = record.shape === "finite-two-tower"
        ? [...new Set((record.modulePorts || []).map(port => Number(port.split(":")[0])))].sort((a,c) => a-c)
          .map(two => ({...toTex(portPoint(record, `${two}:0`)), shape: "dot", two})) : undefined;
      return {id: record.instanceKey, ...tex, stem: record.grade.stem, filtration: record.grade.filtration,
        label: runtime.periodicDisplayLabel(record), shape: record.shape,
        ...(glyphs ? {glyphs} : {}), uncertain: Boolean(record.uncertain)};
    });
    const unit = p => p.basisEndpoint?.entries.length === 1 ? p.basisEndpoint.entries[0].coefficient : 1;
    const quotient = (target, source) => runtime.f4DisplayMultiply(target, runtime.f4DisplayMultiply(source, source));
    const relations = runtime.periodicRelations(base, new Set(runtime.liveClassesAt(base).map(n => n.id)), padded, algebra)
      .map(item => {
        const branch = algebra?.maps(item.source, item.target, item.sourceGrade, item.targetGrade)[0];
        const from = endpoint(item.source.id, item.sourceGrade, item.source, branch);
        const to = endpoint(item.target.id, item.targetGrade, item.target, branch);
        return {id: item.proposition.id, from: toTex(from), to: toTex(to),
          multiplier: item.proposition.conclusion?.chart_connection?.multiplier || "",
          coefficient: f4Latex(quotient(unit(to), unit(from)))};
      });
    const differentials = [];
    for (const page of pages) {
      const current = page === base.page ? base : {...workspace, page};
      const currentAlgebra = page === base.page ? algebra : runtime.pageAlgebra(current, padded);
      const occurrences = page === base.page ? baseOccurrences : runtime.periodicDifferentials(current, b, null, currentAlgebra);
      for (const item of runtime.differentialRenderGroups(current, occurrences, currentAlgebra)) {
        const branch = currentAlgebra?.maps(item.sourceNode, item.targetNode, item.sourceGrade, item.targetGrade)
          .find(value => root.HFPSSPageAlgebra?.allowsConstraintBranch(item.diff, value.two || 0, value.j || 0) ?? true);
        const from = endpoint(item.diff.source_id, item.sourceGrade, item.sourceNode, branch);
        const to = endpoint(item.diff.target_id, item.targetGrade, item.targetNode, branch);
        const scalar = currentAlgebra?.coefficientState(item.diff);
        const displayed = runtime.differentialDisplayCoefficient(current, item.diff, currentAlgebra);
        let coefficient = displayed?.value === 1 ? "" : displayed?.latex || "";
        const metadata = (current.propositions || []).find(p => p.id === item.diff.proposition_id)?.conclusion || {};
        const declared = metadata.coefficient_parameter || metadata.atlas_display_coefficient || item.diff.display_coefficient;
        if (!displayed && scalar?.component === undefined && metadata.coefficient_parameter?.target_component === undefined
            && declared && Object.keys(declared).length) coefficient = "?";
        if ((from.basisEndpoint?.adapted || to.basisEndpoint?.adapted) && scalar?.resolved) {
          const targetUnit = to.basisEndpoint ? unit(to) : scalar.component === undefined ? scalar.value : 1;
          coefficient = f4Latex(quotient(targetUnit, unit(from)));
        }
        differentials.push({id: item.diff.id, page, from: toTex(from), to: toTex(to), coefficient,
          source: item.sourceNode?.label, target: item.targetNode?.label,
          review: runtime.differentialVisualState(item.diff) !== "accepted",
          aliases: item.renderAliases?.map(alias => alias.id) || []});
      }
    }
    for (const [id, item] of combinations) if (inBounds(item.grade, b))
      nodes.push({id, ...toTex(item), stem: item.grade.stem, filtration: item.grade.filtration,
        label: item.label, shape: "combination", coordinates: item.basisEndpoint.coordinates});
    return {workspaceId: workspace.id, name: workspace.name, ...options, nodes, relations, differentials};
  }

  function render(snapshot) {
    const {pageStart, pageEnd, bounds: b, labels} = validateOptions(snapshot);
    const scale = Math.min(1, 36 / (b.stemMax - b.stemMin + 3), 24 / (b.filtrationMax - b.filtrationMin + 3));
    const styles = Object.entries(palette).map(([r, color]) => `d${r}/.style={draw={${color}},tower}`);
    const lines = ["% Generated by HFPSS Studio: viewport/range snapshot.",
      "% Dots and multiplication lines are from the lowest page; arrows include the requested inclusive page range.",
      "% Palette: REU Projects/Final Presentation/Figures/Drawing/2Sigma_corrected_E11above.tex (first chart).",
      "% d19 is absent from that template; the explicit additional color is teal!80!black.",
      provenance("export", {workspace: snapshot.workspaceId, pageStart, pageEnd, bounds: b}),
      "\\documentclass{amsart}", "\\usepackage{lmodern,tikz}", "\\usetikzlibrary{arrows.meta}",
      "\\usepackage[a3paper,landscape,margin=0.4cm]{geometry}", "\\pagestyle{empty}",
      "\\definecolor{chartgray}{gray}{0.5}", "\\definecolor{darkcyan}{rgb}{0,0.7,0.7}",
      "\\definecolor{darkgreen}{rgb}{0,0.65,0}", "\\definecolor{truemagenta}{rgb}{1,0,1}",
      "\\begin{document}", "\\vspace*{\\fill}", "\\begin{center}",
      `\\begin{tikzpicture}[scale=${number(scale)},>=stealth,very thin,`,
      "tower/.style={-{Stealth[length=2pt,width=2pt]}},",
      "multh1/.style={draw={chartgray}},multnu/.style={draw={chartgray}},multtwo/.style={draw={chartgray}},",
      "multx/.style={draw={blue},opacity=.2},multy/.style={draw={orange},opacity=.2},",
      "review differential/.style={dashed,opacity=.75},",
      "unclassified differential/.style={draw=black,tower},", styles.join(",\n"), "]",
      `\\draw[step=1cm,black!20,xshift=.5cm,yshift=.5cm] (${b.stemMin-1},${b.filtrationMin-1}) grid (${b.stemMax},${b.filtrationMax});`,
      `\\node[anchor=south] at (${number((b.stemMin+b.stemMax)/2)},${number(b.filtrationMax+0.75)}) {$E_{${pageStart}}${pageStart === pageEnd ? "" : `\\text{ with }d_{${pageStart}},\\ldots,d_{${pageEnd}}`}$};`];
    const step = Math.max(1, Math.ceil(1 / scale));
    for (let x = b.stemMin; x <= b.stemMax; x += step)
      lines.push(`\\node[scale=.65] at (${x},${number(b.filtrationMin-0.8)}) {${x}};`);
    for (let y = b.filtrationMin; y <= b.filtrationMax; y += step)
      lines.push(`\\node[scale=.65] at (${number(b.stemMin-0.8)},${y}) {${y}};`);
    lines.push("\\begin{scope}", `\\clip (${number(b.stemMin-0.48)},${number(b.filtrationMin-0.48)}) rectangle (${number(b.stemMax+0.48)},${number(b.filtrationMax+0.48)});`);
    const drawLine = (item, style, kind) => {
      if (!finitePoint(item.from) || !finitePoint(item.to)) throw new Error(`Invalid ${kind} endpoint.`);
      lines.push(provenance(kind, item));
      const coefficient = item.coefficient && item.coefficient !== "1"
        ? ` node[midway,fill=white,inner sep=1pt,scale=.6] {$${item.coefficient}$}` : "";
      lines.push(`\\draw[${style}] ${point(item.from)} --${coefficient} ${point(item.to)};`);
    };
    for (const item of snapshot.relations || []) {
      const multiplier = String(item.multiplier || "").replace(/[_{}\\]/g, "");
      const style = multiplier === "h2" ? "multnu" : multiplier === "2" ? "multtwo"
        : multiplier === "x" ? "multx" : multiplier === "y" ? "multy" : "multh1";
      drawLine(item, style, "relation");
    }
    for (const item of snapshot.differentials || []) {
      const r = integer(item.page, "Differential page");
      if (r < pageStart || r > pageEnd) continue;
      drawLine(item, `${palette[r] ? `d${r}` : "unclassified differential"}${item.review ? ",review differential" : ""}`, "differential");
    }
    function glyph(node) {
      const at = point(node), gray = node.uncertain ? "orange!80!black" : "chartgray";
      if (node.shape === "combination") return `\\node[inner sep=0,scale=.6,text=${gray}] at ${at} {$\\Sigma$};`;
      if (node.shape === "unknown") return `\\draw[${gray},fill=white] (${number(node.x)},${number(node.y+.085)}) -- (${number(node.x+.085)},${number(node.y)}) -- (${number(node.x)},${number(node.y-.085)}) -- (${number(node.x-.085)},${number(node.y)}) -- cycle;`;
      if (node.shape === "square" || node.shape === "witt-j-series") {
        const outer = `\\draw[${gray},fill=white] (${number(node.x-.10)},${number(node.y-.10)}) rectangle (${number(node.x+.10)},${number(node.y+.10)});`;
        return outer + (node.shape === "witt-j-series"
          ? `\n\\draw[${gray}] (${number(node.x-.055)},${number(node.y-.055)}) rectangle (${number(node.x+.055)},${number(node.y+.055)});` : "");
      }
      if (["circle", "j-series", "j-positive-series"].includes(node.shape)) {
        const outer = `\\draw[${gray},fill=white] ${at} circle[radius=.105];`;
        return outer + (node.shape === "j-series" ? `\n\\fill[${gray}] ${at} circle[radius=.035];`
          : node.shape === "j-positive-series" ? `\n\\draw[${gray}] ${at} circle[radius=.04];` : "");
      }
      return `\\fill[${gray}] ${at} circle[radius=.055];`;
    }
    for (const node of snapshot.nodes || []) {
      if (!finitePoint(node)) throw new Error("Invalid class coordinate.");
      if (!inBounds({stem: node.stem ?? node.x, filtration: node.filtration ?? node.y}, b)) continue;
      lines.push(provenance("class", node));
      if (node.glyphs?.length) {
        const items = node.glyphs;
        if (items.some(item => !finitePoint(item))) throw new Error("Invalid coefficient-port coordinate.");
        lines.push(`\\draw[multtwo] ${point(items[0])} -- ${point(items[items.length-1])};`);
        for (const item of items) lines.push(glyph({...node, ...item}));
      } else lines.push(glyph(node));
      const labelPoint = node.glyphs?.[0] || node;
      if ((labels || node.showLabel) && node.label)
        lines.push(`\\node[anchor=south west,scale=.5,inner sep=1pt] at (${number(labelPoint.x+.08)},${number(labelPoint.y+.08)}) {$${node.label}$};`);
    }
    lines.push("\\end{scope}", "\\end{tikzpicture}", "\\end{center}", "\\vspace*{\\fill}", "\\end{document}", "");
    return lines.join("\n");
  }
  function download(snapshot) {
    const content = render(snapshot);
    const blob = new Blob([content], {type: "application/x-tex;charset=utf-8"});
    const url = URL.createObjectURL(blob), link = document.createElement("a");
    link.href = url;
    link.download = `${String(snapshot.workspaceId || "chart").replace(/[^\w-]/g, "_")}-E${snapshot.pageStart}-${snapshot.pageEnd}.tex`;
    document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    return content;
  }
  function requestOptions(defaults) {
    return new Promise(resolve => {
      const dialog = document.createElement("dialog");
      dialog.className = "tex-export-dialog";
      dialog.innerHTML = `<form><h2>Export chart to LaTeX</h2><p>Dots and relations use the starting page. All differentials in the inclusive page range are included.</p>
        <fieldset><legend>Page range</legend><label>Starting page<input name="pageStart" type="number" min="1" step="1" required></label><label>Ending page<input name="pageEnd" type="number" min="1" step="1" required></label></fieldset>
        <fieldset><legend>View range (inclusive)</legend><label>Stem low<input name="stemMin" type="number" step="1" required></label><label>Stem high<input name="stemMax" type="number" step="1" required></label><label>Filtration low<input name="filtrationMin" type="number" min="0" step="1" required></label><label>Filtration high<input name="filtrationMax" type="number" min="0" step="1" required></label></fieldset>
        <label><input name="labels" type="checkbox"> Print element labels (may overlap in dense charts)</label><p class="tex-export-error" role="alert"></p><div class="dialog-actions"><button type="button" data-cancel>Cancel</button><button type="submit">Download TeX</button></div></form>`;
      const form = dialog.querySelector("form");
      for (const key of ["pageStart", "pageEnd"]) form.elements[key].value = defaults[key];
      for (const key of ["stemMin", "stemMax", "filtrationMin", "filtrationMax"]) form.elements[key].value = defaults.bounds[key];
      let settled = false;
      const finish = value => { if (settled) return; settled = true; dialog.close(); dialog.remove(); resolve(value); };
      dialog.addEventListener("cancel", event => { event.preventDefault(); finish(null); });
      dialog.querySelector("[data-cancel]").addEventListener("click", () => finish(null));
      form.addEventListener("submit", event => {
        event.preventDefault();
        try {
          finish(validateOptions({pageStart: form.elements.pageStart.value, pageEnd: form.elements.pageEnd.value,
            bounds: Object.fromEntries(["stemMin", "stemMax", "filtrationMin", "filtrationMax"].map(key => [key, form.elements[key].value])),
            labels: form.elements.labels.checked}));
        } catch (error) { dialog.querySelector(".tex-export-error").textContent = error.message; }
      });
      document.body.appendChild(dialog); dialog.showModal();
    });
  }
  const api = {palette, validateOptions, buildSnapshot, render, download, requestOptions};
  root.HFPSSChartTex = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
