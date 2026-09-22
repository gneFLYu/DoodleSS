"""An independent AD2 d19, not a D4 promotion of the January family.

Use only migrated production records and the actual chart algebra. The
finite constant target is distinct from its earlier positive-j d3 image;
AD6 and its already absent B6 target retain their separate d11/zero-d19
explanation. The archived same-equation record remains a review alias.
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
from domain.fate import class_is_live_on_page, derive_class_fate, sync_differential_events
from domain.logic_graph import admitted_proposition_ids
from domain.migrations import migrate_project
from domain.seed import demo_project


FACT = "DER-3I-EULER-AD2-D19"
ROW = "formal_diff_three_d19_a_D2_euler_forced"
A6_ZERO = "DER-3I-AD6-D19-zero"
ATLAS = {"ws_3sigma_i": 0, "ws_q8-ro-a0-b3": 0, "ws_q8-ro-a1-b1": 16}
TRANSLATIONS = tuple((d8, g) for d8 in (-1, 0, 1) for g in (0, 1))
FORWARD_G = {"multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True}


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


def test_three_atlas_rows_have_exact_finite_ports_and_the_pure_fixed_unit(project):
    admitted = admitted_proposition_ids(project)
    for workspace in images(project):
        row, claim, source, target = records(workspace)
        data = claim.conclusion
        assert row.id.endswith(ROW) and data["fact_id"] == FACT
        assert row.status == claim.status == data["admission_status"] == "verified"
        assert claim.kind == "differential" and claim.id in admitted
        assert row.page == data["page"] == 19
        assert row.period_stem == data["period_stem"] == 64
        assert data["period_multiplier"] == "D^8" and data["period_is_invertible"]
        assert data["forward_period"] == FORWARD_G
        assert data["coefficient_scope"] == "exact-port"
        assert not data.get("source_blockers") and not data.get("withdrawn_dependencies")
        assert not data.get("machine_verification_pending")
        shift = ATLAS[workspace.id]
        assert (source.grade.stem, source.grade.filtration) == (14+shift, 2)
        assert (target.grade.stem, target.grade.filtration) == (13+shift, 21)
        for node, pattern in ((source, "S62"), (target, "S11")):
            assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                    node.style.get("j_order", 0)) == (pattern, 0, 0)
            assert not node.archived
        parameter = data["coefficient_parameter"]
        assert parameter["value"] == 1 and parameter["domain"] == [1]
        assert parameter["fixed_reason"] == "pure-sigma-i-galois-fixed"
        assert parameter["id"] not in workspace.settings.get("coefficient_assignments", {})
        proof = data["verification_certificate"]
        assert proof["status"] == "verified" and proof["no_withdrawn_premise"]
        assert proof["scope"] == "source-workspace" and proof["source_workspace_id"] == "ws_3sigma_i"
        assert proof["source_refs"] and data["derived_from"]
        assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(data["derived_from"])
        assert not any(fact in json.dumps(proof) for fact in ("FN-3I-010", "FN-3I-010-pc"))


def test_euler_injectivity_and_complete_filtration_certificate_have_the_exact_ro_degrees(project):
    workspace = next(w for w in images(project) if w.id == "ws_3sigma_i")
    _, claim, _, _ = records(workspace)
    proof = claim.conclusion["verification_certificate"]
    assert proof["method"] == "Euler cofiber and complete homotopy filtration"
    assert proof["page"] == 19 and proof["uses_clipping"] is False
    assert proof["uses_vanishing_line"] is True
    cofiber = proof["euler_cofiber"]
    assert cofiber == {
        "subgroup": "ker(sigma_i)=C4<i>", "source_degree": "16-3sigma_i",
        "target_degree": "16-4sigma_i", "restricted_degree": 13,
        "left_group": "pi13(E^hC4)=0", "consequence": "Euler multiplication is injective",
    }
    assert any("BBHS20" in ref and "Table 4" in ref for ref in proof["source_refs"])
    descent = proof["coefficient_descent"]
    assert descent["extension"] == "W(F4) -> W(algebraic closure of F2)"
    assert descent["faithfully_flat"] is True and descent["embedding"]
    assert "not taking Galois homotopy fixed points" in descent["argument"]
    assert len(descent["comparison_steps"]) == 4
    assert "Mittag-Leffler" in descent["comparison_steps"][2]
    assert "separated convergence" in descent["comparison_steps"][3]
    assert len(descent["forbidden_shortcuts"]) == 3
    filtration = proof["integer_filtration"]
    assert (filtration["stem"], filtration["zero_from_filtration"]) == (12, 22)
    assert filtration["filtration22_basis"] == ["xh1k5D4"]
    assert filtration["differential"] == {
        "page": 9, "source": [13, 13], "target": [12, 22],
        "published_source": "D2h1", "multiplier": "g3D^-8",
    }
    assert filtration["period_unit"] == "u_4sigma_i"
    assert filtration["unit_and_inverse_filtration"] == 0
    assert "23" in filtration["higher_filtration"] and "strong vanishing" in filtration["higher_filtration"]
    assert "entire F22 subgroup is zero" in filtration["hidden_extensions"]
    survival = proof["source_survival"]
    assert survival["bidegree"] == [14, 2]
    assert (survival["pattern"], survival["port"]) == ("S62", "0:0")
    assert {int(page) for page in survival["outgoing"]} == set(range(3, 19, 2))
    target = proof["target"]
    assert target["bidegree"] == [13, 21] and target["dimension"] == 1
    assert (target["pattern"], target["port"]) == ("S11", "0:0")
    assert "Primitive d3 image" in target["positive_j"]
    assert "only zero outgoing, not survival override" in target["outgoing_certificate"]
    inventory = proof["incoming_inventory"]
    assert [(item["page"], item["source"]) for item in inventory] == [
        (page, [14, 21-page]) for page in range(3, 22, 2)
    ]
    assert {item["page"] for item in inventory if not item["patterns"]} == {5, 9, 13, 17, 21}
    assert next(item["patterns"] for item in inventory if item["page"] == 19) == ["S62", "S62V"]
    product = proof["h1_product"]
    assert (product["source"], product["target"], product["result"]) == ([15, 3], [14, 22], "zero on E19")
    assert product["earlier_image"] == {
        "page": 5, "source": [15, 17], "target": [14, 22], "formula": "d5(a k4D4)=Qk5D4",
    }
    assert proof["period"] == {"D_power": 8, "stem": 64, "forward_g": True, "D6_block_inferred": False}


def test_ad2_display_units_and_declared_picard_scope_are_not_runtime_unit_assignments(project):
    # The new source proof does not prove the separate 20+H Picard comparison.
    # Transport uses the user's declared path and must retain its obligation.
    for workspace in images(project):
        row, claim, _, _ = records(workspace)
        assert claim.conclusion["coefficient_parameter"]["value"] == 1
        if workspace.id == "ws_3sigma_i":
            assert not row.display_coefficient
            continue
        plan = workspace.settings["atlas_transport"]
        display = row.display_coefficient
        expected = 3 if workspace.id == "ws_q8-ro-a0-b3" else 2  # zeta^2, zeta
        assert display == claim.conclusion["atlas_display_coefficient"]
        assert display["source_unit"] == 1 and display["target_unit"] == expected
        assert display["transported_value"] == 1 and display["value"] == expected
        assert display["resolved"] and not display["requires_runtime"]
        assert display["frobenius_applied_to_parameter_once"]
        assert claim.conclusion["atlas_transport"]["normalization"] == plan["normalization"]
        if workspace.id == "ws_q8-ro-a1-b1":
            assert plan["normalization"]["status"] == "source-declared"
            assert plan["normalization"]["obligations"]
            assert plan["display_thom_basis"]["obligations"] == plan["normalization"]["obligations"]
            assert plan["display_thom_basis"]["external_thom_unit"] is None
            assert plan["display_thom_basis"]["D_shift_is_permanent_period"] is False
        else:
            assert plan["normalization"]["status"] == "exact"
            assert not plan["normalization"]["obligations"]


def test_backend_stored_endpoint_fates_use_the_verified_row_not_its_review_alias(project):
    candidate = deepcopy(project)
    for workspace in images(candidate):
        row, claim, source, target = records(workspace)
        before = deepcopy(claim.conclusion)
        sync_differential_events(workspace)
        for node, role, conclusion in ((source, "supports", "supports_differential"),
                                       (target, "receives", "is_hit")):
            fate = derive_class_fate(workspace, node.id, project=candidate)
            assert fate.first_hfpss_death == {"page": 19, "role": role, "claim_id": row.id}
            assert fate.conclusion == conclusion and fate.conclusion_page == 19
            assert claim.id in fate.justification_ids
            assert class_is_live_on_page(workspace, node.id, 19, project=candidate)
            assert not class_is_live_on_page(workspace, node.id, 20, project=candidate)
        assert claim.conclusion == before


def test_old_d19_is_review_and_only_its_same_equation_is_authorized_as_a_render_alias(project):
    for workspace in images(project):
        row, claim, _, _ = records(workspace)
        old = [d for d in workspace.differentials if d.page == 19 and d.label == "FN-3I-010"]
        assert len(old) == 1 and old[0].status == "review"
        old_claim = next(p for p in workspace.propositions if p.id == old[0].proposition_id)
        assert old_claim.status == "review" and old_claim.conclusion["source_status"] == "withdrawn-proof"
        assert claim.conclusion["render_equation_aliases"] == [{
            "fact_id": "FN-3I-010", "page": 19, "status": "review", "scope": "same-equation-only",
        }]
        assert row.period_stem == 64 and old[0].period_stem == 32
        assert [d for d in workspace.differentials if d.page == 19 and d.status == "verified"] == [row]
        zero = next(p for p in workspace.propositions if p.conclusion.get("fact_id") == A6_ZERO)
        assert zero.kind == "zero-differential" and zero.status == "verified"
        assert zero.conclusion["page"] == 19 and zero.conclusion["period_stem"] == 64
        assert zero.conclusion["cycle_constraint"] == "outgoing-only"


def test_migration_restores_the_independent_row_without_duplicate_endpoints(project):
    candidate = deepcopy(project)
    expected = {w.id: tuple(asdict(item) for item in records(w)) for w in images(candidate)}
    for workspace in images(candidate):
        row, claim, _, _ = records(workspace)
        workspace.differentials = [d for d in workspace.differentials if d.id != row.id]
        workspace.propositions = [p for p in workspace.propositions if p.id != claim.id]
    for _ in range(2):
        candidate = migrate_project(candidate)
        assert {w.id: tuple(asdict(item) for item in records(w)) for w in images(candidate)} == expected


def probe(name, pattern, stem, filtration, two=0, j=0):
    return {"name": name, "pattern": pattern, "stem": stem, "filtration": filtration, "two": two, "j": j}


@pytest.fixture(scope="module", params=tuple(ATLAS))
def chart(project, request):
    workspace = next(w for w in images(project) if w.id == request.param)
    shift = ATLAS[workspace.id]
    probes = []
    for d8, g in TRANSLATIONS:
        stem, filtration = 14+shift+64*d8+20*g, 2+4*g
        prefix = f"D8{d8}:g{g}"
        for suffix, pattern, s, f in (
            (":source", "S62", stem, filtration),
            (":target", "S11", stem-1, filtration+19),
        ):
            probes += [probe(prefix+suffix, pattern, s, f),
                       probe(prefix+suffix+"-j", pattern, s, f, j=1),
                       probe(prefix+suffix+"-two", pattern, s, f, two=1)]
        probes += [probe(prefix+":other-source", "S62V", stem, filtration),
                   probe(prefix+":target-j-d3-source", "S62V", stem, filtration+16),
                   probe(prefix+":A6", "S62", stem+32, filtration),
                   probe(prefix+":B6", "S11", stem+31, filtration+19)]
    payload = {
        "project": asdict(project), "workspaces": [workspace.id],
        "pages": [3, 4, 11, 12, 19, 20, 24], "vectorAudit": True,
        "bounds": {"stemMin": shift-55, "stemMax": shift+137,
                   "filtrationMin": 0, "filtrationMax": 30},
        "d19Probes": probes, "fact": FACT,
    }
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""
    return {
      d19Probes:input.d19Probes.map(probe=>{
        const node={style:{e2_pattern:probe.pattern,two_valuation:probe.two,j_order:probe.j}};
        const grade={stem:probe.stem,filtration:probe.filtration};
        return {...probe,live:algebra.live(node,grade),ports:[...(algebra.ports(node,grade)||[])]};
      }),
      forcedEdges:edges.filter(e=>e.diff.label===input.fact).map(e=>({
        id:e.diff.id,status:e.diff.status,source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
        sourceLive:algebra.live(classes.get(e.diff.source_id),e.sourceGrade),
        targetLive:algebra.live(classes.get(e.diff.target_id),e.targetGrade)})),
      oldEdges:edges.filter(e=>e.diff.page===19&&e.diff.label==='FN-3I-010').map(e=>({
        id:e.diff.id,status:e.diff.status,source:e.sourceGrade,target:e.targetGrade})),
      renderedGroups:differentialRenderGroups(ws,edges,algebra)
        .filter(e=>e.diff.page===19).map(e=>({
          id:e.diff.id,label:e.diff.label,status:e.diff.status,source:e.sourceGrade,target:e.targetGrade,
          aliases:e.renderAliases.map(a=>({id:a.id,label:a.label,status:a.status}))})),
      incomingD3:edges.filter(e=>e.diff.id.endsWith('formal_diff_three_d3_h1_2_derived'))
        .map(e=>({source:e.sourceGrade,target:e.targetGrade,admitted:algebra.canApply(e.diff),status:e.diff.status})),
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
    return next(item for item in row["d19Probes"] if item["name"] == name)


def test_d19_draws_every_d8_and_forward_g_copy_with_live_exact_endpoints(chart):
    workspace_id, rows = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8{d8}:g{g}"
        stem, filtration = 14+ATLAS[workspace_id]+64*d8+20*g, 2+4*g
        for suffix in (":source", ":target"):
            item = observation(rows[19], prefix+suffix)
            assert item["live"] and item["ports"] == ["0:0"]
        edge = next(e for e in rows[19]["forcedEdges"]
                    if (e["source"]["stem"], e["source"]["filtration"]) == (stem, filtration))
        assert (edge["target"]["stem"], edge["target"]["filtration"]) == (stem-1, filtration+19)
        assert edge["status"] == "verified" and edge["admitted"]
        assert edge["sourceLive"] and edge["targetLive"]
        assert edge["coefficient"]["resolved"] and edge["coefficient"]["value"] == 1
    for row in rows.values():
        assert row["blockedFromPage"] is None and not row["conflicts"]
        assert not row["dangling"]


def test_e20_takes_the_finite_constant_source_and_target_not_extra_j_or_two_layers(chart):
    _, rows = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8{d8}:g{g}"
        for suffix in (":source", ":target"):
            assert not observation(rows[19], prefix+suffix+"-j")["live"]
            assert not observation(rows[19], prefix+suffix+"-two")["live"]
            for page in (20, 24):
                item = observation(rows[page], prefix+suffix)
                assert not item["live"] and not item["ports"]
                assert not observation(rows[page], prefix+suffix+"-j")["live"]
                assert not observation(rows[page], prefix+suffix+"-two")["live"]
        assert not observation(rows[19], prefix+":other-source")["live"]
    assert not rows[20]["forcedEdges"] and not rows[20]["oldEdges"]
    assert not rows[20]["renderedGroups"]


def test_target_positive_j_is_an_earlier_primitive_d3_image_and_is_never_restored(chart):
    workspace_id, rows = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8{d8}:g{g}"
        stem, filtration = 14+ATLAS[workspace_id]+64*d8+20*g, 2+4*g
        assert observation(rows[3], prefix+":target-j")["live"]
        assert observation(rows[3], prefix+":target-j-d3-source")["live"]
        edge = next(e for e in rows[3]["incomingD3"]
                    if (e["target"]["stem"], e["target"]["filtration"]) == (stem-1, filtration+19))
        assert (edge["source"]["stem"], edge["source"]["filtration"]) == (stem, filtration+16)
        assert edge["status"] == "verified" and edge["admitted"]
        for page in (4, 19, 20, 24):
            assert not observation(rows[page], prefix+":target-j")["live"]
            assert not observation(rows[page], prefix+":target-j-d3-source")["live"]


def test_ad6_zero_d19_and_b6_earlier_d11_are_not_replaced_by_a_d4_repeat(chart):
    workspace_id, rows = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8{d8}:g{g}"
        for page in (19, 20):
            a6 = observation(rows[page], prefix+":A6")
            assert a6["live"] and a6["ports"] == ["0:0"]
        assert observation(rows[11], prefix+":B6")["live"]
        for page in (12, 19, 20, 24):
            b6 = observation(rows[page], prefix+":B6")
            assert not b6["live"] and not b6["ports"]
        stem, filtration = 46+ATLAS[workspace_id]+64*d8+20*g, 2+4*g
        for key in ("forcedEdges", "oldEdges", "renderedGroups"):
            assert not any((e["source"]["stem"], e["source"]["filtration"]) == (stem, filtration)
                           for e in rows[19][key])


def test_same_equation_historical_alias_is_retained_but_only_one_verified_arrow_is_drawn(chart):
    _, rows = chart
    before = rows[19]
    assert before["forcedEdges"] and before["oldEdges"]
    for edge in before["forcedEdges"]:
        same_endpoints = lambda item: item["source"] == edge["source"] and item["target"] == edge["target"]
        old = [item for item in before["oldEdges"] if same_endpoints(item)]
        assert len(old) == 1 and old[0]["status"] == "review"
        groups = [item for item in before["renderedGroups"] if same_endpoints(item)]
        assert len(groups) == 1, (edge, groups)
        group = groups[0]
        assert group["id"] == edge["id"] and group["label"] == FACT and group["status"] == "verified"
        assert {alias["id"] for alias in group["aliases"]} == {edge["id"], old[0]["id"]}
        assert {alias["label"]: alias["status"] for alias in group["aliases"]} == {
            FACT: "verified", "FN-3I-010": "review",
        }
    assert len(before["renderedGroups"]) == len(before["forcedEdges"])
