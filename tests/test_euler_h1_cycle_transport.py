"""Euler images of the independently proved two-sigma H2/H6 cycles.

The actual migrated project supplies every certificate and existing map.
Forward-g cycle images may receive the already verified three-sigma d9 or
mixed d11; the certificate constrains outgoing maps only. An explicitly
isolated counterfactual module checks a conflicting outgoing d9 without
asserting that the mathematical Rk^2D^7 target survives to E9.
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
MIXED = "ws_sigma_i_2sigma_j"
FAMILIES = {THREE: "3I", MIXED: "MIX"}
ATLAS = {
    THREE: {THREE, "ws_q8-ro-a0-b3", "ws_q8-ro-a1-b1"},
    MIXED: {MIXED, "ws_q8-ro-a1-b3", "ws_q8-ro-a2-b1", "ws_q8-ro-a2-b3",
            "ws_q8-ro-a3-b1", "ws_q8-ro-a3-b2"},
}
# workspace, seed power, forward g exponent, D8 exponent, incoming page,
# established source row. These are existing maps, not hypothetical inputs.
INCOMING = (
    (THREE, 2, 2, 0, 9, "formal_diff_three_d9_c_D7_euler_derived"),
    (THREE, 6, 2, -1, 9, "formal_diff_three_d9_c_D3_euler_derived"),
    (MIXED, 2, 3, -1, 11, "formal_diff_fn-mix-006_1"),
    (MIXED, 6, 3, -1, 11, "formal_diff_mixed_d11_r_D6_sibling"),
)


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def workspace_by_id(project, ident):
    return next(ws for ws in project.workspaces if ws.id == ident)


def fact_id(source_id, power):
    return f"DER-{FAMILIES[source_id]}-EULER-H{power}-cycle"


def cycle_record(workspace, source_id, power):
    claims = [p for p in workspace.propositions
              if p.conclusion.get("fact_id") == fact_id(source_id, power)]
    assert len(claims) == 1
    claim = claims[0]
    node = next(n for n in workspace.classes if n.id == claim.conclusion["source_id"])
    return claim, node


def run_chart(payload):
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    # Extend observations only. No chart, quotient or admission logic is replaced.
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


def test_four_seed_certificates_have_exact_finite_ports_and_independent_evidence(project):
    admitted = admitted_proposition_ids(project)
    for source_id in FAMILIES:
        workspace = workspace_by_id(project, source_id)
        for power in (2, 6):
            claim, node = cycle_record(workspace, source_id, power)
            data = claim.conclusion
            assert claim.kind == "permanent-cycle" and claim.status == "verified"
            assert claim.id in admitted
            assert data["source_status"] == "independently-verified"
            assert data["cycle_constraint"] == "outgoing-only"
            assert data["coefficient_scope"] == "exact-port"
            assert data["page"] == 2 and data["period_stem"] == 64
            assert data["forward_period"] == {
                "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
            }
            assert (node.grade.stem, node.grade.filtration) == (8 * power, 2)
            assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                    node.style.get("j_order", 0)) == ("S02", 0, 0)
            assert not node.archived
            assert not any(d.proposition_id == claim.id for d in workspace.differentials)
            evidence = json.dumps(data, ensure_ascii=False)
            assert f"DER-2I-TATE-H{power}-cycle" in evidence
            assert "Euler" in evidence and "a_sigma_i" in evidence
            assert "450" in evidence and "469" in evidence
            assert not data.get("source_blockers")
            assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(data.get("derived_from", []))


def test_all_atlas_images_preserve_the_finite_cycle_and_independent_source_reference(project):
    total = 0
    for source_id, expected_ids in ATLAS.items():
        images = [w for w in project.workspaces if w.id == source_id
                  or w.settings.get("atlas_transport", {}).get("source_workspace_id") == source_id]
        assert {w.id for w in images} == expected_ids
        for workspace in images:
            shift = workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)
            for power in (2, 6):
                claim, node = cycle_record(workspace, source_id, power)
                data = claim.conclusion
                assert claim.status == "verified" and data["cycle_constraint"] == "outgoing-only"
                assert data["coefficient_scope"] == "exact-port" and data["period_stem"] == 64
                assert data["forward_period"]["nonnegative"] is True
                assert (node.grade.stem, node.grade.filtration) == (8 * power + shift, 2)
                assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                        node.style.get("j_order", 0)) == ("S02", 0, 0)
                assert f"DER-2I-TATE-H{power}-cycle" in json.dumps(data)
                assert not node.archived
                total += 1
    assert total == 18


@pytest.fixture(scope="module")
def chart(project):
    output = {}
    for source_id in FAMILIES:
        workspace = workspace_by_id(project, source_id)
        probes = []
        for power in (2, 6):
            _, node = cycle_record(workspace, source_id, power)
            for d8 in (0, 1):
                probes.append({"name": f"H{power}-D8-{d8}", "node_id": node.id,
                               "stem": 8 * power + 64 * d8, "filtration": 2})
        rows = []
        for ws_id, power, g, d8, page, row_id in INCOMING:
            if ws_id != source_id:
                continue
            _, node = cycle_record(workspace, source_id, power)
            probes.append({"name": f"H{power}-incoming", "node_id": node.id,
                           "stem": 8 * power + 20 * g + 64 * d8, "filtration": 2 + 4 * g})
            rows.append(row_id)
        payload = {
            "project": asdict(project), "workspaces": [source_id], "pages": [9, 10, 11, 12],
            "bounds": {"stemMin": 0, "stemMax": 116, "filtrationMin": 0, "filtrationMax": 16},
            "vectorAudit": True, "observeRows": rows,
            "cycleProbesByWorkspace": {source_id: probes},
        }
        # Release per-workspace caches; the original project and its source
        # coefficient links remain intact in each actual runtime process.
        output.update(run_chart(payload))
    return output


def test_base_cycles_and_d8_translates_remain_visible_without_new_nonzero_rows(chart):
    for source_id in FAMILIES:
        for page in (9, 10, 11, 12):
            result = chart[source_id][page]
            assert result["blockedFromPage"] is None
            seeds = [p for p in result["cycleObservations"] if "incoming" not in p["name"]]
            assert len(seeds) == 4
            assert all(p["live"] and p["known"] and "0:0" in p["ports"] for p in seeds)


@pytest.mark.parametrize("source_id,power,g,d8,page,row_id", INCOMING)
def test_existing_incoming_maps_still_remove_forward_g_images(project, chart, source_id, power, g, d8, page, row_id):
    workspace = workspace_by_id(project, source_id)
    row = next(d for d in workspace.differentials if d.id == row_id)
    target = next(n for n in workspace.classes if n.id == row.target_id)
    assert row.status == "verified" and row.page == page
    assert (target.grade.stem, target.grade.filtration) == (8 * power + 20 * g + 64 * d8, 2 + 4 * g)
    assert target.style["e2_pattern"] == "S02"
    before, after = chart[source_id][page], chart[source_id][page + 1]
    first = next(p for p in before["cycleObservations"] if p["name"] == f"H{power}-incoming")
    last = next(p for p in after["cycleObservations"] if p["name"] == f"H{power}-incoming")
    assert first["live"] and "0:0" in first["ports"]
    assert not last["live"] and "0:0" not in last["ports"]
    assert row_id in before["rows"]
    assert next(d for d in before["observedRows"] if d["id"] == row_id)["admitted"]
    assert before["blockedFromPage"] is None and after["blockedFromPage"] is None
    assert not any("zero-outgoing cycle constraint" in c.get("reason", "")
                   for result in (before, after) for c in result["conflicts"])


def test_injected_nonzero_d9_conflicts_with_real_h6_certificate_in_an_isolated_module(project):
    claim, source = cycle_record(workspace_by_id(project, THREE), THREE, 6)
    isolated = deepcopy(asdict(workspace_by_id(project, THREE)))
    isolated["id"] = "test_euler_cycle_conflict"
    # Keep the real enumeration/rendering settings so this isolated module
    # uses the production page algebra rather than the legacy drawing path.
    isolated["classes"] = [asdict(source)]
    # This independent one-dimensional test target is NOT a claim about
    # whether the named mathematical Rk^2D^7 target survives to E9.
    target = deepcopy(asdict(source))
    target.update(id="test_only_target", label="Independent test target", expression="test_target")
    target["grade"].update(stem=47, filtration=11)
    target["style"] = {"e2_pattern": "S73", "two_valuation": 0, "j_order": 0}
    isolated["classes"].append(target)
    outgoing_id = "test_only_conflicting_d9"
    isolated["differentials"] = [{"id": outgoing_id, "source_id": source.id,
        "target_id": target["id"], "page": 9, "status": "verified", "period_stem": 0}]
    isolated["propositions"] = [asdict(claim)]
    for field in ("differential_maps", "differential_events", "fates", "relations", "cells",
                  "named_vectors", "period_families", "periodicity_rules", "manual_periodicities"):
        isolated[field] = []
    payload_project = asdict(project)
    payload_project["workspaces"].append(isolated)
    result = run_chart({
        "project": payload_project, "workspaces": [isolated["id"]], "pages": [9, 10],
        "bounds": {"stemMin": 40, "stemMax": 56, "filtrationMin": 0, "filtrationMax": 16},
        "vectorAudit": True, "observeRows": [outgoing_id],
        "cycleProbesByWorkspace": {isolated["id"]: [
            {"name": "H6", "node_id": source.id, "stem": 48, "filtration": 2},
        ]},
    })[isolated["id"]]
    for page in (9, 10):
        data = result[page]
        assert data["blockedFromPage"] == 9
        assert data["cycleObservations"][0]["live"]
        assert not data["observedRows"][0]["admitted"] and data["observedRows"][0]["maps"] == 0
        # A conflicting row may remain visible for review, but cannot act.
        assert any("zero-outgoing cycle constraint" in c.get("reason", "") for c in data["conflicts"])
