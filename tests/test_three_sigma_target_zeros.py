"""Target consequences of d23(W5)=Y are exact outgoing constraints only.

These regressions do not prove the parent differential from its consequences.
test_three_sigma_d23_inventory.py removes the parent and both derived zeros
before checking the independent proof obligations. Here the actual migrated
chart checks the resulting E19/E23/E24 quotients and read-only candidate queries.
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
from domain.fate import _cycle_claim_covers
from domain.logic_graph import admitted_proposition_ids
from domain.migrations import migrate_project
from domain.seed import demo_project


PARENT = "DER-3I-LEIBNIZ-W5-D23"
FACTS = {page: f"DER-3I-W5-TARGET-D{page}-zero" for page in (19, 23)}
ATLAS = {"ws_3sigma_i": 0, "ws_q8-ro-a0-b3": 0, "ws_q8-ro-a1-b1": 16}
TRANSLATIONS = tuple((d8, g) for d8 in (-1, 0, 1) for g in (0, 1))
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


def records(workspace, page):
    claims = [p for p in workspace.propositions if p.conclusion.get("fact_id") == FACTS[page]]
    parents = [p for p in workspace.propositions if p.conclusion.get("fact_id") == PARENT]
    assert len(claims) == len(parents) == 1
    claim, parent = claims[0], parents[0]
    source = next(n for n in workspace.classes if n.id == claim.conclusion["source_id"])
    return claim, source, parent


def test_target_constraints_have_local_parent_premises_in_all_three_atlas_images(project):
    admitted = admitted_proposition_ids(project)
    for workspace in images(project):
        for page in FACTS:
            claim, source, parent = records(workspace, page)
            data = claim.conclusion
            assert claim.kind == "zero-differential" and claim.status == "verified"
            assert claim.id in admitted and parent.id in admitted
            assert claim.premise_ids == [parent.id]
            assert parent.kind == "differential" and parent.conclusion["page"] == 23
            assert data["zero"] is True and data["page"] == page
            assert data["coefficient_scope"] == "exact-port"
            assert data["cycle_constraint"] == "outgoing-only"
            assert data["derived_from"] == [PARENT]
            assert data["period_stem"] == 64 and data["period_is_invertible"] is True
            assert data["forward_period"] == {
                "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
            }
            assert (source.grade.stem, source.grade.filtration) == (43 + ATLAS[workspace.id], 23)
            assert data["grade"] == {"stem": 43 + ATLAS[workspace.id], "filtration": 23}
            assert (source.style["e2_pattern"], source.style.get("two_valuation", 0),
                    source.style.get("j_order", 0)) == ("S73", 0, 0)
            assert not source.archived
            certificate = data["verification_certificate"]
            assert certificate["scope"] == "source-workspace"
            assert certificate["source_workspace_id"] == "ws_3sigma_i"
            assert certificate["premises"] == [PARENT]
            assert certificate["boundary_from_page"] == 24
            assert certificate["survival_override"] is False
            assert certificate["nonzero_parent_map"] == {
                "source": [44, 0], "target": [43, 23], "page": 23,
            }
            assert not data.get("source_blockers") and not data.get("withdrawn_dependencies")
            assert not any(d.proposition_id == claim.id or d.label == FACTS[page]
                           for d in workspace.differentials)
            if workspace.id != "ws_3sigma_i":
                transport = data["atlas_transport"]
                assert transport["source_workspace_id"] == "ws_3sigma_i"
                assert transport["source_proposition_id"] == f"formal_prop_{FACTS[page].lower()}"
                assert parent.id != "formal_prop_der-3i-leibniz-w5-d23_1"


def test_migration_restores_only_zero_claims_without_mutating_the_parent_map(project):
    candidate = deepcopy(project)
    expected = {(w.id, page): tuple(asdict(item) for item in records(w, page))
                for w in images(candidate) for page in FACTS}
    arrows = {w.id: [asdict(d) for d in w.differentials] for w in images(candidate)}
    for workspace in images(candidate):
        workspace.propositions = [p for p in workspace.propositions
                                  if p.conclusion.get("fact_id") not in FACTS.values()]
    for _ in range(2):
        candidate = migrate_project(candidate)
        actual = {(w.id, page): tuple(asdict(item) for item in records(w, page))
                  for w in images(candidate) for page in FACTS}
        assert actual == expected
        assert {w.id: [asdict(d) for d in w.differentials] for w in images(candidate)} == arrows


@pytest.mark.parametrize("page", (19, 23))
def test_exact_scope_is_d8_bilateral_forward_g_and_projective_finite_port_only(project, page):
    # These endpoint copies query the production certificate guard; they are
    # not inserted as extra classes or proposed maps in the project.
    for workspace in images(project):
        claim, source, _ = records(workspace, page)
        for d8, g in TRANSLATIONS:
            node = deepcopy(source)
            node.id = "readonly-scope-probe"
            node.grade.stem += 64*d8 + 20*g
            node.grade.filtration += 4*g
            for scalar in (1, 2, 3):
                node.style["e2_components"] = {"S73": scalar}
                assert _cycle_claim_covers(workspace, claim, node, page)
        for label, stem, filtration, style, query_page in (
            ("D4", 32, 0, {}, page),
            ("negative-g", -20, -4, {}, page),
            ("D8-negative-g", 44, -4, {}, page),
            ("wrong-g-slope", 20, 3, {}, page),
            ("S73V", 0, 0, {"e2_pattern": "S73V"}, page),
            ("Witt", 0, 0, {"two_valuation": 1}, page),
            ("positive-j", 0, 0, {"j_order": 1}, page),
            ("previous-page", 0, 0, {}, page-1),
            ("later-page", 0, 0, {}, page+1),
            ("other-zero-page", 0, 0, {}, 23 if page == 19 else 19),
        ):
            node = deepcopy(source)
            node.id = "readonly-" + label
            node.grade.stem += stem
            node.grade.filtration += filtration
            node.style.pop("e2_components", None)
            node.style.update(style)
            assert not _cycle_claim_covers(workspace, claim, node, query_page), (workspace.id, page, label)


@pytest.mark.parametrize("parent_state", ("missing", "review"))
def test_dependent_zero_requires_its_own_atlas_parent_not_the_source_workspace_parent(project, parent_state):
    candidate = deepcopy(project)
    for workspace in images(candidate):
        claims = [records(workspace, page) for page in FACTS]
        parent = claims[0][2]
        if parent_state == "missing":
            workspace.propositions = [p for p in workspace.propositions if p.id != parent.id]
        else:
            parent.status = "review"
        for page, (claim, source, _) in zip(FACTS, claims):
            assert not _cycle_claim_covers(workspace, claim, source, page)


def probe(name, pattern, stem, filtration, two=0, j=0):
    return dict(name=name, pattern=pattern, stem=stem, filtration=filtration, two=two, j=j)


@pytest.fixture(scope="module", params=tuple(ATLAS))
def chart(project, request):
    workspace = next(w for w in images(project) if w.id == request.param)
    shift = ATLAS[workspace.id]
    probes = []
    for d8, g in TRANSLATIONS:
        stem, filtration = 43 + shift + 64*d8 + 20*g, 23 + 4*g
        prefix = f"D8{d8}:g{g}"
        probes += [probe(prefix+":Y", "S73", stem, filtration),
                   probe(prefix+":Y-j", "S73", stem, filtration, j=1),
                   probe(prefix+":S73V", "S73V", stem, filtration),
                   probe(prefix+":W", "S40", stem+1, filtration-23, two=1)]
        if g == 0:
            for two, j in ((2, 0), (3, 0), (1, 1), (2, 1), (3, 1)):
                probes.append(probe(prefix+f":kernel-{two}:{j}", "S40", stem+1, 0, two=two, j=j))
    payload = {
        "project": asdict(project), "workspaces": [workspace.id], "pages": [19, 23, 24],
        "bounds": dict(stemMin=shift-24, stemMax=shift+132, filtrationMin=0, filtrationMax=30),
        "vectorAudit": True, "targetProbes": probes, "facts": FACTS,
        "translations": TRANSLATIONS, "shift": shift, "parent": PARENT,
    }
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""
    const typed=pattern=>ws.classes.find(n=>!n.archived&&n.style?.e2_pattern===pattern
      &&!(n.style.two_valuation||0)&&!(n.style.j_order||0)
      &&(!n.style.e2_components||JSON.stringify(n.style.e2_components)===JSON.stringify({[pattern]:1})));
    const query=(name,pattern,stem,filtration)=>{
      const source=typed(pattern),target=typed(page===19?'S22H':'S62');
      if(!source||!target)throw new Error('Missing real typed endpoint for '+name);
      const sourceGrade={stem,filtration},targetGrade={stem:stem-1,filtration:filtration+page};
      const candidate=algebra.candidateState({id:'readonly-target-zero-'+name,
        source_id:source.id,target_id:target.id,page,status:'review',coefficient_scope:'exact-port'},
        sourceGrade,targetGrade);
      return {name,status:candidate.status,reasons:candidate.reasons,examined:candidate.examined,
        conditional:candidate.conditional,sourceLive:algebra.live(source,sourceGrade),
        targetLive:algebra.live(target,targetGrade)};
    };
    const queries=page===24?[]:input.translations.map(([d8,g])=>query(
      'D8'+d8+':g'+g,'S73',43+input.shift+64*d8+20*g,23+4*g));
    const controls=page===24?[]:[query('D4','S73',75+input.shift,23),
      query('negative-g','S73',23+input.shift,19),query('S73V','S73V',43+input.shift,23)];
    return {
      targetProbes:input.targetProbes.map(p=>{
        const node={style:{e2_pattern:p.pattern,two_valuation:p.two,j_order:p.j}};
        const grade={stem:p.stem,filtration:p.filtration};
        return {...p,live:algebra.live(node,grade),ports:[...(algebra.ports(node,grade)||[])]};
      }),
      queries,controls,
      zeroEdges:edges.filter(e=>Object.values(input.facts).includes(e.diff.label)||e.diff.zero)
        .map(e=>e.diff.id),
      forcedEdges:edges.filter(e=>e.diff.label===input.parent).map(e=>({
        source:e.sourceGrade,target:e.targetGrade,admitted:algebra.canApply(e.diff),
        coefficient:algebra.coefficientState(e.diff)})),
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
    return next(p for p in row["targetProbes"] if p["name"] == name)


def test_y_is_a_nonzero_finite_target_through_e23_and_a_genuine_boundary_on_e24(chart):
    workspace_id, rows = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8{d8}:g{g}"
        for page in (19, 23):
            y = observation(rows[page], prefix+":Y")
            assert y["live"] and y["ports"] == ["0:0"]
            assert not observation(rows[page], prefix+":Y-j")["live"]
            assert not observation(rows[page], prefix+":S73V")["live"]
        y = observation(rows[24], prefix+":Y")
        assert not y["live"] and not y["ports"]
        stem, filtration = 43 + ATLAS[workspace_id] + 64*d8 + 20*g, 23+4*g
        incoming = [e for e in rows[23]["forcedEdges"]
                    if e["target"]["stem"] == stem and e["target"]["filtration"] == filtration]
        assert incoming and all(e["admitted"] and e["coefficient"]["resolved"]
                                and e["coefficient"]["value"] == 1 for e in incoming)
        assert all(e["source"]["stem"] == stem+1 and e["source"]["filtration"] == filtration-23
                   for e in incoming)


def test_outgoing_zero_never_removes_the_remaining_witt_or_j_kernel(chart):
    _, rows = chart
    for d8, g in TRANSLATIONS:
        prefix = f"D8{d8}:g{g}"
        before, after = (observation(rows[page], prefix+":W") for page in (23, 24))
        assert before["live"] and "1:0" in before["ports"]
        assert not after["live"]
        assert after["ports"] == [port for port in before["ports"] if port != "1:0"]
        if g == 0:
            assert before["ports"] == WITT_BEFORE and after["ports"] == WITT_AFTER
            for two, j in ((2, 0), (3, 0), (1, 1), (2, 1), (3, 1)):
                kernel = observation(rows[24], prefix+f":kernel-{two}:{j}")
                assert kernel["live"] and f"{two}:{j}" in kernel["ports"]


def test_actual_nonzero_candidate_queries_are_constrained_at_exact_target_ports(chart):
    _, rows = chart
    for page in (19, 23):
        for query in rows[page]["queries"]:
            assert query["sourceLive"] and query["conditional"] is False
            if query["targetLive"]:
                assert query["status"] == "contradicted", (page, query)
                assert FACTS[page].lower() in json.dumps(query["reasons"]).lower()
            else:
                # No fabricated endpoint is introduced merely to test a zero.
                assert query["status"] == "absent", (page, query)
        for query in rows[page]["controls"]:
            certificate_text = json.dumps(query["reasons"]).lower()
            assert not any(fact.lower() in certificate_text for fact in FACTS.values()), (page, query)
        other = FACTS[23 if page == 19 else 19].lower()
        assert all(other not in json.dumps(q["reasons"]).lower() for q in rows[page]["queries"])


def test_zero_constraints_never_render_as_arrows_or_overwrite_quotients(chart):
    _, rows = chart
    for row in rows.values():
        assert not row["zeroEdges"]
        assert row["blockedFromPage"] is None and not row["conflicts"]
        assert not row["dangling"]
    assert not rows[19]["forcedEdges"] and not rows[24]["forcedEdges"]
