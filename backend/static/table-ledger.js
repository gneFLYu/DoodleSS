/* Read-only differential inventory, retaining published-table provenance. */
(function (root) {
  "use strict";

  const escape = value => String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);

  const bidegree = node => Number.isInteger(node?.grade?.stem) && Number.isInteger(node?.grade?.filtration)
    ? {stem: node.grade.stem, filtration: node.grade.filtration} : null;
  const degreeText = grade => grade ? `(${grade.stem}, ${grade.filtration})` : "Not recorded";

  function formulaMarkup(value) {
    const text = String(value ?? "");
    // The trusted KaTeX renderer rejects HTML/URL commands with trust:false.
    // Loading or parsing failure must still leave a readable, escaped label.
    if (typeof root.katex?.renderToString === "function") {
      try {
        return root.katex.renderToString(text, {throwOnError: false, trust: false, displayMode: false});
      } catch (_) { /* fall back to escaped source text */ }
    }
    return escape(text);
  }

  function rowsForWorkspace(workspace) {
    const classes = new Map((workspace?.classes || []).map(node => [node.id, node]));
    const propositions = new Map((workspace?.propositions || []).map(claim => [claim.id, claim]));
    const rows = [];
    for (const differential of workspace?.differentials || []) {
      const claim = propositions.get(differential.proposition_id);
      const metadata = claim?.conclusion || {};
      const transport = metadata.atlas_transport && typeof metadata.atlas_transport === "object"
        ? metadata.atlas_transport : null;
      const shift = Number.isInteger(transport?.stem_shift) ? transport.stem_shift : null;
      const transportProvenance = transport
        ? `${transport.action || "Recorded atlas action"}; stem shift ${shift === null ? "not recorded" : (shift >= 0 ? "+" : "") + shift}; from ${transport.source_workspace_id || "source workspace not recorded"}`
        : "";
      const hasPrintedRow = metadata.table_number != null && metadata.table_row != null;
      const tableNumber = Number(hasPrintedRow ? metadata.table_number : metadata.origin_table);
      const rowNumber = Number(hasPrintedRow ? metadata.table_row : metadata.origin_row);
      const tableRecord = [8, 9].includes(tableNumber) && Number.isInteger(rowNumber) && rowNumber > 0;
      const table = tableRecord ? tableNumber : null;
      const row = tableRecord ? rowNumber : null;
      const original = tableRecord && hasPrintedRow;
      const kind = tableRecord ? (original ? "published" : "derived")
        : /^FN-/.test(metadata.fact_id || "") ? "formal"
        : /^DER-/.test(metadata.fact_id || "") || metadata.evidence_kind ? "derived"
        : !claim || /manual/i.test(claim.rule || "") ? "manual" : "other";
      // Distinct records may cite the same printed row. List all of them;
      // the numeric disclosure count must equal the number of displayed rows.
      const key = `${tableRecord ? `table-${table}-row-${row}` : kind}-${differential.id || rows.length}-${rows.length}`;
      const source = classes.get(differential.source_id);
      const target = classes.get(differential.target_id);
      rows.push({
        key, table, row, original, tableRecord, kind,
        differentialId: String(differential.id || key),
        page: Number(differential.page),
        source: source?.label || differential.source_id || "Missing source",
        target: target?.label || differential.target_id || "Missing target",
        sourceBidegree: bidegree(source),
        targetBidegree: bidegree(target),
        printedProof: original ? String(metadata.printed_proof || "") : "",
        transported: Boolean(transport),
        transportProvenance,
        periodStem: Number(metadata.period_stem || differential.period_stem || 0),
        evidence: original ? (transport ? "Transported table row" : "Published table row")
          : (claim?.rule || (tableRecord ? "Derived from table row" : kind === "manual" ? "Manual differential" : "Recorded differential")),
        factId: metadata.fact_id || "",
        coefficient: coefficientDisplay(metadata, differential),
        sourceRef: claim?.source_ref || claim?.source_refs?.join("; ") || "Source locator not recorded",
        status: differential.status || claim?.status || "unrecorded",
        current: Number(differential.page) === Number(workspace?.page),
      });
    }
    return rows.sort((left, right) => Number(right.tableRecord) - Number(left.tableRecord)
      || (left.table || 0) - (right.table || 0)
      || Number(right.original) - Number(left.original)
      || left.row - right.row || left.page - right.page
      || left.differentialId.localeCompare(right.differentialId));
  }

  const fieldTex = value => Number.isInteger(value) && value >= 0 && value <= 3
    ? ["0", "1", "\\zeta", "\\zeta^2"][value] : String(value ?? "");

  function coefficientDisplay(metadata, differential) {
    const display = metadata.atlas_display_coefficient
      || (differential.display_coefficient && Object.keys(differential.display_coefficient).length
        ? differential.display_coefficient : null);
    const parameter = display?.transported_parameter || metadata.coefficient_parameter;
    if (display && typeof display === "object") {
      const resolved = display.resolved !== false && display.value !== null && display.value !== undefined;
      return {
        status: resolved ? "resolved" : "unresolved",
        expression: resolved ? fieldTex(display.value)
          : String(display.symbolic || display.expression || parameter?.expression || parameter?.symbol || parameter?.id || "unresolved"),
        basis: parameter?.target_component
          ? `Relative coefficient on ${parameter.target_component} only; normalized scalar not assigned`
          : "Normalized basis coefficient",
        details: [display.source_unit != null ? `source unit ${fieldTex(display.source_unit)}` : "",
          display.target_unit != null ? `target unit ${fieldTex(display.target_unit)}` : "",
          display.basis_ratio != null ? `basis ratio ${fieldTex(display.basis_ratio)}` : "",
          display.reason ? String(display.reason) : "",
          display.formula ? String(display.formula) : "",
          parameter?.source_parameter ? `linked source: ${parameter.source_parameter.workspace_id || ""} / ${parameter.source_parameter.parameter_id || ""}` : "",
          parameter?.target_component ? `relative coefficient on ${parameter.target_component} only` : ""].filter(Boolean),
      };
    }
    if (parameter && typeof parameter === "object") {
      const raw = parameter.value;
      const fixed = Number.isInteger(raw) && raw >= 0 && raw <= 3
        && (!Array.isArray(parameter.domain) || parameter.domain.includes(raw))
        && [0, 1].includes(parameter.frobenius_power || 0) && !parameter.source_parameter
        && parameter.inverse_parameter_id == null && parameter.affine_offset == null;
      const value = fixed && parameter.frobenius_power === 1 && Number.isInteger(raw) ? [0, 1, 3, 2][raw] : raw;
      return {
        status: fixed ? "resolved" : "unresolved",
        expression: fixed ? fieldTex(value) : String(parameter.expression || parameter.symbol || parameter.id || "unresolved")
          + (parameter.frobenius_power === 1 ? " (Frobenius)" : ""),
        basis: parameter.target_component ? `Relative coefficient on ${parameter.target_component} only` : "Recorded basis coefficient",
        details: [parameter.id ? `parameter ${parameter.id}` : "",
          parameter.source_parameter ? `linked source: ${parameter.source_parameter.workspace_id || ""} / ${parameter.source_parameter.parameter_id || ""}` : "",
          metadata.coefficient_condition ? `conditional: ${metadata.coefficient_condition.parameter_id} = ${metadata.coefficient_condition.equals} in source field` : ""].filter(Boolean),
      };
    }
    return {status: "unrecorded", expression: "", basis: "Not separately recorded", details: []};
  }

  function coefficientMarkup(coefficient) {
    if (coefficient.status === "unrecorded") return escape(coefficient.basis);
    return `<span class="table-ledger-formula">${formulaMarkup(coefficient.expression)}</span><small>${escape(coefficient.basis)}${coefficient.status === "unresolved" ? " · unresolved; no implicit unit-1 assignment" : ""}</small>`
      + coefficient.details.map(detail => `<small>${escape(detail)}</small>`).join("");
  }

  function rowMarkup(row) {
    return `<tr${row.tableRecord ? ` data-table="${row.table}" data-table-row="${row.row}"` : ""} data-evidence-kind="${row.kind}" data-differential-id="${escape(row.differentialId)}"${row.current ? ' class="is-current-page"' : ""}>
      <th scope="row">${row.tableRecord ? `${row.original ? "Row" : "From row"} ${row.row}` : escape(row.factId || row.differentialId || "Recorded differential")}</th>
      <td><span class="table-ledger-formula">${formulaMarkup(row.source)}</span><span aria-hidden="true"> → </span><span class="table-ledger-formula">${formulaMarkup(row.target)}</span></td>
      <td>${degreeText(row.sourceBidegree)}</td>
      <td>${degreeText(row.targetBidegree)}</td>
      <td>d<sub>${row.page}</sub>${row.current ? '<span class="table-ledger-current"> current</span>' : ""}</td>
      <td>${coefficientMarkup(row.coefficient)}</td>
      <td>${row.periodStem || "—"}</td>
      <td>${escape(row.evidence)}<small>${escape(row.status)}</small>${row.transportProvenance ? `<small class="table-ledger-transport">${escape(row.transportProvenance)}</small>` : ""}</td>
      <td>${escape(row.printedProof || (row.original ? "Not recorded" : "Not a printed row"))}</td>
      <td>${escape(row.sourceRef)}</td>
    </tr>`;
  }

  function tableMarkup(rows, table, original) {
    const selected = rows.filter(row => row.table === table && row.original === original);
    if (!selected.length) return "";
    const label = original ? "published rows" : "derived families";
    return `<div class="table-ledger-scroll" role="region" aria-label="Table ${table} ${label}" tabindex="0">
      <table class="table-ledger-table">
        <caption>Table ${table} · ${selected.length} ${label}</caption>
        ${tableHeader()}
        <tbody>${selected.map(rowMarkup).join("")}</tbody>
      </table>
    </div>`;
  }

  function tableHeader() {
    return '<thead><tr><th scope="col">Source row / record</th><th scope="col">Source → target</th><th scope="col">Source (s, f)</th><th scope="col">Target (s, f)</th><th scope="col">Differential</th><th scope="col">Coefficient</th><th scope="col">Derived repeat (stem)</th><th scope="col">Evidence kind / status</th><th scope="col">Printed proof</th><th scope="col">Source reference</th></tr></thead>';
  }

  function otherRecordsMarkup(rows) {
    const selected = rows.filter(row => !row.tableRecord);
    if (!selected.length) return "";
    return `<div class="table-ledger-scroll" role="region" aria-label="Formal, derived and manual differential records" tabindex="0"><table class="table-ledger-table"><caption>Formal, other derived and manual records · ${selected.length}</caption>${tableHeader()}<tbody>${selected.map(rowMarkup).join("")}</tbody></table></div>`;
  }

  function markup(workspace) {
    const rows = rowsForWorkspace(workspace);
    const published = rows.filter(row => row.original).length;
    const derived = rows.filter(row => row.tableRecord && !row.original).length;
    const other = rows.filter(row => !row.tableRecord).length;
    if (!rows.length) return {
      count: 0,
      summary: "No differential records in this workspace",
      html: '<p class="hint">This workspace has no recorded differentials.</p>',
    };
    const current = rows.filter(row => row.current).length;
    return {
      count: rows.length,
      summary: `${published} published · ${derived} derived${other ? ` · ${other} other records` : ""}`,
      html: `<p class="hint">All recorded pages; ${current} ${current === 1 ? "family" : "families"} on E${escape(workspace.page)}. Original table rows and their derived families are counted separately.</p>`
        + [8, 9].map(table => tableMarkup(rows, table, true) + tableMarkup(rows, table, false)).join("")
        + otherRecordsMarkup(rows)
        + '<p class="hint table-ledger-period-note">Derived repeat (stem) is application metadata, not a printed table column. Below 64, it denotes an up-to-unit repeated differential pattern, not an invertible permanent cycle. D⁸ gives the permanent 64-stem translation.</p>',
    };
  }

  function renderPublishedTableLedger(workspace, mount) {
    const disclosure = mount || root.document?.getElementById("published-table-ledger");
    if (!disclosure) return;
    const content = disclosure.querySelector("[data-table-ledger-content]");
    const count = disclosure.querySelector("[data-table-ledger-count]");
    const total = disclosure.querySelector("#shown-differential-count");
    const result = markup(workspace);
    if (count) count.textContent = result.summary;
    if (total) total.textContent = String(result.count);
    if (content) content.innerHTML = result.html;
    // Updating only the contents preserves the user's disclosure open state.
  }

  function claimAuditMarkup(claim) {
    const metadata = claim?.conclusion || {};
    const blockers = Array.isArray(metadata.source_blockers) ? metadata.source_blockers : [];
    const conflicts = Array.isArray(metadata.source_conflicts) ? metadata.source_conflicts : [];
    const issues = blockers.map(value => `<li>${escape(value)}</li>`);
    if (metadata.source_status === "withdrawn-proof") {
      issues.unshift(`<li><strong>Withdrawn proof — not an accepted differential</strong><small>${escape(metadata.authority_decision)}</small><small>${escape((metadata.source_artifacts || []).join("; "))}</small></li>`);
    }
    if (metadata.coefficient_normalization) {
      const normalization = metadata.coefficient_normalization;
      issues.push(`<li>Galois-fixed F4 normalization: nonzero coefficient = 1<small>${escape(normalization.basis)}; ${escape(normalization.source_ref)}</small><small>Preserves Witt factors 2, 4, … . Fixing a coefficient does not establish the differential or its source survival.</small></li>`);
    }
    if (metadata.verification_certificate) {
      const certificate = metadata.verification_certificate;
      issues.push(`<li>Verified derivation: ${escape(certificate.method)}<small>${escape(certificate.derivation)}</small><small>${escape(certificate.scope)}</small><small>${escape((certificate.source_refs || []).join("; "))}</small></li>`);
    }
    if (metadata.d3_product_certificate) {
      const certificate = metadata.d3_product_certificate;
      issues.push(`<li>Verified pure-sector d3 products<small>${escape(certificate.derivation)}</small><small>${escape(certificate.scope)}</small><small>${escape((certificate.source_refs || []).join("; "))}</small></li>`);
    }
    if (metadata.cycle_constraint === "outgoing-only") {
      issues.push('<li>Cycle certificate: zero outgoing differentials<small>This is not immunity to incoming differentials. Forward periodic multiples may still be hit; a negative-source Tate boundary does not delete an HFPSS class.</small></li>');
      if (metadata.derivation) issues.push(`<li>Derivation<small>${escape(metadata.derivation)}</small></li>`);
      const product = metadata.product_certificate;
      if (product) issues.push(`<li>Actual E2 product certificate<small>${escape(product.euler_cube)}</small><small>${escape(product.hidden_product)}</small><small>${escape(product.source_ref)}</small></li>`);
      const comparison = metadata.comparison_certificate;
      if (comparison) issues.push(`<li>Tate comparison certificate<small>${escape(comparison.comparison_range)}</small><small>${escape(comparison.interpretation)}</small><small>Tate zero by E${escape(comparison.tate_zero_by_page)}; possible earlier pages: ${escape((comparison.possible_pages || []).join(", "))}. No specific incoming differential is asserted.</small></li>`);
    }
    for (const conflict of conflicts) {
      if (!conflict || typeof conflict !== "object") continue;
      const fields = [conflict.source_ref, conflict.authority, conflict.checked_identity,
        conflict.conditional_family, conflict.conditional_correction, conflict.unit_parameter].filter(Boolean);
      issues.push(`<li><strong>Source conflict</strong>${fields.map(value => `<small>${escape(value)}</small>`).join("")}</li>`);
    }
    if (metadata.coefficient_constraint) issues.push(`<li>Coefficient constraint: ${escape(metadata.coefficient_constraint)}</li>`);
    for (const constraint of metadata.coefficient_constraints || []) {
      issues.push(`<li>Leibniz compatibility: ${escape((constraint.parameter_ids || []).join(' = '))}<small>${escape(constraint.scope)}</small><small>${escape(constraint.derivation)}</small><small>${escape(constraint.source_ref)}</small></li>`);
      if (constraint.normalization_value !== undefined) issues.push(`<li>Integer-table normalization: ${escape(constraint.normalization_value)}<small>${escape(constraint.normalization_source)}</small></li>`);
    }
    if (metadata.coefficient_transport_error) issues.push(`<li>Coefficient transport error: ${escape(metadata.coefficient_transport_error)}</li>`);
    if (metadata.coefficient_condition) {
      const condition = metadata.coefficient_condition;
      issues.push(`<li>Conditional Euler image: ${escape(condition.parameter_id)} = ${escape(condition.equals)} in the source field<small>The nonzero branch needs its own resolved unit. Otherwise the image is zero in the page quotient; no arrow or class death follows from this row.</small><small>${escape(condition.derivation)}</small><small>${escape(condition.source_ref)}</small></li>`);
    }
    if (metadata.related_period_table) {
      const table = metadata.related_period_table;
      issues.push(`<li>Related historical table: printed ${escape(table.column)} column<small>${escape(table.source_ref)}</small><small>${escape(table.interpretation)}</small><small>${escape(table.authority)}</small></li>`);
    }
    if (metadata.premise_transport_certificate) {
      const certificate = metadata.premise_transport_certificate;
      issues.push(`<li>Premise transport: ${escape(certificate.premise)}<small>${escape(certificate.derivation)}</small><small>${escape(certificate.source_ref)}</small></li>`);
    }
    if (metadata.coefficient_parameter) {
      const parameter = metadata.coefficient_parameter;
      if (parameter.value !== null && parameter.value !== undefined && !parameter.source_parameter) {
        const sourceValue = Number(parameter.value);
        const displayValue = parameter.frobenius_power === 1 ? [0, 1, 3, 2][sourceValue] : sourceValue;
        const scalar = ["0", "1", "ζ", "ζ²"][displayValue] ?? parameter.value;
        issues.push(`<li>Fixed F4 coefficient: ${escape(scalar)}<small>Source parameter id: ${escape(parameter.id)}; ${escape(parameter.fixed_reason || "explicit source normalization")}. Incompatible assignments are reported, not substituted.</small></li>`);
      } else {
        issues.push(`<li>Nonzero F4 parameter: ${escape(parameter.symbol || parameter.id)}${parameter.frobenius_power ? '² (Frobenius image)' : ''}<small>Source parameter id: ${escape(parameter.id)}; no implicit unit-1 assignment.</small></li>`);
      }
      if (parameter.source_parameter) {
        const source = parameter.source_parameter;
        issues.push(`<li>Shared source coefficient: ${escape(source.workspace_id)} / ${escape(source.parameter_id)}<small>Requires source differential ${escape(source.differential_id)} on E${escape(source.page)}. Resolve the unit in that source workspace; a local assignment cannot override it. Frobenius is applied only after resolving the shared source-field unit.</small></li>`);
      }
      if (parameter.target_component !== undefined) issues.push(`<li>Relative coefficient on ${escape(parameter.target_component)} only<small>The other target basis columns are unchanged; P+bQ is not b(P+Q).</small></li>`);
      if (parameter.inverse_parameter_id !== undefined) issues.push(`<li>Linked coefficient ratio: ${escape(parameter.expression || parameter.symbol)}<small>Divide by the shared source-field parameter ${escape(parameter.inverse_parameter_id)} before applying Frobenius. An unresolved denominator does not mean 1.</small></li>`);
      if (parameter.affine_offset !== undefined) issues.push(`<li>Linked coefficient: ${escape(parameter.expression || `${parameter.symbol || parameter.id} + ${parameter.affine_offset}`)}<small>The expression may be zero. A zero branch is a zero differential, not an arrow or a page death.</small></li>`);
    }
    if (!issues.length) return "";
    return `<details class="claim-source-audit"><summary>Source / coefficient caveats</summary><ul>${issues.join("")}</ul></details>`;
  }

  root.HFPSSTableLedger = {rowsForWorkspace, markup, claimAuditMarkup, render: renderPublishedTableLedger};
  root.renderPublishedTableLedger = renderPublishedTableLedger;
})(typeof window !== "undefined" ? window : globalThis);
