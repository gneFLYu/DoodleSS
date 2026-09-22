"""Verified finite mixed d17 without choosing its nonzero F4 unit.

The actual migrated project supplies the proof and every earlier map. All six
atlas images use the real chart/quotient engine, including D8 in both directions
and forward g. The separate D7 residue is not promoted by a D4 translation.
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
from test_mixed_d5_parameters import MIXED_ATLAS


WORKSPACE = "ws_sigma_i_2sigma_j"
FACT = "DER-MIX-D17-V-D3"
ROW = "formal_diff_mixed_d17_v_D3_forced"
PARAMETER = "mixed_d17_VD3"
TRANSLATIONS = tuple((d8, g) for d8 in (-1, 0, 1) for g in (0, 1, 6)) + ((-2, 6),)


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    result = [w for w in project.workspaces if w.id == WORKSPACE or
              w.settings.get("atlas_transport", {}).get("source_workspace_id") == WORKSPACE]
    assert {w.id for w in result} == set(MIXED_ATLAS)
    return result


def records(workspace):
    rows = [d for d in workspace.differentials if d.label == FACT]
    assert len(rows) == 1
    row = rows[0]
    claim = next(p for p in workspace.propositions if p.id == row.proposition_id)
    classes = {n.id: n for n in workspace.classes}
    return row, claim, classes[row.source_id], classes[row.target_id]


def test_six_rows_keep_verified_rank_one_proof_and_unresolved_nonzero_unit(project):
    admitted = admitted_proposition_ids(project)
    for workspace in images(project):
        row, claim, source, target = records(workspace)
        data = claim.conclusion
        reflected, shift = MIXED_ATLAS[workspace.id]
        assert row.id.endswith(ROW) and row.status == claim.status == "verified"
        assert claim.id in admitted
        assert data["fact_id"] == FACT
        assert data["source_status"] == "independently-verified-nonzero-unit"
        assert not data["source_blockers"] and not data["withdrawn_dependencies"]
        assert not data["machine_verification_pending"]
        assert (source.grade.stem, source.grade.filtration) == (24 + shift, 2)
        assert (target.grade.stem, target.grade.filtration) == (23 + shift, 19)
        for node, pattern in ((source, "S02"), (target, "S73")):
            assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                    node.style.get("j_order", 0)) == (pattern, 0, 0)
            assert not node.archived
        assert row.page == data["page"] == 17
        assert row.period_stem == data["period_stem"] == 64
        assert data["period_multiplier"] == "D^8" and data["period_is_invertible"]
        assert data["coefficient_scope"] == "exact-port"
        assert data["rank_one_unit_certificate"] == {
            "status": "verified", "kind": "isolated-finite-F4-isomorphism", "page": 17,
            "source_pattern": "S02", "target_pattern": "S73", "coefficient_scope": "exact-port",
        }
        parameter = data["coefficient_parameter"]
        assert parameter["id"] == PARAMETER and parameter["symbol"] == r"\lambda_{17}"
        assert parameter["domain"] == [1, 2, 3] and parameter["value"] is None
        assert parameter["frobenius_power"] == int(reflected)
        assert PARAMETER not in workspace.settings.get("coefficient_assignments", {})
        assert "coefficient_normalization" not in data and "coefficient_condition" not in data


def test_finite_proof_records_noninvertible_high_multiplier_and_every_odd_page(project):
    workspace = next(w for w in project.workspaces if w.id == WORKSPACE)
    _, claim, _, _ = records(workspace)
    proof = claim.conclusion["verification_certificate"]
    assert proof["status"] == "verified"
    assert proof["method"] == "Complete finite exclusion and RO strong vanishing line"
    assert proof["source_workspace_id"] == WORKSPACE and proof["scope"] == "source-workspace"
    assert proof["page"] == 17 and proof["source_refs"]
    assert proof["low_source"] == {"bidegree": [24, 2], "pattern": "S02", "port": "0:0"}
    assert proof["low_target"] == {"bidegree": [23, 19], "pattern": "S73", "port": "0:0"}
    assert proof["translation"] == {"g_exponent": 6, "D_exponent": -16,
                                    "forward_g_only": True, "invertible_in_HFPSS": False}
    assert proof["high_source"] == {"bidegree": [16, 26], "pattern": "S02", "port": "0:0", "dimension": 1}
    assert proof["high_target"]["bidegree"] == [15, 43]
    assert proof["high_target"]["pattern"] == "S73" and proof["high_target"]["dimension"] == 1
    incoming = {entry["page"]: entry for entry in proof["incoming_inventory"]}
    assert set(incoming) == set(range(3, 24, 2))
    assert all(entry["source_bidegree"] == [17, 26-page] for page, entry in incoming.items())
    # X=x^3u has stem -3: the S53 motif's displayed base already contains D.
    assert incoming[3]["representative"] == "Xk^5D^5"
    assert "permanent" in incoming[3]["reason"]
    assert incoming[7]["representative"] == "Tk^4D^4" and "c nonzero" in incoming[7]["reason"]
    assert incoming[15]["representative"] == "Tk^2D^3"
    assert "c!=1" in incoming[15]["reason"] and "c=1" in incoming[15]["reason"]
    assert {page for entry in proof["outgoing_inventory"] for page in entry["pages"]} == set(range(3, 24, 2))
    assert proof["conditional_premise"] == {
        "fact_id": "DER-MIX-D9-P-D2", "condition": "c=1", "coefficient": 3,
        "independent_of": ["b", "row533", "Jan29"],
    }
    assert proof["vanishing_line"] == {"filtration": 23, "empty_from_page": 24, "all_RO_gradings": True}
    assert proof["coefficient_result"] == "nonzero unit only" and proof["no_withdrawn_premise"]
    assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(claim.conclusion["derived_from"])


def test_earlier_mixed_parameter_reviews_are_not_promoted_or_assigned(project):
    for workspace in images(project):
        assignments = workspace.settings.get("coefficient_assignments", {})
        assert not {PARAMETER, "mixed_d5_A", "mixed_d5_B"}.intersection(assignments)
        for fact in ("FN-MIX-002", "FN-MIX-003", "FN-MIX-005", "DER-MIX-D5-A-EVEN",
                     "DER-MIX-D9-P-D2", "DER-MIX-D9-P-D6", "DER-MIX-D9-Q-D2", "DER-MIX-D9-Q-D6"):
            rows = [row for row in workspace.differentials if row.label == fact]
            assert rows and all(row.status == "review" for row in rows)
            for row in rows:
                claim = next(p for p in workspace.propositions if p.id == row.proposition_id)
                assert claim.status == "review"


def test_migration_restores_all_six_rows_and_is_idempotent(project):
    candidate = deepcopy(project)
    expected = {w.id: tuple(asdict(record) for record in records(w)) for w in images(candidate)}
    for workspace in images(candidate):
        row, claim, _, _ = records(workspace)
        workspace.differentials = [d for d in workspace.differentials if d.id != row.id]
        workspace.propositions = [p for p in workspace.propositions if p.id != claim.id]
    for _ in range(2):
        candidate = migrate_project(candidate)
        assert {w.id: tuple(asdict(record) for record in records(w)) for w in images(candidate)} == expected


def test_d7_residue_has_no_independently_unproved_d17_sibling(project):
    for workspace in images(project):
        row, claim, source, _ = records(workspace)
        assert row.period_stem == 64 and row.period_stem != 32
        assert "does not determine the separate VD^7 residue" in claim.conclusion["derivation"]
        shift = MIXED_ATLAS[workspace.id][1]
        rows = [d for d in workspace.differentials if d.page == 17]
        nodes = {n.id: n for n in workspace.classes}
        assert all(not (nodes[d.source_id].style.get("e2_pattern") == "S02"
                        and nodes[d.source_id].grade.filtration == 2
                        and (nodes[d.source_id].grade.stem - shift - 56) % 64 == 0) for d in rows)
        assert (source.grade.stem - shift - 56) % 64 == 32


def probe(name, pattern, stem, filtration, j=0):
    return {"name": name, "pattern": pattern, "stem": stem, "filtration": filtration, "j": j}


def observation(page, name):
    return next(item for item in page["finiteProbes"] if item["name"] == name)


@pytest.fixture(scope="module", params=tuple(MIXED_ATLAS))
def chart(project, request):
    workspace = next(w for w in images(project) if w.id == request.param)
    shift = MIXED_ATLAS[workspace.id][1]
    probes = []
    for d8, g in TRANSLATIONS:
        stem, filtration = 24 + shift + 64*d8 + 20*g, 2 + 4*g
        prefix = f"D8-{d8}-g-{g}"
        probes += [probe(prefix+"-source", "S02", stem, filtration),
                   probe(prefix+"-target", "S73", stem-1, filtration+17),
                   probe(prefix+"-target-bo", "S73V", stem-1, filtration+17),
                   probe(prefix+"-D7-source", "S02", stem+32, filtration),
                   probe(prefix+"-D7-target", "S73", stem+31, filtration+17)]
    for d8 in (-1, 0, 1):
        probes.append(probe(f"Q-D3-{d8}-positive-j", "S22H", 26+shift+64*d8, 2, j=1))
    payload = {"project": asdict(project), "workspaces": [workspace.id], "pages": [17, 18, 19, 24],
               "bounds": {"stemMin": shift-42, "stemMax": shift+242, "filtrationMin": 0, "filtrationMax": 44},
               "vectorAudit": True, "finiteProbes": probes, "fact": FACT}
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""return {
      lateIncoming:edges.filter(e=>e.diff.id.endsWith('formal_diff_mixed_d19_x_D4_forced'))
        .map(e=>({id:e.diff.id,source:e.sourceGrade,target:e.targetGrade,
          admitted:algebra.canApply(e.diff),status:e.diff.status})),
      finiteProbes: input.finiteProbes.map(probe=>{
        const node={style:{e2_pattern:probe.pattern,two_valuation:0,j_order:probe.j}};
        const grade={stem:probe.stem,filtration:probe.filtration};
        return {...probe,live:algebra.live(node,grade),ports:[...(algebra.ports(node,grade)||[])]};
      }),
      forcedRows:ws.differentials.filter(d=>d.label===input.fact).map(d=>({id:d.id,
        admitted:algebra.canApply(d),unitInvariant:algebra.unitInvariant(d),coefficient:algebra.coefficientState(d)})),
      forcedEdges:edges.filter(e=>e.diff.label===input.fact).map(e=>({
        id:e.diff.id,status:e.diff.status,source:e.sourceGrade,target:e.targetGrade,
        admitted:algebra.canApply(e.diff),unitInvariant:algebra.unitInvariant(e.diff),
        coefficient:algebra.coefficientState(e.diff),
        sourceLive:algebra.live(classes.get(e.diff.source_id),e.sourceGrade),
        targetLive:algebra.live(classes.get(e.diff.target_id),e.targetGrade)})),
      page, points: points.length"""
    completed = subprocess.run(["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
                               input=json.dumps(payload), capture_output=True, text=True,
                               encoding="utf-8", check=True, timeout=240)
    output = json.loads(completed.stdout)
    assert len(output) == 1 and output[0]["id"] == workspace.id
    return shift, {page["page"]: page for page in output[0]["pages"]}


def test_actual_atlas_finite_d17_quotient_for_d8_and_forward_g(chart):
    shift, pages = chart
    e17 = pages[17]
    for d8, g in TRANSLATIONS:
        prefix = f"D8-{d8}-g-{g}"
        stem, filtration = 24+shift+64*d8+20*g, 2+4*g
        for suffix in ("source", "target"):
            at17 = observation(e17, prefix+"-"+suffix)
            assert at17["live"] and at17["ports"] == ["0:0"]
            for page in (18, 24):
                later = observation(pages[page], prefix+"-"+suffix)
                assert not later["live"] and not later["ports"]
        arrow = next(e for e in e17["forcedEdges"] if e["source"]["stem"] == stem
                     and e["source"]["filtration"] == filtration)
        assert arrow["target"]["stem"] == stem-1 and arrow["target"]["filtration"] == filtration+17
        assert arrow["sourceLive"] and arrow["targetLive"] and arrow["admitted"] and arrow["unitInvariant"]
        assert arrow["status"] == "verified"
        assert not arrow["coefficient"]["resolved"] and arrow["coefficient"].get("value") is None
    for page in pages.values():
        assert page["blockedFromPage"] is None and not page["conflicts"]
    assert not pages[18]["forcedEdges"] and not pages[24]["forcedEdges"]


def test_actual_atlas_separate_d7_residue_and_completed_columns_are_unchanged(chart):
    _, pages = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8-{d8}-g-{g}"
        for page in (17, 18, 24):
            # This completed column was already absent after primitive d3;
            # the new finite d17 must not introduce a fabricated surviving tail.
            assert not observation(pages[page], prefix+"-target-bo")["ports"]
            for suffix in ("D7-source", "D7-target"):
                retained = observation(pages[page], prefix+"-"+suffix)
                # The independent incoming d19 now removes high VD7, not its
                # possible d17 target. Low VD7 and all E17/E18 observations
                # remain unchanged; do not erase a whole D8/g family.
                if page == 24 and suffix == "D7-source" and g >= 5:
                    assert not retained["live"] and retained["ports"] == []
                    witness = next(e for e in pages[19]["lateIncoming"]
                                   if (e["target"]["stem"], e["target"]["filtration"])
                                   == (retained["stem"], retained["filtration"]))
                    assert (witness["source"]["stem"], witness["source"]["filtration"]) == (
                        retained["stem"]+1, retained["filtration"]-19)
                    assert witness["source"]["representation"] == witness["target"]["representation"]
                    assert witness["admitted"] and witness["status"] == "verified"
                else:
                    assert retained["live"] and retained["ports"] == ["0:0"]
        d7_stem = observation(pages[17], prefix+"-D7-source")["stem"]
        d7_filtration = observation(pages[17], prefix+"-D7-source")["filtration"]
        assert not any(e["source"]["stem"] == d7_stem and e["source"]["filtration"] == d7_filtration
                       for e in pages[17]["forcedEdges"])
    for d8 in (-1, 0, 1):
        for page in (17, 18, 24):
            tail = observation(pages[page], f"Q-D3-{d8}-positive-j")
            assert tail["live"] and "0:1" in tail["ports"]


def test_actual_atlas_d17_admission_does_not_resolve_lambda(chart):
    _, pages = chart
    rows = pages[17]["forcedRows"]
    assert len(rows) == 1
    assert rows[0]["admitted"] and rows[0]["unitInvariant"]
    assert rows[0]["coefficient"]["resolved"] is False
    assert rows[0]["coefficient"].get("value") is None
