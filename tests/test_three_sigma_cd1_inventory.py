"""Counterfactual E11 inventory for CD1, with the proposed d11 removed.

Use the migrated project and the actual chart quotient, never an injected
expected arrow.  The new d11, its positive-j constraint, its AD6 consequence,
and dependent/transported propositions are removed before runtime evaluation.

Independent source equations (u = u_3sigma_i, g = kD^3):
* formal_notes.tex:678-700: d3(U)=h1^3 u and d3(C)=0, with D an E3 unit.
* formal_notes.tex:730-742: d5(PD)=XkD^2.  Multiplication by permanent g
  gives d5(PkD^4)=Xk^2D^5, the same-page image in K's r=5 source cell.
* formal_notes.tex:764-780; DKLLW main.tex:1095-1111,1183-1190,1889:
  the independently established V d9 and the two-term TD1 zero-d9 proof.
* DKLLW main.tex:2365-2369, Table 9 at 2460:
  d13(eD^4)=Theta=k^3 C_sigma h1 D^5, in grades (31,1)->(30,14).

Full proof obligations are in tmp/cd1-d11-d19-audit.md.  In particular the
runtime does not evaluate e^3=0 or e^2 Theta=K: these are actual product
identities, not a clipping instruction.  Nor does this test infer a map from
an otherwise surviving port.  It checks the finite quotient obligations and
the already-published Euler13 row without assuming the new conclusion.
"""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.migrations import migrate_project
from domain.seed import demo_project


THREE = "ws_3sigma_i"
SIGMA = "ws_sigma_i"
FACT = "DER-3I-EULER-CD1-D11"
DEPENDENT_FACTS = {FACT, "DER-3I-CD1-D11-J-zero", "DER-3I-AD6-D19-zero"}
ROW = "formal_diff_three_d11_c_D1_euler_forced"
PAGES = tuple(range(2, 12))
K_SOURCES = {3: "S11", 5: "S53", 7: "S51", 9: "S13", 11: "S11"}
C_TARGETS = {3: ("S40",), 5: (), 7: ("S00",), 9: ("S02",), 11: ("S40",)}

# Grade queries for genuine registered differentials, not synthetic equations.
WITNESSES = (
    (3, (28, 16), (27, 19)),  # Odd U k4 D5; the constant double K remains.
    (3, (8, 12), (7, 15)),   # Odd U k3 D2; the constant double W' remains.
    (3, (29, 9), (28, 12)),  # Whole U h1 k2 D4 module (K's r7 source).
    (3, (9, 5), (8, 8)),    # Whole S00 target of the low C d7.
    (3, (30, 10), (29, 13)), # Primitive image is j Ck3D5, not constant C.
    (3, (30, 2), (29, 5)),   # Primitive image is j gCD1, not constant gCD1.
    (5, (30, 6), (29, 11)),  # g times FN-3I-003: PkD4 -> Xk2D5.
    (9, (8, 10), (7, 19)),  # Actual nonzero d9 on CD1's potential d9 target.
)


def probe(name, pattern, stem, filtration, two=0, j=0):
    return dict(name=name, pattern=pattern, stem=stem, filtration=filtration, two=two, j=j)


def exact_references(value):
    """Follow structured IDs, not incidental prose mentioning a disputed fact."""
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        return set().union(*(exact_references(item) for item in value.values()))
    if isinstance(value, (list, tuple)):
        return set().union(*(exact_references(item) for item in value))
    return set()


@pytest.fixture(scope="module")
def independent_project():
    project = migrate_project(demo_project())
    propositions = [p for ws in project.workspaces for p in ws.propositions]
    present = {p.conclusion.get("fact_id") for p in propositions}
    assert DEPENDENT_FACTS <= present, "The counterfactual must remove real production conclusions"
    blocked = set(DEPENDENT_FACTS)
    removed_claims = set()
    while True:
        previous = len(removed_claims)
        for proposition in propositions:
            references = exact_references(proposition.conclusion) | set(proposition.premise_ids)
            if references & blocked:
                removed_claims.add(proposition.id)
                blocked.add(proposition.id)
                fact = proposition.conclusion.get("fact_id")
                if fact:
                    blocked.add(fact)
        if len(removed_claims) == previous:
            break

    removed_rows = []
    for workspace in project.workspaces:
        rows = [d for d in workspace.differentials
                if d.proposition_id in removed_claims or d.label == FACT or d.id.endswith(ROW)]
        removed_rows.extend((workspace.id, d.id) for d in rows)
        maps = {d.linear_map_id for d in rows if d.linear_map_id}
        row_ids = {d.id for d in rows}
        workspace.differentials = [d for d in workspace.differentials if d.id not in row_ids]
        workspace.propositions = [p for p in workspace.propositions if p.id not in removed_claims]
        workspace.differential_maps = [m for m in workspace.differential_maps if m.id not in maps]
        assert not any((exact_references(p.conclusion) | set(p.premise_ids)) & blocked
                       for p in workspace.propositions)
    # In particular, removing only the original row while leaving an atlas
    # copy or its independently active zero constraint is not sufficient.
    assert any(ws == THREE and row.endswith(ROW) for ws, row in removed_rows)
    assert any(ws != THREE for ws, _ in removed_rows)
    return project


@pytest.fixture(scope="module")
def chart(independent_project):
    probes = [probe("C", "S11", 9, 1), probe("C:j", "S11", 9, 1, j=1),
              probe("C:j7", "S11", 9, 1, j=7), probe("C:two", "S11", 9, 1, two=1),
              probe("C-out7-source", "S51", 9, 5),
              probe("C-out7-source:j", "S51", 9, 5, j=1)]
    for name, stem, filtration in (("K", 28, 16), ("Wprime", 8, 12)):
        probes.extend((probe(name, "S40", stem, filtration, two=1),
                       probe(name + ":odd", "S40", stem, filtration),
                       probe(name + ":odd-j", "S40", stem, filtration, j=1),
                       probe(name + ":two-j", "S40", stem, filtration, two=1, j=1),
                       probe(name + ":four", "S40", stem, filtration, two=2)))
    for page, pattern in K_SOURCES.items():
        probes.append(probe(f"K-in{page}", pattern, 29, 16-page))
        if pattern in {"S11", "S51"}:
            probes.extend((probe(f"K-in{page}:j", pattern, 29, 16-page, j=1),
                           probe(f"K-in{page}:j7", pattern, 29, 16-page, j=7),
                           probe(f"K-in{page}:two", pattern, 29, 16-page, two=1)))
    for page, patterns in C_TARGETS.items():
        for pattern in patterns:
            probes.append(probe(f"C-out{page}", pattern, 8, 1+page,
                                two=1 if pattern == "S40" else 0))
            if pattern == "S00":
                probes.append(probe("C-out7:j", pattern, 8, 8, j=1))
    cells = ({(29, 16-page) for page in range(2, 13)}
             | {(8, 1+page) for page in range(2, 12)}
             | {(9, 1), (30, 2), (30, 0), (28, 16), (8, 12)})
    queries = [
        dict(name="K-in3", page=3, pattern="S11", source=[29, 13], target=[28, 16],
             targetPattern="S40", targetTwo=1),
        dict(name="K-in9", page=9, pattern="S13", source=[29, 7], target=[28, 16],
             targetPattern="S40", targetTwo=1),
        dict(name="C-out3", page=3, pattern="S11", source=[9, 1], target=[8, 4],
             targetPattern="S40", targetTwo=1),
        dict(name="C-out9", page=9, pattern="S11", source=[9, 1], target=[8, 10],
             targetPattern="S02"),
        dict(name="C-out11", page=11, pattern="S11", source=[9, 1], target=[8, 12],
             targetPattern="S40", targetTwo=1),
        dict(name="K-in11", page=11, pattern="S11", source=[29, 5], target=[28, 16],
             targetPattern="S40", targetTwo=1),
    ]
    payload = {
        "project": asdict(independent_project), "workspaces": [THREE, SIGMA],
        "pages": list(PAGES), "pagesByWorkspace": {SIGMA: [13]}, "vectorAudit": True,
        "boundsByWorkspace": {
            THREE: dict(stemMin=7, stemMax=32, filtrationMin=0, filtrationMax=20),
            SIGMA: dict(stemMin=29, stemMax=32, filtrationMin=0, filtrationMax=16),
        },
        "inventoryProbes": probes, "inventoryCells": [list(grade) for grade in sorted(cells)],
        "candidateQueries": queries, "witnesses": WITNESSES,
    }
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    page_marker = "input.pages.map(page => {"
    assert harness.count(page_marker) == 1
    harness = harness.replace(page_marker, "(input.pagesByWorkspace?.[id] || input.pages).map(page => {")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""
    const pair=grade=>[grade.stem,grade.filtration];
    const same=(grade,expected)=>grade.stem===expected[0]&&grade.filtration===expected[1];
    const typed=(pattern,two=0)=>ws.classes.find(n=>!n.archived
      &&n.style?.e2_pattern===pattern&&(n.style.two_valuation||0)===two
      &&!(n.style.j_order||0)&&(!n.style.e2_components
        ||JSON.stringify(n.style.e2_components)===JSON.stringify({[pattern]:1})));
    return {
      inventoryProbes:id!=='ws_3sigma_i'?[]:input.inventoryProbes.map(p=>{
        const node={style:{e2_pattern:p.pattern,two_valuation:p.two,j_order:p.j}};
        const grade={stem:p.stem,filtration:p.filtration};
        return {...p,live:algebra.live(node,grade),ports:[...(algebra.ports(node,grade)||[])]};
      }),
      inventoryCells:id!=='ws_3sigma_i'?[]:input.inventoryCells.map(([s,f])=>({stem:s,filtration:f,
        patterns:[...new Set(points.filter(p=>p.grade.stem===s&&p.grade.filtration===f)
          .map(p=>p.item.style?.e2_pattern).filter(Boolean))].sort()})),
      witnessEdges:edges.filter(e=>id==='ws_sigma_i'
        ?page===13&&same(e.sourceGrade,[31,1])&&same(e.targetGrade,[30,14])
        :input.witnesses.some(([r,s,t])=>r===page&&same(e.sourceGrade,s)&&same(e.targetGrade,t)))
        .map(e=>{
          const p=algebra.endpoints(e.diff);
          return {id:e.diff.id,label:e.diff.label,source:pair(e.sourceGrade),target:pair(e.targetGrade),
            sourcePattern:p.source.style?.e2_pattern,targetPattern:p.target.style?.e2_pattern,
            sourceJ:p.source.style?.j_order||0,targetJ:p.target.style?.j_order||0,
            targetTwo:p.target.style?.two_valuation||0,
            admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
            sourceLive:algebra.live(p.source,e.sourceGrade),targetLive:algebra.live(p.target,e.targetGrade)};
        }),
      candidateQueries:id!=='ws_3sigma_i'?[]:input.candidateQueries.filter(q=>q.page===page).map(q=>{
        const source=typed(q.pattern),target=typed(q.targetPattern,q.targetTwo||0);
        if(!source||!target)throw new Error('Missing real typed endpoint for '+q.name);
        // Diagnostic only: never inserted into ws.differentials or the quotient.
        const query={id:'readonly-cd1-inventory-'+q.name,source_id:source.id,target_id:target.id,
          page,status:'review',coefficient_scope:'exact-port'};
        const candidate=algebra.candidateState(query,
          {stem:q.source[0],filtration:q.source[1]},
          {stem:q.target[0],filtration:q.target[1]});
        return {name:q.name,status:candidate.status,reasons:candidate.reasons,
          examined:candidate.examined,conditional:candidate.conditional};
      }),
      page, points: points.length"""
    completed = subprocess.run(
        ["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
        input=json.dumps(payload), text=True, encoding="utf-8", capture_output=True,
        check=True, timeout=240,
    )
    return {ws["id"]: {row["page"]: row for row in ws["pages"]}
            for ws in json.loads(completed.stdout)}


def observation(chart, page, name):
    return next(p for p in chart[THREE][page]["inventoryProbes"] if p["name"] == name)


def candidate(chart, page, name):
    return next(q for q in chart[THREE][page]["candidateQueries"] if q["name"] == name)


def witness(chart, page, source, target, workspace=THREE):
    matches = [e for e in chart[workspace][page]["witnessEdges"]
               if e["source"] == list(source) and e["target"] == list(target)]
    assert matches, (workspace, page, source, target)
    assert all(e["admitted"] and e["sourceLive"] and e["targetLive"]
               and e["coefficient"]["resolved"] and e["coefficient"]["value"] == 1 for e in matches)
    return matches


def test_new_conclusions_and_all_transported_rows_are_absent(independent_project, chart):
    for workspace in independent_project.workspaces:
        assert not any(p.conclusion.get("fact_id") in DEPENDENT_FACTS for p in workspace.propositions)
        assert not any(d.label == FACT or d.id.endswith(ROW) for d in workspace.differentials)
    for rows in chart.values():
        for row in rows.values():
            assert row["blockedFromPage"] is None and not row["conflicts"]
            assert not row["dangling"]
            assert not any(ident.endswith(ROW) for ident in row["rows"])


def test_complete_e2_source_target_inventories_and_even_parity(chart):
    cells = {(p["stem"], p["filtration"]): set(p["patterns"])
             for p in chart[THREE][2]["inventoryCells"]}
    for page, pattern in K_SOURCES.items():
        assert cells[29, 16-page] == {pattern}, (page, cells[29, 16-page])
    for page, patterns in C_TARGETS.items():
        assert cells[8, 1+page] == set(patterns), (page, cells[8, 1+page])
    for page in range(2, 12, 2):
        assert not cells[29, 16-page] and not cells[8, 1+page]
    assert not cells[29, 4]  # r12 cannot be the intervening incoming map to K.
    assert cells[9, 1] == {"S11"}
    assert cells[30, 2] == {"S62", "S62V"} and not cells[30, 0]


@pytest.mark.parametrize("page,ports", (
    (3, {"0:0", "0:1"}), (5, {"0:0"}), (7, set()),
    (9, {"0:0"}), (11, {"0:0"}),
))
def test_all_five_incoming_slots_use_their_actual_page_quotient(chart, page, ports):
    record = observation(chart, page, f"K-in{page}")
    assert set(record["ports"]) == ports, (page, record)
    assert record["live"] is bool(ports)


@pytest.mark.parametrize("name", ("K", "Wprime"))
def test_high_and_low_targets_have_only_the_constant_two_layer_on_e11(chart, name):
    for page in PAGES:
        record = observation(chart, page, name)
        assert record["live"] and "1:0" in record["ports"], (page, name, record)
        assert not observation(chart, page, name + ":two-j")["live"]
        assert not observation(chart, page, name + ":four")["live"]
    for suffix in (":odd", ":odd-j"):
        assert observation(chart, 3, name + suffix)["live"]
        assert not observation(chart, 4, name + suffix)["live"]
    for page in range(4, 12):
        assert observation(chart, page, name)["ports"] == ["1:0"]
    source, target = ((28, 16), (27, 19)) if name == "K" else ((8, 12), (7, 15))
    rows = witness(chart, 3, source, target)
    assert all(e["sourcePattern"] == "S40" and e["targetPattern"] == "S33" for e in rows)


def test_low_cd1_constant_and_completed_j_ideal_reach_e11_independently(chart):
    for page in PAGES:
        for name in ("C", "C:j", "C:j7"):
            record = observation(chart, page, name)
            assert record["live"] and set(record["ports"]) == {"0:0", "0:1"}, (page, name)
        assert not observation(chart, page, "C:two")["live"]
    # This preserves a completed ideal, not a second finite generator, and
    # does not use the new d11-positive-j-zero statement removed by the fixture.
    assert candidate(chart, 11, "C-out11")["status"] == "possible"
    assert candidate(chart, 11, "K-in11")["status"] == "possible"


@pytest.mark.parametrize("name,page,fact", (
    ("K-in3", 3, "fn-3i-001-zero"),
    ("K-in9", 9, "der-3i-leibniz-td1-d9-zero"),
    ("C-out3", 3, "fn-3i-001-zero"),
    ("C-out9", 9, "der-3i-euler-cd1-d9-zero"),
))
def test_early_zero_constraints_cover_genuinely_live_ports(chart, name, page, fact):
    query = candidate(chart, page, name)
    assert query["status"] == "contradicted" and query["conditional"] is False, query
    assert fact in json.dumps(query["reasons"]).lower(), query
    source_name = name if name.startswith("K-") else "C"
    assert observation(chart, page, source_name)["live"]
    target_name = "K" if name.startswith("K-") else name
    assert observation(chart, page, target_name)["live"]


def test_k_r5_source_is_a_same_page_image_before_it_leaves_e6(chart):
    assert observation(chart, 5, "K-in5")["live"]
    rows = witness(chart, 5, (30, 6), (29, 11))
    assert all(e["sourcePattern"] == "S22Y" and e["targetPattern"] == "S53" for e in rows)
    assert not observation(chart, 6, "K-in5")["live"]
    assert observation(chart, 6, "K")["live"]
    # d5^2=0 excludes its outgoing map on E5.  This is g times FN-3I-003,
    # not multiplication by k alone and not an assumed absent runtime arrow.


def test_k_r7_source_is_the_entire_primitive_module_without_a_second_two_layer(chart):
    for suffix in ("", ":j", ":j7"):
        assert observation(chart, 3, "K-in7" + suffix)["live"]
        assert not observation(chart, 4, "K-in7" + suffix)["live"]
        assert not observation(chart, 7, "K-in7" + suffix)["ports"]
    assert not observation(chart, 2, "K-in7:two")["live"]
    witness(chart, 3, (29, 9), (28, 12))


@pytest.mark.parametrize("incoming_page,source,target", (
    (3, (30, 10), (29, 13)),
    (11, (30, 2), (29, 5)),
))
def test_high_c_incoming_d3_removes_only_positive_j_not_the_constant(chart, incoming_page, source, target):
    name = f"K-in{incoming_page}"
    rows = witness(chart, 3, source, target)
    assert all(e["sourcePattern"] == "S62V" and e["targetPattern"] == "S11"
               and e["targetJ"] == 1 for e in rows)
    for suffix in (":j", ":j7"):
        assert observation(chart, 3, name + suffix)["live"]
        assert not observation(chart, 4, name + suffix)["live"]
        assert not observation(chart, 11, name + suffix)["live"]
    for page in range(4, 12):
        assert observation(chart, page, name)["live"]
        assert observation(chart, page, name)["ports"] == ["0:0"]
    assert not observation(chart, 2, name + ":two")["live"]


def test_low_cd1_d7_target_is_a_whole_actual_d3_image(chart):
    for suffix in ("", ":j"):
        assert observation(chart, 3, "C-out7" + suffix)["live"]
        assert observation(chart, 3, "C-out7-source" + suffix)["live"]
        assert not observation(chart, 4, "C-out7" + suffix)["live"]
        assert not observation(chart, 7, "C-out7" + suffix)["ports"]
    rows = witness(chart, 3, (9, 5), (8, 8))
    assert all(e["sourcePattern"] == "S51" and e["targetPattern"] == "S00" for e in rows)


def test_low_cd1_d9_candidate_target_itself_has_nonzero_d9(chart):
    assert observation(chart, 9, "C-out9")["ports"] == ["0:0"]
    rows = witness(chart, 9, (8, 10), (7, 19))
    assert all(e["sourcePattern"] == "S02" and e["targetPattern"] == "S73" for e in rows)
    assert not observation(chart, 10, "C-out9")["ports"]
    assert observation(chart, 10, "C")["live"]


def test_published_sigma_euler13_row_is_independent_of_cd1_admission(chart):
    rows = witness(chart, 13, (31, 1), (30, 14), workspace=SIGMA)
    assert all(e["sourcePattern"] == "S71" and e["targetPattern"] == "S22H" for e in rows)
    # The actual source is eD4.  The source product e^3D4 is a zero element
    # in a potentially occupied cell, not a row to insert into the 3sigma chart.
    # e^2Theta=K and the Euler Leibniz argument remain the cited source proof.
