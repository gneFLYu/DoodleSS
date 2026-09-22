"""Counterfactual finite-candidate audit, NOT proof of Jan. 29 or new arrows.

This runs the pre-Euler-cutoff JS quotient with the declared formal rows as explicit
research hypotheses, including the withdrawn Jan. 29 d19/d23 and Euler claims.
Their explicit admission is confined to a deep copy. The nonzero pure-sector
F4 coefficients are independently fixed to 1 by the user's Galois-fixed basis;
they are not a free choice of parameters and do not admit any differential.
No persisted admission is changed and no vanishing-line pruning is enabled.
The independent verified Tate outgoing-cycle constraint is never removed.
It blocks the counterfactual Jan29 d23 already on E23; the recorded late
ports therefore describe the retained pre-quotient state, not convergence
or an independently certified finite forcing argument.

Write u=u_(3sigma_i), A=(x^2+y^2)u, C=(h1+xv1)u, P=(yh2+xh1v1)u,
Q=h1*C, B=(x+y)h1*u, R=x^2*h1*u, U=v1^2*u, and g=k*D^3.
The audited high classes are X=C*k^6*D^(5+4e), Y=R*k^5*D^(6+4e),
e=0,1.  Their distinct D^4 siblings are tested, not identified by a D^4 cycle.

Sources for exclusions: formal_notes.tex:678-705 (d3), 730-762 (d5),
764-779 (d9), 811-848 (d23), 851-860 (d19); DKLLW main.tex Table 6,
1334-1342 (permanent h1,h2,g), 1311-1315 (strong vanishing line).
The surviving d9 directions are candidates, not conclusions of these tests:
nonzero multiplication by g in this partial model is not, by itself, a proof
that another still-unknown differential cannot change that quotient.
"""
from copy import deepcopy
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
from domain.e2_import import verified_e2_classes
from test_three_sigma_convergence import TATE_CYCLE_ID, assert_absent_ad6_d19, assert_tate_cycle_conflict


HIGH = ((17, 25), (49, 25), (27, 23), (59, 23))
PROBES = [
    ("S11", 17, 25), ("S11", 49, 25), ("S11", 37, 29), ("S11", 5, 29),
    ("S73", 27, 23), ("S73", 59, 23), ("S73", 47, 27), ("S73", 15, 27),
    ("S73", 23, 35), ("S73", 55, 35),
    ("S02", 28, 6), ("S02", 60, 6), ("S02", 48, 10), ("S02", 16, 10),
    ("S40", 28, 0), ("S40", 60, 0), ("S40", 24, 12), ("S40", 56, 12),
    ("S40", 28, 16), ("S40", 60, 16),
    ("S62", 26, 30), ("S62", 58, 30),
    ("S00", 28, 20), ("S00", 60, 20),
    ("S22H", 18, 2), ("S22H", 50, 2), ("S22H", 38, 6), ("S22H", 6, 6),
]
EDGE_SOURCES = [
    (18, 22), (50, 22), (29, 17), (61, 17), (39, 3), (7, 3),
    (29, 5), (61, 5),
    (39, 1), (7, 1), (19, 13), (51, 13), (49, 1), (17, 1), (25, 3), (57, 3),
    (26, 30), (58, 30), (28, 16), (60, 16),
    (17, 25), (49, 25), (28, 14), (60, 14),
]


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


@pytest.fixture(scope="module")
def certificate(project):
    """Audit only the explicitly assumed, fixed-unit counterfactual model."""
    candidate = deepcopy(project)
    ws = next(w for w in candidate.workspaces if w.id == "ws_3sigma_i")
    # Preserve the pre-cutoff candidate audit without the later Euler-derived
    # rows covered separately in test_three_sigma_euler_cutoff.py.
    ws.differentials = [d for d in ws.differentials if not d.label.startswith("DER-3I-EULER-D9")]
    for row in ws.differentials:
        if row.label.startswith(("FN-", "DER-3I-D9")):
            row.status = "admitted"
    for claim in ws.propositions:
        if claim.conclusion.get("fact_id", "").startswith(("FN-", "DER-3I-D9")):
            claim.status = "admitted"
    admitted_ids = {d.linear_map_id for d in ws.differentials if d.status == "admitted"}
    for matrix in ws.differential_maps:
        if matrix.id in admitted_ids:
            matrix.status = "admitted"
    ws.settings["coefficient_assignments"] = dict.fromkeys(
        ("three_sigma_d9_D2", "three_sigma_d9_D6", "three_sigma_d9_CD3", "three_sigma_d9_CD7"), 1)
    payload = {
        "project": asdict(candidate), "workspaces": [ws.id], "pages": list(range(2, 25)),
        "bounds": {"stemMin": 0, "stemMax": 63, "filtrationMin": 0, "filtrationMax": 54},
        "vectorAudit": True, "highPoints": HIGH, "edgeSources": EDGE_SOURCES,
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in PROBES],
        "vectorProbes": [{"components": {"S22Y": 1, "S22H": 1}, "stem": s, "filtration": f}
                         for s, f in ((18, 2), (50, 2), (38, 6), (6, 6))]
                        + [{"components": c, "stem": s, "filtration": 18}
                           for s in (18, 50)
                           for c in ({"S22Y": 1}, {"S22H": 1}, {"S22Y": 1, "S22H": 1})],
    }
    # Instrument only the output of the existing harness, not its algebra.
    # Do not write a second JS renderer or an auxiliary generated file.
    driver = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "high: points.filter"
    assert driver.count(marker) == 1
    driver = driver.replace(marker, """
      candidateCells: input.highPoints.map(([s,f]) => ({stem:s,filtration:f,
        incoming: points.filter(p=>p.grade.stem===s+1 && p.grade.filtration===f-page),
        outgoing: points.filter(p=>p.grade.stem===s-1 && p.grade.filtration===f+page)
      })).map(c=>({...c,...Object.fromEntries(['incoming','outgoing'].map(direction=>
        [direction,c[direction].map(p=>({pattern:p.item.style?.e2_pattern,
          ports:p.modulePorts,terms:p.representativeTerms}))]))})),
      certificateEdges: edges.filter(e=>input.edgeSources.some(([s,f])=>
        e.sourceGrade.stem===s && e.sourceGrade.filtration===f)).map(e=>({
          id:e.diff.id,source:[e.sourceGrade.stem,e.sourceGrade.filtration],
          target:[e.targetGrade.stem,e.targetGrade.filtration]})),
      high: points.filter""")
    completed = subprocess.run(["node", "-e", driver], cwd=ROOT, text=True, encoding="utf-8",
                               input=json.dumps(payload), capture_output=True, check=True, timeout=120)
    return {row["page"]: row for row in json.loads(completed.stdout)[0]["pages"]}


def cells(entries):
    """Union aliases of the same coefficient port, without merging P and Q."""
    result = {}
    for entry in entries:
        pattern = entry.get("pattern")
        if pattern:
            result.setdefault(pattern, set()).update(entry["ports"] or [])
        else:
            terms = sorted((t["pattern"], t["coefficient"], t["two"], t["j"])
                           for t in entry["terms"])
            assert terms == [("S22H", 1, 0, 0), ("S22Y", 1, 0, 0)]
            result["P+Q"] = {"0:0"}
    return result


def ports(certificate, page, pattern, stem, filtration):
    row = next(p for p in certificate[page]["probes"]
               if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration))
    return set(row["ports"])


def has_arrow(certificate, page, source, target):
    return any(e["source"] == list(source) and e["target"] == list(target)
               for e in certificate[page]["certificateEdges"])


def test_all_r2_through_r23_candidates_include_both_independent_blocks(certificate):
    # Missing keys mean genuinely empty source/target cells, not unrendered arrows.
    c_in = {3: {"S62": {"0:0"}, "S62V": {"0:0", "0:1"}},
            7: {"S22H": {"0:0"}}, 23: {"S22H": {"0:1"}, "P+Q": {"0:0"}}}
    c_out = {3: {"S40": {"0:0", "1:0", "0:1"}}, 9: {"S02": {"0:0"}}}
    r_in = {3: {"S00": {"0:0", "0:1"}}, 7: {"S40": {"1:0"}},
            9: {"S02": {"0:0"}}, 17: {"S02": {"0:0"}},
            23: {"S40": {"1:0", "2:0", "3:0", "1:1", "2:1", "3:1"}}}
    r_out = {3: {"S22Y": {"0:0"}, "S22H": {"0:0", "0:1"}},
             7: {"S62": {"0:0"}}}
    for page in range(2, 24):
        for point in certificate[page]["candidateCells"]:
            incoming, outgoing = (c_in, c_out) if point["filtration"] == 25 else (r_in, r_out)
            assert cells(point["incoming"]) == incoming.get(page, {})
            assert cells(point["outgoing"]) == outgoing.get(page, {})
    for page, row in certificate.items():
        if page < 23:
            for conflict in row["conflicts"]:
                assert page >= 19
                assert_absent_ad6_d19(conflict)
    assert all(row["blockedFromPage"] is None for page, row in certificate.items() if page < 23)
    for page in (23, 24):
        assert_tate_cycle_conflict(certificate[page])
    assert not [block for row in certificate.values() for block in row["blocks"] if block["barriers"]]


def test_existing_cycle_and_boundary_exclusions_are_occurrence_specific(certificate):
    # The g multiple of CD1 d11 has the exact finite Witt target below.
    # Its D5 sibling is not obtained by a D4-period translation.
    assert {"id": "formal_diff_three_d11_c_D1_euler_forced",
            "source": [29, 5], "target": [28, 16]} in certificate[11]["certificateEdges"]
    assert not has_arrow(certificate, 11, (61, 5), (60, 16))
    for shift in (0, 32):
        # d3(U*h1^2*k^5*D^4)=j*X: this removes jX, NOT the constant X.
        assert has_arrow(certificate, 3, (18 + shift, 22), (17 + shift, 25))
        assert ports(certificate, 7, "S11", 17 + shift, 25) == {"0:0"}
        # Incoming r3 source for R is already a d3 boundary, so d3^2 excludes it.
        assert has_arrow(certificate, 3, (29 + shift, 17), (28 + shift, 20))
        assert ports(certificate, 4, "S00", 28 + shift, 20) == set()
        # The r7 incoming candidate is a declared d23 source, but the
        # independent cycle certificate forbids that outgoing differential.
        # The historical D4-wide d19 remains a counterfactual hypothesis;
        # only its AD2 block now has an independent verified proof.
        # The independently verified CD1 d11 removes only the D1 block;
        # the D5 sibling retains its finite two-layer on this page.
        assert ports(certificate, 11, "S40", 28 + shift, 16) == {"1:0"}
        expected_after_cd1 = set() if shift == 0 else {"1:0"}
        for page in (12, 23, 24):
            assert ports(certificate, page, "S40", 28 + shift, 16) == expected_after_cd1
        assert not has_arrow(certificate, 23, (28 + shift, 16), (27 + shift, 39))
        assert ports(certificate, 19, "S62", 26 + shift, 30) == {"0:0"}
        assert has_arrow(certificate, 19, (26 + shift, 30), (25 + shift, 49)) == (shift == 0)
        assert ports(certificate, 20, "S62", 26 + shift, 30) == (set() if shift == 0 else {"0:0"})
    assert {"id": "formal_diff_three_d19_a_D2_euler_forced",
            "source": [26, 30], "target": [25, 49]} in certificate[19]["certificateEdges"]
    # AD6 g^7 D^-16 remains, with the precise absent-target diagnostic,
    # rather than inheriting the AD2 g^7 D^-16 differential by a false D4 period.
    ad6_conflicts = [conflict for conflict in certificate[19]["conflicts"]
                    if conflict.get("source", {}).get("stem") == 58
                    and conflict["source"]["filtration"] == 30]
    assert len(ad6_conflicts) == 1
    assert_absent_ad6_d19(ad6_conflicts[0])


def test_c_r7_candidate_is_the_euler_product_line_with_empty_2sigma_target(certificate):
    # In E7, Q*k^4*D^(4+4e) = P*k^4*D^(4+4e), not two independent classes:
    # d5(a*k^3*D^(4+4e)) kills their sum.  P is the Euler product of
    # h2*k^4*D^(4+4e)*u_(2sigma), by formal_notes.tex:734-741.
    # This d5 row is an explicit hypothesis of the fixture; its residue
    # coefficient is independently fixed to 1. The h2 factor is a 5-cycle
    # by FN-2I-004 and the D-Leibniz cancellation.
    # Its possible d7 target (18+32e,24) is empty even on the integer E2 pattern.
    integer = verified_e2_classes("integer")

    def e2_columns(stem, filtration):
        columns = set()
        for anchor in integer:
            steps, remainder = divmod(filtration - anchor.filtration, 4)
            if steps >= 0 and remainder == 0 and (stem - anchor.stem - 20 * steps) % 64 == 0:
                columns.add(anchor.pattern_key)
        return columns

    for shift in (0, 32):
        assert has_arrow(certificate, 5, (19 + shift, 13), (18 + shift, 18))
        for probe in certificate[7]["vectorProbes"]:
            if (probe["stem"], probe["filtration"]) == (18 + shift, 18):
                assert probe["live"] == (len(probe["components"]) == 1)
        assert e2_columns(19 + shift, 17) == {"I31"}
        assert e2_columns(18 + shift, 24) == set()


def test_g_annihilator_obstructions_keep_the_coefficient_and_j_ports(certificate):
    for shift in (0, 32):
        reduced = lambda s: (s + shift) % 64  # ONLY the permanent D^8 period
        # At r23, incoming C candidates are (P+Q)D^(2+4e) and jQD^(2+4e).
        # Their g images are respectively d5 and d3 boundaries in (38+32e,6).
        assert has_arrow(certificate, 5, (reduced(39), 1), (reduced(38), 6))
        assert has_arrow(certificate, 3, (reduced(39), 3), (reduced(38), 6))
        assert ports(certificate, 23, "S22H", 18 + shift, 2) == {"0:1"}
        assert ports(certificate, 23, "S22H", reduced(38), 6) == set()
        vectors = {(p["stem"], p["filtration"]): p["live"] for p in certificate[23]["vectorProbes"]}
        assert vectors[(18 + shift, 2)] is True
        assert vectors[(reduced(38), 6)] is False
        assert ports(certificate, 23, "S11", reduced(37), 29) == {"0:0"}  # gX
        # At r17, g times the candidate B*k*D^(4+4e) is killed by the OTHER
        # separately recorded C d9 block (also coefficient 1), whereas gY is still nonzero.
        assert ports(certificate, 17, "S02", 28 + shift, 6) == {"0:0"}
        assert has_arrow(certificate, 9, (reduced(49), 1), (reduced(48), 10))
        assert ports(certificate, 17, "S02", reduced(48), 10) == set()
        assert ports(certificate, 17, "S73", reduced(47), 27) == {"0:0"}
        # At r23, all six surviving Witt/j ports at (28+32e,0) are g^3-torsion:
        # the 2U port maps to a known d9 boundary; higher 2 and j ports vanish
        # already in positive filtration. Do not confuse this with U=0.
        assert ports(certificate, 23, "S40", 28 + shift, 0) == {
            "1:0", "2:0", "3:0", "1:1", "2:1", "3:1"}
        assert has_arrow(certificate, 9, (25 + shift, 3), (24 + shift, 12))
        assert ports(certificate, 23, "S40", 24 + shift, 12) == set()
        assert ports(certificate, 23, "S73", 23 + shift, 35) == {"0:0"}  # g^3Y


def test_unproved_directions_are_not_inserted_or_vanishing_clipped(project, certificate):
    for shift in (0, 32):
        # Conditional remaining choices: X --d9--> B*k^8*D^(6+4e), and
        # B*k^3*D^(5+4e) --d9--> Y. No direction or scalar is invented here.
        assert not has_arrow(certificate, 9, (17 + shift, 25), (16 + shift, 34))
        assert not has_arrow(certificate, 9, (28 + shift, 14), (27 + shift, 23))
        assert ports(certificate, 24, "S11", 17 + shift, 25) == {"0:0"}
        assert ports(certificate, 24, "S73", 27 + shift, 23) == {"0:0"}
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    rows = [d for d in ws.differentials if d.label.startswith("DER-3I-D9")]
    assert len(rows) == 6 and all(d.status == "verified" for d in rows)
    claims = {p.id: p for p in ws.propositions}
    for row in rows:
        proof = claims[row.proposition_id].conclusion["verification_certificate"]
        assert proof["status"] == "verified" and proof["no_withdrawn_premise"]
        assert not {"FN-3I-010", "FN-3I-010-pc"} & set(proof["premises"])
    january = [p for p in ws.propositions
               if p.conclusion.get("fact_id") in {"FN-3I-010", "FN-3I-010-pc"}]
    assert january
    assert all(p.status == "review" and p.conclusion["source_status"] == "withdrawn-proof"
               for p in january)
    independent = next(p for p in ws.propositions if p.id == TATE_CYCLE_ID)
    assert independent.status == "verified"
    assert independent.conclusion["cycle_constraint"] == "outgoing-only"
    assert not ws.settings.get("coefficient_assignments")
