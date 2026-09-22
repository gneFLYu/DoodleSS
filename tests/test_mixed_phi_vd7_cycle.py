"""The Phi image of CD5 forbids outgoing maps, not incoming boundaries.

Use every mixed atlas image and the actual page engine. VD3 remains a distinct
D8 residue with its verified d17; VD7 is never granted immunity to a future
incoming d19. Counterfactual arrows exist only in in-memory test copies.
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
from test_vector_page_invariants import runtime as local_runtime


WORKSPACE = "ws_sigma_i_2sigma_j"
FACT = "DER-MIX-PHI-CD5-VD7-cycle"
CONTROL = "DER-MIX-D17-V-D3"
INCOMING = "DER-MIX-D19-X-D4"
TRANSLATIONS = ((-1, 0), (0, 0), (1, 0), (0, 1), (-2, 6))
PAGES = (11, 12, 17, 18, 19, 20, 24)
FORWARD = {"multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True}


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    result = [w for w in project.workspaces if w.id == WORKSPACE or
              w.settings.get("atlas_transport", {}).get("source_workspace_id") == WORKSPACE]
    assert {w.id for w in result} == set(MIXED_ATLAS)
    return result


def records(workspace):
    claims = [p for p in workspace.propositions if p.conclusion.get("fact_id") == FACT]
    assert len(claims) == 1
    claim = claims[0]
    return claim, next(n for n in workspace.classes if n.id == claim.conclusion["source_id"])


def test_all_six_atlas_claims_are_exact_outgoing_constraints_not_survival_overrides(project):
    admitted = admitted_proposition_ids(project)
    for ws in images(project):
        claim, source = records(ws)
        data = claim.conclusion
        shift = MIXED_ATLAS[ws.id][1]
        assert claim.kind == "permanent-cycle" and claim.status == "verified"
        assert claim.id in admitted and data["admission_status"] == "verified"
        assert data["page"] == source.page == 2
        assert data["cycle_constraint"] == "outgoing-only"
        assert data["coefficient_scope"] == "exact-port"
        assert data["source_status"] == "independently-verified"
        assert not data.get("source_blockers") and not data.get("withdrawn_dependencies")
        assert not data.get("machine_verification_pending")
        assert data["period_stem"] == 64 and data["period_is_invertible"]
        assert data["forward_period"] == FORWARD
        assert (source.grade.stem, source.grade.filtration) == (56 + shift, 2)
        assert (source.style["e2_pattern"], source.style.get("two_valuation", 0),
                source.style.get("j_order", 0)) == ("S02", 0, 0)
        assert not source.archived
        assert not any(d.proposition_id == claim.id or d.label == FACT for d in ws.differentials)
        proof = data["verification_certificate"]
        assert proof["status"] == "verified" and proof["source_refs"]
        assert proof["no_withdrawn_premise"]
        assert "DER-3I-EULER-CD5-cycle" in data["derived_from"]
        assert "formal_prop_der-3i-euler-cd5-cycle" in claim.premise_ids
        assert data["external_premises"] == [{"workspace_id": "ws_3sigma_i",
                                              "proposition_id": "formal_prop_der-3i-euler-cd5-cycle"}]
        assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(data["derived_from"])


def test_transport_uses_target_injectivity_and_records_the_thom_unit_without_choosing_it(project):
    for ws in images(project):
        claim, _ = records(ws)
        transport = claim.conclusion["transport_certificate"]
        assert transport["source_workspace_id"] == "ws_3sigma_i"
        assert transport["source_fact_id"] == "DER-3I-EULER-CD5-cycle"
        assert transport["source_power"] == 5 and transport["source_bidegree"] == [41, 1]
        assert transport["action"] == "omega^2" and transport["applied_inverse"]
        assert transport["phi"] == "N_C4^Q8(dbar)*u_4sigma_k*g^-1*a_H"
        assert transport["euler_multiplier"] == "a_sigma_j"
        assert (transport["phi_stem_shift"], transport["phi_filtration_shift"]) == (-16, 0)
        assert transport["target_power"] == 7 and transport["target_bidegree"] == [56, 2]
        coefficient = transport["coefficient"]
        assert coefficient == {"omega_D_exponent": 5, "euler_zeta_exponent": 1,
                               "total_zeta_exponent_mod3": 0, "Thom_unit_value": None,
                               "Thom_unit_nonzero": True, "target_j_annihilated": True}
        proof = claim.conclusion["verification_certificate"]
        assert proof["scope"] == "source-workspace" and proof["source_workspace_id"] == WORKSPACE
        assert proof["source"] == {"bidegree": [56, 2], "pattern": "S02", "port": "0:0",
                                   "torsion_order": 2, "j_annihilated": True}
        assert proof["target_comparison"] == {
            "differential_page": "r>=2", "filtration": "r+2",
            "injective_from": "r-1", "source_injectivity_required": False,
        }
        assert proof["d17_control"] == {"source_bidegree": [56, 2], "target_bidegree": [55, 19],
                                        "target_pattern": "S73", "target": "Rk^4D^9", "zero": True}
        assert proof["high_translation"] == {
            "g_exponent": 6, "D_exponent": -16, "source_bidegree": [48, 26],
            "d17_target_bidegree": [47, 43], "forward_g_only": True,
            "incoming_survival_asserted": False,
        }
        assert proof["separate_D3_d17_unchanged"]


def test_migration_restores_six_claims_without_duplicate_sources(project):
    candidate = deepcopy(project)
    expected = {w.id: tuple(asdict(item) for item in records(w)) for w in images(candidate)}
    for ws in images(candidate):
        ws.propositions = [p for p in ws.propositions if p.conclusion.get("fact_id") != FACT]
    for _ in range(2):
        candidate = migrate_project(candidate)
        assert {w.id: tuple(asdict(item) for item in records(w)) for w in images(candidate)} == expected


def chart_runtime(project, workspaces, pages, hypothetical=False):
    payload = {"project": asdict(project), "workspaces": [w.id for w in workspaces],
               "pages": list(pages), "vectorAudit": True, "control": CONTROL,
               "fact": FACT, "translations": TRANSLATIONS,
               "shiftByWorkspace": {w.id: MIXED_ATLAS[w.id][1] for w in workspaces},
               "boundsByWorkspace": {
                   w.id: {"stemMin": MIXED_ATLAS[w.id][1]-40,
                          "stemMax": MIXED_ATLAS[w.id][1]+220,
                          "filtrationMin": 0, "filtrationMax": 44} for w in workspaces}}
    if hypothetical:
        # Clone only a finite arrow's shape. Its test-only admission is not
        # a production claim, coefficient assignment, or inferred D4 period.
        for ws in payload["project"]["workspaces"]:
            if ws["id"] not in payload["workspaces"]:
                continue
            claim = next(p for p in ws["propositions"] if p["conclusion"].get("fact_id") == FACT)
            control = next(d for d in ws["differentials"] if d["label"] == CONTROL)
            target = deepcopy(next(n for n in ws["classes"] if n["id"] == control["target_id"]))
            target["id"] = f"test-vd7-target-{ws['id']}"
            target["grade"]["stem"] += 32
            target["label"] = "test-only candidate target"
            row = deepcopy(control)
            row.update(id=f"test-vd7-d17-{ws['id']}", source_id=claim["conclusion"]["source_id"],
                       target_id=target["id"], proposition_id=None, linear_map_id=None,
                       label="test-only VD7 d17 hypothesis", status="verified")
            ws["classes"].append(target)
            ws["differentials"].append(row)
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""return {
      probesByTranslation:input.translations.map(([d8,g])=>{
        const shift=input.shiftByWorkspace[id],s=56+shift+64*d8+20*g,f=2+4*g;
        const read=(pattern,stem,filtration)=>{
          const n={style:{e2_pattern:pattern,two_valuation:0,j_order:0}},grade={stem,filtration};
          return {stem,filtration,live:algebra.live(n,grade),ports:[...(algebra.ports(n,grade)||[])]};
        };
        return {d8,g,vd7:read('S02',s,f),vd3:read('S02',s-32,f),
          d17Target:read('S73',s-33,f+17)};
      }),
      priorIncoming:[12,44].map(s=>{
        const grade={stem:s+input.shiftByWorkspace[id],filtration:14};
        const n={style:{e2_pattern:'S02',two_valuation:0,j_order:0}};
        return {grade,live:algebra.live(n,grade),ports:[...(algebra.ports(n,grade)||[])]};
      }),
      occurrenceEdges:edges.map(e=>({id:e.diff.id,page:e.diff.page,label:e.diff.label,
        source:e.sourceGrade,target:e.targetGrade,sourcePattern:classes.get(e.diff.source_id)?.style.e2_pattern,
        admitted:algebra.canApply(e.diff),unitInvariant:algebra.unitInvariant(e.diff)})),
      selectedPage:ws.page,cycleEdges:edges.filter(e=>e.diff.label===input.fact).length,
      page, points: points.length"""
    completed = subprocess.run(["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
                               input=json.dumps(payload), text=True, encoding="utf-8",
                               capture_output=True, check=True, timeout=240)
    return {w["id"]: {row["page"]: row for row in w["pages"]} for w in json.loads(completed.stdout)}


@pytest.fixture(scope="module")
def chart(project):
    return chart_runtime(project, images(project), PAGES)


@pytest.mark.parametrize("workspace_id", tuple(MIXED_ATLAS))
def test_vd7_has_no_d17_and_other_residue_keeps_its_actual_nonzero_d17(chart, workspace_id):
    pages = chart[workspace_id]
    for at17, at18 in zip(pages[17]["probesByTranslation"], pages[18]["probesByTranslation"]):
        assert (at17["d8"], at17["g"]) == (at18["d8"], at18["g"])
        assert at17["vd7"]["live"] and at17["vd7"]["ports"] == ["0:0"]
        assert at18["vd7"]["live"] and at18["vd7"]["ports"] == ["0:0"]
        for key in ("vd3", "d17Target"):
            assert at17[key]["live"] and at17[key]["ports"] == ["0:0"]
            assert not at18[key]["live"] and not at18[key]["ports"]
        stem, filtration = at17["vd3"]["stem"], at17["vd3"]["filtration"]
        edge = next(e for e in pages[17]["occurrenceEdges"] if e["label"] == CONTROL
                    and (e["source"]["stem"], e["source"]["filtration"]) == (stem, filtration))
        assert edge["admitted"] and edge["unitInvariant"]
        assert (edge["target"]["stem"], edge["target"]["filtration"]) == (stem-1, filtration+17)
        vd7 = at17["vd7"]
        assert not any(e["page"] == 17 and e["sourcePattern"] == "S02"
                       and (e["source"]["stem"], e["source"]["filtration"]) ==
                       (vd7["stem"], vd7["filtration"]) for e in pages[17]["occurrenceEdges"])
    high = next(p for p in pages[17]["probesByTranslation"] if (p["d8"], p["g"]) == (-2, 6))
    assert (high["vd7"]["stem"], high["vd7"]["filtration"]) == (48+MIXED_ATLAS[workspace_id][1], 26)
    for page, row in pages.items():
        assert row["selectedPage"] == page and not row["cycleEdges"]
        assert row["blockedFromPage"] is None and not row["conflicts"] and not row["dangling"]
    # Deliberately no E24 survival assertion: an outgoing-only certificate
    # must continue to allow independently justified incoming differentials.


@pytest.mark.parametrize("workspace_id", tuple(MIXED_ATLAS))
def test_existing_s02_d11_boundaries_are_not_restored_by_the_new_cycle(chart, workspace_id):
    pages = chart[workspace_id]
    assert all(p["live"] and p["ports"] == ["0:0"] for p in pages[11]["priorIncoming"])
    for page in (12, 17, 18, 24):
        assert all(not p["live"] and not p["ports"] for p in pages[page]["priorIncoming"])


@pytest.mark.parametrize("workspace_id", tuple(MIXED_ATLAS))
def test_verified_incoming_d19_takes_precedence_at_the_high_vd7_occurrence(chart, workspace_id):
    pages = chart[workspace_id]
    shift = MIXED_ATLAS[workspace_id][1]
    high = next(p for p in pages[19]["probesByTranslation"] if (p["d8"], p["g"]) == (-2, 6))
    assert high["vd7"]["live"] and high["vd7"]["ports"] == ["0:0"]
    incoming = next(e for e in pages[19]["occurrenceEdges"] if e["label"] == INCOMING
                    and (e["target"]["stem"], e["target"]["filtration"]) == (48+shift, 26))
    assert (incoming["source"]["stem"], incoming["source"]["filtration"]) == (49+shift, 7)
    assert incoming["admitted"] and incoming["unitInvariant"]
    for page in (20, 24):
        later = next(p for p in pages[page]["probesByTranslation"] if (p["d8"], p["g"]) == (-2, 6))
        assert not later["vd7"]["live"] and not later["vd7"]["ports"]


def test_counterfactual_vd7_d17_is_reported_on_all_six_atlas_without_mutating_project(project):
    before = asdict(project)
    result = chart_runtime(project, images(project), (17, 18), hypothetical=True)
    for workspace_id, pages in result.items():
        for page, row in pages.items():
            assert row["selectedPage"] == page
            assert row["blockedFromPage"] == 17
            assert any(c["reason"] == "nonzero differential contradicts a zero-outgoing cycle constraint"
                       and c.get("differential") == f"test-vd7-d17-{workspace_id}"
                       for c in row["conflicts"])
            assert not any(e["id"] == f"test-vd7-d17-{workspace_id}" and e["admitted"]
                           for e in row["occurrenceEdges"])
    assert asdict(project) == before


@pytest.mark.parametrize("workspace_id", tuple(MIXED_ATLAS))
def test_actual_outgoing_only_declaration_allows_an_abstract_incoming_d19(project, workspace_id):
    ws = next(w for w in images(project) if w.id == workspace_id)
    claim, _ = records(ws)
    declaration = asdict(claim)
    declaration["conclusion"].update(source_id="cycle-anchor", class_id="cycle-anchor")
    shift = MIXED_ATLAS[workspace_id][1]
    proof_ws = next(w for w in project.workspaces if w.id == "ws_3sigma_i")
    proof = next(p for p in proof_ws.propositions if p.id == "formal_prop_der-3i-euler-cd5-cycle")
    external_proofs = [{"id": proof_ws.id, "settings": {}, "classes": [],
                        "propositions": [asdict(proof)], "differentials": [], "differential_maps": []}]
    # Abstract finite cells test the engine's directionality, not a claimed
    # new mixed differential. Use the actual declaration at g^6 D^-16 VD7.
    result = local_runtime(r"""
      const shift=SHIFT;
      bounds.stemMin=shift;bounds.stemMax=80+shift;bounds.filtrationMax=30;
      helpers.accepted=r=>['verified','proven'].includes(r.status);
      helpers.coefficientWorkspaces=PROOF_WORKSPACES;
      helpers.copies=grade=>grade.stem===56+shift&&grade.filtration===2
        ? [{grade},{grade:{stem:48+shift,filtration:26}}] : [{grade}];
      const anchor=node('cycle-anchor','S02',56+shift,2);
      const selected=node('selected','S02',48+shift,26);
      const incoming=node('incoming','S73',49+shift,7);
      const arrow=diff('abstract-incoming-d19',incoming.id,selected.id,19);
      const ws=workspace(20,[anchor,selected,incoming],[arrow],[DECLARATION]);
      ws.id=WORKSPACE_ID;
      const algebra=compute(ws);
      console.log(JSON.stringify({blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
        selectedLive:algebra.live(selected,selected.grade),anchorLive:algebra.live(anchor,anchor.grade),
        ports:[...(algebra.ports(selected,selected.grade)||[])],selectedPage:ws.page}));
    """.replace("SHIFT", str(shift)).replace("DECLARATION", json.dumps(declaration))
       .replace("PROOF_WORKSPACES", json.dumps(external_proofs))
       .replace("WORKSPACE_ID", json.dumps(workspace_id)))
    assert result["blocked"] is None and not result["conflicts"]
    assert result["selectedPage"] == 20 and result["anchorLive"]
    assert not result["selectedLive"] and not result["ports"]
