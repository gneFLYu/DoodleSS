/* A reversible presentation of the already computed E_r, never a new quotient.
 * Prefer known incoming directions. Other equations retain exact coordinates;
 * a sum is not an unweighted midpoint of dots or an additional basis vector.
 */
(function (root) {
  "use strict";
  const nonzero = values => values.some(Boolean);
  function create(algebra, occurrences, bounds) {
    const L = root.HFPSSGradedQuotient, B = root.HFPSSDisplayBasis;
    if (!L || !B || !algebra?.vectorBlocks || algebra.blockedFromPage != null) return null;
    const blocks = algebra.vectorBlocks, lookup = new Map(), preferred = new Map(), plans = new Map();
    for (const block of blocks.values()) {
      const [, stem, filtration] = block.id.split(":");
      for (const token of block.tokens) lookup.set(`${token.split(":")[0]}:${stem}:${filtration}`, block);
    }
    const components = node => node?.style?.e2_components
      || (node?.style?.e2_pattern ? {[node.style.e2_pattern]: 1} : {});
    function raw(node, grade, two = 0, j = 0) {
      const ps = components(node), residue = ((grade.stem % 64) + 64) % 64;
      const block = lookup.get(`${Object.keys(ps)[0]}:${residue}:${grade.filtration}`);
      if (!block || !algebra.inTrustedDomain(grade)) return null;
      const port = `${Number(node.style?.two_valuation || 0) + two}:${Number(node.style?.j_order || 0) + j > 0 ? 1 : 0}`;
      const vector = block.tokens.map(token => {
        const at = token.indexOf(":");
        return token.slice(at + 1) === port ? L.scalar(ps[token.slice(0, at)] || 0) : 0;
      });
      const projected = block.q.tryProject(vector);
      if (!projected.inCycles || !nonzero(projected.coordinates)) return {block, live: false, port};
      let uncertain = false;
      for (const barrier of block.barriers) {
        const old = barrier.q.tryProject(vector);
        if (!old.inCycles) continue;
        const value = barrier.map.evaluate(old.coordinates);
        if (value.defined && nonzero(value.value)) return {block, live: false, port};
        uncertain ||= !value.defined;
      }
      return {block, live: true, port, coordinates: projected.coordinates, uncertain};
    }
    // Choose from actual, resolved equations only; a possible b branch is not
    // a choice of b. Sorting makes the selection independent of drawing order.
    for (const edge of [...occurrences].sort((a, b) => a.diff.id.localeCompare(b.diff.id))) {
      if (!edge.sourceNode || !edge.targetNode || !edge.sourceGrade || !edge.targetGrade
          || !algebra.inTrustedDomain(edge.sourceGrade) || !algebra.inTrustedDomain(edge.targetGrade)
          || edge.candidate?.conditional || !algebra.canApply(edge.diff)
          || !algebra.coefficientState(edge.diff).resolved) continue;
      for (const branch of algebra.maps(edge.sourceNode, edge.targetNode, edge.sourceGrade, edge.targetGrade)) {
        const two = branch.two || 0, j = branch.j || 0;
        if (!root.HFPSSPageAlgebra?.allowsConstraintBranch(edge.diff, two, j)) continue;
        const to = raw(edge.targetNode, edge.targetGrade, two, j);
        if (!to?.live || to.uncertain
            || to.coordinates.filter(Boolean).length < 2) continue;
        if (!preferred.has(to.block.id)) preferred.set(to.block.id, new Map());
        preferred.get(to.block.id).set(to.coordinates.join(":"), to.coordinates);
      }
    }
    for (const block of blocks.values()) {
      const rows = [...(preferred.get(block.id)?.values() || [])];
      plans.set(block.id, {basis: B.create(block.q.dimension, rows), adapted: rows.length > 0});
    }
    const slot = (block, index, grade) => `display:${block.id}:${index}:${grade.stem}`;
    const terms = (block, vector) => vector.flatMap((coefficient, i) => {
      if (!coefficient) return [];
      const [pattern, two, j] = block.tokens[i].split(":");
      return [{pattern, two: Number(two), j: Number(j), coefficient}];
    });
    function endpoint(node, grade, two = 0, j = 0) {
      const line = raw(node, grade, two, j);
      if (!line?.live) return line;
      const plan = plans.get(line.block.id), coordinates = plan.basis.project(line.coordinates);
      const entries = coordinates.flatMap((coefficient, i) => coefficient
        ? [{slot: slot(line.block, i, grade), coefficient}] : []);
      return {...line, coordinates, entries, adapted: plan.adapted,
        key: `${line.block.id}:${grade.stem}:${coordinates.join(":")}`,
        terms: terms(line.block, line.block.q.lift(line.coordinates)),
        basisRows: plan.basis.rows};
    }
    function owned(node, grade) {
      const first = raw(node, grade);
      if (!first) return null;
      const matches = [];
      for (let two = 0; two < 4; two++) for (let j = 0; j < 2; j++) {
        const line = endpoint(node, grade, two, j);
        if (line?.live && line.entries.length === 1 && line.entries[0].coefficient === 1
            && !matches.some(m => m.slot === line.entries[0].slot))
          matches.push({slot: line.entries[0].slot, port: line.port});
      }
      return matches;
    }
    return {
      endpoint,
      ports(node, grade) { const lines = owned(node, grade); return lines ? new Set(lines.map(l => l.port)) : algebra.ports(node, grade); },
      displaySlots(node, grade) { return owned(node, grade)?.map(l => l.slot) || algebra.displaySlots(node, grade); },
      representatives(view) {
        const output = [];
        for (const block of blocks.values()) {
          const [, residueText, filtrationText] = block.id.split(":"), residue = Number(residueText), filtration = Number(filtrationText);
          if (filtration < view.filtrationMin || filtration > view.filtrationMax) continue;
          const plan = plans.get(block.id);
          plan.basis.rows.forEach((row, index) => {
            const vector = block.q.lift(row);
            let uncertain = false;
            for (const barrier of block.barriers) {
              const old = barrier.q.tryProject(vector);
              if (!old.inCycles) continue;
              const value = barrier.map.evaluate(old.coordinates);
              if (value.defined && nonzero(value.value)) return;
              uncertain ||= !value.defined;
            }
            for (let stem = residue + 64 * Math.ceil((view.stemMin - residue) / 64); stem <= view.stemMax; stem += 64) {
              const grade = {stem, filtration};
              output.push({slot: slot(block, index, grade), grade, terms: terms(block, vector), uncertain,
                displayBasis: {row: row.slice(), rows: plan.basis.rows, adapted: plan.adapted}});
            }
          });
        }
        return output;
      },
    };
  }
  root.HFPSSChartPresentation = {create};
})(typeof window !== "undefined" ? window : globalThis);
