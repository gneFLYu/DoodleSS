"""Euler-product E13 cutoff for the two additional 3sigma B d9 directions.

The cutoff argument below remains an explicit historical research fixture.
The same two B rows now have separate production certificates using the
published 13-cycle D^-1*h1, with no Ck or Jan29 premise.
C=(h1+xv1)u, B=(x+y)h1*u, R=x^2*h1*u, U=v1^2*u, g=kD^3.
Table 8 rows 20/21, multiplied by g, give
  d13(2h2*k*D^(4+4e)) = x^2*k^4*D^(6+4e), e=0,1.
The permanent Euler class Ck annihilates the source: Ch2 is in the entirely
empty E2 cell (4,2), so cannot hide a 2-extension. Table 6 Cx^2=A*h1=R
then forces Y=R*k^5*D^(6+4e) to be zero already ON E13.

Unlike a partial-runtime vanishing argument, this gives an independent deadline.
Y has no early outgoing differential: it is the product of the permanent Ck
and an integer d13 target. Its possible d3 source is a d3 boundary. Its d7
source 2U*k^4*D^(5+4e) is h1 times the known d11 source R*k^3*D^(5+4e),
not excluded by circularly appealing to the later formal d23. The sole
remaining incoming length is d9. Tate multiplication by g^-3*D^8 gives
  d9(BD^(4+4e)) = mu_(4+4e)*R*k^2*D^(5+4e).
This historical argument is tested only under the explicitly admitted research
premises below: the Jan29 Ck/final-differential proof is now withdrawn. The
user's Galois-fixed pure-sector basis fixes the nonzero F4 units to 1,
independently of those proof statuses; assigning another unit is a conflict.

Source: DKLLW main.tex:1181,1185,1223,1586-1600,1911-1912,488-510;
formal_notes.tex:789-795 (d11), 799-808 (Euler Ck), 697 (h1 extension).
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
from domain.e2_import import verified_e2_classes
from domain.migrations import migrate_project
from test_three_sigma_convergence import assert_complete_january_conflicts
from domain.published_differentials import PUBLISHED_ARROWS
from domain.seed import demo_project


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def test_euler_b_records_have_independent_certificates_not_historical_cutoff_admission(project):
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    nodes, claims = {n.id: n for n in ws.classes}, {p.id: p for p in ws.propositions}
    for power in (4, 8):
        arrow = next(d for d in ws.differentials if d.id == f"formal_diff_three_d9_b_D{power}_euler_derived")
        claim = claims[arrow.proposition_id]
        source, target = nodes[arrow.source_id], nodes[arrow.target_id]
        assert (source.grade.stem, source.grade.filtration) == (8 * power, 2)
        assert (target.grade.stem, target.grade.filtration) == (8 * power - 1, 11)
        assert source.style["e2_pattern"] == "S02" and target.style["e2_pattern"] == "S73"
        assert arrow.page == 9 and arrow.period_stem == 64
        assert arrow.status == claim.status == "verified"
        certificate = claim.conclusion["verification_certificate"]
        assert certificate["status"] == "verified"
        assert certificate["method"] == "Euler products, finite target survival and h1 detection"
        assert certificate["no_withdrawn_premise"] is True
        assert "DKLLW24 D^-1 h1 13-cycle" in certificate["premises"]
        assert not {"FN-3I-010", "FN-3I-010-pc"} & set(certificate["premises"])
        assert claim.conclusion["fact_id"] == "DER-3I-EULER-D9-B"
        parameter = claim.conclusion["coefficient_parameter"]
        assert parameter["id"] == f"three_sigma_d9_BD{power}"
        assert parameter["value"] == 1 and parameter["domain"] == [1]
        assert parameter["fixed_reason"] == "pure-sigma-i-galois-fixed"
        assert claim.conclusion["coefficient_normalization"]["admission_independent"]
        provenance = json.dumps(claim.conclusion, ensure_ascii=False)
        assert "13" in provenance and "D^-1 h1" in provenance


def test_integer_rows_and_empty_ch2_cell_give_an_independent_cutoff():
    integer_rows = [r for r in PUBLISHED_ARROWS if r.workspace_id == "ws_integer"]
    for index, label, target, grade in (
        (19, r"2Dh_2", r"D^{-8}g^3d", (10, 14)),
        (20, r"2D^5h_2", r"D^{-4}g^3d", (42, 14)),
    ):
        row = integer_rows[index]
        assert (row.page, row.source_label, row.target_label) == (13, label, target)
        assert (row.target_stem, row.target_filtration) == grade
        # d=D^2*x^2, g=kD^3. After a further g the target is
        # x^2*k^4*D^6 / D^10, then Ck shifts it by (-3,5).
        e = index - 19
        assert (grade[0] + 20, grade[1] + 4) == (-2 - 16 + 8 * (6 + 4 * e), 18)
        assert (grade[0] + 20 - 3, grade[1] + 4 + 5) == (27 + 32 * e, 23)
    # An empty associated-graded group in every 2-adic degree leaves no hidden
    # 2-extension. This is stronger than only citing the printed relation Ch2=0.
    sigma = verified_e2_classes("sigma_i")
    assert not [a for a in sigma if a.filtration == 2 and a.stem % 8 == 4]


def runtime(project, old_units, new_units):
    candidate = deepcopy(project)
    ws = next(w for w in candidate.workspaces if w.id == "ws_3sigma_i")
    prefixes = ("FN-", "DER-3I-D9", "DER-3I-EULER-D9-B")
    for arrow in ws.differentials:
        if arrow.label.startswith(prefixes):
            arrow.status = "admitted"
    for claim in ws.propositions:
        if claim.conclusion.get("fact_id", "").startswith(prefixes):
            claim.status = "admitted"
    selected = {d.linear_map_id for d in ws.differentials if d.status == "admitted"}
    for matrix in ws.differential_maps:
        if matrix.id in selected:
            matrix.status = "admitted"
    ws.settings["coefficient_assignments"] = {
        "three_sigma_d9_D2": old_units[0], "three_sigma_d9_D6": old_units[1],
        "three_sigma_d9_BD4": new_units[0], "three_sigma_d9_BD8": new_units[1],
        "three_sigma_d9_CD3": old_units[0], "three_sigma_d9_CD7": old_units[0],
    }
    payload = {
        "project": asdict(candidate), "workspaces": [ws.id], "pages": [7, 9, 10, 11, 23, 24],
        "bounds": {"stemMin": -1, "stemMax": 64, "filtrationMin": 0, "filtrationMax": 40},
        "vectorAudit": True,
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in (
            ("S02", 32, 2), ("S02", 64, 2), ("S73", 31, 11), ("S73", 63, 11),
            ("S73", 27, 23), ("S73", 59, 23),
            ("S73", 27, 15), ("S73", 59, 15),  # d11 sources excluding the r7 alternatives
            ("S40", 28, 16), ("S40", 60, 16),
            ("S40", 12, 0), ("S40", 32, 4),
        )],
    }
    completed = subprocess.run(["node", "tests/chart_runtime.cjs"], cwd=ROOT, text=True, encoding="utf-8",
                               input=json.dumps(payload), capture_output=True, check=True, timeout=90)
    return {row["page"]: row for row in json.loads(completed.stdout)[0]["pages"]}


def test_counterfactual_euler_cutoff_preserves_early_pages_but_cannot_override_tate_cycle(project):
    # The project still uses the literal integer Table 8 normalization.
    pages = runtime(project, (1, 1), (1, 1))
    assert not [c for page, row in pages.items() if page < 23 for c in row["conflicts"]]
    for page in (23, 24):
        assert_complete_january_conflicts(pages[page])
    assert not [b for row in pages.values() for b in row["blocks"] if b["barriers"]]
    for power in (4, 8):
        assert f"formal_diff_three_d9_b_D{power}_euler_derived" in pages[9]["rows"]

    def ports(page, pattern, stem, filtration):
        return set(next(p["ports"] for p in pages[page]["probes"]
                        if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))

    for shift in (0, 32):
        assert ports(9, "S02", 32 + shift, 2) == {"0:0"}
        assert ports(9, "S73", 31 + shift, 11) == {"0:0"}
        assert ports(10, "S02", 32 + shift, 2) == set()
        assert ports(10, "S73", 31 + shift, 11) == set()
        assert ports(24, "S73", 27 + shift, 23) == set()
        # Independent early-cycle premise: known d11 source and its h1 product.
        assert ports(7, "S73", 27 + shift, 15) == {"0:0"}
        assert ports(11, "S73", 27 + shift, 15) == {"0:0"}
        assert ports(7, "S40", 28 + shift, 16) == {"1:0"}
        # Only the D1 block is now the independent CD1 d11 image; the D5
        # block is not inferred by a false D4 period.
        assert ports(23, "S40", 28 + shift, 16) == (set() if shift == 0 else {"1:0"})
    assert ports(23, "S40", 32, 4) == {"1:0"}
    assert "1:0" in ports(23, "S40", 12, 0)
    assert "formal_diff_fn-3i-010_2" not in pages[23]["rows"]
    # The independent outgoing-cycle certificate blocks the contradictory
    # quotient. Preserve the entire pre-d23 state, not a manufactured cutoff.
    assert pages[24]["high"] > 0
    assert [p["ports"] for p in pages[24]["probes"]] == [p["ports"] for p in pages[23]["probes"]]
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    assert all(d.status == "verified" for d in ws.differentials if d.label.startswith("DER-3I-EULER-D9-B"))
    assert not ws.settings.get("coefficient_assignments")


@pytest.mark.parametrize("unit", (2, 3))
def test_partial_euler_fixture_cannot_rescale_only_the_twisted_sector(project, unit):
    pages = runtime(project, (unit, unit), (unit, unit))
    for page in (10, 11, 23, 24):
        assert pages[page]["blockedFromPage"] == 9
        assert any(c["reason"] == "conflicting assignments for the same coefficient parameter"
                   for c in pages[page]["conflicts"])
    assert pages[24]["high"] > 0
