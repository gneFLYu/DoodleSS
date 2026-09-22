"""Executable obligations preceding the W5 d23, with that conclusion removed.

This is a real migrated-project/chart-runtime audit, not a test of the new
certificate's prose.  It checks the finite inventories, earlier nonzero maps,
completed coefficient quotients, and independently registered zero constraints.
No hypothetical differential is installed or admitted by the diagnostics.

Scope: the runtime has no evaluator for the hidden product R*h1=2kU or for
the L=D^-1*h1 detector.  Those product identities and their Leibniz arguments
remain source-proof obligations (tmp/w5-d23-proof-audit.md); a surviving port
alone is not a proof of either identity.  The tests below check their required
nonzero detector lines, not a second hand-written multiplication engine.
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
FACT = "DER-3I-LEIBNIZ-W5-D23"
DEPENDENT_FACTS = {FACT, "DER-3I-W5-TARGET-D19-zero", "DER-3I-W5-TARGET-D23-zero"}
ROW = "formal_diff_three_d23_u_D5_forced"
P, Q = {"S22Y": 1}, {"S22H": 1}
SUM = {"S22Y": 1, "S22H": 1}
PAGES = (2, 3, 4, 5, 6, 7, 9, 10, 11, 13, 15, 17, 19, 21, 23)

# Complete occupied E2 directions in the two finite inventories.  Empty
# even-page cells are checked separately against actual E2 chart instances.
W_TARGETS = {
    3: ("S33",), 5: ("S71",), 7: ("S73", "S73V"), 9: (),
    11: ("S33",), 13: ("S71",), 15: ("S73", "S73V"), 17: (),
    19: ("S33",), 21: ("S71",), 23: ("S73", "S73V"),
}
G_SOURCES = {
    3: "S11", 5: "S53", 7: "S51", 9: "S13", 11: "S11",
    13: "S53", 15: "S51", 17: "S13", 19: "S11", 21: "S53", 23: "S51",
}

# These are grade queries for genuine already-registered maps.  In particular
# boundary witnesses are not replaced by a flag saying that their target died.
WITNESSES = (
    (3, (44, 0), (43, 3)),       # U D5 -> h1^3 D5; its double is retained.
    (3, (58, 14), (57, 17)),     # Entire positive-j C ideal, not its constant.
    (3, (57, 21), (56, 24)),     # Entire U h1 completed module.
    (3, (57, 13), (56, 16)),
    (3, (57, 5), (56, 8)),
    (5, (43, 5), (42, 10)),     # W's d5 target maps to finite P+Q.
    (5, (35, 13), (34, 18)),    # B7's d5 target likewise maps to P+Q.
    (5, (43, 13), (42, 18)),
    (5, (43, 21), (42, 26)),
    (5, (58, 18), (57, 23)),    # Incoming d5 to the prospective incoming-d5 X.
    (5, (57, 15), (56, 20)),
    (5, (58, 6), (57, 11)),     # d5(A k D8) = T k^2 D8.
    (5, (58, 2), (57, 7)),      # d5(P D7) = g X D5.
    (9, (44, 6), (43, 15)),     # Forward-g FN008 image.
    (9, (57, 9), (56, 18)),     # Forward-g^2 even-C differential.
)


def probe(name, pattern, stem, filtration, two=0, j=0):
    return dict(name=name, pattern=pattern, stem=stem, filtration=filtration, two=two, j=j)


@pytest.fixture(scope="module")
def independent_project():
    project = migrate_project(demo_project())
    removed = []
    for workspace in project.workspaces:
        claims = {p.id for p in workspace.propositions
                  if p.conclusion.get("fact_id") in DEPENDENT_FACTS}
        rows = [d for d in workspace.differentials
                if d.proposition_id in claims or d.label == FACT or d.id.endswith(ROW)]
        removed.extend((workspace.id, d.id) for d in rows)
        maps = {d.linear_map_id for d in rows if d.linear_map_id}
        row_ids = {d.id for d in rows}
        workspace.differentials = [d for d in workspace.differentials if d.id not in row_ids]
        workspace.propositions = [p for p in workspace.propositions if p.id not in claims]
        workspace.differential_maps = [m for m in workspace.differential_maps if m.id not in maps]
    # Keep harmless class aliases, but remove the conclusion, its row, its
    # derived target-zero constraints, and any linear-map implementation in
    # every image before invoking the runtime. In particular, Y's d19-zero
    # must not be used as a premise for proving the very d23 that implies it.
    assert len(removed) == 3 and any(ws == THREE for ws, _ in removed)
    return project


@pytest.fixture(scope="module")
def chart(independent_project):
    probes = [probe("W", "S40", 44, 0, two=1), probe("W-four", "S40", 44, 0, two=2),
              probe("B7", "S40", 36, 8, two=1), probe("G", "S40", 56, 28, two=1),
              probe("B7-in3", "S11", 37, 5), probe("B7-in5", "S53", 37, 3),
              probe("G-d13-image", "S40", 56, 20, two=1)]
    for page, patterns in W_TARGETS.items():
        for pattern in patterns:
            probes.append(probe(f"W-out{page}:{pattern}", pattern, 43, page))
    for page, pattern in G_SOURCES.items():
        probes.append(probe(f"G-in{page}", pattern, 57, 28-page))
        if pattern in {"S11", "S51"}:
            probes.append(probe(f"G-in{page}:j", pattern, 57, 28-page, j=1))
    vector_specs = [dict(components=components, stem=stem, filtration=filtration)
                    for stem, filtration in ((42, 10), (34, 18), (42, 26), (42, 18))
                    for components in (P, Q, SUM)]
    cells = {(43, page) for page in range(2, 24)} | {(57, 28-page) for page in range(2, 24)}
    # Queries use real stored typed nodes at periodic occurrence grades.  They
    # test whether an independent zero certificate covers a possible map, not
    # whether the map happened to be omitted from the current row list.
    zero_queries = [
        dict(name="G-in3", page=3, pattern="S11", source=[57, 25], target=[56, 28]),
        dict(name="G-in9", page=9, pattern="S13", source=[57, 19], target=[56, 28]),
        dict(name="G-in11", page=11, pattern="S11", source=[57, 17], target=[56, 28]),
        dict(name="B7-in3", page=3, pattern="S11", source=[37, 5], target=[36, 8]),
        dict(name="B7-in5", page=5, pattern="S53", source=[37, 3], target=[36, 8]),
    ]
    payload = {
        "project": asdict(independent_project), "workspaces": [THREE, "ws_integer"],
        "pages": list(PAGES), "pagesByWorkspace": {"ws_integer": [23]}, "vectorAudit": True,
        "boundsByWorkspace": {
            THREE: dict(stemMin=34, stemMax=60, filtrationMin=0, filtrationMax=30),
            "ws_integer": dict(stemMin=-8, stemMax=14, filtrationMin=0, filtrationMax=30),
        },
        "inventoryProbes": probes, "vectorProbes": vector_specs,
        "inventoryCells": [list(grade) for grade in sorted(cells)],
        "zeroQueries": zero_queries, "witnesses": WITNESSES,
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
      inventoryProbes:input.inventoryProbes.map(p=>{
        const node={style:{e2_pattern:p.pattern,two_valuation:p.two,j_order:p.j}};
        const grade={stem:p.stem,filtration:p.filtration};
        return {...p,live:algebra.live(node,grade),ports:[...(algebra.ports(node,grade)||[])]};
      }),
      inventoryCells:input.inventoryCells.map(([s,f])=>({stem:s,filtration:f,
        patterns:[...new Set(points.filter(p=>p.grade.stem===s&&p.grade.filtration===f)
          .map(p=>p.item.style?.e2_pattern).filter(Boolean))].sort()})),
      witnessEdges:edges.filter(e=>id==='ws_integer'||input.witnesses.some(([r,s,t])=>
        r===page&&same(e.sourceGrade,s)&&same(e.targetGrade,t))).map(e=>{
          const p=algebra.endpoints(e.diff);
          return {id:e.diff.id,label:e.diff.label,source:pair(e.sourceGrade),target:pair(e.targetGrade),
            sourcePattern:p.source.style?.e2_pattern,targetPattern:p.target.style?.e2_pattern,
            targetComponents:p.target.style?.e2_components,sourceJ:p.source.style?.j_order||0,
            targetJ:p.target.style?.j_order||0,targetTwo:p.target.style?.two_valuation||0,
            admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
            sourceLive:algebra.live(p.source,e.sourceGrade),targetLive:algebra.live(p.target,e.targetGrade)};
        }),
      zeroQueries:id!=='ws_3sigma_i'?[]:input.zeroQueries.filter(q=>q.page===page).map(q=>{
        const source=typed(q.pattern),target=typed('S40',1);
        if(!source||!target)throw new Error('Missing real typed endpoint for '+q.name);
        const query={id:'readonly-inventory-'+q.name,source_id:source.id,target_id:target.id,
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


def vector(chart, page, grade, components):
    return next(p for p in chart[THREE][page]["vectorProbes"]
                if (p["stem"], p["filtration"]) == grade and p["components"] == components)


def witness(chart, page, source, target, workspace=THREE):
    matches = [e for e in chart[workspace][page]["witnessEdges"]
               if e["source"] == list(source) and e["target"] == list(target)]
    assert matches, (page, source, target)
    assert all(e["admitted"] and e["sourceLive"] and e["targetLive"]
               and e["coefficient"]["resolved"] and e["coefficient"]["value"] == 1 for e in matches)
    return matches


def test_new_conclusion_is_absent_from_every_workspace_before_the_audit(independent_project, chart):
    for workspace in independent_project.workspaces:
        assert not any(p.conclusion.get("fact_id") in DEPENDENT_FACTS
                       for p in workspace.propositions)
        assert not any(d.label == FACT or d.id.endswith(ROW) for d in workspace.differentials)
    for rows in chart.values():
        for row in rows.values():
            assert row["blockedFromPage"] is None and not row["conflicts"]
            assert not row["dangling"]


def test_complete_e2_inventories_and_even_page_parity(chart):
    cells = {(p["stem"], p["filtration"]): set(p["patterns"])
             for p in chart[THREE][2]["inventoryCells"]}
    for page, patterns in W_TARGETS.items():
        assert cells[43, page] == set(patterns), (page, cells[43, page])
    for page, pattern in G_SOURCES.items():
        assert cells[57, 28-page] == {pattern}, (page, cells[57, 28-page])
    for page in range(2, 24, 2):
        assert not cells[43, page] and not cells[57, 28-page]


def test_detector_b7_and_high_g_are_nonzero_without_the_proposed_d23(chart):
    for page in (3, 4, 5, 6, 7):
        b7 = observation(chart, page, "B7")
        assert b7["live"] and "1:0" in b7["ports"]
    for page in PAGES:
        for name in ("W", "W-four", "G"):
            record = observation(chart, page, name)
            assert record["live"], (page, name, record)
    assert observation(chart, 23, "G")["ports"] == ["1:0"]
    assert "2:0" in observation(chart, 23, "W")["ports"]  # f0 is Witt, not just F4.
    witness(chart, 3, (44, 0), (43, 3))
    assert "0:0" not in observation(chart, 4, "W")["ports"]


def test_finite_p_and_q_and_their_sum_are_nonzero_on_e5(chart):
    for grade in ((42, 10), (34, 18), (42, 26), (42, 18)):
        p, q, total = (vector(chart, 5, grade, c) for c in (P, Q, SUM))
        assert p["live"] and q["live"] and total["live"], grade
        assert p["slots"] != q["slots"], grade
    for source, target in (((43, 5), (42, 10)), ((35, 13), (34, 18)),
                           ((43, 21), (42, 26))):
        assert all(e["targetComponents"] == SUM for e in witness(chart, 5, source, target))
        assert not vector(chart, 6, target, SUM)["live"]
    witness(chart, 5, (43, 13), (42, 18))
    assert not vector(chart, 6, (42, 18), Q)["live"]


@pytest.mark.parametrize("page,pattern,absent_from", (
    (5, "S71", 6), (11, "S33", 4), (13, "S71", 6),
    (15, "S73", 10), (19, "S33", 4), (21, "S71", 6),
))
def test_w5_earlier_target_dispositions_are_actual_quotients(chart, page, pattern, absent_from):
    name = f"W-out{page}:{pattern}"
    assert observation(chart, 3, name)["live"]
    for check_page in {max(page, absent_from), 23}:
        assert not observation(chart, check_page, name)["live"], (page, check_page)


def test_w5_d7_detector_and_later_finite_target_do_not_include_s73v(chart):
    assert observation(chart, 7, "W-out7:S73")["live"]
    assert observation(chart, 7, "B7")["live"]
    witness(chart, 9, (44, 6), (43, 15))
    for page in (7, 15, 23):
        name = f"W-out{page}:S73V"
        assert observation(chart, 3, name)["live"]
        assert not observation(chart, 4, name)["ports"]
        assert not observation(chart, page, name)["live"]
    assert observation(chart, 23, "W-out23:S73")["ports"] == ["0:0"]


@pytest.mark.parametrize("name,page,fact", (
    ("G-in3", 3, "fn-3i-001-zero"),
    ("G-in9", 9, "der-3i-leibniz-td5-d9-zero"),
    ("G-in11", 11, "der-3i-euler-cd5-cycle"),
    ("B7-in3", 3, "fn-3i-001-zero"),
    ("B7-in5", 5, "der-3i-euler-xd5-cycle"),
))
def test_registered_zero_certificates_cover_actual_nonzero_incoming_ports(chart, name, page, fact):
    query = next(q for q in chart[THREE][page]["zeroQueries"] if q["name"] == name)
    assert query["status"] == "contradicted" and query["conditional"] is False, query
    assert fact in json.dumps(query["reasons"]).lower(), query
    assert observation(chart, page, name)["live"]


def test_g_incoming_d5_source_is_a_same_page_image_not_an_unexplained_omission(chart):
    assert observation(chart, 5, "G-in5")["live"]
    witness(chart, 5, (58, 18), (57, 23))
    assert not observation(chart, 6, "G-in5")["live"]
    # d5 squared = 0 excludes its outgoing map to G on E5; G was not
    # removed together with this source's genuine incoming image.
    assert observation(chart, 6, "G")["live"]


@pytest.mark.parametrize("page", (7, 15, 23))
def test_g_incoming_uh1_is_the_entire_primitive_d3_module(chart, page):
    for suffix in ("", ":j"):
        assert observation(chart, 3, f"G-in{page}{suffix}")["live"]
        assert not observation(chart, 4, f"G-in{page}{suffix}")["live"]
        assert not observation(chart, page, f"G-in{page}{suffix}")["ports"]
    filtration = 28-page
    witness(chart, 3, (57, filtration), (56, filtration+3))


def test_g_incoming_c_positive_j_is_not_restored_by_cd5_cycle(chart):
    assert observation(chart, 3, "G-in11:j")["live"]
    edge = witness(chart, 3, (58, 14), (57, 17))
    assert all(e["targetPattern"] == "S11" and e["targetJ"] == 1 for e in edge)
    for page in (4, 11, 23):
        assert observation(chart, page, "G-in11")["ports"] == ["0:0"]
        assert not observation(chart, page, "G-in11:j")["live"]


def test_g_later_incoming_sources_have_nonzero_earlier_maps(chart):
    assert observation(chart, 5, "G-in13")["live"]
    assert observation(chart, 5, "G-d13-image")["ports"] == ["1:0"]
    edge = witness(chart, 5, (57, 15), (56, 20))
    assert all(e["targetPattern"] == "S40" and e["targetTwo"] == 1 for e in edge)
    assert not observation(chart, 6, "G-in13")["live"]
    assert observation(chart, 9, "G-in19")["live"]
    witness(chart, 9, (57, 9), (56, 18))
    for page in (10, 19, 23):
        assert not observation(chart, page, "G-in19")["ports"]
        assert not observation(chart, page, "G-in19:j")["live"]


@pytest.mark.parametrize("incoming_page,source,target", (
    (17, (58, 6), (57, 11)),
    (21, (58, 2), (57, 7)),
))
def test_g_incoming_t_and_x_are_genuine_d5_boundaries_never_revived(chart, incoming_page, source, target):
    name = f"G-in{incoming_page}"
    assert observation(chart, 5, name)["live"]
    witness(chart, 5, source, target)
    for page in (6, incoming_page, 23):
        assert not observation(chart, page, name)["ports"], (incoming_page, page)


def test_published_integer_l_and_gl_reach_their_real_d23_targets(chart):
    # This checks the already-published maps, not the unimplemented cross-
    # workspace products with W5/Y. Those are explicitly outside this test's scope.
    witness(chart, 23, (-7, 1), (-8, 24), workspace="ws_integer")
    witness(chart, 23, (13, 5), (12, 28), workspace="ws_integer")
