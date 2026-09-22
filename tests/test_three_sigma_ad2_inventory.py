"""Independent finite prerequisites for the AD2 Euler-cofiber d19 argument.

The future AD2 conclusion and its structured dependents are omitted.  The
independent CD5 cycle is retained.  Tables in tmp/cd1-d11-d19-audit.md:167-208
are checked against the actual migrated chart, including completed j ideals,
finite coefficient directions, same-page images, and the P/Q quotient.

Sources: formal_notes.tex:678-705 (complete primitive d3), 707-762 (d5),
520-526 and 678-762 (independent Euler-derived P/Q/C d9); DKLLW main.tex:1895
(d9(D^2 h1), translated by permanent g^3 D^-8), 1311-1315 (integer strong
bound).  Actual Euler multiplication, BBHS Table 4's complete pi13(C4)=0,
convergence, and the unbounded vanishing theorem remain source-proof inputs.
Finite runtime tests do not implement a second product engine or prove an
infinite bound by imposing a display cutoff.
"""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import pytest

from test_three_sigma_cd1_inventory import exact_references

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from domain.migrations import migrate_project
from domain.seed import demo_project


THREE, INTEGER = "ws_3sigma_i", "ws_integer"
FACT = "DER-3I-EULER-AD2-D19"
ROW = "formal_diff_three_d19_a_D2_euler_forced"
P, Q = {"S22Y": 1}, {"S22H": 1}
SUM = {"S22Y": 1, "S22H": 1}
A_TARGETS = {
    3: "S11", 5: "S13", 7: "S51", 9: "S53", 11: "S11",
    13: "S13", 15: "S51", 17: "S53", 19: "S11",
}
B_SOURCES = {
    3: ("S62", "S62V"), 5: (), 7: ("S22Y", "S22H"), 9: (),
    11: ("S62", "S62V"), 13: (), 15: ("S22Y", "S22H"), 17: (),
    19: ("S62", "S62V"), 21: (),
}
WITNESSES = (
    (3, (14, 2), (13, 5)),    # AD2's distinct S62V direction -> jCkD2.
    (3, (14, 10), (13, 13)),  # B's incoming11 S62V direction -> jC.
    (3, (14, 18), (13, 21)),  # B's incoming3 hits only positive-j B.
    (3, (13, 9), (12, 12)),   # A's d7 target: entire primitive source.
    (3, (13, 17), (12, 20)),  # A's d15 target: entire primitive source.
    (3, (15, 11), (14, 14)),  # B's incoming7 Q-positive-j image.
    (3, (15, 3), (14, 6)),    # B's incoming15 Q-positive-j image.
    (5, (15, 9), (14, 14)),   # P+Q, not both separate columns.
    (5, (14, 6), (13, 11)),   # B's incoming15 P and A's d9 target.
    (5, (15, 1), (14, 6)),    # B's incoming15 Q.
    (5, (14, 10), (13, 15)),  # B's incoming11 A and A's d13 target.
    (5, (13, 19), (12, 24)),  # A's d17 X target -> finite two-layer.
    (5, (15, 17), (14, 22)),  # h1 B2 = Q k5 D4 is already a finite d5 image.
    (9, (13, 13), (12, 22)),  # A's d11 C target has earlier nonzero d9.
    (9, (14, 14), (13, 23)),  # B's incoming7 finite [P]=[Q] has nonzero d9.
)


def probe(name, pattern, stem, filtration, two=0, j=0):
    return dict(name=name, pattern=pattern, stem=stem, filtration=filtration, two=two, j=j)


@pytest.fixture(scope="module")
def project_audit():
    project = migrate_project(demo_project())
    blocked, removed = {FACT, ROW}, set()
    propositions = [p for ws in project.workspaces for p in ws.propositions]
    production_has_row = any(p.conclusion.get("fact_id") == FACT for p in propositions)
    while True:
        previous = len(removed)
        for p in propositions:
            if (exact_references(p.conclusion) | set(p.premise_ids)) & blocked:
                removed.add(p.id)
                blocked.add(p.id)
                if p.conclusion.get("fact_id"):
                    blocked.add(p.conclusion["fact_id"])
        if previous == len(removed):
            break
    removed_rows = []
    for ws in project.workspaces:
        rows = [d for d in ws.differentials
                if d.proposition_id in removed or d.label == FACT or d.id.endswith(ROW)]
        ids = {d.id for d in rows}
        removed_rows.extend((ws.id, d.id) for d in rows)
        maps = {d.linear_map_id for d in rows if d.linear_map_id}
        ws.differentials = [d for d in ws.differentials if d.id not in ids]
        ws.propositions = [p for p in ws.propositions if p.id not in removed]
        ws.differential_maps = [m for m in ws.differential_maps if m.id not in maps]
        assert not any((exact_references(p.conclusion) | set(p.premise_ids)) & blocked
                       for p in ws.propositions)
    pure = next(ws for ws in project.workspaces if ws.id == THREE)
    assert any(p.conclusion.get("fact_id") == "DER-3I-EULER-CD5-cycle" for p in pure.propositions)
    return dict(project=project, production_has_row=production_has_row, removed_rows=removed_rows)


@pytest.fixture(scope="module")
def independent_project(project_audit):
    return project_audit["project"]


@pytest.fixture(scope="module")
def chart(independent_project):
    probes = [probe("A", "S62", 14, 2), probe("A:two", "S62", 14, 2, two=1),
              probe("B", "S11", 13, 21), probe("B:j", "S11", 13, 21, j=1),
              probe("B:j7", "S11", 13, 21, j=7), probe("B:two", "S11", 13, 21, two=1),
              probe("h1A", "S73", 15, 3), probe("h1B", "S22H", 14, 22),
              probe("h1B:j", "S22H", 14, 22, j=1)]
    for page, pattern in A_TARGETS.items():
        for suffix, two, j in (("", 0, 0), (":j", 0, 1), (":two", 1, 0)):
            probes.append(probe(f"A-out{page}{suffix}", pattern, 13, 2+page, two, j))
    for page, patterns in B_SOURCES.items():
        for pattern in patterns:
            for suffix, two, j in (("", 0, 0), (":j", 0, 1), (":two", 1, 0)):
                probes.append(probe(f"B-in{page}:{pattern}{suffix}", pattern, 14, 21-page, two, j))
    cells = ({(13, 2+page) for page in range(2, 20)}
             | {(14, 21-page) for page in range(2, 22)} | {(15, 0), (14, 2), (13, 21)})
    queries = [
        dict(name="A-out5", page=5, pattern="S62", source=[14, 2], target=[13, 7], targetPattern="S13"),
        dict(name="B-in7:P", page=7, pattern="S22Y", source=[14, 14], target=[13, 21], targetPattern="S11"),
        dict(name="B-in7:Q", page=7, pattern="S22H", source=[14, 14], target=[13, 21], targetPattern="S11"),
        dict(name="B-zero3", page=3, pattern="S11", source=[13, 21], target=[12, 24], targetPattern="S40", targetTwo=1),
        dict(name="A-out19", page=19, pattern="S62", source=[14, 2], target=[13, 21], targetPattern="S11"),
    ]
    payload = {
        "project": asdict(independent_project), "workspaces": [THREE, INTEGER],
        "pages": list(range(2, 22)), "pagesByWorkspace": {INTEGER: [2, 9, 10, 24]},
        "vectorAudit": True, "auditNoClipping": True,
        "boundsByWorkspace": {
            THREE: dict(stemMin=10, stemMax=16, filtrationMin=0, filtrationMax=30),
            INTEGER: dict(stemMin=11, stemMax=14, filtrationMin=0, filtrationMax=64),
        },
        "inventoryProbes": {THREE: probes, INTEGER: [
            probe("eB", "I02", 12, 22), probe("eB:j", "I02", 12, 22, j=1),
            probe("eB:two", "I02", 12, 22, two=1)]},
        "inventoryCells": {THREE: [list(g) for g in sorted(cells)],
                           INTEGER: [[12, f] for f in range(22, 65)]},
        "candidateQueries": queries, "witnesses": WITNESSES,
        "vectorProbes": [dict(components=c, stem=14, filtration=f)
                         for f in (6, 14) for c in (P, Q, SUM)],
    }
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "input.pages.map(page => {"
    assert harness.count(marker) == 1
    harness = harness.replace(marker, "(input.pagesByWorkspace?.[id] || input.pages).map(page => {")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""
    const same=(grade,expected)=>grade.stem===expected[0]&&grade.filtration===expected[1];
    const typed=(pattern,two=0)=>ws.classes.find(n=>!n.archived
      &&n.style?.e2_pattern===pattern&&(n.style.two_valuation||0)===two
      &&!(n.style.j_order||0)&&(!n.style.e2_components
        ||JSON.stringify(n.style.e2_components)===JSON.stringify({[pattern]:1})));
    return {
      inventoryProbes:input.inventoryProbes[id].map(p=>{
        const node={style:{e2_pattern:p.pattern,two_valuation:p.two,j_order:p.j}};
        const grade={stem:p.stem,filtration:p.filtration};
        return {...p,live:algebra.live(node,grade),ports:[...(algebra.ports(node,grade)||[])]};
      }),
      inventoryCells:input.inventoryCells[id].map(([s,f])=>({stem:s,filtration:f,
        trusted:algebra.inTrustedDomain({stem:s,filtration:f}),
        patterns:[...new Set(points.filter(p=>p.grade.stem===s&&p.grade.filtration===f)
          .map(p=>p.item.style?.e2_pattern).filter(Boolean))].sort()})),
      witnessEdges:edges.filter(e=>id==='ws_integer'
        ?page===9&&same(e.sourceGrade,[13,13])&&same(e.targetGrade,[12,22])
        :input.witnesses.some(([r,s,t])=>r===page&&same(e.sourceGrade,s)&&same(e.targetGrade,t)))
        .map(e=>{
          const p=algebra.endpoints(e.diff);
          return {id:e.diff.id,source:[e.sourceGrade.stem,e.sourceGrade.filtration],
            target:[e.targetGrade.stem,e.targetGrade.filtration],
            sourcePattern:p.source.style?.e2_pattern,targetPattern:p.target.style?.e2_pattern,
            targetComponents:p.target.style?.e2_components,targetJ:p.target.style?.j_order||0,
            targetTwo:p.target.style?.two_valuation||0,
            admitted:algebra.canApply(e.diff),coefficient:algebra.coefficientState(e.diff),
            sourceLive:algebra.live(p.source,e.sourceGrade),targetLive:algebra.live(p.target,e.targetGrade)};
        }),
      candidateQueries:id!=='ws_3sigma_i'?[]:input.candidateQueries.filter(q=>q.page===page).map(q=>{
        const source=typed(q.pattern),target=typed(q.targetPattern,q.targetTwo||0);
        if(!source||!target)throw new Error('Missing actual endpoint: '+q.name);
        const query={id:'readonly-ad2-inventory-'+q.name,source_id:source.id,target_id:target.id,
          page,status:'review',coefficient_scope:'exact-port'};
        const c=algebra.candidateState(query,{stem:q.source[0],filtration:q.source[1]},
          {stem:q.target[0],filtration:q.target[1]});
        return {name:q.name,status:c.status,conditional:c.conditional,reasons:c.reasons};
      }),
      page, points: points.length"""
    result = subprocess.run(["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
                            input=json.dumps(payload), text=True, encoding="utf-8", capture_output=True,
                            check=True, timeout=240)
    return {w["id"]: {p["page"]: p for p in w["pages"]} for w in json.loads(result.stdout)}


def observation(chart, page, name, workspace=THREE):
    return next(p for p in chart[workspace][page]["inventoryProbes"] if p["name"] == name)


def vector(chart, page, filtration, components):
    return next(p for p in chart[THREE][page]["vectorProbes"]
                if p["stem"] == 14 and p["filtration"] == filtration and p["components"] == components)


def witness(chart, page, source, target, workspace=THREE):
    rows = [e for e in chart[workspace][page]["witnessEdges"]
            if e["source"] == list(source) and e["target"] == list(target)]
    assert rows, (workspace, page, source, target)
    assert all(e["admitted"] and e["sourceLive"] and e["targetLive"]
               and e["coefficient"]["resolved"] and e["coefficient"]["value"] == 1 for e in rows)
    return rows


def test_future_d19_is_not_a_premise_and_cd5_is_retained(independent_project, chart):
    for ws in independent_project.workspaces:
        assert not any(d.id.endswith(ROW) or d.label == FACT for d in ws.differentials)
        assert not any(p.conclusion.get("fact_id") == FACT for p in ws.propositions)
    for pages in chart.values():
        for row in pages.values():
            assert row["blockedFromPage"] is None and not row["conflicts"]
            assert not row["dangling"]


def test_present_production_conclusion_is_removed_from_all_three_atlas_images(project_audit):
    if project_audit["production_has_row"]:
        rows = [(ws, ident) for ws, ident in project_audit["removed_rows"] if ident.endswith(ROW)]
        assert len(rows) == 3 and len({ws for ws, _ in rows}) == 3, rows
        assert any(ws == THREE for ws, _ in rows)
    else:
        assert not project_audit["removed_rows"]


def test_both_complete_e2_inventories_and_empty_even_slots(chart):
    cells = {(p["stem"], p["filtration"]): set(p["patterns"])
             for p in chart[THREE][2]["inventoryCells"]}
    for page, pattern in A_TARGETS.items():
        assert cells[13, 2+page] == {pattern}, page
    for page, patterns in B_SOURCES.items():
        assert cells[14, 21-page] == set(patterns), page
        for pattern in patterns:
            assert not observation(chart, 2, f"B-in{page}:{pattern}:two")["live"]
    for page in range(2, 20, 2):
        assert not cells[13, 2+page] and not cells[14, 21-page]
    assert not cells[14, 1] and not cells[14, 0] and not cells[15, 0]


def test_low_a_survival_and_distinct_same_cell_primitive_direction(chart):
    for page in range(2, 20):
        assert observation(chart, page, "A")["live"]
        assert observation(chart, page, "A")["ports"] == ["0:0"]
        assert not observation(chart, page, "A:two")["live"]
    rows = witness(chart, 3, (14, 2), (13, 5))
    assert all(e["sourcePattern"] == "S62V" and e["targetJ"] == 1 for e in rows)
    for suffix in ("", ":j"):
        assert observation(chart, 3, "B-in19:S62V" + suffix)["live"]
        assert not observation(chart, 4, "B-in19:S62V" + suffix)["live"]


def test_b_constant_reaches_e19_without_the_future_row_but_its_j_ideal_does_not(chart):
    for page in range(2, 22):
        assert observation(chart, page, "B")["live"]
        assert not observation(chart, page, "B:two")["live"]
    for suffix in (":j", ":j7"):
        assert observation(chart, 3, "B" + suffix)["live"]
        assert not observation(chart, 4, "B" + suffix)["live"]
    assert observation(chart, 19, "B")["ports"] == ["0:0"]
    rows = witness(chart, 3, (14, 18), (13, 21))
    assert all(e["sourcePattern"] == "S62V" and e["targetJ"] == 1 for e in rows)


@pytest.mark.parametrize("name,page,fact", (
    ("A-out5", 5, "der-3i-d5-a-even"),
    ("B-in7:P", 7, "der-3i-d7-p-even"),
    ("B-in7:Q", 7, "der-3i-d7-q-zero"),
    ("B-zero3", 3, "der-3i-euler-cd5-cycle"),
))
def test_independent_registered_zero_constraints_cover_live_candidate_ports(chart, name, page, fact):
    query = next(q for q in chart[THREE][page]["candidateQueries"] if q["name"] == name)
    assert query["status"] == "contradicted" and query["conditional"] is False, query
    assert fact in json.dumps(query["reasons"]).lower(), query


@pytest.mark.parametrize("page,absent_from", ((7, 4), (9, 6), (11, 10), (13, 6), (15, 4), (17, 6)))
def test_a_earlier_outgoing_targets_are_quotient_zero(chart, page, absent_from):
    assert observation(chart, 3, f"A-out{page}")["live"]
    assert not observation(chart, absent_from, f"A-out{page}")["live"]
    assert not observation(chart, page, f"A-out{page}")["live"]
    assert not observation(chart, page, f"A-out{page}:j")["live"]
    assert not observation(chart, 2, f"A-out{page}:two")["live"]


def test_all_earlier_source_or_target_removals_have_real_maps(chart):
    for page, source, target in WITNESSES:
        witness(chart, page, source, target)


def test_b_incoming7_uses_the_finite_p_equals_q_quotient_not_two_directions(chart):
    for page in (7, 9):
        p, q, total = (vector(chart, page, 14, c) for c in (P, Q, SUM))
        assert p["live"] and q["live"] and not total["live"]
        assert p["slots"] == q["slots"] and len(p["slots"]) == 1
        assert not observation(chart, page, "B-in7:S22H:j")["live"]
    assert all(e["targetComponents"] == SUM for e in witness(chart, 5, (15, 9), (14, 14)))
    rows = witness(chart, 9, (14, 14), (13, 23))
    assert {e["sourcePattern"] for e in rows} == {"S22Y", "S22H"}
    assert all(e["targetPattern"] == "S13" for e in rows)
    assert not vector(chart, 10, 14, P)["live"] and not vector(chart, 10, 14, Q)["live"]


def test_b_incoming11_and15_are_absent_and_only_the_finite_a_remains_at19(chart):
    for page in (11, 15, 19):
        for pattern in B_SOURCES[page]:
            name = f"B-in{page}:{pattern}"
            assert observation(chart, page, name)["live"] is (page == 19 and pattern == "S62")
            assert not observation(chart, page, name + ":j")["live"]
    query = next(q for q in chart[THREE][19]["candidateQueries"] if q["name"] == "A-out19")
    assert query["status"] == "possible"  # not installed or treated as already proved


def test_h1_product_target_is_already_a_boundary_not_a_second_d19_arrow(chart):
    assert observation(chart, 5, "h1B")["live"]
    rows = witness(chart, 5, (15, 17), (14, 22))
    assert all(e["targetPattern"] == "S22H" and e["targetJ"] == 0
               and e.get("targetComponents") in (None, Q) for e in rows)
    for page in (6, 19):
        assert not observation(chart, page, "h1B")["live"]
        assert not observation(chart, page, "h1B:j")["live"]
    assert observation(chart, 19, "h1A")["live"]
    # The true product identity h1*A=R does not permit drawing an arrow to
    # an E19-zero target; it gives only the zero h1-multiple of the equation.


def test_integer_euler_image_has_one_finite_e9_direction_and_a_real_d9_preimage(chart):
    cells = {(p["stem"], p["filtration"]): p for p in chart[INTEGER][2]["inventoryCells"]}
    assert cells[12, 22]["patterns"] == ["I02"]
    assert observation(chart, 9, "eB", INTEGER)["live"]
    assert observation(chart, 9, "eB", INTEGER)["ports"] == ["0:0"]
    assert not observation(chart, 9, "eB:j", INTEGER)["live"]
    assert not observation(chart, 9, "eB:two", INTEGER)["live"]
    rows = witness(chart, 9, (13, 13), (12, 22), workspace=INTEGER)
    assert all(e["targetPattern"] == "I02" for e in rows)
    for page in (10, 24):
        assert not observation(chart, page, "eB", INTEGER)["live"]
        assert not observation(chart, page, "eB", INTEGER)["ports"]


def test_integer_higher_filtrations_are_empty_by_actual_maps_not_a_display_cutoff(chart):
    rows = chart[INTEGER][24]["inventoryCells"]
    assert all(p["trusted"] and not p["patterns"] for p in rows if p["filtration"] >= 22)
    assert chart[INTEGER][24]["high"] == 0
    # This negative control re-renders without differential rows; it must
    # expose high E2 classes.  It is not a hardcoded vanishing-line clip.
    assert chart[INTEGER][24]["unmappedHigh"] > 0
