"""A finite d9 zero certificate is neither a permanent cycle nor an incoming map.

S02 is tested as its actual single finite port. The separate I00 fixture is an
abstract Witt-port control for exact-scope handling, not an extra S02 j-tail.
"""
import json
from copy import deepcopy
from pathlib import Path
import subprocess

import pytest

from backend.domain.fate import _cycle_claim_covers, derive_class_fate, sync_workspace_fates
from backend.domain.models import ClassNode, Differential, Grade, Proposition, Workspace


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
const result = vm.runInContext(`
function make(shift = 0, incoming = false, witt = false) {
  const representation = shift === 0 ? {sigma_i: -3} : {sigma_i: -1, sigma_j: -1};
  const node = (id, pattern, stem, filtration, extra = {}) => ({id, label: id, page: 2,
    grade: {stem: stem + shift, filtration, representation},
    style: {e2_pattern: pattern, two_valuation: 0, j_order: 0, ...extra}});
  const row = (id, source, target, page, status = 'review') => ({id, source_id: source,
    target_id: target, page, status, period_stem: 64});
  const f = witt ? 0 : 2, sourcePattern = witt ? 'I00' : 'S02';
  const classes = [node('finite', sourcePattern, 8, f),
    node('target9', witt ? 'I00' : 'T', 7, f + 9),
    node('target11', witt ? 'I00' : 'T', 7, f + 11),
    node('series', 'S11', 9, 1, {j_order: 1}), node('series-target', 'S11', 8, 10, {j_order: 1}),
    node('twice', 'I00', 16, 0, {two_valuation: 1}), node('twice-target', 'I00', 15, 9)];
  const differentials = [row('out9', 'finite', 'target9', 9), row('out11', 'finite', 'target11', 11),
    row('series9', 'series', 'series-target', 9), row('twice9', 'twice', 'twice-target', 9)];
  if (incoming) {
    classes.push(node('finite-g2', 'S02', 48, 10), node('incoming-source', 'A', 49, 1));
    differentials.push(row('incoming9', 'incoming-source', 'finite-g2', 9, 'verified'));
  }
  return {id: 'scope-' + shift + '-' + incoming + '-' + witt, page: 9, classes, differentials,
    propositions: [{id: 'finite-d9-zero', kind: 'zero-differential', status: 'verified', conclusion: {
      source_id: 'finite', page: 9, period_stem: 64, cycle_constraint: 'outgoing-only',
      coefficient_scope: 'exact-port', forward_period: {stem: 20, filtration: 4, nonnegative: true},
      source_provenance: {workspace_id: 'original', source_bidegree: [8, f]}}}],
    differential_maps: [], cells: [], fates: [], settings: {
      atlas_transport: {source_workspace_id: 'original', stem_shift: shift},
      rendering: {enumerated_e2_pattern: 'integer', enumerated_horizontal_period: 64,
        period_lattice: [{stem: 64, filtration: 0, exponent_domain: 'integer'},
          {stem: 20, filtration: 4, exponent_domain: 'nonnegative'}]}}};
}
function inspect(ws, page) {
  ws.page = page;
  state.project = {workspaces: [ws], period_families: [], page_period_cycles: []};
  state.workspaceId = ws.id;
  const shift = ws.settings.atlas_transport.stem_shift;
  const bounds = {stemMin: shift - 1, stemMax: shift + 129, filtrationMin: 0, filtrationMax: 24};
  const before = JSON.stringify(ws), algebra = pageAlgebra(ws, bounds);
  const find = id => ws.classes.find(n => n.id === id);
  const candidate = (id, ds = 0, df = 0) => {
    const diff = ws.differentials.find(d => d.id === id);
    const source = find(diff.source_id), target = find(diff.target_id);
    const sg = {...source.grade, stem: source.grade.stem + ds, filtration: source.grade.filtration + df};
    const tg = {...target.grade, stem: target.grade.stem + ds, filtration: target.grade.filtration + df};
    const state = algebra.candidateState(diff, sg, tg);
    return {status: state.status, reasons: state.reasons,
      sourceGrade: sg, targetGrade: tg,
      maps: state.variants.flatMap(v => v.maps.map(m => [m.two, m.j]))};
  };
  const probes = ['finite', 'series', 'twice', ...(find('finite-g2') ? ['finite-g2','incoming-source'] : [])]
    .map(id => {const n = find(id); return {id, grade: n.grade, live: algebra.live(n, n.grade),
      ports: [...(algebra.ports(n, n.grade) || [])]};});
  const candidates = page === 9 ? {anchor: candidate('out9'), D8: candidate('out9', 64),
    g2: candidate('out9', 40, 8), j: candidate('series9'), two: candidate('twice9'),
    ...(find('finite-g2') ? {incoming: candidate('incoming9')} : {})}
    : page === 11 ? {anchor: candidate('out11'), g2: candidate('out11', 40, 8)} : {};
  const rendered = periodicDifferentials(ws, bounds).map(e => ({id: e.diff.id,
    source: [e.sourceGrade.stem, e.sourceGrade.filtration]}));
  const points = periodicClassInstances(ws, bounds);
  const finite = find('finite');
  return {page, probes, candidates, rendered, blocked: algebra.blockedFromPage, conflicts: algebra.conflicts,
    finiteDot: points.some(p => p.item.style?.e2_pattern === finite.style.e2_pattern
      && p.grade.stem === finite.grade.stem && p.grade.filtration === finite.grade.filtration),
    unchanged: before === JSON.stringify(ws), definitions: ws.differentials.length,
    certificateKind: ws.propositions[0].kind, certificatePage: ws.propositions[0].conclusion.page};
}
const transported = [-16, 0, 16].map(shift => {const ws = make(shift);
  return {shift, pages: [8,9,10,11,12].map(page => inspect(ws, page))};});
const witt = [9,10,11,12].map(page => inspect(make(0, false, true), page));
const incoming = [-16,0,16].map(shift => {const ws = make(shift, true);
  return {shift, pages: [9,10,11].map(page => inspect(ws, page))};});
const scopeOnly = make(0, false, true);
delete scopeOnly.propositions[0].conclusion.cycle_constraint;
const explicitWithoutConstraint = inspect(scopeOnly, 9);
delete scopeOnly.propositions[0].conclusion.coefficient_scope;
const legacyClosure = inspect(scopeOnly, 9);
({transported,witt,incoming,explicitWithoutConstraint,legacyClosure});
`, context);
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run(["node", "-e", script], cwd=ROOT, text=True,
                            encoding="utf-8", capture_output=True, check=True, timeout=30)
    return json.loads(result.stdout)


def page_rows(case):
    return {row["page"]: row for row in case["pages"]}


@pytest.mark.parametrize("shift", [-16, 0, 16])
def test_finite_s02_zero_is_only_a_d9_outgoing_constraint(audit, shift):
    rows = page_rows(next(c for c in audit["transported"] if c["shift"] == shift))
    for name in ("anchor", "D8", "g2"):
        assert rows[9]["candidates"][name]["status"] == "contradicted"
    assert rows[11]["candidates"]["anchor"]["status"] == "possible"
    assert rows[11]["candidates"]["g2"]["status"] == "possible"
    assert rows[9]["candidates"]["anchor"]["sourceGrade"]["stem"] == 8 + shift
    assert rows[9]["candidates"]["g2"]["sourceGrade"]["stem"] == 48 + shift
    assert rows[9]["candidates"]["g2"]["sourceGrade"]["filtration"] == 10
    for row in rows.values():
        assert row["blocked"] is None and not row["conflicts"]
        assert row["finiteDot"] and row["unchanged"]
        assert row["certificateKind"] == "zero-differential" and row["certificatePage"] == 9
        assert row["definitions"] == 4
        finite = next(p for p in row["probes"] if p["id"] == "finite")
        assert finite["live"] and finite["ports"] == ["0:0"]
    assert not any(edge["id"] == "out9" for edge in rows[9]["rendered"])
    assert any(edge["id"] == "out11" for edge in rows[11]["rendered"])


def test_finite_certificate_never_changes_other_j_or_witt_families(audit):
    for case in audit["transported"]:
        rows = page_rows(case)
        assert rows[9]["candidates"]["j"]["status"] == "possible"
        assert rows[9]["candidates"]["two"]["status"] == "possible"
        for ident in ("series", "twice"):
            expected = next(p for p in rows[8]["probes"] if p["id"] == ident)["ports"]
            assert all(next(p for p in row["probes"] if p["id"] == ident)["ports"] == expected
                       for row in rows.values())


def test_exact_port_on_an_abstract_witt_module_preserves_two_layers_and_j_tail(audit):
    rows = {row["page"]: row for row in audit["witt"]}
    assert rows[9]["candidates"]["anchor"]["status"] == "possible"
    assert set(map(tuple, rows[9]["candidates"]["anchor"]["maps"])) == {(1,0),(2,0),(0,1)}
    assert set(map(tuple, rows[11]["candidates"]["anchor"]["maps"])) == {(0,0),(1,0),(2,0),(0,1)}
    expected = next(p for p in rows[9]["probes"] if p["id"] == "finite")["ports"]
    assert all(next(p for p in row["probes"] if p["id"] == "finite")["ports"] == expected
               for row in rows.values())
    assert all(row["finiteDot"] and row["unchanged"] for row in rows.values())


def test_explicit_scope_without_constraint_is_not_mistaken_for_legacy_closure(audit):
    explicit = audit["explicitWithoutConstraint"]
    assert explicit["candidates"]["anchor"]["status"] == "possible"
    assert set(map(tuple, explicit["candidates"]["anchor"]["maps"])) == {(1,0),(2,0),(0,1)}
    legacy = audit["legacyClosure"]
    assert legacy["candidates"]["anchor"]["status"] == "contradicted"
    assert explicit["finiteDot"] and legacy["finiteDot"]
    assert explicit["unchanged"] and legacy["unchanged"]


@pytest.mark.parametrize("shift", [-16, 0, 16])
def test_zero_outgoing_does_not_prevent_a_real_incoming_d9(audit, shift):
    rows = page_rows(next(c for c in audit["incoming"] if c["shift"] == shift))
    assert rows[9]["candidates"]["g2"]["status"] == "contradicted"
    assert rows[9]["candidates"]["incoming"]["status"] == "possible"
    assert any(edge["id"] == "incoming9" for edge in rows[9]["rendered"])
    assert rows[11]["candidates"]["g2"]["status"] == "absent"
    for page, row in rows.items():
        assert row["blocked"] is None and not row["conflicts"] and row["unchanged"]
        for ident in ("finite-g2", "incoming-source"):
            probe = next(p for p in row["probes"] if p["id"] == ident)
            assert probe["live"] is (page == 9)
        # Only the true incoming image disappears; the lower source remains.
        assert next(p for p in row["probes"] if p["id"] == "finite")["live"]
        assert row["finiteDot"] and row["definitions"] == 5


def backend_workspace(kind="zero-differential", scope="exact-port", constraint="outgoing-only"):
    ws = Workspace("scope", "Scope regression")
    source = ClassNode("source", "source", Grade(8, 0, {"sigma_i": -3}),
                       style={"e2_pattern": "I00", "two_valuation": 1, "j_order": 0})
    data = {"source_id": source.id, "page": 9, "period_stem": 64,
            "forward_period": {"stem": 20, "filtration": 4, "nonnegative": True}}
    if scope is not None:
        data["coefficient_scope"] = scope
    if constraint is not None:
        data["cycle_constraint"] = constraint
    claim = Proposition("zero", kind, "Scoped zero outgoing", status="verified", conclusion=data)
    ws.classes.append(source)
    ws.propositions.append(claim)
    return ws, source, claim


@pytest.mark.parametrize("same_id", [False, True])
@pytest.mark.parametrize("kind", ["zero-differential", "permanent-cycle"])
@pytest.mark.parametrize("scope,constraint,two,j,covered", [
    ("exact-port", "outgoing-only", 0, 0, False),
    ("exact-port", "outgoing-only", 1, 0, True),
    ("exact-port", "outgoing-only", 2, 0, False),
    ("exact-port", "outgoing-only", 1, 1, False),
    ("exact-port", None, 2, 0, False),
    ("exact-port", None, 1, 1, False),
    (None, {"coefficient_scope": "exact-port"}, 2, 0, False),
    ("constant-two-multiples", None, 2, 0, True),
    ("constant-two-multiples", None, 1, 1, False),
    ("all-multiples", "outgoing-only", 2, 1, True),
    ("all-multiples", None, 0, 1, False),
])
def test_backend_explicit_scope_cannot_be_bypassed_by_source_alias(kind, scope, constraint, two, j, covered, same_id):
    ws, source, claim = backend_workspace(kind, scope, constraint)
    target = deepcopy(source)
    target.id = source.id if same_id else "alias"
    target.style.update(two_valuation=two, j_order=j)
    before = deepcopy((ws, target))
    assert _cycle_claim_covers(ws, claim, target, 9) is covered
    assert (ws, target) == before


@pytest.mark.parametrize("kind,covered", [("zero-differential", True), ("permanent-cycle", False)])
def test_backend_defaults_preserve_legacy_zero_closure_but_not_permanent_j_extension(kind, covered):
    ws, source, claim = backend_workspace(kind, None, None)
    target = deepcopy(source)
    target.id = "positive-j"
    target.style.update(two_valuation=2, j_order=1)
    assert _cycle_claim_covers(ws, claim, target, 9) is covered


def test_backend_exact_positive_ideal_uses_the_saturated_j_port():
    ws, source, claim = backend_workspace()
    source.style["j_order"] = 1
    target = deepcopy(source)
    target.id = "positive-ideal-alias"
    target.style["j_order"] = 2
    assert _cycle_claim_covers(ws, claim, target, 9)
    target.style["j_order"] = 0
    assert not _cycle_claim_covers(ws, claim, target, 9)


@pytest.mark.parametrize("shift", [-16, 0, 16])
def test_backend_transported_page_scope_and_period_remain_exact(shift):
    ws, source, claim = backend_workspace()
    source.grade.stem += shift
    source.grade.representation = {"sigma_j": -3}
    translated = deepcopy(source)
    translated.id = "translated"
    translated.grade.stem += 64 + 40
    translated.grade.filtration += 8
    assert _cycle_claim_covers(ws, claim, translated, 9)
    assert not _cycle_claim_covers(ws, claim, translated, 11)
    translated.style["two_valuation"] += 1
    assert not _cycle_claim_covers(ws, claim, translated, 9)
    # Same-ID copies still require the stated grading/period relation.
    translated = deepcopy(source)
    translated.grade.stem += 8
    assert not _cycle_claim_covers(ws, claim, translated, 9)


def test_backend_zero_certificate_neither_deletes_source_nor_protects_incoming_target():
    ws, source, claim = backend_workspace()
    source.grade.filtration = 10
    source.style = {"e2_pattern": "S02", "two_valuation": 0, "j_order": 0}
    sync_workspace_fates(ws)
    assert derive_class_fate(ws, source.id).first_hfpss_death is None
    origin = ClassNode("origin", "origin", Grade(9, 1, {"sigma_i": -3}), style={"e2_pattern": "A"})
    incoming_claim = Proposition("incoming-claim", "differential", "Incoming d9", status="verified",
                                 conclusion={"source_id": origin.id, "target_id": source.id, "page": 9})
    incoming = Differential("incoming", origin.id, source.id, 9, status="verified", proposition_id=incoming_claim.id)
    ws.classes.append(origin)
    ws.differentials.append(incoming)
    ws.propositions.append(incoming_claim)
    sync_workspace_fates(ws)
    fate = derive_class_fate(ws, source.id)
    assert fate.first_hfpss_death == {"page": 9, "role": "receives", "claim_id": "incoming"}
    assert not source.archived and ws.propositions == [claim, incoming_claim]


def test_backend_page_nine_certificate_does_not_block_a_page_eleven_outgoing_map():
    ws, source, certificate = backend_workspace()
    target = ClassNode("target", "target", Grade(7, 11, {"sigma_i": -3}), style={"e2_pattern": "T"})
    claim = Proposition("outgoing-claim", "differential", "Outgoing d11", status="verified",
                        conclusion={"source_id": source.id, "target_id": target.id, "page": 11})
    outgoing = Differential("outgoing", source.id, target.id, 11, status="verified", proposition_id=claim.id)
    ws.classes.append(target)
    ws.propositions.append(claim)
    ws.differentials.append(outgoing)
    sync_workspace_fates(ws)
    assert derive_class_fate(ws, source.id).first_hfpss_death == {
        "page": 11, "role": "supports", "claim_id": "outgoing",
    }
    assert not source.archived and ws.propositions == [certificate, claim]
