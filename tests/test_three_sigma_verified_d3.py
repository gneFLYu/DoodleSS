"""Independent early 3-sigma d3 on the unmodified migrated project.

These are not research-hypothesis fixtures: no review row, claim, matrix or
coefficient assignment is changed.  Formal notes 678--700 use the earlier
two-sigma Thom differential and DKLLW's two one-sigma d3 propositions.  The
chosen pure Galois-fixed basis fixes F4 units, not the Witt factors 2 and 4.
In particular, d3(C)=0 is an early-page assertion, not the withdrawn Jan29
claim that Ck is a permanent cycle.
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


@pytest.fixture(scope="module")
def audit():
    project = migrate_project(demo_project())
    workspaces = [w for w in project.workspaces if w.id == "ws_3sigma_i" or
                  w.settings.get("atlas_transport", {}).get("source_workspace_id") == "ws_3sigma_i"]
    assert len(workspaces) == 3
    shifts = {w.id: w.settings.get("atlas_transport", {}).get("stem_shift", 0) for w in workspaces}
    probes = set()
    for shift in shifts.values():
        for repeat in (0, 8, 16):
            for pattern, stem, filtration in (
                ("S40", 4, 0), ("S33", 3, 3), ("S11", 1, 1),
                ("S51", 5, 1), ("S00", 4, 4),
                ("S62V", 6, 2), ("S11", 5, 5),
                ("S73V", 7, 3), ("S22H", 6, 6),
            ):
                probes.add((pattern, stem + repeat + shift, filtration))
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [3, 4], "vectorAudit": True,
        "boundsByWorkspace": {
            ident: {"stemMin": shift, "stemMax": shift + 23,
                    "filtrationMin": 0, "filtrationMax": 6}
            for ident, shift in shifts.items()
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
    }
    result = subprocess.run(
        ["node", "tests/chart_runtime.cjs"], cwd=ROOT, text=True, encoding="utf-8",
        input=json.dumps(payload), capture_output=True, check=True, timeout=90,
    )
    rows = {w["id"]: {page["page"]: page for page in w["pages"]} for w in json.loads(result.stdout)}
    return project, workspaces, shifts, rows


def ports(row, pattern, stem, filtration):
    return set(next(p["ports"] for p in row["probes"]
                    if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))


def test_independent_d3_and_d5_certificates_do_not_admit_the_january_claim(audit):
    _, workspaces, _, _ = audit
    for ws in workspaces:
        claims = {p.id: p for p in ws.propositions}
        d3 = [d for d in ws.differentials
              if d.page == 3 and claims[d.proposition_id].conclusion.get("fact_id") == "FN-3I-001"]
        assert len(d3) == 4
        for arrow in d3:
            claim = claims[arrow.proposition_id]
            assert arrow.status == claim.status == "verified"
            assert claim.conclusion["coefficient_normalization"]["value"] == 1
            assert claim.conclusion["period_stem"] == 8
            if arrow.linear_map_id:
                matrix = next(m for m in ws.differential_maps if m.id == arrow.linear_map_id)
                assert matrix.status == "verified"
        c_zero = next(p for p in ws.propositions if p.conclusion.get("fact_id") == "FN-3I-001-zero")
        assert c_zero.status == "verified" and c_zero.conclusion["page"] == 3
        q_d5 = next(p for p in ws.propositions if p.conclusion.get("fact_id") == "FN-3I-001-Q-zero")
        assert q_d5.status == "verified" and q_d5.conclusion["page"] == 5
        assert "d3_product_certificate" not in q_d5.conclusion
        certificate = q_d5.conclusion["verification_certificate"]
        assert certificate["status"] == "verified"
        assert "(0,6)" in certificate["derivation"] and "(4,2)" in certificate["derivation"]
        assert "not an implication from d3(C)=0" in q_d5.conclusion["derivation"]
        assert "No FN-3I-002, Jan29" in certificate["scope"]
        january = [p for p in ws.propositions if p.conclusion.get("fact_id") in {"FN-3I-010", "FN-3I-010-pc"}]
        assert january and all(p.status == "review" for p in january)
        assert not ws.settings.get("coefficient_assignments")


def test_primitive_d3_repeats_every_eight_stems_and_preserves_even_witt_layers(audit):
    _, workspaces, shifts, result = audit
    for ws in workspaces:
        e3, e4 = result[ws.id][3], result[ws.id][4]
        assert any(ident.endswith("diff_three_d3") for ident in e3["rows"]), {
            "workspace": ws.id, "rows": e3["rows"], "anchors": e3["anchors"],
            "conflicts": e3["conflicts"], "blockedFromPage": e3["blockedFromPage"],
            "endpoints": [{"differential": d.id,
                           "nodes": [{"id": node.id, "page": node.page, "archived": node.archived,
                                      "grade": asdict(node.grade), "style": node.style}
                                     for node in ws.classes if node.id in (d.source_id, d.target_id)]}
                          for d in ws.differentials if d.page == 3],
        }
        assert e3["edges"] >= 12  # Four actual arrow families in three D translates.
        for row in (e3, e4):
            assert not row["conflicts"] and row["blockedFromPage"] is None
            assert not row["dangling"]
        assert not e4["rows"]  # d3 is drawn on E3, not carried onto E4.
        for repeat in (0, 8, 16):
            shift = shifts[ws.id] + repeat
            before = ports(e3, "S40", 4 + shift, 0)
            after = ports(e4, "S40", 4 + shift, 0)
            assert {"0:0", "1:0", "2:0", "3:0"} <= before
            assert after == {port for port in before if not port.startswith("0:")}
            assert {"1:0", "2:0", "3:0"} <= after
            assert ports(e3, "S33", 3 + shift, 3)
            assert ports(e4, "S33", 3 + shift, 3) == set()


def test_h1_product_arrows_respect_constant_and_positive_j_directions(audit):
    _, workspaces, shifts, result = audit
    suffixes = {f"formal_diff_three_d3_h1_{n}_derived" for n in (1, 2, 3)}
    for ws in workspaces:
        e3, e4 = result[ws.id][3], result[ws.id][4]
        assert all(any(ident.endswith(suffix) for ident in e3["rows"]) for suffix in suffixes)
        for repeat in (0, 8, 16):
            shift = shifts[ws.id] + repeat
            for pattern, stem, filtration in (("S51", 5, 1), ("S62V", 6, 2), ("S73V", 7, 3)):
                assert ports(e3, pattern, stem + shift, filtration)
                assert ports(e4, pattern, stem + shift, filtration) == set()
            assert ports(e3, "S00", 4 + shift, 4)
            assert ports(e4, "S00", 4 + shift, 4) == set()
            for pattern, stem, filtration in (("S11", 5, 5), ("S22H", 6, 6)):
                assert {"0:0", "0:1"} <= ports(e3, pattern, stem + shift, filtration)
                assert ports(e4, pattern, stem + shift, filtration) == {"0:0"}


def test_c_zero_is_a_live_three_cycle_without_admitting_the_later_euler_claim(audit):
    _, workspaces, shifts, result = audit
    for ws in workspaces:
        e3, e4 = result[ws.id][3], result[ws.id][4]
        for repeat in (0, 8, 16):
            stem = 1 + shifts[ws.id] + repeat
            assert ports(e3, "S11", stem, 1) == {"0:0", "0:1"}
            assert ports(e4, "S11", stem, 1) == ports(e3, "S11", stem, 1)
