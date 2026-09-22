"""Production two-sigma d21 families and their actual earlier-page quotients.

The tests do not admit claims, assign coefficients, or delete other maps.
Each atlas image runs in a fresh Node process with the full project retained.
The permanent D8 and forward-g translates are separate from a nonexistent
D4 period.  A surviving kernel is checked explicitly, not clipped away to
manufacture convergence.
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
ATLAS = {TWO, "ws_q8-ro-a0-b2", "ws_q8-ro-a2-b2"}
PAGES = (3, 4, 5, 6, 7, 8, 9, 10, 13, 14, 21, 22)
CASES = {
    "019": {"fact": "FN-2I-019", "stem": 55, "filtration": 5,
            "source": {"I31": 1}, "sourceTwo": 0,
            "target": {"I62X": 1, "I62Y": 1}, "targetTwo": 0},
    "019-low": {"fact": "FN-2I-019", "stem": 35, "filtration": 1,
                "source": {"I31": 1}, "sourceTwo": 0,
                "target": {"I62X": 1, "I62Y": 1}, "targetTwo": 0},
    "020": {"fact": "FN-2I-020", "stem": 1, "filtration": 3,
            "source": {"I13": 1}, "sourceTwo": 0,
            "target": {"I00": 1}, "targetTwo": 2},
    "021": {"fact": "FN-2I-021", "stem": 16, "filtration": 8,
            "source": {"I00": 1}, "sourceTwo": 2,
            "target": {"I31": 1}, "targetTwo": 0},
    "021-low": {"fact": "FN-2I-021", "stem": -4, "filtration": 4,
                "source": {"I00": 1}, "sourceTwo": 2,
                "target": {"I31": 1}, "targetTwo": 0},
    "021-f0": {"fact": "FN-2I-021", "stem": 40, "filtration": 0,
               "source": {"I00": 1}, "sourceTwo": 2,
               "target": {"I31": 1}, "targetTwo": 0},
}
TRANSLATES = [{"d8": d8, "g": g, "stem": 64 * d8 + 20 * g, "filtration": 4 * g}
              for d8 in (0, 1) for g in (0, 1)]


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    selected = [ws for ws in project.workspaces if ws.id == TWO or
                ws.settings.get("atlas_transport", {}).get("source_workspace_id") == TWO]
    assert {ws.id for ws in selected} == ATLAS
    return selected


def shift_of(workspace):
    return workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)


def record(workspace, case):
    claims = {p.id: p for p in workspace.propositions}
    nodes = {n.id: n for n in workspace.classes}
    rows = [d for d in workspace.differentials
            if claims[d.proposition_id].conclusion.get("fact_id") == case["fact"]
            and (nodes[d.source_id].grade.stem, nodes[d.source_id].grade.filtration)
            == (case["stem"] + shift_of(workspace), case["filtration"])]
    assert len(rows) == 1
    row = rows[0]
    return row, claims[row.proposition_id], nodes[row.source_id], nodes[row.target_id]


@pytest.fixture(scope="module")
def chart(project):
    harness = (ROOT / "tests" / "chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    # Only collect additional read-only observations from production algebra.
    diagnostics = r"""
    function probe(components,grade,two=0,j=0) {
      const style={e2_components:components,two_valuation:two,j_order:j};
      const entries=Object.entries(components);
      if(entries.length===1 && entries[0][1]===1) style.e2_pattern=entries[0][0];
      const node={style};
      return {components,two,j,live:algebra.live(node,grade),
        knownCycle:algebra.knownCycle(node,grade),trusted:algebra.inTrustedDomain(grade),
        slots:algebra.endpointSlots(node,grade)};
    }
    function block(members,grade) {
      const residue=((grade.stem%64)+64)%64;
      const value=algebra.vectorBlocks.get(members+':'+residue+':'+grade.filtration);
      return value ? {rank:value.q.dimension,barriers:value.barriers.length} : null;
    }
    const atlasShift=ws.settings.atlas_transport?.stem_shift||0;
    const d21Cases=Object.entries(input.d21Cases).flatMap(([name,spec])=>
      input.translates.map(delta=>{
        const sourceGrade={stem:spec.stem+atlasShift+delta.stem,
          filtration:spec.filtration+delta.filtration};
        const targetGrade={stem:sourceGrade.stem-1,filtration:sourceGrade.filtration+21};
        const source=probe(spec.source,sourceGrade,spec.sourceTwo);
        const target=probe(spec.target,targetGrade,spec.targetTwo);
        const selected=edges.filter(e=>e.diff.label===spec.fact
          && e.sourceGrade.stem===sourceGrade.stem
          && e.sourceGrade.filtration===sourceGrade.filtration);
        return {name,delta,sourceGrade,targetGrade,source,target,
          sourceTwo: name.startsWith('019') ? probe({I31:1},sourceGrade,1) : null,
          targetV: name.startsWith('019') ? probe({I62V:1},targetGrade) : null,
          targetX: name.startsWith('019') ? probe({I62X:1},targetGrade) : null,
          targetY: name.startsWith('019') ? probe({I62Y:1},targetGrade) : null,
          targetBlock: name.startsWith('019') ? block('I62X+I62Y',targetGrade) : null,
          sourceEight: name==='021-f0' ? probe({I00:1},sourceGrade,3) : null,
          sourceFourJ: name==='021-f0' ? probe({I00:1},sourceGrade,2,1) : null,
          otherSource: name==='020' ? probe({I13X:1},sourceGrade) : null,
          sumSource: name==='020' ? probe({I13:1,I13X:1},sourceGrade) : null,
          sourceBlock: name==='020' ? block('I13+I13X',sourceGrade) : null,
          rendered:selected.map(e=>({id:e.diff.id,status:e.diff.status,
            admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
            sourceLive:algebra.live(classes.get(e.diff.source_id),e.sourceGrade),
            targetLive:algebra.live(classes.get(e.diff.target_id),e.targetGrade)}))};
      }));
    return {d21Cases,d21Occurrences:edges.filter(e=>input.d21Facts.includes(e.diff.label))
      .map(e=>({fact:e.diff.label,source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),
        sourceLive:algebra.live(classes.get(e.diff.source_id),e.sourceGrade),
        targetLive:algebra.live(classes.get(e.diff.target_id),e.targetGrade)})),
      page, points: points.length"""
    payload = {"project": asdict(project), "pages": list(PAGES), "vectorAudit": True,
               "d21Cases": CASES, "d21Facts": sorted({c["fact"] for c in CASES.values()}),
               "translates": TRANSLATES}
    result = {}
    for ws in images(project):
        shift = shift_of(ws)
        completed = subprocess.run(
            ["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
            input=json.dumps({**payload, "workspaces": [ws.id],
                              "bounds": {"stemMin": shift - 6, "stemMax": shift + 140,
                                         "filtrationMin": 0, "filtrationMax": 34}}),
            text=True, encoding="utf-8", capture_output=True, check=True, timeout=180,
        )
        rows = json.loads(completed.stdout)
        assert [w["id"] for w in rows] == [ws.id]
        result[ws.id] = {row["page"]: row for row in rows[0]["pages"]}
    return result


def observations(chart, name, page):
    for ident, pages in chart.items():
        for occurrence in pages[page]["d21Cases"]:
            if occurrence["name"] == name:
                yield ident, occurrence


def test_d21_claims_are_independently_verified_with_d8_not_d4_periods(project):
    for ws in images(project):
        assert not ws.settings.get("coefficient_assignments")
        for case in CASES.values():
            row, claim, _, _ = record(ws, case)
            metadata = claim.conclusion
            assert row.status == claim.status == metadata["admission_status"] == "verified"
            assert row.page == metadata["page"] == 21
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"] and not metadata.get("machine_verification_pending")
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["method"] == "Published d23 product and finite E21 quotient"
            assert certificate["source_refs"] and certificate["premises"] and certificate["derivation"]
            comparison = certificate["table_comparison"]
            assert comparison["source"].startswith("table_Q8.tex:")
            assert comparison["table_period_stem"] == 64
            assert comparison["table_representative"] and comparison["relation_to_formal"]
            assert not {"FN-3I-010", "FN-3I-010-pc"} & set(certificate["premises"])
            assert row.period_stem == metadata["period_stem"] == 64
            assert metadata["period_kind"] == "same-object" and metadata["period_is_invertible"]
            assert metadata["period_multiplier"] == "D^8"
            assert metadata["coefficient_normalization"]["value"] == 1
            if row.linear_map_id:
                assert next(m for m in ws.differential_maps if m.id == row.linear_map_id).status == "verified"


def test_d21_endpoints_retain_exact_witt_layers_and_the_sum_target(project):
    for ws in images(project):
        for case in CASES.values():
            _, _, source, target = record(ws, case)
            stem, filtration = case["stem"] + shift_of(ws), case["filtration"]
            assert (source.grade.stem, source.grade.filtration) == (stem, filtration)
            assert (target.grade.stem, target.grade.filtration) == (stem - 1, filtration + 21)
            for node, components, two in ((source, case["source"], case["sourceTwo"]),
                                           (target, case["target"], case["targetTwo"])):
                actual = node.style.get("e2_components") or {node.style["e2_pattern"]: 1}
                assert actual == components
                assert node.style.get("two_valuation", 0) == two
                assert node.style.get("j_order", 0) == 0


def test_all_atlas_pages_and_d8_g_translates_use_actual_live_d21_endpoints(project, chart):
    assert set(chart) == ATLAS
    for ws in images(project):
        pages = chart[ws.id]
        assert list(pages) == list(PAGES)
        for page, row in pages.items():
            assert len(row["d21Cases"]) == len(CASES) * len(TRANSLATES)
            assert row["blockedFromPage"] is None, (ws.id, page, row["conflicts"])
            for item in row["d21Cases"]:
                assert item["source"]["trusted"] and item["target"]["trusted"]
                if page == 21:
                    assert item["source"]["live"] and item["target"]["live"], (ws.id, item)
                    assert item["rendered"], (ws.id, item)
                    for arrow in item["rendered"]:
                        assert arrow["status"] == "verified" and arrow["admitted"]
                        assert arrow["sourceLive"] and arrow["targetLive"]
                        assert arrow["coefficient"]["resolved"] and arrow["coefficient"]["value"] == 1
                else:
                    assert item["rendered"] == []
            assert bool(row["d21Occurrences"]) is (page == 21)
            assert all(e["admitted"] and e["sourceLive"] and e["targetLive"]
                       for e in row["d21Occurrences"])
            assert not [d for d in row["dangling"] if any(d["id"].endswith(record(ws, c)[0].id)
                                                            for c in CASES.values())]


def test_no_d21_family_is_invented_thirty_two_stems_away(project, chart):
    for ws in images(project):
        arrows = chart[ws.id][21]["d21Occurrences"]
        for case in CASES.values():
            assert not any(e["fact"] == case["fact"]
                           and e["source"] == {"stem": case["stem"] + shift_of(ws) + 32,
                                                "filtration": case["filtration"]}
                           for e in arrows)


def test_fn019_keeps_the_odd_source_after_its_two_layer_dies_at_d5(chart):
    for name in ("019", "019-low"):
        for page in PAGES:
            for ident, item in observations(chart, name, page):
                assert item["source"]["live"] is (page <= 21), (ident, page, item)
                low_two_survivor = name == "019-low" and item["delta"]["g"] == 0
                assert item["sourceTwo"]["live"] is (low_two_survivor or page <= 5), (ident, page, item)
                assert item["targetV"]["live"] is (page == 3), (ident, page, item)
                assert item["target"]["live"] is (page <= 21), (ident, page, item)
                # This is the d5 kernel span(X+Y), not a target quotient X=Y:
                # the individual columns support equal nonzero outgoing maps.
                assert item["targetX"]["live"] is (page <= 5), (ident, page, item)
                assert item["targetY"]["live"] is (page <= 5), (ident, page, item)
                expected_rank = 2 if page <= 5 else 1 if page <= 21 else 0
                assert item["targetBlock"] == {"rank": expected_rank, "barriers": 0}, (ident, page, item)


def test_fn020_has_a_rank_one_map_and_preserves_only_the_low_kernel_at_e22(chart):
    for page in PAGES:
        for ident, item in observations(chart, "020", page):
            assert item["source"]["live"] is (page <= 21), (ident, page, item)
            assert item["otherSource"]["live"] is (page <= 21), (ident, page, item)
            assert item["target"]["live"] is (page <= 21), (ident, page, item)
            high = item["delta"]["g"] > 0
            sum_live = not high or page <= 5
            assert item["sumSource"]["live"] is sum_live, (ident, page, item)
            expected_rank = (2 if page <= 21 else 1) if not high else (
                2 if page <= 5 else 1 if page <= 21 else 0)
            assert item["sourceBlock"] == {"rank": expected_rank, "barriers": 0}, (ident, page, item)
            if page == 21 and not high:
                assert item["sumSource"]["knownCycle"], (ident, item)


def test_fn021_and_its_low_tate_translate_die_only_after_the_declared_d21(chart):
    for name in ("021", "021-low", "021-f0"):
        for page in PAGES:
            for ident, item in observations(chart, name, page):
                assert item["source"]["two"] == 2 and item["target"]["two"] == 0
                assert item["source"]["live"] is (page <= 21), (ident, page, item)
                assert item["target"]["live"] is (page <= 21), (ident, page, item)


def test_filtration_zero_d21_preserves_the_free_witt_tail_and_positive_j_ideal(chart):
    for page in PAGES:
        for ident, item in observations(chart, "021-f0", page):
            if item["delta"]["g"]:
                continue
            assert item["sourceGrade"]["filtration"] == 0
            assert item["sourceEight"]["live"], (ident, page, item)
            assert item["sourceFourJ"]["live"], (ident, page, item)


def test_table_representatives_are_distinct_verified_anchors_with_explicit_provenance(project):
    for ws in images(project):
        for name, suffix, line in (
            ("019-low", "formal_diff_two_d21_h2_low_derived", 407),
            ("021-f0", "formal_diff_two_d21_four_f0_derived", 409),
        ):
            row, claim, _, _ = record(ws, CASES[name])
            assert row.id.endswith(suffix)
            comparison = claim.conclusion["verification_certificate"]["table_comparison"]
            assert comparison["source"] == f"table_Q8.tex:{line}"
            assert comparison["table_period_stem"] == 64


def test_actual_production_late_quotient_vanishes_above_twenty_two_without_clipping(project):
    # This is the untouched production project, not the conditional-convergence
    # fixture.  The shared harness separately removes arrows only for its
    # no-clipping control, restores them, and reports that control as unmappedHigh.
    payload = {"project": asdict(project), "pages": [22, 24],
               "vectorAudit": True, "auditNoClipping": True}
    checked = set()
    for ws in images(project):
        shift = shift_of(ws)
        completed = subprocess.run(
            ["node", "tests/chart_runtime.cjs"], cwd=ROOT,
            input=json.dumps({**payload, "workspaces": [ws.id],
                              "bounds": {"stemMin": shift, "stemMax": shift + 63,
                                         "filtrationMin": 0, "filtrationMax": 64}}),
            text=True, encoding="utf-8", capture_output=True, check=True, timeout=180,
        )
        result = json.loads(completed.stdout)
        assert [row["id"] for row in result] == [ws.id]
        assert [row["page"] for row in result[0]["pages"]] == [22, 24]
        for row in result[0]["pages"]:
            assert row["blockedFromPage"] is None
            assert not row["conflicts"], (ws.id, row["page"], row["conflicts"])
            assert not [block for block in row["blocks"] if block["barriers"]]
            assert not row["dangling"], (ws.id, row["page"], row["dangling"])
            assert row["high"] == 0, (ws.id, row["page"], row["highPatterns"])
            assert row["unmappedHigh"] > 0, (ws.id, row["page"])
        checked.add(ws.id)
    assert checked == ATLAS
