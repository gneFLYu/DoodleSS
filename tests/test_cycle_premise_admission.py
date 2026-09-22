"""Proof prerequisites gate cycles and explicitly opted-in ordinary maps.

Small abstract finite cells exercise the production backend fate and browser
quotient engines. No new mathematical claim or saved project is constructed.
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
from domain.fate import (
    ACCEPTED_STATUSES, _cycle_claim_covers, class_is_live_on_page,
    derive_class_fate, sync_differential_events, sync_workspace_fates,
)
from domain.models import (
    ClassNode, Differential, Grade, Project, Proposition, Workspace,
    project_from_dict, project_to_dict,
)
from test_vector_page_invariants import RUNTIME, runtime


CASES = {
    "legacy": True,
    "accepted": True,
    "missing": False,
    "review": False,
    "rejected": False,
    "tombstone": False,
    "transitive": True,
    "transitive-missing": False,
    "transitive-review": False,
    "cycle": False,
    "self-cycle": False,
    "duplicate-id": False,
    "foreign-only": False,
    "malformed-list": False,
    "malformed-id": False,
    "transitive-malformed": False,
}
KINDS = ("zero-differential", "permanent-cycle")

ORDINARY_CASES = {
    "accepted": True,
    "legacy": True,
    "legacy-missing-proof": True,
    "row-only": False,
    "claim-only": False,
    "missing-proof": False,
    "missing-row": False,
    "duplicate-proof": False,
    "duplicate-claim-only": False,
    "root-review": False,
    "root-tombstone": False,
    "root-review-no-premises": False,
    "missing-premise": False,
    "review-premise": False,
    "empty-premises": False,
    "null-premises": False,
    "malformed-premises": False,
    "row-null": False,
    "row-zero": False,
    "row-string": False,
    "claim-null": False,
    "claim-zero": False,
    "claim-string": False,
    "claim-false": False,
}


def premise(ident, *, status="verified", dependencies=None):
    return Proposition(ident, "lemma", "Abstract proof dependency", status=status,
                       premise_ids=[] if dependencies is None else dependencies)


def fixture(case, kind="zero-differential", *, incoming=False, no_arrow=False):
    source = ClassNode("source", "Finite source", Grade(7, 3), style={"e2_pattern": "S73"})
    other = ClassNode("other", "Other finite class", Grade(8, 1) if incoming else Grade(6, 6),
                      style={"e2_pattern": "I13"})
    claim = Proposition("cycle", kind, "Abstract outgoing cycle constraint", status="verified",
                        conclusion={"source_id": source.id, "page": 3 if kind == "zero-differential" else 2,
                                    "coefficient_scope": "exact-port", "cycle_constraint": "outgoing-only"},
                        premise_ids=["first"])
    proof = premise("first")
    ws = Workspace("local", "Local abstract test", spectral_sequence="hfpss", page=4,
                   classes=[source, other], propositions=[claim, proof])
    foreign = Workspace("foreign", "Other workspace", propositions=[premise("first")])
    if case == "legacy":
        claim.premise_ids = []
        proof.status = "review"  # Unrelated reviews do not block legacy proofs.
    elif case in ("missing", "foreign-only"):
        ws.propositions.remove(proof)
    elif case in ("review", "rejected"):
        proof.status = case
    elif case == "tombstone":
        proof.kind = "tombstone"  # An accepted status cannot restore a removed fact.
    elif case.startswith("transitive"):
        proof.premise_ids = ["leaf"]
        leaf = premise("leaf", status="review" if case == "transitive-review" else "verified")
        if case != "transitive-missing":
            ws.propositions.append(leaf)
        if case == "transitive-malformed":
            leaf.premise_ids = "not-an-id-list"
    elif case == "cycle":
        proof.premise_ids = ["leaf"]
        ws.propositions.append(premise("leaf", dependencies=["first"]))
    elif case == "self-cycle":
        claim.premise_ids = [claim.id]
    elif case == "duplicate-id":
        ws.propositions.append(premise("first"))
    elif case == "malformed-list":
        claim.premise_ids = "first"
    elif case == "malformed-id":
        claim.premise_ids = [None]
    if not no_arrow:
        row = Differential("map", other.id if incoming else source.id,
                           source.id if incoming else other.id, 2 if incoming else 3,
                           status="verified", proposition_id="map-proof")
        ws.differentials.append(row)
        ws.propositions.append(Proposition("map-proof", "differential", "Abstract map", status="verified",
                                           conclusion={"source_id": row.source_id, "target_id": row.target_id,
                                                       "page": row.page}))
    return ws, claim, source, foreign


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("case,admitted", CASES.items())
def test_backend_cycle_prerequisites_are_recursive_local_and_fail_closed(case, admitted, kind):
    ws, claim, source, foreign = fixture(case, kind)
    original = deepcopy(asdict(ws))
    assert _cycle_claim_covers(ws, claim, source, 3) is admitted
    assert asdict(ws) == original
    sync_differential_events(ws)
    project = Project("test", "Abstract tests", workspaces=[ws, foreign])
    fate = derive_class_fate(ws, source.id, project=project)
    if admitted:
        assert fate.first_hfpss_death is None
    else:
        assert fate.first_hfpss_death == {"page": 3, "role": "supports", "claim_id": "map"}


@pytest.fixture(scope="module")
def frontend_cases():
    payload = []
    for kind in KINDS:
        for case in CASES:
            ws, _, _, foreign = fixture(case, kind)
            payload.append({"case": case, "kind": kind, "workspace": asdict(ws), "foreign": asdict(foreign)})
    script = RUNTIME + r"""
      helpers.accepted=record=>!!record&&ACCEPTED.includes(record.status);
      const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
      console.log(JSON.stringify(input.map(test=>{
        helpers.coefficientWorkspaces=[test.foreign];
        const before=JSON.stringify(test.workspace);
        const algebra=compute(test.workspace),source=test.workspace.classes[0],other=test.workspace.classes[1];
        return {case:test.case,kind:test.kind,blocked:algebra.blockedFromPage,
          sourceLive:algebra.live(source,source.grade),otherLive:algebra.live(other,other.grade),
          conflicts:algebra.conflicts,unchanged:before===JSON.stringify(test.workspace)};
      })));
    """.replace("ACCEPTED", json.dumps(sorted(ACCEPTED_STATUSES)))
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(payload),
                               text=True, encoding="utf-8", capture_output=True, check=True, timeout=20)
    return json.loads(completed.stdout)


@pytest.mark.parametrize("kind", KINDS)
def test_frontend_uses_the_same_dependency_gate_without_changing_legacy_behavior(frontend_cases, kind):
    rows = [row for row in frontend_cases if row["kind"] == kind]
    assert len(rows) == len(CASES)
    for row in rows:
        admitted = CASES[row["case"]]
        assert row["unchanged"]
        assert row["sourceLive"] is admitted and row["otherLive"] is admitted, row
        if admitted:
            assert row["blocked"] == 3
            assert any("zero-outgoing cycle constraint" in entry["reason"] for entry in row["conflicts"])
        else:
            assert row["blocked"] is None and not row["conflicts"], row


@pytest.mark.parametrize("kind", KINDS)
def test_admitted_cycle_does_not_block_or_restore_an_incoming_boundary(kind):
    ws, claim, source, _ = fixture("transitive", kind, incoming=True)
    assert _cycle_claim_covers(ws, claim, source, 3)
    sync_differential_events(ws)
    fate = derive_class_fate(ws, source.id)
    assert fate.first_hfpss_death == {"page": 2, "role": "receives", "claim_id": "map"}
    result = runtime(r"""
      helpers.accepted=record=>!!record&&ACCEPTED.includes(record.status);
      const ws=WORKSPACE,algebra=compute(ws);
      console.log(JSON.stringify({blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
        live:ws.classes.map(n=>algebra.live(n,n.grade))}));
    """.replace("ACCEPTED", json.dumps(sorted(ACCEPTED_STATUSES))).replace("WORKSPACE", json.dumps(asdict(ws))))
    assert result == {"blocked": None, "conflicts": [], "live": [False, False]}


def test_unavailable_permanent_cycle_premise_cannot_proclaim_nonzero_survival():
    ws, _, source, _ = fixture("missing", "permanent-cycle", no_arrow=True)
    assert derive_class_fate(ws, source.id).conclusion != "permanent_cycle"
    ws.propositions.append(premise("first"))
    assert derive_class_fate(ws, source.id).conclusion == "permanent_cycle"


def test_ordinary_differential_admission_is_unchanged_by_this_cycle_only_gate():
    ws, _, source, _ = fixture("legacy")
    ws.propositions = [p for p in ws.propositions if p.kind == "differential"]
    ws.propositions[0].premise_ids = ["missing-proof"]
    sync_differential_events(ws)
    assert derive_class_fate(ws, source.id).first_hfpss_death == {
        "page": 3, "role": "supports", "claim_id": "map",
    }
    result = runtime(r"""
      helpers.accepted=record=>!!record&&ACCEPTED.includes(record.status);
      const ws=WORKSPACE,algebra=compute(ws);
      console.log(JSON.stringify({blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
        live:ws.classes.map(n=>algebra.live(n,n.grade))}));
    """.replace("ACCEPTED", json.dumps(sorted(ACCEPTED_STATUSES))).replace("WORKSPACE", json.dumps(asdict(ws))))
    assert result == {"blocked": None, "conflicts": [], "live": [False, False]}


@pytest.mark.parametrize("kind", KINDS)
def test_changing_only_transitive_premise_ids_invalidates_the_frontend_cache(kind):
    ws, _, _, _ = fixture("transitive", kind)
    result = runtime(r"""
      helpers.accepted=record=>!!record&&ACCEPTED.includes(record.status);
      const ws=WORKSPACE;
      const inspect=()=>{const algebra=compute(ws),source=ws.classes[0];return {
        blocked:algebra.blockedFromPage,live:algebra.live(source,source.grade)};};
      const first=ws.propositions.find(p=>p.id==='first'),rows=[inspect()];
      first.premise_ids=['unavailable'];rows.push(inspect());
      first.premise_ids=['first'];rows.push(inspect());
      first.premise_ids=['leaf'];rows.push(inspect());
      const leaf=ws.propositions.find(p=>p.id==='leaf');
      leaf.kind='tombstone';rows.push(inspect());
      leaf.kind='lemma';rows.push(inspect());
      console.log(JSON.stringify(rows));
    """.replace("ACCEPTED", json.dumps(sorted(ACCEPTED_STATUSES))).replace("WORKSPACE", json.dumps(asdict(ws))))
    assert result == [{"blocked": 3, "live": True}, {"blocked": None, "live": False},
                      {"blocked": None, "live": False}, {"blocked": 3, "live": True},
                      {"blocked": None, "live": False}, {"blocked": 3, "live": True}]


def test_public_and_backend_page_algebra_are_identical():
    assert (ROOT / "backend/static/page-algebra.js").read_bytes() == (ROOT / "public/static/page-algebra.js").read_bytes()


EXTERNAL_CASES = {
    "qualified": True, "local-decoy": True, "missing-workspace": False,
    "missing-proof": False, "review": False, "rejected": False, "tombstone": False,
    "duplicate-workspace": False, "duplicate-proof": False, "duplicate-locator": False,
    "conflicting-locator": False, "malformed-list": False, "malformed-locator": False,
    "malformed-workspace": False, "malformed-proof": False, "undeclared-id": False,
    "transitive-local": True, "transitive-local-missing": False,
    "transitive-external": True, "transitive-review": False, "external-cycle": False,
}


def external_fixture(case, kind="permanent-cycle", incoming=False):
    ws, claim, source, foreign = fixture("accepted", kind, incoming=incoming)
    third = Workspace("third", "Third explicit proof scope", propositions=[premise("leaf")])
    claim.conclusion["external_premises"] = [{"workspace_id": "foreign", "proposition_id": "first"}]
    local = next(p for p in ws.propositions if p.id == "first")
    local.status = "review" if case == "local-decoy" else "verified"
    external = foreign.propositions[0]
    scopes = [ws, foreign, third]
    if case == "missing-workspace":
        scopes.remove(foreign)
    elif case == "missing-proof":
        foreign.propositions = []
    elif case in ("review", "rejected"):
        external.status = case  # The accepted local decoy cannot replace it.
    elif case == "tombstone":
        external.kind = "tombstone"
    elif case == "duplicate-workspace":
        scopes.append(deepcopy(foreign))
    elif case == "duplicate-proof":
        foreign.propositions.append(premise("first"))
    elif case == "duplicate-locator":
        claim.conclusion["external_premises"] *= 2
    elif case == "conflicting-locator":
        third.propositions.append(premise("first"))
        claim.conclusion["external_premises"].append({"workspace_id": "third", "proposition_id": "first"})
    elif case == "malformed-list":
        claim.conclusion["external_premises"] = "foreign:first"
    elif case == "malformed-locator":
        claim.conclusion["external_premises"] = [None]
    elif case == "malformed-workspace":
        claim.conclusion["external_premises"][0]["workspace_id"] = None
    elif case == "malformed-proof":
        claim.conclusion["external_premises"][0]["proposition_id"] = []
    elif case == "undeclared-id":
        claim.premise_ids = []
    elif case in ("transitive-local", "transitive-local-missing"):
        external.premise_ids = ["leaf"]
        ws.propositions.append(premise("leaf"))
        if case == "transitive-local":
            foreign.propositions.append(premise("leaf"))
    elif case in ("transitive-external", "transitive-review", "external-cycle"):
        external.premise_ids = ["leaf"]
        external.conclusion["external_premises"] = [{"workspace_id": "third", "proposition_id": "leaf"}]
        if case == "transitive-review":
            third.propositions[0].status = "review"
        elif case == "external-cycle":
            third.propositions[0].premise_ids = ["cycle"]
            third.propositions[0].conclusion["external_premises"] = [
                {"workspace_id": "local", "proposition_id": "cycle"}]
    return Project("external-test", "Explicit proof scopes", workspaces=scopes), ws, claim, source


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("case,admitted", EXTERNAL_CASES.items())
def test_backend_external_locator_qualifies_only_the_declared_premise(case, admitted, kind):
    project, ws, claim, source = external_fixture(case, kind)
    before = asdict(project)
    assert _cycle_claim_covers(ws, claim, source, 3, project=project) is admitted
    assert asdict(project) == before
    # Omitting project context must fail closed even with a same-ID local proof.
    assert not _cycle_claim_covers(ws, claim, source, 3)
    sync_differential_events(ws)
    fate = derive_class_fate(ws, source.id, project=project)
    assert (fate.first_hfpss_death is None) is admitted


@pytest.fixture(scope="module")
def frontend_external_cases():
    payload = []
    for kind in KINDS:
        for case in EXTERNAL_CASES:
            project, ws, _, _ = external_fixture(case, kind)
            payload.append({"case": case, "kind": kind, "workspace": asdict(ws),
                            "externals": [asdict(w) for w in project.workspaces if w is not ws]})
    script = RUNTIME + r"""
      helpers.accepted=record=>!!record&&ACCEPTED.includes(record.status);
      const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
      console.log(JSON.stringify(input.map(test=>{
        helpers.coefficientWorkspaces=[test.workspace,...test.externals];
        const before=JSON.stringify(test),algebra=compute(test.workspace),source=test.workspace.classes[0];
        return {case:test.case,kind:test.kind,blocked:algebra.blockedFromPage,
          sourceLive:algebra.live(source,source.grade),conflicts:algebra.conflicts,
          unchanged:before===JSON.stringify(test)};
      })));
    """.replace("ACCEPTED", json.dumps(sorted(ACCEPTED_STATUSES)))
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(payload),
                               text=True, encoding="utf-8", capture_output=True, check=True, timeout=20)
    return json.loads(completed.stdout)


@pytest.mark.parametrize("kind", KINDS)
def test_frontend_external_proofs_match_backend_and_do_not_borrow_same_name_records(frontend_external_cases, kind):
    rows = [r for r in frontend_external_cases if r["kind"] == kind]
    assert len(rows) == len(EXTERNAL_CASES)
    for row in rows:
        admitted = EXTERNAL_CASES[row["case"]]
        assert row["unchanged"] and row["sourceLive"] is admitted, row
        assert row["blocked"] == (3 if admitted else None), row
        assert bool(row["conflicts"]) is admitted, row


@pytest.mark.parametrize("kind", KINDS)
def test_external_cycle_proof_cannot_restore_an_incoming_boundary(kind):
    project, ws, claim, source = external_fixture("transitive-external", kind, incoming=True)
    assert _cycle_claim_covers(ws, claim, source, 3, project=project)
    sync_differential_events(ws)
    assert derive_class_fate(ws, source.id, project=project).first_hfpss_death == {
        "page": 2, "role": "receives", "claim_id": "map"}


@pytest.mark.parametrize("kind", KINDS)
def test_frontend_cache_tracks_external_leaf_status_kind_links_and_workspace_ambiguity(kind):
    project, ws, _, _ = external_fixture("transitive-external", kind)
    payload = {"workspace": asdict(ws), "externals": [asdict(w) for w in project.workspaces if w is not ws]}
    result = runtime(r"""
      helpers.accepted=r=>!!r&&ACCEPTED.includes(r.status);
      const input=PAYLOAD,ws=input.workspace,[foreign,third]=input.externals;
      helpers.coefficientWorkspaces=[ws,foreign,third];
      const inspect=()=>{const a=compute(ws),n=ws.classes[0];return {
        blocked:a.blockedFromPage,live:a.live(n,n.grade)};};
      const first=foreign.propositions[0],leaf=third.propositions[0],rows=[inspect()];
      leaf.status='review';rows.push(inspect());
      leaf.status='verified';rows.push(inspect());
      leaf.kind='tombstone';rows.push(inspect());
      leaf.kind='lemma';rows.push(inspect());
      leaf.premise_ids=['unavailable'];rows.push(inspect());
      leaf.premise_ids=[];rows.push(inspect());
      first.conclusion.external_premises[0].workspace_id='missing';rows.push(inspect());
      first.conclusion.external_premises[0].workspace_id='third';rows.push(inspect());
      helpers.coefficientWorkspaces.push(structuredClone(third));rows.push(inspect());
      helpers.coefficientWorkspaces.pop();rows.push(inspect());
      leaf.premise_ids=['cycle'];leaf.conclusion.external_premises=[{workspace_id:'local',proposition_id:'cycle'}];
      rows.push(inspect());
      leaf.premise_ids=[];leaf.conclusion.external_premises=[];rows.push(inspect());
      console.log(JSON.stringify(rows));
    """.replace("ACCEPTED", json.dumps(sorted(ACCEPTED_STATUSES))).replace("PAYLOAD", json.dumps(payload)))
    assert result == [{"blocked": 3 if i % 2 == 0 else None, "live": i % 2 == 0} for i in range(13)]


@pytest.mark.parametrize("kind", KINDS)
def test_external_proof_conclusion_edits_recompute_even_when_admission_is_unchanged(kind):
    project, ws, _, _ = external_fixture("transitive-external", kind)
    payload = {"workspace": asdict(ws), "externals": [asdict(w) for w in project.workspaces if w is not ws]}
    result = runtime(r"""
      helpers.accepted=r=>!!r&&ACCEPTED.includes(r.status);
      const input=PAYLOAD,ws=input.workspace,[foreign,third]=input.externals;
      helpers.coefficientWorkspaces=[ws,foreign,third];
      const leaf=third.propositions[0],rows=[];
      let previous=compute(ws);
      const initiallyCached=compute(ws)===previous;
      const inspect=()=>{
        const current=compute(ws);
        rows.push({sameCache:current===previous,blocked:current.blockedFromPage});
        previous=current;
      };
      leaf.conclusion.source_id='external-source-a';inspect();
      leaf.conclusion.source_id='external-source-b';inspect();
      leaf.conclusion.verification_certificate={source:{stem:7,filtration:3}};inspect();
      leaf.conclusion.verification_certificate.source.filtration=7;inspect();
      delete leaf.conclusion.source_id;inspect();
      console.log(JSON.stringify({initiallyCached,rows,finallyCached:compute(ws)===previous}));
    """.replace("ACCEPTED", json.dumps(sorted(ACCEPTED_STATUSES))).replace("PAYLOAD", json.dumps(payload)))
    assert result["initiallyCached"] and result["finallyCached"]
    assert result["rows"] == [{"sameCache": False, "blocked": 3}] * 5


def ordinary_fixture(case):
    ws, cycle, source, _ = fixture("accepted")
    ws.propositions.remove(cycle)
    row = ws.differentials[0]
    proof = next(p for p in ws.propositions if p.id == row.proposition_id)
    leaf = next(p for p in ws.propositions if p.id == "first")
    row.required_admitted_premises = True
    proof.conclusion["required_admitted_premises"] = True
    proof.premise_ids = [leaf.id]
    if case in ("legacy", "legacy-missing-proof"):
        row.required_admitted_premises = False
        proof.conclusion.pop("required_admitted_premises")
    sync_differential_events(ws)  # Keep original events through proof edits.
    if case in ("legacy", "legacy-missing-proof"):
        row.required_admitted_premises = False
        proof.conclusion.pop("required_admitted_premises", None)
        leaf.status = "review"
        if case == "legacy-missing-proof":
            ws.propositions.remove(proof)
    elif case == "row-only":
        proof.conclusion.pop("required_admitted_premises")
    elif case == "claim-only":
        row.required_admitted_premises = False
    elif case == "missing-proof":
        ws.propositions.remove(proof)
    elif case == "missing-row":
        ws.differentials.clear()
    elif case == "duplicate-proof":
        ws.propositions.append(deepcopy(proof))
    elif case == "duplicate-claim-only":
        row.required_admitted_premises = False
        duplicate = deepcopy(proof)
        duplicate.conclusion.pop("required_admitted_premises")
        ws.propositions.append(duplicate)
    elif case in ("root-review", "root-review-no-premises"):
        proof.status = "review"
        if case.endswith("no-premises"):
            proof.premise_ids = []
    elif case == "root-tombstone":
        proof.kind = "tombstone"
    elif case == "missing-premise":
        ws.propositions.remove(leaf)
    elif case == "review-premise":
        leaf.status = "review"
    elif case in ("empty-premises", "null-premises", "malformed-premises"):
        proof.premise_ids = {"empty-premises": [], "null-premises": None,
                             "malformed-premises": "first"}[case]
    elif case.startswith("row-") or case.startswith("claim-"):
        location, value = case.split("-", 1)
        invalid = {"null": None, "zero": 0, "string": "true", "false": False}[value]
        if location == "row":
            row.required_admitted_premises = invalid
        else:
            proof.conclusion["required_admitted_premises"] = invalid
    return ws, source


@pytest.mark.parametrize("case,admitted", ORDINARY_CASES.items())
def test_backend_opt_in_ordinary_rows_require_both_flags_and_the_live_proof(case, admitted):
    ws, source = ordinary_fixture(case)
    original = deepcopy(asdict(ws))
    fate = derive_class_fate(ws, source.id)
    assert fate.first_hfpss_death == (
        {"page": 3, "role": "supports", "claim_id": "map"} if admitted else None)
    assert asdict(ws) == original


def test_frontend_opt_in_ordinary_rows_match_backend_and_keep_legacy_rows_unchanged():
    payload = [{"case": case, "workspace": asdict(ordinary_fixture(case)[0])} for case in ORDINARY_CASES]
    script = RUNTIME + r"""
      helpers.accepted=r=>!!r&&ACCEPTED.includes(r.status);
      const input=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
      console.log(JSON.stringify(input.map(test=>{
        const ws=test.workspace,before=JSON.stringify(ws),a=compute(ws);
        return {case:test.case,live:ws.classes.map(n=>a.live(n,n.grade)),
          blocked:a.blockedFromPage,unchanged:before===JSON.stringify(ws)};
      })));
    """.replace("ACCEPTED", json.dumps(sorted(ACCEPTED_STATUSES)))
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, input=json.dumps(payload),
                               text=True, encoding="utf-8", capture_output=True, check=True, timeout=20)
    result = json.loads(completed.stdout)
    assert result == [{"case": case, "live": [not admitted] * 2, "blocked": None, "unchanged": True}
                      for case, admitted in ORDINARY_CASES.items()]


def test_ordinary_gate_cache_tracks_persistent_row_flag_and_removed_proof():
    ws, _ = ordinary_fixture("accepted")
    result = runtime(r"""
      helpers.accepted=r=>!!r&&ACCEPTED.includes(r.status);
      const ws=WORKSPACE,row=ws.differentials[0],proof=ws.propositions.find(p=>p.id===row.proposition_id);
      const out=[];let previous=null;
      const inspect=()=>{const a=compute(ws);out.push({same:a===previous,
        live:a.live(ws.classes[0],ws.classes[0].grade)});previous=a;};
      inspect();inspect();
      row.required_admitted_premises=false;inspect();
      row.required_admitted_premises=true;inspect();
      delete row.required_admitted_premises;inspect();
      row.required_admitted_premises=true;inspect();
      ws.propositions=ws.propositions.filter(p=>p!==proof);inspect();
      ws.propositions.push(proof);inspect();
      proof.premise_ids=[];inspect();
      proof.premise_ids=['first'];inspect();inspect();
      console.log(JSON.stringify(out));
    """.replace("ACCEPTED", json.dumps(sorted(ACCEPTED_STATUSES))).replace("WORKSPACE", json.dumps(asdict(ws))))
    assert result == [{"same": i in (1, 10), "live": i in (2, 4, 6, 8)} for i in range(11)]


def test_ordinary_gate_cache_distinguishes_legacy_absent_flag_from_invalid_null():
    ws, _ = ordinary_fixture("legacy")
    result = runtime(r"""
      helpers.accepted=r=>!!r&&ACCEPTED.includes(r.status);
      const ws=WORKSPACE,row=ws.differentials[0],rows=[];
      delete row.required_admitted_premises;
      let previous=null;
      const inspect=()=>{const a=compute(ws);rows.push({same:a===previous,
        live:a.live(ws.classes[0],ws.classes[0].grade)});previous=a;};
      inspect();row.required_admitted_premises=null;inspect();
      delete row.required_admitted_premises;inspect();
      row.required_admitted_premises=undefined;inspect();
      row.required_admitted_premises=false;inspect();
      console.log(JSON.stringify(rows));
    """.replace("ACCEPTED", json.dumps(sorted(ACCEPTED_STATUSES))).replace("WORKSPACE", json.dumps(asdict(ws))))
    assert result == [{"same": False, "live": i % 2 == 1} for i in range(5)]


def test_backend_cached_ordinary_fate_rechecks_proof_withdrawal_and_restoration():
    ws, source = ordinary_fixture("accepted")
    row = ws.differentials[0]
    proof = next(p for p in ws.propositions if p.id == row.proposition_id)
    leaf = next(p for p in ws.propositions if p.id == "first")
    assert all(p.kind not in KINDS and "coefficient_parameter" not in p.conclusion for p in ws.propositions)
    sync_workspace_fates(ws)
    assert ws._fate_has_required_premises
    assert not ws._fate_has_cycle_certificates
    nodes = [source, next(n for n in ws.classes if n.id == row.target_id)]

    def expect(live):
        for node in nodes:
            assert class_is_live_on_page(ws, node.id, 3)
            assert class_is_live_on_page(ws, node.id, 4) is live

    expect(False)
    for status in ("review", "rejected"):
        leaf.status = status
        expect(True)
        leaf.status = "verified"
        expect(False)
    for dependencies in ([], None):
        proof.premise_ids = dependencies
        expect(True)
        proof.premise_ids = [leaf.id]
        expect(False)
    ws.propositions.remove(proof)
    expect(True)
    ws.propositions.append(proof)
    expect(False)
    ws.differentials.remove(row)
    expect(True)
    ws.differentials.append(row)
    expect(False)
    # Queries re-evaluate admission without rewriting the synced event/fate.
    assert all(fate.first_hfpss_death is not None for fate in ws.fates)


def test_backend_cached_gate_retains_event_admission_when_both_current_flags_are_removed():
    ws, source = ordinary_fixture("review-premise")
    row = ws.differentials[0]
    proof = next(p for p in ws.propositions if p.id == row.proposition_id)
    sync_workspace_fates(ws)
    assert class_is_live_on_page(ws, source.id, 4)
    assert ws._fate_has_required_premises
    # Event provenance keeps an opted-in map from silently becoming a legacy
    # map when both current declarations are removed.
    row.required_admitted_premises = False
    proof.conclusion.pop("required_admitted_premises")
    assert class_is_live_on_page(ws, source.id, 4)
    row.required_admitted_premises = True
    proof.conclusion["required_admitted_premises"] = True
    assert class_is_live_on_page(ws, source.id, 4)
    next(p for p in ws.propositions if p.id == "first").status = "verified"
    assert not class_is_live_on_page(ws, source.id, 4)


@pytest.mark.parametrize("case", ("row-only", "claim-only"))
def test_backend_cached_legacy_fate_notices_a_new_partial_opt_in(case):
    ws, source = ordinary_fixture("legacy")
    row = ws.differentials[0]
    proof = next(p for p in ws.propositions if p.id == row.proposition_id)
    sync_workspace_fates(ws)
    assert not ws._fate_has_required_premises
    assert not class_is_live_on_page(ws, source.id, 4)
    if case == "row-only":
        row.required_admitted_premises = True
    else:
        proof.conclusion["required_admitted_premises"] = True
    assert class_is_live_on_page(ws, source.id, 4)


def test_serialized_event_provenance_blocks_a_removed_row_and_proof_without_private_cache_flags():
    ws, source = ordinary_fixture("accepted")
    sync_workspace_fates(ws)
    project = Project("test", "Event provenance", workspaces=[ws])
    saved = json.loads(json.dumps(project_to_dict(project)))
    assert all(event["required_admitted_premises"] is True
               for event in saved["workspaces"][0]["differential_events"])
    loaded = project_from_dict(saved)
    ws = loaded.workspaces[0]
    assert not hasattr(ws, "_fate_has_required_premises")
    assert not hasattr(ws, "_fate_has_cycle_certificates")
    assert not class_is_live_on_page(ws, source.id, 4, project=loaded)
    row = ws.differentials.pop()
    proof = next(p for p in ws.propositions if p.id == row.proposition_id)
    ws.propositions.remove(proof)
    original_events = deepcopy([asdict(event) for event in ws.differential_events])
    assert len(original_events) == 2
    assert all(fate.first_hfpss_death is not None for fate in ws.fates)
    for node in ws.classes:
        assert class_is_live_on_page(ws, node.id, 4, project=loaded)
    assert [asdict(event) for event in ws.differential_events] == original_events
    ws.differentials.append(row)
    ws.propositions.append(proof)
    for node in ws.classes:
        assert not class_is_live_on_page(ws, node.id, 4, project=loaded)


def test_sync_upgrades_legacy_event_admission_markers_without_reverting_or_rewriting_provenance():
    ws, _ = ordinary_fixture("legacy")
    row = ws.differentials[0]
    proof = next(p for p in ws.propositions if p.id == row.proposition_id)
    initial = [asdict(event) for event in ws.differential_events]
    assert all(event["required_admitted_premises"] is False for event in initial)
    row.required_admitted_premises = True
    proof.conclusion["required_admitted_premises"] = True
    sync_differential_events(ws)
    upgraded = [asdict(event) for event in ws.differential_events]
    assert upgraded == [{**event, "required_admitted_premises": True} for event in initial]
    row.required_admitted_premises = False
    proof.conclusion.pop("required_admitted_premises")
    sync_differential_events(ws)
    assert [asdict(event) for event in ws.differential_events] == upgraded


@pytest.mark.parametrize("invalid", (None, 0, "true"))
def test_invalid_event_admission_marker_fails_closed_even_with_an_accepted_current_row(invalid):
    ws, _ = ordinary_fixture("accepted")
    sync_workspace_fates(ws)
    for event in ws.differential_events:
        event.required_admitted_premises = invalid
    for node in ws.classes:
        assert class_is_live_on_page(ws, node.id, 4)


def test_roundtrip_unmarked_legacy_events_keep_the_existing_history_behavior():
    ws, source = ordinary_fixture("legacy")
    sync_workspace_fates(ws)
    raw = project_to_dict(Project("old", "Old project", workspaces=[ws]))
    for event in raw["workspaces"][0]["differential_events"]:
        event.pop("required_admitted_premises")
    loaded = project_from_dict(json.loads(json.dumps(raw))).workspaces[0]
    assert all(event.required_admitted_premises is False for event in loaded.differential_events)
    loaded.differentials.clear()
    loaded.propositions.clear()
    assert not class_is_live_on_page(loaded, source.id, 4)
