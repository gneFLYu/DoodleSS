"""Exercise finite same-cell linear combinations through the real renderer."""
import json
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.migrations import migrate_project
from domain.seed import demo_project


@pytest.fixture(scope="module")
def two_sigma():
    payload = {"project": asdict(migrate_project(demo_project())), "workspaces": ["ws_2sigma_i"],
               "pages": [2, 3, 4, 5, 6, 11, 12, 13, 14], "vectorAudit": True,
               "bounds": {"stemMin": 0, "stemMax": 63, "filtrationMin": 0, "filtrationMax": 32},
               "probes": [{"pattern":p, "stem":s, "filtration":f} for p,s,f in (
                   ("I40",12,0), ("I33",11,3), ("I00",4,4), ("I11",5,5), ("I22H",6,6))],
               "vectorProbes": [{"stem":s, "filtration":2,"components":c}
                                for s in (6,14,30) for c in ({"I62X":1,"I62Y":1},{"I62Y":1})]}
    result = subprocess.run(["node", "tests/chart_runtime.cjs"], cwd=ROOT, text=True,
                            encoding="utf-8", input=json.dumps(payload), capture_output=True, check=True)
    return json.loads(result.stdout)[0]["pages"]


def test_two_sigma_d5_changes_basis_and_keeps_exactly_its_kernel(two_sigma):
    def probe(page, stem, components):
        return next(p for row in two_sigma if row["page"] == page for p in row["vectorProbes"]
                    if p["stem"] == stem and p["components"] == components)
    a, b = {"I62X":1,"I62Y":1}, {"I62Y":1}
    assert probe(5, 6, a)["live"] and probe(5, 6, b)["live"]
    assert not probe(6, 6, a)["live"]
    assert probe(6, 6, b)["live"]
    assert probe(6, 14, a)["live"]
    assert not probe(6, 14, b)["live"]
    assert probe(11, 14, a)["live"] and not probe(12, 14, a)["live"]
    assert probe(13, 30, a)["live"] and not probe(14, 30, a)["live"]


def test_e2_named_sum_is_not_an_extra_independent_point(two_sigma):
    e2 = next(row for row in two_sigma if row["page"] == 2)
    for probe in e2["vectorProbes"]:
        finite = [p for p in probe["displayed"] if p.get("pattern") in {"I62X","I62Y"} or p.get("components")]
        assert len(finite) == 2, finite


def test_two_sigma_table_derived_d3_hits_j_ideals_not_whole_cells(two_sigma):
    e3 = next(row for row in two_sigma if row["page"] == 3)
    e4 = next(row for row in two_sigma if row["page"] == 4)
    expected = {f"formal_diff_two_d3_{key}_derived" for key in ("v6", "h1_1", "h1_2", "h1_3")}
    assert expected.issubset(e3["rows"])
    for pattern in ("I33", "I11", "I22H"):
        before = next(p for p in e3["probes"] if p["pattern"] == pattern)
        after = next(p for p in e4["probes"] if p["pattern"] == pattern)
        assert {"0:0", "0:1"}.issubset(before["ports"])
        assert "0:0" in after["ports"] and "0:1" not in after["ports"]
    square = next(p for p in e4["probes"] if p["pattern"] == "I40")
    assert "0:0" not in square["ports"] and "1:0" in square["ports"]
    assert not [c for c in e4["conflicts"] if "d_r^2" in c.get("reason", "")]


def test_no_unfilled_linear_directions_in_verified_two_sigma_d5_blocks(two_sigma):
    for row in two_sigma:
        assert not [c for c in row["conflicts"] if c.get("page") == 5 and "proper subspace" in c.get("reason", "")]


def test_declared_three_sigma_sum_descends_through_d5_then_d11():
    # An explicit research hypothesis, not a promotion of the persisted ledger.
    project = migrate_project(demo_project())
    workspace = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    hypotheses = {"FN-3I-001", "FN-3I-003", "FN-3I-005", "FN-3I-006", "FN-3I-009"}
    for arrow in workspace.differentials:
        if arrow.label in hypotheses:
            arrow.status = "admitted"
    for claim in workspace.propositions:
        if claim.conclusion.get("origin_fact_id") in hypotheses or claim.conclusion.get("fact_id") in hypotheses:
            claim.status = "admitted"
    for matrix in workspace.differential_maps:
        if any(d.linear_map_id == matrix.id and d.label in hypotheses for d in workspace.differentials):
            matrix.status = "admitted"
    payload = {"project": asdict(project), "workspaces": [workspace.id], "pages": [3,4,5,6,11,12],
               "bounds": {"stemMin":0,"stemMax":63,"filtrationMin":0,"filtrationMax":24},
               "vectorAudit": True,
               "vectorProbes": [{"stem":s,"filtration":f,"components":c}
                                for s,f in ((6,6),(14,6),(30,14))
                                for c in ({"S22Y":1},{"S22H":1},{"S22Y":1,"S22H":1})]}
    result = subprocess.run(["node","tests/chart_runtime.cjs"],cwd=ROOT,text=True,encoding="utf-8",
                            input=json.dumps(payload),capture_output=True,check=True)
    rows = json.loads(result.stdout)[0]["pages"]
    def probe(page, stem, components):
        return next(p for r in rows if r["page"] == page for p in r["vectorProbes"]
                    if p["stem"] == stem and p["components"] == components)
    p, q, total = {"S22Y":1},{"S22H":1},{"S22Y":1,"S22H":1}
    assert probe(5,6,total)["live"]
    assert not probe(6,6,total)["live"]
    assert probe(6,6,p)["live"] and probe(6,6,q)["live"]
    assert probe(6,6,p)["slots"] == probe(6,6,q)["slots"]
    assert not probe(6,14,p)["live"] and not probe(6,14,q)["live"]
    assert probe(11,30,q)["live"] and not probe(12,30,q)["live"]
    assert not probe(12,30,p)["live"]
    e5 = next(r for r in rows if r["page"] == 5)
    assert "diff_three_d5_sum" in e5["rows"]  # matrix-backed arrow has periodic copies
    assert not [c for r in rows for c in r["conflicts"] if "d_r^2" in c.get("reason", "")]
