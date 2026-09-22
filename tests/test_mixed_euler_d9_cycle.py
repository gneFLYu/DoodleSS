"""Finite baseline and exact-port CD1/CD5 / mixed BH-D3/D7 zero-d9 certificates.

The baseline checks do not admit a candidate differential.
The three-sigma candidate's target already supports a verified d9; in mixed
degree its finite target must remain distinct from the adjacent bo column.
Review-only drawing data never supply a page transition. Separate certificate
checks use the production claims, not a substitute proof or scalar assignment.
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
from domain.logic_graph import admitted_proposition_ids
from domain.migrations import migrate_project
from domain.seed import demo_project


MIXED = "ws_sigma_i_2sigma_j"
THREE = "ws_3sigma_i"
MIXED_ATLAS = {
    MIXED: (False, 0), "ws_q8-ro-a1-b3": (False, -16),
    "ws_q8-ro-a2-b1": (True, 0), "ws_q8-ro-a2-b3": (False, -32),
    "ws_q8-ro-a3-b1": (True, -16), "ws_q8-ro-a3-b2": (True, -32),
}
PURE_TARGET_OUTGOING = {1: "formal_diff_three_d9_b_D4_euler_derived",
                        5: "formal_diff_three_d9_b_D8_euler_derived"}
MIXED_INCOMING = {"formal_diff_fn-mix-006_1": (12, 14),
                  "formal_diff_mixed_d11_r_D6_sibling": (44, 14)}
PURE_ATLAS = {THREE: 0, "ws_q8-ro-a0-b3": 0, "ws_q8-ro-a1-b1": 16}
CERTIFICATES = {
    (THREE, 1): "DER-3I-EULER-CD1-D9-zero",
    (THREE, 5): "DER-3I-EULER-CD5-D9-zero",
    (MIXED, 3): "DER-MIX-PHI-BH-D3-D9-zero",
    (MIXED, 7): "DER-MIX-PHI-BH-D7-D9-zero",
}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def mixed_images(project):
    result = [w for w in project.workspaces if w.id == MIXED or
              w.settings.get("atlas_transport", {}).get("source_workspace_id") == MIXED]
    assert {w.id for w in result} == set(MIXED_ATLAS)
    return result


def certificate_records(workspace, source_id, power):
    claims = [p for p in workspace.propositions
              if p.conclusion.get("fact_id") == CERTIFICATES[(source_id, power)]]
    assert len(claims) == 1
    claim = claims[0]
    node = next(n for n in workspace.classes if n.id == claim.conclusion["source_id"])
    return claim, node


def test_all_eighteen_claims_are_exact_page_nine_zero_maps_not_permanent_cycles(project):
    admitted = admitted_proposition_ids(project)
    count = 0
    for source_id, expected in ((THREE, set(PURE_ATLAS)), (MIXED, set(MIXED_ATLAS))):
        workspaces = [w for w in project.workspaces if w.id == source_id or
                      w.settings.get("atlas_transport", {}).get("source_workspace_id") == source_id]
        assert {w.id for w in workspaces} == expected
        for workspace in workspaces:
            shift = workspace.settings.get("atlas_transport", {}).get("stem_shift", 0)
            for power in ((1, 5) if source_id == THREE else (3, 7)):
                claim, node = certificate_records(workspace, source_id, power)
                data = claim.conclusion
                assert claim.kind == "zero-differential" and claim.status == "verified"
                assert claim.id in admitted and data["source_status"] == "independently-verified"
                assert data["zero"] and data["page"] == 9
                assert data["cycle_constraint"] == "outgoing-only" and data["coefficient_scope"] == "exact-port"
                assert data["period_stem"] == 64 and data["period_is_invertible"]
                assert data["forward_period"] == {
                    "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
                }
                ds, filtration, pattern = (1, 1, "S11") if source_id == THREE else (0, 2, "S02")
                assert (node.grade.stem, node.grade.filtration) == (8 * power + ds + shift, filtration)
                assert (node.style["e2_pattern"], node.style["two_valuation"], node.style["j_order"]) == (pattern, 0, 0)
                assert not node.archived and not any(d.proposition_id == claim.id for d in workspace.differentials)
                assert not data.get("source_blockers") and not data.get("withdrawn_dependencies")
                assert not data.get("machine_verification_pending")
                assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(data["derived_from"])
                count += 1
    assert count == 18


def test_independent_detector_blocks_preserve_the_live_d7_two_layer_and_phi_metadata(project):
    for (source_id, power), fact in CERTIFICATES.items():
        workspace = next(w for w in project.workspaces if w.id == source_id)
        claim, _ = certificate_records(workspace, source_id, power)
        pure_power = power if source_id == THREE else power - 2
        proof = claim.conclusion["verification_certificate"]
        assert proof["status"] == "verified" and proof["source_workspace_id"] == THREE
        assert proof["method"] == "Square-zero on a one-dimensional finite target"
        assert proof["detector_differential_id"] == PURE_TARGET_OUTGOING[pure_power]
        assert proof["detector_verification"]["status"] == "verified"
        assert proof["translation"] == {"g_exponent": 2, "D_exponent": -8, "forward_g_only": True}
        target = proof["finite_target"]
        assert (target["pattern"], target["port"], target["dimension"]) == ("S02", "0:0", 1)
        assert target["bidegree"] == [8 * pure_power, 10]
        assert target["nonzero_d9_target"] == {"bidegree": [8 * pure_power - 1, 19], "pattern": "S73", "port": "0:0"}
        two_layer = target["d7_incoming_two_layer"]
        assert (two_layer["bidegree"], two_layer["pattern"], two_layer["port"]) == ([8 * pure_power, 12], "S40", "1:0")
        assert "Not declared absent or a d5 boundary" in two_layer["disposition"]
        assert "L=D^-1*h1" in two_layer["disposition"]
        if source_id == MIXED:
            transport = claim.conclusion["transport_certificate"]
            assert transport["source_workspace_id"] == THREE
            assert transport["source_fact_id"] == CERTIFICATES[(THREE, pure_power)]
            assert transport["source_power"] == pure_power and transport["action"] == "omega^2"
            assert transport["applied_inverse"] and transport["final_D_exponent"] == 0
            assert transport["euler_multiplier"] == "a_sigma_j"
            assert "common Thom unit" in claim.conclusion["derivation"]
        assert "coefficient_parameter" not in claim.conclusion


def test_migration_restores_and_idempotently_keeps_all_eighteen_claims(project):
    candidate = deepcopy(project)
    fact_ids = set(CERTIFICATES.values())
    original = {p.id: asdict(p) for w in candidate.workspaces for p in w.propositions
                if p.conclusion.get("fact_id") in fact_ids}
    assert len(original) == 18
    for workspace in candidate.workspaces:
        workspace.propositions = [p for p in workspace.propositions
                                  if p.conclusion.get("fact_id") not in fact_ids]
    for _ in range(2):
        candidate = migrate_project(candidate)
        refreshed = {p.id: asdict(p) for w in candidate.workspaces for p in w.propositions
                     if p.conclusion.get("fact_id") in fact_ids}
        assert refreshed == original


def patterns_at(stem, filtration):
    if filtration < 0:
        return set()
    return {cell.pattern_key for cell in verified_e2_classes("sigma_i")
            if filtration >= cell.filtration and (filtration - cell.filtration) % 4 == 0
            and (stem - cell.stem - 20 * ((filtration - cell.filtration) // 4)) % 64 == 0}


def test_candidate_support_is_finite_and_separates_series_columns():
    assert patterns_at(56, 2) == {"S02"}
    assert patterns_at(55, 11) == {"S73", "S73V"}
    assert patterns_at(56, 8) == {"S00"}
    assert patterns_at(56, 6) == set()
    assert patterns_at(56, 4) == {"S40"}
    assert patterns_at(41, 1) == {"S11"}
    assert patterns_at(40, 10) == {"S02"}
    assert patterns_at(39, 19) == {"S73", "S73V"}


def test_six_mixed_images_retain_real_transport_and_unassigned_parameters(project):
    for workspace in mixed_images(project):
        reflected, shift = MIXED_ATLAS[workspace.id]
        plan = workspace.settings.get("atlas_transport", {})
        assert plan.get("stem_shift", 0) == shift
        assert plan.get("reflected", False) == reflected
        assert not {"mixed_d5_A", "mixed_d5_B"}.intersection(
            workspace.settings.get("coefficient_assignments", {}))
        for power in (3, 7):
            assert any(n.style.get("e2_pattern") == "S02" and not n.archived
                       and n.grade.filtration == 2 and (n.grade.stem - 8 * power - shift) % 64 == 0
                       for n in workspace.classes)


def run_chart(payload):
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    # Extend observations only: the actual chart and quotient engines execute.
    observations = r"""return {
      finiteProbes: (input.finiteProbesByWorkspace?.[ws.id] || []).map(probe => {
        const node={style:{e2_pattern:probe.pattern,two_valuation:probe.two||0,j_order:probe.j||0}};
        const grade={stem:probe.stem,filtration:probe.filtration};
        return {...probe,ports:[...(algebra.ports(node,grade)||[])],
          live:algebra.live(node,grade),known:algebra.knownCycle(node,grade)};
      }),
      edgeAudit: edges.filter(e=>(input.rowSuffixes||[]).some(s=>e.diff.id.endsWith(s)))
        .map(e=>({id:e.diff.id,source:e.sourceGrade,target:e.targetGrade,
          admitted:algebra.canApply(e.diff),status:e.diff.status,
          sourceLive:algebra.live(classes.get(e.diff.source_id),e.sourceGrade),
          targetLive:algebra.live(classes.get(e.diff.target_id),e.targetGrade)})),
      rowAdmissions:ws.differentials.filter(d=>(input.rowSuffixes||[]).some(s=>d.id.endsWith(s)))
        .map(d=>({id:d.id,admitted:algebra.canApply(d)})),
      page, points: points.length"""
    result = subprocess.run(["node", "-e", harness.replace(marker, observations)], cwd=ROOT,
                            input=json.dumps(payload), capture_output=True, text=True,
                            encoding="utf-8", check=True, timeout=180)
    return {row["id"]: {page["page"]: page for page in row["pages"]}
            for row in json.loads(result.stdout)}


def probe(name, pattern, stem, filtration, **extra):
    return {"name": name, "pattern": pattern, "stem": stem, "filtration": filtration, **extra}


def observed(page, name):
    return next(p for p in page["finiteProbes"] if p["name"] == name)


@pytest.fixture(scope="module")
def mixed_chart(project):
    result = {}
    for workspace in mixed_images(project):
        shift = MIXED_ATLAS[workspace.id][1]
        probes = []
        for power in (3, 7):
            for d8 in (0, 1):
                for g in (0, 1):
                    s, f = 8 * power + shift + 64 * d8 + 20 * g, 2 + 4 * g
                    prefix = f"BH{power}-D8-{d8}-g-{g}"
                    probes += [probe(prefix + "-source", "S02", s, f),
                               probe(prefix + "-target", "S73", s - 1, f + 9),
                               probe(prefix + "-target-bo", "S73V", s - 1, f + 9),
                               probe(prefix + "-incoming-d3", "S00", s, f + 6),
                               probe(prefix + "-incoming-d7", "S40", s, f + 2)]
        for row_id, (s, f) in MIXED_INCOMING.items():
            probes.append(probe(row_id, "S02", s + shift, f))
        result.update(run_chart({
            "project": asdict(project), "workspaces": [workspace.id], "pages": [3, 4, 9, 10, 11, 12],
            "bounds": {"stemMin": shift + 8, "stemMax": shift + 145,
                       "filtrationMin": 0, "filtrationMax": 16},
            "vectorAudit": True, "finiteProbesByWorkspace": {workspace.id: probes},
            "rowSuffixes": list(MIXED_INCOMING),
        }))
    return result


def test_actual_mixed_e9_source_target_and_earlier_d3_ports(mixed_chart):
    for workspace_id in MIXED_ATLAS:
        before, after, e9 = (mixed_chart[workspace_id][r] for r in (3, 4, 9))
        for power in (3, 7):
            for d8 in (0, 1):
                for g in (0, 1):
                    prefix = f"BH{power}-D8-{d8}-g-{g}"
                    for suffix in ("source", "target"):
                        current = observed(e9, prefix + "-" + suffix)
                        assert current["live"] and current["ports"] == ["0:0"]
                    for suffix in ("target-bo", "incoming-d3", "incoming-d7"):
                        assert observed(before, prefix + "-" + suffix)["ports"]
                        assert not observed(after, prefix + "-" + suffix)["ports"]
                    assert "1:0" in observed(before, prefix + "-incoming-d7")["ports"]
        assert e9["blockedFromPage"] is None


def test_actual_mixed_existing_d11_families_still_receive_incoming(mixed_chart):
    # These are neighboring D2/D6 families, not BH-D7 translates. They guard
    # against accidentally extending a new zero-d9 constraint to permanence.
    for workspace_id, (_, shift) in MIXED_ATLAS.items():
        e11, e12 = mixed_chart[workspace_id][11], mixed_chart[workspace_id][12]
        for row_id, (stem, filtration) in MIXED_INCOMING.items():
            assert observed(e11, row_id)["ports"] == ["0:0"]
            assert not observed(e12, row_id)["ports"]
            arrow = next(e for e in e11["edgeAudit"] if e["id"].endswith(row_id)
                         and e["target"]["stem"] == stem + shift
                         and e["target"]["filtration"] == filtration)
            assert arrow["admitted"] and arrow["sourceLive"] and arrow["targetLive"]
        assert e11["blockedFromPage"] is None and e12["blockedFromPage"] is None


@pytest.fixture(scope="module", params=tuple(PURE_ATLAS))
def pure_chart(project, request):
    workspace_id = request.param
    shift = PURE_ATLAS[workspace_id]
    workspace = next(w for w in project.workspaces if w.id == workspace_id)
    assert workspace.settings.get("atlas_transport", {}).get("stem_shift", 0) == shift
    probes = []
    for power in (1, 5):
        s = 8 * power + shift
        probes += [probe(f"C{power}-constant", "S11", s + 1, 1),
                   probe(f"C{power}-positive-j", "S11", s + 1, 1, j=1),
                   probe(f"C{power}-finite-T", "S02", s, 10),
                   probe(f"C{power}-finite-R", "S73", s - 1, 19),
                   probe(f"C{power}-R-bo", "S73V", s - 1, 19),
                   probe(f"C{power}-R-incoming-d7", "S40", s, 12, two=1)]
    return shift, run_chart({
        "project": asdict(project), "workspaces": [workspace_id], "pages": [3, 4, 7, 9, 10],
        "bounds": {"stemMin": 5 + shift, "stemMax": 43 + shift,
                   "filtrationMin": 0, "filtrationMax": 20},
        "vectorAudit": True, "finiteProbesByWorkspace": {workspace_id: probes},
        "rowSuffixes": list(PURE_TARGET_OUTGOING.values()),
    })[workspace_id]


def test_actual_pure_target_has_its_verified_nonzero_d9_and_finite_target(pure_chart):
    shift, pages = pure_chart
    e9, e10 = pages[9], pages[10]
    for power in (1, 5):
        prefix = f"C{power}-"
        for suffix in ("constant", "positive-j", "finite-T", "finite-R"):
            assert observed(e9, prefix + suffix)["live"]
        for suffix in ("finite-T", "finite-R"):
            assert observed(e9, prefix + suffix)["ports"] == ["0:0"]
            assert not observed(e10, prefix + suffix)["live"] and not observed(e10, prefix + suffix)["ports"]
        assert observed(pages[3], prefix + "R-bo")["ports"]
        assert not observed(pages[4], prefix + "R-bo")["ports"]
        for suffix in ("constant", "positive-j"):
            assert observed(e10, prefix + suffix)["live"]
        for page in (7, 9):
            finite_two = observed(pages[page], prefix + "R-incoming-d7")
            assert finite_two["live"] and finite_two["ports"] == ["1:0"]
        arrow = next(e for e in e9["edgeAudit"] if e["source"]["stem"] == 8 * power + shift
                     and e["source"]["filtration"] == 10 and e["target"]["stem"] == 8 * power - 1 + shift
                     and e["target"]["filtration"] == 19)
        assert arrow["id"].endswith(PURE_TARGET_OUTGOING[power]) and arrow["admitted"]
        assert arrow["sourceLive"] and arrow["targetLive"]
    assert e9["blockedFromPage"] is None and e10["blockedFromPage"] is None


def test_review_only_candidate_does_not_change_mixed_source_or_target(project):
    original = asdict(project)
    candidate = deepcopy(original)
    workspace = next(w for w in candidate["workspaces"] if w["id"] == MIXED)
    source = deepcopy(next(n for n in workspace["classes"] if n["style"].get("e2_pattern") == "S02"
                  and (n["grade"]["stem"] - 56) % 64 == 0 and n["grade"]["filtration"] == 2))
    source.update(id="test_only_review_source")
    source["grade"].update(stem=56, filtration=2)
    workspace["classes"].append(source)
    target = deepcopy(next(n for n in workspace["classes"] if n["style"].get("e2_pattern") == "S73"))
    target.update(id="test_only_review_target")
    target["grade"].update(stem=55, filtration=11)
    target["style"] = {"e2_pattern": "S73", "two_valuation": 0, "j_order": 0}
    workspace["classes"].append(target)
    row_id = "test_only_review_mixed_d9"
    workspace["differentials"].append({"id": row_id, "source_id": source["id"],
        "target_id": target["id"], "page": 9, "status": "review", "period_stem": 64})
    payload = {"workspaces": [MIXED], "pages": [9, 10], "vectorAudit": True,
        "bounds": {"stemMin": 53, "stemMax": 58, "filtrationMin": 0, "filtrationMax": 12},
        "finiteProbesByWorkspace": {MIXED: [probe("source", "S02", 56, 2), probe("target", "S73", 55, 11)]},
        "rowSuffixes": [row_id]}
    baseline = run_chart({**payload, "project": original})[MIXED]
    drawn = run_chart({**payload, "project": candidate})[MIXED]
    for page in (9, 10):
        assert drawn[page]["finiteProbes"] == baseline[page]["finiteProbes"]
        assert drawn[page]["blockedFromPage"] == baseline[page]["blockedFromPage"]
        assert all(not item["admitted"] for item in drawn[page]["rowAdmissions"])


def isolated_certificate_module(project, source_id, power):
    base = next(w for w in project.workspaces if w.id == source_id)
    claim, node = certificate_records(base, source_id, power)
    workspace = deepcopy(asdict(base))
    workspace["id"] = f"test_only_zero_{source_id}_D{power}"
    workspace["classes"] = [asdict(node)]
    workspace["propositions"] = [asdict(claim)]
    # Keep the production enumeration settings so the real page algebra runs.
    for field in ("differentials", "differential_maps", "differential_events", "fates", "relations",
                  "cells", "named_vectors", "period_families", "periodicity_rules", "manual_periodicities"):
        workspace[field] = []
    return workspace, asdict(node)


@pytest.mark.parametrize("source_id,power", CERTIFICATES)
def test_isolated_nonzero_d9_conflicts_with_the_actual_exact_port_certificate(project, source_id, power):
    workspace, source = isolated_certificate_module(project, source_id, power)
    target = deepcopy(source)
    target.update(id="test_only_nonzero_target", label="Independent test target", expression="test_target")
    target["grade"].update(stem=source["grade"]["stem"] - 1, filtration=source["grade"]["filtration"] + 9)
    target["style"] = {"e2_pattern": "S02" if source_id == THREE else "S73", "two_valuation": 0, "j_order": 0}
    workspace["classes"].append(target)
    row_id = "test_only_conflicting_d9"
    workspace["differentials"] = [{"id": row_id, "source_id": source["id"], "target_id": target["id"],
                                   "page": 9, "status": "verified", "period_stem": 64}]
    candidate = asdict(project)
    candidate["workspaces"].append(workspace)
    s, f = source["grade"]["stem"], source["grade"]["filtration"]
    output = run_chart({
        "project": candidate, "workspaces": [workspace["id"]], "pages": [9, 10], "vectorAudit": True,
        "bounds": {"stemMin": s - 3, "stemMax": s + 3, "filtrationMin": 0, "filtrationMax": f + 10},
        "rowSuffixes": [row_id],
        "finiteProbesByWorkspace": {workspace["id"]: [probe("source", source["style"]["e2_pattern"], s, f)]},
    })[workspace["id"]]
    for page in (9, 10):
        result = output[page]
        assert result["blockedFromPage"] == 9
        assert observed(result, "source")["live"]
        assert result["rowAdmissions"] == [{"id": row_id, "admitted": False}]
        assert any("zero-outgoing cycle constraint" in c.get("reason", "") for c in result["conflicts"])


@pytest.mark.parametrize("power", (3, 7))
def test_isolated_incoming_d9_is_allowed_on_a_forward_g_zero_source(project, power):
    # This is an engine-contract example, not a proposed mathematical map.
    # The actual neighboring FN006 d11 maps are tested separately above.
    workspace, seed = isolated_certificate_module(project, MIXED, power)
    s = seed["grade"]["stem"] + 40
    target = deepcopy(seed)
    target.update(id="test_only_forward_g_target")
    target["grade"].update(stem=s, filtration=10)
    source = deepcopy(seed)
    source.update(id="test_only_incoming_source", label="Independent incoming source", expression="test_source")
    source["grade"].update(stem=s + 1, filtration=1)
    source["style"] = {"e2_pattern": "S11", "two_valuation": 0, "j_order": 0}
    workspace["classes"].extend([source, target])
    row_id = "test_only_allowed_incoming_d9"
    workspace["differentials"] = [{"id": row_id, "source_id": source["id"], "target_id": target["id"],
                                   "page": 9, "status": "verified", "period_stem": 64}]
    candidate = asdict(project)
    candidate["workspaces"].append(workspace)
    output = run_chart({
        "project": candidate, "workspaces": [workspace["id"]], "pages": [9, 10], "vectorAudit": True,
        "bounds": {"stemMin": s - 3, "stemMax": s + 3, "filtrationMin": 0, "filtrationMax": 12},
        "rowSuffixes": [row_id],
        "finiteProbesByWorkspace": {workspace["id"]: [probe("forward-g", "S02", s, 10)]},
    })[workspace["id"]]
    assert observed(output[9], "forward-g")["live"]
    assert not observed(output[10], "forward-g")["live"]
    assert output[9]["rowAdmissions"] == [{"id": row_id, "admitted": True}]
    assert any(e["id"] == row_id and e["admitted"] for e in output[9]["edgeAudit"])
    for page in (9, 10):
        assert output[page]["blockedFromPage"] is None
        assert not any("zero-outgoing cycle constraint" in c.get("reason", "") for c in output[page]["conflicts"])
