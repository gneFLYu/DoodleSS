"""Verified early 3-sigma d5, without admitting any later research hypotheses.

FN-3I-003--006 follow from the earlier verified d3, accepted FN-2I-004,
actual Euler/h2 products, and the pure Galois-fixed basis. The P+Q image
has rank one, while the hidden h2 product lands only on a constant even
Witt layer. Neither a vanishing-line cutoff nor the Jan29 proof is used.
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

D5_FACTS = {f"FN-3I-{number:03d}" for number in range(3, 7)}
D5_IDS = ("diff_three_d5_yh2", "diff_three_d5_x3", "diff_three_d5_xyD2", "diff_three_d5_sum")


@pytest.fixture(scope="module")
def audit():
    project = migrate_project(demo_project())
    workspaces = [w for w in project.workspaces if w.id == "ws_3sigma_i" or
                  w.settings.get("atlas_transport", {}).get("source_workspace_id") == "ws_3sigma_i"]
    assert len(workspaces) == 3
    shifts = {w.id: w.settings.get("atlas_transport", {}).get("stem_shift", 0) for w in workspaces}
    probes, vectors = set(), []
    for shift in sorted(set(shifts.values())):
        for repeat in (0, 8, 16, 24):
            for pattern, stem, filtration in (
                ("S11", 1, 1), ("S22Y", 2, 2), ("S22H", 2, 2), ("S71", 7, 1),
            ):
                probes.add((pattern, stem + repeat + shift, filtration))
        for repeat in (0, 16):
            for pattern, stem, filtration in (
                ("S53", 13, 3), ("S53", 9, 7), ("S40", 12, 8), ("S40", 12, 0),
                ("S22Y", 6, 6), ("S22H", 6, 6), ("S22Y", 14, 6), ("S22H", 14, 6),
            ):
                probes.add((pattern, stem + repeat + shift, filtration))
            for components in ({"S22Y": 1}, {"S22H": 1},
                               {"S22Y": 1, "S22H": 1}, {"S22Y": 1, "S22H": 2}):
                vectors.append({"components": components, "stem": 6 + repeat + shift, "filtration": 6})
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [5, 6], "vectorAudit": True,
        "boundsByWorkspace": {
            ident: {"stemMin": shift, "stemMax": shift + 31,
                    "filtrationMin": 0, "filtrationMax": 12}
            for ident, shift in shifts.items()
        },
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probes)],
        "vectorProbes": vectors,
    }
    result = subprocess.run(["node", "tests/chart_runtime.cjs"], cwd=ROOT,
                            input=json.dumps(payload), text=True, encoding="utf-8",
                            capture_output=True, check=True, timeout=90)
    rows = {ws["id"]: {row["page"]: row for row in ws["pages"]} for ws in json.loads(result.stdout)}
    return project, workspaces, shifts, rows


def ports(row, pattern, stem, filtration):
    return set(next(probe["ports"] for probe in row["probes"]
                    if (probe["pattern"], probe["stem"], probe["filtration"]) == (pattern, stem, filtration)))


def vector(row, components, stem, filtration=6):
    return next(probe for probe in row["vectorProbes"]
                if probe["components"] == components and (probe["stem"], probe["filtration"]) == (stem, filtration))


def test_early_d5_and_both_later_d9_blocks_have_separate_verified_admissions(audit):
    _, workspaces, _, _ = audit
    for ws in workspaces:
        claims = {p.id: p for p in ws.propositions}
        selected = [d for d in ws.differentials if claims[d.proposition_id].conclusion.get("fact_id") in D5_FACTS]
        assert len(selected) == 4
        for arrow in selected:
            claim = claims[arrow.proposition_id]
            assert arrow.page == 5 and arrow.status == claim.status == "verified"
            assert claim.conclusion["period_stem"] == 16
            assert claim.conclusion["coefficient_normalization"]["value"] == 1
            if arrow.linear_map_id:
                assert next(m for m in ws.differential_maps if m.id == arrow.linear_map_id).status == "verified"
        for fact, period in (("FN-3I-003-even-zero", 16), ("FN-3I-001-Q-zero", 8)):
            claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == fact)
            assert claim.status == "verified" and claim.conclusion["page"] == 5
            assert claim.conclusion["period_stem"] == period
        january = [p for p in ws.propositions if p.conclusion.get("fact_id") in {"FN-3I-010", "FN-3I-010-pc"}]
        assert january and all(p.status == "review" for p in january)
        even_d9_facts = {"DER-3I-D9-P", "DER-3I-D9-Q", "DER-3I-D9-C"}
        d9 = [d for d in ws.differentials if d.page == 9]
        even_d9 = [d for d in d9 if claims[d.proposition_id].conclusion.get("fact_id") in even_d9_facts]
        assert len(even_d9) == 6
        for row in even_d9:
            claim = claims[row.proposition_id]
            metadata = claim.conclusion
            assert row.status == claim.status == "verified" and row.period_stem == 64
            assert metadata["source_status"] == "independently-verified"
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["method"] == "Euler image, finite g-injection and h1 lift"
            assert certificate["source_refs"] and certificate["premises"]
            assert certificate["no_withdrawn_premise"] is True
            assert not {"FN-3I-010", "FN-3I-010-pc"} & set(certificate["premises"])
            assert not {"FN-3I-010", "FN-3I-010-pc"} & set(metadata["derived_from"])
        remaining_d9 = [d for d in d9 if claims[d.proposition_id].conclusion.get("fact_id") not in even_d9_facts]
        assert len(remaining_d9) == 8
        for row in remaining_d9:
            claim = claims[row.proposition_id]
            metadata = claim.conclusion
            assert row.status == claim.status == "verified" and row.period_stem == 64
            assert metadata["source_status"] == "independently-verified"
            certificate = metadata["verification_certificate"]
            assert certificate["status"] == "verified"
            assert certificate["method"] == "Euler products, finite target survival and h1 detection"
            assert certificate["source_refs"] and certificate["premises"]
            assert certificate["no_withdrawn_premise"] is True
            assert not {"FN-3I-010", "FN-3I-010-pc"} & set(certificate["premises"])
            assert not {"FN-3I-010", "FN-3I-010-pc"} & set(metadata["derived_from"])
        assert not ws.settings.get("coefficient_assignments")


def test_actual_d5_arrows_repeat_by_sixteen_stems_without_drawing_on_e6(audit):
    _, workspaces, shifts, result = audit
    for ws in workspaces:
        e5, e6 = result[ws.id][5], result[ws.id][6]
        assert all(any(ident.endswith(suffix) for ident in e5["rows"]) for suffix in D5_IDS), {
            "workspace": ws.id, "rows": e5["rows"], "anchors": e5["anchors"],
        }
        assert e5["edges"] >= 8 and not e6["rows"]
        for row in (e5, e6):
            assert not row["conflicts"] and row["blockedFromPage"] is None
            assert not row["dangling"]
        for repeat in (0, 16):
            shift = shifts[ws.id] + repeat
            for pattern, stem, filtration in (("S22Y", 10, 2), ("S53", 13, 3),
                                              ("S71", 15, 1), ("S71", 7, 1)):
                assert ports(e5, pattern, stem + shift, filtration) == {"0:0"}
                assert ports(e6, pattern, stem + shift, filtration) == set()


def test_zero_directions_preserve_low_q_power_series_and_even_d_p(audit):
    _, workspaces, shifts, result = audit
    for ws in workspaces:
        e5, e6 = result[ws.id][5], result[ws.id][6]
        for repeat in (0, 8, 16, 24):
            shift = shifts[ws.id] + repeat
            assert ports(e5, "S22H", 2 + shift, 2) == {"0:0", "0:1"}
            assert ports(e6, "S22H", 2 + shift, 2) == {"0:0", "0:1"}
            assert ports(e6, "S22Y", 2 + shift, 2) == ({"0:0"} if repeat % 16 == 0 else set())
            assert ports(e5, "S11", 1 + shift, 1) == {"0:0", "0:1"}
            assert ports(e6, "S11", 1 + shift, 1) == {"0:0", "0:1"}


def test_p_plus_q_is_one_boundary_line_not_two_killed_columns(audit):
    _, workspaces, shifts, result = audit
    for ws in workspaces:
        e5, e6 = result[ws.id][5], result[ws.id][6]
        for repeat in (0, 16):
            shift = shifts[ws.id] + repeat
            stem = 6 + shift
            assert ports(e5, "S22Y", stem, 6) == {"0:0"}
            assert ports(e5, "S22H", stem, 6) == {"0:0"}  # Positive-j tail was already a d3 image.
            # ports() owns displayed basis representatives, not every nonzero
            # class. P=Q must draw one point, while both named classes remain
            # nonzero and have the identical quotient endpoint below.
            displayed = [ports(e6, pattern, stem, 6) for pattern in ("S22Y", "S22H")]
            assert sum(len(p) for p in displayed) == 1
            assert set().union(*displayed) == {"0:0"}
            assert vector(e5, {"S22Y": 1, "S22H": 1}, stem)["live"] is True
            assert vector(e6, {"S22Y": 1, "S22H": 1}, stem)["live"] is False
            for components in ({"S22Y": 1}, {"S22H": 1}, {"S22Y": 1, "S22H": 2}):
                assert vector(e6, components, stem)["live"] is True
            p_slots = vector(e6, {"S22Y": 1}, stem)["slots"]
            assert len(p_slots) == 1 and p_slots == vector(e6, {"S22H": 1}, stem)["slots"]
            block = next(b for b in e6["blocks"] if b["id"] == f"S22H+S22Y:{stem % 64}:6")
            assert block["rank"] == 1 and block["barriers"] == 0
            # In the other 8-stem parity the P direction is itself a source,
            # and Q is the incoming image; the resulting cell really is zero.
            assert ports(e6, "S22Y", 14 + shift, 6) == set()
            assert ports(e6, "S22H", 14 + shift, 6) == set()


def test_hidden_h2_target_is_only_the_constant_two_witt_layer(audit):
    _, workspaces, shifts, result = audit
    for ws in workspaces:
        claim = next(p for p in ws.propositions if p.conclusion.get("fact_id") == "FN-3I-004")
        target = next(c for c in ws.classes if c.id == claim.conclusion["target_id"])
        assert target.style["e2_pattern"] == "S40"
        assert target.style["two_valuation"] == 1 and target.style.get("j_order", 0) == 0
        e5, e6 = result[ws.id][5], result[ws.id][6]
        for repeat in (0, 16):
            shift = shifts[ws.id] + repeat
            assert ports(e5, "S40", 12 + shift, 8) == {"1:0"}
            assert ports(e6, "S40", 12 + shift, 8) == set()
            before, after = ports(e5, "S40", 12 + shift, 0), ports(e6, "S40", 12 + shift, 0)
            assert {"1:0", "2:0", "3:0"} <= before
            assert after == before  # Killing the finite high target never deletes the Witt bo base.
