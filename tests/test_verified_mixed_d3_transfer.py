"""Production-chart checks for the independent mixed d3 and kernel transfer.

No review rows are admitted by these tests. The F4 unit zeta and the Witt
2-level are distinct, and a constant-layer differential never deletes a
whole positive-j family.
"""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.fate import derive_class_fate
from domain.migrations import migrate_project
from domain.seed import demo_project


MIXED = "ws_sigma_i_2sigma_j"
TWO = "ws_2sigma_i"
TRANSFER_FACT = "DER-2I-TRANSFER-TWO-cycle"


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def workspace(project, ident):
    return next(w for w in project.workspaces if w.id == ident)


def mixed_images(project):
    reflected = next(w for w in project.workspaces
                     if w.settings.get("atlas_transport", {}).get("source_workspace_id") == MIXED
                     and w.settings["atlas_transport"]["reflected"])
    return [workspace(project, MIXED), reflected]


def chart(project, workspaces, pages, probe_specs, bounds):
    shifts = {w.id: w.settings.get("atlas_transport", {}).get("stem_shift", 0) for w in workspaces}
    probes = {(pattern, stem + shift, filtration)
              for shift in shifts.values() for pattern, stem, filtration in probe_specs}
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces], "pages": pages,
        "boundsByWorkspace": {
            ident: {**bounds, "stemMin": bounds["stemMin"] + shift, "stemMax": bounds["stemMax"] + shift}
            for ident, shift in shifts.items()
        },
        "vectorAudit": True,
        "probes": [{"pattern": pattern, "stem": stem, "filtration": filtration}
                   for pattern, stem, filtration in sorted(probes)],
    }
    completed = subprocess.run(
        ["node", "tests/chart_runtime.cjs"], cwd=ROOT, input=json.dumps(payload),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=120,
    )
    return {w["id"]: {row["page"]: row for row in w["pages"]} for w in json.loads(completed.stdout)}


def ports(row, pattern, stem, filtration):
    return set(next(p["ports"] for p in row["probes"]
                    if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))


@pytest.fixture(scope="module")
def mixed_charts(project):
    return chart(project, mixed_images(project), [3, 4], [
        ("S11", 1, 1), ("S11", 9, 1), ("S40", 0, 4), ("S40", 8, 4),
        ("S40", 4, 0), ("S51", 5, 1), ("S62V", 6, 2), ("S73V", 7, 3),
    ], {"stemMin": -1, "stemMax": 24, "filtrationMin": 0, "filtrationMax": 12})


@pytest.fixture(scope="module")
def two_charts(project):
    return chart(project, [workspace(project, TWO)], [2, 3, 4, 5, 6, 7, 9, 13, 23, 24], [
        ("I00", 0, 0), ("I00", 8, 0), ("I00", 16, 0), ("I00", 24, 0),
        ("I31", 7, 5), ("I31", 15, 5), ("I31", 23, 5),
    ], {"stemMin": -1, "stemMax": 25, "filtrationMin": 0, "filtrationMax": 12})[TWO]


def test_mixed_verified_rows_preserve_exact_witt_layer_and_no_pure_pin(project):
    for ws in mixed_images(project):
        claims = {p.id: p for p in ws.propositions}
        rows = [d for d in ws.differentials
                if claims[d.proposition_id].conclusion.get("fact_id") == "FN-MIX-001"]
        assert len(rows) == 5
        assert all(d.status == claims[d.proposition_id].status == "verified" for d in rows)
        assert all(d.page == 3 and d.period_stem == 8 for d in rows)
        nodes = {n.id: n for n in ws.classes}
        c_row = next(d for d in rows if nodes[d.source_id].style.get("e2_pattern") == "S11")
        conclusion = claims[c_row.proposition_id].conclusion
        spec = conclusion["coefficient_parameter"]
        assert spec["id"] == "mixed_d3_C"
        assert spec["value"] == 2 and spec["domain"] == [2]
        assert spec["frobenius_power"] == int(ws.settings.get("atlas_transport", {}).get("reflected", False))
        assert "coefficient_normalization" not in conclusion
        target = nodes[c_row.target_id]
        assert target.style["e2_pattern"] == "S40"
        assert target.style["two_valuation"] == 1
        assert target.style.get("j_order", 0) == 0
        assert not ws.settings.get("coefficient_assignments")


def test_actual_page_algebra_conjugates_zeta_not_the_witt_two_level(project):
    # The normal chart harness deliberately emits rendered objects, not map
    # coefficients. Load those same production modules in a small VM to inspect
    # coefficientState directly; no algebra is reimplemented here.
    script = r"""
const fs=require('node:fs'), vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for (const name of ['graded-quotient.js','vector-page-algebra.js','page-algebra.js'])
  vm.runInContext(fs.readFileSync('backend/static/'+name,'utf8'),context);
const app=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(app.slice(0,app.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.input=input;
const result=vm.runInContext(`
state.project=input.project;
input.workspaces.map(id=>{
  const ws=state.project.workspaces.find(w=>w.id===id), classes=new Map(ws.classes.map(c=>[c.id,c]));
  const claim=ws.propositions.find(p=>p.conclusion?.coefficient_parameter?.id==='mixed_d3_C');
  const row=ws.differentials.find(d=>d.proposition_id===claim.id);
  const shift=ws.settings.atlas_transport?.stem_shift||0;
  const bounds={stemMin:shift-1,stemMax:shift+24,filtrationMin:0,filtrationMax:12};
  return {id,states:[3,4].map(page=>{
    ws.page=page; const algebra=pageAlgebra(ws,bounds), pair=algebra.endpoints(row);
    return {page,coefficient:algebra.coefficientState(row),
      targetTwo:pair.target.style.two_valuation,targetJ:pair.target.style.j_order||0,
      targetComponents:pair.target.style.e2_components,
      zero:algebra.isZero(row),blocked:algebra.blockedFromPage,conflicts:algebra.conflicts};
  })};
})`,context);
process.stdout.write(JSON.stringify(result));
"""
    images = mixed_images(project)
    completed = subprocess.run(["node", "-e", script], cwd=ROOT,
                               input=json.dumps({"project": asdict(project), "workspaces": [w.id for w in images]}),
                               text=True, encoding="utf-8", capture_output=True, check=True, timeout=60)
    rows = json.loads(completed.stdout)
    assert len(rows) == 2
    for ws, result in zip(images, rows):
        expected = 3 if ws.settings.get("atlas_transport", {}).get("reflected") else 2
        for state in result["states"]:
            assert state["coefficient"]["resolved"]
            assert state["coefficient"]["value"] == expected
            assert (state["targetTwo"], state["targetJ"]) == (1, 0)
            assert state["targetComponents"] == {"S40": expected}
            assert not state["zero"] and state["blocked"] is None and not state["conflicts"]


def test_mixed_c_constant_dies_but_positive_j_tail_survives_in_both_atlases(project, mixed_charts):
    for ws in mixed_images(project):
        shift = ws.settings.get("atlas_transport", {}).get("stem_shift", 0)
        rows = mixed_charts[ws.id]
        for page in rows.values():
            assert page["blockedFromPage"] is None and not page["conflicts"]
            assert not page["dangling"]
        for stem in (1, 9):
            assert ports(rows[3], "S11", stem + shift, 1) == {"0:0", "0:1"}
            assert ports(rows[4], "S11", stem + shift, 1) == {"0:1"}
            assert "1:0" in ports(rows[3], "S40", stem - 1 + shift, 4)
            assert "1:0" not in ports(rows[4], "S40", stem - 1 + shift, 4)
        c_row = next(d for d in ws.differentials
                     if next(p for p in ws.propositions if p.id == d.proposition_id)
                     .conclusion.get("coefficient_parameter", {}).get("id") == "mixed_d3_C")
        assert c_row.id in rows[3]["rows"]
        assert c_row.id not in rows[4]["rows"]


def test_mixed_u_and_three_h1_closures_use_the_real_e3_e4_quotients(project, mixed_charts):
    for ws in mixed_images(project):
        shift = ws.settings.get("atlas_transport", {}).get("stem_shift", 0)
        rows = mixed_charts[ws.id]
        for pattern, stem, filtration in (("S40", 4, 0), ("S51", 5, 1),
                                           ("S62V", 6, 2), ("S73V", 7, 3)):
            assert "0:0" in ports(rows[3], pattern, stem + shift, filtration)
            assert "0:0" not in ports(rows[4], pattern, stem + shift, filtration)
        # A differential from the Witt odd layer does not turn its kernel into F4.
        assert {"1:0", "2:0", "3:0"} <= ports(rows[4], "S40", 4 + shift, 0)
        closures = [d.id for d in ws.differentials
                    if "formal_diff_mixed_d3_h1_" in d.id]
        assert len(closures) == 3 and set(closures) <= set(rows[3]["rows"])


def test_kernel_transfer_and_repaired_fn006_use_separate_certificates(project):
    ws = workspace(project, TWO)
    claims = {p.id: p for p in ws.propositions}
    nodes = {n.id: n for n in ws.classes}
    row = next(d for d in ws.differentials if d.id == "diff_two_d5_2D")
    assert row.status == claims[row.proposition_id].status == "verified"
    assert row.page == 5 and row.period_stem == 16
    assert nodes[row.source_id].style["two_valuation"] == 1
    assert nodes[row.target_id].style["two_valuation"] == 1
    zero = next(p for p in ws.propositions if p.conclusion.get("fact_id") == "FN-2I-005-zero")
    assert zero.kind == "zero-differential" and zero.status == "verified"
    assert zero.conclusion["page"] == 5
    cycle = next(p for p in ws.propositions if p.conclusion.get("fact_id") == TRANSFER_FACT)
    assert cycle.kind == "permanent-cycle" and cycle.status == "verified"
    assert cycle.conclusion["page"] == 2 and cycle.conclusion["period_stem"] == 64
    assert cycle.conclusion["cycle_constraint"] == "outgoing-only"
    source = nodes[cycle.conclusion.get("source_id", cycle.conclusion.get("class_id"))]
    assert source.grade.stem == source.grade.filtration == 0
    assert (source.style["e2_pattern"], source.style["two_valuation"], source.style.get("j_order", 0)) == ("I00", 1, 0)
    fate = derive_class_fate(ws, source.id, project=project)
    assert fate.conclusion == "permanent_cycle" and fate.last_hfpss_live_page == "infinity"
    assert fate.first_hfpss_death is None
    fn006 = next(d for d in ws.differentials if d.id == "diff_two_d5_xh1")
    assert fn006.status == claims[fn006.proposition_id].status == "verified"
    assert claims[fn006.proposition_id].conclusion["verification_certificate"]["method"] == (
        "coefficient Euler sequence and transfer naturality")


def test_two_sigma_odd_d5_kills_only_the_two_layer_and_even_d5_is_zero(two_charts):
    for page in (5, 6):
        assert two_charts[page]["blockedFromPage"] is None and not two_charts[page]["conflicts"]
        assert not two_charts[page]["dangling"]
    assert "diff_two_d5_2D" in two_charts[5]["rows"]
    assert "diff_two_d5_2D" not in two_charts[6]["rows"]
    for stem in (8, 24):
        assert "1:0" in ports(two_charts[5], "I00", stem, 0)
        assert "1:0" not in ports(two_charts[6], "I00", stem, 0)
        assert {"2:0", "3:0"} <= ports(two_charts[6], "I00", stem, 0)
        assert "1:0" in ports(two_charts[5], "I31", stem - 1, 5)
        assert "1:0" not in ports(two_charts[6], "I31", stem - 1, 5)
    assert "1:0" in ports(two_charts[5], "I00", 16, 0)
    assert "1:0" in ports(two_charts[6], "I00", 16, 0)


def test_two_u_is_not_confused_with_its_noncycle_d_multiples(two_charts):
    for page, row in two_charts.items():
        assert "1:0" in ports(row, "I00", 0, 0), f"2u2sigma was erased on E{page}"
    assert "1:0" not in ports(two_charts[6], "I00", 8, 0)
    assert "1:0" in ports(two_charts[6], "I00", 16, 0)
