/* Coupled finite-field columns inside the enumerated E2 patterns.
 * Scalar Witt levels remain separate ports. An equation on A+B is never
 * silently extended by declaring d(A) or d(B) to be zero.
 */
(function (root) {
  "use strict";
  const mod = n => ((n % 64) + 64) % 64;
  const nonzero = v => v.some(Boolean);
  const patterns = node => node?.style?.e2_components
    || (node?.style?.e2_pattern ? {[node.style.e2_pattern]: 1} : {});

  function create(ws, cells, conflicts, trustedDomain = {filtrationMin: 0, filtrationMax: Infinity}) {
    const L = root.HFPSSGradedQuotient;
    if (!L) return null;
    const parent = new Map();
    const find = p => parent.has(p) && parent.get(p) !== p ? find(parent.get(p)) : p;
    const join = keys => { for (const p of keys) parent.set(find(p), find(keys[0])); };
    for (const node of ws.classes.filter(n => !n.archived)) {
      join(Object.keys(node.style?.e2_components || {}));
    }
    // A matrix can produce a coupled vector even when the saved target only
    // names one column. Use its explicitly declared basis, but do not infer a
    // family from an unused basis field or an invalid/archived matrix.
    const nodes = new Map(ws.classes.map(node => [node.id, node]));
    const matrices = new Map((ws.differential_maps || []).map(matrix => [matrix.id, matrix]));
    for (const diff of ws.differentials || []) {
      const matrix = matrices.get(diff.linear_map_id), source = nodes.get(diff.source_id), target = nodes.get(diff.target_id);
      const basis = target?.style?.e2_basis_patterns, coordinates = source?.coordinates || [1];
      if (diff.archived || !matrix || matrix.archived || !source || source.archived || !target || target.archived
          || !Array.isArray(basis) || basis.length < 2 || new Set(basis).size !== basis.length
          || basis.some(pattern => typeof pattern !== "string" || !/^[A-Za-z][A-Za-z0-9_-]*$/.test(pattern))
          || !Array.isArray(coordinates) || !coordinates.length || !Array.isArray(matrix.matrix)
          || matrix.matrix.length !== basis.length
          || matrix.matrix.some(row => !Array.isArray(row) || row.length !== coordinates.length)) continue;
      try {
        coordinates.forEach(unit => L.scalar(unit));
        matrix.matrix.forEach(row => row.forEach(unit => L.scalar(unit)));
      } catch (_) { continue; }
      join(basis);
    }
    const families = new Map();
    for (const p of parent.keys()) {
      const key = find(p);
      if (!families.has(key)) families.set(key, []);
      families.get(key).push(p);
    }
    const familyFor = new Map();
    for (const members of families.values()) if (members.length > 1) {
      members.sort();
      for (const p of members) familyFor.set(p, members);
    }
    const blocks = new Map();
    for (const key of cells.keys()) {
      const [pattern, stem, filtration] = key.split(":");
      const members = familyFor.get(pattern);
      if (!members) continue;
      const id = `${members.join("+")}:${stem}:${filtration}`;
      if (blocks.has(id)) continue;
      const tokens = members.flatMap(p => [...(cells.get(`${p}:${stem}:${filtration}`) || [])].map(port => `${p}:${port}`));
      const identity = tokens.map((_, i) => tokens.map((_, j) => Number(i === j)));
      blocks.set(id, {id, tokens, barriers: [], q: L.quotient({ambientDimension: tokens.length, cycles: identity, boundaries: []})});
    }
    function blockFor(node, grade) {
      const members = familyFor.get(Object.keys(patterns(node))[0]);
      return members ? blocks.get(`${members.join("+")}:${mod(grade.stem)}:${grade.filtration}`) : null;
    }
    const port = (node, two, j) => `${Number(node.style?.two_valuation || 0) + two}:${Number(node.style?.j_order || 0) + j > 0 ? 1 : 0}`;
    function endpoint(node, grade, two = 0, j = 0) {
      if (!node) return {live: false, zero: true, sparse: {}};
      if (grade.filtration < trustedDomain.filtrationMin || grade.filtration > trustedDomain.filtrationMax) {
        return {live: false, zero: false, unknown: true, outsideDomain: true, sparse: {}};
      }
      const block = blockFor(node, grade), ps = patterns(node), p = port(node, two, j);
      if (!block) {
        const pattern = Object.keys(ps)[0], key = `${pattern}:${mod(grade.stem)}:${grade.filtration}`;
        const live = cells.get(key)?.has(p) || false;
        return {live, zero: !live, sparse: live ? {[`${key}:${p}`]: L.scalar(ps[pattern])} : {}, key, port: p};
      }
      const vector = block.tokens.map(token => {
        const separator = token.indexOf(":"), name = token.slice(0, separator);
        return token.slice(separator + 1) === p ? L.scalar(ps[name] || 0) : 0;
      });
      const projected = block.q.tryProject(vector);
      if (!projected.inCycles) return {block, vector, live: false, zero: false, noncycle: true, sparse: {}};
      let unknown = false;
      for (const barrier of block.barriers) {
        const previous = barrier.q.tryProject(vector);
        if (!previous.inCycles) continue;
        const value = barrier.map.evaluate(previous.coordinates);
        if (!value.defined) unknown = true;
        else if (nonzero(value.value)) return {block, vector, live: false, zero: false, noncycle: true, sparse: {}};
      }
      const live = nonzero(projected.coordinates);
      const sparse = Object.fromEntries(projected.coordinates.map((c, i) => [`${block.id}#${i}`, c]).filter(([, c]) => c));
      return {block, vector, coordinates: projected.coordinates, live, zero: !live, unknown, sparse};
    }
    function branches(source, target, sourceGrade, targetGrade, diff = null) {
      const result = [], seen = new Set();
      for (let two = 0; two < 4; two++) for (let j = 0; j < 2; j++) {
        if (!root.HFPSSPageAlgebra.allowsConstraintBranch(diff, two, j)) continue;
        const from = endpoint(source, sourceGrade, two, j), to = endpoint(target, targetGrade, two, j);
        const key = JSON.stringify([from.vector || from.sparse, to.vector || to.sparse]);
        if (seen.has(key)) continue;
        seen.add(key);
        result.push({from, to, two, j});
      }
      return result;
    }
    function process(page, arrows, accepted, {commit = true} = {}) {
      const pending = new Map(), scalarRemovals = [];
      const state = block => {
        if (!pending.has(block.id)) pending.set(block.id, {block, constraints: [], incoming: [], hasOutgoing: false});
        return pending.get(block.id);
      };
      for (const arrow of arrows.filter(a => a.diff.page === page && accepted(a.diff))) {
        const coupled = blockFor(arrow.source, arrow.sourceGrade) || blockFor(arrow.target, arrow.targetGrade);
        if (!coupled) continue;
        for (const {from, to} of branches(arrow.source, arrow.target, arrow.sourceGrade, arrow.targetGrade, arrow.diff)) {
          if (from.outsideDomain || to.outsideDomain) continue;
          if (from.noncycle || to.noncycle || from.unknown || to.unknown) {
            conflicts.push({id: arrow.diff.id, page, reason: "vector is not a known cycle on this page"});
            continue;
          }
          if (!from.live) continue;
          if (from.block) {
            const item = state(from.block);
            item.hasOutgoing = true;
            item.constraints.push({id: arrow.diff.id, source: from.coordinates, target: to.sparse});
          } else if (to.live) scalarRemovals.push([from.key, from.port]);
          if (to.live) {
            if (to.block) state(to.block).incoming.push(to.vector);
            else scalarRemovals.push([to.key, to.port]);
          }
        }
      }
      // Construct all maps on E_r first; apply kernels/images simultaneously.
      const updates = [];
      let inconsistent = false;
      for (const {block, constraints, incoming, hasOutgoing} of pending.values()) {
        let cycles = block.q.cycleBasis, nextBarrier = null;
        if (hasOutgoing) {
          for (const vector of incoming) constraints.push({id: "d_r^2=0", source: block.q.project(vector), target: {}});
          const codomain = [...new Set(constraints.flatMap(c => Object.keys(c.target)))].sort();
          const map = L.partialMap({sourceDimension: block.q.dimension, targetDimension: codomain.length,
            constraints: constraints.map(c => ({...c, target: codomain.map(k => c.target[k] || 0)}))});
          if (!map.consistent) {
            conflicts.push({page, block: block.id, reason: "inconsistent linear constraints or d_r^2 != 0", witnesses: map.conflicts});
            inconsistent = true;
            continue;
          }
          if (map.isTotal) cycles = [...block.q.boundaryBasis, ...map.knownKernelBasis.map(v => block.q.lift(v))];
          else {
            nextBarrier = {q: block.q, map};
            // The top r levels are discarded from the trustworthy domain
            // after this quotient. There, nonzero targets can be outside the
            // halo while target-free cycle certificates remain available;
            // that asymmetry is not a genuine underdetermined-map warning.
            const filtration = Number(block.id.split(":")[2]);
            if (commit && filtration + page <= trustedDomain.filtrationMax) {
              conflicts.push({page, block: block.id, reason: "outgoing map is only specified on a proper subspace", definedRank: map.domainDimension, rank: block.q.dimension});
            }
          }
        }
        try {
          const next = L.quotient({ambientDimension: block.tokens.length, cycles,
            boundaries: [...block.q.boundaryBasis, ...incoming]});
          updates.push({block, next, nextBarrier});
        } catch (error) { conflicts.push({page, block: block.id, reason: error.message}); inconsistent = true; }
      }
      // A contradictory claimed map cannot erase either endpoint.
      if (inconsistent) return false;
      if (!commit) return true;
      for (const {block, next, nextBarrier} of updates) {
        if (nextBarrier) block.barriers.push(nextBarrier);
        block.q = next;
      }
      for (const [key, p] of scalarRemovals) cells.get(key)?.delete(p);
      return true;
    }
    const proportional = (v, w) => {
      const first = w.findIndex(Boolean);
      if (first < 0 || !v[first]) return false;
      const scale = L.mul(v[first], L.inverse(w[first]));
      return v.every((c, i) => c === L.mul(scale, w[i]));
    };
    function owned(node, grade) {
      const block = blockFor(node, grade);
      if (!block) return null;
      const matches = [];
      for (let two = 0; two < 4; two++) for (let j = 0; j < 2; j++) {
        const line = endpoint(node, grade, two, j);
        if (!line.live) continue;
        const index = block.q.representatives.findIndex(v => proportional(line.vector, v));
        if (index >= 0 && !matches.some(m => m.index === index)) matches.push({index, port: port(node, two, j)});
      }
      return {block, matches};
    }
    return {
      blocks, blockFor, endpoint, process,
      validateKnownSources(page, arrows, accepted) {
        let consistent = true;
        for (const arrow of arrows.filter(a => a.diff.page === page && !a.diff.zero && accepted(a.diff))) {
          for (const {from, to, two, j} of branches(arrow.source, arrow.target, arrow.sourceGrade, arrow.targetGrade, arrow.diff)) {
            // Zero -> zero is a redundant product row. An unknown/outer-halo
            // endpoint is not evidence for a nonzero image or a contradiction.
            if (from.unknown || to.unknown || !to.live) continue;
            if (!from.noncycle && !from.zero) continue;
            conflicts.push({id: arrow.diff.id, page, source: arrow.sourceGrade, target: arrow.targetGrade,
              two, j, sourceState: from.noncycle ? "noncycle" : "zero",
              reason: "nonzero differential has a source that is zero or not a cycle on this page"});
            consistent = false;
          }
        }
        return consistent;
      },
      validateScalarCycles(page, arrows, accepted) {
        const zeros = new Map(), nonzeros = new Map();
        for (const arrow of arrows.filter(a => a.diff.page === page && accepted(a.diff))) {
          for (const {from, to} of branches(arrow.source, arrow.target, arrow.sourceGrade, arrow.targetGrade, arrow.diff)) {
            if (!from.live || from.block || from.unknown || to.unknown) continue;
            const key = `${from.key}:${from.port}`;
            if (arrow.diff.zero) zeros.set(key, arrow.diff.id);
            else if (to.live) nonzeros.set(key, arrow.diff.id);
          }
        }
        const overlap = [...zeros.keys()].filter(key => nonzeros.has(key));
        for (const key of overlap) conflicts.push({page, reason: "nonzero differential contradicts a zero-outgoing cycle constraint",
          port: key, cycle: zeros.get(key), differential: nonzeros.get(key)});
        return !overlap.length;
      },
      validateScalarChains(page, arrows, accepted) {
        const incoming = new Map(), outgoing = new Map();
        for (const arrow of arrows.filter(a => a.diff.page === page && accepted(a.diff))) {
          for (const {from, to} of branches(arrow.source, arrow.target, arrow.sourceGrade, arrow.targetGrade, arrow.diff)) {
            if (!from.live || !to.live || from.unknown || to.unknown) continue;
            if (!to.block) incoming.set(`${to.key}:${to.port}`, arrow.diff.id);
            if (!from.block) outgoing.set(`${from.key}:${from.port}`, arrow.diff.id);
          }
        }
        const overlap = [...incoming.keys()].filter(key => outgoing.has(key));
        for (const key of overlap) conflicts.push({page, reason: "d_r^2 != 0 through a scalar coefficient port",
          port: key, incoming: incoming.get(key), outgoing: outgoing.get(key)});
        return !overlap.length;
      },
      maps(source, target, a, b) { return branches(source, target, a, b).filter(p => p.from.live && p.to.live && !p.from.unknown && !p.to.unknown); },
      ports(node, grade) { const item = owned(node, grade); return item ? new Set(item.matches.map(m => m.port)) : null; },
      slots(node, grade) { const item = owned(node, grade); return item ? item.matches.map(m => `quotient:${item.block.id}:${m.index}:${grade.stem}`) : []; },
      endpointSlots(node, grade) {
        const line = endpoint(node, grade);
        return line.block && line.live ? line.coordinates.map((c, i) => c ? `quotient:${line.block.id}:${i}:${grade.stem}` : null).filter(Boolean) : [];
      },
      representatives(bounds) {
        const records = [];
        for (const block of blocks.values()) {
          const [, stemText, filtrationText] = block.id.split(":"), residue = Number(stemText), filtration = Number(filtrationText);
          if (filtration < bounds.filtrationMin || filtration > bounds.filtrationMax) continue;
          if (filtration < trustedDomain.filtrationMin || filtration > trustedDomain.filtrationMax) continue;
          for (let index = 0; index < block.q.representatives.length; index++) {
            const vector = block.q.representatives[index];
            let noncycle = false, uncertain = false;
            for (const barrier of block.barriers) {
              const old = barrier.q.tryProject(vector);
              if (!old.inCycles) continue;
              const value = barrier.map.evaluate(old.coordinates);
              noncycle ||= value.defined && nonzero(value.value);
              uncertain ||= !value.defined;
            }
            if (noncycle) continue;
            const terms = vector.flatMap((coefficient, i) => {
              if (!coefficient) return [];
              const [pattern, two, j] = block.tokens[i].split(":");
              return [{pattern, two: Number(two), j: Number(j), coefficient}];
            });
            for (let stem = residue + 64 * Math.ceil((bounds.stemMin - residue) / 64); stem <= bounds.stemMax; stem += 64) {
              records.push({slot: `quotient:${block.id}:${index}:${stem}`, grade: {stem, filtration}, terms, uncertain});
            }
          }
        }
        return records;
      },
    };
  }
  root.HFPSSVectorPageAlgebra = {create};
})(typeof window !== "undefined" ? window : globalThis);
