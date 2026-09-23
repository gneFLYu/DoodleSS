"""Opt-in document adoption, distinguished from independently verified algebra.

Only the application profile opts into this baseline. Tests exercise the real
migration and chart engine; no extra differential is inserted to make a page
pass, and all coefficient settings remain owned by the user.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from domain.atlas_transport import q8_atlas_transport_plan
from domain.document_baseline import apply_document_baseline
from domain.migrations import migrate_project
from domain.seed import demo_project


MIXED = "ws_sigma_i_2sigma_j"
FIVE_LABELS = {"FN-MIX-002", "FN-MIX-003", "DER-MIX-D5-A-EVEN", "FN-MIX-005"}
PARAMETERS = {"mixed_d5_B": 1,
              "mixed_d17_VD3": 1, "mixed_d19_XD4": 1}
NEW_ROWS = {
    "formal_diff_document_mixed_d11_r_D2":
        (11, 32, "S73", (15, 3), "S22H", (14, 14), "TQ8-MIX-L0528"),
    "formal_diff_document_mixed_d19_r_D5":
        (19, 64, "S73", (39, 3), "S22H", (38, 22), "TQ8-MIX-L0538"),
    "formal_diff_document_mixed_d21_p_D4":
        (21, 64, "S22Y", (34, 2), "S53", (33, 23), "DER-MIX-D21-P-D4-EULER"),
    "formal_diff_document_mixed_d21_q_D4":
        (21, 64, "S22H", (34, 2), "S53", (33, 23), "DER-MIX-D21-Q-D4-B-INVERSE"),
}


def workspace(project, ident=MIXED):
    return next(w for w in project.workspaces if w.id == ident)


def claim_for(ws, row):
    return next(p for p in ws.propositions if p.id == row.proposition_id)


def assignments(project):
    return {w.id: deepcopy(w.settings.get("coefficient_assignments")) for w in project.workspaces}


def baseline(project):
    copy = deepcopy(project)
    copy.research_brief["document_baseline"] = True
    return migrate_project(copy)


@pytest.fixture(scope="module")
def strict_project():
    return migrate_project(demo_project())


@pytest.fixture(scope="module")
def adopted_project(strict_project):
    return baseline(strict_project)


def test_core_demo_and_strict_migration_do_not_opt_in(strict_project):
    assert strict_project.research_brief.get("document_baseline") is not True
    ws = workspace(strict_project)
    assert not set(NEW_ROWS) & {d.id for d in ws.differentials}
    rows = [d for d in ws.differentials if d.page == 5 and d.label in FIVE_LABELS]
    assert len(rows) == 5
    assert all(d.status not in {"admitted", "verified"} for d in rows)
    assert all(not claim_for(ws, d).conclusion.get("document_baseline") for d in rows)


@pytest.mark.parametrize("flag", [False, None, "true", 1])
def test_direct_profile_gate_requires_boolean_true(strict_project, flag):
    project = deepcopy(strict_project)
    project.research_brief["document_baseline"] = flag
    before = asdict(project)
    apply_document_baseline(project)
    assert asdict(project) == before


def test_other_project_id_is_not_changed(strict_project):
    project = deepcopy(strict_project)
    project.id = "user-scratch-project"
    project.research_brief["document_baseline"] = True
    before = asdict(project)
    apply_document_baseline(project)
    assert asdict(project) == before


@pytest.mark.parametrize("stored_flag, expected", [(None, True), (False, False), (True, True)])
def test_flask_load_defaults_only_missing_profile_and_preserves_false(monkeypatch, strict_project, stored_flag, expected):
    import app as app_module
    payload = asdict(strict_project)
    if stored_flag is None:
        payload["research_brief"].pop("document_baseline", None)
    else:
        payload["research_brief"]["document_baseline"] = stored_flag
    # A read-only fake path avoids changing the actual saved project.
    encoded = json.dumps(payload)
    monkeypatch.setattr(app_module, "DATA_PATH", SimpleNamespace(
        exists=lambda: True, read_text=lambda **kwargs: encoded))
    loaded = app_module.load_project()
    assert loaded.research_brief["document_baseline"] is expected
    actual = {d.id for d in workspace(loaded).differentials}
    assert (set(NEW_ROWS) <= actual) is expected


def test_profile_parameters_are_claim_defaults_not_user_assignments(strict_project, adopted_project):
    assert assignments(adopted_project) == assignments(strict_project)
    ws = workspace(adopted_project)
    for ident, value in PARAMETERS.items():
        specs = [p.conclusion["coefficient_parameter"] for p in ws.propositions
                 if p.conclusion.get("coefficient_parameter", {}).get("id") == ident
                 and not p.conclusion["coefficient_parameter"].get("source_parameter")]
        assert specs, ident
        assert {s["value"] for s in specs} == {value}, (ident, specs)


def test_only_b_rows_remain_document_adopted_while_c_has_a_live_proof(adopted_project):
    ws = workspace(adopted_project)
    rows = [d for d in ws.differentials if d.page == 5 and d.label in FIVE_LABELS]
    assert len(rows) == 5
    for row in rows:
        claim = claim_for(ws, row)
        if claim.conclusion.get("coefficient_parameter", {}).get("id") == "mixed_d5_A":
            assert row.status == claim.status == "source-verified"
            assert claim.conclusion["coefficient_parameter"]["proof_binding"]
            assert claim.conclusion["coefficient_parameter"]["value"] is None
            assert "document_baseline" not in claim.conclusion
            continue
        assert row.status == claim.status == "admitted"
        assert claim.conclusion["source_status"] == "document-adopted"
        assert claim.conclusion["document_baseline"]["authority"] == "document-adopted"
        assert claim.source_ref
        if row.linear_map_id:
            assert next(m for m in ws.differential_maps if m.id == row.linear_map_id).status == "admitted"


@pytest.mark.parametrize("ident, expected", NEW_ROWS.items())
def test_new_document_rows_use_actual_exact_constant_ports(adopted_project, ident, expected):
    ws = workspace(adopted_project)
    page, period, sp, sg, tp, tg, fact = expected
    row = next(d for d in ws.differentials if d.id == ident)
    claim = claim_for(ws, row)
    nodes = {n.id: n for n in ws.classes}
    assert row.page == page and row.period_stem == period
    assert row.status == claim.status == "admitted"
    assert claim.conclusion["source_status"] == "document-adopted"
    assert claim.conclusion["fact_id"] == fact
    for node, pattern, grade in ((nodes[row.source_id], sp, sg), (nodes[row.target_id], tp, tg)):
        assert node.style["e2_pattern"] == pattern
        assert (node.grade.stem, node.grade.filtration) == grade
        assert node.style.get("two_valuation", 0) == node.style.get("j_order", 0) == 0
    assert claim.conclusion["document_baseline"]["authority"] == "document-adopted"


def test_q_d21_is_linked_inverse_b_and_positive_j_is_separate(adopted_project):
    ws = workspace(adopted_project)
    row = next(d for d in ws.differentials if d.id == "formal_diff_document_mixed_d21_q_D4")
    spec = claim_for(ws, row).conclusion["coefficient_parameter"]
    assert spec["inverse_parameter_id"] == "mixed_d5_B"
    assert spec["value"] == 1 and spec["frobenius_power"] == 0
    assert spec["id"] != "mixed_d5_B"  # The numerator cannot accidentally be inverted twice.
    assert all("lambda21" not in p.conclusion.get("coefficient_parameter", {}).get("id", "").replace("_", "")
               for p in ws.propositions)


def test_repeated_migration_keeps_pages_and_all_sixteen_atlas_tiles(adopted_project):
    project = deepcopy(adopted_project)
    for index, ws in enumerate(project.workspaces):
        ws.page = [5, 11, 19, 21, 22][index % 5]
    pages = {w.id: w.page for w in project.workspaces}
    counts = {w.id: (len(w.classes), len(w.differentials), len(w.propositions), len(w.differential_maps))
              for w in project.workspaces}
    migrate_project(project)
    assert {w.id: w.page for w in project.workspaces} == pages
    assert {w.id: (len(w.classes), len(w.differentials), len(w.propositions), len(w.differential_maps))
            for w in project.workspaces} == counts
    first = asdict(project)
    migrate_project(project)
    assert asdict(project) == first
    assert len(q8_atlas_transport_plan(project)) == 16
    for ws in project.workspaces:
        for items in (ws.classes, ws.differentials, ws.propositions, ws.differential_maps):
            assert len({item.id for item in items}) == len(items)


def test_known_counterexamples_are_not_readmitted(adopted_project):
    two = workspace(adopted_project, "ws_2sigma_i")
    bad = [d for d in two.differentials if d.label == "FN-2I-002"]
    assert bad and all(d.status not in {"admitted", "verified", "verified-pattern"} for d in bad)
    three = workspace(adopted_project, "ws_3sigma_i")
    bad = [d for d in three.differentials if d.label == "FN-3I-010"]
    assert bad and all(d.status not in {"admitted", "verified", "verified-pattern"} for d in bad)
    assert next(d for d in three.differentials if d.id == "formal_diff_three_d19_a_D2_euler_forced").period_stem == 64
    assert next(d for d in three.differentials if d.id == "formal_diff_three_d23_u_D5_forced").period_stem == 64
    ws = workspace(adopted_project)
    for row in [d for d in ws.differentials if d.label == "FN-MIX-006"]:
        assert claim_for(ws, row).conclusion["coefficient_parameter"]["value"] == 3


def test_user_conflicting_assignments_are_preserved(strict_project):
    project = deepcopy(strict_project)
    ws = workspace(project)
    user = {"mixed_d5_A": 1, "mixed_d5_B": 2, "mixed_d17_VD3": 3,
            "mixed_d19_XD4": 2, "user_parameter": 3}
    ws.settings["coefficient_assignments"] = deepcopy(user)
    project.research_brief["document_baseline"] = True
    migrate_project(project)
    assert workspace(project).settings["coefficient_assignments"] == user
    migrate_project(project)
    assert workspace(project).settings["coefficient_assignments"] == user


def test_disabling_a_saved_profile_restores_owned_statuses_without_deleting_nodes(strict_project, adopted_project):
    project = deepcopy(adopted_project)
    user = {"user_parameter": 2}
    workspace(project).settings["coefficient_assignments"] = deepcopy(user)
    nodes_before = {w.id: {n.id for n in w.classes} for w in project.workspaces}
    project.research_brief["document_baseline"] = False
    migrate_project(project)
    strict_by_id = {w.id: w for w in strict_project.workspaces}
    for ws in project.workspaces:
        assert nodes_before[ws.id] <= {n.id for n in ws.classes}
        assert "document_baseline" not in ws.settings
        assert not any(p.conclusion.get("document_baseline") for p in ws.propositions)
        assert not any(p.conclusion.get("coefficient_parameter", {}).get("document_baseline")
                       for p in ws.propositions)
        assert not any(d.id.endswith(tuple(NEW_ROWS)) for d in ws.differentials)
        assert not any(p.conclusion.get("fact_id") == "DER-MIX-D21-JQ-D4-ZERO" for p in ws.propositions)
        old_rows = {d.id: d for d in strict_by_id[ws.id].differentials}
        for row in ws.differentials:
            if row.id in old_rows and row.label in FIVE_LABELS:
                assert row.status == old_rows[row.id].status
        old_claims = {p.id: p for p in strict_by_id[ws.id].propositions}
        for claim in ws.propositions:
            spec = claim.conclusion.get("coefficient_parameter", {})
            if claim.id in old_claims and spec.get("id") in PARAMETERS:
                assert spec["value"] == old_claims[claim.id].conclusion["coefficient_parameter"]["value"]
    assert workspace(project).settings["coefficient_assignments"] == user
    disabled = asdict(project)
    migrate_project(project)
    assert asdict(project) == disabled


def chart(payload):
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    extra = r"""return {coefficientRows:ws.differentials.filter(d=>d.page===page).map(d=>({
        id:d.id,label:d.label,status:d.status,coefficient:algebra.coefficientState(d),applicable:algebra.canApply(d)})),
      actualEdges:edges.map(e=>({id:e.diff.id,source:e.sourceGrade,target:e.targetGrade,
        coefficient:algebra.coefficientState(e.diff),applicable:algebra.canApply(e.diff)})),
      settingsAfter:ws.settings,page, points: points.length"""
    result = subprocess.run(["node", "-e", harness.replace(marker, extra)], cwd=ROOT,
                            input=json.dumps(payload), text=True, encoding="utf-8",
                            capture_output=True, check=True, timeout=240)
    return {ws["id"]: {p["page"]: p for p in ws["pages"]} for ws in json.loads(result.stdout)}


def ports(page, pattern, stem, filtration):
    return set(next(p["ports"] for p in page["probes"]
                    if (p["pattern"], p["stem"], p["filtration"]) == (pattern, stem, filtration)))


def vector(page, components, stem, filtration):
    return next(p["live"] for p in page["vectorProbes"]
                if p["components"] == components and (p["stem"], p["filtration"]) == (stem, filtration))


@pytest.fixture(scope="module")
def actual_pages(adopted_project):
    probes = [("S62", 6, 2), ("S62", 14, 2), ("S71", 7, 1), ("S71", 15, 1),
              ("S73", 15, 3), ("S22H", 14, 14), ("S73", 39, 3), ("S22H", 38, 22),
              ("S22Y", 34, 2), ("S22H", 34, 2), ("S53", 33, 23)]
    payload = {"project": asdict(adopted_project), "workspaces": [MIXED],
               "pages": [5, 6, 11, 12, 19, 20, 21, 22], "vectorAudit": True,
               "bounds": {"stemMin": 0, "stemMax": 40, "filtrationMin": 0, "filtrationMax": 25},
               "probes": [dict(pattern=p, stem=s, filtration=f) for p, s, f in probes],
               "vectorProbes": [dict(components=c, stem=34, filtration=2)
                                for c in ({"S22Y": 1}, {"S22H": 1}, {"S22Y": 1, "S22H": 1})]}
    return chart(payload)[MIXED]


def test_actual_pages_have_no_blocking_conflicts_or_dangling_arrows(actual_pages):
    for page, data in actual_pages.items():
        assert not data["conflicts"], (page, data["conflicts"])
        assert data["blockedFromPage"] is None, (page, data["blockedFromPage"])
        assert not data["dangling"], (page, data["dangling"])


def test_actual_d5_sources_map_then_disappear_from_the_next_page(actual_pages):
    for pattern, stem in (("S62", 6), ("S62", 14), ("S71", 7), ("S71", 15)):
        filtration = 2 if pattern == "S62" else 1
        assert "0:0" in ports(actual_pages[5], pattern, stem, filtration)
        assert "0:0" not in ports(actual_pages[6], pattern, stem, filtration)


@pytest.mark.parametrize("ident", NEW_ROWS)
def test_each_new_arrow_is_present_at_its_real_anchor(actual_pages, ident):
    page, _, _, sg, _, tg, _ = NEW_ROWS[ident]
    edge = next(e for e in actual_pages[page]["actualEdges"] if e["id"] == ident
                and (e["source"]["stem"], e["source"]["filtration"]) == sg)
    assert (edge["target"]["stem"], edge["target"]["filtration"]) == tg
    assert edge["applicable"] and edge["coefficient"]["resolved"]
    assert edge["coefficient"]["value"] == 1


@pytest.mark.parametrize("page, stem, target_stem, target_filtration", [(11, 15, 14, 14), (19, 39, 38, 22)])
def test_document_r_rows_have_live_endpoints_and_next_page_images(actual_pages, page, stem, target_stem, target_filtration):
    assert "0:0" in ports(actual_pages[page], "S73", stem, 3)
    assert "0:0" in ports(actual_pages[page], "S22H", target_stem, target_filtration)
    assert "0:0" not in ports(actual_pages[page + 1], "S73", stem, 3)
    assert "0:0" not in ports(actual_pages[page + 1], "S22H", target_stem, target_filtration)


def test_d21_is_rank_one_and_retains_the_low_kernel_and_power_series(actual_pages):
    before, after = actual_pages[21], actual_pages[22]
    assert ports(before, "S53", 33, 23) == {"0:0"}
    assert not ports(after, "S53", 33, 23)
    for components in ({"S22Y": 1}, {"S22H": 1}):
        assert vector(before, components, 34, 2)
        assert not vector(after, components, 34, 2)
    assert vector(before, {"S22Y": 1, "S22H": 1}, 34, 2)
    assert vector(after, {"S22Y": 1, "S22H": 1}, 34, 2)
    assert "0:1" in ports(before, "S22H", 34, 2)
    assert "0:1" in ports(after, "S22H", 34, 2)


@pytest.fixture(scope="module")
def mixed_atlas(adopted_project):
    sector_workspaces = {sector.id: sector.workspace_id for sector in adopted_project.grading_sectors}
    plans = {sid: {**plan, "target_workspace_id": sector_workspaces[sid]}
             for sid, plan in q8_atlas_transport_plan(adopted_project).items()
             if plan["source_workspace_id"] == MIXED}
    assert len(plans) == 6
    return plans


def test_six_mixed_atlas_images_keep_adoption_and_single_frobenius(adopted_project, mixed_atlas):
    source = workspace(adopted_project)
    source_rows = {d.id: d for d in source.differentials}
    for sector, plan in mixed_atlas.items():
        target = workspace(adopted_project, plan["target_workspace_id"])
        prefix = "" if target.id == MIXED else f"atlas_{sector}_"
        images = {d.id: d for d in target.differentials}
        for ident in NEW_ROWS:
            row = images[prefix + ident]
            assert row.status == "admitted" and row.period_stem == source_rows[ident].period_stem
            claim = claim_for(target, row)
            assert claim.conclusion["document_baseline"]["authority"] == "document-adopted"
            spec = claim.conclusion.get("coefficient_parameter")
            if spec:
                assert spec["frobenius_power"] == int(plan["reflected"])
        q = claim_for(target, images[prefix + "formal_diff_document_mixed_d21_q_D4"]).conclusion["coefficient_parameter"]
        assert q["inverse_parameter_id"] == "mixed_d5_B"


@pytest.fixture(scope="module")
def atlas_coefficients(adopted_project, mixed_atlas):
    bounds = {}
    ids = []
    for plan in mixed_atlas.values():
        ident, shift = plan["target_workspace_id"], plan["stem_shift"]
        ids.append(ident)
        bounds[ident] = dict(stemMin=4 + shift, stemMax=17 + shift,
                             filtrationMin=0, filtrationMax=9)
    return chart({"project": asdict(adopted_project), "workspaces": ids, "pages": [5],
                  "boundsByWorkspace": bounds, "vectorAudit": True})


def test_actual_atlas_d5_units_apply_frobenius_once(atlas_coefficients, mixed_atlas):
    for sector, plan in mixed_atlas.items():
        data = atlas_coefficients[plan["target_workspace_id"]][5]
        assert not data["conflicts"] and data["blockedFromPage"] is None
        rows = data["coefficientRows"]
        odd = next(d for d in rows if d["label"] == "FN-MIX-003")
        even = next(d for d in rows if d["label"] == "DER-MIX-D5-A-EVEN")
        assert odd["coefficient"]["resolved"] and even["coefficient"]["resolved"]
        assert odd["coefficient"]["value"] == (2 if plan["reflected"] else 3)
        assert even["coefficient"]["value"] == (3 if plan["reflected"] else 2)
        assert odd["applicable"] and even["applicable"]


def test_real_chart_reports_conflicting_user_coefficient_without_overwriting_it(adopted_project):
    project = deepcopy(adopted_project)
    user = {"mixed_d5_A": 1, "user_parameter": 3}
    workspace(project).settings["coefficient_assignments"] = deepcopy(user)
    data = chart({"project": asdict(project), "workspaces": [MIXED], "pages": [5],
                  "bounds": {"stemMin": 4, "stemMax": 17, "filtrationMin": 0, "filtrationMax": 9}})[MIXED][5]
    assert data["settingsAfter"]["coefficient_assignments"] == user
    affected = [d for d in data["coefficientRows"] if d["label"] in {"FN-MIX-003", "DER-MIX-D5-A-EVEN"}]
    assert len(affected) == 2
    assert all(not d["coefficient"]["resolved"] and not d["applicable"] for d in affected)
