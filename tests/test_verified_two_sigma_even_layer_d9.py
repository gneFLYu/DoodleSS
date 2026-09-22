"""FN017 in pristine production data, including both independent D8 blocks.

The published integer d23 product forces a boundary before E23; it does not
authorize clipping the chart at a vanishing line.  The low and high I31
sources have already lost their odd constants to FN004 d5.  FN017 kills
their remaining two-layer, while primitive d3 killed the target's positive-j
ideal earlier.  No review admission, coefficient assignment, or endpoint
rewriting is performed here.  A 32-stem agreement is a differential pattern,
not a permanent D4 unit.
"""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.migrations import migrate_project
from domain.seed import demo_project


TWO = "ws_2sigma_i"
FACT = "FN-2I-017"
ROW_SUFFIX = "formal_diff_fn-2i-017_1"
EXPECTED_PREMISES = {
    f"FN-2I-{number:03}" for number in (1, 3, 4, 5, 6, 9, 11, 13, 14, 16)
}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    result = [w for w in project.workspaces if w.id == TWO or
              w.settings.get("atlas_transport", {}).get("source_workspace_id") == TWO]
    assert {w.id for w in result} == {TWO, "ws_q8-ro-a0-b2", "ws_q8-ro-a2-b2"}
    return result


def shift_of(workspace):
    return workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)


def ports(row, pattern, stem, filtration):
    return set(next(p["ports"] for p in row["probes"]
                    if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))


@pytest.fixture(scope="module")
def chart(project):
    workspaces = images(project)
    probes = set()
    for ws in workspaces:
        for repeat in (0, 32):
            offset = shift_of(ws) + repeat
            for pattern, stem, filtration in (
                ("I31", 11, 1), ("I22H", 10, 10),
                ("I31", 27, 17), ("I22H", 26, 26),
                ("I31", 31, 5), ("I22H", 30, 14),
                ("I00", 28, 12),
            ):
                probes.add((pattern, stem + offset, filtration))
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [3, 4, 5, 6, 9, 10], "vectorAudit": True,
        "boundsByWorkspace": {
            w.id: {"stemMin": 8 + shift_of(w), "stemMax": 64 + shift_of(w),
                   "filtrationMin": 0, "filtrationMax": 26} for w in workspaces
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
    }
    completed = subprocess.run(
        ["node", "tests/chart_runtime.cjs"], cwd=ROOT, input=json.dumps(payload),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=150,
    )
    return {w["id"]: {p["page"]: p for p in w["pages"]} for w in json.loads(completed.stdout)}


def test_fn017_has_an_independent_published_d23_product_certificate(project):
    for ws in images(project):
        claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == FACT)
        row = next(d for d in ws.differentials if d.proposition_id == claim.id)
        metadata = claim.conclusion
        assert row.status == claim.status == metadata["admission_status"] == "verified"
        assert row.page == metadata["page"] == 9
        assert metadata["source_status"] == "independently-verified"
        assert not metadata["source_blockers"]
        certificate = metadata["verification_certificate"]
        assert certificate["status"] == "verified"
        assert certificate["method"] == "Published d23 product boundary and finite incoming-source exclusion"
        assert certificate["source_refs"] and certificate["derivation"]
        assert EXPECTED_PREMISES <= set(certificate["premises"])
        cited = " ".join(certificate["premises"]).lower().replace(" ", "")
        assert "table8" in cited and "row22" in cited
        for premise in certificate["premises"]:
            lowered = premise.lower()
            assert FACT not in premise
            assert "jan29" not in lowered and "jan 29" not in lowered
            assert "vanishing" not in lowered
        assert metadata["coefficient_normalization"]["value"] == 1
        assert row.period_stem == metadata["period_stem"] == 32
        assert metadata["period_kind"] == "repeated-differential-pattern"
        assert metadata["period_is_invertible"] is False
        assert "formal_notes.tex" in " ".join(claim.source_refs)
        if row.linear_map_id:
            assert next(m for m in ws.differential_maps if m.id == row.linear_map_id).status == "verified"
        assert not ws.settings.get("coefficient_assignments")


def test_fn017_preserves_the_witt_two_factor_and_constant_target_port(project):
    for ws in images(project):
        claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == FACT)
        row = next(d for d in ws.differentials if d.proposition_id == claim.id)
        nodes = {n.id: n for n in ws.classes}
        source, target, shift = nodes[row.source_id], nodes[row.target_id], shift_of(ws)
        assert (source.grade.stem, source.grade.filtration) == (11 + shift, 1)
        assert (target.grade.stem, target.grade.filtration) == (10 + shift, 10)
        assert (source.style["e2_pattern"], source.style.get("two_valuation", 0),
                source.style.get("j_order", 0)) == ("I31", 1, 0)
        assert (target.style["e2_pattern"], target.style.get("two_valuation", 0),
                target.style.get("j_order", 0)) == ("I22H", 0, 0)


def test_d5_removes_odd_sources_then_d9_removes_only_the_remaining_two_layer(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for repeat in (0, 32):
            for stem, filtration in ((11, 1), (27, 17), (31, 5)):
                location = (stem + repeat + shift, filtration)
                assert ports(rows[5], "I31", *location) == {"0:0", "1:0"}, (ws.id, location)
                assert ports(rows[6], "I31", *location) == {"1:0"}, (ws.id, location)
                assert ports(rows[9], "I31", *location) == {"1:0"}, (ws.id, location)
                assert ports(rows[10], "I31", *location) == set(), (ws.id, location)


def test_primitive_d3_kills_j_targets_before_fn017_kills_the_constants(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for repeat in (0, 32):
            for stem, filtration in ((10, 10), (26, 26), (30, 14)):
                location = (stem + repeat + shift, filtration)
                assert ports(rows[3], "I22H", *location) == {"0:0", "0:1"}, (ws.id, location)
                for page in (4, 5, 6, 9):
                    assert ports(rows[page], "I22H", *location) == {"0:0"}, (ws.id, page, location)
                assert ports(rows[10], "I22H", *location) == set(), (ws.id, location)


def test_high_source_double_is_not_an_fn005_boundary_in_these_two_blocks(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for repeat in (0, 32):
            # 2k^3D^(5,9)u = g^3D^-8 * 2D^(4,8)u, both FN005 zero maps.
            # Bare D parity of k^3D^m is not a valid d5 computation.
            location = (28 + repeat + shift, 12)
            assert "1:0" in ports(rows[5], "I00", *location)
            assert "1:0" in ports(rows[6], "I00", *location)
            assert ports(rows[6], "I31", 27 + repeat + shift, 17) == {"1:0"}


def test_fn017_is_drawn_only_on_e9_without_early_conflicts_or_dead_endpoints(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for page, row in rows.items():
            assert row["blockedFromPage"] is None and not row["conflicts"], (ws.id, page, row["conflicts"])
            assert not row["dangling"], (ws.id, page, row["dangling"])
            assert not [block for block in row["blocks"] if block["barriers"]], (ws.id, page)
            present = any(ident.endswith(ROW_SUFFIX) for ident in row["rows"])
            assert present is (page == 9), (ws.id, page, row["rows"])


def test_actual_fn017_rendered_occurrences_have_live_exact_ports(project):
    script = r"""
const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for(const name of ['graded-quotient.js','vector-page-algebra.js','page-algebra.js'])
  vm.runInContext(fs.readFileSync('backend/static/'+name,'utf8'),context);
const app=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(app.slice(0,app.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.input=input;
const output=vm.runInContext(`
state.project=input.project;
input.workspaces.map(id=>{
  const ws=state.project.workspaces.find(w=>w.id===id),shift=ws.settings.atlas_transport?.stem_shift||0;
  const nodes=new Map(ws.classes.map(n=>[n.id,n]));
  const bounds={stemMin:shift+8,stemMax:shift+64,filtrationMin:0,filtrationMax:26};
  return {id,shift,pages:[9,10].map(page=>{
    ws.page=page;const algebra=pageAlgebra(ws,bounds);
    return {page,occurrences:periodicDifferentials(ws,bounds).filter(e=>e.diff.label==='FN-2I-017')
      .map(e=>{const pair=algebra.endpoints(e.diff);return {
        source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
        sourcePattern:pair.source.style.e2_pattern,targetPattern:pair.target.style.e2_pattern,
        sourceTwo:pair.source.style.two_valuation||0,targetTwo:pair.target.style.two_valuation||0,
        sourceJ:pair.source.style.j_order||0,targetJ:pair.target.style.j_order||0,
        sourceLive:algebra.live(nodes.get(e.diff.source_id),e.sourceGrade),
        targetLive:algebra.live(nodes.get(e.diff.target_id),e.targetGrade)};})};
  })};
})`,context);
process.stdout.write(JSON.stringify(output));
"""
    payload = {"project": asdict(project), "workspaces": [w.id for w in images(project)]}
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(payload),
                               text=True, encoding="utf-8", capture_output=True, check=True, timeout=120)
    results = json.loads(completed.stdout)
    assert len(results) == 3
    for workspace in results:
        e9, e10 = workspace["pages"]
        assert e9["page"] == 9 and e10["page"] == 10
        assert e9["occurrences"] and not e10["occurrences"]
        for occurrence in e9["occurrences"]:
            assert occurrence["admitted"] and occurrence["sourceLive"] and occurrence["targetLive"]
            assert occurrence["coefficient"]["resolved"] and occurrence["coefficient"]["value"] == 1
            assert (occurrence["sourcePattern"], occurrence["targetPattern"]) == ("I31", "I22H")
            assert (occurrence["sourceTwo"], occurrence["targetTwo"]) == (1, 0)
            assert occurrence["sourceJ"] == occurrence["targetJ"] == 0
            assert occurrence["target"]["stem"] == occurrence["source"]["stem"] - 1
            assert occurrence["target"]["filtration"] == occurrence["source"]["filtration"] + 9
        for repeat in (0, 32):
            for stem, filtration in ((11, 1), (27, 17), (31, 5)):
                expected = (stem + repeat + workspace["shift"], filtration)
                assert any((e["source"]["stem"], e["source"]["filtration"]) == expected
                           for e in e9["occurrences"]), (workspace["id"], expected)
