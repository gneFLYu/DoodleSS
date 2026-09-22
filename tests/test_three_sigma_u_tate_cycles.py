"""The two independent FN007 negative-source Tate cycle certificates.

The constant Witt classes 2UD^3 and 2UD^7 have zero outgoing HFPSS
maps. Their positive-filtration images may still receive the real FN007
d9. All chart observations use the actual migrated project and JS algebra.
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

from domain.logic_graph import admitted_proposition_ids
from domain.migrations import migrate_project
from domain.seed import demo_project


THREE = "ws_3sigma_i"
ATLAS = {THREE, "ws_q8-ro-a0-b3", "ws_q8-ro-a1-b1"}
SOURCE_ROWS = {3: "diff_three_d9_25", 7: "formal_diff_three_d9_t_D7_sibling"}


def fact_id(power):
    return f"DER-3I-TATE-U-D{power}-cycle"


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    result = [w for w in project.workspaces if w.id == THREE or
              w.settings.get("atlas_transport", {}).get("source_workspace_id") == THREE]
    assert {w.id for w in result} == ATLAS
    return result


def cycle_record(workspace, power):
    claims = [p for p in workspace.propositions if p.conclusion.get("fact_id") == fact_id(power)]
    assert len(claims) == 1
    claim = claims[0]
    return claim, next(n for n in workspace.classes if n.id == claim.conclusion["source_id"])


def test_independent_d3_and_d7_blocks_keep_the_exact_witt_layer(project):
    admitted = admitted_proposition_ids(project)
    base = next(w for w in project.workspaces if w.id == THREE)
    for power, row_id in SOURCE_ROWS.items():
        claim, node = cycle_record(base, power)
        data = claim.conclusion
        assert claim.kind == "permanent-cycle" and claim.status == "verified"
        assert claim.id in admitted and data["source_status"] == "independently-verified"
        assert data["cycle_constraint"] == "outgoing-only"
        assert data["coefficient_scope"] == "constant-two-multiples"
        assert data["page"] == 2 and data["period_stem"] == 64
        assert data["D_block"] == power and data["source_fact_id"] == "FN-3I-007"
        assert data["source_differential_id"] == row_id
        assert data["forward_period"] == {
            "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
        }
        assert (node.grade.stem, node.grade.filtration) == (8 * power + 4, 0)
        assert (node.style["e2_pattern"], node.style["two_valuation"], node.style["j_order"]) == ("S40", 1, 0)
        assert not node.archived and not any(d.proposition_id == claim.id for d in base.differentials)
        row = next(d for d in base.differentials if d.id == row_id)
        premise = next(p for p in base.propositions if p.id == row.proposition_id)
        assert row.page == 9 and row.status == premise.status == "verified"
        assert row.period_stem == 64
        assert premise.conclusion["verification_certificate"]["no_withdrawn_premise"]
        assert f"DER-2I-TATE-H{power - 1}-cycle" in data["derived_from"]
        assert data["verification_certificate"]["source_verification"]["D_blocks"] == [3, 7]
        assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(data["derived_from"])
        assert not data.get("source_blockers") and not data.get("machine_verification_pending")
        if power == 7:
            assert "For m=3,7 separately" in premise.conclusion["derivation"]
            assert "separate H6 Tate cycle" in data["derivation"]


def test_negative_source_is_tate_only_and_reverses_the_exact_fn007_translation(project):
    base = next(w for w in project.workspaces if w.id == THREE)
    for power in SOURCE_ROWS:
        claim, _ = cycle_record(base, power)
        certificate = claim.conclusion["comparison_certificate"]
        assert certificate["spectral_sequence"] == "tate" and certificate["page"] == 9
        assert certificate["tate_zero_by_page"] == 10
        assert certificate["source_bidegree"] == [8 * power + 5, -9]
        assert certificate["target_bidegree"] == [8 * power + 4, 0]
        assert certificate["translation"] == {"g_exponent": -3, "D_exponent": 8, "permanent_unit": True}
        shift = (-3 * 20 + 8 * 8, -3 * 4)
        for positive_key, tate_key in (("positive_source_bidegree", "source_bidegree"),
                                       ("positive_target_bidegree", "target_bidegree")):
            original = certificate[positive_key]
            assert [original[0] + shift[0], original[1] + shift[1]] == certificate[tate_key]
        assert "incoming maps remain allowed" in certificate["interpretation"]
    nodes = {n.id: n for n in base.classes}
    assert all(nodes[d.source_id].grade.filtration >= 0 and nodes[d.target_id].grade.filtration >= 0
               for d in base.differentials)


def test_three_actual_atlas_images_preserve_both_source_certificates(project):
    count = 0
    for workspace in images(project):
        shift = workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)
        for power, row_id in SOURCE_ROWS.items():
            claim, node = cycle_record(workspace, power)
            data = claim.conclusion
            assert claim.status == "verified" and data["cycle_constraint"] == "outgoing-only"
            assert data["coefficient_scope"] == "constant-two-multiples" and data["period_stem"] == 64
            assert data["source_differential_id"].endswith(row_id)
            assert any(d.id == data["source_differential_id"] for d in workspace.differentials)
            assert data["comparison_certificate"]["source_workspace_id"] == THREE
            assert data["comparison_certificate"]["target_bidegree"] == [8 * power + 4, 0]
            assert (node.grade.stem, node.grade.filtration) == (8 * power + 4 + shift, 0)
            assert (node.style["e2_pattern"], node.style["two_valuation"], node.style["j_order"]) == ("S40", 1, 0)
            assert not node.archived
            count += 1
    assert count == 6


def test_migration_restores_missing_certificates_without_replacing_existing_nodes(project):
    candidate = deepcopy(project)
    original_nodes = {}
    for workspace in images(candidate):
        for power in SOURCE_ROWS:
            _, node = cycle_record(workspace, power)
            original_nodes[(workspace.id, power)] = deepcopy(node)
        workspace.propositions = [p for p in workspace.propositions
                                  if p.conclusion.get("fact_id") not in {fact_id(3), fact_id(7)}]
    candidate = migrate_project(candidate)
    for workspace in images(candidate):
        for power in SOURCE_ROWS:
            claim, node = cycle_record(workspace, power)
            assert claim.status == "verified"
            assert node == original_nodes[(workspace.id, power)]


def run_chart(payload):
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    # Only output observations change; all state, matrices and admissions
    # come from the real production project and chart implementation.
    observation = r"""return {
      cycleObservations: (input.cycleProbesByWorkspace?.[ws.id] || []).map(probe => {
        const node = classes.get(probe.node_id);
        const grade = {stem:probe.stem, filtration:probe.filtration};
        return {...probe, live:algebra.live(node,grade), known:algebra.knownCycle(node,grade),
          ports:[...(algebra.ports(node,grade) || [])]};
      }),
      observedRows: ws.differentials.filter(d => (input.observeRows || []).includes(d.id))
        .map(d => ({id:d.id, admitted:algebra.canApply(d),
          maps:algebra.maps(classes.get(d.source_id),classes.get(d.target_id),
            classes.get(d.source_id).grade,classes.get(d.target_id).grade).length})),
      page, points: points.length"""
    completed = subprocess.run(
        ["node", "-e", harness.replace(marker, observation)], cwd=ROOT,
        input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8",
        check=True, timeout=180,
    )
    return {row["id"]: {page["page"]: page for page in row["pages"]}
            for row in json.loads(completed.stdout)}


@pytest.fixture(scope="module")
def chart(project):
    output = {}
    for workspace in images(project):
        shift = workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)
        probes, rows = [], []
        for power, row_id in SOURCE_ROWS.items():
            _, node = cycle_record(workspace, power)
            for d8 in (0, 1):
                probes.append({"name": f"U{power}-D8-{d8}", "node_id": node.id,
                               "stem": 8 * power + 4 + shift + 64 * d8, "filtration": 0})
            for g in (3, 4):
                # Reverse the actual Tate translation; g=4 also tests a
                # genuine forward-g copy of the established incoming row.
                probes.append({"name": f"U{power}-incoming-g{g}", "node_id": node.id,
                               "stem": 8 * power + 4 + shift + 20 * g - 64,
                               "filtration": 4 * g})
            rows.append(next(d.id for d in workspace.differentials if d.id.endswith(row_id)))
        output.update(run_chart({
            "project": asdict(project), "workspaces": [workspace.id], "pages": [7, 9, 10],
            "bounds": {"stemMin": 20 + shift, "stemMax": 132 + shift,
                       "filtrationMin": 0, "filtrationMax": 18},
            "vectorAudit": True, "observeRows": rows,
            "cycleProbesByWorkspace": {workspace.id: probes},
        }))
    return output


def test_actual_chart_keeps_both_constant_witt_seeds_and_d8_images(chart):
    for workspace_id in ATLAS:
        for page in (7, 9, 10):
            data = chart[workspace_id][page]
            assert data["blockedFromPage"] is None
            seeds = [p for p in data["cycleObservations"] if "incoming" not in p["name"]]
            assert len(seeds) == 4
            assert all(p["live"] and p["known"] and "1:0" in p["ports"] for p in seeds)
            assert all("0:0" not in p["ports"] for p in seeds)


def test_actual_chart_preserves_fn007_incoming_and_its_forward_g_copies(chart):
    for workspace_id in ATLAS:
        before, after = chart[workspace_id][9], chart[workspace_id][10]
        incoming = [p for p in before["cycleObservations"] if "incoming" in p["name"]]
        assert len(incoming) == 4
        assert all(p["live"] and "1:0" in p["ports"] for p in incoming)
        for probe in incoming:
            later = next(p for p in after["cycleObservations"] if p["name"] == probe["name"])
            assert not later["live"] and "1:0" not in later["ports"]
        assert len(before["observedRows"]) == 2
        assert all(row["admitted"] and row["id"] in before["rows"] for row in before["observedRows"])
        assert before["blockedFromPage"] is None and after["blockedFromPage"] is None
        assert not any("zero-outgoing cycle constraint" in c.get("reason", "")
                       for data in (before, after) for c in data["conflicts"])


@pytest.mark.parametrize("power", (3, 7))
def test_injected_d7_is_rejected_by_the_real_outgoing_only_certificate(project, power):
    base = next(w for w in project.workspaces if w.id == THREE)
    claim, source = cycle_record(base, power)
    isolated = deepcopy(asdict(base))
    isolated["id"] = f"test_only_u_d{power}_cycle"
    # Keep real rendering/enumeration settings, unlike a legacy-only drawing.
    isolated["classes"] = [asdict(source)]
    target = deepcopy(asdict(source))
    target.update(id="test_only_d7_target", label="Independent test target", expression="test_target")
    target["grade"].update(stem=8 * power + 3, filtration=7)
    target["style"] = {"e2_pattern": "S73", "two_valuation": 0, "j_order": 0}
    isolated["classes"].append(target)
    row_id = "test_only_conflicting_d7"
    isolated["differentials"] = [{"id": row_id, "source_id": source.id, "target_id": target["id"],
                                 "page": 7, "status": "verified", "period_stem": 0}]
    isolated["propositions"] = [asdict(claim)]
    for field in ("differential_maps", "differential_events", "fates", "relations", "cells",
                  "named_vectors", "period_families", "periodicity_rules", "manual_periodicities"):
        isolated[field] = []
    candidate = asdict(project)
    candidate["workspaces"].append(isolated)
    output = run_chart({
        "project": candidate, "workspaces": [isolated["id"]], "pages": [7, 8],
        "bounds": {"stemMin": 8 * power, "stemMax": 8 * power + 10,
                   "filtrationMin": 0, "filtrationMax": 9},
        "vectorAudit": True, "observeRows": [row_id],
        "cycleProbesByWorkspace": {isolated["id"]: [
            {"name": "constant-two", "node_id": source.id, "stem": 8 * power + 4, "filtration": 0},
        ]},
    })[isolated["id"]]
    for page in (7, 8):
        result = output[page]
        assert result["blockedFromPage"] == 7
        assert result["cycleObservations"][0]["live"]
        assert not result["observedRows"][0]["admitted"] and result["observedRows"][0]["maps"] == 0
        assert any("zero-outgoing cycle constraint" in c.get("reason", "") for c in result["conflicts"])
