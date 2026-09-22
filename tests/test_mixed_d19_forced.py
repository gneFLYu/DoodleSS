"""The independently forced mixed d19, without choosing its nonzero F4 unit.

Exercise the actual migrated project and chart quotient in all six mixed atlas
images. The proof uses the new VD7 outgoing-cycle certificate, not the old
table537 argument, a D4 period, or a chosen value of c, b, or lambda19.
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
from domain.fate import _isolated_rank_one_unit, _parameterized_event_eligibility, derive_class_fate
from domain.migrations import migrate_project
from domain.models import project_from_dict, project_to_dict
from domain.seed import demo_project
from test_mixed_d5_parameters import MIXED_ATLAS


WORKSPACE = "ws_sigma_i_2sigma_j"
FACT = "DER-MIX-D19-X-D4"
ROW = "formal_diff_mixed_d19_x_D4_forced"
CYCLE = "DER-MIX-PHI-CD5-VD7-cycle"
PARAMETER = "mixed_d19_XD4"
TRANSLATIONS = tuple((d8, g) for d8 in (-1, 0, 1) for g in (0, 1, 6))


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
    nodes = {n.id: n for n in workspace.classes}
    return row, claim, nodes[row.source_id], nodes[row.target_id]


def test_all_six_rows_have_exact_finite_ports_and_an_unassigned_nonzero_unit(project):
    admitted = admitted_proposition_ids(project)
    for workspace in images(project):
        row, claim, source, target = records(workspace)
        data = claim.conclusion
        reflected, shift = MIXED_ATLAS[workspace.id]
        assert row.id.endswith(ROW) and row.status == claim.status == "verified"
        assert claim.id in admitted and data["fact_id"] == FACT
        assert data["source_status"] == "independently-verified-nonzero-unit"
        assert not data["source_blockers"] and not data["withdrawn_dependencies"]
        assert not data["machine_verification_pending"]
        assert (source.grade.stem, source.grade.filtration) == (29 + shift, 3)
        assert (target.grade.stem, target.grade.filtration) == (28 + shift, 22)
        for node, pattern in ((source, "S53"), (target, "S02")):
            assert (node.style["e2_pattern"], node.style.get("two_valuation", 0),
                    node.style.get("j_order", 0)) == (pattern, 0, 0)
            assert not node.archived
        assert row.page == data["page"] == 19
        assert row.period_stem == data["period_stem"] == 64
        assert data["period_multiplier"] == "D^8" and data["period_is_invertible"]
        assert data["coefficient_scope"] == "exact-port"
        assert row.required_admitted_premises is True
        assert data["required_admitted_premises"] is True
        cycle = next(p for p in workspace.propositions if p.conclusion.get("fact_id") == CYCLE)
        assert claim.premise_ids == [cycle.id]
        assert data["rank_one_unit_certificate"] == {
            "status": "verified", "kind": "isolated-finite-F4-isomorphism", "page": 19,
            "source_pattern": "S53", "target_pattern": "S02", "coefficient_scope": "exact-port",
        }
        parameter = data["coefficient_parameter"]
        assert parameter["id"] == PARAMETER and parameter["symbol"] == r"\lambda_{19}"
        assert parameter["domain"] == [1, 2, 3] and parameter["value"] is None
        assert parameter["frobenius_power"] == int(reflected)
        assert not {PARAMETER, "mixed_d5_A", "mixed_d5_B"}.intersection(
            workspace.settings.get("coefficient_assignments", {}))
        assert "coefficient_normalization" not in data and "coefficient_condition" not in data


def test_proof_uses_the_new_all_outgoing_vd7_constraint_and_not_historical_table537(project):
    admitted = admitted_proposition_ids(project)
    for workspace in images(project):
        _, claim, _, _ = records(workspace)
        data = claim.conclusion
        assert CYCLE in data["derived_from"]
        assert not {"FN-3I-010", "FN-3I-010-pc", "DER-MIX-PHI-BH-D7-D9-zero"}.intersection(
            data["derived_from"])
        cycle = next(p for p in workspace.propositions if p.conclusion.get("fact_id") == CYCLE)
        assert cycle.status == "verified" and cycle.id in admitted
        evidence = cycle.conclusion
        assert evidence["cycle_constraint"] == "outgoing-only"
        assert evidence["source_fact_id"] == "DER-3I-EULER-CD5-cycle"
        assert evidence["coefficient_scope"] == "exact-port"
        proof = evidence["verification_certificate"]
        assert proof["target_comparison"] == {
            "differential_page": "r>=2", "filtration": "r+2", "injective_from": "r-1",
            "source_injectivity_required": False,
        }
        assert proof["d17_control"]["zero"] and proof["separate_D3_d17_unchanged"]
        assert not proof["high_translation"]["incoming_survival_asserted"]
        assert proof["no_withdrawn_premise"]
        scalar = evidence["transport_certificate"]["coefficient"]
        assert scalar["omega_D_exponent"] == 5 and scalar["euler_zeta_exponent"] == 1
        assert scalar["total_zeta_exponent_mod3"] == 0
        assert scalar["Thom_unit_value"] is None and scalar["Thom_unit_nonzero"]
        assert scalar["target_j_annihilated"]


def test_complete_finite_inventory_covers_survival_incoming_and_noninvertible_detection(project):
    workspace = next(w for w in project.workspaces if w.id == WORKSPACE)
    _, claim, _, _ = records(workspace)
    proof = claim.conclusion["verification_certificate"]
    assert proof["status"] == "verified" and proof["page"] == 19
    assert proof["scope"] == "source-workspace" and proof["source_workspace_id"] == WORKSPACE
    for key, grade, pattern in (("low_source", [29, 3], "S53"), ("low_target", [28, 22], "S02"),
                                ("high_source", [49, 7], "S53"), ("high_target", [48, 26], "S02")):
        assert proof[key]["bidegree"] == grade and proof[key]["pattern"] == pattern
        assert proof[key]["port"] == "0:0" and proof[key]["dimension"] == 1
    assert proof["low_source"]["torsion_order"] == 2 and proof["low_source"]["j_annihilated"]
    assert proof["high_target"]["outgoing_certificate"] == CYCLE
    assert proof["target_translation"] == {
        "g_exponent": 6, "D_exponent": -16, "forward_g_only": True, "invertible_in_HFPSS": False,
    }
    assert {page for entry in proof["low_source_outgoing"] for page in entry["pages"]} == set(range(3, 19, 2))
    high_incoming = {entry["page"]: entry for entry in proof["high_source_incoming"]}
    assert set(high_incoming) == {3, 5, 7}
    assert all(entry["source_bidegree"] == [50, 7-page] for page, entry in high_incoming.items())
    assert set(high_incoming[5]["patterns"]) == {"S22Y", "S22H"}
    assert "entire QD6" in high_incoming[5]["reason"] and "positive-j" in high_incoming[5]["reason"]
    incoming = {entry["page"]: entry for entry in proof["incoming_inventory"]}
    assert set(incoming) == set(range(3, 24, 2))
    assert all(entry["source_bidegree"] == [49, 26-page] for page, entry in incoming.items())
    assert incoming[3]["representative"] == "Xk5D9" and "Euler" in incoming[3]["reason"]
    assert incoming[7]["representative"] == "Tk4D8" and "c nonzero" in incoming[7]["reason"]
    for page in (5, 13, 21):
        assert "Entire primitive d3" in incoming[page]["reason"]
    for page in (9, 17):
        assert "completed positive-j ideal" in incoming[page]["reason"]
    assert "c!=1" in incoming[15]["reason"] and "c=1" in incoming[15]["reason"]
    assert incoming[19]["representative"] == "XkD7=gXD4"
    assert "Euler-H6" in incoming[23]["reason"]
    assert proof["conditional_premise"] == {
        "fact_id": "DER-MIX-D9-P-D6", "condition": "c=1", "coefficient": 3,
        "independent_of": ["b", "row537", "Jan29"],
    }
    assert proof["even_pages"] and proof["low_source_incoming"] and proof["high_source_outgoing"]
    assert proof["vanishing_line"] == {"filtration": 23, "empty_from_page": 24, "all_RO_gradings": True}
    assert proof["coefficient_result"] == "nonzero unit only" and proof["no_withdrawn_premise"]
    assert "No negative-g HFPSS" in proof["forward_detection"]
    assert any("comparison only" in ref for ref in proof["source_refs"] if "table_Q8" in ref)
    q_zero = next(p for p in workspace.propositions if p.conclusion.get("fact_id") == "FN-MIX-005-Q-zero")
    q_proof = q_zero.conclusion["verification_certificate"]
    assert "all positive j powers" in q_proof["closure"]
    assert "filtration -1" in q_proof["positive_j_layers"]


def test_migration_restores_six_rows_without_altering_the_independent_d17(project):
    candidate = deepcopy(project)
    expected = {w.id: tuple(asdict(record) for record in records(w)) for w in images(candidate)}
    earlier = {w.id: [asdict(d) for d in w.differentials if d.label == "DER-MIX-D17-V-D3"]
               for w in images(candidate)}
    assert all(len(rows) == 1 and rows[0]["page"] == 17 and rows[0]["period_stem"] == 64
               for rows in earlier.values())
    for workspace in images(candidate):
        row, claim, _, _ = records(workspace)
        workspace.differentials = [d for d in workspace.differentials if d.id != row.id]
        workspace.propositions = [p for p in workspace.propositions if p.id != claim.id]
    for _ in range(2):
        candidate = migrate_project(candidate)
        assert {w.id: tuple(asdict(record) for record in records(w)) for w in images(candidate)} == expected
        assert {w.id: [asdict(d) for d in w.differentials if d.label == "DER-MIX-D17-V-D3"]
                for w in images(candidate)} == earlier


def test_opt_in_row_flag_and_exact_dependencies_survive_json_roundtrip(project):
    restored = project_from_dict(json.loads(json.dumps(project_to_dict(project))))
    for workspace in images(restored):
        row, claim, _, _ = records(workspace)
        cycle = next(p for p in workspace.propositions if p.conclusion.get("fact_id") == CYCLE)
        assert row.required_admitted_premises is True
        assert claim.conclusion["required_admitted_premises"] is True
        assert claim.premise_ids == [cycle.id]
        earlier = next(d for d in workspace.differentials if d.label == "DER-MIX-D17-V-D3")
        assert earlier.required_admitted_premises is False


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
        stem, filtration = 29 + shift + 64*d8 + 20*g, 3 + 4*g
        prefix = f"D8-{d8}-g-{g}"
        probes += [probe(prefix+"-source", "S53", stem, filtration),
                   probe(prefix+"-target", "S02", stem-1, filtration+19)]
    for d8 in (-1, 0, 1):
        offset = shift + 64*d8
        probes += [probe(f"Q-D3-{d8}-positive-j", "S22H", 26+offset, 2, j=1),
                   probe(f"VD7-{d8}-low", "S02", 56+offset, 2),
                   probe(f"d17-{d8}-source", "S02", 24+offset, 2),
                   probe(f"d17-{d8}-target", "S73", 23+offset, 19)]
    payload = {"project": asdict(project), "workspaces": [workspace.id], "pages": [17, 18, 19, 20, 24],
               "bounds": {"stemMin": shift-44, "stemMax": shift+224, "filtrationMin": 0, "filtrationMax": 48},
               "vectorAudit": True, "finiteProbes": probes, "fact": FACT}
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""return {
      finiteProbes: input.finiteProbes.map(probe=>{
        const node={style:{e2_pattern:probe.pattern,two_valuation:0,j_order:probe.j}};
        const grade={stem:probe.stem,filtration:probe.filtration};
        return {...probe,live:algebra.live(node,grade),ports:[...(algebra.ports(node,grade)||[])],
          displayed:points.filter(p=>p.item.style?.e2_pattern===probe.pattern &&
            p.grade.stem===grade.stem && p.grade.filtration===grade.filtration)
            .map(p=>({id:p.item.id,ports:p.modulePorts}))};
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


def test_actual_six_atlas_d19_edges_and_exact_quotient_for_d8_and_forward_g(chart):
    shift, pages = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8-{d8}-g-{g}"
        stem, filtration = 29+shift+64*d8+20*g, 3+4*g
        for suffix in ("source", "target"):
            on_page = observation(pages[19], prefix+"-"+suffix)
            assert on_page["live"] and on_page["ports"] == ["0:0"]
            assert on_page["displayed"] and all("0:0" in p["ports"] for p in on_page["displayed"])
            for page in (20, 24):
                later = observation(pages[page], prefix+"-"+suffix)
                assert not later["live"] and not later["ports"] and not later["displayed"]
        edge = next(e for e in pages[19]["forcedEdges"] if e["source"]["stem"] == stem
                    and e["source"]["filtration"] == filtration)
        assert edge["target"]["stem"] == stem-1 and edge["target"]["filtration"] == filtration+19
        assert edge["sourceLive"] and edge["targetLive"] and edge["admitted"] and edge["unitInvariant"]
        assert edge["status"] == "verified"
        assert not edge["coefficient"]["resolved"] and edge["coefficient"].get("value") is None
    for page, output in pages.items():
        assert output["blockedFromPage"] is None and not output["conflicts"]
        if page != 19:
            assert not output["forcedEdges"]


def test_actual_six_atlas_keep_low_vd7_completed_tail_and_earlier_d17_unchanged(chart):
    _, pages = chart
    for d8 in (-1, 0, 1):
        for page, output in pages.items():
            for suffix in ("source", "target"):
                earlier = observation(output, f"d17-{d8}-{suffix}")
                assert earlier["live"] == (page == 17)
                assert earlier["ports"] == (["0:0"] if page == 17 else [])
            low = observation(output, f"VD7-{d8}-low")
            assert low["live"] and low["ports"] == ["0:0"] and low["displayed"]
            tail = observation(output, f"Q-D3-{d8}-positive-j")
            assert tail["live"] and "0:1" in tail["ports"]


def test_actual_six_atlas_admission_does_not_fix_the_d19_coefficient(chart):
    _, pages = chart
    rows = pages[19]["forcedRows"]
    assert len(rows) == 1 and rows[0]["admitted"] and rows[0]["unitInvariant"]
    assert not rows[0]["coefficient"]["resolved"] and rows[0]["coefficient"].get("value") is None


# A finite cross-section tests all six atlas images and all possible nonzero
# scalar choices without a redundant status x scalar x atlas Cartesian product.
DEPENDENCY_CASES = (
    {"name": "baseline", "mutation": "none", "value": None, "admitted": True},
    {"name": "review-unassigned", "mutation": "review", "value": None, "admitted": False},
    {"name": "restore-after-review", "mutation": "none", "value": None, "admitted": True},
    {"name": "rejected-unit-1", "mutation": "rejected", "value": 1, "admitted": False},
    {"name": "restore-after-rejected", "mutation": "none", "value": None, "admitted": True},
    {"name": "missing-unit-2", "mutation": "missing", "value": 2, "admitted": False},
    {"name": "restore-after-missing", "mutation": "none", "value": None, "admitted": True},
    {"name": "external-cd5-review-unit-3", "mutation": "external-review", "value": 3, "admitted": False},
    {"name": "restore-after-external", "mutation": "none", "value": None, "admitted": True},
    {"name": "missing-entire-d19-claim", "mutation": "missing-claim", "value": None, "admitted": False},
    {"name": "restore-after-claim", "mutation": "none", "value": None, "admitted": True},
    {"name": "empty-premises-unit-1", "mutation": "empty-premises", "value": 1, "admitted": False},
    {"name": "restore-after-empty-premises", "mutation": "none", "value": None, "admitted": True},
    {"name": "null-premises-unassigned", "mutation": "null-premises", "value": None, "admitted": False},
    {"name": "restore-after-null-premises", "mutation": "none", "value": None, "admitted": True},
)


def dependency_cases(project, workspace_id):
    candidate = deepcopy(project)
    workspace = next(w for w in candidate.workspaces if w.id == workspace_id)
    row, claim, _, _ = records(workspace)
    cycle = next(p for p in workspace.propositions if p.conclusion.get("fact_id") == CYCLE)
    external = next(w for w in candidate.workspaces if w.id == "ws_3sigma_i")
    leaf = next(p for p in external.propositions if p.conclusion.get("fact_id") == "DER-3I-EULER-CD5-cycle")
    saved_claims = list(workspace.propositions)
    saved_premises = list(claim.premise_ids)
    cycle_status, leaf_status = cycle.status, leaf.status
    saved_assignments = dict(workspace.settings.get("coefficient_assignments", {}))
    for case in DEPENDENCY_CASES:
        workspace.propositions = list(saved_claims)
        claim.premise_ids = list(saved_premises)
        cycle.status, leaf.status = cycle_status, leaf_status
        workspace.settings["coefficient_assignments"] = dict(saved_assignments)
        mutation = case["mutation"]
        if mutation in ("review", "rejected"):
            cycle.status = mutation
        elif mutation == "missing":
            workspace.propositions = [p for p in workspace.propositions if p.id != cycle.id]
        elif mutation == "external-review":
            leaf.status = "review"
        elif mutation == "missing-claim":
            workspace.propositions = [p for p in workspace.propositions if p.id != claim.id]
        elif mutation == "empty-premises":
            claim.premise_ids = []
        elif mutation == "null-premises":
            claim.premise_ids = None
        assignments = workspace.settings["coefficient_assignments"]
        if case["value"] is None:
            assignments.pop(PARAMETER, None)
        else:
            assignments[PARAMETER] = case["value"]
        yield case, candidate, workspace, row, claim


@pytest.mark.parametrize("workspace_id", tuple(MIXED_ATLAS))
def test_all_six_dependency_withdrawals_block_the_fact_dag_and_restore_it(project, workspace_id):
    for case, candidate, workspace, row, claim in dependency_cases(project, workspace_id):
        admitted = admitted_proposition_ids(candidate)
        assert (claim.id in admitted) == case["admitted"], case["name"]
        # Withdrawal is a dependency state, not an edit to the d19 statement,
        # status, finite-map certificate, or scalar normalization.
        assert row.status == claim.status == "verified"
        assert claim.conclusion["required_admitted_premises"] is True
        assert claim.conclusion["coefficient_parameter"]["value"] is None
        earlier = next(d for d in workspace.differentials if d.label == "DER-MIX-D17-V-D3")
        assert earlier.proposition_id in admitted and earlier.status == "verified"


@pytest.mark.parametrize("workspace_id", tuple(MIXED_ATLAS))
def test_all_six_backend_fates_respect_unknown_and_resolved_unit_dependencies(project, workspace_id):
    for case, candidate, workspace, row, claim in dependency_cases(project, workspace_id):
        nodes = {n.id: n for n in workspace.classes}
        history = [asdict(event) for event in workspace.differential_events]
        assert row.required_admitted_premises is True
        assert _isolated_rank_one_unit(workspace, row, project=candidate) == (
            case["admitted"] and case["value"] is None), case["name"]
        guard = _parameterized_event_eligibility(workspace, project=candidate)
        row_events = [event for event in workspace.differential_events if event.differential_claim_id == row.id]
        assert {event.role for event in row_events} == {"supports", "receives"}
        assert all(guard[event.id] == case["admitted"] for event in row_events), case["name"]
        for ident, role in ((row.source_id, "supports"), (row.target_id, "receives")):
            assert not nodes[ident].archived
            fate = derive_class_fate(workspace, ident, project=candidate, _coefficient_guard=guard)
            expected = {"page": 19, "role": role, "claim_id": row.id} if case["admitted"] else None
            assert fate.first_hfpss_death == expected, (case["name"], fate)
            if case["admitted"]:
                assert claim.id in fate.justification_ids and fate.last_hfpss_live_page == 19
        earlier = next(d for d in workspace.differentials if d.label == "DER-MIX-D17-V-D3")
        for ident, role in ((earlier.source_id, "supports"), (earlier.target_id, "receives")):
            fate = derive_class_fate(workspace, ident, project=candidate, _coefficient_guard=guard)
            assert fate.first_hfpss_death == {"page": 17, "role": role, "claim_id": earlier.id}
        assert [asdict(event) for event in workspace.differential_events] == history
        assert claim.conclusion["coefficient_parameter"]["value"] is None


@pytest.mark.parametrize("workspace_id", tuple(MIXED_ATLAS))
def test_actual_six_atlas_recheck_withdrawal_and_restoration_without_scalar_bypass(project, workspace_id):
    workspace = next(w for w in images(project) if w.id == workspace_id)
    shift = MIXED_ATLAS[workspace_id][1]
    payload = {"project": asdict(project), "workspace": workspace_id, "shift": shift,
               "fact": FACT, "cycleFact": CYCLE, "parameter": PARAMETER, "cases": DEPENDENCY_CASES}
    # Reuse the actual chart harness loader; the snapshots below repeatedly
    # compute E20 on the SAME workspace object to exercise cache invalidation.
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "const output = vm.runInContext(`"
    assert harness.count(marker) == 1
    loader = harness.split(marker)[0]
    snapshots = r"""
      state.project=input.project;
      const ws=state.project.workspaces.find(w=>w.id===input.workspace);
      const bounds={stemMin:40+input.shift,stemMax:64+input.shift,filtrationMin:0,filtrationMax:44};
      const savedClaims=[...ws.propositions];
      const cycle=savedClaims.find(p=>p.conclusion?.fact_id===input.cycleFact);
      const claim=savedClaims.find(p=>p.id===ws.differentials.find(d=>d.label===input.fact).proposition_id);
      const savedPremises=[...claim.premise_ids];
      const pure=state.project.workspaces.find(w=>w.id==='ws_3sigma_i');
      const leaf=pure.propositions.find(p=>p.conclusion?.fact_id==='DER-3I-EULER-CD5-cycle');
      const cycleStatus=cycle.status,leafStatus=leaf.status;
      const assignments={...(ws.settings.coefficient_assignments||{})};
      ws.page=20;
      input.cases.map(test=>{
        ws.propositions=[...savedClaims];
        claim.premise_ids=[...savedPremises];
        cycle.status=cycleStatus;leaf.status=leafStatus;
        ws.settings.coefficient_assignments={...assignments};
        if(test.value===null)delete ws.settings.coefficient_assignments[input.parameter];
        else ws.settings.coefficient_assignments[input.parameter]=test.value;
        if(test.mutation==='review'||test.mutation==='rejected')cycle.status=test.mutation;
        else if(test.mutation==='missing')ws.propositions=ws.propositions.filter(p=>p!==cycle);
        else if(test.mutation==='external-review')leaf.status='review';
        else if(test.mutation==='missing-claim')ws.propositions=ws.propositions.filter(p=>p.id!==ws.differentials.find(d=>d.label===input.fact).proposition_id);
        else if(test.mutation==='empty-premises')claim.premise_ids=[];
        else if(test.mutation==='null-premises')claim.premise_ids=null;
        const algebra=pageAlgebra(ws,bounds),points=periodicClassInstances(ws,bounds);
        const row=ws.differentials.find(d=>d.label===input.fact);
        const endpoint=(pattern,stem,filtration)=>{
          const grade={stem:stem+input.shift,filtration};
          const node={style:{e2_pattern:pattern,two_valuation:0,j_order:0}};
          return {live:algebra.live(node,grade),ports:[...(algebra.ports(node,grade)||[])],
            displayed:points.filter(p=>p.item.style?.e2_pattern===pattern&&
              p.grade.stem===grade.stem&&p.grade.filtration===grade.filtration).length};
        };
        const earlier=ws.differentials.find(d=>d.label==='DER-MIX-D17-V-D3');
        return {name:test.name,canApply:algebra.canApply(row),unitInvariant:algebra.unitInvariant(row),
          coefficient:algebra.coefficientState(row),source:endpoint('S53',49,7),target:endpoint('S02',48,26),
          d17CanApply:algebra.canApply(earlier),d17Source:endpoint('S02',24,2),d17Target:endpoint('S73',23,19),
          conflicts:algebra.conflicts,blockedFromPage:algebra.blockedFromPage};
      });
    """
    script = loader + "\nconst result=vm.runInContext(" + json.dumps(snapshots) + ",context);\nprocess.stdout.write(JSON.stringify(result));"
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(payload),
                               capture_output=True, text=True, encoding="utf-8", check=True, timeout=240)
    output = json.loads(completed.stdout)
    assert len(output) == len(DEPENDENCY_CASES)
    for case, snapshot in zip(DEPENDENCY_CASES, output):
        assert snapshot["name"] == case["name"]
        assert snapshot["canApply"] == case["admitted"], snapshot
        assert snapshot["unitInvariant"] == case["admitted"], snapshot
        for key in ("source", "target"):
            endpoint = snapshot[key]
            assert endpoint["live"] == (not case["admitted"]), snapshot
            assert endpoint["ports"] == ([] if case["admitted"] else ["0:0"]), snapshot
            assert bool(endpoint["displayed"]) == (not case["admitted"]), snapshot
        if case["mutation"] != "missing-claim":
            assert snapshot["coefficient"]["resolved"] == (case["value"] is not None)
            if case["value"] is None:
                assert snapshot["coefficient"].get("value") is None
        assert snapshot["blockedFromPage"] is None and not snapshot["conflicts"], snapshot
        assert snapshot["d17CanApply"]
        assert not snapshot["d17Source"]["live"] and not snapshot["d17Source"]["ports"]
        assert not snapshot["d17Target"]["live"] and not snapshot["d17Target"]["ports"]
