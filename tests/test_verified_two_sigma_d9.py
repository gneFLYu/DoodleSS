"""Verified two-sigma d9/d11 families in the actual production chart.

The migrated project is used without admitting review rows or assigning
unknown coefficients.  Two occurrences separated by 32 stems are a proved
differential pattern, not multiplication by a permanent D^4.  The Tate
certificates only constrain outgoing maps; their positive g multiples may
still be hit by the recorded d11.
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
FACTS = {"FN-2I-009", "FN-2I-010", "FN-2I-011"}
D9_SUFFIXES = {"formal_diff_fn-2i-010_1", "formal_diff_fn-2i-010_2", "diff_two_d9"}


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


def vector_probe(row, components, stem, filtration):
    return next(p for p in row["vectorProbes"]
                if p["components"] == components and (p["stem"], p["filtration"]) == (stem, filtration))


@pytest.fixture(scope="module")
def chart(project):
    workspaces = images(project)
    probes, vectors = set(), set()
    for ws in workspaces:
        shift = shift_of(ws)
        for repeat in (0, 32):
            for pattern, stem, filtration in (
                ("I31", 15, 5), ("I31", 27, 1),
                ("I22H", 14, 14), ("I22H", 26, 10), ("I22H", 26, 2),
                ("I11", 13, 13), ("I11", 17, 1), ("I11", 37, 5),
                ("I00", 16, 0),
            ):
                probes.add((pattern, stem + repeat + shift, filtration))
            for stem, filtration in ((14, 2), (25, 11)):
                vectors.add((stem + repeat + shift, filtration))
    vector_specs = []
    for stem, filtration in sorted(vectors):
        components = ({"I62X": 1, "I62Y": 1},) if filtration == 2 else (
            {"I13": 1}, {"I13X": 1}, {"I13": 1, "I13X": 1},
        )
        vector_specs.extend({"components": c, "stem": stem, "filtration": filtration} for c in components)
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [5, 7, 9, 10, 11, 12], "vectorAudit": True,
        "boundsByWorkspace": {
            w.id: {"stemMin": shift_of(w) - 64, "stemMax": shift_of(w) + 127,
                   "filtrationMin": 0, "filtrationMax": 24} for w in workspaces
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
        "vectorProbes": vector_specs,
    }
    result = subprocess.run(
        ["node", "tests/chart_runtime.cjs"], cwd=ROOT, input=json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8", check=True, timeout=150,
    )
    return {w["id"]: {p["page"]: p for p in w["pages"]} for w in json.loads(result.stdout)}


def test_verified_sources_keep_proof_and_pattern_metadata_in_all_three_atlases(project):
    for ws in images(project):
        claims = {p.id: p for p in ws.propositions}
        selected = [d for d in ws.differentials if claims[d.proposition_id].conclusion.get("fact_id") in FACTS]
        assert len(selected) == 4
        assert sorted(d.page for d in selected) == [9, 9, 9, 11]
        for row in selected:
            claim = claims[row.proposition_id]
            metadata = claim.conclusion
            assert row.status == claim.status == metadata["admission_status"] == "verified"
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"]
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["source_refs"] and certificate["derivation"]
            assert "formal_notes.tex" in " ".join(claim.source_refs)
            assert metadata["coefficient_normalization"]["value"] == 1
            assert row.period_stem == metadata["period_stem"] == 32
            assert metadata["period_kind"] == "repeated-differential-pattern"
            assert metadata["period_is_invertible"] is False
            if row.linear_map_id:
                matrix = next(m for m in ws.differential_maps if m.id == row.linear_map_id)
                assert matrix.status == "verified"
        assert not ws.settings.get("coefficient_assignments")


def test_two_layer_d9_rows_kill_exactly_the_surviving_witt_ports(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for repeat in (0, 32):
            offset = shift + repeat
            for stem, filtration in ((15, 5), (27, 1)):
                assert ports(rows[5], "I31", stem + offset, filtration) == {"0:0", "1:0"}
                assert ports(rows[7], "I31", stem + offset, filtration) == {"1:0"}
                assert ports(rows[9], "I31", stem + offset, filtration) == {"1:0"}
                assert ports(rows[10], "I31", stem + offset, filtration) == set()
            for stem, filtration in ((14, 14), (26, 10)):
                assert ports(rows[9], "I22H", stem + offset, filtration) == {"0:0"}
                assert ports(rows[10], "I22H", stem + offset, filtration) == set()


def test_leibniz_d9_kills_the_constant_line_but_not_the_positive_j_tail(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for stem in (26, 58):
            assert ports(rows[9], "I22H", stem + shift, 2) == {"0:0", "0:1"}
            for page in (10, 11, 12):
                assert ports(rows[page], "I22H", stem + shift, 2) == {"0:1"}


def test_leibniz_target_is_one_quotient_line_not_two_independent_dots(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for stem in (25, 57):
            h = vector_probe(rows[9], {"I13": 1}, stem + shift, 11)
            x = vector_probe(rows[9], {"I13X": 1}, stem + shift, 11)
            total = vector_probe(rows[9], {"I13": 1, "I13X": 1}, stem + shift, 11)
            assert h["live"] and x["live"] and not total["live"]
            assert len(h["slots"]) == 1 and h["slots"] == x["slots"]
            assert total["slots"] == []
            for components in ({"I13": 1}, {"I13X": 1}, {"I13": 1, "I13X": 1}):
                after = vector_probe(rows[10], components, stem + shift, 11)
                assert not after["live"] and after["slots"] == []


def test_h2_h6_certificates_are_constant_outgoing_constraints_not_hfpss_deaths(project):
    for ws in images(project):
        nodes, shift = {n.id: n for n in ws.classes}, shift_of(ws)
        for power in (2, 6):
            fact = f"DER-2I-TATE-H{power}-cycle"
            claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == fact)
            metadata = claim.conclusion
            assert claim.kind == "permanent-cycle" and claim.status == "verified"
            assert metadata["cycle_constraint"] == "outgoing-only"
            assert metadata["page"] == 2 and metadata["period_stem"] == 64
            assert metadata.get("coefficient_scope", "constant-two-multiples") != "all-multiples"
            assert metadata["forward_period"]["stem"] == 20
            assert metadata["forward_period"]["filtration"] == 4
            assert metadata["forward_period"]["nonnegative"] is True
            node = nodes[metadata.get("source_id", metadata.get("class_id"))]
            assert (node.grade.stem, node.grade.filtration) == (8 * power + 1 + shift, 1)
            assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                    node.style.get("j_order", 0)) == ("I11", 0, 0)
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"]
            comparison = metadata["comparison_certificate"]
            assert comparison["status"] == "verified" and comparison["spectral_sequence"] == "tate"


def test_outgoing_only_h_cycles_allow_the_recorded_d11_incoming_boundary(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for repeat in (0, 32):
            offset = repeat + shift
            # g^3 D^-8 H2/H6 are the known positive-filtration d11 targets.
            assert ports(rows[11], "I11", 13 + offset, 13) == {"0:0"}
            assert ports(rows[12], "I11", 13 + offset, 13) == set()
            assert vector_probe(rows[11], {"I62X": 1, "I62Y": 1}, 14 + offset, 2)["live"]
            assert not vector_probe(rows[12], {"I62X": 1, "I62Y": 1}, 14 + offset, 2)["live"]
            for page in (9, 10, 11, 12):
                assert ports(rows[page], "I11", 17 + offset, 1) == {"0:0", "0:1"}
                assert ports(rows[page], "I11", 37 + offset, 5) == {"0:0"}
        assert any(ident.endswith("diff_two_d11") for ident in rows[11]["rows"])
        assert not any(ident.endswith("diff_two_d11") for ident in rows[12]["rows"])


def test_positive_j_tate_certificates_do_not_certify_the_constant_witt_layer(project, chart):
    for ws in images(project):
        nodes, shift = {n.id: n for n in ws.classes}, shift_of(ws)
        for power in (2, 6):
            fact = f"DER-2I-TATE-JD{power}-cycle"
            claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == fact)
            metadata = claim.conclusion
            assert claim.kind == "permanent-cycle" and claim.status == "verified"
            assert metadata["cycle_constraint"] == "outgoing-only"
            assert metadata["page"] == 2 and metadata["period_stem"] == 64
            assert metadata["coefficient_scope"] == "constant-two-multiples"
            assert metadata["source_component"] == "positive-j" and metadata["covers"]
            source = nodes[metadata.get("source_id", metadata.get("class_id"))]
            assert (source.grade.stem, source.grade.filtration) == (8 * power + shift, 0)
            assert (source.style["e2_pattern"], source.style.get("two_valuation", 0),
                    source.style["j_order"]) == ("I00", 0, 1)
            comparison = metadata["comparison_certificate"]
            assert comparison["status"] == "verified" and comparison["spectral_sequence"] == "tate"
            assert comparison["page"] == 3
            # Nested evidence records the source workspace coordinates; atlas
            # transport changes the node's grade, not the original proof.
            assert comparison["source_bidegree"] == [8 * power + 1, -3]
            assert comparison["target_bidegree"] == [8 * power, 0]
            for row in chart[ws.id].values():
                assert {"0:1", "1:1", "2:1", "3:1"} <= ports(row, "I00", 8 * power + shift, 0)


def test_new_families_do_not_create_early_page_conflicts_or_dangling_arrows(project, chart):
    for ws in images(project):
        for row in chart[ws.id].values():
            assert row["blockedFromPage"] is None and not row["conflicts"]
            assert not [block for block in row["blocks"] if block["barriers"]]
            assert not row["dangling"]
        for suffix in D9_SUFFIXES:
            assert any(ident.endswith(suffix) for ident in chart[ws.id][9]["rows"])
            assert not any(ident.endswith(suffix) for ident in chart[ws.id][10]["rows"])


def test_actual_periodic_arrows_have_live_endpoints_and_admitted_maps(project):
    # The shared chart harness emits rows, including honest review previews.
    # Inspect the production algebra too, so visibility alone cannot satisfy
    # the admission test and all translated endpoints must genuinely be live.
    script = r"""
const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const context=vm.createContext({document:{body:{dataset:{}}},window:{}});
for(const name of ['graded-quotient.js','vector-page-algebra.js','page-algebra.js'])
  vm.runInContext(fs.readFileSync('backend/static/'+name,'utf8'),context);
const app=fs.readFileSync('backend/static/app.js','utf8');
vm.runInContext(app.slice(0,app.lastIndexOf('if (PAGE_MODE === "reviewing")')),context);
context.input=input;
const result=vm.runInContext(`
state.project=input.project;
input.workspaces.map(id=>{
  const ws=state.project.workspaces.find(w=>w.id===id),shift=ws.settings.atlas_transport?.stem_shift||0;
  const nodes=new Map(ws.classes.map(n=>[n.id,n]));
  const bounds={stemMin:shift-64,stemMax:shift+127,filtrationMin:0,filtrationMax:24};
  return {id,shift,pages:[9,11].map(page=>{
    ws.page=page;const algebra=pageAlgebra(ws,bounds);
    return {page,occurrences:periodicDifferentials(ws,bounds)
      .filter(e=>['FN-2I-009','FN-2I-010','FN-2I-011'].includes(e.diff.label))
      .map(e=>({row:e.diff.id,source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
        sourceLive:algebra.live(nodes.get(e.diff.source_id),e.sourceGrade),
        targetLive:algebra.live(nodes.get(e.diff.target_id),e.targetGrade)}))};
  })};
})`,context);
process.stdout.write(JSON.stringify(result));
"""
    payload = {"project": asdict(project), "workspaces": [w.id for w in images(project)]}
    result = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(payload),
                            text=True, encoding="utf-8", capture_output=True, check=True, timeout=90)
    rows = json.loads(result.stdout)
    assert len(rows) == 3
    for workspace in rows:
        shift = workspace["shift"]
        for page in workspace["pages"]:
            occurrences = page["occurrences"]
            assert occurrences
            assert all(e["admitted"] and e["sourceLive"] and e["targetLive"] for e in occurrences)
            assert all(e["coefficient"]["resolved"] and e["coefficient"]["value"] == 1 for e in occurrences)
            expected = ((15, 5), (27, 1), (26, 2)) if page["page"] == 9 else ((14, 2),)
            for stem, filtration in expected:
                for repeat in (0, 32):
                    assert any((e["source"]["stem"], e["source"]["filtration"]) ==
                               (stem + repeat + shift, filtration) for e in occurrences)
            for occurrence in occurrences:
                assert occurrence["target"]["stem"] == occurrence["source"]["stem"] - 1
                assert occurrence["target"]["filtration"] == occurrence["source"]["filtration"] + page["page"]
