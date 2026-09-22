"""Production odd-three-sigma d9 families, without research admissions.

T=(x+y)h1^2 u, B=(x+y)h1 u and C=(h1+xv1)u.  The T-D3/D7,
B-D3/D7/D4/D8 and C-D3/D7 maps have independent Euler/product proofs.
Their actual E9 endpoints, Witt layer and quotient are tested in all three
atlas images, under permanent D8 and forward g=kD^3.  D4 siblings are
separate anchors, never a presumed D4-period at E9.  The jC zero maps are
only outgoing d9 constraints and must not revive earlier d3 boundaries.
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


THREE = "ws_3sigma_i"
ATLAS = {THREE, "ws_q8-ro-a0-b3", "ws_q8-ro-a1-b1"}
# power, source-pattern, source stem offset, source filtration,
# target-pattern, target two-valuation.  All endpoint j-orders are zero.
CASES = {
    "diff_three_d9_25": (3, "S13", 1, 3, "S40", 1),
    "formal_diff_three_d9_t_D7_sibling": (7, "S13", 1, 3, "S40", 1),
    "diff_three_d9_25b": (3, "S02", 0, 2, "S73", 0),
    "formal_diff_three_d9_b_D7_sibling": (7, "S02", 0, 2, "S73", 0),
    "formal_diff_three_d9_b_D4_euler_derived": (4, "S02", 0, 2, "S73", 0),
    "formal_diff_three_d9_b_D8_euler_derived": (8, "S02", 0, 2, "S73", 0),
    "formal_diff_three_d9_c_D3_euler_derived": (3, "S11", 1, 1, "S02", 0),
    "formal_diff_three_d9_c_D7_euler_derived": (7, "S11", 1, 1, "S02", 0),
}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    result = [w for w in project.workspaces if w.id == THREE or
              w.settings.get("atlas_transport", {}).get("source_workspace_id") == THREE]
    assert {w.id for w in result} == ATLAS
    return result


def shift_of(workspace):
    return workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)


def occurrences(workspace):
    for suffix, spec in CASES.items():
        power, pattern, ds, filtration, target, two = spec
        for d8 in (0, 64):
            for g in (0, 1):
                yield (suffix, pattern, target, two,
                       8 * power + ds + shift_of(workspace) + d8 + 20 * g,
                       filtration + 4 * g)


def ports(row, pattern, stem, filtration):
    return set(next(p["ports"] for p in row["probes"]
                    if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))


@pytest.fixture(scope="module")
def chart(project):
    workspaces = images(project)
    probes = set()
    for ws in workspaces:
        for _, source, target, _, stem, filtration in occurrences(ws):
            probes.add((source, stem, filtration))
            probes.add((target, stem - 1, filtration + 9))
            if target == "S73":
                probes.add(("S73V", stem - 1, filtration + 9))
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [3, 4, 5, 6, 7, 9, 10], "vectorAudit": True,
        "oddD9Suffixes": list(CASES),
        "boundsByWorkspace": {
            w.id: {"stemMin": 22 + shift_of(w), "stemMax": 150 + shift_of(w),
                   "filtrationMin": 0, "filtrationMax": 17} for w in workspaces
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
    }
    # Extend only the shared harness's read-only output.  Algebra, admission,
    # source coefficients and matrices are the untouched production objects.
    harness = (ROOT / "tests" / "chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""return {oddD9Occurrences: edges
      .filter(e => input.oddD9Suffixes.some(suffix => e.diff.id.endsWith(suffix)))
      .map(e => {const pair = algebra.endpoints(e.diff); return {
        id:e.diff.id,source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
        sourceLive:algebra.live(classes.get(e.diff.source_id),e.sourceGrade),
        targetLive:algebra.live(classes.get(e.diff.target_id),e.targetGrade),
        sourcePattern:pair.source.style.e2_pattern,targetPattern:pair.target.style.e2_pattern,
        sourceTwo:pair.source.style.two_valuation||0,targetTwo:pair.target.style.two_valuation||0,
        sourceJ:pair.source.style.j_order||0,targetJ:pair.target.style.j_order||0
      };}), page, points: points.length"""
    completed = subprocess.run(
        ["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
        input=json.dumps(payload), text=True, encoding="utf-8",
        capture_output=True, check=True, timeout=180,
    )
    return {w["id"]: {r["page"]: r for r in w["pages"]} for w in json.loads(completed.stdout)}


def test_all_eight_anchors_have_independent_verified_certificates(project):
    for ws in images(project):
        claims = {p.id: p for p in ws.propositions}
        selected = [d for d in ws.differentials if any(d.id.endswith(s) for s in CASES)]
        assert len(selected) == 8
        for row in selected:
            metadata = claims[row.proposition_id].conclusion
            assert row.status == claims[row.proposition_id].status == metadata["admission_status"] == "verified"
            assert row.page == metadata["page"] == 9
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"] and not metadata.get("withdrawn_dependencies")
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["method"] == "Euler products, finite target survival and h1 detection"
            assert certificate["source_refs"] and certificate["premises"] and certificate["derivation"]
            for dependency in [*metadata["derived_from"], *certificate["premises"]]:
                assert not any(token in dependency.lower() for token in (
                    "fn-3i-009", "fn-3i-010", "jan29", "jan.29", "jan 29", "2026-01-29", "vanishing",
                )), (row.id, dependency)
            assert row.period_stem == metadata["period_stem"] == 64
            assert metadata["period_kind"] == "same-object"
            assert metadata["period_is_invertible"] and metadata["period_multiplier"] == "D^8"
            if row.linear_map_id:
                assert next(m for m in ws.differential_maps if m.id == row.linear_map_id).status == "verified"


def test_exact_endpoint_layers_and_pure_galois_units_are_not_conflated(project):
    for ws in images(project):
        nodes = {n.id: n for n in ws.classes}
        claims = {p.id: p for p in ws.propositions}
        for suffix, (power, pattern, ds, filtration, target_pattern, target_two) in CASES.items():
            row = next(d for d in ws.differentials if d.id.endswith(suffix))
            source, target = nodes[row.source_id], nodes[row.target_id]
            metadata = claims[row.proposition_id].conclusion
            assert (source.grade.stem, source.grade.filtration) == (8 * power + ds + shift_of(ws), filtration)
            assert (target.grade.stem, target.grade.filtration) == (source.grade.stem - 1, filtration + 9)
            assert (source.style["e2_pattern"], target.style["e2_pattern"]) == (pattern, target_pattern)
            assert source.style.get("two_valuation", 0) == 0
            assert target.style.get("two_valuation", 0) == target_two
            assert source.style.get("j_order", 0) == target.style.get("j_order", 0) == 0
            parameter = metadata["coefficient_parameter"]
            assert parameter["value"] == 1 and parameter["domain"] == [1]
            assert parameter["fixed_reason"] == "pure-sigma-i-galois-fixed"
            assert parameter["frobenius_power"] == int(ws.settings.get("atlas_transport", {}).get("reflected", False))
            assert metadata["coefficient_normalization"]["admission_independent"] is True
        assert not ws.settings.get("coefficient_assignments")


def test_jc_constraints_are_verified_page_nine_zeros_not_permanent_cycles(project):
    for ws in images(project):
        nodes = {n.id: n for n in ws.classes}
        for power in (3, 7):
            fact = f"DER-3I-D9-JC-D{power}-zero"
            claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == fact)
            metadata = claim.conclusion
            source = nodes[metadata["source_id"]]
            assert claim.kind == "zero-differential"
            assert claim.status == metadata["admission_status"] == "verified"
            assert metadata["page"] == 9 and metadata["zero"] is True
            assert metadata["source_status"] == "independently-verified"
            assert metadata["verification_certificate"]["status"] == "verified"
            assert not metadata["source_blockers"]
            assert metadata["period_stem"] == 64
            assert metadata["forward_period"] == {
                "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
            }
            assert (source.grade.stem, source.grade.filtration) == (8 * power + 1 + shift_of(ws), 1)
            assert (source.style["e2_pattern"], source.style.get("j_order", 0),
                    source.style.get("two_valuation", 0)) == ("S11", 1, 0)
            assert not any(d.proposition_id == claim.id for d in ws.differentials)


def test_t_targets_are_finite_witt_two_layers_not_odd_f4_dots(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for _, source, target, two, stem, filtration in occurrences(ws):
            if source != "S13":
                continue
            assert (target, two) == ("S40", 1)
            at = (stem - 1, filtration + 9)
            assert {"0:0", "1:0", "0:1"} <= ports(rows[3], target, *at)
            for page in (4, 5, 6, 7, 9):
                assert ports(rows[page], target, *at) == {"1:0"}, (ws.id, page, at)
            assert ports(rows[10], target, *at) == set()


def test_finite_b_and_t_sources_and_all_targets_die_exactly_after_d9(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for _, source, target, two, stem, filtration in occurrences(ws):
            for page in (3, 4, 5, 6, 7, 9):
                assert "0:0" in ports(rows[page], source, stem, filtration), (ws.id, page, source, stem, filtration)
                if source in {"S02", "S13"}:
                    assert ports(rows[page], source, stem, filtration) == {"0:0"}
            assert "0:0" not in ports(rows[10], source, stem, filtration)
            assert ports(rows[9], target, stem - 1, filtration + 9) == {f"{two}:0"}
            assert ports(rows[10], target, stem - 1, filtration + 9) == set()
            if target == "S73":
                assert "0:0" in ports(rows[3], "S73V", stem - 1, filtration + 9)
                for page in (4, 5, 6, 7, 9, 10):
                    assert ports(rows[page], "S73V", stem - 1, filtration + 9) == set()


def test_c_positive_j_tails_survive_low_but_never_resurrect_high_d3_deaths(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for power in (3, 7):
            for d8 in (0, 64):
                stem = 8 * power + 1 + d8 + shift_of(ws)
                high = (stem + 20, 5)
                assert ports(rows[3], "S11", *high) == {"0:0", "0:1"}
                for page in (3, 4, 5, 6, 7, 9):
                    assert ports(rows[page], "S11", stem, 1) == {"0:0", "0:1"}
                assert ports(rows[10], "S11", stem, 1) == {"0:1"}
                for page in (4, 5, 6, 7, 9):
                    assert ports(rows[page], "S11", *high) == {"0:0"}
                assert ports(rows[10], "S11", *high) == set()


def test_actual_d9_arrows_cover_every_anchor_d8_and_g_with_live_endpoints(project, chart):
    for ws in images(project):
        drawn = chart[ws.id][9]["oddD9Occurrences"]
        assert drawn
        for item in drawn:
            assert item["admitted"] and item["sourceLive"] and item["targetLive"]
            assert item["coefficient"]["resolved"] and item["coefficient"]["value"] == 1
            assert item["sourceTwo"] == 0 and item["sourceJ"] == item["targetJ"] == 0
            assert item["target"]["stem"] == item["source"]["stem"] - 1
            assert item["target"]["filtration"] == item["source"]["filtration"] + 9
        for suffix, source, target, two, stem, filtration in occurrences(ws):
            matched = [item for item in drawn if item["id"].endswith(suffix) and
                       (item["source"]["stem"], item["source"]["filtration"]) == (stem, filtration)]
            assert len(matched) == 1, (ws.id, suffix, stem, filtration)
            assert (matched[0]["sourcePattern"], matched[0]["targetPattern"], matched[0]["targetTwo"]) == (source, target, two)


def test_no_early_conflicts_or_dead_endpoints_and_arrows_only_on_e9(project, chart):
    for ws in images(project):
        for page, row in chart[ws.id].items():
            assert row["blockedFromPage"] is None and not row["conflicts"], (ws.id, page, row["conflicts"])
            assert not row["dangling"], (ws.id, page, row["dangling"])
            assert not [b for b in row["blocks"] if b["barriers"]], (ws.id, page)
            assert bool(row["oddD9Occurrences"]) is (page == 9)
            for suffix in CASES:
                assert any(ident.endswith(suffix) for ident in row["rows"]) is (page == 9), (ws.id, page, suffix)
