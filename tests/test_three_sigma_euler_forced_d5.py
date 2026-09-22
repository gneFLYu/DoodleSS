"""Independently Euler-forced FN002 on the unmodified production chart.

The older verified-d5 file covers FN003--006 and the P/Q quotient.  This
file instead checks the finite S62 -> S13 map forced by FN-2I-010.  The
same-cell S62V column is an earlier d3 source, not a second d5 source.
One small batched chart-runtime invocation covers all three pure images.
No fixture changes admission, matrices, coefficients, or page algebra.
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


FACT = "FN-3I-002"
HIGH_ROW = "diff_three_d5_main"
LOW_ROW = "formal_diff_three_d5_tate_positive_derived"


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    result = [w for w in project.workspaces if w.id == "ws_3sigma_i" or
              w.settings.get("atlas_transport", {}).get("source_workspace_id") == "ws_3sigma_i"]
    assert len(result) == 3 and any(w.id == "ws_3sigma_i" for w in result)
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
        for repeat in (0, 16, 32, 48):
            offset = repeat + shift_of(ws)
            for stem, filtration in ((6, 2), (14, 10)):
                probes.add(("S62", stem + offset, filtration))
                probes.add(("S62V", stem + offset, filtration))
                probes.add(("S13", stem - 1 + offset, filtration + 5))
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [3, 4, 5, 6], "vectorAudit": True,
        "boundsByWorkspace": {
            w.id: {"stemMin": shift_of(w), "stemMax": shift_of(w) + 63,
                   "filtrationMin": 0, "filtrationMax": 16} for w in workspaces
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
    }
    # Add read-only diagnostics to the shared harness output, not a second
    # implementation or a second Node process. Visibility alone is not admission.
    harness = (ROOT / "tests" / "chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""return {forcedD5Occurrences: edges
      .filter(e => e.diff.label === 'FN-3I-002')
      .map(e => {const pair = algebra.endpoints(e.diff); return {
        id: e.diff.id, source: e.sourceGrade, target: e.targetGrade,
        admitted: algebra.canApply(e.diff), coefficient: algebra.coefficientState(e.diff),
        sourceLive: algebra.live(classes.get(e.diff.source_id), e.sourceGrade),
        targetLive: algebra.live(classes.get(e.diff.target_id), e.targetGrade),
        sourcePattern: pair.source.style.e2_pattern, targetPattern: pair.target.style.e2_pattern,
        sourceTwo: pair.source.style.two_valuation || 0, targetTwo: pair.target.style.two_valuation || 0,
        sourceJ: pair.source.style.j_order || 0, targetJ: pair.target.style.j_order || 0
      };}), page, points: points.length"""
    completed = subprocess.run(
        ["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
        input=json.dumps(payload), text=True, encoding="utf-8",
        capture_output=True, check=True, timeout=120,
    )
    return {w["id"]: {p["page"]: p for p in w["pages"]} for w in json.loads(completed.stdout)}


def test_fn002_has_an_independent_verified_euler_certificate_and_fixed_unit(project):
    for ws in images(project):
        claims = {p.id: p for p in ws.propositions}
        rows = [d for d in ws.differentials if claims[d.proposition_id].conclusion.get("fact_id") == FACT]
        assert len(rows) == 2
        for row in rows:
            claim = claims[row.proposition_id]
            metadata = claim.conclusion
            assert row.status == claim.status == metadata["admission_status"] == "verified"
            assert row.page == metadata["page"] == 5
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"]
            assert metadata["coefficient_normalization"]["value"] == 1
            assert row.period_stem == metadata["period_stem"] == 16
            assert metadata["period_kind"] == "repeated-differential-pattern"
            assert metadata["period_is_invertible"] is False
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["method"] == "Euler image and finite incoming-source exclusion"
            assert {"FN-2I-010", "FN-3I-001"} <= set(certificate["premises"])
            assert certificate["source_refs"] and certificate["derivation"]
            for premise in certificate["premises"]:
                lowered = premise.lower()
                assert not any(token in lowered for token in (
                    "jan29", "jan.29", "jan 29", "2026-01-29", "vanishing",
                    "fn-3i-007", "fn-3i-008", "fn-3i-010",
                ))
                assert premise != FACT
            if row.linear_map_id:
                assert next(m for m in ws.differential_maps if m.id == row.linear_map_id).status == "verified"
        assert not ws.settings.get("coefficient_assignments")


def test_high_and_tate_low_anchors_are_finite_constant_lines_not_witt_or_pq_columns(project):
    for ws in images(project):
        nodes, claims = {n.id: n for n in ws.classes}, {p.id: p for p in ws.propositions}
        for suffix, stem, filtration in ((HIGH_ROW, 14, 10), (LOW_ROW, 6, 2)):
            row = next(d for d in ws.differentials if d.id.endswith(suffix))
            source, target = nodes[row.source_id], nodes[row.target_id]
            assert (source.grade.stem, source.grade.filtration) == (stem + shift_of(ws), filtration)
            assert (target.grade.stem, target.grade.filtration) == (stem - 1 + shift_of(ws), filtration + 5)
            for node, pattern in ((source, "S62"), (target, "S13")):
                assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                        node.style.get("j_order", 0)) == (pattern, 0, 0)
            if suffix == LOW_ROW:
                metadata = claims[row.proposition_id].conclusion
                assert metadata["evidence_kind"] == "Tate-comparison-derived"
                assert metadata["comparison_source_filtration"] == 2
                assert metadata["comparison_target_filtration"] == 7
                assert metadata["comparison_translation"] == {
                    "g_exponent": -2, "D_exponent": 4, "spectral_sequence": "tate",
                }


def test_d3_removes_s62v_but_leaves_the_same_cell_finite_a_for_d5(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        for repeat in (0, 16, 32, 48):
            for base, filtration in ((6, 2), (14, 10)):
                stem = base + repeat + shift
                assert "0:0" in ports(rows[3], "S62V", stem, filtration)
                assert ports(rows[4], "S62V", stem, filtration) == set()
                assert ports(rows[5], "S62V", stem, filtration) == set()
                for page in (3, 4, 5):
                    assert ports(rows[page], "S62", stem, filtration) == {"0:0"}
        assert any(d.endswith("formal_diff_three_d3_h1_2_derived") for d in rows[3]["rows"])


def test_e5_to_e6_removes_exactly_the_forced_source_and_target_constant_ports(project, chart):
    for ws in images(project):
        rows, shift = chart[ws.id], shift_of(ws)
        # The +32 cases are the second independently sourced FN010 block;
        # +16 additionally checks the two-torsion Leibniz pattern.
        for repeat in (0, 16, 32, 48):
            for base, filtration in ((6, 2), (14, 10)):
                stem = base + repeat + shift
                for page in (3, 4, 5):
                    assert ports(rows[page], "S13", stem - 1, filtration + 5) == {"0:0"}
                assert ports(rows[5], "S62", stem, filtration) == {"0:0"}
                assert ports(rows[6], "S62", stem, filtration) == set()
                assert ports(rows[6], "S13", stem - 1, filtration + 5) == set()


def test_production_arrows_cover_both_blocks_with_live_endpoints_and_scalar_one(project, chart):
    for ws in images(project):
        occurrences, shift = chart[ws.id][5]["forcedD5Occurrences"], shift_of(ws)
        assert occurrences
        for occurrence in occurrences:
            assert occurrence["admitted"] and occurrence["sourceLive"] and occurrence["targetLive"]
            assert occurrence["coefficient"]["resolved"] and occurrence["coefficient"]["value"] == 1
            assert (occurrence["sourcePattern"], occurrence["targetPattern"]) == ("S62", "S13")
            assert occurrence["sourceTwo"] == occurrence["targetTwo"] == 0
            assert occurrence["sourceJ"] == occurrence["targetJ"] == 0
            assert occurrence["target"]["stem"] == occurrence["source"]["stem"] - 1
            assert occurrence["target"]["filtration"] == occurrence["source"]["filtration"] + 5
        for suffix, base, filtration in ((HIGH_ROW, 14, 10), (LOW_ROW, 6, 2)):
            for repeat in (0, 16, 32, 48):
                source = {"stem": base + repeat + shift, "filtration": filtration}
                assert any(e["id"].endswith(suffix) and e["source"]["stem"] == source["stem"]
                           and e["source"]["filtration"] == source["filtration"] for e in occurrences), (ws.id, suffix, source)


def test_fn002_only_draws_on_e5_and_adds_no_conflicts_or_dangling_arrows(project, chart):
    for ws in images(project):
        for page, row in chart[ws.id].items():
            assert row["blockedFromPage"] is None and not row["conflicts"]
            assert not row["dangling"]
            assert not [block for block in row["blocks"] if block["barriers"]]
            if page == 5:
                assert any(d.endswith(HIGH_ROW) for d in row["rows"])
                assert any(d.endswith(LOW_ROW) for d in row["rows"])
            else:
                assert row["forcedD5Occurrences"] == []
                assert not any(d.endswith((HIGH_ROW, LOW_ROW)) for d in row["rows"])
