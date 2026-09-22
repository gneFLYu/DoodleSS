"""Euler exactness detects low XD5 without reviving its positive-g images.

The complete C4 filtration bound proves a nonzero low E-infinity detector.
Its outgoing-zero certificate transports by D8 and forward g, but does not
assert injectivity of multiplication by g: g*XD5 is the real d5(PD7) image.
All page probes use the actual migrated model and browser quotient engine.
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


FACT = "DER-3I-EULER-XD5-cycle"
ATLAS = {"ws_3sigma_i": 0, "ws_q8-ro-a0-b3": 0, "ws_q8-ro-a1-b1": 16}
D8_POWERS = (-1, 0, 1)


@pytest.fixture(scope="module")
def project():
    return migrate_project(demo_project())


def images(project):
    selected = [w for w in project.workspaces if w.id == "ws_3sigma_i" or
                w.settings.get("atlas_transport", {}).get("source_workspace_id") == "ws_3sigma_i"]
    assert {w.id for w in selected} == set(ATLAS)
    return selected


def records(workspace):
    claims = [p for p in workspace.propositions if p.conclusion.get("fact_id") == FACT]
    assert len(claims) == 1
    claim = claims[0]
    source = next(n for n in workspace.classes if n.id == claim.conclusion["source_id"])
    return claim, source


def test_exact_finite_cycle_certificate_in_all_three_atlas_images(project):
    count = 0
    for workspace in images(project):
        claim, source = records(workspace)
        count += 1
        data = claim.conclusion
        assert claim.kind == "permanent-cycle" and claim.status == "verified"
        assert data["admission_status"] == "verified" and data["page"] == 2
        assert data["cycle_constraint"] == "outgoing-only"
        assert data["coefficient_scope"] == "exact-port"
        assert data["source_status"] == "independently-verified"
        assert not data["source_blockers"] and not data.get("withdrawn_dependencies")
        assert data["period_stem"] == 64
        assert data["forward_period"] == {
            "multiplier": "g=kD^3", "stem": 20, "filtration": 4, "nonnegative": True,
        }
        assert (source.grade.stem, source.grade.filtration) == (37 + ATLAS[workspace.id], 3)
        assert (source.style["e2_pattern"], source.style.get("two_valuation", 0),
                source.style.get("j_order", 0)) == ("S53", 0, 0)
        assert not source.archived and source.page == 2
        certificate = data["verification_certificate"]
        assert certificate["status"] == "verified"
        assert certificate["method"] == "Euler cofiber and complete C4 filtration bound"
        assert certificate["source_refs"] and certificate["no_withdrawn_premise"] is True
        assert not {"FN-3I-010", "FN-3I-010-pc"}.intersection(data["derived_from"])
        assert not any(d.proposition_id == claim.id or d.label == FACT for d in workspace.differentials)
    assert count == 3


def test_migration_restores_the_cycle_and_its_source_without_duplicate_claims(project):
    candidate = deepcopy(project)
    expected = {w.id: tuple(asdict(item) for item in records(w)) for w in images(candidate)}
    for workspace in images(candidate):
        claim, _ = records(workspace)
        workspace.propositions = [p for p in workspace.propositions if p.id != claim.id]
    for _ in range(2):
        candidate = migrate_project(candidate)
        assert {w.id: tuple(asdict(item) for item in records(w)) for w in images(candidate)} == expected


def probe(name, pattern, stem, filtration, j=0):
    return {"name": name, "pattern": pattern, "stem": stem, "filtration": filtration, "j": j}


@pytest.fixture(scope="module")
def chart(project):
    workspaces = images(project)
    probes = []
    for workspace in workspaces:
        for d8 in D8_POWERS:
            stem = 37 + ATLAS[workspace.id] + 64*d8
            prefix = f"{workspace.id}:D8{d8}"
            probes += [probe(prefix+":low", "S53", stem, 3),
                       probe(prefix+":low-j", "S53", stem, 3, j=1),
                       probe(prefix+":g-image", "S53", stem+20, 7),
                       probe(prefix+":g-image-j", "S53", stem+20, 7, j=1),
                       probe(prefix+":d5-source", "S22Y", stem+21, 2),
                       probe(prefix+":S51", "S51", stem, 1),
                       probe(prefix+":S51-j", "S51", stem, 1, j=1)]
    payload = {
        "project": asdict(project), "workspaces": [w.id for w in workspaces],
        "pages": [3, 4, 5, 6, 21, 24], "vectorAudit": True,
        "finiteProbes": probes, "fact": FACT,
        "boundsByWorkspace": {
            w.id: {"stemMin": ATLAS[w.id]-32, "stemMax": ATLAS[w.id]+127,
                   "filtrationMin": 0, "filtrationMax": 8} for w in workspaces
        },
    }
    harness = (ROOT / "tests/chart_runtime.cjs").read_text(encoding="utf-8")
    marker = "return {page, points: points.length"
    assert harness.count(marker) == 1
    diagnostics = r"""return {
      finiteProbes:input.finiteProbes.map(probe=>{
        const node={style:{e2_pattern:probe.pattern,two_valuation:0,j_order:probe.j}};
        const grade={stem:probe.stem,filtration:probe.filtration};
        return {...probe,live:algebra.live(node,grade),ports:[...(algebra.ports(node,grade)||[])]};
      }),
      incomingD5:edges.filter(e=>e.diff.id.endsWith('diff_three_d5_yh2'))
        .map(e=>({id:e.diff.id,source:e.sourceGrade,target:e.targetGrade,
          admitted:algebra.canApply(e.diff),status:e.diff.status})),
      cycleEdges:edges.filter(e=>e.diff.label===input.fact).length,
      page, points: points.length"""
    completed = subprocess.run(
        ["node", "-e", harness.replace(marker, diagnostics)], cwd=ROOT,
        input=json.dumps(payload), text=True, encoding="utf-8",
        capture_output=True, check=True, timeout=180,
    )
    return {w["id"]: {p["page"]: p for p in w["pages"]} for w in json.loads(completed.stdout)}


def observation(row, name):
    return next(item for item in row["finiteProbes"] if item["name"] == name)


@pytest.mark.parametrize("workspace_id", tuple(ATLAS))
def test_low_xd5_survives_with_no_positive_j_tail(chart, workspace_id):
    rows = chart[workspace_id]
    for d8 in D8_POWERS:
        prefix = f"{workspace_id}:D8{d8}"
        for page in (3, 6, 21, 24):
            low = observation(rows[page], prefix+":low")
            assert low["live"] and low["ports"] == ["0:0"]
            assert not observation(rows[page], prefix+":low-j")["live"]
    for row in rows.values():
        assert row["blockedFromPage"] is None and not row["conflicts"]
        assert not row["dangling"] and row["cycleEdges"] == 0


@pytest.mark.parametrize("workspace_id", tuple(ATLAS))
def test_forward_g_cycle_may_be_the_real_d5_image_and_is_not_revived(chart, workspace_id):
    rows = chart[workspace_id]
    for d8 in D8_POWERS:
        prefix = f"{workspace_id}:D8{d8}"
        before = observation(rows[5], prefix+":g-image")
        assert before["live"] and before["ports"] == ["0:0"]
        assert observation(rows[5], prefix+":d5-source")["live"]
        stem = 37 + ATLAS[workspace_id] + 64*d8
        edge = next(e for e in rows[5]["incomingD5"]
                    if e["target"]["stem"] == stem+20 and e["target"]["filtration"] == 7)
        assert edge["source"]["stem"] == stem+21 and edge["source"]["filtration"] == 2
        assert edge["admitted"] and edge["status"] == "verified"
        for page in (6, 21, 24):
            image = observation(rows[page], prefix+":g-image")
            assert not image["live"] and not image["ports"]
            assert not observation(rows[page], prefix+":g-image-j")["live"]
        assert not observation(rows[6], prefix+":d5-source")["live"]


@pytest.mark.parametrize("workspace_id", tuple(ATLAS))
def test_only_other_low_filtration_column_leaves_by_injective_d3_including_j(chart, workspace_id):
    rows = chart[workspace_id]
    for d8 in D8_POWERS:
        prefix = f"{workspace_id}:D8{d8}"
        before = observation(rows[3], prefix+":S51")
        assert before["live"] and before["ports"] == ["0:0", "0:1"]
        assert observation(rows[3], prefix+":S51-j")["live"]
        for page in (4, 6, 21, 24):
            after = observation(rows[page], prefix+":S51")
            assert not after["live"] and not after["ports"]
            assert not observation(rows[page], prefix+":S51-j")["live"]


@pytest.mark.parametrize("page", (3, 9, 21))
def test_real_cycle_metadata_blocks_hypothetical_outgoing_but_allows_incoming(project, page):
    workspace = next(w for w in images(project) if w.id == "ws_3sigma_i")
    claim, _ = records(workspace)
    declaration = asdict(claim)
    declaration["conclusion"]["source_id"] = "finite-source"
    declaration["conclusion"]["class_id"] = "finite-source"
    # These artificial local arrows only test certificate semantics. They are
    # never additions to the actual spectral sequence or to the saved project.
    result = runtime(r"""
      bounds.filtrationMax=32;
      helpers.accepted=record=>['proven','verified'].includes(record.status);
      const data=DECLARATION;
      console.log(JSON.stringify([false,true].map(incoming=>{
        const source=node('finite-source','S53',37,3);
        const other=node('other','I13',incoming?38:36,incoming?1:3+PAGE);
        const row=diff('hypothetical',incoming?other.id:source.id,
          incoming?source.id:other.id,incoming?2:PAGE);
        const ws=workspace(incoming?3:PAGE+1,[source,other],[row],[structuredClone(data)]);
        const algebra=compute(ws);
        return {blocked:algebra.blockedFromPage,conflicts:algebra.conflicts,
          sourceLive:algebra.live(source,source.grade),otherLive:algebra.live(other,other.grade),
          admitted:algebra.canApply(row)};
      })));
    """.replace("DECLARATION", json.dumps(declaration)).replace("PAGE", str(page)))
    outgoing, incoming = result
    assert outgoing["blocked"] == page and outgoing["sourceLive"] and outgoing["otherLive"]
    assert not outgoing["admitted"]
    assert any("zero-outgoing cycle constraint" in row["reason"] for row in outgoing["conflicts"])
    assert incoming["blocked"] is None and not incoming["conflicts"]
    assert not incoming["sourceLive"] and not incoming["otherLive"]

