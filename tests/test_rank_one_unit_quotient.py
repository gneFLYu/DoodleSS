"""An isolated finite isomorphism determines its quotient, not its F4 unit."""
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def audit():
    script = r"""
const fs = require('node:fs'), vm = require('node:vm');
const context = vm.createContext({window: {}});
for (const name of ['graded-quotient', 'vector-page-algebra', 'page-algebra'])
  vm.runInContext(fs.readFileSync(`backend/static/${name}.js`, 'utf8'), context);
const result = vm.runInContext(`
const clone = value => JSON.parse(JSON.stringify(value));
const node = (id, pattern, stem, filtration, style = {}) => ({id, label: id, page: 2,
  grade: {stem, filtration}, style: {e2_pattern: pattern, ...style}});
const row = (id, source, target, page = 17, status = 'review') => ({id,
  source_id: source, target_id: target, page, status, period_stem: 64});
function make(shift = 0, reflected = false) {
  return {id: 'mixed-' + shift + '-' + reflected, page: 17,
    classes: [node('source', 'S02', 26 + shift, 2), node('target', 'S73', 25 + shift, 19)],
    differentials: [{...row('lambda', 'source', 'target', 17, 'verified'), proposition_id: 'proof'}],
    propositions: [{id: 'proof', kind: 'differential', status: 'verified', conclusion: {
      fact_id: 'DER-MIX-D17-V-D3', coefficient_scope: 'exact-port',
      coefficient_parameter: {id: 'mixed_d17_VD3', symbol: '\\\\lambda_{17}',
        domain: [1, 2, 3], value: null, frobenius_power: Number(reflected)},
      rank_one_unit_certificate: {status: 'verified', kind: 'isolated-finite-F4-isomorphism',
        page: 17, source_pattern: 'S02', target_pattern: 'S73', coefficient_scope: 'exact-port'}
    }}], settings: {rendering: {}}, differential_maps: [], cells: []};
}
const bounds = {stemMin: -64, stemMax: 128, filtrationMin: 0, filtrationMax: 28};
const periods = [{stem: 64, filtration: 0}, {stem: 20, filtration: 4}];
const helpers = {accepted: item => ['verified','admitted'].includes(item.status),
  classPeriods: () => periods, diffPeriods: () => periods,
  copies(grade, rules, bounds) {
    const result = [];
    for (let g = 0; grade.filtration + 4*g <= bounds.filtrationMax; g++) {
      const filtration = grade.filtration + 4*g;
      if (filtration < bounds.filtrationMin) continue;
      const stem = grade.stem + 20*g;
      const lo = Math.ceil((bounds.stemMin - stem)/64), hi = Math.floor((bounds.stemMax - stem)/64);
      for (let d = lo; d <= hi; d++) result.push({grade: {...grade, stem: stem + d*64, filtration}});
    }
    return result;
  }};
function inspect(ws, page = 17) {
  ws.page = page;
  const before = JSON.stringify(ws), algebra = window.HFPSSPageAlgebra.compute(ws, bounds, helpers);
  const diff = ws.differentials[0], source = ws.classes[0], target = ws.classes[1];
  const probes = [[0,0],[64,0],[-64,0],[20,4],[40,8]].map(([s,f]) => {
    const sg = {...source.grade, stem: source.grade.stem+s, filtration: source.grade.filtration+f};
    const tg = {...target.grade, stem: target.grade.stem+s, filtration: target.grade.filtration+f};
    const candidate = page === 17 ? algebra.candidateState(diff, sg, tg) : null;
    return {source: algebra.live(source, sg), target: algebra.live(target, tg),
      candidate: candidate && {status: candidate.status, conditional: candidate.conditional,
        values: candidate.variants.map(v => [v.assignments.mixed_d17_VD3, v.coefficient.value]),
        ports: candidate.variants.flatMap(v => v.maps.map(m => [m.two,m.j]))}};
  });
  return {page, probes, coefficient: algebra.coefficientState(diff), canApply: algebra.canApply(diff),
    invariant: algebra.unitInvariant(diff), blocked: algebra.blockedFromPage, conflicts: algebra.conflicts,
    assignments: ws.settings.coefficient_assignments || null,
    parameter: clone(ws.propositions[0].conclusion.coefficient_parameter),
    unchanged: before === JSON.stringify(ws)};
}
const positive = [];
for (const shift of [-16,0,16]) for (const reflected of [false,true]) {
  const ws = make(shift, reflected);
  positive.push({shift, reflected, pages: [16,17,18,24].map(page => inspect(ws, page))});
}
const fixed = [1,2,3].map(unit => {
  const ws = make(); ws.propositions[0].conclusion.coefficient_parameter.value = unit;
  return {unit, result: inspect(ws,18)};
});
const rejected = {};
for (const kind of ['review-row','review-claim','wrong-claim-kind','wrong-degree','missing-certificate','review-certificate','wrong-kind',
  'wrong-page','wrong-pattern','wrong-scope','missing-scope','source-two','source-j','witt',
  'series','components','basis','matrix','implicit-block','condition','affine','inverse','linked',
  'bad-domain','bad-frobenius','conflicting-assignment','shared-declaration','shared-constraint',
  'shared-target','shared-source','d8-collision','g-collision']) {
  const ws = make(), proof = ws.propositions[0], meta = proof.conclusion,
    spec = meta.coefficient_parameter, certificate = meta.rank_one_unit_certificate;
  if (kind === 'review-row') ws.differentials[0].status = 'review';
  if (kind === 'review-claim') proof.status = 'review';
  if (kind === 'wrong-claim-kind') proof.kind = 'permanent-cycle';
  if (kind === 'wrong-degree') ws.classes[1].grade.stem++;
  if (kind === 'missing-certificate') delete meta.rank_one_unit_certificate;
  if (kind === 'review-certificate') certificate.status = 'review';
  if (kind === 'wrong-kind') certificate.kind = 'rank-one';
  if (kind === 'wrong-page') certificate.page = 19;
  if (kind === 'wrong-pattern') certificate.source_pattern = 'S62';
  if (kind === 'wrong-scope') certificate.coefficient_scope = 'all-multiples';
  if (kind === 'missing-scope') delete meta.coefficient_scope;
  if (kind === 'source-two') ws.classes[0].style.two_valuation = 1;
  if (kind === 'source-j') ws.classes[0].style.j_order = 1;
  if (['witt','series'].includes(kind)) {
    certificate.source_pattern = ws.classes[0].style.e2_pattern = kind === 'witt' ? 'I00' : 'S11';
  }
  if (kind === 'components') ws.classes[0].style.e2_components = {S02:1};
  if (kind === 'basis') ws.classes[0].style.e2_basis_patterns = ['S02'];
  if (kind === 'matrix') {
    ws.differentials[0].linear_map_id = 'matrix';
    ws.classes[1].style.e2_basis_patterns = ['S73'];
    ws.differential_maps.push({id:'matrix',status:'verified',matrix:[[1]]});
  }
  if (kind === 'implicit-block') ws.classes.push(node('sum','S02',26,2,{e2_components:{S02:1,B:1}}));
  if (kind === 'condition') meta.coefficient_condition = null;
  if (kind === 'affine') spec.affine_offset = 1;
  if (kind === 'inverse') spec.inverse_parameter_id = spec.id;
  if (kind === 'linked') spec.source_parameter = {workspace_id:'absent'};
  if (kind === 'bad-domain') spec.domain = [0,1,2,3];
  if (kind === 'bad-frobenius') spec.frobenius_power = 9;
  if (kind === 'conflicting-assignment') {spec.value=1; ws.settings.coefficient_assignments = {[spec.id]:2};}
  if (kind === 'shared-declaration') ws.propositions.push({id:'other',conclusion:{coefficient_parameter:clone(spec)}});
  if (kind === 'shared-constraint') meta.coefficient_constraints = [{id:'coupled',kind:'equal-nonzero-parameters',
    page:17,parameter_ids:[spec.id,'other']}];
  if (kind === 'shared-target') {
    ws.classes.push(node('other','B',26,2));
    ws.differentials.push(row('other','other','target'));
  }
  if (kind === 'shared-source') {
    ws.classes.push(node('other','B',25,19));
    ws.differentials.push(row('other','source','other'));
  }
  if (['d8-collision','g-collision'].includes(kind)) {
    const [s,f] = kind === 'd8-collision' ? [64,0] : [20,4];
    ws.classes.push(node('alias','S02',26+s,2+f), node('other','B',25+s,19+f));
    ws.differentials.push(row('other','alias','other'));
  }
  rejected[kind] = [inspect(ws,17),inspect(ws,18)];
}
const cycles = {};
for (const [kind,source,page,status] of [['source','source',17,'verified'],
  ['target','target',17,'verified'],['earlier','source',11,'verified'],['review','source',17,'review']]) {
  const ws = make();
  ws.propositions.push({id:'zero',kind:'zero-differential',status,conclusion:{source_id:source,
    page,period_stem:64,zero:true,coefficient_scope:'exact-port',cycle_constraint:'outgoing-only'}});
  cycles[kind] = [inspect(ws,17),inspect(ws,18)];
}
const absent = {};
for (const kind of ['source','target']) {
  const ws = make(), target = ws.classes[kind === 'source' ? 0 : 1], page = kind === 'source' ? 2 : 3;
  ws.classes.push(node('earlier','A',target.grade.stem+1,target.grade.filtration-page));
  ws.differentials.push(row('earlier','earlier',kind,page,'verified'));
  absent[kind] = inspect(ws,17);
}
const cacheWs = make(), cache = [inspect(cacheWs,18)];
cacheWs.propositions[0].conclusion.rank_one_unit_certificate.status = 'review'; cache.push(inspect(cacheWs,18));
cacheWs.propositions[0].conclusion.rank_one_unit_certificate.status = 'verified'; cache.push(inspect(cacheWs,18));
delete cacheWs.propositions[0].conclusion.coefficient_scope; cache.push(inspect(cacheWs,18));
cacheWs.propositions[0].conclusion.coefficient_scope = 'exact-port'; cache.push(inspect(cacheWs,18));
const diagonal = [1,2,3].map(unit => ({unit, kernel: window.HFPSSGradedQuotient.partialMap({
  sourceDimension:2, targetDimension:1,
  constraints:[{id:'A',source:[1,0],target:[unit]},{id:'B',source:[0,1],target:[1]}]
}).knownKernelBasis}));
({positive,fixed,rejected,cycles,absent,cache,diagonal});
`, context);
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, text=True,
                               encoding="utf-8", capture_output=True, check=True, timeout=30)
    return json.loads(completed.stdout)


def test_six_transport_settings_keep_nonzero_unit_unknown_and_take_same_quotient(audit):
    for image in audit["positive"]:
        for row in image["pages"]:
            assert row["unchanged"] and row["assignments"] is None
            assert row["coefficient"]["resolved"] is False and "value" not in row["coefficient"]
            assert row["parameter"]["value"] is None and row["parameter"]["domain"] == [1, 2, 3]
            assert row["parameter"]["frobenius_power"] == int(image["reflected"])
            assert row["blocked"] is None and row["conflicts"] == []
            assert row["invariant"] == row["canApply"] == (row["page"] >= 17)
            for probe in row["probes"]:
                assert probe["source"] == probe["target"] == (row["page"] <= 17)
                if row["page"] != 17:
                    continue
                candidate = probe["candidate"]
                assert candidate["status"] == "possible" and candidate["conditional"]
                assert candidate["values"] == ([[1, 1], [2, 3], [3, 2]] if image["reflected"]
                                                   else [[1, 1], [2, 2], [3, 3]])
                assert candidate["ports"] == [[0, 0]] * 3


def test_quotient_matches_every_actual_unit_without_assigning_one(audit):
    reference = audit["positive"][0]["pages"][2]["probes"]
    for item in audit["fixed"]:
        row = item["result"]
        assert row["canApply"] and not row["invariant"]
        assert row["coefficient"]["resolved"] and row["coefficient"]["value"] == item["unit"]
        assert row["probes"] == reference


@pytest.mark.parametrize("kind", [
    "review-row", "review-claim", "wrong-claim-kind", "wrong-degree", "missing-certificate", "review-certificate", "wrong-kind",
    "wrong-page", "wrong-pattern", "wrong-scope", "missing-scope", "source-two", "source-j",
    "witt", "series", "components", "basis", "matrix", "implicit-block", "condition", "affine",
    "inverse", "linked", "bad-domain", "bad-frobenius", "conflicting-assignment", "shared-declaration",
    "shared-constraint", "shared-target", "shared-source", "d8-collision", "g-collision",
])
def test_nonisolated_or_unverified_cases_do_not_use_representative_unit(audit, kind):
    current, following = audit["rejected"][kind]
    assert not current["invariant"] and not following["invariant"]
    assert not current["canApply"] and not following["canApply"]
    assert current["unchanged"] and following["unchanged"]
    if kind == "review-row":
        assert following["blocked"] is None
        assert all(p["source"] and p["target"] for p in following["probes"])
    else:
        assert following["blocked"] == 17


def test_zero_outgoing_constraint_still_contradicts_certified_nonzero_map(audit):
    for row in audit["cycles"]["source"]:
        assert row["blocked"] == 17 and not row["canApply"] and not row["invariant"]
        assert any("zero-outgoing" in conflict["reason"] for conflict in row["conflicts"])
        assert all(p["source"] and p["target"] for p in row["probes"])
    for kind in ("target", "earlier", "review"):
        for row in audit["cycles"][kind]:
            assert row["blocked"] is None and row["conflicts"] == []
            assert row["canApply"] and row["invariant"]


def test_shared_target_counterexample_really_has_a_unit_dependent_diagonal_kernel(audit):
    multiplication = ((0, 0, 0, 0), (0, 1, 2, 3), (0, 2, 3, 1), (0, 3, 1, 2))
    assert len({json.dumps(row["kernel"]) for row in audit["diagonal"]}) == 3
    for row in audit["diagonal"]:
        assert len(row["kernel"]) == 1
        a, b = row["kernel"][0]
        assert a and b and multiplication[row["unit"]][a] ^ b == 0
    assert all(not row["canApply"] for row in audit["rejected"]["shared-target"])


def test_an_earlier_boundary_cannot_be_a_nonzero_source_or_target(audit):
    for row in audit["absent"].values():
        assert row["blocked"] == 17
        assert not row["canApply"] and not row["invariant"]
        assert row["conflicts"]


def test_scope_and_certificate_edits_invalidate_the_page_quotient_cache(audit):
    for index, row in enumerate(audit["cache"]):
        valid = index % 2 == 0
        assert row["canApply"] == row["invariant"] == valid
        assert row["blocked"] == (None if valid else 17)
        assert all(p["source"] == p["target"] == (not valid) for p in row["probes"])


def test_runtime_static_copies_remain_identical():
    assert (ROOT / "backend/static/page-algebra.js").read_bytes() == (ROOT / "public/static/page-algebra.js").read_bytes()
