"""Reject counterfactual Jan29 convergence against an independent Tate cycle.

The pure sigma_i Galois-fixed basis independently fixes every nonzero F4
coefficient to 1. It does not establish any proposed differential or its
source's survival. In particular, it needs no FN-3I-010 d23 premise.

The convergence cases explicitly admit the declared formal rows ONLY in a
deep copy, including the withdrawn Jan. 29 hypotheses FN-3I-010 and its Euler
permanent-cycle claim. The independent verified Tate certificate for 2UDu
is always retained: the contradictory d23 must block that quotient rather
than manufacture convergence. Earlier page and coefficient checks still run.
No admission is inferred from a chart, and no vanishing-line clipping is used.

Non-1 assignments conflict with the fixed coefficient even when the Jan. 29
hypotheses are not admitted. Those failures must be coefficient-assignment
conflicts, not the obsolete d23-dependent Leibniz-compatibility constraint.
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
from domain.atlas_transport import ensure_q8_atlas_transports
from domain.migrations import migrate_project
from domain.seed import demo_project

PARAMETERS = tuple(f"three_sigma_d9_{name}" for name in ("D2", "D6", "BD4", "BD8", "CD3", "CD7"))
EULER_IDS = tuple(f"formal_diff_three_d9_{letter}_D{power}_euler_derived"
                  for letter, powers in (("b", (4, 8)), ("c", (3, 7))) for power in powers)
PREFIXES = ("FN-", "DER-3I-D9", "DER-3I-EULER-D9")
TATE_CYCLE_ID = "formal_prop_der-3i-tate-w-cycle"
TATE_CYCLE_CONFLICT = "nonzero differential contradicts a zero-outgoing cycle constraint"


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def hypothesis(project, common=1, mismatch=None, transports=False):
    """Explicitly assume withdrawn Jan. 29 rows in an isolated counterfactual."""
    candidate = deepcopy(project)
    ws = next(w for w in candidate.workspaces if w.id == "ws_3sigma_i")
    for arrow in ws.differentials:
        if arrow.label.startswith(PREFIXES):
            arrow.status = "admitted"
    for claim in ws.propositions:
        if claim.conclusion.get("fact_id", "").startswith(PREFIXES):
            claim.status = "admitted"
    selected = {d.linear_map_id for d in ws.differentials if d.status == "admitted"}
    for matrix in ws.differential_maps:
        if matrix.id in selected:
            matrix.status = "admitted"
    ws.settings["coefficient_assignments"] = dict.fromkeys(PARAMETERS, common)
    if mismatch:
        ws.settings["coefficient_assignments"][mismatch] = 2
    if transports:
        ensure_q8_atlas_transports(candidate)
    return candidate


def runtime(candidate, workspace_ids, pages=(3, 5, 7, 9, 10, 23, 24), unclipped=False):
    selected = [w for w in candidate.workspaces if w.id in workspace_ids]
    shifts = {w.id: w.settings.get("atlas_transport", {}).get("stem_shift", 0) for w in selected}
    probe_rows = set()
    for shift in shifts.values():
        for pattern, stem, filtration in (
            ("S11", 25, 1), ("S11", 57, 1), ("S02", 24, 10), ("S02", 56, 10),
            ("S40", 12, 0), ("S40", 32, 4),
        ):
            probe_rows.add((pattern, stem + shift, filtration))
    payload = {
        "project": asdict(candidate), "workspaces": workspace_ids, "pages": list(pages),
        "boundsByWorkspace": {ident: {"stemMin": shift, "stemMax": shift + 63,
                                       "filtrationMin": 0, "filtrationMax": 40}
                              for ident, shift in shifts.items()},
        "vectorAudit": True, "auditNoClipping": unclipped,
        "probes": [{"pattern": p, "stem": s, "filtration": f} for p, s, f in sorted(probe_rows)],
    }
    result = subprocess.run(["node", "tests/chart_runtime.cjs"], cwd=ROOT, text=True, encoding="utf-8",
                            input=json.dumps(payload), capture_output=True, check=True, timeout=120)
    return {ws["id"]: {row["page"]: row for row in ws["pages"]} for ws in json.loads(result.stdout)}


def ports(page, pattern, stem, filtration):
    return set(next(p["ports"] for p in page["probes"]
                    if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))


def assert_single_tate_cycle_conflict(conflict, *, stem_shift=0):
    """Recognize exactly one surviving W1 cycle/FN010 d23 contradiction."""
    assert conflict["page"] == 23 and conflict["reason"] == TATE_CYCLE_CONFLICT
    suffix = TATE_CYCLE_ID + "@23"
    assert conflict["cycle"].endswith(suffix)
    prefix = conflict["cycle"][:-len(suffix)]
    assert conflict["differential"] == prefix + "formal_diff_fn-3i-010_2"
    pattern, stem, filtration, two, j = conflict["port"].split(":")
    assert pattern == "S40" and (two, j) == ("1", "0")
    stem, filtration = int(stem), int(filtration)
    # Higher g images are now d11 boundaries. Only the three surviving
    # low-g directions can supply this particular zero-outgoing conflict.
    assert filtration in (0, 4, 8)
    assert (stem - stem_shift - 12 - 20*(filtration // 4)) % 64 == 0
    return prefix, ((stem - stem_shift) % 64, filtration)


def assert_absent_ad6_d19(conflict, *, stem_shift=0, prefix=""):
    """Only the obsolete D4 sibling's exact missing-target diagnostic."""
    assert conflict["reason"] == "source or target port absent on this page"
    assert conflict["id"] == prefix + "formal_diff_fn-3i-010_1" and conflict["page"] == 19
    source, target = conflict["source"], conflict["target"]
    assert source["filtration"] >= 2 and (source["filtration"] - 2) % 4 == 0
    g = (source["filtration"] - 2) // 4
    assert (source["stem"] - stem_shift - 46 - 20*g) % 64 == 0
    assert (target["stem"], target["filtration"]) == (source["stem"] - 1, source["filtration"] + 19)
    return ((source["stem"] - stem_shift) % 64, source["filtration"])


def assert_complete_january_conflicts(row, *, stem_shift=0):
    """Classify every obstruction in the unchanged, full FN010 hypothesis.

    New CD1 d11 boundaries invalidate the old AD6 d19 targets and the high-g
    W1 d23 sources. The independent low W1 Tate cycle remains a third,
    separate obstruction; unrelated errors must not satisfy this helper.
    """
    assert row["blockedFromPage"] == 23 and row["conflicts"]
    tate = [assert_single_tate_cycle_conflict(c, stem_shift=stem_shift)
            for c in row["conflicts"] if c["reason"] == TATE_CYCLE_CONFLICT]
    assert tate and len({prefix for prefix, _ in tate}) == 1
    prefix = tate[0][0]
    assert (12, 0) in {grade for _, grade in tate}
    absent_d19, absent_d23 = set(), set()
    for conflict in row["conflicts"]:
        reason = conflict["reason"]
        if reason == TATE_CYCLE_CONFLICT:
            continue  # Already checked individually above, including its port.
        source, target = conflict["source"], conflict["target"]
        if reason == "source or target port absent on this page":
            absent_d19.add(assert_absent_ad6_d19(conflict, stem_shift=stem_shift, prefix=prefix))
        else:
            assert reason == "nonzero differential has a source that is zero or not a cycle on this page"
            assert conflict["id"] == prefix + "formal_diff_fn-3i-010_2" and conflict["page"] == 23
            assert conflict["sourceState"] == "zero" and conflict["two"] == conflict["j"] == 0
            assert source["filtration"] >= 12 and (source["filtration"] - 12) % 4 == 0
            g = (source["filtration"] - 12) // 4
            # Exactly 2Uk3D2 and its D8/forward-g images, now d11 targets.
            assert (source["stem"] - stem_shift - 8 - 20*g) % 64 == 0
            assert (target["stem"], target["filtration"]) == (source["stem"] - 1, source["filtration"] + 23)
            absent_d23.add(((source["stem"] - stem_shift) % 64, source["filtration"]))
    assert (46, 2) in absent_d19
    assert {(8, 12), (28, 16)} <= absent_d23
    assert not any(ident.endswith("formal_diff_fn-3i-010_2") for ident in row["rows"])
    assert not [b for b in row["blocks"] if b["barriers"]]


def assert_tate_cycle_conflict(row, *, stem_shift=0):
    """Public full-fixture check, retaining the mandatory low Tate obstruction."""
    assert_complete_january_conflicts(row, stem_shift=stem_shift)


def test_euler_records_fix_units_independently_of_withdrawn_january_proof(project):
    ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    claims = {p.id: p for p in ws.propositions}
    for ident in EULER_IDS:
        arrow = next(d for d in ws.differentials if d.id == ident)
        claim = claims[arrow.proposition_id]
        assert arrow.status == claim.status == "verified"
        certificate = claim.conclusion["verification_certificate"]
        assert certificate["status"] == "verified"
        assert certificate["method"] == "Euler products, finite target survival and h1 detection"
        assert certificate["no_withdrawn_premise"] is True
        assert not {"FN-3I-010", "FN-3I-010-pc"} & set(certificate["premises"])
        parameter = claim.conclusion["coefficient_parameter"]
        assert parameter["id"] in PARAMETERS
        assert parameter["value"] == 1 and parameter["domain"] == [1]
        assert parameter["fixed_reason"] == "pure-sigma-i-galois-fixed"
        assert claim.conclusion["coefficient_normalization"]["admission_independent"] is True
        assert not any(c["id"] == "three-sigma-d9-product-compatibility"
                       for c in claim.conclusion.get("coefficient_constraints", []))
    january = [p for p in ws.propositions
               if p.conclusion.get("fact_id") in {"FN-3I-010", "FN-3I-010-pc"}]
    assert january
    assert all(p.status == "review" and p.conclusion["source_status"] == "withdrawn-proof"
               for p in january)
    assert not ws.settings.get("coefficient_assignments")


def test_counterfactual_january_d23_is_blocked_without_clipping_or_weakening_early_pages(project):
    candidate = hypothesis(project, common=1)
    workspace = next(w for w in candidate.workspaces if w.id == "ws_3sigma_i")
    cycle = next(p for p in workspace.propositions if p.id == TATE_CYCLE_ID)
    assert cycle.status == "verified" and cycle.conclusion["cycle_constraint"] == "outgoing-only"
    rows = runtime(candidate, [workspace.id], unclipped=True)[workspace.id]
    assert not [c for page, row in rows.items() if page < 23 for c in row["conflicts"]]
    assert all(row["blockedFromPage"] is None for page, row in rows.items() if page < 23)
    assert not [b for row in rows.values() for b in row["blocks"] if b["barriers"]]
    for stem in (25, 57):
        # Independent early-cycle proof: d3(C)=0; d5 target empty;
        # the entire d7 target is the d3 image of Uh1*k*D^3 / D^7.
        for page in (3, 5, 7, 9):
            assert "0:0" in ports(rows[page], "S11", stem, 1)
        assert ports(rows[10], "S11", stem, 1) == {"0:1"}
        assert ports(rows[9], "S02", stem - 1, 10) == {"0:0"}
        assert ports(rows[10], "S02", stem - 1, 10) == set()
    assert set(EULER_IDS).issubset(rows[9]["rows"])
    assert "formal_diff_three_d9_t_D7_sibling" in rows[9]["rows"]
    assert "formal_diff_three_d9_b_D7_sibling" in rows[9]["rows"]
    assert "1:0" in ports(rows[23], "S40", 12, 0)
    assert ports(rows[23], "S40", 32, 4) == {"1:0"}
    for page in (23, 24):
        assert_tate_cycle_conflict(rows[page])
        assert {"1:0", "2:0", "3:0"} <= ports(rows[page], "S40", 12, 0)
        assert ports(rows[page], "S40", 32, 4) == {"1:0"}
    assert rows[24]["high"] > 0  # Unknown later quotient, not a claimed convergence.
    assert rows[24]["unmappedHigh"] > 0


@pytest.mark.parametrize("common", (2, 3))
def test_uniform_nonone_assignments_conflict_with_fixed_pure_coefficients(project, common):
    rows = runtime(hypothesis(project, common), ["ws_3sigma_i"], pages=(9, 10))["ws_3sigma_i"]
    assert rows[10]["blockedFromPage"] == 9
    assert any("conflicting assignments" in c["reason"]
               for c in rows[10]["conflicts"])


@pytest.mark.parametrize("mismatch", PARAMETERS)
def test_one_nonone_assignment_blocks_the_counterfactual_quotient(project, mismatch):
    rows = runtime(hypothesis(project, mismatch=mismatch), ["ws_3sigma_i"], pages=(9, 10))["ws_3sigma_i"]
    assert rows[10]["blockedFromPage"] == 9
    assert any("conflicting assignments" in c["reason"] for c in rows[10]["conflicts"])


def test_fixed_coefficient_conflict_needs_no_january_d19_d23_or_euler_premise(project):
    candidate = hypothesis(project, mismatch="three_sigma_d9_BD4")
    workspace = next(w for w in candidate.workspaces if w.id == "ws_3sigma_i")
    claims = {c.id: c for c in workspace.propositions}
    january_ids = {p.id for p in workspace.propositions
                   if p.conclusion.get("fact_id") in {"FN-3I-010", "FN-3I-010-pc"}}
    january_rows = [d for d in workspace.differentials if d.proposition_id in january_ids]
    assert {d.page for d in january_rows} == {19, 23}
    for ident in january_ids:
        claims[ident].status = "review"
    for arrow in january_rows:
        arrow.status = claims[arrow.proposition_id].status = "review"
        for matrix in workspace.differential_maps:
            if matrix.id == arrow.linear_map_id:
                matrix.status = "review"
    assert all(p.status == "review" for p in workspace.propositions if p.id in january_ids)
    assert all(d.status == "review" for d in january_rows)
    rows = runtime(candidate, [workspace.id], pages=(9, 10))[workspace.id]
    assert rows[10]["blockedFromPage"] == 9
    assert any("conflicting assignments" in c["reason"] for c in rows[10]["conflicts"])
    assert not any(c["reason"] in {
        "Leibniz coefficient compatibility violated",
        "coefficient normalization differs from the cited integer table",
    } for c in rows[10]["conflicts"])


def test_counterfactual_atlas_images_keep_fixed_units_and_the_independent_cycle_obstruction(project):
    candidate = hypothesis(project, transports=True)
    source = next(w for w in candidate.workspaces if w.id == "ws_3sigma_i")
    images = [w for w in candidate.workspaces
              if w.settings.get("atlas_transport", {}).get("source_workspace_id") == source.id]
    assert len(images) == 2  # source S30 plus the S03 and shifted S11 images
    for target in images:
        plan = target.settings["atlas_transport"]
        prefix = f"atlas_{plan['sector_id']}_"
        assert target.settings["coefficient_assignments"] == source.settings["coefficient_assignments"]
        assert target.settings["coefficient_assignments"] is not source.settings["coefficient_assignments"]
        target_claims = {c.id: c for c in target.propositions}
        assert target_claims[prefix + TATE_CYCLE_ID].status == "verified"
        for ident in EULER_IDS:
            original = next(d for d in source.differentials if d.id == ident)
            image = next(d for d in target.differentials if d.id == prefix + ident)
            assert image.status == original.status == "admitted"
            parameter = target_claims[image.proposition_id].conclusion["coefficient_parameter"]
            assert parameter["id"] in PARAMETERS
            assert parameter["value"] == 1 and parameter["domain"] == [1]
            assert parameter["frobenius_power"] == int(plan["reflected"])
    workspaces = [source, *images]
    result = runtime(candidate, [w.id for w in workspaces], pages=(9, 23, 24), unclipped=True)
    for workspace in workspaces:
        shift = workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)
        rows = result[workspace.id]
        assert not rows[9]["conflicts"] and rows[9]["blockedFromPage"] is None
        assert not [b for row in rows.values() for b in row["blocks"] if b["barriers"]]
        assert all(any(ident.endswith(suffix) for ident in rows[9]["rows"]) for suffix in EULER_IDS)
        assert ports(rows[23], "S40", 32 + shift, 4) == {"1:0"}
        for page in (23, 24):
            assert_tate_cycle_conflict(rows[page], stem_shift=shift)
            assert {"1:0", "2:0", "3:0"} <= ports(rows[page], "S40", 12 + shift, 0)
            assert ports(rows[page], "S40", 32 + shift, 4) == {"1:0"}
        assert rows[24]["high"] > 0 and rows[24]["unmappedHigh"] > 0
