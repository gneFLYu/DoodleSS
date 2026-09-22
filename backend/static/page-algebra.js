/* Finite coefficient ports in the D^8 fundamental domain.
 * j>0 denotes a completed ideal, not an eagerly enumerated series.
 * 2^3 denotes the remaining free Witt tail in filtration zero.
 */
(function (root) {
  "use strict";
  const modulo = (n, d) => ((n % d) + d) % d;
  const cellKey = (node, grade) => node?.style?.e2_pattern
    ? `${node.style.e2_pattern}:${modulo(grade.stem, 64)}:${grade.filtration}` : "";
  const portKey = (two, j) => `${two}:${j > 0 ? 1 : 0}`;

  function seedPorts(pattern, filtration) {
    const ports = new Set();
    const add = (two, j = 0) => ports.add(portKey(two, j));
    const witt = ["I00", "I40", "S00", "S40"].includes(pattern);
    const series = witt || ["I11", "I51", "I22H", "I62V", "I33", "I73V", "S11", "S51", "S22H", "S33", "S62V", "S73V"].includes(pattern);
    const highestTwo = witt ? (filtration === 0 ? 3 : (pattern === "I00" ? 2 : (pattern === "S40" ? 1 : 0))) : (pattern === "I31" ? 1 : 0);
    for (let two = 0; two <= highestTwo; two++) add(two);
    if (series) for (let two = 0; two <= (witt && filtration === 0 ? 3 : 0); two++) add(two, 1);
    return ports;
  }

  function component(node) {
    const s = node?.style || {};
    return {two: Number(s.two_valuation || 0), j: Number(s.j_order || 0)};
  }

  // A certificate for one coefficient layer is not a certificate for the
  // whole Witt/j-adic cell. Legacy zero maps retain their stated module
  // closure; permanent-cycle certificates default to the displayed j layer
  // and its additive 2-multiples, not an unrelated completed-series tail.
  function allowsConstraintBranch(diff, two, j) {
    const constraint = diff?.cycle_constraint;
    const scope = diff?.coefficient_scope || constraint?.coefficient_scope;
    if (!constraint && !scope) return true;
    if (scope === "exact-port") return two === 0 && j === 0;
    if (scope === "all-multiples") return true;
    return j === 0;
  }

  function mapPorts(source, target, sourcePorts, targetPorts, diff = null) {
    const a = component(source), b = component(target), maps = [];
    for (let two = 0; two < 4; two++) {
      for (let j = 0; j < 2; j++) {
        if (!allowsConstraintBranch(diff, two, j)) continue;
        const from = portKey(a.two + two, a.j + j);
        const to = portKey(b.two + two, b.j + j);
        if (sourcePorts?.has(from) && targetPorts?.has(to)) maps.push({from, to});
      }
    }
    return maps;
  }

  const caches = new WeakMap();
  function compute(ws, bounds, helpers) {
    // An E_{r+1} class in filtration f needs both E_r endpoints through f+r.
    // Reserve the sum of relevant page shifts, not a single 24-cell halo:
    // otherwise freshly seeded outer targets can masquerade as known cycles.
    const pageCosts = new Set(ws.differentials.map(d => d.page)
      .filter(r => Number.isInteger(r) && r >= 2 && r <= ws.page));
    const halo = [...pageCosts].reduce((sum, r) => sum + r, 0);
    const maximum = Math.max(64, Math.ceil((bounds.filtrationMax + halo) / 32) * 32);
    const externalIds = new Set((ws.propositions || []).map(p => p.conclusion?.coefficient_parameter?.source_parameter?.workspace_id));
    const externalWorkspaces = (helpers.coefficientWorkspaces || []).filter(w => externalIds.has(w.id));
    // An external premise is an explicit locator for one declared premise ID,
    // never permission to borrow an unqualified same-name proof.
    const availableProofScopes = [...(helpers.coefficientWorkspaces || [])];
    if (!availableProofScopes.includes(ws)) availableProofScopes.push(ws);
    const proofScopesById = new Map();
    for (const owner of availableProofScopes) {
      if (typeof owner?.id !== "string" || !owner.id.trim()) continue;
      if (!proofScopesById.has(owner.id)) proofScopesById.set(owner.id, []);
      proofScopesById.get(owner.id).push(owner);
    }
    // Include all recursively referenced proof scopes in the cache key.
    // Missing/duplicated scopes and edits to an external leaf invalidate it.
    const proofScopes = [ws], seenProofScopes = new Set([ws]), referencedProofScopes = new Set();
    for (let index = 0; index < proofScopes.length; index++) {
      for (const proof of proofScopes[index].propositions || []) {
        const locators = proof.conclusion?.external_premises;
        if (!Array.isArray(locators)) continue;
        for (const locator of locators) {
          if (typeof locator?.workspace_id !== "string") continue;
          referencedProofScopes.add(locator.workspace_id);
          for (const owner of proofScopesById.get(locator.workspace_id) || []) {
            if (seenProofScopes.has(owner)) continue;
            seenProofScopes.add(owner); proofScopes.push(owner);
          }
        }
      }
    }
    // Edits may change an existing arrow without changing the array length.
    // Include algebraically relevant fields so a page edit cannot reuse an
    // obsolete quotient. Camera translations do not invalidate this cache.
    const signature = JSON.stringify([ws.page, maximum, ws.settings.rendering,
      ws.classes.map(c => [c.id, c.grade, c.page, c.archived, c.coordinates, c.style?.e2_pattern, c.style?.e2_components,
        c.style?.e2_basis_patterns, c.style?.two_valuation, c.style?.j_order]),
      ws.differentials.map(d => [d.id, d.source_id, d.target_id, d.page, d.status, d.archived, d.period_stem, d.period_filtration, d.linear_map_id, d.proposition_id,
        Object.prototype.hasOwnProperty.call(d, "required_admitted_premises") ? d.required_admitted_premises : false]),
      (ws.differential_maps || []).map(m => [m.id, m.matrix, m.status, m.archived]),
      (ws.propositions || []).filter(p => ["zero-differential", "permanent-cycle"].includes(p.kind))
        .map(p => [p.id, p.kind, p.status, p.conclusion]),
      (ws.propositions || []).filter(p => p.conclusion?.coefficient_parameter).map(p => [p.id, p.conclusion.coefficient_parameter]),
      (ws.propositions || []).filter(p => Object.prototype.hasOwnProperty.call(p.conclusion || {}, "coefficient_condition"))
        .map(p => [p.id, p.conclusion.coefficient_condition]),
      (ws.propositions || []).filter(p => p.conclusion?.coefficient_constraints).map(p => [p.id, p.conclusion.coefficient_constraints]),
      (ws.propositions || []).map(p => [p.id, p.kind, p.status, p.premise_ids, p.conclusion?.fact_id,
        p.conclusion?.rank_one_unit_certificate, p.conclusion?.coefficient_scope, p.conclusion?.cycle_constraint]),
      ws.settings.coefficient_assignments || {},
      externalWorkspaces.map(w => [w.id, w.settings?.coefficient_assignments,
        (w.propositions || []).map(p => [p.id, p.status, p.conclusion?.coefficient_parameter,
          p.conclusion?.fact_id, p.conclusion?.coefficient_constraints]),
        (w.differentials || []).map(d => [d.id, d.page, d.status, d.proposition_id, d.linear_map_id]),
        (w.differential_maps || []).map(m => [m.id, m.status, m.archived])]),
      [...referencedProofScopes].map(id => [id, (proofScopesById.get(id) || []).length]),
      proofScopes.map(w => [w.id, (w.propositions || []).map(p =>
        [p.id, p.kind, p.status, p.premise_ids, p.conclusion])]),
      helpers.periodSignature || ""]);
    const cached = caches.get(ws);
    if (cached?.signature === signature) return cached.value;
    const domain = {stemMin: 0, stemMax: 63, filtrationMin: 0, filtrationMax: maximum};
    const trustedDomain = {filtrationMin: 0, filtrationMax: maximum};
    const inTrustedDomain = grade => grade.filtration >= trustedDomain.filtrationMin
      && grade.filtration <= trustedDomain.filtrationMax;
    const nodes = new Map(ws.classes.map(c => [c.id, c]));
    const linearMaps = new Map((ws.differential_maps || []).map(m => [m.id, m]));
    const claims = new Map((ws.propositions || []).map(p => [p.id, p]));
    // Ordinary premise IDs stay local. A qualified locator overrides local
    // lookup, so a same-name local record cannot impersonate an external proof.
    const recordsByScope = new Map(), admissionByScope = new Map(), checkingByScope = new Map();
    const scopeRecords = owner => {
      if (!recordsByScope.has(owner)) {
        const records = new Map();
        for (const proof of owner.propositions || [])
          records.set(proof.id, records.has(proof.id) ? null : proof);
        recordsByScope.set(owner, records);
        admissionByScope.set(owner, new Map()); checkingByScope.set(owner, new Set());
      }
      return recordsByScope.get(owner);
    };
    const acceptedProof = (owner, proof) => {
      const premiseRecords = scopeRecords(owner);
      const premiseAdmission = admissionByScope.get(owner), checkingPremises = checkingByScope.get(owner);
      if (!proof || typeof proof.id !== "string" || !proof.id.trim()
          || premiseRecords.get(proof.id) !== proof || !helpers.accepted(proof)
          || proof.kind === "tombstone") return false;
      if (checkingPremises.has(proof.id)) return false;
      if (premiseAdmission.has(proof.id)) return premiseAdmission.get(proof.id);
      const premises = proof.premise_ids ?? [];
      const external = proof.conclusion?.external_premises === undefined ? [] : proof.conclusion.external_premises;
      if (!Array.isArray(premises) || !Array.isArray(external)) return false;
      const locators = new Map();
      for (const locator of external) {
        if (!locator || typeof locator.workspace_id !== "string" || !locator.workspace_id.trim()
            || typeof locator.proposition_id !== "string" || !locator.proposition_id.trim()
            || !premises.includes(locator.proposition_id) || locators.has(locator.proposition_id)) return false;
        locators.set(locator.proposition_id, locator.workspace_id);
      }
      checkingPremises.add(proof.id);
      const admitted = premises.every(id => {
        if (typeof id !== "string" || !id.trim()) return false;
        let targetOwner = owner;
        if (locators.has(id)) {
          const matches = proofScopesById.get(locators.get(id)) || [];
          if (matches.length !== 1) return false;
          targetOwner = matches[0];
        }
        return acceptedProof(targetOwner, scopeRecords(targetOwner).get(id));
      });
      checkingPremises.delete(proof.id);
      premiseAdmission.set(proof.id, admitted);
      return admitted;
    };
    const cyclePremisesAccepted = proof => {
      const external = proof.conclusion?.external_premises;
      const noLocal = proof.premise_ids == null || (Array.isArray(proof.premise_ids) && !proof.premise_ids.length);
      const noExternal = external === undefined || (Array.isArray(external) && !external.length);
      return noLocal && noExternal || acceptedProof(ws, proof);
    };
    const requiredDifferentialPremisesAccepted = diff => {
      const proofs = (ws.propositions || []).filter(proof => proof.id === diff.proposition_id);
      const mirror = Object.prototype.hasOwnProperty.call(diff, "required_admitted_premises")
        ? diff.required_admitted_premises : false;
      const optedIn = mirror !== false || proofs.some(proof =>
        Object.prototype.hasOwnProperty.call(proof.conclusion || {}, "required_admitted_premises"));
      if (!optedIn) return true;
      // A persistent row flag prevents deleting its proof from silently
      // restoring legacy admission. Both mirrors must be literal booleans.
      const proof = proofs.length === 1 ? proofs[0] : null;
      return mirror === true && proof?.conclusion?.required_admitted_premises === true
        && proof.kind === "differential" && Array.isArray(proof.premise_ids)
        && proof.premise_ids.length > 0 && acceptedProof(ws, proof);
    };
    const scopedDifferential = diff => {
      const metadata = claims.get(diff.proposition_id)?.conclusion || {};
      const scope = metadata.coefficient_scope ?? diff.coefficient_scope;
      const constraint = metadata.cycle_constraint ?? diff.cycle_constraint;
      return scope === undefined && constraint === undefined ? diff
        : {...diff, coefficient_scope: scope, cycle_constraint: constraint};
    };
    const L = root.HFPSSGradedQuotient, parameters = new Map(), declarations = new Map();
    // A stable parameter names one source-field scalar, even in a psi image.
    // Missing assignments are never interpreted as 1. Conflicting declarations
    // are diagnosed before any page quotient can consume their endpoints.
    for (const claim of claims.values()) {
      const spec = claim.conclusion?.coefficient_parameter;
      if (!spec?.id) continue;
      if (!declarations.has(spec.id)) declarations.set(spec.id, []);
      declarations.get(spec.id).push(spec);
      if (!parameters.has(spec.id)) parameters.set(spec.id, {values: new Set(), errors: [], domains: []});
      const record = parameters.get(spec.id);
      if (Array.isArray(spec.domain)) record.domains.push(spec.domain);
      if (Object.prototype.hasOwnProperty.call(spec, "source_parameter")) continue;
      for (const value of [spec.value, ws.settings.coefficient_assignments?.[spec.id]]) {
        if (value === null || value === undefined) continue;
        try {
          const scalar = L.scalar(value);
          if (!scalar) throw new Error("zero is not an F4 unit");
          record.values.add(scalar);
        } catch (error) { record.errors.push(error.message); }
      }
    }
    // A transported coefficient is a reference to the live source workspace,
    // not a second, independently assignable mixed-sector scalar. Resolve raw
    // source-field units here; the target occurrence applies Frobenius later.
    const sourceConstraintConflict = (source, page, choices = null) => {
      const sourceClaims = new Map((source.propositions || []).map(p => [p.id, p]));
      const matrices = new Map((source.differential_maps || []).map(m => [m.id, m]));
      const ids = new Set(), facts = new Set(), factPages = new Set(), constraints = new Map();
      for (const row of source.differentials || []) {
        if (!helpers.accepted(row)) continue;
        const matrix = matrices.get(row.linear_map_id);
        if (row.linear_map_id && (!matrix || matrix.archived || !helpers.accepted(matrix))) continue;
        const metadata = sourceClaims.get(row.proposition_id)?.conclusion || {};
        if (metadata.coefficient_parameter?.id) ids.add(metadata.coefficient_parameter.id);
        if (metadata.fact_id) {
          facts.add(metadata.fact_id);
          factPages.add(`${metadata.fact_id}@${row.page}`);
        }
        for (const constraint of metadata.coefficient_constraints || []) {
          if (constraint?.id) constraints.set(constraint.id, constraint);
        }
      }
      const rawValues = id => {
        if (choices?.has(id)) return [choices.get(id)];
        const values = new Set();
        for (const claim of sourceClaims.values()) {
          const spec = claim.conclusion?.coefficient_parameter;
          if (spec?.id !== id) continue;
          for (const value of [spec.value, source.settings?.coefficient_assignments?.[id]]) {
            if (value == null) continue;
            try { const unit = L.scalar(value); if (unit) values.add(unit); } catch (_) { /* diagnosed at resolution */ }
          }
        }
        return [...values];
      };
      return [...constraints.values()].some(c => {
        if (c.kind !== "equal-nonzero-parameters" || !Number.isInteger(c.page) || c.page > page
            || !Array.isArray(c.parameter_ids) || !c.parameter_ids.length
            || !c.parameter_ids.every(id => ids.has(id))
            || !(c.required_facts || []).every(id => facts.has(id))
            || !(c.required_differentials || []).every(d => factPages.has(`${d?.fact_id}@${d?.page}`))) return false;
        const values = c.parameter_ids.map(rawValues);
        if (!values.every(v => v.length === 1)) return false;
        return new Set(values.map(v => v[0])).size > 1
          || (Object.prototype.hasOwnProperty.call(c, "normalization_value")
            && values.some(v => v[0] !== c.normalization_value));
      });
    };
    for (const [id, specs] of declarations) {
      if (!specs.some(s => Object.prototype.hasOwnProperty.call(s, "source_parameter"))) continue;
      const record = parameters.get(id), ref = specs[0].source_parameter;
      record.linked = true;
      record.values.clear();
      const fail = reason => { record.errors.push(reason); record.bindingReason ||= reason; };
      if (!ref || typeof ref !== "object" || Array.isArray(ref)
          || typeof ref.workspace_id !== "string" || !ref.workspace_id
          || ref.parameter_id !== id || typeof id !== "string" || !id
          || typeof ref.differential_id !== "string" || !ref.differential_id
          || !Number.isInteger(ref.page) || ref.page < 2
          || specs.some(s => !s.source_parameter || ["workspace_id", "parameter_id", "differential_id", "page"]
            .some(key => s.source_parameter[key] !== ref[key]))) {
        fail("invalid linked coefficient reference"); continue;
      }
      if (specs.some(s => s.value !== null && s.value !== undefined)
          || ws.settings.coefficient_assignments?.[id] != null) {
        fail("linked coefficient cannot have a local assignment"); continue;
      }
      const sources = externalWorkspaces.filter(w => w.id === ref.workspace_id);
      if (sources.length !== 1 || ref.workspace_id === ws.id) {
        fail("linked coefficient source workspace is unavailable"); continue;
      }
      const source = sources[0], sourceRows = (source.differentials || []).filter(d => d.id === ref.differential_id);
      record.sourceWorkspace = source;
      record.sourcePage = ref.page;
      const row = sourceRows[0], sourceClaims = (source.propositions || []).filter(p => p.id === row?.proposition_id);
      const sourceClaim = sourceClaims[0], sourceSpec = sourceClaim?.conclusion?.coefficient_parameter;
      const matrices = (source.differential_maps || []).filter(m => m.id === row?.linear_map_id);
      const matrix = matrices[0];
      if (sourceRows.length !== 1 || row.page !== ref.page || sourceClaims.length !== 1 || sourceSpec?.id !== id) {
        fail("linked coefficient source differential does not match"); continue;
      }
      if (!helpers.accepted(row) || !helpers.accepted(sourceClaim)
          || (row.linear_map_id && (matrices.length !== 1 || matrix.archived || !helpers.accepted(matrix)))) {
        fail("linked coefficient source differential is not admitted"); continue;
      }
      const sourceSpecs = (source.propositions || []).map(p => p.conclusion?.coefficient_parameter).filter(s => s?.id === id);
      if (sourceSpecs.some(s => Object.prototype.hasOwnProperty.call(s, "source_parameter"))) {
        fail("nested linked coefficient references are not supported"); continue;
      }
      for (const spec of sourceSpecs) {
        if (Array.isArray(spec.domain)) record.domains.push(spec.domain);
        for (const value of [spec.value, source.settings?.coefficient_assignments?.[id]]) {
          if (value === null || value === undefined) continue;
          try {
            const scalar = L.scalar(value);
            if (!scalar) throw new Error("zero unit");
            record.values.add(scalar);
          } catch (_) { fail("invalid linked coefficient source assignment"); }
        }
      }
      if (record.values.size > 1) fail("conflicting linked coefficient source assignments");
      else if (!record.values.size) fail("linked coefficient source parameter is unresolved");
      else if (record.domains.some(domain => !domain.includes([...record.values][0])))
        fail("linked coefficient source assignment is outside its domain");
      if (sourceConstraintConflict(source, ref.page)) fail("linked coefficient source coefficient constraints conflict");
    }
    // The condition refers to the original source-field parameter, including
    // in a psi image. Its false branch is a certified zero Euler image, not
    // a nonzero map with an arbitrarily chosen unit.
    // Candidate choices are local read-only views, never stored assignments.
    // An unresolved but otherwise validated source link may be enumerated;
    // a missing/unadmitted/malformed source reference may not.
    const parameterView = (id, choices = null) => {
      const record = parameters.get(id);
      if (!record || !choices?.has(id)) return record;
      const unresolvedLink = "linked coefficient source parameter is unresolved";
      return {...record, values: new Set([choices.get(id)]),
        errors: record.errors.filter(reason => reason !== unresolvedLink),
        bindingReason: record.bindingReason === unresolvedLink ? null : record.bindingReason};
    };
    const conditionState = (diff, choices = null) => {
      const condition = claims.get(diff.proposition_id)?.conclusion?.coefficient_condition;
      if (condition === undefined) return {resolved: true, nonzero: true};
      if (!condition || typeof condition !== "object"
          || typeof condition.parameter_id !== "string" || !condition.parameter_id
          || ![1, 2, 3].includes(condition.equals) || condition.otherwise !== "zero-euler-image") {
        return {resolved: false, reason: "invalid coefficient condition"};
      }
      const record = parameterView(condition.parameter_id, choices), values = [...(record?.values || [])];
      const reason = !record ? "coefficient condition parameter is undeclared"
        : record.errors.length ? "invalid coefficient condition assignment"
        : values.length > 1 ? "conflicting assignments for coefficient condition"
        : !values.length ? "coefficient condition is unresolved"
        : record.domains.some(domain => !domain.includes(values[0])) ? "coefficient condition is outside its domain" : "";
      return reason ? {resolved: false, id: condition.parameter_id, reason}
        : {resolved: true, id: condition.parameter_id, value: values[0], nonzero: values[0] === condition.equals};
    };
    const coefficientState = (diff, choices = null) => {
      const condition = conditionState(diff, choices);
      if (!condition.resolved) return condition;
      if (!condition.nonzero) return {resolved: true, value: 0, zeroEulerImage: true, condition};
      const spec = claims.get(diff.proposition_id)?.conclusion?.coefficient_parameter;
      if (!spec) return {resolved: true, value: 1};
      const record = parameterView(spec.id, choices), values = [...(record?.values || [])];
      let reason = !spec.id ? "coefficient parameter has no stable id"
        : record.bindingReason ? record.bindingReason
        : record.errors.length ? "invalid F4 unit assignment"
        : values.length > 1 ? "conflicting assignments for the same coefficient parameter"
        : !values.length ? "coefficient parameter is unresolved" : "";
      const power = spec.frobenius_power;
      if (![0, 1].includes(power)) reason = "invalid coefficient Frobenius power";
      if (values.length && Array.isArray(spec.domain) && !spec.domain.includes(values[0])) reason = "coefficient assignment is outside its domain";
      let offset = 0;
      try { offset = L.scalar(spec.affine_offset ?? 0); }
      catch (_) { reason = "invalid F4 affine offset"; }
      let inverse = 1;
      if (spec.inverse_parameter_id !== undefined) {
        const id = spec.inverse_parameter_id, denominator = parameterView(id, choices);
        const units = [...(denominator?.values || [])];
        const denominatorReason = typeof id !== "string" || !id ? "invalid coefficient denominator id"
          : !denominator ? "coefficient denominator parameter is undeclared"
          : denominator.errors.length ? "invalid coefficient denominator assignment"
          : units.length > 1 ? "conflicting assignments for coefficient denominator"
          : !units.length ? "coefficient denominator is unresolved"
          : denominator.domains.some(domain => !domain.includes(units[0])) ? "coefficient denominator is outside its domain" : "";
        if (denominatorReason) reason = denominatorReason;
        else inverse = [0, 1, 3, 2][units[0]];
      }
      const component = spec.target_component;
      if (component !== undefined) {
        const style = nodes.get(diff.target_id)?.style || {};
        const basis = style.e2_basis_patterns || Object.keys(style.e2_components || {});
        if (typeof component !== "string" || !basis.includes(component)) reason = "invalid coefficient target component";
      }
      // Take the ratio in the shared source field before conjugating it.
      // In particular psi(gamma/b)=psi(gamma)/psi(b).
      const value = values.length ? L.mul(L.add(values[0], offset), inverse) : 0;
      return reason ? {resolved: false, id: spec.id, reason}
        : {resolved: true, id: spec.id, value: power ? L.mul(value, value) : value, component};
    };
    const matrixEndpoints = diff => {
      const source = nodes.get(diff.source_id), target = nodes.get(diff.target_id);
      const matrix = linearMaps.get(diff.linear_map_id), basis = target?.style?.e2_basis_patterns;
      const L = root.HFPSSGradedQuotient;
      if (!matrix || !basis || !L || matrix.matrix.length !== basis.length) return {source, target};
      const coordinates = source.coordinates || [1];
      if (matrix.matrix.some(row => row.length !== coordinates.length)) return {source, target};
      const values = matrix.matrix.map(row => row.reduce((sum, c, i) => L.add(sum, L.mul(L.scalar(c), L.scalar(coordinates[i]))), 0));
      const style = {...target.style, e2_components: Object.fromEntries(basis.map((p, i) => [p, values[i]]))};
      delete style.e2_pattern;
      return {source, target: {...target, style}};
    };
    const endpoints = (diff, coefficient = coefficientState(diff)) => {
      const pair = matrixEndpoints(diff);
      if (!coefficient.resolved || coefficient.value === 1 || !pair.target) return pair;
      const target = pair.target, components = target.style?.e2_components
        || (target.style?.e2_pattern ? {[target.style.e2_pattern]: 1} : null);
      if (!components) return pair;
      const scaled = Object.fromEntries(Object.entries(components).map(([p, c]) =>
        [p, coefficient.component && p !== coefficient.component ? c : L.mul(coefficient.value, c)]));
      const basis = target.style.e2_basis_patterns;
      const cell = (ws.cells || []).find(c => c.id === target.cell_id);
      const scalarText = value => ["0", "1", "\\zeta", "\\zeta^2"][value];
      const label = basis && cell?.basis?.length === basis.length
        ? basis.flatMap((p, i) => !scaled[p] ? [] : [scaled[p] === 1 ? cell.basis[i].label
          : `${scalarText(scaled[p])}(${cell.basis[i].label})`]).join("+") || "0"
        : !coefficient.component ? (coefficient.value ? `${scalarText(coefficient.value)}(${target.label})` : "0") : target.label;
      const coordinates = basis ? basis.map(p => scalarText(scaled[p] || 0)) : target.coordinates;
      return {...pair, target: {...target, label, coordinates, style: {...target.style, e2_components: scaled}}};
    };
    const isZero = (diff, target = endpoints(diff).target) => {
      if (diff.zero) return true;
      const coefficient = coefficientState(diff);
      if (!coefficient.resolved) return false;
      const components = target?.style?.e2_components;
      return components ? Object.values(components).every(c => L.scalar(c) === 0) : coefficient.value === 0;
    };
    const accepted = diff => helpers.accepted(diff) && requiredDifferentialPremisesAccepted(diff) && (!diff.linear_map_id
      || (!linearMaps.get(diff.linear_map_id)?.archived && helpers.accepted(linearMaps.get(diff.linear_map_id) || {})));
    const activeParameters = new Set(), activeFacts = new Set(), activeFactPages = new Set(), constraints = new Map();
    for (const diff of ws.differentials.filter(accepted)) {
      const metadata = claims.get(diff.proposition_id)?.conclusion;
      if (metadata?.coefficient_parameter?.id) activeParameters.add(metadata.coefficient_parameter.id);
      if (metadata?.fact_id) activeFacts.add(metadata.fact_id);
      if (metadata?.fact_id) activeFactPages.add(`${metadata.fact_id}@${diff.page}`);
      for (const constraint of metadata?.coefficient_constraints || []) {
        if (constraint?.id) constraints.set(constraint.id, constraint);
      }
    }
    const constraintFailures = (page, choices = null) => [...constraints.values()].filter(c => c.page === page
      && c.kind === "equal-nonzero-parameters" && Array.isArray(c.parameter_ids)
      && c.parameter_ids.every(id => activeParameters.has(id))
      && (c.required_facts || []).every(id => activeFacts.has(id))
      && (c.required_differentials || []).every(d => activeFactPages.has(`${d.fact_id}@${d.page}`)))
      .flatMap(c => {
        const values = c.parameter_ids.map(id => [...(parameterView(id, choices)?.values || [])]);
        // Missing/invalid individual assignments have their own diagnostics.
        if (!values.every(v => v.length === 1)) return [];
        const scalars = values.map(v => v[0]);
        const reason = new Set(scalars).size > 1 ? "Leibniz coefficient compatibility violated"
          : c.normalization_value !== undefined && scalars.some(v => v !== c.normalization_value)
            ? "coefficient normalization differs from the cited integer table" : "";
        return reason ? [{id:c.id, page, parameterIds:c.parameter_ids, reason,
          normalizationSource:c.normalization_source}] : [];
      });
    const cells = new Map(), arrows = [], conflicts = [];
    const ensure = (node, grade) => {
      for (const pattern of Object.keys(node?.style?.e2_components || {})) {
        const key = `${pattern}:${modulo(grade.stem, 64)}:${grade.filtration}`;
        if (grade.filtration >= 0 && !cells.has(key)) cells.set(key, seedPorts(pattern, grade.filtration));
      }
      const key = cellKey(node, grade);
      if (key && grade.filtration >= 0 && !cells.has(key)) cells.set(key, seedPorts(node.style.e2_pattern, grade.filtration));
      return key;
    };
    for (const node of ws.classes) {
      if (node.archived || node.page > ws.page) continue;
      for (const copy of helpers.copies(node.grade, helpers.classPeriods(ws, node), domain)) ensure(node, copy.grade);
    }
    const zeros = (ws.propositions || []).filter(p => p.kind === "zero-differential" && cyclePremisesAccepted(p)
        && (p.conclusion?.source_id || p.conclusion?.class_id))
      .map(p => ({...p.conclusion, id: p.id, status: p.status, proposition_id: p.id,
        source_id: p.conclusion.source_id || p.conclusion.class_id, target_id: null, zero: true}));
    const relevantPages = [...new Set([ws.page, ...ws.differentials.map(d => d.page), ...zeros.map(d => d.page)])];
    for (const claim of ws.propositions || []) {
      const metadata = claim.conclusion || {}, sourceId = metadata.source_id || metadata.class_id;
      if (claim.kind !== "permanent-cycle" || !sourceId || !cyclePremisesAccepted(claim)) continue;
      const start = metadata.page ?? nodes.get(sourceId)?.page ?? 2;
      for (const page of relevantPages.filter(r => r >= start && r <= ws.page)) {
        // These are internal zero-outgoing constraints, not incoming Tate
        // differentials and not a promise that the HFPSS class cannot be hit.
        zeros.push({...metadata, id: `${claim.id}@${page}`, proposition_id: claim.id,
          status: claim.status, page, source_id: sourceId, target_id: null, zero: true,
          // A missing row period must not inherit the current d_r's short
          // repeat (e.g. turn the D^8 certificate into a D^2 certificate).
          period_stem: metadata.period_stem || 64,
          cycle_constraint: metadata.cycle_constraint || "outgoing-only",
          coefficient_scope: metadata.coefficient_scope || metadata.cycle_constraint?.coefficient_scope || "constant-two-multiples"});
      }
    }
    for (const storedDiff of [...ws.differentials, ...zeros]) {
      const diff = scopedDifferential(storedDiff);
      if (diff.archived || diff.page > ws.page) continue;
      const {source, target: nonzeroTarget} = endpoints(diff);
      const zero = isZero(diff, nonzeroTarget);
      const target = zero ? null : nonzeroTarget;
      const patterned = n => n?.style?.e2_pattern || n?.style?.e2_components;
      if (!source || source.archived || !patterned(source)
          || (!zero && (!target || target.archived || !patterned(target)))) continue;
      for (const copy of helpers.copies(source.grade, helpers.diffPeriods(ws, diff), domain)) {
        const sourceGrade = copy.grade;
        const targetGrade = {...target?.grade, stem: sourceGrade.stem - 1, filtration: sourceGrade.filtration + diff.page};
        const sourceKey = ensure(source, sourceGrade), targetKey = ensure(target, targetGrade);
        arrows.push({diff: zero ? {...diff, zero: true} : diff, source, target,
          sourceGrade, targetGrade, sourceKey, targetKey});
      }
    }
    const vectors = root.HFPSSVectorPageAlgebra?.create(ws, cells, conflicts, trustedDomain);
    const incidentRows = new Map(), occurrences = new Map();
    const endpointKeys = (node, grade) => Object.keys(node?.style?.e2_components
      || (node?.style?.e2_pattern ? {[node.style.e2_pattern]: 1} : {}))
      .map(pattern => `${pattern}:${modulo(grade.stem, 64)}:${grade.filtration}`);
    for (const arrow of arrows) {
      if (!occurrences.has(arrow.diff.id)) occurrences.set(arrow.diff.id, []);
      occurrences.get(arrow.diff.id).push(arrow);
      if (arrow.diff.zero) continue;
      for (const key of [...endpointKeys(arrow.source, arrow.sourceGrade), ...endpointKeys(arrow.target, arrow.targetGrade)]) {
        const pageKey = `${arrow.diff.page}:${key}`;
        if (!incidentRows.has(pageKey)) incidentRows.set(pageKey, new Set());
        incidentRows.get(pageKey).add(arrow.diff.id);
      }
    }
    const unitInvariantIds = new Set();
    for (const diff of ws.differentials) {
      const claim = claims.get(diff.proposition_id), metadata = claim?.conclusion || {};
      const certificate = metadata.rank_one_unit_certificate, spec = metadata.coefficient_parameter;
      const coefficient = coefficientState(diff), pair = matrixEndpoints(diff), copies = occurrences.get(diff.id);
      if (!vectors || !accepted(diff) || !helpers.accepted(claim || {}) || claim?.kind !== "differential"
          || diff.archived || diff.linear_map_id
          || coefficient.resolved || coefficient.reason !== "coefficient parameter is unresolved"
          || certificate?.status !== "verified" || certificate.kind !== "isolated-finite-F4-isomorphism"
          || certificate.page !== diff.page || certificate.coefficient_scope !== "exact-port"
          || metadata.coefficient_scope !== "exact-port" || !copies?.length
          || !spec?.id || spec.value !== null || ![0, 1].includes(spec.frobenius_power)
          || !Array.isArray(spec.domain) || !spec.domain.length || spec.domain.some(unit => ![1, 2, 3].includes(unit))
          || ["target_component", "affine_offset", "source_parameter", "inverse_parameter_id"].some(key => key in spec)
          || "coefficient_condition" in metadata || (declarations.get(spec.id) || []).length !== 1
          || ws.differentials.filter(row => row.id === diff.id).length !== 1) continue;
      // A shared relative coefficient can change a diagonal kernel. This
      // narrow certificate does not solve coupled parameter constraints.
      if ([...claims.values()].some(other => {
        const data = other.conclusion || {}, parameter = data.coefficient_parameter;
        return parameter?.inverse_parameter_id === spec.id || data.coefficient_condition?.parameter_id === spec.id
          || (data.coefficient_constraints || []).some(constraint => constraint.parameter_ids?.includes(spec.id));
      })) continue;
      const native = (node, pattern) => node && !node.archived && node.page <= diff.page
        && node.style?.e2_pattern === pattern && !node.style.e2_components
        && !node.style.e2_basis_patterns && !node.cell_id && !(node.coordinates?.length)
        && component(node).two === 0 && component(node).j === 0;
      if (!native(pair.source, certificate.source_pattern) || !native(pair.target, certificate.target_pattern)) continue;
      if (pair.target.grade.stem !== pair.source.grade.stem - 1
          || pair.target.grade.filtration !== pair.source.grade.filtration + diff.page) continue;
      if (copies.some(arrow => [[arrow.source, arrow.sourceGrade], [arrow.target, arrow.targetGrade]].some(([node, grade]) => {
        const ports = seedPorts(node.style.e2_pattern, grade.filtration);
        return ports.size !== 1 || !ports.has("0:0") || vectors.blockFor(node, grade)
          || [...(incidentRows.get(`${diff.page}:${cellKey(node, grade)}`) || [])].some(id => id !== diff.id);
      }))) continue;
      unitInvariantIds.add(diff.id);
    }
    // Only the isolated finite quotient uses this representative unit.
    // It is never returned as the differential's coefficient or assigned
    // to its shared parameter: all nonzero units have the same kernel/image.
    const quotientCoefficientState = diff => {
      const coefficient = coefficientState(diff);
      return !coefficient.resolved && unitInvariantIds.has(diff.id)
        ? {resolved: true, value: 1, unitInvariant: true} : coefficient;
    };
    let blockedFromPage = null;
    for (const page of [...new Set(arrows.map(a => a.diff.page))].sort((a,b) => a-b)) {
      if (page > ws.page) break;
      const unresolved = [...new Map(arrows.filter(a => a.diff.page === page && accepted(a.diff))
        .map(a => [a.diff.id, a.diff])).values()].filter(d => !quotientCoefficientState(d).resolved);
      if (unresolved.length && page < ws.page) {
        for (const diff of unresolved) conflicts.push({id: diff.id, page, ...coefficientState(diff)});
        blockedFromPage = page;
        break; // E_{page+1} is unknown, so no later page may use it as a known quotient.
      }
      const incompatible = constraintFailures(page);
      if (incompatible.length) {
        conflicts.push(...incompatible);
        blockedFromPage = page;
        break;
      }
      // An isolated certified F4 isomorphism is nonzero independently of
      // its unit; other unresolved maps remain outside the known quotient.
      const resolvedAccepted = diff => accepted(diff) && quotientCoefficientState(diff).resolved;
      // These checks only collect diagnostics from E_r. Run every check
      // before blocking: one absent source must not hide an independent
      // cycle or square-zero contradiction elsewhere on the same page.
      const vectorChecks = vectors ? [
        vectors.validateKnownSources(page, arrows, resolvedAccepted),
        vectors.validateScalarCycles(page, arrows, resolvedAccepted),
        vectors.validateScalarChains(page, arrows, resolvedAccepted),
      ] : [];
      if (vectorChecks.some(valid => !valid)) {
        blockedFromPage = page;
        break;
      }
      const absentUnitTargets = arrows.filter(arrow => arrow.diff.page === page && unitInvariantIds.has(arrow.diff.id)
        && inTrustedDomain(arrow.sourceGrade) && inTrustedDomain(arrow.targetGrade)
        && cells.get(arrow.sourceKey)?.has("0:0") && !cells.get(arrow.targetKey)?.has("0:0"));
      if (absentUnitTargets.length) {
        for (const arrow of absentUnitTargets) conflicts.push({id: arrow.diff.id, page,
          source: arrow.sourceGrade, target: arrow.targetGrade,
          reason: "certified nonzero finite differential has an absent target port"});
        blockedFromPage = page;
        break;
      }
      const removals = [];
      for (const arrow of arrows.filter(a => a.diff.page === page && resolvedAccepted(a.diff))) {
        if (arrow.diff.zero || vectors?.blockFor(arrow.source, arrow.sourceGrade)
            || vectors?.blockFor(arrow.target, arrow.targetGrade)) continue;
        if (!inTrustedDomain(arrow.sourceGrade) || !inTrustedDomain(arrow.targetGrade)) continue;
        const maps = mapPorts(arrow.source, arrow.target, cells.get(arrow.sourceKey), cells.get(arrow.targetKey), arrow.diff);
        if (!maps.length) {
          // Only a known zero -> zero product is harmless redundancy.
          // Missing/unknown ports are not promoted to proved zeros.
          let redundant = Boolean(vectors);
          for (let two = 0; two < 4 && redundant; two++) for (let j = 0; j < 2; j++) {
            const from = vectors.endpoint(arrow.source, arrow.sourceGrade, two, j);
            const to = vectors.endpoint(arrow.target, arrow.targetGrade, two, j);
            if (!from.zero || !to.zero || from.unknown || to.unknown) redundant = false;
          }
          if (!redundant) conflicts.push({id: arrow.diff.id, page, source: arrow.sourceGrade,
            target: arrow.targetGrade, reason: "source or target port absent on this page"});
          continue;
        }
        for (const map of maps) removals.push([arrow.sourceKey, map.from], [arrow.targetKey, map.to]);
      }
      // Each d_r is applied to E_r simultaneously, never to its own quotient.
      // Validate the displayed E_r as well, but do not take its quotient
      // until E_{r+1}. A contradictory page cannot feed any later map.
      if (vectors?.process(page, arrows, resolvedAccepted, {commit: page < ws.page}) === false) {
        blockedFromPage = page;
        break;
      }
      if (page < ws.page) for (const [key, port] of removals) cells.get(key)?.delete(port);
      if (page < ws.page && pageCosts.has(page)) trustedDomain.filtrationMax -= page;
    }
    const value = {
      cells, conflicts, endpoints, coefficientState, conditionState, isZero, blockedFromPage,
      // Storage in the discarded halo is not a computed quotient block.
      // Keep its internal barriers, but never publish it as a page result.
      vectorBlocks: vectors && new Map([...vectors.blocks].filter(([id]) =>
        inTrustedDomain({filtration: Number(id.split(":")[2])}))),
      trustedFiltrationMax: trustedDomain.filtrationMax, inTrustedDomain,
      unitInvariant(diff) { return blockedFromPage === null && unitInvariantIds.has(diff.id); },
      canApply(diff) { return blockedFromPage === null && quotientCoefficientState(diff).resolved
        && !constraintFailures(diff.page).length && accepted(diff); },
      knownCycle(node, grade) {
        if (blockedFromPage !== null || !inTrustedDomain(grade)) return false;
        if (vectors?.blockFor(node, grade)) { const e = vectors.endpoint(node, grade); return e.live && !e.unknown; }
        return this.live(node, grade);
      },
      representatives(view) { return (vectors?.representatives(view) || []).map(r => blockedFromPage === null ? r : {...r, uncertain: true}); },
      ports(node, grade) { return vectors?.ports(node, grade) ?? cells.get(cellKey(node, grade)); },
      displaySlots(node, grade) { return vectors?.slots(node, grade) || []; },
      endpointSlots(node, grade) { return vectors?.endpointSlots(node, grade) || []; },
      live(node, grade) {
        if (!inTrustedDomain(grade)) return false;
        if (vectors?.blockFor(node, grade)) return vectors.endpoint(node, grade).live;
        const ports = cells.get(cellKey(node, grade));
        if (!ports) return true;
        const c = component(node);
        return ports.has(portKey(c.two, c.j));
      },
      maps(source, target, sourceGrade, targetGrade) {
        if (blockedFromPage !== null || !inTrustedDomain(sourceGrade) || !inTrustedDomain(targetGrade)) return [];
        if (vectors?.blockFor(source, sourceGrade) || vectors?.blockFor(target, targetGrade)) {
          return vectors.maps(source, target, sourceGrade, targetGrade);
        }
        return mapPorts(source, target, cells.get(cellKey(source, sourceGrade)), cells.get(cellKey(target, targetGrade)));
      },
    };
    const candidateCoefficients = new WeakMap(), candidateStates = new WeakMap(), zeroSpans = new Map();
    const candidateVariants = diff => {
      if (candidateCoefficients.has(diff)) return candidateCoefficients.get(diff);
      const original = coefficientState(diff), metadata = claims.get(diff.proposition_id)?.conclusion || {};
      const ids = new Set([metadata.coefficient_parameter?.id,
        metadata.coefficient_parameter?.inverse_parameter_id, metadata.coefficient_condition?.parameter_id].filter(Boolean));
      const linkedSources = [...new Set([...ids].map(id => parameters.get(id)?.sourceWorkspace).filter(Boolean))];
      // Include related raw parameters so equalities are checked jointly, not
      // independently against three unrelated choices for one source scalar.
      const enabledRelations = (items, ids, facts, factPages) => items.filter(c => c.page <= diff.page
        && c.kind === "equal-nonzero-parameters" && Array.isArray(c.parameter_ids)
        && c.parameter_ids.every(id => ids.has(id))
        && (c.required_facts || []).every(id => facts.has(id))
        && (c.required_differentials || []).every(d => factPages.has(`${d.fact_id}@${d.page}`)));
      const relations = enabledRelations([...constraints.values()], activeParameters, activeFacts, activeFactPages);
      for (const source of linkedSources) {
        const sourceClaims = new Map((source.propositions || []).map(p => [p.id, p]));
        const matrices = new Map((source.differential_maps || []).map(m => [m.id, m]));
        const sourceIds = new Set(), facts = new Set(), factPages = new Set(), items = [];
        for (const row of source.differentials || []) {
          const matrix = matrices.get(row.linear_map_id);
          if (!helpers.accepted(row) || (row.linear_map_id && (!matrix || matrix.archived || !helpers.accepted(matrix)))) continue;
          const conclusion = sourceClaims.get(row.proposition_id)?.conclusion || {};
          if (conclusion.coefficient_parameter?.id) sourceIds.add(conclusion.coefficient_parameter.id);
          if (conclusion.fact_id) { facts.add(conclusion.fact_id); factPages.add(`${conclusion.fact_id}@${row.page}`); }
          items.push(...(conclusion.coefficient_constraints || []));
        }
        relations.push(...enabledRelations(items, sourceIds, facts, factPages));
      }
      let changed = true;
      while (changed) {
        changed = false;
        for (const relation of relations) {
          if (relation.kind !== "equal-nonzero-parameters" || !relation.parameter_ids?.some(id => ids.has(id))) continue;
          for (const id of relation.parameter_ids) if (!ids.has(id)) { ids.add(id); changed = true; }
        }
      }
      const options = id => {
        const record = parameters.get(id);
        let domains = record?.domains || [], values = [...(record?.values || [])];
        const errors = (record?.errors || []).filter(reason => reason !== "linked coefficient source parameter is unresolved");
        const specs = declarations.get(id) || linkedSources.flatMap(source =>
          (source.propositions || []).map(p => p.conclusion?.coefficient_parameter).filter(spec => spec?.id === id));
        if (!record) {
          if (!specs.length) return null;
          domains = specs.filter(spec => Array.isArray(spec.domain)).map(spec => spec.domain);
          try {
            values = [...new Set([...specs.map(spec => spec.value),
              ...linkedSources.map(source => source.settings?.coefficient_assignments?.[id])]
              .filter(unit => unit != null).map(unit => L.scalar(unit)))];
          } catch (_) { return null; }
        }
        if (errors.length || values.length > 1 || values.some(unit => ![1, 2, 3].includes(unit))
            || domains.some(domain => !domain.length || domain.some(unit => ![1, 2, 3].includes(unit)))
            || specs.some(spec => spec.domain !== undefined && (!Array.isArray(spec.domain)
              || !spec.domain.length || spec.domain.some(unit => ![1, 2, 3].includes(unit))))) return null;
        return (values.length ? values : [1, 2, 3]).filter(unit => domains.every(domain => domain.includes(unit)));
      };
      let choices = [new Map()], reason = null;
      for (const id of ids) {
        const units = options(id);
        if (!units?.length) { reason = `No legal finite domain for coefficient parameter ${id}`; break; }
        if (choices.length * units.length > 256) { reason = "Candidate coefficient domain exceeds the finite display limit"; break; }
        choices = choices.flatMap(choice => units.map(unit => new Map([...choice, [id, unit]])));
      }
      const variants = [];
      if (!reason) for (const choice of choices) {
        const coefficient = coefficientState(diff, choice);
        if (!coefficient.resolved) { reason ||= coefficient.reason; continue; }
        if ([...new Set(relations.map(c => c.page))].some(page => constraintFailures(page, choice).length)
            || linkedSources.some(source => sourceConstraintConflict(source, diff.page, choice))) continue;
        variants.push({coefficient, assignments: Object.fromEntries(choice), ...endpoints(diff, coefficient)});
      }
      const result = {variants, conditional: !original.resolved,
        reason: reason || (!variants.length ? "No jointly compatible coefficient choices" : null)};
      candidateCoefficients.set(diff, result);
      return result;
    };
    const candidateEndpoint = (node, grade, two, j) => {
      if (vectors) {
        const line = vectors.endpoint(node, grade, two, j);
        return line.live && !Object.values(line.sparse).some(Boolean) ? {...line, live: false, zero: true} : line;
      }
      const c = component(node), port = portKey(c.two + two, c.j + j), key = cellKey(node, grade);
      const live = Boolean(cells.get(key)?.has(port));
      return {live, zero: !live, key, port, sparse: live ? {[`${key}:${port}`]: 1} : {}};
    };
    const zeroSpan = grade => {
      const key = `${modulo(grade.stem, 64)}:${grade.filtration}`;
      if (zeroSpans.has(key)) return zeroSpans.get(key);
      const rows = [];
      for (const arrow of arrows) {
        if (!arrow.diff.zero || arrow.diff.page !== ws.page || !accepted(arrow.diff)
            || !coefficientState(arrow.diff).resolved || arrow.sourceGrade.filtration !== grade.filtration
            || modulo(arrow.sourceGrade.stem, 64) !== modulo(grade.stem, 64)) continue;
        for (let two = 0; two < 4; two++) for (let j = 0; j < 2; j++) {
          if (!allowsConstraintBranch(arrow.diff, two, j)) continue;
          const line = candidateEndpoint(arrow.source, grade, two, j);
          if (line.live && !line.unknown) rows.push({id: arrow.diff.id, sparse: line.sparse});
        }
      }
      const keys = [...new Set(rows.flatMap(row => Object.keys(row.sparse)))].sort();
      const basis = rows.map(row => keys.map(key => row.sparse[key] || 0));
      const result = {ids: [...new Set(rows.map(row => row.id))], covers(line) {
        return rows.length > 0 && Object.keys(line.sparse).every(key => keys.includes(key))
          && L.reduce(keys.map(key => line.sparse[key] || 0), basis).inSpan;
      }};
      zeroSpans.set(key, result);
      return result;
    };
    // This is a display query on the existing E_r quotient. It never admits a
    // review claim, assigns a coefficient, or applies an additional quotient.
    value.candidateState = (diff, sourceGrade, targetGrade) => {
      const fail = (code, message) => ({status: "unknown", conditional: !coefficientState(diff).resolved,
        variants: [], examined: [], reasons: [{code, message}]});
      if (diff.page !== ws.page) return fail("different-page", "Candidate is not on the current page");
      if (blockedFromPage !== null || !inTrustedDomain(sourceGrade) || !inTrustedDomain(targetGrade))
        return fail("unknown-quotient", "The current endpoint quotient is not known");
      const pair = matrixEndpoints(diff), typed = node => node?.style?.e2_pattern || node?.style?.e2_components;
      if (!typed(pair.source) || !typed(pair.target)) return fail("untyped-endpoint", "Candidate query requires typed endpoints");
      if (diff.linear_map_id) {
        const matrix = linearMaps.get(diff.linear_map_id), basis = pair.target.style?.e2_basis_patterns;
        if (!matrix || matrix.archived || !basis || matrix.matrix.length !== basis.length
            || matrix.matrix.some(row => row.length !== (pair.source.coordinates || [1]).length))
          return fail("invalid-matrix", "Candidate matrix endpoints are unavailable");
      }
      if (!candidateStates.has(diff)) candidateStates.set(diff, new Map());
      const key = `${modulo(sourceGrade.stem, 64)}:${sourceGrade.filtration}:${modulo(targetGrade.stem, 64)}:${targetGrade.filtration}`;
      const cache = candidateStates.get(diff);
      if (cache.has(key)) return cache.get(key);
      const candidates = candidateVariants(diff);
      if (candidates.reason) return fail("coefficient-domain", candidates.reason);
      const variants = [], examined = [], reasons = [], zero = zeroSpan(sourceGrade);
      let hasContradiction = false, hasUnknown = false, everyZero = true;
      for (const variant of candidates.variants) {
        const components = variant.target.style?.e2_components;
        const explicitlyZero = diff.zero || variant.coefficient.zeroEulerImage
          || (components ? Object.values(components).every(unit => L.scalar(unit) === 0) : variant.coefficient.value === 0);
        const maps = [], covered = [], seen = new Set();
        let unknown = false;
        if (!explicitlyZero) {
          everyZero = false;
          for (let two = 0; two < 4; two++) for (let j = 0; j < 2; j++) {
            if (!allowsConstraintBranch(scopedDifferential(diff), two, j)) continue;
            const from = candidateEndpoint(variant.source, sourceGrade, two, j);
            const to = candidateEndpoint(variant.target, targetGrade, two, j);
            const branchKey = JSON.stringify([from.sparse, to.sparse]);
            if (seen.has(branchKey)) continue;
            seen.add(branchKey);
            if (from.unknown || to.unknown) { unknown = true; continue; }
            if (!from.live || !to.live) continue;
            const branch = {from, to, two, j};
            if (zero.covers(from)) covered.push(branch);
            else maps.push(branch);
          }
        }
        const status = maps.length ? "possible" : unknown ? "unknown" : covered.length ? "contradicted"
          : explicitlyZero ? "zero" : "absent";
        examined.push({assignments: variant.assignments, coefficient: variant.coefficient, status,
          contradictedPorts: covered.map(({two, j}) => ({two, j})), certificateIds: covered.length ? zero.ids : []});
        if (maps.length) variants.push({...variant, maps});
        hasContradiction ||= covered.length > 0;
        hasUnknown ||= unknown;
      }
      const status = variants.length ? "possible" : hasUnknown ? "unknown" : hasContradiction ? "contradicted"
        : everyZero ? "zero" : "absent";
      if (hasContradiction) reasons.push({code: "verified-outgoing-zero", certificateIds: zero.ids,
        message: "Verified zero-outgoing certificates cover these actual source ports"});
      if (hasUnknown) reasons.push({code: "unknown-endpoint", message: "An endpoint has an unresolved quotient branch"});
      if (status === "absent") reasons.push({code: "absent-endpoint", message: "No nonzero branch has both endpoint ports present"});
      const result = {status, conditional: candidates.conditional, variants, examined, reasons};
      cache.set(key, result);
      return result;
    };
    caches.set(ws, {signature, value});
    return value;
  }
  root.HFPSSPageAlgebra = {compute, cellKey, seedPorts, component, allowsConstraintBranch};
})(typeof window !== "undefined" ? window : globalThis);
