"""Read-only finite coefficient choices and current-page zero certificates."""
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def audit():
    script = r"""
const fs = require('node:fs'), vm = require('node:vm');
const context = vm.createContext({document: {body: {dataset: {}}}, window: {}});
for (const name of ['graded-quotient', 'vector-page-algebra', 'page-algebra'])
  vm.runInContext(fs.readFileSync(`backend/static/${name}.js`, 'utf8'), context);
const app = fs.readFileSync('backend/static/app.js', 'utf8');
vm.runInContext(app.slice(0, app.lastIndexOf('if (PAGE_MODE === "reviewing")')), context);
const output = vm.runInContext(`
const node = (id, stem, filtration, style) => ({id, label: id, page: 2, grade: {stem, filtration}, style});
const bounds = {stemMin: -1, stemMax: 65, filtrationMin: 0, filtrationMax: 28};
const parameter = (id, extra = {}) => ({id, domain: [1, 2, 3], value: null, frobenius_power: 0, ...extra});
const workspaceBase = (id, classes, differentials, propositions = []) => ({id, page: 23,
  classes, differentials, propositions, cells: [], differential_maps: [], fates: [],
  settings: {rendering: {enumerated_e2_pattern: 'integer', enumerated_horizontal_period: 64,
    period_lattice: [{stem: 64, filtration: 0, exponent_domain: 'integer'}]}}});
function coupled(extra = {}) {
  const target = node('target', 0, 26, {e2_components: {B: 1, C: 1}, e2_basis_patterns: ['B', 'C']});
  return workspaceBase('coupled', [node('early', 1, 23, {e2_pattern: 'A'}),
    node('source', 1, 3, {e2_pattern: 'X'}), target], [
    {id: 'early', source_id: 'early', target_id: 'target', page: 3, status: 'verified', period_stem: 64},
    {id: 'candidate', source_id: 'source', target_id: 'target', page: 23, status: 'review', period_stem: 64, proposition_id: 'claim'}
  ], [{id: 'claim', kind: 'differential', status: 'review', conclusion: {
    coefficient_parameter: parameter('b', {target_component: 'C', ...extra})}}]);
}
function inspect(ws, external = [], shift = 0) {
  state.project = {workspaces: [ws, ...external], period_families: [], page_period_cycles: []};
  state.workspaceId = ws.id;
  const model = JSON.stringify(state.project), algebra = pageAlgebra(ws, bounds);
  const d = ws.differentials.find(d => d.id === 'candidate'), pair = algebra.endpoints(d);
  const sg = {...pair.source.grade, stem: pair.source.grade.stem + shift};
  const tg = {...pair.target.grade, stem: pair.target.grade.stem + shift};
  const quotient = () => JSON.stringify({cells: [...algebra.cells].map(([k,v]) => [k,[...v]]),
    blocks: [...(algebra.vectorBlocks || [])].map(([k,b]) => [k,b.q.cycleBasis,b.q.boundaryBasis,b.barriers.length]),
    conflicts: algebra.conflicts, blocked: algebra.blockedFromPage});
  const before = quotient(), coefficient = JSON.stringify(algebra.coefficientState(d));
  const result = algebra.candidateState(d, sg, tg);
  const repeat = algebra.candidateState(d, sg, tg);
  return {status: result.status, conditional: result.conditional, reasons: result.reasons,
    examined: result.examined, variants: result.variants.map(v => ({coefficient: v.coefficient,
      assignments: v.assignments, target: v.target.style.e2_components,
      maps: v.maps.map(m => ({two: m.two, j: m.j, sourceKnown: m.from.live && !m.from.unknown,
        targetKnown: m.to.live && !m.to.unknown, targetDimension: m.to.block?.q.dimension,
        targetSparse: m.to.sparse}))})),
    originalCoefficient: algebra.coefficientState(d), blocked: algebra.blockedFromPage,
    unchanged: model === JSON.stringify(state.project) && before === quotient()
      && coefficient === JSON.stringify(algebra.coefficientState(d)),
    repeatEqual: JSON.stringify(result) === JSON.stringify(repeat)};
}
const coupledCases = [];
for (const power of [0, 1]) for (const value of [null, 1, 2, 3]) {
  coupledCases.push({power, value, result: inspect(coupled({value, frobenius_power: power}))});
}
const sameRatio = inspect(coupled({inverse_parameter_id: 'b'}));
const ratio = coupled({id: 'gamma', inverse_parameter_id: 'b', affine_offset: 1, frobenius_power: 1});
ratio.propositions.push({id: 'b-declaration', conclusion: {coefficient_parameter: parameter('b')}});
const ratioResult = inspect(ratio);
const conditional = coupled({frobenius_power: 1});
conditional.propositions[0].conclusion.coefficient_condition = {parameter_id: 'b', equals: 2, otherwise: 'zero-euler-image'};
const conditionalResult = inspect(conditional);
conditional.propositions[0].conclusion.coefficient_parameter.domain = [1, 3];
const conditionalZero = inspect(conditional);
const invalid = inspect(coupled({frobenius_power: 9}));
const conflicting = coupled({value: 1});
conflicting.settings.coefficient_assignments = {b: 2};
const conflictingResult = inspect(conflicting);
const gatedConstraints = [];
for (const enabled of [false, true]) {
  const ws = coupled();
  ws.differentials[1].status = 'verified';
  ws.differentials.push({id: 'other', source_id: 'source', target_id: 'target', page: 23,
    status: enabled ? 'verified' : 'review', proposition_id: 'other-claim'});
  ws.propositions.push({id: 'other-claim', conclusion: {fact_id: 'premise',
    coefficient_parameter: parameter('c', {target_component: 'C'})}});
  ws.propositions[0].conclusion.coefficient_constraints = [{id: 'equality', page: 23,
    kind: 'equal-nonzero-parameters', parameter_ids: ['b', 'c'], normalization_value: 2,
    required_facts: ['premise'], required_differentials: [{fact_id: 'premise', page: 23}]}];
  gatedConstraints.push({enabled, result: inspect(ws)});
}
const linkedCases = [];
for (const admitted of [false, true]) {
  const ws = coupled({frobenius_power: 1, source_parameter: {
    workspace_id: 'external', parameter_id: 'b', differential_id: 'remote', page: 5}});
  const external = workspaceBase('external', [], [{id: 'remote', page: 5,
    status: admitted ? 'verified' : 'review', proposition_id: 'remote-claim'}],
    [{id: 'remote-claim', status: admitted ? 'verified' : 'review', conclusion: {
      coefficient_parameter: parameter('b', {domain: [2, 3]})}}]);
  linkedCases.push({admitted, result: inspect(ws, [external])});
}
const matrix = coupled();
matrix.classes.push(node('matrix-target', 0, 26, {e2_components: {B: 1, C: 0}, e2_basis_patterns: ['B', 'C']}));
matrix.differentials[1].target_id = 'matrix-target';
matrix.differentials[1].linear_map_id = 'matrix';
matrix.differential_maps = [{id: 'matrix', matrix: [[1], [1]], status: 'review'}];
const matrixResult = inspect(matrix);
matrix.classes = matrix.classes.filter(c => ['source', 'matrix-target'].includes(c.id));
matrix.classes.find(c => c.id === 'matrix-target').style = {e2_pattern: 'B', e2_basis_patterns: ['B', 'C']};
matrix.differentials = matrix.differentials.filter(d => d.id === 'candidate');
const basisOnlyMatrix = inspect(matrix);
function tower(scope = 'constant-two-multiples', status = 'verified') {
  return workspaceBase('tower', [node('source', 8, 0, {e2_pattern: 'I00'}),
    node('target', 7, 23, {e2_pattern: 'I00'})],
    [{id: 'candidate', source_id: 'source', target_id: 'target', page: 23, status: 'review', period_stem: 64}],
    [{id: 'cycle', kind: 'permanent-cycle', status, conclusion: {source_id: 'source',
      page: 2, period_stem: 64, cycle_constraint: 'outgoing-only', coefficient_scope: scope}}]);
}
const scopes = ['exact-port', 'constant-two-multiples', 'all-multiples'].map(scope => ({scope, result: inspect(tower(scope))}));
const reviewCycle = inspect(tower('all-multiples', 'review'));
const future = tower('all-multiples'); future.propositions[0].conclusion.page = 24;
const futureCycle = inspect(future);
const shiftedCycle = inspect(tower('all-multiples'), [], 64);
const conflict = tower('all-multiples'); conflict.differentials[0].status = 'verified';
const acceptedConflict = inspect(conflict);
function alias(boundary = false, certificates = ['X']) {
  const ws = workspaceBase('alias', [node('early', 9, 0, {e2_pattern: 'A'}),
    node('sum', 8, 3, {e2_components: {X: 1, Y: 1}}),
    node('X', 8, 3, {e2_pattern: 'X'}), node('Y', 8, 3, {e2_pattern: 'Y'}),
    node('target', 7, 26, {e2_pattern: 'T'})], [
    {id: 'early', source_id: 'early', target_id: 'sum', page: 3, status: 'verified', period_stem: 64},
    {id: 'candidate', source_id: boundary ? 'sum' : 'Y', target_id: 'target', page: 23,
      status: 'review', period_stem: 64}], certificates.map(id => ({id: 'cycle-'+id,
        kind: 'zero-differential', status: 'verified', conclusion: {source_id: id, page: 23, period_stem: 64}})));
  return ws;
}
const aliasResult = inspect(alias()), boundaryResult = inspect(alias(true));
const sum = alias(true, ['X', 'Y']); sum.differentials.shift();
const spanResult = inspect(sum);
sum.propositions.pop();
const partialSpan = inspect(sum);
({coupledCases, sameRatio, ratioResult, conditionalResult, conditionalZero, invalid, gatedConstraints,
  conflictingResult, linkedCases, matrixResult, basisOnlyMatrix, scopes, reviewCycle, futureCycle,
  shiftedCycle, acceptedConflict, aliasResult, boundaryResult, spanResult, partialSpan});
`, context);
process.stdout.write(JSON.stringify(output));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True,
                            encoding="utf-8", capture_output=True, check=True, timeout=30)
    return json.loads(result.stdout)


@pytest.mark.parametrize("power", [0, 1])
def test_unknown_component_keeps_each_possible_nonzero_quotient_target(audit, power):
    row = next(c["result"] for c in audit["coupledCases"] if c["power"] == power and c["value"] is None)
    assert row["status"] == "possible" and row["conditional"]
    assert {v["assignments"]["b"] for v in row["variants"]} == {2, 3}
    assert {v["coefficient"]["value"] for v in row["variants"]} == {2, 3}
    assert next(e for e in row["examined"] if e["assignments"]["b"] == 1)["status"] == "absent"
    for variant in row["variants"]:
        raw = variant["assignments"]["b"]
        expected = raw if power == 0 else {2: 3, 3: 2}[raw]
        assert variant["target"] == {"B": 1, "C": expected}


@pytest.mark.parametrize("value", [1, 2, 3])
def test_resolved_component_uses_only_its_actual_value(audit, value):
    rows = [c["result"] for c in audit["coupledCases"] if c["value"] == value]
    assert all(row["status"] == ("absent" if value == 1 else "possible") for row in rows)
    assert all(not row["conditional"] for row in rows)


def test_ratios_share_one_raw_parameter_and_apply_affine_then_frobenius(audit):
    same = audit["sameRatio"]
    assert same["status"] == "absent"
    assert {e["coefficient"]["value"] for e in same["examined"]} == {1}
    assert len(same["examined"]) == 3
    ratio = audit["ratioResult"]
    assert len(ratio["examined"]) == 9
    multiplication = ((0, 0, 0, 0), (0, 1, 2, 3), (0, 2, 3, 1), (0, 3, 1, 2))
    for branch in ratio["examined"]:
        gamma, b = branch["assignments"]["gamma"], branch["assignments"]["b"]
        unit = multiplication[gamma ^ 1][(0, 1, 3, 2)[b]]
        assert branch["coefficient"]["value"] == multiplication[unit][unit]
    # A zero coefficient on C leaves B, rather than making the whole vector zero.
    assert any(v["coefficient"]["value"] == 0 and v["target"] == {"B": 1, "C": 0}
               for v in ratio["variants"])


def test_conditions_use_raw_parameter_before_frobenius(audit):
    row = audit["conditionalResult"]
    assert row["status"] == "possible" and len(row["variants"]) == 1
    assert row["variants"][0]["assignments"] == {"b": 2}
    assert row["variants"][0]["coefficient"]["value"] == 3
    assert audit["conditionalZero"]["status"] == "zero"


def test_invalid_or_conflicting_declarations_never_become_placeholder_one(audit):
    assert audit["invalid"]["status"] == audit["conflictingResult"]["status"] == "unknown"
    assert not audit["invalid"]["variants"] and not audit["conflictingResult"]["variants"]


def test_parameter_relations_are_joint_and_require_their_admission_gates(audit):
    disabled, enabled = [row["result"] for row in audit["gatedConstraints"]]
    assert {tuple(sorted(v["assignments"].items())) for v in disabled["variants"]} == {
        (("b", 2),), (("b", 3),),
    }
    assert enabled["status"] == "possible" and enabled["conditional"]
    assert [v["assignments"] for v in enabled["variants"]] == [{"b": 2, "c": 2}]
    assert len(enabled["examined"]) == 1


def test_linked_domains_require_admitted_source_and_remain_unassigned(audit):
    denied, allowed = [row["result"] for row in audit["linkedCases"]]
    assert denied["status"] == "unknown"
    assert allowed["status"] == "possible" and allowed["conditional"]
    assert {v["assignments"]["b"] for v in allowed["variants"]} == {2, 3}
    assert not allowed["originalCoefficient"]["resolved"]


def test_matrix_is_evaluated_before_component_choices(audit):
    row = audit["matrixResult"]
    assert row["status"] == "possible"
    assert {v["target"]["C"] for v in row["variants"]} == {2, 3}
    assert all(v["target"]["B"] == 1 for v in row["variants"])


def test_basis_only_matrix_target_retains_every_actual_column(audit):
    row = audit["basisOnlyMatrix"]
    assert row["status"] == "possible"
    assert {v["coefficient"]["value"] for v in row["variants"]} == {1, 2, 3}
    for variant in row["variants"]:
        assert len(variant["maps"]) == 1
        target = variant["maps"][0]
        assert target["targetDimension"] == 2
        assert target["targetSparse"] == {
            "B+C:0:26#0": 1, "B+C:0:26#1": variant["coefficient"]["value"],
        }


def test_zero_cycle_scope_distinguishes_actual_two_and_j_ports(audit):
    rows = {c["scope"]: c["result"] for c in audit["scopes"]}
    exact = rows["exact-port"]
    assert exact["status"] == "possible"
    assert {(m["two"], m["j"]) for v in exact["variants"] for m in v["maps"]} == {(1, 0), (2, 0), (0, 1)}
    constant = rows["constant-two-multiples"]
    assert constant["status"] == "possible"
    assert {(m["two"], m["j"]) for v in constant["variants"] for m in v["maps"]} == {(0, 1)}
    assert rows["all-multiples"]["status"] == "contradicted"
    assert "cycle@23" in rows["all-multiples"]["reasons"][0]["certificateIds"]


def test_review_or_future_certificate_does_not_remove_a_candidate(audit):
    assert audit["reviewCycle"]["status"] == audit["futureCycle"]["status"] == "possible"
    assert audit["shiftedCycle"]["status"] == "contradicted"


def test_zero_certificates_use_current_quotient_aliases_and_spans(audit):
    assert audit["aliasResult"]["status"] == "contradicted"
    assert audit["boundaryResult"]["status"] == "absent"
    assert audit["spanResult"]["status"] == "contradicted"
    assert audit["partialSpan"]["status"] == "possible"


def test_accepted_conflict_still_blocks_quotient_without_candidate_side_effects(audit):
    assert audit["acceptedConflict"]["blocked"] == 23
    assert audit["acceptedConflict"]["status"] == "unknown"


def test_display_queries_do_not_mutate_models_coefficients_or_quotients(audit):
    def results(value):
        if isinstance(value, dict):
            if "unchanged" in value:
                yield value
            else:
                for child in value.values():
                    yield from results(child)
        elif isinstance(value, list):
            for child in value:
                yield from results(child)

    rows = list(results(audit))
    assert len(rows) >= 25
    assert all(row["unchanged"] and row["repeatEqual"] for row in rows)
    assert all(m["sourceKnown"] and m["targetKnown"]
               for row in rows for v in row["variants"] for m in v["maps"])


def test_public_page_algebra_is_identical():
    assert (ROOT / "backend/static/page-algebra.js").read_bytes() == (ROOT / "public/static/page-algebra.js").read_bytes()
