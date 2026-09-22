// Exercise the actual chart functions without a browser or a second implementation.
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const script = fs.readFileSync('backend/static/app.js', 'utf8');
const context = vm.createContext({document: {body: {dataset: {}}}, window: {}});
vm.runInContext(fs.readFileSync('backend/static/graded-quotient.js', 'utf8'), context);
vm.runInContext(fs.readFileSync('backend/static/vector-page-algebra.js', 'utf8'), context);
vm.runInContext(fs.readFileSync('backend/static/page-algebra.js', 'utf8'), context);
vm.runInContext(script.slice(0, script.lastIndexOf('if (PAGE_MODE === "reviewing")')), context);
context.input = input;
const output = vm.runInContext(`
state.project = input.project;
const defaultBounds = input.bounds || {stemMin: -64, stemMax: 127, filtrationMin: 0, filtrationMax: 64};
input.workspaces.map(id => {
  const ws = state.project.workspaces.find(w => w.id === id);
  const bounds = input.boundsByWorkspace?.[id] || defaultBounds;
  return {id, pages: input.pages.map(page => {
    ws.page = page;
    const classes = new Map(ws.classes.map(c => [c.id, c]));
    const dead = deadE2OccurrenceKeys(ws, bounds, page);
    const points = periodicClassInstances(ws, bounds);
    const edges = periodicDifferentials(ws, bounds);
    const algebra = pageAlgebra(ws, bounds);
    const probes = (input.probes || []).map(probe => ({...probe,
      ports: [...(algebra?.ports({style:{e2_pattern:probe.pattern}}, {stem:probe.stem,filtration:probe.filtration}) || [])]}));
    for (const probe of probes) probe.glyph = quotientGlyph({modulePorts:probe.ports});
    const vectorProbes = (input.vectorProbes || []).map(probe => {
      const node = {style:{e2_components:probe.components}};
      // Scalar-column probes use the same dual pattern/component metadata
      // as real chart nodes. A components-only record denotes a coupled
      // vector, not an untyped scalar cell.
      const terms = Object.entries(probe.components);
      if (terms.length === 1 && terms[0][1] === 1) node.style.e2_pattern = terms[0][0];
      const grade = {stem:probe.stem,filtration:probe.filtration};
      const slots = algebra?.endpointSlots(node,grade) || [];
      return {...probe,live:algebra?.live(node,grade),slots,
        displayed:points.filter(p=>p.grade.stem===grade.stem && p.grade.filtration===grade.filtration)
          .map(p=>({label:p.item.label,pattern:p.item.style.e2_pattern,components:p.item.style.e2_components,ports:p.modulePorts}))};
    });
    let unmappedHigh;
    if (input.auditNoClipping && page >= 22) {
      const saved = ws.differentials;
      ws.differentials = [];
      unmappedHigh = periodicClassInstances(ws, bounds).filter(p => p.grade.filtration >= 23).length;
      ws.differentials = saved;
    }
    const dangling = edges.filter(e => dead.has(e2OccurrenceKey(classes.get(e.diff.source_id), e.sourceGrade))
      || dead.has(e2OccurrenceKey(classes.get(e.diff.target_id), e.targetGrade)));
    const highPatterns = {};
    for (const point of points.filter(p => p.grade.filtration >= 23)) {
      const key = point.item.style?.e2_pattern || point.item.id;
      highPatterns[key] ||= [];
      if (highPatterns[key].length < 8) highPatterns[key].push({grade:point.grade, ports:point.modulePorts,label:point.item.label});
    }
    return {page, points: points.length, edges: edges.length, highPatterns, probes, vectorProbes, unmappedHigh,
      ...(input.vectorAudit ? {conflicts:algebra?.conflicts || [], blockedFromPage:algebra?.blockedFromPage,
        blocks:[...(algebra?.vectorBlocks?.values() || [])].map(b=>({id:b.id,rank:b.q.dimension,barriers:b.barriers.length}))}:{}),
      high: points.filter(p => p.grade.filtration >= 23).length,
      rows: [...new Set(edges.map(e => e.diff.id))],
      ...(input.tableOccurrenceAudit ? {tableOccurrences: edges
        .filter(e => e.diff.id.startsWith('published_diff_'))
        .map(e => ({id:e.diff.id,source:e.sourceGrade,target:e.targetGrade}))} : {}),
      dangling: dangling.map(e => ({id:e.diff.id, source:e.sourceGrade, target:e.targetGrade})).slice(0,12),
      anchors: ws.differentials.filter(d => d.page === page).map(d => ({id:d.id,
        source:classes.get(d.source_id)?.label,
        sourceDead:dead.has(e2OccurrenceKey(classes.get(d.source_id), classes.get(d.source_id).grade)),
        targetDead:dead.has(e2OccurrenceKey(classes.get(d.target_id), classes.get(d.target_id).grade))}))};
  })};
})`, context);
process.stdout.write(JSON.stringify(output));
