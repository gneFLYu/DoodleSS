"""Page-nine Leibniz zeros on TD and TD5, not permanent-cycle assertions.

Actual migrated chart records supply the three atlas images and all earlier
differentials. D8 translates and forward g preserve the constant finite line;
the distinct TD3/TD7 sources retain their verified nonzero d9. Small abstract
modules additionally check the scope of the real zero-certificate metadata,
without adding those hypothetical arrows to a saved or production project.
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
from domain.migrations import migrate_project
from domain.seed import demo_project
from test_vector_page_invariants import runtime


ATLAS = {"ws_3sigma_i": 0, "ws_q8-ro-a0-b3": 0, "ws_q8-ro-a1-b1": 16}
FACTS = {power: f"DER-3I-LEIBNIZ-TD{power}-D9-zero" for power in (1, 5)}
NONZERO = {3: "diff_three_d9_25", 7: "formal_diff_three_d9_t_D7_sibling"}
TRANSLATES = tuple((d8, g) for d8 in (-1, 0, 1) for g in (0, 1))


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    selected = [w for w in project.workspaces if w.id == "ws_3sigma_i" or
                w.settings.get("atlas_transport", {}).get("source_workspace_id") == "ws_3sigma_i"]
    assert {w.id for w in selected} == set(ATLAS)
    return selected


def zero_records(workspace):
    nodes = {node.id: node for node in workspace.classes}
    records = []
    for power, fact in FACTS.items():
        claims = [p for p in workspace.propositions if p.conclusion.get("fact_id") == fact]
        assert len(claims) == 1
        claim = claims[0]
        records.append((power, claim, nodes[claim.conclusion["source_id"]]))
    return records


def test_six_zero_claims_have_exact_page_port_and_transport_scope(project):
    count = 0
    for workspace in images(project):
        for power, claim, source in zero_records(workspace):
            count += 1
            data = claim.conclusion
            assert claim.kind == "zero-differential"
            assert claim.status == data["admission_status"] == "verified"
            assert data["zero"] is True and data["page"] == 9
            assert data["cycle_constraint"] == "outgoing-only"
            assert data["coefficient_scope"] == "exact-port"
            assert data["source_status"] == "independently-verified"
            assert not data["source_blockers"] and not data.get("withdrawn_dependencies")
            assert data["verification_certificate"]["status"] == "verified"
            assert data["period_stem"] == 64
            assert data["forward_period"] == {
                "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
            }
            assert (source.grade.stem, source.grade.filtration) == (8*power + 1 + ATLAS[workspace.id], 3)
            assert (source.style["e2_pattern"], source.style.get("two_valuation", 0),
                    source.style.get("j_order", 0)) == ("S13", 0, 0)
            assert not source.archived and source.page <= 9
            assert not any(d.proposition_id == claim.id or d.label == FACTS[power]
                           for d in workspace.differentials)
            assert not any(p.kind == "permanent-cycle" and p.conclusion.get("fact_id") == FACTS[power]
                           for p in workspace.propositions)
    assert count == 6


def test_migration_restores_exact_sources_and_is_idempotent(project):
    candidate = deepcopy(project)
    expected = {
        w.id: [(power, asdict(claim), asdict(source)) for power, claim, source in zero_records(w)]
        for w in images(candidate)
    }
    for workspace in images(candidate):
        ids = {claim.id for _, claim, _ in zero_records(workspace)}
        workspace.propositions = [p for p in workspace.propositions if p.id not in ids]
    for _ in range(2):
        candidate = migrate_project(candidate)
        assert {
            w.id: [(power, asdict(claim), asdict(source)) for power, claim, source in zero_records(w)]
            for w in images(candidate)
        } == expected


def point(name, pattern, stem, filtration, two=0, j=0):
    return {"name": name, "pattern": pattern, "stem": stem, "filtration": filtration, "two": two, "j": j}


@pytest.fixture(scope="module")
def chart(project):
    workspaces = images(project)
    probes = []
    for workspace in workspaces:
        for power in (1, 3, 5, 7):
            for d8, g in TRANSLATES:
                stem, filtration = 8*power + 1 + ATLAS[workspace.id] + 64*d8 + 20*g, 3 + 4*g
                prefix = f"{workspace.id}:TD{power}:D8{d8}:g{g}"
                probes += [point(prefix+":source", "S13", stem, filtration),
                           point(prefix+":target", "S40", stem-1, filtration+9, two=1),
                           point(prefix+":source-j", "S13", stem, filtration, j=1)]
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [9, 10], "vectorAudit": True, "finiteProbes": probes,
        "nonzeroSuffixes": list(NONZERO.values()), "zeroFacts": list(FACTS.values()),
        "boundsByWorkspace": {
            w.id: {"stemMin": ATLAS[w.id]-60, "stemMax": ATLAS[w.id]+144,
                   "filtrationMin": 0, "filtrationMax": 16} for w in workspaces
        },
    }
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""return {
      finiteProbes:input.finiteProbes.map(probe=>{
        const node={style:{e2_pattern:probe.pattern,two_valuation:probe.two,j_order:probe.j}};
        const grade={stem:probe.stem,filtration:probe.filtration};
        return {...probe,live:algebra.live(node,grade),ports:[...(algebra.ports(node,grade)||[])]};
      }),
      nonzeroEdges:edges.filter(e=>input.nonzeroSuffixes.some(s=>e.diff.id.endsWith(s)))
        .map(e=>({id:e.diff.id,source:e.sourceGrade,target:e.targetGrade,
          admitted:algebra.canApply(e.diff),status:e.diff.status})),
      zeroEdges:edges.filter(e=>input.zeroFacts.includes(e.diff.label)).length,
      page, points: points.length"""
    result = subprocess.run(
        ["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
        input=json.dumps(payload), text=True, encoding="utf-8",
        capture_output=True, check=True, timeout=180,
    )
    return {workspace["id"]: {row["page"]: row for row in workspace["pages"]}
            for workspace in json.loads(result.stdout)}


def observation(row, name):
    return next(probe for probe in row["finiteProbes"] if probe["name"] == name)


@pytest.mark.parametrize("workspace_id", tuple(ATLAS))
def test_td1_td5_and_potential_targets_remain_without_inventing_j_tails(chart, workspace_id):
    rows = chart[workspace_id]
    for power in (1, 5):
        for d8, g in TRANSLATES:
            prefix = f"{workspace_id}:TD{power}:D8{d8}:g{g}"
            for page in (9, 10):
                source = observation(rows[page], prefix+":source")
                target = observation(rows[page], prefix+":target")
                assert source["live"] and source["ports"] == ["0:0"]
                assert target["live"] and target["ports"] == ["1:0"]
                assert not observation(rows[page], prefix+":source-j")["live"]
    for row in rows.values():
        assert not row["conflicts"] and row["blockedFromPage"] is None
        assert not row["dangling"] and row["zeroEdges"] == 0


@pytest.mark.parametrize("workspace_id", tuple(ATLAS))
def test_distinct_td3_td7_nonzero_d9_families_still_take_their_quotients(chart, workspace_id):
    rows = chart[workspace_id]
    for power, suffix in NONZERO.items():
        for d8, g in TRANSLATES:
            prefix = f"{workspace_id}:TD{power}:D8{d8}:g{g}"
            for endpoint, port in (("source", "0:0"), ("target", "1:0")):
                before = observation(rows[9], prefix+":"+endpoint)
                after = observation(rows[10], prefix+":"+endpoint)
                assert before["live"] and before["ports"] == [port]
                assert not after["live"] and not after["ports"]
            stem = 8*power + 1 + ATLAS[workspace_id] + 64*d8 + 20*g
            filtration = 3 + 4*g
            edge = next(e for e in rows[9]["nonzeroEdges"] if e["id"].endswith(suffix)
                        and e["source"]["stem"] == stem and e["source"]["filtration"] == filtration)
            assert edge["target"]["stem"] == stem-1 and edge["target"]["filtration"] == filtration+9
            assert edge["status"] == "verified" and edge["admitted"]
    assert not rows[10]["nonzeroEdges"]


@pytest.mark.parametrize("power", (1, 5))
def test_actual_zero_metadata_restricts_only_outgoing_d9_in_abstract_modules(project, power):
    workspace = next(w for w in images(project) if w.id == "ws_3sigma_i")
    _, claim, _ = next(record for record in zero_records(workspace) if record[0] == power)
    # Keep the actual scope metadata, but remap IDs and place one hypothetical
    # local module at a time. These are engine contracts, not added theorems.
    declaration = asdict(claim)
    declaration["conclusion"]["source_id"] = "finite-source"
    declaration["conclusion"]["class_id"] = "finite-source"
    result = runtime(r"""
      bounds.filtrationMax=24;
      helpers.accepted=record=>['proven','verified'].includes(record.status);
      const data=DECLARATION;
      const stem=SOURCE_STEM;
      const cases=[
        {name:'outgoing-d9',page:9,incoming:false},
        {name:'outgoing-d11',page:11,incoming:false},
        {name:'incoming-d2',page:2,incoming:true},
      ];
      console.log(JSON.stringify(cases.map(test=>{
        const source=node('finite-source','S13',stem,3);
        const other=node('other','I13',stem+(test.incoming?1:-1),test.incoming?1:3+test.page);
        const row=diff('hypothetical',test.incoming?other.id:source.id,
          test.incoming?source.id:other.id,test.page);
        const ws=workspace(test.page+1,[source,other],[row],[structuredClone(data)]);
        const algebra=compute(ws);
        return {name:test.name,blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
          sourceLive:algebra.live(source,source.grade),otherLive:algebra.live(other,other.grade),
          admitted:algebra.canApply(row)};
      })));
    """.replace("DECLARATION", json.dumps(declaration)).replace("SOURCE_STEM", str(8*power+1)))
    blocked, later, incoming = result
    assert blocked["blocked"] == 9 and blocked["sourceLive"] and blocked["otherLive"]
    assert not blocked["admitted"]
    assert any("zero-outgoing cycle constraint" in c["reason"] for c in blocked["conflicts"])
    for row in (later, incoming):
        assert row["blocked"] is None and not row["conflicts"]
        assert not row["sourceLive"] and not row["otherLive"]
