"""Independent FN016 proof and its coefficient-sensitive production quotient.

The low h2 D^(2,6) sources are W/4: d9 removes only their odd constant.
Their high g^4 D^-8 translates have already lost the two1 line to FN005.
The h1^2 target's positive-j ideal dies by primitive d3, not by d9.
These tests use pristine migrated production data without admitting claims,
assigning coefficients, clipping a vanishing line, or assuming FN017.
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
FACT = "FN-2I-016"
ROW_SUFFIX = "formal_diff_fn-2i-016_1"
EXPECTED_PREMISES = {"FN-2I-001", "FN-2I-004", "FN-2I-005", "FN-2I-006", "FN-2I-009"}


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
        for power in (2, 6):
            for d8 in (-64, 0, 64):
                offset = 8 * power + shift_of(ws) + d8
                for pattern, stem, filtration in (
                    ("I31", 3, 1), ("I22H", 2, 10),
                    ("I31", 19, 17), ("I22H", 18, 26),
                    ("I00", 20, 12), ("I33", 19, 19),
                    ("I13", 1, 3), ("I13", 41, 11),
                ):
                    probes.add((pattern, offset + stem, filtration))
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [3, 4, 5, 6, 9, 10], "vectorAudit": True,
        "boundsByWorkspace": {
            w.id: {"stemMin": shift_of(w) - 64, "stemMax": shift_of(w) + 159,
                   "filtrationMin": 0, "filtrationMax": 32} for w in workspaces
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
    }
    completed = subprocess.run(
        ["node", "tests/chart_runtime.cjs"], cwd=ROOT, input=json.dumps(payload),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=180,
    )
    return {w["id"]: {p["page"]: p for p in w["pages"]} for w in json.loads(completed.stdout)}


def test_fn016_has_an_independent_verified_d11_product_certificate(project):
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
        assert certificate["method"] == "d11 product boundary and finite incoming-source exclusion"
        assert certificate["source_refs"] and certificate["derivation"]
        assert EXPECTED_PREMISES <= set(certificate["premises"])
        for premise in certificate["premises"]:
            lowered = premise.lower()
            assert "fn-2i-017" not in lowered and "jan29" not in lowered and "jan 29" not in lowered
            assert "vanishing" not in lowered
            assert FACT not in premise  # No circular appeal to the row being proved.
        assert metadata["coefficient_normalization"]["value"] == 1
        assert row.period_stem == metadata["period_stem"] == 32
        assert metadata["period_kind"] == "repeated-differential-pattern"
        assert metadata["period_is_invertible"] is False
        assert "formal_notes.tex" in " ".join(claim.source_refs)
        if row.linear_map_id:
            assert next(m for m in ws.differential_maps if m.id == row.linear_map_id).status == "verified"
        assert not ws.settings.get("coefficient_assignments")


def test_fn016_maps_the_odd_i31_constant_to_the_i22h_constant(project):
    for ws in images(project):
        claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == FACT)
        row = next(d for d in ws.differentials if d.proposition_id == claim.id)
        nodes = {n.id: n for n in ws.classes}
        source, target, shift = nodes[row.source_id], nodes[row.target_id], shift_of(ws)
        assert (source.grade.stem, source.grade.filtration) == (19 + shift, 1)
        assert (target.grade.stem, target.grade.filtration) == (18 + shift, 10)
        for node, pattern in ((source, "I31"), (target, "I22H")):
            assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                    node.style.get("j_order", 0)) == (pattern, 0, 0)


def test_low_witt_sources_keep_the_two1_kernel_on_e10_in_both_blocks(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for power in (2, 6):
            for d8 in (-64, 0, 64):
                stem = 8 * power + 3 + shift + d8
                for page in (5, 6, 9):
                    assert ports(rows[page], "I31", stem, 1) == {"0:0", "1:0"}
                assert ports(rows[10], "I31", stem, 1) == {"1:0"}


def test_d3_removes_target_j_tails_before_d9_removes_the_constants(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for power in (2, 6):
            for d8 in (-64, 0, 64):
                offset = 8 * power + shift + d8
                for stem, filtration in ((offset + 2, 10), (offset + 18, 26)):
                    assert ports(rows[3], "I22H", stem, filtration) == {"0:0", "0:1"}
                    for page in (4, 5, 6, 9):
                        assert ports(rows[page], "I22H", stem, filtration) == {"0:0"}
                    assert ports(rows[10], "I22H", stem, filtration) == set()
        assert any(d.endswith("formal_diff_two_d3_h1_3_derived") for d in rows[3]["rows"])


def test_high_source_two_layer_is_an_earlier_fn005_boundary_not_a_d9_casualty(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for power in (2, 6):
            for d8 in (-64, 0, 64):
                offset = 8 * power + shift + d8
                # g^4 D^-8 h2 D^m u has filtration 17, not the low W/4 quotient.
                assert ports(rows[5], "I31", offset + 19, 17) == {"0:0", "1:0"}
                # d5(2k^3 D^(m+4)u)=2h2 k^4 D^(m+4)u.
                assert "1:0" in ports(rows[5], "I00", offset + 20, 12)
                assert "1:0" not in ports(rows[6], "I00", offset + 20, 12)
                assert ports(rows[6], "I31", offset + 19, 17) == {"0:0"}
                assert ports(rows[9], "I31", offset + 19, 17) == {"0:0"}
                assert ports(rows[10], "I31", offset + 19, 17) == set()
        assert any(d.endswith("diff_two_d5_2D") for d in rows[5]["rows"])


def test_potential_high_d7_source_is_already_a_fn006_d5_boundary(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for power in (2, 6):
            for d8 in (-64, 0, 64):
                stem = 8 * power + 19 + shift + d8
                # h1^3 k^4 D^(m+4)u cannot hit T_m by d7: FN006 hit it by d5.
                assert "0:0" in ports(rows[5], "I33", stem, 19)
                assert "0:0" not in ports(rows[6], "I33", stem, 19)
                assert "0:0" not in ports(rows[9], "I33", stem, 19)
        assert any(d.endswith("diff_two_d5_xh1") for d in rows[5]["rows"])


def test_h2_cube_cycle_certificates_do_not_protect_their_g_squared_incoming_targets(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for power in (2, 6):
            for d8 in (-64, 0, 64):
                offset = 8 * power + shift + d8
                # h2^3 D^(1,5)u is a zero-outgoing seed, not an immortal family.
                assert ports(rows[9], "I13", offset + 1, 3) == {"0:0"}
                assert ports(rows[10], "I13", offset + 1, 3) == {"0:0"}
                # g^2 times the same seed is precisely an FN011 d9 target.
                assert ports(rows[9], "I13", offset + 41, 11) == {"0:0"}
                assert ports(rows[10], "I13", offset + 41, 11) == set()


def test_fn016_draws_only_on_e9_without_conflicts_or_dangling_maps(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for row in rows.values():
            assert row["blockedFromPage"] is None and not row["conflicts"]
            assert not row["dangling"]
            assert not [block for block in row["blocks"] if block["barriers"]]
        assert any(d.endswith(ROW_SUFFIX) for d in rows[9]["rows"])
        assert not any(d.endswith(ROW_SUFFIX) for d in rows[10]["rows"])


def test_actual_fn016_occurrences_have_live_odd_endpoints_and_unit_one(project):
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
  ws.page=9;
  const nodes=new Map(ws.classes.map(n=>[n.id,n]));
  const bounds={stemMin:shift-64,stemMax:shift+159,filtrationMin:0,filtrationMax:32};
  const algebra=pageAlgebra(ws,bounds);
  return {id,shift,blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
    occurrences:periodicDifferentials(ws,bounds).filter(e=>e.diff.label==='FN-2I-016')
      .map(e=>{const pair=algebra.endpoints(e.diff);return {
        source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
        sourcePattern:pair.source.style.e2_pattern,targetPattern:pair.target.style.e2_pattern,
        sourceTwo:pair.source.style.two_valuation||0,targetTwo:pair.target.style.two_valuation||0,
        sourceJ:pair.source.style.j_order||0,targetJ:pair.target.style.j_order||0,
        sourceLive:algebra.live(nodes.get(e.diff.source_id),e.sourceGrade),
        targetLive:algebra.live(nodes.get(e.diff.target_id),e.targetGrade)};})};
})`,context);
process.stdout.write(JSON.stringify(output));
"""
    payload = {"project": asdict(project), "workspaces": [w.id for w in images(project)]}
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(payload),
                               text=True, encoding="utf-8", capture_output=True, check=True, timeout=120)
    results = json.loads(completed.stdout)
    assert len(results) == 3
    for ws in results:
        assert ws["blocked"] is None and not ws["conflicts"]
        occurrences = ws["occurrences"]
        assert occurrences
        for occurrence in occurrences:
            assert occurrence["admitted"] and occurrence["sourceLive"] and occurrence["targetLive"]
            assert occurrence["coefficient"]["resolved"] and occurrence["coefficient"]["value"] == 1
            assert (occurrence["sourcePattern"], occurrence["targetPattern"]) == ("I31", "I22H")
            assert occurrence["sourceTwo"] == occurrence["targetTwo"] == 0
            assert occurrence["sourceJ"] == occurrence["targetJ"] == 0
            assert occurrence["target"]["stem"] == occurrence["source"]["stem"] - 1
            assert occurrence["target"]["filtration"] == occurrence["source"]["filtration"] + 9
        for power in (2, 6):
            expected = [(8 * power + 3 + d8 + 20 * g + ws["shift"], 1 + 4 * g)
                        for d8 in (-64, 0, 64) for g in (0, 1)]
            expected.append((8 * power + 19 + ws["shift"], 17))  # g^4 D^-8.
            for source in expected:
                assert any((e["source"]["stem"], e["source"]["filtration"]) == source
                           for e in occurrences), (ws["id"], source)
