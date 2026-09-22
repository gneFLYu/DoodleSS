"""The independently forced W5 d23 and its exact Witt-layer quotients.

The old W1 claim remains under review. D8 is invertible and g acts forwards;
the high detection class is an outgoing translate, not a fabricated incoming
h1-product. The real browser algebra includes its filtration-51 target even
when that target is outside the viewport.
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


FACT = "DER-3I-LEIBNIZ-W5-D23"
ROW = "formal_diff_three_d23_u_D5_forced"
ATLAS = {"ws_3sigma_i": 0, "ws_q8-ro-a0-b3": 0, "ws_q8-ro-a1-b1": 16}
TRANSLATIONS = tuple((d8, g) for d8 in (-1, 0, 1) for g in (0, 1)) + ((-2, 7),)
WITT_BEFORE = ["1:0", "2:0", "3:0", "1:1", "2:1", "3:1"]
WITT_AFTER = [port for port in WITT_BEFORE if port != "1:0"]


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    selected = [w for w in project.workspaces if w.id == "ws_3sigma_i" or
                w.settings.get("atlas_transport", {}).get("source_workspace_id") == "ws_3sigma_i"]
    assert {w.id for w in selected} == set(ATLAS)
    return selected


def records(workspace):
    rows = [d for d in workspace.differentials if d.label == FACT]
    assert len(rows) == 1
    row = rows[0]
    claim = next(p for p in workspace.propositions if p.id == row.proposition_id)
    nodes = {n.id: n for n in workspace.classes}
    return row, claim, nodes[row.source_id], nodes[row.target_id]


def test_three_atlas_rows_have_the_exact_witt_source_finite_target_and_fixed_unit(project):
    admitted = admitted_proposition_ids(project)
    for workspace in images(project):
        row, claim, source, target = records(workspace)
        data = claim.conclusion
        assert row.id.endswith(ROW) and row.status == claim.status == "verified"
        assert claim.kind == "differential" and claim.id in admitted
        assert data["fact_id"] == FACT and row.page == data["page"] == 23
        assert row.period_stem == data["period_stem"] == 64
        assert data["period_multiplier"] == "D^8" and data["period_is_invertible"]
        assert data["coefficient_scope"] == "exact-port"
        assert data["render_equation_aliases"] == [{
            "fact_id": "FN-3I-010", "page": 23, "status": "review", "scope": "same-equation-only",
        }]
        assert data["forward_period"] == {
            "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
        }
        assert not data.get("source_blockers") and not data.get("withdrawn_dependencies")
        assert not data.get("machine_verification_pending")
        shift = ATLAS[workspace.id]
        assert (source.grade.stem, source.grade.filtration) == (44 + shift, 0)
        assert (target.grade.stem, target.grade.filtration) == (43 + shift, 23)
        for node, pattern, two in ((source, "S40", 1), (target, "S73", 0)):
            assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                    node.style.get("j_order", 0)) == (pattern, two, 0)
            assert not node.archived
        parameter = data["coefficient_parameter"]
        assert parameter["value"] == 1 and parameter["domain"] == [1]
        assert parameter["fixed_reason"] == "pure-sigma-i-galois-fixed"
        assert parameter["id"] not in workspace.settings.get("coefficient_assignments", {})
        proof = data["verification_certificate"]
        assert proof["status"] == "verified" and proof["no_withdrawn_premise"]
        assert proof["source_refs"]
        assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(data["derived_from"])
        assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(proof.get("premises", []))


def test_finite_proof_inventory_and_high_detection_keep_the_actual_direction(project):
    base = next(w for w in images(project) if w.id == "ws_3sigma_i")
    _, claim, _, _ = records(base)
    proof = claim.conclusion["verification_certificate"]
    assert proof["method"] == "Complete finite exclusion and published d23 product"
    assert proof["scope"] == "source-workspace" and proof["source_workspace_id"] == base.id
    assert proof["page"] == 23 and proof["uses_vanishing_line"] is False
    assert proof["low_source"]["bidegree"] == [44, 0]
    assert (proof["low_source"]["pattern"], proof["low_source"]["port"]) == ("S40", "1:0")
    assert proof["low_target"]["bidegree"] == [43, 23]
    assert proof["low_target"]["dimension"] == 1 and proof["low_target"]["torsion_order"] == 2
    assert proof["low_target"]["j_annihilated"] is True
    outgoing = {page for entry in proof["low_outgoing_inventory"]
                for page in entry.get("pages", [entry.get("page")])}
    assert outgoing == set(range(3, 24, 2))
    high = proof["high_detection"]
    assert {entry["page"] for entry in high["incoming_inventory"]} == set(range(3, 24, 2))
    assert high["bidegree"] == [56, 28] and high["port"] == "1:0"
    assert high["multiplier"] == {
        "g_exponent": 7, "D_exponent": -16, "permanent": True, "invertible_in_HFPSS": False,
    }
    assert high["actual_d23"]["source"] == [56, 28]
    assert high["actual_d23"]["target"] == [55, 51]
    assert "outgoing" in high["actual_d23"]["kind"]
    assert proof["coefficient_equation"]["G_nonzero"] is True
    assert proof["coefficient_equation"]["lambda"] == 1 and proof["coefficient_equation"]["field"] == "F4"
    assert proof["period"] == {"D_power": 8, "stem": 64, "forward_g": True, "D1_block_inferred": False}


def test_migration_restores_only_the_new_d8_family_and_is_idempotent(project):
    candidate = deepcopy(project)
    expected = {w.id: tuple(asdict(item) for item in records(w)) for w in images(candidate)}
    for workspace in images(candidate):
        row, claim, _, _ = records(workspace)
        workspace.differentials = [d for d in workspace.differentials if d.id != row.id]
        workspace.propositions = [p for p in workspace.propositions if p.id != claim.id]
    for _ in range(2):
        candidate = migrate_project(candidate)
        assert {w.id: tuple(asdict(item) for item in records(w)) for w in images(candidate)} == expected


def test_old_d1_statement_is_not_readmitted_or_given_d4_periodicity(project):
    for workspace in images(project):
        rows = [d for d in workspace.differentials if d.page == 23]
        assert len(rows) == 2
        old = next(d for d in rows if d.label == "FN-3I-010")
        claim = next(p for p in workspace.propositions if p.id == old.proposition_id)
        assert old.status == claim.status == "review"
        assert claim.conclusion["source_status"] == "withdrawn-proof"
        fresh, _, source, _ = records(workspace)
        assert fresh.period_stem == 64
        assert (source.grade.stem - ATLAS[workspace.id] - 12) % 64 == 32
        assert [d for d in rows if d.status == "verified"] == [fresh]


def probe(name, pattern, stem, filtration, two=0, j=0):
    return {"name": name, "pattern": pattern, "stem": stem, "filtration": filtration, "two": two, "j": j}


@pytest.fixture(scope="module", params=tuple(ATLAS))
def chart(project, request):
    workspace = next(w for w in images(project) if w.id == request.param)
    shift = ATLAS[workspace.id]
    probes = []
    for d8, g in TRANSLATIONS:
        stem, filtration = 44 + shift + 64*d8 + 20*g, 4*g
        prefix = f"D8{d8}:g{g}"
        probes += [probe(prefix+":source", "S40", stem, filtration, two=1),
                   probe(prefix+":target", "S73", stem-1, filtration+23),
                   probe(prefix+":target-j", "S73", stem-1, filtration+23, j=1)]
        if g == 0:
            for two, j in ((2, 0), (3, 0), (1, 1), (2, 1), (3, 1)):
                probes.append(probe(prefix+f":preserved-{two}:{j}", "S40", stem, filtration, two=two, j=j))
        if g in (0, 1):
            probes.append(probe(prefix+":old-source", "S40", stem-32, filtration, two=1))
    payload = {
        "project": asdict(project), "workspaces": [workspace.id], "pages": [23, 24],
        "bounds": {"stemMin": shift-60, "stemMax": shift+136, "filtrationMin": 0, "filtrationMax": 30},
        "vectorAudit": True, "d23Probes": probes, "fact": FACT,
        "auditWithoutRow": workspace.id == "ws_3sigma_i",
    }
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""
    const probeOne=(engine,probe)=>{
      const node={style:{e2_pattern:probe.pattern,two_valuation:probe.two,j_order:probe.j}};
      const grade={stem:probe.stem,filtration:probe.filtration};
      return {...probe,live:engine.live(node,grade),ports:[...(engine.ports(node,grade)||[])]};
    };
    let withoutForcedRow=null;
    if(input.auditWithoutRow&&page===24){
      const saved=ws.differentials;
      try{
        ws.differentials=saved.filter(d=>d.label!==input.fact);
        const counterfactual=pageAlgebra(ws,bounds);
        withoutForcedRow=input.d23Probes.filter(p=>p.name.startsWith('D8-2:g7:'))
          .map(p=>probeOne(counterfactual,p));
      }finally{ws.differentials=saved;}
    }
    return {
      d23Probes:input.d23Probes.map(probe=>probeOne(algebra,probe)),
      withoutForcedRow,
      forcedEdges:edges.filter(e=>e.diff.label===input.fact).map(e=>({
        id:e.diff.id,status:e.diff.status,source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
        sourceLive:algebra.live(classes.get(e.diff.source_id),e.sourceGrade),
        targetLive:algebra.live(classes.get(e.diff.target_id),e.targetGrade)})),
      oldEdges:edges.filter(e=>e.diff.label==='FN-3I-010').map(e=>({
        id:e.diff.id,status:e.diff.status,source:e.sourceGrade,target:e.targetGrade})),
      renderedGroups:differentialRenderGroups(ws,edges,algebra).map(e=>({
        id:e.diff.id,label:e.diff.label,status:e.diff.status,source:e.sourceGrade,target:e.targetGrade,
        aliases:e.renderAliases.map(a=>({id:a.id,label:a.label,status:a.status}))})),
      oldCandidates:ws.differentials.filter(d=>d.label==='FN-3I-010'&&d.page===23).map(d=>{
        const {source,target}=algebra.endpoints(d);
        const candidate=algebra.candidateState(d,source.grade,target.grade);
        return {status:d.status,candidate:candidate.status,sourceLive:algebra.live(source,source.grade)};
      }),
      page, points: points.length"""
    completed = subprocess.run(
        ["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
        input=json.dumps(payload), text=True, encoding="utf-8", capture_output=True,
        check=True, timeout=240,
    )
    output = json.loads(completed.stdout)
    assert len(output) == 1 and output[0]["id"] == workspace.id
    return workspace.id, {row["page"]: row for row in output[0]["pages"]}


def observation(row, name):
    return next(item for item in row["d23Probes"] if item["name"] == name)


def test_d23_draws_every_d8_and_forward_g_copy_with_live_exact_endpoints(chart):
    workspace_id, rows = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8{d8}:g{g}"
        stem, filtration = 44 + ATLAS[workspace_id] + 64*d8 + 20*g, 4*g
        source = observation(rows[23], prefix+":source")
        target = observation(rows[23], prefix+":target")
        assert source["live"] and "1:0" in source["ports"]
        assert target["live"] and target["ports"] == ["0:0"]
        assert not observation(rows[23], prefix+":target-j")["live"]
        edge = next(e for e in rows[23]["forcedEdges"]
                    if e["source"]["stem"] == stem and e["source"]["filtration"] == filtration)
        assert edge["target"]["stem"] == stem-1 and edge["target"]["filtration"] == filtration+23
        assert edge["status"] == "verified" and edge["admitted"]
        assert edge["sourceLive"] and edge["targetLive"]
        assert edge["coefficient"]["resolved"] and edge["coefficient"]["value"] == 1
    for row in rows.values():
        assert row["blockedFromPage"] is None and not row["conflicts"]
        assert not row["dangling"]


def test_e24_takes_only_the_constant_two_layer_and_preserves_witt_and_j(chart):
    _, rows = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8{d8}:g{g}"
        before = observation(rows[23], prefix+":source")
        after = observation(rows[24], prefix+":source")
        assert not after["live"] and after["ports"] == [port for port in before["ports"] if port != "1:0"]
        target = observation(rows[24], prefix+":target")
        assert not target["live"] and not target["ports"]
        if g == 0:
            assert before["ports"] == WITT_BEFORE and after["ports"] == WITT_AFTER
            for two, j in ((2, 0), (3, 0), (1, 1), (2, 1), (3, 1)):
                retained = observation(rows[24], prefix+f":preserved-{two}:{j}")
                assert retained["live"] and f"{two}:{j}" in retained["ports"]
    assert not rows[24]["forcedEdges"]
    assert not rows[24]["oldEdges"] and not rows[24]["renderedGroups"]


def test_historical_d5_alias_is_retained_but_drawn_as_one_verified_equation(chart):
    _, rows = chart
    before = rows[23]
    assert before["forcedEdges"] and before["oldEdges"]
    for edge in before["forcedEdges"]:
        same_endpoints = lambda item: item["source"] == edge["source"] and item["target"] == edge["target"]
        historical = [item for item in before["oldEdges"] if same_endpoints(item)]
        assert len(historical) == 1 and historical[0]["status"] == "review"
        groups = [item for item in before["renderedGroups"] if same_endpoints(item)]
        assert len(groups) == 1, (edge, groups)
        group = groups[0]
        assert group["status"] == "verified" and group["label"] == FACT
        assert group["id"] == edge["id"]
        assert {alias["id"] for alias in group["aliases"]} == {edge["id"], historical[0]["id"]}
        assert {alias["label"]: alias["status"] for alias in group["aliases"]} == {
            FACT: "verified", "FN-3I-010": "review",
        }
    assert len(before["renderedGroups"]) == len(before["forcedEdges"])


def test_high_detection_source_uses_outgoing_d23_even_with_target_outside_viewport(chart):
    workspace_id, rows = chart
    prefix = "D8-2:g7:"
    source = observation(rows[23], prefix+"source")
    target = observation(rows[23], prefix+"target")
    assert (source["stem"], source["filtration"]) == (56 + ATLAS[workspace_id], 28)
    assert (target["stem"], target["filtration"]) == (55 + ATLAS[workspace_id], 51)
    assert source["live"] and source["ports"] == ["1:0"] and target["live"]
    assert not observation(rows[24], prefix+"source")["live"]
    assert not observation(rows[24], prefix+"target")["live"]
    if workspace_id == "ws_3sigma_i":
        # Same viewport and E24, removing only the new row restores these
        # previously live ports. Their removal is an algebraic quotient, not
        # a global display cutoff at filtration 23 or the viewport edge.
        counterfactual = {p["name"]: p for p in rows[24]["withoutForcedRow"]}
        assert counterfactual[prefix+"source"]["live"]
        assert counterfactual[prefix+"target"]["live"]


def test_old_d1_cycle_remains_visible_without_a_review_arrow(chart):
    workspace_id, rows = chart
    for page in (23, 24):
        for d8, g in TRANSLATIONS:
            if g not in (0, 1):
                continue
            old = observation(rows[page], f"D8{d8}:g{g}:old-source")
            assert old["live"] and "1:0" in old["ports"]
            stem, filtration = 12 + ATLAS[workspace_id] + 64*d8 + 20*g, 4*g
            for items in (rows[page]["oldEdges"], rows[page]["forcedEdges"], rows[page]["renderedGroups"]):
                assert not any(item["source"]["stem"] == stem and item["source"]["filtration"] == filtration
                               for item in items)
    assert rows[23]["oldCandidates"] == [{"status": "review", "candidate": "contradicted", "sourceLive": True}]
