"""Repaired FN014 in the actual, unmodified production chart runtime.

H1 and H5 give separate 32-stem d7 patterns modulo permanent D8.  Their
targets have only the two1 line on E7: FN003*h2 already hit the two2 line
by d5.  The d7 removes the I11 constant but not its positive-j tail.
Tate certificates constrain outgoing maps of a coupled vector, not the
individual summands, and do not protect forward-g images from incoming maps.
No fixture admits a reviewed differential or supplies a coefficient value.
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
FACT = "FN-2I-014"
ROW_SUFFIX = "formal_diff_fn-2i-014_1"
SUM = {"I13X": 1, "I13": 1}


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


def fact_claim(workspace, fact):
    return next(p for p in workspace.propositions if p.conclusion.get("fact_id") == fact)


def ports(row, pattern, stem, filtration):
    return set(next(p["ports"] for p in row["probes"]
                    if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))


def vector(row, components, stem, filtration):
    return next(p for p in row["vectorProbes"] if p["components"] == components
                and (p["stem"], p["filtration"]) == (stem, filtration))


@pytest.fixture(scope="module")
def chart(project):
    workspaces = images(project)
    probes, vectors = set(), set()
    for ws in workspaces:
        for sibling in (0, 32):
            for d8 in (-64, 0, 64):
                offset = shift_of(ws) + sibling + d8
                probes.add(("I11", 9 + offset, 1))
                probes.add(("I00", 8 + offset, 8))
                # FN003*h2 outgoing source; AH2 Tate-cycle seed and its g image.
                vectors.update(((9 + offset, 3), (17 + offset, 3), (37 + offset, 7)))
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [5, 6, 7, 8], "vectorAudit": True,
        "boundsByWorkspace": {
            w.id: {"stemMin": shift_of(w) - 64, "stemMax": shift_of(w) + 159,
                   "filtrationMin": 0, "filtrationMax": 24} for w in workspaces
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
        "vectorProbes": [{"components": components, "stem": s, "filtration": f}
                         for s, f in sorted(vectors)
                         for components in (SUM, {"I13X": 1}, {"I13": 1})],
    }
    completed = subprocess.run(
        ["node", "tests/chart_runtime.cjs"], cwd=ROOT, input=json.dumps(payload),
        text=True, encoding="utf-8", capture_output=True, check=True, timeout=150,
    )
    return {w["id"]: {p["page"]: p for p in w["pages"]} for w in json.loads(completed.stdout)}


def test_repaired_transfer_proof_is_verified_not_merely_pattern_admitted(project):
    for ws in images(project):
        claim = fact_claim(ws, FACT)
        row = next(d for d in ws.differentials if d.proposition_id == claim.id)
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
        assert certificate["method"] == "C4 d13 transfer and E2 Euler-kernel exclusion"
        assert {"FN-2I-003", "DER-2I-TATE-AH2-D2-cycle", "DER-2I-TATE-AH2-D6-cycle"} <= set(certificate["premises"])
        assert certificate["source_refs"] and certificate["derivation"]
        assert "formal_notes.tex" in " ".join(claim.source_refs)
        if row.linear_map_id:
            assert next(m for m in ws.differential_maps if m.id == row.linear_map_id).status == "verified"
        assert not ws.settings.get("coefficient_assignments")


def test_fn014_uses_i11_constant_and_the_two1_target_in_all_three_atlases(project):
    for ws in images(project):
        claim = fact_claim(ws, FACT)
        row = next(d for d in ws.differentials if d.proposition_id == claim.id)
        nodes = {n.id: n for n in ws.classes}
        source, target, shift = nodes[row.source_id], nodes[row.target_id], shift_of(ws)
        assert (source.grade.stem, source.grade.filtration) == (9 + shift, 1)
        assert (target.grade.stem, target.grade.filtration) == (8 + shift, 8)
        assert (source.style["e2_pattern"], source.style.get("two_valuation", 0),
                source.style.get("j_order", 0)) == ("I11", 0, 0)
        assert (target.style["e2_pattern"], target.style["two_valuation"],
                target.style.get("j_order", 0)) == ("I00", 1, 0)


def test_h1_and_h5_constants_die_on_e8_but_the_completed_j_tails_remain(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for base in (9, 41):
            for d8 in (-64, 0, 64):
                stem = base + shift + d8
                for page in (5, 6, 7):
                    assert ports(rows[page], "I11", stem, 1) == {"0:0", "0:1"}
                assert ports(rows[8], "I11", stem, 1) == {"0:1"}


def test_prior_d5_hits_four_then_fn014_hits_the_only_remaining_two_line(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for base in (8, 40):
            for d8 in (-64, 0, 64):
                stem = base + shift + d8
                assert ports(rows[5], "I00", stem, 8) == {"1:0", "2:0"}
                # d5((x^2+y^2)h2 D^(1,5)u)=4k^2D^(2,6)u.
                assert vector(rows[5], SUM, stem + 1, 3)["live"]
                assert not vector(rows[6], SUM, stem + 1, 3)["live"]
                assert ports(rows[6], "I00", stem, 8) == {"1:0"}
                assert ports(rows[7], "I00", stem, 8) == {"1:0"}
                assert ports(rows[8], "I00", stem, 8) == set()
        assert any(d.endswith("formal_diff_two_d5_h2_sum_derived") for d in rows[5]["rows"])


def test_ah2_tate_certificates_are_independent_coupled_vector_constraints(project):
    for ws in images(project):
        nodes, shift = {n.id: n for n in ws.classes}, shift_of(ws)
        for power in (2, 6):
            claim = fact_claim(ws, f"DER-2I-TATE-AH2-D{power}-cycle")
            metadata = claim.conclusion
            assert claim.kind == "permanent-cycle" and claim.status == "verified"
            assert metadata["admission_status"] == "verified"
            assert metadata["cycle_constraint"] == "outgoing-only"
            assert metadata["page"] == 2 and metadata["period_stem"] == 64
            assert metadata["forward_period"]["stem"] == 20
            assert metadata["forward_period"]["filtration"] == 4
            assert metadata["forward_period"]["nonnegative"] is True
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"]
            assert "FN-2I-003" in metadata["derived_from"]
            assert FACT not in metadata["derived_from"]
            source = nodes[metadata.get("source_id", metadata.get("class_id"))]
            assert (source.grade.stem, source.grade.filtration) == (8 * power + 1 + shift, 3)
            assert source.style["e2_components"] == metadata["e2_components"] == SUM
            assert source.style.get("two_valuation", 0) == source.style.get("j_order", 0) == 0
            comparison = metadata["comparison_certificate"]
            assert comparison["status"] == "verified" and comparison["spectral_sequence"] == "tate"
            assert comparison["page"] == 5
            # Nested proof coordinates remain in the original source workspace.
            assert comparison["source_bidegree"] == [8 * power + 2, -2]
            assert comparison["target_bidegree"] == [8 * power + 1, 3]


def test_h2_cube_complement_has_its_own_independent_fn011_tate_certificate(project):
    # A cycle on I13X+I13 alone does not certify either summand.  FN011
    # independently makes the I13 complement a negative-source Tate target.
    for ws in images(project):
        nodes, shift = {n.id: n for n in ws.classes}, shift_of(ws)
        for power in (1, 5):
            claim = fact_claim(ws, f"DER-2I-TATE-H2CUBE-D{power}-cycle")
            metadata = claim.conclusion
            assert claim.kind == "permanent-cycle" and claim.status == "verified"
            assert metadata["admission_status"] == "verified"
            assert metadata["cycle_constraint"] == "outgoing-only"
            assert metadata["page"] == 2 and metadata["period_stem"] == 64
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"]
            assert "FN-2I-011" in metadata["derived_from"]
            assert FACT not in metadata["derived_from"]
            assert metadata["forward_period"]["stem"] == 20
            assert metadata["forward_period"]["filtration"] == 4
            assert metadata["forward_period"]["nonnegative"] is True
            source = nodes[metadata.get("source_id", metadata.get("class_id"))]
            assert (source.grade.stem, source.grade.filtration) == (8 * power + 9 + shift, 3)
            assert source.style["e2_pattern"] == "I13"
            assert metadata["e2_components"] == {"I13": 1}
            assert (source.style.get("e2_components") or {"I13": 1}) == {"I13": 1}
            assert source.style.get("two_valuation", 0) == source.style.get("j_order", 0) == 0
            comparison = metadata["comparison_certificate"]
            assert comparison["status"] == "verified" and comparison["spectral_sequence"] == "tate"
            assert comparison["page"] == 9
            # Original proof coordinates, not the transported atlas coordinates.
            assert comparison["source_bidegree"] == [8 * power + 10, -6]
            assert comparison["target_bidegree"] == [8 * power + 9, 3]


def test_ah2_seed_survives_but_its_forward_g_sum_is_hit_not_both_summands(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for base in (17, 49):
            for d8 in (-64, 0, 64):
                stem = base + shift + d8
                for page in (5, 6, 7, 8):
                    assert vector(rows[page], SUM, stem, 3)["live"]
                # FN003 hits g*AH2. Outgoing-only does not confer immortality.
                target_stem = stem + 20
                assert vector(rows[5], SUM, target_stem, 7)["live"]
                assert not vector(rows[6], SUM, target_stem, 7)["live"]
                left = vector(rows[6], {"I13X": 1}, target_stem, 7)
                right = vector(rows[6], {"I13": 1}, target_stem, 7)
                assert left["live"] and right["live"]
                assert left["slots"] == right["slots"]


def test_transfer_two_cycle_does_not_protect_the_h5_target_from_incoming_d7(project, chart):
    for ws in images(project):
        claim = fact_claim(ws, "DER-2I-TRANSFER-TWO-cycle")
        assert claim.status == "verified"
        assert claim.conclusion["cycle_constraint"] == "outgoing-only"
        assert claim.conclusion["period_stem"] == 64
        for d8 in (-64, 0, 64):
            # (40,8)=g^2*(0,0); the certified two1 line is an incoming target.
            stem = 40 + shift_of(ws) + d8
            assert ports(chart[ws.id][7], "I00", stem, 8) == {"1:0"}
            assert ports(chart[ws.id][8], "I00", stem, 8) == set()


def test_fn014_arrows_draw_only_on_e7_without_new_conflicts_or_dangling_endpoints(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for row in rows.values():
            assert row["blockedFromPage"] is None and not row["conflicts"]
            assert not row["dangling"]
            assert not [block for block in row["blocks"] if block["barriers"]]
        assert any(d.endswith(ROW_SUFFIX) for d in rows[7]["rows"])
        for page in (5, 6, 8):
            assert not any(d.endswith(ROW_SUFFIX) for d in rows[page]["rows"])


def test_fn014_actual_maps_cover_both_d8_blocks_and_forward_g_with_unit_one(project):
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
    occurrences:periodicDifferentials(ws,bounds).filter(e=>e.diff.label==='FN-2I-014')
      .map(e=>{const pair=algebra.endpoints(e.diff);return {
        source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
        sourcePattern:pair.source.style.e2_pattern,targetPattern:pair.target.style.e2_pattern,
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
            assert (occurrence["sourcePattern"], occurrence["targetPattern"]) == ("I11", "I00")
            assert occurrence["sourceTwo"] == occurrence["sourceJ"] == occurrence["targetJ"] == 0
            assert occurrence["targetTwo"] == 1
            assert occurrence["target"]["stem"] == occurrence["source"]["stem"] - 1
            assert occurrence["target"]["filtration"] == occurrence["source"]["filtration"] + 7
        for sibling in (0, 32):
            for d8 in (-64, 0, 64):
                for g in (0, 1):
                    source = (9 + sibling + d8 + 20 * g + ws["shift"], 1 + 4 * g)
                    assert any((e["source"]["stem"], e["source"]["filtration"]) == source
                               for e in occurrences), (ws["id"], source)
