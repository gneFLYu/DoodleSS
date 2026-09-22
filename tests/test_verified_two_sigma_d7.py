"""Verified FN-2I-012/013 in the production coefficient-sensitive chart.

No review differential, coefficient, or matrix is admitted in these fixtures.
The D3/D7 and D4/D8 blocks retain their separate 32-stem patterns.  A target
with Witt valuation one is not the same map as the valuation-two target,
and killing an I11 constant never deletes its completed positive-j tail.
Before d7, FN003*h2 has already hit the two2 layer at (24,8), while
FN005 has removed the two1 layer at (32,8) as an outgoing d5 source.
Thus each d7 target is one residual line, not a two-layer Witt group.
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
FACTS = {"FN-2I-012", "FN-2I-013"}
ROW_SUFFIXES = {"formal_diff_fn-2i-012_1", "formal_diff_fn-2i-013_1"}
EXPECTED_PREMISES = {"FN-2I-001", "FN-2I-003", "FN-2I-005", "FN-2I-006", "FN-2I-011"}


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


def sum_vector(row, stem):
    return next(p for p in row["vectorProbes"]
                if p["components"] == {"I13X": 1, "I13": 1}
                and (p["stem"], p["filtration"]) == (stem, 3))


@pytest.fixture(scope="module")
def chart(project):
    workspaces = images(project)
    probes, vectors = set(), set()
    for ws in workspaces:
        for repeat in (0, 32):
            for d8 in (-64, 0, 64):
                offset = shift_of(ws) + repeat + d8
                for pattern, stem, filtration in (
                    ("I11", 25, 1), ("I00", 24, 8),
                    ("I11", 33, 1), ("I00", 32, 8),
                    ("I11", 17, 1), ("I00", 16, 0),
                    ("I31", 31, 13),
                ):
                    probes.add((pattern, stem + offset, filtration))
                vectors.add(25 + offset)
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [5, 6, 7, 8, 9], "vectorAudit": True,
        "boundsByWorkspace": {
            w.id: {"stemMin": shift_of(w) - 64, "stemMax": shift_of(w) + 159,
                   "filtrationMin": 0, "filtrationMax": 24} for w in workspaces
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
        "vectorProbes": [{"components": {"I13X": 1, "I13": 1}, "stem": stem, "filtration": 3}
                         for stem in sorted(vectors)],
    }
    completed = subprocess.run(
        ["node", "tests/chart_runtime.cjs"], cwd=ROOT, input=json.dumps(payload),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=150,
    )
    return {w["id"]: {p["page"]: p for p in w["pages"]} for w in json.loads(completed.stdout)}


def test_d7_proofs_and_pure_units_are_verified_without_a_permanent_d4(project):
    for ws in images(project):
        claims = {p.id: p for p in ws.propositions}
        rows = [d for d in ws.differentials if claims[d.proposition_id].conclusion.get("fact_id") in FACTS]
        assert len(rows) == 2
        for row in rows:
            claim = claims[row.proposition_id]
            metadata = claim.conclusion
            assert row.status == claim.status == metadata["admission_status"] == "verified"
            assert row.page == metadata["page"] == 7
            assert row.period_stem == metadata["period_stem"] == 32
            assert metadata["period_kind"] == "repeated-differential-pattern"
            assert metadata["period_is_invertible"] is False
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"]
            assert metadata["coefficient_normalization"]["value"] == 1
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["method"] == "d9 product contradiction and exact Witt target quotient"
            assert EXPECTED_PREMISES <= set(certificate["premises"])
            assert certificate["source_refs"] and certificate["derivation"]
            assert "formal_notes.tex" in " ".join(claim.source_refs)
            if row.linear_map_id:
                assert next(m for m in ws.differential_maps if m.id == row.linear_map_id).status == "verified"
        assert not ws.settings.get("coefficient_assignments")


def test_two_and_four_targets_keep_different_witt_valuations_in_every_atlas(project):
    for ws in images(project):
        nodes, claims = {n.id: n for n in ws.classes}, {p.id: p for p in ws.propositions}
        shift = shift_of(ws)
        for fact, stem, two in (("FN-2I-012", 25, 1), ("FN-2I-013", 33, 2)):
            row = next(d for d in ws.differentials if claims[d.proposition_id].conclusion.get("fact_id") == fact)
            source, target = nodes[row.source_id], nodes[row.target_id]
            assert (source.grade.stem, source.grade.filtration) == (stem + shift, 1)
            assert (target.grade.stem, target.grade.filtration) == (stem - 1 + shift, 8)
            assert source.style["e2_pattern"] == "I11"
            assert source.style.get("two_valuation", 0) == source.style.get("j_order", 0) == 0
            assert target.style["e2_pattern"] == "I00"
            assert target.style["two_valuation"] == two and target.style.get("j_order", 0) == 0


def test_both_d7_families_remove_only_the_source_constant_and_keep_j_tails(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for stem in (25, 57, 33, 65):
            for d8 in (-64, 0, 64):
                translated = stem + shift + d8
                assert ports(rows[7], "I11", translated, 1) == {"0:0", "0:1"}
                assert ports(rows[8], "I11", translated, 1) == {"0:1"}
                assert ports(rows[9], "I11", translated, 1) == {"0:1"}


def test_d5_incoming_kills_four_then_d7_kills_the_remaining_two_line(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for stem in (24, 56):
            for d8 in (-64, 0, 64):
                translated = stem + shift + d8
                assert ports(rows[5], "I00", translated, 8) == {"1:0", "2:0"}
                # FN003*h2: d5((x^2+y^2)h2 D^(3,7)u)=4k^2 D^(4,8)u.
                # The sum is a genuine outgoing source, not either summand.
                assert sum_vector(rows[5], translated + 1)["live"]
                assert not sum_vector(rows[6], translated + 1)["live"]
                assert ports(rows[6], "I00", translated, 8) == {"1:0"}
                assert ports(rows[7], "I00", translated, 8) == {"1:0"}
                assert ports(rows[8], "I00", translated, 8) == set()
        assert any(ident.endswith("formal_diff_two_d5_h2_sum_derived") for ident in rows[5]["rows"])


def test_d5_outgoing_removes_two_then_d7_hits_the_remaining_four_line(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for stem in (32, 64):
            for d8 in (-64, 0, 64):
                translated = stem + shift + d8
                assert ports(rows[5], "I00", translated, 8) == {"1:0", "2:0"}
                # FN005's forward-g translate is d5(2k^2 D^(5,9)u)
                # =2k^3 h2 D^(5,9)u.  The two1 source is not a cycle.
                assert "1:0" in ports(rows[5], "I31", translated - 1, 13)
                assert "1:0" not in ports(rows[6], "I31", translated - 1, 13)
                assert ports(rows[6], "I00", translated, 8) == {"2:0"}
                assert ports(rows[7], "I00", translated, 8) == {"2:0"}
                assert ports(rows[8], "I00", translated, 8) == set()
        assert any(ident.endswith("diff_two_d5_2D") for ident in rows[5]["rows"])


def test_tate_cycles_do_not_protect_other_d_powers_from_incoming_maps(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        facts = {p.conclusion.get("fact_id"): p for p in ws.propositions}
        for power in (2, 6):
            assert facts[f"DER-2I-TATE-H{power}-cycle"].status == "verified"
            assert facts[f"DER-2I-TATE-JD{power}-cycle"].status == "verified"
            for row in rows.values():
                assert ports(row, "I11", 8 * power + 1 + shift, 1) == {"0:0", "0:1"}
                assert {"0:1", "1:1", "2:1", "3:1"} <= ports(row, "I00", 8 * power + shift, 0)
        # Despite those outgoing-only certificates, actual incoming d7 maps
        # must still remove their stated constant two/four target ports.
        assert "1:0" not in ports(rows[8], "I00", 24 + shift, 8)
        assert "2:0" not in ports(rows[8], "I00", 32 + shift, 8)


def test_d7_arrows_draw_on_e7_only_without_creating_local_conflicts(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for row in rows.values():
            assert row["blockedFromPage"] is None and not row["conflicts"]
            assert not row["dangling"]
            assert not [block for block in row["blocks"] if block["barriers"]]
        for suffix in ROW_SUFFIXES:
            assert any(ident.endswith(suffix) for ident in rows[7]["rows"])
            assert not any(ident.endswith(suffix) for ident in rows[8]["rows"])


def test_g_and_d8_translates_use_live_endpoints_and_distinct_target_layers(project):
    # Use the same production modules as chart_runtime, with extra output for
    # actual coefficient maps and each translated occurrence's liveness.
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
  ws.page=7;
  const nodes=new Map(ws.classes.map(n=>[n.id,n]));
  const bounds={stemMin:shift-64,stemMax:shift+159,filtrationMin:0,filtrationMax:24};
  const algebra=pageAlgebra(ws,bounds);
  return {id,shift,blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
    occurrences:periodicDifferentials(ws,bounds).filter(e=>['FN-2I-012','FN-2I-013'].includes(e.diff.label))
      .map(e=>{const pair=algebra.endpoints(e.diff);return {
        fact:e.diff.label,source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
        sourceTwo:pair.source.style.two_valuation||0,targetTwo:pair.target.style.two_valuation,
        sourceJ:pair.source.style.j_order||0,targetJ:pair.target.style.j_order||0,
        sourceLive:algebra.live(nodes.get(e.diff.source_id),e.sourceGrade),
        targetLive:algebra.live(nodes.get(e.diff.target_id),e.targetGrade)};})};
})`,context);
process.stdout.write(JSON.stringify(output));
"""
    payload = {"project": asdict(project), "workspaces": [w.id for w in images(project)]}
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(payload),
                               text=True, encoding="utf-8", capture_output=True, check=True, timeout=90)
    results = json.loads(completed.stdout)
    assert len(results) == 3
    for ws in results:
        assert ws["blocked"] is None and not ws["conflicts"]
        occurrences = ws["occurrences"]
        assert occurrences
        for occurrence in occurrences:
            assert occurrence["admitted"] and occurrence["sourceLive"] and occurrence["targetLive"]
            assert occurrence["coefficient"]["resolved"] and occurrence["coefficient"]["value"] == 1
            assert occurrence["sourceTwo"] == occurrence["sourceJ"] == occurrence["targetJ"] == 0
            assert occurrence["targetTwo"] == (1 if occurrence["fact"] == "FN-2I-012" else 2)
            assert occurrence["target"]["stem"] == occurrence["source"]["stem"] - 1
            assert occurrence["target"]["filtration"] == occurrence["source"]["filtration"] + 7
        for fact, base in (("FN-2I-012", 25), ("FN-2I-013", 33)):
            for sibling in (0, 32):
                for d8 in (-64, 0, 64):
                    for g in (0, 1):
                        stem = base + sibling + d8 + 20 * g + ws["shift"]
                        filtration = 1 + 4 * g
                        assert any(e["fact"] == fact and (e["source"]["stem"], e["source"]["filtration"]) ==
                                   (stem, filtration) for e in occurrences), (ws["id"], fact, stem, filtration)
