"""The Euler13-forced CD1 d11 has a constant image and a completed j kernel.

Exercise the actual migrated chart, including its forward-g quotient outside
the viewport. The separate CD5 cycle and independently proved AD2 d19
must not acquire the D1/D6 conclusions through an invalid D4 translation.
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


FACT = "DER-3I-EULER-CD1-D11"
ROW = "formal_diff_three_d11_c_D1_euler_forced"
J_ZERO = "DER-3I-CD1-D11-J-zero"
A_ZERO = "DER-3I-AD6-D19-zero"
ATLAS = {"ws_3sigma_i": 0, "ws_q8-ro-a0-b3": 0, "ws_q8-ro-a1-b1": 16}
D8_POWERS = (-1, 0, 1)
TRANSLATIONS = tuple((d8, g) for d8 in D8_POWERS for g in (0, 1)) + ((-1, 5),)
NONZERO_D9 = {power: f"formal_diff_three_d9_c_D{power}_euler_derived" for power in (3, 7)}
FORWARD_G = {"multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    selected = [w for w in project.workspaces if w.id == "ws_3sigma_i" or
                w.settings.get("atlas_transport", {}).get("source_workspace_id") == "ws_3sigma_i"]
    assert {w.id for w in selected} == set(ATLAS)
    return selected


def claim_for(workspace, fact):
    claims = [p for p in workspace.propositions if p.conclusion.get("fact_id") == fact]
    assert len(claims) == 1
    return claims[0]


def records(workspace):
    claim = claim_for(workspace, FACT)
    rows = [d for d in workspace.differentials if d.proposition_id == claim.id]
    assert len(rows) == 1
    row = rows[0]
    nodes = {n.id: n for n in workspace.classes}
    return row, claim, nodes[row.source_id], nodes[row.target_id]


def test_all_three_atlas_rows_retain_the_exact_constant_and_witt_target_ports(project):
    admitted = admitted_proposition_ids(project)
    for workspace in images(project):
        row, claim, source, target = records(workspace)
        data = claim.conclusion
        assert row.id.endswith(ROW) and row.label == FACT
        assert row.status == claim.status == data["admission_status"] == "verified"
        assert claim.kind == "differential" and claim.id in admitted
        assert row.page == data["page"] == 11
        assert row.period_stem == data["period_stem"] == 64
        assert data["period_multiplier"] == "D^8" and data["period_is_invertible"]
        assert data["forward_period"] == FORWARD_G
        assert data["coefficient_scope"] == "exact-port"
        assert not data.get("source_blockers") and not data.get("withdrawn_dependencies")
        assert not data.get("machine_verification_pending")
        shift = ATLAS[workspace.id]
        assert (source.grade.stem, source.grade.filtration) == (9 + shift, 1)
        assert (target.grade.stem, target.grade.filtration) == (8 + shift, 12)
        for node, pattern, two in ((source, "S11", 0), (target, "S40", 1)):
            assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                    node.style.get("j_order", 0)) == (pattern, two, 0)
            assert not node.archived
        parameter = data["coefficient_parameter"]
        assert parameter["value"] == 1 and parameter["domain"] == [1]
        assert parameter["fixed_reason"] == "pure-sigma-i-galois-fixed"
        assert parameter["id"] not in workspace.settings.get("coefficient_assignments", {})
        proof = data["verification_certificate"]
        assert proof["status"] == "verified" and proof["no_withdrawn_premise"]
        assert proof["source_refs"] and proof["uses_vanishing_line"] is False
        assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(data["derived_from"])


def test_zero_claims_cover_only_the_exact_page_and_port_with_local_ad6_premises(project):
    admitted = admitted_proposition_ids(project)
    count = 0
    for workspace in images(project):
        _, parent, _, _ = records(workspace)
        nodes = {n.id: n for n in workspace.classes}
        for fact, page, pattern, stem, filtration, j in (
            (J_ZERO, 11, "S11", 9, 1, 1),
            (A_ZERO, 19, "S62", 46, 2, 0),
        ):
            count += 1
            claim = claim_for(workspace, fact)
            data, source = claim.conclusion, nodes[claim.conclusion["source_id"]]
            assert claim.kind == "zero-differential" and claim.id in admitted
            assert claim.status == data["admission_status"] == "verified"
            assert data["zero"] is True and data["page"] == page
            assert data["cycle_constraint"] == "outgoing-only"
            # The 0:1 port represents the whole positive-j ideal, not just j^1.
            assert data["coefficient_scope"] == "exact-port"
            assert data["source_component"] == ("positive-j" if j else "constant")
            assert data["period_stem"] == 64 and data["forward_period"] == FORWARD_G
            assert (source.grade.stem, source.grade.filtration) == (stem + ATLAS[workspace.id], filtration)
            assert (source.style["e2_pattern"], source.style.get("two_valuation", 0),
                    source.style.get("j_order", 0)) == (pattern, 0, j)
            assert not source.archived
            assert not any(d.proposition_id == claim.id or d.label == fact for d in workspace.differentials)
            proof = data["verification_certificate"]
            assert proof["status"] == "verified" and proof["survival_override"] is False
            if fact == A_ZERO:
                assert claim.premise_ids == [parent.id]
                assert proof["target_differential"] == {"source": [45, 21], "target": [44, 32], "page": 11}
            else:
                assert parent.id not in claim.premise_ids
                assert proof["tate_source_bidegree"] == [10, -2]
                assert proof["tate_target_bidegree"] == [9, 1]
    assert count == 6


def test_source_certificate_distinguishes_the_e13_deadline_from_a_d13_image(project):
    workspace = next(w for w in images(project) if w.id == "ws_3sigma_i")
    _, claim, _, _ = records(workspace)
    proof = claim.conclusion["verification_certificate"]
    assert proof["method"] == "Euler13 product and complete finite incoming inventory"
    equation = proof["Euler13_equation"]
    assert equation["bidegree"] == [28, 16]
    assert equation["zero_on_page"] == equation["zero_outgoing_before"] == 13
    assert [(item["page"], item["bidegree"]) for item in proof["incoming_inventory"]] == [
        (3, [29, 13]), (5, [29, 11]), (7, [29, 9]), (9, [29, 7]), (11, [29, 5]),
    ]
    assert proof["source_survival"]["bidegree"] == [9, 1]
    assert proof["source_survival"]["port"] == "0:0"
    assert proof["finite_target"]["bidegree"] == [8, 12]
    assert proof["finite_target"]["port"] == "1:0" and proof["finite_target"]["dimension"] == 1
    assert proof["target_detection"]["nonzero_on_page"] == 11
    assert proof["period"] == {"D_power": 8, "stem": 64, "forward_g": True, "D5_block_inferred": False}


def test_migration_restores_the_row_and_two_zero_claims_without_duplicate_sources(project):
    candidate = deepcopy(project)

    def snapshot(workspace):
        row_records = tuple(asdict(item) for item in records(workspace))
        zero_records = tuple((asdict(claim_for(workspace, fact)),
                              asdict(next(n for n in workspace.classes
                                          if n.id == claim_for(workspace, fact).conclusion["source_id"])))
                             for fact in (J_ZERO, A_ZERO))
        return row_records, zero_records

    expected = {w.id: snapshot(w) for w in images(candidate)}
    for workspace in images(candidate):
        row, claim, _, _ = records(workspace)
        removed = {claim.id, *(claim_for(workspace, fact).id for fact in (J_ZERO, A_ZERO))}
        workspace.differentials = [d for d in workspace.differentials if d.id != row.id]
        workspace.propositions = [p for p in workspace.propositions if p.id not in removed]
    for _ in range(2):
        candidate = migrate_project(candidate)
        assert {w.id: snapshot(w) for w in images(candidate)} == expected


def test_new_ad6_zero_keeps_the_old_d4_family_separate_from_independent_ad2(project):
    for workspace in images(project):
        old = [d for d in workspace.differentials if d.page == 19 and d.label == "FN-3I-010"]
        assert len(old) == 1
        claim = next(p for p in workspace.propositions if p.id == old[0].proposition_id)
        assert old[0].status == claim.status == "review"
        assert claim.conclusion["source_status"] == "withdrawn-proof"
        verified = [d for d in workspace.differentials if d.page == 19 and d.status == "verified"]
        assert len(verified) == 1
        assert verified[0].id.endswith("formal_diff_three_d19_a_D2_euler_forced")
        assert verified[0].period_stem == 64
        data = claim_for(workspace, A_ZERO).conclusion
        assert data["period_stem"] == 64 and data["grade"]["stem"] == 46 + ATLAS[workspace.id]
        assert not any(p.kind == "permanent-cycle" and p.conclusion.get("fact_id") in {J_ZERO, A_ZERO}
                       for p in workspace.propositions)


def probe(name, pattern, stem, filtration, two=0, j=0):
    return {"name": name, "pattern": pattern, "stem": stem, "filtration": filtration, "two": two, "j": j}


@pytest.fixture(scope="module", params=tuple(ATLAS))
def chart(project, request):
    workspace = next(w for w in images(project) if w.id == request.param)
    shift = ATLAS[workspace.id]
    probes = []
    for d8, g in TRANSLATIONS:
        stem, filtration = 9 + shift + 64*d8 + 20*g, 1 + 4*g
        prefix = f"D8{d8}:g{g}"
        probes += [probe(prefix+":source", "S11", stem, filtration),
                   probe(prefix+":source-j", "S11", stem, filtration, j=1),
                   probe(prefix+":target", "S40", stem-1, filtration+11, two=1),
                   probe(prefix+":target-j", "S40", stem-1, filtration+11, two=1, j=1)]
        if g == 1:
            probes.append(probe(prefix+":primitive-source", "S62V", stem+1, filtration-3))
    for d8 in D8_POWERS:
        offset = shift + 64*d8
        for power in (3, 5, 7):
            prefix, stem = f"D8{d8}:CD{power}", 8*power + 1 + offset
            probes += [probe(prefix+":source", "S11", stem, 1),
                       probe(prefix+":source-j", "S11", stem, 1, j=1)]
            if power in NONZERO_D9:
                probes.append(probe(prefix+":target", "S02", stem-1, 10))
        probes += [probe(f"D8{d8}:AD6", "S62", 46+offset, 2),
                   probe(f"D8{d8}:AD6-other", "S62V", 46+offset, 2),
                   probe(f"D8{d8}:AD2", "S62", 14+offset, 2)]
    probes.append(probe("K", "S40", 28+shift, 16, two=1))
    payload = {
        "project": asdict(project), "workspaces": [workspace.id],
        "pages": [3, 4, 9, 10, 11, 12, 19, 20, 24], "vectorAudit": True,
        "bounds": {"stemMin": shift-60, "stemMax": shift+130,
                   "filtrationMin": 0, "filtrationMax": 24},
        "cycleProbes": probes, "fact": FACT, "zeroFacts": [J_ZERO, A_ZERO],
        "nonzeroSuffixes": list(NONZERO_D9.values()),
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
    if(input.auditWithoutRow&&page===11){
      const savedDiffs=ws.differentials,savedClaims=ws.propositions;
      try{
        ws.differentials=savedDiffs.filter(d=>d.label!==input.fact);
        ws.propositions=savedClaims.filter(p=>p.conclusion?.fact_id!==input.fact);
        const counterfactual=pageAlgebra(ws,bounds);
        withoutForcedRow={blockedFromPage:counterfactual.blockedFromPage,conflicts:counterfactual.conflicts,
          probes:input.cycleProbes.filter(p=>p.name==='K'||p.name.startsWith('D80:g'))
            .map(p=>probeOne(counterfactual,p))};
      }finally{ws.differentials=savedDiffs;ws.propositions=savedClaims;}
    }
    return {
      cycleProbes:input.cycleProbes.map(p=>probeOne(algebra,p)),withoutForcedRow,
      forcedEdges:edges.filter(e=>e.diff.label===input.fact).map(e=>({
        id:e.diff.id,status:e.diff.status,source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
        sourceLive:algebra.live(classes.get(e.diff.source_id),e.sourceGrade),
        targetLive:algebra.live(classes.get(e.diff.target_id),e.targetGrade)})),
      nonzeroD9:edges.filter(e=>input.nonzeroSuffixes.some(s=>e.diff.id.endsWith(s)))
        .map(e=>({id:e.diff.id,source:e.sourceGrade,target:e.targetGrade,
          admitted:algebra.canApply(e.diff),status:e.diff.status})),
      oldD19:edges.filter(e=>e.diff.page===19&&e.diff.label==='FN-3I-010')
        .map(e=>({status:e.diff.status,source:e.sourceGrade,target:e.targetGrade,admitted:algebra.canApply(e.diff)})),
      zeroEdges:edges.filter(e=>input.zeroFacts.includes(e.diff.label)).length,
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
    return next(item for item in row["cycleProbes"] if item["name"] == name)


def test_d11_draws_all_d8_and_forward_g_translates_with_exact_live_endpoints(chart):
    workspace_id, rows = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8{d8}:g{g}"
        stem, filtration = 9 + ATLAS[workspace_id] + 64*d8 + 20*g, 1 + 4*g
        source, target = (observation(rows[11], prefix+suffix) for suffix in (":source", ":target"))
        assert source["live"] and "0:0" in source["ports"]
        assert target["live"] and target["ports"] == ["1:0"]
        assert not observation(rows[11], prefix+":target-j")["live"]
        edge = next(e for e in rows[11]["forcedEdges"]
                    if (e["source"]["stem"], e["source"]["filtration"]) == (stem, filtration))
        assert (edge["target"]["stem"], edge["target"]["filtration"]) == (stem-1, filtration+11)
        assert edge["status"] == "verified" and edge["admitted"]
        assert edge["sourceLive"] and edge["targetLive"]
        assert edge["coefficient"]["resolved"] and edge["coefficient"]["value"] == 1
    assert not rows[12]["forcedEdges"]
    for row in rows.values():
        assert row["blockedFromPage"] is None and not row["conflicts"]
        assert not row["dangling"] and row["zeroEdges"] == 0


def test_e12_preserves_the_low_positive_j_ideal_but_not_high_primitive_images(chart):
    _, rows = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8{d8}:g{g}"
        before = observation(rows[11], prefix+":source")
        assert before["ports"] == (["0:0", "0:1"] if g == 0 else ["0:0"])
        for page in (12, 19, 20, 24):
            source = observation(rows[page], prefix+":source")
            assert not source["live"] and source["ports"] == (["0:1"] if g == 0 else [])
            assert observation(rows[page], prefix+":source-j")["live"] is (g == 0)
            target = observation(rows[page], prefix+":target")
            assert not target["live"] and not target["ports"]
    for d8 in D8_POWERS:
        prefix = f"D8{d8}:g1"
        assert observation(rows[3], prefix+":source-j")["live"]
        assert observation(rows[3], prefix+":primitive-source")["live"]
        for page in (4, 11, 12, 24):
            assert not observation(rows[page], prefix+":source-j")["live"]
            assert not observation(rows[page], prefix+":primitive-source")["live"]


def test_independent_cd5_cycle_is_not_given_a_d4_translate_of_the_new_map(chart):
    workspace_id, rows = chart
    for d8 in D8_POWERS:
        for page in (3, 10, 11, 12, 20, 24):
            for suffix in (":source", ":source-j"):
                item = observation(rows[page], f"D8{d8}:CD5"+suffix)
                assert item["live"] and item["ports"] == ["0:0", "0:1"]
        stem = 41 + ATLAS[workspace_id] + 64*d8
        assert not any((edge["source"]["stem"], edge["source"]["filtration"]) == (stem, 1)
                       for edge in rows[11]["forcedEdges"])


def test_cd3_and_cd7_still_have_their_independent_nonzero_d9(chart):
    workspace_id, rows = chart
    for d8 in D8_POWERS:
        for power, suffix in NONZERO_D9.items():
            prefix = f"D8{d8}:CD{power}"
            before, after = (observation(rows[page], prefix+":source") for page in (9, 10))
            assert before["live"] and before["ports"] == ["0:0", "0:1"]
            assert not after["live"] and after["ports"] == ["0:1"]
            assert observation(rows[10], prefix+":source-j")["live"]
            assert observation(rows[9], prefix+":target")["live"]
            assert not observation(rows[10], prefix+":target")["live"]
            stem = 8*power + 1 + ATLAS[workspace_id] + 64*d8
            edge = next(e for e in rows[9]["nonzeroD9"] if e["id"].endswith(suffix)
                        and (e["source"]["stem"], e["source"]["filtration"]) == (stem, 1))
            assert (edge["target"]["stem"], edge["target"]["filtration"]) == (stem-1, 10)
            assert edge["status"] == "verified" and edge["admitted"]
    assert not rows[10]["nonzeroD9"]


def test_b6_uses_its_offscreen_d11_target_and_does_not_change_the_ad2_block(chart):
    workspace_id, rows = chart
    shift = ATLAS[workspace_id]
    high = next(e for e in rows[11]["forcedEdges"]
                if (e["source"]["stem"], e["source"]["filtration"]) == (45+shift, 21))
    assert (high["target"]["stem"], high["target"]["filtration"]) == (44+shift, 32)
    assert high["target"]["filtration"] > 24  # The actual viewport's filtration maximum.
    for page in (12, 19, 20, 24):
        b6 = observation(rows[page], "D8-1:g5:source")
        assert not b6["live"] and not b6["ports"]
    for d8 in D8_POWERS:
        for page in (19, 20):
            a6 = observation(rows[page], f"D8{d8}:AD6")
            assert a6["live"] and a6["ports"] == ["0:0"]
            assert not observation(rows[page], f"D8{d8}:AD6-other")["live"]
            # The independent Euler-cofiber d19, not CD1's d11, now accounts
            # for AD2 on E20. AD6 still retains its distinct zero d19.
            assert observation(rows[page], f"D8{d8}:AD2")["live"] is (page == 19)
        assert not any(e["source"]["stem"] == 46+shift+64*d8 and e["source"]["filtration"] == 2
                       for e in rows[19]["oldD19"])
    assert all(e["status"] == "review" and not e["admitted"] for e in rows[19]["oldD19"])


def test_e11_endpoints_do_not_depend_on_the_new_row_being_installed(chart):
    workspace_id, rows = chart
    if workspace_id != "ws_3sigma_i":
        assert rows[11]["withoutForcedRow"] is None
        return
    before = rows[11]["withoutForcedRow"]
    assert before["blockedFromPage"] is None and not before["conflicts"]
    observed = {p["name"]: p for p in before["probes"]}
    assert observed["K"]["live"] and observed["K"]["ports"] == ["1:0"]
    for g in (0, 1):
        source = observed[f"D80:g{g}:source"]
        target = observed[f"D80:g{g}:target"]
        assert source["live"] and source["ports"] == (["0:0", "0:1"] if g == 0 else ["0:0"])
        assert target["live"] and target["ports"] == ["1:0"]
