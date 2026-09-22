"""Independently verified even-D three-sigma d9, without research admissions.

P=(yh2+xh1v1)u, C=(h1+xv1)u, Q=C*h1. The two independent D2/D6
blocks repeat by permanent D8 and forward g. At low filtration d9 leaves
P+Q and the positive-j Q ideal; at a forward-g translate FN006 already
made P+Q a d5 boundary and primitive d3 already killed the positive-j
C/Q ideals. Zero d9 certificates must not resurrect those earlier deaths.
The chosen pure-sector unit is 1; the withdrawn Jan29/Ck argument is not
admitted, assigned a coefficient, or used to obtain these quotients.
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
PATTERNS = {"p": ("S22Y", "S13"), "q": ("S22H", "S13"), "c": ("S11", "S02")}
SUM = {"S22Y": 1, "S22H": 1}
P = {"S22Y": 1}
Q = {"S22H": 1}
SKEW = {"S22Y": 1, "S22H": 2}
SUFFIXES = {f"formal_diff_three_d9_{column}_D{m}_derived" for column in PATTERNS for m in (2, 6)}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    result = [w for w in project.workspaces if w.id == THREE or
              w.settings.get("atlas_transport", {}).get("source_workspace_id") == THREE]
    assert len(result) == 3 and any(w.id == THREE for w in result)
    return result


def shift_of(workspace):
    return workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)


def ports(row, pattern, stem, filtration):
    return set(next(p["ports"] for p in row["probes"]
                    if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))


def vector(row, components, stem, filtration):
    return next(p for p in row["vectorProbes"] if p["components"] == components and
                (p["stem"], p["filtration"]) == (stem, filtration))


@pytest.fixture(scope="module")
def chart(project):
    workspaces = images(project)
    probes, vector_specs = set(), []
    for shift in sorted({shift_of(w) for w in workspaces}):
        for m in (2, 6):
            for d8 in (0, 64):
                for g in (0, 1):
                    offset = shift + 8 * m + d8 + 20 * g
                    for pattern, stem, filtration in (
                        ("S22Y", 2, 2), ("S22H", 2, 2), ("S11", 1, 1),
                        ("S13", 1, 11), ("S02", 0, 10),
                    ):
                        probes.add((pattern, stem + offset, filtration + 4 * g))
                    vector_specs.extend({"components": c, "stem": offset + 2,
                                         "filtration": 2 + 4 * g} for c in (P, Q, SUM, SKEW))
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [3, 4, 5, 6, 7, 9, 10], "vectorAudit": True,
        "boundsByWorkspace": {
            w.id: {"stemMin": 16 + shift_of(w), "stemMax": 135 + shift_of(w),
                   "filtrationMin": 0, "filtrationMax": 15} for w in workspaces
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
        "vectorProbes": vector_specs,
    }
    # Read-only diagnostics around the actual renderer, in the same batched
    # runtime call. No harness file, model, matrix, or private algebra is changed.
    harness = (ROOT / "tests" / "chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""return {evenD9Occurrences: edges
      .filter(e => /^DER-3I-D9-[PQC](?:-|$)/.test(e.diff.label))
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
        capture_output=True, check=True, timeout=150,
    )
    return {w["id"]: {r["page"]: r for r in w["pages"]} for w in json.loads(completed.stdout)}


def test_six_maps_have_independent_verified_sources_without_january_dependencies(project):
    for ws in images(project):
        claims = {p.id: p for p in ws.propositions}
        nodes = {n.id: n for n in ws.classes}
        selected = [d for d in ws.differentials if any(d.id.endswith(s) for s in SUFFIXES)]
        assert len(selected) == 6
        for row in selected:
            metadata = claims[row.proposition_id].conclusion
            assert row.status == claims[row.proposition_id].status == metadata["admission_status"] == "verified"
            assert row.page == metadata["page"] == 9
            assert metadata["source_status"] == "independently-verified"
            assert not metadata["source_blockers"] and not metadata.get("withdrawn_dependencies")
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["source_refs"] and certificate["derivation"] and certificate["premises"]
            dependencies = [*metadata["derived_from"], *certificate["premises"]]
            for dependency in dependencies:
                lowered = dependency.lower()
                assert not any(token in lowered for token in (
                    "fn-3i-010", "jan29", "jan.29", "jan 29", "2026-01-29", "vanishing",
                )), (row.id, dependency)
            assert row.period_stem == metadata["period_stem"] == 64
            assert metadata["paired_pattern_stem"] == 32
            parameter = metadata["coefficient_parameter"]
            assert parameter["value"] == 1 and parameter["domain"] == [1]
            assert parameter["fixed_reason"] == "pure-sigma-i-galois-fixed"
            assert parameter["frobenius_power"] == int(ws.settings.get("atlas_transport", {}).get("reflected", False))
            assert metadata["coefficient_normalization"]["admission_independent"] is True
            source, target = nodes[row.source_id], nodes[row.target_id]
            m = 2 if "_D2_" in row.id else 6
            column = next(c for c in PATTERNS if f"three_d9_{c}_" in row.id)
            source_f = 1 if column == "c" else 2
            assert (source.grade.stem, source.grade.filtration) == (8 * m + source_f + shift_of(ws), source_f)
            assert (target.grade.stem, target.grade.filtration) == (source.grade.stem - 1, source_f + 9)
            assert (source.style["e2_pattern"], target.style["e2_pattern"]) == PATTERNS[column]
            assert source.style.get("two_valuation", 0) == target.style.get("two_valuation", 0) == 0
            assert source.style.get("j_order", 0) == target.style.get("j_order", 0) == 0
            if row.linear_map_id:
                assert next(a for a in ws.differential_maps if a.id == row.linear_map_id).status == "verified"
        january = [p for p in ws.propositions if p.conclusion.get("fact_id") in {"FN-3I-010", "FN-3I-010-pc"}]
        assert january and all(p.status == "review" for p in january)
        assert not ws.settings.get("coefficient_assignments")


def test_new_zero_certificates_are_exact_page_constraints_not_permanent_families(project):
    for ws in images(project):
        nodes = {n.id: n for n in ws.classes}
        zeros = [p for p in ws.propositions if p.kind == "zero-differential" and p.status == "verified"]
        a_zero = next(p for p in zeros if p.conclusion.get("fact_id") == "DER-3I-D5-A-EVEN")
        a_meta = a_zero.conclusion
        a_source = nodes[a_meta["source_id"]]
        assert a_meta["page"] == 5 and a_meta["period_stem"] == 16
        assert a_source.style["e2_pattern"] == "S62"
        assert a_source.grade.filtration == 2
        assert (a_source.grade.stem - shift_of(ws)) % 16 == 14
        assert a_source.style.get("j_order", 0) == a_source.style.get("two_valuation", 0) == 0

        # These are the independent early C/Q cycle obligations, not Ck pc.
        for fact, page, pattern, filtration in (
            ("DER-3I-D5-C-zero", 5, "S11", 1),
            ("DER-3I-D7-C-zero", 7, "S11", 1),
            ("DER-3I-D7-Q-zero", 7, "S22H", 2),
        ):
            claim = next(p for p in zeros if p.conclusion.get("fact_id") == fact)
            metadata = claim.conclusion
            source = nodes[metadata["source_id"]]
            assert metadata["page"] == page
            assert source.style["e2_pattern"] == pattern and source.grade.filtration == filtration
            assert source.style.get("j_order", 0) == 0
            assert metadata["source_status"] == "independently-verified"
            assert metadata["verification_certificate"]["status"] == "verified"

        for m in (2, 6):
            for pattern, filtration in (("S11", 1), ("S22H", 2)):
                location = (8 * m + filtration + shift_of(ws), filtration)
                matched = [p for p in zeros if p.conclusion.get("page") == 9 and
                           p.conclusion.get("source_id") in nodes and
                           nodes[p.conclusion["source_id"]].style.get("e2_pattern") == pattern and
                           nodes[p.conclusion["source_id"]].style.get("j_order", 0) == 1 and
                           (nodes[p.conclusion["source_id"]].grade.stem,
                            nodes[p.conclusion["source_id"]].grade.filtration) == location]
                assert len(matched) == 1, (ws.id, pattern, location)
                claim = matched[0]
                metadata = claim.conclusion
                column = "C" if pattern == "S11" else "Q"
                assert metadata["fact_id"] == f"DER-3I-D9-J{column}-D{m}-zero"
                assert metadata["period_stem"] == 64
                assert metadata["source_status"] == "independently-verified"
                assert metadata["verification_certificate"]["status"] == "verified"
                assert not metadata["source_blockers"]
                assert metadata["forward_period"]["stem"] == 20
                assert metadata["forward_period"]["filtration"] == 4
                assert metadata["forward_period"]["nonnegative"] is True
                assert nodes[metadata["source_id"]].style.get("two_valuation", 0) == 0
                assert not any(d.proposition_id == claim.id for d in ws.differentials)


def test_low_pq_has_a_rank_one_d9_and_keeps_sum_and_positive_j_kernel(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for m in (2, 6):
            for d8 in (0, 64):
                stem = 8 * m + 2 + d8 + shift_of(ws)
                for page in (5, 6, 7, 9):
                    assert ports(rows[page], "S22Y", stem, 2) == {"0:0"}
                    assert ports(rows[page], "S22H", stem, 2) == {"0:0", "0:1"}
                    assert all(vector(rows[page], c, stem, 2)["live"] for c in (P, Q, SUM, SKEW))
                assert vector(rows[10], SUM, stem, 2)["live"] is True
                assert len(vector(rows[10], SUM, stem, 2)["slots"]) == 1
                for components in (P, Q, SKEW):
                    assert vector(rows[10], components, stem, 2)["live"] is False
                assert ports(rows[10], "S22H", stem, 2) == {"0:1"}
                block = next(b for b in rows[10]["blocks"] if b["id"] == f"S22H+S22Y:{stem % 64}:2")
                assert block["rank"] == 2 and block["barriers"] == 0


def test_high_pq_sum_is_an_earlier_boundary_and_d9_kills_the_shared_constant(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for m in (2, 6):
            for d8 in (0, 64):
                stem = 8 * m + 22 + d8 + shift_of(ws)
                assert vector(rows[5], SUM, stem, 6)["live"] is True
                for page in (6, 7, 9):
                    assert vector(rows[page], SUM, stem, 6)["live"] is False
                    p, q = vector(rows[page], P, stem, 6), vector(rows[page], Q, stem, 6)
                    assert p["live"] and q["live"] and p["slots"] == q["slots"]
                    assert len(p["slots"]) == 1
                    displayed = [ports(rows[page], name, stem, 6) for name in ("S22Y", "S22H")]
                    assert sum(len(values) for values in displayed) == 1
                    assert set().union(*displayed) == {"0:0"}
                for components in (P, Q, SUM, SKEW):
                    assert not vector(rows[10], components, stem, 6)["live"]
                assert ports(rows[10], "S22Y", stem, 6) == set()
                assert ports(rows[10], "S22H", stem, 6) == set()


def test_zero_d9_tail_certificates_never_resurrect_high_d3_boundaries(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        for m in (2, 6):
            for d8 in (0, 64):
                offset = 8 * m + d8 + shift_of(ws)
                for pattern, stem, filtration in (("S11", 1, 1), ("S22H", 2, 2)):
                    low = (stem + offset, filtration)
                    high = (stem + offset + 20, filtration + 4)
                    assert "0:1" in ports(rows[3], pattern, *high)
                    for page in (4, 5, 6, 7, 9, 10):
                        assert "0:1" not in ports(rows[page], pattern, *high), (ws.id, pattern, high, page)
                        assert "0:1" in ports(rows[page], pattern, *low), (ws.id, pattern, low, page)
                for page in (3, 4, 5, 6, 7, 9):
                    assert ports(rows[page], "S11", offset + 1, 1) == {"0:0", "0:1"}
                assert ports(rows[10], "S11", offset + 1, 1) == {"0:1"}
                assert ports(rows[9], "S11", offset + 21, 5) == {"0:0"}
                assert ports(rows[10], "S11", offset + 21, 5) == set()


def test_actual_d9_arrows_cover_both_blocks_d8_and_g_with_live_finite_targets(project, chart):
    for ws in images(project):
        rows = chart[ws.id]
        occurrences = rows[9]["evenD9Occurrences"]
        assert occurrences
        for occurrence in occurrences:
            assert occurrence["admitted"] and occurrence["sourceLive"] and occurrence["targetLive"]
            assert occurrence["coefficient"]["resolved"] and occurrence["coefficient"]["value"] == 1
            assert (occurrence["sourcePattern"], occurrence["targetPattern"]) in PATTERNS.values()
            assert occurrence["sourceTwo"] == occurrence["targetTwo"] == 0
            assert occurrence["sourceJ"] == occurrence["targetJ"] == 0
            assert occurrence["target"]["stem"] == occurrence["source"]["stem"] - 1
            assert occurrence["target"]["filtration"] == occurrence["source"]["filtration"] + 9
        for m in (2, 6):
            for d8 in (0, 64):
                for g in (0, 1):
                    offset = 8 * m + d8 + 20 * g + shift_of(ws)
                    for column, (_, target_pattern) in PATTERNS.items():
                        f = 1 if column == "c" else 2
                        suffix = f"formal_diff_three_d9_{column}_D{m}_derived"
                        expected = (offset + f, f + 4 * g)
                        assert any(e["id"].endswith(suffix) and
                                   (e["source"]["stem"], e["source"]["filtration"]) == expected
                                   for e in occurrences), (ws.id, suffix, expected)
                        target = (offset + f - 1, f + 4 * g + 9)
                        assert ports(rows[9], target_pattern, *target) == {"0:0"}
                        assert ports(rows[10], target_pattern, *target) == set()


def test_no_early_conflicts_and_no_even_d9_arrow_on_other_pages(project, chart):
    for ws in images(project):
        for page, row in chart[ws.id].items():
            assert row["blockedFromPage"] is None and not row["conflicts"], (ws.id, page, row["conflicts"])
            assert not row["dangling"], (ws.id, page, row["dangling"])
            assert not [b for b in row["blocks"] if b["barriers"]], (ws.id, page)
            assert bool(row["evenD9Occurrences"]) is (page == 9)
            for suffix in SUFFIXES:
                assert any(ident.endswith(suffix) for ident in row["rows"]) is (page == 9), (ws.id, page, suffix)
